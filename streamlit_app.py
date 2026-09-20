import math
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


# ============================================================
# FUTBET PRO
# ============================================================

st.set_page_config(
    page_title="FUTBET PRO",
    page_icon="⚽",
    layout="wide",
)

API_URL = "https://v3.football.api-sports.io"

BRASILIA_TZ = ZoneInfo("America/Sao_Paulo")


# ============================================================
# LIGAS
# ============================================================

LEAGUES = {
    "🇧🇷 Brasileirão": 71,
    "🇬🇧 Premier League": 39,
    "🇪🇸 La Liga": 140,
    "🇮🇹 Serie A": 135,
    "🇩🇪 Bundesliga": 78,
    "🇫🇷 Ligue 1": 61,
    "🇵🇹 Liga Portugal": 94,
    "🇳🇱 Eredivisie": 88,
    "🇪🇺 Champions League": 2,
    "🇪🇺 Europa League": 3,
}


# ============================================================
# FUNÇÃO PARA CONSULTAR A API
# ============================================================

def api_get(endpoint, params, api_key):

    try:

        resposta = requests.get(
            f"{API_URL}/{endpoint}",
            headers={
                "x-apisports-key": api_key
            },
            params=params,
            timeout=25,
        )

        resposta.raise_for_status()

        dados = resposta.json()

        if dados.get("errors"):
            return None, dados["errors"]

        return dados.get("response", []), None

    except Exception as erro:

        return None, str(erro)


# ============================================================
# TÍTULO
# ============================================================

st.title("⚽ FUTBET PRO")

st.caption(
    "Análise automática de jogos de futebol"
)
# ============================================================
# BUSCAR JOGOS DO DIA
# ============================================================

@st.cache_data(ttl=900)
def buscar_jogos(data, ligas, temporada, api_key):

    jogos = []

    for liga_id in ligas:

        dados, erro = api_get(
            "fixtures",
            {
                "date": data,
                "league": liga_id,
                "season": temporada,
                "timezone": "America/Sao_Paulo",
            },
            api_key,
        )

        if erro or not dados:
            continue

        for jogo in dados:

            status = jogo["fixture"]["status"]["short"]

            # Ignora jogos que já terminaram
            if status not in ["NS", "TBD", "PST"]:
                continue

            jogos.append(
                {
                    "id": jogo["fixture"]["id"],

                    "liga": jogo["league"]["name"],

                    "pais": jogo["league"]["country"],

                    "casa_id": jogo["teams"]["home"]["id"],

                    "casa": jogo["teams"]["home"]["name"],

                    "fora_id": jogo["teams"]["away"]["id"],

                    "fora": jogo["teams"]["away"]["name"],

                    "horario": jogo["fixture"]["date"],
                }
            )

    # Remove jogos duplicados

    unicos = {}

    for jogo in jogos:
        unicos[jogo["id"]] = jogo

    return list(unicos.values())


# ============================================================
# CONFIGURAÇÃO DA API
# ============================================================

try:

    API_KEY = st.secrets["APIFOOTBALL_KEY"]

except Exception:

    API_KEY = st.text_input(
        "🔑 Digite sua API-Football Key",
        type="password",
    )


# ============================================================
# CONFIGURAÇÕES DO APP
# ============================================================

st.sidebar.header("⚙️ Configurações")

data_jogos = st.sidebar.date_input(
    "📅 Data dos jogos",
    value=datetime.now(BRASILIA_TZ).date(),
)


ligas_selecionadas = st.sidebar.multiselect(

    "🏆 Escolha as competições",

    list(LEAGUES.keys()),

    default=[
        "🇧🇷 Brasileirão",
        "🇬🇧 Premier League",
        "🇪🇸 La Liga",
        "🇮🇹 Serie A",
        "🇩🇪 Bundesliga",
        "🇵🇹 Liga Portugal",
        "🇳🇱 Eredivisie",
    ],
)


# ============================================================
# BOTÃO PARA PROCURAR OS JOGOS
# ============================================================

if st.sidebar.button(
    "🔎 PROCURAR JOGOS",
    use_container_width=True,
):

    if not API_KEY:

        st.error(
            "Digite sua API-Football Key primeiro."
        )

        st.stop()

    if not ligas_selecionadas:

        st.warning(
            "Escolha pelo menos uma competição."
        )

        st.stop()

    ids_ligas = [
        LEAGUES[nome]
        for nome in ligas_selecionadas
    ]

    with st.spinner(
        "🔎 Procurando os jogos..."
    ):

        jogos = buscar_jogos(
            data_jogos.isoformat(),
            ids_ligas,
            data_jogos.year,
            API_KEY,
        )

    st.session_state["jogos"] = jogos


# ============================================================
# MOSTRAR JOGOS ENCONTRADOS
# ============================================================

jogos = st.session_state.get(
    "jogos",
    []
)


if jogos:

    st.success(
        f"🔥 {len(jogos)} jogos encontrados!"
    )

    for jogo in jogos:

        st.write(
            f"⚽ **{jogo['casa']} x {jogo['fora']}**"
        )

        st.caption(
            f"{jogo['liga']} • "
            f"{jogo['horario'][11:16]}"
        )

        st.divider()

else:

    st.info(
        "Escolha as competições e clique em "
        "**PROCURAR JOGOS**."
    )
    # ============================================================
# ÚLTIMOS JOGOS DOS TIMES
# ============================================================

@st.cache_data(ttl=1800)
def buscar_ultimos_jogos(time_id, temporada, api_key, quantidade=5):

    dados, erro = api_get(
        "fixtures",
        {
            "team": time_id,
            "last": quantidade,
            "season": temporada,
            "timezone": "America/Sao_Paulo",
        },
        api_key,
    )

    if erro or not dados:
        return []

    resultados = []

    for jogo in dados:

        status = jogo["fixture"]["status"]["short"]

        if status not in ["FT", "AET", "PEN"]:
            continue

        gols_casa = jogo["goals"]["home"]
        gols_fora = jogo["goals"]["away"]

        resultados.append(
            {
                "id": jogo["fixture"]["id"],

                "casa_id": jogo["teams"]["home"]["id"],
                "casa": jogo["teams"]["home"]["name"],

                "fora_id": jogo["teams"]["away"]["id"],
                "fora": jogo["teams"]["away"]["name"],

                "gols_casa": gols_casa,
                "gols_fora": gols_fora,

                "data": jogo["fixture"]["date"],
            }
        )

    return resultados


# ============================================================
# CALCULAR FORMA RECENTE
# ============================================================

def calcular_forma(time_id, jogos):

    gols_marcados = []
    gols_sofridos = []

    vitorias = 0
    empates = 0
    derrotas = 0

    for jogo in jogos:

        if jogo["casa_id"] == time_id:

            marcados = jogo["gols_casa"]
            sofridos = jogo["gols_fora"]

        else:

            marcados = jogo["gols_fora"]
            sofridos = jogo["gols_casa"]

        gols_marcados.append(marcados)
        gols_sofridos.append(sofridos)

        if marcados > sofridos:

            vitorias += 1

        elif marcados == sofridos:

            empates += 1

        else:

            derrotas += 1


    quantidade = len(gols_marcados)

    if quantidade == 0:

        return {
            "media_marcados": 1.0,
            "media_sofridos": 1.0,
            "vitorias": 0,
            "empates": 0,
            "derrotas": 0,
            "jogos": 0,
        }


    return {

        "media_marcados":
            sum(gols_marcados) / quantidade,

        "media_sofridos":
            sum(gols_sofridos) / quantidade,

        "vitorias": vitorias,

        "empates": empates,

        "derrotas": derrotas,

        "jogos": quantidade,
    }


# ============================================================
# BUSCAR FORMA DOS DOIS TIMES
# ============================================================

@st.cache_data(ttl=1800)
def analisar_forma_jogo(
    casa_id,
    fora_id,
    temporada,
    api_key,
):

    jogos_casa = buscar_ultimos_jogos(
        casa_id,
        temporada,
        api_key,
        5,
    )

    jogos_fora = buscar_ultimos_jogos(
        fora_id,
        temporada,
        api_key,
        5,
    )

    forma_casa = calcular_forma(
        casa_id,
        jogos_casa,
    )

    forma_fora = calcular_forma(
        fora_id,
        jogos_fora,
    )

    return forma_casa, forma_fora
    # ============================================================
# MODELO DE POISSON
# ============================================================

def fatorial(n):

    return math.factorial(n)


def prob_poisson(gols, media):

    if media <= 0:
        return 0.0

    return (
        math.exp(-media)
        * (media ** gols)
        / fatorial(gols)
    )


# ============================================================
# PROBABILIDADES DE GOLS
# ============================================================

def probabilidades_jogo(forma_casa, forma_fora):

    # Média ofensiva e defensiva recente

    ataque_casa = forma_casa["media_marcados"]
    defesa_casa = forma_casa["media_sofridos"]

    ataque_fora = forma_fora["media_marcados"]
    defesa_fora = forma_fora["media_sofridos"]


    # Estimativa de gols esperados

    media_casa = (
        ataque_casa + defesa_fora
    ) / 2

    media_fora = (
        ataque_fora + defesa_casa
    ) / 2


    # Evita médias extremas

    media_casa = max(
        0.25,
        min(media_casa, 4.0)
    )

    media_fora = max(
        0.25,
        min(media_fora, 4.0)
    )


    # Matriz de probabilidades

    matriz = {}

    for gols_casa in range(0, 8):

        for gols_fora in range(0, 8):

            prob = (
                prob_poisson(
                    gols_casa,
                    media_casa
                )
                *
                prob_poisson(
                    gols_fora,
                    media_fora
                )
            )

            matriz[
                (gols_casa, gols_fora)
            ] = prob


    # ========================================================
    # RESULTADOS
    # ========================================================

    prob_casa = 0
    prob_empate = 0
    prob_fora = 0

    for (gc, gf), prob in matriz.items():

        if gc > gf:

            prob_casa += prob

        elif gc == gf:

            prob_empate += prob

        else:

            prob_fora += prob


    # ========================================================
    # MERCADOS
    # ========================================================

    prob_1x = (
        prob_casa
        +
        prob_empate
    )

    prob_x2 = (
        prob_empate
        +
        prob_fora
    )


    # Casa marca pelo menos 1

    prob_casa_gol = 1 - math.exp(
        -media_casa
    )


    # Fora marca pelo menos 1

    prob_fora_gol = 1 - math.exp(
        -media_fora
    )


    # Mais de 1.5 gols

    prob_mais_15 = 0

    for (gc, gf), prob in matriz.items():

        if gc + gf >= 2:

            prob_mais_15 += prob


    # Mais de 2.5 gols

    prob_mais_25 = 0

    for (gc, gf), prob in matriz.items():

        if gc + gf >= 3:

            prob_mais_25 += prob


    return {

        "media_casa": media_casa,

        "media_fora": media_fora,

        "casa": prob_casa,

        "empate": prob_empate,

        "fora": prob_fora,

        "1X": prob_1x,

        "X2": prob_x2,

        "casa_gol": prob_casa_gol,

        "fora_gol": prob_fora_gol,

        "mais_15": prob_mais_15,

        "mais_25": prob_mais_25,
                }
    # ============================================================
# PREVISÃO DA API-FOOTBALL
# ============================================================

@st.cache_data(ttl=1800)
def buscar_previsao(fixture_id, api_key):

    dados, erro = api_get(
        "predictions",
        {
            "fixture": fixture_id,
        },
        api_key,
    )

    if erro or not dados:
        return None

    try:

        previsao = dados[0]["predictions"]

        porcentagens = previsao.get(
            "percent",
            {}
        )

        vencedor = previsao.get(
            "winner",
            {}
        )

        dupla_chance = previsao.get(
            "under_over",
            None
        )

        conselho = previsao.get(
            "advice",
            ""
        )


        # ====================================================
        # PORCENTAGENS DA API
        # ====================================================

        casa = porcentagens.get(
            "home",
            "0%"
        )

        empate = porcentagens.get(
            "draw",
            "0%"
        )

        fora = porcentagens.get(
            "away",
            "0%"
        )


        def converter_percentual(valor):

            try:

                if isinstance(valor, str):

                    valor = (
                        valor
                        .replace("%", "")
                        .replace(",", ".")
                        .strip()
                    )

                return float(valor) / 100

            except Exception:

                return 0.0


        return {

            "casa":
                converter_percentual(casa),

            "empate":
                converter_percentual(empate),

            "fora":
                converter_percentual(fora),

            "vencedor":
                vencedor,

            "dupla_chance":
                dupla_chance,

            "conselho":
                conselho,
        }

    except Exception:

        return None


# ============================================================
# COMBINAR NOSSO MODELO + API
# ============================================================

def combinar_probabilidades(
    modelo,
    previsao_api,
):

    if not previsao_api:

        return modelo


    # ========================================================
    # PESOS
    # ========================================================
    #
    # 60% = nosso modelo matemático
    # 40% = previsão da API
    #

    peso_modelo = 0.60
    peso_api = 0.40


    casa = (
        modelo["casa"] * peso_modelo
        +
        previsao_api["casa"] * peso_api
    )

    empate = (
        modelo["empate"] * peso_modelo
        +
        previsao_api["empate"] * peso_api
    )

    fora = (
        modelo["fora"] * peso_modelo
        +
        previsao_api["fora"] * peso_api
    )


    # ========================================================
    # DUPLA CHANCE
    # ========================================================

    prob_1x = casa + empate

    prob_x2 = empate + fora


    return {

        **modelo,

        "casa": casa,

        "empate": empate,

        "fora": fora,

        "1X": prob_1x,

        "X2": prob_x2,
# ============================================================
# BUSCAR ODDS DA PARTIDA
# ============================================================

@st.cache_data(ttl=900)
def buscar_odds(fixture_id, api_key):

    dados, erro = api_get(
        "odds",
        {
            "fixture": fixture_id,
        },
        api_key,
    )

    if erro or not dados:
        return {}

    mercados = {}

    try:

        bookmakers = dados[0].get(
            "bookmakers",
            []
        )

        if not bookmakers:
            return {}

        # Usa a primeira casa disponível
        bookmaker = bookmakers[0]

        for mercado in bookmaker.get(
            "bets",
            []
        ):

            nome_mercado = mercado.get(
                "name",
                ""
            )

            valores = mercado.get(
                "values",
                []
            )

            if not valores:
                continue

            mercados[nome_mercado] = valores

    except Exception:

        return {}

    return mercados


# ============================================================
# CONVERTER ODDS PARA PROBABILIDADE IMPLÍCITA
# ============================================================

def odd_para_probabilidade(odd):

    try:

        odd = float(odd)

        if odd <= 1:
            return 0.0

        return 1 / odd

    except Exception:

        return 0.0


# ============================================================
# ENCONTRAR ODDS DE UM MERCADO
# ============================================================

def encontrar_odd(mercados, nomes, valor_procurado=None):

    for nome in nomes:

        valores = mercados.get(nome)

        if not valores:
            continue

        for item in valores:

            valor = str(
                item.get("value", "")
            )

            if (
                valor_procurado is None
                or valor == str(valor_procurado)
            ):

                try:

                    odd = float(
                        item.get("odd", 0)
                    )

                    if odd > 1:

                        return odd

                except Exception:

                    pass

    return None


# ============================================================
# EXTRAIR PRINCIPAIS MERCADOS
# ============================================================

def extrair_mercados_odds(
    mercados,
    casa,
    fora,
):

    resultado = {}


    # ========================================================
    # VITÓRIA DA CASA
    # ========================================================

    resultado["casa"] = encontrar_odd(
        mercados,
        [
            "Match Winner",
            "Fulltime Result",
        ],
        "Home",
    )


    # ========================================================
    # EMPATE
    # ========================================================

    resultado["empate"] = encontrar_odd(
        mercados,
        [
            "Match Winner",
            "Fulltime Result",
        ],
        "Draw",
    )


    # ========================================================
    # VITÓRIA DO TIME DE FORA
    # ========================================================

    resultado["fora"] = encontrar_odd(
        mercados,
        [
            "Match Winner",
            "Fulltime Result",
        ],
        "Away",
    )


    # ========================================================
    # MAIS DE 1.5 GOLS
    # ========================================================

    resultado["mais_15"] = encontrar_odd(
        mercados,
        [
            "Goals Over/Under",
            "Over/Under",
        ],
        "Over 1.5",
    )


    # ========================================================
    # MAIS DE 2.5 GOLS
    # ========================================================

    resultado["mais_25"] = encontrar_odd(
        mercados,
        [
            "Goals Over/Under",
            "Over/Under",
        ],
        "Over 2.5",
    )


    # ========================================================
    # DUPLA CHANCE 1X
    # ========================================================

    resultado["1X"] = encontrar_odd(
        mercados,
        [
            "Double Chance",
        ],
        "Home/Draw",
    )


    # ========================================================
    # DUPLA CHANCE X2
    # ========================================================

    resultado["X2"] = encontrar_odd(
        mercados,
        [
            "Double Chance",
        ],
        "Draw/Away",
    )


    return resultado
    # ============================================================
# ESCOLHER O MELHOR MERCADO
# ============================================================

def escolher_melhor_mercado(
    probabilidades,
    odds,
    casa,
    fora,
):

    mercados = []


    # ========================================================
    # DUPLA CHANCE 1X
    # ========================================================

    if odds.get("1X"):

        prob = probabilidades["1X"]

        odd = odds["1X"]

        mercados.append(
            {
                "mercado": "1X",
                "descricao": f"{casa} ou empate",
                "probabilidade": prob,
                "odd": odd,
            }
        )


    # ========================================================
    # DUPLA CHANCE X2
    # ========================================================

    if odds.get("X2"):

        prob = probabilidades["X2"]

        odd = odds["X2"]

        mercados.append(
            {
                "mercado": "X2",
                "descricao": f"Empate ou {fora}",
                "probabilidade": prob,
                "odd": odd,
            }
        )


    # ========================================================
    # CASA MARCA 1+
    # ========================================================

    if odds.get("casa_gol"):

        prob = probabilidades["casa_gol"]

        odd = odds["casa_gol"]

        mercados.append(
            {
                "mercado": "CASA_GOL",
                "descricao": f"{casa} marca 1+ gol",
                "probabilidade": prob,
                "odd": odd,
            }
        )


    # ========================================================
    # FORA MARCA 1+
    # ========================================================

    if odds.get("fora_gol"):

        prob = probabilidades["fora_gol"]

        odd = odds["fora_gol"]

        mercados.append(
            {
                "mercado": "FORA_GOL",
                "descricao": f"{fora} marca 1+ gol",
                "probabilidade": prob,
                "odd": odd,
            }
        )


    # ========================================================
    # MAIS DE 1.5 GOLS
    # ========================================================

    if odds.get("mais_15"):

        prob = probabilidades["mais_15"]

        odd = odds["mais_15"]

        mercados.append(
            {
                "mercado": "OVER_15",
                "descricao": "Mais de 1.5 gols",
                "probabilidade": prob,
                "odd": odd,
            }
        )


    # ========================================================
    # MAIS DE 2.5 GOLS
    # ========================================================

    if odds.get("mais_25"):

        prob = probabilidades["mais_25"]

        odd = odds["mais_25"]

        mercados.append(
            {
                "mercado": "OVER_25",
                "descricao": "Mais de 2.5 gols",
                "probabilidade": prob,
                "odd": odd,
            }
        )


    # ========================================================
    # VITÓRIA DA CASA
    # ========================================================

    if odds.get("casa"):

        prob = probabilidades["casa"]

        # Só considera vitória simples
        # quando a probabilidade estimada
        # for de pelo menos 62%.

        if prob >= 0.62:

            odd = odds["casa"]

            mercados.append(
                {
                    "mercado": "CASA",
                    "descricao": f"Vitória {casa}",
                    "probabilidade": prob,
                    "odd": odd,
                }
            )


    # ========================================================
    # VITÓRIA DO VISITANTE
    # ========================================================

    if odds.get("fora"):

        prob = probabilidades["fora"]

        if prob >= 0.62:

            odd = odds["fora"]

            mercados.append(
                {
                    "mercado": "FORA",
                    "descricao": f"Vitória {fora}",
                    "probabilidade": prob,
                    "odd": odd,
                }
            )


    # ========================================================
    # REMOVER MERCADOS INVÁLIDOS
    # ========================================================

    mercados_validos = []

    for mercado in mercados:

        if (
            mercado["odd"] > 1
            and mercado["probabilidade"] > 0
        ):

            mercados_validos.append(
                mercado
            )


    if not mercados_validos:

        return None


    # ========================================================
    # PONTUAÇÃO
    # ========================================================
    #
    # A ideia é procurar mercados que tenham:
    #
    # • alta probabilidade
    # • odd razoável
    #
    # Não basta simplesmente pegar a maior odd.
    #

    for mercado in mercados_validos:

        prob = mercado["probabilidade"]

        odd = mercado["odd"]

        mercado["valor_modelo"] = (
            prob * odd
        )


    # ========================================================
    # PRIMEIRO PRIORIZAMOS PROBABILIDADE
    # ========================================================

    mercados_validos.sort(
        key=lambda x: (
            x["probabilidade"],
            x["valor_modelo"],
        ),
        reverse=True,
    )


    melhor = mercados_validos[0]

    return melhor
    # ============================================================
# ANALISAR TODOS OS JOGOS
# ============================================================

def analisar_todos_os_jogos(
    jogos,
    api_key,
):

    resultados = []

    for jogo in jogos:

        try:

            # =================================================
            # FORMA RECENTE
            # =================================================

            forma_casa, forma_fora = analisar_forma_jogo(
                jogo["casa_id"],
                jogo["fora_id"],
                datetime.now(BRASILIA_TZ).year,
                api_key,
            )


            # =================================================
            # MODELO MATEMÁTICO
            # =================================================

            probabilidades = probabilidades_jogo(
                forma_casa,
                forma_fora,
            )


            # =================================================
            # PREVISÃO DA API
            # =================================================

            previsao_api = buscar_previsao(
                jogo["id"],
                api_key,
            )


            probabilidades = combinar_probabilidades(
                probabilidades,
                previsao_api,
            )


            # =================================================
            # ODDS
            # =================================================

            mercados_odds = buscar_odds(
                jogo["id"],
                api_key,
            )


            odds = extrair_mercados_odds(
                mercados_odds,
                jogo["casa"],
                jogo["fora"],
            )


            # =================================================
            # ESCOLHER MELHOR MERCADO
            # =================================================

            melhor = escolher_melhor_mercado(
                probabilidades,
                odds,
                jogo["casa"],
                jogo["fora"],
            )


            # =================================================
            # SE NÃO ENCONTROU MERCADO
            # =================================================

            if not melhor:

                continue


            # =================================================
            # SALVAR RESULTADO
            # =================================================

            resultados.append(
                {
                    "id": jogo["id"],

                    "liga": jogo["liga"],

                    "casa": jogo["casa"],

                    "fora": jogo["fora"],

                    "horario": jogo["horario"],

                    "mercado": melhor["mercado"],

                    "descricao": melhor["descricao"],

                    "probabilidade":
                        melhor["probabilidade"],

                    "odd":
                        melhor["odd"],

                    "valor_modelo":
                        melhor["valor_modelo"],

                    "forma_casa":
                        forma_casa,

                    "forma_fora":
                        forma_fora,

                    "probabilidades":
                        probabilidades,

                    "odds":
                        odds,

                    "previsao_api":
                        previsao_api,
                }
            )


        except Exception as erro:

            # Se um jogo apresentar algum
            # problema, continua analisando
            # os demais.

            continue


    # ========================================================
    # ORDENAR POR PROBABILIDADE
    # ========================================================

    resultados.sort(
        key=lambda x: (
            x["probabilidade"],
            x["valor_modelo"],
        ),
        reverse=True,
    )


    return resultados


# ============================================================
# BOTÃO DE ANÁLISE AUTOMÁTICA
# ============================================================

if jogos and API_KEY:

    st.sidebar.divider()

    if st.sidebar.button(
        "🧠 ANALISAR JOGOS",
        use_container_width=True,
    ):

        with st.spinner(
            "🧠 Analisando forma, probabilidades e mercados..."
        ):

            analises = analisar_todos_os_jogos(
                jogos,
                API_KEY,
            )

        st.session_state["analises"] = analises


# ============================================================
# RECUPERAR ANÁLISES
# ============================================================

analises = st.session_state.get(
    "analises",
    []
)
# ============================================================
# RANKING DOS MELHORES JOGOS
# ============================================================

if analises:

    st.header("🏆 Melhores oportunidades do dia")

    st.caption(
        "Ranking baseado nas probabilidades calculadas pelo modelo "
        "e nos dados disponíveis da API."
    )

    for posicao, analise in enumerate(
        analises,
        start=1
    ):

        prob = analise["probabilidade"]

        odd = analise["odd"]

        st.subheader(
            f"#{posicao} ⚽ "
            f"{analise['casa']} x {analise['fora']}"
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.metric(
                "Mercado",
                analise["descricao"],
            )

        with col2:

            st.metric(
                "Odd",
                f"{odd:.2f}",
            )

        with col3:

            st.metric(
                "Probabilidade",
                f"{prob * 100:.1f}%",
            )

        with col4:

            st.metric(
                "Valor do modelo",
                f"{analise['valor_modelo']:.2f}",
            )


        st.caption(
            f"🏆 {analise['liga']} • "
            f"🕐 {analise['horario'][11:16]}"
        )


        # ====================================================
        # FORMA RECENTE
        # ====================================================

        with st.expander(
            "📊 Ver análise detalhada"
        ):

            forma_casa = analise[
                "forma_casa"
            ]

            forma_fora = analise[
                "forma_fora"
            ]


            col_a, col_b = st.columns(2)


            with col_a:

                st.markdown(
                    f"### 🏠 {analise['casa']}"
                )

                st.write(
                    f"Jogos analisados: "
                    f"{forma_casa['jogos']}"
                )

                st.write(
                    f"Vitórias: "
                    f"{forma_casa['vitorias']}"
                )

                st.write(
                    f"Empates: "
                    f"{forma_casa['empates']}"
                )

                st.write(
                    f"Derrotas: "
                    f"{forma_casa['derrotas']}"
                )

                st.write(
                    f"Gols marcados por jogo: "
                    f"{forma_casa['media_marcados']:.2f}"
                )

                st.write(
                    f"Gols sofridos por jogo: "
                    f"{forma_casa['media_sofridos']:.2f}"
                )


            with col_b:

                st.markdown(
                    f"### ✈️ {analise['fora']}"
                )

                st.write(
                    f"Jogos analisados: "
                    f"{forma_fora['jogos']}"
                )

                st.write(
                    f"Vitórias: "
                    f"{forma_fora['vitorias']}"
                )

                st.write(
                    f"Empates: "
                    f"{forma_fora['empates']}"
                )

                st.write(
                    f"Derrotas: "
                    f"{forma_fora['derrotas']}"
                )

                st.write(
                    f"Gols marcados por jogo: "
                    f"{forma_fora['media_marcados']:.2f}"
                )

                st.write(
                    f"Gols sofridos por jogo: "
                    f"{forma_fora['media_sofridos']:.2f}"
                )


            # =================================================
            # PROBABILIDADES
            # =================================================

            st.markdown(
                "### 📈 Probabilidades do modelo"
            )

            probabilidades = analise[
                "probabilidades"
            ]

            tabela_probabilidades = pd.DataFrame(
                [
                    {
                        "Mercado": "Vitória casa",
                        "Probabilidade":
                            f"{probabilidades['casa'] * 100:.1f}%",
                    },
                    {
                        "Mercado": "Empate",
                        "Probabilidade":
                            f"{probabilidades['empate'] * 100:.1f}%",
                    },
                    {
                        "Mercado": "Vitória fora",
                        "Probabilidade":
                            f"{probabilidades['fora'] * 100:.1f}%",
                    },
                    {
                        "Mercado": "Casa ou empate (1X)",
                        "Probabilidade":
                            f"{probabilidades['1X'] * 100:.1f}%",
                    },
                    {
                        "Mercado": "Empate ou fora (X2)",
                        "Probabilidade":
                            f"{probabilidades['X2'] * 100:.1f}%",
                    },
                    {
                        "Mercado": "Casa marca 1+",
                        "Probabilidade":
                            f"{probabilidades['casa_gol'] * 100:.1f}%",
                    },
                    {
                        "Mercado": "Fora marca 1+",
                        "Probabilidade":
                            f"{probabilidades['fora_gol'] * 100:.1f}%",
                    },
                    {
                        "Mercado": "Mais de 1.5 gols",
                        "Probabilidade":
                            f"{probabilidades['mais_15'] * 100:.1f}%",
                    },
                    {
                        "Mercado": "Mais de 2.5 gols",
                        "Probabilidade":
                            f"{probabilidades['mais_25'] * 100:.1f}%",
                    },
                ]
            )

            st.dataframe(
                tabela_probabilidades,
                use_container_width=True,
                hide_index=True,
            )


        st.divider()
        # ============================================================
# GERAR MÚLTIPLAS AUTOMATICAMENTE
# ============================================================

def calcular_odd_multipla(selecoes):

    odd_total = 1.0

    for selecao in selecoes:

        odd_total *= selecao["odd"]

    return odd_total


def calcular_probabilidade_multipla(selecoes):

    probabilidade = 1.0

    for selecao in selecoes:

        probabilidade *= selecao["probabilidade"]

    return probabilidade


# ============================================================
# GERAR OPÇÕES DE MERCADO PARA CADA JOGO
# ============================================================

def gerar_opcoes_jogo(analise):

    probabilidades = analise["probabilidades"]
    odds = analise["odds"]

    opcoes = []


    mercados = [
        ("1X", "1X", probabilidades["1X"]),
        ("X2", "X2", probabilidades["X2"]),
        (
            "CASA_GOL",
            f"{analise['casa']} marca 1+ gol",
            probabilidades["casa_gol"],
        ),
        (
            "FORA_GOL",
            f"{analise['fora']} marca 1+ gol",
            probabilidades["fora_gol"],
        ),
        (
            "OVER_15",
            "Mais de 1.5 gols",
            probabilidades["mais_15"],
        ),
        (
            "OVER_25",
            "Mais de 2.5 gols",
            probabilidades["mais_25"],
        ),
        (
            "CASA",
            f"Vitória {analise['casa']}",
            probabilidades["casa"],
        ),
        (
            "FORA",
            f"Vitória {analise['fora']}",
            probabilidades["fora"],
        ),
    ]


    for codigo, descricao, probabilidade in mercados:

        odd = odds.get(codigo)

        if not odd:
            continue

        if odd <= 1:
            continue

        # Evita mercados muito improváveis
        if probabilidade < 0.55:
            continue

        opcoes.append(
            {
                "jogo_id": analise["id"],

                "jogo":
                    f"{analise['casa']} x {analise['fora']}",

                "mercado": codigo,

                "descricao": descricao,

                "odd": odd,

                "probabilidade": probabilidade,
            }
        )


    # Maior probabilidade primeiro

    opcoes.sort(
        key=lambda x: x["probabilidade"],
        reverse=True,
    )

    return opcoes


# ============================================================
# MONTAR UMA MÚLTIPLA
# ============================================================

def montar_multipla(
    analises,
    odd_min,
    odd_max,
    max_selecoes=8,
):

    todas_opcoes = []

    for analise in analises:

        opcoes = gerar_opcoes_jogo(
            analise
        )

        if not opcoes:
            continue

        # Pega somente as melhores opções
        # daquele jogo.

        todas_opcoes.extend(
            opcoes[:3]
        )


    # Ordena pela maior probabilidade

    todas_opcoes.sort(
        key=lambda x: x["probabilidade"],
        reverse=True,
    )


    selecoes = []

    jogos_usados = set()


    # ========================================================
    # PRIMEIRA ETAPA
    # ========================================================

    for opcao in todas_opcoes:

        if len(selecoes) >= max_selecoes:
            break

        if opcao["jogo_id"] in jogos_usados:
            continue

        odd_atual = calcular_odd_multipla(
            selecoes
        )

        nova_odd = (
            odd_atual * opcao["odd"]
        )


        if nova_odd <= odd_max:

            selecoes.append(opcao)

            jogos_usados.add(
                opcao["jogo_id"]
            )


    # ========================================================
    # SEGUNDA ETAPA
    # ========================================================
    #
    # Se ainda não alcançou a odd mínima,
    # procura outras opções.
    #

    for opcao in todas_opcoes:

        if len(selecoes) >= max_selecoes:
            break

        if opcao["jogo_id"] in jogos_usados:
            continue

        odd_atual = calcular_odd_multipla(
            selecoes
        )

        nova_odd = (
            odd_atual * opcao["odd"]
        )

        if nova_odd <= odd_max:

            selecoes.append(opcao)

            jogos_usados.add(
                opcao["jogo_id"]
            )

        if (
            calcular_odd_multipla(selecoes)
            >= odd_min
        ):

            break


    odd_final = calcular_odd_multipla(
        selecoes
    )

    prob_final = calcular_probabilidade_multipla(
        selecoes
    )


    return {
        "selecoes": selecoes,
        "odd": odd_final,
        "probabilidade": prob_final,
    }


# ============================================================
# GERAR AS 3 MÚLTIPLAS
# ============================================================

if analises:

    st.header(
        "🎯 Múltiplas automáticas"
    )


    multipla_1_5 = montar_multipla(
        analises,
        1.0,
        5.0,
        6,
    )


    multipla_10 = montar_multipla(
        analises,
        8.0,
        12.0,
        8,
    )


    multipla_50 = montar_multipla(
        analises,
        40.0,
        60.0,
        12,
    )


    # ========================================================
    # FUNÇÃO PARA MOSTRAR MÚLTIPLA
    # ========================================================

    def mostrar_multipla(
        titulo,
        multipla,
    ):

        st.subheader(titulo)

        selecoes = multipla["selecoes"]


        if not selecoes:

            st.warning(
                "Não foi possível montar esta múltipla "
                "com os mercados disponíveis."
            )

            return


        st.metric(
            "Odd total",
            f"{multipla['odd']:.2f}",
        )

        st.metric(
            "Probabilidade conjunta estimada",
            f"{multipla['probabilidade'] * 100:.2f}%",
        )


        for numero, selecao in enumerate(
            selecoes,
            start=1,
        ):

            st.write(
                f"**{numero}. "
                f"{selecao['jogo']}**"
            )

            st.write(
                f"➡️ {selecao['descricao']} "
                f"• Odd {selecao['odd']:.2f} "
                f"• Prob. "
                f"{selecao['probabilidade'] * 100:.1f}%"
            )

            st.divider()


    # ========================================================
    # MOSTRAR
    # ========================================================

    mostrar_multipla(
        "🟢 Múltipla 1–5",
        multipla_1_5,
    )

    mostrar_multipla(
        "🟡 Múltipla próxima de 10",
        multipla_10,
    )

    mostrar_multipla(
        "🔴 Múltipla próxima de 50",
        multipla_50,
    )
# ============================================================
# RESUMO FINAL DO FUTBET PRO
# ============================================================

if analises:

    st.divider()

    st.header("📋 Resumo da análise")

    total_jogos = len(analises)

    media_probabilidades = (
        sum(
            analise["probabilidade"]
            for analise in analises
        )
        / total_jogos
    )

    maior_probabilidade = max(
        analises,
        key=lambda x: x["probabilidade"]
    )


    # ========================================================
    # INDICADORES
    # ========================================================

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "⚽ Jogos analisados",
            total_jogos,
        )

    with col2:

        st.metric(
            "📊 Probabilidade média",
            f"{media_probabilidades * 100:.1f}%",
        )

    with col3:

        st.metric(
            "🔥 Maior probabilidade",
            f"{maior_probabilidade['probabilidade'] * 100:.1f}%",
        )


    # ========================================================
    # MELHOR OPORTUNIDADE ENCONTRADA
    # ========================================================

    st.subheader(
        "🔥 Maior probabilidade encontrada"
    )

    st.write(
        f"### ⚽ {maior_probabilidade['casa']} "
        f"x {maior_probabilidade['fora']}"
    )

    st.write(
        f"**Mercado:** "
        f"{maior_probabilidade['descricao']}"
    )

    st.write(
        f"**Probabilidade estimada:** "
        f"{maior_probabilidade['probabilidade'] * 100:.1f}%"
    )

    st.write(
        f"**Odd encontrada:** "
        f"{maior_probabilidade['odd']:.2f}"
    )


    # ========================================================
    # AVISO
    # ========================================================

    st.info(
        "ℹ️ As probabilidades são estimativas matemáticas "
        "baseadas nos dados disponíveis. Elas não garantem "
        "o resultado de uma partida."
    )


# ============================================================
# RODAPÉ
# ============================================================

st.divider()

st.caption(
    "FUTBET PRO • Análise estatística de futebol"
)

    
    }
