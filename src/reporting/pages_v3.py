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

_GLOSA_SINAL = {
    # Glosa curta, inline, do rotulo cru de `narr.classificar_sinal_paridade`
    # - nunca aparece "pelado" na capa (auditoria de clareza pre-apresentacao).
    "Domestic Premium": "preço doméstico acima da paridade de importação",
    "Import-Cost Premium": "custo de importação acima do preço doméstico",
    "At Parity": "preço doméstico e custo de importação equivalentes",
}


def _fmt_pts(valor) -> str:
    return "n/d" if valor is None or (isinstance(valor, float) and np.isnan(valor)) else f"{valor:+.1f} pts"


def _fmt_rs(valor) -> str:
    return "n/d" if valor is None or (isinstance(valor, float) and np.isnan(valor)) else f"R$ {valor:,.0f}/t"


# =============================================================================
# PAGE 1 - MARKET VIEW
# =============================================================================

def pagina_market_view(fig, dados: dict, data_geracao: dt.datetime, pagina_num: int) -> None:
    c.banda_topo(fig, "IPIA-HRC — MARKET VIEW")
    # Autoria na propria capa (nao so no rodape) - na faixa de topo, lado
    # oposto ao kicker, para nao consumir orcamento vertical do corpo ja
    # denso da pagina 1.
    fig.text(1 - MARGEM, 0.965, "Preparado por: Matheus Mori · matheus.kengi@gmail.com",
             transform=fig.transFigure, fontsize=t.TAM_CORPO_PEQUENO, color="white", fontfamily=t.FONTE_SANS,
             ha="right", va="center")

    if dados.get("ipia_atual") is None:
        c.titulo_serif(fig, MARGEM, 0.905, "IPIA-HRC", fontsize=t.TAM_TITULO_CAPA_V3)
        fig.text(MARGEM, 0.85, "Sem dado publicado nesta vintage.", transform=fig.transFigure,
                 fontsize=t.TAM_KICKER, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        c.rodape_pagina(fig, "Sem fontes aplicáveis — sem dado.", pagina_num=pagina_num, data_geracao=data_geracao)
        return

    ipia_atual = dados["ipia_atual"]
    cor_hero = _COR_PROVISIONAL_HRC if dados["is_provisional_atual"] else t.COR_ACCENT_2
    periodo_txt = _mes_pt(dados["periodo_atual"], abreviado=False)

    # --- COMO LER ESTE RELATORIO (orientacao antes de qualquer numero) ------
    # Paragrafo compacto (texto_corrido, ja usado no resto da pagina) em vez
    # de callout_numerado com caixa - a versao em caixa com 3 itens estourou
    # o rodape no primeiro render (achado de QA visual desta mesma tarefa),
    # nao ha orcamento vertical na capa para uma caixa cheia aqui.
    y_como = 0.912
    c.secao_titulo(fig, MARGEM, y_como, "COMO LER ESTE RELATÓRIO", fontsize=t.TAM_CORPO_SECUNDARIO)
    y_como -= 0.016
    y_como = c.texto_corrido(
        fig, MARGEM, y_como, 1 - 2 * MARGEM,
        "IPIA-HRC é um índice experimental e independente de paridade de custo de importação de "
        "bobina a quente — não é um relatório de agência de rating nem recomendação de investimento. "
        "Roteiro: pág. 1 traz o número principal e o que mudou no mês; pág. 2, de onde vem o custo "
        "de importar; pág. 3, histórico e status de confiabilidade do dado (Publication-grade/"
        "Experimental/Provisório, detalhados lá); pág. 4, metodologia completa e glossário de "
        "termos técnicos (PPI_COST, PPI_OFFER e outros).",
        fontsize=t.TAM_CORPO_MINIMO, cor=t.COR_TEXTO_SECUNDARIO)

    # DELTA desloca todo o restante da capa para baixo, na mesma medida do
    # bloco acima — o espacamento relativo entre hero/KPI/sinal permanece
    # identico ao original (Sec.5/10), so a ancora de topo muda.
    y_hero = y_como - 0.02
    DELTA_CAPA = 0.895 - y_hero

    # --- HERO NUMBER (Sec.5) ------------------------------------------------
    fig.text(MARGEM, y_hero, f"{ipia_atual:.1f}", transform=fig.transFigure, fontsize=t.TAM_HERO_NUMERO,
             color=cor_hero, fontfamily=t.FONTE_SERIF, fontweight="bold", va="top")
    fig.text(MARGEM, 0.825 - DELTA_CAPA,
             f"IPIA-HRC  ·  {dados['rotulo_atual']}  ·  {periodo_txt}  ·  paridade = 100",
             transform=fig.transFigure, fontsize=t.TAM_SUBTITULO_PAGINA, color=t.COR_TEXTO_SECUNDARIO,
             fontfamily=t.FONTE_SANS, va="top")

    x_kpi = MARGEM + 0.44
    c.kpi_tile(fig, x_kpi, y_hero, 0.26, "Δ MOM", _fmt_pts(dados["delta_mom_ipia"]),
              cor_valor=t.COR_TEXTO_PRINCIPAL)
    c.kpi_tile(fig, x_kpi + 0.28, y_hero, 0.26, "Δ YOY", _fmt_pts(dados["delta_yoy_ipia"]),
              cor_valor=t.COR_TEXTO_PRINCIPAL)

    # --- IMPORT PARITY SIGNAL (Sec.10) --------------------------------------
    sinal = narr.classificar_sinal_paridade(ipia_atual)
    y_sinal = 0.775 - DELTA_CAPA
    fig.text(MARGEM, y_sinal, "IMPORT PARITY SIGNAL", transform=fig.transFigure, fontsize=t.TAM_CORPO_PEQUENO,
             color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")
    glosa_sinal = _GLOSA_SINAL.get(sinal["categoria"], "")
    texto_sinal = (f"{sinal['categoria']} — {glosa_sinal} ({sinal['distancia_pts']:+.1f} pts vs. 100)"
                  if glosa_sinal else
                  f"{sinal['categoria']}  ({sinal['distancia_pts']:+.1f} pts vs. 100)")
    y_sinal_fim = c.texto_corrido(fig, MARGEM, y_sinal - 0.020, 1 - 2 * MARGEM, texto_sinal,
                                  fontsize=t.TAM_TITULO_GRAFICO, cor=cor_hero, bold=True)

    # --- HEADLINE + INTERPRETACAO (narrativa determinística) ---------------
    resumo = dados.get("resumo_executivo")
    y_head = y_sinal_fim - 0.020
    if resumo is not None:
        y_after = c.texto_corrido(fig, MARGEM, y_head, 1 - 2 * MARGEM, resumo["interpretation"],
                                  fontsize=t.TAM_DECK_CAPA, bold=True)
        y_after -= 0.012
        y_after = c.texto_corrido(fig, MARGEM, y_after, 1 - 2 * MARGEM, resumo["parity_interpretation"],
                                  fontsize=t.TAM_CORPO_PADRAO, cor=t.COR_TEXTO_SECUNDARIO)
    else:
        y_after = c.texto_corrido(fig, MARGEM, y_head, 1 - 2 * MARGEM,
                                  narr.montar_interpretacao_100(ipia_atual), fontsize=t.TAM_DECK_CAPA, bold=True)
        y_after = c.texto_corrido(
            fig, MARGEM, y_after - 0.012, 1 - 2 * MARGEM,
            "Decomposição de drivers indisponível para esta vintage (mês anterior sem transição "
            "calculável ou artefato de decomposição não gerado) — ver página 4.",
            fontsize=t.TAM_CORPO_SECUNDARIO, cor=t.COR_TEXTO_SECUNDARIO)

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
                                          fontsize=t.TAM_CORPO_PADRAO, cor=t.COR_TEXTO_SECUNDARIO)

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
        fig.text(x, y_info, rotulo, transform=fig.transFigure, fontsize=t.TAM_ROTULO_AUXILIAR,
                 color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        fig.text(x, y_info - 0.017, str(valor), transform=fig.transFigure, fontsize=t.TAM_CORPO_SECUNDARIO,
                 color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")

    # --- RISCOS + DISCLAIMER (capa) ------------------------------------------
    # "Principais Premissas" migrou para o topo da pagina 2 (decisao de
    # reorg da capa, revisada com o usuario antes de mexer). "Riscos a
    # Monitorar" deixou de ser bloco com titulo proprio - agora e 1 linha so,
    # colada ao disclaimer, para reduzir a densidade da capa mantendo o aviso
    # do GECEX visivel na primeira pagina.
    y_extra = y_info - 0.045
    y_extra = c.texto_corrido(
        fig, MARGEM, y_extra, 1 - 2 * MARGEM,
        "Riscos: cotas/medidas de defesa comercial não resolvidas (ex. GECEX 929/2026) — ver "
        "Watchlist, pág. 4.",
        fontsize=t.TAM_CORPO_COMPACTO, cor=t.COR_TEXTO_SECUNDARIO)
    fig.text(MARGEM, y_extra - 0.014, "Pesquisa independente — não constitui recomendação de investimento.",
             transform=fig.transFigure, fontsize=t.TAM_NOTA_FONTE_SECUNDARIA, color=t.COR_TEXTO_SECUNDARIO,
             fontfamily=t.FONTE_SANS, fontstyle="italic", va="top")

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
    titulo_serif(fig, MARGEM, 0.90, "Paridade de Importação & Drivers", fontsize=t.TAM_TITULO_PAGINA)

    if dados.get("ppi_atual") is None:
        fig.text(MARGEM, 0.85, "Sem dado publicado nesta vintage.", transform=fig.transFigure,
                 fontsize=t.TAM_KICKER, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        c.rodape_pagina(fig, "Sem fontes aplicáveis — sem dado.", pagina_num=pagina_num, data_geracao=data_geracao)
        return

    periodo_txt = _mes_pt(dados["periodo_atual"], abreviado=False)
    # Narrativa mensal (Sec.55) so aparece em meses com arquivo aprovado -
    # os tres ganhos de espaco abaixo (premissas/waterfall/pos-tabela) so se
    # aplicam NESSES meses, para abrir espaco real para o paragrafo sem
    # mudar 1px o layout de todo mes em que a secao nao existe.
    _tem_narrativa = dados.get("narrativa_mensal") is not None

    # --- PPI_COST headline + Offer opcional (Sec.11/12) ---------------------
    y = 0.845
    fig.text(MARGEM, y, f"PPI_COST — {periodo_txt}", transform=fig.transFigure, fontsize=t.TAM_CORPO_PADRAO,
             color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")
    fig.text(MARGEM, y - 0.028, _fmt_rs(dados["ppi_atual"]), transform=fig.transFigure, fontsize=t.TAM_HERO_SECUNDARIO,
             color=t.COR_ACCENT_2, fontfamily=t.FONTE_SERIF, fontweight="bold", va="top")
    if dados.get("ppi_offer_atual") is not None:
        fig.text(MARGEM + 0.45, y, "PPI_OFFER — PPI_COST + margem", transform=fig.transFigure,
                 fontsize=t.TAM_CORPO_PEQUENO, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        fig.text(MARGEM + 0.45, y - 0.013, "comercial de 3% (cenário analítico)", transform=fig.transFigure,
                 fontsize=t.TAM_CORPO_PEQUENO, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        fig.text(MARGEM + 0.45, y - 0.035, _fmt_rs(dados["ppi_offer_atual"]), transform=fig.transFigure,
                 fontsize=t.TAM_VALOR_SECUNDARIO, color=t.COR_APROXIMADO, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")

    # --- PRINCIPAIS PREMISSAS (migrado da capa - reorg revisada com o -------
    # usuario antes de mexer: pagina 1 estava densa demais, este bloco tem
    # melhor lugar tematico aqui, ao lado do PPI_COST/decomposicao que ele
    # descreve, no espaco que ja existia antes do Grafico 1).
    y_premissas = y - (0.078 if _tem_narrativa else 0.095)
    c.secao_titulo(fig, MARGEM, y_premissas, "PRINCIPAIS PREMISSAS", fontsize=t.TAM_CORPO_PADRAO)
    y_premissas -= 0.017
    y_premissas = c.texto_corrido(
        fig, MARGEM, y_premissas, 1 - 2 * MARGEM,
        "Preço doméstico ancorado nas divulgações públicas ponderadas de Usiminas e CSN (ADR 0001). "
        "PPI_COST exclui margem comercial desde a metodologia 1.5 (ADR 0015). Drivers decompostos "
        "por Shapley exato, resíduo ≈0 por construção (ADR 0016).",
        fontsize=t.TAM_CORPO_COMPACTO, cor=t.COR_TEXTO_SECUNDARIO)

    # --- WATERFALL (Sec.13/14) ------------------------------------------------
    # Alturas deste grafico e dos dois blocos seguintes (tabela, composicao)
    # levemente reduzidas em relacao ao original - a migracao do bloco
    # Premissas para cima deste grafico (reorg de densidade da capa, revisada
    # com o usuario) empurrou todo o resto da pagina para baixo; sem esse
    # ajuste o rodape do Grafico 2 colidia com a citacao de fontes (achado de
    # QA visual desta mesma tarefa). Rotulos/numeros continuam legiveis nas
    # novas alturas.
    y_top1 = c.cabecalho_grafico(
        fig, MARGEM, y_premissas - 0.012, 1 - 2 * MARGEM,
        (f"Gráfico 1: IPIA-HRC — de {_mes_pt(dados['decomposicao_ultima_transicao']['previous_reference_period'])} "
        f"a {periodo_txt}" if dados.get("decomposicao_disponivel")
        else "Gráfico 1: IPIA-HRC — decomposição indisponível"),
        interpretacao=(dados["resumo_executivo"]["what_changed"]["sentenca"]
                      if dados.get("resumo_executivo") else None))
    altura_wf = 0.135 if _tem_narrativa else 0.15
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
                  transform=ax_wf.transAxes, fontsize=t.TAM_CORPO_PADRAO, color=t.COR_TEXTO_SECUNDARIO,
                  fontfamily=t.FONTE_SANS)

    # --- DRIVER TABLE, top 5 por |contribuicao| (Sec.15) --------------------
    # Gap de 0.045 (nao reduzido) - e o respiro para os rotulos do eixo X do
    # waterfall, que ficam rotacionados 20 graus e estouram para baixo da
    # area do axes; reduzir esse gap especifico colidia com o titulo da
    # tabela (achado de QA visual desta mesma tarefa).
    y_tab = y_top1 - altura_wf - 0.045
    c.secao_titulo(fig, MARGEM, y_tab, "TOP 5 DRIVERS DO MÊS")
    y_tab -= 0.025
    if dados.get("decomposicao_disponivel"):
        linha = dados["decomposicao_ultima_transicao"]
        ranking = narr.ranking_drivers({d: float(linha[d]) for d in motor.DRIVERS_PPI_COST})[:5]
        # Marcador tipografico (Sec.56, ADR 0018) - asterisco no nome, NUNCA icone
        # (principio de design ja definido: relatorio nao tem aparencia de dashboard).
        # Decisao de QUAIS drivers marcar fica em narrative.drivers_com_marcador_atipico
        # (funcao pura, testavel sem matplotlib) - aqui so desenha.
        drivers_marcados = narr.drivers_com_marcador_atipico(ranking, dados.get("diagnostico_importacao_atual"))
        tem_marcador = bool(drivers_marcados)
        linhas_tabela = [
            [motor.NOMES_LEGIVEIS_DRIVERS_IPIA_HRC.get(d, d) + ("*" if d in drivers_marcados else ""),
            f"{v:+.2f} pts",
            "Alta" if narr.direcao_valor_driver(d, v) == "alta" else
            "Queda" if narr.direcao_valor_driver(d, v) == "queda" else "Estável"]
            for d, v in ranking
        ]
        c.tabela_simples(fig, (MARGEM, y_tab - 0.10, 1 - 2 * MARGEM, 0.10),
                         ["Driver", "Contribution", "Direction"], linhas_tabela, alinhar_direita_a_partir_de=1)
        # Gap pos-tabela menor quando o rodape do marcador tambem vai ser desenhado -
        # o total (gap + rodape) fica igual ao caso "so narrativa" ja validado por
        # render (achado de QA visual desta mesma tarefa: sem esse ajuste, narrativa +
        # marcador juntos - o pior caso, ex. jun/2026 - quase colidiam com o rodape).
        if tem_marcador:
            y_tab -= 0.10 if _tem_narrativa else 0.11
            fig.text(MARGEM, y_tab, "* Volume do mês abaixo do padrão histórico — ver Data Confidence, pág. 3.",
                     transform=fig.transFigure, fontsize=t.TAM_SELO, color=t.COR_TEXTO_SECUNDARIO,
                     fontfamily=t.FONTE_SANS, fontstyle="italic", va="top")
            y_tab -= 0.010
        else:
            y_tab -= 0.11 if _tem_narrativa else 0.12
    else:
        y_tab -= 0.02

    # --- IMPORT COST COMPOSITION (Sec.16) -----------------------------------
    y_comp = y_tab - 0.01
    interp_comp = "Onde está o custo de importação — composição do PPI_COST no período mais recente."
    y_top2 = c.cabecalho_grafico(fig, MARGEM, y_comp, 1 - 2 * MARGEM,
                                 "Gráfico 2: Composição do PPI_COST", interpretacao=interp_comp)
    altura_comp = 0.075
    if dados.get("composicao_ppi_disponivel"):
        comp = dados["composicao_ppi_mes_atual"]
        componentes = [
            ("CIF (FOB+frete+seguro)", comp["cif_brl_t"], t.PALETA_CATEGORICA[0]),
            ("II", comp["ii_brl_t"], t.COR_II),
            ("AFRMM", comp["afrmm_brl_t"], t.COR_AFRMM),
            ("Antidumping", comp["antidumping_brl_t"], t.COR_NEGATIVO),
            ("Desp. portuárias", comp["d_porto_rs_t"], t.COR_DESPESAS_PORTO),
            ("Frete interno", comp["d_interno_rs_t"], t.COR_FRETE_INTERNO),
        ]
        ax_comp = fig.add_axes((MARGEM, y_top2 - altura_comp, 1 - 2 * MARGEM, altura_comp))
        c.grafico_barras_empilhadas(ax_comp, "PPI_COST", componentes)
    else:
        ax_comp = fig.add_axes((MARGEM, y_top2 - altura_comp, 1 - 2 * MARGEM, altura_comp))
        ax_comp.axis("off")
        ax_comp.text(0.02, 0.5, "Composição granular indisponível para este período.",
                    transform=ax_comp.transAxes, fontsize=t.TAM_CORPO_PADRAO, color=t.COR_TEXTO_SECUNDARIO,
                    fontfamily=t.FONTE_SANS)

    # --- NARRATIVA DO MÊS (Sec.55 - semi-manual, revisada por humano) -------
    # `dados["narrativa_mensal"]` so existe quando um arquivo
    # docs/research/AAAA-MM-narrativa.md foi APROVADO explicitamente
    # (narrativa_mensal.carregar_narrativa_aprovada, ADR 0017) - rascunho,
    # ausente ou malformado ja chegam aqui como None, e a pagina segue
    # identica a antes desta secao existir (nunca fabrica/mostra rascunho).
    narrativa = dados.get("narrativa_mensal")
    if narrativa is not None:
        y_narr = y_top2 - altura_comp - 0.025
        c.secao_titulo(fig, MARGEM, y_narr, "NARRATIVA DO MÊS", fontsize=t.TAM_CORPO_PADRAO)
        y_narr -= 0.017
        y_narr = c.texto_corrido(fig, MARGEM, y_narr, 1 - 2 * MARGEM, narrativa["texto"], fontsize=t.TAM_CORPO_COMPACTO)
        y_narr -= 0.007
        fig.text(MARGEM, y_narr,
                 f"Revisado por: {narrativa['revisado_por']} em {narrativa['data_revisao']} — "
                 "contexto qualitativo com revisão humana explícita, não gerado automaticamente.",
                 transform=fig.transFigure, fontsize=t.TAM_CITACAO_REVISOR, color=t.COR_TEXTO_SECUNDARIO,
                 fontfamily=t.FONTE_SANS, fontstyle="italic", va="top")

    c.rodape_pagina(fig,
                    "PPI_COST não inclui margem comercial desde a metodologia 1.5 (ADR 0015). Decomposição: "
                    "Shapley exato sobre 10 drivers, resíduo ≈0 por construção (ADR 0016).",
                    pagina_num=pagina_num, data_geracao=data_geracao)


# =============================================================================
# PAGE 3 - HISTORY & CONFIDENCE
# =============================================================================

_ROTULOS_STATUS_HUMANOS = {
    # Mesmos rotulos humanos ja usados na legenda do grafico historico -
    # so para casar a coluna "Status" desta tabela com o que o leitor ja
    # viu no grafico (a descricao vem pronta, ja aceita, de `_LEGENDA_STATUS_HRC`).
    STATUS_PUBLICATION_GRADE_HRC: "Publication-grade",
    STATUS_EXPERIMENTAL_HRC: "Experimental",
    "PROVISIONAL": "Provisório",
}


def pagina_history_confidence(fig, dados: dict, data_geracao: dt.datetime, pagina_num: int) -> None:
    from .components import cabecalho_pagina_interna, titulo_serif
    cabecalho_pagina_interna(fig, "IPIA-HRC — Relatório")
    titulo_serif(fig, MARGEM, 0.90, "Histórico & Confiança", fontsize=t.TAM_TITULO_PAGINA)

    combinada = dados["combinada"]
    if combinada.empty:
        fig.text(MARGEM, 0.85, "Sem dado publicado nesta vintage.", transform=fig.transFigure,
                 fontsize=t.TAM_KICKER, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        c.rodape_pagina(fig, "Sem fontes aplicáveis — sem dado.", pagina_num=pagina_num, data_geracao=data_geracao)
        return

    # --- HISTORICO COMPLETO (Sec.17/18/20) -----------------------------------
    titulo_hist = "Gráfico 3: " + (
                  "IPIA-HRC recuou no mês, mas segue "
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
    ax_hist.set_ylabel("Pontos (100 = paridade)", fontsize=t.TAM_CORPO_PEQUENO, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS)

    # --- SIGNIFICADO DOS STATUS (glosa dos rotulos da legenda acima) --------
    y_legenda_status = y_top1 - altura1 - 0.02
    linhas_legenda_status = [[_ROTULOS_STATUS_HUMANOS.get(status, status), desc]
                             for status, desc in _LEGENDA_STATUS_HRC]
    c.tabela_simples(fig, (MARGEM, y_legenda_status - 0.075, 1 - 2 * MARGEM, 0.075),
                     ["Status", "Significado"], linhas_legenda_status, alinhar_direita_a_partir_de=2)

    # --- POSICAO HISTORICA (Sec.19) ------------------------------------------
    y_pos = y_legenda_status - 0.075 - 0.03
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
    y_pos = c.texto_corrido(fig, MARGEM, y_pos, 1 - 2 * MARGEM, texto_confianca, fontsize=t.TAM_CORPO_DISCLOSURE)
    y_pos -= 0.018
    y_pos = c.texto_corrido(fig, MARGEM, y_pos, 1 - 2 * MARGEM, _DISCLOSURE_PROXY_DOMESTICO,
                            fontsize=t.TAM_NOTA_METODOLOGICA, cor=t.COR_TEXTO_SECUNDARIO)
    y_pos -= 0.018
    y_pos = c.texto_corrido(fig, MARGEM, y_pos, 1 - 2 * MARGEM, _DISCLOSURE_BAIXA_LIQUIDEZ,
                            fontsize=t.TAM_NOTA_METODOLOGICA, cor=t.COR_TEXTO_SECUNDARIO)
    y_pos -= 0.018
    y_pos = c.texto_corrido(
        fig, MARGEM, y_pos, 1 - 2 * MARGEM,
        "O FOB é um valor unitário derivado do comércio realizado, não um price assessment de agência; "
        "mudanças de composição do mix importado podem afetar o valor — ver docs/METODOLOGIA.md §9.7.",
        fontsize=t.TAM_NOTA_METODOLOGICA, cor=t.COR_TEXTO_SECUNDARIO)

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
    titulo_serif(fig, MARGEM, 0.90, "Metodologia & Watchlist", fontsize=t.TAM_TITULO_PAGINA)

    # --- METODOLOGIA EM 30 SEGUNDOS (Sec.24/25/26) ---------------------------
    c.secao_titulo(fig, MARGEM, 0.855, "METODOLOGIA EM 30 SEGUNDOS")
    y = 0.828
    for linha_diagrama in ("Comex Stat  →  PPI_COST",
                          "PIA-HRC + IPP-242  →  Preço doméstico",
                          "Preço doméstico / PPI_COST × 100  →  IPIA-HRC"):
        fig.text(MARGEM, y, linha_diagrama, transform=fig.transFigure, fontsize=t.TAM_SUBTITULO_PAGINA,
                 color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")
        y -= 0.020
    y -= 0.008
    y = c.texto_corrido(
        fig, MARGEM, y, 1 - 2 * MARGEM,
        "PPI_COST = FOB + frete + seguro + câmbio + tarifas (II/AFRMM/antidumping) + custos "
        "portuários + logística interna.", fontsize=t.TAM_CORPO_SECUNDARIO, cor=t.COR_TEXTO_SECUNDARIO)
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
        fontsize=t.TAM_NOTA_METODOLOGICA, cor=t.COR_TEXTO_SECUNDARIO)

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
        fig.text(x, y_cut, rotulo, transform=fig.transFigure, fontsize=t.TAM_ROTULO_AUXILIAR,
                 color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        fig.text(x, y_cut - 0.017, str(valor), transform=fig.transFigure, fontsize=t.TAM_CORPO_PEQUENO, ha="left",
                 color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")

    # --- RELATED RESEARCH (pontes para as fontes do proprio projeto) --------
    # Uma linha so, sem titulo em linha separada - pagina 4 ja tem orcamento
    # vertical apertado entre DATA CUT e o rodape (achado de QA visual desta
    # mesma tarefa: a primeira versao com titulo+paragrafo colidiu com o
    # rodape).
    y_related = y_cut - 0.017 - 0.024
    c.texto_corrido(
        fig, MARGEM, y_related, 1 - 2 * MARGEM,
        "Related Research — Instituto Aço Brasil (dados setoriais) · docs/METODOLOGIA.md · "
        "ADRs 0001, 0015, 0016 (âncora doméstica, escopo PPI_COST, decomposição Shapley)",
        fontsize=t.TAM_NOTA_FONTE_SECUNDARIA, cor=t.COR_TEXTO_SECUNDARIO)

    c.rodape_pagina(fig,
                    "Metodologia completa: docs/METODOLOGIA.md. Decisões: ADR 0009-0016. "
                    "Decomposição: docs/validation/ipia_hrc_driver_decomposition.md.",
                    pagina_num=pagina_num, data_geracao=data_geracao)
