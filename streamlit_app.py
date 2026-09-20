import math
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

LEAGUES = {
    "Brasileirão": 71,
    "Premier League": 39,
    "La Liga": 140,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61,
    "Liga Portugal": 94,
    "Eredivisie": 88,
    "Champions League": 2,
    "Europa League": 3,
}


# =========================================================
# SENHA
# =========================================================

APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")

if not APP_PASSWORD:
    st.title("🔐 FUTBET PRO")
    st.warning("O aplicativo ainda não foi configurado.")
    st.info(
        "No Streamlit, abra os Secrets e adicione:\n\n"
        'APP_PASSWORD = "SUA_SENHA"'
    )
    st.stop()


if "autenticado" not in st.session_state:
    st.session_state.autenticado = False


if not st.session_state.autenticado:

    st.markdown(
        """
        <div style="
            text-align:center;
            padding:40px 10px;
        ">
            <h1>⚽ FUTBET PRO</h1>
            <p>🔐 Área privada</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    senha = st.text_input(
        "Digite sua senha",
        type="password",
        placeholder="Sua senha"
    )

    if st.button("🔓 ENTRAR", use_container_width=True):

        if senha == APP_PASSWORD:
            st.session_state.autenticado = True
            st.rerun()

        else:
            st.error("❌ Senha incorreta.")

    st.stop()


# =========================================================
# API
# =========================================================

def api_get(endpoint, params, api_key):

    if not api_key:
        st.error("❌ API-Football Key não configurada.")
        return None

    headers = {
        "x-apisports-key": api_key
    }

    try:

        response = requests.get(
            f"{API_URL}/{endpoint}",
            headers=headers,
            params=params,
            timeout=20
        )

    except requests.RequestException as e:

        st.error(f"❌ Erro de conexão com a API: {e}")
        return None

    if response.status_code != 200:

        st.error(
            f"❌ API-Football HTTP {response.status_code}"
        )

        try:
            erro = response.json()
            st.code(str(erro))
        except Exception:
            st.code(response.text[:1000])

        return None

    try:

        dados = response.json()

    except Exception:

        st.error("❌ A API retornou uma resposta inválida.")
        return None

    # Mostra erros enviados pela própria API
    if dados.get("errors"):

        erros = dados.get("errors")

        if erros:
            st.error(f"❌ Erro da API: {erros}")
            return None

    return dados


# =========================================================
# BUSCAR JOGOS DO DIA
# =========================================================

@st.cache_data(ttl=900)
def buscar_jogos(data, league_ids, api_key):

    resultado = api_get(
        "fixtures",
        {
            "date": data,
            "timezone": "America/Sao_Paulo"
        },
        api_key
    )

    if not resultado:
        return []

    jogos = []

    selecionadas = set(league_ids)

    for item in resultado.get("response", []):

        liga_id = item.get("league", {}).get("id")

        status = (
            item.get("fixture", {})
            .get("status", {})
            .get("short")
        )

        # Apenas jogos ainda não iniciados
        if liga_id in selecionadas and status in ["NS", "TBD"]:

            jogos.append(item)

    return jogos


# =========================================================
# ÚLTIMOS JOGOS
# =========================================================

@st.cache_data(ttl=1800)
def buscar_ultimos_jogos(team_id, api_key):

    resultado = api_get(
        "fixtures",
        {
            "team": team_id,
            "last": 5,
            "timezone": "America/Sao_Paulo"
        },
        api_key
    )

    if not resultado:
        return []

    return resultado.get("response", [])


# =========================================================
# FORMA
# =========================================================

def calcular_forma(jogos, team_id):

    pontos = 0
    gols_marcados = 0
    gols_sofridos = 0
    jogos_validos = 0

    for jogo in jogos:

        gols = jogo.get("goals", {})

        home_id = (
            jogo.get("teams", {})
            .get("home", {})
            .get("id")
        )

        away_id = (
            jogo.get("teams", {})
            .get("away", {})
            .get("id")
        )

        home_goals = gols.get("home")
        away_goals = gols.get("away")

        if home_goals is None or away_goals is None:
            continue

        jogos_validos += 1

        if team_id == home_id:

            gols_marcados += home_goals
            gols_sofridos += away_goals

            if home_goals > away_goals:
                pontos += 3

            elif home_goals == away_goals:
                pontos += 1

        elif team_id == away_id:

            gols_marcados += away_goals
            gols_sofridos += home_goals

            if away_goals > home_goals:
                pontos += 3

            elif home_goals == away_goals:
                pontos += 1

    if jogos_validos == 0:
        return {
            "pontos": 0,
            "media_gols": 0,
            "media_sofridos": 0
        }

    return {
        "pontos": pontos,
        "media_gols": gols_marcados / jogos_validos,
        "media_sofridos": gols_sofridos / jogos_validos
    }


def analisar_forma(jogos, team_id):

    forma = []

    for jogo in jogos:

        gols = jogo.get("goals", {})

        home_id = jogo["teams"]["home"]["id"]
        away_id = jogo["teams"]["away"]["id"]

        home_goals = gols.get("home")
        away_goals = gols.get("away")

        if home_goals is None or away_goals is None:
            continue

        if team_id == home_id:

            if home_goals > away_goals:
                forma.append("V")

            elif home_goals == away_goals:
                forma.append("E")

            else:
                forma.append("D")

        elif team_id == away_id:

            if away_goals > home_goals:
                forma.append("V")

            elif away_goals == home_goals:
                forma.append("E")

            else:
                forma.append("D")

    return forma


# =========================================================
# POISSON
# =========================================================

def poisson(k, lamb):

    return (
        math.exp(-lamb)
        * (lamb ** k)
        / math.factorial(k)
    )


def calcular_probabilidades(
    media_home,
    media_away
):

    prob_home = 0
    prob_draw = 0
    prob_away = 0

    for gols_home in range(0, 8):

        for gols_away in range(0, 8):

            prob = (
                poisson(gols_home, media_home)
                * poisson(gols_away, media_away)
            )

            if gols_home > gols_away:
                prob_home += prob

            elif gols_home == gols_away:
                prob_draw += prob

            else:
                prob_away += prob

    return {
        "home": prob_home,
        "draw": prob_draw,
        "away": prob_away
    }


# =========================================================
# PREVISÃO API
# =========================================================

@st.cache_data(ttl=1800)
def buscar_previsao(fixture_id, api_key):

    resultado = api_get(
        "predictions",
        {
            "fixture": fixture_id
        },
        api_key
    )

    if not resultado:
        return None

    resposta = resultado.get("response", [])

    if not resposta:
        return None

    return resposta[0]


def converter_percentual(valor):

    if valor is None:
        return None

    if isinstance(valor, (int, float)):
        return float(valor)

    try:
        texto = str(valor)
        texto = texto.replace("%", "").replace(",", ".")
        return float(texto)
    except Exception:
        return None


def combinar_modelos(
    modelo,
    previsao
):

    if not previsao:
        return modelo

    pred = previsao.get("predictions", {})

    vencedor = pred.get("winner", {})
    winner_id = vencedor.get("id")

    prob = pred.get("percent", {})

    home = converter_percentual(
        prob.get("home")
    )

    draw = converter_percentual(
        prob.get("draw")
    )

    away = converter_percentual(
        prob.get("away")
    )

    resultado = modelo.copy()

    if home is not None:
        resultado["home"] = (
            modelo["home"] * 0.6
            + (home / 100) * 0.4
        )

    if draw is not None:
        resultado["draw"] = (
            modelo["draw"] * 0.6
            + (draw / 100) * 0.4
        )

    if away is not None:
        resultado["away"] = (
            modelo["away"] * 0.6
            + (away / 100) * 0.4
        )

    resultado["api_winner_id"] = winner_id

    return resultado


# =========================================================
# ODDS
# =========================================================

@st.cache_data(ttl=900)
def buscar_odds(fixture_id, api_key):

    resultado = api_get(
        "odds",
        {
            "fixture": fixture_id
        },
        api_key
    )

    if not resultado:
        return []

    return resultado.get("response", [])


def procurar_odd(books, nome):

    for bookmaker in books:

        for bet in bookmaker.get("bets", []):

            for value in bet.get("values", []):

                valor_nome = str(
                    value.get("value", "")
                ).lower()

                if nome.lower() in valor_nome:

                    odd = value.get("odd")

                    try:
                        return float(odd)
                    except Exception:
                        pass

    return None


def extrair_odds(odds):

    if not odds:
        return {}

    books = []

    for item in odds:

        for bookmaker in item.get("bookmakers", []):

            books.append(bookmaker)

    resultado = {}

    resultado["home"] = procurar_odd(
        books,
        "Home"
    )

    resultado["draw"] = procurar_odd(
        books,
        "Draw"
    )

    resultado["away"] = procurar_odd(
        books,
        "Away"
    )

    resultado["over1.5"] = procurar_odd(
        books,
        "Over 1.5"
    )

    resultado["over2.5"] = procurar_odd(
        books,
        "Over 2.5"
    )

    resultado["btts"] = procurar_odd(
        books,
        "Both Teams Score"
    )

    return resultado


# =========================================================
# ESCOLHA DE MERCADO
# =========================================================

def escolher_mercado(probabilidades, odds):

    candidatos = []

    if odds.get("home"):
        candidatos.append(
            (
                "Vitória Casa",
                probabilidades["home"],
                odds["home"]
            )
        )

    if odds.get("draw"):
        candidatos.append(
            (
                "Empate",
                probabilidades["draw"],
                odds["draw"]
            )
        )

    if odds.get("away"):
        candidatos.append(
            (
                "Vitória Fora",
                probabilidades["away"],
                odds["away"]
            )
        )

    if odds.get("over1.5"):

        candidatos.append(
            (
                "Mais de 1.5 gols",
                None,
                odds["over1.5"]
            )
        )

    if not candidatos:
        return None

    # Prioriza mercados com maior probabilidade
    candidatos_validos = [
        c for c in candidatos
        if c[1] is not None
    ]

    if candidatos_validos:

        candidatos_validos.sort(
            key=lambda x: x[1],
            reverse=True
        )

        melhor = candidatos_validos[0]

        return {
            "mercado": melhor[0],
            "probabilidade": melhor[1],
            "odd": melhor[2]
        }

    return {
        "mercado": candidatos[0][0],
        "probabilidade": None,
        "odd": candidatos[0][2]
    }


# =========================================================
# ANALISAR JOGOS
# =========================================================

def analisar_jogos(jogos, api_key):

    resultados = []

    progresso = st.progress(0)

    total = len(jogos)

    for index, jogo in enumerate(jogos):

        fixture = jogo["fixture"]
        teams = jogo["teams"]

        fixture_id = fixture["id"]

        home = teams["home"]
        away = teams["away"]

        home_id = home["id"]
        away_id = away["id"]

        ultimos_home = buscar_ultimos_jogos(
            home_id,
            api_key
        )

        ultimos_away = buscar_ultimos_jogos(
            away_id,
            api_key
        )

        forma_home = calcular_forma(
            ultimos_home,
            home_id
        )

        forma_away = calcular_forma(
            ultimos_away,
            away_id
        )

        # Médias mínimas para evitar modelo quebrado
        media_home = max(
            0.2,
            forma_home["media_gols"]
        )

        media_away = max(
            0.2,
            forma_away["media_gols"]
        )

        probabilidades = calcular_probabilidades(
            media_home,
            media_away
        )

        previsao = buscar_previsao(
            fixture_id,
            api_key
        )

        probabilidades = combinar_modelos(
            probabilidades,
            previsao
        )

        odds_raw = buscar_odds(
            fixture_id,
            api_key
        )

        odds = extrair_odds(
            odds_raw
        )

        mercado = escolher_mercado(
            probabilidades,
            odds
        )

        if mercado:

            resultados.append(
                {
                    "fixture_id": fixture_id,
                    "liga": jogo["league"]["name"],
                    "pais": jogo["league"]["country"],
                    "data": fixture["date"],
                    "casa": home["name"],
                    "fora": away["name"],
                    "home_prob": probabilidades["home"],
                    "draw_prob": probabilidades["draw"],
                    "away_prob": probabilidades["away"],
                    "mercado": mercado["mercado"],
                    "probabilidade": mercado["probabilidade"],
                    "odd": mercado["odd"],
                    "forma_casa": forma_home["pontos"],
                    "forma_fora": forma_away["pontos"],
                }
            )

        progresso.progress(
            (index + 1) / total
        )

    progresso.empty()

    return resultados


# =========================================================
# MÚLTIPLAS
# =========================================================

def opcoes_do_jogo(jogo):

    opcoes = []

    if jogo.get("mercado") and jogo.get("odd"):

        opcoes.append(
            {
                "jogo": (
                    f'{jogo["casa"]} x {jogo["fora"]}'
                ),
                "mercado": jogo["mercado"],
                "odd": jogo["odd"],
                "probabilidade": jogo["probabilidade"]
            }
        )

    return opcoes


def odd_multipla(lista):

    resultado = 1

    for item in lista:
        resultado *= item["odd"]

    return resultado


def prob_multipla(lista):

    resultado = 1

    for item in lista:

        if item["probabilidade"] is None:
            continue

        resultado *= item["probabilidade"]

    return resultado


def montar_multipla(
    resultados,
    alvo_min,
    alvo_max,
    quantidade_max=8
):

    melhores = [
        x for x in resultados
        if x.get("odd")
        and x["odd"] > 1
        and x.get("probabilidade") is not None
    ]

    melhores.sort(
        key=lambda x: x["probabilidade"],
        reverse=True
    )

    melhores = melhores[:12]

    melhor_combinacao = None

    for tamanho in range(
        2,
        min(quantidade_max, len(melhores)) + 1
    ):

        for combinacao in combinations(
            melhores,
            tamanho
        ):

            odd_total = odd_multipla(
                combinacao
            )

            if (
                odd_total >= alvo_min
                and odd_total <= alvo_max
            ):

                prob_total = prob_multipla(
                    combinacao
                )

                if (
                    melhor_combinacao is None
                    or prob_total
                    > melhor_combinacao["probabilidade"]
                ):

                    melhor_combinacao = {
                        "jogos": combinacao,
                        "odd": odd_total,
                        "probabilidade": prob_total
                    }

    return melhor_combinacao


# =========================================================
# INTERFACE
# =========================================================

st.title("⚽ FUTBET PRO")

st.caption(
    "Análise automática de jogos, mercados e múltiplas"
)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("⚙️ Configurações")

api_key = st.secrets.get(
    "APIFOOTBALL_KEY",
    ""
)

if not api_key:

    api_key = st.sidebar.text_input(
        "🔑 API-Football Key",
        type="password"
    )

data_escolhida = st.sidebar.date_input(
    "📅 Data dos jogos",
    value=datetime.now(
        ZoneInfo("America/Sao_Paulo")
    ).date()
)

competicoes = st.sidebar.multiselect(
    "🏆 Competições",
    list(LEAGUES.keys()),
    default=[
        "Brasileirão",
        "Premier League",
        "La Liga",
        "Serie A",
        "Bundesliga",
        "Ligue 1",
        "Liga Portugal",
        "Eredivisie",
        "Champions League",
        "Europa League"
    ]
)


if st.sidebar.button(
    "🔎 BUSCAR JOGOS",
    use_container_width=True
):

    if not api_key:

        st.error(
            "❌ API-Football Key não encontrada."
        )

    elif not competicoes:

        st.warning(
            "⚠️ Selecione pelo menos uma competição."
        )

    else:

        data_api = data_escolhida.strftime(
            "%Y-%m-%d"
        )

        ids = [
            LEAGUES[nome]
            for nome in competicoes
        ]

        with st.spinner(
            "🔎 Buscando jogos..."
        ):

            jogos = buscar_jogos(
                data_api,
                ids,
                api_key
            )

        st.session_state.jogos = jogos

        if jogos:

            st.success(
                f"✅ {len(jogos)} jogos encontrados."
            )

        else:

            st.warning(
                "⚠️ Nenhum jogo encontrado para os filtros escolhidos."
            )


# =========================================================
# BOTÃO SAIR
# =========================================================

if st.sidebar.button(
    "🚪 Sair",
    use_container_width=True
):

    st.session_state.autenticado = False
    st.rerun()


# =========================================================
# RESULTADOS
# =========================================================

jogos = st.session_state.get(
    "jogos",
    []
)


if not jogos:

    st.info(
        "👈 Escolha a data e as competições e clique em "
        "**BUSCAR JOGOS**."
    )

else:

    st.subheader(
        f"📅 Jogos encontrados: {len(jogos)}"
    )

    tabela = []

    for jogo in jogos:

        tabela.append(
            {
                "Competição": jogo["league"]["name"],
                "Casa": jogo["teams"]["home"]["name"],
                "Fora": jogo["teams"]["away"]["name"],
                "Horário": (
                    jogo["fixture"]["date"]
                    .replace("T", " ")
                    .split("+")[0]
                )
            }
        )

    st.dataframe(
        pd.DataFrame(tabela),
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # ANALISAR
    # =====================================================

    if st.button(
        "🧠 ANALISAR TODOS OS JOGOS",
        use_container_width=True
    ):

        if not api_key:

            st.error(
                "❌ API-Football Key não encontrada."
            )

        else:

            with st.spinner(
                "🧠 Analisando forma, previsões e mercados..."
            ):

                resultados = analisar_jogos(
                    jogos,
                    api_key
                )

            st.session_state.resultados = resultados

            if resultados:

                st.success(
                    f"✅ {len(resultados)} jogos analisados."
                )

            else:

                st.warning(
                    "⚠️ Não foi possível gerar análises."
                )


# =========================================================
# RANKING
# =========================================================

resultados = st.session_state.get(
    "resultados",
    []
)


if resultados:

    st.divider()

    st.subheader(
        "🏆 Ranking dos melhores jogos"
    )

    resultados_ordenados = sorted(
        resultados,
        key=lambda x: (
            x["probabilidade"]
            if x["probabilidade"] is not None
            else 0
        ),
        reverse=True
    )

    ranking = []

    for i, jogo in enumerate(
        resultados_ordenados,
        start=1
    ):

        ranking.append(
            {
                "#": i,
                "Jogo": (
                    f'{jogo["casa"]} x {jogo["fora"]}'
                ),
                "Competição": jogo["liga"],
                "Mercado": jogo["mercado"],
                "Probabilidade": (
                    f'{jogo["probabilidade"] * 100:.1f}%'
                    if jogo["probabilidade"] is not None
                    else "-"
                ),
                "Odd": jogo["odd"]
            }
        )

    st.dataframe(
        pd.DataFrame(ranking),
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # DETALHES
    # =====================================================

    st.divider()

    st.subheader(
        "🔎 Análise detalhada"
    )

    for jogo in resultados_ordenados[:10]:

        titulo = (
            f'{jogo["casa"]} x {jogo["fora"]}'
        )

        with st.expander(titulo):

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Casa",
                    f'{jogo["home_prob"] * 100:.1f}%'
                )

            with col2:

                st.metric(
                    "Empate",
                    f'{jogo["draw_prob"] * 100:.1f}%'
                )

            with col3:

                st.metric(
                    "Fora",
                    f'{jogo["away_prob"] * 100:.1f}%'
                )

            st.write(
                f'🏆 **Competição:** {jogo["liga"]}'
            )

            st.write(
                f'🎯 **Mercado escolhido:** {jogo["mercado"]}'
            )

            st.write(
                f'📊 **Probabilidade estimada:** '
                f'{jogo["probabilidade"] * 100:.1f}%'
            )

            st.write(
                f'💰 **Odd encontrada:** {jogo["odd"]}'
            )

            st.write(
                f'📈 **Forma Casa:** '
                f'{jogo["forma_casa"]} pontos nos últimos jogos'
            )

            st.write(
                f'📉 **Forma Fora:** '
                f'{jogo["forma_fora"]} pontos nos últimos jogos'
            )


    # =====================================================
    # MÚLTIPLAS
    # =====================================================

    st.divider()

    st.subheader(
        "🎯 Múltiplas automáticas"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            "### 🟢 Conservadora"
        )

        multipla = montar_multipla(
            resultados,
            1.8,
            5
        )

        if multipla:

            st.write(
                f'💰 Odd total: **{multipla["odd"]:.2f}**'
            )

            st.write(
                f'📊 Probabilidade combinada: '
                f'**{multipla["probabilidade"] * 100:.2f}%**'
            )

            for jogo in multipla["jogos"]:

                st.write(
                    f'• {jogo["jogo"]} — '
                    f'{jogo["mercado"]} '
                    f'@ {jogo["odd"]}'
                )

        else:

            st.info(
                "Nenhuma combinação encontrada."
            )


    with col2:

        st.markdown(
            "### 🟡 Moderada"
        )

        multipla = montar_multipla(
            resultados,
            5,
            15
        )

        if multipla:

            st.write(
                f'💰 Odd total: **{multipla["odd"]:.2f}**'
            )

            st.write(
                f'📊 Probabilidade combinada: '
                f'**{multipla["probabilidade"] * 100:.2f}%**'
            )

            for jogo in multipla["jogos"]:

                st.write(
                    f'• {jogo["jogo"]} — '
                    f'{jogo["mercado"]} '
                    f'@ {jogo["odd"]}'
                )

        else:

            st.info(
                "Nenhuma combinação encontrada."
            )


    with col3:

        st.markdown(
            "### 🔴 Agressiva"
        )

        multipla = montar_multipla(
            resultados,
            15,
            50
        )

        if multipla:

            st.write(
                f'💰 Odd total: **{multipla["odd"]:.2f}**'
            )

            st.write(
                f'📊 Probabilidade combinada: '
                f'**{multipla["probabilidade"] * 100:.2f}%**'
            )

            for jogo in multipla["jogos"]:

                st.write(
                    f'• {jogo["jogo"]} — '
                    f'{jogo["mercado"]} '
                    f'@ {jogo["odd"]}'
                )

        else:

            st.info(
                "Nenhuma combinação encontrada."
            )


# =========================================================
# RODAPÉ
# =========================================================

st.divider()

st.caption(
    "FUTBET PRO • Ferramenta de análise estatística "
    "• As probabilidades são estimativas e não garantem resultados."
)
