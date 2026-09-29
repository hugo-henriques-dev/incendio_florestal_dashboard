"""
Filtros interativos da view de distribuição geográfica, incluindo a
gestão de estado da cascata Distrito -> Concelho -> Freguesia.
"""

import streamlit as st

from constantes import LABELS_CLASSE_AREA, ANOS_RECENTES
from ui.ui_utils import mostrar_em_colunas

_HIERARQUIA = ["distrito", "concelho", "freguesia"]
_VALOR_TODOS = {"distrito": "Todos", "concelho": "Todos", "freguesia": "Todas"}


def obter_filtros_distribuicao(gdf):
    """
    Apresenta os filtros da distribuição geográfica e gere o estado
    da cascata de localização Distrito -> Concelho -> Freguesia.

    :param gdf: GeoDataFrame com os dados utilizados pelos filtros.
    :returns: Tuplo com o intervalo de anos, classe de área, tipo de causa,
        distrito, concelho e freguesia selecionados.
    """
    ano_min = int(gdf["Ano"].min())
    ano_max = int(gdf["Ano"].max())

    valores_existentes = gdf["ClasseArea"].dropna().unique()
    opcoes_classe_area = ["Todas"] + [
        valor for valor in LABELS_CLASSE_AREA if valor in valores_existentes
    ]

    intervalo_anos, classe_area, tipo_causa = mostrar_em_colunas([
        lambda: st.slider(
            "Ano",
            min_value=ano_min,
            max_value=ano_max,
            value=(ano_max - ANOS_RECENTES + 1, ano_max),
        ),
        lambda: st.selectbox(
            "Área ardida",
            opcoes_classe_area,
            format_func=lambda valor: LABELS_CLASSE_AREA.get(valor, valor),
        ),
        lambda: st.selectbox(
            "Tipo de causa",
            ["Todos"] + sorted(
                gdf["TipoCausa"].dropna().unique().tolist()
            ),
        ),
    ])

    # Valores iniciais da cascata
    if "distrito" not in st.session_state:
        st.session_state.distrito = "Todos"

    if "concelho" not in st.session_state:
        st.session_state.concelho = "Todos"

    if "freguesia" not in st.session_state:
        st.session_state.freguesia = "Todas"

    # -------------------------
    # Distrito
    # -------------------------
    distritos = ["Todos"] + sorted(
        gdf["Distrito"].dropna().unique().tolist()
    )

    if st.session_state.distrito not in distritos:
        st.session_state.distrito = "Todos"

    # -------------------------
    # Concelho
    # -------------------------
    dados_concelho = filtrar_localizacao(
        gdf,
        distrito=st.session_state.distrito,
    )

    concelhos = ["Todos"] + sorted(
        dados_concelho["Concelho"].dropna().unique().tolist()
    )

    if st.session_state.concelho not in concelhos:
        st.session_state.concelho = "Todos"

    # -------------------------
    # Freguesia
    # -------------------------
    dados_freguesia = filtrar_localizacao(
        gdf,
        distrito=st.session_state.distrito,
        concelho=st.session_state.concelho,
    )

    freguesias = ["Todas"] + sorted(
        dados_freguesia["Freguesia"].dropna().unique().tolist()
    )

    if st.session_state.freguesia not in freguesias:
        st.session_state.freguesia = "Todas"

    # -------------------------
    # Widgets de localização
    # -------------------------
    mostrar_em_colunas([
        lambda: st.selectbox(
            "Distrito",
            distritos,
            key="distrito",
            on_change=_atualizar_localizacao,
            args=("distrito",),
        ),
        lambda: st.selectbox(
            "Concelho",
            concelhos,
            key="concelho",
            on_change=_atualizar_localizacao,
            args=("concelho", gdf),
        ),
        lambda: st.selectbox(
            "Freguesia",
            freguesias,
            key="freguesia",
            on_change=_atualizar_localizacao,
            args=("freguesia",),
        ),
    ])

    st.button(
        "Limpar localização",
        on_click=_limpar_localizacao,
    )

    return (
        intervalo_anos,
        classe_area,
        tipo_causa,
        st.session_state.distrito,
        st.session_state.concelho,
        st.session_state.freguesia,
    )


def filtrar_localizacao(gdf, distrito="Todos", concelho="Todos", freguesia="Todas"):
    """
    Restringe o GeoDataFrame aos níveis de localização diferentes de
    "Todos"/"Todas".

    :param gdf: GeoDataFrame a filtrar.
    :param distrito: Distrito selecionado, ou "Todos".
    :param concelho: Concelho selecionado, ou "Todos".
    :param freguesia: Freguesia selecionada, ou "Todas".
    :returns: GeoDataFrame filtrado.
    """
    if distrito != "Todos":
        gdf = gdf[gdf["Distrito"] == distrito]

    if concelho != "Todos":
        gdf = gdf[gdf["Concelho"] == concelho]

    if freguesia != "Todas":
        gdf = gdf[gdf["Freguesia"] == freguesia]

    return gdf


def _atualizar_localizacao(nivel, gdf=None):
    """
    Repõe os níveis de localização abaixo de `nivel` quando este muda, e,
    apenas para "concelho", infere o Distrito a partir dos dados (para
    "freguesia" não se faz o mesmo, porque nomes de Freguesia não são
    únicos a nível nacional).

    :param nivel: "distrito", "concelho" ou "freguesia".
    :param gdf: GeoDataFrame completo, necessário só para inferir o
        Distrito a partir do Concelho.
    :returns: None.
    """
    valor = st.session_state[nivel]
    indice = _HIERARQUIA.index(nivel)

    for nivel_abaixo in _HIERARQUIA[indice + 1:]:
        st.session_state[nivel_abaixo] = _VALOR_TODOS[nivel_abaixo]

    if valor == _VALOR_TODOS[nivel] or nivel != "concelho":
        return

    dados = gdf[gdf["Concelho"] == valor]

    if len(dados) > 0:
        st.session_state["distrito"] = dados["Distrito"].iloc[0]


def _limpar_localizacao():
    st.session_state.distrito = "Todos"
    st.session_state.concelho = "Todos"
    st.session_state.freguesia = "Todas"