"""
Prepara os datasets derivados necessários para o dashboard.
"""

import geopandas as gpd
import pandas as pd

from constantes import (
    FICHEIRO_SAIDA,
    DIR_PREPARADOS,
    FICHEIRO_EVOLUCAO_ANUAL,
    FICHEIRO_DISTRIBUICAO_GEO,
    FICHEIRO_DISTRIBUICAO_GEO_RECENTE,
    ANOS_RECENTES
)
from etl.processar_dados import agregar_em_hexagonos


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
        FICHEIRO_SAIDA,
        columns=["Codigo", "Ano", "AreaTotal"],
    )

    print(f"Ocorrências carregadas: {len(dados)}")
    print("A calcular indicadores anuais...")

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

    gdf = gpd.read_parquet(FICHEIRO_SAIDA)

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

    gdf = gpd.read_parquet(FICHEIRO_SAIDA)

    ano_max = gdf["Ano"].max()
    ano_min_recente = ano_max - ANOS_RECENTES + 1

    gdf_recente = gdf[gdf["Ano"] >= ano_min_recente]

    resultado = agregar_em_hexagonos(gdf_recente)

    resultado.to_parquet(FICHEIRO_DISTRIBUICAO_GEO_RECENTE, index=False)

    print(f"Período: {ano_min_recente}-{ano_max}")
    print(f"Hexágonos ocupados: {len(resultado)}")
    print(f"Ficheiro: {FICHEIRO_DISTRIBUICAO_GEO_RECENTE}")

    return resultado


def preparar_todos_datasets():
    """
    Prepara todos os datasets necessários para a dashboard.

    :returns: None.
    """
    preparar_evolucao_anual()
    preparar_distribuicao_geo()
    preparar_distribuicao_geo_recente()
    
    print("\n" + "=" * 50)
    print("TODOS OS DATASETS PREPARADOS!")
    print("=" * 50)