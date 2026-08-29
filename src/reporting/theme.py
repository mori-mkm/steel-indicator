"""Tokens de design do relatorio PDF do IPIA.

Derivado de analise visual de relatorios reais da S&P Global
(references/report_design/, fora do Git - so referencia estrutural, sem
reaproveitar cor/fonte/conteudo de marca). Detalhes e racional completo em
docs/report_design_system.md - este modulo e so a materializacao em codigo
dos tokens documentados la.
"""
from __future__ import annotations

# --- Paleta ------------------------------------------------------------
COR_FUNDO             = "#FFFFFF"
COR_BANDA_TOPO         = "#101820"
COR_TEXTO_PRINCIPAL    = "#1A1A1A"
COR_TEXTO_SECUNDARIO   = "#6B6B6B"
COR_ACCENT_1           = "#B5541C"  # ember - titulos de secao
COR_ACCENT_2           = "#2B4570"  # indigo - callouts, KPI principal, dado OFICIAL
COR_APROXIMADO         = "#9AA5B1"  # dado APROXIMADO - nunca escondido, sempre rotulado
COR_DESTAQUE_FUNDO     = "#F4ECE1"  # fundo de caixa de destaque / cabecalho de tabela
COR_LINHA_GRADE        = "#DCDCDC"
COR_POSITIVO           = "#3B7A57"
COR_NEGATIVO           = "#A93226"

PALETA_CATEGORICA = ["#B5541C", "#2B4570", "#3B7A57"]  # ember, indigo, verde-azulado

# --- Tipografia ----------------------------------------------------------
# Resolvida UMA VEZ, na importacao, para um nome CONCRETO ja confirmado
# instalado (nunca uma lista de "chutes") - Reporting V3 Sec.39: passar uma
# lista de candidatos direto para `fontfamily=[...]` (testado) faz o
# matplotlib emitir um "findfont: Font family not found" por CANDIDATO
# AUSENTE na cadeia antes de resolver o ultimo (medido empiricamente nesta
# stage) - trocar "Arial" isolado por uma lista pioraria o ruido de log em
# vez de eliminar. Verificando com `matplotlib.font_manager.fontManager`
# quais nomes desta preferencia estao de fato instalados e usando so o
# primeiro que existe elimina o warning por completo, em qualquer SO:
# Windows/macOS tipicamente tem Arial/Georgia; Linux com fontconfig+
# liberation-fonts tem Liberation Sans/Serif (metricamente compativeis com
# Arial/Times); DejaVu Sans/Serif vem EMPACOTADO com o proprio matplotlib
# (sempre presente em `fontManager.ttflist`, garante que o ultimo candidato
# da cadeia sempre resolve, em qualquer ambiente, mesmo minimo).
def _resolver_fonte_instalada(preferencia: list) -> str:
    import matplotlib.font_manager as _fm
    instaladas = {f.name for f in _fm.fontManager.ttflist}
    for nome in preferencia:
        if nome in instaladas:
            return nome
    return preferencia[-1]  # nunca deveria cair aqui - o ultimo candidato e sempre bundled


FONTE_SERIF = _resolver_fonte_instalada(["Georgia", "Liberation Serif", "DejaVu Serif"])
FONTE_SANS  = _resolver_fonte_instalada(["Arial", "Liberation Sans", "DejaVu Sans"])

# --- Grid / pagina ---------------------------------------------------------
LARGURA_POL = 8.27   # A4 retrato
ALTURA_POL  = 11.69
MARGEM_POL  = 0.65

NOME_RELATORIO = "IPIA — Relatório Mensal"
