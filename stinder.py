import streamlit as st
import pandas as pd
from datetime import datetime
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import deepl
from textblob import TextBlob

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

# Procesar texto con TfidfVectorizer
@st.cache_resource
def process_text(data):
    tfidf = TfidfVectorizer(stop_words="english")
    data["processed_text"] = data["detailed_description"].fillna("")
    tfidf_matrix = tfidf.fit_transform(data["processed_text"])
    return tfidf, tfidf_matrix

tfidf, tfidf_matrix = process_text(data)

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

# Función para obtener recomendaciones basadas en similitud
# Modifica las recomendaciones utilizando feedback de usuarios
def get_recommendations(game_name, tfidf_matrix, data):
    feedback_data = pd.read_csv(feedback_file)
    idx = data[data["name"].str.contains(game_name, case=False, na=False)].index
    if len(idx) == 0:
        return pd.DataFrame()
    idx = idx[0]
    cosine_sim = linear_kernel(tfidf_matrix[idx], tfidf_matrix).flatten()
    similar_indices = cosine_sim.argsort()[-50:][::-1]  # Asegurarse de tener suficientes recomendaciones iniciales

    # Crear un DataFrame de recomendaciones con puntaje ajustado
    recommendations = data.iloc[similar_indices].copy()
    recommendations = recommendations.drop_duplicates(subset=["appid"]).reset_index(drop=True)  # Eliminar duplicados
    recommendations["adjusted_score"] = cosine_sim[similar_indices[:len(recommendations)]]

    # Ajustar el puntaje usando feedback
    for i, game in recommendations.iterrows():
        game_feedback = feedback_data[feedback_data["appid"] == game["appid"]]
        likes = game_feedback[game_feedback["feedback_type"] == "like"]["count"].sum()
        dislikes = game_feedback[game_feedback["feedback_type"] == "dislike"]["count"].sum()
        feedback_score = likes - dislikes
        recommendations.at[i, "adjusted_score"] += feedback_score * 0.1  # Peso de feedback ajustable

    # Ordenar por puntaje ajustado
    recommendations = recommendations.sort_values(by="adjusted_score", ascending=False)

    # Asegurarse de devolver exactamente 10 recomendaciones
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

# Input para buscar un juego
user_input = st.text_input("Enter a game name to get recommendations:")

# Inicializar lista de exclusión en la sesión
if "excluded_games" not in st.session_state:
    st.session_state["excluded_games"] = []

# Inicializar índice de recomendaciones por búsqueda
if "current_index" not in st.session_state:
    st.session_state["current_index"] = 0

if "last_search" not in st.session_state:
    st.session_state["last_search"] = ""

# Resetear el estado si la búsqueda cambia
if user_input != st.session_state["last_search"]:
    st.session_state["current_index"] = 0
    st.session_state["excluded_games"] = []
    st.session_state["last_search"] = user_input

# Mostrar sugerencias mientras el usuario escribe
if user_input:
    matching_games = data[data["name"].str.contains(user_input, case=False, na=False)]
    matching_game_names = matching_games["name"].tolist()

    if matching_game_names:
        selected_game = st.selectbox("Did you mean:", matching_game_names, key="game_selector")
        user_input = selected_game if selected_game else user_input

    recommendations = get_recommendations(user_input, tfidf_matrix, data)

    # Filtrar juegos en la lista de exclusión
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
        st.write("No games found. Try a different search.")
