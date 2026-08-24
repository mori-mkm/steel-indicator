# Design system do relatório PDF do IPIA

Tokens de design usados por `src/reporting/theme.py` para o relatório de
3 páginas gerado por `--pdf-ipia`. Derivado de análise visual de 3
relatórios reais da S&P Global Ratings (`references/report_design/` —
fora do Git, referência estrutural/visual apenas: nenhum logo, texto,
foto ou cor de marca da S&P foi reaproveitado; a identidade abaixo
(cores, tipografia específica) é própria do IPIA).

## O que foi observado nas referências (padrões estruturais, não conteúdo)

- Duas famílias tipográficas: título editorial em **serifada** (capa,
  títulos de página, títulos de gráfico/tabela); corpo, eixos, dados e
  legendas em **sem-serifa**.
- Banda de topo escura na capa, com um "kicker" pequeno em branco acima
  do título grande.
- Uma cor de destaque única para títulos de seção (bold, sem-serifa).
- Caixa de destaque numerada com fundo em tom pastel — a mesma cor de
  fundo reaparece como cabeçalho de tabela (um único token "fundo de
  destaque", reusado em mais de um componente).
- Gráficos sem moldura, só grade horizontal cinza clara; paleta
  categórica pequena (poucas cores saturadas); legenda simples ao lado;
  título do gráfico em serif, subtítulo em sans cinza; nota/fonte em
  cinza pequeno abaixo.
- Rodapé consistente em todas as páginas (marca/URL à esquerda, data +
  nº de página à direita); cabeçalho pequeno com o nome do relatório no
  topo das páginas internas.

## Paleta (identidade própria do IPIA)

| Token | HEX | Uso |
|---|---|---|
| `COR_FUNDO` | `#FFFFFF` | fundo da página |
| `COR_BANDA_TOPO` | `#101820` | banda de topo da capa |
| `COR_TEXTO_PRINCIPAL` | `#1A1A1A` | corpo, números, KPIs |
| `COR_TEXTO_SECUNDARIO` | `#6B6B6B` | legendas, notas de rodapé, datas |
| `COR_ACCENT_1` (ember) | `#B5541C` | títulos de seção |
| `COR_ACCENT_2` (índigo) | `#2B4570` | callouts numerados, KPI principal, dado **oficial** |
| `COR_APROXIMADO` | `#9AA5B1` | dado **aproximado** — visualmente menos afirmativo que o oficial, nunca escondido, sempre rotulado |
| `COR_DESTAQUE_FUNDO` | `#F4ECE1` | fundo de caixas de destaque e cabeçalho de tabela |
| `COR_LINHA_GRADE` | `#DCDCDC` | grade horizontal dos gráficos |
| `COR_POSITIVO` | `#3B7A57` | delta/variação positiva |
| `COR_NEGATIVO` | `#A93226` | delta/variação negativa |

Paleta categórica de gráfico (séries múltiplas: câmbio, penetração,
origem por país): `#B5541C` (ember), `#2B4570` (índigo), `#3B7A57`
(verde-azulado) — três matizes distintos, saturação moderada, na mesma
família de "relatório editorial financeiro" das referências, mas sem
reusar os matizes específicos da S&P (petróleo/âmbar/magenta).

## Tipografia

| Token | Fonte | Uso |
|---|---|---|
| `FONTE_SERIF` | `Georgia` | título da capa, título de página, título de gráfico/tabela |
| `FONTE_SANS` | `Arial` | corpo, eixos, KPIs, tabelas, legendas |

Ambas confirmadas instaladas neste sistema via
`matplotlib.font_manager.fontManager.ttflist` antes de serem escolhidas
— não há arquivo de fonte bundlado no projeto. **Dependência de fonte do
host**: se um ambiente futuro não tiver `Georgia`/`Arial` instaladas, o
matplotlib cai para `DejaVu Sans` automaticamente para o que faltar —
degrada silenciosamente (relatório continua sendo gerado, só perde a
diferenciação serif/sans), nunca quebra a geração do PDF.

## Grid e página

- Tamanho de página: A4 retrato, `8.27 × 11.69 in` (mesmo formato já
  usado no relatório de 1 página anterior).
- Margem única: `0.65 in` em todos os lados, nas 3 páginas.
- Banda de topo (`COR_BANDA_TOPO`): só na página 1 (capa).
- Cabeçalho pequeno (nome do relatório, `COR_TEXTO_SECUNDARIO`): páginas
  2 e 3 (internas).
- Rodapé (marca à esquerda, data + nº de página à direita,
  `COR_TEXTO_SECUNDARIO`): as 3 páginas.

## Regra de uso do selo oficial/aproximado

Qualquer número derivado de fonte híbrida (hoje: taxa de penetração de
importação, ver `docs/adr/0007`) precisa aparecer no PDF com selo visual
explícito — `COR_ACCENT_2` sólido para `tipo_dado_penetracao=
"oficial_mensal"`, `COR_APROXIMADO` tracejado/mais claro para
`"aproximado_consumo_aparente"` — e uma legenda textual que nomeie os
dois, nunca só a cor. Mesmo princípio de "nunca escondido" já usado no
resto do projeto (ver `CLAUDE.md`), aplicado ao design visual.
