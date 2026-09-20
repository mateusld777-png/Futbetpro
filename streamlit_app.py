import math
from datetime import datetime
from itertools import combinations
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
TZ = ZoneInfo("America/Sao_Paulo")


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
# API
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
# JOGOS DO DIA
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

            if status not in ["NS", "TBD"]:
                continue

            jogos.append(
                {
                    "id": jogo["fixture"]["id"],
                    "liga": jogo["league"]["name"],
                    "casa_id": jogo["teams"]["home"]["id"],
                    "casa": jogo["teams"]["home"]["name"],
                    "fora_id": jogo["teams"]["away"]["id"],
                    "fora": jogo["teams"]["away"]["name"],
                    "horario": jogo["fixture"]["date"],
                }
            )

    unicos = {}

    for jogo in jogos:
        unicos[jogo["id"]] = jogo

    return list(unicos.values())


# ============================================================
# ÚLTIMOS 5 JOGOS
# ============================================================

@st.cache_data(ttl=1800)
def buscar_ultimos_jogos(
    time_id,
    api_key,
):

    dados, erro = api_get(
        "fixtures",
        {
            "team": time_id,
            "last": 5,
            "timezone": "America/Sao_Paulo",
        },
        api_key,
    )

    if erro or not dados:
        return []

    jogos = []

    for jogo in dados:

        status = jogo["fixture"]["status"]["short"]

        if status not in ["FT", "AET", "PEN"]:
            continue

        jogos.append(
            {
                "casa_id":
                    jogo["teams"]["home"]["id"],

                "fora_id":
                    jogo["teams"]["away"]["id"],

                "gols_casa":
                    jogo["goals"]["home"],

                "gols_fora":
                    jogo["goals"]["away"],
            }
        )

    return jogos


def calcular_forma(time_id, jogos):

    marcados = []
    sofridos = []

    vitorias = 0
    empates = 0
    derrotas = 0

    for jogo in jogos:

        if jogo["casa_id"] == time_id:

            feitos = jogo["gols_casa"]
            recebidos = jogo["gols_fora"]

        else:

            feitos = jogo["gols_fora"]
            recebidos = jogo["gols_casa"]

        marcados.append(feitos)
        sofridos.append(recebidos)

        if feitos > recebidos:

            vitorias += 1

        elif feitos == recebidos:

            empates += 1

        else:

            derrotas += 1

    quantidade = len(marcados)

    if quantidade == 0:

        return {
            "marcados": 1.0,
            "sofridos": 1.0,
            "vitorias": 0,
            "empates": 0,
            "derrotas": 0,
            "jogos": 0,
        }

    return {
        "marcados":
            sum(marcados) / quantidade,

        "sofridos":
            sum(sofridos) / quantidade,

        "vitorias":
            vitorias,

        "empates":
            empates,

        "derrotas":
            derrotas,

        "jogos":
            quantidade,
    }


@st.cache_data(ttl=1800)
def analisar_forma(
    casa_id,
    fora_id,
    api_key,
):

    jogos_casa = buscar_ultimos_jogos(
        casa_id,
        api_key,
    )

    jogos_fora = buscar_ultimos_jogos(
        fora_id,
        api_key,
    )

    return (
        calcular_forma(
            casa_id,
            jogos_casa,
        ),
        calcular_forma(
            fora_id,
            jogos_fora,
        ),
    )


# ============================================================
# MODELO DE POISSON
# ============================================================

def poisson(gols, media):

    if media <= 0:
        return 0

    return (
        math.exp(-media)
        * media ** gols
        / math.factorial(gols)
    )


def calcular_probabilidades(
    forma_casa,
    forma_fora,
):

    media_casa = (
        forma_casa["marcados"]
        +
        forma_fora["sofridos"]
    ) / 2

    media_fora = (
        forma_fora["marcados"]
        +
        forma_casa["sofridos"]
    ) / 2

    media_casa = max(
        0.25,
        min(media_casa, 4),
    )

    media_fora = max(
        0.25,
        min(media_fora, 4),
    )

    matriz = {}

    for gc in range(8):

        for gf in range(8):

            matriz[(gc, gf)] = (
                poisson(
                    gc,
                    media_casa,
                )
                *
                poisson(
                    gf,
                    media_fora,
                )
            )

    casa = sum(
        p
        for (gc, gf), p in matriz.items()
        if gc > gf
    )

    empate = sum(
        p
        for (gc, gf), p in matriz.items()
        if gc == gf
    )

    fora = sum(
        p
        for (gc, gf), p in matriz.items()
        if gc < gf
    )

    return {

        "casa": casa,

        "empate": empate,

        "fora": fora,

        "1X":
            casa + empate,

        "X2":
            empate + fora,

        "casa_gol":
            1 - math.exp(-media_casa),

        "fora_gol":
            1 - math.exp(-media_fora),

        "over15":
            sum(
                p
                for (gc, gf), p in matriz.items()
                if gc + gf >= 2
            ),

        "over25":
            sum(
                p
                for (gc, gf), p in matriz.items()
                if gc + gf >= 3
            ),

        "media_casa":
            media_casa,

        "media_fora":
            media_fora,
    }


# ============================================================
# PREVISÕES DA API
# ============================================================

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

        return 0


@st.cache_data(ttl=1800)
def buscar_previsao(
    fixture_id,
    api_key,
):

    dados, erro = api_get(
        "predictions",
        {
            "fixture": fixture_id
        },
        api_key,
    )

    if erro or not dados:
        return None

    try:

        previsao = dados[0]["predictions"]

        percent = previsao.get(
            "percent",
            {},
        )

        return {

            "casa":
                converter_percentual(
                    percent.get("home", 0)
                ),

            "empate":
                converter_percentual(
                    percent.get("draw", 0)
                ),

            "fora":
                converter_percentual(
                    percent.get("away", 0)
                ),

        }

    except Exception:

        return None


def combinar_modelos(
    modelo,
    previsao,
):

    if not previsao:
        return modelo

    casa = (
        modelo["casa"] * 0.60
        +
        previsao["casa"] * 0.40
    )

    empate = (
        modelo["empate"] * 0.60
        +
        previsao["empate"] * 0.40
    )

    fora = (
        modelo["fora"] * 0.60
        +
        previsao["fora"] * 0.40
    )

    modelo["casa"] = casa
    modelo["empate"] = empate
    modelo["fora"] = fora
    modelo["1X"] = casa + empate
    modelo["X2"] = empate + fora

    return modelo


# ============================================================
# ODDS
# ============================================================

@st.cache_data(ttl=900)
def buscar_odds(
    fixture_id,
    api_key,
):

    dados, erro = api_get(
        "odds",
        {
            "fixture": fixture_id
        },
        api_key,
    )

    if erro or not dados:
        return {}

    try:

        bookmakers = dados[0].get(
            "bookmakers",
            [],
        )

        if not bookmakers:
            return {}

        mercados = {}

        for bookmaker in bookmakers[:3]:

            for mercado in bookmaker.get(
                "bets",
                [],
            ):

                nome = mercado.get(
                    "name",
                    "",
                )

                valores = mercado.get(
                    "values",
                    [],
                )

                if valores and nome not in mercados:

                    mercados[nome] = valores

        return mercados

    except Exception:

        return {}


def procurar_odd(
    mercados,
    nomes,
    valores_procurados,
):

    for nome in nomes:

        valores = mercados.get(
            nome,
            [],
        )

        for item in valores:

            valor = str(
                item.get(
                    "value",
                    "",
                )
            ).strip()

            for procurado in valores_procurados:

                if valor.lower() == procurado.lower():

                    try:

                        odd = float(
                            item.get(
                                "odd",
                                0,
                            )
                        )

                        if odd > 1:
                            return odd

                    except Exception:
                        pass

    return None


def extrair_odds(mercados):

    return {

        "casa":
            procurar_odd(
                mercados,
                [
                    "Match Winner",
                    "Fulltime Result",
                ],
                [
                    "Home",
                    "1",
                ],
            ),

        "empate":
            procurar_odd(
                mercados,
                [
                    "Match Winner",
                    "Fulltime Result",
                ],
                [
                    "Draw",
                    "X",
                ],
            ),

        "fora":
            procurar_odd(
                mercados,
                [
                    "Match Winner",
                    "Fulltime Result",
                ],
                [
                    "Away",
                    "2",
                ],
            ),

        "1X":
            procurar_odd(
                mercados,
                [
                    "Double Chance",
                ],
                [
                    "Home/Draw",
                    "1X",
                ],
            ),

        "X2":
            procurar_odd(
                mercados,
                [
                    "Double Chance",
                ],
                [
                    "Draw/Away",
                    "X2",
                ],
            ),

        "over15":
            procurar_odd(
                mercados,
                [
                    "Goals Over/Under",
                    "Over/Under",
                ],
                [
                    "Over 1.5",
                ],
            ),

        "over25":
            procurar_odd(
                mercados,
                [
                    "Goals Over/Under",
                    "Over/Under",
                ],
                [
                    "Over 2.5",
                ],
            ),
    }


# ============================================================
# ESCOLHER MERCADO
# ============================================================

def escolher_mercado(
    probabilidades,
    odds,
    casa,
    fora,
):

    candidatos = []

    mercados = [

        (
            "1X",
            f"{casa} ou empate",
            "1X",
        ),

        (
            "X2",
            f"Empate ou {fora}",
            "X2",
        ),

        (
            "OVER15",
            "Mais de 1.5 gols",
            "over15",
        ),

        (
            "OVER25",
            "Mais de 2.5 gols",
            "over25",
        ),

        (
            "CASA",
            f"Vitória {casa}",
            "casa",
        ),

        (
            "FORA",
            f"Vitória {fora}",
            "fora",
        ),
    ]

    for codigo, descricao, chave in mercados:

        odd = odds.get(codigo.lower())

        if odd is None:
            odd = odds.get(chave)

        prob = probabilidades.get(
            chave,
            0,
        )

        if not odd:
            continue

        if prob < 0.55:
            continue

        if (
            codigo in ["CASA", "FORA"]
            and prob < 0.62
        ):
            continue

        candidatos.append(
            {
                "codigo": codigo,
                "descricao": descricao,
                "probabilidade": prob,
                "odd": odd,
                "valor": prob * odd,
            }
        )

    if not candidatos:
        return None

    candidatos.sort(
        key=lambda x: (
            x["probabilidade"],
            x["valor"],
        ),
        reverse=True,
    )

    return candidatos[0]


# ============================================================
# ANALISAR JOGOS
# ============================================================

def analisar_jogos(
    jogos,
    api_key,
):

    resultados = []

    for jogo in jogos:

        try:

            forma_casa, forma_fora = analisar_forma(
                jogo["casa_id"],
                jogo["fora_id"],
                api_key,
            )

            probabilidades = calcular_probabilidades(
                forma_casa,
                forma_fora,
            )

            previsao = buscar_previsao(
                jogo["id"],
                api_key,
            )

            probabilidades = combinar_modelos(
                probabilidades,
                previsao,
            )

            mercados_api = buscar_odds(
                jogo["id"],
                api_key,
            )

            odds = extrair_odds(
                mercados_api
            )

            melhor = escolher_mercado(
                probabilidades,
                odds,
                jogo["casa"],
                jogo["fora"],
            )

            if not melhor:
                continue

            resultados.append(
                {
                    **jogo,

                    "descricao":
                        melhor["descricao"],

                    "codigo":
                        melhor["codigo"],

                    "probabilidade":
                        melhor["probabilidade"],

                    "odd":
                        melhor["odd"],

                    "valor":
                        melhor["valor"],

                    "forma_casa":
                        forma_casa,

                    "forma_fora":
                        forma_fora,

                    "probabilidades":
                        probabilidades,

                    "odds":
                        odds,
                }
            )

        except Exception:

            continue

    resultados.sort(
        key=lambda x: (
            x["probabilidade"],
            x["valor"],
        ),
        reverse=True,
    )

    return resultados


# ============================================================
# OPÇÕES PARA MÚLTIPLAS
# ============================================================

def opcoes_do_jogo(analise):

    p = analise["probabilidades"]
    o = analise["odds"]

    lista = [

        (
            "1X",
            f"{analise['casa']} ou empate",
            p["1X"],
            o.get("1X"),
        ),

        (
            "X2",
            f"Empate ou {analise['fora']}",
            p["X2"],
            o.get("X2"),
        ),

        (
            "OVER15",
            "Mais de 1.5 gols",
            p["over15"],
            o.get("over15"),
        ),

        (
            "OVER25",
            "Mais de 2.5 gols",
            p["over25"],
            o.get("over25"),
        ),

        (
            "CASA",
            f"Vitória {analise['casa']}",
            p["casa"],
            o.get("casa"),
        ),

        (
            "FORA",
            f"Vitória {analise['fora']}",
            p["fora"],
            o.get("fora"),
        ),
    ]

    resultado = []

    for codigo, descricao, prob, odd in lista:

        if not odd:
            continue

        if prob < 0.55:
            continue

        if (
            codigo in ["CASA", "FORA"]
            and prob < 0.62
        ):
            continue

        resultado.append(
            {
                "jogo_id":
                    analise["id"],

                "jogo":
                    f"{analise['casa']} x {analise['fora']}",

                "descricao":
                    descricao,

                "odd":
                    odd,

                "probabilidade":
                    prob,
            }
        )

    resultado.sort(
        key=lambda x: x["probabilidade"],
        reverse=True,
    )

    return resultado[:3]


def odd_multipla(selecoes):

    total = 1

    for selecao in selecoes:
        total *= selecao["odd"]

    return total


def prob_multipla(selecoes):

    total = 1

    for selecao in selecoes:
        total *= selecao["probabilidade"]

    return total


def montar_multipla(
    analises,
    minimo,
    maximo,
    limite,
):

    opcoes = []

    for analise in analises:

        melhores = opcoes_do_jogo(
            analise
        )

        if melhores:
            opcoes.append(
                melhores[0]
            )

    if len(opcoes) < 2:

        return {
            "selecoes": [],
            "odd": 0,
            "probabilidade": 0,
        }

    opcoes.sort(
        key=lambda x: x["probabilidade"],
        reverse=True,
    )

    base = opcoes[
        :min(12, len(opcoes))
    ]

    possibilidades = []

    for quantidade in range(
        2,
        min(limite, len(base)) + 1,
    ):

        for combo in combinations(
            base,
            quantidade,
        ):

            odd = odd_multipla(
                combo
            )

            if minimo <= odd <= maximo:

                possibilidades.append(
                    {
                        "selecoes":
                            list(combo),

                        "odd":
                            odd,

                        "probabilidade":
                            prob_multipla(combo),
                    }
                )

    if possibilidades:

        possibilidades.sort(
            key=lambda x: (
                -x["probabilidade"],
                abs(
                    x["odd"]
                    -
                    ((minimo + maximo) / 2)
                ),
            )
        )

        return possibilidades[0]

    return {
        "selecoes": [],
        "odd": 0,
        "probabilidade": 0,
    }


# ============================================================
# INTERFACE
# ============================================================

st.title("⚽ FUTBET PRO")

st.caption(
    "Análise automática de jogos, mercados e múltiplas"
)


st.sidebar.header(
    "⚙️ Configurações"
)


API_KEY = st.sidebar.text_input(
    "🔑 API-Football Key",
    type="password",
)


DATA = st.sidebar.date_input(
    "📅 Data dos jogos",
    value=datetime.now(TZ).date(),
)


LIGAS = st.sidebar.multiselect(
    "🏆 Competições",
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


if st.sidebar.button(
    "🔎 PROCURAR JOGOS",
    use_container_width=True,
):

    if not API_KEY:

        st.error(
            "Digite sua API-Football Key."
        )

        st.stop()

    if not LIGAS:

        st.warning(
            "Escolha pelo menos uma competição."
        )

        st.stop()

    ids = [
        LEAGUES[nome]
        for nome in LIGAS
    ]

    with st.spinner(
        "🔎 Procurando jogos..."
    ):

        jogos = buscar_jogos(
            DATA.isoformat(),
            ids,
            DATA.year,
            API_KEY,
        )

    st.session_state["jogos"] = jogos

    st.session_state.pop(
        "analises",
        None,
    )


jogos = st.session_state.get(
    "jogos",
    [],
)


if jogos:

    st.success(
        f"🔥 {len(jogos)} jogos encontrados!"
    )

    tabela = pd.DataFrame(
        [
            {
                "Liga":
                    jogo["liga"],

                "Jogo":
                    f"{jogo['casa']} x {jogo['fora']}",

                "Horário":
                    jogo["horario"][11:16],
            }

            for jogo in jogos
        ]
    )

    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True,
    )


    if st.button(
        "🧠 ANALISAR JOGOS",
        use_container_width=True,
    ):

        with st.spinner(
            "🧠 Analisando jogos..."
        ):

            analises = analisar_jogos(
                jogos,
                API_KEY,
            )

        st.session_state[
            "analises"
        ] = analises


analises = st.session_state.get(
    "analises",
    [],
)


# ============================================================
# RESULTADOS
# ============================================================

if analises:

    st.header(
        "🏆 Melhores oportunidades"
    )

    for numero, analise in enumerate(
        analises,
        1,
    ):

        st.subheader(
            f"#{numero} ⚽ "
            f"{analise['casa']} x "
            f"{analise['fora']}"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Mercado",
                analise["descricao"],
            )

        with col2:

            st.metric(
                "Odd",
                f"{analise['odd']:.2f}",
            )

        with col3:

            st.metric(
                "Probabilidade",
                f"{analise['probabilidade'] * 100:.1f}%",
            )


        st.caption(
            f"{analise['liga']} • "
            f"{analise['horario'][11:16]}"
        )


        with st.expander(
            "📊 Ver detalhes"
        ):

            fc = analise[
                "forma_casa"
            ]

            ff = analise[
                "forma_fora"
            ]

            p = analise[
                "probabilidades"
            ]


            a, b = st.columns(2)


            with a:

                st.write(
                    f"🏠 **{analise['casa']}**"
                )

                st.write(
                    f"Últimos jogos: {fc['jogos']}"
                )

                st.write(
                    f"Vitórias: {fc['vitorias']}"
                )

                st.write(
                    f"Empates: {fc['empates']}"
                )

                st.write(
                    f"Derrotas: {fc['derrotas']}"
                )

                st.write(
                    f"Gols marcados/jogo: "
                    f"{fc['marcados']:.2f}"
                )

                st.write(
                    f"Gols sofridos/jogo: "
                    f"{fc['sofridos']:.2f}"
                )


            with b:

                st.write(
                    f"✈️ **{analise['fora']}**"
                )

                st.write(
                    f"Últimos jogos: {ff['jogos']}"
                )

                st.write(
                    f"Vitórias: {ff['vitorias']}"
                )

                st.write(
                    f"Empates: {ff['empates']}"
                )

                st.write(
                    f"Derrotas: {ff['derrotas']}"
                )

                st.write(
                    f"Gols marcados/jogo: "
                    f"{ff['marcados']:.2f}"
                )

                st.write(
                    f"Gols sofridos/jogo: "
                    f"{ff['sofridos']:.2f}"
                )


            st.write(
                "### 📈 Probabilidades"
            )

            dados_prob = pd.DataFrame(
                [
                    [
                        "Vitória casa",
                        p["casa"],
                    ],
                    [
                        "Empate",
                        p["empate"],
                    ],
                    [
                        "Vitória fora",
                        p["fora"],
                    ],
                    [
                        "1X",
                        p["1X"],
                    ],
                    [
                        "X2",
                        p["X2"],
                    ],
                    [
                        "Casa marca 1+",
                        p["casa_gol"],
                    ],
                    [
                        "Fora marca 1+",
                        p["fora_gol"],
                    ],
                    [
                        "Mais de 1.5",
                        p["over15"],
                    ],
                    [
                        "Mais de 2.5",
                        p["over25"],
                    ],
                ],
                columns=[
                    "Mercado",
                    "Probabilidade",
                ],
            )

            dados_prob[
                "Probabilidade"
            ] = (
                dados_prob[
                    "Probabilidade"
                ]
                * 100
            ).round(1).astype(str) + "%"


            st.dataframe(
                dados_prob,
                use_container_width=True,
                hide_index=True,
            )


        st.divider()


# ============================================================
# MÚLTIPLAS
# ============================================================

if analises:

    st.header(
        "🎯 Múltiplas automáticas"
    )


    multipla_5 = montar_multipla(
        analises,
        1,
        5,
        6,
    )


    multipla_10 = montar_multipla(
        analises,
        8,
        12,
        8,
    )


    multipla_50 = montar_multipla(
        analises,
        40,
        60,
        12,
    )


    def mostrar_multipla(
        titulo,
        dados,
    ):

        st.subheader(
            titulo
        )

        if not dados["selecoes"]:

            st.warning(
                "Não foi possível montar "
                "essa múltipla com as odds "
                "disponíveis."
            )

            return


        c1, c2 = st.columns(2)


        with c1:

            st.metric(
                "Odd total",
                f"{dados['odd']:.2f}",
            )


        with c2:

            st.metric(
                "Probabilidade conjunta",
                f"{dados['probabilidade'] * 100:.2f}%",
            )


        for numero, selecao in enumerate(
            dados["selecoes"],
            1,
        ):

            st.write(
                f"**{numero}. {selecao['jogo']}**"
            )

            st.write(
                f"➡️ {selecao['descricao']} "
                f"| Odd {selecao['odd']:.2f} "
                f"| Prob. "
                f"{selecao['probabilidade'] * 100:.1f}%"
            )


    mostrar_multipla(
        "🟢 Múltipla 1–5",
        multipla_5,
    )


    mostrar_multipla(
        "🟡 Múltipla próxima de 10",
        multipla_10,
    )


    mostrar_multipla(
        "🔴 Múltipla próxima de 50",
        multipla_50,
    )


    st.info(
        "As probabilidades são estimativas "
        "estatísticas e não garantem o resultado."
    )


st.divider()

st.caption(
    "FUTBET PRO • Análise estatística de futebol"
)
