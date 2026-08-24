# Design system do relatório PDF do IPIA

Tokens de design usados por `src/reporting/theme.py` para o relatório de
4 páginas gerado por `--pdf-ipia`. Derivado de análise visual de 3
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
  cinza pequeno abaixo. **Nota (ago/2026)**: "legenda ao lado" é o que as
  referências mostravam estruturalmente — o IPIA adotou uma variação
  própria (legenda numa linha horizontal ACIMA da área de plotagem, nunca
  ao lado nem sobreposta aos dados), ver "Cabeçalho de gráfico" abaixo.
  Isso não é uma correção de uma regra pré-existente violada — é uma
  convenção nova, adotada depois que uma legenda posicionada dentro do
  eixo (`loc="upper left"`) colidiu com a própria linha plotada num
  gráfico real do relatório.
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
- Margem única: `0.65 in` em todos os lados, nas 4 páginas.
- Banda de topo (`COR_BANDA_TOPO`): só na página 1 (capa).
- Cabeçalho pequeno (nome do relatório, `COR_TEXTO_SECUNDARIO`): páginas
  2, 3 e 4 (internas).
- Rodapé (marca à esquerda, data + nº de página à direita,
  `COR_TEXTO_SECUNDARIO`): as 4 páginas.
- 4 páginas: capa, decomposição de custo, séries temporais, indicadores e
  origem — ver "Por que a página de dashboard virou duas" abaixo.

## Caixas de texto: altura e quebra de linha derivadas do conteúdo

`components.caixa_texto` / `callout_numerado` (usados pela caixa "o que o
IPIA mede", pelos callouts numerados de "O QUE MUDOU" e pelas caixas de
ressalva) **nunca** recebem uma altura fixa escolhida a dedo, nem quebram
linha por contagem de caracteres. A largura de quebra é derivada da
largura real da caixa (em pontos, na fonte/tamanho usados — medida via
`matplotlib.textpath.TextPath`, sem precisar de canvas/renderer) e a
altura da caixa é derivada do número de linhas resultante. Isso evita as
duas falhas visuais que motivaram a correção: texto estourando a borda
(largura de quebra desalinhada da largura real da caixa) e caixa maior
que o necessário (altura fixa que sobrava espaço vazio quando o texto era
curto). Toda função que desenha essas caixas retorna a coordenada Y da
borda inferior real, para o chamador encadear o próximo elemento sem
adivinhar — uma posição Y fixa abaixo de uma caixa de altura dinâmica é
o jeito mais fácil de reintroduzir sobreposição.

## Cabeçalho de gráfico: título + interpretação + legenda

Todo gráfico do relatório usa `components.cabecalho_grafico` para
desenhar, nesta ordem, ACIMA da área de plotagem (nunca dentro do
`Axes`, nunca sobrepondo dado): (1) título em serif; (2) uma linha curta
de interpretação em sans cinza, sempre derivada de valor real já
calculado (mínimo/máximo, direção, líder) — nunca uma frase decorativa
sem número; (3) legenda horizontal, quando o gráfico tem mais de uma
série, com swatches de linha/marcador + rótulo, também acima da área de
plotagem. A função devolve a coordenada Y onde o `Axes` do gráfico deve
começar, então o eixo em si nunca tem `set_title`/`legend` próprios — só
os componentes `grafico_linha`/`grafico_barras_*` cuidam da série de
dados. Todo gráfico do relatório também precisa de pelo menos uma menção
no texto corrido da página (fora do próprio cabeçalho do gráfico) que
referencie o que ele mostra — nunca um gráfico puramente decorativo sem
nenhuma frase apontando para ele.

## Por que a página de dashboard virou duas

A antiga página única "Dashboard — Série Histórica e Indicadores"
(4 KPIs + 3 gráficos de linha + gráfico de barras horizontais + rodapé,
tudo num A4) ficou densa demais depois que título+interpretação de cada
gráfico passaram a ocupar espaço próprio fora do eixo (ver seção
anterior) — não cabia mais sem espremer. Dividida em:

- **Página 3 — Séries Temporais**: KPIs (ponto atual de cada métrica) +
  os 3 gráficos de evolução mensal (IPIA, penetração de importação,
  câmbio). Pergunta que essa página responde: "como cada série andou no
  tempo".
- **Página 4 — Indicadores e Origem das Importações**: gráfico de origem
  geográfica (agora com espaço de sobra, em vez de espremido no rodapé da
  página única) + tabela de recapitulação dos últimos 6 meses (mesmos
  dados já usados nas páginas anteriores, sem recálculo). Pergunta que
  essa página responde: "de onde vem a importação e onde estamos agora".

A mesma justificativa está no docstring de `pages.pagina_series_temporais`.

## Regra de uso do selo oficial/aproximado

Qualquer número derivado de fonte híbrida (hoje: taxa de penetração de
importação, ver `docs/adr/0007`) precisa aparecer no PDF com selo visual
explícito — `COR_ACCENT_2` sólido para `tipo_dado_penetracao=
"oficial_mensal"`, `COR_APROXIMADO` tracejado/mais claro para
`"aproximado_consumo_aparente"` — e uma legenda textual que nomeie os
dois, nunca só a cor. Mesmo princípio de "nunca escondido" já usado no
resto do projeto (ver `CLAUDE.md`), aplicado ao design visual.

## Selo de proveniência (OBSERVADO/CALCULADO/ESTIMADO + PROXY) e período por KPI

Ver [ADR 0008](adr/0008-taxonomia-observado-calculado-estimado-proxy-e-vintage.md)
para a investigação e o racional completo da taxonomia. Regras de
aplicação visual:

- Todo `kpi_tile` que representa um número não-`OBSERVADO`-puro (ou
  seja, `nivel != OBSERVADO` e/ou `proxy=True`) carrega um selo curto
  (`components.selo_dado_texto`, ex. `"CALCULADO · PROXY"`) — cor
  `COR_ACCENT_1` (ember) por padrão, `COR_APROXIMADO` quando o nível é
  `ESTIMADO`. Um KPI `OBSERVADO` puro (ex. câmbio PTAX) não carrega
  selo — esse é o caso "normal", que não precisa de aviso.
- Todo `kpi_tile` carrega seu próprio `periodo` (mês/janela real daquele
  número específico) — nunca "atual" sem qualificar, mesmo quando dois
  tiles da mesma linha mostram períodos diferentes (ex.: página 3,
  câmbio costuma ficar um mês à frente de IPIA/spread/penetração — ver
  ADR 0008). `periodo` fica na linha de baixo, junto de `nota` (nunca
  anexado ao rótulo do KPI — rótulos longos como "PENETRAÇÃO (PLANOS)"
  com período anexado estouravam a largura da coluna e colavam no
  próximo KPI; bug real corrigido nesta versão).
- Limitações materiais (proxy de segmento, fórmula alternativa de fonte
  híbrida) precisam aparecer em texto corrido em pelo menos uma página
  fora de qualquer caixa de ressalvas isolada — hoje: uma frase solta na
  capa (fora de qualquer caixa) e uma nota completa na página 4, além da
  caixa de ressalvas já existente na página 2. O texto completo do
  `metodo_motivo` de `formula_alternativa` fica só na página 4 (que tem
  espaço de sobra) — colocá-lo na interpretação do gráfico de página 3
  empurrava o resto da página contra o rodapé (testado e revertido).
