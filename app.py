import streamlit as st
import pandas as pd

st.set_page_config(page_title="STAT APP", layout="wide")

st.title("STAT APP - Test Funzionante")

uploaded = st.file_uploader("Carica un file Excel", type=["xlsx"])

if uploaded:
    try:
        df = pd.read_excel(uploaded)
        st.write("File caricato correttamente:")
        st.dataframe(df)
    except Exception as e:
        st.error(f"Errore nel leggere il file: {e}")
