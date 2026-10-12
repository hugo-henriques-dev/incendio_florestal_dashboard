"""
Funções auxiliares reutilizadas pelas várias views do dashboard, para
evitar duplicação de lógica de formatação e apresentação.
"""

import streamlit as st

from constantes import COR_SEM_OCORRENCIAS, LIMITES_PROBABILIDADE, PALETA


def formatar_numero(valor, casas=0):
    """
    Formata um número de acordo com a convenção portuguesa, utilizando
    espaços como separadores de milhares e vírgulas como separadores decimais.

    :param valor: Número a formatar.
    :param casas: Número de casas decimais a mostrar.
    :returns: String formatada, ex.: "824 875".
    """
    return (
        f"{valor:,.{casas}f}".replace(",", " ").replace(".", ",")
    )


def obter_distrito_top_causa(distritos_causa, tipo_causa):
    """
    Devolve a linha do distrito com mais ocorrências para um dado
    TipoCausa.

    :param distritos_causa: DataFrame agregado por Distrito e
        TipoCausa, com uma coluna "Ocorrencias".
    :param tipo_causa: Valor de TipoCausa a filtrar (ex.: "Intencional").
    :returns: Series correspondente ao distrito com mais ocorrências
        desse tipo de causa.
    :raises IndexError: Se não existirem linhas para o tipo de causa.
    """
    return (
        distritos_causa[distritos_causa["TipoCausa"] == tipo_causa]
        .sort_values("Ocorrencias", ascending=False)
        .iloc[0]
    )


def mostrar_legenda_probabilidade(contagens, n_sem_ocorrencias):
    """
    Apresenta a legenda do mapa de probabilidade estimada, com uma cor
    por classe de probabilidade e o número de concelhos em cada uma.

    Os rótulos das classes são construídos a partir de
    LIMITES_PROBABILIDADE e as cores vêm de PALETA, pela mesma ordem
    usada para colorir o mapa. Quando o mês tem concelhos sem qualquer
    ocorrência registada, acrescenta uma entrada com a respetiva cor.

    :param contagens: Número de concelhos em cada classe de
        probabilidade, pela ordem de PALETA.
    :param n_sem_ocorrencias: Número de concelhos sem ocorrências no mês.
    :returns: None.
    """
    limites_pct = [
        formatar_numero(limite * 100)
        for limite in LIMITES_PROBABILIDADE
    ]

    rotulos = [
        f"Menos de {limites_pct[0]}%",
        *[
            f"De {inferior}% a menos de {superior}%"
            for inferior, superior in zip(
                limites_pct,
                limites_pct[1:],
            )
        ],
        f"{limites_pct[-1]}% ou mais",
    ]

    entradas = [
        (cor, f"{rotulo} ({n})")
        for cor, rotulo, n in zip(PALETA, rotulos, contagens)
    ]

    # Os concelhos sem registos ficam no topo da legenda, antes das classes
    if n_sem_ocorrencias > 0:
        entradas.insert(
            0,
            (
                COR_SEM_OCORRENCIAS,
                f"Sem ocorrências registadas ({n_sem_ocorrencias})",
            ),
        )

    itens = "".join(
        f"""
        <div style="display:flex;align-items:center;gap:8px;">
            <span style="
                display:inline-block;
                width:16px;
                height:12px;
                flex-shrink:0;
                border-radius:2px;
                background:{cor};
            "></span>
            <span>{rotulo}</span>
        </div>
        """
        for cor, rotulo in entradas
    )

    st.html(
        f"""
        <div style="font-size:0.85rem;line-height:1.5;">
            <div style="font-weight:600;margin-bottom:10px;">
                Probabilidade estimada
            </div>
            <div style="display:flex;flex-direction:column;gap:6px;">
                {itens}
            </div>
        </div>
        """
    )


def mostrar_metricas(metricas):
    """
    Apresenta uma lista de métricas em blocos de 3 colunas.

    :param metricas: Lista de dicts com "titulo", "valor" e,
        opcionalmente, "help".
    :returns: None.
    """
    # Cada bloco de 3 métricas é uma nova linha de colunas
    for i in range(0, len(metricas), 3):
        colunas = st.columns(3)

        for coluna, metrica in zip(colunas, metricas[i:i + 3]):
            coluna.metric(
                metrica["titulo"],
                metrica["valor"],
                help=metrica.get("help"),
            )


def mostrar_em_colunas(funcoes):
    """
    Distribui uma lista de widgets Streamlit por colunas, uma função por
    coluna, e devolve os valores que cada uma produzir.

    :param funcoes: Lista de callables sem argumentos, cada um desenhando
        um widget (ex.: lambda: st.selectbox(...)).
    :returns: Lista com o valor devolvido por cada função, pela mesma
        ordem.
    """
    colunas = st.columns(len(funcoes))
    resultados = []

    for coluna, funcao in zip(colunas, funcoes):
        with coluna:
            resultados.append(funcao())

    return resultados


def mostrar_footer():
    """
    Apresenta o rodapé da aplicação com as fontes dos dados e dos recursos
    gráficos utilizados.

    :returns: None.
    """
    st.html(
        """
        <div class="footer">
            <div>
                Fonte de dados:
                <a
                    href="https://fogos.icnf.pt/"
                    target="_blank"
                >
                    ICNF
                </a>
            </div>

            <div>
                Mapa de concelhos:
                Informação geográfica cedida pela Direção-Geral do Território
                (<a
                    href="https://snig.dgterritorio.gov.pt/rndg/srv/por/catalog.search#/metadata/198497815bf647ecaa990c34c42e932e"
                    target="_blank"
                >CAOP 2025</a>,
                licença
                <a
                    href="https://creativecommons.org/licenses/by/4.0/"
                    target="_blank"
                >CC BY 4.0</a>), adaptada.
            </div>

            <div>
                Fire icons created by
                <a
                    href="https://www.flaticon.com/free-icons/fire"
                    target="_blank"
                >
                    Magnific - Flaticon
                </a>
            </div>
        </div>
        """
    )