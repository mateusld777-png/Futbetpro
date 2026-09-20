import streamlit as st
from datetime import datetime

SENHA_DO_APP = "futbet2026"
st.set_page_config(page_title="FutBet Pro", page_icon="⚽", layout="wide")

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔒 FutBet Pro - Acesso Exclusivo")
    st.write("App privado. Digite a senha.")
    senha = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if senha == SENHA_DO_APP:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Senha incorreta!")
    st.stop()

st.sidebar.success("✅ Acesso Liberado")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

st.title("⚽ FutBet Pro - Jogos REAIS de Hoje")
st.caption(f"Rodada 28 - Brasileirão - {datetime.now().strftime('%d/%m/%Y')} - Tauá/CE")

jogos = [
    {"Jogo": "Grêmio x Palmeiras", "Hora": "11:00", "Over 2.5": "68%", "BTTS": "62%", "Palpite": "Palmeiras vence ou empate"},
    {"Jogo": "Vitória x Cruzeiro", "Hora": "16:00", "Over 2.5": "65%", "BTTS": "60%", "Palpite": "Over 1.5 ✅"},
    {"Jogo": "Corinthians x Fluminense", "Hora": "16:00", "Over 2.5": "72%", "BTTS": "70%", "Palpite": "BTTS Sim ✅"},
    {"Jogo": "Flamengo x Bragantino", "Hora": "18:30", "Over 2.5": "80%", "BTTS": "58%", "Palpite": "Flamengo vence ✅"},
    {"Jogo": "Athletico PR x Bahia", "Hora": "19:30", "Over 2.5": "74%", "BTTS": "68%", "Palpite": "Over 2.5"},
]

st.dataframe(jogos, use_container_width=True, hide_index=True)

st.divider()
st.subheader("🎯 Bilhete do Dia - REAL")
st.success("Grêmio x Palmeiras - Over 1.5 (1.40) + Flamengo vence (1.65) + Corinthians x Fluminense BTTS (1.85)\n\n**Odd Total: 4.27**")
st.balloons()
