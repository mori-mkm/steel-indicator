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
- **Nenhuma infraestrutura de vintage/persistência foi implementada** —
  `congelado_df` é injetado pelo chamador (ex. um script de orquestração
  que lê o CSV OFFICIAL anterior antes de rodar de novo); não há
  armazenamento de vintages históricos automatizado. O valor corrente do
  IPIA é sempre mostrado como PROVISIONAL, nunca como definitivo.
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

# 15. Bloqueantes do IPIA V2

O IPIA reformulado permanece:

```text
NOT READY FOR PUBLICATION
```

até fechar os quatro bloqueantes:

## 15.1 Comex POST

Executar e validar o endpoint `/general` ao vivo.

## 15.2 Histórico de frete/seguro/CIF

Determinar desde quando as métricas estão preenchidas de forma utilizável por produto/NCM.

## 15.3 NCMs vigentes por período

Construir a lógica histórica que elimina códigos extintos fora de vigência.

## 15.4 Excel do Aço Brasil

Baixar, inspecionar, mapear e validar as abas/colunas relevantes.

Esses bloqueantes devem aparecer em status operacional do projeto até encerramento.

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
- Aço Brasil estruturado ainda precisa ser validado.

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
