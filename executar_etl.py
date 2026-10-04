"""
Executa o processo ETL dos dados de incêndios florestais.

Coordena a obtenção, o processamento e a preparação dos dados,
bem como a sua sincronização com o Supabase Storage.
"""

from constantes import FICHEIROS_SUPABASE as FICHEIROS_PREPARADOS
from dados_io.enviar_dados import enviar_dados_supabase
from etl.obter_dados import extrair_dados
from etl.preparar_datasets import preparar_todos_datasets
from etl.processar_dados import processar_dados


def main():
    """
    Executa todas as etapas do processo ETL e sincroniza os datasets preparados.
    O processamento dos dados só é realizado quando existem novos dados ou quando
    os ficheiros preparados não estão disponíveis.

    :returns: None.
    """
    dados_atualizados = extrair_dados()

    # Reprocessa se houver dados novos ou se faltar algum ficheiro preparado
    if dados_atualizados or not all(
        ficheiro.exists()
        for ficheiro in FICHEIROS_PREPARADOS
    ):
        processar_dados()
        preparar_todos_datasets()

    enviar_dados_supabase()


if __name__ == "__main__":
    main()