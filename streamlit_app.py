import streamlit as st
import random
from datetime import date

st.set_page_config(page_title="FUTBET PRO", page_icon="⚽", layout="centered")

# --- SENHA ---
if "acesso" not in st.session_state:
    st.session_state.acesso = False

if not st.session_state.acesso:
    st.title("⚽ FUTBET PRO")
    st.write("3 Análises Diárias")
    senha = st.text_input("Digite a senha", type="password")
    if st.button("ENTRAR"):
        if senha == "futbet2026":
            st.session_state.acesso = True
            st.rerun()
        else:
            st.error("Senha errada!")
    st.stop()

# --- JOGOS ---
jogos_base = [
    {"casa": "Flamengo", "fora": "Palmeiras", "palpite": "Dupla Chance Flamengo", "odd": 1.45},
    {"casa": "Real Madrid", "fora": "Barcelona", "palpite": "Mais de 1.5 Gols", "odd": 1.35},
    {"casa": "Man City", "fora": "Arsenal", "palpite": "Man City marca", "odd": 1.40},
    {"casa": "Brasil", "fora": "Argentina", "palpite": "Ambas marcam - Nao", "odd": 1.80},
    {"casa": "PSG", "fora": "Bayern", "palpite": "+7.5 Escanteios", "odd": 1.70},
]

def gerar_bilhetes():
    b = random.sample(jogos_base, 4)

    bilhete1 = {
        "nome": "BILHETE SIMPLES",
        "desc": "Para dobrar a banca",
        "odd": "2.15",
        "cor": "#16a34a",
        "jogos": [b[0]]
    }
    bilhete2 = {
        "nome": "BILHETE ODD 10x",
        "desc": "Equilibrado",
        "odd": "10.80",
        "cor": "#2563eb",
        "jogos": [b[0], b[1], b[2]]
    }
    bilhete3 = {
        "nome": "BILHETE ODD 50x",
        "desc": "O da forra - R$1 vira R$50",
        "odd": "50.45",
        "cor": "#9333ea",
        "jogos": [b[0], b[1], b[2], b[3]]
    }
    return [bilhete1, bilhete2, bilhete3]

if "data" not in st.session_state or st.session_state.data!= str(date.today()):
    st.session_state.bilhetes = gerar_bilhetes()
    st.session_state.data = str(date.today())

st.title(f"FUTBET PRO - {date.today().strftime('%d/%m/%Y')}")

for bil in st.session_state.bilhetes:
    with st.container(border=True):
        st.markdown(f"<div style='background:{bil['cor']}; padding:10px; border-radius:8px; color:white;'><b>{bil['nome']}</b> - {bil['odd']}x <br><small>{bil['desc']}</small></div>", unsafe_allow_html=True)
        for j in bil["jogos"]:
            st.write(f"**{j['casa']} x {j['fora']}** - {j['palpite']} ({j['odd']}x)")

if st.button("Atualizar Bilhetes"):
    st.session_state.bilhetes = gerar_bilhetes()
    st.rerun()
