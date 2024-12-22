import streamlit as st
import pandas as pd
from datetime import datetime
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

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

# Función para obtener recomendaciones basadas en similitud
def get_recommendations(game_name, tfidf_matrix, data):
    idx = data[data["name"].str.contains(game_name, case=False, na=False)].index
    if len(idx) == 0:
        return pd.DataFrame()
    idx = idx[0]
    cosine_sim = linear_kernel(tfidf_matrix[idx], tfidf_matrix).flatten()
    similar_indices = cosine_sim.argsort()[-11:-1][::-1]
    return data.iloc[similar_indices]

# Archivo para guardar feedback
feedback_file = "feedback.csv"
if not os.path.exists(feedback_file):
    pd.DataFrame(columns=["user", "timestamp", "game_name", "feedback_type", "input_query"]).to_csv(feedback_file, index=False)

# Función para guardar feedback en CSV
def save_feedback(user, game_name, feedback_type, input_query):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    feedback_entry = pd.DataFrame([[user, timestamp, game_name, feedback_type, input_query]], 
                                   columns=["user", "timestamp", "game_name", "feedback_type", "input_query"])
    feedback_entry.to_csv(feedback_file, mode="a", header=False, index=False)

# Configurar la interfaz con colores personalizados
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
    </style>
    """,
    unsafe_allow_html=True
)

st.image("./public/logo.png", width=400)
st.title("Stinder")

# Input para buscar un juego
user_input = st.text_input("Enter a game name to get recommendations:")

# Mostrar sugerencias mientras el usuario escribe
if user_input:
    matching_games = data[data["name"].str.contains(user_input, case=False, na=False)]
    matching_game_names = matching_games["name"].tolist()

    if matching_game_names:
        selected_game = st.selectbox("Did you mean:", matching_game_names, key="game_selector")
        user_input = selected_game if selected_game else user_input

    recommendations = get_recommendations(user_input, tfidf_matrix, data)

    if not recommendations.empty:
        if "current_index" not in st.session_state:
            st.session_state["current_index"] = 0

        current_index = st.session_state["current_index"]
        if current_index < len(recommendations):
            game = recommendations.iloc[current_index]

            st.image(game["header_image"], use_container_width=True)
            st.subheader(game["name"])

            # Botones de interacción
            col1, col2 = st.columns(2)

            with col1:
                if st.button("❤", key=f"like-{current_index}", help="Like", use_container_width=True):
                    save_feedback("user", game["name"], "like", user_input)
                    st.session_state["current_index"] += 1

            with col2:
                if st.button("✖", key=f"dislike-{current_index}", help="Dislike", use_container_width=True):
                    save_feedback("user", game["name"], "dislike", user_input)
                    st.session_state["current_index"] += 1

        else:
            st.write("No more recommendations. Try a different search.")
    else:
        st.write("No games found. Try a different search.")
