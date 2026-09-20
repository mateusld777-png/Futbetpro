import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="FUTBET PRO", page_icon="⚽", layout="wide")

# SENHA (mantém a mesma)
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if not st.session_state.autenticado:
    st.title("⚽ FUTBET PRO")
    senha = st.text_input("Digite a senha:", type="password")
    if st.button("🔐 ENTRAR", use_container_width=True):
        if senha == st.secrets.get("APP_PASSWORD", ""):
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

st.title("⚽ FUTBET PRO")
st.caption("Análise estatística - modo offline (sem API)")

# JOGOS DE HOJE - tu edita aqui manualmente, sem precisar de API
jogos_hoje = [
    {"horario": "15:00", "liga": "🇧🇷 Brasileirão", "home": "Flamengo", "away": "Palmeiras", "mercado": "Over 1.5", "prob": 72.5, "odd": 1.35, "conf": 85},
    {"horario": "15:45", "liga": "🏴 Premier League", "home": "Man City", "away": "Arsenal", "mercado": "1X", "prob": 68.3, "odd": 1.42, "conf": 82},
    {"horario": "16:00", "liga": "🇪🇸 La Liga", "home": "Real Madrid", "away": "Barcelona", "mercado": "BTTS", "prob": 65.1, "odd": 1.75, "conf": 78},
]

df = pd.DataFrame(jogos_hoje)
st.subheader(f"⚽ Jogos hoje: {len(jogos_hoje)}")
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("🎯 Múltiplas")
c1,c2,c3 = st.columns(3)
odd2 = jogos_hoje[0]["odd"] * jogos_hoje[1]["odd"]
odd3 = odd2 * jogos_hoje[2]["odd"]
c1.metric("Múltipla 2", f"{odd2:.2f}x")
c2.metric("Múltipla 3", f"{odd3:.2f}x")
c3.metric("Múltipla 4", "Em breve")
