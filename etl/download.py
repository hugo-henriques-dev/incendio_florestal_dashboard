"""
Funções para obtenção, transferência e validação dos ficheiros de dados.
"""

import json
import os
import sqlite3
from pathlib import Path
from time import sleep

import requests
from tqdm import tqdm

from constantes import (
    HEADERS_DOWNLOAD,
    TIMEOUT_DOWNLOAD,
    TENTATIVAS_DOWNLOAD,
    CHUNK_SIZE_DOWNLOAD,
)


# -------------------------------------------------------------------------
# Verificação da fonte
# -------------------------------------------------------------------------

def obter_metadados_remotos(url):
    """
    Obtém os metadados da versão atualmente disponibilizada no servidor.

    O servidor do ICNF suporta pedidos HEAD e disponibiliza ETag,
    Last-Modified e Content-Length.

    :param url: URL da fonte.
    :returns: Dicionário com URL, ETag, Last-Modified e tamanho.
    :raises RuntimeError: Se não for possível consultar a fonte.
    """
    try:
        resposta = requests.head(
            url,
            headers=HEADERS_DOWNLOAD,
            timeout=(30, 60),
            allow_redirects=True,
        )

        resposta.raise_for_status()

        tamanho = resposta.headers.get("Content-Length")

        return {
            "url": resposta.url,
            "etag": resposta.headers.get("ETag"),
            "last_modified": resposta.headers.get("Last-Modified"),
            "content_length": (
                int(tamanho)
                if tamanho is not None
                else None
            ),
        }

    except requests.RequestException as erro:
        raise RuntimeError(
            "Não foi possível consultar os metadados do ficheiro "
            "disponibilizado pelo ICNF."
        ) from erro

    finally:
        if "resposta" in locals():
            resposta.close()


def carregar_metadados(caminho):
    """
    Carrega os metadados guardados num ficheiro JSON.

    :param caminho: Caminho do ficheiro de metadados.
    :returns: Dicionário com os metadados ou None quando não existem
        metadados válidos.
    """
    if not caminho.exists():
        return None

    try:
        with open(caminho, "r", encoding="utf-8") as ficheiro:
            return json.load(ficheiro)

    except (OSError, json.JSONDecodeError):
        return None


def guardar_metadados(caminho, metadados):
    """
    Guarda metadados num ficheiro JSON através de uma escrita atómica.

    :param caminho: Caminho do ficheiro de metadados.
    :param metadados: Dicionário com os metadados a guardar.
    """
    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ficheiro_temporario = Path(f"{caminho}.part")

    with open(ficheiro_temporario, "w", encoding="utf-8") as ficheiro:
        json.dump(
            metadados,
            ficheiro,
            ensure_ascii=False,
            indent=2,
        )

        ficheiro.flush()
        os.fsync(ficheiro.fileno())

    os.replace(ficheiro_temporario, caminho)


def fonte_foi_atualizada(metadados_locais, metadados_remotos):
    """
    Determina se a versão remota é diferente da versão local.

    O ETag é utilizado como identificador principal da versão. O tamanho
    é usado como verificação complementar. Quando não existe ETag,
    utiliza-se Last-Modified e, quando disponível, o tamanho.

    :param metadados_locais: Metadados da versão local.
    :param metadados_remotos: Metadados da versão remota.
    :returns: True se a versão remota for diferente, False se for igual,
        ou None quando não é possível determinar.
    """
    if metadados_locais is None:
        return None

    etag_local = metadados_locais.get("etag")
    etag_remoto = metadados_remotos.get("etag")

    tamanho_local = metadados_locais.get("content_length")
    tamanho_remoto = metadados_remotos.get("content_length")

    last_modified_local = metadados_locais.get("last_modified")
    last_modified_remoto = metadados_remotos.get("last_modified")

    # O ICNF disponibiliza ETag, pelo que esta é a comparação principal.
    if etag_local and etag_remoto:
        if etag_local != etag_remoto:
            return True

        if (
            tamanho_local is not None
            and tamanho_remoto is not None
            and tamanho_local != tamanho_remoto
        ):
            return True

        return False

    # Fallback para Last-Modified.
    if last_modified_local and last_modified_remoto:
        if last_modified_local != last_modified_remoto:
            return True

        if (
            tamanho_local is not None
            and tamanho_remoto is not None
            and tamanho_local != tamanho_remoto
        ):
            return True

        return False

    # Último recurso: comparar apenas o tamanho.
    if (
        tamanho_local is not None
        and tamanho_remoto is not None
    ):
        return tamanho_local != tamanho_remoto

    return None


# -------------------------------------------------------------------------
# Download e validação
# -------------------------------------------------------------------------

def validar_tamanho(ficheiro, tamanho_esperado):
    """
    Confirma que o ficheiro tem o tamanho esperado segundo a resposta
    do servidor.

    :param ficheiro: Caminho do ficheiro a validar.
    :param tamanho_esperado: Tamanho esperado em bytes ou None quando
        não foi disponibilizado pelo servidor.
    :raises RuntimeError: Se o tamanho real for diferente do esperado.
    """
    if tamanho_esperado is None:
        return

    tamanho_real = ficheiro.stat().st_size

    if tamanho_real != tamanho_esperado:
        raise RuntimeError(
            f"Download incompleto: {tamanho_real:,} bytes "
            f"em vez de {tamanho_esperado:,}."
        )


def validar_geopackage(ficheiro):
    """
    Valida a integridade básica do GeoPackage como base de dados SQLite.

    Confirma o identificador de aplicação do GeoPackage e executa uma
    verificação de integridade da base de dados.

    :param ficheiro: Caminho do GeoPackage a validar.
    :raises RuntimeError: Se o ficheiro não for um GeoPackage válido
        ou apresentar corrupção.
    """
    base_dados = None

    try:
        caminho_uri = (f"file:{ficheiro.resolve()}?mode=ro")

        base_dados = sqlite3.connect(
            caminho_uri,
            uri=True,
        )

        application_id = base_dados.execute(
            "PRAGMA application_id;"
        ).fetchone()[0]

        if application_id != 0x47504B47:
            raise RuntimeError(
                "O ficheiro descarregado não parece ser "
                "um GeoPackage válido."
            )

        resultado = base_dados.execute(
            "PRAGMA integrity_check;"
        ).fetchone()[0]

        if resultado != "ok":
            raise RuntimeError(
                "O GeoPackage falhou a verificação de integridade: "
                f"{resultado}"
            )

    except sqlite3.Error as erro:
        raise RuntimeError(
            "Não foi possível validar a integridade do GeoPackage."
        ) from erro

    finally:
        if base_dados is not None:
            base_dados.close()


def descarregar_gpkg(
    url,
    ficheiro_destino,
    metadados_remotos,
    tentativas=TENTATIVAS_DOWNLOAD,
):
    """
    Descarrega o GeoPackage, retomando uma descarga parcial da mesma
    versão remota quando possível.

    O servidor do ICNF suporta HTTP Range e devolve 206 Partial Content,
    permitindo retomar uma descarga interrompida.

    A descarga é feita para um ficheiro temporário (.part). Os metadados
    associados identificam a versão remota a que pertence. Se a versão
    não corresponder à versão atualmente disponibilizada, a descarga
    parcial é eliminada e reiniciada.

    O ficheiro só é promovido para o destino final depois de validar
    o tamanho e a integridade do GeoPackage.

    :param url: URL de download direto do GeoPackage.
    :param ficheiro_destino: Caminho onde o ficheiro final é guardado.
    :param metadados_remotos: Metadados da versão remota.
    :param tentativas: Número máximo de tentativas.
    :raises RuntimeError: Se não for possível descarregar ou validar
        o GeoPackage.
    """
    ficheiro_destino.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ficheiro_temporario = Path(f"{ficheiro_destino}.part")

    ficheiro_metadados_parciais = Path(f"{ficheiro_destino}.part.meta.json")

    tamanho_esperado = metadados_remotos.get("content_length")

    # Verifica se existe uma descarga parcial.
    if ficheiro_temporario.exists():

        metadados_parciais = carregar_metadados(ficheiro_metadados_parciais)

        corresponde = (
            metadados_parciais is not None
            and fonte_foi_atualizada(
                metadados_parciais,
                metadados_remotos,
            ) is False
        )

        tamanho_parcial = ficheiro_temporario.stat().st_size

        if tamanho_esperado is not None and tamanho_parcial > tamanho_esperado:
            corresponde = False

        if not corresponde:
            print(
                "A descarga parcial não corresponde à versão atual. "
                "Será eliminada e reiniciada."
            )

            ficheiro_temporario.unlink(missing_ok=True)

            ficheiro_metadados_parciais.unlink(missing_ok=True)

    # Guarda a identificação da versão a que pertence
    # a descarga parcial.
    if not ficheiro_temporario.exists():
        guardar_metadados(
            ficheiro_metadados_parciais,
            metadados_remotos,
        )

    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):
        try:
            tamanho_atual = (
                ficheiro_temporario.stat().st_size
                if ficheiro_temporario.exists()
                else 0
            )

            # Se a parcial já tiver o tamanho esperado,
            # basta validá-la.
            if tamanho_esperado is not None and tamanho_atual == tamanho_esperado:
                print(
                    "A descarga parcial já está completa. "
                    "A validar o GeoPackage..."
                )

                validar_geopackage(ficheiro_temporario)

                os.replace(
                    ficheiro_temporario,
                    ficheiro_destino,
                )

                ficheiro_metadados_parciais.unlink(missing_ok=True)

                print("Download concluído com sucesso.")

                return

            headers = HEADERS_DOWNLOAD.copy()
            retomar = tamanho_atual > 0

            if retomar:
                headers["Range"] = (f"bytes={tamanho_atual}-")

                print(
                    f"A retomar download a partir de "
                    f"{tamanho_atual / 1024**2:.1f} MB "
                    f"(tentativa {tentativa}/{tentativas})..."
                )

            else:
                print(
                    f"A descarregar fogos.gpkg "
                    f"(tentativa {tentativa}/{tentativas})..."
                )

            with requests.get(
                url,
                headers=headers,
                timeout=TIMEOUT_DOWNLOAD,
                stream=True,
                allow_redirects=True,
            ) as resposta:

                resposta.raise_for_status()

                codigo = resposta.status_code

                if retomar and codigo == 206:
                    content_range = resposta.headers.get(
                        "Content-Range"
                    )

                    if not content_range:
                        raise RuntimeError(
                            "O servidor respondeu a uma retoma sem "
                            "enviar o cabeçalho Content-Range."
                        )

                    partes = content_range.split()

                    if len(partes) != 2:
                        raise RuntimeError(
                            "O cabeçalho Content-Range recebido "
                            "é inválido."
                        )

                    intervalo, total = partes[1].split("/")

                    inicio = int(
                        intervalo.split("-")[0]
                    )

                    tamanho_total_resposta = int(total)

                    if inicio != tamanho_atual:
                        raise RuntimeError(
                            "O servidor iniciou a retoma num ponto "
                            "diferente do esperado."
                        )

                    if (
                        tamanho_esperado is not None
                        and tamanho_total_resposta
                        != tamanho_esperado
                    ):
                        raise RuntimeError(
                            "O tamanho total do ficheiro mudou "
                            "durante o download."
                        )

                    modo = "ab"
                    tamanho_inicial = tamanho_atual

                else:
                    # O servidor ignorou Range e devolveu o ficheiro
                    # completo. Reiniciamos de forma segura.
                    if retomar and codigo == 200:
                        print(
                            "O servidor não utilizou Range. "
                            "A descarga será reiniciada."
                        )

                    modo = "wb"
                    tamanho_inicial = 0

                tamanho_total = tamanho_esperado

                if tamanho_total is None:
                    content_length = resposta.headers.get(
                        "Content-Length"
                    )

                    if content_length is not None:
                        tamanho_total = (
                            tamanho_inicial + int(content_length)
                            if codigo == 206
                            else int(content_length)
                        )

                with open(
                    ficheiro_temporario,
                    modo,
                ) as ficheiro:

                    with tqdm(
                        total=tamanho_total,
                        initial=tamanho_inicial,
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                        desc="Download",
                    ) as progresso:

                        for bloco in resposta.iter_content(
                            chunk_size=CHUNK_SIZE_DOWNLOAD
                        ):
                            if not bloco:
                                continue

                            ficheiro.write(bloco)
                            progresso.update(len(bloco))

                    ficheiro.flush()
                    os.fsync(ficheiro.fileno())

            validar_tamanho(
                ficheiro_temporario,
                tamanho_esperado,
            )

            print("A validar o GeoPackage...")

            validar_geopackage(ficheiro_temporario)

            os.replace(
                ficheiro_temporario,
                ficheiro_destino,
            )

            ficheiro_metadados_parciais.unlink(missing_ok=True)
            print("Download concluído com sucesso.")

            return

        except (
            requests.RequestException,
            OSError,
            RuntimeError,
            ValueError,
        ) as erro:

            ultimo_erro = erro

            print(f"Erro: {erro}")

            if tentativa < tentativas:
                tempo_espera = (
                    15 * (2 ** (tentativa - 1))
                )

                print(f"A aguardar {tempo_espera}s antes de nova tentativa...")
                sleep(tempo_espera)

    raise RuntimeError(
        "Não foi possível descarregar o GeoPackage do ICNF."
    ) from ultimo_erro