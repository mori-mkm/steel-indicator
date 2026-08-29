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
from . import pages_v3
from . import narrative


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


# =============================================================================
# IPIA-HRC Reporting V3 (market intelligence executivo) - Sec.1-54
# =============================================================================
# Caminho NOVO e PARALELO a `gerar_relatorio_ipia_hrc` (V2, acima -
# permanece inalterado, usado pelos testes de Stage G6 que ja o
# protegiam). `--pdf-ipia` (CLI) passa a chamar `gerar_relatorio_ipia_hrc_v3`
# a partir desta stage - ver docs/validation/ipia_hrc_reporting_v3.md.
#
# A decomposicao de drivers (Shapley) NAO e recalculada aqui - e lida de
# um artefato JA PERSISTIDO por `scripts/gerar_ipia_hrc_driver_decomposition.py`
# (Sec.49: "nao reconstruir numeros ao vivo silenciosamente se o contrato
# atual e report-from-vintage"). Se o artefato nao existir ou nao
# corresponder a vintage sendo relatada, o relatorio degrada
# graciosamente (paginas de driver ficam sem waterfall/narrativa
# derivada de decomposicao, nunca fabricam um numero).

CAMINHO_DECOMPOSICAO_MENSAL_PADRAO = "data/processed/validation/ipia_hrc_driver_decomposition/decomposicao_mensal.csv"
CAMINHO_COMPONENTES_MENSAIS_PADRAO = "data/processed/validation/ipia_hrc_driver_decomposition/componentes_mensais.csv"


def carregar_decomposicao_se_disponivel(caminho: str = CAMINHO_DECOMPOSICAO_MENSAL_PADRAO) -> Optional[pd.DataFrame]:
    """Le o artefato de transicoes (`decomposicao_mensal.csv`) ja
    persistido - NUNCA recalcula a decomposicao ao vivo dentro do
    reporting. Devolve None se o arquivo nao existir (degradacao
    graciosa, nunca uma excecao nem um numero fabricado)."""
    if not os.path.exists(caminho):
        return None
    return pd.read_csv(caminho, parse_dates=["reference_period", "previous_reference_period"])


def carregar_componentes_mensais_se_disponivel(
        caminho: str = CAMINHO_COMPONENTES_MENSAIS_PADRAO) -> Optional[pd.DataFrame]:
    """Le o artefato de NIVEIS absolutos por mes (`componentes_mensais.csv`,
    composicao do PPI_COST) - mesma politica de degradacao graciosa de
    `carregar_decomposicao_se_disponivel`."""
    if not os.path.exists(caminho):
        return None
    return pd.read_csv(caminho, parse_dates=["reference_period"])


def _linha_para_periodo(df: Optional[pd.DataFrame], vintage_id: str, periodo,
                        coluna_periodo: str = "reference_period", modo: Optional[str] = "cost") -> Optional[dict]:
    if df is None or df.empty or periodo is None:
        return None
    filtro = (df[coluna_periodo] == periodo) & (df["vintage_id"] == vintage_id)
    if modo is not None and "modo" in df.columns:
        filtro &= (df["modo"] == modo)
    linha = df[filtro]
    return linha.iloc[0].to_dict() if not linha.empty else None


def preparar_dados_relatorio_ipia_hrc_v3(vintage: dict, decomposicao_df: Optional[pd.DataFrame] = None,
                                         componentes_mensais_df: Optional[pd.DataFrame] = None) -> dict:
    """Funcao PURA (nenhum I/O): estende `preparar_dados_relatorio_ipia_hrc`
    (V2, reusado sem duplicar) com o que o Reporting V3 precisa: valor
    MoM/YoY, decomposicao Shapley da ultima transicao (se disponivel),
    resumo executivo determinístico (`reporting.narrative`), composicao
    do PPI_COST do mes atual (se disponivel) e posicao historica do IPIA
    (percentil/mediana/min/max sobre a serie ja publicada).

    `decomposicao_df`/`componentes_mensais_df` aceitam o resultado ja
    carregado de `carregar_decomposicao_se_disponivel`/
    `carregar_componentes_mensais_se_disponivel` (injecao de teste, mesmo
    padrao do resto do modulo) - None em qualquer um dos dois so
    desativa a secao correspondente (`decomposicao_disponivel=False`/
    `composicao_ppi_disponivel=False`), nunca fabrica dado.
    """
    dados = preparar_dados_relatorio_ipia_hrc(vintage)

    combinada = dados["combinada"]
    rotulo_atual, _periodo_txt, ipia_atual, e_provisorio = pages._valor_corrente_ipia_hrc(dados)
    if pd.isna(ipia_atual):
        ipia_atual = None  # vintage sem nenhum mes calculavel - _valor_corrente_ipia_hrc devolve NaN, nunca None
    linha_atual = (dados["ultimo_provisional"] if dados["ultimo_provisional"] is not None
                  else dados["ultimo_oficial"])
    periodo_atual = linha_atual["reference_period"] if linha_atual is not None else None
    status_atual = linha_atual["publication_status"] if linha_atual is not None else None

    ipia_anterior = None
    if linha_atual is not None:
        idx_atual = combinada.index[combinada["reference_period"] == periodo_atual]
        if len(idx_atual) and idx_atual[0] > 0:
            ipia_anterior = float(combinada.iloc[idx_atual[0] - 1]["ipia_hrc_v2"])

    ipia_yoy = None
    if periodo_atual is not None:
        linha_yoy = combinada[combinada["reference_period"] == periodo_atual - pd.DateOffset(years=1)]
        if not linha_yoy.empty and pd.notna(linha_yoy.iloc[0]["ipia_hrc_v2"]):
            ipia_yoy = float(linha_yoy.iloc[0]["ipia_hrc_v2"])

    linha_decomp = _linha_para_periodo(decomposicao_df, dados["vintage_id"], periodo_atual)
    decomposicao_disponivel = linha_decomp is not None and ipia_atual is not None and ipia_anterior is not None

    resumo_executivo = None
    if decomposicao_disponivel:
        resumo_executivo = narrative.gerar_resumo_executivo_ipia(
            ipia_atual=float(ipia_atual), ipia_anterior=ipia_anterior,
            decomposicao=linha_decomp, publication_status=status_atual)

    linha_componentes = _linha_para_periodo(componentes_mensais_df, dados["vintage_id"], periodo_atual, modo=None)

    serie_historica = combinada["ipia_hrc_v2"].dropna()
    posicao_historica = None
    if not serie_historica.empty and ipia_atual is not None:
        posicao_historica = {
            "percentil": float((serie_historica < ipia_atual).mean() * 100.0),
            "mediana": float(serie_historica.median()),
            "min": float(serie_historica.min()), "max": float(serie_historica.max()),
            "distancia_mediana_pts": float(ipia_atual - serie_historica.median()),
        }

    dados.update({
        "ipia_atual": float(ipia_atual) if ipia_atual is not None else None,
        "periodo_atual": periodo_atual, "rotulo_atual": rotulo_atual,
        "status_atual": status_atual, "is_provisional_atual": e_provisorio,
        "ppi_atual": (float(linha_atual["ppi_rs_t"])
                     if linha_atual is not None and pd.notna(linha_atual["ppi_rs_t"]) else None),
        "ppi_offer_atual": (float(linha_atual["ppi_offer_rs_t"])
                            if linha_atual is not None and "ppi_offer_rs_t" in linha_atual
                            and pd.notna(linha_atual["ppi_offer_rs_t"]) else None),
        "preco_domestico_atual": (float(linha_atual["preco_domestico_rs_t"])
                                  if linha_atual is not None and pd.notna(linha_atual["preco_domestico_rs_t"])
                                  else None),
        "ipia_anterior": ipia_anterior,
        # `ipia_atual` tambem precisa do guard (nao so `ipia_anterior`/`ipia_yoy`) - achado do
        # code review desta stage: um vintage com o mes mais recente UNKNOWN (ipia_atual=None)
        # mas o mes anterior/ano anterior calculavel levantava TypeError (None - float) aqui.
        "delta_mom_ipia": (float(ipia_atual - ipia_anterior)
                          if ipia_atual is not None and ipia_anterior is not None else None),
        "ipia_yoy": ipia_yoy,
        "delta_yoy_ipia": (float(ipia_atual - ipia_yoy)
                          if ipia_atual is not None and ipia_yoy is not None else None),
        "decomposicao_disponivel": decomposicao_disponivel,
        "decomposicao_ultima_transicao": linha_decomp,
        "resumo_executivo": resumo_executivo,
        "composicao_ppi_disponivel": linha_componentes is not None,
        "composicao_ppi_mes_atual": linha_componentes,
        "posicao_historica": posicao_historica,
    })
    return dados


def gerar_relatorio_ipia_hrc_v3(caminho_pdf: str, vintage: dict,
                                decomposicao_df: Optional[pd.DataFrame] = None,
                                componentes_mensais_df: Optional[pd.DataFrame] = None,
                                data_geracao: Optional[dt.datetime] = None) -> dict:
    """Gera o relatorio PDF V3 (4 paginas: Market View, Import Parity &
    Drivers, History & Confidence, Methodology & Watchlist) a partir de
    uma vintage JA CARREGADA - mesmo contrato de `gerar_relatorio_ipia_hrc`
    (nunca busca rede, nunca cria vintage nova; `vintage` obrigatorio).

    `decomposicao_df`/`componentes_mensais_df` sao SEMPRE repassados como
    recebidos (default `None`) - esta funcao NUNCA le disco sozinha; quem
    quiser o comportamento "carregar dos caminhos padrao se disponivel"
    precisa chamar `carregar_decomposicao_se_disponivel()`/
    `carregar_componentes_mensais_se_disponivel()` explicitamente ANTES
    de chamar esta funcao (e o que o branch `--pdf-ipia` do CLI faz) -
    manter a leitura de disco fora desta funcao facilita uso em teste
    (injecao determinística, sem tocar o filesystem)."""
    if not vintage or "manifest" not in vintage:
        raise ValueError("gerar_relatorio_ipia_hrc_v3 precisa de uma vintage ja carregada "
                         "(carregar_vintage_ipia_hrc_v2) - nunca busca dado ao vivo nem cria vintage nova.")

    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["text.parse_math"] = False
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    dados = preparar_dados_relatorio_ipia_hrc_v3(vintage, decomposicao_df=decomposicao_df,
                                                 componentes_mensais_df=componentes_mensais_df)
    data_geracao = data_geracao or dt.datetime.now()
    diretorio = os.path.dirname(caminho_pdf)
    if diretorio:
        os.makedirs(diretorio, exist_ok=True)

    paginas = [
        pages_v3.pagina_market_view,
        pages_v3.pagina_import_parity_drivers,
        pages_v3.pagina_history_confidence,
        pages_v3.pagina_methodology_watchlist,
    ]
    with PdfPages(caminho_pdf) as pdf:
        for i, pagina_fn in enumerate(paginas, start=1):
            fig = plt.figure(figsize=(t.LARGURA_POL, t.ALTURA_POL))
            pagina_fn(fig, dados, data_geracao, pagina_num=i)
            pdf.savefig(fig)
            plt.close(fig)

    return {"n_paginas": len(paginas), "vintage_id": dados["vintage_id"]}
