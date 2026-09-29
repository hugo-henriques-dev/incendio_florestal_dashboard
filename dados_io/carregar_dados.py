"""
Funções para carregar os datasets utilizados pela aplicação.
"""

from io import BytesIO
from urllib.request import Request, urlopen

import geopandas as gpd
import pandas as pd
import streamlit as st

from constantes import (
    BUCKET_SUPABASE,
    FICHEIRO_DISTRIBUICAO_GEO,
    FICHEIRO_DISTRIBUICAO_GEO_RECENTE,
    FICHEIRO_EVOLUCAO_ANUAL,
    FICHEIRO_SAIDA,
)


def _obter_url_publica(nome_ficheiro: str) -> str | None:
    """
    Constrói o URL público de um ficheiro no Supabase Storage.

    :param nome_ficheiro: Nome do ficheiro no bucket.
    :returns: URL público do ficheiro, ou None se o Supabase não estiver
        configurado.
    """
    url_supabase = st.secrets.get("SUPABASE_URL")

    if not url_supabase:
        return None

    return (
        f"{url_supabase.rstrip('/')}"
        f"/storage/v1/object/public/{BUCKET_SUPABASE}/{nome_ficheiro}"
    )


def _descarregar_ficheiro(nome_ficheiro: str) -> BytesIO:
    """
    Descarrega um ficheiro do Supabase Storage para memória.

    :param nome_ficheiro: Nome do ficheiro no bucket.
    :returns: Conteúdo do ficheiro em memória.
    :raises RuntimeError: Se o ficheiro não puder ser descarregado.
    """
    url = _obter_url_publica(nome_ficheiro)

    if not url:
        raise RuntimeError(
            "SUPABASE_URL não está definida nos secrets."
        )

    pedido = Request(
        url,
        headers={"User-Agent": "Incendios-Florestais-PT"},
    )

    try:
        with urlopen(pedido, timeout=120) as resposta:
            return BytesIO(resposta.read())
    except Exception as erro:
        raise RuntimeError(
            f"Não foi possível descarregar '{nome_ficheiro}' "
            "do Supabase Storage."
        ) from erro


@st.cache_data
def carregar_ocorrencias():
    """
    Carrega o dataset de ocorrências.

    Usa o ficheiro local quando disponível; caso contrário, usa o
    Supabase Storage.

    :returns: GeoDataFrame com as ocorrências.
    """
    if FICHEIRO_SAIDA.exists():
        return gpd.read_parquet(FICHEIRO_SAIDA)

    return gpd.read_parquet(_descarregar_ficheiro("fogos.parquet"))


@st.cache_data
def carregar_evolucao_anual():
    """
    Carrega o dataset de evolução anual.

    Usa o ficheiro local quando disponível; caso contrário, usa o
    Supabase Storage.

    :returns: DataFrame com a evolução anual.
    """
    if FICHEIRO_EVOLUCAO_ANUAL.exists():
        return pd.read_parquet(FICHEIRO_EVOLUCAO_ANUAL)

    return pd.read_parquet(
        _descarregar_ficheiro("evolucao_anual.parquet")
    )


@st.cache_data
def carregar_distribuicao_geo():
    """
    Carrega o dataset espacial preparado para a distribuição geográfica
    sem filtros.

    Usa o ficheiro local quando disponível; caso contrário, usa o
    Supabase Storage.

    :returns: GeoDataFrame com a distribuição geográfica.
    """
    if FICHEIRO_DISTRIBUICAO_GEO.exists():
        return gpd.read_parquet(FICHEIRO_DISTRIBUICAO_GEO)

    return gpd.read_parquet(
        _descarregar_ficheiro("distribuicao_geografica.parquet")
    )


@st.cache_data
def carregar_distribuicao_geo_recente():
    """
    Carrega o dataset espacial preparado para os anos mais recentes.

    Usa o ficheiro local quando disponível; caso contrário, usa o
    Supabase Storage.

    :returns: GeoDataFrame com a distribuição geográfica.
    """
    if FICHEIRO_DISTRIBUICAO_GEO_RECENTE.exists():
        return gpd.read_parquet(FICHEIRO_DISTRIBUICAO_GEO_RECENTE)

    return gpd.read_parquet(
        _descarregar_ficheiro(
            "distribuicao_geografica_recente.parquet"
        )
    )