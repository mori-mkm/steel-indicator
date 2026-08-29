"""As 4 paginas do Reporting V3 do IPIA-HRC (market intelligence
executivo - docs/validation/ipia_hrc_reporting_v3.md).

Cada funcao so DESENHA - recebe o dict ja calculado por
`report_builder.preparar_dados_relatorio_ipia_hrc_v3` (que por sua vez
reusa `preparar_dados_relatorio_ipia_hrc`, V2, sem duplicar) e usa os
helpers de `components.py`/`narrative.py`. Nenhuma matematica de
indice/decomposicao acontece aqui (`.claude/rules/reporting.md`) - a
decomposicao Shapley e lida de um artefato ja persistido
(`report_builder.carregar_decomposicao_se_disponivel`), nunca recalculada.
"""
from __future__ import annotations

import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import indices_setoriais as motor  # noqa: E402

from . import theme as t
from . import components as c
from . import narrative as narr
from .pages import (
    MARGEM, _mes_pt, _reindexar_calendario,
    STATUS_EXPERIMENTAL_HRC, STATUS_PUBLICATION_GRADE_HRC,
    _CORES_STATUS_HRC, _COR_PROVISIONAL_HRC, _LEGENDA_STATUS_HRC,
    _DISCLOSURE_PROXY_DOMESTICO, _DISCLOSURE_BAIXA_LIQUIDEZ,
)

_LIMIAR_RUIDO_WATERFALL_PTS = 0.05  # Sec.14: nao rotula visualmente contribuicoes
# abaixo disso (agrupadas em "Outros"), mas o dado bruto/audit trail
# (tabela da Sec.15, CSV de decomposicao) nunca omite nenhum driver.


def _fmt_pts(valor) -> str:
    return "n/d" if valor is None or (isinstance(valor, float) and np.isnan(valor)) else f"{valor:+.1f} pts"


def _fmt_rs(valor) -> str:
    return "n/d" if valor is None or (isinstance(valor, float) and np.isnan(valor)) else f"R$ {valor:,.0f}/t"


# =============================================================================
# PAGE 1 - MARKET VIEW
# =============================================================================

def pagina_market_view(fig, dados: dict, data_geracao: dt.datetime, pagina_num: int) -> None:
    c.banda_topo(fig, "IPIA-HRC — MARKET VIEW")

    if dados.get("ipia_atual") is None:
        c.titulo_serif(fig, MARGEM, 0.905, "IPIA-HRC", fontsize=22)
        fig.text(MARGEM, 0.85, "Sem dado publicado nesta vintage.", transform=fig.transFigure,
                 fontsize=10, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        c.rodape_pagina(fig, "Sem fontes aplicáveis — sem dado.", pagina_num=pagina_num, data_geracao=data_geracao)
        return

    ipia_atual = dados["ipia_atual"]
    cor_hero = _COR_PROVISIONAL_HRC if dados["is_provisional_atual"] else t.COR_ACCENT_2
    periodo_txt = _mes_pt(dados["periodo_atual"], abreviado=False)

    # --- HERO NUMBER (Sec.5) ------------------------------------------------
    fig.text(MARGEM, 0.895, f"{ipia_atual:.1f}", transform=fig.transFigure, fontsize=56,
             color=cor_hero, fontfamily=t.FONTE_SERIF, fontweight="bold", va="top")
    fig.text(MARGEM, 0.825, f"IPIA-HRC  ·  {dados['rotulo_atual']}  ·  {periodo_txt}  ·  paridade = 100",
             transform=fig.transFigure, fontsize=9.5, color=t.COR_TEXTO_SECUNDARIO,
             fontfamily=t.FONTE_SANS, va="top")

    x_kpi = MARGEM + 0.44
    c.kpi_tile(fig, x_kpi, 0.895, 0.26, "Δ MOM", _fmt_pts(dados["delta_mom_ipia"]),
              cor_valor=t.COR_TEXTO_PRINCIPAL)
    c.kpi_tile(fig, x_kpi + 0.28, 0.895, 0.26, "Δ YOY", _fmt_pts(dados["delta_yoy_ipia"]),
              cor_valor=t.COR_TEXTO_PRINCIPAL)

    # --- IMPORT PARITY SIGNAL (Sec.10) --------------------------------------
    sinal = narr.classificar_sinal_paridade(ipia_atual)
    y_sinal = 0.775
    fig.text(MARGEM, y_sinal, "IMPORT PARITY SIGNAL", transform=fig.transFigure, fontsize=8,
             color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")
    fig.text(MARGEM, y_sinal - 0.020, f"{sinal['categoria']}  ({sinal['distancia_pts']:+.1f} pts vs. 100)",
             transform=fig.transFigure, fontsize=12, color=cor_hero, fontfamily=t.FONTE_SANS,
             fontweight="bold", va="top")

    # --- HEADLINE + INTERPRETACAO (narrativa determinística) ---------------
    resumo = dados.get("resumo_executivo")
    y_head = y_sinal - 0.055
    if resumo is not None:
        y_after = c.texto_corrido(fig, MARGEM, y_head, 1 - 2 * MARGEM, resumo["interpretation"],
                                  fontsize=10.5, bold=True)
        y_after -= 0.012
        y_after = c.texto_corrido(fig, MARGEM, y_after, 1 - 2 * MARGEM, resumo["parity_interpretation"],
                                  fontsize=9, cor=t.COR_TEXTO_SECUNDARIO)
    else:
        y_after = c.texto_corrido(fig, MARGEM, y_head, 1 - 2 * MARGEM,
                                  narr.montar_interpretacao_100(ipia_atual), fontsize=10.5, bold=True)
        y_after = c.texto_corrido(
            fig, MARGEM, y_after - 0.012, 1 - 2 * MARGEM,
            "Decomposição de drivers indisponível para esta vintage (mês anterior sem transição "
            "calculável ou artefato de decomposição não gerado) — ver página 4.",
            fontsize=8.5, cor=t.COR_TEXTO_SECUNDARIO)

    # --- WHAT CHANGED (Sec.9) -----------------------------------------------
    y_wc = y_after - 0.035
    c.secao_titulo(fig, MARGEM, y_wc, "O QUE MUDOU NO MÊS")
    y_wc -= 0.028
    if resumo is not None:
        itens = []
        principal = resumo["main_driver"]
        itens.append((f"{principal['nome']} — {_fmt_pts(principal['contribuicao'])}",
                      f"Principal contribuição do mês ({principal['direcao_valor']})."))
        if resumo["secondary_driver"] is not None:
            seg = resumo["secondary_driver"]
            itens.append((f"{seg['nome']} — {_fmt_pts(seg['contribuicao'])}",
                          f"Segunda maior contribuição ({seg['direcao_valor']})."))
        if resumo["offsetting_driver"] is not None:
            comp = resumo["offsetting_driver"]
            itens.append((f"{comp['nome']} — {_fmt_pts(comp['contribuicao'])}",
                          f"Principal compensação positiva ({comp['direcao_valor']})."))
        y_after_callout = c.callout_numerado(fig, MARGEM, y_wc, 1 - 2 * MARGEM, itens)
    else:
        y_after_callout = c.texto_corrido(fig, MARGEM, y_wc, 1 - 2 * MARGEM,
                                          "Sem decomposição disponível para o mês atual.",
                                          fontsize=9, cor=t.COR_TEXTO_SECUNDARIO)

    # --- REPORT INFO strip ---------------------------------------------------
    y_info = y_after_callout - 0.03
    info = [
        ("Status de publicação", dados["status_atual"]),
        ("Metodologia", dados["methodology_version"]),
        ("Vintage", dados["vintage_id"][:8]),
    ]
    largura_bloco = (1 - 2 * MARGEM) / len(info)
    for i, (rotulo, valor) in enumerate(info):
        x = MARGEM + i * largura_bloco
        fig.text(x, y_info, rotulo, transform=fig.transFigure, fontsize=7.5,
                 color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        fig.text(x, y_info - 0.017, str(valor), transform=fig.transFigure, fontsize=8.5,
                 color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")

    c.rodape_pagina(fig,
                    "Fontes: Comex Stat, BCB/SGS, IBGE/SIDRA (PIA-Produto, IPP 242-Siderurgia). "
                    "Decomposição: Shapley exato (ADR 0016). Metodologia completa: docs/METODOLOGIA.md.",
                    pagina_num=pagina_num, data_geracao=data_geracao)


# =============================================================================
# PAGE 2 - IMPORT PARITY & DRIVERS
# =============================================================================

def pagina_import_parity_drivers(fig, dados: dict, data_geracao: dt.datetime, pagina_num: int) -> None:
    from .components import cabecalho_pagina_interna, titulo_serif
    cabecalho_pagina_interna(fig, "IPIA-HRC — Relatório")
    titulo_serif(fig, MARGEM, 0.90, "Paridade de Importação & Drivers", fontsize=19)

    if dados.get("ppi_atual") is None:
        fig.text(MARGEM, 0.85, "Sem dado publicado nesta vintage.", transform=fig.transFigure,
                 fontsize=10, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        c.rodape_pagina(fig, "Sem fontes aplicáveis — sem dado.", pagina_num=pagina_num, data_geracao=data_geracao)
        return

    periodo_txt = _mes_pt(dados["periodo_atual"], abreviado=False)

    # --- PPI_COST headline + Offer opcional (Sec.11/12) ---------------------
    y = 0.845
    fig.text(MARGEM, y, f"PPI_COST — {periodo_txt}", transform=fig.transFigure, fontsize=9,
             color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")
    fig.text(MARGEM, y - 0.028, _fmt_rs(dados["ppi_atual"]), transform=fig.transFigure, fontsize=26,
             color=t.COR_ACCENT_2, fontfamily=t.FONTE_SERIF, fontweight="bold", va="top")
    if dados.get("ppi_offer_atual") is not None:
        fig.text(MARGEM + 0.45, y, "PPI_OFFER (cenário 3% — analítico)", transform=fig.transFigure,
                 fontsize=8, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        fig.text(MARGEM + 0.45, y - 0.022, _fmt_rs(dados["ppi_offer_atual"]), transform=fig.transFigure,
                 fontsize=13, color=t.COR_APROXIMADO, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")

    # --- WATERFALL (Sec.13/14) ------------------------------------------------
    y_top1 = c.cabecalho_grafico(
        fig, MARGEM, y - 0.075, 1 - 2 * MARGEM,
        f"IPIA-HRC — de {_mes_pt(dados['decomposicao_ultima_transicao']['previous_reference_period'])} "
        f"a {periodo_txt}" if dados.get("decomposicao_disponivel") else "IPIA-HRC — decomposição indisponível",
        interpretacao=(dados["resumo_executivo"]["what_changed"]["sentenca"]
                      if dados.get("resumo_executivo") else None))
    altura_wf = 0.20
    if dados.get("decomposicao_disponivel"):
        linha = dados["decomposicao_ultima_transicao"]
        contribuicoes = {d: float(linha[d]) for d in motor.DRIVERS_PPI_COST}
        rotulos_legiveis = narr.agrupar_para_waterfall(contribuicoes, limiar=_LIMIAR_RUIDO_WATERFALL_PTS)

        ipia_ini = dados["ipia_anterior"]
        ipia_fim = dados["ipia_atual"]
        ax_wf = fig.add_axes((MARGEM, y_top1 - altura_wf, 1 - 2 * MARGEM, altura_wf))
        c.grafico_waterfall(ax_wf, "IPIA t-1", ipia_ini, rotulos_legiveis, "IPIA t", ipia_fim)
    else:
        ax_wf = fig.add_axes((MARGEM, y_top1 - altura_wf, 1 - 2 * MARGEM, altura_wf))
        ax_wf.axis("off")
        ax_wf.text(0.02, 0.5, "Decomposição de drivers indisponível para este período.",
                  transform=ax_wf.transAxes, fontsize=9, color=t.COR_TEXTO_SECUNDARIO,
                  fontfamily=t.FONTE_SANS)

    # --- DRIVER TABLE, top 5 por |contribuicao| (Sec.15) --------------------
    y_tab = y_top1 - altura_wf - 0.045
    c.secao_titulo(fig, MARGEM, y_tab, "TOP 5 DRIVERS DO MÊS")
    y_tab -= 0.025
    if dados.get("decomposicao_disponivel"):
        linha = dados["decomposicao_ultima_transicao"]
        ranking = narr.ranking_drivers({d: float(linha[d]) for d in motor.DRIVERS_PPI_COST})[:5]
        linhas_tabela = [
            [motor.NOMES_LEGIVEIS_DRIVERS_IPIA_HRC.get(d, d), f"{v:+.2f} pts",
            "Alta" if narr.direcao_valor_driver(d, v) == "alta" else
            "Queda" if narr.direcao_valor_driver(d, v) == "queda" else "Estável"]
            for d, v in ranking
        ]
        c.tabela_simples(fig, (MARGEM, y_tab - 0.115, 1 - 2 * MARGEM, 0.115),
                         ["Driver", "Contribution", "Direction"], linhas_tabela, alinhar_direita_a_partir_de=1)
        y_tab -= 0.135
    else:
        y_tab -= 0.02

    # --- IMPORT COST COMPOSITION (Sec.16) -----------------------------------
    y_comp = y_tab - 0.015
    interp_comp = "Onde está o custo de importação — composição do PPI_COST no período mais recente."
    y_top2 = c.cabecalho_grafico(fig, MARGEM, y_comp, 1 - 2 * MARGEM,
                                 "Composição do PPI_COST", interpretacao=interp_comp)
    altura_comp = 0.09
    if dados.get("composicao_ppi_disponivel"):
        comp = dados["composicao_ppi_mes_atual"]
        componentes = [
            ("CIF (FOB+frete+seguro)", comp["cif_brl_t"], t.PALETA_CATEGORICA[0]),
            ("II", comp["ii_brl_t"], "#6B4226"),
            ("AFRMM", comp["afrmm_brl_t"], "#8C6E4A"),
            ("Antidumping", comp["antidumping_brl_t"], t.COR_NEGATIVO),
            ("Desp. portuárias", comp["d_porto_rs_t"], "#7F8C8D"),
            ("Frete interno", comp["d_interno_rs_t"], "#95A5A6"),
        ]
        ax_comp = fig.add_axes((MARGEM, y_top2 - altura_comp, 1 - 2 * MARGEM, altura_comp))
        c.grafico_barras_empilhadas(ax_comp, "PPI_COST", componentes)
    else:
        ax_comp = fig.add_axes((MARGEM, y_top2 - altura_comp, 1 - 2 * MARGEM, altura_comp))
        ax_comp.axis("off")
        ax_comp.text(0.02, 0.5, "Composição granular indisponível para este período.",
                    transform=ax_comp.transAxes, fontsize=9, color=t.COR_TEXTO_SECUNDARIO,
                    fontfamily=t.FONTE_SANS)

    c.rodape_pagina(fig,
                    "PPI_COST não inclui margem comercial desde a metodologia 1.5 (ADR 0015). Decomposição: "
                    "Shapley exato sobre 10 drivers, resíduo ≈0 por construção (ADR 0016).",
                    pagina_num=pagina_num, data_geracao=data_geracao)


# =============================================================================
# PAGE 3 - HISTORY & CONFIDENCE
# =============================================================================

def pagina_history_confidence(fig, dados: dict, data_geracao: dt.datetime, pagina_num: int) -> None:
    from .components import cabecalho_pagina_interna, titulo_serif
    cabecalho_pagina_interna(fig, "IPIA-HRC — Relatório")
    titulo_serif(fig, MARGEM, 0.90, "Histórico & Confiança", fontsize=19)

    combinada = dados["combinada"]
    if combinada.empty:
        fig.text(MARGEM, 0.85, "Sem dado publicado nesta vintage.", transform=fig.transFigure,
                 fontsize=10, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        c.rodape_pagina(fig, "Sem fontes aplicáveis — sem dado.", pagina_num=pagina_num, data_geracao=data_geracao)
        return

    # --- HISTORICO COMPLETO (Sec.17/18/20) -----------------------------------
    titulo_hist = ("IPIA-HRC recuou no mês, mas segue "
                  + ("acima" if dados["ipia_atual"] > 100 else "abaixo") + " da paridade"
                  if dados.get("delta_mom_ipia") is not None and dados["delta_mom_ipia"] < 0 else
                  "IPIA-HRC avançou no mês" if dados.get("delta_mom_ipia") is not None
                  and dados["delta_mom_ipia"] > 0 else "IPIA-HRC — histórico completo")
    legenda_hist = [
        (_CORES_STATUS_HRC[STATUS_PUBLICATION_GRADE_HRC], "none", "o", "Publication-grade"),
        (_CORES_STATUS_HRC[STATUS_EXPERIMENTAL_HRC], "none", "o", "Experimental"),
        (_COR_PROVISIONAL_HRC, "--", "^", "Provisório"),
    ]
    y_top1 = c.cabecalho_grafico(
        fig, MARGEM, 0.845, 1 - 2 * MARGEM, titulo_hist,
        interpretacao="Linha tracejada em 100 = paridade de custo. Lacunas indicam meses sem dado "
                     "publicável (UNKNOWN) — nunca interpolados.",
        legenda=legenda_hist)
    altura1 = 0.185
    ax_hist = fig.add_axes((MARGEM, y_top1 - altura1, 1 - 2 * MARGEM, altura1))
    for status, cor in _CORES_STATUS_HRC.items():
        recorte = combinada[combinada["publication_status"] == status]
        if not recorte.empty:
            ax_hist.scatter(recorte["reference_period"], recorte["ipia_hrc_v2"], color=cor, s=12, zorder=3)
    oficial_calc = combinada[combinada["publication_status"] != motor.STATUS_PROVISIONAL]
    if not oficial_calc.empty:
        serie_of = _reindexar_calendario(
            oficial_calc.set_index("reference_period")["ipia_hrc_v2"], combinada["reference_period"])
        ax_hist.plot(serie_of.index, serie_of.to_numpy(), color=t.COR_TEXTO_SECUNDARIO, linewidth=1.0, zorder=1)
    provisional_recorte = combinada[combinada["publication_status"] == motor.STATUS_PROVISIONAL]
    if not provisional_recorte.empty:
        ax_hist.plot(provisional_recorte["reference_period"], provisional_recorte["ipia_hrc_v2"],
                    color=_COR_PROVISIONAL_HRC, linestyle="--", linewidth=1.2, zorder=2)
    ax_hist.axhline(100.0, linestyle="--", color=t.COR_TEXTO_SECUNDARIO, linewidth=0.8)
    for spine in ("top", "right", "left"):
        ax_hist.spines[spine].set_visible(False)
    ax_hist.spines["bottom"].set_color(t.COR_LINHA_GRADE)
    ax_hist.grid(axis="y", color=t.COR_LINHA_GRADE, linewidth=0.7)
    ax_hist.set_axisbelow(True)
    ax_hist.tick_params(axis="both", labelsize=7.5, colors=t.COR_TEXTO_SECUNDARIO, length=0)
    ax_hist.set_ylabel("Pontos (100 = paridade)", fontsize=8, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS)

    # --- POSICAO HISTORICA (Sec.19) ------------------------------------------
    y_pos = y_top1 - altura1 - 0.045
    c.secao_titulo(fig, MARGEM, y_pos, "POSIÇÃO HISTÓRICA (não é valuation)")
    y_pos -= 0.03
    pos = dados.get("posicao_historica")
    if pos is not None:
        c.kpi_tile(fig, MARGEM, y_pos, 0.24, "PERCENTIL HISTÓRICO", f"{pos['percentil']:.0f}º")
        c.kpi_tile(fig, MARGEM + 0.26, y_pos, 0.24, "VS. MEDIANA", _fmt_pts(pos["distancia_mediana_pts"]))
        c.kpi_tile(fig, MARGEM + 0.52, y_pos, 0.24, "MÍNIMO DA SÉRIE", f"{pos['min']:.1f}")
        c.kpi_tile(fig, MARGEM + 0.78, y_pos, 0.22, "MÁXIMO DA SÉRIE", f"{pos['max']:.1f}")
    y_pos -= 0.075

    # --- CONFIDENCE PANEL (Sec.21) -------------------------------------------
    c.secao_titulo(fig, MARGEM, y_pos, "DATA CONFIDENCE")
    y_pos -= 0.025
    resumo = dados.get("resumo_executivo")
    texto_confianca = (resumo["confidence_sentence"] if resumo is not None
                      else narr.montar_confidence_sentence(dados["status_atual"]))
    y_pos = c.texto_corrido(fig, MARGEM, y_pos, 1 - 2 * MARGEM, texto_confianca, fontsize=8.7)
    y_pos -= 0.018
    y_pos = c.texto_corrido(fig, MARGEM, y_pos, 1 - 2 * MARGEM, _DISCLOSURE_PROXY_DOMESTICO,
                            fontsize=8.2, cor=t.COR_TEXTO_SECUNDARIO)
    y_pos -= 0.018
    y_pos = c.texto_corrido(fig, MARGEM, y_pos, 1 - 2 * MARGEM, _DISCLOSURE_BAIXA_LIQUIDEZ,
                            fontsize=8.2, cor=t.COR_TEXTO_SECUNDARIO)
    y_pos -= 0.018
    y_pos = c.texto_corrido(
        fig, MARGEM, y_pos, 1 - 2 * MARGEM,
        "O FOB é um valor unitário derivado do comércio realizado, não um price assessment de agência; "
        "mudanças de composição do mix importado podem afetar o valor — ver docs/METODOLOGIA.md §9.7.",
        fontsize=8.2, cor=t.COR_TEXTO_SECUNDARIO)

    c.rodape_pagina(fig,
                    "Séries completas: ipia_hrc_v2_official.csv / ipia_hrc_v2_provisional.csv. "
                    "Publicação append-only (ADR 0012).",
                    pagina_num=pagina_num, data_geracao=data_geracao)


# =============================================================================
# PAGE 4 - METHODOLOGY / WATCHLIST
# =============================================================================

_GLOSSARIO = [
    ("HRC", "Bobina de aço laminada a quente — produto de referência do índice."),
    ("PPI_COST", "Custo estimado de importar e internalizar HRC, sem margem comercial."),
    ("IPIA", "= Preço doméstico / PPI_COST × 100."),
    ("PIA", "Pesquisa Industrial Anual (IBGE) — benchmark anual do preço doméstico."),
    ("IPP", "Índice de Preços ao Produtor (IBGE) — trajetória mensal que encadeia a PIA."),
    ("Provisional", "Estimativa corrente após o último benchmark PIA — sujeita a revisão."),
]

_WATCHLIST_DRIVERS = ["fob", "fx", "freight", "domestic_price"]


def pagina_methodology_watchlist(fig, dados: dict, data_geracao: dt.datetime, pagina_num: int) -> None:
    from .components import cabecalho_pagina_interna, titulo_serif
    cabecalho_pagina_interna(fig, "IPIA-HRC — Relatório")
    titulo_serif(fig, MARGEM, 0.90, "Metodologia & Watchlist", fontsize=19)

    # --- METODOLOGIA EM 30 SEGUNDOS (Sec.24/25/26) ---------------------------
    c.secao_titulo(fig, MARGEM, 0.855, "METODOLOGIA EM 30 SEGUNDOS")
    y = 0.828
    for linha_diagrama in ("Comex Stat  →  PPI_COST",
                          "PIA-HRC + IPP-242  →  Preço doméstico",
                          "Preço doméstico / PPI_COST × 100  →  IPIA-HRC"):
        fig.text(MARGEM, y, linha_diagrama, transform=fig.transFigure, fontsize=9.5,
                 color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")
        y -= 0.020
    y -= 0.008
    y = c.texto_corrido(
        fig, MARGEM, y, 1 - 2 * MARGEM,
        "PPI_COST = FOB + frete + seguro + câmbio + tarifas (II/AFRMM/antidumping) + custos "
        "portuários + logística interna.", fontsize=8.5, cor=t.COR_TEXTO_SECUNDARIO)
    y -= 0.028
    y_after_bullets = c.callout_numerado(fig, MARGEM, y, 1 - 2 * MARGEM, [
        ("PIA = nível anual", "Receita/volume de HRC no mercado interno, benchmark do IBGE."),
        ("IPP = trajetória mensal", "Índice de Preços ao Produtor (Siderurgia) distribui o nível anual mês a mês."),
        ("Denton = reconciliação", "Proportional Denton concilia a trajetória mensal do IPP com o nível anual da PIA."),
    ])

    # --- GLOSSARY (Sec.27) ---------------------------------------------------
    y_gloss = y_after_bullets - 0.03
    c.secao_titulo(fig, MARGEM, y_gloss, "GLOSSÁRIO")
    y_gloss -= 0.025
    linhas_gloss = [[termo, definicao] for termo, definicao in _GLOSSARIO]
    c.tabela_simples(fig, (MARGEM, y_gloss - 0.135, 1 - 2 * MARGEM, 0.135),
                     ["Termo", "Definição"], linhas_gloss, alinhar_direita_a_partir_de=2)
    y_gloss -= 0.155

    # --- WHAT TO WATCH (Sec.28/29) -------------------------------------------
    c.secao_titulo(fig, MARGEM, y_gloss, "WHAT TO WATCH NEXT")
    y_watch = y_gloss - 0.025
    resumo = dados.get("resumo_executivo")
    contribs_atual = dados.get("decomposicao_ultima_transicao")
    linhas_watch = []
    for driver in _WATCHLIST_DRIVERS:
        nome = motor.NOMES_LEGIVEIS_DRIVERS_IPIA_HRC.get(driver, driver)
        if contribs_atual is not None:
            contrib = float(contribs_atual[driver])
            direcao = narr.direcao_valor_driver(driver, contrib)
            linhas_watch.append([nome, direcao.capitalize(), f"{contrib:+.2f} pts"])
        else:
            linhas_watch.append([nome, "n/d", "n/d"])
    c.tabela_simples(fig, (MARGEM, y_watch - 0.09, 1 - 2 * MARGEM, 0.09),
                     ["Driver", "Current direction", "Recent contribution"], linhas_watch,
                     alinhar_direita_a_partir_de=1)
    y_watch -= 0.11
    y_watch = c.texto_corrido(
        fig, MARGEM, y_watch, 1 - 2 * MARGEM,
        "Direção reflete apenas o mês mais recente decomposto — não é previsão. Cotas/medidas de "
        "defesa comercial ainda não resolvidas (ex. GECEX 929/2026) permanecem risco metodológico: "
        "podem tornar meses futuros UNKNOWN, nunca um resultado direcional presumido.",
        fontsize=8.2, cor=t.COR_TEXTO_SECUNDARIO)

    # --- DATA CUT (Sec.30) ----------------------------------------------------
    # y fixo, mas com folga generosa acima do rodape (que pode ocupar 2
    # linhas quando a lista de fontes for longa, como nesta pagina) -
    # 0.145 colidia visualmente com o rodape (achado de QA visual, Sec.52).
    y_cut = 0.20
    c.secao_titulo(fig, MARGEM, y_cut, "DATA CUT")
    y_cut -= 0.022
    info = [
        ("Reference period", _mes_pt(dados["periodo_atual"]) if dados.get("periodo_atual") is not None else "n/d"),
        ("Vintage", dados["vintage_id"]),
        ("Metodologia", dados["methodology_version"]),
        ("Gerado em", f"{data_geracao:%Y-%m-%d %H:%M} UTC"),
    ]
    largura_bloco = (1 - 2 * MARGEM) / len(info)
    for i, (rotulo, valor) in enumerate(info):
        x = MARGEM + i * largura_bloco
        fig.text(x, y_cut, rotulo, transform=fig.transFigure, fontsize=7.5,
                 color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        fig.text(x, y_cut - 0.017, str(valor), transform=fig.transFigure, fontsize=8, ha="left",
                 color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")

    c.rodape_pagina(fig,
                    "Metodologia completa: docs/METODOLOGIA.md. Decisões: ADR 0009-0016. "
                    "Decomposição: docs/validation/ipia_hrc_driver_decomposition.md.",
                    pagina_num=pagina_num, data_geracao=data_geracao)
