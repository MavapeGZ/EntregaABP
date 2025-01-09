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
    appid_series = data[data["name"] == game_name]["appid"]
    if not appid_series.empty:
        appid = appid_series.iloc[0]
    else:
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
            # Leer el archivo sin encabezados inicialmente
            df = pd.read_csv(file, header=None)

            # Verificar si el primer valor es una cadena que coincide con 'appid' (ignorando mayúsculas/minúsculas)
            first_cell = df.iloc[0, 0]
            if isinstance(first_cell, str) and first_cell.strip().lower() == "appid":
                # Leer nuevamente con encabezados
                df = pd.read_csv(file)
            else:
                # Asignar nombres de columnas manualmente
                df.columns = ["appid", "hours_played"]

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
        return pd.DataFrame()  # Retornar vacío para indicar que no hay datos de usuario

    # Agrupar y sumar horas jugadas
    user_data = user_data.groupby("appid")["hours_played"].sum().reset_index()

    # Filtrar juegos con horas jugadas > 0
    user_data = user_data[user_data["hours_played"] > 0]

    # Combinar con base_data para incluir información del juego
    user_library = base_data.merge(user_data, on="appid")

    return user_library

# Función para obtener recomendaciones basadas en CSVs o similitud
def get_recommendations(user_library, tfidf_full_matrix, full_data, feedback_data):
    recommendations = pd.DataFrame()
    recommended_appids = set()

    # Seleccionar los 5 juegos con más horas jugadas
    top_5 = user_library.sort_values(by="hours_played", ascending=False).head(5)

    for _, row in top_5.iterrows():
        appid = row["appid"]
        game_name = row["name"]
        data_idx = full_data[full_data["appid"] == appid].index
        if len(data_idx) == 0:
            continue
        data_idx = data_idx[0]

        # Calcular la similitud coseno con TF-IDF del juego actual
        cosine_sim = linear_kernel(tfidf_full_matrix[data_idx], tfidf_full_matrix).flatten()
        similar_indices = cosine_sim.argsort()[-100:][::-1]  # Obtener más para filtrar después

        # Crear un DataFrame de recomendaciones
        similar_games = full_data.iloc[similar_indices].copy()

        # Excluir los juegos en la biblioteca del usuario
        similar_games = similar_games[~similar_games["appid"].isin(user_library["appid"])]

        # Excluir ya recomendados
        similar_games = similar_games[~similar_games["appid"].isin(recommended_appids)]

        # Ajustar el puntaje con feedback
        similar_games["adjusted_score"] = cosine_sim[similar_indices[:len(similar_games)]]

        for i, game in similar_games.iterrows():
            game_feedback = feedback_data[feedback_data["appid"] == game["appid"]]
            likes = game_feedback[game_feedback["feedback_type"] == "like"]["count"].sum()
            dislikes = game_feedback[game_feedback["feedback_type"] == "dislike"]["count"].sum()
            feedback_score = likes - dislikes
            similar_games.at[i, "adjusted_score"] += feedback_score * 0.1

        # Ordenar por puntaje ajustado
        similar_games = similar_games.sort_values(by="adjusted_score", ascending=False)

        # Tomar los primeros 2 juegos que no hayan sido recomendados aún
        top_2 = similar_games.head(2)
        recommendations = pd.concat([recommendations, top_2], ignore_index=True)
        recommended_appids.update(top_2["appid"].tolist())

        # Si ya hemos alcanzado 10 recomendaciones, salir del loop
        if len(recommendations) >= 10:
            break

    # Asegurarse de tener como máximo 10 recomendaciones
    recommendations = recommendations.head(10)

    return recommendations

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

# Subir múltiples archivos CSV
uploaded_files = st.file_uploader("Enter up to 5 CSV Steam Libraries for recommendations:", 
                                  type="csv", accept_multiple_files=True)

# Validar el límite de archivos subidos
if uploaded_files and len(uploaded_files) > 5:
    st.error("You can upload a maximum of 5 CSV files.")
    uploaded_files = uploaded_files[:5]

# Procesar archivos subidos si existen
if uploaded_files:
    user_library = process_user_csvs(uploaded_files, data)
    if not user_library.empty:
        st.markdown(
            """
            <style>
            .stAlert {
                background-color: green !important;
                color: white !important;
                border-radius: 10px !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        st.success("Custom Steam libraries loaded successfully!")
    else:
        user_library = pd.DataFrame()
        st.warning("No valid user data found. Using default dataset for recommendations.")
else:
    user_library = pd.DataFrame()  # Librería vacía si no se suben archivos
    st.markdown(
        """
        <style>
        .stInfo {
            background-color: #E63946 !important;
            color: white !important;
            border-radius: 10px !important; 
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.info("No libraries provided. Using default dataset for name/description-based recommendations.")

# Decidir si las recomendaciones serán user_based (solo si se han subido archivos y hay datos válidos)
is_user_based = not user_library.empty

# Procesar la matriz TF-IDF completa para el dataset completo
tfidf_full, tfidf_full_matrix = process_text(data)

# Cargar el feedback una sola vez
feedback_data = pd.read_csv(feedback_file)

# Inicializar lista de exclusión en la sesión
if "excluded_games" not in st.session_state:
    st.session_state["excluded_games"] = []

# Inicializar índice de recomendaciones por búsqueda
if "current_index" not in st.session_state:
    st.session_state["current_index"] = 0

if "last_search" not in st.session_state:
    st.session_state["last_search"] = ""

# Inputs de búsqueda
query = ""
by_description = False
if not is_user_based:
    # Priorizar búsqueda por nombre si ambos están llenos
    search_by_name = bool(user_input_name.strip()) and not bool(user_input_description.strip())
    search_by_description = bool(user_input_description.strip()) and not bool(user_input_name.strip())

    if search_by_name:
        query = user_input_name
    elif search_by_description:
        query = user_input_description
else:
    # En modo user_based, no se usa query
    pass

# Resetear el estado si la búsqueda cambia
current_search = query
if current_search != st.session_state["last_search"] or is_user_based != bool(st.session_state.get("is_user_based", False)):
    st.session_state["current_index"] = 0
    st.session_state["excluded_games"] = []
    st.session_state["last_search"] = current_search
    st.session_state["is_user_based"] = is_user_based

# Mostrar sugerencias mientras el usuario escribe si busca por nombre
if not is_user_based and bool(user_input_name.strip()):
    matching_games = data[data["name"].str.contains(user_input_name, case=False, na=False)]
    matching_game_names = matching_games["name"].tolist()

    if matching_game_names:
        # Mostrar un selectbox para que el usuario elija entre los juegos coincidentes
        selected_game = st.selectbox("Did you mean:", matching_game_names, key="game_selector")
        
        # Almacenar el juego seleccionado en la sesión
        if selected_game and st.session_state.get("last_selected_game") != selected_game:
            st.session_state["last_selected_game"] = selected_game
            st.session_state["current_index"] = 0  # Reiniciar índice de recomendaciones
            st.session_state["excluded_games"] = []  # Reiniciar juegos excluidos

# Obtener recomendaciones
if is_user_based or current_search:
    if is_user_based:
        # Recomendaciones basadas en la biblioteca del usuario
        recommendations = get_recommendations(
            user_library=user_library,
            tfidf_full_matrix=tfidf_full_matrix,
            full_data=data,
            feedback_data=feedback_data
        )
    else:
        # Recomendaciones basadas en el nombre o descripción
        if search_by_description:
            # Búsqueda por descripción
            expanded_query = expand_query(query)
            query_vector = tfidf_full.transform([expanded_query])
            cosine_sim = linear_kernel(query_vector, tfidf_full_matrix).flatten()
            
            similar_indices = cosine_sim.argsort()[-50:][::-1]

            recommendations = data.iloc[similar_indices].copy()
            recommendations = recommendations.drop_duplicates(subset=["appid"]).reset_index(drop=True)
            recommendations["adjusted_score"] = cosine_sim[similar_indices[:len(recommendations)]]

            # Excluir juegos ya excluidos
            recommendations = recommendations[~recommendations["name"].isin(st.session_state["excluded_games"])]

            # Ajustar puntaje con feedback
            for i, game in recommendations.iterrows():
                game_feedback = feedback_data[feedback_data["appid"] == game["appid"]]
                likes = game_feedback[game_feedback["feedback_type"] == "like"]["count"].sum()
                dislikes = game_feedback[game_feedback["feedback_type"] == "dislike"]["count"].sum()
                feedback_score = likes - dislikes
                recommendations.at[i, "adjusted_score"] += feedback_score * 0.1

            # Ordenar y limitar a 10 recomendaciones
            recommendations = recommendations.sort_values(by="adjusted_score", ascending=False).head(10)

        elif "last_selected_game" in st.session_state and st.session_state["last_selected_game"]:
            # Búsqueda por nombre
            query = st.session_state["last_selected_game"]
            idx_series = data[data["name"] == query].index

            if len(idx_series) > 0:
                idx = idx_series[0]
                cosine_sim = linear_kernel(tfidf_full_matrix[idx], tfidf_full_matrix).flatten()

                similar_indices = cosine_sim.argsort()[-50:][::-1]

                recommendations = data.iloc[similar_indices].copy()
                recommendations = recommendations.drop_duplicates(subset=["appid"]).reset_index(drop=True)
                recommendations["adjusted_score"] = cosine_sim[similar_indices[:len(recommendations)]]

                # Excluir el juego seleccionado y juegos ya excluidos
                recommendations = recommendations[
                    (recommendations["name"] != query) &
                    (~recommendations["name"].isin(st.session_state["excluded_games"]))
                ]

                # Ajustar puntaje con feedback
                for i, game in recommendations.iterrows():
                    game_feedback = feedback_data[feedback_data["appid"] == game["appid"]]
                    likes = game_feedback[game_feedback["feedback_type"] == "like"]["count"].sum()
                    dislikes = game_feedback[game_feedback["feedback_type"] == "dislike"]["count"].sum()
                    feedback_score = likes - dislikes
                    recommendations.at[i, "adjusted_score"] += feedback_score * 0.1

                # Ordenar y limitar a 10 recomendaciones
                recommendations = recommendations.sort_values(by="adjusted_score", ascending=False).head(10)



        else:
            # Recomendaciones basadas en nombre
            idx_series = data[data["name"].str.contains(query, case=False, na=False)].index
            if len(idx_series) > 0:
                idx = idx_series[0]
                cosine_sim = linear_kernel(tfidf_full_matrix[idx], tfidf_full_matrix).flatten()

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

                # Excluir juegos ya excluidos en la sesión
                recommendations = recommendations[~recommendations["name"].isin(st.session_state["excluded_games"])]

                # Tomar las primeras 10 recomendaciones
                recommendations = recommendations.head(10)
            else:
                # No se encontró ningún juego que coincida con el nombre
                recommendations = pd.DataFrame()

    # Filtrar juegos en la lista de exclusión (solo en modo no user_based)
    if not is_user_based and "name" in recommendations.columns:
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

            # Buttons para like/dislike
            col1, col2 = st.columns(2)
            with col1:
                st.button("❤", on_click=like_game, key=f"like-{current_index}", help="Like", use_container_width=True)
            with col2:
                st.button("✖", on_click=dislike_game, key=f"dislike-{current_index}", help="Dislike", use_container_width=True)

            # Text feedback con estado de sesión
            text_feedback_key = f"feedback-{current_index}"
            if text_feedback_key not in st.session_state:
                st.session_state[text_feedback_key] = ""

            text_feedback = st.text_area(
                "Provide your feedback on this game:",
                key=text_feedback_key,  # Bind to session state
            )

            # Feedback button con callback
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
