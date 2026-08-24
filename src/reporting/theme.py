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
# Confirmadas instaladas neste sistema via matplotlib.font_manager antes de
# escolhidas (ver docs/report_design_system.md). Se um ambiente futuro nao
# tiver essas fontes, o matplotlib cai para DejaVu Sans automaticamente -
# degrada, nunca quebra a geracao do PDF.
FONTE_SERIF = "Georgia"
FONTE_SANS  = "Arial"

# --- Grid / pagina ---------------------------------------------------------
LARGURA_POL = 8.27   # A4 retrato
ALTURA_POL  = 11.69
MARGEM_POL  = 0.65

NOME_RELATORIO = "IPIA — Relatório Mensal"
