"""
Executa todas as etapas do processo ETL.
"""

from dados_io.enviar_dados import enviar_dados_supabase
from etl.obter_dados import extrair_dados
from etl.processar_dados import processar_dados
from etl.preparar_datasets import preparar_todos_datasets


def main():
    """
    Executa todas as etapas do processo ETL.

    :returns: None.
    """
    extrair_dados()
    processar_dados()
    preparar_todos_datasets()
    enviar_dados_supabase()


if __name__ == "__main__":
    main()