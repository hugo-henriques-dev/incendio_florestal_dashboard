"""
Envia os datasets preparados para o Supabase Storage.
"""

import hashlib
import json
import os
import tomllib
from pathlib import Path

from supabase import create_client

from constantes import BUCKET_SUPABASE, FICHEIROS_SUPABASE, MANIFEST_SUPABASE


def _criar_cliente_supabase():
    """
    Cria o cliente Supabase usando as variáveis de ambiente ou o ficheiro
    .streamlit/secrets.toml.

    :returns: Cliente Supabase configurado ou None se as credenciais
        não estiverem definidas.
    """
    url = os.getenv("SUPABASE_URL")
    chave = os.getenv("SUPABASE_KEY")

    # As variáveis de ambiente têm prioridade; o secrets.toml só
    # preenche o que faltar (útil em execução local)
    if not url or not chave:
        caminho_secrets = (
            Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"
        )

        if caminho_secrets.exists():
            with caminho_secrets.open("rb") as ficheiro:
                secrets = tomllib.load(ficheiro)

            url = url or secrets.get("SUPABASE_URL")
            chave = chave or secrets.get("SUPABASE_KEY")

    if not url or not chave:
        return None

    return create_client(url, chave)


def _enviar_ficheiro(cliente, caminho_ficheiro, nome_ficheiro):
    """
    Envia um ficheiro para o bucket do Supabase Storage.

    :param cliente: Cliente Supabase configurado.
    :param caminho_ficheiro: Caminho local do ficheiro a enviar.
    :param nome_ficheiro: Nome do ficheiro dentro do bucket.
    :returns: None.
    :raises RuntimeError: Se o ficheiro não existir ou o envio falhar.
    """
    if not caminho_ficheiro.exists():
        raise RuntimeError(f"O ficheiro preparado não existe: {caminho_ficheiro}")

    try:
        with caminho_ficheiro.open("rb") as ficheiro:
            cliente.storage.from_(BUCKET_SUPABASE).upload(
                path=nome_ficheiro,
                file=ficheiro,
                file_options={
                    "content-type": "application/octet-stream",
                    "cache-control": "3600",
                    "upsert": "true", # substitui o ficheiro existente
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

    if cliente is None:
        print("Credenciais do Supabase não configuradas. Envio ignorado.")
        return

    print("\n" + "=" * 50)
    print("ENVIO DOS DATASETS PARA O SUPABASE")
    print("=" * 50)

    manifesto = _carregar_manifesto(cliente)
    hashes_locais = _calcular_hashes_locais()
    ficheiros_alterados = _obter_ficheiros_alterados(
        hashes_locais=hashes_locais,
        manifesto=manifesto,
    )

    if not ficheiros_alterados:
        print("\nNenhum dataset foi alterado.")
        print("=" * 50)
        return

    for caminho_ficheiro, nome_ficheiro in ficheiros_alterados:
        print(f"\nA enviar: {nome_ficheiro}")

        _enviar_ficheiro(
            cliente=cliente,
            caminho_ficheiro=caminho_ficheiro,
            nome_ficheiro=nome_ficheiro,
        )

        print(f"Concluído: {nome_ficheiro}")

    # O manifesto só é atualizado depois de todos os envios terem sucesso;
    # se algum falhar, a próxima execução volta a enviar os que faltam
    _guardar_manifesto(
        cliente=cliente,
        manifesto=hashes_locais,
    )

    print("\n" + "=" * 50)
    print("ENVIO CONCLUÍDO!")
    print("=" * 50)


def _calcular_hash(caminho_ficheiro):
    """
    Calcula o hash SHA-256 de um ficheiro.

    :param caminho_ficheiro: Caminho do ficheiro a analisar.
    :returns: Hash SHA-256 do ficheiro.
    :raises RuntimeError: Se o ficheiro não existir ou não puder ser lido.
    """
    if not caminho_ficheiro.exists():
        raise RuntimeError(f"O ficheiro não existe: {caminho_ficheiro}")

    sha256 = hashlib.sha256()

    try:
        with caminho_ficheiro.open("rb") as ficheiro:
            # Lê em blocos de 1 MB para não carregar o ficheiro todo em memória
            for bloco in iter(lambda: ficheiro.read(1024 * 1024), b""):
                sha256.update(bloco)
    except OSError as erro:
        raise RuntimeError(
            f"Não foi possível calcular o hash de '{caminho_ficheiro}'."
        ) from erro

    return sha256.hexdigest()


def _carregar_manifesto(cliente):
    """
    Carrega o manifesto do Supabase Storage.

    Se o manifesto ainda não existir, devolve um dicionário vazio.

    :param cliente: Cliente Supabase configurado.
    :returns: Manifesto com os hashes dos ficheiros.
    :raises RuntimeError: Se o manifesto existir mas não puder ser lido.
    """
    try:
        conteudo = (
            cliente.storage
            .from_(BUCKET_SUPABASE)
            .download(MANIFEST_SUPABASE)
        )
    except Exception as erro:
        mensagem = str(erro).lower()

        # O cliente não distingue "não existe" de outros erros, por isso
        # procura-se no texto da mensagem. Sem manifesto (primeira
        # execução), todos os ficheiros são enviados.
        if any(
            erro in mensagem
            for erro in ("not found", "no such key", "404")
        ):
            return {}

        raise RuntimeError(
            "Não foi possível carregar o manifesto do Supabase Storage."
        ) from erro

    try:
        return json.loads(conteudo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise RuntimeError(
            "O manifesto do Supabase Storage não contém JSON válido."
        ) from erro


def _calcular_hashes_locais():
    """
    Calcula os hashes SHA-256 dos ficheiros locais a enviar.

    :returns: Dicionário com o nome remoto de cada ficheiro e o respetivo hash.
    :raises RuntimeError: Se algum dos ficheiros não existir.
    """
    hashes = {}

    for caminho, nome_ficheiro in FICHEIROS_SUPABASE.items():
        hashes[nome_ficheiro] = _calcular_hash(caminho)

    return hashes


def _obter_ficheiros_alterados(hashes_locais, manifesto):
    """
    Identifica os ficheiros locais que ainda não existem no manifesto
    ou cujo conteúdo foi alterado.

    :param hashes_locais: Hashes SHA-256 dos ficheiros locais.
    :param manifesto: Hashes SHA-256 registados no Supabase.
    :returns: Lista com o caminho local e o nome remoto dos ficheiros
        que devem ser enviados.
    """
    ficheiros_alterados = []

    for caminho_ficheiro, nome_ficheiro in FICHEIROS_SUPABASE.items():
        hash_local = hashes_locais[nome_ficheiro]
        hash_remoto = manifesto.get(nome_ficheiro)

        # hash_remoto é None quando o ficheiro nunca foi enviado
        if hash_remoto != hash_local:
            ficheiros_alterados.append(
                (caminho_ficheiro, nome_ficheiro)
            )

    return ficheiros_alterados


def _guardar_manifesto(cliente, manifesto):
    """
    Guarda o manifesto no Supabase Storage.

    :param cliente: Cliente Supabase configurado.
    :param manifesto: Hashes SHA-256 dos ficheiros enviados.
    :raises RuntimeError: Se o manifesto não puder ser guardado.
    """
    conteudo = json.dumps(
        manifesto,
        indent=4,
        ensure_ascii=False,
    ).encode("utf-8")

    try:
        cliente.storage.from_(BUCKET_SUPABASE).upload(
            path=MANIFEST_SUPABASE,
            file=conteudo,
            file_options={
                "content-type": "application/json",
                "upsert": "true",
            },
        )

    except Exception as erro:
        raise RuntimeError(
            "Não foi possível guardar o manifesto no Supabase Storage."
        ) from erro