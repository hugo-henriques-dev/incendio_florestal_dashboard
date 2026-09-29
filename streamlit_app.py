"""
Executa a aplicação Streamlit e gere a navegação entre as diferentes
views do dashboard.
"""

import streamlit as st

from constantes import ANOS_RECENTES, CSS_ESTILOS, PNG_FAVICON
from dados_io.carregar_dados import (
    carregar_ocorrencias,
    carregar_evolucao_anual,
    carregar_distribuicao_geo,
    carregar_distribuicao_geo_recente
)
from etl.processar_dados import agregar_em_hexagonos
from ui.ui_utils import mostrar_footer
from ui.views import (
    mostrar_visao_geral,
    mostrar_evolucao_temporal,
    mostrar_distribuicao_geografica,
    mostrar_perigo_incendio,
)
from ui.filtros import filtrar_localizacao, obter_filtros_distribuicao


def main():
    """
    Configura e executa a interface principal da aplicação.

    Gere a navegação entre as diferentes views, carrega os datasets
    necessários e aplica os filtros da distribuição geográfica.

    :returns: None.
    """
    st.set_page_config(
        page_title="Incêndios Florestais PT",
        page_icon=PNG_FAVICON,
        layout="wide",
    )

    st.html(CSS_ESTILOS)
    st.title(
        "Incêndios Florestais em Portugal",
        text_alignment="center",
    )

    gdf = carregar_ocorrencias()

    view = st.selectbox(
        "Visualização",
        [
            "Visão geral",
            "Evolução temporal",
            "Distribuição geográfica",
            "Perigo de Incêndio",
            "Dados",
        ],
    )

    if view == "Visão geral":
        dados = carregar_evolucao_anual()
        mostrar_visao_geral(gdf, dados)

    elif view == "Evolução temporal":
        dados = carregar_evolucao_anual()
        mostrar_evolucao_temporal(dados)

    elif view == "Distribuição geográfica":
        (
            intervalo_anos,
            classe_area,
            tipo_causa,
            distrito,
            concelho,
            freguesia,
        ) = obter_filtros_distribuicao(gdf)

        dados_filtrados = gdf.copy()

        ano_min_disponivel = int(gdf["Ano"].min())
        ano_max_disponivel = int(gdf["Ano"].max())
        ano_min_recente = ano_max_disponivel - ANOS_RECENTES + 1

        if intervalo_anos != (ano_min_disponivel, ano_max_disponivel):
            dados_filtrados = dados_filtrados[
                dados_filtrados["Ano"].between(*intervalo_anos)
            ]

        if classe_area != "Todas":
            dados_filtrados = dados_filtrados[
                dados_filtrados["ClasseArea"] == classe_area
            ]

        if tipo_causa != "Todos":
            dados_filtrados = dados_filtrados[
                dados_filtrados["TipoCausa"] == tipo_causa
            ]

        dados_filtrados = filtrar_localizacao(
            dados_filtrados,
            distrito=distrito,
            concelho=concelho,
            freguesia=freguesia,
        )

        if dados_filtrados.empty:
            st.warning(
                "Não existem ocorrências para os filtros selecionados."
            )
        else:
            sem_outros_filtros = (
                classe_area == "Todas"
                and tipo_causa == "Todos"
                and distrito == "Todos"
                and concelho == "Todos"
                and freguesia == "Todas"
            )

            if sem_outros_filtros and intervalo_anos == (ano_min_disponivel, ano_max_disponivel):
                hexagonos = carregar_distribuicao_geo()
            elif sem_outros_filtros and intervalo_anos == (ano_min_recente, ano_max_disponivel):
                hexagonos = carregar_distribuicao_geo_recente()
            else:
                hexagonos = agregar_em_hexagonos(dados_filtrados)

            mostrar_distribuicao_geografica(hexagonos)

    elif view == "Perigo de Incêndio":
        mostrar_perigo_incendio(gdf)

    elif view == "Dados":
        st.html("<span id='sei-la'>Uns Dados</span>")
        st.dataframe(gdf.drop(columns="geometry"))
    
    mostrar_footer()


if __name__ == "__main__":
    main()