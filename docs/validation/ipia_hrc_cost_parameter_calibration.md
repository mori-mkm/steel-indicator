# IPIA-HRC — Margin / Port / Inland Cost Parameter Calibration

**Status: RESEARCH + VALIDATION ONLY — não implementa nenhuma mudança.**
`ParamsIPIA`, PPI oficial, IPIA, vintages, `VERSAO_METODOLOGIA` e
reporting permanecem exatamente como estavam antes desta etapa.

Reproduzir: `docker build -t steel-indicator-dev .` seguido de
`docker run --rm -v "$(pwd)/data:/app/data" steel-indicator-dev python scripts/validar_ipia_hrc_cost_parameters.py`
(no Windows/git-bash, prefixar `MSYS_NO_PATHCONV=1`). Reusa
`agregar_ipia_hrc_multi_ncm_mensal(p=...)` (produção, já aceita um
`ParamsIPIA` diferente do default como argumento explícito) — nenhuma
função de cálculo foi reimplementada.

## Question

> Os parâmetros atuais (D_porto=R$210/t, D_interno=R$140/t,
> margem=3%) representam de forma defensável o custo econômico de
> internalizar HRC importado no Brasil? Se não, quais faixas de valores
> são empiricamente mais defensáveis?

## 1. Executive conclusion

- **D_porto (R$210/t)**: nenhum benchmark público de R$/t para carga
  breakbulk/siderúrgica foi localizado — o terminal mais relevante
  pesquisado (Porto Itapoá/SC, na 2ª UF de entrada de HRC) publica
  armazenagem/movimentação **ad valorem ou por contêiner**, e cobra carga
  de projeto/breakbulk **"Sob Consulta"** (sem tabela pública). Evidência
  insuficiente para recalibrar o nível central; faixa LOW-HIGH construída
  por analogia estrutural, não por medição direta.
- **D_interno (R$140/t)**: nenhuma rota de referência documentada
  existia. A composição real de UF de entrada (Comex Stat, dado
  próprio) é **radicalmente diferente do que se assumiria por
  conveniência**: Amazonas (33%) e Santa Catarina (20%) dominam,
  Rio de Janeiro (18%) e Ceará (17%) na sequência — São Paulo é **1,1%**.
  Santos nunca deveria ter sido usado como âncora implícita. O mix de
  portos também mudou materialmente ano a ano (2022: 85% Santa Catarina;
  2025: 46% Amazonas) — uma "rota única" fixa é uma simplificação frágil.
- **Margem (3%)**: **nenhum benchmark público de markup de
  trading/importação de aço plano foi encontrado.** A fórmula de
  produção aplica a margem sobre o **landed cost inteiro** (CIF + II +
  AFRMM + AD + D_porto + D_interno), não só sobre o valor da mercadoria —
  isso mistura conceitualmente markup comercial, custo financeiro e
  overhead num único número, sem decomposição.
- **Erosão real (achado não previsto no escopo original, mas material)**:
  o IPCA acumulado 2019-01–2026-07 é **+50,1%**. R$210 e R$140 nominais
  hoje valem, em termos de jan/2019, apenas **R$139,88 e R$93,25** — uma
  queda real de cerca de um terço. Isso é, por si só, uma limitação maior
  que o nível inicial dos parâmetros.
- **Materialidade (contrafactual real, 2019-2026, N~78-90 meses)**:
  isolando cada parâmetro no seu extremo HIGH — D_porto +2,80% PPI médio,
  D_interno +3,06%, margem +2,91% — magnitudes **comparáveis** dentro das
  faixas testadas. Normalizando por unidade (elasticidade), a margem
  continua sendo a mais sensível por ponto percentual (**≈0,97% de PPI
  por p.p. de margem**, batendo quase exatamente com a sensibilidade de
  -4,85%/5p.p. já documentada em `docs/METODOLOGIA.md` §9.10).
- **Threshold crossings**: no cenário HIGH conjunto, até 5 meses (de um
  IPIA hipotético construído com preço doméstico constante, só para teste
  mecânico) cruzariam o threshold 100 em relação ao Current — nenhum
  cruzamento no cenário "Evidence Base" (idêntico ao Current, por falta
  de evidência que justifique mover o centro).
- **Recommendation**: D_porto → **D (INSUFFICIENT EVIDENCE)**; D_interno
  → **D (INSUFFICIENT EVIDENCE)**, mas com achado de composição de porto
  que deveria orientar pesquisa futura; margem → **B (RECALIBRATE)** não
  no nível, mas na **transparência conceitual** — decompor o que os 3%
  representam antes de qualquer novo número.

## 2. Current parameter audit

Confirmado direto em `ParamsIPIA` (`src/indices_setoriais.py`):

| Parameter | Current | Unit | Provenance | Time-varying? |
|---|---:|---|---|---|
| D_porto (`despesas_porto_rs_t`) | 210 | R$/t | ESTIMADO | Não |
| D_interno (`frete_interno_rs_t`) | 140 | R$/t | ESTIMADO | Não |
| margem (`margem_importador`) | 3% | % | ESTIMADO | Não |

Nenhum outro custo fixo escondido foi encontrado na fórmula
(`custo_importacao_rs_t`/`_ppi_brl_t`) — os únicos componentes do PPI são
CIF (FOB+frete+seguro observados), II, AFRMM, antidumping, D_porto,
D_interno e margem, nesta ordem, com margem aplicada por último sobre a
soma de todos os anteriores.

## 3. Economic definitions

### D_porto
Custos de internalização física/aduaneira no porto — a metodologia
original (`references/manual_metodologico_indices_setoriais.md` §5.5) não
detalha a composição exata; a leitura mais defensável é capatazia +
armazenagem + THC + despacho, mas **isso nunca foi confirmado
explicitamente como a composição pretendida** — registrado como limitação
(não assumir que "tudo entra").

### D_interno
Custo logístico porto → destino de referência. Não havia, antes desta
etapa, nenhuma rota de referência documentada — "porto → cliente" sem
especificar qual porto nem qual cliente.

### Margem
A fórmula de produção (`_ppi_brl_t`) aplica `margem_importador` como
markup sobre `CIF + II + AFRMM + AD + D_porto + D_interno` — ou seja, um
markup de **cost-plus sobre o landed cost inteiro**, incluindo tributos e
logística, não um markup só sobre o valor da mercadoria. Isso já é uma
mistura implícita de conceitos: um trading real cobra markup sobre o que
ele desembolsa (o que inclui tributos), então a estrutura da fórmula é
economicamente coerente com "markup de trading" — mas não separa quanto
disso é margem comercial pura vs. custo financeiro do capital empatado vs.
overhead administrativo (Seção 5/6 abaixo).

## 4. Port-cost evidence

### Portos relevantes (Comex Stat, dado próprio — nunca assumido)

Cesta HRC completa, 2022-2026, agrupado por UF de entrada:

| UF | Share do volume (KG) |
|---|---:|
| Amazonas | 32,9% |
| Santa Catarina | 19,6% |
| Rio de Janeiro | 17,8% |
| Ceará | 16,8% |
| Piauí | 8,6% |
| Rondônia | 1,4% |
| São Paulo | 1,1% |

**Achado não previsto no escopo original, mas materialmente importante**:
Manaus (Amazonas) é o principal ponto de entrada — provavelmente ligado à
Zona Franca de Manaus, o que levanta uma questão de interpretação não
resolvida nesta etapa: o HRC que entra em Manaus é consumido localmente
(polo industrial de eletroeletrônicos/duas rodas) ou redistribuído
nacionalmente a partir de lá? Nenhuma das duas hipóteses foi confirmada.
**Santos (São Paulo) — a âncora implícita mais comum em análises de
comércio exterior brasileiro — responde por só 1,1% do volume.** O mix
também mudou substancialmente ano a ano (2022: 85% Santa Catarina; 2025:
46% Amazonas, 27% Rio de Janeiro) — não há uma "rota típica" estável ao
longo do tempo.

### Tarifas portuárias — Porto Itapoá/SC (Tier 1/2, tabela oficial 2026)

Terminal na mesma região do 2º maior ponto de entrada (Santa Catarina),
com contato comercial dedicado a "Siderurgia" — tabela pública
(`Tabela-Publicada-2026-1-1.pdf`, atualizada dez/2025) confirma:

- Armazenagem de importação: **% ad valorem sobre o CIF** (0,687% no 1º
  período, escalonando até 0,544%/dia depois do 30º dia), com mínimo por
  contêiner (R$1.377 a R$551), **não R$/tonelada**.
- Movimentação de contêiner: valores fixos por contêiner (R$124-495),
  não por tonelada.
- **Carga de projeto/breakbulk (item 7, "Movimentação de Cargas
  Projeto")** — a categoria mais próxima de bobina a quente não
  containerizada — está listada como **"Sob Consulta"** em toda a
  tabela pública, sem valor numérico divulgado.

**Conclusão desta seção**: não existe, nas fontes públicas pesquisadas,
um valor R$/t diretamente comparável ao `despesas_porto_rs_t` atual para
o tipo de carga relevante. A estrutura real de cobrança portuária
brasileira (ad valorem ou por contêiner) também não corresponde
diretamente ao conceito "R$/t fixo" do parâmetro — isso é, por si, um
limite conceitual do parâmetro, não só de nível.

### D_porto — faixa curada (LOW/BASE/HIGH)

| Componente | Low | Base | High | Source |
|---|---:|---:|---:|---|
| D_porto_total | R$120/t | R$210/t (inalterado) | R$320/t | Ordem de grandeza a partir de armazenagem ad valorem + movimentação observadas no Porto Itapoá, **nunca uma medição direta de breakbulk** (ver ressalva acima) |

## 5. Inland-freight evidence

### Fonte oficial

Resolução ANTT nº 6.084/2026 (17/07/2026), Tabela A (carga geral):
fórmula `(distância_km × CCD) + CC`, onde CCD (Coeficiente de Custo de
Deslocamento, R$/km) e CC (Custo de Carga/Descarga, fixo) variam por
número de eixos. Calculadora oficial: `calculadorafrete.antt.gov.br`
(não consultada programaticamente nesta etapa). Ordem de grandeza
recolhida de agregadores especializados em frete (Tier 3, só para
contexto — nunca como valor final): 2 eixos ≈R$3,00-4,00/km; 5 eixos
(carreta, configuração mais plausível para bobina a quente, ~27t úteis)
≈R$5,00-6,50/km; 6-7 eixos (bitrem) ≈R$6,50-8,50/km. **O piso mínimo ANTT
não deve ser tratado como preço de mercado** — é um piso regulatório, o
preço efetivamente pago pode ser maior.

### Destino econômico

Não construído um modelo logístico nacional — usada uma rota de
referência defensável por UF de entrada dominante: Santa Catarina
(2º maior UF) → polo industrial de São Paulo é a combinação mais citável
para consumo relevante (automotivo, bens de capital). Amazonas (1º maior
UF) tem destino incerto (ver Seção 4) — não usado como base da rota de
referência por falta de evidência sobre para onde o volume vai depois de
Manaus.

### Cenários

| Cenário | Rota conceitual | km (aprox., não medido por API de rotas) | R$/t (5 eixos, ANTT) |
|---|---|---:|---:|
| Short haul | São Francisco do Sul/SC → Joinville/SC (consumo industrial local) | ~50 | R$60/t |
| Base route | São Francisco do Sul/SC → São Paulo/SP | ~450 | R$140/t (inalterado) |
| Long haul | Itaguaí/RJ → Belo Horizonte/MG | ~550 | R$260/t |

### Modal alternativo

Cabotagem/ferrovia não investigada em profundidade — Manaus (maior UF de
entrada) sugere que **navegação fluvial/cabotagem pode ser
estruturalmente relevante** para uma fração grande do volume, mas isso
não foi confirmado nem quantificado nesta etapa. Registrado como
limitação, não como conclusão.

## 6. Margin evidence

Pesquisa dirigida (trading/markup de aço plano, distribuição, importação
industrial) **não encontrou nenhum benchmark público quantificado** —
resultados de busca retornaram contexto de mercado (volume de
importação, pressão sobre a indústria doméstica) mas nenhum número de
markup. Consistente com a natureza da informação (margem comercial de
trading é tipicamente informação proprietária/contratual, não publicada).

**Pergunta metodológica central (§15 do sprint, não respondida
definitivamente aqui — registrada para decisão futura)**: o IPIA-HRC
pretende medir:

- **A — Import Parity COST**: quanto custa fisicamente importar e
  internalizar; ou
- **B — Import Parity OFFER/TRADER PRICE**: quanto um comprador
  doméstico pagaria via trading.

Se a intenção é A, uma margem comercial de trading talvez não pertença ao
núcleo do índice. Se é B, ela pertence, mas precisa de evidência de
markup real, não de um número herdado sem verificação. **Esta etapa não
decide entre A e B** — é uma pergunta explicitamente de decisão Level 3
para o usuário.

### Decomposição conceitual (diagnóstico, não implementado)

- **Financial carrying cost**: capital empatado entre contratação e
  recebimento (tipicamente 60-120 dias considerando trânsito marítimo +
  desembaraço). Ordem de grandeza, usando CDI/Selic como benchmark de
  custo de capital em reais (não calculado numericamente nesta etapa —
  exigiria uma premissa de prazo médio que não foi pesquisada) — é
  plausivelmente uma fração relevante dos 3% atuais.
- **Operational overhead**: despacho, documentação, estrutura
  administrativa do importador — não estimado.
- **Commercial margin**: lucro/risco do trading — não estimado.

**Nenhuma decomposição numérica foi produzida** — apenas o registro de
que os 3% atuais provavelmente misturam os três conceitos sem que isso
esteja explícito em nenhum lugar da metodologia.

## 7. Time-varying assessment

| Parâmetro | Deveria variar no tempo? | Driver plausível | Decisão |
|---|---|---|---|
| D_porto | Possivelmente | Inflação de serviços, tarifas portuárias (têm reajuste próprio, ex. Res. ANTAQ) | Não implementado — evidência insuficiente para uma série, não só um nível |
| D_interno | Possivelmente | Diesel, pedágio, tabela ANTT (já é atualizada periodicamente pela própria ANTT) | Não implementado |
| Margem | Possivelmente | Juros (Selic/CDI), risco cambial, ciclo de mercado | Não implementado |

Nenhuma complexidade adicional foi implementada — a pergunta permanece
em aberto, registrada para decisão futura com evidência específica.

## 8. Real erosion (IPCA) — achado não previsto no escopo original

Deflacionando pelo IPCA acumulado (BCB/SGS série 433, jan/2019 a
jul/2026 — mesma janela de referência do IPIA-HRC V2):

| | Nominal hoje | Valor real em termos de jan/2019 |
|---|---:|---:|
| IPCA acumulado | — | **+50,13%** |
| D_porto | R$210,00 | **R$139,88** |
| D_interno | R$140,00 | **R$93,25** |

Manter R$210/R$140 nominais desde a origem do parâmetro implica uma
**queda real de ~33%** no custo que esses parâmetros pretendem
representar — se o custo físico real de porto/frete acompanhou a
inflação geral (hipótese razoável, não confirmada especificamente para
serviços portuários/frete), o parâmetro está ficando **estruturalmente
subestimado a cada ano que passa**, independentemente de o nível inicial
(2019) ter sido correto ou não. Isso pode ser um problema maior que o
nível inicial dos parâmetros — o hold-flat nominal, por si, introduz um
viés crescente.

## 9. Scenario matrix

Matriz conjunta, recalculada contrafactualmente sobre a série real
2019-2026 (`agregar_ipia_hrc_multi_ncm_mensal`, produção, sem
`congelado_df`):

| Scenario | D_porto | D_interno | Margin | Mean PPI (R$/t) | Median PPI | Mean Δ% | Max \|Δ%\| | Status changed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Low | 120 | 60 | 0% | 3.997,04 | 3.743,94 | -7,12% | 9,46% | 0 |
| **Current** | **210** | **140** | **3%** | **4.292,05** | **4.031,35** | **0%** | **0%** | **0** |
| Evidence Base | 210 | 140 | 3% | 4.292,05 | 4.031,35 | 0% | 0% | 0 |
| High | 320 | 260 | 6% | 4.660,86 | 4.392,57 | +8,94% | 12,30% | 0 |

"Evidence Base" coincide com "Current" porque **nenhuma evidência
encontrada nesta etapa justificou mover o centro** — só os limites
LOW/HIGH têm base analítica (Seções 4-6). Isso é deliberado, não um erro:
mover o centro sem evidência seria exatamente o que a Seção 29 do sprint
proíbe.

## 10. PPI impact

Ver Seção 9. Nenhum mês teve `publication_status` alterado em nenhum
cenário — os parâmetros afetam só o **valor**, nunca a cobertura (mesmo
padrão já observado no sprint de correção regulatória).

## 11. IPIA impact

**Ressalva obrigatória**: esta seção usa um preço doméstico
**hipotético constante** (R$4.800/t) só para testar o comportamento
mecânico do threshold — **não é o IPIA real** (que depende do lado
doméstico, fora do escopo desta calibração de custo).

| Scenario | IPIA hipotético médio | Threshold crossings vs. Current |
|---|---:|---:|
| Low | 128,14 | 4 |
| Current | 118,71 | 0 |
| Evidence Base | 118,71 | 0 |
| High | 108,65 | 5 |

## 12. Threshold impact

Nenhum cruzamento no cenário central (Evidence Base = Current). Nos
extremos (Low/High), o IPIA hipotético cruza o threshold 100 em 4-5 dos
meses testados — material, mas **só relevante se algum dos extremos
fosse adotado**, o que esta etapa não recomenda (Seção 17/§28).

## 13. Parameter materiality ranking

Isolamento one-at-a-time (cada parâmetro sozinho no extremo HIGH, os
outros em Current):

| Cenário | Mean Δ% PPI | Max \|Δ%\| |
|---|---:|---:|
| D_porto only (HIGH) | +2,80% | 4,36% |
| D_interno only (HIGH) | +3,06% | 4,76% |
| Margem only (HIGH) | +2,91% | 2,91% |

Elasticidade normalizada (por unidade de variação do próprio
parâmetro):

| Parâmetro | %Δparâmetro (até HIGH) | %ΔPPI médio | Elasticidade/sensibilidade |
|---|---:|---:|---:|
| D_porto | +52,4% | +2,80% | 0,0535 (%PPI por %ΔD_porto) |
| D_interno | +85,7% | +3,06% | 0,0357 (%PPI por %ΔD_interno) |
| Margem | +3,00 p.p. | +2,91% | **0,97% PPI por p.p. de margem** |

**Consistência com a análise anterior**: a sensibilidade de margem
encontrada aqui (0,97%/p.p.) bate quase exatamente com a já registrada em
`docs/METODOLOGIA.md` §9.10 (-4,85% para +5p.p. → 0,97%/p.p.) — mesma
ordem de grandeza, calculada de forma independente sobre toda a série
2019-2026 em vez de um único mês. **Ranking de materialidade por unidade
de incerteza plausível: margem > D_interno ≈ D_porto** — confirma a
conclusão original do contexto do sprint, agora com evidência multi-ano.

## 14. Decision matrix

| Criterion | D_porto | D_interno | Margem |
|---|---|---|---|
| Economic definition | Parcialmente clara (composição não confirmada) | Não tinha rota definida antes desta etapa; agora tem candidata | Ambígua — mistura markup/custo financeiro/overhead, nunca decomposta |
| Public evidence | Fraca (tarifas ad valorem/contêiner, breakbulk sob consulta) | Moderada (ANTT oficial, mas piso não é preço de mercado) | Nenhuma encontrada |
| Reproducibility | Baixa (sem fonte estruturada única) | Moderada (fórmula ANTT reproduzível, distância aproximada) | Não aplicável (sem fonte) |
| Historical treatment | Hold-flat nominal desde a pesquisa original, nunca calibrado | Idem | Idem |
| Materiality | Moderada (elasticidade 0,05) | Moderada (elasticidade 0,04) | **Alta** (0,97%/p.p.) |
| Complexity to fix | Baixa/Média (pesquisar contrato real com despachante) | Baixa (já há fórmula ANTT oficial) | Alta (exige decisão conceitual A vs. B antes de qualquer número) |

## 15. Recommendation per parameter

### D_PORTO
**D — INSUFFICIENT EVIDENCE.** Nenhuma fonte pública dá um R$/t
diretamente comparável para carga breakbulk siderúrgica. Próximo passo
realista: contato direto com despachante aduaneiro/terminal (já
recomendado na pesquisa metodológica original, nunca executado).

### D_INTERNO
**D — INSUFFICIENT EVIDENCE**, com ressalva: ao contrário de D_porto, já
existe uma fórmula pública reproduzível (ANTT) — o que falta é a decisão
de qual rota de referência adotar, dado que a composição real de UF de
entrada é muito mais dispersa (e mais dominada por Amazonas) do que
qualquer suposição prévia. Recomenda-se resolver primeiro a pergunta
"o que acontece com o HRC que entra por Manaus" antes de fixar uma rota.

### MARGIN
**B — RECALIBRATE**, mas o que precisa ser recalibrado primeiro é a
**definição conceitual** (A: Import Parity Cost vs. B: Offer/Trader
Price — Seção 6), não o número. Sem essa decisão, qualquer novo valor
numérico teria a mesma fragilidade do 3% atual: um número plausível sem
lastro. Alternativa igualmente defensável: **D — SEPARATE COST PPI FROM
OFFER PPI**, se a decisão for que os dois conceitos são úteis
separadamente — não escolhida aqui por ser uma mudança estrutural maior,
fora do escopo desta etapa de pesquisa.

## 16. Confidence

**LOW** para D_porto e D_interno (evidência pública insuficiente para
qualquer recalibração de nível). **MEDIUM** para a conclusão sobre
margem (a ausência de evidência pública é, em si, uma conclusão robusta,
mesmo sem apontar um número substituto). **HIGH** para o achado de
composição de porto (dado próprio do projeto, Comex Stat, direto) e para
a erosão real por IPCA (cálculo determinístico sobre série oficial do
BCB).

## Limitations

1. Nenhuma fonte estruturada única cobre D_porto para carga breakbulk —
   a faixa construída é uma ordem de grandeza, não uma medição.
2. Distâncias de rota são aproximações de conhecimento geográfico geral,
   não medidas por API de roteirização nesta etapa.
3. O destino econômico do HRC que entra via Manaus (maior UF) não foi
   determinado — pode ser consumo local (Zona Franca) ou redistribuição
   nacional, com implicações logísticas muito diferentes para D_interno.
4. Nenhum benchmark de margem de trading foi encontrado — a conclusão
   "sem evidência" é robusta, mas não permite propor um número
   alternativo.
5. O "IPIA hipotético" desta etapa usa preço doméstico constante — não
   deve ser confundido com o IPIA real, que depende do lado doméstico
   (PIA/IPP/Denton), fora do escopo desta calibração de custo.
6. A decomposição de margem em financial carrying cost/overhead/margem
   comercial é conceitual — nenhum valor numérico foi estimado para os
   componentes individuais.

## References

- `docs/METODOLOGIA.md` §9.8 (proveniência dos parâmetros do PPI), §9.9
  (histórico/justificativa da constância de D_porto/D_interno/margem),
  §9.10 (sensibilidade original, mês-base 2019-02).
- `references/manual_metodologico_indices_setoriais.md` §5.5 (origem dos
  valores atuais como "pontos de partida plausíveis para calibração").
- Resolução ANTT nº 6.084/2026 (piso mínimo de frete, Tabela A).
- Porto Itapoá — "Tabela de Preços e Serviços 2026" (armazenagem/
  movimentação, atualizada dez/2025).
- BCB/SGS série 433 (IPCA, variação % mensal).
- Comex Stat `/general` (dado próprio do projeto — distribuição por UF
  de entrada, 2022-2026).
