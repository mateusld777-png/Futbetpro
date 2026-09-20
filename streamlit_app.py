import math
from datetime import datetime, timedelta
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


# ============================================================
# SENHA DO APLICATIVO
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
        <div style="
            text-align:center;
            padding:40px 10px 20px 10px;
        ">
            <h1>⚽ FUTBET PRO</h1>
            <p style="font-size:18px;">
                Área privada de análise esportiva
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    senha = st.text_input(
        "🔐 Digite sua senha",
        type="password",
        placeholder="Sua senha"
    )

    if st.button(
        "🔓 ENTRAR",
        use_container_width=True
    ):
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

        if response.status_code != 200:
            st.error(
                f"❌ Erro HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )
            return None

        data = response.json()

        errors = data.get("errors")

        if errors:
            st.error(f"❌ Erro da API: {errors}")
            return None

        return data

    except requests.exceptions.RequestException as e:

        st.error(
            f"❌ Erro de conexão com a API: {e}"
        )

        return None


# ============================================================
# BUSCAR JOGOS DO DIA
# ============================================================

@st.cache_data(ttl=900)
def buscar_jogos(data_escolhida, ligas, api_key):

    resultado = api_get(
        "fixtures",
        {
            "date": data_escolhida,
            "timezone": "America/Sao_Paulo"
        },
        api_key
    )

    if not resultado:
        return []

    jogos = []

    ligas_ids = set(ligas)

    for item in resultado.get("response", []):

        liga_id = item.get("league", {}).get("id")

        status = (
            item.get("fixture", {})
            .get("status", {})
            .get("short")
        )

        if liga_id in ligas_ids and status in ["NS", "TBD"]:

            jogos.append(item)

    return jogos


# ============================================================
# ÚLTIMOS JOGOS DO TIME
#
# NÃO USA MAIS last=5
#
# Busca um período e depois pega localmente os 5
# jogos mais recentes.
# ============================================================

@st.cache_data(ttl=1800)
def buscar_ultimos_jogos(
    team_id,
    data_referencia,
    api_key
):

    try:

        data_ref = datetime.strptime(
            data_referencia,
            "%Y-%m-%d"
        ).date()

    except Exception:

        return []


    # Busca aproximadamente os últimos 4 meses
    data_inicio = data_ref - timedelta(days=120)

    # Somente jogos anteriores à partida analisada
    data_fim = data_ref - timedelta(days=1)


    resultado = api_get(
        "fixtures",
        {
            "team": team_id,
            "from": data_inicio.strftime("%Y-%m-%d"),
            "to": data_fim.strftime("%Y-%m-%d"),
            "timezone": "America/Sao_Paulo"
        },
        api_key
    )


    if not resultado:
        return []


    jogos = []


    for item in resultado.get("response", []):

        status = (
            item.get("fixture", {})
            .get("status", {})
            .get("short")
        )

        if status in ["FT", "AET", "PEN"]:

            jogos.append(item)


    # Mais recentes primeiro
    jogos.sort(
        key=lambda x: x.get(
            "fixture", {}
        ).get(
            "timestamp",
            0
        ),
        reverse=True
    )


    return jogos[:5]


# ============================================================
# FORMA DO TIME
# ============================================================

def calcular_forma(
    jogos,
    team_id
):

    if not jogos:
        return {
            "jogos": 0,
            "vitorias": 0,
            "empates": 0,
            "derrotas": 0,
            "gols_marcados": 0,
            "gols_sofridos": 0,
            "media_gols": 0,
            "media_sofridos": 0,
            "pontos": 0,
            "forma": ""
        }


    vitorias = 0
    empates = 0
    derrotas = 0
    gols_marcados = 0
    gols_sofridos = 0
    pontos = 0

    resultados = []


    for jogo in jogos:

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

        gols_home = (
            jogo.get("goals", {})
            .get("home")
        )

        gols_away = (
            jogo.get("goals", {})
            .get("away")
        )


        if gols_home is None or gols_away is None:
            continue


        if team_id == home_id:

            marcados = gols_home
            sofridos = gols_away

        elif team_id == away_id:

            marcados = gols_away
            sofridos = gols_home

        else:

            continue


        gols_marcados += marcados
        gols_sofridos += sofridos


        if marcados > sofridos:

            vitorias += 1
            pontos += 3
            resultados.append("V")

        elif marcados == sofridos:

            empates += 1
            pontos += 1
            resultados.append("E")

        else:

            derrotas += 1
            resultados.append("D")


    total = (
        vitorias +
        empates +
        derrotas
    )


    if total == 0:

        return {
            "jogos": 0,
            "vitorias": 0,
            "empates": 0,
            "derrotas": 0,
            "gols_marcados": 0,
            "gols_sofridos": 0,
            "media_gols": 0,
            "media_sofridos": 0,
            "pontos": 0,
            "forma": ""
        }


    return {

        "jogos": total,

        "vitorias": vitorias,

        "empates": empates,

        "derrotas": derrotas,

        "gols_marcados": gols_marcados,

        "gols_sofridos": gols_sofridos,

        "media_gols": gols_marcados / total,

        "media_sofridos": gols_sofridos / total,

        "pontos": pontos,

        "forma": "".join(resultados)

    }


# ============================================================
# POISSON
# ============================================================

def poisson(
    gols,
    media
):

    try:

        return (
            math.exp(-media)
            * media ** gols
            / math.factorial(gols)
        )

    except Exception:

        return 0


def calcular_probabilidades(
    lambda_home,
    lambda_away
):

    home_win = 0
    draw = 0
    away_win = 0

    over_15 = 0

    max_goals = 10


    for gols_home in range(max_goals + 1):

        for gols_away in range(max_goals + 1):

            prob_home = poisson(
                gols_home,
                lambda_home
            )

            prob_away = poisson(
                gols_away,
                lambda_away
            )

            prob = (
                prob_home *
                prob_away
            )


            if gols_home > gols_away:

                home_win += prob

            elif gols_home == gols_away:

                draw += prob

            else:

                away_win += prob


            if (
                gols_home +
                gols_away
            ) >= 2:

                over_15 += prob


    return {

        "home": home_win,

        "draw": draw,

        "away": away_win,

        "over15": over_15,

        "home_1plus":
            1 - math.exp(-lambda_home),

        "away_1plus":
            1 - math.exp(-lambda_away),

        "1x":
            home_win + draw,

        "x2":
            draw + away_win,

        "12":
            home_win + away_win
    }


# ============================================================
# PREVISÃO DA API
# ============================================================

@st.cache_data(ttl=1800)
def buscar_previsao(
    fixture_id,
    api_key
):

    resultado = api_get(
        "predictions",
        {
            "fixture": fixture_id
        },
        api_key
    )

    if not resultado:
        return None


    resposta = resultado.get(
        "response",
        []
    )


    if not resposta:
        return None


    return resposta[0]


# ============================================================
# CONVERTER PERCENTUAL
# ============================================================

def converter_percentual(valor):

    try:

        valor = float(
            str(valor)
            .replace("%", "")
            .strip()
        )

        if valor > 1:
            return valor / 100

        return valor

    except Exception:

        return None


# ============================================================
# COMBINAR MODELOS
# ============================================================

def combinar_modelos(
    modelo,
    previsao
):

    if not previsao:

        return modelo


    try:

        predictions = previsao.get(
            "predictions",
            {}
        )

        vencedor = predictions.get(
            "winner",
            {}
        )


        api_home = converter_percentual(
            vencedor.get("home")
        )

        api_away = converter_percentual(
            vencedor.get("away")
        )

        api_draw = converter_percentual(
            vencedor.get("draw")
        )


        if (
            api_home is None or
            api_away is None or
            api_draw is None
        ):

            return modelo


        return {

            "home":
                modelo["home"] * 0.60
                + api_home * 0.40,

            "draw":
                modelo["draw"] * 0.60
                + api_draw * 0.40,

            "away":
                modelo["away"] * 0.60
                + api_away * 0.40,

            "over15":
                modelo["over15"],

            "home_1plus":
                modelo["home_1plus"],

            "away_1plus":
                modelo["away_1plus"],

            "1x":
                modelo["home"] * 0.60
                + api_home * 0.40
                + modelo["draw"] * 0.60
                + api_draw * 0.40,

            "x2":
                modelo["draw"] * 0.60
                + api_draw * 0.40
                + modelo["away"] * 0.60
                + api_away * 0.40,

            "12":
                modelo["home"] * 0.60
                + api_home * 0.40
                + modelo["away"] * 0.60
                + api_away * 0.40
        }


    except Exception:

        return modelo


# ============================================================
# ODDS
# ============================================================

@st.cache_data(ttl=900)
def buscar_odds(
    fixture_id,
    api_key
):

    resultado = api_get(
        "odds",
        {
            "fixture": fixture_id
        },
        api_key
    )

    if not resultado:
        return []


    return resultado.get(
        "response",
        []
    )


def procurar_odd(
    odds_data,
    nomes
):

    nomes = [
        nome.lower()
        for nome in nomes
    ]


    for bloco in odds_data:

        bookmakers = bloco.get(
            "bookmakers",
            []
        )

        for bookmaker in bookmakers:

            bets = bookmaker.get(
                "bets",
                []
            )

            for bet in bets:

                bet_name = str(
                    bet.get("name", "")
                ).lower()


                for valor in bet.get(
                    "values",
                    []
                ):

                    label = str(
                        valor.get("value", "")
                    ).lower()


                    texto = (
                        bet_name
                        + " "
                        + label
                    )


                    if any(
                        nome in texto
                        for nome in nomes
                    ):

                        try:

                            return float(
                                valor.get("odd")
                            )

                        except Exception:

                            pass


    return None


def extrair_odds(
    odds_data
):

    return {

        "home":
            procurar_odd(
                odds_data,
                ["home"]
            ),

        "draw":
            procurar_odd(
                odds_data,
                ["draw"]
            ),

        "away":
            procurar_odd(
                odds_data,
                ["away"]
            ),

        "over15":
            procurar_odd(
                odds_data,
                [
                    "over 1.5",
                    "over1.5"
                ]
            ),

        "1x":
            procurar_odd(
                odds_data,
                [
                    "home or draw",
                    "1x"
                ]
            ),

        "x2":
            procurar_odd(
                odds_data,
                [
                    "draw or away",
                    "x2"
                ]
            ),

        "12":
            procurar_odd(
                odds_data,
                [
                    "home or away",
                    "12"
                ]
            )
    }


# ============================================================
# ESCOLHER MERCADO
# ============================================================

def escolher_mercado(
    probabilidades,
    odds
):

    mercados = [

        (
            "Dupla chance 1X",
            probabilidades["1x"],
            odds.get("1x")
        ),

        (
            "Dupla chance X2",
            probabilidades["x2"],
            odds.get("x2")
        ),

        (
            "Mais de 1.5 gols",
            probabilidades["over15"],
            odds.get("over15")
        ),

        (
            "Vitória mandante",
            probabilidades["home"],
            odds.get("home")
        ),

        (
            "Vitória visitante",
            probabilidades["away"],
            odds.get("away")
        )
    ]


    # Primeiro tenta mercados com odd disponível
    mercados_com_odd = [
        m for m in mercados
        if m[2] is not None
    ]


    if mercados_com_odd:

        # Busca equilíbrio entre probabilidade e odd
        mercados_com_odd.sort(
            key=lambda x:
                (x[1] * min(x[2], 3)),
            reverse=True
        )

        nome, prob, odd = mercados_com_odd[0]

        return {
            "mercado": nome,
            "probabilidade": prob,
            "odd": odd
        }


    # Se não houver odds disponíveis,
    # mostra o mercado de maior probabilidade.
    mercados.sort(
        key=lambda x: x[1],
        reverse=True
    )


    nome, prob, odd = mercados[0]


    return {
        "mercado": nome,
        "probabilidade": prob,
        "odd": None
    }


# ============================================================
# ANALISAR JOGOS
# ============================================================

def analisar_jogos(
    jogos,
    api_key
):

    resultados = []


    for indice, fixture in enumerate(jogos):

        try:

            fixture_id = (
                fixture
                .get("fixture", {})
                .get("id")
            )


            data_jogo = (
                fixture
                .get("fixture", {})
                .get("date", "")
            )


            data_referencia = (
                data_jogo[:10]
                if data_jogo
                else datetime.now(
                    ZoneInfo("America/Sao_Paulo")
                ).strftime("%Y-%m-%d")
            )


            home = (
                fixture
                .get("teams", {})
                .get("home", {})
            )

            away = (
                fixture
                .get("teams", {})
                .get("away", {})
            )


            home_id = home.get("id")
            away_id = away.get("id")


            home_name = home.get(
                "name",
                "Mandante"
            )

            away_name = away.get(
                "name",
                "Visitante"
            )


            # ----------------------------------------
            # ÚLTIMOS 5 JOGOS
            # ----------------------------------------

            ultimos_home = buscar_ultimos_jogos(
                home_id,
                data_referencia,
                api_key
            )

            ultimos_away = buscar_ultimos_jogos(
                away_id,
                data_referencia,
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


            # ----------------------------------------
            # MÉDIAS
            # ----------------------------------------

            media_home_marcados = (
                forma_home["media_gols"]
                if forma_home["jogos"] > 0
                else 1.2
            )

            media_home_sofridos = (
                forma_home["media_sofridos"]
                if forma_home["jogos"] > 0
                else 1.2
            )

            media_away_marcados = (
                forma_away["media_gols"]
                if forma_away["jogos"] > 0
                else 1.0
            )

            media_away_sofridos = (
                forma_away["media_sofridos"]
                if forma_away["jogos"] > 0
                else 1.2
            )


            # ----------------------------------------
            # MODELO DE GOLS
            # ----------------------------------------

            lambda_home = (
                media_home_marcados * 0.60
                + media_away_sofridos * 0.40
            )

            lambda_away = (
                media_away_marcados * 0.60
                + media_home_sofridos * 0.40
            )


            # Pequeno ajuste de mando
            lambda_home *= 1.08


            probabilidades = calcular_probabilidades(
                lambda_home,
                lambda_away
            )


            # ----------------------------------------
            # PREVISÃO DA API
            # ----------------------------------------

            previsao = buscar_previsao(
                fixture_id,
                api_key
            )


            probabilidades = combinar_modelos(
                probabilidades,
                previsao
            )


            # ----------------------------------------
            # ODDS
            # ----------------------------------------

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


            # ----------------------------------------
            # SCORE DE CONFIANÇA
            # ----------------------------------------

            melhor_probabilidade = (
                mercado["probabilidade"]
            )


            confianca = (
                melhor_probabilidade * 100
            )


            # Penaliza quando há pouca forma
            total_jogos_forma = (
                forma_home["jogos"]
                + forma_away["jogos"]
            )


            if total_jogos_forma < 6:
                confianca *= 0.90


            resultados.append({

                "fixture_id":
                    fixture_id,

                "competicao":
                    fixture
                    .get("league", {})
                    .get("name", ""),

                "data":
                    data_jogo,

                "home":
                    home_name,

                "away":
                    away_name,

                "forma_home":
                    forma_home,

                "forma_away":
                    forma_away,

                "probabilidades":
                    probabilidades,

                "odds":
                    odds,

                "mercado":
                    mercado["mercado"],

                "probabilidade":
                    mercado["probabilidade"],

                "odd":
                    mercado["odd"],

                "confianca":
                    confianca,

                "lambda_home":
                    lambda_home,

                "lambda_away":
                    lambda_away

            })


        except Exception as e:

            st.warning(
                f"⚠️ Não foi possível analisar "
                f"um dos jogos: {e}"
            )


    return resultados


# ============================================================
# OPÇÕES PARA MÚLTIPLAS
# ============================================================

def opcoes_do_jogo(
    resultado
):

    p = resultado["probabilidades"]
    odds = resultado["odds"]


    opcoes = []


    mercados = [

        (
            "1X",
            p["1x"],
            odds.get("1x")
        ),

        (
            "X2",
            p["x2"],
            odds.get("x2")
        ),

        (
            "Mais de 1.5 gols",
            p["over15"],
            odds.get("over15")
        ),

        (
            "Vitória mandante",
            p["home"],
            odds.get("home")
        ),

        (
            "Vitória visitante",
            p["away"],
            odds.get("away")
        )
    ]


    for nome, prob, odd in mercados:

        if odd is None:
            continue

        if odd <= 1:
            continue

        opcoes.append({

            "jogo":
                f"{resultado['home']} x {resultado['away']}",

            "mercado":
                nome,

            "odd":
                odd,

            "prob":
                prob,

            "confianca":
                prob * 100
        })


    return opcoes


# ============================================================
# ODDS DA MÚLTIPLA
# ============================================================

def odd_multipla(
    selecoes
):

    resultado = 1.0

    for selecao in selecoes:

        resultado *= selecao["odd"]

    return resultado


# ============================================================
# PROBABILIDADE DA MÚLTIPLA
# ============================================================

def prob_multipla(
    selecoes
):

    resultado = 1.0

    for selecao in selecoes:

        resultado *= selecao["prob"]

    return resultado


# ============================================================
# MONTAR MÚLTIPLA
# ============================================================

def montar_multipla(
    resultados,
    alvo_odd,
    max_jogos=8
):

    opcoes = []


    for resultado in resultados:

        jogo_opcoes = opcoes_do_jogo(
            resultado
        )

        if jogo_opcoes:

            # Pega somente a melhor opção
            # de cada jogo para reduzir combinações.
            jogo_opcoes.sort(
                key=lambda x:
                    x["prob"],
                reverse=True
            )

            opcoes.append(
                jogo_opcoes[0]
            )


    if len(opcoes) < 2:
        return []


    opcoes = sorted(
        opcoes,
        key=lambda x:
            x["prob"],
        reverse=True
    )


    opcoes = opcoes[:max_jogos]


    melhor = None
    melhor_distancia = float("inf")


    limite_jogos = min(
        len(opcoes),
        8
    )


    for tamanho in range(
        2,
        limite_jogos + 1
    ):

        for combinacao in combinations(
            opcoes,
            tamanho
        ):

            odd_total = odd_multipla(
                combinacao
            )

            prob_total = prob_multipla(
                combinacao
            )


            if odd_total <= 0:
                continue


            distancia = abs(
                math.log(odd_total)
                - math.log(alvo_odd)
            )


            # Evita múltiplas muito improváveis
            if prob_total < 0.01:
                continue


            if distancia < melhor_distancia:

                melhor_distancia = distancia

                melhor = {

                    "selecoes":
                        list(combinacao),

                    "odd":
                        odd_total,

                    "probabilidade":
                        prob_total

                }


    return melhor


# ============================================================
# TÍTULO
# ============================================================

st.title("⚽ FUTBET PRO")

st.caption(
    "Análise automática de jogos, mercados e múltiplas"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ CONFIGURAÇÕES")


    api_key = st.secrets.get(
        "APIFOOTBALL_KEY",
        ""
    )


    if not api_key:

        api_key = st.text_input(
            "🔑 API-Football Key",
            type="password",
            help="Sua chave da API-Football"
        )


    st.divider()


    data_escolhida = st.date_input(
        "📅 Data dos jogos",
        value=datetime.now(
            ZoneInfo("America/Sao_Paulo")
        ).date()
    )


    ligas_selecionadas = st.multiselect(
        "🏆 Competições",
        options=list(LEAGUES.keys()),
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


    buscar = st.button(
        "🔎 BUSCAR JOGOS",
        use_container_width=True
    )


    st.divider()


    if st.button(
        "🚪 Sair",
        use_container_width=True
    ):

        st.session_state.autenticado = False
        st.rerun()


# ============================================================
# BUSCA
# ============================================================

if buscar:

    if not api_key:

        st.error(
            "❌ Coloque sua API-Football Key."
        )

        st.stop()


    if not ligas_selecionadas:

        st.warning(
            "⚠️ Selecione pelo menos uma competição."
        )

        st.stop()


    liga_ids = [
        LEAGUES[nome]
        for nome in ligas_selecionadas
    ]


    with st.spinner(
        "🔎 Procurando jogos..."
    ):

        jogos = buscar_jogos(
            data_escolhida.strftime(
                "%Y-%m-%d"
            ),
            liga_ids,
            api_key
        )


    st.session_state.jogos = jogos


# ============================================================
# MOSTRAR JOGOS
# ============================================================

jogos = st.session_state.get(
    "jogos",
    []
)


if jogos:

    st.success(
        f"⚽ {len(jogos)} jogos encontrados."
    )


    tabela = []


    for jogo in jogos:

        tabela.append({

            "Competição":
                jogo
                .get("league", {})
                .get("name", ""),

            "Mandante":
                jogo
                .get("teams", {})
                .get("home", {})
                .get("name", ""),

            "Visitante":
                jogo
                .get("teams", {})
                .get("away", {})
                .get("name", ""),

            "Horário":
                jogo
                .get("fixture", {})
                .get("date", "")[11:16]

        })


    st.dataframe(
        pd.DataFrame(tabela),
        use_container_width=True,
        hide_index=True
    )


    if st.button(
        "🧠 ANALISAR TODOS OS JOGOS",
        use_container_width=True
    ):

        # O plano Free tem 100 requisições/dia.
        # Para evitar gastar a cota inteira de uma vez,
        # limitamos a análise inicial a 20 jogos.
        jogos_para_analisar = jogos[:20]


        with st.spinner(
            "🧠 Analisando forma, previsões e mercados..."
        ):

            resultados = analisar_jogos(
                jogos_para_analisar,
                api_key
            )


        st.session_state.resultados = resultados


# ============================================================
# RESULTADOS
# ============================================================

resultados = st.session_state.get(
    "resultados",
    []
)


if resultados:

    st.divider()

    st.header(
        "📊 RANKING DOS JOGOS"
    )


    resultados_ordenados = sorted(
        resultados,
        key=lambda x:
            x["confianca"],
        reverse=True
    )


    ranking = []


    for i, resultado in enumerate(
        resultados_ordenados,
        start=1
    ):

        ranking.append({

            "#":
                i,

            "Jogo":
                f"{resultado['home']} x {resultado['away']}",

            "Mercado":
                resultado["mercado"],

            "Probabilidade":
                f"{resultado['probabilidade'] * 100:.1f}%",

            "Odd":
                (
                    f"{resultado['odd']:.2f}"
                    if resultado["odd"] is not None
                    else "-"
                ),

            "Confiança":
                f"{resultado['confianca']:.1f}%"

        })


    st.dataframe(
        pd.DataFrame(ranking),
        use_container_width=True,
        hide_index=True
    )


    # ========================================================
    # ANÁLISE DETALHADA
    # ========================================================

    st.divider()

    st.header(
        "🔍 ANÁLISE DETALHADA"
    )


    for resultado in resultados_ordenados:

        with st.expander(
            f"⚽ {resultado['home']} x {resultado['away']}"
        ):

            col1, col2 = st.columns(2)


            with col1:

                st.subheader(
                    resultado["home"]
                )

                forma = resultado[
                    "forma_home"
                ]

                st.write(
                    f"Últimos jogos: {forma['jogos']}"
                )

                st.write(
                    f"Forma: {forma['forma'] or '-'}"
                )

                st.write(
                    f"Vitórias: {forma['vitorias']}"
                )

                st.write(
                    f"Empates: {forma['empates']}"
                )

                st.write(
                    f"Derrotas: {forma['derrotas']}"
                )

                st.write(
                    f"Média de gols: "
                    f"{forma['media_gols']:.2f}"
                )


            with col2:

                st.subheader(
                    resultado["away"]
                )

                forma = resultado[
                    "forma_away"
                ]

                st.write(
                    f"Últimos jogos: {forma['jogos']}"
                )

                st.write(
                    f"Forma: {forma['forma'] or '-'}"
                )

                st.write(
                    f"Vitórias: {forma['vitorias']}"
                )

                st.write(
                    f"Empates: {forma['empates']}"
                )

                st.write(
                    f"Derrotas: {forma['derrotas']}"
                )

                st.write(
                    f"Média de gols: "
                    f"{forma['media_gols']:.2f}"
                )


            st.divider()


            p = resultado[
                "probabilidades"
            ]


            st.subheader(
                "📈 Probabilidades calculadas"
            )


            prob_df = pd.DataFrame({

                "Mercado": [

                    "Vitória mandante",

                    "Empate",

                    "Vitória visitante",

                    "Dupla chance 1X",

                    "Dupla chance X2",

                    "Mais de 1.5 gols",

                    "Mandante marcar 1+",

                    "Visitante marcar 1+"
                ],

                "Probabilidade": [

                    f"{p['home'] * 100:.1f}%",

                    f"{p['draw'] * 100:.1f}%",

                    f"{p['away'] * 100:.1f}%",

                    f"{p['1x'] * 100:.1f}%",

                    f"{p['x2'] * 100:.1f}%",

                    f"{p['over15'] * 100:.1f}%",

                    f"{p['home_1plus'] * 100:.1f}%",

                    f"{p['away_1plus'] * 100:.1f}%"
                ]

            })


            st.dataframe(
                prob_df,
                use_container_width=True,
                hide_index=True
            )


            st.divider()


            st.subheader(
                "🎯 Mercado escolhido pelo sistema"
            )


            st.success(
                f"**{resultado['mercado']}**"
            )


            c1, c2, c3 = st.columns(3)


            with c1:

                st.metric(
                    "Probabilidade",
                    f"{resultado['probabilidade'] * 100:.1f}%"
                )


            with c2:

                if resultado["odd"] is not None:

                    st.metric(
                        "Odd",
                        f"{resultado['odd']:.2f}"
                    )

                else:

                    st.metric(
                        "Odd",
                        "Não encontrada"
                    )


            with c3:

                st.metric(
                    "Confiança",
                    f"{resultado['confianca']:.1f}%"
                )


# ============================================================
# MÚLTIPLAS
# ============================================================

if resultados:

    st.divider()

    st.header(
        "🎯 MÚLTIPLAS AUTOMÁTICAS"
    )


    col1, col2, col3 = st.columns(3)


    with col1:

        st.subheader(
            "🟢 Conservadora"
        )

        if st.button(
            "Montar odd ~5",
            key="odd5",
            use_container_width=True
        ):

            multipla = montar_multipla(
                resultados,
                5
            )

            st.session_state[
                "multipla5"
            ] = multipla


    with col2:

        st.subheader(
            "🟡 Moderada"
        )

        if st.button(
            "Montar odd ~10",
            key="odd10",
            use_container_width=True
        ):

            multipla = montar_multipla(
                resultados,
                10
            )

            st.session_state[
                "multipla10"
            ] = multipla


    with col3:

        st.subheader(
            "🔴 Agressiva"
        )

        if st.button(
            "Montar odd ~50",
            key="odd50",
            use_container_width=True
        ):

            multipla = montar_multipla(
                resultados,
                50
            )

            st.session_state[
                "multipla50"
            ] = multipla


    # ========================================================
    # MOSTRAR MÚLTIPLAS
    # ========================================================

    for chave, titulo in [
        ("multipla5", "🟢 Múltipla ~5"),
        ("multipla10", "🟡 Múltipla ~10"),
        ("multipla50", "🔴 Múltipla ~50")
    ]:

        multipla = st.session_state.get(
            chave
        )


        if multipla:

            st.subheader(
                titulo
            )


            for selecao in multipla[
                "selecoes"
            ]:

                st.write(
                    f"⚽ **{selecao['jogo']}**"
                )

                st.write(
                    f"Mercado: "
                    f"{selecao['mercado']} | "
                    f"Odd: {selecao['odd']:.2f} | "
                    f"Prob.: {selecao['prob'] * 100:.1f}%"
                )


            c1, c2 = st.columns(2)


            with c1:

                st.metric(
                    "Odd total",
                    f"{multipla['odd']:.2f}"
                )


            with c2:

                st.metric(
                    "Probabilidade matemática",
                    f"{multipla['probabilidade'] * 100:.2f}%"
                )


            st.divider()


# ============================================================
# AVISO
# ============================================================

st.caption(
    "⚠️ As probabilidades são estimativas estatísticas, "
    "não garantias de resultado."
)
