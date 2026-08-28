# Steel Indicator — Metodologia Oficial dos Índices

## Status do documento

**Versão metodológica:** `2.0-draft`  
**Status:** metodologia-alvo aprovada para implementação; **não publication-ready** enquanto os bloqueantes explicitamente listados neste documento permanecerem abertos.

Este documento é a referência metodológica oficial do repositório `steel-indicator`.

Ele consolida:

- o comportamento econômico já validado no projeto legado;
- os achados posteriores do guia operacional de coleta;
- as decisões metodológicas aprovadas para a reformulação;
- o escopo multiíndice do repositório.

Os arquivos em `references/` permanecem como evidência e pesquisa original. Quando houver conflito, achados posteriores **verificados em fontes reais** têm precedência sobre hipóteses anteriores.

---

# 1. Escopo oficial do repositório

O repositório implementará quatro produtos:

1. **IPIA-HRC** — Índice de Paridade de Importação do Aço para bobina laminada a quente.
2. **IPIA-Vergalhão** — Índice de Paridade de Importação do Aço para vergalhão.
3. **ICCS** — Índice de Condições de Crédito Setorial.
4. **ICS** — Índice Sintético de Condições Setoriais.

O **IIDB está fora do escopo** deste repositório.

A arquitetura é comum aos quatro produtos, mas a implementação é incremental:

1. infraestrutura compartilhada;
2. IPIA-HRC;
3. IPIA-Vergalhão;
4. ICCS;
5. ICS.

O objetivo é evitar pipelines isolados por índice.

---

# 2. Princípio central de migração

O sistema atual é **base a ser evoluída**, não descartada.

## 2.1 O que é preservado como baseline

Devem ser preservados durante a migração:

- fórmulas econômicas já implementadas, como baseline de comparação;
- coletores existentes, até serem separados em módulos;
- NCMs já pesquisadas, até validação histórica contra o catálogo e fontes oficiais;
- dados curados das siderúrgicas;
- lógica de preço doméstico, até evolução metodológica explícita;
- taxonomia `OBSERVADO / CALCULADO / ESTIMADO / PROXY`;
- `reference_period`;
- tratamento de baixa liquidez, até decisão metodológica nova;
- reporting existente;
- ADRs;
- autotestes/golden tests;
- compatibilidade externa da CLI durante a migração.

A estrutura monolítica do código **não precisa ser preservada**.

## 2.2 Legacy behavior is evidence, not authority

Os testes de characterization e o `--selftest` registram o comportamento legado.

Quando esta metodologia nova divergir deliberadamente do comportamento antigo:

1. a divergência deve ser explícita;
2. deve existir uma spec/ADR quando necessário;
3. novos testes devem validar a metodologia nova;
4. a série legacy deve ser mantida temporariamente para comparação quando isso ajudar no diagnóstico;
5. o resultado novo não deve ser forçado a reproduzir o antigo.

---

# 3. Princípios comuns aos índices

## 3.1 Reprodutibilidade

Todo número publicado deve poder ser reconstruído a partir de:

- versão da metodologia;
- código utilizado;
- dados de entrada;
- parâmetros vigentes no período;
- data de coleta;
- `reference_period`;
- provenance;
- vintage;
- regras de transformação.

## 3.2 Janela de referência congelada

Quando um índice composto usar padronização por z-score, a janela de referência deve ser fixa.

A referência inicial continua:

```text
2013-01 a 2019-12
```

Para uma variável \(x_{i,t}\):

\[
z_{i,t} =
\frac{x_{i,t} - \mu_i^{ref}}
{\sigma_i^{ref}}
\]

com truncamento:

\[
z_{i,t} \in [-3, +3]
\]

A chegada de novos meses não pode reescrever o passado.

Se uma série não possuir histórico suficiente nessa janela, o tratamento deve ser documentado antes de publicação.

## 3.3 Escala de índices sintéticos

Para ICCS e ICS, quando aplicável:

\[
Indice_t = 50 + 10 \times z_t^{composto}
\]

truncado em:

```text
[0, 100]
```

Interpretação:

- 50 = média da janela de referência;
- acima de 50 = condição melhor que a média histórica;
- abaixo de 50 = condição pior que a média histórica.

Essa regra **não se aplica ao IPIA**, cuja escala econômica é centrada em 100.

## 3.4 Pesos

Pesos metodológicos devem ser:

- teóricos;
- documentados;
- fixos entre revisões formais.

PCA é ferramenta de validação, não de definição de pesos.

## 3.5 Cobertura e dados faltantes

Quando uma variável estiver ausente:

- redistribuir o peso proporcionalmente dentro da estrutura definida;
- publicar a cobertura;
- não inventar o dado faltante;
- abaixo de 60% de cobertura, o índice não deve ser publicado naquele período, salvo decisão metodológica explícita específica ao índice.

## 3.6 Ajuste sazonal

Séries de fluxo podem receber ajuste sazonal quando houver justificativa estatística e econômica.

Séries de estoque, razões e taxas não devem ser ajustadas automaticamente.

A implementação deverá registrar:

- série bruta;
- método de ajuste;
- parâmetros;
- série ajustada;
- versão do procedimento.

## 3.7 Revisões e vintages

Toda coleta persistente deve registrar no mínimo:

- `collected_at`;
- `reference_period`;
- `source_id`;
- `n_obs`;
- intervalo de observações;
- status de validação;
- hash do conteúdo;
- versão de metodologia;
- versão de código.

Revisão de fonte deve gerar novo vintage.

O dado antigo não deve ser sobrescrito silenciosamente.

---

# 4. Proveniência

A proveniência possui dois eixos independentes.

## 4.1 Nível de processamento

### OBSERVADO
Valor diretamente publicado por uma fonte primária, sem transformação econômica relevante.

### CALCULADO
Valor derivado por operação determinística sobre dados observados.

Exemplos:

- valor unitário = valor / peso;
- preço médio ponderado;
- taxa de penetração calculada.

### ESTIMADO
Valor resultante de interpolação, projeção, hold-flat, benchmarking ou outra técnica que complete informação não observada diretamente naquele período.

### PROXY
Indica incompatibilidade entre o escopo real da fonte e o rótulo conceitual desejado.

`PROXY` é ortogonal a `OBSERVADO / CALCULADO / ESTIMADO`.

Um valor pode ser:

```text
CALCULADO + PROXY
ESTIMADO + PROXY
OBSERVADO sem proxy
```

## 4.2 Reference period

Cada variável deve carregar seu próprio `reference_period`.

Não se deve usar um rótulo genérico como “atual” quando variáveis possuem defasagens diferentes.

Quando duas variáveis são combinadas matematicamente, elas devem ser reconciliadas no mesmo período de referência.

---

# 5. Engenharia de fontes

## 5.1 Structured-data-first

Ordem de preferência para produção:

1. API;
2. CSV/XLSX;
3. tabela estruturada oficial;
4. PDF apenas como último recurso.

Quando uma informação relevante existir apenas em PDF:

```text
PDF
→ curadoria/validação
→ artefato estruturado versionado
→ pipeline
```

Evitar dependência recorrente de extração de PDF quando houver alternativa estruturada.

## 5.2 Status de validação

Toda fonte/identificador deve ser classificada como:

### VERIFICADO
A fonte foi executada e o resultado conferido contra evidência oficial.

### DOCUMENTADO
A fonte/identificador foi confirmado em documentação ou fonte oficial, mas não executado no ambiente atual.

### A CONFIRMAR
A evidência ainda não é suficiente.

Nenhuma série deve ser promovida silenciosamente de “a confirmar” para “verificada”.

---

# 6. Regras específicas de coleta

## 6.1 BCB SGS

Nunca usar:

```text
/dados/ultimos/N
```

para ingestão ou validação.

Usar consultas com janela explícita por data.

O coletor deve:

- reprocessar janela móvel adequada para capturar revisões;
- validar datas retornadas;
- validar número de observações;
- registrar vintage;
- validar rótulo e conceito econômico da série.

## 6.2 Comex Stat

A ingestão deve usar o endpoint oficial `/general` via POST estruturado.

Não somar cegamente todos os códigos retornados por `/tables/ncm`.

A validade da NCM deve ser resolvida por período histórico.

Uma cesta pode mudar ao longo do tempo em função de:

- criação/extinção de códigos;
- desdobramentos;
- reclassificações;
- mudanças de TEC.

## 6.3 Aço Brasil

Priorizar o Excel estruturado oficial.

PDF pode ser usado para:

- documentação;
- conferência;
- validação do valor oficial;
- fallback manual quando não houver alternativa.

A fonte deve ser tratada como publicação setorial estruturada, não como scraping de PDF por padrão.

---

# 7. Backfill histórico

Objetivo geral:

> reconstruir a maior série historicamente comparável possível.

Regras:

- 2020–presente é o mínimo obrigatório quando viável, não o limite;
- retroceder além de 2020 sempre que as fontes e regras forem comparáveis;
- nunca aplicar parâmetros atuais retroativamente;
- respeitar tarifa, AFRMM, antidumping, cota e demais regras vigentes em cada período;
- registrar mudanças de classificação ou metodologia;
- não preencher lacunas silenciosamente apenas para produzir uma série contínua;
- preferir uma série mais curta e defensável a uma série longa construída sobre hipóteses frágeis.

---

# 8. IPIA — visão comum

O IPIA mede a relação entre:

- preço doméstico do produto;
- custo econômico de importar o mesmo produto e colocá-lo no mercado brasileiro.

Para cada família \(p\):

\[
IPIA_{p,t} =
\left(
\frac{P^{dom}_{p,t}}
{PPI_{p,t}}
\right)
\times 100
\]

Interpretação:

- **IPIA > 100**: preço doméstico acima da paridade;
- **IPIA < 100**: preço doméstico abaixo da paridade;
- **IPIA = 100**: equilíbrio entre preço doméstico e custo de importação.

O mesmo motor deve atender:

- HRC;
- vergalhão.

As configurações específicas ficam fora da função econômica genérica.

---

# 9. IPIA — lado importado

## 9.1 Preço realizado de importação

A fonte oficial é o Comex Stat.

Para cada produto, origem, NCM e período:

\[
P^{FOB}_{t}
=
\frac{Valor\ FOB_t}
{Peso\ Liquido_t}
\]

convertido para US$/t.

O objetivo não é reproduzir uma cotação teórica internacional, e sim medir o preço efetivamente realizado na fronteira brasileira.

## 9.2 Frete e seguro

Quando disponíveis na fonte:

\[
Frete_t =
\frac{Valor\ Frete_t}{Peso_t}
\]

\[
Seguro_t =
\frac{Valor\ Seguro_t}{Peso_t}
\]

Esses valores observados têm precedência sobre parâmetros fixos aproximados.

A disponibilidade histórica efetiva das métricas deve ser validada por produto/NCM.

## 9.3 CIF

\[
CIF_t^{US\$/t}
=
P_t^{FOB}
+
Frete_t
+
Seguro_t
\]

## 9.4 Custo de importação / PPI

Forma conceitual:

\[
PPI_t =
[
CIF_t \times FX_t
+
II_t
+
AFRMM_t
+
AD_t
+
D_{porto,t}
+
D_{interno,t}
]
\times
(1 + margem_t)
\]

onde:

- `FX_t` = câmbio de referência do período;
- `II_t` = imposto de importação vigente;
- `AFRMM_t` = regra vigente no período;
- `AD_t` = antidumping específico aplicável no período;
- `D_porto` = despesas portuárias;
- `D_interno` = frete interno de referência;
- `margem` = margem do importador, quando aplicável.

## 9.5 Parâmetros históricos

A implementação nova deve usar parâmetros **time-varying**.

Não é permitido aplicar:

- alíquota atual de II;
- AFRMM atual;
- antidumping atual;
- cota atual;
- majoração atual;

a períodos históricos onde a regra não estava vigente.

A arquitetura deve permitir tabelas de vigência com:

```text
valid_from
valid_to
product_family
ncm
parameter
value
source
validation_status
```

### 9.5.1 Janela publication-grade do IPIA-HRC (ADR 0009)

Para IPIA-HRC, a investigação de II/TEC, AFRMM e antidumping (2012–presente)
concluiu que apenas **2022-04-01 → presente** tem todos os parâmetros de
internação confirmados com evidência suficiente para publicação oficial.

O período **2012-01-01 → 2022-03-31** permanece **historical experimental**
— nunca concatenado silenciosamente à série oficial — porque a alíquota de
II individual de 9 dos 13 NCMs da cesta não está comprovada nesse intervalo
(apenas uma faixa de 10%–14% é conhecida). Ver `docs/adr/0009-*` e
`docs/research/hrc_import_policy_history.md` para a evidência completa.

### 9.5.2 Agregação bottom-up multi-NCM e publication policy (ADR 0009)

Decisão Level 3 aprovada para resolver a limitação de representatividade
entre NCMs (adendo Stage E6 do ADR 0009): a agregação dos 13 NCMs de
`NCM_BOBINA_QUENTE` é **bottom-up**, por `(mês, NCM, país)` — II resolvido
por NCM, AFRMM por mês, antidumping por país, **todos aplicados antes de
qualquer soma** — e só então o PPI resultante é ponderado pelo volume
(KG) efetivamente importado em cada grupo. Nunca: NCM representativo único,
média simples de alíquotas entre NCMs, alíquota única sobre um CIF já
combinado, ou cesta fixa tipo Laspeyres.

Duas políticas de publicação, nunca misturadas na mesma série oficial:

- **PUBLICATION_GRADE** (`>= 2022-04-01`): só calcula o mês se
  `known_policy_kg == total_kg` (dentro de tolerância numérica). Qualquer
  volume observado com política desconhecida (ex.: cota GECEX 929/2026
  com consumo não rastreado) torna o mês inteiro `UNKNOWN`
  (PPI/IPIA = NaN), **sem redistribuir peso** entre os grupos conhecidos.
- **EXPERIMENTAL** (`2012-01-01` a `2022-03-31`): calculável somente se
  `coverage >= 60%` **e** o range de incerteza do II não confirmado —
  aplicando a faixa documentada 10%–14% (nunca 12% como ponto certo) só à
  parcela desconhecida do volume — for `<= 2%`. Quando calculável, o ponto
  estimado usa somente os grupos conhecidos, com peso redistribuído
  proporcionalmente entre eles; a faixa 10%–14% nunca vira o valor do
  ponto central, só o teste de elegibilidade.

Implementado em `agregar_ipia_hrc_multi_ncm_mensal()`/
`custo_importacao_bottom_up_mensal()` (`src/indices_setoriais.py`). Não
conectado a `--selftest`/CLI/relatório nesta stage — mesmo status de
"peça de cálculo interna, testada" que `calcular_ipia_hrc_v2()`. Evidência
quantitativa (distribuição de coverage, sensibilidade econômica do II
desconhecido, teste de limiares candidatos) em
`docs/research/hrc_import_policy_history.md`.

## 9.6 Câmbio (FX)

**Convenção oficial (ADR 0014, motor V2 — `agregar_ipia_hrc_multi_ncm_mensal`,
alimenta `ipia_hrc_v2_official.csv`/`ipia_hrc_v2_provisional.csv`):**

```
FX_t = (1 / N_t) · Σ FX_d,  para todo dia útil d com cotação válida cujo mês-calendário é t
```

- **Fonte:** BCB/SGS, série `1` — "Taxa de câmbio - Livre - Dólar americano
  (venda) - diário" (PTAX venda de fechamento — confirmado ao vivo contra
  o endpoint oficial de PTAX; o boletim de fechamento já é, por
  metodologia do BCB desde a Resolução BCB nº 45/2020, a média aritmética
  dos 4 boletins diários).
- **Frequência da fonte:** diária (dias úteis).
- **Moeda:** BRL por USD, venda (não compra, não paralela).
- **Agregação mensal:** média aritmética simples das observações diárias
  válidas cujo mês-calendário é exatamente `t` — implementada em
  `indices_setoriais.calcular_fx_mensal(cambio_diario, meses_idx)`, a
  única função que produz o câmbio mensal do motor V2. Nunca faz
  forward-fill entre meses.
- **Meses sem nenhuma observação diária válida:** `calcular_fx_mensal`
  levanta `ValueError` explícito (fail-fast) — nunca herda
  silenciosamente o câmbio de outro mês.
- **Correspondência temporal com o Comex Stat:** o Comex Stat define o
  mês de uma importação pela data de **desembaraço aduaneiro** (confirmado
  no FAQ oficial do MDIC), evento que ocorre dentro do próprio mês `t` —
  a média mensal cobre exatamente esse período, ao contrário da convenção
  anterior (ver histórico abaixo).
- **Limite operacional da fonte:** a API do BCB/SGS rejeita (HTTP 406)
  janelas de consulta de série diária maiores que ~10 anos; a coleta é
  particionada em blocos de até 10 anos e concatenada
  (`_pipeline_cambio_historico_seguro`). Nunca usa `/dados/ultimos/N`
  (proibido pelo projeto — ver `docs/data-sources.md`).
- **Nível de proveniência:** `OBSERVADO` — valor direto da fonte;
  `calcular_fx_mensal` é uma média aritmética determinística sobre
  observado, sem interpolação/encadeamento/suavização (não muda a
  classificação `OBSERVADO`, na mesma lógica de FOB/frete/seguro
  observados via razão em §9.8).
- **Limitação (câmbio observado ≠ câmbio efetivamente contratado por
  cada importador):** nenhuma convenção baseada em PTAX/SGS reproduz
  necessariamente a taxa efetiva de uma empresa específica — hedge,
  forward, fechamento antecipado ou outras condições de tesouraria podem
  divergir da PTAX. O IPIA-HRC estima uma **paridade de mercado
  reprodutível** a partir de fonte pública e auditável, não a tesouraria
  de nenhuma empresa. Isso não é uma falha do índice, é a diferença entre
  um benchmark reproduzível e um custo individual.

**Histórico da convenção (não mais vigente para o motor V2):** até a ADR
0014, o motor V2 usava `sgs(...).reindex(<índice mensal>, method="ffill")`,
que fazia `FX_t` corresponder à última cotação PTAX venda observada **antes
do início** do mês `t` — na prática, o fechamento do mês **anterior**, não
uma média nem o fechamento do próprio mês `t`. Esse comportamento nunca foi
uma decisão metodológica deliberada (efeito colateral de `freq="MS"` +
`ffill`; ver `docs/validation/fx_convention_validation.md` e ADR 0014 para
a investigação completa e a decisão). **O motor legado V1**
(`calcular_ipia_mensal`, `custo_importacao_detalhado_mensal` — usado por
`--selftest` e pelo PDF antigo, nunca pela série oficial/provisional)
**permanece deliberadamente nessa convenção antiga** — é referência
histórica congelada, não a série publicada.

## 9.7 Viés de valor unitário (unit value bias)

O preço FOB de importação usado no PPI (§9.1) é, por construção, um **valor
unitário observado** (`Valor FOB_t / Peso Líquido_t`), não uma cotação de
preço em sentido estrito (price assessment). Essa distinção é reconhecida
na literatura de índices de preços de comércio exterior — ver *Export and
Import Price Index Manual* (IMF/ILO/OECD/Eurostat/UN/World Bank, 2009),
que trata unit values como um substituto imperfeito de um índice de preço
puro justamente pela possibilidade de viés de composição.

**Por que um valor unitário não é equivalente a um índice puro de preço:**
mesmo calculado em granularidade `mês × NCM (8 dígitos) × país de origem`
(§9.5.2), uma única posição de NCM ainda pode agrupar produtos com
espessura, largura, grau do aço, acabamento e condições comerciais
diferentes. Uma variação no FOB/kg observado em um mês pode refletir:

1. uma mudança real no preço pago por um produto comparável; **ou**
2. uma mudança na composição/mix de qualidade dentro da própria NCM (por
   exemplo, substituição de um fornecedor/especificação por outro), sem
   que o preço de um produto comparável tenha mudado.

**O que a agregação bottom-up (mês × NCM × país, §9.5.2) resolve e o que
não resolve:** ela reduz o viés de composição *entre* categorias distintas
(não mistura, por exemplo, NCMs com produtos claramente diferentes num
único número, nem aplica uma alíquota de política comercial incorreta a um
grupo heterogêneo). Ela **não elimina** o viés de composição *dentro* de
uma mesma NCM × país × mês, porque o Comex Stat não expõe especificação
técnica (espessura/largura/grau/acabamento) abaixo do nível de NCM.

**Implicação para a interpretação do IPIA-HRC:** variações mês a mês do
PPI — em particular movimentos atípicos que não coincidem com movimentos
de preço internacional conhecidos — podem, em parte, refletir mudança de
mix de produto importado, não apenas variação de preço. Isso é uma
limitação de dado, não um erro de cálculo, e não invalida o uso do Comex
Stat como fonte: o valor unitário aduaneiro é o preço efetivamente
realizado na fronteira brasileira, o que tem valor próprio distinto de uma
cotação teórica de agência (`references/manual_metodologico_indices_setoriais.md`
§5.1). Nenhuma conclusão empírica sobre a magnitude desse viés é feita
aqui — isso exige validação contra um benchmark externo independente
(CRU/Fastmarkets/Kallanish ou equivalente), explicitamente fora do escopo
desta etapa (ver §26 e roadmap).

**Esta etapa não altera a fórmula do PPI nem substitui o Comex Stat por
causa deste gap.** O objetivo aqui é exclusivamente reconhecer e
documentar a limitação.

## 9.8 Classificação de proveniência dos parâmetros do PPI

Auditoria completa dos componentes do PPI (§9.4), com a classificação de
nível já definida em §4 (`OBSERVADO`/`CALCULADO`/`ESTIMADO`, eixo `PROXY`
ortogonal). Nenhum parâmetro novo é introduzido; esta tabela apenas torna
explícita a classificação de parâmetros que já existiam no código.

| Parâmetro | Fórmula/origem atual | Fonte | Nível | Varia no tempo? | Granularidade | Vigência | Hipótese/observação |
|---|---|---|---|---|---|---|---|
| FOB | `ValorFOB_t / PesoLíquido_t` | Comex Stat `/general` | CALCULADO (valor unitário sobre observado — ver §9.7 para o viés associado) | Sim, por mês | mês × NCM × país | Sem vigência (recalculado a cada coleta) | Unit value, não price assessment — §9.7 |
| Frete | `ValorFrete_t / Peso_t` | Comex Stat `/general` | CALCULADO | Sim, por mês, quando disponível na fonte | mês × NCM × país | Sem vigência | Precedência sobre parâmetro fixo aproximado quando observado (§9.2) |
| Seguro | `ValorSeguro_t / Peso_t` | Comex Stat `/general` | CALCULADO | Sim, por mês, quando disponível na fonte | mês × NCM × país | Sem vigência | Idem frete |
| Câmbio (FX) | PTAX venda, média mensal das observações diárias válidas (ADR 0014; motor V1 legado permanece na convenção antiga — última cotação antes do mês) | BCB/SGS série 1 | OBSERVADO | Sim, mensal (derivado de diário) | Mensal (mesmo câmbio para todos os NCMs/países no mês) | Sem vigência (série contínua) | Ver §9.6 para a regra completa |
| II (Imposto de Importação) | `resolver_ii(ncm, data)` | Legislação/TEC (Res. CAMEX/GECEX) | OBSERVADO | Sim, por NCM e por data (`valid_from`/`valid_to`) | NCM × período de vigência | `2022-04-01→presente`: PUBLICATION_GRADE; `2012-01-01→2022-03-31`: EXPERIMENTAL (9/13 NCMs não comprovados); fora dessa janela: UNKNOWN | Nunca usa alíquota atual como fallback para período sem regra comprovada (§9.5.1) |
| AFRMM | `resolver_afrmm(data)` | Lei 10.893/2004 (25%) até 2022-03-24; Lei 14.301/2022 (8%) a partir de 2022-03-25 | OBSERVADO | Sim, por data (`valid_from`/`valid_to`) | Nacional, por período de vigência | Vigência legal explícita (duas faixas documentadas) | Aplicado somente sobre o frete (`Frete_USD × Câmbio × alíquota`), nunca sobre o CIF completo |
| Antidumping | `resolver_antidumping(origin, data, exporter)` | Resoluções GECEX/CAMEX por origem/exportador | OBSERVADO | Sim, por origem/exportador/data (`valid_from`/`valid_to`) | País de origem × exportador × período | Medidas específicas documentadas (ex.: suspensão China/Rússia 2018-01–2020-01); usa sempre `effective_value`, nunca `nominal_value`, no custo | `nominal_value` preservado só como proveniência informativa |
| D_porto (despesas portuárias) | Constante `ParamsIPIA.despesas_porto_rs_t` | Ponto de partida da pesquisa original (`references/manual_metodologico_indices_setoriais.md` §5.5) | **ESTIMADO** (hold-flat; nunca calibrado) | Não — constante única desde a origem do parâmetro | Nacional, sem distinção por período | Sem vigência — mesma constante aplicada retroativamente a toda a série | R$ 210/t. A pesquisa original identifica explicitamente este valor como "ponto de partida plausível para calibração, não medição", a ser calibrado com despachantes antes do primeiro release — calibração nunca realizada (ver §26) |
| D_interno (frete interno porto→cliente) | Constante `ParamsIPIA.frete_interno_rs_t` | Idem acima | **ESTIMADO** (hold-flat; nunca calibrado) | Não | Nacional, rota de referência não publicada | Sem vigência | R$ 140/t. Mesma ressalva de calibração pendente; rota de referência assumida não está documentada |
| Margem do importador | Constante `ParamsIPIA.margem_importador` | Idem acima | **ESTIMADO** (hold-flat; nunca calibrado) | Não | Nacional | Sem vigência | 3%. Pesquisa original: "zere se quiser medir custo puro em vez de preço ofertado" — decisão de manter em 3% nunca formalizada além do valor default do código |

**Nota sobre a coluna Nível:** FOB/Frete/Seguro são `CALCULADO` (razão
determinística sobre um valor observado, sem estimativa) e não `OBSERVADO`
puro, seguindo a definição de §4 — o valor unitário em si não deixa de
carregar o viés de composição descrito em §9.7, que é uma propriedade do
dado de origem, não do rótulo de proveniência.

## 9.9 D_porto, D_interno e margem — histórico e justificativa da constância

Investigação específica pedida para estes três parâmetros:

- **Valores em uso:** R$ 210/t (D_porto), R$ 140/t (D_interno), 3% (margem)
  — `ParamsIPIA`, `src/indices_setoriais.py`.
- **Origem:** os três vêm, sem alteração, da pesquisa metodológica original
  (`references/manual_metodologico_indices_setoriais.md` §5.5), que os
  apresenta explicitamente como *pontos de partida plausíveis para
  calibração*, não como medições.
- **Desde quando estão em uso:** desde a implementação do motor de cálculo
  do PPI (não há registro de nenhuma revisão de valor no histórico do
  repositório).
- **São fixos?** Sim — constantes escalares únicas aplicadas a toda a
  série histórica e a toda a série futura até serem alteradas
  manualmente. Não são corrigidos por inflação, não têm vigência
  (`valid_from`/`valid_to`), não variam por mês/ano.
- **Existe fonte documentada?** Não além da pesquisa original citada
  acima. Nenhum ADR ou spec formaliza uma calibração.
- **Existem testes?** Há teste de regressão que trava os valores atuais
  como constantes conhecidas (`tests/unit/test_ppi_parametros_e_cambio.py`,
  adicionado nesta etapa) — não havia nenhum antes.
- **Por que permanecem constantes nesta etapa:** o próprio código já
  reconhece a limitação (`ParamsIPIA.__doc__`: "O único bloco subjetivo do
  índice — publique estes números junto com o índice e revise uma vez por
  ano"). Alterar os valores sem a calibração empírica pedida pela pesquisa
  original (contato com despachantes aduaneiros) seria trocar um
  placeholder não medido por outro placeholder não medido, sem ganho de
  veracidade — e mudaria toda a série histórica publicada sem justificativa
  metodológica (proibido por este documento). Portanto: apenas
  classificação e documentação nesta etapa, sem mudança de valor.
- **Impacto no PPI (materialidade):** ver §9.10 — dos três, a margem tem o
  maior impacto por ponto percentual de choque; D_porto e D_interno têm
  impacto comparativamente pequeno.
- **Existe fonte melhor já presente no projeto?** Não identificada nesta
  auditoria.
- **Seria necessário construir uma série temporal?** Nenhuma variação
  documentada ao longo do tempo foi encontrada para estes três parâmetros
  — não há evidência de que precisem ser time-varying (ao contrário de
  II/AFRMM/antidumping, que têm mudanças legais documentadas). Se uma
  fonte de custo portuário/frete rodoviário/margem de trading ao longo do
  tempo for identificada no futuro, a decisão de torná-los time-varying é
  Level 3 (muda valores publicados) e requer spec/ADR próprios.
- **O problema exige mudança metodológica ou apenas documentação?**
  Apenas documentação nesta etapa (classificação `ESTIMADO` + registro da
  calibração pendente). A calibração em si (contato com despachantes,
  conforme a pesquisa original já recomendava) é trabalho de próxima etapa,
  fora do escopo definido aqui.

## 9.10 Sensibilidade dos parâmetros estimados

Uma análise de sensibilidade sobre os parâmetros do PPI — incluindo os três
classificados como `ESTIMADO` em §9.8 — já foi executada em
`docs/validation/ipia_hrc_v2_final_validation.md` §11 (Stage G3), sobre o
mês-base 2019-02 (PPI = R$ 3.107,39/t), por simulação pura (nenhum
parâmetro default alterado):

| Choque | ΔPPI | ΔIPIA |
|---|---|---|
| FX ±10% | ±8,84% | ∓8,84% |
| FOB ±10% | ±7,96% | ∓7,96% |
| Margem do importador +5pp | +4,85% | -4,85% |
| Frete internacional +20% | +1,72% | -1,72% |
| D_porto (custo portuário) +20% | +1,39% | -1,39% |
| D_interno (frete interno) +20% | +0,93% | -0,93% |

**Leitura:** todos os sinais são economicamente corretos (choque de custo
positivo → PPI sobe → IPIA cai). Ordenação de materialidade: **FX > FOB >
margem > frete internacional > D_porto > D_interno**. Isso distingue, entre
os parâmetros `ESTIMADO`, hipóteses estruturalmente importantes (margem,
com impacto de quase 5% do IPIA para um choque de 5 pontos percentuais) de
hipóteses pouco materiais (D_porto e D_interno, com impacto abaixo de 1,5%
mesmo para um choque de 20%). Uma futura calibração de D_porto/D_interno
tem, portanto, prioridade menor que uma eventual revisão da margem do
importador — mas ambas seguem sem calibração formal nesta etapa (§9.9).
Esta análise não foi refeita nesta etapa por já cobrir exatamente os
parâmetros e o formato de choque pedidos; nenhum novo cenário foi
necessário.

---

# 10. NCMs do IPIA

## 10.1 Regra geral

Cada família possui sua própria cesta.

A cesta deve ser:

- versionada;
- validada contra fonte oficial;
- historicamente consciente;
- auditável.

## 10.2 IPIA-HRC

A cesta legacy de HRC é preservada como baseline de pesquisa.

Antes de publicação V2:

- cruzar com o catálogo;
- validar contra NCMs vigentes;
- mapear mudanças históricas;
- excluir códigos extintos fora de sua vigência.

## 10.3 IPIA-Vergalhão

A cesta deve ser definida em spec própria.

Não reutilizar automaticamente NCMs de HRC ou agregados de “longos”.

A família deve ter definição de produto própria e comparabilidade econômica explícita.

---

# 11. Tratamento de baixa liquidez no lado importado

O tratamento atual de baixa liquidez permanece como baseline até revisão metodológica específica.

Princípios preservados:

- volume econômico é mais informativo que quantidade de registros;
- observações brutas não devem ser sobrescritas;
- qualquer suavização deve produzir coluna derivada;
- meses interpolados/suavizados devem manter provenance explícita.

Antes de alterar:

- limiar de volume;
- função de peso;
- janela de suavização;
- método de interpolação;

deve existir análise metodológica específica por produto.

HRC e vergalhão podem demandar limiares diferentes.

## 11.1 IPIA-HRC V2 — baixa liquidez: NO THRESHOLD / DISCLOSURE ONLY (Stage G4C, ADR 0013)

O tratamento acima (§11) é o **baseline legado** (`VOLUME_MINIMO_T=5000`,
`suavizar_preco_importacao`) — pertence à metodologia V1 (CIF único
combinado, peso de confiabilidade contínuo) e **não é herdado pelo
IPIA-HRC V2** (agregador bottom-up multi-NCM).

**Decisão final (Level 3 aprovada):** IPIA-HRC V2 não adota nenhum
threshold binário de baixa liquidez neste momento. Nem `liquidity_status`,
nem `low_liquidity` booleano, nem `threshold_t`, nem limiar por percentil
foram criados. `total_kg` continua publicado como informação observável,
sem transformação. `ipia_hrc_v2`, `ppi_rs_t` e `publication_status` nunca
dependem de volume — só de `policy_coverage`/`ppi_uncertainty_range_pct`
(regra já aprovada, ADR 0009). Nenhuma suavização, interpolação, exclusão
ou UNKNOWN por volume é aplicada.

**Por que o percentil 10 do Stage G3 não virou contrato de produção:**
`calc_vol["total_kg"].quantile(0.10)` (`scripts/validar_ipia_hrc_v2_final.py`)
foi útil como ferramenta EXPLORATÓRIA para perguntar "os extremos de IPIA
coincidem com baixa liquidez?" durante a validação — e a resposta
empírica foi não, de forma conclusiva o suficiente para não justificar
ação: relação volume×volatilidade fraca (correlação ≈ -0,19), e nenhum
outlier investigado foi classificado como economicamente indefensável (0
casos "D - SUSPICIOUS", todos "A" ou "B"). Mas o percentil em si nunca
teve aprovação metodológica como regra de PUBLICAÇÃO, e tem um defeito
estrutural que o desqualifica mesmo que fosse aprovado: é relativo à
amostra corrente — o mesmo mês histórico poderia mudar de classificação
conforme novos meses entrassem na série, mesmo com seu `total_kg`
inalterado. Ferramenta de análise válida; nunca virou contrato.

**Disclosure obrigatório** (toda publicação do IPIA-HRC deve incluir):

> PT-BR: "Meses com menor volume importado podem apresentar maior
> sensibilidade à composição das operações observadas. O IPIA-HRC
> preserva os valores observados e não aplica suavização ou exclusão
> automática baseada em volume."
>
> EN: "Months with lower import volume may show greater sensitivity to
> the composition of observed transactions. IPIA-HRC preserves observed
> values and does not apply automatic smoothing or exclusion based on
> volume."

**Reabertura futura:** uma regra quantitativa de liquidez (threshold,
suavização, ou exclusão) exigirá nova decisão metodológica Level 3,
fundamentada em evidência específica (não a reutilização silenciosa do
percentil exploratório do Stage G3 nem do `VOLUME_MINIMO_T` legado).

---

# 12. IPIA-HRC — preço doméstico

## 12.1 Regra-alvo V1

A metodologia pública inicial é:

```text
âncora trimestral de nível
+
movimento mensal por índice de preços
```

A fonte deve ser a mais granular e comparável disponível.

## 12.2 Candidatas iniciais

Começar investigando:

- CSN;
- Usiminas.

Avaliar:

- Gerdau;
- outras produtoras;

pelos mesmos critérios de qualidade.

Nenhuma empresa entra obrigatoriamente apenas por ser grande ou estar citada em pesquisa anterior.

## 12.3 Critério de inclusão

Uma empresa pode compor a âncora quando:

- receita e volume se referem ao mesmo período;
- receita e volume cobrem o mesmo mercado;
- o escopo do produto é suficientemente homogêneo;
- a informação é estruturada ou curada de forma reprodutível;
- a unidade econômica é comparável às demais empresas.

## 12.4 Preço realizado

Quando a informação permitir:

\[
P^{dom}_{t}
=
\frac{\sum_i Receita_{i,t}}
{\sum_i Volume_{i,t}}
\]

A ponderação deve ocorrer por volume econômico, não por média simples entre empresas.

## 12.5 Proxy

Se receita/volume representar um segmento amplo de aço:

```text
tipo = PROXY
```

Nunca rotular como preço puro de HRC.

O relatório e os datasets devem deixar explícitos:

- escopo real da fonte;
- nível de processamento;
- se existe proxy.

## 12.6 Encadeamento mensal

O IPP utilizado deve ser o mais específico disponível e metodologicamente apropriado para HRC.

Prioridade:

1. série de preço específica ao produto, se disponível e validada;
2. série de preço mais próxima ao produto;
3. IPP de siderurgia/metalurgia como fallback documentado.

## 12.7 Temporal benchmarking

O encadeamento simples entre âncoras trimestrais é baseline, não solução definitiva.

A implementação V2 deve avaliar técnicas formais de temporal benchmarking quando:

- houver saltos artificiais na fronteira de trimestres;
- a soma/média mensal não reconciliar adequadamente com as âncoras;
- o método simples introduzir distorção visível.

Qualquer técnica nova deve:

- preservar as âncoras observadas;
- não usar informação futura indevidamente;
- ser determinística;
- gerar provenance `ESTIMADO` nos pontos inferidos.

## 12.8 Hierarquia futura de fontes

Se surgir fonte de transações domésticas efetivas de HRC:

```text
transações observadas
> fonte pública produto-específica
> CVM + IPP
> proxy de segmento
```

Uma fonte superior pode substituir a V1 mediante spec/ADR.

## 12.9 Domestic Price V2 — implementação (Stage E8)

Implementado em `preco_domestico_hrc_mensal_v2()`/`ancora_domestica_
ponderada_v2()`/`carregar_preco_domestico_trimestral_v2()`/
`ibge_sidra_ipp_siderurgia()` (`src/indices_setoriais.py`), caminho
explícito e paralelo ao legado (`carregar_preco_domestico_trimestral`/
`preco_domestico_ponderado`/`encadear_preco_domestico_mensal`, inalterados
— a expansão mensal reaproveita `encadear_preco_domestico_mensal` sem
modificação). Não conectado a `--selftest`/CLI/relatório nesta stage.

- **§12.3/12.4** — a âncora usa `Σ receita / Σ volume` entre empresas
  qualificadas (nunca média simples). Uma linha do CSV curado é
  desqualificada via `tipo = "incompativel_receita_volume"` quando receita
  e volume não cobrem o mesmo universo econômico — exclusão declarada pelo
  curador linha a linha, não inferida numericamente, e nunca redistribuída
  em silêncio. Hoje nenhuma linha real usa esse tipo (Usiminas/CSN são
  compatíveis).
- **Gerdau (§12.2)** avaliada e **não incluída**: os segmentos públicos da
  Gerdau no Brasil reportam aço longo, não HRC/planos — receita e volume
  não são compatíveis com a cesta HRC hoje. Não há allowlist de nomes de
  empresa no código: uma fonte futura comprovadamente compatível entra
  automaticamente via `tipo` qualificado no CSV curado.
- **§12.6** — IPP trocado de CNAE 24 "Metalurgia" (tabela SIDRA 6903,
  usado pelo legado) para o grupo industrial 242 "Siderurgia" (tabela
  SIDRA 6723, classificação `844[47259]`, confirmado ao vivo nesta stage):
  mais específico (exclui metalurgia não-ferrosa/fundição/ferroligas), mas
  ainda um agregado de toda a siderurgia brasileira — nenhuma tabela IPP
  do SIDRA quebra por produto ou por CNAE de 4+ dígitos. Corresponde ao
  nível 3 da hierarquia de §12.6 ("IPP de siderurgia como fallback
  documentado") — não existe fonte de nível 1/2 disponível hoje.
- **§12.5** — `is_proxy` no output mensal é `True` quando a âncora é
  escopo "Siderurgia" (não específico de HRC) **ou** o mês foi encadeado
  pelo IPP (242-Siderurgia também não é específico) — hoje isso cobre
  essencialmente todos os meses.
- Provenance reaproveita a taxonomia já existente
  (`steel_indicator/domain/provenance.py`: CALCULADO em `nivel_trimestral`,
  ESTIMADO em `encadeado_ipp`/`hold_flat_fallback`) e o `validation_status`
  reaproveita `steel_indicator/data/contracts.py`
  (`VERIFICADO`/`DOCUMENTADO`/`A_CONFIRMAR`): o CSV curado é DOCUMENTADO
  (conferido contra citação de página do release oficial, não executado
  como coletor ao vivo); `ibge_sidra_ipp_siderurgia` é um coletor
  executado ao vivo (VERIFICADO quando roda).

## 12.10 Domestic Price V2 — benchmark PIA-Produto (Stage E10, ADR 0010)

Decisão Level 3 aprovada (investigação completa em
`docs/research/hrc_domestic_price_sources.md`): a IBGE PIA-Produto
(tabela SIDRA 7752, categoria Prodlist 2422.2020 "Bobinas a quente de
aços ao carbono, não revestidos") passa a ser um **segundo caminho**,
paralelo à âncora corporativa (§12.9), implementado em
`preco_domestico_hrc_pia_v2()`/`ibge_sidra_pia_hrc_anual()`/
`denton_proporcional()` (`src/indices_setoriais.py`). Os dois caminhos
**nunca são combinados por splice/reancoragem** — a âncora corporativa
serve só como benchmark de validação externa contra a série PIA
(`scripts/gerar_domestic_price_hrc_pia_v2.py`), nunca para recalibrar seu
nível.

- **Nível PIA×IPP hierarquia (§12.8)**: PIA é uma fonte pública
  produto-específica (nível 2 da hierarquia) — mais específica de produto
  que a âncora corporativa "Siderurgia" (nível 4, proxy de segmento), mas
  mistura mercado interno + exportação (confirmado contra a nota técnica
  oficial do IBGE — nenhuma variável do produto separa destino). Por
  isso é PROXY também, com motivo explícito e ortogonal ao da âncora
  corporativa: `proxy_reason=DESTINATION_MIX` (PIA) vs.
  `proxy_reason=PRODUCT_AGGREGATION` (IPP 242-Siderurgia, reaproveitado
  sem alteração do §12.9).
- **Benchmarking temporal**: nível anual da PIA (`receita líquida de
  vendas / quantidade vendida`) distribuído mês a mês pelo movimento do
  IPP 242-Siderurgia via **Proportional Denton** (primeiras diferenças —
  IMF *Quarterly National Accounts Manual*, cap. 6), nunca forward-fill
  anual, interpolação linear simples ou pro-rata degrau. Restrição:
  `mean(preço mensal do ano) == preço PIA daquele ano` — rotulada
  `TEMPORAL_ALLOCATION_PROXY` porque a PIA é um *unit value* ponderado
  pela quantidade real vendida no ano, não uma soma de preços mensais; o
  projeto não possui hoje quantidade doméstica de HRC mensal para pesar
  a restrição de forma mais fiel, e não inventa esse peso.
- **Propriedade conhecida do Denton conjunto**: como a otimização cobre
  toda a janela benchmarked de uma vez (para suavizar a fronteira entre
  anos), reprocessar a série ao receber um novo ano de PIA pode revisar
  levemente meses de anos mais antigos perto da nova fronteira — prática
  padrão de temporal benchmarking, não uma falha de look-ahead (a média
  anual de cada ano continua batendo exatamente o alvo PIA em qualquer
  reprocessamento). A extensão provisional (abaixo), por outro lado,
  nunca olha para frente — depende só do IPP até o próprio mês.
- **Cobertura**: só gera série mensal para os anos em que a PIA e os 12
  meses do IPP 242-Siderurgia coexistem (janela real, confirmada ao vivo:
  2019-2023 — o IPP 242-Siderurgia só começa em dez/2018). Anos de PIA
  sem IPP completo (2014-2018) não viram série mensal artificial — ficam
  disponíveis só como benchmark anual isolado via
  `ibge_sidra_pia_hrc_anual()`.
- **Extensão provisional**: após o último ano PIA observado (hoje 2023),
  os meses seguintes são encadeados a partir da última relação
  preço-benchmarked/IPP observada (mesma fórmula de
  `encadear_preco_domestico_mensal`, a partir do último mês Denton em vez
  de uma âncora trimestral direta) — `is_provisional=True`,
  `provenance_level=ESTIMADO`. Nunca promovida a publication-grade
  automaticamente; nunca misturada silenciosamente com a janela
  benchmarked. `pia_reference_year` é preservado em toda linha
  especificamente para permitir, no futuro, reprocessar os meses
  provisórios quando uma nova PIA sair — o mecanismo de revisão/vintage
  em si não foi implementado nesta stage, só os campos que o permitem.
- **Execução real** (`scripts/gerar_domestic_price_hrc_pia_v2.py`,
  `data/processed/domestic_price_hrc_pia_v2.csv`): 60 meses benchmarked
  (2019-01 a 2023-12) + 30 meses provisórios (2024-01 a 2026-06, na data
  desta execução). Comparado contra a âncora corporativa V2 nos 15 meses
  em que as duas têm dado: PIA×IPP fica sistematicamente **abaixo** da
  âncora corporativa, delta médio -11,66%, desvio-padrão do delta 1,49pp
  (gap estável, não um ruído) — consistente com a hipótese já registrada
  em `docs/research/hrc_domestic_price_sources.md` de que a âncora
  corporativa "Siderurgia" está inflada por mix de produto frente a um
  preço mais próximo de HRC puro. Nenhum ajuste foi aplicado a partir
  dessa comparação — é validação, não calibração.
- Não conectado a `--selftest`/CLI/relatório nesta stage — mesmo status
  dos demais caminhos V2 (peça de cálculo interna, testada).

## 12.11 IPIA-HRC V2 PIA-based — status PROVISIONAL e séries oficial/provisional (Stage E11, ADR 0011)

Decisão Level 3 aprovada: integra o import side bottom-up multi-NCM
(`agregar_ipia_hrc_multi_ncm_mensal`, §9.5.2) com o Domestic Price V2
caminho PIA (§12.10) — nunca a âncora corporativa Usiminas+CSN, que
continua existindo só como benchmark independente. Implementado em
`calcular_ipia_hrc_v2_pia()`/`separar_ipia_hrc_v2_oficial_provisional()`
(`src/indices_setoriais.py`). Não conectado a `--selftest`/CLI/relatório
nesta stage — mesmo status dos demais caminhos V2.

- **Quarto status, `PROVISIONAL`**: o vocabulário de `publication_status`
  passa a ter quatro valores — `PUBLICATION_GRADE`, `EXPERIMENTAL`,
  `PROVISIONAL`, `UNKNOWN`. `PROVISIONAL` vive em `indices_setoriais.py`,
  não em `steel_indicator.parameters.trade_policy` — não é um status de
  política comercial (import side); `status_efetivo()` continua nunca
  devolvendo `PROVISIONAL`. `PROVISIONAL` só existe no nível COMPOSTO
  (domestico × import), quando o lado doméstico é a extensão provisional
  pós-última-PIA de `preco_domestico_hrc_pia_v2()`.
- **Regra de status conjunta**, usando dinamicamente o último ano PIA
  benchmarked (`last_pia_year`, calculado a partir do próprio
  `pia_domestico_df` de cada execução, nunca hardcoded):
  - domestico ausente OU import `UNKNOWN` → IPIA `UNKNOWN`;
  - domestico BENCHMARKED (`is_provisional=False`) + import
    `EXPERIMENTAL` → IPIA `EXPERIMENTAL`;
  - domestico BENCHMARKED + import `PUBLICATION_GRADE` → IPIA
    `PUBLICATION_GRADE`;
  - domestico PROVISIONAL (`is_provisional=True`) + import calculável
    (`EXPERIMENTAL` ou `PUBLICATION_GRADE`) → IPIA `PROVISIONAL`, sempre —
    nunca um `PUBLICATION_GRADE`/`EXPERIMENTAL` com uma flag
    `is_provisional=True` como substituto.
  `domestic_is_proxy` continua ortogonal a `publication_status` (a série
  PIA é sempre proxy, em qualquer um dos quatro status).
- **Duas saídas explicitamente separadas, nunca concatenadas
  automaticamente**: OFFICIAL (só `EXPERIMENTAL`/`PUBLICATION_GRADE`,
  nunca `PROVISIONAL`) e PROVISIONAL (só `PROVISIONAL`, com os campos
  adicionais `is_provisional`/`last_pia_year`). Meses `UNKNOWN` não
  aparecem em nenhum dos dois arquivos publicados — ficam disponíveis na
  série completa (`calcular_ipia_hrc_v2_pia()`, antes de separar) para
  quem precisar do gap explícito (ex. visualização). O cálculo econômico é
  o mesmo dos demais caminhos V2 (`IPIA = preço doméstico / PPI × 100`,
  nunca duplicado fora de `ipia()`) — a separação é contrato de
  estabilidade de publicação, não mudança de fórmula.
- **Congelamento no fluxo normal**: meses já publicados como OFFICIAL
  (`EXPERIMENTAL`/`PUBLICATION_GRADE`) devem ficar congelados — uma
  atualização normal do provisional (novo mês de IPP, ou até um novo ano
  de PIA promovendo meses provisórios a benchmarked) não pode mover
  números históricos já publicados. Implementado via `congelado_df`
  (parâmetro opcional de `calcular_ipia_hrc_v2_pia()`): recebe a saída
  OFFICIAL de uma execução anterior e sobrescreve, verbatim, todo mês nela
  presente — descartando o que o recálculo fresco desta execução
  produziria para esses meses, independente da causa da mudança upstream
  (revisão do IPP, ou a "propriedade conhecida" do Denton conjunto de
  `preco_domestico_hrc_pia_v2()`/ADR 0010, que pode revisar meses antigos
  ao somar um novo ano de PIA). Deliberadamente **não** foi implementado
  um Denton condicionado ao último ponto congelado (mecanismo permitido,
  mas não obrigatório, pela decisão aprovada) — o congelamento por
  sobrescrita cobre a garantia exigida (nenhum mês OFFICIAL já publicado
  muda) de forma mais simples e auditável, sem tocar a matemática de
  `denton_proporcional()`; a smoothness de continuidade entre o último mês
  congelado e o primeiro mês recém-promovido a benchmarked fica um pouco
  mais abrupta nesse cenário específico, tradeoff aceito nesta stage.
  Meses fora de `congelado_df` (novos meses provisórios, ou meses
  provisórios promovidos a benchmarked por uma nova PIA) sempre usam o
  valor fresco da execução — é assim que o provisional avança mês a mês e
  é promovido quando uma nova PIA chega.
- **Duas exceções futuras ao congelamento, NÃO implementadas nesta
  stage** (a decisão aprovada só exige que a arquitetura não as torne
  impossíveis, não que sejam construídas agora): (1) correção/revisão
  oficial da fonte IBGE (PIA ou IPP republicados com valor corrigido); (2)
  mudança metodológica deliberada (ex. trocar o benchmark ou o método de
  encadeamento). Qualquer uma delas exigiria decisão explícita de
  reabrir/reprocessar meses congelados — fora do fluxo normal.
- **Nenhuma infraestrutura de vintage/persistência foi implementada nesta
  stage** (E11) — `congelado_df` era injetado manualmente pelo chamador.
  A persistência append-only real (armazenamento local automatizado de
  cada execução como uma vintage imutável) foi implementada na stage
  seguinte — ver §12.12 (Stage G2/ADR 0012). O valor corrente do IPIA
  continua sempre mostrado como PROVISIONAL, nunca como definitivo.
- **Execução real** (`scripts/gerar_ipia_hrc_v2_pia.py`,
  `data/processed/ipia_hrc_v2_official.csv`,
  `data/processed/ipia_hrc_v2_provisional.csv`): OFFICIAL cobre 2019-02 a
  2023-12 (48 meses — 27 `EXPERIMENTAL`, 21 `PUBLICATION_GRADE`; IPIA
  mín=70,06, mediana=95,73, máx=154,13). PROVISIONAL cobre 2024-01 a
  2026-06 (30 meses; IPIA mín=95,64, mediana=113,37, máx=131,32; último
  valor corrente, 2026-06, PROVISIONAL=126,74). Comparado contra o IPIA-HRC
  V2 corporate antigo (`calcular_serie_ipia_hrc_v2`, âncora Usiminas+CSN)
  nos 15 meses sobrepostos (2025-04 a 2026-06): o IPIA PIA-based fica
  sistematicamente **abaixo** do corporate, delta médio -11,66%,
  desvio-padrão do delta 1,49pp — mesma magnitude e estabilidade já
  medidas no nível de preço doméstico isolado (§12.10), agora propagada
  para o índice completo (a correção de product-mix do lado doméstico é a
  explicação estrutural dominante do gap, não o import side, que é
  idêntico nos dois caminhos). Nenhum ajuste foi aplicado a partir dessa
  comparação — é validação, não calibração.

## 12.12 IPIA-HRC V2 — vintages de publicação append-only (Stage G2, ADR 0012)

Decisão Level 3 aprovada: camada mínima, local e auditável de vintages de
publicação para o IPIA-HRC V2 PIA-based (§12.11). Mecânica genérica
(gerar ID, escrever atomicamente, hashear, indexar, carregar, listar) em
`steel_indicator/storage/vintage_store.py` — reutilizável pelos demais
produtos do repositório (IPIA-Vergalhão, ICCS, ICS); integração econômica
específica do IPIA-HRC V2 (`calcular_revised`, `preparar_series_para_
vintage`, `salvar_vintage_ipia_hrc_v2`, `carregar_vintage_ipia_hrc_v2`,
`listar_vintages_ipia_hrc_v2`, `ultima_vintage_ipia_hrc_v2`) em
`src/indices_setoriais.py`. Sem banco, sem cloud, sem API — só filesystem
local (`data/processed/vintages/ipia_hrc_v2/<vintage_id>/`), sempre
`.gitignore`d (o mesmo padrão `data/processed/*` já cobre o diretório
novo).

- **`reference_period` ≠ `data_vintage`**: `reference_period` é o mês
  econômico descrito; `data_vintage` é quando aquela VERSÃO do resultado
  foi produzida. Uma observação com o mesmo `reference_period` pode
  existir em vintages diferentes (ex.: 2024-06 como `PROVISIONAL` numa
  vintage, depois `PUBLICATION_GRADE` com valor diferente numa vintage
  posterior) — as duas permanecem recuperáveis, nenhuma sobrescreve a
  outra.
- **Vintage ID**: formato `YYYYMMDDTHHMMSSZ`, sempre UTC, ordenável
  lexicograficamente = cronologicamente, sem `:` (seguro no Windows).
  Colisão (duas vintages pedindo o mesmo segundo) nunca é resolvida
  silenciosamente — `criar_vintage()` levanta `FileExistsError`.
  Injeção explícita de `vintage_id` é suportada para testes
  determinísticos.
- **Imutabilidade**: uma vintage criada nunca é sobrescrita
  (`vintage_store.criar_vintage`). Escrita atômica — tudo montado num
  diretório temporário dentro do próprio `<base_dir>/<produto>/` e só
  então renomeado (`os.rename`) para o `vintage_id` final; uma falha
  antes do rename nunca deixa uma vintage parcial visível, e o
  `index.csv` só é atualizado depois do rename bem-sucedido. Sem
  locking distribuído — execução local/single-process nesta stage, por
  decisão explícita.
- **Manifest** (`manifest.json`, um por vintage): `vintage_id`,
  `created_at_utc` (derivado do próprio `vintage_id` — única fonte de
  verdade do instante de criação), `previous_vintage_id`,
  `methodology_version` (reaproveita `VERSAO_METODOLOGIA`, mecanismo já
  existente — nenhum segundo sistema de versionamento; este batch não
  muda a fórmula econômica do IPIA, então nenhum bump acontece só por
  adicionar persistência), `series`/`coverage`/`counts` (contagem por
  `publication_status`, incluindo `unknown_complete_series`),
  `sources` (`pia_last_observed_year` + `*_fetch_at_utc` — "quando esta
  execução consultou a fonte", nunca uma data de publicação da fonte
  inventada quando ela não a expõe), `files` e `hashes` (SHA256 de cada
  arquivo persistido, verificado contra o arquivo real ao vivo nesta
  stage).
- **Input snapshots**: cada vintage persiste `import_side.csv`
  (resultado usado do agregador bottom-up multi-NCM,
  `agregar_ipia_hrc_multi_ncm_mensal`) e `domestic_price.csv` (resultado
  usado de `preco_domestico_hrc_pia_v2()`) — os INPUTS PROCESSADOS que
  produziram aquela vintage, suficientes para reproduzir o cálculo
  econômico sem nova chamada às APIs externas. **Reproduzir uma vintage
  do IPIA ≠ reconstruir o estado histórico das APIs externas**: se
  Comex Stat/BCB/IBGE revisarem seus próprios dados depois da coleta,
  este mecanismo não pretende recuperar o valor que a API tinha
  naquele instante — só o que o IPIA calculou/publicou com o que foi
  de fato processado. Não são persistidos: respostas brutas do Comex,
  PDFs, payloads HTTP completos, cache de API — deliberadamente fora de
  escopo (não é um data lake).
- **`data_vintage`/`source_vintage_id`/`methodology_version`/`revised`**
  em toda linha de `official.csv`/`provisional.csv`
  (`preparar_series_para_vintage`). `source_vintage_id` usa o próprio
  `vintage_id` (decisão aprovada permite explicitamente) — cada vintage
  desta stage sempre recalcula os inputs do zero numa única execução,
  então publication vintage e source vintage coincidem.
- **`revised`**: comparação contra a vintage IMEDIATAMENTE anterior
  (`calcular_revised`) — compara `preco_domestico_rs_t`/`ppi_rs_t`/
  `ipia_hrc_v2` (`math.isclose`, tolerante a ruído de ponto flutuante) e
  `publication_status` (igualdade exata) contra a UNIÃO
  official+provisional da vintage anterior (nunca só o mesmo arquivo —
  um mês promovido de provisional a oficial precisa ser comparado
  contra onde estava antes). Mês novo → `False`; inalterado → `False`;
  mudou → `True`. Nunca compara `data_vintage`/`source_vintage_id` —
  mudar só o identificador de execução nunca conta como revisão.
- **Official freeze no fluxo normal**: `scripts/gerar_ipia_hrc_v2_pia.py`
  detecta a última vintage (`ultima_vintage_ipia_hrc_v2`), carrega o
  `official.csv` dela (`carregar_vintage_ipia_hrc_v2`) e passa como
  `congelado_df` para `calcular_ipia_hrc_v2_pia()` — decisão tomada no
  SCRIPT de orquestração, nunca escondida numa função econômica de
  baixo nível (mesmo princípio já registrado no §12.11 para
  `congelado_df`). Primeira vintage: sem `previous_vintage_id`, sem
  `congelado_df`.
- **Provisional permanece revisável**: uma nova execução pode alterar
  valores provisórios existentes, adicionar novos meses, ou promover
  meses provisórios a oficiais quando uma nova PIA cobrir aquele ano —
  testado explicitamente
  (`tests/unit/test_ipia_hrc_v2_vintages.py::
  test_promocao_provisional_para_official_apos_nova_pia`, simulando
  Vintage A com 2023-12 oficial + 2024 provisório, depois Vintage B com
  2024 promovido a oficial via `EXPERIMENTAL`/`PUBLICATION_GRADE`
  conforme `import_status`, confirmando que a Vintage A nunca muda —
  byte a byte).
- **Duas exceções futuras ao congelamento, NÃO implementadas**: (a)
  correção/revisão oficial da fonte IBGE; (b) mudança metodológica
  deliberada. A arquitetura não as torna impossíveis (qualquer uma
  geraria uma NOVA vintage, nunca alteraria uma antiga), mas nenhuma
  das duas foi implementada nesta stage.
- **Execução real** (primeira vintage local,
  `data/processed/vintages/ipia_hrc_v2/`): vintage `20260827T150423Z`,
  `previous_vintage_id=None`, `methodology_version=1.2`,
  `last_pia_year=2023`. OFFICIAL e PROVISIONAL idênticos aos números já
  registrados no §12.11 (mesma execução, agora também persistida como
  vintage). Os 4 hashes SHA256 do manifest conferem contra os arquivos
  reais no disco. Recarregar a vintage
  (`carregar_vintage_ipia_hrc_v2`) e recalcular usando só
  `import_side.csv`+`domestic_price.csv` reproduz `official.csv`+
  `provisional.csv` numericamente (dentro de `rtol=1e-9`) — confirmado
  ao vivo nesta stage.
- Implementado em `steel_indicator/storage/vintage_store.py` (genérico)
  e `src/indices_setoriais.py` (`calcular_revised`,
  `preparar_series_para_vintage`, `salvar_vintage_ipia_hrc_v2`,
  `carregar_vintage_ipia_hrc_v2`, `listar_vintages_ipia_hrc_v2`,
  `ultima_vintage_ipia_hrc_v2`). **Conectado à CLI a partir do Stage G5**
  (`python src/indices_setoriais.py --ipia` publica; `--ipia-latest` lê a
  última vintage sem rede) via a orquestração canônica
  `executar_pipeline_ipia_hrc()`. **Conectado ao relatório PDF a partir do
  Stage G6**: `--pdf-ipia` carrega a última vintage já publicada
  (`carregar_vintage_ipia_hrc_v2`) e gera o relatório V2 inteiramente a
  partir dela (`reporting/report_builder.py::gerar_relatorio_ipia_hrc`) —
  sem rede, sem criar vintage nova; falha com instrução clara se nenhuma
  vintage existir ainda. O relatório legado (`gerar_relatorio_ipia`)
  permanece no código, mas não é mais o caminho de `--pdf-ipia`.
  Migração futura para object storage/banco é possível (o layout
  `<produto>/<vintage_id>/` + manifest não impede isso), mas não
  implementada agora.

---

# 13. IPIA-Vergalhão — preço doméstico

O motor econômico é o mesmo do HRC.

A âncora doméstica deve ser específica a vergalhão.

Prioridades de investigação:

1. fonte pública produto-específica estruturada;
2. SINAPI ou outra série pública homogênea, se economicamente comparável;
3. divulgações empresariais estruturadas;
4. proxy documentada apenas se não houver alternativa melhor.

A metodologia final do preço doméstico de vergalhão deve ser congelada em spec própria antes de publicação.

Não assumir que o método CVM + IPP do HRC é automaticamente correto para vergalhão.

---

# 14. IPIA oficial e Nowcast

## 14.1 Oficial

Primeira implementação:

```text
IPIA oficial mensal
```

Usa apenas componentes fechados conforme a regra de publicação.

## 14.2 Nowcast

Fora do escopo V1.

A arquitetura deve permitir uma futura versão semanal.

O Nowcast deverá:

- ser série separada;
- usar rótulo explícito;
- informar data do último dado duro;
- nunca sobrescrever nem ser concatenado silenciosamente à série oficial.

---

# 15. Bloqueantes do IPIA V2 — reconciliação (Stage G4B, ADR 0013)

Esta seção registrava originalmente quatro bloqueantes genéricos do "IPIA
V2" (redação original preservada abaixo de cada item, para auditabilidade
— nada foi apagado). O Stage G4 (`docs/decisions/ipia_hrc_v2_publication_readiness.md`)
e o Stage G4B (ADR 0013) reconciliaram cada um contra a evidência
acumulada nas Stages E2/E3/G3, **escopados estritamente a IPIA-HRC**.

**Esta reconciliação NÃO se aplica automaticamente a:**
- IPIA-Vergalhão (cesta NCM e fontes ainda não investigadas — §10.3/§13);
- qualquer janela de publicação fora de 2019-02–presente (o que foi
  validado é a janela real proposta para publicação, não o histórico
  completo do Comex Stat, que chega a 1997 para import side isolado);
- indicadores auxiliares que dependam de fontes não usadas pelo core do
  IPIA-HRC V2 (ex. Aço Brasil, ver §15.4).

Um produto/janela fora deste escopo permanece com o status original
(`NOT READY FOR PUBLICATION` até investigação própria), nunca herda um
fechamento validado para outro produto.

## 15.1 Comex POST

**Redação original:** "Executar e validar o endpoint `/general` ao vivo."

| Campo | Conteúdo |
|---|---|
| Status original | `A CONFIRMAR` — nunca executado ao vivo |
| Evidência de resolução | `docs/research/comex_live_validation.md` §1 — FACT, endpoint/payload/schema confirmados ao vivo (`success:true`, schema idêntico ao adapter de produção) |
| Escopo do fechamento | Genérico ao endpoint — não depende de produto específico |
| Status atual | **CLOSED** (IPIA-HRC e qualquer outro produto que use o mesmo endpoint) |

## 15.2 Histórico de frete/seguro/CIF

**Redação original:** "Determinar desde quando as métricas estão preenchidas de forma utilizável por produto/NCM."

| Campo | Conteúdo |
|---|---|
| Status original | `A CONFIRMAR` |
| Evidência de resolução | `docs/research/comex_live_validation.md` §3/§11 — FACT, `metricFreight`/`metricInsurance` USABLE desde 1997-01 para a cesta HRC (`NCM_BOBINA_QUENTE`) |
| Escopo do fechamento | Somente a cesta HRC; a janela real de publicação (2019-02+) fica inteiramente dentro do intervalo confirmado, com folga de 22 anos |
| Status atual | **CLOSED para IPIA-HRC, janela de publicação 2019+.** Continua `A CONFIRMAR` para vergalhão/outras famílias (não testadas) |

## 15.3 NCMs vigentes por período

**Redação original:** "Construir a lógica histórica que elimina códigos extintos fora de vigência."

| Campo | Conteúdo |
|---|---|
| Status original | `A CONFIRMAR` |
| Evidência de resolução | `docs/research/hrc_ncm_history.md` §4/§8/§12 — FACT via duas tabelas oficiais de correlação MDIC/Camex (2012↔2017, 2017↔2022): zero mudanças na posição 7208 desde 2012 |
| Escopo do fechamento | Somente os 13 NCMs de `NCM_BOBINA_QUENTE`, com evidência FACT para 2012-presente (cobre toda a janela de publicação 2019+ com folga); a janela 1997-2012 permanece só INFERENCE (sem tabela de correlação localizada), mas nunca entra na publicação proposta |
| Status atual | **CLOSED para IPIA-HRC, janela de publicação 2019+.** Continua `A CONFIRMAR` para vergalhão e para qualquer backfill de import-side isolado anterior a 2019 |

## 15.4 Excel do Aço Brasil

**Redação original:** "Baixar, inspecionar, mapear e validar as abas/colunas relevantes."

| Campo | Conteúdo |
|---|---|
| Status original | `A CONFIRMAR` |
| Evidência de resolução | Inspeção do pipeline V2 (`preco_domestico_hrc_pia_v2`, `agregar_ipia_hrc_multi_ncm_mensal`, `calcular_ipia_hrc_v2_pia`): nenhuma dependência de Aço Brasil em nenhum componente do cálculo core do IPIA-HRC |
| Escopo do fechamento | Aço Brasil nunca foi adotado pelo core V2 (só alimenta a taxa de penetração de importação do caminho legado, `taxa_penetracao_importacao_planos_mensal`, um indicador auxiliar/legacy, não o IPIA-HRC em si) |
| Status atual | **NOT APPLICABLE ao core do IPIA-HRC.** O Instituto Aço Brasil continua podendo existir como fonte de indicadores auxiliares/legacy (ex. penetração de importação) — se um relatório futuro reintroduzir esse indicador ao lado do IPIA-HRC V2, este bloqueante volta a ser relevante e precisa ser reaberto então |

## 15.5 Status consolidado

Com os quatro itens acima fechados ou não-aplicáveis **especificamente para
IPIA-HRC, janela 2019-02–presente**, o IPIA-HRC deixa de estar bloqueado
por `docs/METODOLOGIA.md` §15 nessa janela. Isso não substitui os demais
critérios de publication-readiness (proxy do domestic, disclosure, política
de baixa liquidez — ver ADR 0013).

**Atualização (Stage G5):** o wiring de CLI (`--ipia`/`--ipia-latest`) foi
implementado — ver §12.12 acima e a orquestração canônica
`executar_pipeline_ipia_hrc()`.

**Atualização (Stage G6):** o wiring do relatório PDF (`--pdf-ipia`) foi
implementado — ver §12.12 acima. O relatório V2 é gerado inteiramente a
partir da vintage persistida (nunca recoleta/recalcula), audita e remove
do caminho publicado os indicadores auxiliares legados que dependeriam de
rede (origem por país, penetração de importação via Aço Brasil — ver
§15.4) e mantém o benchmark corporativo (Usiminas+CSN) apenas como
validação textual, nunca como preço doméstico oficial.

---

# 16. ICCS — objetivo

O ICCS mede as condições de crédito enfrentadas pelos setores tomadores.

Não é:

- rating;
- nota de crédito empresarial;
- avaliação individual de emissor.

É um índice agregado de condições setoriais.

---

# 17. ICCS — revisão metodológica obrigatória

O desenho anterior assumia disponibilidade de inadimplência em granularidade setorial fina.

A pesquisa operacional posterior mostrou que:

- saldo de crédito existe em granularidade setorial mais fina;
- inadimplência/qualidade não existe na mesma granularidade;
- SCR.data oferece qualidade em nível mais agregado de CNAE.

Essa descoberta **supersede** a premissa anterior.

## 17.1 Arquitetura de duas camadas

Adotar:

### Camada fina
Informação específica do subsetor:

- saldo de crédito;
- atividade;
- produção;
- preços;
- capacidade;
- comércio exterior;
- outras variáveis disponíveis em granularidade compatível.

### Camada ampla
Qualidade de crédito disponível em seção/grupo mais amplo.

A limitação deve ser pública.

Não fingir que a inadimplência ampla é específica do subsetor.

## 17.2 Proibição de proxy inferencial

Não derivar “inadimplência fina” de:

- desaceleração do crédito;
- atividade;
- outras variáveis correlacionadas.

Isso produziria inferência sobre inferência.

## 17.3 Pesos

O desenho antigo:

```text
Qualidade da carteira = 30%
```

está supersedido.

Novo alvo:

```text
Qualidade da carteira ≈ 22%
```

O peso removido deve ser redistribuído para pilares cuja informação seja realmente fina, especialmente:

- acesso/volume;
- capacidade de pagamento.

**Os pesos exatos ainda devem ser congelados em spec metodológica específica do ICCS antes de implementação final.**

Até lá, não inventar valores exatos.

---

# 18. ICCS — pipeline conceitual

```text
coleta
→ validação por fonte
→ mapeamento CNAE/setor
→ transformação
→ padronização
→ orientação
→ agregação por pilar
→ agregação final
→ cobertura
→ PCA/diagnóstico
→ vintage
→ publicação
```

A infraestrutura deve ser compartilhada com IPIA/ICS sempre que apropriado.

---

# 19. ICCS — critérios de aceitação

Antes de publicação, o ICCS deve provar:

## 19.1 Coerência interna
PCA deve indicar estrutura conjunta razoável.

Referência inicial:

```text
PC1 >= 45% da variância
```

## 19.2 Estabilidade
A entrada de um mês novo não deve reescrever materialmente o histórico fora de revisões legítimas das fontes.

## 19.3 Utilidade
O índice deve demonstrar relação econômica útil com desfechos futuros relevantes.

O teste de antecedência deve ser definido respeitando a granularidade real da inadimplência disponível.

Não usar um target fino inexistente.

## 19.4 Cobertura
Cobertura abaixo do limiar definido impede publicação.

---

# 20. ICS — definição

A primeira versão do ICS será um:

> índice sintético de condições setoriais

construído sobre variáveis públicas contínuas.

Pode incluir:

- produção;
- utilização de capacidade;
- comércio exterior;
- preços;
- emprego;
- energia;
- outras variáveis específicas por setor.

Não deve ser chamado de índice de difusão enquanto não usar respostas de painel.

---

# 21. ICS — painel futuro

Survey/painel é extensão posterior.

O projeto deve permitir no futuro:

- painel fixo;
- cobertura por capacidade/faturamento;
- perguntas ternárias;
- saldo de respostas;
- divulgação de `n`;
- média móvel inicial;
- separação entre medidas observadas e expectativas.

Não implementar painel na primeira fase da infraestrutura comum.

---

# 22. Infraestrutura compartilhada

Todos os índices devem consumir a mesma arquitetura de dados:

```text
SOURCE
  ↓
FETCH
  ↓
RAW VINTAGE
  ↓
CONTRACT VALIDATION
  ↓
NORMALIZATION
  ↓
TRANSFORMATION
  ↓
QUALITY VALIDATION
  ↓
CALCULATION INPUT
  ↓
INDEX ENGINE
  ↓
PUBLICATION VINTAGE
```

O índice específico não deve:

- recolher a mesma fonte novamente;
- reimplementar validação de API;
- duplicar tratamento de vintage;
- criar regra própria de provenance incompatível.

---

# 23. Calendário e publication readiness

Um índice só pode ser considerado pronto para publicação quando:

- fontes bloqueantes estiverem verificadas;
- metodologia estiver versionada;
- histórico estiver reproduzível;
- critérios de aceitação estiverem satisfeitos;
- provenance/vintage estiver funcionando;
- calendário de divulgação estiver definido;
- política de revisão estiver documentada;
- limitações forem públicas.

Implementação técnica concluída não significa publication-ready.

---

# 24. Governança de mudança metodológica

Mudança metodológica deve:

1. possuir motivação explícita;
2. identificar comportamento anterior;
3. explicar comportamento novo;
4. registrar impacto histórico;
5. possuir testes;
6. atualizar versão metodológica;
7. preservar comparação com versão anterior quando material.

Mudanças estruturais sem efeito econômico não exigem bump metodológico.

---

# 25. Licenciamento e uso de dados

O pipeline deve armazenar metadados de licença/status de uso quando relevante.

Princípios:

- vender o índice e a análise, não redistribuir bases quando a licença não permitir;
- fontes com uso comercial não confirmado permanecem com status explícito;
- fontes restritas não entram em produção sem autorização/licença;
- não substituir dados licenciados por cópias indiretas ou scraping não autorizado.

---

# 26. Limitações atuais conhecidas

## IPIA-HRC
- preço doméstico ainda é majoritariamente proxy de segmento;
- histórico doméstico ainda é curto;
- NCMs ainda precisam de validação histórica;
- parâmetros de internação (II/TEC, AFRMM, antidumping) têm modelo histórico mínimo versionado (`steel_indicator/parameters/trade_policy.py`, ADR 0009), mas II individual de 9 dos 13 NCMs permanece não comprovado para 2012-01–2022-03 (janela `historical experimental`, não publication-grade — ver ADR 0009);
- `calcular_ipia_hrc_v2()` (`src/indices_setoriais.py`) já usa esse modelo histórico para o custo de importação, mas aplica a alíquota de **um único NCM informado pelo chamador** ao CIF já agregado dos 13 NCMs (mesma agregação de `serie_mensal_preco_bobina`) — sem ponderação por volume. Permanece assim, deliberadamente, como registro do que **não** fazer — não foi alterado por este batch;
- a limitação de representatividade acima **foi resolvida** por
  `agregar_ipia_hrc_multi_ncm_mensal()`/`custo_importacao_bottom_up_mensal()`
  (Stage E7, decisão Level 3 aprovada — ver §9.5.2 e ADR 0009): agregação
  bottom-up por `(mês, NCM, país)`, ponderada por KG, com publication
  policy própria (`PUBLICATION_GRADE` exige 100% do volume com política
  conhecida; `EXPERIMENTAL` exige coverage≥60% e range de incerteza≤2%).
  Também **não está conectado a `--selftest`/CLI/relatório** nesta stage —
  permanece peça de cálculo interna/testada até uma decisão explícita de
  publicação;
- disponibilidade histórica de frete/seguro precisa ser confirmada;
- Aço Brasil estruturado ainda precisa ser validado;
- o preço FOB de importação é um valor unitário (`Valor FOB / Peso`), não
  um price assessment puro — viés de composição/mix de qualidade dentro da
  NCM não é eliminado pela agregação bottom-up por NCM×país (§9.7);
  validação contra benchmark externo independente ainda não foi feita;
- `D_porto` (R$ 210/t), `D_interno` (R$ 140/t) e a margem do importador
  (3%) são constantes `ESTIMADO` (hold-flat) herdadas sem alteração da
  pesquisa metodológica original, nunca calibradas com despachantes
  aduaneiros conforme a própria pesquisa recomendava (§9.8, §9.9). Impacto
  no IPIA é pequeno para D_porto/D_interno e moderado para a margem
  (§9.10) — nenhum dos três bloqueia publicação, mas nenhum tem fonte
  primária documentada;
- ~~o câmbio de referência do PPI é a última cotação PTAX venda disponível
  até o mês (forward-fill), não uma média mensal~~ — **resolvido pela ADR
  0014** (FX Convention Sprint): o motor V2 passou a usar média mensal
  das observações diárias válidas (`calcular_fx_mensal`, §9.6). O motor
  legado V1 permanece deliberadamente na convenção antiga (referência
  histórica, não a série publicada).

## IPIA-Vergalhão
- cesta NCM final não está congelada;
- fonte doméstica homogênea ainda precisa ser escolhida e validada;
- histórico comparável ainda precisa ser mapeado.

## ICCS
- pesos finais pós-descoberta da granularidade de inadimplência ainda precisam ser congelados;
- mapeamento fino/amplo por setor precisa de spec explícita;
- critérios de antecedência precisam respeitar o target realmente disponível.

## ICS
- composição setorial inicial ainda precisa de especificação própria.

---

# 27. Roadmap metodológico

## Fase 1 — plataforma
- contratos de fonte;
- coleta;
- vintages;
- validação;
- transformação;
- provenance;
- parâmetros históricos.

## Fase 2 — IPIA
- HRC;
- vergalhão;
- backfill;
- comparação legacy vs nova metodologia;
- publicação oficial mensal.

## Fase 3 — ICCS
- arquitetura de duas camadas;
- pesos finais;
- séries;
- backfill;
- critérios de aceitação.

## Fase 4 — ICS
- índice sintético;
- setores prioritários;
- painel apenas em etapa futura.

---

# 28. Relação com código legado

Enquanto durar a migração:

```text
legacy
→ comparação
→ diagnóstico
→ golden tests
```

e:

```text
nova metodologia
→ specs
→ novos módulos
→ novos testes
→ publication candidate
```

O código antigo pode continuar existindo temporariamente.

Ele não deve impedir uma mudança metodológica explicitamente aprovada.

---

# 29. Critério de encerramento da reformulação

A reformulação da arquitetura/metodologia estará concluída quando:

- o monólito deixar de ser a fonte central de verdade;
- fontes forem adapters independentes;
- vintages forem persistidos;
- provenance fizer parte dos contratos;
- HRC e vergalhão usarem o mesmo motor;
- parâmetros históricos forem versionados;
- os quatro bloqueantes do IPIA estiverem fechados;
- IPIA-HRC e IPIA-Vergalhão tiverem histórico reproduzível;
- ICCS tiver pesos e granularidade final documentados;
- ICS tiver spec aprovada;
- reporting consumir somente outputs calculados, sem recolher/recalcular lógica de negócio.

---

# 30. Documentos relacionados

Consultar:

- `CLAUDE.md` — regras operacionais para desenvolvimento;
- `docs/architecture.md` — arquitetura de software;
- `docs/data-sources.md` — contratos e status das fontes;
- `docs/adr/` — decisões metodológicas/arquiteturais;
- `docs/specs/` — implementação incremental;
- `references/catalogo_series_coleta.xlsx`;
- `references/guia_de_coleta_de_series.md`;
- `references/manual_metodologico_indices_setoriais.md`.

Os arquivos em `references/` são evidência de pesquisa.  
Este documento é a metodologia oficial que o código deve implementar.
