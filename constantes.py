"""
Constantes utilizadas no processamento, preparação e apresentação
dos dados de incêndios florestais.
"""

from pathlib import Path

# =============================================================================
# CAMINHOS
# =============================================================================
DIR_RAIZ = Path(__file__).resolve().parent

DIR_DADOS = DIR_RAIZ / "dados"
DIR_ORIGINAIS = DIR_DADOS / "originais"
DIR_PROCESSADOS = DIR_DADOS / "processados"
DIR_PREPARADOS = DIR_DADOS / "preparados"

# Dados originais
FICHEIRO_GPKG_BRUTO = DIR_ORIGINAIS / "fogos.gpkg"
FICHEIRO_CAOP_MUNICIPIOS_BRUTO = DIR_ORIGINAIS / "caop_municipios_bruto.parquet"

# Dados processados e preparados
FICHEIRO_FOGOS = DIR_PROCESSADOS / "fogos.parquet"
FICHEIRO_EVOLUCAO_ANUAL = DIR_PREPARADOS / "evolucao_anual.parquet"
FICHEIRO_DISTRIBUICAO_GEO = DIR_PREPARADOS / "distribuicao_geografica.parquet"
FICHEIRO_DISTRIBUICAO_GEO_RECENTE = (
    DIR_PREPARADOS / "distribuicao_geografica_recente.parquet"
)
FICHEIRO_CAOP_MUNICIPIOS = (
    DIR_PREPARADOS / "caop_municipios.parquet"
)
FICHEIRO_PREVISAO_PROBABILIDADES = DIR_PREPARADOS / "previsao_probabilidades.parquet"

PNG_FAVICON = DIR_RAIZ / "static" / "wildfire.png"
CSS_ESTILOS = DIR_RAIZ / "static" / "style.css"

# =============================================================================
# SUPABASE
# =============================================================================
BUCKET_SUPABASE = "dados"
MANIFEST_SUPABASE = "manifest.json"

FICHEIROS_SUPABASE = {
    FICHEIRO_FOGOS: "fogos.parquet",
    FICHEIRO_EVOLUCAO_ANUAL: "evolucao_anual.parquet",
    FICHEIRO_DISTRIBUICAO_GEO: "distribuicao_geografica.parquet",
    FICHEIRO_DISTRIBUICAO_GEO_RECENTE: "distribuicao_geografica_recente.parquet",
    FICHEIRO_CAOP_MUNICIPIOS: "caop_municipios.parquet",
    FICHEIRO_PREVISAO_PROBABILIDADES: "previsao_probabilidades.parquet",
}

# =============================================================================
# FONTE DE DADOS (ICNF)
# =============================================================================
URL_FOGOS_GPKG = "https://fogos.icnf.pt/download/ExportarDadosSGIF/fogos.gpkg"

HEADERS_DOWNLOAD = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept-Encoding": "identity",
}

TIMEOUT_DOWNLOAD = (30, 300)
TIMEOUT_METADADOS = (30, 60)
TENTATIVAS_DOWNLOAD = 3
CHUNK_SIZE_DOWNLOAD = 1024 * 1024  # 1 MB

# =============================================================================
# FONTE DE DADOS (CAOP)
# =============================================================================
URL_CAOP_MUNICIPIOS = (
    "https://ogcapi.dgterritorio.gov.pt/"
    "collections/municipios/items"
)

# Municípios da CAOP2025 (Continente), usado para validar a resposta da API
TOTAL_MUNICIPIOS_CAOP = 278

# Municípios por pedido à API
TAMANHO_PAGINA_CAOP = 25

TIMEOUT_CAOP = 120
ESPERA_ENTRE_PAGINAS_CAOP = 1

# Erros temporários do servidor, em que se tenta o pedido de novo
ESTADOS_REPETIVEIS_CAOP = {502, 503, 504}

# =============================================================================
# COLUNAS
# =============================================================================
COLUNAS_PADRAO = [
    "Codigo", "Ano", "Mes", "Distrito", "Concelho", "Freguesia",
    "DHInicio", "DHFim", "DuracaoHoras",
    "TipoCausa",
    "AreaTotal", "AreaPov", "AreaMato", "AreaAgric", "ClasseArea",
    "fwi",
    "Lat_4326", "Lon_4326",
]

# =============================================================================
# PROCESSAMENTO
# =============================================================================
COLUNAS_AUXILIARES_DURACAO = [
    "DH1Intervencao",
    "DHResolucao",
    "DHConclusao",
]

LIMITE_HORAS_SUSPEITO = 720
LIMITE_AREA_HA_SUSPEITO = 50
LIMITE_KM_CONCELHO = 40

LARGURA_HEXAGONO_KM = 3

# Decaimento do peso dos anos históricos, em que
# peso = exp(-DECAIMENTO_ANUAL * idade) e idade é a distância ao ano
# histórico mais recente (0 = todos os anos pesam o mesmo)
DECAIMENTO_ANUAL = 0.15

# =============================================================================
# PREPARAÇÃO
# =============================================================================
# Predefinição de filtro para distribuição geográfica
ANOS_RECENTES = 11

# Escolhida comparando o número de vértices para vários valores: 400 m foi
# o melhor compromisso entre o detalhe das fronteiras e o desempenho
TOLERANCIA_SIMPLIFICACAO_CAOP_M = 400

# =============================================================================
# INTERFACE
# =============================================================================
MESES = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}

MESES_ABREVIADOS = {
    numero: nome[:3]
    for numero, nome in MESES.items()
}

LABELS_CLASSE_AREA = {
    "[Area-1]": "Menos de 1 ha",
    "[Area1-10]": "1 a 10 ha",
    "[Area10-50]": "10 a 50 ha",
    "[Area-50-100]": "50 a 100 ha",
    "[Area100-500]": "100 a 500 ha",
    "[Area500-1000]": "500 a 1 000 ha",
    "[Area+1000]": "Mais de 1 000 ha",
}

PALETA = [
    "#32A836",
    "#FEE91A",
    "#F38200",
    "#D83E39",
    "#8A364D",
]

# Cor dos concelhos sem qualquer ocorrência registada no mês selecionado.
COR_SEM_OCORRENCIAS = "#D9D9D9"

# Tamanho da letra (px) das caixas de hover dos gráficos
FONT_HOVER = 16

# Limites entre as 5 classes de probabilidade (proporção de 0 a 1), pela
# ordem de PALETA: menos de 20%, 20-45%, 45-70%, 70-90% e 90% ou mais.
LIMITES_PROBABILIDADE = (0.20, 0.45, 0.70, 0.90)