"""
Funções responsáveis pela apresentação das diferentes views do dashboard.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from constantes import FONT_HOVER, PALETA
from ui.ui_utils import (
    formatar_numero,
    mostrar_metricas,
    obter_distrito_top_causa,
)


def mostrar_visao_geral(gdf, dados):
    """
    Apresenta a visão geral dos dados, incluindo métricas principais
    e a distribuição mensal das ocorrências.

    :param gdf: GeoDataFrame com as ocorrências de incêndios.
    :param dados: DataFrame com os indicadores agregados por ano.
    :returns: None.
    """
    # ====== Métricas ======
    total_ocorrencias = len(gdf)
    area_total = gdf["AreaTotal"].sum()
    ano_inicial = gdf["Ano"].min()
    ano_final = gdf["Ano"].max()

    media_area_anual = dados["AreaHa"].mean()

    ano_maior_area = dados.loc[
        dados["AreaHa"].idxmax(), "Ano"
    ]
    maior_area = dados["AreaHa"].max()

    ano_mais_ocorrencias = dados.loc[
        dados["Ocorrencias"].idxmax(), "Ano"
    ]
    mais_ocorrencias = dados["Ocorrencias"].max()

    # Registos sem causa ou sem distrito ficam fora desta contagem
    distritos_causa = (
        gdf.dropna(subset=["TipoCausa", "Distrito"])
        .groupby(["Distrito", "TipoCausa"])
        .size()
        .reset_index(name="Ocorrencias")
    )

    # Aviso mostrado no help das métricas por causa, porque os registos
    # sem causa não entram nesses valores
    percent_sem_causa = gdf["TipoCausa"].isna().mean() * 100
    texto_sem_causa = (
        f"{percent_sem_causa:.1f}".replace(".", ",")
        + "% das ocorrências não têm causa preenchida em TipoCausa."
    )

    distrito_intencional = obter_distrito_top_causa(distritos_causa, "Intencional")
    distrito_negligente = obter_distrito_top_causa(distritos_causa, "Negligente")
    distrito_natural = obter_distrito_top_causa(distritos_causa, "Natural")

    metricas = [
        {
            "titulo": "Ocorrências",
            "valor": f"{total_ocorrencias:,}".replace(",", " "),
        },
        {
            "titulo": "Área ardida",
            "valor": f"{area_total:,.0f} ha".replace(",", " "),
        },
        {
            "titulo": "Período",
            "valor": f"{ano_inicial} - {ano_final}",
        },
        {
            "titulo": "Média anual de área ardida",
            "valor": f"{media_area_anual:,.0f} ha".replace(",", " "),
        },
        {
            "titulo": "Ano com maior área ardida",
            "valor": (
                f"{ano_maior_area} "
                f"({maior_area / 1000:,.0f} mil ha)"
            ).replace(",", " "),
        },
        {
            "titulo": "Ano com mais ocorrências",
            "valor": (
                f"{ano_mais_ocorrencias} "
                f"({mais_ocorrencias:,})"
            ).replace(",", " "),
        },
        {
            "titulo": "Distrito com mais ocorrências intencionais",
            "valor": (
                f"{distrito_intencional['Distrito']} "
                f"({distrito_intencional['Ocorrencias']:,})"
            ).replace(",", " "),
            "help": texto_sem_causa,
        },
        {
            "titulo": "Distrito com mais ocorrências negligentes",
            "valor": (
                f"{distrito_negligente['Distrito']} "
                f"({distrito_negligente['Ocorrencias']:,})"
            ).replace(",", " "),
            "help": texto_sem_causa,
        },
        {
            "titulo": "Distrito com mais ocorrências naturais",
            "valor": (
                f"{distrito_natural['Distrito']} "
                f"({distrito_natural['Ocorrencias']:,})"
            ).replace(",", " "),
            "help": texto_sem_causa,
        },
    ]

    mostrar_metricas(metricas)

    # ====== Distribuição mensal ======
    # O reindex garante os 12 meses, mesmo que algum não tenha ocorrências
    dados_mensais = (
        gdf.groupby("Mes")
        .size()
        .reindex(range(1, 13), fill_value=0)
        .reset_index(name="Ocorrencias")
    )

    meses = (
        "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"
    )

    dados_mensais["Mes"] = dados_mensais["Mes"].map(
        dict(enumerate(meses, start=1))
    )

    fig = px.bar(
        dados_mensais,
        x="Mes",
        y="Ocorrencias",
        labels={
            "Mes": "Mês",
            "Ocorrencias": "Ocorrências",
        },
        title="Ocorrências por mês - total de todos os anos",
    )

    fig.update_traces(
        customdata=dados_mensais["Ocorrencias"].map(formatar_numero),
        hovertemplate="<b>%{x}: %{customdata} ocorrências</b><extra></extra>",
        hoverlabel=dict(
            font_size=FONT_HOVER
        )
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )


def mostrar_evolucao_temporal(dados):
    """
    Apresenta a evolução anual do número de ocorrências e da área ardida,
    bem como a relação entre estas duas variáveis e os respetivos
    coeficientes de correlação de Pearson e Spearman.

    :param dados: DataFrame com os indicadores agregados por ano.
    :returns: None.
    """
    dados["AreaMilHa"] = dados["AreaHa"] / 1000

    # ====== Evolução anual ======
    fig_ocorrencias = go.Figure()

    fig_ocorrencias.add_trace(
        go.Scatter(
            x=dados["Ano"],
            y=dados["Ocorrencias"],
            mode="lines+markers",
            name="Ocorrências",
            line=dict(width=3),
            marker=dict(size=7),
            customdata=dados["Ocorrencias"].map(formatar_numero),
            hovertemplate=(
                "<b>Ano: %{x}</b><br>"
                "Ocorrências: %{customdata}"
                "<extra></extra>"
            ),
        )
    )

    fig_ocorrencias.update_layout(
        title="Número de ocorrências por ano",
        xaxis_title="Ano",
        yaxis_title="Número de ocorrências",
        hovermode="x",
        margin=dict(t=60, b=40, l=60, r=20),
            hoverlabel=dict(font_size=FONT_HOVER),
        height=400,
    )

    st.plotly_chart(
        fig_ocorrencias,
        width="stretch",
    )

    fig_area = go.Figure()

    fig_area.add_trace(
        go.Bar(
            x=dados["Ano"],
            y=dados["AreaMilHa"],
            name="Área ardida",
            hovertemplate=(
                "<b>Ano: %{x}</b><br>"
                "Área ardida: %{y:,.1f} mil ha"
                "<extra></extra>"
            ),
        )
    )

    fig_area.update_layout(
        title="Área ardida por ano",
        xaxis_title="Ano",
        yaxis_title="Área ardida (mil ha)",
        hovermode="x",
        margin=dict(t=60, b=40, l=60, r=20),
        hoverlabel=dict(font_size=FONT_HOVER),
        height=400,
    )

    st.plotly_chart(
        fig_area,
        width="stretch",
    )


    # ====== Relação entre ocorrências e área ardida ======
    correlacao_pearson = dados["Ocorrencias"].corr(
        dados["AreaMilHa"],
        method="pearson",
    )

    # Spearman = Pearson calculado sobre as posições (ranks) dos valores
    correlacao_spearman = (
        dados["Ocorrencias"].rank().corr(
            dados["AreaMilHa"].rank()
        )
    )

    fig_relacao = go.Figure()

    fig_relacao.add_trace(
        go.Scatter(
            x=dados["Ocorrencias"],
            y=dados["AreaMilHa"],
            mode="markers",
            name="Ano",
            marker=dict(size=9),
            text=dados["Ano"],
            customdata=dados["Ocorrencias"].map(formatar_numero),
            hovertemplate=(
                "<b>Ano: %{text}</b><br>"
                "Ocorrências: %{customdata}<br>"
                "Área ardida: %{y:,.1f} mil ha"
                "<extra></extra>"
            ),
        )
    )
    x = dados["Ocorrencias"].to_numpy()
    y = dados["AreaMilHa"].to_numpy()

    # Reta de regressão linear (grau 1) desenhada com 100 pontos
    coeficientes = np.polyfit(x, y, 1)
    tendencia = np.poly1d(coeficientes)

    x_linha = np.linspace(x.min(), x.max(), 100)

    fig_relacao.add_trace(
        go.Scatter(
            x=x_linha,
            y=tendencia(x_linha),
            mode="lines",
            name="Tendência linear",
            line=dict(width=2, dash="dash"),
            hoverinfo="skip",
        )
    )

    fig_relacao.update_layout(
        title="Relação entre número de ocorrências e área ardida",
        xaxis_title="Número de ocorrências",
        yaxis_title="Área ardida (mil ha)",
        hovermode="closest",
        margin=dict(t=60, b=40, l=60, r=20),
        hoverlabel=dict(font_size=FONT_HOVER),
        height=400,
    )

    st.plotly_chart(
        fig_relacao,
        width="stretch",
    )

    st.metric(
        "Correlação de Pearson",
        f"{correlacao_pearson:.2f}",
        help=(
            "Mede a intensidade e a direção da relação linear entre o número "
            "de ocorrências e a área ardida.\n\n"
            "Valores positivos indicam que tendem a aumentar em conjunto; "
            "valores negativos indicam que uma tende a aumentar quando a "
            "outra diminui. Quanto mais próximo de 0, menor é a relação linear."
        ),
    )

    st.metric(
        "Correlação de Spearman",
        f"{correlacao_spearman:.2f}",
        help=(
            "Mede a intensidade e a direção da relação entre o número de "
            "ocorrências e a área ardida, considerando a ordem dos valores.\n\n"
            "Valores positivos indicam que tendem a aumentar em conjunto; "
            "valores negativos indicam que uma tende a aumentar quando a "
            "outra diminui. Quanto mais próximo de 0, menor é a relação."
        ),
    )


def mostrar_distribuicao_geografica(hexagonos):
    """
    Apresenta a distribuição geográfica das ocorrências através de
    hexágonos classificados por quintis de concentração.

    Quando todos os hexágonos têm o mesmo número de ocorrências, é
    apresentada uma única classe de concentração, em vez de criar
    quintis sem variação suficiente.

    :param hexagonos: GeoDataFrame com os hexágonos e o número de
        ocorrências em cada um.
    :returns: None.
    """
    hexagonos = hexagonos.copy()
    total_ocorrencias = int(hexagonos["Ocorrencias"].sum())

    # ====== Classes de concentração ======
    if hexagonos["Ocorrencias"].nunique() <= 1:
        valor = formatar_numero(hexagonos["Ocorrencias"].iloc[0])
        rotulo_unico = f"Concentração uniforme ({valor})"

        hexagonos["ClasseConcentracao"] = rotulo_unico
        ordem_classes = [rotulo_unico]
        paleta = ["#32A836"]
    else:
        # Permite menos de 5 classes quando há muitos valores repetidos.
        faixas = pd.qcut(
            hexagonos["Ocorrencias"],
            q=5,
            duplicates="drop",
        )

        intervalos = faixas.cat.categories

        nomes_classes = [
            "Muito baixa",
            "Baixa",
            "Média",
            "Alta",
            "Muito alta",
        ][:len(intervalos)]

        mapa_classes = {
            str(intervalo): nome
            for intervalo, nome in zip(intervalos, nomes_classes)
        }

        hexagonos["ClasseConcentracao"] = (
            faixas.astype(str).map(mapa_classes)
        )

        limites_classes = (
            hexagonos.groupby(
                "ClasseConcentracao",
                observed=True,
            )["Ocorrencias"]
            .agg(["min", "max"])
            .reindex(nomes_classes)
        )

        rotulos_classes = []

        for classe in nomes_classes:
            minimo = limites_classes.loc[classe, "min"]
            maximo = limites_classes.loc[classe, "max"]

            rotulos_classes.append(
                f"{classe} "
                f"({formatar_numero(minimo)}–{formatar_numero(maximo)})"
            )

        mapa_rotulos = dict(
            zip(nomes_classes, rotulos_classes)
        )

        hexagonos["ClasseConcentracao"] = (
            hexagonos["ClasseConcentracao"].map(mapa_rotulos)
        )

        ordem_classes = rotulos_classes
        paleta = PALETA[:len(ordem_classes)]

    hexagonos["OcorrenciasFormatadas"] = (
        hexagonos["Ocorrencias"].map(formatar_numero)
    )

    # ====== Centro do mapa ======
    # Usa o centro da caixa envolvente, evitando a união dos hexágonos.
    minx, miny, maxx, maxy = hexagonos.total_bounds
    centro_lat = (miny + maxy) / 2
    centro_lon = (minx + maxx) / 2

    # ====== GeoJSON ======
    # Envia apenas as geometrias, pois os valores são associados pelo índice.
    geojson = hexagonos[["geometry"]].__geo_interface__

    # ====== Construção do mapa ======
    mapa = px.choropleth_map(
        hexagonos,
        geojson=geojson,
        locations=hexagonos.index,
        color="ClasseConcentracao",
        category_orders={
            "ClasseConcentracao": ordem_classes,
        },
        color_discrete_sequence=paleta,
        map_style="open-street-map",
        center={
            "lat": centro_lat,
            "lon": centro_lon,
        },
        zoom=7,
        opacity=0.7,
        custom_data=["OcorrenciasFormatadas"],
        labels={
            "ClasseConcentracao": "Concentração de ocorrências",
        },
        height=600,
    )

    mapa.update_traces(
        hovertemplate=(
            "<b>Ocorrências: %{customdata[0]}</b>"
            "<extra></extra>"
        ),
    )

    mapa.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend_title_text=(
            "Concentração de ocorrências"
            f"<br>Total: {formatar_numero(total_ocorrencias)}"
        ),
    )

    st.plotly_chart(
        mapa,
        width="stretch",
    )


def mostrar_perigo_incendio(gdf):
    """
    Apresenta a distribuição das ocorrências e da área ardida pelos
    níveis de perigo do Fire Weather Index (FWI).

    :param gdf: GeoDataFrame com as ocorrências e a respetiva classe FWI.
    :returns: None.
    """
    st.write(
        "Fire Weather Index (FWI) - índice meteorológico de perigo de incêndio "
        "que indica o potencial de ignição e propagação do fogo com base nas "
        "condições meteorológicas."
    )

    ordem_fwi = [
        "Baixo",
        "Moderado",
        "Elevado",
        "Muito Elevado",
        "Extremo",
    ]

    # ====== Ocorrências por nível de perigo ======
    # O reindex mantém a ordem dos níveis e inclui os que não têm registos
    dados_fwi_ocorrencias = (
        gdf["ClasseFWI"]
        .value_counts()
        .reindex(ordem_fwi, fill_value=0)
        .reset_index()
    )

    dados_fwi_ocorrencias.columns = [
        "ClasseFWI",
        "Ocorrencias",
    ]

    fig_ocorrencias = px.pie(
        dados_fwi_ocorrencias,
        names="ClasseFWI",
        values="Ocorrencias",
        category_orders={
            "ClasseFWI": ordem_fwi,
        },
        color="ClasseFWI",
        color_discrete_sequence=PALETA,
        title="Ocorrências por nível de perigo do FWI",
    )

    # sort=False mantém a ordem de Baixo a Extremo em vez de ordenar por tamanho
    fig_ocorrencias.update_traces(
        sort=False,
        textinfo="label+percent",
        textposition="inside",
        textfont_size=16,
        customdata=dados_fwi_ocorrencias["Ocorrencias"].map(
            formatar_numero
        ),
        hovertemplate=(
            "<b>%{label}: %{customdata} ocorrências "
            "(%{percent})</b><extra></extra>"
        ),
    )
    
    fig_ocorrencias.update_layout(
        height=600,
        showlegend=False,
        margin=dict(t=60, b=20, l=20, r=20),
        hoverlabel=dict(font_size=FONT_HOVER),
    )

    st.plotly_chart(
        fig_ocorrencias,
        width="stretch",
    )

    # ====== Área ardida por nível de perigo ======
    dados_fwi_area = (
        gdf.groupby("ClasseFWI", dropna=False)["AreaTotal"]
        .sum()
        .reindex(ordem_fwi, fill_value=0)
        .reset_index()
    )

    dados_fwi_area.columns = [
        "ClasseFWI",
        "AreaHa",
    ]

    dados_fwi_area["AreaMilHa"] = (
        dados_fwi_area["AreaHa"] / 1000
    )

    fig_area = px.bar(
        dados_fwi_area,
        x="AreaMilHa",
        y="ClasseFWI",
        orientation="h",
        category_orders={
            "ClasseFWI": ordem_fwi,
        },
        labels={
            "ClasseFWI": "Nível de perigo",
            "AreaMilHa": "Área ardida (mil ha)",
        },
        title="Área ardida por nível de perigo do FWI",
    )

    fig_area.update_traces(
        hovertemplate=(
            "<b>Área ardida: %{customdata} ha</b>"
            "<extra></extra>"
        ),
        customdata=dados_fwi_area["AreaHa"].map(
            formatar_numero
        ),
        hoverlabel=dict(font_size=FONT_HOVER),
    )

    st.plotly_chart(
        fig_area,
        width="stretch",
    )