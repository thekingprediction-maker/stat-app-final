import streamlit as st
import pandas as pd

st.set_page_config(page_title="STAT APP - OFFICIAL", layout="wide")
st.title("STAT APP - Dataset Viewer")

FILES = {
    "Tiri Serie A": "tiri_serie_a.xlsx",
    "Falli Serie A": "falli_serie_a.xlsx",
    "Falli Liga": "falli_liga.xlsx"
}

scelta = st.selectbox("Seleziona il dataset:", list(FILES.keys()))

file_path = FILES[scelta]

st.write(f"Caricamento del file: **{file_path}**")

try:
    df = pd.read_excel(file_path)
    st.success("File caricato correttamente!")
    st.dataframe(df)
except Exception as e:
    st.error(f"Errore nel leggere il file '{file_path}': {e}")
