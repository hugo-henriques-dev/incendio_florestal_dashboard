"""
Funções responsáveis pela apresentação das diferentes views do dashboard.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pydeck as pdk

from constantes import (
    COR_SEM_OCORRENCIAS,
    FONT_HOVER,
    LIMITES_PROBABILIDADE,
    MESES,
    MESES_ABREVIADOS,
    PALETA
)
from ui.ui_utils import (
    formatar_numero,
    mostrar_legenda_probabilidade,
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
        f"{formatar_numero(percent_sem_causa, 1)}%"
        " das ocorrências não têm causa preenchida em TipoCausa."
    )

    distrito_intencional = obter_distrito_top_causa(distritos_causa, "Intencional")
    distrito_negligente = obter_distrito_top_causa(distritos_causa, "Negligente")
    distrito_natural = obter_distrito_top_causa(distritos_causa, "Natural")

    metricas = [
        {
            "titulo": "Ocorrências",
            "valor": formatar_numero(total_ocorrencias),
        },
        {
            "titulo": "Área ardida",
            "valor": f"{formatar_numero(area_total)} ha",
        },
        {
            "titulo": "Período",
            "valor": f"{ano_inicial} - {ano_final}",
        },
        {
            "titulo": "Média anual de área ardida",
            "valor": f"{formatar_numero(media_area_anual)} ha",
        },
        {
            "titulo": "Ano com maior área ardida",
            "valor": (
                f"{ano_maior_area} "
                f"({formatar_numero(maior_area / 1000)} mil ha)"
            ),
        },
        {
            "titulo": "Ano com mais ocorrências",
            "valor": (
                f"{ano_mais_ocorrencias} "
                f"({formatar_numero(mais_ocorrencias)})"
            ),
        },
        {
            "titulo": "Distrito com mais ocorrências intencionais",
            "valor": (
                f"{distrito_intencional['Distrito']} "
                f"({formatar_numero(distrito_intencional['Ocorrencias'])})"
            ),
            "help": texto_sem_causa,
        },
        {
            "titulo": "Distrito com mais ocorrências negligentes",
            "valor": (
                f"{distrito_negligente['Distrito']} "
                f"({formatar_numero(distrito_negligente['Ocorrencias'])})"
            ),
            "help": texto_sem_causa,
        },
        {
            "titulo": "Distrito com mais ocorrências naturais",
            "valor": (
                f"{distrito_natural['Distrito']} "
                f"({formatar_numero(distrito_natural['Ocorrencias'])})"
            ),
            "help": texto_sem_causa,
        },
    ]

    mostrar_metricas(metricas)
    st.write("---")

    # ====== Distribuição mensal ======
    # O reindex garante os 12 meses, mesmo que algum não tenha ocorrências
    dados_mensais = (
        gdf.groupby("Mes")
        .size()
        .reindex(range(1, 13), fill_value=0)
        .reset_index(name="Ocorrencias")
    )

    dados_mensais["Mes"] = dados_mensais["Mes"].map(MESES_ABREVIADOS)

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

    st.write("---")
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

    st.write("---")

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
            "<b>Concentração de ocorrências</b>"
            f"<br>Total de ocorrências: {formatar_numero(total_ocorrencias)}"
            f"<br><br>Total de hexágonos: {formatar_numero(len(hexagonos))}"
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
        "Fire Weather Index ([FWI]("
        "https://fogos.icnf.pt/localizador/legenda/Indices_FWI.pdf "
        "\"Índice Meteorológico de Perigo de Incêndio "
        "(documento PDF do ICNF)\"))"
        " - índice meteorológico de perigo de incêndio que indica "
        "o potencial de ignição e propagação do fogo com base nas "
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

    dados_fwi_area["AreaHaTexto"] = dados_fwi_area["AreaHa"].map(
        formatar_numero
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
        color="ClasseFWI",
        color_discrete_map=dict(zip(ordem_fwi, PALETA)),
        custom_data=["AreaHaTexto"],
    )

    fig_area.update_traces(
        hovertemplate=(
            "<b>Área ardida: %{customdata[0]} ha</b>"
            "<extra></extra>"
        ),
        hoverlabel=dict(font_size=FONT_HOVER),
    )

    st.plotly_chart(
        fig_area,
        width="stretch",
    )


def mostrar_previsao(probabilidades, municipios):
    """
    Apresenta a vista de previsão, incluindo o mapa de probabilidades
    por concelho e o perfil sazonal do concelho selecionado.

    :param probabilidades: DataFrame com as probabilidades estimadas
        por concelho e mês, e o período do histórico, calculados no ETL.
    :param municipios: GeoDataFrame com a geometria dos municípios.
    :returns: None.
    """
    _mostrar_mapa_previsao(probabilidades, municipios)
    _mostrar_perfil_sazonal(probabilidades)


def _mostrar_mapa_previsao(probabilidades, municipios):
    """
    Apresenta o mapa da probabilidade estimada de ocorrência de incêndios
    por concelho, para o mês selecionado.

    A probabilidade é calculada no ETL como uma proporção ponderada dos
    anos históricos em que houve pelo menos uma ocorrência nesse mês,
    atribuindo maior peso aos anos mais recentes, segundo DECAIMENTO_ANUAL.
    O ano da previsão e o período do histórico vêm da própria tabela, por
    isso o texto corresponde sempre ao que foi calculado.

    Os concelhos sem qualquer ocorrência registada no mês têm uma cor
    própria e não entram na escala de classes.

    :param probabilidades: DataFrame com a probabilidade estimada por
        concelho e mês, calculada no ETL.
    :param municipios: GeoDataFrame com a geometria dos municípios.
    :returns: None.
    :raises AssertionError: Se algum município da CAOP não tiver
        probabilidade na tabela.
    """
    mes = st.selectbox(
        "Mês",
        MESES,
        format_func=lambda chave: MESES[chave],
    )

    ano_previsao = probabilidades["AnoPrevisao"].iloc[0]
    ano_inicial = probabilidades["AnoHistoricoInicial"].iloc[0]
    ano_final = probabilidades["AnoHistoricoFinal"].iloc[0]

    st.write(
        f"""
        Estimativa da probabilidade de cada concelho registar pelo menos
        uma ocorrência em **{MESES[mes].lower()} de {ano_previsao}**,
        com base nos registos de
        **{ano_inicial}-{ano_final}**.
        O ano {ano_previsao - 1} fica de fora por ter registos ainda por
        completar.

        Os anos mais recentes pesam mais, porque em testes com anos passados
        foram melhor indicador do ano seguinte, e assume-se que o
        padrão recente se mantém. Por isso, as estimativas acompanham as mudanças
        de tendência com algum atraso, e o mapa serve sobretudo para comparar
        concelhos e meses.
        """
    )

    # Só os valores do mês selecionado, uma linha por concelho.
    dados_concelho = probabilidades[
        probabilidades["Mes"] == mes
    ].drop(columns="Mes")

    dados_mapa = municipios.merge(
        dados_concelho,
        left_on="municipio",
        right_on="Concelho",
        how="left",
        validate="1:1",
    )

    # Falha cedo se algum município da CAOP não existir nos dados do ICNF.
    assert dados_mapa["Probabilidade"].notna().all()

    # ====== Classes e cores ======
    # Cor de cada classe de PALETA, convertida de hexadecimal para RGB.
    cores = [
        [int(cor[i:i + 2], 16) for i in (1, 3, 5)]
        for cor in PALETA
    ]

    # Classe de probabilidade (0 a 4) de cada concelho, segundo
    # LIMITES_PROBABILIDADE.
    classes = np.digitize(
        dados_mapa["Probabilidade"],
        LIMITES_PROBABILIDADE,
    )

    # Concelhos sem qualquer ocorrência no histórico do mês têm cor própria.
    sem_ocorrencias = dados_mapa["AnosComOcorrencia"] == 0

    cor_sem_ocorrencias = [
        int(COR_SEM_OCORRENCIAS[i:i + 2], 16)
        for i in (1, 3, 5)
    ]

    dados_mapa["cor"] = [
        cor_sem_ocorrencias if sem else cores[classe]
        for sem, classe in zip(sem_ocorrencias, classes)
    ]

    # Concelhos por classe de probabilidade, sem contar os que não têm
    # registos, porque esses aparecem a cinzento.
    contagens = np.bincount(
        classes[~sem_ocorrencias.to_numpy()],
        minlength=len(PALETA),
    )

    # Nos concelhos sem registos, o hover diz isso em vez de mostrar 0%.
    dados_mapa["ProbabilidadeTexto"] = [
        "sem ocorrências registadas" if sem
        else f"{formatar_numero(p * 100, 1)}%"
        for sem, p in zip(
            sem_ocorrencias,
            dados_mapa["Probabilidade"],
        )
    ]

    dados_mapa["OcorrenciasTexto"] = (
        dados_mapa["Ocorrencias"].map(formatar_numero)
    )

    # ====== Mapa ======
    # Centro do mapa: centro da caixa envolvente dos municípios.
    minx, miny, maxx, maxy = dados_mapa.total_bounds

    # Só as colunas usadas na cor e no tooltip.
    camada = pdk.Layer(
        "GeoJsonLayer",
        data=dados_mapa[
            [
                "municipio",
                "AnosComOcorrencia",
                "AnosHistoricos",
                "ProbabilidadeTexto",
                "OcorrenciasTexto",
                "cor",
                "geometry",
            ]
        ].__geo_interface__,
        pickable=True,
        stroked=True,
        filled=True,
        get_fill_color="properties.cor",
        get_line_color=[90, 90, 90, 180],
        line_width_min_pixels=1,
    )

    # O tooltip do pydeck não acompanha o tema do Streamlit, por isso as
    # cores dele são escolhidas consoante o tema atual.
    if st.context.theme.type == "dark":
        estilo_tooltip = {
            "backgroundColor": "#262730",
            "color": "#fafafa",
            "border": "1px solid #4a4d5a",
        }
    else:
        estilo_tooltip = {
            "backgroundColor": "#ffffff",
            "color": "#2a3f5f",
            "border": "1px solid #d3d3d3",
        }

    mapa = pdk.Deck(
        layers=[camada],
        map_style=None,
        initial_view_state=pdk.ViewState(
            latitude=(miny + maxy) / 2,
            longitude=(minx + maxx) / 2,
            zoom=6.3,
        ),
        tooltip={
            "html": (
                "<b>{municipio}</b><br>"
                "Probabilidade estimada: {ProbabilidadeTexto}<br>"
                "Anos com ocorrência: "
                "{AnosComOcorrencia} de {AnosHistoricos}<br>"
                "Total de ocorrências no mês: {OcorrenciasTexto}"
            ),
            "style": {
                **estilo_tooltip,
                "padding": "8px 10px",
                "borderRadius": "2px",
                "fontFamily": "Arial, sans-serif",
                "fontSize": f"{FONT_HOVER}px",
                "lineHeight": "1.3",
                "whiteSpace": "nowrap",
            },
        },
    )

    # ====== Layout ======
    col_mapa, col_legenda = st.columns([4, 1.3], gap="medium")

    with col_mapa:
        st.pydeck_chart(
            mapa,
            height=650,
            width="stretch",
            alt=(
                "Mapa da probabilidade estimada de ocorrência de incêndios "
                "por concelho, no mês selecionado."
            ),
        )

    with col_legenda:
        mostrar_legenda_probabilidade(
            contagens,
            int(sem_ocorrencias.sum()),
        )


def _mostrar_perfil_sazonal(probabilidades):
    """
    Apresenta a probabilidade estimada de ocorrência de incêndios em cada
    mês do ano, para o concelho selecionado, com as cores das classes do
    mapa.

    Enquanto nenhum concelho estiver selecionado, o gráfico não é
    apresentado.

    :param probabilidades: DataFrame com a probabilidade estimada e os
        indicadores históricos por concelho e mês, calculados no ETL.
    :returns: None.
    """
    st.write(
        """
        ---
        Probabilidade estimada de cada mês para o concelho escolhido,
        com as cores da legenda do mapa.
        """
    )

    concelho = st.selectbox(
        "Concelho",
        sorted(probabilidades["Concelho"].unique()),
        index=None,
        placeholder="Escolhe um concelho",
        key="concelho_previsao",
    )

    # Sem concelho escolhido, não há gráfico para mostrar
    if concelho is None:
        return

    dados = (
        probabilidades[probabilidades["Concelho"] == concelho]
        .sort_values("Mes")
    )
    total_anos_historicos = dados["AnosHistoricos"].iloc[0]

    # Mesma classificação do mapa, para as cores coincidirem com a legenda
    classes = np.digitize(
        dados["Probabilidade"],
        LIMITES_PROBABILIDADE,
    )

    sem_ocorrencias = dados["AnosComOcorrencia"] == 0

    probabilidade_texto = [
        "sem ocorrências registadas" if sem
        else f"{formatar_numero(p * 100, 1)}%"
        for sem, p in zip(
            sem_ocorrencias,
            dados["Probabilidade"],
        )
    ]

    anos_ocorrencia_texto = dados["AnosComOcorrencia"].map(
        lambda anos: (
            f"{formatar_numero(anos)} de "
            f"{formatar_numero(total_anos_historicos)}"
        )
    )

    ocorrencias_texto = dados["Ocorrencias"].map(formatar_numero)
    mes_texto = dados["Mes"].map(MESES)

    customdata = list(zip(
        mes_texto,
        probabilidade_texto,
        anos_ocorrencia_texto,
        ocorrencias_texto,
    ))

    fig = go.Figure(
        go.Bar(
            x=dados["Mes"].map(MESES_ABREVIADOS),
            y=dados["Probabilidade"] * 100,
            marker_color=[PALETA[classe] for classe in classes],
            customdata=customdata,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Probabilidade estimada: %{customdata[1]}<br>"
                "Anos com ocorrência: %{customdata[2]}<br>"
                "Total de ocorrências no mês: %{customdata[3]}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=f"Probabilidade estimada por mês - {concelho}",
        xaxis_title="Mês",
        yaxis_title="Probabilidade estimada (%)",
        yaxis_range=[0, 100],
        hovermode="x",
        margin=dict(t=60, b=40, l=60, r=20),
        hoverlabel=dict(font_size=FONT_HOVER),
        height=400,
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )