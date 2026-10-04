"""
Filtros interativos da view de distribuição geográfica, incluindo a
gestão de estado da cascata Distrito -> Concelho -> Freguesia.
"""

import streamlit as st

from constantes import ANOS_RECENTES, LABELS_CLASSE_AREA
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

    # Só mostra classes que existem nos dados, pela ordem de
    # LABELS_CLASSE_AREA (por tamanho, não alfabética)
    valores_existentes = gdf["ClasseArea"].dropna().unique()
    opcoes_classe_area = ["Todas"] + [
        valor for valor in LABELS_CLASSE_AREA if valor in valores_existentes
    ]

    intervalo_anos, classe_area, tipo_causa = mostrar_em_colunas([
        # O valor inicial é a janela recente, para coincidir com o
        # dataset pré-calculado
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

    # ====== Estado da cascata de localização ======
    # As opções de cada nível dependem do nível acima, por isso o valor
    # guardado é validado antes de desenhar os widgets: se já não existir
    # nas opções, volta a "Todos"/"Todas"
    for nivel, valor in _VALOR_TODOS.items():
        st.session_state.setdefault(nivel, valor)

    # Distrito
    distritos = [_VALOR_TODOS["distrito"]] + sorted(
        gdf["Distrito"].dropna().unique().tolist()
    )

    if st.session_state.distrito not in distritos:
        st.session_state.distrito = _VALOR_TODOS["distrito"]

    # Concelho
    dados_concelho = filtrar_localizacao(
        gdf,
        distrito=st.session_state.distrito,
    )

    concelhos = [_VALOR_TODOS["concelho"]] + sorted(
        dados_concelho["Concelho"].dropna().unique().tolist()
    )

    if st.session_state.concelho not in concelhos:
        st.session_state.concelho = _VALOR_TODOS["concelho"]

    # Freguesia
    dados_freguesia = filtrar_localizacao(
        gdf,
        distrito=st.session_state.distrito,
        concelho=st.session_state.concelho,
    )

    # Nomes de freguesia que existem em mais de um concelho (calculado sobre
    # todos os dados, para a etiqueta de cada opção não mudar com os filtros)
    concelhos_por_freguesia = (
        gdf.dropna(subset=["Concelho", "Freguesia"])
        .groupby("Freguesia")["Concelho"]
        .nunique()
    )
    freguesias_repetidas = set(
        concelhos_por_freguesia[concelhos_por_freguesia > 1].index
    )

    pares = (
        dados_freguesia[["Concelho", "Freguesia"]]
        .dropna()
        .drop_duplicates()
        .sort_values(["Freguesia", "Concelho"])
    )

    # Só os nomes que existem em mais de um concelho levam o concelho na
    # etiqueta, para opções diferentes não se fundirem numa só
    opcoes_freguesia = {}

    for concelho, freguesia in zip(pares["Concelho"], pares["Freguesia"]):
        if freguesia in freguesias_repetidas and (
            st.session_state.concelho == _VALOR_TODOS["concelho"]
        ):
            etiqueta = f"{freguesia} ({concelho})"
        else:
            etiqueta = freguesia

        opcoes_freguesia[etiqueta] = (concelho, freguesia)

    freguesias = [_VALOR_TODOS["freguesia"]] + list(opcoes_freguesia)

    if st.session_state.freguesia not in freguesias:
        st.session_state.freguesia = _VALOR_TODOS["freguesia"]

    # O on_change da freguesia consulta este mapa para saber o concelho
    # correspondente a cada opção
    st.session_state["_opcoes_freguesia"] = opcoes_freguesia

    # ====== Widgets de localização ======
    # Os on_change correm antes da nova execução, por isso o estado já
    # está atualizado quando as opções são recalculadas acima.
    # O concelho e a freguesia recebem o gdf, para inferir os níveis acima.
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
            args=("freguesia", gdf),
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
    Repõe os níveis de localização abaixo de `nivel` quando este muda e
    infere os níveis acima: o Distrito a partir do Concelho, e o Concelho
    e o Distrito a partir da Freguesia.

    :param nivel: "distrito", "concelho" ou "freguesia".
    :param gdf: GeoDataFrame completo, necessário para inferir o
        Distrito a partir do Concelho (ou da Freguesia).
    :returns: None.
    """
    valor = st.session_state[nivel]
    indice = _HIERARQUIA.index(nivel)

    for nivel_abaixo in _HIERARQUIA[indice + 1:]:
        st.session_state[nivel_abaixo] = _VALOR_TODOS[nivel_abaixo]

    if valor == _VALOR_TODOS[nivel]:
        return

    if nivel == "freguesia":
        # A etiqueta da opção pode incluir o concelho; recupera-o e deixa
        # só o nome da freguesia, que é o que o filtro compara
        concelho, freguesia = st.session_state["_opcoes_freguesia"][valor]
        st.session_state["concelho"] = concelho
        st.session_state["freguesia"] = freguesia
        valor = concelho

    elif nivel != "concelho":
        return

    dados = gdf[gdf["Concelho"] == valor]

    if len(dados) > 0:
        st.session_state["distrito"] = dados["Distrito"].iloc[0]


def _limpar_localizacao():
    """
    Repõe os três níveis de localização (Distrito, Concelho e Freguesia)
    em "Todos"/"Todas".

    :returns: None.
    """
    for nivel, valor in _VALOR_TODOS.items():
        st.session_state[nivel] = valor