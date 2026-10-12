"""
Obtém os municípios da CAOP2025 (DGT) através da API OGC, valida-os e
guarda-os.
"""

from time import sleep

import geopandas as gpd
import requests
import shapely

from constantes import (
    ESPERA_ENTRE_PAGINAS_CAOP,
    ESTADOS_REPETIVEIS_CAOP,
    FICHEIRO_CAOP_MUNICIPIOS_BRUTO,
    TAMANHO_PAGINA_CAOP,
    TENTATIVAS_DOWNLOAD,
    TIMEOUT_CAOP,
    TOTAL_MUNICIPIOS_CAOP,
    URL_CAOP_MUNICIPIOS
)


def _obter_pagina(offset):
    """
    Obtém uma página de municípios da API OGC da DGT.

    Repete o pedido, com espera exponencial (2s, 4s...), quando o
    servidor devolve um erro temporário (ESTADOS_REPETIVEIS_CAOP) ou a
    ligação falha.

    :param offset: Posição do primeiro município da página.
    :returns: Dicionário GeoJSON com as features da página.
    :raises requests.HTTPError: Se o servidor devolver um erro que não
        é temporário.
    :raises RuntimeError: Se as tentativas se esgotarem.
    """
    parametros = {
        "f": "json",
        "lang": "pt-PT",
        "limit": TAMANHO_PAGINA_CAOP,
        "offset": offset,
        # Só os campos usados: código e nome do município
        "properties": "dtmn,municipio",
        "crs": "http://www.opengis.net/def/crs/EPSG/0/4326",
    }

    for tentativa in range(TENTATIVAS_DOWNLOAD):
        try:
            resposta = requests.get(
                URL_CAOP_MUNICIPIOS,
                params=parametros,
                timeout=TIMEOUT_CAOP,
            )

            # Transforma o erro temporário numa exceção, para entrar
            # no except abaixo e ser repetido
            if resposta.status_code in ESTADOS_REPETIVEIS_CAOP:
                raise requests.HTTPError(
                    f"HTTP {resposta.status_code}",
                    response=resposta,
                )

            resposta.raise_for_status()

            return resposta.json()

        except requests.exceptions.HTTPError as erro:
            status = (
                erro.response.status_code
                if erro.response is not None
                else None
            )

            # Erros que não são temporários (ex.: 404) não se repetem
            if status not in ESTADOS_REPETIVEIS_CAOP:
                raise

            ultima_tentativa = tentativa == TENTATIVAS_DOWNLOAD - 1

            if ultima_tentativa:
                raise RuntimeError(
                    f"Falha ao obter a página com offset={offset} "
                    f"após {TENTATIVAS_DOWNLOAD} tentativas."
                ) from erro

            espera = 2 ** (tentativa + 1)

            print(
                f"Falha HTTP {status} no offset {offset}. "
                f"Nova tentativa em {espera}s..."
            )
            sleep(espera)

        except (
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as erro:

            ultima_tentativa = tentativa == TENTATIVAS_DOWNLOAD - 1

            if ultima_tentativa:
                raise RuntimeError(
                    f"Falha ao obter a página com offset={offset} "
                    f"após {TENTATIVAS_DOWNLOAD} tentativas."
                ) from erro

            espera = 2 ** (tentativa + 1)

            print(
                f"Falha de ligação no offset {offset}: {erro}. "
                f"Nova tentativa em {espera}s..."
            )
            sleep(espera)


def _obter_municipios():
    """
    Obtém todos os municípios da API, página a página.

    :returns: Dicionário GeoJSON (FeatureCollection) com os municípios.
    :raises RuntimeError: Se alguma página não puder ser obtida.
    """
    features = []
    offset = 0

    while True:
        dados = _obter_pagina(offset)
        pagina = dados.get("features", [])

        features.extend(pagina)

        print(
            f"Features obtidas: {len(features)} "
            f"(página: {len(pagina)})"
        )

        # Uma página incompleta é a última
        if len(pagina) < TAMANHO_PAGINA_CAOP:
            break

        offset += TAMANHO_PAGINA_CAOP
        sleep(ESPERA_ENTRE_PAGINAS_CAOP)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def _validar_municipios(geojson):
    """
    Valida a resposta da API e devolve os municípios num GeoDataFrame.

    Confirma o número de municípios (TOTAL_MUNICIPIOS_CAOP), a presença
    dos campos dtmn e municipio, a ausência de geometrias nulas ou
    vazias e a unicidade de dtmn e municipio (a view de previsão junta
    por municipio com validate="1:1"). Corrige ainda a inversão dos
    eixos das coordenadas.

    :param geojson: FeatureCollection devolvida por _obter_municipios.
    :returns: GeoDataFrame em EPSG:4326, com os campos dtmn e municipio.
    :raises ValueError: Se alguma validação falhar.
    """
    concelhos = gpd.GeoDataFrame.from_features(
        geojson["features"],
        crs="EPSG:4326",
    )

    numero_municipios = len(concelhos)

    if numero_municipios != TOTAL_MUNICIPIOS_CAOP:
        raise ValueError(
            f"Número inesperado de municípios: "
            f"{numero_municipios} "
            f"(esperado: {TOTAL_MUNICIPIOS_CAOP})"
        )

    campos_obrigatorios = {"dtmn", "municipio"}
    campos_em_falta = campos_obrigatorios - set(concelhos.columns)

    if campos_em_falta:
        raise ValueError(
            f"Campos em falta na resposta da API: "
            f"{', '.join(sorted(campos_em_falta))}"
        )

    if concelhos.geometry.isna().any():
        raise ValueError("Existem geometrias nulas.")

    if concelhos.geometry.is_empty.any():
        raise ValueError("Existem geometrias vazias.")

    duplicados = concelhos["dtmn"].duplicated().sum()

    if duplicados:
        raise ValueError(
            f"Existem {duplicados} códigos dtmn duplicados."
        )

    if concelhos["municipio"].duplicated().any():
        raise ValueError(
            "Existem municípios com nomes duplicados."
        )

    # A API devolve as coordenadas com os eixos invertidos
    # relativamente à orientação esperada pelo GeoPandas/Shapely.
    geometrias_corrigidas = shapely.transform(
        concelhos.geometry.values,
        lambda coordenadas: coordenadas[:, ::-1],
    )

    concelhos = concelhos.set_geometry(geometrias_corrigidas)

    return concelhos


def _guardar_parquet(concelhos):
    """
    Guarda os municípios em FICHEIRO_CAOP_MUNICIPIOS_BRUTO através de uma
    escrita atómica.

    :param concelhos: GeoDataFrame dos municípios a guardar.
    :returns: None.
    """
    FICHEIRO_CAOP_MUNICIPIOS_BRUTO.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ficheiro_temporario = FICHEIRO_CAOP_MUNICIPIOS_BRUTO.with_name(
        f"{FICHEIRO_CAOP_MUNICIPIOS_BRUTO.name}.tmp"
    )

    # Escreve num ficheiro temporário e só depois substitui o original
    concelhos.to_parquet(
        ficheiro_temporario,
        index=False,
    )

    ficheiro_temporario.replace(FICHEIRO_CAOP_MUNICIPIOS_BRUTO)


def descarregar_municipios_caop():
    """
    Obtém os municípios da CAOP2025 através da API da DGT, valida-os e
    guarda o resultado em FICHEIRO_CAOP_MUNICIPIOS_BRUTO, substituindo o
    ficheiro existente.

    :returns: None.
    :raises RuntimeError: Se não for possível obter os municípios.
    :raises ValueError: Se a resposta da API não passar a validação.
    """
    print("\n" + "=" * 50)
    print("A obter municípios CAOP2025...")

    geojson = _obter_municipios()

    concelhos = _validar_municipios(geojson)

    _guardar_parquet(concelhos)

    print("MUNICÍPIOS CAOP DESCARREGADOS!")
    print(f"Ficheiro: {FICHEIRO_CAOP_MUNICIPIOS_BRUTO}")
    print(f"Municípios: {len(concelhos)}")