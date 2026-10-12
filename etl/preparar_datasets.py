"""
Prepara os datasets derivados necessários para o dashboard.
"""

from datetime import datetime

import geopandas as gpd
import pandas as pd
import shapely

from constantes import (
    ANOS_RECENTES,
    DIR_PREPARADOS,
    FICHEIRO_CAOP_MUNICIPIOS,
    FICHEIRO_CAOP_MUNICIPIOS_BRUTO,
    FICHEIRO_DISTRIBUICAO_GEO,
    FICHEIRO_DISTRIBUICAO_GEO_RECENTE,
    FICHEIRO_EVOLUCAO_ANUAL,
    FICHEIRO_FOGOS,
    FICHEIRO_PREVISAO_PROBABILIDADES,
    TOLERANCIA_SIMPLIFICACAO_CAOP_M
)
from etl.processar_dados import agregar_em_hexagonos, calcular_probabilidades


def preparar_evolucao_anual():
    """
    Cria um dataset agregado por ano para análise da evolução dos incêndios.

    Calcula o número de ocorrências e a área ardida conhecida por ano.
    A área é também convertida para milhares de hectares para facilitar
    a utilização posterior na dashboard.

    :returns: None.
    """
    print("\n" + "=" * 50)
    print("A carregar dados processados...")

    dados = pd.read_parquet(
        FICHEIRO_FOGOS,
        columns=["Codigo", "Ano", "AreaTotal"],
    )

    print(f"Ocorrências carregadas: {len(dados)}")
    print("A calcular indicadores anuais...")

    # O sum ignora as áreas nulas (estimadas), por isso AreaHa só
    # contabiliza a área conhecida
    dados = (
        dados.groupby("Ano")
        .agg(
            Ocorrencias=("Codigo", "count"),
            AreaHa=("AreaTotal", "sum"),
        )
        .reset_index()
    )

    dados["AreaMilHa"] = dados["AreaHa"] / 1000

    DIR_PREPARADOS.mkdir(parents=True, exist_ok=True)

    dados.to_parquet(
        FICHEIRO_EVOLUCAO_ANUAL,
        index=False,
    )

    print("EVOLUÇÃO ANUAL PREPARADA!")
    print(f"Ficheiro: {FICHEIRO_EVOLUCAO_ANUAL}")
    print(f"Anos: {len(dados)}")


def preparar_distribuicao_geo():
    """
    Agrega todas as ocorrências em hexágonos e guarda
    o resultado num dataset preparado para o mapa.
    """
    print("\n" + "=" * 50)
    print("A preparar distribuição geográfica em hexágonos...")

    gdf = gpd.read_parquet(FICHEIRO_FOGOS)

    resultado = agregar_em_hexagonos(gdf)

    resultado.to_parquet(
        FICHEIRO_DISTRIBUICAO_GEO,
        index=False,
    )

    print(f"Hexágonos ocupados: {len(resultado)}")
    print(f"Ficheiro: {FICHEIRO_DISTRIBUICAO_GEO}")

    return resultado


def preparar_distribuicao_geo_recente():
    """
    Agrega em hexágonos apenas os últimos ANOS_RECENTES anos completos,
    para servir de vista por omissão rápida na Distribuição Geográfica.
    """
    print("\n" + "=" * 50)
    print(f"A preparar distribuição geográfica dos últimos {ANOS_RECENTES} anos...")

    gdf = gpd.read_parquet(FICHEIRO_FOGOS)

    # A janela conta com o último ano disponível (ver streamlit_app.py,
    # que usa o mesmo cálculo para decidir se usa este dataset)
    ano_max = gdf["Ano"].max()
    ano_min_recente = ano_max - ANOS_RECENTES + 1

    gdf_recente = gdf[gdf["Ano"] >= ano_min_recente]

    resultado = agregar_em_hexagonos(gdf_recente)

    resultado.to_parquet(FICHEIRO_DISTRIBUICAO_GEO_RECENTE, index=False)

    print(f"Período: {ano_min_recente}-{ano_max}")
    print(f"Hexágonos ocupados: {len(resultado)}")
    print(f"Ficheiro: {FICHEIRO_DISTRIBUICAO_GEO_RECENTE}")

    return resultado


def preparar_previsao_probabilidades():
    """
    Calcula a probabilidade estimada de ocorrência de incêndios por
    concelho e mês e guarda o resultado num dataset preparado para a
    vista de previsão.

    O ano em curso, obtido do relógio do sistema, fica de fora do
    histórico por ter registos incompletos, pelo que o resultado
    depende da data de execução.

    :returns: None.
    """
    print("\n" + "=" * 50)
    print("A calcular probabilidades estimadas por concelho e mês...")

    dados = pd.read_parquet(
        FICHEIRO_FOGOS,
        columns=["Concelho", "Ano", "Mes"],
    )

    # O ano em curso define o histórico (anos anteriores) e o ano previsto (o seguinte)
    ano_atual = datetime.now().year

    resultado = calcular_probabilidades(dados, ano_atual)

    DIR_PREPARADOS.mkdir(parents=True, exist_ok=True)

    resultado.to_parquet(FICHEIRO_PREVISAO_PROBABILIDADES, index=False)

    print(f"Histórico até: {ano_atual - 1}")
    print(f"Combinações concelho-mês: {len(resultado)}")
    print(f"Ficheiro: {FICHEIRO_PREVISAO_PROBABILIDADES}")


def preparar_municipios_caop():
    """
    Simplifica as fronteiras dos municípios da CAOP (tolerância de
    TOLERANCIA_SIMPLIFICACAO_CAOP_M) para aliviar a renderização do mapa
    de previsão e guarda o resultado num dataset preparado.

    A simplificação preserva as fronteiras partilhadas entre concelhos
    vizinhos. É feita em metros (EPSG:3763) e o resultado é guardado
    em EPSG:4326.

    :returns: None.
    """
    print("\n" + "=" * 50)
    print("A simplificar as geometrias dos municípios CAOP...")

    concelhos = gpd.read_parquet(FICHEIRO_CAOP_MUNICIPIOS_BRUTO)
    projetado = concelhos.to_crs("EPSG:3763")

    if not shapely.coverage_is_valid(projetado.geometry.values).all():
        print(
            "Aviso: a cobertura de origem tem sobreposições ou frestas; "
            "a simplificação pode não preservar todas as fronteiras."
        )

    # coverage_simplify trata os municípios em conjunto, por isso os
    # vizinhos continuam a encaixar sem frestas nem sobreposições
    projetado["geometry"] = shapely.coverage_simplify(
        projetado.geometry.values,
        TOLERANCIA_SIMPLIFICACAO_CAOP_M,
    )

    resultado = projetado.to_crs("EPSG:4326")

    DIR_PREPARADOS.mkdir(parents=True, exist_ok=True)

    resultado.to_parquet(FICHEIRO_CAOP_MUNICIPIOS, index=False)

    vertices_antes = int(
        shapely.get_num_coordinates(concelhos.geometry.values).sum()
    )
    vertices_depois = int(
        shapely.get_num_coordinates(resultado.geometry.values).sum()
    )

    print(f"Vértices: {vertices_antes} -> {vertices_depois}")
    print(f"Ficheiro: {FICHEIRO_CAOP_MUNICIPIOS}")


def preparar_todos_datasets():
    """
    Prepara todos os datasets necessários para a dashboard.

    :returns: None.
    """
    preparar_evolucao_anual()
    preparar_distribuicao_geo()
    preparar_distribuicao_geo_recente()
    preparar_previsao_probabilidades()
    preparar_municipios_caop()

    print("\n" + "=" * 50)
    print("TODOS OS DATASETS PREPARADOS!")
    print("=" * 50)