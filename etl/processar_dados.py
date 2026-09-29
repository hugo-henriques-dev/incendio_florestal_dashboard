"""
Processa o GeoPackage bruto do ICNF, selecionando e normalizando os campos
necessários para o dashboard.

As regras de limpeza aplicadas aqui resultam da exploração feita em
ferramentas/validar_dados.py.
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
import numpy as np

from constantes import (
    COLUNAS_PADRAO,
    FICHEIRO_GPKG_BRUTO,
    FICHEIRO_SAIDA,
    DIR_PROCESSADOS,
    COLUNAS_AUXILIARES_DURACAO,
    LARGURA_HEXAGONO_KM,
    LIMITE_AREA_HA_SUSPEITO,
    LIMITE_HORAS_SUSPEITO,
    LIMITE_KM_CONCELHO,
)


def carregar_dados_brutos():
    """
    Carrega os campos necessários do GeoPackage bruto do ICNF.

    A geometria nativa da fonte não é lida: está vazia em 92% dos
    registos, pelo que se opta por construir sempre a geometria a
    partir de Lat_4326/Lon_4326 (ver construir_geometria).

    :returns: DataFrame com os campos de COLUNAS_PADRAO e os campos
        auxiliares necessários à normalização.
    """
    colunas = COLUNAS_PADRAO + COLUNAS_AUXILIARES_DURACAO

    return gpd.read_file(
        FICHEIRO_GPKG_BRUTO,
        columns=colunas,
        ignore_geometry=True,
    )


def construir_geometria(df):
    """
    Constrói a geometria a partir de Lat_4326/Lon_4326.

    Regra geral, estes campos estão sempre preenchidos na fonte. Quando
    estão em falta - seja porque a fonte não os forneceu, seja porque
    foram anulados por corrigir_coordenadas_suspeitas - o registo é
    mantido, mas fica sem geometria (None). Isto preserva o registo nas
    contagens e agregações não-geográficas (ex.: evolução anual), só o
    exclui de visualizações espaciais.

    :param df: DataFrame com as colunas Lat_4326 e Lon_4326.
    :returns: GeoDataFrame em EPSG:4326, com geometria None onde não há
        coordenadas válidas.
    """
    mascara_valida = df["Lat_4326"].notna() & df["Lon_4326"].notna()

    geometria = gpd.GeoSeries([None] * len(df), index=df.index, crs="EPSG:4326")
    geometria.loc[mascara_valida] = gpd.points_from_xy(
        df.loc[mascara_valida, "Lon_4326"],
        df.loc[mascara_valida, "Lat_4326"],
    )

    return gpd.GeoDataFrame(df, geometry=geometria, crs="EPSG:4326")


def corrigir_duracao_suspeita(gdf):
    """
    Anula a DuracaoHoras dos registos com padrão de erro de registo.

    Casos com DuracaoHoras > 720h e AreaTotal < 50ha em que
    DH1Intervencao, DHResolucao e DHConclusao estão todos vazios
    mostram um padrão sistemático em que DHFim cai no mesmo dia/hora
    que DHInicio, meses depois.

    :param gdf: GeoDataFrame a corrigir.
    :returns: GeoDataFrame com DuracaoHoras corrigida.
    """
    suspeitos = (
        (gdf["DuracaoHoras"] > LIMITE_HORAS_SUSPEITO)
        & (gdf["AreaTotal"] < LIMITE_AREA_HA_SUSPEITO)
        & gdf["DH1Intervencao"].isna()
        & gdf["DHResolucao"].isna()
        & gdf["DHConclusao"].isna()
    )

    gdf.loc[suspeitos, "DuracaoHoras"] = None

    return gdf


def corrigir_coordenadas_suspeitas(df):
    """
    Anula Lat_4326/Lon_4326 dos registos cuja coordenada está a mais de
    LIMITE_KM_CONCELHO do centro do seu próprio Concelho.

    A referência de cada Concelho é a mediana de Lat_4326/Lon_4326 dos
    seus próprios registos (robusta a outliers). Validado contra os
    centróides oficiais da CAOP2025 (DGT) para vários concelhos, sem
    evidência de contaminação da mediana pelos próprios casos suspeitos
    (ver ferramentas/verificar_referencias_caop.py).

    :param df: DataFrame a corrigir.
    :returns: DataFrame com Lat_4326/Lon_4326 corrigidas.
    """
    com_coordenadas = df.dropna(subset=["Lat_4326", "Lon_4326", "Concelho"])

    referencias = (
        com_coordenadas.groupby("Concelho")[["Lat_4326", "Lon_4326"]]
        .median()
        .rename(columns={"Lat_4326": "Lat_ref", "Lon_4326": "Lon_ref"})
    )

    df = df.join(referencias, on="Concelho")

    dist_km = (
        ((df["Lat_4326"] - df["Lat_ref"]) * 111) ** 2
        + ((df["Lon_4326"] - df["Lon_ref"]) * 85) ** 2
    ) ** 0.5

    suspeitos = dist_km > LIMITE_KM_CONCELHO

    df.loc[suspeitos, ["Lat_4326", "Lon_4326"]] = None

    return df.drop(columns=["Lat_ref", "Lon_ref"])


def agregar_em_hexagonos(gdf):
    """
    Agrega ocorrências em hexágonos regulares.

    A largura do hexágono (de lado a lado) é definida por
    LARGURA_HEXAGONO_KM. A agregação é feita em metros no sistema
    EPSG:3763 e o resultado é devolvido em EPSG:4326.

    :param gdf: GeoDataFrame com as ocorrências e respetivas geometrias.
    :returns: GeoDataFrame com os hexágonos e o número de ocorrências
        em cada um.
    """
    gdf = gdf[gdf.geometry.notna()]

    gdf_proj = gdf.to_crs("EPSG:3763")

    # Para um hexágono flat-top, a largura de lado a lado é 2 * lado.
    lado = (LARGURA_HEXAGONO_KM * 1000) / 2

    x = gdf_proj.geometry.x.to_numpy()
    y = gdf_proj.geometry.y.to_numpy()

    # Coordenadas axiais do sistema hexagonal.
    q = (2 / 3) * x / lado
    r = (-1 / 3 * x + np.sqrt(3) / 3 * y) / lado
    s = -q - r

    # Arredondamento de coordenadas cúbicas para obter o hexágono.
    q_round = np.rint(q)
    r_round = np.rint(r)
    s_round = np.rint(s)

    dq = np.abs(q_round - q)
    dr = np.abs(r_round - r)
    ds = np.abs(s_round - s)

    q_final = q_round.copy()
    r_final = r_round.copy()

    mascara_q = (dq > dr) & (dq > ds)
    mascara_r = (dr > dq) & (dr > ds)

    q_final[mascara_q] = -r_round[mascara_q] - s_round[mascara_q]
    r_final[mascara_r] = -q_round[mascara_r] - s_round[mascara_r]

    gdf_proj["hex_q"] = q_final.astype(int)
    gdf_proj["hex_r"] = r_final.astype(int)

    agregados = (
        gdf_proj
        .groupby(["hex_q", "hex_r"])
        .size()
        .reset_index(name="Ocorrencias")
    )

    # Centro de cada hexágono.
    agregados["CentroX"] = lado * 1.5 * agregados["hex_q"]

    agregados["CentroY"] = (
        lado
        * np.sqrt(3)
        * (agregados["hex_r"] + agregados["hex_q"] / 2)
    )

    geometrias = []

    for x_centro, y_centro in zip(
        agregados["CentroX"],
        agregados["CentroY"],
    ):
        angulos = np.arange(0, 360, 60)
        vertices = [
            (
                x_centro + lado * np.cos(np.radians(angulo)),
                y_centro + lado * np.sin(np.radians(angulo)),
            )
            for angulo in angulos
        ]

        geometrias.append(Polygon(vertices))

    return gpd.GeoDataFrame(
        agregados[["Ocorrencias"]],
        geometry=geometrias,
        crs="EPSG:3763",
    ).to_crs("EPSG:4326")


def classificar_fwi(valor):
    """
    Classifica um valor do Fire Weather Index (FWI) segundo os níveis
    de perigo definidos para o dashboard.

    :param valor: Valor numérico do FWI.
    :returns: Classe de perigo correspondente ou None quando o valor
        está em falta.
    """
    if pd.isna(valor):
        return None
    if valor < 9.5:
        return "Baixo"
    if valor < 18.3:
        return "Moderado"
    if valor < 25.3:
        return "Elevado"
    if valor < 39:
        return "Muito Elevado"
    return "Extremo"


def processar_dados():
    """
    Processa o GeoPackage bruto do ICNF e guarda o dataset normalizado.

    :returns: GeoDataFrame processado.
    """
    print("\n" + "=" * 50)
    print("A carregar dados brutos...")
    df = carregar_dados_brutos()
    print(f"Registos brutos: {len(df)}")
    
    df["Ano"] = df["Ano"].astype(int)
    df["Mes"] = df["Mes"].astype(int)

    print("A construir geometria a partir de Lat_4326/Lon_4326...")
    df = corrigir_coordenadas_suspeitas(df)
    gdf = construir_geometria(df)

    # AreaTotal = 0 corresponde, em 99.8% dos casos, a uma área estimada
    # (marcada como "Estimated" em Observacoes, não confirmada por medição
    # direta; 12% destes casos estão ainda marcados como "anomaly") -
    # origem exata da estimativa (terreno ou satélite) não determinada.
    # Mantém-se o registo, mas a área passa a NULL.
    areas_estimadas = gdf["AreaTotal"] == 0
    gdf.loc[areas_estimadas, ["AreaTotal", "AreaPov", "AreaMato", "AreaAgric"]] = None

    gdf = corrigir_duracao_suspeita(gdf)
    gdf = gdf.drop(columns=["Lat_4326", "Lon_4326"] + COLUNAS_AUXILIARES_DURACAO)

    DIR_PROCESSADOS.mkdir(parents=True, exist_ok=True)
    
    gdf["ClasseFWI"] = df["fwi"].apply(classificar_fwi)

    gdf.to_parquet(FICHEIRO_SAIDA, index=False)

    print("\nDADOS PROCESSADOS!")
    print(f"Ficheiro: {FICHEIRO_SAIDA}")
    print(f"Registos finais: {len(gdf)}")
    print(f"Registos sem geometria válida: {gdf.geometry.isna().sum()}")

    return gdf