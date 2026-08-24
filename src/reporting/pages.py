"""As 3 paginas do relatorio do IPIA. Cada funcao so desenha - recebe os
DataFrames ja calculados pelo motor (`indices_setoriais.py`, nunca
recalcula nada aqui) e usa os helpers de `components.py`/tokens de
`theme.py`.
"""
from __future__ import annotations

import datetime as dt
import sys
import os

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import indices_setoriais as motor  # noqa: E402  (import apos sys.path, motor de calculo)

from . import theme as t
from . import components as c

MARGEM = t.MARGEM_POL / t.LARGURA_POL

_MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
               "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
_MESES_COMPLETO = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                   "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def _mes_pt(data, abreviado: bool = True) -> str:
    """Nome do mes em portugues, independente do locale do sistema
    (strftime %b/%B usa o locale ativo - neste sistema cai em ingles)."""
    nomes = _MESES_ABREV if abreviado else _MESES_COMPLETO
    return f"{nomes[data.month - 1]}/{data.year}" if abreviado else f"{nomes[data.month - 1]} de {data.year}"


def _gerar_bullets_executivos(df_ipia: pd.DataFrame) -> list:
    """Funcao pura: compara o ultimo mes com o anterior em 3 metricas ja
    calculadas (IPIA, spread domestico-paridade, penetracao de
    importacao) e frasea a direcao/magnitude - nunca uma frase fixa,
    sempre derivada do dado real. Se so houver 1 mes, avisa isso."""
    if len(df_ipia) < 2:
        return [("Histórico insuficiente para comparação",
                 "Menos de 2 meses de dado disponível na série atual.")]
    ultimo, penultimo = df_ipia.iloc[-1], df_ipia.iloc[-2]
    bullets = []

    delta_ipia = ultimo["ipia"] - penultimo["ipia"]
    direcao = "subiu" if delta_ipia > 0 else "caiu" if delta_ipia < 0 else "ficou estável"
    bullets.append((
        f"IPIA {direcao} {abs(delta_ipia):.1f} pontos no mês",
        f"De {penultimo['ipia']:.1f} para {ultimo['ipia']:.1f} pontos "
        f"({_mes_pt(df_ipia.index[-2])} → {_mes_pt(df_ipia.index[-1])})."
    ))

    spread_u = ultimo["preco_domestico_rs_t"] - ultimo["ppi_rs_t"]
    spread_p = penultimo["preco_domestico_rs_t"] - penultimo["ppi_rs_t"]
    delta_spread = spread_u - spread_p
    direcao_s = "ampliou" if delta_spread > 0 else "reduziu" if delta_spread < 0 else "manteve"
    bullets.append((
        f"Spread doméstico vs. paridade {direcao_s} R$ {abs(delta_spread):,.0f}/t",
        f"De R$ {spread_p:,.0f}/t para R$ {spread_u:,.0f}/t no mesmo período."
    ))

    pen_u = ultimo.get("penetracao_importacao_planos_pct")
    pen_p = penultimo.get("penetracao_importacao_planos_pct")
    if pd.notna(pen_u) and pd.notna(pen_p):
        delta_pen = pen_u - pen_p
        direcao_pen = "subiu" if delta_pen > 0 else "caiu" if delta_pen < 0 else "ficou estável"
        rotulo_tipo = "oficial" if ultimo.get("tipo_dado_penetracao") == "oficial_mensal" else "aproximado"
        bullets.append((
            f"Penetração de importação (Planos) {direcao_pen} {abs(delta_pen):.1f} p.p.",
            f"De {pen_p:.1f}% para {pen_u:.1f}% ({rotulo_tipo}, ver docs/adr/0007)."
        ))
    else:
        bullets.append((
            "Penetração de importação sem comparação disponível",
            "Fonte (Instituto Aço Brasil) ainda não cobre os dois meses mais "
            "recentes da série para comparar a variação."
        ))
    return bullets


def pagina_capa(fig, df_ipia: pd.DataFrame, data_geracao: dt.datetime) -> None:
    c.banda_topo(fig, "IPIA — RELATÓRIO MENSAL")
    c.titulo_serif(fig, MARGEM, 0.905, "IPIA", fontsize=34)
    fig.text(MARGEM, 0.865, "Índice de Paridade de Importação do Aço — Bobina Laminada a Quente",
             transform=fig.transFigure, fontsize=12, color=t.COR_TEXTO_PRINCIPAL,
             fontfamily=t.FONTE_SERIF, va="top")

    ultimo = df_ipia.iloc[-1]
    delta_total = df_ipia["ipia"].iloc[-1] - df_ipia["ipia"].iloc[0]
    tendencia = "alta" if delta_total > 0 else "queda" if delta_total < 0 else "estabilidade"
    deck = (f"Paridade em {ultimo['ipia']:.0f} pontos — {tendencia} de "
           f"{abs(delta_total):.1f} pts em {len(df_ipia)} meses")
    fig.text(MARGEM, 0.838, deck, transform=fig.transFigure, fontsize=10.5,
             color=t.COR_ACCENT_2, fontfamily=t.FONTE_SANS, fontstyle="italic", va="top")

    # box "o que o IPIA mede" - linguagem simples, 2-3 frases, sem duplicar METODOLOGIA.md
    ax_exp = c.caixa_destaque(fig, (MARGEM, 0.775, 1 - 2 * MARGEM, 0.045), cor_borda=t.COR_ACCENT_1)
    ax_exp.text(0.02, 0.5,
               "O IPIA compara o custo de importar bobina laminada a quente com o preço "
               "praticado no mercado brasileiro. Acima de 100, importar teria compensado; "
               "abaixo de 100, o produto nacional está mais barato que a paridade de importação.",
               transform=ax_exp.transAxes, fontsize=8.7, color=t.COR_TEXTO_PRINCIPAL,
               fontfamily=t.FONTE_SANS, va="center", wrap=True)

    # sparkline (no lugar da foto - 100% dado real, historico completo do IPIA)
    ax_spark = fig.add_axes((MARGEM, 0.635, 1 - 2 * MARGEM, 0.115))
    ax_spark.plot(df_ipia.index, df_ipia["ipia"], color=t.COR_ACCENT_2, linewidth=1.8)
    ax_spark.fill_between(df_ipia.index, df_ipia["ipia"], df_ipia["ipia"].min(),
                          color=t.COR_ACCENT_2, alpha=0.10)
    ax_spark.axis("off")

    # KPIs
    c.kpi_tile(fig, MARGEM, 0.605, 0.25, "IPIA ATUAL", f"{ultimo['ipia']:.1f}",
              cor_valor=t.COR_ACCENT_2,
              nota=f"{'▲' if delta_total >= 0 else '▼'} {abs(delta_total):.1f} pts no período")
    spread_atual = ultimo["preco_domestico_rs_t"] - ultimo["ppi_rs_t"]
    c.kpi_tile(fig, MARGEM + 0.32, 0.605, 0.25, "SPREAD (DOM. VS. PARIDADE)",
              f"R$ {spread_atual:,.0f}/t")
    penet = ultimo.get("penetracao_importacao_planos_pct")
    tipo_penet = ultimo.get("tipo_dado_penetracao")
    if pd.notna(penet):
        rotulo = "oficial" if tipo_penet == "oficial_mensal" else "aproximado"
        c.kpi_tile(fig, MARGEM + 0.64, 0.605, 0.25, "PENETRAÇÃO (PLANOS)",
                  f"{penet:.1f}%", nota=rotulo)
    else:
        c.kpi_tile(fig, MARGEM + 0.64, 0.605, 0.25, "PENETRAÇÃO (PLANOS)",
                  "n/d", nota="sem dado neste mês")

    c.secao_titulo(fig, MARGEM, 0.535, "O QUE MUDOU")
    c.callout_numerado(fig, (MARGEM, 0.185, 1 - 2 * MARGEM, 0.335),
                       _gerar_bullets_executivos(df_ipia))

    # Report Information
    info = [
        ("Período", f"{_mes_pt(df_ipia.index.min())} – {_mes_pt(df_ipia.index.max())}"),
        ("Frequência", "Mensal"),
        ("Versão da metodologia", motor.VERSAO_METODOLOGIA),
        ("Última atualização", f"{data_geracao:%d/%m/%Y %H:%M}"),
    ]
    y = 0.165
    fig.text(MARGEM, y + 0.018, "REPORT INFORMATION", transform=fig.transFigure, fontsize=8,
             color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")
    largura_bloco = (1 - 2 * MARGEM) / len(info)
    for i, (rotulo, valor) in enumerate(info):
        x = MARGEM + i * largura_bloco
        fig.text(x, y - 0.004, rotulo, transform=fig.transFigure, fontsize=7.5,
                 color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        fig.text(x, y - 0.020, valor, transform=fig.transFigure, fontsize=9,
                 color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")

    c.rodape_pagina(fig,
                    "Fontes: Comex Stat, BCB/SGS, releases trimestrais Usiminas/CSN, "
                    "IBGE/SIDRA, Instituto Aço Brasil. Ver docs/METODOLOGIA.md para a "
                    "metodologia completa.",
                    pagina_num=1, data_geracao=data_geracao)


def pagina_decomposicao_custo(fig, df_ipia: pd.DataFrame, df_custo: pd.DataFrame,
                              data_geracao: dt.datetime, pagina_num: int) -> None:
    c.cabecalho_pagina_interna(fig, "IPIA — Relatório Mensal")
    c.titulo_serif(fig, MARGEM, 0.90, "Decomposição do Custo de Importação", fontsize=19)
    ultimo = df_custo.iloc[-1]
    ultimo_ipia = df_ipia.iloc[-1]
    fig.text(MARGEM, 0.868, f"Mês de referência: {_mes_pt(df_custo.index[-1], abreviado=False)}",
             transform=fig.transFigure, fontsize=9.5, color=t.COR_TEXTO_SECUNDARIO,
             fontfamily=t.FONTE_SANS, va="top")

    fob_brl_t = ultimo["fob_usd_t"] * ultimo["cambio"]
    frete_brl_t = ultimo["frete_usd_t"] * ultimo["cambio"]
    seguro_brl_t = ultimo["seguro_usd_t"] * ultimo["cambio"]
    componentes = [
        ("FOB (China)", fob_brl_t, t.COR_ACCENT_2),
        ("Frete internacional", frete_brl_t, t.PALETA_CATEGORICA[0]),
        ("Seguro", seguro_brl_t, t.PALETA_CATEGORICA[2]),
        ("Imposto de Importação", ultimo["ii_brl_t"], "#6B4226"),
        ("AFRMM", ultimo["afrmm_brl_t"], "#8C6E4A"),
        ("Antidumping", ultimo["antidumping_brl_t"], t.COR_NEGATIVO),
        ("Despesas de porto", ultimo["despesas_porto_rs_t"], "#7F8C8D"),
        ("Frete interno", ultimo["frete_interno_rs_t"], "#95A5A6"),
        ("Margem do importador", ultimo["margem_rs_t"], t.COR_ACCENT_1),
    ]

    ax_wf = fig.add_axes((MARGEM, 0.70, 1 - 2 * MARGEM, 0.13))
    c.grafico_barras_empilhadas(ax_wf, "Custo de\ninternação", componentes,
                                titulo="Do FOB ao custo de internação (R$/t)")

    # comparacao preco domestico vs. custo de internacao. Rotulos curtos e
    # eixo deslocado a direita (reserva espaco a esquerda) - rotulos mais
    # longos ficavam cortados na borda da pagina (y-tick label e desenhado
    # FORA da area do axes, entao precisa de margem propria reservada).
    ax_cmp = fig.add_axes((MARGEM + 0.14, 0.50, 1 - 2 * MARGEM - 0.14, 0.13))
    c.grafico_barras_horizontais(
        ax_cmp, ["Preço doméstico", "Custo de internação"],
        [ultimo_ipia["preco_domestico_rs_t"], ultimo["ppi_brl_t"]],
        cor=t.COR_ACCENT_2, titulo="Preço doméstico vs. custo de internação",
        formato_valor="R$ {:,.0f}/t")
    spread = ultimo_ipia["preco_domestico_rs_t"] - ultimo["ppi_brl_t"]
    fig.text(MARGEM, 0.475,
             f"Spread: R$ {spread:,.0f}/t  ({ultimo_ipia['ipia'] - 100:+.1f} pts em relação à paridade)",
             transform=fig.transFigure, fontsize=9, color=t.COR_TEXTO_PRINCIPAL,
             fontfamily=t.FONTE_SANS, fontweight="bold", va="top")

    total = sum(v for _, v, _ in componentes)
    linhas_tabela = [[nome, f"{valor:,.0f}", f"{valor / total * 100:.1f}%"]
                     for nome, valor, _ in componentes]
    linhas_tabela.append(["Total (custo de internação)", f"{total:,.0f}", "100,0%"])
    c.tabela_simples(fig, (MARGEM, 0.24, 1 - 2 * MARGEM, 0.20),
                     ["Componente", "R$/t", "% do total"], linhas_tabela,
                     alinhar_direita_a_partir_de=1)

    # so o mes de referencia (ultimo) importa aqui - checar a serie inteira
    # (`.any()`) e um bug: o primeiro mes do historico fica NaN (cambio sem
    # valor anterior para o ffill), e NaN != 0 e True no pandas, o que fazia
    # a checagem dar positivo mesmo com antidumping sempre zerado.
    antidumping_confirmado = pd.notna(ultimo["antidumping_brl_t"]) and ultimo["antidumping_brl_t"] != 0
    ax_r = c.caixa_destaque(fig, (MARGEM, 0.145, 1 - 2 * MARGEM, 0.075), cor_borda=t.COR_ACCENT_1)
    nota_antidumping = ("valor real aplicado no período." if antidumping_confirmado else
                        "não confirmado como definitivo — default zerado até confirmação, ver docs/adr da checagem mais recente.")
    ax_r.text(0.02, 0.5,
             f"RESSALVAS: preço doméstico é proxy do segmento \"Siderurgia\" "
             f"({ultimo_ipia['tipo_dado_domestico']}), não específico de bobina a quente "
             f"(ver docs/adr/0003). Antidumping: {nota_antidumping}",
             transform=ax_r.transAxes, fontsize=8, color=t.COR_TEXTO_PRINCIPAL,
             fontfamily=t.FONTE_SANS, va="center", wrap=True)

    c.rodape_pagina(fig,
                    "Fonte: Comex Stat (FOB/frete/seguro), BCB/SGS (câmbio). Componentes "
                    "calculados por custo_importacao_rs_t() — nenhum valor recalculado "
                    "neste relatório.",
                    pagina_num=pagina_num, data_geracao=data_geracao)


def pagina_dashboard(fig, df_ipia: pd.DataFrame, df_custo: pd.DataFrame,
                     df_origem: pd.DataFrame, data_geracao: dt.datetime, pagina_num: int) -> None:
    c.cabecalho_pagina_interna(fig, "IPIA — Relatório Mensal")
    c.titulo_serif(fig, MARGEM, 0.90, "Dashboard — Série Histórica e Indicadores", fontsize=19)

    ultimo = df_ipia.iloc[-1]
    spread = ultimo["preco_domestico_rs_t"] - ultimo["ppi_rs_t"]
    penet = ultimo.get("penetracao_importacao_planos_pct")
    tipo_penet = ultimo.get("tipo_dado_penetracao")
    cambio_atual = df_custo["cambio"].iloc[-1] if len(df_custo) else float("nan")

    y_kpi = 0.855
    c.kpi_tile(fig, MARGEM, y_kpi, 0.22, "IPIA", f"{ultimo['ipia']:.1f}", cor_valor=t.COR_ACCENT_2)
    c.kpi_tile(fig, MARGEM + 0.24, y_kpi, 0.22, "SPREAD", f"R$ {spread:,.0f}/t")
    if pd.notna(penet):
        rotulo = "oficial" if tipo_penet == "oficial_mensal" else "aproximado"
        c.kpi_tile(fig, MARGEM + 0.48, y_kpi, 0.22, "PENETRAÇÃO (PLANOS)", f"{penet:.1f}%", nota=rotulo)
    else:
        c.kpi_tile(fig, MARGEM + 0.48, y_kpi, 0.22, "PENETRAÇÃO (PLANOS)", "n/d")
    c.kpi_tile(fig, MARGEM + 0.72, y_kpi, 0.22, "CÂMBIO (PTAX)", f"R$ {cambio_atual:.2f}")

    # altura reduzida (nao 0.135 como os demais graficos da pagina) - o
    # titulo do grafico e desenhado ACIMA do topo do axes pelo matplotlib
    # (set_title + pad), e o topo padrao colidia com o valor do KPI da
    # linha logo acima.
    ax_ipia = fig.add_axes((MARGEM, 0.665, 1 - 2 * MARGEM, 0.115))
    c.grafico_linha(ax_ipia, df_ipia.index, df_ipia["ipia"], cor=t.COR_ACCENT_2,
                    titulo="IPIA — série histórica", ylabel="Pontos (100 = paridade)",
                    linha_ref=100.0)

    ax_pen = fig.add_axes((MARGEM, 0.475, 1 - 2 * MARGEM, 0.135))
    tem_penet = "penetracao_importacao_planos_pct" in df_ipia.columns and df_ipia["penetracao_importacao_planos_pct"].notna().any()
    if tem_penet:
        serie_pen = df_ipia.dropna(subset=["penetracao_importacao_planos_pct"])
        ax_pen.plot(serie_pen.index, serie_pen["penetracao_importacao_planos_pct"],
                   color=t.COR_APROXIMADO, linestyle="--", linewidth=1.3, marker="o", markersize=3)
        oficiais = serie_pen[serie_pen["tipo_dado_penetracao"] == "oficial_mensal"]
        if len(oficiais):
            ax_pen.scatter(oficiais.index, oficiais["penetracao_importacao_planos_pct"],
                          color=t.COR_ACCENT_2, s=32, zorder=5, marker="D")
        for spine in ("top", "right", "left"):
            ax_pen.spines[spine].set_visible(False)
        ax_pen.spines["bottom"].set_color(t.COR_LINHA_GRADE)
        ax_pen.grid(axis="y", color=t.COR_LINHA_GRADE, linewidth=0.7)
        ax_pen.set_axisbelow(True)
        ax_pen.tick_params(labelsize=7.5, colors=t.COR_TEXTO_SECUNDARIO, length=0)
        ax_pen.set_title("Penetração de importação (Planos) — Instituto Aço Brasil", fontsize=11,
                        fontfamily=t.FONTE_SERIF, fontweight="bold", color=t.COR_TEXTO_PRINCIPAL,
                        loc="left", pad=8)
        ax_pen.set_ylabel("%", fontsize=8, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS)
        handles = [
            Line2D([0], [0], color=t.COR_APROXIMADO, linestyle="--", marker="o", markersize=4,
                  label="Aproximado (Excel — ver docs/adr/0007)"),
            Line2D([0], [0], color=t.COR_ACCENT_2, linestyle="none", marker="D", markersize=5,
                  label="Oficial (PDF Aço Brasil)"),
        ]
        ax_pen.legend(handles=handles, fontsize=6.5, frameon=False, loc="upper left")
    else:
        ax_pen.axis("off")
        ax_pen.text(0.02, 0.5, "Penetração de importação: sem dado disponível na série atual.",
                   transform=ax_pen.transAxes, fontsize=9, color=t.COR_TEXTO_SECUNDARIO,
                   fontfamily=t.FONTE_SANS)

    ax_cambio = fig.add_axes((MARGEM, 0.285, 1 - 2 * MARGEM, 0.135))
    if len(df_custo):
        c.grafico_linha(ax_cambio, df_custo.index, df_custo["cambio"], cor=t.PALETA_CATEGORICA[2],
                        titulo="Câmbio (PTAX venda) — série histórica", ylabel="R$/US$")
    else:
        ax_cambio.axis("off")

    ax_origem = fig.add_axes((MARGEM, 0.135, 1 - 2 * MARGEM, 0.115))
    if df_origem is not None and len(df_origem):
        top = df_origem.head(5)
        mi, mf = df_origem.attrs.get("mes_inicio"), df_origem.attrs.get("mes_fim")
        periodo = f"{_mes_pt(mi)}–{_mes_pt(mf)}" if mi is not None and mf is not None else ""
        c.grafico_barras_horizontais(ax_origem, list(top.index), list(top["pct_do_volume"]),
                                     cor=t.COR_ACCENT_1,
                                     titulo=f"Origem das importações — top países ({periodo})")
    else:
        ax_origem.axis("off")
        ax_origem.text(0.02, 0.5, "Origem das importações: sem dado disponível.",
                      transform=ax_origem.transAxes, fontsize=9, color=t.COR_TEXTO_SECUNDARIO,
                      fontfamily=t.FONTE_SANS)

    c.rodape_pagina(fig,
                    "Fontes: Comex Stat (importação, origem), BCB/SGS (câmbio), releases "
                    "trimestrais Usiminas/CSN (preço doméstico), IBGE/SIDRA IPP (encadeamento "
                    "mensal), Instituto Aço Brasil (penetração de importação, Planos).",
                    pagina_num=pagina_num, data_geracao=data_geracao)
