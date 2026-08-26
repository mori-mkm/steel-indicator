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
- parâmetros de internação ainda não estão historicamente versionados;
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
