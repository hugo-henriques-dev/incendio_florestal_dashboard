"""
Processa o GeoPackage bruto do ICNF, normalizando os campos necessários
para o dashboard, e disponibiliza as funções de agregação em hexágonos
e de classificação do FWI.

As regras de limpeza aplicadas aqui resultam da exploração feita em
ferramentas/validar_dados.py.
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from constantes import (
    COLUNAS_AUXILIARES_DURACAO,
    COLUNAS_PADRAO,
    DIR_PROCESSADOS,
    FICHEIRO_GPKG_BRUTO,
    FICHEIRO_FOGOS,
    LARGURA_HEXAGONO_KM,
    LIMITE_AREA_HA_SUSPEITO,
    LIMITE_HORAS_SUSPEITO,
    LIMITE_KM_CONCELHO
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

    # Parte de tudo a None e só preenche os registos com coordenadas
    geometria = gpd.GeoSeries([None] * len(df), index=df.index, crs="EPSG:4326")
    geometria.loc[mascara_valida] = gpd.points_from_xy(
        df.loc[mascara_valida, "Lon_4326"],
        df.loc[mascara_valida, "Lat_4326"],
    )

    return gpd.GeoDataFrame(df, geometry=geometria, crs="EPSG:4326")


def corrigir_duracao_suspeita(gdf):
    """
    Anula a DuracaoHoras dos registos com padrão de erro de registo.

    Um registo é suspeito quando:

    - DuracaoHoras excede LIMITE_HORAS_SUSPEITO;
    - AreaTotal é inferior a LIMITE_AREA_HA_SUSPEITO;
    - DH1Intervencao, DHResolucao e DHConclusao estão todos vazios.

    Nestes casos, DHFim cai sistematicamente no mesmo dia/hora que
    DHInicio, meses depois.

    Altera o GeoDataFrame recebido e devolve o mesmo objeto.

    :param gdf: GeoDataFrame a corrigir.
    :returns: O próprio GeoDataFrame, com DuracaoHoras corrigida.
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

    Não altera o DataFrame recebido: devolve um novo.

    :param df: DataFrame a corrigir.
    :returns: Novo DataFrame com Lat_4326/Lon_4326 corrigidas.
    """
    com_coordenadas = df.dropna(subset=["Lat_4326", "Lon_4326", "Concelho"])

    referencias = (
        com_coordenadas.groupby("Concelho")[["Lat_4326", "Lon_4326"]]
        .median()
        .rename(columns={"Lat_4326": "Lat_ref", "Lon_4326": "Lon_ref"})
    )

    df = df.join(referencias, on="Concelho")

    # Distância aproximada em km: 1° de latitude ≈ 111 km e 1° de longitude
    # ≈ 85 km à latitude de Portugal continental
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
    pontos = gdf.geometry[gdf.geometry.notna()].to_crs("EPSG:3763")

    # Para um hexágono flat-top, a largura de lado a lado é 2 * lado.
    lado = (LARGURA_HEXAGONO_KM * 1000) / 2

    # ====== Atribuição de cada ocorrência a um hexágono ======
    x = pontos.x.to_numpy()
    y = pontos.y.to_numpy()

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

    # Recalcula a coordenada com maior erro de arredondamento, para
    # manter q + r + s = 0
    mascara_q = (dq > dr) & (dq > ds)
    mascara_r = (dr > dq) & (dr > ds)

    q_final[mascara_q] = -r_round[mascara_q] - s_round[mascara_q]
    r_final[mascara_r] = -q_round[mascara_r] - s_round[mascara_r]

    # ====== Contagem e geometria dos hexágonos ======
    agregados = (
        pd.DataFrame({
            "hex_q": q_final.astype(int),
            "hex_r": r_final.astype(int),
        })
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

    # Vértices de todos os hexágonos de uma vez: um array (n, 6, 2)
    angulos = np.radians(np.arange(0, 360, 60))
    vertices_x = agregados["CentroX"].to_numpy()[:, None] + lado * np.cos(angulos)
    vertices_y = agregados["CentroY"].to_numpy()[:, None] + lado * np.sin(angulos)

    geometrias = shapely.polygons(np.stack([vertices_x, vertices_y], axis=-1))

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

    # As coordenadas suspeitas são anuladas antes de construir a geometria,
    # para que esses registos fiquem sem geometria
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

    gdf.to_parquet(FICHEIRO_FOGOS, index=False)

    print("\nDADOS PROCESSADOS!")
    print(f"Ficheiro: {FICHEIRO_FOGOS}")
    print(f"Registos finais: {len(gdf)}")
    print(f"Registos sem geometria válida: {gdf.geometry.isna().sum()}")

    return gdf