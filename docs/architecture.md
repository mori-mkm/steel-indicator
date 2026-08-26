# Steel Indicator — Software Architecture

## Status

This document defines the **target software architecture** and migration boundaries for the `steel-indicator` repository.

It does not define economic methodology. Methodology lives in:

- `docs/METODOLOGIA.md`;
- accepted ADRs in `docs/adr/`;
- accepted implementation specs in `docs/specs/`.

Original research remains in `references/`.

The architecture must support:

- IPIA-HRC;
- IPIA-Rebar;
- ICCS;
- ICS.

IIDB is out of scope.

---

# 1. Architectural objective

The project must evolve from a monolithic indicator script into a shared multi-index platform with explicit boundaries for:

- source collection;
- raw vintages;
- validation;
- normalization;
- transformations;
- historical parameters;
- provenance;
- index calculation;
- publication outputs.

The core target flow is:

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
INDEX-SPECIFIC ENGINE
  ↓
PUBLICATION VINTAGE
  ↓
REPORT / CSV / API
```

The same infrastructure must serve IPIA, ICCS and ICS wherever concepts are shared.

---

# 2. Current migration state

The repository started with most production behavior in:

```text
src/indices_setoriais.py
```

The legacy module owns or historically owned:

1. generic index engine;
2. ICCS declarative specification;
3. IPIA calculation;
4. domestic-price anchor;
5. external source collectors;
6. parsing and data quality;
7. report-facing aggregations;
8. provenance/vintage classification;
9. embedded `selftest()`;
10. live source checks;
11. CLI.

The refactor has already started.

Current migration facts:

- external characterization tests exist;
- the legacy `--selftest` remains active;
- the generic index engine has been extracted to:

```text
src/steel_indicator/domain/index_engine.py
```

- `src/indices_setoriais.py` remains the compatibility/orchestration legacy surface during migration;
- reporting remains partially coupled to the legacy module;
- production source adapters are not yet fully separated.

This transitional state is intentional.

---

# 3. Architectural principles

## 3.1 Separate structure from methodology

A structural refactor must preserve accepted behavior.

A methodology upgrade may intentionally change outputs, but only through:

- explicit spec;
- updated methodology;
- tests for the new behavior;
- versioned comparison to legacy when useful.

Do not hide methodology changes inside module extraction.

## 3.2 Legacy is a compatibility layer

`src/indices_setoriais.py` is temporary.

During migration it may:

- re-export extracted symbols;
- preserve CLI behavior;
- preserve old imports;
- preserve golden-test compatibility.

It must gradually stop owning business logic.

New production logic should not be added to the monolith unless a migration constraint makes it unavoidable.

## 3.3 Pure domain logic

Calculation modules must not:

- call HTTP;
- read files directly;
- write files;
- depend on reporting;
- inspect environment-specific paths.

Pure modules receive validated data and return deterministic results.

## 3.4 Collect once

A source must be fetched once per collection task.

Downstream consumers receive explicit data objects or persisted datasets.

Forbidden pattern:

```text
reporting → collect source again
calculation → collect source again
validation → collect source again
```

Preferred:

```text
collector
   ↓
validated dataset
   ↓
calculation
   ↓
reporting
```

## 3.5 Provenance is part of the data contract

`OBSERVADO / CALCULADO / ESTIMADO / PROXY` and `reference_period` are not display-only labels.

They belong to the calculation/output contracts.

## 3.6 Historical policy is data

Tariffs, AFRMM, antidumping, quotas and other time-varying rules must be modeled as historical data/configuration, not constants embedded in formulas.

---

# 4. Target package structure

Target direction:

```text
src/
└── steel_indicator/
    ├── __init__.py
    │
    ├── application/
    │   ├── __init__.py
    │   ├── collect.py
    │   ├── calculate.py
    │   ├── publish.py
    │   └── workflows.py
    │
    ├── domain/
    │   ├── __init__.py
    │   ├── index_engine.py
    │   ├── provenance.py
    │   ├── periods.py
    │   └── validation.py
    │
    ├── data/
    │   ├── __init__.py
    │   ├── contracts.py
    │   ├── normalization.py
    │   ├── transformations.py
    │   └── quality.py
    │
    ├── sources/
    │   ├── __init__.py
    │   ├── http.py
    │   ├── bcb.py
    │   ├── comex.py
    │   ├── ibge.py
    │   ├── aco_brasil.py
    │   ├── cvm.py
    │   └── sinapi.py
    │
    ├── storage/
    │   ├── __init__.py
    │   ├── raw_vintage.py
    │   ├── manifest.py
    │   ├── curated.py
    │   └── publication_vintage.py
    │
    ├── parameters/
    │   ├── __init__.py
    │   ├── historical.py
    │   ├── trade_policy.py
    │   └── product_config.py
    │
    ├── ipia/
    │   ├── __init__.py
    │   ├── models.py
    │   ├── calculation.py
    │   ├── import_price.py
    │   ├── domestic_price.py
    │   ├── liquidity.py
    │   ├── backfill.py
    │   └── products/
    │       ├── hrc.py
    │       └── rebar.py
    │
    ├── iccs/
    │   ├── __init__.py
    │   ├── models.py
    │   ├── specification.py
    │   ├── mapping.py
    │   ├── calculation.py
    │   └── diagnostics.py
    │
    ├── ics/
    │   ├── __init__.py
    │   ├── models.py
    │   ├── specification.py
    │   ├── calculation.py
    │   └── diagnostics.py
    │
    ├── reporting/
    │   ├── __init__.py
    │   ├── components.py
    │   ├── pages.py
    │   ├── report_builder.py
    │   └── theme.py
    │
    └── cli.py
```

This is a target map, not permission to create every file immediately.

Only introduce modules when a real responsibility is extracted or implemented.

---

# 5. Dependency direction

Allowed:

```text
CLI
 ↓
application workflows
 ↓
index-specific services
 ↓
domain calculations
 ↑
validated data contracts
 ↑
source/storage adapters
```

Reporting:

```text
reporting
 ↓
calculated result objects
```

Forbidden:

```text
domain → requests
domain → filesystem
domain → reporting

reporting → live source collection
reporting → duplicate business formula

index calculation → source-specific HTTP details

source adapters → reporting
```

---

# 6. Domain layer

`steel_indicator/domain/` contains concepts shared by multiple indices.

Examples:

- generic index aggregation;
- frozen-window z-score;
- weight redistribution;
- coverage rules;
- provenance;
- reference periods;
- generic validation primitives.

It must not contain:

- Comex payloads;
- BCB URL details;
- HRC NCM baskets;
- ICCS sector mappings;
- report layout.

`domain/index_engine.py` is already the first extracted module.

---

# 7. Data contracts

The system should move away from implicit DataFrame conventions toward explicit contracts.

A normalized series should be able to express at least:

```text
series_id
source_id
reference_period
collected_at
value
unit
frequency
status
processing_level
proxy
method
validation_status
vintage_id
```

Index-specific inputs may extend this contract.

DataFrames may remain the implementation format, but column meaning must be explicit and validated.

---

# 8. Source layer

`steel_indicator/sources/` contains source-specific access and parsing.

Each adapter is responsible for:

- request construction;
- authentication if required;
- structured response parsing;
- source-specific schema validation;
- returning raw/near-raw structured observations.

Adapters must not calculate final indices.

## 8.1 Shared HTTP

`sources/http.py` should centralize, when useful:

- session configuration;
- timeout;
- retries;
- response validation;
- error normalization;
- user agent;
- logging hooks.

Do not build a complex framework before repeated behavior exists.

## 8.2 BCB

Responsibilities:

- SGS date-bounded retrieval;
- label/source metadata;
- deterministic date validation;
- revision-aware recollection window.

Explicitly forbidden:

```text
/ultimos/N
```

for ingestion or validation.

## 8.3 Comex

Responsibilities:

- `/general` POST;
- requested metrics;
- product/NCM filters;
- period filters;
- response schema;
- raw trade records.

NCM historical validity belongs in a separate product/config or parameter layer, not hidden inside generic HTTP code.

## 8.4 IBGE

Responsibilities:

- SIDRA request construction;
- table/classification/variable identifiers;
- schema validation;
- reference-period normalization.

## 8.5 Aço Brasil

Structured Excel is the preferred production input.

PDF-specific parsing should be treated as validation/fallback tooling, not the default recurring ingestion path when structured data exists.

## 8.6 CVM/company data

Automated production ingestion should prefer structured disclosures.

When a required value is only available in PDF:

```text
PDF
→ curation
→ versioned structured file
→ calculation
```

The calculation layer should consume the structured artifact, not the PDF.

---

# 9. Storage and vintage architecture

Persistence must distinguish:

```text
raw source vintage
processed/normalized data
curated inputs
publication vintage
```

Recommended conceptual layout:

```text
data/
├── raw/
│   └── <source>/<dataset>/<collection-date>/
├── processed/
│   └── ...
├── curated/
│   └── ...
└── published/
    └── ...
```

Exact physical paths may evolve.

## 9.1 Raw vintage

Raw responses must be immutable.

A recollection creates a new vintage.

## 9.2 Manifest

Each persisted acquisition should eventually register:

```text
vintage_id
collected_at
source_id
dataset_id
reference_start
reference_end
n_obs
sha256
validation_status
code_version
methodology_version
```

## 9.3 Curated data

Small curated files may be versioned in Git when they are necessary for reproducibility and legally appropriate.

Curated data must retain source lineage.

---

# 10. Historical parameter layer

Time-varying policy parameters must not remain hardcoded constants.

Target model:

```text
parameter
product_family
ncm_or_scope
valid_from
valid_to
value
unit
source
validation_status
```

Examples:

- import tariff;
- AFRMM;
- antidumping;
- quotas;
- temporary tariff increases;
- product-specific trade measures.

The IPIA calculation receives the parameter valid for the requested reference period.

---

# 11. IPIA architecture

## 11.1 Shared engine

IPIA-HRC and IPIA-Rebar share:

- economic formula;
- import-side calculation primitives;
- exchange-rate handling;
- provenance framework;
- parameter resolution;
- publication result schema.

They do not share blindly:

- NCM baskets;
- domestic anchors;
- liquidity thresholds;
- product-specific quality rules.

## 11.2 Product configuration

Product-specific definitions should be configuration/code objects, for example:

```text
ProductConfig
├── family
├── ncm_basket/version
├── domestic_price_strategy
├── liquidity_rules
├── internalization_parameters
└── source requirements
```

Avoid:

```python
if product == "hrc":
    ...
elif product == "rebar":
    ...
```

spread across the codebase.

Centralize product differences.

## 11.3 Import pipeline

Target:

```text
Comex raw
  ↓
historically-valid NCM filter
  ↓
schema validation
  ↓
monthly product aggregation
  ↓
realized FOB / freight / insurance
  ↓
liquidity-quality treatment
  ↓
historical policy parameters
  ↓
import parity cost
```

## 11.4 Domestic HRC

Target V1:

```text
structured company disclosures
  ↓
comparability validation
  ↓
quarterly level anchor
  ↓
IPP / product-specific monthly movement
  ↓
temporal benchmarking when needed
  ↓
monthly domestic HRC estimate
```

Proxy status must remain explicit.

## 11.5 Domestic rebar

Separate strategy.

Candidate sources must be evaluated before freezing implementation.

Do not assume HRC domestic-price logic is automatically valid.

---

# 12. ICCS architecture

ICCS uses the generic index engine but requires its own data model.

Key design constraint:

```text
fine sector credit balance
        +
broad credit-quality data
```

must coexist explicitly.

Target components:

```text
iccs/
├── specification.py
├── mapping.py
├── calculation.py
└── diagnostics.py
```

## 12.1 Mapping layer

`mapping.py` should express:

- target sector;
- fine series;
- broad quality section;
- source lineage;
- granularity mismatch.

The broad quality layer must not be relabeled as fine-grained observed delinquency.

## 12.2 Specification

Final ICCS pillar weights belong in accepted methodology/specification, not scattered constants.

The old 30% quality weight is superseded.

Approximate target is 22%, but exact accepted weights should be frozen before final implementation.

---

# 13. ICS architecture

ICS should reuse:

- collection infrastructure;
- transformation layer;
- generic index engine;
- provenance;
- diagnostics;
- publication framework.

Initial ICS is synthetic.

A future survey/panel implementation should be isolated behind a separate input adapter/model rather than changing the meaning of the synthetic historical series.

---

# 14. Application/orchestration layer

The application layer coordinates side effects.

Example:

```text
collect_ipia(product, period)
    ↓
validate_inputs(...)
    ↓
prepare_ipia_inputs(...)
    ↓
calculate_ipia(...)
    ↓
persist_publication(...)
```

Orchestration may call:

- sources;
- storage;
- validators;
- domain calculations.

Pure calculation functions should not know whether data came from HTTP, CSV, cache or a test fixture.

---

# 15. Reporting architecture

`steel_indicator/reporting/` is presentation-only.

Reporting may:

- format values;
- build charts;
- create tables;
- create PDFs;
- render provenance labels.

Reporting must not:

- recollect Comex/BCB/IBGE;
- calculate IPIA independently;
- apply alternate methodology;
- silently select a different reference period.

One calculated result object should feed all publication formats.

Target:

```text
calculation result
├── CSV
├── PDF
├── future API
└── future web page
```

Same numeric truth.

---

# 16. CLI architecture

The current CLI is a compatibility interface during migration.

Internally it may change.

External behavior should remain compatible until an accepted spec intentionally changes it.

Target CLI responsibilities:

- parse command;
- select workflow;
- pass parameters;
- display result/status;
- set exit code.

CLI should not contain business formulas.

---

# 17. Testing architecture

Testing is part of the harness, not an afterthought.

Layers:

```text
tests/
├── characterization/
├── unit/
├── integration/
└── reporting/
```

## 17.1 Characterization

Protect legacy behavior during migration.

They are not permanent authority over intentionally revised methodology.

## 17.2 Unit

Protect pure new modules.

No network.

No mutable global source dependencies.

## 17.3 Integration

Validate:

- source adapters;
- schema contracts;
- persistence;
- end-to-end orchestration.

Network integration tests must be explicitly separated from deterministic suites.

## 17.4 Reporting

Validate:

- result consumption;
- PDF generation;
- expected labels;
- no duplicate data collection;
- cutoff/reference-period correctness.

---

# 18. Migration strategy

The previous migration plan is superseded by this multi-index target.

## Phase A — harness and baseline

Status: substantially complete.

- CLAUDE/rules/agents;
- legacy `--selftest`;
- external characterization suite;
- architectural/methodological documentation.

## Phase B — safe structural extraction

Status: started.

Completed/started:

- generic `domain/index_engine.py`.

Next structural work must be reviewed against the target architecture before implementation.

Focus:

- provenance domain model;
- shared data contracts;
- storage/vintage contracts;
- source boundaries.

Do not continue extracting legacy IPIA modules mechanically if doing so would encode obsolete methodology as the final design.

## Phase C — shared data platform

Implement the common path:

```text
fetch
→ raw vintage
→ validate
→ normalize
→ provenance
→ calculation input
```

Priority source adapters:

1. Comex;
2. BCB;
3. Aço Brasil;
4. IBGE;
5. CVM/company structured inputs;
6. rebar-specific structured source if accepted.

## Phase D — historical parameters

Create time-aware parameter resolution for:

- tariffs;
- AFRMM;
- antidumping;
- quotas;
- other trade measures.

This phase is required before serious historical IPIA backfill.

## Phase E — IPIA-HRC V2

Implement:

- validated historical NCM basket;
- Comex realized import side;
- observed freight/insurance availability rules;
- domestic V1 anchor;
- backfill;
- legacy vs V2 comparison;
- publication-readiness blockers.

## Phase F — IPIA-Rebar

Reuse common IPIA engine.

Implement:

- product definition;
- NCM basket;
- domestic price source;
- product-specific liquidity/quality;
- historical backfill.

## Phase G — ICCS

Implement:

- two-layer granularity mapping;
- final pillar specification;
- collection/transform pipeline;
- diagnostics;
- backfill.

## Phase H — ICS

Implement synthetic index over shared platform.

Survey/panel is later.

## Phase I — reporting migration

Move reporting fully to package imports and calculated result objects.

Remove legacy `sys.path` compatibility hacks.

## Phase J — legacy retirement

Only after:

- new workflows are stable;
- tests are green;
- CLI compatibility is addressed;
- legacy vs new methodology differences are documented.

Then reduce/retire `src/indices_setoriais.py`.

---

# 19. Refactor acceptance invariants

After each behavior-preserving extraction:

- smallest relevant tests pass;
- full deterministic pytest passes;
- legacy `--selftest` passes while still required;
- no unintended network call is introduced;
- no provenance metadata is lost;
- no public schema changes accidentally;
- no methodology behavior changes unintentionally;
- `git diff` is inspected.

After each methodology change:

- legacy divergence is explicitly documented;
- new tests validate accepted behavior;
- methodology version impact is stated;
- backfill impact is assessed.

---

# 20. Publication readiness

Technical implementation is not equivalent to publication readiness.

An index is publication-ready only when:

- required sources are verified;
- blocking data questions are closed;
- historical parameters are defensible;
- provenance/vintage works;
- acceptance diagnostics pass;
- methodology is versioned;
- limitations are documented.

For IPIA V2, the four methodology blockers defined in `docs/METODOLOGIA.md` remain mandatory gates.

---

# 21. ADR triggers

Create/update an ADR for meaningful lasting trade-offs in:

- module/package boundaries;
- storage/vintage strategy;
- source substitution;
- source quality hierarchy;
- temporal benchmarking method;
- historical parameter representation;
- public schemas;
- methodology;
- report architecture;
- major dependency additions.

Routine extraction that directly follows this architecture does not require an ADR unless a new trade-off appears.

---

# 22. Anti-patterns

Do not introduce:

```text
new sys.path manipulation
```

Do not create:

```text
one collector per index for the same source
```

Do not create:

```text
business formulas inside reporting
```

Do not hide:

```text
PROXY as OBSERVADO
```

Do not:

```text
overwrite raw vintage
```

Do not:

```text
apply current policy parameters to historical periods
```

Do not:

```text
convert every DataFrame into a custom class without a concrete need
```

Do not over-engineer the platform before real repeated abstractions exist.

---

# 23. Architectural success criteria

The architecture is considered successfully migrated when:

- `src/indices_setoriais.py` is no longer the business-logic center;
- source adapters are independently testable;
- raw collections are vintage-aware;
- data contracts carry provenance/reference periods;
- historical parameters are time-aware;
- HRC and rebar share the same IPIA engine;
- ICCS and ICS reuse the generic platform;
- reporting consumes a single calculated numeric truth;
- deterministic calculation runs without network access;
- legacy compatibility can be removed without losing reproducibility.

---

# 24. Related documents

Use together with:

- `CLAUDE.md`;
- `docs/METODOLOGIA.md`;
- `docs/data-sources.md`;
- `docs/adr/`;
- `docs/specs/`;
- `references/catalogo_series_coleta.xlsx`;
- `references/guia_de_coleta_de_series.md`;
- `references/manual_metodologico_indices_setoriais.md`.

`docs/METODOLOGIA.md` decides **what the indices mean and calculate**.

This document decides **how the software is divided so that those methodologies can be implemented, tested and reproduced safely**.
