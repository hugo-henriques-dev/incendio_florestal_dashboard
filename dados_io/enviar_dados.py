"""
Envia os datasets preparados para o Supabase Storage.
"""

import os
from pathlib import Path
import tomllib

from supabase import Client, create_client

from constantes import (
    BUCKET_SUPABASE,
    FICHEIROS_SUPABASE,
)


def _criar_cliente_supabase() -> Client:
    """
    Cria o cliente Supabase usando as variáveis de ambiente ou o ficheiro
    .streamlit/secrets.toml.

    :returns: Cliente Supabase configurado.
    :raises RuntimeError: Se as credenciais não estiverem definidas.
    """
    url = os.getenv("SUPABASE_URL")
    chave = os.getenv("SUPABASE_KEY")

    if not url or not chave:
        caminho_secrets = (
            Path(__file__).resolve().parent.parent
            / ".streamlit"
            / "secrets.toml"
        )

        if caminho_secrets.exists():
            with caminho_secrets.open("rb") as ficheiro:
                secrets = tomllib.load(ficheiro)

            url = url or secrets.get("SUPABASE_URL")
            chave = chave or secrets.get("SUPABASE_KEY")

    if not url:
        raise RuntimeError("SUPABASE_URL não está definida.")

    if not chave:
        raise RuntimeError("SUPABASE_KEY não está definida.")

    return create_client(url, chave)


def _enviar_ficheiro(
    cliente: Client,
    caminho_ficheiro: Path,
    nome_ficheiro: str,
) -> None:
    """
    Envia um ficheiro para o bucket do Supabase Storage.

    :param cliente: Cliente Supabase configurado.
    :param caminho_ficheiro: Caminho local do ficheiro a enviar.
    :param nome_ficheiro: Nome do ficheiro dentro do bucket.
    :returns: None.
    :raises RuntimeError: Se o ficheiro não existir ou o envio falhar.
    """
    if not caminho_ficheiro.exists():
        raise RuntimeError(
            f"O ficheiro preparado não existe: {caminho_ficheiro}"
        )

    try:
        with caminho_ficheiro.open("rb") as ficheiro:
            cliente.storage.from_(BUCKET_SUPABASE).upload(
                path=nome_ficheiro,
                file=ficheiro,
                file_options={
                    "content-type": "application/octet-stream",
                    "cache-control": "3600",
                    "upsert": "true",
                },
            )
    except Exception as erro:
        raise RuntimeError(
            f"Erro ao enviar '{nome_ficheiro}' para o Supabase Storage."
        ) from erro


def enviar_dados_supabase():
    """
    Envia os datasets preparados para o Supabase Storage.

    :returns: None.
    :raises RuntimeError: Se ocorrer um erro durante o envio.
    """
    cliente = _criar_cliente_supabase()

    print("\n" + "=" * 50)
    print("ENVIO DOS DATASETS PARA O SUPABASE")
    print("=" * 50)

    for caminho_ficheiro, nome_ficheiro in FICHEIROS_SUPABASE.items():
        print(f"\nA enviar: {nome_ficheiro}")

        _enviar_ficheiro(
            cliente=cliente,
            caminho_ficheiro=caminho_ficheiro,
            nome_ficheiro=nome_ficheiro,
        )

        print(f"Concluído: {nome_ficheiro}")

    print("\n" + "=" * 50)
    print("TODOS OS DATASETS ENVIADOS!")
    print("=" * 50)