"""Orquestrador do relatorio PDF do IPIA (4 paginas).

Busca o dado (via indices_setoriais.py - motor de calculo, nunca
duplicado aqui) e monta o PDF multi-pagina com matplotlib
(`PdfPages` - ja faz parte do matplotlib, sem dependencia nova).
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from typing import Optional

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import indices_setoriais as motor  # noqa: E402

from . import theme as t
from . import pages


def gerar_relatorio_ipia(caminho_pdf: str, ano_ini: int = 2020, ano_fim: int = 2026,
                         data_geracao: Optional[dt.datetime] = None,
                         df_ipia: Optional[pd.DataFrame] = None,
                         df_custo: Optional[pd.DataFrame] = None,
                         df_origem: Optional[pd.DataFrame] = None) -> int:
    """Gera o relatorio PDF de 4 paginas (capa, decomposicao de custo,
    series temporais, indicadores e origem) e devolve o numero de meses
    na serie do IPIA usada.

    df_ipia/df_custo/df_origem aceitam DataFrame ja pronto (mesmo formato
    de `calcular_ipia_mensal`/`custo_importacao_detalhado_mensal`/
    `origem_importacao_bobina_por_pais`) para uso em teste sem rede - se
    None, busca ao vivo. Quando busca ao vivo, o dado bruto do Comex Stat
    e buscado UMA vez so e reaproveitado entre `custo_importacao_detalhado_mensal`
    e `origem_importacao_bobina_por_pais` (nunca duas chamadas de rede
    para o mesmo dado).
    """
    import matplotlib
    matplotlib.use("Agg")
    # "R$" aparece 2x em varias strings do relatorio (ex.: "de R$ X para R$ Y") -
    # o matplotlib por padrao trata texto entre um PAR de "$" como mathtext
    # (LaTeX), o que corrompe o texto renderizado (espacos somem, palavras
    # colam). Desliga esse parsing globalmente - nao usamos mathtext em
    # lugar nenhum do relatorio.
    matplotlib.rcParams["text.parse_math"] = False
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    if df_ipia is None or df_custo is None or df_origem is None:
        df_bruto_comex = motor._comex_bobina_bruto(ano_ini, ano_fim)
        if df_ipia is None:
            df_ipia = motor.calcular_ipia_mensal(ano_ini, ano_fim, df_bruto=df_bruto_comex)
        if df_custo is None:
            df_custo = motor.custo_importacao_detalhado_mensal(ano_ini, ano_fim, df_bruto=df_bruto_comex)
        if df_origem is None:
            df_origem = motor.origem_importacao_bobina_por_pais(ano_ini, ano_fim, df_bruto=df_bruto_comex)

    if df_ipia is None or df_ipia.empty:
        raise ValueError("Nenhum dado de IPIA disponivel para o periodo - "
                         "confira o periodo ou rode --check-sources primeiro.")

    data_geracao = data_geracao or dt.datetime.now()
    diretorio = os.path.dirname(caminho_pdf)
    if diretorio:
        os.makedirs(diretorio, exist_ok=True)

    with PdfPages(caminho_pdf) as pdf:
        fig1 = plt.figure(figsize=(t.LARGURA_POL, t.ALTURA_POL))
        pages.pagina_capa(fig1, df_ipia, data_geracao)
        pdf.savefig(fig1)
        plt.close(fig1)

        fig2 = plt.figure(figsize=(t.LARGURA_POL, t.ALTURA_POL))
        pages.pagina_decomposicao_custo(fig2, df_ipia, df_custo, data_geracao, pagina_num=2)
        pdf.savefig(fig2)
        plt.close(fig2)

        fig3 = plt.figure(figsize=(t.LARGURA_POL, t.ALTURA_POL))
        pages.pagina_series_temporais(fig3, df_ipia, df_custo, data_geracao, pagina_num=3)
        pdf.savefig(fig3)
        plt.close(fig3)

        fig4 = plt.figure(figsize=(t.LARGURA_POL, t.ALTURA_POL))
        pages.pagina_indicadores_origem(fig4, df_ipia, df_custo, df_origem, data_geracao, pagina_num=4)
        pdf.savefig(fig4)
        plt.close(fig4)

    return len(df_ipia)
