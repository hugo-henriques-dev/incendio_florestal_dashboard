"""
Controla a extração dos dados disponibilizados pelo ICNF.
"""

from datetime import datetime, timezone

from constantes import FICHEIRO_GPKG_BRUTO, URL_FOGOS_GPKG
from etl.download import (
    carregar_metadados,
    descarregar_gpkg,
    fonte_foi_atualizada,
    guardar_metadados,
    obter_metadados_remotos
)


def extrair_dados():
    """
    Verifica se o GeoPackage disponibilizado pelo ICNF foi alterado.

    Quando não há alterações e o ficheiro local existe, não faz qualquer
    download. Quando existe uma nova versão, descarrega-a e atualiza os
    metadados locais.

    :returns: True se o ficheiro foi descarregado, False se foi reutilizado
        o ficheiro local.
    :raises RuntimeError: Se não for possível consultar ou descarregar
        a fonte.
    """
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