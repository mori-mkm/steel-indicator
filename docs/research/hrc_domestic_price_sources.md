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

---

# Adendo (2026-08-26, mesmo dia) — exposição a exportação da PIA-Produto HRC

Investigação Level 3 de continuação: fecha a validação pendente antes de
decidir se a PIA-Produto 2422.2020 pode virar âncora oficial. **Não
implementa nada** — `preco_domestico_hrc_mensal_v2()` e o CSV curado
continuam inalterados.

## 1. Conceito PIA — confirmado contra documentação oficial do IBGE

Fonte: "Notas técnicas" oficiais da PIA-Produto (IBGE, *Pesquisa
Industrial*, v.29 n.2, Produto, 2010 — mesmo desenho conceitual da tabela
7752 atual, que reusa as mesmas variáveis 864/1982 confirmadas ao vivo).

- **FACT** (citação verbatim): *"Quantidade vendida no ano - quantidade
  total do produto vendido no ano, pela unidade local, independentemente
  de ter sido produzido no ano ou na unidade local, desde que produzido
  pela empresa"*. Nenhuma menção a mercado interno/externo.
- **FACT** (citação verbatim): *"Vendas realizadas no ano - receita
  líquida de vendas do produto no ano, inclusive a de produtos que são
  fabricados em outras unidades locais da mesma empresa. Não inclui a
  revenda de mercadorias adquiridas de outras empresas."*
- **FACT** (citação verbatim, definição de receita líquida): *"receita
  bruta das vendas de mercadorias produzidas pela empresa..., deduzidos
  os impostos incidentes sobre estas vendas (os que guardam
  proporcionalidade com valor de venda, tais como: ICMS, IPI, ISS,
  PIS/Pasep, Cofins, Simples Nacional, etc.) e as vendas canceladas,
  abatimentos e descontos incondicionais."*
- **FACT**: em nenhum ponto do documento (7 páginas, conceituação
  completa de variáveis investigadas e tabuladas) existe uma variável ou
  quebra que separe mercado interno de exportação a nível de produto. A
  pesquisa é objetivamente desenhada para TOTAL (interno + exportação
  combinados) — confirmado pela ausência total de qualquer campo
  correspondente, não inferido por omissão.
- **FACT** (reforça a leitura acima): um dos dois objetivos declarados da
  pesquisa (página 1) é *"Propiciar informações para a análise articulada
  dos fluxos de produção interna e do comércio externo de produtos
  industriais"* — ou seja, o próprio IBGE desenha a PIA-Produto para ser
  **cruzada** com estatística de comércio exterior (Comex), não para já
  vir separada internamente. Isso valida diretamente a abordagem usada
  nesta pesquisa (cruzar com Comex Stat).
- **FACT**: "Valor das vendas" tabulado corresponde a vendas realizadas
  **diretamente pelas unidades locais produtivas industriais** — exclui
  vendas de departamentos comerciais/administrativos separados. Boa
  propriedade para comparabilidade com paridade de importação (nível
  fábrica, não varejo).
- **DOC** (não FACT — documento é da edição 2010; as edições 2014-2023 da
  tabela 7752 usam as mesmas variáveis 864/1982, mas o texto conceitual
  detalhado das edições mais recentes não foi acessado diretamente,
  bloqueado por 403 em `ibge.gov.br`): assume-se, por estabilidade
  histórica de desenho de pesquisa e por reuso do mesmo ID de variável,
  que a definição não mudou entre 2010 e 2023 — não confirmado edição a
  edição.
- **UNKNOWN**: se a cobertura amostral (que já era 87% do total das
  vendas industriais em 2010) mudou materialmente ano a ano dentro da
  janela 2014-2023 especificamente para a classe siderúrgica.

**Conclusão da seção**: confirmado que `quantidade_vendida`/`receita_
líquida_de_vendas` da PIA-Produto são totais (mercado interno +
exportação), não domésticos puros. A pergunta de materialidade (seção
seguinte) é, portanto, real e não hipotética.

## 2-3. Exposição a exportação — resultado quantitativo

Cruzamento PIA-Produto (categoria 54849) × Comex Stat exportação (cesta
`NCM_BOBINA_QUENTE`, 13 NCMs já validados pelo projeto; também calculado
sem o código "com_relevo" 72081000 — resultado praticamente idêntico,
diferença <0,1 p.p. em todos os anos, porque é um produto de nicho de
baixo volume). Reproduzível via
`scripts/research/pia_hrc_export_exposure.py`.

Correspondência NCM↔Prodlist: **INFERENCE**, não FACT — não foi
localizada uma tabela de correspondência oficial NCM↔Prodlist acessível
nesta pesquisa (haveria um "Anexo" na publicação completa da PIA-Produto,
não obtido). O raciocínio usado: os 13 NCMs de `NCM_BOBINA_QUENTE` cobrem
faixas "decapada" (7208.25-27, decapagem é tratamento de superfície, não
revestimento) e "não decapada" (7208.36-39) — nenhuma das duas envolve
revestimento metálico/pintura, então ambas deveriam cair em "não
revestidos" (2422.2020), não em "revestidos" (2422.2035/2422.2160). Só
"com_relevo" (72081000, chapa xadrez) é fisicamente distinta e
provavelmente cai num código Prodlist próprio não identificado aqui.

**Resultado** (`export_share_qty = export_t / qtd_pia_t`, por ano):

| Ano | Qtd. vendida PIA (t) | Export. Comex (t) | export\_share\_qty |
|---|---|---|---|
| 2014 | 4.621.070 | 1.131.808 | 24,5% |
| 2015 | 4.696.041 | 2.001.077 | **42,6%** |
| 2016 | 4.052.308 | 1.499.560 | 37,0% |
| 2017 | 4.638.307 | 1.619.788 | 34,9% |
| 2018 | 5.054.072 | 1.312.932 | 26,0% |
| 2019 | 4.325.679 | 1.139.167 | 26,3% |
| 2020 | 3.630.153 | 667.342 | 18,4% |
| 2021 | 4.496.777 | 659.152 | 14,7% |
| 2022 | 4.206.224 | 1.182.349 | 28,1% |
| 2023 | 3.567.327 | 443.768 | **12,4%** |

**Materialidade**: mínimo 12,4%, mediana 26,2%, máximo 42,6%. **Nenhum
ano fica abaixo de 10%; 7 dos 10 anos ficam acima de 20%.** Correlação
com o ano: -0,70 (tendência de queda moderada, não monotônica — pico em
2015, mínimo em 2023, sem outlier formal por IQR). Isso está muito longe
de desprezível: por definição do próprio critério da tarefa, a exposição
cai quase sempre na faixa ">20%", nunca na faixa "<5%".

## 4. Sensibilidade do preço doméstico — SOMENTE indicativa

**Compatibilidade contábil avaliada, não assumida**: subtrair FOB
(Comex, USD, na data de despacho aduaneiro) da receita líquida PIA (R$,
reconhecida no ano-calendário de venda pela unidade local) tem três
incompatibilidades reais, nenhuma delas resolvida nesta pesquisa:
(a) câmbio usado é uma média anual simples, não a taxa efetiva de cada
embarque; (b) possível descasamento de tempo entre venda reconhecida
(PIA) e despacho aduaneiro (Comex) perto da virada do ano; (c) a
"receita líquida" da PIA já é líquida de ICMS/IPI/PIS-Cofins só na parte
doméstica (a parcela de exportação já é imune a esses tributos por
desenho constitucional — não há dupla-contagem aí, mas não há garantia de
que o valor faturado reconhecido pela empresa bate exatamente com o FOB
declarado na exportação, que pode diferir por Incoterm, frete interno
até o porto, ou entidade faturadora).

Por isso, o cálculo abaixo é rotulado explicitamente **SENSIBILIDADE**,
nunca oficial:

```
domestic_quantity_approx = qtd_pia_t - export_t
domestic_revenue_approx  = receita_pia_rs - (export_fob_usd * cambio_medio_anual)
preco_domestico_aprox    = domestic_revenue_approx / domestic_quantity_approx
```

| Ano | PIA blended (R$/t) | Export unit. (R$/t) | Aprox. doméstico (R$/t, SENSIBILIDADE) | Delta vs blended |
|---|---|---|---|---|
| 2014 | 1.757,59 | 1.328,60 | 1.896,75 | +7,9% |
| 2015 | 1.474,99 | 1.380,93 | 1.544,83 | +4,7% |
| 2016 | 1.560,70 | 1.273,95 | 1.729,15 | +10,8% |
| 2017 | 1.896,30 | 1.619,06 | 2.045,06 | +7,8% |
| 2018 | 2.234,10 | 2.202,22 | 2.245,29 | +0,5% |
| 2019 | 2.406,92 | 1.936,40 | 2.575,13 | +7,0% |
| 2020 | 2.840,67 | 2.475,75 | 2.922,86 | +2,9% |
| 2021 | 5.644,69 | 4.926,39 | 5.768,07 | +2,2% |
| 2022 | 5.393,31 | 4.390,17 | 5.785,55 | +7,3% |
| 2023 | 4.844,33 | 3.735,43 | 5.001,87 | +3,3% |

**Leitura qualitativa** (a única com confiança suficiente para este
nível de dado): em **todos os 10 anos**, o preço unitário de exportação
ficou abaixo do preço PIA combinado (interno+exportação) — ou seja, as
exportações de HRC saíram consistentemente mais baratas que a média
combinada, e por isso remover o volume/receita de exportação **empurra o
preço doméstico aproximado para CIMA** do preço PIA combinado (nunca para
baixo), em magnitude que varia de +0,5% a +10,8% conforme o ano — sem
padrão fixo (reforça por que um desconto fixo nunca seria defensável).
**Não vira série oficial.** Serve só como indicador de direção e de
risco: o preço PIA bruto (sem ajuste) já é, se algo, um **piso**
conservador da leitura doméstica pura, não um teto.

## 5. Comparação com referências

**Limitação honesta de sobreposição temporal**: PIA cobre 2014-2023;
os benchmarks externos (Argus/SteelOrbis, adendo anterior) e a âncora
corporativa V2 cobrem só 2025-2026. **Não existe nenhum ano em comum
entre as três fontes** — qualquer comparação de nível cruza um hiato de
pelo menos 2 anos e não isola tendência de câmbio/ciclo de preço do
período entre elas. Reportado explicitamente para não fingir uma
comparação mais direta do que ela é.

Com essa ressalva: PIA 2023 (último ano disponível) = R$4.844/t
(combinado) a R$5.002/t (aproximação doméstica, SENSIBILIDADE). A âncora
corporativa V2 2025Q2-2026Q2 = R$4.951-5.378/t. Os benchmarks externos
HRC-específicos de 2025-2026 (Argus/SteelOrbis) = R$3.600-4.560/t. **A
leitura PIA (mesmo a versão bruta, sem ajuste de exportação) fica entre
os dois** — mais alta que os benchmarks comerciais recentes, mais baixa
que a âncora corporativa recente — o que é consistente com a hipótese
de que a âncora corporativa "Siderurgia" está inflada por mix de produto
(achado do adendo anterior) e que a PIA (produto-específica, mas
destino-misto) fica estruturalmente entre as duas leituras. Não dá para
separar quanto do gap é ciclo temporal (2023→2025-26) e quanto é mix de
produto sem mais dados — mas a ordenação (comercial < PIA < corporativo)
é o que se esperaria se ambas as hipóteses (mix de produto na âncora
corporativa, mix de destino na PIA) forem parcialmente verdadeiras ao
mesmo tempo, não mutuamente excludentes.

**Veredito da seção**: o preço PIA HRC parece **(a) próximo do mercado
doméstico em ordem de grandeza**, mas com evidência clara (seção 2-3) de
que uma fração material e variável (12-43%) do volume/receita é
exportação, precificada sistematicamente abaixo da média combinada — não
é **(c)** estruturalmente inconsistente (os níveis são plausíveis e
seguem o ciclo conhecido do aço), mas também não é seguro afirmar que
está **isento** de viés **(b) puxado para exportação**: o viés existe e
tem direção conhecida (puxa o combinado para BAIXO do doméstico puro),
só não tem magnitude precisa o bastante para corrigir com confiança.

## 6. Decisão sobre as opções

**OPTION A (usar PIA HRC diretamente como âncora, sem qualificação) —
NÃO RECOMENDADA.** A exposição a exportação é material e variável
(12-43%, mediana 26,2%) — longe de desprezível. Tratar a série como
"preço doméstico" sem qualificação seria uma afirmação não sustentada
pela evidência.

**OPTION B (PIA HRC pode ser âncora, mas permanece PROXY por misturar
destino doméstico/exportação) — RECOMENDADA.** Espelha exatamente como o
projeto já trata a âncora corporativa hoje (PROXY por mix de produto) —
mesma disciplina, motivo diferente (mix de destino, não mix de produto).
A vantagem real da PIA sobre a âncora corporativa atual (especificidade
de produto: HRC genuíno, não "Siderurgia" inteira) permanece válida e
não é anulada pela ressalva de exportação — só significa que PIA precisa
de SEU PRÓPRIO selo de PROXY, com motivo documentado, não um selo
herdado do mix de produto que ela justamente resolve.

**OPTION C (só benchmark de validação, nunca âncora) — alternativa mais
conservadora, também defensável**, especialmente dado o hiato temporal
da seção 5 (nenhum ano em comum com o período atualmente publicável).

**OPTION D (algum ajuste de exportação defensável) — NÃO RECOMENDADA
AGORA.** A seção 4 mostra que um ajuste é qualitativamente coerente
(direção sempre a mesma) mas não tem precisão suficiente (câmbio médio
anual em vez de mensal/por-embarque, sem confirmação de que receita PIA
e FOB Comex são estritamente comparáveis linha a linha) nem estabilidade
(a fração de exportação varia de 12% a 43% sem tendência limpa) para virar
um ajuste oficial. Fica registrado como direção de pesquisa futura, não
como opção pronta para implementar.

## PROPOSED DOMESTIC PRICE ARCHITECTURE (avaliação, seção 7 da tarefa)

Arquitetura proposta pela tarefa: PIA-Produto HRC anual → âncora de
nível → IPP 242-Siderurgia mensal → interpolação/extrapolação mensal,
com reancoragem quando novo ano PIA sair.

**Avaliação — parcialmente defensável, com duas ressalvas reais:**

1. **O mecanismo em si não é novo**: encadear um nível confirmado por
   IPP até a próxima confirmação é exatamente o que
   `encadear_preco_domestico_mensal` já faz hoje para a âncora trimestral
   corporativa (ADR 0002, já aprovado). Aplicar o mesmo mecanismo a uma
   âncora anual em vez de trimestral não é uma técnica estatística nova
   — é o mesmo método em cadência mais longa. Defensável nesse sentido.
2. **Mas a resolução piora**: hoje, dentro do trimestre confirmado, o
   nível fica constante por 3 meses antes de qualquer encadeamento. Com
   âncora ANUAL, o nível ficaria constante por até 12 meses antes de
   qualquer variação de IPP — perde granularidade dentro do próprio ano
   observado, não só no período extrapolado. Deveria ser declarado
   explicitamente como uma característica da âncora anual, não escondido.
3. **Defasagem de ~2 anos muda o caráter da série**: a PIA 2023 só foi
   divulgada em meados de 2025. Isso significa que, para QUALQUER mês
   recente/atual, a PIA nunca vai estar "confirmada" a tempo — o mês mais
   recente estaria sempre em extrapolação IPP de um nível de pelo menos
   1-2 anos atrás, um horizonte de extrapolação muito mais longo que o
   caso trimestral de hoje (tipicamente 0-3 meses de hold-flat/IPP antes
   do próximo trimestre confirmar). Isso não invalida a arquitetura para
   HISTÓRICO PROFUNDO, mas a torna estruturalmente inadequada como fonte
   PRINCIPAL para os meses mais recentes/atuais — recomenda-se
   explicitamente um desenho **híbrido**: PIA-âncora (com IPP) para o
   período histórico já coberto pela PIA (2014-2023, alinhado com a
   janela `EXPERIMENTAL` de política de importação já definida em
   ADR 0009 para 2012-01 a 2022-03), e âncora corporativa trimestral
   (Usiminas+CSN) para 2022-04 em diante (alinhado com a janela
   `PUBLICATION_GRADE` já definida no mesmo ADR) — reaproveitando a
   mesma filosofia de duas trilhas que o projeto já usa para política
   comercial, em vez de forçar uma fonte única para todo o histórico.
4. **Revisão retroativa não tem mecanismo hoje**: "quando novo ano PIA
   for divulgado, reancorar/revisar meses provisórios" implica revisar
   PUBLICADOS já emitidos. O projeto tem taxonomia de proveniência
   (OBSERVADO/CALCULADO/ESTIMADO/PROXY, vintage/cutoff) mas **não** um
   mecanismo de republicação/revisão de `reference_period` já publicado
   — isso seria uma decisão de design nova (como versionar, como
   comunicar a revisão, se republica silenciosamente ou gera um vintage
   novo), não uma consequência automática de adotar a PIA. Fica como
   questão em aberto, não resolvida aqui.

**Veredito**: estatisticamente defensável como MECANISMO (reusa técnica
já aprovada), mas só recomendável na variante HÍBRIDA (item 3) e só após
uma decisão própria sobre revisão retroativa (item 4) — não como
substituição direta e completa da âncora corporativa atual em toda a
janela.

## EXPECTED HISTORICAL COVERAGE (seção 8 da tarefa)

Se adotada a arquitetura híbrida (PIA 2014-2022-03 + corporativa
2022-04+):

- **Primeira data mensal possível**: 2014-01 (mesmo início da cobertura
  PIA/Comex usada nesta pesquisa; tecnicamente a série PIA-Produto existe
  desde 1998, mas a tabela SIDRA 7752 atual só disponibiliza 2014-2023 —
  cobertura anterior exigiria uma tabela SIDRA diferente/descontinuada,
  não investigada aqui).
- **Último mês com âncora PIA observada**: 2023-12 (ou 2022-03, se o
  corte for alinhado à fronteira `EXPERIMENTAL`/`PUBLICATION_GRADE` já
  aprovada, deixando 2022-04 em diante inteiramente a cargo da âncora
  corporativa).
- **Meses extrapolados/provisórios (se PIA fosse usada isoladamente, sem
  a variante híbrida)**: de 2024-01 até o mês corrente — hoje isso já
  seriam mais de 30 meses de extrapolação/hold-flat sobre um nível de
  pelo menos 2 anos de idade, crescendo a cada mês até a próxima PIA
  sair. Reforça por que a variante híbrida (§7) é a recomendável, não a
  PIA isolada cobrindo tudo.
- **Quanto a cobertura melhora vs. os 15 meses atuais**: potencialmente
  muito — de 15 meses (2025-04 a 2026-06) para até ~110 meses (2014-01 a
  2026-06), a maior parte com `publication_status=EXPERIMENTAL` (2014-01
  a 2022-03, alinhado ao lado de importação, que já é `EXPERIMENTAL`
  nessa janela por ADR 0009) e uma fração menor `PUBLICATION_GRADE`
  (2022-04 em diante, sujeita à curadoria trimestral ainda pendente,
  seção anterior deste documento). **2014→presente é alcançável em
  princípio** para a trilha `EXPERIMENTAL` — não é um teto teórico, é uma
  combinação de fonte já existente (PIA, Comex) com decisão de design
  ainda pendente (adotar a arquitetura híbrida, decidir revisão
  retroativa).

## IMPLEMENTATION BLOCKED (adendo)

Tudo que já estava bloqueado no adendo anterior continua bloqueado. Além
disso, especificamente por esta investigação:

- Qualquer subtração FOB-de-receita-PIA como número oficial (a coluna
  `preco_domestico_aprox_rs_t_SENSIBILIDADE` é só leitura de risco, nunca
  entra em cálculo publicado).
- Qualquer arquitetura PIA+IPP (híbrida ou não) implementada sem decisão
  explícita sobre revisão retroativa de `reference_period` já publicado.
- Qualquer promoção da janela 2014-2022-03 a `PUBLICATION_GRADE` — se
  adotada, essa janela nasceria `EXPERIMENTAL`, alinhada à mesma
  classificação já aprovada para o lado de importação nesse período
  (ADR 0009), não `PUBLICATION_GRADE`.
- Confirmação da correspondência exata NCM↔Prodlist 2422.2020 (hoje
  INFERENCE, não FACT) antes de qualquer uso além de indicador de
  materialidade.

## Artefato desta investigação

- `scripts/research/pia_hrc_export_exposure.py` — reproduz o cruzamento
  PIA×Comex export e a tabela de sensibilidade completa; salva
  `data/processed/pia_hrc_export_exposure.csv` (gitignored, como o resto
  de `data/processed/`).
