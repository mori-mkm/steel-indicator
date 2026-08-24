"""Blocos de desenho reutilizaveis entre as paginas do relatorio do IPIA.

Cada funcao recebe `fig` (ou um `Axes` ja criado) e coordenadas/dados ja
calculados - nenhuma funcao aqui calcula nada, so desenha (ver
docs/report_design_system.md para os tokens usados). pages.py decide o
grid de cada pagina e chama estes helpers.
"""
from __future__ import annotations

import textwrap
from typing import Optional, Sequence

import matplotlib.patches as mpatches

from . import theme as t


def banda_topo(fig, kicker: str) -> None:
    """Banda escura de topo (so na capa), com o kicker em branco."""
    fig.add_artist(mpatches.Rectangle(
        (0, 0.93), 1, 0.07, transform=fig.transFigure, facecolor=t.COR_BANDA_TOPO,
        edgecolor="none", zorder=0))
    fig.text(t.MARGEM_POL / t.LARGURA_POL, 0.965, kicker, transform=fig.transFigure,
             fontsize=10, color="white", fontfamily=t.FONTE_SANS,
             fontweight="bold", va="center")


def titulo_serif(fig, x: float, y: float, texto: str, fontsize: float = 26,
                 cor: str = t.COR_TEXTO_PRINCIPAL, ha: str = "left") -> None:
    fig.text(x, y, texto, transform=fig.transFigure, fontsize=fontsize, color=cor,
             fontfamily=t.FONTE_SERIF, fontweight="bold", ha=ha, va="top")


def secao_titulo(fig, x: float, y: float, texto: str, fontsize: float = 12) -> None:
    fig.text(x, y, texto, transform=fig.transFigure, fontsize=fontsize,
             color=t.COR_ACCENT_1, fontfamily=t.FONTE_SANS, fontweight="bold",
             ha="left", va="top")


def cabecalho_pagina_interna(fig, texto: str) -> None:
    """Cabecalho pequeno no topo das paginas internas (2 e 3)."""
    fig.text(t.MARGEM_POL / t.LARGURA_POL, 1 - 0.35 / t.ALTURA_POL, texto,
             transform=fig.transFigure, fontsize=8.5, color=t.COR_TEXTO_SECUNDARIO,
             fontfamily=t.FONTE_SANS, fontweight="bold", va="top")


def rodape_pagina(fig, fontes_texto: str, pagina_num: int, data_geracao) -> None:
    margem_x = t.MARGEM_POL / t.LARGURA_POL
    y_texto = 0.11
    fig.text(margem_x, y_texto, textwrap.fill(fontes_texto, width=105),
             transform=fig.transFigure, fontsize=6.8, color=t.COR_TEXTO_SECUNDARIO,
             fontfamily=t.FONTE_SANS, va="top")
    y_barra = 0.045
    fig.text(margem_x, y_barra, "IPIA Brasil", transform=fig.transFigure,
             fontsize=8, color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS,
             fontweight="bold", va="center")
    fig.text(1 - margem_x, y_barra, f"{data_geracao:%d/%m/%Y}   {pagina_num}",
             transform=fig.transFigure, fontsize=8, color=t.COR_TEXTO_SECUNDARIO,
             fontfamily=t.FONTE_SANS, ha="right", va="center")


def kpi_tile(fig, x: float, y: float, largura: float, rotulo: str, valor_texto: str,
            cor_valor: str = t.COR_TEXTO_PRINCIPAL, nota: Optional[str] = None) -> None:
    """Um KPI: rotulo pequeno em cima, valor grande embaixo, nota opcional."""
    fig.text(x, y, rotulo, transform=fig.transFigure, fontsize=8.5,
             color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
    fig.text(x, y - 0.022, valor_texto, transform=fig.transFigure, fontsize=17,
             color=cor_valor, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")
    if nota:
        fig.text(x, y - 0.045, nota, transform=fig.transFigure, fontsize=7.5,
                 color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")


def caixa_destaque(fig, rect: tuple, cor_borda: str = t.COR_ACCENT_1):
    """Caixa de fundo COR_DESTAQUE_FUNDO (usada para callouts e para a
    explicacao em linguagem simples da capa). Retorna o Axes criado, off
    (sem eixo), para quem chamou escrever texto dentro."""
    ax = fig.add_axes(rect)
    ax.axis("off")
    ax.add_patch(mpatches.FancyBboxPatch(
        (0, 0), 1, 1, transform=ax.transAxes, boxstyle="round,pad=0.02,rounding_size=0.02",
        facecolor=t.COR_DESTAQUE_FUNDO, edgecolor=cor_borda, linewidth=1))
    return ax


def callout_numerado(fig, rect: tuple, itens: Sequence[tuple]) -> None:
    """Caixa de destaque com itens numerados (headline colorido + corpo).
    itens: lista de (headline, corpo). Espacamento calibrado pelo numero de
    linhas de cada corpo (nao pela altura total da caixa dividida
    igualmente por item) - senao itens curtos deixam vaos grandes entre
    si, com o espaco sobrando concentrado so no fim da caixa."""
    ax = caixa_destaque(fig, rect)
    y = 0.93
    for i, (headline, corpo) in enumerate(itens, start=1):
        ax.text(0.03, y, f"{i}. {headline}", transform=ax.transAxes, fontsize=9.5,
               color=t.COR_ACCENT_2, fontfamily=t.FONTE_SANS, fontweight="bold",
               va="top", wrap=True)
        y -= 0.075
        corpo_quebrado = textwrap.fill(corpo, width=95)
        n_linhas = corpo_quebrado.count("\n") + 1
        ax.text(0.03, y, corpo_quebrado, transform=ax.transAxes,
               fontsize=8.5, color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS, va="top")
        y -= 0.045 * n_linhas + 0.06


def grafico_linha(ax, x, y, cor: str = t.COR_ACCENT_2, titulo: Optional[str] = None,
                  ylabel: Optional[str] = None, linha_ref: Optional[float] = None,
                  linestyle: str = "-", marker: str = "o") -> None:
    """Estilo padrao de grafico de linha: sem moldura, so grade horizontal."""
    ax.plot(x, y, color=cor, linestyle=linestyle, marker=marker, markersize=3.5, linewidth=1.6)
    if linha_ref is not None:
        ax.axhline(linha_ref, linestyle="--", color=t.COR_TEXTO_SECUNDARIO, linewidth=0.8)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(t.COR_LINHA_GRADE)
    ax.grid(axis="y", color=t.COR_LINHA_GRADE, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=7.5, colors=t.COR_TEXTO_SECUNDARIO, length=0)
    if titulo:
        ax.set_title(titulo, fontsize=11, fontfamily=t.FONTE_SERIF, fontweight="bold",
                    color=t.COR_TEXTO_PRINCIPAL, loc="left", pad=8)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS)


def grafico_barras_empilhadas(ax, rotulo: str, componentes: Sequence[tuple], titulo: Optional[str] = None) -> None:
    """Barra empilhada horizontal (decomposicao de custo). componentes:
    lista de (nome, valor, cor)."""
    total = sum(v for _, v, _ in componentes) or 1.0
    esquerda = 0.0
    for nome, valor, cor in componentes:
        ax.barh([rotulo], [valor], left=esquerda, color=cor, edgecolor="white", linewidth=0.5)
        # so escreve o rotulo dentro do segmento se ele for largo o bastante
        # para nao colidir com o vizinho (segmentos finos - ex. seguro,
        # AFRMM - ficam sem numero no grafico, mas continuam exatos na
        # tabela logo abaixo, nenhum dado escondido)
        if valor / total > 0.04:
            ax.text(esquerda + valor / 2, 0, f"{valor:,.0f}", ha="center", va="center",
                   fontsize=7, color="white", fontfamily=t.FONTE_SANS, fontweight="bold")
        esquerda += valor
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_yticks([])
    ax.tick_params(axis="x", labelsize=7.5, colors=t.COR_TEXTO_SECUNDARIO)
    ax.grid(axis="x", color=t.COR_LINHA_GRADE, linewidth=0.7)
    ax.set_axisbelow(True)
    if titulo:
        ax.set_title(titulo, fontsize=11, fontfamily=t.FONTE_SERIF, fontweight="bold",
                    color=t.COR_TEXTO_PRINCIPAL, loc="left", pad=8)


def grafico_barras_horizontais(ax, rotulos: Sequence[str], valores: Sequence[float],
                               cor: str = t.COR_ACCENT_2, titulo: Optional[str] = None,
                               formato_valor: str = "{:.1f}%") -> None:
    y_pos = range(len(rotulos))
    ax.barh(list(y_pos), valores, color=cor)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(rotulos, fontsize=8.5, fontfamily=t.FONTE_SANS, color=t.COR_TEXTO_PRINCIPAL)
    ax.invert_yaxis()
    for i, v in enumerate(valores):
        ax.text(v, i, f" {formato_valor.format(v)}", va="center", fontsize=8,
               color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS)
    for spine in ("top", "right", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.set_xticks([])
    if titulo:
        ax.set_title(titulo, fontsize=11, fontfamily=t.FONTE_SERIF, fontweight="bold",
                    color=t.COR_TEXTO_PRINCIPAL, loc="left", pad=8)


def tabela_simples(fig, rect: tuple, colunas: Sequence[str], linhas: Sequence[Sequence[str]],
                   alinhar_direita_a_partir_de: int = 1) -> None:
    """Tabela desenhada manualmente: cabecalho com fundo COR_DESTAQUE_FUNDO,
    linhas finas entre registros, colunas de dado alinhadas a direita."""
    ax = fig.add_axes(rect)
    ax.axis("off")
    n_linhas = len(linhas) + 1
    n_cols = len(colunas)
    largura_col = 1.0 / n_cols
    altura_linha = 1.0 / n_linhas

    ax.add_patch(mpatches.Rectangle(
        (0, 1 - altura_linha), 1, altura_linha, transform=ax.transAxes,
        facecolor=t.COR_DESTAQUE_FUNDO, edgecolor="none"))
    for c, nome in enumerate(colunas):
        ha = "left" if c < alinhar_direita_a_partir_de else "right"
        x = c * largura_col + (0.01 if ha == "left" else largura_col - 0.01)
        ax.text(x, 1 - altura_linha / 2, nome, transform=ax.transAxes, fontsize=8,
               fontweight="bold", color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS,
               ha=ha, va="center")
    for r, linha in enumerate(linhas):
        y_topo = 1 - altura_linha * (r + 2)
        y_centro = y_topo + altura_linha / 2
        ax.plot([0, 1], [y_topo + altura_linha, y_topo + altura_linha],
               transform=ax.transAxes, color=t.COR_LINHA_GRADE, linewidth=0.6)
        for c, valor in enumerate(linha):
            ha = "left" if c < alinhar_direita_a_partir_de else "right"
            x = c * largura_col + (0.01 if ha == "left" else largura_col - 0.01)
            ax.text(x, y_centro, str(valor), transform=ax.transAxes, fontsize=8,
                   color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS, ha=ha, va="center")
