# Steel Indicator — Data Source Registry

## Purpose

This is the operational source registry for collection and validation.

It records what a source is used for, its current confidence/status and the checks required before relying on it.

This document does not replace official source documentation.

---

## Verification states

### VERIFIED
The actual source/endpoint/file was executed or inspected and the identifier, expected semantics and returned observations were checked.

### DOCUMENTED
The source/identifier is supported by official documentation or reliable source material, but has not yet passed the project's live validation contract.

### TO_CONFIRM
A material assumption remains unresolved.

A source can be technically reachable while still being `TO_CONFIRM`.

---

## Registry

| Source | Use in Steel Indicator | Access | Current status | Important contract |
|---|---|---|---|---|
| MDIC Comex Stat | HRC import value, quantity/weight, freight, insurance, origin | POST API | VERIFIED with remaining field-level checks | Validate current NCM basket and availability of freight/insurance for required periods |
| BCB SGS | Exchange rate and macro/credit series | GET API | MIXED | Validate every series identifier/label; use deterministic date ranges |
| IBGE SIDRA — IPP 242-Siderurgia (table 6723) | Monthly chaining of domestic steel-price anchor | API | VERIFIED live for IPIA-HRC (see `docs/METODOLOGIA.md` §12.9) | Series switched from CNAE 24 "Metalurgia" to industrial group 242 "Siderurgia" (ADR/Stage documented in METODOLOGIA §12.9) — this row previously said "IPP Metalurgia" / table 6903, which is stale |
| Instituto Aço Brasil | Steel production/trade/apparent consumption/import penetration | HTML + PDF/XLS | DOCUMENTED / partial implementation | Validate workbook/table schema and record publication vintage |
| Curated public company releases | Quarterly domestic price anchor | versioned curated CSV | VERIFIED per curated evidence | Preserve source company, quarter, type/proxy classification and derivation |
| BCB SCR.data | Future credit-condition index inputs | ZIP/open data | DOCUMENTED | Validate CNAE representation and ODbL obligations before derived-dataset distribution |

---

## BCB SGS safety rule

Do **not** use:

```text
/dados/ultimos/N
```

as an ingestion or source-validation mechanism.

Project research observed inconsistent terminal windows depending on `N`.

Use explicit date-bounded retrieval instead, then validate:

- first returned date;
- last returned date;
- expected frequency;
- duplicate dates;
- missing periods;
- series label/identifier;
- plausible unit/range when documented.

---

## Comex Stat checks

Before treating the HRC basket as publication-ready:

- validate the active NCM list against the current tariff classification;
- exclude obsolete codes where applicable;
- verify unit/weight semantics;
- confirm freight and insurance availability over the required history;
- preserve origin-country detail before aggregation;
- validate months with zero/no records instead of silently assuming zero trade;
- archive the raw response/vintage used for a publication.

The IPIA uses realized import data rather than a licensed agency price.

---

## IBGE SIDRA checks

For each series:

- table identifier;
- variable identifier;
- classification/category;
- unit;
- monthly reference period;
- handling of revised observations.

Do not treat "endpoint responded" as enough.

---

## Aço Brasil checks

The source may involve HTML discovery plus PDF or legacy `.xls`.

Collectors should separate:

1. discovery of the current publication URL;
2. download;
3. raw vintage persistence;
4. parsing;
5. table/schema validation.

Terms for commercial use should remain explicitly tracked if not formally confirmed.

---

## Domestic-price curated data

`data/curated/preco_domestico_aco.csv` is intentionally versioned.

Each observation should preserve enough evidence to identify:

- company;
- reference quarter;
- revenue/volume or published price used;
- calculation method;
- `tipo` / proxy status;
- original public document reference.

Do not silently promote a segment-level proxy to product-specific observed price.

---

## Vintage contract

Persistent collection should eventually produce a manifest containing at least:

| Field | Meaning |
|---|---|
| `collected_at` | timestamp/date when Steel Indicator fetched the source |
| `source_id` | stable source/series identifier |
| `reference_start` | first reference observation |
| `reference_end` | last reference observation |
| `n_obs` | number of observations/rows |
| `sha256` | hash of persisted raw content |
| `validation_status` | VERIFIED / DOCUMENTED / TO_CONFIRM or pipeline-specific PASS/FAIL/UNKNOWN |
| `methodology_version` | when relevant to a publication |
| `code_version` | commit/tag when relevant to a publication |

Goal: answer "what did the source contain when this number was published?" without reconstructing history from a revised API.

---

## Source-validation output contract

Automated validation should return machine-readable results conceptually equivalent to:

```text
source
check
status: PASS | FAIL | UNKNOWN
evidence
checked_at
```

`UNKNOWN` is a valid engineering state.

It must never be silently coerced to `PASS`.
