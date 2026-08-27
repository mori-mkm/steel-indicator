"""Blocos de desenho reutilizaveis entre as paginas do relatorio do IPIA.

Cada funcao recebe `fig` (ou um `Axes` ja criado) e coordenadas/dados ja
calculados - nenhuma funcao aqui calcula nada, so desenha (ver
docs/report_design_system.md para os tokens usados). pages.py decide o
grid de cada pagina e chama estes helpers.
"""
from __future__ import annotations

from typing import Optional, Sequence

import matplotlib.patches as mpatches
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.textpath import TextPath

from . import theme as t

# =============================================================================
# Medicao real de texto (glyph, nao chute de "caracteres por linha") -
# usada por todo componente que precisa quebrar texto para caber numa
# largura exata (caixas de destaque, callouts, rotulos de grafico). Nao
# precisa de canvas/renderer - TextPath calcula a partir da fonte direto.
# =============================================================================

def _largura_texto_pt(texto: str, fontsize: float, fontfamily: str = t.FONTE_SANS,
                      bold: bool = False) -> float:
    """Largura real (em pontos) que `texto` ocupa nessa fonte/tamanho."""
    if not texto:
        return 0.0
    fp = FontProperties(family=fontfamily, size=fontsize, weight="bold" if bold else "normal")
    return TextPath((0, 0), texto, size=fontsize, prop=fp).get_extents().width


def _altura_linha_pt(fontsize: float) -> float:
    """Altura de uma linha de texto (fontsize + entrelinha), em pontos."""
    return fontsize * 1.35


def _quebrar_texto_para_largura(texto: str, largura_max_pt: float, fontsize: float,
                                fontfamily: str = t.FONTE_SANS, bold: bool = False) -> list:
    """Quebra `texto` em linhas que cabem em `largura_max_pt`, medindo a
    largura REAL de cada linha candidata (TextPath) - nao um numero fixo
    de caracteres por linha (que nao tem nenhuma relacao com a largura
    real da caixa em polegadas/pontos no fontsize usado)."""
    palavras = texto.split()
    if not palavras:
        return [""]
    linhas, linha_atual = [], ""
    for palavra in palavras:
        candidata = f"{linha_atual} {palavra}".strip()
        if not linha_atual or _largura_texto_pt(candidata, fontsize, fontfamily, bold) <= largura_max_pt:
            linha_atual = candidata
        else:
            linhas.append(linha_atual)
            linha_atual = palavra
    linhas.append(linha_atual)
    return linhas


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
    """Cabecalho pequeno no topo das paginas internas (2, 3, 4)."""
    fig.text(t.MARGEM_POL / t.LARGURA_POL, 1 - 0.35 / t.ALTURA_POL, texto,
             transform=fig.transFigure, fontsize=8.5, color=t.COR_TEXTO_SECUNDARIO,
             fontfamily=t.FONTE_SANS, fontweight="bold", va="top")


def rodape_pagina(fig, fontes_texto: str, pagina_num: int, data_geracao) -> None:
    margem_x = t.MARGEM_POL / t.LARGURA_POL
    largura_util_pt = (1 - 2 * margem_x) * t.LARGURA_POL * 72
    linhas = _quebrar_texto_para_largura(fontes_texto, largura_util_pt, 6.8, t.FONTE_SANS)
    fig.text(margem_x, 0.11, "\n".join(linhas),
             transform=fig.transFigure, fontsize=6.8, color=t.COR_TEXTO_SECUNDARIO,
             fontfamily=t.FONTE_SANS, va="top")
    y_barra = 0.045
    fig.text(margem_x, y_barra, "Steel Indicator", transform=fig.transFigure,
             fontsize=8, color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS,
             fontweight="bold", va="center")
    fig.text(1 - margem_x, y_barra, f"{data_geracao:%d/%m/%Y}   {pagina_num}",
             transform=fig.transFigure, fontsize=8, color=t.COR_TEXTO_SECUNDARIO,
             fontfamily=t.FONTE_SANS, ha="right", va="center")


def selo_dado_texto(nivel: str, proxy: bool = False) -> str:
    """Texto curto do selo de proveniencia (ex. 'CALCULADO', 'ESTIMADO ·
    PROXY') a partir da classificacao feita pelo motor
    (`indices_setoriais.classificar_*`, ver docs/adr/0008). Vazio para
    OBSERVADO puro sem proxy - esse e o caso "normal", que nao precisa de
    aviso visual. Nunca omite PROXY nem um nivel != OBSERVADO."""
    partes = [] if nivel == "OBSERVADO" else [nivel]
    if proxy:
        partes.append("PROXY")
    return " · ".join(partes)


def kpi_tile(fig, x: float, y: float, largura: float, rotulo: str, valor_texto: str,
            cor_valor: str = t.COR_TEXTO_PRINCIPAL, nota: Optional[str] = None,
            periodo: Optional[str] = None, selo: Optional[str] = None) -> None:
    """Um KPI: rotulo pequeno em cima, valor grande embaixo, nota+periodo
    opcionais numa linha combinada (mes/janela real desse numero
    especifico - nunca "atual" sem qualificar) e selo opcional (texto de
    `selo_dado_texto`, ex. "CALCULADO · PROXY"). `periodo` NAO e anexado
    ao rotulo (rotulos longos como "PENETRAÇÃO (PLANOS)" + periodo
    estouravam a largura da coluna e coladvam no proximo KPI - por isso
    fica na linha de baixo, que tem mais espaco)."""
    fig.text(x, y, rotulo, transform=fig.transFigure, fontsize=8.5,
             color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
    fig.text(x, y - 0.022, valor_texto, transform=fig.transFigure, fontsize=17,
             color=cor_valor, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")
    y_linha = y - 0.045
    complemento = " · ".join(parte for parte in (nota, periodo) if parte)
    if complemento:
        fig.text(x, y_linha, complemento, transform=fig.transFigure, fontsize=7.5,
                 color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS, va="top")
        y_linha -= 0.015
    if selo:
        cor_selo = t.COR_APROXIMADO if "ESTIMADO" in selo else t.COR_ACCENT_1
        fig.text(x, y_linha, selo, transform=fig.transFigure, fontsize=7,
                 color=cor_selo, fontfamily=t.FONTE_SANS, fontweight="bold", va="top")


def caixa_destaque(fig, rect: tuple, cor_borda: str = t.COR_ACCENT_1):
    """Caixa de fundo COR_DESTAQUE_FUNDO, num rect JA CALCULADO (fracao de
    figura). Primitiva de baixo nivel usada por `caixa_texto` e
    `callout_numerado` - nao chame direto de pages.py, essas duas ja
    calculam a altura certa a partir do conteudo."""
    ax = fig.add_axes(rect)
    ax.axis("off")
    ax.add_patch(mpatches.FancyBboxPatch(
        (0, 0), 1, 1, transform=ax.transAxes, boxstyle="round,pad=0.02,rounding_size=0.02",
        facecolor=t.COR_DESTAQUE_FUNDO, edgecolor=cor_borda, linewidth=1))
    return ax


_PADDING_CAIXA_PT = 10.0


def caixa_texto(fig, x: float, y_topo: float, largura: float, texto: str,
                fontsize: float = 8.7, cor_borda: str = t.COR_ACCENT_1) -> float:
    """Caixa de destaque de paragrafo unico, com LARGURA de quebra de
    linha calculada a partir da largura real da caixa (nunca estoura a
    borda) e ALTURA calculada a partir do numero de linhas resultante
    (nunca sobra - nem falta - espaco por causa de uma altura fixa
    escolhida a dedo). Retorna a coordenada Y (fracao de figura) da borda
    inferior da caixa, para o chamador posicionar o proximo elemento logo
    abaixo sem adivinhar.
    """
    largura_pt = largura * t.LARGURA_POL * 72
    largura_util_pt = largura_pt - 2 * _PADDING_CAIXA_PT
    linhas = _quebrar_texto_para_largura(texto, largura_util_pt, fontsize, t.FONTE_SANS)
    altura_pt = len(linhas) * _altura_linha_pt(fontsize) + 2 * _PADDING_CAIXA_PT
    altura_frac = altura_pt / (t.ALTURA_POL * 72)
    y_base = y_topo - altura_frac

    ax = caixa_destaque(fig, (x, y_base, largura, altura_frac), cor_borda=cor_borda)
    inset_x = _PADDING_CAIXA_PT / largura_pt
    ax.text(inset_x, 0.5, "\n".join(linhas), transform=ax.transAxes, fontsize=fontsize,
           color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS, va="center", ha="left")
    return y_base


def texto_corrido(fig, x: float, y_topo: float, largura: float, texto: str,
                  fontsize: float = 9, cor: str = t.COR_TEXTO_PRINCIPAL, bold: bool = False) -> float:
    """Paragrafo solto (sem caixa), quebrado pela largura REAL disponivel -
    para qualquer linha de corpo que possa passar de uma linha (ex.:
    "spread entre X e Y" com numeros variaveis). Uma unica linha de
    fig.text() sem quebra sai da pagina quando o texto/numero e mais
    longo do que o esperado numa edicao futura. Retorna a coordenada Y da
    ultima linha desenhada."""
    largura_pt = largura * t.LARGURA_POL * 72
    linhas = _quebrar_texto_para_largura(texto, largura_pt, fontsize, t.FONTE_SANS, bold=bold)
    fig.text(x, y_topo, "\n".join(linhas), transform=fig.transFigure, fontsize=fontsize,
             color=cor, fontfamily=t.FONTE_SANS, fontweight="bold" if bold else "normal", va="top")
    return y_topo - len(linhas) * _altura_linha_pt(fontsize) / (t.ALTURA_POL * 72)


def callout_numerado(fig, x: float, y_topo: float, largura: float, itens: Sequence[tuple],
                     titulo_fontsize: float = 9.5, corpo_fontsize: float = 8.5) -> float:
    """Caixa de destaque com itens numerados (headline colorido + corpo).
    itens: lista de (headline, corpo). Mesma logica de `caixa_texto`: a
    largura de quebra vem da largura real da caixa, a altura total vem da
    soma exata das linhas de cada item (nao uma altura fixa dividida
    igualmente por item, que deixava vaos grandes quando os itens eram
    curtos). Retorna a coordenada Y da borda inferior da caixa.
    """
    largura_pt = largura * t.LARGURA_POL * 72
    largura_util_pt = largura_pt - 2 * _PADDING_CAIXA_PT
    espaco_entre_itens_pt = 10.0
    espaco_titulo_corpo_pt = 4.0

    itens_quebrados = []
    for i, (headline, corpo) in enumerate(itens, start=1):
        linhas_headline = _quebrar_texto_para_largura(
            f"{i}. {headline}", largura_util_pt, titulo_fontsize, t.FONTE_SANS, bold=True)
        linhas_corpo = _quebrar_texto_para_largura(corpo, largura_util_pt, corpo_fontsize, t.FONTE_SANS)
        itens_quebrados.append((linhas_headline, linhas_corpo))

    altura_pt = 2 * _PADDING_CAIXA_PT
    for linhas_headline, linhas_corpo in itens_quebrados:
        altura_pt += len(linhas_headline) * _altura_linha_pt(titulo_fontsize)
        altura_pt += espaco_titulo_corpo_pt
        altura_pt += len(linhas_corpo) * _altura_linha_pt(corpo_fontsize)
        altura_pt += espaco_entre_itens_pt
    altura_pt -= espaco_entre_itens_pt  # sem espaco extra depois do ultimo item

    altura_frac = altura_pt / (t.ALTURA_POL * 72)
    y_base = y_topo - altura_frac
    ax = caixa_destaque(fig, (x, y_base, largura, altura_frac), cor_borda=t.COR_ACCENT_1)

    inset_x = _PADDING_CAIXA_PT / largura_pt
    y_cursor_pt = altura_pt - _PADDING_CAIXA_PT
    for linhas_headline, linhas_corpo in itens_quebrados:
        for linha in linhas_headline:
            ax.text(inset_x, y_cursor_pt / altura_pt, linha, transform=ax.transAxes,
                   fontsize=titulo_fontsize, color=t.COR_ACCENT_2, fontfamily=t.FONTE_SANS,
                   fontweight="bold", va="top")
            y_cursor_pt -= _altura_linha_pt(titulo_fontsize)
        y_cursor_pt -= espaco_titulo_corpo_pt
        for linha in linhas_corpo:
            ax.text(inset_x, y_cursor_pt / altura_pt, linha, transform=ax.transAxes,
                   fontsize=corpo_fontsize, color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS,
                   va="top")
            y_cursor_pt -= _altura_linha_pt(corpo_fontsize)
        y_cursor_pt -= espaco_entre_itens_pt

    return y_base


# =============================================================================
# Cabecalho padrao de grafico: titulo + interpretacao + legenda no TOPO
# (nunca dentro da area de plotagem - regra nova, ver
# docs/report_design_system.md). Regra geral: todo grafico do relatorio
# usa isso, nunca mais `ax.set_title`/`ax.legend` direto dentro do grafico
# - centraliza a correcao aqui, uma vez, em vez de cada grafico novo
# repetir o mesmo erro de posicionamento.
# =============================================================================

def cabecalho_grafico(fig, x: float, y_topo: float, largura: float, titulo: str,
                      interpretacao: Optional[str] = None,
                      legenda: Optional[Sequence[tuple]] = None) -> float:
    """Desenha titulo (serif) + linha de interpretacao (sans, cinza,
    opcional) + legenda horizontal (opcional, ACIMA da area do grafico).
    Retorna a coordenada Y (fracao de figura) onde o eixo do grafico deve
    COMECAR (topo do axes) - nunca a legenda/titulo sobrepoe a area de
    plotagem, porque o axes so comeca depois desse cabecalho.

    legenda: lista de (cor, linestyle, marker, rotulo).
    """
    y = y_topo
    fig.text(x, y, titulo, transform=fig.transFigure, fontsize=11,
             fontfamily=t.FONTE_SERIF, fontweight="bold", color=t.COR_TEXTO_PRINCIPAL, va="top")
    y -= 15.5 / (t.ALTURA_POL * 72)

    if interpretacao:
        largura_pt = largura * t.LARGURA_POL * 72
        linhas = _quebrar_texto_para_largura(interpretacao, largura_pt, 8.0, t.FONTE_SANS)
        fig.text(x, y, "\n".join(linhas), transform=fig.transFigure, fontsize=8.0,
                 fontfamily=t.FONTE_SANS, color=t.COR_TEXTO_SECUNDARIO, va="top")
        y -= len(linhas) * _altura_linha_pt(8.0) / (t.ALTURA_POL * 72)

    if legenda:
        y -= 4 / (t.ALTURA_POL * 72)
        x_cursor = x
        largura_pol_swatch = 0.22  # polegadas
        for cor, linestyle, marker, rotulo in legenda:
            x0 = x_cursor
            x1 = x_cursor + largura_pol_swatch / t.LARGURA_POL
            y_linha = y - 3 / (t.ALTURA_POL * 72)
            fig.add_artist(Line2D([x0, x1], [y_linha, y_linha], color=cor, linestyle=linestyle,
                                  marker=marker, markersize=4, linewidth=1.4,
                                  transform=fig.transFigure))
            x_cursor = x1 + 6 / (t.LARGURA_POL * 72)
            fig.text(x_cursor, y, rotulo, transform=fig.transFigure, fontsize=7.5,
                     fontfamily=t.FONTE_SANS, color=t.COR_TEXTO_SECUNDARIO, va="top")
            largura_rotulo_pt = _largura_texto_pt(rotulo, 7.5, t.FONTE_SANS)
            x_cursor += largura_rotulo_pt / (t.LARGURA_POL * 72) + 18 / (t.LARGURA_POL * 72)
        y -= _altura_linha_pt(7.5) / (t.ALTURA_POL * 72)

    y -= 8 / (t.ALTURA_POL * 72)  # respiro antes do axes do grafico
    return y


def grafico_linha(ax, x, y, cor: str = t.COR_ACCENT_2,
                  ylabel: Optional[str] = None, linha_ref: Optional[float] = None,
                  linestyle: str = "-", marker: str = "o") -> None:
    """Estilo padrao de grafico de linha: sem moldura, so grade horizontal.
    Titulo/interpretacao/legenda NAO ficam aqui - ver `cabecalho_grafico`,
    chamado por pages.py antes de criar este axes."""
    ax.plot(x, y, color=cor, linestyle=linestyle, marker=marker, markersize=3.5, linewidth=1.6)
    if linha_ref is not None:
        ax.axhline(linha_ref, linestyle="--", color=t.COR_TEXTO_SECUNDARIO, linewidth=0.8)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(t.COR_LINHA_GRADE)
    ax.grid(axis="y", color=t.COR_LINHA_GRADE, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=7.5, colors=t.COR_TEXTO_SECUNDARIO, length=0)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8, color=t.COR_TEXTO_SECUNDARIO, fontfamily=t.FONTE_SANS)


def grafico_barras_empilhadas(ax, rotulo: str, componentes: Sequence[tuple]) -> None:
    """Barra empilhada horizontal (decomposicao de custo). componentes:
    lista de (nome, valor, cor). Titulo via `cabecalho_grafico`."""
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


def grafico_barras_horizontais(fig, x: float, y: float, largura: float, altura: float,
                               rotulos: Sequence[str], valores: Sequence[float],
                               cor: str = t.COR_ACCENT_2, formato_valor: str = "{:.1f}%",
                               fontsize_rotulo: float = 8.5):
    """Barras horizontais com margem esquerda calculada a partir do
    rotulo mais LARGO de verdade nesta chamada (medido via TextPath, nao
    um deslocamento fixo escolhido a dedo) - nunca corta rotulo na borda
    da pagina, seja qual for o pais/edicao de dados. Recebe `fig` +
    coordenadas (nao um `ax` pronto) porque precisa decidir sozinho onde
    o axes comeca. Retorna o Axes criado.
    """
    largura_pt = largura * t.LARGURA_POL * 72
    maior_rotulo_pt = max((_largura_texto_pt(r, fontsize_rotulo, t.FONTE_SANS) for r in rotulos),
                          default=0.0)
    inset_frac = min((maior_rotulo_pt + 14) / largura_pt, 0.45) if largura_pt > 0 else 0.0
    ax = fig.add_axes((x + inset_frac * largura, y, largura * (1 - inset_frac), altura))

    y_pos = range(len(rotulos))
    ax.barh(list(y_pos), valores, color=cor)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(rotulos, fontsize=fontsize_rotulo, fontfamily=t.FONTE_SANS,
                       color=t.COR_TEXTO_PRINCIPAL)
    ax.invert_yaxis()
    for i, v in enumerate(valores):
        ax.text(v, i, f" {formato_valor.format(v)}", va="center", fontsize=8,
               color=t.COR_TEXTO_PRINCIPAL, fontfamily=t.FONTE_SANS)
    for spine in ("top", "right", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.set_xticks([])
    return ax


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
