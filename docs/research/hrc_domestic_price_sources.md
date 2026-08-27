# Fontes do preço doméstico do IPIA-HRC V2 — investigação Level 3

Data: 2026-08-26. Não implementa nada — investigação para decisão Level 3
(ver CLAUDE.md §Autonomia). `preco_domestico_hrc_mensal_v2()`/
`ancora_domestica_ponderada_v2()` (`src/indices_setoriais.py`) e o CSV
curado (`data/curated/preco_domestico_aco.csv`) **não foram alterados**
por esta investigação.

## Contexto que motivou a investigação

A primeira validação econômica end-to-end do IPIA-HRC V2 (15 meses
calculáveis, 2025-04 a 2026-06) mostrou IPIA médio ≈133 (mínimo 121,
máximo 148), com PPI V2 ≈ PPI legado e Domestic Price V2 ≈ Domestic
legado — ou seja, o nível elevado não é um artefato da nova arquitetura.
A limitação estrutural já documentada (ADR 0001, `docs/METODOLOGIA.md`
§12.5/§12.9) é que a âncora doméstica é `receita/volume` do segmento
"Siderurgia" inteiro de Usiminas+CSN (`domestic_is_proxy=True` em 100%
dos meses), não HRC especificamente. Esta investigação pergunta: existe
fonte melhor?

## 1. Objetivo econômico (critério de avaliação)

O numerador do IPIA-HRC deve representar o **preço doméstico realizável
de HRC no Brasil, em R$/t, economicamente comparável ao HRC importado que
alimenta o PPI** (13 NCMs de `NCM_BOBINA_QUENTE`, bottom-up por NCM/país).
Toda fonte abaixo é avaliada contra isso: quanto mais próxima de "HRC
puro, transação real, R$/t, Brasil", melhor.

## 2-3. Mapeamento de fontes + matriz estruturada

| # | Fonte | Produto | Granularidade | Periodicidade | Unidade | Cobertura histórica | Acesso | Automação | Structured? | Provenance | Proxy? | Confidence | Custo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Usiminas release trimestral (Mziq/RI) | "Siderurgia" (HRC+CRC+galvanizado+chapas grossas) | Segmento, MI | Trimestral | R$/t (receita/volume) | Curado: 2025Q2-2026Q2 (5 tri); PDFs existem desde ~2011-2012 (não curados) | PDF via IR, download livre | Manual (pdfplumber) | Semi-estruturado (tabela dentro de PDF) | DOCUMENTADO | **Sim** | Alta (cross-validado com CSN, ADR 0001) | Grátis |
| 2 | CSN release trimestral (Mziq/RI) | "Siderurgia" (planos+longos) | Segmento, MI | Trimestral | R$/t (Preço Médio direto) | Curado: 2025Q2-2025Q4, 2026Q2 (2026Q1 não localizado); PDFs existem desde ~2011-2012 (não curados) | PDF via IR, download livre | Manual (pdfplumber) | Semi-estruturado | DOCUMENTADO | **Sim** | Alta | Grátis |
| 3 | Gerdau (avaliada, não incluída) | Aço longo (Brasil) | — | — | — | — | — | — | — | — | N/A | Escopo incompatível (longo, não plano) — confirmado, não reaberto aqui |
| 4 | CVM ITR/DFP estruturado (`dados.cvm.gov.br`) | Empresa toda (DRE consolidado/individual) | Nenhuma dimensão de segmento nos CSVs bulk | Trimestral/anual | R$ (Mil Reais) | 2011-presente (ZIPs anuais confirmados) | ZIP CSV, download livre, API `dados.cvm.gov.br` | **Alta** (CSV padronizado) | **Estruturado** | VERIFICADO (baixado e inspecionado ao vivo) | N/A | **Baixa p/ este uso** — sem dimensão de segmento, mais grosseiro que já usamos | Grátis |
| 5 | IBGE/SIDRA IPP 242-Siderurgia (tabela 6723) — **fonte atual do encadeamento mensal** | Toda a siderurgia (CNAE) | Grupo industrial | Mensal | Índice (dez/2018=100) | 2013-presente | API `servicodados.ibge.gov.br` | Alta | Estruturado | VERIFICADO | **Sim** | Alta (única tabela IPP ativa mais específica confirmada) | Grátis |
| 6 | IBGE/SIDRA PIA-Produto (tabela 7752, classif. 1264, categoria 54849 = "2422.2020 Bobinas a quente de aços ao carbono, não revestidos") — **achado novo desta investigação** | **HRC especificamente** (bobina a quente não revestida, carbono) | Produto (Prodlist), nacional (todos os produtores) | **Anual** | R$/t (receita líquida de vendas / quantidade vendida, ambas em "Toneladas" confirmado no metadado) | **2014-2023** (defasagem ~2 anos, sem 2024-2026) | API `servicodados.ibge.gov.br`, `scripts/research/ibge_pia_produto_hrc.py` | Alta | Estruturado | **VERIFICADO** (dado real puxado ao vivo nesta pesquisa) | **Sim** (receita/volume, mesma técnica já aprovada) | Alta para o que é (nível anual plausível: 2020=R$2.841/t, 2021=R$5.645/t [pico do supercycle], 2022=R$5.393/t, 2023=R$4.844/t — consistente com o ciclo de preço do aço conhecido) | Grátis |
| 7 | Instituto Aço Brasil, Excel "Performance Mensal" — **lacuna fechada nesta pesquisa** | N/A | N/A | Mensal | Mil t (volume) + US$ mi (só total import/export, não por produto) | 2013-presente | XLS, download livre | Alta | Estruturado | **VERIFICADO** (baixado e inspecionado ao vivo, `scripts/research/inspecionar_acobrasil_xls.py`) | N/A | **Não tem preço/receita nenhuma coluna** — confirma definitivamente que não serve como fonte de preço doméstico (serve só para penetração de importação, uso já existente) | Grátis |
| 8 | Fastmarkets (MB) — assessment "MB-STE-0007: Steel hot-rolled coil, domestic, exw Brazil, Reais/tonne" | **HRC especificamente, ex-works Brasil** | Nacional | Quinzenal (era semanal; mudou por causa do novo regime AD/tarifa) | R$/t | Desconhecida (não verificada — pendente de licença) | Assinatura paga | Alta se licenciado | Estruturado (dado comercial) | DOC (achado em página de metodologia/marketing pública, não acessado) | Não (é justamente a fonte HRC-pura que falta) | Alta especificidade, mas não verificada operacionalmente | **Pago, licença não avaliada** |
| 9 | Argus Media — Brazil HRC domestic ex-works + HRC cfr Brasil (importado) | HRC especificamente | Nacional | Diária/semanal/mensal (varia por produto) | R$/t e US$/t | Desconhecida | Assinatura paga; artigos "Viewpoint" públicos com números pontuais | Alta se licenciado | Estruturado (comercial) | DOC (existência) / **FACT para os pontos citados no artigo público** (ver §8) | Não | Alta especificidade | **Pago** |
| 10 | CRU Group — Steel Sheet Products Monitor, Brazil HRC exw (BRL/t) e FOB (USD/t) | HRC especificamente | Nacional | Semanal (cadência BR não confirmada) | R$/t e US$/t | Desconhecida | Assinatura paga | Alta se licenciado | Estruturado (comercial) | DOC (só página de marketing, nenhum nível encontrado) | Não | Não verificada | **Pago** |
| 11 | S&P Global Platts/Commodity Insights | TSI HRC (global, sem série Brasil-doméstico dedicada confirmada) | — | Diária (produto geral) | — | — | Assinatura paga | — | — | DOC/UNKNOWN — nenhuma série BR-doméstica dedicada confirmada nas páginas públicas | Não | Baixa (não confirmada) | **Pago** |
| 12 | SteelOrbis (imprensa setorial) | HRC especificamente, ex-works, grades comerciais básicas | Nacional | ~Semanal (notas de mercado) | R$/t e US$/t (export FOB) | Pontual, não é série histórica baixável | Artigos gratuitos/parcialmente gratuitos | Baixa (não é feed, é nota de imprensa) | Não estruturado | **FACT para os pontos citados** (ver §8) | Não | Média (fonte de imprensa, não metodologia publicada) | Grátis (acesso a artigos) |

## 4. Usiminas e CSN — FACT / INFERENCE / UNKNOWN

**FACT**: nenhuma das duas separa HRC de outros produtos planos (CRC,
galvanizado, chapas grossas) em NENHUM canal de divulgação já verificado
— nem no release trimestral (tabela operacional mais granular que
publicam), nem na estrutura de dados da CVM (ver abaixo). Confirmado para
2025Q2-2026Q2 (ADR 0001) e agora também para a estrutura CVM (2011-2026).

**INFERENCE**: se existisse uma quebra por produto, o lugar mais provável
seria uma nota explicativa de segmentos operacionais dentro do ITR/DFP
completo (texto/tabela dentro do PDF da nota, não extraído nos CSVs bulk
da CVM) — não verificado diretamente nesta pesquisa (o CSV estruturado da
CVM não tem essa dimensão; o PDF completo da nota não foi aberto). Não é
FACT, é uma hipótese de próximo passo caso Option B seja escolhida no
futuro.

**UNKNOWN**: se existe alguma divulgação não-pública (apresentação a
analistas, relatório de pesquisa sell-side) com volume/receita HRC
isolado. Não investigado (fora do escopo de fonte pública/reproduzível).

**Regra do projeto respeitada**: não foi combinada receita de universo
amplo com volume de universo estreito (ou vice-versa) em nenhum ponto
desta investigação — onde a granularidade de produto não existe, a fonte
foi marcada como PROXY ou descartada, nunca "consertada" com um numerador
e denominador de escopos diferentes.

## 5. IPP — existe algo mais específico que 242-Siderurgia?

**Não, para preço/índice de preço** (achado desta pesquisa, verificado ao
vivo): as três tabelas IPP atualmente ativas do SIDRA (6723, 6903, 6904)
são todas por classificação CNAE/categoria econômica — nenhuma quebra por
produto. A tabela 6723/242-Siderurgia (já em uso) é confirmada como a
mais específica disponível. Séries pré-dez/2018 (5796/5800) estão
encerradas, mesma granularidade CNAE.

**Sim, para valor/quantidade (não é índice de preço, mas dá para derivar
preço unitário)**: tabela 7752 (PIA-Produto), item 6 da matriz acima —
achado novo, HRC especificamente, mas anual com defasagem de 2 anos. Não
substitui o IPP mensal (não tem a frequência necessária para o
encadeamento mês a mês), mas é candidato a **âncora anual complementar**
ou a **benchmark de validação anual** — ver Option D.

## 6. Comparação de opções

### OPTION A — manter âncora atual (Usiminas+CSN, segmento "Siderurgia"), PROXY explícito
Sem mudança de código. É o que já está implementado e corretamente
rotulado (`domestic_is_proxy=True`).
- **Comparabilidade com PPI HRC**: baixa/moderada — mistura HRC com CRC/
  galvanizado/chapas grossas.
- **Especificidade de produto**: nenhuma.
- **Cobertura histórica**: hoje 5 trimestres curados; **extensível por
  trabalho de curadoria** (mesmo método já validado, ADR 0001) até pelo
  menos 2022Q2 (documentos já sabidamente existentes, "pendência maior"
  registrada em ADR 0001: 2023Q1-2025Q1, 9 trimestres, mais 2026Q1 da
  CSN). Extensão até 2012 é UNKNOWN — não confirmado se o formato atual
  de release ("Desempenho Operacional das Unidades de Negócios") existia
  tão cedo.
- **Automação**: nenhuma (manual, como hoje).
- **Reprodutibilidade/auditabilidade**: alta (metodologia de extração já
  documentada e cross-validada, ADR 0001).
- **Custo/licença**: grátis.
- **Risco de descontinuação**: baixo (empresas abertas, obrigadas a
  divulgar).
- **Publication-grade readiness**: já é o estado atual, corretamente
  rotulado como PROXY — não piora nem resolve o problema de
  comparabilidade.

### OPTION B — âncora HRC específica a partir de divulgação das empresas
**Bloqueada por ausência de dado**, não por escolha de design: nenhuma
fonte pública (release, CVM estruturado) separa HRC hoje (§4). Não pode
ser implementada sem uma fonte nova ainda não identificada.

### OPTION C — índice/preço externo específico de HRC (Fastmarkets/Argus/CRU/Platts)
- **Comparabilidade**: potencialmente a melhor de todas — são literalmente
  "HRC, domestic, exw Brazil".
- **Especificidade de produto**: alta (nominalmente).
- **Cobertura histórica**: **UNKNOWN** — não verificada (pendente de
  licença); a mudança recente de cadência do Fastmarkets (semanal →
  quinzenal, por causa do novo regime de tarifa/antidumping) sugere que a
  série está em evolução metodológica, o que é um risco a mais para
  backfill limpo.
- **Automação**: alta se licenciado; nula sem licença.
- **Reprodutibilidade/auditabilidade**: **menor** que as demais opções —
  um terceiro auditando o IPIA não consegue reproduzir um número de
  fornecedor pago sem a mesma assinatura; muda o caráter do índice de
  "calculado from scratch" para "licenciado de terceiro".
- **Custo/licença**: pago, não avaliado (proposta explícita da tarefa: não
  depender de fonte paywalled para implementação, só para benchmark).
- **Risco de descontinuação/dependência de fornecedor**: real.
- **Publication-grade readiness**: não avaliável sem negociação comercial
  prévia. Números pontuais gratuitos (artigos de imprensa do próprio
  Argus, SteelOrbis) já servem como **benchmark** (§8), não como fonte
  operacional.

### OPTION D — híbrido: âncora corporativa observada + informação de mix de uma fonte HRC observável
Esta investigação encontrou uma base concreta e nova para esta opção: a
tabela IBGE/SIDRA 7752 (PIA-Produto, item 6 da matriz) é uma série ANUAL,
NACIONAL, HRC-específica e estruturada (não um índice de mix inventado).
Dois usos possíveis, com riscos MUITO diferentes:

- **D1 — benchmark de validação anual (baixo risco)**: comparar, uma vez
  por ano quando o dado sair, a âncora corporativa trimestral (Usiminas+
  CSN) contra o nível implícito da PIA-Produto para o mesmo ano civil.
  Não altera o cálculo publicado — é uma checagem de plausibilidade
  adicional, no mesmo espírito da comparação legado-vs-V2 já feita na
  validação anterior. Não é o "fator de correção" que a tarefa proíbe
  criar, porque não entra na fórmula do índice.
- **D2 — âncora nacional formal alternativa ou complementar (alto risco,
  decisão própria)**: usar a série PIA-Produto como âncora de nível em vez
  de (ou combinada com) Usiminas+CSN, encadeada mensalmente por algum
  índice de movimento. Isso exigiria: (a) uma técnica formal de temporal
  benchmarking (`docs/METODOLOGIA.md` §12.7 já antecipa que isso pode ser
  necessário, mas não decide o método); (b) uma decisão explícita sobre
  como reconciliar uma âncora anual com uma âncora trimestral quando as
  duas discordam; (c) aceitar que a série para antes de 2024 — não cobre
  o período mais recente sem algum encadeamento adicional. **Não
  recomendado implementar agora** — é uma decisão de design nova, não
  uma escolha entre fontes já prontas.

- **Especificidade de produto**: alta (D1: só para validação; D2: alta
  se implementado, mas caro em complexidade).
- **Cobertura histórica**: 2014-2023 (10 pontos anuais), defasagem ~2 anos
  — não cobre 2024-2026, então não resolve sozinho a janela atual
  calculável do IPIA-HRC V2 (2025-04 a 2026-06).
- **Automação**: alta (API estruturada, já confirmada ao vivo).
- **Reprodutibilidade/auditabilidade**: alta (fonte pública, gratuita,
  metodologia de pesquisa oficial do IBGE).
- **Custo**: grátis.
- **Risco de descontinuação**: baixo-moderado (é pesquisa oficial
  recorrente do IBGE, mas já teve mudança de classificação Prodlist
  2016→2019→2022 no passado — cuidado ao encadear séries entre edições).
- **Publication-grade readiness**: D1 pode ser feito com esforço pequeno
  e sem decisão de metodologia nova (é só benchmark). D2 exige spec/ADR
  próprio.

### OPTION E
Nenhuma alternativa adicional claramente superior às quatro acima foi
identificada nesta pesquisa.

## 7. Cobertura histórica — resumo por opção

| Opção | Primeira data defensável | Frequência | Backfill até 2022-04 | Backfill até 2018 | Backfill até 2012 |
|---|---|---|---|---|---|
| A (atual) | 2025-04 (curado) | Trimestral | Provável, com esforço de curadoria (documentos já sabidamente existentes) | Possível, não confirmado (formato do release nessa época não verificado) | UNKNOWN |
| B | N/A (bloqueada) | — | — | — | — |
| C (comercial) | UNKNOWN (depende de licença) | Quinzenal/semanal/diária conforme provedor | UNKNOWN | UNKNOWN | Improvável (séries parecem recentes/em evolução metodológica) |
| D1 (benchmark anual) | 2014 | Anual, defasagem ~2 anos | Sim (2014-2023 cobre 2022 civil) | Sim | Não (começa em 2014) |
| D2 (âncora formal) | 2014, mas não cobre 2024-2026 sem encadeamento adicional | Anual | Parcial (precisa de encadeamento mensal/trimestral complementar) | Parcial | Não |

## 8. Benchmark do nível (R$5.100-5.400/t é plausível como quê?)

Evidência externa encontrada (Argus Media, artigo público "Price battle
pushes Brazil HRC lower in 2025"; SteelOrbis, nota de mercado de
04/03/2026) — **HRC especificamente, ex-works doméstico**:

| Data | Fonte | HRC doméstico ex-works | HRC importado cfr Brasil |
|---|---|---|---|
| 02/01/2025 | Argus | R$4.000-4.300/t | — |
| jul/2025 | Argus | abaixo de R$3.400/t | abaixo de US$500/t |
| 11/12/2025 | Argus | R$3.600-3.900/t | US$515-550/t |
| 04/03/2026 | SteelOrbis | R$4.560/t (grades comerciais básicas) | export FOB US$730/t |

Nenhuma fonte encontrada cita HRC doméstico puro em R$5.100-5.400/t para
2025Q2-2026Q2. Os pontos de referência HRC-específicos (R$3.600-4.560/t
ao longo do mesmo período) ficam **consistentemente abaixo** da âncora
atual do projeto (âncora corporativa "Siderurgia": R$4.951-5.378/t no
mesmo período — ver `data/processed/ipia_hrc_v2_validation_components.csv`,
coluna `anchor_price_rs_t`).

Isso é evidência (não prova — os benchmarks externos são pontuais, não
uma série completa, e não foram validados quanto à metodologia exata de
coleta) de que a âncora atual, sendo um mix "Siderurgia" (HRC+CRC+
galvanizado+chapas grossas), está **estruturalmente acima** de um preço
HRC puro — na ordem de 15% a 40% dependendo do mês/fonte comparada, não
um desconto fixo (nunca inventado aqui, só observado). A tabela
IBGE/PIA-Produto (§5-6, item D) reforça essa leitura de forma
independente: em 2023 (último ano disponível), o preço unitário HRC
nacional implícito era R$4.844/t — mais baixo que a âncora corporativa
projetada por V2 para 2025-2026, mesmo considerando dois anos de
inflação/câmbio entre as datas.

**Não foi criado nenhum fator de correção a partir disso** — é
apresentado aqui só como evidência de materialidade para a decisão do
usuário.

## 9. Critérios de decisão — resumo

| Critério | A | C (comercial) | D1 (benchmark anual) |
|---|---|---|---|
| Comparabilidade com PPI HRC | Baixa/moderada | Alta (se real) | Não altera A; só valida |
| Especificidade de produto | Nenhuma | Alta | Alta (mas anual) |
| Cobertura histórica | Extensível por curadoria | UNKNOWN | 2014-2023 |
| Automação | Nenhuma | Alta se licenciado | Alta |
| Reprodutibilidade/auditabilidade | Alta | Baixa (dependente de licença) | Alta |
| Custo | Grátis | Pago, não avaliado | Grátis |
| Dependência de scraping | Não (RI oficial) | Não (feed comercial) | Não (API oficial) |
| Risco de descontinuação | Baixo | Real (fornecedor comercial) | Baixo-moderado |
| Publication-grade readiness | Já é o estado atual | Bloqueada até negociação de licença | Compatível com produção como *complemento*, não substituto |

## RECOMMENDATION

Nenhuma mudança de código agora. Três ações de acompanhamento, cada uma
com seu próprio nível de decisão/esforço, nenhuma decidida aqui:

1. **Curto prazo, baixo risco (Level 2, se autorizado)**: estender a
   curadoria trimestral de Usiminas+CSN (Option A, mesma metodologia já
   aprovada em ADR 0001) até pelo menos 2022Q2, cobrindo os trimestres já
   identificados como pendência (`2023Q1-2025Q1`, `2026Q1` CSN). Não é
   decisão de metodologia — é execução de um método já aceito.
2. **Curto prazo, baixo risco (Level 2, se autorizado)**: adicionar a
   checagem de benchmark anual D1 (IBGE PIA-Produto tabela 7752) como
   validação de plausibilidade fora da fórmula publicada — mesmo padrão
   já usado por `scripts/validar_ipia_hrc_v2.py`, nunca entra no cálculo.
3. **Médio prazo, decisão própria (Level 3)**: avaliar formalmente se vale
   negociar acesso a Fastmarkets MB-STE-0007 ou ao assessment Argus Brazil
   HRC domestic exw — a única fonte que promete resolver o problema de
   comparabilidade de produto de forma direta, mas com custo, risco de
   dependência de fornecedor e cobertura histórica desconhecidos que
   pesam contra a auditabilidade que o projeto valoriza (CLAUDE.md
   §Auditabilidade). Não recomendável sem avaliação de custo/licença real.

Nenhuma das três ações troca a âncora atual nem introduz fator de
correção — Option A permanece o estado publicado até uma decisão
explícita em contrário.

## EXPECTED HISTORICAL COVERAGE

Ver tabela §7. Resumo: Option A é extensível a ~2022-04 com esforço de
curadoria conhecido (mesmo método, sem decisão nova); D1 cobre 2014-2023
mas não substitui A porque é anual e não cobre 2024+; C é UNKNOWN até
negociação de licença; B não existe.

## EXPECTED IMPACT ON PRODUCT COMPARABILITY

- **A (manter)**: nenhuma mudança — permanece PROXY documentado,
  comparabilidade baixa/moderada, como hoje.
- **C (se licenciado e validado)**: potencialmente a maior melhoria de
  comparabilidade de todas as opções — mas não confirmada, cara, e reduz
  auditabilidade de terceiro.
- **D1 (benchmark)**: não muda a comparabilidade do índice PUBLICADO (não
  entra na fórmula) — só aumenta a confiança de que o gap Option-A-vs-HRC-
  puro está sendo monitorado com uma fonte independente.
- **D2 (âncora formal)**: melhoria potencial de comparabilidade, mas exige
  desenho metodológico novo (temporal benchmarking entre âncora anual e
  mensal) — não avaliável sem essa decisão própria.

Nenhum novo valor de IPIA foi estimado ou projetado a partir desta
investigação — os dados atuais não suportam um número diferente sem uma
decisão explícita de fonte/metodologia.

## IMPLEMENTATION BLOCKED (até decisão do usuário)

- Qualquer alteração em `preco_domestico_hrc_mensal_v2()`,
  `ancora_domestica_ponderada_v2()`, `carregar_preco_domestico_trimestral_v2()`
  ou no CSV curado `data/curated/preco_domestico_aco.csv`.
- Qualquer fator de correção, desconto ou ajuste de mix aplicado à âncora
  doméstica (Option D2 nomeadamente).
- Qualquer integração ou compromisso comercial com Fastmarkets/Argus/CRU/
  Platts (Option C) sem avaliação de custo/licença formal.
- Qualquer uso da tabela IBGE PIA-Produto (7752) dentro do cálculo
  publicado do IPIA (mesmo como D1 "benchmark" — deve ser proposto como
  seu próprio batch Level 2 explícito, não implementado por extensão
  automática desta pesquisa).
- Qualquer batch de curadoria adicional de trimestres Usiminas/CSN (mesmo
  sendo metodologicamente idêntico ao já aprovado) — deve ser proposto
  como seu próprio Level 2 com escopo explícito (quantos trimestres, quais
  empresas), não iniciado silenciosamente a partir desta investigação.
- Conexão de qualquer caminho V2 a `--selftest`/CLI/relatório.
- Qualquer novo valor de IPIA "recalibrado" para os meses já publicados.

## Artefatos desta pesquisa

- `scripts/research/inspecionar_acobrasil_xls.py` — confirma ao vivo que
  o Excel "Performance Mensal" do Aço Brasil não tem preço/receita (fecha
  lacuna do catálogo).
- `scripts/research/ibge_pia_produto_hrc.py` — reproduz a série anual
  HRC-específica da tabela SIDRA 7752 (achado novo desta pesquisa).
- Nenhum arquivo de produção alterado. Nenhum `git add`/`commit`/`push`
  executado.
