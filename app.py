import streamlit as st
import pandas as pd

st.set_page_config(page_title="STAT APP", layout="wide")

st.title("STAT APP - Test Senza Upload")

# Carica un file fisso locale
FILE_NAME = "data.xlsx"

try:
    df = pd.read_excel(FILE_NAME)
    st.success(f"File '{FILE_NAME}' caricato correttamente.")
    st.dataframe(df)
except Exception as e:
    st.error(f"Errore nel leggere il file '{FILE_NAME}': {e}")
