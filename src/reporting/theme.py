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

# Componentes do grafico "Composicao do PPI_COST" (pages.py/pages_v3.py) -
# ate ago/2026 viviam como hex literal direto nas duas paginas (duplicado,
# sem nome). Fase 2 da migracao de design system: so nomeia os valores JA
# usados, nenhum valor mudou, exceto COR_FRETE_INTERNO (ver abaixo).
# COR_FRETE_INTERNO original (#95A5A6) colidia com COR_APROXIMADO
# (distancia RGB ~12, o par mais proximo de toda a paleta) - risco real de
# impressao (tons quase identicos no papel) e colisao semantica, ja que
# COR_APROXIMADO marca dado estimado em outro componente do relatorio.
# Trocado por um tom areia/argila, mesma familia terrosa de COR_II/
# COR_AFRMM, com distancia RGB minima de ~64 a qualquer cor ja nomeada na
# paleta (a mais proxima passa a ser COR_DESPESAS_PORTO).
COR_II              = "#6B4226"  # Imposto de Importacao, componente do PPI_COST
COR_AFRMM           = "#8C6E4A"
COR_DESPESAS_PORTO  = "#7F8C8D"
COR_FRETE_INTERNO   = "#B39A6B"

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

# --- Tamanhos de fonte (Fase 1 da migracao de design system, ago/2026) -----
# Nomeia os valores REAIS ja usados em pages.py/pages_v3.py/components.py -
# nenhum numero mudou (verificado por render antes/depois). Nao e uma escala
# tipografica desenhada do zero: os 24 valores abaixo sao o resultado de
# ajuste fino independente por componente ao longo de varias tarefas, entao
# nao ha um "step" limpo entre eles - so ganharam nome. Uma proposta externa
# (ago/2026) sugeriu uma escala menor e diferente (cover_title=36,
# page_title=16, etc.) - NAO ADOTADA, ver docs/report_design_system.md
# ("Item em aberto" / secao de tipografia) para o registro completo.
TAM_HERO_NUMERO            = 56    # numero IPIA-HRC gigante, capa V3 (pagina_market_view)
TAM_TITULO_CAPA            = 34    # titulo "IPIA"/"IPIA-HRC", capa V1/V2 (pagina_capa*)
TAM_HERO_SECUNDARIO        = 26    # numero PPI_COST, pagina 2 V3; default nao-usado de titulo_serif
TAM_TITULO_CAPA_V3         = 22    # titulo "IPIA-HRC", capa V3 (pagina_market_view)
TAM_TITULO_PAGINA          = 19    # titulo de pagina interna (2-4), todas as versoes
TAM_VALOR_KPI              = 17    # valor grande de kpi_tile
TAM_VALOR_SECUNDARIO       = 13    # valor PPI_OFFER (aproximado/secundario), pagina 2 V3
TAM_TITULO_SECAO           = 12    # default de secao_titulo; subtitulo serif da capa V1/V2
TAM_TITULO_GRAFICO         = 11    # titulo de cabecalho_grafico; sinal de paridade em destaque (capa V3)
TAM_DECK_CAPA              = 10.5  # linha "deck" da capa V1/V2; interpretacao em destaque da capa V3
TAM_KICKER                 = 10    # kicker da banda_topo; mensagens "sem dado publicado"
TAM_SUBTITULO_PAGINA       = 9.5   # subtitulo abaixo do titulo de pagina; default titulo de callout_numerado
TAM_CORPO_PADRAO           = 9     # default de texto_corrido; corpo geral
TAM_CORPO_DISCLOSURE       = 8.7   # default de caixa_texto; paragrafos de disclosure (pagina metodologia)
TAM_CORPO_SECUNDARIO       = 8.5   # cabecalho_pagina_interna; rotulos/valores de kpi e tabelas; default de
                                    # corpo de callout_numerado e rotulo de grafico_barras_horizontais
TAM_NOTA_METODOLOGICA      = 8.2   # notas de disclosure/watchlist, pagina 3-4 V3
TAM_CORPO_PEQUENO          = 8     # o mais reutilizado: ylabel de eixo, rodape, tabela_simples, valores
                                    # de waterfall/barras, disclosures V1/V2
TAM_CORPO_COMPACTO         = 7.6   # paragrafos compactos (Principais Premissas, Narrativa do Mes), pagina 2 V3
TAM_ROTULO_AUXILIAR        = 7.5   # nota/periodo de kpi_tile; legenda de grafico; labelsize de eixo
TAM_CORPO_MINIMO           = 7.4   # paragrafo "Como ler este relatorio", capa V3
TAM_NOTA_FONTE_SECUNDARIA  = 7.2   # "Related Research"; disclaimer de rodape da capa V3
TAM_SELO                   = 7     # selo de proveniencia (kpi_tile); marcador de composicao atipica (ADR 0018)
TAM_FONTE_CITACAO          = 6.8   # citacao de fontes no rodape_pagina (a menor fonte "de verdade")
TAM_CITACAO_REVISOR        = 6.6   # linha "Revisado por..." da narrativa mensal (ADR 0017)

# --- Grid / pagina ---------------------------------------------------------
LARGURA_POL = 8.27   # A4 retrato
ALTURA_POL  = 11.69
MARGEM_POL  = 0.65

NOME_RELATORIO = "IPIA — Relatório Mensal"
