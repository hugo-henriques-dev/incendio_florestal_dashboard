"""
Controla a extração dos dados de fontes externas: as ocorrências
disponibilizadas pelo ICNF e os municípios da CAOP (DGT).
"""

from datetime import datetime, timezone

from constantes import (
    FICHEIRO_CAOP_MUNICIPIOS_BRUTO,
    FICHEIRO_GPKG_BRUTO,
    URL_FOGOS_GPKG
)
from etl.descarregar_caop import descarregar_municipios_caop
from etl.descarregar_fogos import (
    carregar_metadados,
    descarregar_gpkg,
    fonte_foi_atualizada,
    guardar_metadados,
    obter_metadados_remotos
)


def extrair_dados():
    """
    Obtém os dados de que o ETL precisa: os municípios da CAOP e o
    GeoPackage do ICNF.

    Os municípios da CAOP2025 são uma edição fixa, por isso só são
    obtidos quando o ficheiro local não existe. Para os gerar de novo
    (por exemplo, depois de alterar TOLERANCIA_SIMPLIFICACAO_CAOP_M),
    basta apagar o ficheiro.

    Em relação ao GeoPackage, verifica se o ficheiro disponibilizado pelo
    ICNF foi alterado. Quando não há alterações e o ficheiro local
    existe, não faz qualquer download. Quando existe uma nova versão,
    descarrega-a e atualiza os metadados locais.

    :returns: True se o GeoPackage foi descarregado, False se foi
        reutilizado o ficheiro local. Os municípios da CAOP não entram
        neste valor.
    :raises RuntimeError: Se não for possível consultar ou descarregar
        alguma das fontes.
    :raises ValueError: Se a resposta da API da CAOP não passar a
        validação.
    """
    # A CAOP2025 é uma edição fixa, por isso só se obtém quando falta.
    # Fica antes da verificação do ICNF, que pode terminar logo com return
    if FICHEIRO_CAOP_MUNICIPIOS_BRUTO.exists():
        print("Os municípios da CAOP já existem.")
        print("Não é necessário descarregar novamente.")
    else:
        descarregar_municipios_caop()

    ficheiro_metadados = FICHEIRO_GPKG_BRUTO.with_suffix(".meta.json")

    print("A verificar a versão disponibilizada pelo ICNF...")

    metadados_remotos = obter_metadados_remotos(URL_FOGOS_GPKG)
    metadados_locais = carregar_metadados(ficheiro_metadados)

    # None = sem metadados suficientes para comparar versões
    atualizada = fonte_foi_atualizada(
        metadados_locais,
        metadados_remotos,
    )

    # Só salta o download se a fonte não mudou E o ficheiro local existe
    if atualizada is False and FICHEIRO_GPKG_BRUTO.exists():
        print("A fonte não sofreu alterações.")
        print("Não é necessário descarregar novamente.")
        return False

    if atualizada is None:
        print(
            "Não existem metadados locais suficientes para "
            "confirmar a versão. Será feito um novo download."
        )
    else:
        print("Foi detetada uma nova versão.")

    descarregar_gpkg(
        URL_FOGOS_GPKG,
        FICHEIRO_GPKG_BRUTO,
        metadados_remotos,
    )

    # Guarda os metadados remotos para comparar na próxima execução
    guardar_metadados(
        ficheiro_metadados,
        {
            **metadados_remotos,
            "downloaded_at": datetime.now(
                timezone.utc
            ).isoformat(),
        },
    )

    print("TRANSFERÊNCIA CONCLUÍDA COM SUCESSO!")
    print(f"Localização: {FICHEIRO_GPKG_BRUTO}")

    return True