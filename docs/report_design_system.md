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
| `COR_II` | `#6B4226` | componente "Imposto de Importação" no gráfico de composição do PPI_COST |
| `COR_AFRMM` | `#8C6E4A` | componente "AFRMM" no gráfico de composição do PPI_COST |
| `COR_DESPESAS_PORTO` | `#7F8C8D` | componente "Despesas de porto" no gráfico de composição do PPI_COST |
| `COR_FRETE_INTERNO` | `#95A5A6` | componente "Frete interno" no gráfico de composição do PPI_COST — avaliado contra `COR_APROXIMADO` (distância RGB ~12, a mais próxima de toda a paleta) e mantido deliberadamente: nunca aparecem lado a lado, eixos semânticos diferentes (categoria de gráfico vs. selo de proveniência) |

Os quatro acima existiam como hex literal direto em `pages.py`/`pages_v3.py`
até ago/2026 (Fase 2 da migração de design system) — só ganharam nome,
nenhum valor mudou.

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

### Tamanhos de fonte

Fase 1 da migração de design system (ago/2026): os 24 tamanhos abaixo
existiam como número literal direto em `pages.py`/`pages_v3.py`/
`components.py` até esta etapa — nenhum valor mudou, só ganharam nome em
`theme.py`. Não é uma escala tipográfica desenhada com um "step"
consistente: é o resultado de ajuste fino independente por componente ao
longo de várias tarefas anteriores — por isso os valores são quase
contínuos (6.6 a 56) em vez de uma progressão limpa.

| Token | Valor | Uso principal |
|---|---:|---|
| `TAM_HERO_NUMERO` | 56 | número IPIA-HRC gigante, capa V3 |
| `TAM_TITULO_CAPA` | 34 | título "IPIA"/"IPIA-HRC", capa V1/V2 |
| `TAM_HERO_SECUNDARIO` | 26 | número PPI_COST, página 2 V3 |
| `TAM_TITULO_CAPA_V3` | 22 | título "IPIA-HRC", capa V3 |
| `TAM_TITULO_PAGINA` | 19 | título de página interna (2-4), todas as versões |
| `TAM_VALOR_KPI` | 17 | valor grande de `kpi_tile` |
| `TAM_VALOR_SECUNDARIO` | 13 | valor PPI_OFFER (secundário/aproximado) |
| `TAM_TITULO_SECAO` | 12 | default de `secao_titulo`; subtítulo serif da capa V1/V2 |
| `TAM_TITULO_GRAFICO` | 11 | título de `cabecalho_grafico` |
| `TAM_DECK_CAPA` | 10.5 | linha "deck"/interpretação em destaque da capa |
| `TAM_KICKER` | 10 | kicker da `banda_topo`; mensagens "sem dado" |
| `TAM_SUBTITULO_PAGINA` | 9.5 | subtítulo abaixo do título de página |
| `TAM_CORPO_PADRAO` | 9 | default de `texto_corrido` |
| `TAM_CORPO_DISCLOSURE` | 8.7 | default de `caixa_texto`; parágrafos de metodologia |
| `TAM_CORPO_SECUNDARIO` | 8.5 | cabeçalho de página interna; rótulos/valores de KPI e tabelas |
| `TAM_NOTA_METODOLOGICA` | 8.2 | notas de disclosure/watchlist, página 3-4 V3 |
| `TAM_CORPO_PEQUENO` | 8 | o mais reutilizado — ylabel de eixo, rodapé, tabelas, waterfall |
| `TAM_CORPO_COMPACTO` | 7.6 | Principais Premissas / Narrativa do Mês, página 2 V3 |
| `TAM_ROTULO_AUXILIAR` | 7.5 | nota/período de KPI; legenda de gráfico; labelsize de eixo |
| `TAM_CORPO_MINIMO` | 7.4 | parágrafo "Como ler este relatório", capa V3 |
| `TAM_NOTA_FONTE_SECUNDARIA` | 7.2 | "Related Research"; disclaimer da capa V3 |
| `TAM_SELO` | 7 | selo de proveniência; marcador de composição atípica (ADR 0018) |
| `TAM_FONTE_CITACAO` | 6.8 | citação de fontes no rodapé — a menor fonte "de verdade" |
| `TAM_CITACAO_REVISOR` | 6.6 | linha "Revisado por..." da narrativa mensal (ADR 0017) |

**Divergência registrada, não adotada:** uma proposta externa (ago/2026)
sugeriu uma escala menor e diferente (`cover_title=36`, `page_title=16`,
`section_title=12`, `body=9`...) usando fontes `Inter`/`Source Serif 4`.
Decisão do usuário: manter os valores reais acima integralmente — a
proposta não foi adotada nem parcialmente. `Inter`/`Source Serif 4`
também não estão instaladas neste ambiente (confirmado via
`matplotlib.font_manager`) — ver seção de tipografia acima para o
mecanismo de fallback que já protege contra esse risco.

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

## Princípios visuais gerais

Regras já em vigor por decisão explícita do usuário em tarefas
anteriores, nunca escritas aqui até agora — existiam só como instrução
pontual, não como referência consultável antes de mexer no relatório.

- **O relatório deve parecer research institucional, não um dashboard
  exportado para PDF.** Nunca usar ícone/emoji como marcador visual,
  mesmo para chamar atenção a uma ressalva — usar marcador tipográfico
  em texto (ex.: asterisco + nota de rodapé, no mesmo espírito de como a
  S&P marca "f" de forecast nos gráficos deles). Precedente real: o
  marcador de composição atípica na tabela de drivers (ADR 0018) usa
  `"Preço FOB*"` + rodapé, nunca um símbolo de alerta.
- Espaço em branco generoso, hierarquia editorial forte (serif para
  título, sans para corpo/dado) — já seguido desde a origem do design
  system (seção acima), só não estava nomeado como princípio explícito.
- Gráficos sempre em fundo branco, sem moldura, título/interpretação/
  legenda sempre FORA da área de plotagem (já documentado em "Cabeçalho
  de gráfico" acima).

## Sistema de coordenadas (para qualquer proposta futura de tokens)

O relatório é desenhado com **matplotlib** (`PdfPages`), em **coordenadas
fracionárias de figura (0.0–1.0)** via `transform=fig.transFigure` — não
em pontos/polegadas absolutos. `theme.LARGURA_POL`/`ALTURA_POL` (A4, em
polegadas) só entram como fator de conversão pontual quando uma função
precisa medir texto em pontos reais (`components._largura_texto_pt` via
`TextPath`, para quebra de linha e altura de caixa). Qualquer proposta de
tokens de geometria (margem, largura de coluna, posição de gráfico) só é
diretamente aplicável a este código se expressa nesse mesmo sistema —
uma proposta em pontos absolutos sobre página Letter (612×792pt) não é
uma troca de valor, é uma troca de paradigma de renderização inteira
(reescreveria a lógica de posicionamento de `pages.py`/`pages_v3.py`/
`components.py` por completo, não só os tokens).

## Caixas de destaque: aparência real (não aspiracional)

`components.caixa_destaque` (usada por `caixa_texto`/`callout_numerado`)
desenha **cantos arredondados** (`boxstyle="round,pad=0.02,
rounding_size=0.02"`) **com borda** (`edgecolor`, `linewidth=1`) — esta é
a aparência real já publicada, não um estado transitório a corrigir. Uma
proposta externa (ago/2026) sugeriu o oposto (cantos retos, sem borda,
"não transformar callouts em cards modernos") — registrado aqui como
**divergência em aberto, não adotada**: mudar a forma do callout é
decisão de identidade visual (mesma categoria de "trocar paleta de
cor"), não algo a decidir silenciosamente numa atualização de doc.

## Item em aberto: largura da coluna de narrativa

A seção "Narrativa do mês" (página 2, ADR 0017/0018) usa hoje a largura
útil TOTAL da página (`1 - 2×MARGEM`), igual a qualquer parágrafo de
corpo do relatório — não uma coluna estreita dedicada. Uma proposta
externa (ago/2026) sugere que texto de narrativa NUNCA deveria esticar
para preencher a largura da página, com uma coluna deliberadamente mais
estreita. **Não implementado ainda** — estreitar a coluna muda um valor
numérico de layout (largura), então fica fora do escopo desta atualização
de doc (Fase 0 da migração de design system, ago/2026) e só deveria
acontecer numa etapa futura de spacing, com aprovação explícita, dado que
a página 2 já tem orçamento vertical apertado (ver "DRIVER TABLE" acima)
e estreitar a coluna sem redistribuir a largura sobrando exige decidir
para onde esse espaço vai.
