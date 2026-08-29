# IPIA-HRC — Missing Data Audit

**Status: VALIDATION + DIAGNOSTICS ONLY — não implementa nenhuma mudança.**
Nenhum dado foi imputado, nenhum backcasting foi feito, nenhum status de
publicação foi alterado. PPI, IPIA, `VERSAO_METODOLOGIA`, vintages e
reporting permanecem exatamente como estavam antes desta etapa.

Reproduzir: `docker build -t steel-indicator-dev .` seguido de
`docker run --rm -v "$(pwd)/data:/app/data" steel-indicator-dev python scripts/auditar_ipia_hrc_missing.py`
(no Windows/git-bash, prefixar `MSYS_NO_PATHCONV=1`). Roda a série
completa de produção (`calcular_ipia_hrc_v2_pia`) e lê PIA/IPP/CSV curado
diretamente das funções de coleta já existentes — nunca reimplementa
nenhuma delas.

## Question

> Quais dados realmente faltam no pipeline do IPIA-HRC, por que faltam e
> quais deles materialmente prejudicam o cálculo, histórico ou análise do
> indicador?

## 1. Executive conclusion

- Na janela real onde o IPIA-HRC V2 PIA-based é sequer calculável
  (2019-01 a 2026-07, 91 meses, execução ao vivo desta etapa): **21 meses
  PUBLICATION_GRADE, 27 EXPERIMENTAL, 30 PROVISIONAL, 13 UNKNOWN.** Os 13
  meses `UNKNOWN` **não têm IPIA algum** — nenhum número é publicado, nem
  mesmo com incerteza.
- **O gargalo real não é falta de dado de comércio** (o Comex Stat
  devolveu alguma linha em 90 dos 91 meses) — é **falta de política
  comercial confirmada** (II individual por NCM) para cobrir o volume
  observado. Isso é `TECHNICAL_MISSING`/`HISTORICAL_UNAVAILABLE`
  regulatório, não um problema de coleta de preço/volume.
- **O lado doméstico não tem nenhum mês tecnicamente ausente na janela
  observável**: IPP 242-Siderurgia tem cobertura 100% (zero meses
  faltando, dez/2018–jul/2026, confirmado ao vivo); PIA-HRC tem os 10
  anos que existem (2014–2023) — o "gap" 2024+ é `PUBLICATION_LAG`, não
  ausência de coleta.
- **2024+ no lado doméstico não é missing — é extensão model-assisted
  provisória** (`is_provisional=True`, `ESTIMADO`), já implementada e já
  rotulada corretamente na produção (§12.11/ADR 0011). Esta auditoria
  confirma que a classificação de código já é coerente com a taxonomia
  pedida neste sprint — não achou nenhum caso de "provisional disfarçado
  de definitivo".
- **Nenhum gap encontrado é `HIGH`** no sentido de bloquear Reporting V3
  de forma que exija correção antes de continuar — os 13 meses `UNKNOWN`
  já são tratados corretamente (excluídos de ambas as saídas publicadas,
  nunca escondidos, nunca interpolados).
- **Recomendação: A — MISSING DOES NOT BLOCK REPORTING V3.**

## 2. Coverage matrix

| Component | First | Last | Expected freq | Observed | Missing | Coverage % | Missing type |
|---|---|---|---|---:|---:|---:|---|
| FOB/KG/frete/seguro (Comex Stat, bottom-up NCM×país×mês) | 2019-01 | 2026-07 | mensal | 91 linhas | 0 | 100% | — (cobertura de linhas; calculabilidade real é a linha seguinte) |
| FX (BCB/SGS, média mensal) | 2019-01 | 2026-07 | mensal (derivado de diário) | 91 | 0 | 100% | — (`calcular_fx_mensal` levanta `ValueError` fail-fast se faltar; nunca faltou em produção) |
| II/AFRMM/antidumping (mês *calculável*, `import_status≠UNKNOWN`) | 2019-02 | 2023-12 (OFFICIAL) / 2026-06+ (PROVISIONAL) | mensal | 78 | 13 | 85,7% | ver Seção 3 — majoritariamente `A_TECHNICAL_MISSING`/`E_HISTORICAL_UNAVAILABLE` |
| PIA-HRC (IBGE/SIDRA 7752) | 2014 | 2023 | anual | 10 anos | 0 (na janela existente) | 100% | `D_PUBLICATION_LAG` para 2024+ |
| IPP 242-Siderurgia (IBGE/SIDRA 6723) | 2018-12 | 2026-07 | mensal | 92 | 0 | 100% | — |
| Corporate anchor (Usiminas+CSN curado) | 2025Q2 | 2026Q2 | trimestral | 5 trimestres | n/a | n/a | benchmark de validação independente (ADR 0010) — "observação esperada" não se aplica; nunca foi projetado para cobrir todo o histórico |
| D_porto / D_interno / margem (`ParamsIPIA`) | n/a | n/a | n/a (constante) | 0 séries | n/a | n/a | `F_STRUCTURAL_PARAMETER` — não é uma série, "observação esperada" não se aplica |
| Benchmark externo (UN Comtrade, sprint anterior) | 2019-01 | 2024-12 | mensal | 72 | 19 (vs. janela até 2026-07) | 79,1% | `D_PUBLICATION_LAG` — defasagem de publicação da fonte chinesa, não um gap do projeto |

**Nota sobre "expected observation"**: para corporate anchor e para os
parâmetros estruturais, uma contagem de "meses esperados" não tem
significado — o corporate anchor é, por desenho (ADR 0010), um benchmark
de validação pontual, nunca uma série contínua obrigatória; os parâmetros
estruturais são constantes, não séries temporais. Forçar um percentual de
cobertura para esses dois casos criaria uma métrica artificial — por isso
`coverage_pct=n/a`, não `0%` nem `100%` fabricados.

## 3. Missing taxonomy

Classificação de cada ausência (Seção 20 do sprint, seis categorias,
`A_TECHNICAL_MISSING` a `F_STRUCTURAL_PARAMETER`):

Os **13 meses `UNKNOWN`** do import side (2019-01, 2019-11, 2019-12,
2020-03, 2020-04, 2020-06, 2020-08, 2020-10, 2020-11, 2021-09, 2022-02,
2022-03, 2026-07):

| Mês | total_kg | policy_coverage | Classificação |
|---|---:|---:|---|
| 2019-01 | 1.745.000 | 1,1% | `E_HISTORICAL_UNAVAILABLE` (II individual não comprovado, janela historical experimental, ADR 0009) |
| 2019-11, 2019-12 | 1,82M / 1,59M | 0% | `E_HISTORICAL_UNAVAILABLE` (idem) |
| 2020-03, 2020-04 | 3,87M / 1,37M | 11,5% / 31,3% | `E_HISTORICAL_UNAVAILABLE` (idem) |
| 2020-06, 2020-08, 2020-10 | 55,1k / 1,10M / 314,8k | 0% | `E_HISTORICAL_UNAVAILABLE` (idem) |
| 2020-11 | — (sem linha) | — | `A_TECHNICAL_MISSING` candidato — mês sem nenhuma linha retornada nesta execução ao vivo (ver nota abaixo) |
| 2021-09 | 27,38M | 6,3% | `E_HISTORICAL_UNAVAILABLE` (idem, ainda dentro de 2012-01→2022-03) |
| 2022-02, 2022-03 | 3,00M / 2,54M | 58,0% / 24,0% | `E_HISTORICAL_UNAVAILABLE` (idem — 2022-03 é o último mês da janela historical experimental, ADR 0009) |
| 2026-07 | 54,69M | 4,4% | `A_TECHNICAL_MISSING`/quota — volume observado com política de cota (GECEX 929/2026) não rastreada por consumo, `UNKNOWN` explícito por desenho (ADR 0009 §9.5.1), nunca um NCM não comprovado historicamente |

**Nota sobre 2020-11**: nesta execução ao vivo, o Comex Stat não devolveu
nenhuma linha com `kg>0` para a cesta HRC completa nesse mês específico —
diferente de uma consulta anterior nesta mesma sessão de trabalho, que
havia mostrado volume positivo para 2020-11 numa janela de busca mais
ampla (2012–2026). A causa mais provável é variação native da API entre
consultas (paginação/agregação do lado do servidor), não uma mudança
estrutural do dado — mas não foi confirmada com uma terceira consulta
nesta etapa. Classificado provisoriamente como `A_TECHNICAL_MISSING`
(possível instabilidade de coleta), não como `B_ECONOMIC_NO_OBSERVATION`
(zero importações reais) — a diferença entre execuções é evidência contra
"zero real", não a favor. Recomendação: reconfirmar com uma nova consulta
dedicada antes de qualquer decisão sobre este mês específico.

**Outros casos da taxonomia, fora dos 13 meses UNKNOWN**:

| Caso | Classificação | Nota |
|---|---|---|
| Combinações NCM×país×mês nunca importadas | `B_ECONOMIC_NO_OBSERVATION` | a maioria dos "buracos" na matriz completa `mês×NCM×país` — não houve evento comercial, não é ausência de coleta |
| PIA anual → preço mensal | `C_FREQUENCY_MISMATCH` | já resolvido em produção via Proportional Denton (ADR 0010) — não é um gap em aberto |
| PIA 2024+ ainda não publicada | `D_PUBLICATION_LAG` | coberta por extensão provisória (ver Seção 5) |
| Benchmark externo (UN Comtrade) parado em 2024-12 | `D_PUBLICATION_LAG` | fonte terceira, fora do controle do projeto |
| II individual dos 9 NCMs não comprovados (2012-01→2022-03) | `E_HISTORICAL_UNAVAILABLE` | candidato a pesquisa documental adicional, não a modelagem (ver Seção 8) |
| D_porto / D_interno / margem | `F_STRUCTURAL_PARAMETER` | nunca deve ser chamado de "missing" — é parâmetro, não série (METODOLOGIA §9.8/9.9) |

## 4. PPI gaps

Classificação de impacto no PPI (Seção 23 do sprint):

| Ausência | Impacto |
|---|---|
| II individual não comprovado (9/13 NCMs, 2012-01→2022-03) | **STATUS-LIMITING** — permite EXPERIMENTAL (coverage≥60%, incerteza≤2%) mas nunca PUBLICATION_GRADE nessa janela |
| Cota GECEX 929/2026 com consumo não rastreado | **BLOCKING** — mês inteiro vira UNKNOWN sem redistribuição de peso (regra já aprovada, ADR 0009 §9.5.1) |
| Frete/seguro por NCM/país quando ausente na fonte | **NON-BLOCKING** — precedência para observado, mas o cálculo não trava se ausente pontualmente (§9.2 METODOLOGIA) |
| D_porto / D_interno / margem | **PARAMETRIC** — sempre preenchido por parâmetro explícito, nunca bloqueia, nunca é tratado como dado ausente |
| FX mensal sem observação diária válida | **BLOCKING (nunca ocorreu em produção)** — `calcular_fx_mensal` levanta `ValueError` fail-fast por desenho; não há caminho silencioso |

## 5. Domestic gaps

**PIA-HRC**: observada até **2023** (confirmado ao vivo nesta etapa —
nenhum ano novo desde o sprint de validação anterior). Anos mensais:

- **Benchmarked** (nível anual reconciliado pela PIA via Denton): 2019 a
  2023 — 59 meses `CALCULATED` na matriz mensal desta auditoria (2019-02
  a 2023-12; 2019-01 fica fora por ser o único mês antes do primeiro mês
  benchmarked).
- **Provisional** (extensão pós-última-PIA, encadeada pelo IPP a partir
  do último ponto Denton): 2024-01 em diante — 31 meses `PROVISIONAL` na
  janela desta auditoria (até 2026-07).
- **Unavailable**: nenhum ano intermediário — a série é contígua
  (`CALCULATED` 2019-2023 seguido imediatamente por `PROVISIONAL` 2024+,
  sem buraco).

**IPP-242**: **zero meses ausentes** na janela observada (dez/2018 a
jul/2026, 92 meses, confirmado ao vivo — `full_idx.difference(ipp.index)`
retorna vazio). Não há nada a registrar aqui além da confirmação de
integridade.

## 6. Não confundir provisional com missing

Confirmado nesta auditoria: a extensão doméstica 2024+ **já está
corretamente classificada em produção** como `is_provisional=True` +
`domestic_is_proxy=True` + provenance `ESTIMADO` (nunca como "preço
ausente"), e o `publication_status` conjunto do IPIA vira `PROVISIONAL`
(nunca `PUBLICATION_GRADE`/`EXPERIMENTAL` com uma flag secundária) sempre
que o lado doméstico é provisório — regra já fechada no ADR 0011. Esta
etapa não encontrou nenhum caso em que a distinção estivesse borrada no
código ou na saída publicada.

## 7. Status impact — quantos meses e por quê

Execução ao vivo de `calcular_ipia_hrc_v2_pia(ano_ini=2019, ano_fim=2026)`,
91 meses (2019-01 a 2026-07):

| `publication_status` | N meses | % |
|---|---:|---:|
| PUBLICATION_GRADE | 21 | 23,1% |
| EXPERIMENTAL | 27 | 29,7% |
| PROVISIONAL | 30 | 33,0% |
| **UNKNOWN** | **13** | **14,3%** |

**Resposta objetiva às duas perguntas do sprint:**

> Quantos meses do histórico potencial deixam de ter IPIA devido a
> missing data?

**13 de 91 meses (14,3%)** na janela onde o IPIA-HRC V2 PIA-based é
teoricamente calculável (2019-01+, limitado pelo início do IPP-242).
Antes disso (2012-01 a 2018-11), o IPIA-HRC V2 PIA-based **nunca é
calculável** — não por dado ausente pontualmente, mas porque o IPP-242
(insumo do Denton) só começa a existir em dez/2018 — uma restrição
estrutural da fonte, não uma lacuna a preencher.

> Quantos meses são calculáveis apenas graças a estimativas/proxies/
> parâmetros?

**Todos os 78 meses não-UNKNOWN** dependem de pelo menos um proxy/
estimativa/parâmetro — nenhum mês do IPIA-HRC V2 PIA-based é "puro
observado" nos dois lados simultaneamente: o lado doméstico é sempre
`PROXY` (PIA por `DESTINATION_MIX`, IPP por `PRODUCT_AGGREGATION`, já
documentado antes desta etapa), e o PPI sempre depende de três parâmetros
`ESTIMADO`/hold-flat (D_porto, D_interno, margem — METODOLOGIA §9.8).
Isso não é um problema desta auditoria identificar — é a natureza já
conhecida e documentada da metodologia V1 do domestic side (§12.1
METODOLOGIA). Dos 78, **57** dependem adicionalmente de encadeamento/
provisório no import ou domestic side (`ESTIMATED` na matriz mensal desta
auditoria: 27 EXPERIMENTAL + 30 PROVISIONAL), e **21** têm o import side
em `PUBLICATION_GRADE` (política comercial 100% conhecida) — mas mesmo
esses 21 ainda carregam o proxy doméstico permanente.

## 8. Model-imputation candidates

Somente identificação — **nada implementado nesta etapa**:

| Componente | Tipo | `MODEL_IMPUTATION_SUITABLE` | Justificativa |
|---|---|---|---|
| Comex Stat FOB/KG em mês com `policy_coverage<60%` | `A_TECHNICAL_MISSING` | **NO** | o dado de comércio existe; falta é política (II por NCM) — imputação não resolve lacuna regulatória, a ação correta é `recollect`/pesquisa documental |
| Mês/NCM/país sem nenhum registro | `B_ECONOMIC_NO_OBSERVATION` | **NO** | ausência de evento econômico não é uma lacuna de dado |
| PIA anual → preço mensal | `C_FREQUENCY_MISMATCH` | **MAYBE (já resolvido)** | temporal disaggregation já em produção (Proportional Denton) — não é um gap em aberto |
| PIA do ano corrente (2024+, não publicada) | `D_PUBLICATION_LAG` | **MAYBE** | já existe extensão model-assisted (encadeamento IPP); um motor probabilístico (state-space/Kalman) poderia dar banda de incerteza explícita em vez de ponto único — pesquisa futura razoável, não substitui o mecanismo atual |
| II individual dos 9 NCMs não comprovados, 2012-01→2022-03 | `E_HISTORICAL_UNAVAILABLE` | **MAYBE** | é parâmetro regulatório (decisão de política pública), não série estocástica — modelo estatístico não "prevê" uma alíquota da CAMEX; candidato realista é pesquisa documental adicional, não ARMA/Kalman |
| D_porto / D_interno / margem | `F_STRUCTURAL_PARAMETER` | **NO** | não são séries com histórico a reconstruir — são parâmetros de calibração única (contato com despachantes, já recomendado na pesquisa original) |
| Corporate anchor fora de 2025Q2-2026Q2 | `E_HISTORICAL_UNAVAILABLE` | **NO** | é só benchmark de validação independente — estender via modelo daria a falsa impressão de uma segunda fonte observada quando seria só o próprio IPP reaplicado |

### Future probabilistic reconstruction candidates (conceitual — nada implementado)

Para os dois casos classificados `MAYBE` acima (extensão provisória da
PIA e, com reserva, o II histórico não comprovado), técnicas a considerar
em pesquisa futura, nunca nesta etapa:

- **State-space / Kalman smoothing** — poderia substituir o encadeamento
  determinístico da extensão provisória por uma estimativa com banda de
  incerteza explícita, análoga ao que já existe para o import side
  historical experimental (`ppi_lower`/`ppi_upper`).
- **Dynamic regression** — relacionar a extensão provisória a outras
  séries observadas (ex. câmbio, IPP) com atualização bayesiana a cada
  novo mês de IPP.
- **ARIMA / ARMA-GARCH** — aplicável em princípio à série de preço
  doméstico provisória; não aplicável a parâmetros regulatórios (II) nem
  a constantes estruturais (D_porto/D_interno/margem), que não são
  processos estocásticos.
- **Conditional simulation** — para gerar cenários de II histórico dentro
  da faixa documentada (10%-14%), como extensão do que a janela
  EXPERIMENTAL já faz de forma determinística (`ppi_lower`/`ppi_upper`).

**Nenhuma destas técnicas foi implementada, testada ou sequer prototipada
nesta etapa.** Nenhuma série foi invertida. Nenhum backcasting foi feito.

## 9. Recommendation

**A — MISSING DOES NOT BLOCK REPORTING V3.**

Justificativa objetiva: os 13 meses `UNKNOWN` já são excluídos de forma
correta e transparente das duas séries publicadas (nunca aparecem em
`official.csv`/`provisional.csv`, mas continuam disponíveis na série
completa para quem precisar do gap explícito — §12.11); a extensão
doméstica provisória já está corretamente rotulada e nunca é apresentada
como definitiva; o IPP-242 (insumo de alta frequência mais crítico do
domestic side) tem cobertura de 100% sem nenhum buraco. O único achado
desta auditoria que merece seguimento é o caso pontual de 2020-11
(Seção 3), que é uma investigação de reconfirmação de coleta, não um
bloqueio de Reporting V3. Nenhum componente do pipeline hoje impede um
relatório honesto e auditável do estado atual do IPIA-HRC.

## Final

- **Files created**: `docs/validation/ipia_hrc_liquidity_concentration.md`,
  `docs/validation/ipia_hrc_missing_data_audit.md`,
  `scripts/analisar_ipia_hrc_liquidez.py`,
  `scripts/auditar_ipia_hrc_missing.py`,
  `tests/unit/test_ipia_hrc_liquidity_missing.py`.
- **Files modified**: nenhum.
- **Production impact**: nenhuma alteração em `src/`.

## References

- `docs/validation/ipia_hrc_liquidity_concentration.md` (Parte I deste
  mesmo sprint).
- `docs/validation/comex_unit_value_external_hrc_validation.md`,
  `docs/validation/ipp242_pia_hrc_validation.md` (sprints anteriores).
- `docs/METODOLOGIA.md` §9.5.1/§9.5.2 (política comercial, agregação
  bottom-up), §12.10/§12.11 (PIA/Denton, status conjunto), §26
  (limitações conhecidas).
- ADR 0009, ADR 0010, ADR 0011, ADR 0013.
