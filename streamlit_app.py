import math
from datetime import datetime
from itertools import combinations
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="FUTBET PRO",
    page_icon="⚽",
    layout="wide"
)

API_URL = "https://v3.football.api-sports.io"

LEAGUES = {
    "🇧🇷 Brasileirão": 71,
    "🏴 Premier League": 39,
    "🇪🇸 La Liga": 140,
    "🇮🇹 Serie A": 135,
    "🇩🇪 Bundesliga": 78,
    "🇫🇷 Ligue 1": 61,
    "🇵🇹 Liga Portugal": 94,
    "🇳🇱 Eredivisie": 88,
    "🏆 Champions League": 2,
    "🏆 Europa League": 3,
}


# ============================================================
# PROTEÇÃO POR SENHA
# ============================================================

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
        <div style="text-align:center; margin-top:80px;">
            <h1>🔐 FUTBET PRO</h1>
            <p>Área privada</p>
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


# ============================================================
# API
# ============================================================

def api_get(endpoint, params, api_key):

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

        if response.status_code != 200:
            return None

        return response.json()

    except Exception:
        return None


# ============================================================
# BUSCAR JOGOS
# ============================================================

@st.cache_data(ttl=900)
def buscar_jogos(data, league_ids, api_key):

    jogos = []

    for league_id in league_ids:

        resultado = api_get(
            "fixtures",
            {
                "date": data,
                "league": league_id,
                "season": datetime.strptime(
                    data, "%Y-%m-%d"
                ).year,
                "timezone": "America/Sao_Paulo"
            },
            api_key
        )

        if not resultado:
            continue

        for item in resultado.get("response", []):

            status = item["fixture"]["status"]["short"]

            if status not in ["NS", "TBD"]:
                continue

            jogos.append(item)

    return jogos


# ============================================================
# ÚLTIMOS JOGOS DO TIME
# ============================================================

@st.cache_data(ttl=1800)
def buscar_ultimos_jogos(team_id, api_key):

    resultado = api_get(
        "fixtures",
        {
            "team": team_id,
            "last": 5,
            "status": "FT"
        },
        api_key
    )

    if not resultado:
        return []

    return resultado.get("response", [])


# ============================================================
# FORMA
# ============================================================

def calcular_forma(jogos, team_id):

    pontos = 0
    gols_marcados = 0
    gols_sofridos = 0

    vitorias = 0
    empates = 0
    derrotas = 0

    total = 0

    for jogo in jogos:

        home_id = jogo["teams"]["home"]["id"]
        away_id = jogo["teams"]["away"]["id"]

        gols_home = jogo["goals"]["home"]
        gols_away = jogo["goals"]["away"]

        if gols_home is None or gols_away is None:
            continue

        total += 1

        if team_id == home_id:

            gols_marcados += gols_home
            gols_sofridos += gols_away

            if gols_home > gols_away:
                pontos += 3
                vitorias += 1

            elif gols_home == gols_away:
                pontos += 1
                empates += 1

            else:
                derrotas += 1

        else:

            gols_marcados += gols_away
            gols_sofridos += gols_home

            if gols_away > gols_home:
                pontos += 3
                vitorias += 1

            elif gols_away == gols_home:
                pontos += 1
                empates += 1

            else:
                derrotas += 1

    if total == 0:
        return {
            "pontos": 0,
            "media_gols": 0,
            "media_sofridos": 0,
            "vitorias": 0,
            "empates": 0,
            "derrotas": 0
        }

    return {
        "pontos": pontos,
        "media_gols": gols_marcados / total,
        "media_sofridos": gols_sofridos / total,
        "vitorias": vitorias,
        "empates": empates,
        "derrotas": derrotas
    }


def analisar_forma(team_id, api_key):

    jogos = buscar_ultimos_jogos(team_id, api_key)

    return calcular_forma(jogos, team_id)


# ============================================================
# POISSON
# ============================================================

def poisson(lmbda, k):

    if lmbda <= 0:
        return 0

    return (
        math.exp(-lmbda)
        * (lmbda ** k)
        / math.factorial(k)
    )


def calcular_probabilidades(
    media_home,
    media_away,
    max_gols=7
):

    probabilidades = {}

    casa = 0
    empate = 0
    fora = 0

    over15 = 0
    over25 = 0

    casa_marca = 0
    fora_marca = 0

    for gols_casa in range(max_gols + 1):

        for gols_fora in range(max_gols + 1):

            prob = (
                poisson(media_home, gols_casa)
                * poisson(media_away, gols_fora)
            )

            if gols_casa > gols_fora:
                casa += prob

            elif gols_casa == gols_fora:
                empate += prob

            else:
                fora += prob

            total_gols = gols_casa + gols_fora

            if total_gols >= 2:
                over15 += prob

            if total_gols >= 3:
                over25 += prob

            if gols_casa >= 1:
                casa_marca += prob

            if gols_fora >= 1:
                fora_marca += prob

    probabilidades["casa"] = casa
    probabilidades["empate"] = empate
    probabilidades["fora"] = fora
    probabilidades["over15"] = over15
    probabilidades["over25"] = over25
    probabilidades["casa_marca"] = casa_marca
    probabilidades["fora_marca"] = fora_marca

    return probabilidades


# ============================================================
# PREVISÃO API-FOOTBALL
# ============================================================

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

    respostas = resultado.get("response", [])

    if not respostas:
        return None

    return respostas[0]


def converter_percentual(valor):

    if valor is None:
        return 0

    try:

        if isinstance(valor, str):
            valor = valor.replace("%", "").strip()

        return float(valor) / 100

    except Exception:
        return 0


def combinar_modelos(
    modelo,
    previsao_api
):

    if not previsao_api:
        return modelo

    try:

        pred = previsao_api.get("predictions", {})

        vencedor = pred.get("percent", {})

        api_casa = converter_percentual(
            vencedor.get("home")
        )

        api_empate = converter_percentual(
            vencedor.get("draw")
        )

        api_fora = converter_percentual(
            vencedor.get("away")
        )

        resultado = dict(modelo)

        if api_casa > 0:
            resultado["casa"] = (
                modelo["casa"] * 0.6
                + api_casa * 0.4
            )

        if api_empate > 0:
            resultado["empate"] = (
                modelo["empate"] * 0.6
                + api_empate * 0.4
            )

        if api_fora > 0:
            resultado["fora"] = (
                modelo["fora"] * 0.6
                + api_fora * 0.4
            )

        return resultado

    except Exception:

        return modelo


# ============================================================
# ODDS
# ============================================================

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
        return None

    respostas = resultado.get("response", [])

    if not respostas:
        return None

    return respostas[0]


def procurar_odd(odds, palavras):

    if not odds:
        return None

    try:

        bookmakers = odds.get("bookmakers", [])

        for bookmaker in bookmakers:

            for aposta in bookmaker.get("bets", []):

                nome = aposta.get("name", "").lower()

                if any(
                    palavra.lower() in nome
                    for palavra in palavras
                ):

                    for valor in aposta.get("values", []):

                        odd = valor.get("odd")

                        try:
                            return float(odd)

                        except Exception:
                            continue

    except Exception:
        pass

    return None


def extrair_odds(odds):

    resultado = {}

    resultado["casa"] = procurar_odd(
        odds,
        ["home"]
    )

    resultado["fora"] = procurar_odd(
        odds,
        ["away"]
    )

    resultado["over15"] = procurar_odd(
        odds,
        ["over 1.5", "over1.5"]
    )

    resultado["over25"] = procurar_odd(
        odds,
        ["over 2.5", "over2.5"]
    )

    return resultado


# ============================================================
# ESCOLHA DE MERCADO
# ============================================================

def escolher_mercado(probabilidades):

    opcoes = [
        (
            "Mais de 1.5 gols",
            probabilidades["over15"],
            "over15"
        ),
        (
            "Casa marca 1+ gol",
            probabilidades["casa_marca"],
            "casa_marca"
        ),
        (
            "Fora marca 1+ gol",
            probabilidades["fora_marca"],
            "fora_marca"
        ),
        (
            "Casa vence",
            probabilidades["casa"],
            "casa"
        ),
        (
            "Fora vence",
            probabilidades["fora"],
            "fora"
        )
    ]

    opcoes.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return opcoes[0]


# ============================================================
# ANÁLISE DOS JOGOS
# ============================================================

def analisar_jogos(jogos, api_key):

    resultados = []

    for jogo in jogos:

        try:

            fixture_id = jogo["fixture"]["id"]

            home = jogo["teams"]["home"]
            away = jogo["teams"]["away"]

            forma_home = analisar_forma(
                home["id"],
                api_key
            )

            forma_away = analisar_forma(
                away["id"],
                api_key
            )

            media_home = max(
                0.25,
                (
                    forma_home["media_gols"]
                    + forma_away["media_sofridos"]
                ) / 2
            )

            media_away = max(
                0.25,
                (
                    forma_away["media_gols"]
                    + forma_home["media_sofridos"]
                ) / 2
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

            mercado, probabilidade, chave = escolher_mercado(
                probabilidades
            )

            resultados.append({
                "fixture_id": fixture_id,
                "home": home["name"],
                "away": away["name"],
                "home_id": home["id"],
                "away_id": away["id"],
                "probabilidade": probabilidade,
                "mercado": mercado,
                "chave": chave,
                "odds": odds,
                "forma_home": forma_home,
                "forma_away": forma_away,
                "probabilidades": probabilidades
            })

        except Exception:
            continue

    return resultados


# ============================================================
# OPÇÕES PARA MÚLTIPLA
# ============================================================

def opcoes_do_jogo(jogo):

    p = jogo["probabilidades"]

    opcoes = [
        {
            "jogo": f'{jogo["home"]} x {jogo["away"]}',
            "mercado": "Mais de 1.5 gols",
            "prob": p["over15"],
            "odd": jogo["odds"].get("over15")
        },
        {
            "jogo": f'{jogo["home"]} x {jogo["away"]}',
            "mercado": f'{jogo["home"]} marca 1+',
            "prob": p["casa_marca"],
            "odd": None
        },
        {
            "jogo": f'{jogo["home"]} x {jogo["away"]}',
            "mercado": f'{jogo["away"]} marca 1+',
            "prob": p["fora_marca"],
            "odd": None
        },
        {
            "jogo": f'{jogo["home"]} x {jogo["away"]}',
            "mercado": f'{jogo["home"]} vence',
            "prob": p["casa"],
            "odd": jogo["odds"].get("casa")
        },
        {
            "jogo": f'{jogo["home"]} x {jogo["away"]}',
            "mercado": f'{jogo["away"]} vence',
            "prob": p["fora"],
            "odd": jogo["odds"].get("fora")
        }
    ]

    return opcoes


def odd_multipla(apostas):

    odd = 1

    for aposta in apostas:

        if aposta["odd"] is None:
            return None

        odd *= aposta["odd"]

    return odd


def prob_multipla(apostas):

    prob = 1

    for aposta in apostas:
        prob *= aposta["prob"]

    return prob


def montar_multipla(
    analises,
    alvo_min,
    alvo_max,
    quantidade=4
):

    candidatos = []

    for jogo in analises:

        candidatos.extend(
            opcoes_do_jogo(jogo)
        )

    candidatos = [
        x for x in candidatos
        if x["odd"] is not None
        and x["odd"] > 1
    ]

    candidatos.sort(
        key=lambda x: x["prob"],
        reverse=True
    )

    melhor = None

    limite = min(
        len(candidatos),
        12
    )

    for grupo in combinations(
        candidatos[:limite],
        quantidade
    ):

        jogos_unicos = set(
            x["jogo"]
            for x in grupo
        )

        if len(jogos_unicos) != quantidade:
            continue

        odd = odd_multipla(grupo)

        if odd is None:
            continue

        if alvo_min <= odd <= alvo_max:

            prob = prob_multipla(grupo)

            if melhor is None or prob > melhor["prob"]:
                melhor = {
                    "apostas": grupo,
                    "odd": odd,
                    "prob": prob
                }

    return melhor


# ============================================================
# INTERFACE
# ============================================================

st.title("⚽ FUTBET PRO")

st.caption(
    "Análise automática de jogos, mercados e múltiplas"
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("⚙️ Configurações")


api_key = st.secrets.get("APIFOOTBALL_KEY", "")

if not api_key:

    api_key = st.sidebar.text_input(
        "🔑 API-Football Key",
        type="password",
        help="Você poderá colocar sua chave aqui enquanto ainda não usar os Secrets."
    )


if st.sidebar.button(
    "🚪 Sair",
    use_container_width=True
):

    st.session_state.autenticado = False
    st.rerun()


data_escolhida = st.sidebar.date_input(
    "📅 Data dos jogos",
    value=datetime.now(
        ZoneInfo("America/Sao_Paulo")
    ).date()
)


ligas_escolhidas = st.sidebar.multiselect(
    "🏆 Competições",
    options=list(LEAGUES.keys()),
    default=list(LEAGUES.keys())
)


buscar = st.sidebar.button(
    "🔎 BUSCAR JOGOS",
    use_container_width=True
)


# ============================================================
# TELA PRINCIPAL
# ============================================================

if not api_key:

    st.info(
        "🔑 Coloque sua chave da API-Football na barra lateral "
        "para começar."
    )

    st.markdown(
        """
        ### O que o FUTBET PRO fará

        ⚽ Encontrar jogos do dia

        📊 Analisar os últimos jogos dos times

        🤖 Combinar o modelo estatístico com a previsão da API

        🎯 Procurar mercados como:
        - Mais de 1.5 gols
        - Time marca 1+
        - Vitória
        - Outros mercados disponíveis

        📈 Montar múltiplas em diferentes faixas de odd
        """
    )

    st.stop()


if buscar:

    league_ids = [
        LEAGUES[nome]
        for nome in ligas_escolhidas
    ]

    data_str = data_escolhida.strftime(
        "%Y-%m-%d"
    )

    with st.spinner("🔎 Buscando jogos..."):

        jogos = buscar_jogos(
            data_str,
            league_ids,
            api_key
        )

    if not jogos:

        st.warning(
            "Nenhum jogo encontrado para os filtros escolhidos."
        )

        st.stop()

    st.success(
        f"⚽ {len(jogos)} jogos encontrados."
    )

    with st.spinner(
        "🤖 Analisando forma, probabilidades e mercados..."
    ):

        analises = analisar_jogos(
            jogos,
            api_key
        )

    if not analises:

        st.error(
            "Não foi possível analisar os jogos."
        )

        st.stop()


    # ========================================================
    # RANKING
    # ========================================================

    st.header("🏆 Ranking dos jogos")

    ranking = sorted(
        analises,
        key=lambda x: x["probabilidade"],
        reverse=True
    )

    tabela = []

    for i, jogo in enumerate(
        ranking,
        start=1
    ):

        tabela.append({
            "#": i,
            "Jogo": f'{jogo["home"]} x {jogo["away"]}',
            "Mercado": jogo["mercado"],
            "Probabilidade": f'{jogo["probabilidade"] * 100:.1f}%'
        })

    st.dataframe(
        pd.DataFrame(tabela),
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # ANÁLISE DETALHADA
    # ========================================================

    st.header("🔬 Análise detalhada")

    for jogo in ranking[:10]:

        with st.expander(
            f'⚽ {jogo["home"]} x {jogo["away"]}'
        ):

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Mercado sugerido",
                    jogo["mercado"]
                )

            with col2:

                st.metric(
                    "Probabilidade",
                    f'{jogo["probabilidade"] * 100:.1f}%'
                )

            with col3:

                odd = jogo["odds"].get(
                    jogo["chave"]
                )

                if odd:
                    st.metric(
                        "Odd encontrada",
                        f"{odd:.2f}"
                    )
                else:
                    st.metric(
                        "Odd",
                        "Não encontrada"
                    )


            st.write("### 📊 Forma recente")

            col1, col2 = st.columns(2)

            with col1:

                f = jogo["forma_home"]

                st.write(
                    f'**{jogo["home"]}**'
                )

                st.write(
                    f'Vitórias: {f["vitorias"]} | '
                    f'Empates: {f["empates"]} | '
                    f'Derrotas: {f["derrotas"]}'
                )

                st.write(
                    f'Média de gols: '
                    f'{f["media_gols"]:.2f}'
                )

            with col2:

                f = jogo["forma_away"]

                st.write(
                    f'**{jogo["away"]}**'
                )

                st.write(
                    f'Vitórias: {f["vitorias"]} | '
                    f'Empates: {f["empates"]} | '
                    f'Derrotas: {f["derrotas"]}'
                )

                st.write(
                    f'Média de gols: '
                    f'{f["media_gols"]:.2f}'
                )


            st.write("### 🎯 Probabilidades")

            p = jogo["probabilidades"]

            probabilidades_df = pd.DataFrame({
                "Mercado": [
                    "Casa vence",
                    "Empate",
                    "Fora vence",
                    "Mais de 1.5 gols",
                    "Mais de 2.5 gols",
                    f'{jogo["home"]} marca 1+',
                    f'{jogo["away"]} marca 1+'
                ],
                "Probabilidade": [
                    f'{p["casa"] * 100:.1f}%',
                    f'{p["empate"] * 100:.1f}%',
                    f'{p["fora"] * 100:.1f}%',
                    f'{p["over15"] * 100:.1f}%',
                    f'{p["over25"] * 100:.1f}%',
                    f'{p["casa_marca"] * 100:.1f}%',
                    f'{p["fora_marca"] * 100:.1f}%'
                ]
            })

            st.dataframe(
                probabilidades_df,
                use_container_width=True,
                hide_index=True
            )


    # ========================================================
    # MÚLTIPLAS
    # ========================================================

    st.header("🎯 Múltiplas automáticas")

    niveis = [
        ("🟢 Conservadora", 1.5, 5),
        ("🟡 Média", 5, 15),
        ("🔴 Agressiva", 15, 60)
    ]

    for nome, minimo, maximo in niveis:

        st.subheader(nome)

        multipla = montar_multipla(
            analises,
            minimo,
            maximo,
            quantidade=4
        )

        if not multipla:

            st.info(
                "Não foi encontrada uma combinação "
                "dentro dessa faixa."
            )

            continue


        st.write(
            f'**Odd aproximada: {multipla["odd"]:.2f}**'
        )

        st.write(
            f'Probabilidade matemática combinada: '
            f'{multipla["prob"] * 100:.2f}%'
        )

        for aposta in multipla["apostas"]:

            st.write(
                f'⚽ **{aposta["jogo"]}** — '
                f'{aposta["mercado"]} '
                f'— Odd {aposta["odd"]:.2f}'
            )

        st.divider()


else:

    st.info(
        "👈 Escolha a data e as competições na barra lateral "
        "e clique em **BUSCAR JOGOS**."
    )


# ============================================================
# RODAPÉ
# ============================================================

st.caption(
    "FUTBET PRO • Ferramenta de análise estatística"
)
