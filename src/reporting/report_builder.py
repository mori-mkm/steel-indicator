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


# =============================================================================
# IPIA-HRC (PIA-based, publication contract) - Stage G6
# =============================================================================
# Caminho NOVO e PARALELO ao `gerar_relatorio_ipia` acima (legado,
# inalterado - continua existindo, usado pelas characterization tests que
# ja protegiam esse comportamento). `--pdf-ipia` (CLI) passa a chamar
# `gerar_relatorio_ipia_hrc` a partir desta stage - ver
# `docs/METODOLOGIA.md` secao 12.12/15.5 e ADR 0013.
#
# Diferenca estrutural deliberada: `gerar_relatorio_ipia` (legado) aceita
# df_ipia/df_custo/df_origem=None e busca ao vivo quando faltam.
# `gerar_relatorio_ipia_hrc` NUNCA busca nada - recebe uma vintage JA
# CARREGADA (`indices_setoriais.carregar_vintage_ipia_hrc_v2`) como
# parametro obrigatorio. Isso garante estruturalmente que gerar o
# relatorio nunca contata Comex/IBGE/BCB nem cria uma vintage nova - o
# unico jeito de "esquecer" e passar `vintage=None`, que a funcao rejeita
# explicitamente (ver abaixo) em vez de silenciosamente buscar ao vivo.

def preparar_dados_relatorio_ipia_hrc(vintage: dict) -> dict:
    """Funcao PURA (nenhum I/O): a partir de uma vintage JA CARREGADA
    (`indices_setoriais.carregar_vintage_ipia_hrc_v2`), deriva tudo que as
    paginas do relatorio V2 precisam para desenhar - nunca recalcula
    economia (`ipia_hrc_v2`/`ppi_rs_t`/`preco_domestico_rs_t`/
    `publication_status` vem exatamente como persistidos), so filtra/
    combina/resume os DataFrames ja prontos (mesmo objeto que official.csv/
    provisional.csv/CLI ja usam - nunca uma segunda verdade economica, ver
    `.claude/rules/reporting.md`).

    Retorna um dict com (chaves usadas pelas paginas em `pages.py`):
      manifest, oficial, provisional, combinada (oficial+provisional,
      ordenada por reference_period - UNKNOWN nunca entra, official.csv/
      provisional.csv ja excluem), import_side, domestic_price,
      ultimo_oficial (Series ou None), ultimo_provisional (Series ou
      None), contagem_status (dict publication_status -> int, sobre a
      combinada), vintage_id, methodology_version, last_pia_year,
      created_at_utc, previous_vintage_id.
    """
    manifest = vintage["manifest"]
    oficial = vintage["official"].sort_values("reference_period").reset_index(drop=True)
    provisional = vintage["provisional"].sort_values("reference_period").reset_index(drop=True)
    combinada = pd.concat([oficial, provisional], ignore_index=True).sort_values(
        "reference_period").reset_index(drop=True)

    return {
        "manifest": manifest,
        "oficial": oficial,
        "provisional": provisional,
        "combinada": combinada,
        "import_side": vintage["import_side"],
        "domestic_price": vintage["domestic_price"],
        "ultimo_oficial": oficial.iloc[-1] if not oficial.empty else None,
        "ultimo_provisional": provisional.iloc[-1] if not provisional.empty else None,
        "contagem_status": combinada["publication_status"].value_counts().to_dict() if not combinada.empty else {},
        "vintage_id": manifest["vintage_id"],
        "previous_vintage_id": manifest.get("previous_vintage_id"),
        "methodology_version": manifest["methodology_version"],
        "last_pia_year": manifest.get("sources", {}).get("pia_last_observed_year"),
        "created_at_utc": manifest["created_at_utc"],
    }


def gerar_relatorio_ipia_hrc(caminho_pdf: str, vintage: dict,
                             data_geracao: Optional[dt.datetime] = None) -> dict:
    """Gera o relatorio PDF de 4 paginas do IPIA-HRC (PIA-based,
    publication contract - Stage G6) a partir de uma vintage JA
    CARREGADA. `vintage` e OBRIGATORIO (nunca None/omitido) e precisa vir
    de `indices_setoriais.carregar_vintage_ipia_hrc_v2()` - esta funcao
    nunca chama rede nem cria vintage nova; e so uma camada de
    apresentacao sobre o que ja foi publicado (ver
    `.claude/rules/reporting.md`: "Do not recollect source data
    independently when the engine already has it").

    Levanta `ValueError` se `vintage` for None/vazio (nunca cai em
    silencio para nenhum outro caminho) - o chamador (CLI) e responsavel
    por checar `ultima_vintage_ipia_hrc_v2() is None` ANTES de chamar esta
    funcao e falhar alto com instrucao de rodar `--ipia` primeiro (ver
    `main()` em `src/indices_setoriais.py`).

    Retorna dict com `n_paginas` e `vintage_id` (para o chamador
    imprimir/confirmar qual vintage gerou o relatorio).
    """
    if not vintage or "manifest" not in vintage:
        raise ValueError("gerar_relatorio_ipia_hrc precisa de uma vintage ja carregada "
                         "(carregar_vintage_ipia_hrc_v2) - nunca busca dado ao vivo nem cria vintage nova.")

    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["text.parse_math"] = False  # mesmo motivo do relatorio legado (ver acima)
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    dados = preparar_dados_relatorio_ipia_hrc(vintage)
    data_geracao = data_geracao or dt.datetime.now()
    diretorio = os.path.dirname(caminho_pdf)
    if diretorio:
        os.makedirs(diretorio, exist_ok=True)

    with PdfPages(caminho_pdf) as pdf:
        fig1 = plt.figure(figsize=(t.LARGURA_POL, t.ALTURA_POL))
        pages.pagina_capa_ipia_hrc(fig1, dados, data_geracao)
        pdf.savefig(fig1)
        plt.close(fig1)

        fig2 = plt.figure(figsize=(t.LARGURA_POL, t.ALTURA_POL))
        pages.pagina_paridade_importacao_ipia_hrc(fig2, dados, data_geracao, pagina_num=2)
        pdf.savefig(fig2)
        plt.close(fig2)

        fig3 = plt.figure(figsize=(t.LARGURA_POL, t.ALTURA_POL))
        pages.pagina_dinamica_historica_ipia_hrc(fig3, dados, data_geracao, pagina_num=3)
        pdf.savefig(fig3)
        plt.close(fig3)

        fig4 = plt.figure(figsize=(t.LARGURA_POL, t.ALTURA_POL))
        pages.pagina_mercado_metodologia_ipia_hrc(fig4, dados, data_geracao, pagina_num=4)
        pdf.savefig(fig4)
        plt.close(fig4)

    return {"n_paginas": 4, "vintage_id": dados["vintage_id"]}
