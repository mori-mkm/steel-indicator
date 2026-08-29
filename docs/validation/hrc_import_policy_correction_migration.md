# IPIA-HRC — Import Policy Correction Migration

**Status: IMPLEMENTED.** Decisão aprovada pelo usuário: **B — PARTIAL
IMPLEMENTATION, VERIFIED policy only**. Este documento é o registro da
migração — a evidência completa (fontes, hierarquia, contrafactual
pré-implementação) permanece em
`docs/validation/hrc_import_policy_evidence_hardening.md`, que **não foi
alterado** por esta etapa.

Reproduzir: `docker build -t steel-indicator-dev .` seguido de
`docker run --rm -v "$(pwd)/data:/app/data" steel-indicator-dev python scripts/migrar_hrc_import_policy_correction.py`
(no Windows/git-bash, prefixar `MSYS_NO_PATHCONV=1`).

## Previous implementation

`steel_indicator/parameters/trade_policy.py` (`_ALIQUOTA_2022_TODOS_OS_13`)
atribuía 10,8% a `72082610`, `72082710`, `72083610`, `72083810` a partir
de 2022-04-01, indefinidamente (`valid_to=None`), e não continha nenhuma
regra para uma elevação tarifária sobre `72082690`/`72082790` — esses
dois códigos permaneciam em 10,8% flat para sempre, mesmo após 2026-02-26.

## Verified discrepancy

1. **4 NCMs com alíquota errada** (2022-04-01 em diante): evidência
   oficial confirma 9%, não 10,8% — mesma exceção "limite mínimo de
   elasticidade 275/355 MPa" já corretamente aplicada a `72083910`.
2. **2 NCMs com elevação tarifária não modelada**: `72082690`/`72082790`
   sobem para 25% entre 2026-02-26 e 2027-02-25 (Resolução Gecex nº
   865/2026) — mecanismo **incondicional** (Case A), sem cota, confirmado
   por ausência de colunas `Quota`/`Unidade quota` na fonte oficial para
   essas duas linhas.

## Legal evidence

Reconfirmada **ao vivo, nesta etapa**, antes de qualquer edição de
código (Sec.28 do sprint) — planilha oficial gov.br/mdic/camex idêntica à
usada no validation sprint (mesmo tamanho de arquivo, 1.428.642 bytes):

| NCM | Aba oficial | Alíquota confirmada |
|---|---|---:|
| 72082610 | Anexo I - TEC | 9% |
| 72082710 | Anexo I - TEC | 9% |
| 72083610 | Anexo I - TEC | 9% |
| 72083810 | Anexo I - TEC | 9% |
| 72082690 (elevação) | Anexo IX - DCC | 25%, `Quota='-'`, `Unidade quota='-'` |
| 72082790 (elevação) | Anexo IX - DCC | 25%, `Quota='-'`, `Unidade quota='-'` |

Fonte: <https://www.gov.br/mdic/pt-br/assuntos/camex/se-camex/strat/tarifas/vigentes>
("Anexos I a X da Resolução Gecex nº 272/2021").

## Corrected implementation

### Four-NCM correction

| NCM | old rate | corrected rate | valid_from | valid_to | evidence |
|---|---:|---:|---|---|---|
| 72082610 | 10,8% | **9%** | 2022-04-01 | (aberto) | VERIFIED — Anexo I/II oficial |
| 72082710 | 10,8% | **9%** | 2022-04-01 | (aberto) | VERIFIED — Anexo I/II oficial |
| 72083610 | 10,8% | **9%** | 2022-04-01 | (aberto) | VERIFIED — Anexo I/II oficial |
| 72083810 | 10,8% | **9%** | 2022-04-01 | (aberto) | VERIFIED — Anexo I/II oficial |

Regra temporal — não `NCM -> 9% forever` sem lastro: o histórico
2012-2022-03 desses 4 códigos **permanece `UNKNOWN`**, inalterado (nunca
existiu evidência VERIFIED para esse período; ver "Historical period
intentionally unchanged" abaixo). A correção se aplica **apenas** ao
segmento `valid_from=2022-04-01` já existente na arquitetura — mesmo
padrão `FaixaAliquotaII(ncm, valid_from, valid_to, aliquota, legal_basis)`
de sempre, só o valor e o `legal_basis` mudaram.

### Res. GECEX 865/2026 — regra legal e tratamento

- **Regra legal**: Resolução Gecex nº 865/2026 (24/02/2026), Anexo IX do
  ato consolidado (Res. Gecex nº 272/2021).
- **Vigência**: 2026-02-26 a 2027-02-25 (inclusive).
- **Quota**: **nenhuma** — confirmado explicitamente (Case A) contra a
  fonte oficial, que não lista `Quota`/`Unidade quota` para essas duas
  linhas (ao contrário das 4 linhas da Res. Gecex nº 929/2026, que têm
  volume exato em KG por sub-período).
- **In-quota rate**: não aplicável (não há mecanismo de cota).
- **Out-of-quota rate**: não aplicável — a alíquota de 25% é
  incondicional durante a vigência.
- **Como a incerteza foi tratada**: não há incerteza a tratar neste caso
  — ao contrário da cota Gecex nº 929/2026 (que **permanece intocada**,
  `resolver_ii` continua retornando `UNKNOWN` durante os sub-períodos de
  cota para `72083700`/`72083890`/`72083910`/`72083990`, exatamente como
  antes desta migração), a elevação 865/2026 não tem ambiguidade de fluxo
  — 100% do volume declarado nesses dois NCMs, nesse período, está sujeito
  a 25%, por desenho da própria norma.

Implementação: três segmentos temporais em `_montar_tabela_ii()` (antes
da vigência → 10,8%; durante → 25%; depois → 10,8% novamente), seguindo
exatamente o padrão já usado para a cota 929/2026 (segmentos
`FaixaAliquotaII` antes/depois de uma janela), sem introduzir nenhuma
estrutura de dados nova.

**Nenhuma tarifa média, midpoint, FIFO ou consumo presumido foi usado em
nenhum dos dois casos.**

## Historical period intentionally unchanged

**2012–2022-03 continua `UNKNOWN` para os 9 NCMs não comprovados**
(incluindo os 4 agora corrigidos para o regime 2022-04+, que permanecem
sem evidência VERIFIED para 2012-2022-03). A hipótese estrutural INFERRED
registrada no validation document (padrão `.10`/`.90` sugerindo 10%/12%
historicamente) **não foi promovida a produção** — nenhuma linha nova foi
adicionada a `_ALIQUOTA_2012_CONHECIDA`. Confirmado por teste
(`test_regime_2012_2022_03_permanece_inalterado_para_os_4_codigos_confirmados`
e os 4 testes `test_correcao_9pct_antes_da_vigencia_permanece_unknown`).

## 2020-11

Confirmado no validation sprint anterior: **TRUE_ZERO**, reprodutível (3
consultas independentes concordam). Nenhuma imputação foi feita nesta
etapa nem em nenhuma anterior — nenhuma linha de importação foi criada
artificialmente, nenhuma série foi alterada para preencher esse mês.

## Vintage impact

| | Vintage antiga | Vintage nova |
|---|---|---|
| `vintage_id` | `20260828T213446Z` | `20260829T022116Z` |
| `previous_vintage_id` | `20260827T213900Z` | `20260828T213446Z` |
| `methodology_version` | 1.3 | **1.4** |
| OFFICIAL | 2019-02 a 2023-12 (48 meses) | 2019-02 a 2023-12 (48 meses) |
| PROVISIONAL | 2024-01 a 2026-06 (30 meses) | 2024-01 a 2026-06 (30 meses) |

## OFFICIAL preservation

**Confirmado byte a byte**: os 5 arquivos da vintage antiga
(`manifest.json`, `official.csv`, `provisional.csv`, `import_side.csv`,
`domestic_price.csv`) têm exatamente os mesmos hashes SHA-256 antes e
depois da migração — nenhum arquivo da vintage `20260828T213446Z` foi
tocado. A vintage nova foi criada via `salvar_vintage_ipia_hrc_v2`
(append-only, ADR 0012), nunca por sobrescrita.

Este é o mesmo padrão usado na migração cambial (ADR 0014,
`scripts/migrar_fx_convention_media_mensal.py`): recálculo completo **sem**
`congelado_df` (exceção deliberada ao fluxo rotineiro de
`executar_pipeline_ipia_hrc`, que continua protegendo corretamente contra
revisões rotineiras a partir de agora, com esta vintage nova como base).
**Motivo de revisão classificado como `REGULATORY_SOURCE_CORRECTION`**
(vocabulário do próprio sprint, registrado no CSV de comparação e no
docstring do script de migração) — não há campo de manifest dedicado a
"motivo de revisão" na arquitetura existente, e nenhum foi criado (Sec.12
do sprint: "não crie arquitetura enorme, use o audit trail já existente")
— o mecanismo de audit trail já existente (`methodology_version`,
`previous_vintage_id`, o comentário de changelog em
`VERSAO_METODOLOGIA` no código, e este documento) já registra o motivo de
forma auditável.

## Historical impact

Comparação completa em
`data/processed/validation/hrc_import_policy_correction/import_policy_correction_old_vs_new.csv`
(78 meses, todos comparáveis).

| Métrica | Valor |
|---|---:|
| Meses com PPI alterado | 48 de 78 |
| PPI Δ% — média (só os 48 alterados) | +0,0556% |
| PPI Δ% — mínimo | -0,4889% (2023-04) |
| PPI Δ% — máximo | +5,5956% (2026-03) |
| IPIA Δ pts — média (só os 48 alterados) | -0,0736 pts |
| IPIA Δ pts — mínimo | -6,5222 pts (2026-03) |
| IPIA Δ pts — máximo | +0,5111 pts (2023-04) |
| Meses OFFICIAL (congelados) afetados | **19 de 48** |

### OFFICIAL window — tabela completa (48 meses, 19 alterados)

| Mês | PPI old (R$/t) | PPI corrected (R$/t) | Δ R$/t | Δ % | IPIA old | IPIA corrected | Δ pts | status old | status new |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| 2022-04 | 6.254,54 | 6.250,61 | -3,93 | -0,063% | 90,5335 | 90,5904 | +0,057 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2022-05 | 6.143,01 | 6.140,96 | -2,06 | -0,033% | 97,7300 | 97,7627 | +0,033 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2022-06 | 7.158,72 | 7.131,00 | -27,72 | -0,387% | 82,9190 | 83,2413 | +0,322 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2022-07 | 6.425,36 | 6.422,06 | -3,30 | -0,051% | 87,2763 | 87,3211 | +0,045 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2022-08 | 7.032,35 | 7.016,94 | -15,41 | -0,219% | 75,6399 | 75,8061 | +0,166 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2022-09 | 6.058,18 | 6.058,01 | -0,17 | -0,003% | 83,9205 | 83,9229 | +0,002 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2022-10 | 6.612,30 | 6.611,15 | -1,15 | -0,017% | 75,7324 | 75,7455 | +0,013 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2022-11 | 5.073,87 | 5.072,82 | -1,05 | -0,021% | 97,6536 | 97,6738 | +0,020 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2022-12 | 5.423,51 | 5.422,01 | -1,50 | -0,028% | 89,8500 | 89,8748 | +0,025 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2023-03 | 4.344,66 | 4.344,20 | -0,46 | -0,011% | 114,2817 | 114,2938 | +0,012 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2023-04 | 4.909,70 | 4.885,69 | -24,00 | **-0,489%** | 104,0224 | 104,5334 | **+0,511** | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2023-05 | 3.771,08 | 3.770,02 | -1,06 | -0,028% | 133,3575 | 133,3949 | +0,037 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2023-06 | 4.199,20 | 4.198,58 | -0,61 | -0,015% | 121,3733 | 121,3911 | +0,018 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2023-07 | 3.712,82 | 3.711,98 | -0,84 | -0,023% | 133,6403 | 133,6704 | +0,030 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2023-08 | 4.279,21 | 4.277,43 | -1,78 | -0,041% | 112,0373 | 112,0839 | +0,046 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2023-09 | 4.354,33 | 4.352,43 | -1,90 | -0,044% | 107,4737 | 107,5205 | +0,047 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2023-10 | 4.034,85 | 4.034,08 | -0,78 | -0,019% | 113,6707 | 113,6926 | +0,022 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2023-11 | 3.899,86 | 3.899,61 | -0,25 | -0,006% | 115,9409 | 115,9482 | +0,007 | PUBLICATION_GRADE | PUBLICATION_GRADE |
| 2023-12 | 3.682,00 | 3.681,99 | -0,01 | -0,0004% | 123,8863 | 123,8867 | +0,0004 | PUBLICATION_GRADE | PUBLICATION_GRADE |

Os demais 29 meses OFFICIAL (2019-02 a 2022-03, todos EXPERIMENTAL) e
2023-01/2023-02 têm Δ=0 — nenhum dos 4 NCMs corrigidos teve volume nesses
meses, ou o mês está fora da janela `valid_from=2022-04-01` da correção.

### Largest PPI changes (todos os 48 meses, top 15)

| Mês | PPI old | PPI new | Δ R$/t | Δ % | status |
|---|---:|---:|---:|---:|---|
| 2026-03 | 3.686,27 | 3.892,54 | +206,27 | **+5,5956%** | PROVISIONAL |
| 2023-04 | 4.909,70 | 4.885,69 | -24,00 | -0,4889% | PUBLICATION_GRADE (OFFICIAL) |
| 2024-12 | 5.208,16 | 5.183,72 | -24,44 | -0,4693% | PROVISIONAL |
| 2022-06 | 7.158,72 | 7.131,00 | -27,72 | -0,3872% | PUBLICATION_GRADE (OFFICIAL) |
| 2026-05 | 3.541,50 | 3.533,45 | -8,05 | -0,2273% | PROVISIONAL |
| 2022-08 | 7.032,35 | 7.016,94 | -15,41 | -0,2192% | PUBLICATION_GRADE (OFFICIAL) |
| 2024-02 | 3.860,94 | 3.857,33 | -3,60 | -0,0933% | PROVISIONAL |
| 2025-04 | 4.360,87 | 4.357,35 | -3,52 | -0,0806% | PROVISIONAL |
| 2025-02 | 4.669,32 | 4.666,09 | -3,23 | -0,0692% | PROVISIONAL |
| 2026-01 | 3.887,09 | 3.884,42 | -2,67 | -0,0687% | PROVISIONAL |
| 2022-04 | 6.254,54 | 6.250,61 | -3,93 | -0,0628% | PUBLICATION_GRADE (OFFICIAL) |
| 2025-10 | 4.121,33 | 4.118,74 | -2,59 | -0,0628% | PROVISIONAL |
| 2024-03 | 3.839,70 | 3.837,45 | -2,24 | -0,0584% | PROVISIONAL |
| 2026-04 | 3.503,09 | 3.505,14 | +2,04 | +0,0583% | PROVISIONAL |
| 2022-07 | 6.425,36 | 6.422,06 | -3,30 | -0,0514% | PUBLICATION_GRADE (OFFICIAL) |

### Largest IPIA changes

O maior Δ pts absoluto é o mesmo mês do maior Δ% de PPI: **2026-03,
-6,52 pts** (123,08 → 116,56, PROVISIONAL). O maior Δ pts dentro do
OFFICIAL congelado é **2023-04, +0,511 pts** (104,02 → 104,53).

## Threshold crossings

**Zero.** Nenhum mês cruzou o threshold 100 (IPIA > 100 ↔ IPIA < 100)
entre a vintage antiga e a nova. Confirmado programaticamente
(`threshold_100_crossing` na comparação completa).

**MoM reversals: 0 de 77** meses com variação mês a mês comparável — a
direção da variação mensal do IPIA nunca se inverteu entre as duas
vintages.

**Impacto no valor corrente**: o último mês PROVISIONAL comparável
(2026-06) tem Δ pts pequeno (a correção maior, 2026-03, já não é mais o
mês mais recente na data desta migração — ver `--ipia-latest` para o
valor corrente exato da vintage nova).

## Publication status changes

**Zero meses mudaram de `publication_status`** entre a vintage antiga e a
nova — confirmado tanto no contrafactual pré-implementação (validation
sprint) quanto na execução real desta migração. A correção altera **só o
valor**, nunca a classificação de cobertura. Em particular:

- Nenhum mês 2012-2022-03 foi promovido (permanece fora da janela PIA-
  based, e os 9 NCMs não comprovados continuam `UNKNOWN` nesse período).
- Nenhum mês da cota Gecex nº 929/2026 foi promovido (a lógica de cota
  não foi tocada).

## Quota unresolved volume

Não quantificado novamente nesta etapa — a cota Gecex nº 929/2026
permanece exatamente como estava (mecanismo `_JANELAS_COTA`/
`resolver_ii` inalterado, `UNKNOWN` durante os sub-períodos para os 4
NCMs afetados). Quantificação já registrada em
`docs/validation/hrc_import_policy_evidence_hardening.md` Seção 11 (ex.:
volume observado em jul/2026 já excede o teto do sub-período inteiro para
3 dos 4 códigos) — permanece válida e não foi alterada por esta
implementação.

## Reproducibility

- Evidência legal reconfirmada ao vivo antes da edição de código (mesmo
  arquivo, mesmo hash de tamanho).
- Vintage antiga: 100% reproduzível, hashes SHA-256 inalterados.
- Vintage nova: reproduzível a partir de `import_side.csv`/
  `domestic_price.csv` persistidos (mesma garantia do ADR 0012).
- Script de migração idempotente na leitura (nunca sobrescreve); rodar de
  novo criaria uma vintage adicional, não substituiria a atual.

## Tests

collected 435, passed 435, failed 0, errors 0 (396 baseline + 39 novos em
`tests/unit/test_trade_policy_hrc.py`, cobrindo as duas correções em `t-1`/
`t`/`t+1` nas datas relevantes, `_TABELA_II` sem sobreposição, e regressão
dos NCMs não afetados).

## Selftest

**PASS.** (O motor legado V1 exercido pelo `--selftest` não usa
`steel_indicator/parameters/trade_policy.py` — mudança não observável por
ele, comportamento esperado, mesma situação da ADR 0014.)
