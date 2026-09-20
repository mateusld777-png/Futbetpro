import math
import time
from datetime import datetime
from itertools import combinations
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


# =========================================================
# CONFIGURAÇÃO
# =========================================================

st.set_page_config(
    page_title="FUTBET PRO",
    page_icon="⚽",
    layout="wide"
)

API_URL = "https://v3.football.api-sports.io"

# Free da API tem limite de requisições por minuto.
# Mantemos intervalo seguro entre chamadas.
RATE_LIMIT_INTERVAL = 6.2

# Para o plano gratuito:
# 1 chamada para jogos + até 4 previsões + até 4 odds = 9 chamadas
MAX_JOGOS_ANALISE = 4


LEAGUES = {
    71: "🇧🇷 Brasileirão",
    39: "🏴 Premier League",
    140: "🇪🇸 La Liga",
    135: "🇮🇹 Serie A",
    78: "🇩🇪 Bundesliga",
    61: "🇫🇷 Ligue 1",
    94: "🇵🇹 Liga Portugal",
    88: "🇳🇱 Eredivisie",
    2: "🏆 Champions League",
    3: "🏆 Europa League",
}


# =========================================================
# SENHA
# =========================================================

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False


if not st.session_state.autenticado:

    st.title("⚽ FUTBET PRO")

    senha = st.text_input(
        "Digite a senha para entrar:",
        type="password"
    )

    if st.button("🔐 ENTRAR", use_container_width=True):

        senha_correta = st.secrets.get("APP_PASSWORD", "")

        if senha_correta and senha == senha_correta:
            st.session_state.autenticado = True
            st.rerun()

        else:
            st.error("Senha incorreta.")

    st.stop()


# =========================================================
# API
# =========================================================

API_KEY = st.secrets.get("APIFOOTBALL_KEY", "")


if not API_KEY:
    st.error("A chave APIFOOTBALL_KEY não foi encontrada nos Secrets.")
    st.stop()


# =========================================================
# CONTROLE DE VELOCIDADE
# =========================================================

def controlar_velocidade():

    agora = time.time()

    ultimo = st.session_state.get("ultima_chamada_api", 0)

    espera = RATE_LIMIT_INTERVAL - (agora - ultimo)

    if espera > 0:
        time.sleep(espera)

    st.session_state.ultima_chamada_api = time.time()


def api_get(endpoint, params=None):

    controlar_velocidade()

    headers = {
        "x-apisports-key": API_KEY
    }

    try:

        resposta = requests.get(
            f"{API_URL}/{endpoint}",
            headers=headers,
            params=params or {},
            timeout=20
        )

    except Exception:
        return None, "Falha de conexão com a API."


    if resposta.status_code == 429:

        retry = resposta.headers.get("Retry-After")

        try:
            retry = int(retry)
        except:
            retry = 10

        time.sleep(min(retry, 30))

        controlar_velocidade()

        try:

            resposta = requests.get(
                f"{API_URL}/{endpoint}",
                headers=headers,
                params=params or {},
                timeout=20
            )

        except Exception:
            return None, "Falha ao tentar novamente."


    try:
        dados = resposta.json()
    except:
        return None, "Resposta inválida da API."


    if resposta.status_code >= 400:
        return None, dados.get("errors", "Erro da API.")


    if dados.get("errors"):
        return None, dados.get("errors")


    return dados, None


# =========================================================
# JOGOS DO DIA
# =========================================================

@st.cache_data(ttl=900)
def buscar_jogos(data):

    dados, erro = api_get(
        "fixtures",
        {
            "date": data
        }
    )

    if erro or not dados:
        return [], erro


    jogos = []

    for item in dados.get("response", []):

        league_id = item.get("league", {}).get("id")

        if league_id not in LEAGUES:
            continue


        status = item.get("fixture", {}).get("status", {}).get("short", "")

        if status not in ["NS", "TBD"]:
            continue


        fixture = item.get("fixture", {})

        home = item.get("teams", {}).get("home", {})
        away = item.get("teams", {}).get("away", {})
        league = item.get("league", {})


        jogos.append({

            "fixture_id": fixture.get("id"),

            "data": data,

            "horario": fixture.get("date", ""),

            "home": home.get("name", "Mandante"),

            "away": away.get("name", "Visitante"),

            "home_id": home.get("id"),

            "away_id": away.get("id"),

            "league_id": league_id,

            "league": LEAGUES.get(
                league_id,
                league.get("name", "")
            ),

        })


    jogos.sort(
        key=lambda x: x.get("horario", "")
    )

    return jogos, None


# =========================================================
# PREVISÃO
# =========================================================

@st.cache_data(ttl=1800)
def buscar_previsao(fixture_id):

    dados, erro = api_get(
        "predictions",
        {
            "fixture": fixture_id
        }
    )

    if erro or not dados:
        return None, erro


    resposta = dados.get("response", [])

    if not resposta:
        return None, "Previsão não encontrada."


    return resposta[0], None


# =========================================================
# ODDS
# =========================================================

@st.cache_data(ttl=900)
def buscar_odds(fixture_id):

    dados, erro = api_get(
        "odds",
        {
            "fixture": fixture_id
        }
    )

    if erro or not dados:
        return None, erro


    return dados.get("response", []), None


# =========================================================
# UTILITÁRIOS
# =========================================================

def normalizar_texto(valor):

    if valor is None:
        return ""

    return " ".join(
        str(valor)
        .lower()
        .replace("_", " ")
        .split()
    )


def numero(valor):

    if valor is None:
        return None

    try:

        texto = str(valor)

        texto = (
            texto
            .replace("%", "")
            .replace(",", ".")
            .strip()
        )

        return float(texto)

    except:
        return None


def percentual(valor):

    n = numero(valor)

    if n is None:
        return None

    if n > 1:
        return n / 100

    return n


def odd_valida(valor):

    n = numero(valor)

    if n is None:
        return None

    if n <= 1:
        return None

    return n


# =========================================================
# FORM / ÚLTIMOS 5
# =========================================================

def extrair_last5(team_data):

    if not team_data:
        return {
            "form": "",
            "gf_avg": None,
            "ga_avg": None,
            "gf_total": None,
            "ga_total": None,
        }


    last5 = team_data.get("last_5", {})

    goals = last5.get("goals", {})

    gf = goals.get("for", {})
    ga = goals.get("against", {})


    return {

        "form": last5.get("form", ""),

        "gf_avg": numero(
            gf.get("average")
        ),

        "ga_avg": numero(
            ga.get("average")
        ),

        "gf_total": numero(
            gf.get("total")
        ),

        "ga_total": numero(
            ga.get("total")
        ),

    }


def contar_forma(form):

    form = str(form or "").upper()

    return {

        "V": form.count("W"),
        "E": form.count("D"),
        "D": form.count("L"),

    }


# =========================================================
# POISSON
# =========================================================

def poisson(k, media):

    try:

        if media < 0:
            return 0

        return (
            math.exp(-media)
            * media ** k
            / math.factorial(k)
        )

    except:

        return 0


def calcular_probabilidades(
    lambda_home,
    lambda_away
):

    max_gols = 8

    tabela = {}

    for gols_home in range(max_gols + 1):

        for gols_away in range(max_gols + 1):

            p = (
                poisson(
                    gols_home,
                    lambda_home
                )
                *
                poisson(
                    gols_away,
                    lambda_away
                )
            )

            tabela[
                (gols_home, gols_away)
            ] = p


    home = 0
    draw = 0
    away = 0

    over15 = 0

    home_1plus = 0
    away_1plus = 0

    btts = 0


    for (gh, ga), p in tabela.items():

        if gh > ga:
            home += p

        elif gh == ga:
            draw += p

        else:
            away += p


        if gh + ga >= 2:
            over15 += p


        if gh >= 1:
            home_1plus += p


        if ga >= 1:
            away_1plus += p


        if gh >= 1 and ga >= 1:
            btts += p


    return {

        "home": home,
        "draw": draw,
        "away": away,

        "1x": home + draw,
        "x2": draw + away,
        "12": home + away,

        "over15": over15,

        "home_1plus": home_1plus,

        "away_1plus": away_1plus,

        "btts": btts,

    }


# =========================================================
# MODELO
# =========================================================

def construir_modelo(previsao):

    teams = previsao.get("teams", {})

    home_data = teams.get("home", {})
    away_data = teams.get("away", {})


    home5 = extrair_last5(home_data)
    away5 = extrair_last5(away_data)


    # Médias dos últimos 5.
    # Quando disponíveis, combinamos ataque próprio
    # com defesa adversária.

    home_for = home5["gf_avg"]
    home_against = home5["ga_avg"]

    away_for = away5["gf_avg"]
    away_against = away5["ga_avg"]


    if home_for is None:
        home_for = 1.35

    if home_against is None:
        home_against = 1.20

    if away_for is None:
        away_for = 1.15

    if away_against is None:
        away_against = 1.35


    lambda_home = (
        home_for * 0.60
        +
        away_against * 0.40
    )


    lambda_away = (
        away_for * 0.60
        +
        home_against * 0.40
    )


    # Pequena vantagem de mando.

    lambda_home *= 1.05


    poisson_probs = calcular_probabilidades(
        lambda_home,
        lambda_away
    )


    prediction = previsao.get(
        "predictions",
        {}
    )


    api_percent = prediction.get(
        "percent",
        {}
    )


    api_probs = {

        "home": percentual(
            api_percent.get("home")
        ),

        "draw": percentual(
            api_percent.get("draw")
        ),

        "away": percentual(
            api_percent.get("away")
        ),

    }


    # Se a API forneceu percentuais,
    # combinamos API + Poisson.

    if all(
        api_probs[x] is not None
        for x in ["home", "draw", "away"]
    ):

        probs = {

            "home":
                poisson_probs["home"] * 0.45
                +
                api_probs["home"] * 0.55,

            "draw":
                poisson_probs["draw"] * 0.45
                +
                api_probs["draw"] * 0.55,

            "away":
                poisson_probs["away"] * 0.45
                +
                api_probs["away"] * 0.55,

        }


        total = sum(probs.values())

        if total > 0:

            probs["home"] /= total
            probs["draw"] /= total
            probs["away"] /= total


        probs["1x"] = (
            probs["home"]
            +
            probs["draw"]
        )

        probs["x2"] = (
            probs["draw"]
            +
            probs["away"]
        )

        probs["12"] = (
            probs["home"]
            +
            probs["away"]
        )


        # Mercados de gols continuam vindo
        # do modelo Poisson.

        probs["over15"] = poisson_probs["over15"]
        probs["home_1plus"] = poisson_probs["home_1plus"]
        probs["away_1plus"] = poisson_probs["away_1plus"]
        probs["btts"] = poisson_probs["btts"]

    else:

        probs = poisson_probs


    return {

        "probs": probs,

        "lambda_home": lambda_home,

        "lambda_away": lambda_away,

        "home5": home5,

        "away5": away5,

        "advice": prediction.get(
            "advice",
            ""
        ),

        "under_over": prediction.get(
            "under_over",
            ""
        ),

    }


# =========================================================
# EXTRAÇÃO CORRETA DAS ODDS
# =========================================================

def extrair_odds(odds_response):

    if not odds_response:

        return {
            "bookmaker": None,
            "home": None,
            "draw": None,
            "away": None,
            "1x": None,
            "x2": None,
            "12": None,
            "over15": None,
            "home_1plus": None,
            "away_1plus": None,
            "btts_yes": None,
        }


    candidatos = []


    for bookmaker_data in odds_response:

        bookmaker = bookmaker_data.get(
            "bookmaker",
            {}
        )

        bookmaker_name = bookmaker.get(
            "name",
            "Bookmaker"
        )


        mercados = {

            "home": None,
            "draw": None,
            "away": None,

            "1x": None,
            "x2": None,
            "12": None,

            "over15": None,

            "home_1plus": None,
            "away_1plus": None,

            "btts_yes": None,

        }


        bets = bookmaker.get(
            "bets",
            []
        )


        for bet in bets:

            nome = normalizar_texto(
                bet.get("name")
            )


            # =================================================
            # VENCEDOR DA PARTIDA
            # =================================================

            if nome in {
                "match winner",
                "1x2"
            }:

                for value in bet.get(
                    "values",
                    []
                ):

                    valor = normalizar_texto(
                        value.get("value")
                    )

                    odd = odd_valida(
                        value.get("odd")
                    )


                    if valor == "home":
                        mercados["home"] = odd

                    elif valor == "draw":
                        mercados["draw"] = odd

                    elif valor == "away":
                        mercados["away"] = odd


            # =================================================
            # DUPLA CHANCE
            # =================================================

            elif nome == "double chance":

                for value in bet.get(
                    "values",
                    []
                ):

                    valor = normalizar_texto(
                        value.get("value")
                    )

                    odd = odd_valida(
                        value.get("odd")
                    )


                    if valor in {
                        "home/draw",
                        "home or draw"
                    }:

                        mercados["1x"] = odd


                    elif valor in {
                        "draw/away",
                        "draw or away"
                    }:

                        mercados["x2"] = odd


                    elif valor in {
                        "home/away",
                        "home or away"
                    }:

                        mercados["12"] = odd


            # =================================================
            # OVER / UNDER
            # =================================================

            elif nome in {
                "goals over/under",
                "goals over under"
            }:

                for value in bet.get(
                    "values",
                    []
                ):

                    valor = normalizar_texto(
                        value.get("value")
                    )

                    odd = odd_valida(
                        value.get("odd")
                    )


                    if valor == "over 1.5":

                        mercados["over15"] = odd


            # =================================================
            # TOTAL DO MANDANTE
            # =================================================

            elif nome in {
                "total - home",
                "total home"
            }:

                for value in bet.get(
                    "values",
                    []
                ):

                    valor = normalizar_texto(
                        value.get("value")
                    )

                    odd = odd_valida(
                        value.get("odd")
                    )


                    if valor == "over 0.5":

                        mercados["home_1plus"] = odd


            # =================================================
            # TOTAL DO VISITANTE
            # =================================================

            elif nome in {
                "total - away",
                "total away"
            }:

                for value in bet.get(
                    "values",
                    []
                ):

                    valor = normalizar_texto(
                        value.get("value")
                    )

                    odd = odd_valida(
                        value.get("odd")
                    )


                    if valor == "over 0.5":

                        mercados["away_1plus"] = odd


            # =================================================
            # AMBAS MARCAM
            # =================================================

            elif nome in {
                "both teams score",
                "both teams to score"
            }:

                for value in bet.get(
                    "values",
                    []
                ):

                    valor = normalizar_texto(
                        value.get("value")
                    )

                    odd = odd_valida(
                        value.get("odd")
                    )


                    if valor == "yes":

                        mercados["btts_yes"] = odd


        quantidade = sum(
            1
            for v in mercados.values()
            if v is not None
        )


        candidatos.append(
            (
                quantidade,
                bookmaker_name,
                mercados
            )
        )


    if not candidatos:

        return {
            "bookmaker": None,
            "home": None,
            "draw": None,
            "away": None,
            "1x": None,
            "x2": None,
            "12": None,
            "over15": None,
            "home_1plus": None,
            "away_1plus": None,
            "btts_yes": None,
        }


    # Escolhe o bookmaker que trouxe mais mercados
    # relevantes, evitando pegar uma casa que só tenha
    # um mercado incompleto.

    candidatos.sort(
        key=lambda x: x[0],
        reverse=True
    )


    quantidade, bookmaker_name, mercados = candidatos[0]

    mercados["bookmaker"] = bookmaker_name

    return mercados


# =========================================================
# ESCOLHER MERCADO
# =========================================================

def escolher_mercado(modelo, odds):

    probs = modelo["probs"]


    candidatos = [

        (
            "Dupla chance 1X",
            probs["1x"],
            odds.get("1x")
        ),

        (
            "Dupla chance X2",
            probs["x2"],
            odds.get("x2")
        ),

        (
            "Mais de 1.5 gols",
            probs["over15"],
            odds.get("over15")
        ),

        (
            "Mandante marcar 1+",
            probs["home_1plus"],
            odds.get("home_1plus")
        ),

        (
            "Visitante marcar 1+",
            probs["away_1plus"],
            odds.get("away_1plus")
        ),

        (
            "Vitória mandante",
            probs["home"],
            odds.get("home")
        ),

        (
            "Empate",
            probs["draw"],
            odds.get("draw")
        ),

        (
            "Vitória visitante",
            probs["away"],
            odds.get("away")
        ),

        (
            "Ambas marcam",
            probs["btts"],
            odds.get("btts_yes")
        ),

    ]


    disponiveis = []

    for nome, prob, odd in candidatos:

        if (
            prob is not None
            and odd is not None
            and odd > 1
        ):

            disponiveis.append(
                {
                    "mercado": nome,
                    "probabilidade": prob,
                    "odd": odd,
                    "valor": prob * odd
                }
            )


    if not disponiveis:

        return None


    # Priorizamos probabilidade.
    # O valor da odd é usado como critério secundário.

    disponiveis.sort(
        key=lambda x: (
            x["probabilidade"],
            x["valor"]
        ),
        reverse=True
    )


    escolhido = disponiveis[0]


    # Confiança é uma escala interna do sistema,
    # não uma garantia de resultado.

    escolhido["confianca"] = (
        escolhido["probabilidade"] * 100
    )


    return escolhido


# =========================================================
# ANÁLISE DE UM JOGO
# =========================================================

def analisar_jogo(jogo):

    fixture_id = jogo["fixture_id"]


    previsao, erro_previsao = buscar_previsao(
        fixture_id
    )


    if erro_previsao or not previsao:

        return {
            "erro": "Não foi possível obter a previsão.",
            "jogo": jogo
        }


    modelo = construir_modelo(
        previsao
    )


    odds_response, erro_odds = buscar_odds(
        fixture_id
    )


    if erro_odds:

        odds = extrair_odds([])

    else:

        odds = extrair_odds(
            odds_response
        )


    mercado = escolher_mercado(
        modelo,
        odds
    )


    return {

        "jogo": jogo,

        "modelo": modelo,

        "odds": odds,

        "mercado": mercado,

        "erro": None,

    }


# =========================================================
# OPÇÕES PARA MÚLTIPLAS
# =========================================================

def opcoes_jogo(resultado):

    if resultado.get("erro"):
        return []


    modelo = resultado["modelo"]
    odds = resultado["odds"]


    probs = modelo["probs"]


    opcoes = [

        (
            "1X",
            probs["1x"],
            odds.get("1x")
        ),

        (
            "X2",
            probs["x2"],
            odds.get("x2")
        ),

        (
            "+1.5 gols",
            probs["over15"],
            odds.get("over15")
        ),

        (
            "Mandante 1+ gol",
            probs["home_1plus"],
            odds.get("home_1plus")
        ),

        (
            "Visitante 1+ gol",
            probs["away_1plus"],
            odds.get("away_1plus")
        ),

        (
            "Mandante vence",
            probs["home"],
            odds.get("home")
        ),

        (
            "Visitante vence",
            probs["away"],
            odds.get("away")
        ),

        (
            "BTTS",
            probs["btts"],
            odds.get("btts_yes")
        ),

    ]


    resultado_final = []


    for nome, prob, odd in opcoes:

        if (
            prob is not None
            and odd is not None
            and odd > 1
        ):

            resultado_final.append(
                {
                    "nome": nome,
                    "prob": prob,
                    "odd": odd
                }
            )


    resultado_final.sort(
        key=lambda x: x["prob"],
        reverse=True
    )


    return resultado_final


# =========================================================
# INTERFACE
# =========================================================

st.title("⚽ FUTBET PRO")

st.caption(
    "Análise estatística de partidas, mercados e odds."
)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("⚙️ Configurações")


data_escolhida = st.sidebar.date_input(
    "📅 Data dos jogos",
    value=datetime.now(
        ZoneInfo("America/Fortaleza")
    ).date()
)


ligas_escolhidas = st.sidebar.multiselect(
    "🏆 Competições",
    options=list(LEAGUES.keys()),
    default=[
        39,
        71,
        140,
        135
    ],
    format_func=lambda x: LEAGUES[x]
)


st.sidebar.info(
    f"""
Plano gratuito da API:

• Máximo de {MAX_JOGOS_ANALISE} jogos por análise
• O sistema evita chamadas muito rápidas
• Os resultados ficam em cache
• A chave da API permanece protegida nos Secrets
"""
)


# =========================================================
# BUSCAR JOGOS
# =========================================================

data_string = data_escolhida.strftime(
    "%Y-%m-%d"
)


if not ligas_escolhidas:

    st.warning(
        "Selecione pelo menos uma competição."
    )

    st.stop()


with st.spinner("🔎 Procurando jogos..."):

    jogos, erro = buscar_jogos(
        data_string
    )


if erro:

    st.error(
        f"Erro ao buscar jogos: {erro}"
    )

    st.stop()


jogos = [
    j for j in jogos
    if j["league_id"] in ligas_escolhidas
]


if not jogos:

    st.info(
        "Nenhum jogo encontrado para as competições selecionadas."
    )

    st.stop()


# =========================================================
# LISTA DE JOGOS
# =========================================================

st.subheader(
    f"⚽ Jogos encontrados: {len(jogos)}"
)


for jogo in jogos:

    try:

        horario = datetime.fromisoformat(
            jogo["horario"].replace(
                "Z",
                "+00:00"
            )
        ).astimezone(
            ZoneInfo("America/Fortaleza")
        ).strftime("%H:%M")

    except:

        horario = "--:--"


    st.write(
        f"**{horario} — "
        f"{jogo['home']} x {jogo['away']}** "
        f"• {jogo['league']}"
    )


st.divider()


# =========================================================
# ANALISAR
# =========================================================

if len(jogos) > MAX_JOGOS_ANALISE:

    st.warning(
        f"""
        Existem {len(jogos)} jogos, mas o plano gratuito está
        configurado para analisar no máximo {MAX_JOGOS_ANALISE}
        por vez para preservar sua cota da API.
        """
    )


jogos_para_analisar = jogos[
    :MAX_JOGOS_ANALISE
]


if st.button(
    "🧠 ANALISAR JOGOS",
    use_container_width=True
):

    resultados = []


    barra = st.progress(0)


    for i, jogo in enumerate(
        jogos_para_analisar
    ):

        resultado = analisar_jogo(
            jogo
        )

        resultados.append(
            resultado
        )


        barra.progress(
            (i + 1)
            /
            len(jogos_para_analisar)
        )


    st.session_state.resultados = resultados

    st.success(
        "✅ Análise concluída."
    )


# =========================================================
# RESULTADOS
# =========================================================

if "resultados" not in st.session_state:

    st.info(
        "Clique em **ANALISAR JOGOS** para começar."
    )

    st.stop()


resultados = st.session_state.resultados


validos = [
    r for r in resultados
    if not r.get("erro")
    and r.get("mercado")
]


# =========================================================
# RANKING
# =========================================================

st.subheader("🏆 Ranking dos mercados")


if not validos:

    st.warning(
        "Não foi possível encontrar mercados com odds disponíveis."
    )

else:

    ranking = []


    for r in validos:

        jogo = r["jogo"]
        mercado = r["mercado"]
        odds = r["odds"]


        ranking.append({

            "Jogo":
                f"{jogo['home']} x {jogo['away']}",

            "Mercado":
                mercado["mercado"],

            "Probabilidade":
                f"{mercado['probabilidade'] * 100:.1f}%",

            "Odd":
                f"{mercado['odd']:.2f}",

            "Confiança":
                f"{mercado['confianca']:.1f}%",

            "Bookmaker":
                odds.get(
                    "bookmaker"
                ) or "Não informado",

        })


    df = pd.DataFrame(
        ranking
    )


    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# DETALHES
# =========================================================

st.subheader("🔍 Detalhes")


for r in resultados:

    jogo = r["jogo"]


    with st.expander(
        f"{jogo['home']} x {jogo['away']} — {jogo['league']}"
    ):

        if r.get("erro"):

            st.warning(
                r["erro"]
            )

            continue


        modelo = r["modelo"]
        odds = r["odds"]
        mercado = r["mercado"]


        col1, col2, col3 = st.columns(3)


        with col1:

            st.write("### 🏠 Mandante")

            st.write(
                f"Forma: "
                f"`{modelo['home5']['form'] or '--'}`"
            )

            st.write(
                f"Gols marcados/último jogo médio: "
                f"{modelo['home5']['gf_avg'] or 0:.2f}"
            )

            st.write(
                f"Gols sofridos/último jogo médio: "
                f"{modelo['home5']['ga_avg'] or 0:.2f}"
            )


        with col2:

            st.write("### ✈️ Visitante")

            st.write(
                f"Forma: "
                f"`{modelo['away5']['form'] or '--'}`"
            )

            st.write(
                f"Gols marcados/último jogo médio: "
                f"{modelo['away5']['gf_avg'] or 0:.2f}"
            )

            st.write(
                f"Gols sofridos/último jogo médio: "
                f"{modelo['away5']['ga_avg'] or 0:.2f}"
            )


        with col3:

            st.write("### 🤖 Modelo")

            st.write(
                f"Mandante: "
                f"{modelo['probs']['home'] * 100:.1f}%"
            )

            st.write(
                f"Empate: "
                f"{modelo['probs']['draw'] * 100:.1f}%"
            )

            st.write(
                f"Visitante: "
                f"{modelo['probs']['away'] * 100:.1f}%"
            )


        st.divider()


        st.write("### 📊 Mercados")


        mercados_detalhes = [

            (
                "1X",
                modelo["probs"]["1x"],
                odds.get("1x")
            ),

            (
                "X2",
                modelo["probs"]["x2"],
                odds.get("x2")
            ),

            (
                "+1.5 gols",
                modelo["probs"]["over15"],
                odds.get("over15")
            ),

            (
                "Mandante 1+ gol",
                modelo["probs"]["home_1plus"],
                odds.get("home_1plus")
            ),

            (
                "Visitante 1+ gol",
                modelo["probs"]["away_1plus"],
                odds.get("away_1plus")
            ),

            (
                "BTTS",
                modelo["probs"]["btts"],
                odds.get("btts_yes")
            ),

            (
                "Mandante vence",
                modelo["probs"]["home"],
                odds.get("home")
            ),

            (
                "Visitante vence",
                modelo["probs"]["away"],
                odds.get("away")
            ),

        ]


        tabela_mercados = []


        for nome, prob, odd in mercados_detalhes:

            tabela_mercados.append({

                "Mercado":
                    nome,

                "Probabilidade":
                    f"{prob * 100:.1f}%",

                "Odd":
                    f"{odd:.2f}"
                    if odd is not None
                    else "—",

            })


        st.dataframe(
            pd.DataFrame(
                tabela_mercados
            ),
            use_container_width=True,
            hide_index=True
        )


        if odds.get("bookmaker"):

            st.caption(
                f"📌 Odds obtidas da casa: "
                f"**{odds['bookmaker']}**"
            )


        if mercado:

            st.success(
                f"""
                🎯 **Mercado selecionado:**
                {mercado['mercado']}

                📈 Probabilidade estimada:
                {mercado['probabilidade'] * 100:.1f}%

                💰 Odd:
                {mercado['odd']:.2f}
                """
            )


# =========================================================
# MÚLTIPLAS
# =========================================================

st.divider()

st.subheader("🎯 Múltiplas")


opcoes_por_jogo = []


for r in validos:

    opcoes = opcoes_jogo(r)

    if opcoes:

        opcoes_por_jogo.append(
            (
                r,
                opcoes
            )
        )


def montar_multipla(
    quantidade
):

    if len(opcoes_por_jogo) < quantidade:

        return None


    melhores = []


    for r, opcoes in opcoes_por_jogo:

        if not opcoes:
            continue


        # Mercado de maior probabilidade disponível
        melhores.append(
            (
                r,
                opcoes[0]
            )
        )


    if len(melhores) < quantidade:

        return None


    # Pega os jogos com maior probabilidade
    melhores.sort(
        key=lambda x: x[1]["prob"],
        reverse=True
    )


    selecionados = melhores[
        :quantidade
    ]


    odd_total = 1

    prob_total = 1


    linhas = []


    for r, opcao in selecionados:

        odd_total *= opcao["odd"]

        prob_total *= opcao["prob"]


        linhas.append({

            "Jogo":
                f"{r['jogo']['home']} x "
                f"{r['jogo']['away']}",

            "Mercado":
                opcao["nome"],

            "Odd":
                opcao["odd"],

            "Probabilidade":
                opcao["prob"],

        })


    return {

        "odd_total": odd_total,

        "prob_total": prob_total,

        "linhas": linhas,

    }


col1, col2, col3 = st.columns(3)


for coluna, quantidade, titulo in [
    (col1, 2, "🔥 Múltipla 2"),
    (col2, 3, "🔥 Múltipla 3"),
    (col3, 4, "🔥 Múltipla 4"),
]:

    with coluna:

        st.write(f"### {titulo}")


        multipla = montar_multipla(
            quantidade
        )


        if multipla is None:

            st.info(
                "Não há jogos suficientes."
            )

        else:

            st.metric(
                "Odd total",
                f"{multipla['odd_total']:.2f}"
            )


            st.write(
                "Probabilidade matemática "
                "aproximada do conjunto:",
                f"{multipla['prob_total'] * 100:.2f}%"
            )


            for linha in multipla["linhas"]:

                st.write(
                    f"• **{linha['Jogo']}** — "
                    f"{linha['Mercado']} "
                    f"@ {linha['Odd']:.2f}"
                )


# =========================================================
# RODAPÉ
# =========================================================

st.divider()

st.caption(
    "⚠️ As probabilidades são estimativas estatísticas, "
    "não garantias de resultado. Odds podem mudar antes "
    "do início da partida."
)
