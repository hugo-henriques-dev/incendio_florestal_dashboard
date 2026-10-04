# Incêndios Florestais em Portugal

Dashboard interativo sobre incêndios florestais em Portugal, construído com Streamlit e com base nos dados abertos do [ICNF](https://fogos.icnf.pt/).

**App:** https://incendios-florestais-pt.streamlit.app/

## Vistas

* **Visão geral:** métricas principais e distribuição mensal das ocorrências.
* **Evolução temporal:** ocorrências e área ardida por ano, com correlações.
* **Distribuição geográfica:** mapa de hexágonos com filtros por ano, área, causa e localização.
* **Perigo de incêndio:** ocorrências e área ardida por nível de FWI.
* **Dados:** tabela das ocorrências.

## Como funciona

O projeto está dividido em duas partes, ligadas através do Supabase Storage:

1. **ETL** (`executar_etl.py`): descarrega o GeoPackage do ICNF, limpa e normaliza os dados, gera os datasets preparados em Parquet e envia para o Supabase os ficheiros que foram alterados.
2. **App** (`streamlit_app.py`): carrega os datasets a partir do disco local ou do Supabase e apresenta o dashboard.

## Estrutura

```text
streamlit_app.py   # aplicação Streamlit
executar_etl.py    # ponto de entrada do ETL
constantes.py      # caminhos, limiares e configuração
etl/               # obtenção, processamento e preparação dos dados
dados_io/          # carregamento e envio dos datasets
ui/                # filtros, utilitários e views
static/            # CSS e favicon
dados/             # dados locais
requirements.txt   # dependências do projeto
```

## Instalação

Requer Python 3.11 ou superior.

Instalar as dependências:

```bash
pip install -r requirements.txt
```

## Executar localmente

Para executar o ETL:

```bash
python executar_etl.py
```

Para iniciar o dashboard:

```bash
streamlit run streamlit_app.py
```

## Configuração do Supabase

O Supabase Storage é utilizado para disponibilizar os datasets ao dashboard e para armazenar os ficheiros enviados pelo ETL.

As credenciais podem ser definidas através de variáveis de ambiente ou em `.streamlit/secrets.toml`.

## Fonte

[ICNF - Instituto da Conservação da Natureza e das Florestas](https://fogos.icnf.pt/)
