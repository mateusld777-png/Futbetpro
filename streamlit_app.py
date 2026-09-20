
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="FutBet Pro", page_icon="⚽", layout="wide")

st.title("⚽ FutBet Pro - Análise Inteligente")
st.caption(f"Hoje: {datetime.now().strftime('%d/%m/%Y %H:%M')} - Tauá/CE")

jogos = [
    {"Jogo": "Flamengo x Palmeiras", "Hora": "16:00", "Over 2.5": "78%", "BTTS": "65%", "Palpite": "Over 2.5 ✅"},
    {"Jogo": "Real Madrid x Barcelona", "Hora": "16:30", "Over 2.5": "82%", "BTTS": "71%", "Palpite": "BTTS Sim ✅"},
    {"Jogo": "Man City x Arsenal", "Hora": "18:00", "Over 2.5": "75%", "BTTS": "68%", "Palpite": "Over 1.5 HT"},
    {"Jogo": "Fortaleza x Ceará", "Hora": "19:00", "Over 2.5": "60%", "BTTS": "58%", "Palpite": "Fortaleza vence"},
]

st.dataframe(jogos, use_container_width=True, hide_index=True)

st.divider()
st.subheader("🎯 Bilhete do Dia")
st.success("Flamengo Over 2.5 (1.85) + Real BTTS Sim (1.70) = Odd Total 3.14")

if st.button("Atualizar Análises"):
    st.balloons()
    st.toast("Atualizado!")
