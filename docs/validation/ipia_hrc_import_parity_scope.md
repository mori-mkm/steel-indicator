# IPIA-HRC — Import Parity Scope: Cost vs Offer/Trader Price

**Status: METHODOLOGICAL DECISION ANALYSIS ONLY — não implementa nenhuma
mudança.** `ParamsIPIA`, PPI oficial, IPIA, vintages, `VERSAO_METODOLOGIA`
e reporting permanecem exatamente como estavam antes desta etapa. Uma
única simulação contrafactual (margem 0% vs 3%) foi executada reusando
`agregar_ipia_hrc_multi_ncm_mensal` (produção) — nenhum valor oficial
mudou.

Reproduzir o contrafactual: `python scripts/contrafactual_margem_zero_vs_atual.py`
(faz chamadas de rede reais a Comex Stat/BCB — não escreve em
`data/processed/` fora do próprio output de terminal).

## Question

> O IPIA-HRC principal deve medir **A — Import Parity Cost** (o custo
> econômico de importar e internalizar), **B — Import Parity
> Offer/Trader Price** (o preço pelo qual um trading venderia o material
> a um comprador doméstico), ou **C — ambos**, com um core de custo e uma
> camada analítica separada de oferta?

## 1. Original objective

A pesquisa metodológica original (`references/manual_metodologico_indices_setoriais.md`
§5) desenhou o IPIA para resolver um problema específico: **paridade de
importação sem licenciar cotação de agência de preços** (Platts/Argus/
Fastmarkets, §5.1). A solução foi usar o valor unitário do Comex Stat —
"o preço efetivamente realizado na fronteira brasileira" — em vez de uma
cotação FOB teórica de origem.

A leitura de negócio que a própria pesquisa atribui ao índice (§5.2) é:

> "Acima de 100 → o preço doméstico está acima da paridade: importar
> compensa, e o produtor local está sob pressão. [...] É a conta que a
> área comercial de toda siderúrgica e de todo distribuidor de aço
> refaz o tempo todo."

Isso enquadra o índice do lado da **pressão competitiva sobre o produtor
doméstico** — "será que importar compensa, dado meu preço doméstico
atual?" — não do lado "quanto eu pagaria a um trading para receber o
material". As três perspectivas do sprint, aplicadas à evidência:

| Perspectiva | Pergunta | O IPIA foi desenhado para isso? |
|---|---|---|
| **Produtor doméstico** | "Qual é a pressão competitiva de um produto importado?" | **Sim — é a leitura explícita da pesquisa original** (§5.2, citação acima). |
| **Comprador industrial** | "Quanto eu pagaria para obter HRC importado?" | Parcial — a fórmula original já inclui margem de trading (§5.2), então tecnicamente aproxima um preço de oferta, mas a leitura de negócio documentada é sobre pressão competitiva, não sobre uma decisão de compra individual. |
| **Trader** | "Por quanto preciso vender para obter margem?" | Não — nenhuma fonte (pesquisa original, METODOLOGIA.md, ADRs) discute o índice como ferramenta de precificação de trading. A margem foi incluída, mas nunca calibrada nem justificada como um markup real de mercado (`docs/validation/ipia_hrc_cost_parameter_calibration.md` §6). |

**Achado decisivo**: a própria pesquisa original **já continha a
pergunta A vs. B** e a deixou explicitamente em aberto para quem
implementasse (§5.5, tabela de parâmetros de internação):

> "Margem do importador | 3% | **Zere se quiser medir custo puro em vez
> de preço ofertado**"

Ou seja: isto não é uma pergunta nova criada por este sprint — é uma
decisão de escopo que a pesquisa original identificou e nunca foi
formalmente resolvida. `docs/METODOLOGIA.md` §9.8 cita a mesma frase e
confirma: "decisão de manter em 3% nunca formalizada além do valor
default do código."

## 2. Economic perspectives — conclusão

Nenhuma das três perspectivas é a mesma variável econômica. A pesquisa
original combina majoritariamente a perspectiva do **produtor
doméstico/pressão competitiva** com uma fórmula que, por incluir margem,
também se aproxima parcialmente da perspectiva do **comprador
industrial**. A perspectiva do **trader** nunca foi o objetivo — a
margem foi incluída por plausibilidade de fórmula ("um trading real cobra
markup sobre o que desembolsa"), não por uma decisão deliberada de medir
pricing de trading.

## 3. Cost parity definition — `PPI_COST`

**Definição formal proposta**: `PPI_COST` inclui apenas os componentes
necessários para trazer fisicamente o produto estrangeiro até uma
condição comparável ao produto doméstico — CIF na fronteira +
tributos/encargos legais de internação + logística física até o ponto de
comparação. Nenhum componente de remuneração comercial de um
intermediário.

| Componente | CORE COST | Justificativa |
|---|---|---|
| FOB | **YES** | Preço de compra do produto no exterior — insumo físico do custo. |
| Freight | **YES** | Custo físico de transporte internacional, observado (Comex Stat) quando disponível. |
| Insurance | **YES** | Custo físico/contratual de transporte, observado quando disponível. |
| FX | **YES** | Conversão cambial necessária para expressar custo em R$ — não é escolha, é conversão de unidade. |
| II (Imposto de Importação) | **YES** | Encargo legal obrigatório para internalizar o produto — parte do custo de trazer o bem à condição de venda no Brasil. |
| AFRMM | **YES** | Idem — encargo legal sobre o frete marítimo, obrigatório. |
| Antidumping | **YES** | Encargo legal específico por origem/exportador quando vigente — mesma natureza do II. |
| D_porto (despesas portuárias) | **YES** | Capatazia/armazenagem/despacho — custo físico de internalização, não remuneração de intermediário. |
| D_interno (frete interno) | **CONDITIONAL** | Custo físico de logística — pertence ao core **desde que a rota de referência seja definida de forma defensável e documentada** (ver Seção 12; não decidido nesta etapa). |
| Margin (margem do importador) | **NO** | Remuneração comercial de um intermediário (trading) — não é custo de trazer fisicamente o produto ao Brasil, é o preço que o comprador pagaria **a mais** por não fazer a importação diretamente. |

**Conclusão da Seção 3**: dos 10 componentes atuais, 9 já são
economicamente `CORE COST` sem ambiguidade (FOB, freight, insurance, FX,
II, AFRMM, antidumping, D_porto e D_interno-condicional). O único
componente cuja natureza conceitual diverge do resto da fórmula é a
margem — todos os outros representam desembolso físico ou legal
obrigatório para internalizar o produto; a margem representa remuneração
de quem faz a internalização por conta do comprador, o que é uma decisão
de canal de compra, não uma condição física/legal do produto.

## 4. Offer/Trader price definition — `PPI_OFFER`

**Definição formal proposta (não assumida como correta a priori,
conforme pedido do sprint)**:

```
PPI_OFFER = PPI_COST × (1 + commercial_margin)
```

Isso reproduz exatamente a estrutura atual de produção
(`base × (1 + margem_importador)`), o que já é uma evidência de que a
fórmula em produção hoje é estruturalmente uma fórmula de `PPI_OFFER`,
mesmo rotulada como "custo" em vários lugares (Seção 6 detalha essa
inconsistência de rótulo).

Elementos que um markup de trading real precisaria decompor, avaliados
individualmente:

| Elemento | Já embutido em outro componente do PPI atual? | Seria adicional? |
|---|---|---|
| **Financial/working-capital cost** (capital empatado entre contratação e recebimento, ~60-120 dias, função de Selic/CDI) | Não — nenhum componente atual do PPI remunera o capital de giro do importador. | **Sim**, se `PPI_OFFER` quiser ser completo — hoje está implicitamente "dentro" dos 3%, sem decomposição (`docs/validation/ipia_hrc_cost_parameter_calibration.md` §6). |
| **Credit risk** (risco de inadimplência do comprador doméstico face ao trading) | Não. | Sim, mesma observação — misturado nos 3% sem número próprio. |
| **Inventory risk** (variação de preço entre compra e revenda, se o trading mantém estoque) | Não. | Sim — só existe se o modelo de negócio do trading envolver estoque, não repasse direto. |
| **FX hedge cost** (custo de travar câmbio entre contratação e liquidação) | Parcialmente relacionado ao câmbio observado (§9.6 METODOLOGIA.md usa PTAX médio do mês, não a taxa efetivamente contratada por um importador específico — essa é uma limitação já documentada, não uma remuneração). | Sim, se o objetivo for o custo efetivo de um importador que trava câmbio antecipadamente. |
| **Operational overhead** (despacho, documentação, estrutura administrativa) | Não — D_porto cobre capatazia/armazenagem/despacho aduaneiro físico, não a estrutura administrativa do próprio trading. | Sim. |
| **Commercial margin** (lucro puro) | É o único elemento que os 3% atuais nominalmente pretendem representar. | Já está no core atual, mas sem benchmark (`ipia_hrc_cost_parameter_calibration.md` §6: "nenhum benchmark público de markup de trading de aço plano foi encontrado"). |

**Conclusão da Seção 4**: os 3% atuais não são uma "margem comercial
pura" — são, na melhor leitura possível, um número único tentando
representar de forma agregada financial carrying cost + overhead +
margem comercial + (parcialmente) FX hedge, sem que nenhum desses
subcomponentes tenha sido decomposto ou calibrado individualmente. Isso
não invalida a existência conceitual de `PPI_OFFER` — só confirma que o
valor atual (3%) não é uma medição de nenhum desses elementos
especificamente.

## 5. Double-counting risk

Mapeamento explícito, conforme pedido:

- **Risco principal**: se no futuro o projeto decidir modelar
  separadamente financial carrying cost (via Selic/CDI e um prazo médio
  de trânsito) e/ou FX hedge cost, e a margem de 3% for mantida
  simultaneamente como estava (sem redução), o novo componente e a
  margem antiga passariam a cobrir o mesmo conceito duas vezes — o PPI
  ficaria inflado sem nenhuma mudança real de custo.
- **Onde isso pode acontecer concretamente**: a Seção 9.9 do
  METODOLOGIA.md já registra que D_porto/D_interno podem, no futuro, se
  tornar "time-varying" (ex.: D_interno indexado à tabela ANTT, que já
  existe oficialmente). Se D_interno passar a refletir o custo real de
  frete rodoviário via ANTT (que já embute o custo operacional do
  transportador, incluindo sua própria margem de operação), e a margem
  de 3% continuar sendo aplicada sobre a base inteira (que já inclui
  D_interno), parte da margem estaria remunerando duas vezes a mesma
  cadeia logística — uma vez explicitamente (tabela ANTT) e outra
  implicitamente (o markup de 3% sobre essa mesma linha).
- **Mitigação estrutural**: a arquitetura dual (Seção 9) resolve isso por
  construção — ao isolar `PPI_COST` como o único candidato a
  recalibração de componentes físicos/logísticos, e `PPI_OFFER` como uma
  camada estritamente multiplicativa por cima do `PPI_COST` já
  finalizado, nunca há dois parâmetros cobrindo o mesmo conceito dentro
  do mesmo core.

## 6. Domestic-price comparability

**Achado central desta seção, com peso decisivo para a recomendação**:
o preço doméstico usado pelo IPIA — em ambas as versões — é
estruturalmente um **preço de produtor/mill**, não um preço de
revenda/distribuidor:

- **V1** (ADR 0001): média ponderada de "receita líquida ÷ volume vendido
  no mercado interno" de Usiminas e CSN — preço médio realizado pelo
  próprio fabricante nas suas vendas diretas, sem nenhuma camada de
  distribuição/trading embutida.
- **V2** (README, ADR 0010): PIA-Produto (IBGE/SIDRA) — "valor da
  produção" declarado pela própria indústria produtora, distribuído
  mensalmente via IPP-242. Mesma natureza: valor de venda do produtor,
  não do canal de revenda.

**Implicação direta**: comparar um preço doméstico que é
estruturalmente "preço de fábrica" contra um `PPI_OFFER` que inclui a
margem de um trading intermediário é uma comparação assimétrica — o lado
importado estaria sendo cobrado uma camada comercial adicional
(intermediação) que o lado doméstico, por definição da própria fonte
usada, não carrega (o produtor doméstico vende direto, sem essa camada
no preço medido). Isso não significa que um comprador industrial real
nunca pague essa margem ao importar — significa que **o par
doméstico/importado hoje usado no IPIA não é like-for-like se o lado
importado incluir margem comercial e o lado doméstico não incluir a
margem equivalente de um distribuidor doméstico**.

Essa assimetria pesa a favor de `PPI_COST` como definição mais
comparável ao preço doméstico atualmente ancorado (produtor/mill), e
contra `PPI_OFFER` como a definição-núcleo do índice principal — a menos
que o projeto decida também trocar a âncora doméstica para um preço de
revenda/distribuidor (fora de escopo, mudaria outra decisão Level 3 já
aceita em ADR 0001/0010).

## 7. Import parity practice (institutional/market research)

Pesquisa direcionada (não apoiada em uma única fonte, conforme pedido):

- **FEWS NET** (USAID Famine Early Warning Systems Network) — guia
  metodológico "Import/Export Parity Price Analysis": define preço de
  paridade de importação como o custo de trazer o produto ao mercado
  doméstico (FOB + frete + seguro + tarifas + custo de transporte
  interno até o ponto de consumo) — **sem markup comercial** — e usa
  explicitamente o gap entre paridade e preço de mercado observado como
  o *diagnóstico* de quanto os traders estão (ou não) extraindo de
  margem. Ou seja, no desenho FEWS NET, a margem não é parte da
  paridade — ela é justamente o que a comparação com o preço de mercado
  revela.
- **Glossários de mercado de commodities/energia** (import parity price
  para combustíveis, definição amplamente replicada): "FOB no porto de
  origem + frete marítimo + seguro + custos portuários/descarga +
  tarifas/impostos + transporte interno até o ponto de consumo" — mesma
  estrutura, sem margem comercial como componente padrão.
- **Prática de mercado de aço (comentário setorial, Steel Market
  Update/steelonthenet)**: ao estimar CIF em portos dos EUA para
  comparação com preço doméstico, analistas somam um valor único de
  frete + handling + **margem de trading** — aqui a margem aparece
  agregada, mas com um propósito diferente: estimar o **preço de
  oferta/prateleira** de material importado como teto competitivo
  ("domestic mills price below the import parity ceiling"), não a
  paridade em si.

**Leitura conjunta**: a definição institucional mais citada e mais
transparente (FEWS NET, glossários de energia/commodities) trata import
parity como **landed cost sem margem comercial** — a margem é tratada
como uma variável a ser *observada/inferida* pela comparação, não como
um insumo do próprio índice de paridade. A prática setorial de aço que
inclui margem o faz para um propósito distinto (estimar um teto de
oferta), não para redefinir "paridade". Isso é evidência convergente
(múltiplas fontes, propósitos coerentes) a favor de `PPI_COST` como o
conceito mais alinhado ao nome "import parity" e mais amplamente
praticado.

## 8. Economic perspective table

| Use case | PPI Cost | PPI Offer |
|---|---|---|
| Competitividade da siderurgia doméstica | **Ideal** — mede exatamente a pressão de custo de entrada, sem contaminar com a decisão comercial de um trading específico. | Distorce a leitura de pressão competitiva ao somar uma variável de canal de compra não relacionada ao custo de produção estrangeiro. |
| Decisão importar vs comprar doméstico | Necessário, mas insuficiente sozinho para um comprador que de fato usaria um trading (subestimaria o custo real da rota trading). | Mais realista para esse caso específico — mas só se a margem for calibrada com evidência real, o que hoje não existe. |
| Monitoramento macro/setorial | **Ideal** — reprodutível, sem dependência de uma premissa de canal comercial não observável. | Introduz um grau de liberdade (margem não calibrada) que não deveria afetar uma leitura macro. |
| Pricing de trading | Insuficiente sozinho — um trading real precisa da margem para decidir seu próprio preço. | **Ideal** em princípio, mas exige benchmark real de margem, hoje inexistente (Seção 4/6 do sprint anterior). |
| Comparabilidade histórica | **Mais robusta** — nenhum componente sem calibração formal (margem) contamina a série histórica publicada. | Mais frágil — herdar um número de margem nunca calibrado (3%, desde a pesquisa original, nunca revisado) para toda a série histórica é o oposto de "comparável e auditável". |
| Reprodutibilidade | **Alta** — todos os componentes restantes são observados/calculados/legais, exceto D_porto/D_interno (ainda ESTIMADO, mas fisicamente definíveis). | Menor — depende de um parâmetro (margem) sem fonte pública, calibração ou revisão formal desde a origem. |

## 9. Threshold-100 interpretation

- **COST**: `IPIA=100` significa "o preço doméstico (produtor) iguala o
  custo econômico de trazer o produto estrangeiro ao Brasil em condição
  comparável". Leitura limpa: acima de 100, o custo físico/legal de
  importar é menor que o preço doméstico — há espaço de pressão
  competitiva real, independentemente de qualquer decisão comercial de
  canal.
- **OFFER**: `IPIA=100` significa "o preço doméstico iguala o preço que
  um trading cobraria para entregar o material" — leitura que depende de
  uma margem não calibrada; um leitor não tem como saber se um
  cruzamento do threshold reflete mudança real de custo ou apenas o
  valor arbitrário de margem herdado da pesquisa original.
- **Qual é mais clara e defensável para publicação**: **COST**. A
  interpretação COST é auditável até o último componente (mesmo
  D_porto/D_interno, embora `ESTIMADO`, são fisicamente definíveis e
  calibráveis com evidência real — Seção 3). A interpretação OFFER herda
  a fragilidade de um parâmetro (`margem_importador`) que nunca teve
  fonte, nunca foi calibrado e cuja ausência de benchmark público é, ela
  mesma, uma conclusão robusta do sprint anterior.

## 10. Margin 0% vs 3% impact (contrafactual, produção não alterada)

Reexecução isolada — apenas a margem varia (0% vs 3%, Current);
D_porto/D_interno mantidos em Current (R$210/R$140) nos dois cenários —
via `scripts/contrafactual_margem_zero_vs_atual.py`, reusando
`agregar_ipia_hrc_multi_ncm_mensal` (produção), 2019-01 a 2026-07 (N=78
meses):

| Métrica | Valor |
|---|---:|
| Mean ΔPPI (zero vs. atual) | **-2,91%** |
| Max \|ΔPPI\| | 2,91% (constante — margem é um multiplicador fixo, não depende do mês) |
| Mean ΔIPIA hipotético (zero vs. atual) | **+3,00%** |
| Max \|ΔIPIA hipotético\| | 3,00% (idem — exatamente `1/(1-3%)-1`) |
| Threshold crossings (IPIA hipotético, zero vs. atual, sobre preço doméstico hipotético constante R$4.800/t) | **2 de 78 meses** |
| PPI atual, mês mais recente (margem 3%) | R$ 3.781,51/t |
| PPI zero, mês mais recente (margem 0%) | R$ 3.671,37/t |
| Diferença absoluta, mês mais recente | R$ 110,14/t |

**Leitura**: como a margem é aplicada multiplicativamente sobre toda a
base (CIF+tributos+D_porto+D_interno), seu efeito percentual é constante
mês a mês (~2,91%/3,00%) — não há sazonalidade nem dependência de outros
parâmetros. O efeito é pequeno em termos absolutos de threshold (2
cruzamentos em 78 meses, usando o mesmo preço doméstico hipotético
constante do sprint anterior, não o IPIA real), mas é a maior
contribuição isolada por ponto percentual entre os três parâmetros
`ESTIMADO` (consistente com a elasticidade de ~0,97%/p.p. já documentada
em `docs/METODOLOGIA.md` §9.10 e no sprint anterior).

## 11. Dual architecture assessment

**Proposta**: `PPI_COST` como core metodológico (recalculado e
publicado), `PPI_OFFER = PPI_COST × (1 + margem_comercial_parametrizável)`
como camada analítica separada, não oficial, claramente rotulada.

Vantagens:
- Core reproduzível sem nenhum parâmetro sem fonte pública — resolve o
  ponto mais frágil identificado em todo o sprint anterior (margem sem
  benchmark).
- Não força a fingir que existe um "markup universal de trading de aço
  plano" — que a pesquisa de mercado (Seção 4/7) mostra não existir
  publicamente.
- Permite, no futuro, oferecer cenários de margem parametrizáveis
  (0%/3%/6%/valor calibrado) sem que isso afete a série oficial —
  exatamente o padrão que o Reporting atual já sinaliza informalmente ao
  rotular o PPI como "custo" (Seção 6 abaixo) mesmo incluindo margem.
- Convergente com a prática institucional mais citada (FEWS NET,
  glossários de commodity/energy — Seção 7): parity = cost; margem é uma
  camada de leitura, não um insumo do índice.

Desvantagens:
- Muda a interpretação numérica de toda a série IPIA-HRC oficial já
  publicada (o valor de `IPIA` hoje já embute 3% de margem) — é uma
  decisão Level 3 explícita, não incremental.
- Exige decidir, para a camada `PPI_OFFER`, se ela é apenas ilustrativa
  (parâmetro livre, sem pretensão de medir um valor real) ou se o
  projeto vai efetivamente buscar uma calibração de margem real no
  futuro — isso é trabalho adicional, não zero-custo.
- Dois números publicados por período (mesmo que um seja "oficial" e
  outro "analítico") aumenta a superfície de comunicação/documentação
  que o projeto precisa manter clara para não confundir o leitor.

## 12. D_porto / D_interno — nota conceitual (não recalibrado nesta etapa)

- **D_porto**: já classificado como fisicamente parte do custo de
  internalização (capatazia/armazenagem/despacho) — permanece `CORE
  COST` sob qualquer opção (A/B/C). Não há dependência da decisão
  A vs. B.
- **D_interno**: sua posição como `CORE COST` depende de até onde o PPI
  precisa chegar geograficamente para ser comparável ao preço doméstico.
  Como o preço doméstico é um preço de **produtor** (Seção 6, não um
  preço entregue num centro consumidor específico), o ponto de
  comparabilidade mais defensável conceitualmente é **próximo ao ponto
  de saída do produto do canal de importação** (porto ou imediações),
  não necessariamente "cliente industrial final" — mas essa é
  exatamente a pergunta que o sprint anterior identificou como sem rota
  de referência documentada (composição de UF de entrada muito dispersa,
  Amazonas 33% sem destino confirmado). **Não decidida aqui** —
  registrada para a próxima etapa de evidência direta (Seção 16,
  Recomendação 2).

## 13. Decision matrix

| Criterion | Cost | Offer | Dual |
|---|---:|---:|---:|
| Economic clarity | Alta — cada componente é custo físico/legal definível | Baixa — margem mistura 4+ conceitos nunca decompostos (Seção 4) | Alta no core; a camada offer é explicitamente rotulada como estimativa |
| Reproducibility | Alta | Baixa (depende de um parâmetro sem fonte) | Alta no core; camada offer reproduzível *dado* um parâmetro explícito |
| Public-data support | Forte (9 de 10 componentes já são OBSERVADO/CALCULADO/legais) | Fraca (nenhum benchmark de margem encontrado — Seção 4/6 do sprint anterior) | Forte no core; fraca na camada offer (mesma limitação, mas isolada) |
| Subjectivity | Baixa | Alta | Baixa no core; alta mas isolada na camada offer |
| Comparability with domestic price | Alta (ambos os lados em nível "produtor", Seção 6) | Baixa (assimetria de canal comercial, Seção 6) | Alta no core; a camada offer é explicitamente não comparável 1:1 e rotulada assim |
| Usefulness for market intelligence | Média (falta a perspectiva de canal de compra real) | Alta *em princípio*, condicionada a calibração futura | Alta — cobre os dois usos sem misturar um no outro |
| Auditability | Alta | Baixa | Alta no core; a camada offer é auditável como "cenário", não como "medição" |
| Future extensibility | Média (adicionar canal de compra depois exige nova decisão Level 3) | Baixa (already conflates future extensions — Seção 5, double counting) | **Alta** — cada extensão futura (financial carrying cost, FX hedge, distintos canais) tem um lugar natural na camada offer, sem tocar o core |

## 14. Recommendation

**C — DUAL ARCHITECTURE**, com prioridade de implementação em duas fases
distintas (ver Seção 16 para a ordem recomendada):

- **Core = `PPI_COST`**: remover a margem comercial do cálculo oficial
  do PPI/IPIA em uma futura revisão (Level 3, decisão do usuário,
  mudaria a série histórica publicada — não implementado aqui).
- **Offer = camada analítica separada, opcional, explicitamente rotulada
  como cenário/estimativa**, nunca misturada com a série oficial.

**Por que não A, B ou D isoladamente**:
- **A (só Cost, remover margem e nunca mais falar de oferta)** descarta
  informação real: existe uma pergunta de negócio legítima ("quanto eu
  pagaria via trading?") que o projeto pode querer responder no futuro,
  mesmo sem calibração pronta hoje.
- **B (Core = Offer, buscar calibração)** vai contra a evidência mais
  forte deste sprint: nenhum benchmark público de margem de trading foi
  encontrado (nem neste sprint nem no anterior), a prática institucional
  mais citada não inclui margem na definição de paridade (Seção 7), e a
  âncora doméstica atual (preço de produtor) não é comparável a um
  preço com margem embutida (Seção 6). Fixar o *core* institucional
  numa variável sem fonte é o oposto do que a metodologia do projeto
  exige (`docs/METODOLOGIA.md`, `CLAUDE.md` — nunca fabricar estimativa
  sem evidência).
- **D (Inconclusive)** não se sustenta: há evidência convergente
  suficiente (pesquisa original, governança interna do projeto,
  reporting já em produção, comparabilidade doméstica, prática
  institucional externa) apontando na mesma direção (Cost como core) —
  a única coisa genuinamente pendente é a decisão de implementar, que é
  do usuário, não a falta de evidência conceitual.

**Achado colateral que reforça a recomendação**: o Reporting já em
produção **já rotula o PPI como custo**, não como oferta, em ambas as
versões:
- Legado (`src/reporting/pages.py:270-272`): "custo de internação" vs.
  "preço doméstico".
- V2 atual (`src/reporting/pages.py:790`): *"Custo de paridade de
  importação (PPI)"*.

Ou seja, **o próprio produto publicado hoje já se apresenta como medindo
custo**, apesar de a fórmula incluir uma margem comercial não calibrada.
A arquitetura dual apenas alinha o conteúdo do índice ao rótulo que o
projeto já usa para descrevê-lo.

## 15. Level 3 gate

Esta etapa **não implementa** nenhuma das opções. Qualquer passo
seguinte que:
- remova a margem do core oficial;
- crie `PPI_COST` como série publicada;
- crie `PPI_OFFER` como camada nova;
- altere a interpretação do threshold 100;
- altere qualquer valor oficial já publicado;

é Level 3 e requer decisão explícita do usuário antes de qualquer
implementação, incluindo qual das opções (A/B/C/D) adotar e em que
sequência.

## 16. Confidence

- **HIGH** — a pergunta A vs. B já existia na pesquisa metodológica
  original (citação literal, Seção 1) e nunca foi resolvida; isso não é
  uma inferência, é um fato documental direto.
- **HIGH** — o Reporting em produção já rotula o PPI como "custo" em
  ambas as versões (achado de código direto, Seção 14).
- **HIGH** — a âncora doméstica (V1 e V2) é estruturalmente um preço de
  produtor, não de revenda (ADRs 0001/0010, achado direto).
- **MEDIUM** — a leitura de prática institucional (Seção 7) é baseada em
  pesquisa web desta etapa (FEWS NET, glossários de energia/commodities,
  comentário setorial de aço) — convergente entre fontes, mas não
  exaustiva; nenhuma fonte proprietária (Platts/Fastmarkets/CRU
  methodology papers, tipicamente pagas) foi consultada.
- **MEDIUM** — a recomendação C (dual) é uma síntese de evidência
  convergente, não uma medição — a decisão final entre A/B/C continua
  sendo do usuário, conforme o gate Level 3.

## 17. Production impact

**Nenhuma série oficial mudou.** `ParamsIPIA`, PPI/IPIA oficial,
vintages, `VERSAO_METODOLOGIA` e reporting permanecem idênticos ao
início desta etapa. O único artefato de código novo é
`scripts/contrafactual_margem_zero_vs_atual.py` (research-only, fora de
`src/`), que reusa `agregar_ipia_hrc_multi_ncm_mensal` sem alterá-la.

## 18. Tests

Nenhum teste automatizado novo foi necessário (nenhum helper analítico
persistente foi criado além do script de contrafactual, que não é uma
função de produção reutilizável — é um runner de uma única comparação).
Suíte completa reexecutada após a criação do script (que não toca
`src/` nem `tests/`):

```
python -m pytest tests/ -v
```

Resultado observado: **445 passed** (idêntico à baseline do início
desta etapa).

## 19. Selftest

```
python src/indices_setoriais.py --selftest
```

Resultado observado: `RESULTADO: todos os testes passaram.` (PASS).

## Limitations

1. A Seção 7 (prática institucional) é uma pesquisa web desta etapa, não
   uma revisão sistemática da literatura de price-reporting agencies —
   fontes proprietárias (Platts/Fastmarkets/CRU) não foram consultadas.
2. O contrafactual de margem (Seção 10) usa o mesmo preço doméstico
   hipotético constante do sprint anterior (R$4.800/t) — não é o IPIA
   real, serve só para testar o comportamento mecânico do threshold.
3. Esta etapa não decide a rota geográfica de D_interno (Seção 12) —
   permanece uma pendência de evidência separada, já registrada no
   sprint anterior.
4. Nenhuma decomposição numérica de financial carrying cost/overhead/
   margem comercial pura foi produzida (Seção 4) — apenas o mapeamento
   conceitual de quais elementos existiriam se o projeto decidir
   implementar `PPI_OFFER` no futuro.

## References

- `references/manual_metodologico_indices_setoriais.md` §5 (objetivo
  original do IPIA, fórmula, tabela de parâmetros de internação —
  fonte da citação decisiva "zere se quiser medir custo puro...").
- `docs/METODOLOGIA.md` §9.7 (viés de valor unitário), §9.8
  (classificação de proveniência dos parâmetros do PPI), §9.9
  (histórico/justificativa da constância), §9.10 (sensibilidade).
- `docs/validation/ipia_hrc_cost_parameter_calibration.md` (sprint
  anterior — composição real de UF de entrada, ausência de benchmark
  de margem, elasticidade normalizada).
- `docs/adr/0001-ancora-preco-domestico-usiminas-csn-ponderado.md`,
  `docs/adr/0010-pia-produto-hrc-benchmark-anual-proportional-denton.md`
  (natureza da âncora doméstica como preço de produtor).
- `src/indices_setoriais.py` (`ParamsIPIA`, `custo_importacao_rs_t`,
  `_ppi_brl_t`).
- `src/reporting/pages.py` (rotulagem "custo de internação"/"custo de
  paridade de importação" já em produção).
- `.claude/rules/methodology.md` (invariante conceitual do projeto:
  "IPIA = domestic price / import parity **cost** × 100").
- FEWS NET (USAID) — "Import/Export Parity Price Analysis" (guia
  metodológico, pesquisa web desta etapa).
- Glossários de import parity price para commodities/energia e
  comentário setorial de aço (Steel Market Update/steelonthenet,
  pesquisa web desta etapa) — ver Seção 7 para síntese e ressalva de
  confiança MEDIUM.
