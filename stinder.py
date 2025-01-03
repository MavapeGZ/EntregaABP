import streamlit as st
import pandas as pd
from datetime import datetime
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import deepl
from textblob import TextBlob
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
import json
import numpy as np

# Set page configuration with custom title and favicon
st.set_page_config(
    page_title="Stinder - Steam Game Recommender",
    page_icon="./public/logo.png",
    layout="centered",
    initial_sidebar_state="auto",
)

# Cargar datos
@st.cache_data
def load_data():
    return pd.read_csv("./data/steam_data.csv")

data = load_data()

# Cargar expansiones de consultas desde un archivo JSON
@st.cache_data
def load_query_expansions(file_path="./data/dictionary/synonym_dictionary.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

QUERY_EXPANSIONS = load_query_expansions()

def expand_query(query):
    words = query.lower().split()
    expanded = []
    for word in words:
        expanded.append(word)
        if word in QUERY_EXPANSIONS:
            expanded.extend(QUERY_EXPANSIONS[word])
    return " ".join(set(expanded))

# Procesar texto con TfidfVectorizer
@st.cache_resource
def process_text(data):
    tfidf = TfidfVectorizer(stop_words="english")
    # Combinar el nombre del juego, su descripción y las etiquetas para procesar el texto
    tag_columns = data.columns[6:]  # Asumimos que las etiquetas comienzan desde la columna 6
    data["tags_combined"] = data[tag_columns].fillna(0).astype(str).apply(" ".join, axis=1)
    data["processed_text"] = (data["name"] + " " + data["detailed_description"] + " " + data["tags_combined"]).fillna("")
    tfidf_matrix = tfidf.fit_transform(data["processed_text"])
    return tfidf, tfidf_matrix

tfidf, tfidf_matrix = process_text(data)

# Crear el directorio feedback si no existe
feedback_dir = "./feedback"
if not os.path.exists(feedback_dir):
    os.makedirs(feedback_dir)

# Crear archivo feedback si no existe
feedback_file = "./feedback/feedback.csv"
if not os.path.exists(feedback_file):
    pd.DataFrame(columns=["appid", "game_name", "feedback_type", "count"]).to_csv(feedback_file, index=False)

# Función para actualizar feedback en el CSV
def update_feedback(game_name, feedback_type):
    feedback_data = pd.read_csv(feedback_file)
    
    # Obtener el appid correspondiente al juego
    appid = data[data["name"] == game_name]["appid"].iloc[0] if not data[data["name"] == game_name].empty else None
    if appid is None:
        return

    # Buscar si ya existe la fila correspondiente
    match = (feedback_data["appid"] == appid) & (feedback_data["feedback_type"] == feedback_type)
    if match.any():
        feedback_data.loc[match, "count"] += 1
    else:
        feedback_data = pd.concat([
            feedback_data,
            pd.DataFrame({"appid": [appid], "game_name": [game_name], "feedback_type": [feedback_type], "count": [1]})
        ], ignore_index=True)

    # Ordenar por appid antes de guardar
    feedback_data = feedback_data.sort_values(by="appid")
    feedback_data.to_csv(feedback_file, index=False)

# Configurar el traductor de DeepL
DEEPL_API_KEY = "4dbf5d8d-2be8-4eb0-9f14-937143d569b2:fx"  # Reemplaza con tu clave de API
translator = deepl.Translator(DEEPL_API_KEY)

# Función para manejar el feedback textual
def process_text_feedback(game_name, text_feedback):
    if not text_feedback.strip():
        return  # No actualizar nada si el texto está vacío
    
    try:
        translated_feedback = translator.translate_text(text_feedback, source_lang="ES", target_lang="EN-US").text
        sentiment = "like" if TextBlob(translated_feedback).sentiment.polarity > 0 else "dislike"
    except Exception as e:
        sentiment = "unknown"

    if sentiment != "unknown":
        update_feedback(game_name, sentiment)



@st.cache_data
def process_user_csvs(uploaded_files, base_data):
    user_data = pd.DataFrame()

    for file in uploaded_files:
        try:
            # Leer el archivo y detectar estructura
            df = pd.read_csv(file, header=None)

            # Detectar estructura específica de columnas
            if df.iloc[0, 0] == "appid":  # Archivo con encabezados
                df = pd.read_csv(file)  # Leer nuevamente con encabezados
            else:  # Archivo sin encabezados
                df.columns = ["appid", "hours_played"]  # Asignar nombres de columnas

            # Convertir tipos de datos
            df["appid"] = df["appid"].astype(int)
            df["hours_played"] = df["hours_played"].astype(float)

            # Filtrar por appids válidos
            df = df[df["appid"].isin(base_data["appid"])]

            # Concatenar datos válidos
            user_data = pd.concat([user_data, df], ignore_index=True)

        except pd.errors.EmptyDataError:
            st.error(f"The file {file.name} is empty.")
        except ValueError as ve:
            st.error(f"Error processing {file.name}: {ve}")
        except Exception as e:
            st.error(f"Unexpected error with {file.name}: {e}")

    if user_data.empty:
        st.warning("No valid data was processed. Using default dataset.")
        return base_data

    # Agrupar y sumar horas jugadas
    user_data = user_data.groupby("appid")["hours_played"].sum().reset_index()

    # Combinar con base_data
    merged_data = base_data.merge(user_data, on="appid", how="left")
    merged_data["hours_played"] = merged_data["hours_played"].fillna(0)

    # Filtrar juegos con horas jugadas > 0
    filtered_data = merged_data[merged_data["hours_played"] > 0]

    return filtered_data

# Función para obtener recomendaciones basadas en CSVs o similitud
def get_recommendations(query, tfidf_matrix, data, by_description=False, user_based=False):
    # Cargamos el feedback
    feedback_data = pd.read_csv(feedback_file)

    # === CASO 1: RECOMENDACIONES BASADAS EN LAS CSV DEL USUARIO ===
    if user_based:
        filtered_data = data[data["hours_played"] > 0]
        if filtered_data.empty:
            return pd.DataFrame()  # Si no hay datos válidos

        # 1) 5 juegos más jugados
        top_5 = filtered_data.sort_values(by="hours_played", ascending=False).head(5)

        # 2) DataFrame final de recomendaciones y set para evitar duplicados
        final_recommendations = pd.DataFrame()
        recommended_appids = set()

        # 3) Para cada uno de los 5 juegos más jugados
        for _, row in top_5.iterrows():
            appid = row["appid"]
            data_idx = data[data["appid"] == appid].index
            if len(data_idx) == 0:
                continue
            data_idx = data_idx[0]

            # Calcular la similitud coseno con TF-IDF
            cosine_sim = linear_kernel(tfidf_matrix[data_idx], tfidf_matrix).flatten()
            similar_indices = cosine_sim.argsort()[-50:][::-1]

            # Crear un DataFrame de recomendaciones
            recommendations = data.iloc[similar_indices].copy()
            recommendations = recommendations.drop_duplicates(subset=["appid"]).reset_index(drop=True)

            # Agregar columna "adjusted_score"
            recommendations["adjusted_score"] = cosine_sim[similar_indices[:len(recommendations)]]

            # Ajustar el puntaje con feedback
            for i, game in recommendations.iterrows():
                game_feedback = feedback_data[feedback_data["appid"] == game["appid"]]
                likes = game_feedback[game_feedback["feedback_type"] == "like"]["count"].sum()
                dislikes = game_feedback[game_feedback["feedback_type"] == "dislike"]["count"].sum()
                feedback_score = likes - dislikes
                recommendations.at[i, "adjusted_score"] += feedback_score * 0.1

            # Excluir el propio juego base y juegos ya recomendados
            recommendations = recommendations[recommendations["appid"] != appid]
            recommendations = recommendations[~recommendations["appid"].isin(recommended_appids)]

            # Ordenar por score ajustado
            recommendations = recommendations.sort_values(by="adjusted_score", ascending=False)

            # Tomar los 2 primeros
            top_2 = recommendations.head(2)

            # Agregar al DataFrame final
            final_recommendations = pd.concat([final_recommendations, top_2], ignore_index=True)

            # Actualizar el set de appids recomendados
            recommended_appids.update(top_2["appid"].tolist())

        return final_recommendations

    # === CASO 2: RECOMENDACIONES BASADAS EN NOMBRE O DESCRIPCIÓN ===
    if by_description:
        expanded_query = expand_query(query)
        query_vector = tfidf.transform([expanded_query])
        cosine_sim = linear_kernel(query_vector, tfidf_matrix).flatten()
    else:
        idx = data[data["name"].str.contains(query, case=False, na=False)].index
        if len(idx) == 0:
            return pd.DataFrame()
        idx = idx[0]
        cosine_sim = linear_kernel(tfidf_matrix[idx], tfidf_matrix).flatten()

    similar_indices = cosine_sim.argsort()[-50:][::-1]

    # Crear un DataFrame de recomendaciones con puntaje ajustado
    recommendations = data.iloc[similar_indices].copy()
    recommendations = recommendations.drop_duplicates(subset=["appid"]).reset_index(drop=True)
    recommendations["adjusted_score"] = cosine_sim[similar_indices[:len(recommendations)]]

    # Ajustar el puntaje usando feedback
    for i, game in recommendations.iterrows():
        game_feedback = feedback_data[feedback_data["appid"] == game["appid"]]
        likes = game_feedback[game_feedback["feedback_type"] == "like"]["count"].sum()
        dislikes = game_feedback[game_feedback["feedback_type"] == "dislike"]["count"].sum()
        feedback_score = likes - dislikes
        recommendations.at[i, "adjusted_score"] += feedback_score * 0.1

    # Ordenar por puntaje ajustado
    recommendations = recommendations.sort_values(by="adjusted_score", ascending=False)

    # Excluir el juego original de las recomendaciones (si coincide el nombre)
    if "name" in recommendations.columns:
        recommendations = recommendations[recommendations["name"] != query]

    return recommendations.head(10)


# Configurar la interfaz
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #1a1a1a, #ff0000);
        color: white;
        text-align: center;
    }
    .stButton > button {
        border-radius: 50%;
        width: 60px;
        height: 60px;
        font-size: 20px;
    }
    .like-button {
        background-color: #28a745;
        color: white;
    }
    .dislike-button {
        background-color: #dc3545;
        color: white;
    }
    .centered {
        display: flex;
        justify-content: center;
        align-items: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

coli, colii, coliii = st.columns([1, 2, 1])
with colii:
    st.image("./public/logo.png", width=400)

st.markdown("<h1 style='text-align: center; margin-left: 15px;'>Stinder</h1>", unsafe_allow_html=True)

# Inputs para buscar un juego por nombre o descripción
user_input_name = st.text_input("Enter a game name to get recommendations:")
user_input_description = st.text_area("Enter a description to get recommendations:")

# Por defecto, usar el DataFrame original:
combined_data = data.copy()  ### CAMBIO
combined_data.reset_index(drop=True, inplace=True)  ### CAMBIO

tfidf, tfidf_matrix = process_text(combined_data)  ### CAMBIO

# Subir múltiples archivos CSV
uploaded_files = st.file_uploader("Enter up to 5 CSV Steam Librarys for recomendations:", 
                                  type="csv", accept_multiple_files=True)

# Validar el límite de archivos subidos
if uploaded_files and len(uploaded_files) > 5:
    st.error("You can upload a maximum of 5 CSV files.")
    uploaded_files = uploaded_files[:5]

# Procesar archivos subidos si existen
if uploaded_files:
    combined_data = process_user_csvs(uploaded_files, data)
    combined_data.reset_index(drop=True, inplace=True)

    # Volvemos a generar la matriz TF-IDF con combined_data
    tfidf, tfidf_matrix = process_text(combined_data)  
    st.success("Custom Steam libraries loaded successfully!")
else:
    # Si no suben librerías, usar la dataset por defecto (ya está en combined_data) y la tfidf_matrix ya creada al inicio.
    st.info("No libraries provided. Using default dataset for name/description-based recommendations.")

# Decidir si las recomendaciones serán user_based (solo si se han subido archivos).
is_user_based = bool(uploaded_files and len(uploaded_files) > 0)

# Priorizar búsqueda por nombre si ambos están llenos
search_by_name = bool(user_input_name.strip()) and not bool(user_input_description.strip())
search_by_description = bool(user_input_description.strip()) and not bool(user_input_name.strip())

# Si hay algo que buscar (o hay CSVs) calculamos recomendaciones:
if user_input_name or user_input_description or is_user_based:
    recommendations = get_recommendations(
        query=user_input_name if search_by_name else user_input_description,
        tfidf_matrix=tfidf_matrix,
        data=combined_data,
        by_description=search_by_description,
        user_based=is_user_based
    )

# Inicializar lista de exclusión en la sesión
if "excluded_games" not in st.session_state:
    st.session_state["excluded_games"] = []

# Inicializar índice de recomendaciones por búsqueda
if "current_index" not in st.session_state:
    st.session_state["current_index"] = 0

if "last_search" not in st.session_state:
    st.session_state["last_search"] = ""

# Resetear el estado si la búsqueda cambia
current_search = user_input_name if search_by_name else user_input_description
if current_search != st.session_state["last_search"]:
    st.session_state["current_index"] = 0
    st.session_state["excluded_games"] = []
    st.session_state["last_search"] = current_search

# Mostrar sugerencias mientras el usuario escribe si busca por nombre
if search_by_name and user_input_name:
    matching_games = combined_data[combined_data["name"].str.contains(user_input_name, case=False, na=False)]
    matching_game_names = matching_games["name"].tolist()

    if matching_game_names:
        selected_game = st.selectbox("Did you mean:", matching_game_names, key="game_selector")
        current_search = selected_game if selected_game else user_input_name

# Mostrar recomendaciones
if current_search or uploaded_files:
    recommendations = get_recommendations(
        query=current_search if not uploaded_files else "",
        tfidf_matrix=tfidf_matrix,
        data=combined_data,
        by_description=search_by_description,
        user_based=bool(uploaded_files)
    )

    # Filtrar juegos en la lista de exclusión
    if "name" in recommendations.columns:
        recommendations = recommendations[~recommendations["name"].isin(st.session_state["excluded_games"])]

    if not recommendations.empty:
        current_index = st.session_state["current_index"]
        if current_index < len(recommendations):
            game = recommendations.iloc[current_index]

            st.image(game["header_image"], use_container_width=True)
            st.subheader(game["name"])

            # Callback functions for button actions
            def like_game():
                update_feedback(game["name"], "like")
                st.session_state["current_index"] += 1

            def dislike_game():
                update_feedback(game["name"], "dislike")
                st.session_state["excluded_games"].append(game["name"])
                st.session_state["current_index"] += 1

            # Buttons for like/dislike
            col1, col2 = st.columns(2)
            with col1:
                st.button("❤", on_click=like_game, key=f"like-{current_index}", help="Like", use_container_width=True)
            with col2:
                st.button("✖", on_click=dislike_game, key=f"dislike-{current_index}", help="Dislike", use_container_width=True)

            # Text feedback with session state
            text_feedback_key = f"feedback-{current_index}"
            if text_feedback_key not in st.session_state:
                st.session_state[text_feedback_key] = ""

            text_feedback = st.text_area(
                "Provide your feedback on this game:",
                key=text_feedback_key,  # Bind to session state
            )

            # Feedback button with callback
            def submit_feedback():
                process_text_feedback(game["name"], st.session_state[text_feedback_key])
                st.success("Thank you for your feedback!")
                st.session_state["current_index"] += 1

            st.button(
                "Submit Feedback",
                on_click=submit_feedback,
                key=f"submit-feedback-{current_index}",
                help="Submit Feedback",
                use_container_width=False,
            )

        else:
            st.write("No more recommendations. Try a different search.")
    else:
        st.write("No games found matching your search. Please try a different name.")
