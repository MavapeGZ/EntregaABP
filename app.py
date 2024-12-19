import streamlit as st
import pandas as pd


# Load the dataset
steamGamesFile = "./data/steam_data.csv"
steamGames = pd.read_csv(steamGamesFile)


# Display the title
st.title("Stinder - Steam Game Recommender")


# Display the dataset
st.write("Here is the dataset of Steam games:")
st.write(steamGames.head())


# User input for game recommendation
user_input = st.text_input("Enter a game you like:")


# Simple recommendation logic (for demonstration purposes)
if user_input:
    recommendations = steamGames[steamGames['name'].str.contains(user_input, case=False)]
    st.write("Recommended games:")
    st.write(recommendations)
