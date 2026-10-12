"""
Executa a aplicação Streamlit e gere a navegação entre as diferentes
views do dashboard.
"""

import streamlit as st

from constantes import ANOS_RECENTES, CSS_ESTILOS, PNG_FAVICON
from dados_io.carregar_dados import (
    carregar_distribuicao_geo,
    carregar_distribuicao_geo_recente,
    carregar_evolucao_anual,
    carregar_municipios_caop,
    carregar_ocorrencias,
    carregar_probabilidades_previsao
)
from etl.processar_dados import agregar_em_hexagonos
from ui.filtros import filtrar_localizacao, obter_filtros_distribuicao
from ui.ui_utils import mostrar_footer
from ui.views import (
    mostrar_distribuicao_geografica,
    mostrar_evolucao_temporal,
    mostrar_perigo_incendio,
    mostrar_previsao,
    mostrar_visao_geral
)


def main():
    """
    Configura e executa a interface principal da aplicação.

    Gere a navegação entre as diferentes views, carrega os datasets
    necessários e aplica os filtros da distribuição geográfica.

    :returns: None.
    """
    # ====== Configuração da página ======
    st.set_page_config(
        page_title="Incêndios Florestais PT",
        page_icon=PNG_FAVICON,
        layout="wide",
    )

    st.html(CSS_ESTILOS)
    st.title(
        "Incêndios Florestais em Portugal",
        text_alignment="center"
    )

    # ====== Dados base e navegação ======
    # Ocorrências carregadas uma vez, pois são usadas por várias views
    gdf = carregar_ocorrencias()

    # Carregadas aqui, e não na view, porque o ano da previsão faz parte
    # do rótulo da navegação
    probabilidades = carregar_probabilidades_previsao()
    ano_previsao = int(probabilidades["AnoPrevisao"].iloc[0])

    labels_view = {
        "visao_geral": "Visão geral",
        "evolucao": "Evolução temporal",
        "distribuicao": "Distribuição geográfica",
        "perigo": "Perigo de Incêndio",
        "previsao": f"Probabilidade estimada de incêndio em {ano_previsao}",
    }

    view = st.selectbox(
        "Visualização",
        labels_view,
        format_func=lambda chave: labels_view[chave],
    )

    # ====== Renderização da view selecionada ======
    match view:
        case "visao_geral":
            dados = carregar_evolucao_anual()
            mostrar_visao_geral(gdf, dados)

        case "evolucao":
            dados = carregar_evolucao_anual()
            mostrar_evolucao_temporal(dados)

        case "distribuicao":
            (
                intervalo_anos,
                classe_area,
                tipo_causa,
                distrito,
                concelho,
                freguesia,
            ) = obter_filtros_distribuicao(gdf)

            dados_filtrados = gdf

            ano_min_disponivel = int(gdf["Ano"].min())
            ano_max_disponivel = int(gdf["Ano"].max())
            ano_min_recente = ano_max_disponivel - ANOS_RECENTES + 1

            # Só filtra quando o valor difere do default ("Todos"/"Todas"
            # ou intervalo completo), evitando filtragens desnecessárias
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
                st.warning("Não existem ocorrências para os filtros selecionados.")
            else:
                sem_outros_filtros = all(
                    valor in ("Todos", "Todas")
                    for valor in (classe_area, tipo_causa, distrito, concelho, freguesia)
                )

                # Sem filtros além do intervalo de anos, usa os hexágonos pré-calculados
                # (período completo ou recente); caso contrário, agrega em tempo real
                if sem_outros_filtros and intervalo_anos == (ano_min_disponivel, ano_max_disponivel):
                    hexagonos = carregar_distribuicao_geo()
                elif sem_outros_filtros and intervalo_anos == (ano_min_recente, ano_max_disponivel):
                    hexagonos = carregar_distribuicao_geo_recente()
                else:
                    hexagonos = agregar_em_hexagonos(dados_filtrados)

                mostrar_distribuicao_geografica(hexagonos)

        case "perigo":
            mostrar_perigo_incendio(gdf)

        case "previsao":
            municipios = carregar_municipios_caop()
            mostrar_previsao(probabilidades, municipios)

    mostrar_footer()


if __name__ == "__main__":
    main()
