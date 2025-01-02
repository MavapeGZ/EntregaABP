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

# Función para obtener recomendaciones basadas en similitud por nombre o descripción
def get_recommendations(query, tfidf_matrix, data, by_description=False):
    feedback_data = pd.read_csv(feedback_file)

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

    # Excluir el juego original de las recomendaciones
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

# Priorizar búsqueda por nombre si ambos están llenos
search_by_name = bool(user_input_name.strip()) and not bool(user_input_description.strip())
search_by_description = bool(user_input_description.strip()) and not bool(user_input_name.strip())

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
    matching_games = data[data["name"].str.contains(user_input_name, case=False, na=False)]
    matching_game_names = matching_games["name"].tolist()

    if matching_game_names:
        selected_game = st.selectbox("Did you mean:", matching_game_names, key="game_selector")
        current_search = selected_game if selected_game else user_input_name
    #else:
    #   st.write("No games found matching your search. Please try a different name.")

# Mostrar recomendaciones
if current_search:
    recommendations = get_recommendations(current_search, tfidf_matrix, data, by_description=search_by_description)

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
