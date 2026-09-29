"""
Funções auxiliares reutilizadas pelas várias views do dashboard, para
evitar duplicação de lógica de formatação e apresentação.
"""

import streamlit as st


def formatar_numero(valor, casas=0):
    """
    Formata um número com separador de milhar em espaço, em vez de
    vírgula, seguindo a convenção portuguesa.

    :param valor: Número a formatar.
    :param casas: Número de casas decimais a mostrar.
    :returns: String formatada, ex.: "824 875".
    """
    return f"{valor:,.{casas}f}".replace(",", " ")


def obter_distrito_top_causa(distritos_causa, tipo_causa):
    """
    Devolve a linha do distrito com mais ocorrências para um dado
    TipoCausa.

    :param distritos_causa: DataFrame agregado por Distrito e
        TipoCausa, com uma coluna "Ocorrencias".
    :param tipo_causa: Valor de TipoCausa a filtrar (ex.: "Intencional").
    :returns: Series correspondente ao distrito com mais ocorrências
        desse tipo de causa.
    """
    return (
        distritos_causa[distritos_causa["TipoCausa"] == tipo_causa]
        .sort_values("Ocorrencias", ascending=False)
        .iloc[0]
    )


def mostrar_metricas(metricas):
    """
    Apresenta uma lista de métricas em blocos de 3 colunas.

    :param metricas: Lista de dicts com "titulo", "valor" e,
        opcionalmente, "help".
    :returns: None.
    """
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