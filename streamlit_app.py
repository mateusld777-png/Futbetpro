import streamlit as st
import pandas as pd

st.set_page_config(page_title="FUTBET PRO", page_icon="⚽", layout="wide")

# --- SENHA ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if not st.session_state.autenticado:
    st.title("⚽ FUTBET PRO")
    senha = st.text_input("Senha:", type="password")
    if st.button("🔐 ENTRAR", use_container_width=True):
        if senha == st.secrets.get("APP_PASSWORD",""):
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    st.stop()

# --- BANCO DE JOGOS (fica na memória) ---
if "jogos" not in st.session_state:
    st.session_state.jogos = [
        {"horario": "16:00", "liga": "🇧🇷 Brasileirão", "home": "Vasco", "away": "Bahia", "mercado": "Over 1.5", "prob": 74.0, "odd": 1.32, "conf": 88},
        {"horario": "18:30", "liga": "🇧🇷 Brasileirão", "home": "Corinthians", "away": "Fluminense", "mercado": "1X", "prob": 69.0, "odd": 1.40, "conf": 80},
    ]

st.title("⚽ FUTBET PRO")
st.caption("Modo Profissional - sem API, sem suspensão")

# --- EDITOR LATERAL ---
st.sidebar.header("✏️ Editar Jogos")
with st.sidebar.form("add_jogo"):
    horario = st.text_input("Horário", "20:00")
    liga = st.selectbox("Liga", ["🇧🇷 Brasileirão", "🏴 Premier League", "🇪🇸 La Liga", "🇮🇹 Serie A", "🇩🇪 Bundesliga", "🏆 Champions"])
    home = st.text_input("Mandante", "Flamengo")
    away = st.text_input("Visitante", "Palmeiras")
    mercado = st.selectbox("Mercado", ["Over 1.5", "Over 2.5", "1X", "X2", "BTTS Sim", "Casa vence", "Fora vence"])
    odd = st.number_input("Odd", 1.10, 10.0, 1.40, 0.01)
    prob = st.number_input("Prob %", 0.0, 100.0, 70.0, 0.5)
    conf = st.number_input("Confiança %", 0.0, 100.0, 80.0, 1.0)
    if st.form_submit_button("➕ Adicionar Jogo", use_container_width=True):
        st.session_state.jogos.append({
            "horario": horario, "liga": liga, "home": home, "away": away,
            "mercado": mercado, "prob": prob, "odd": odd, "conf": conf
        })
        st.success("Adicionado!")

if st.sidebar.button("🗑️ Limpar Tudo"):
    st.session_state.jogos = []
    st.rerun()

# --- LISTA ---
st.subheader(f"⚽ Jogos hoje: {len(st.session_state.jogos)}")
if not st.session_state.jogos:
    st.info("Nenhum jogo. Adiciona ali na lateral 👈")
else:
    df = pd.DataFrame(st.session_state.jogos)
    df["Jogo"] = df["home"] + " x " + df["away"]
    st.dataframe(df[["horario","liga","Jogo","mercado","prob","odd","conf"]], use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🎯 Múltiplas")
    c1,c2,c3
