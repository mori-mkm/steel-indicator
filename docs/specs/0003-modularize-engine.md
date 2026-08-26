# Spec 0003 — Methodology-Aware Platform Refactor

**Status:** Revised — ready after methodology reset  
**Type:** Architecture refactor and migration  
**Direct methodology change:** No  
**Supersedes:** previous version of Spec 0003  
**Depends on:** Spec 0002, `docs/METODOLOGIA.md`, `docs/architecture.md`

---

## 1. Why this spec was revised

The original Spec 0003 assumed that the current IPIA behavior was the target behavior and that the refactor should mechanically extract the monolith in this order:

1. generic engine;
2. current IPIA primitives/models;
3. provenance;
4. domestic price;
5. sources;
6. orchestration;
7. CLI;
8. reporting.

That assumption is no longer valid.

The accepted methodology now requires:

- a shared multi-index platform;
- IPIA-HRC and IPIA-Rebar using one engine;
- product-specific NCM baskets and domestic-price strategies;
- historical, time-varying trade-policy parameters;
- observed Comex freight/insurance when available;
- explicit publication-readiness blockers;
- a revised ICCS architecture;
- a future ICS on the same infrastructure.

Therefore, this spec must prevent the project from extracting legacy structures into permanent modules when those structures encode assumptions that are being replaced.

---

## 2. Current baseline

At the time of this revision:

- Spec 0002 characterization coverage is complete;
- deterministic pytest coverage exists;
- legacy `python src/indices_setoriais.py --selftest` passes;
- the generic index engine has already been extracted to:

```text
src/steel_indicator/domain/index_engine.py
```

That extraction is accepted and remains part of the target architecture.

The legacy monolith remains:

```text
src/indices_setoriais.py
```

and is still the compatibility surface for behavior not yet migrated.

---

## 3. Important decision: old Batch 2 is cancelled

Do **not** implement the previously proposed Batch 2 as written.

Specifically, do not move the legacy:

```text
ParamsIPIA
custo_importacao_rs_t()
ipia()
```

into final target modules merely because they are pure.

Reason:

`ParamsIPIA` currently models several import-cost assumptions as scalar/default parameters. The target methodology requires historically valid parameters resolved by:

- product family;
- NCM/scope;
- reference period;
- validity interval;
- source;
- validation status.

Extracting the legacy model unchanged into the new package would make an obsolete assumption look like the permanent domain model.

The legacy functions remain protected by characterization tests and may stay in the compatibility monolith until their target contracts are defined.

---

## 4. Goal

Transform the repository into the architecture defined in `docs/architecture.md` while:

1. preserving legacy behavior where the task is structural;
2. explicitly separating future methodology changes;
3. creating shared infrastructure before index-specific duplication;
4. keeping the system continuously testable and reversible;
5. avoiding premature abstractions.

The target is not merely a smaller `indices_setoriais.py`.

The target is a platform that can support:

```text
IPIA-HRC
IPIA-Rebar
ICCS
ICS
```

through shared collection, validation, storage, provenance and transformation infrastructure.

---

## 5. Source-of-truth rules for this migration

Follow the project precedence defined in `CLAUDE.md`.

For this spec, the key distinction is:

```text
characterization tests
= evidence of legacy behavior

docs/METODOLOGIA.md
= target methodology
```

When they agree:

- preserve behavior during extraction.

When they intentionally differ:

- do not change behavior inside this architecture-only batch;
- record the divergence;
- create/update an index-specific implementation spec;
- implement the new methodology under that explicit spec.

---

## 6. Non-goals

This spec does **not** directly:

- publish IPIA V2;
- change historical IPIA results;
- implement IPIA-Rebar;
- finalize ICCS weights;
- implement ICS;
- remove the legacy monolith;
- remove the legacy `--selftest`;
- implement the IPIA weekly nowcast;
- perform broad code cleanup unrelated to architectural boundaries.

Those require later child specs or explicit accepted methodology changes.

---

# 7. Migration strategy

Use a **platform-first, extract-and-verify** strategy.

The migration is divided into stages.

Do not implement all stages in one run.

Each implementation batch must remain small enough that a failing test has a narrow cause.

---

# 8. Stage A — freeze the revised baseline

Before more production refactoring:

1. ensure the new:
   - `CLAUDE.md`;
   - `docs/METODOLOGIA.md`;
   - `docs/architecture.md`;
   - this Spec 0003;
   are saved;

2. run:

```bash
python -m pytest tests/ -v
python src/indices_setoriais.py --selftest
```

3. inspect:

```bash
git status
git diff --stat
```

4. commit the methodology/architecture documentation separately from the next production-code extraction.

### Acceptance

- deterministic tests green;
- legacy selftest green;
- documentation commit isolated;
- working tree clean before the next code batch.

---

# 9. Stage B — preserve completed generic engine extraction

The existing:

```text
steel_indicator/domain/index_engine.py
```

is accepted.

Do not rework it unless:

- tests reveal a regression;
- new shared requirements require a real domain change;
- an accepted methodology/spec changes its behavior.

It remains responsible for generic concepts such as:

- variable/pillar/index specification;
- fixed-window standardization;
- weight redistribution;
- coverage;
- generic diagnostics where truly reusable.

Do not add IPIA-specific trade or source behavior to this module.

---

# 10. Stage C — common domain contracts

Before extracting more legacy IPIA implementation, create the smallest shared contracts required by the target architecture.

Recommended order:

## C1. Provenance contract

Target responsibility:

```text
steel_indicator/domain/provenance.py
```

Represent, without presentation logic:

- processing level:
  - OBSERVADO;
  - CALCULADO;
  - ESTIMADO;
- PROXY status;
- method;
- source;
- `reference_period`;
- validation status where appropriate.

### Rule

Preserve existing legacy provenance semantics.

Do not redesign labels while extracting them.

### Tests

Create unit/characterization coverage for:

- existing classification semantics;
- combinations of processing level + proxy;
- preservation of `reference_period`;
- no accidental downgrade from PROXY/ESTIMADO.

---

## C2. Core data contracts

Introduce only the minimum contracts needed to pass validated data between layers.

Candidate target:

```text
steel_indicator/data/contracts.py
```

A normalized observation/result contract should be able to express:

```text
series_id
source_id
reference_period
value
unit
frequency
provenance
validation_status
vintage_id
```

### Constraint

Do not convert every DataFrame into custom classes.

DataFrames may remain the transport format.

The goal is explicit schemas/contracts, not object-oriented redesign.

---

## C3. Vintage/manifest contract

Define the persistent metadata contract before implementing full storage.

Candidate targets:

```text
steel_indicator/storage/manifest.py
steel_indicator/storage/raw_vintage.py
```

Required conceptual fields:

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

### Initial scope

It is acceptable for the first batch to define/test deterministic manifest construction without yet migrating every existing collector.

---

# 11. Stage D — historical parameter model

This stage is required before the new IPIA calculation model becomes authoritative.

Create a target contract for time-varying parameters.

Candidate:

```text
steel_indicator/parameters/historical.py
steel_indicator/parameters/trade_policy.py
```

The model must support:

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

Initial parameter types include:

- import tariff;
- AFRMM;
- antidumping;
- quotas;
- temporary trade measures.

### Critical constraint

Do not populate historical values by guesswork.

A parameter may exist as:

```text
A_CONFIRMAR
```

until verified.

### Legacy compatibility

The old scalar/default `ParamsIPIA` remains legacy behavior until the new IPIA implementation spec defines how legacy and historical parameter resolution coexist.

---

# 12. Stage E — shared source boundaries

Extract source adapters one source at a time.

Recommended priority:

1. Comex;
2. BCB;
3. Aço Brasil;
4. IBGE;
5. CVM/company structured inputs;
6. rebar-specific source after acceptance.

Each source extraction must separate:

```text
HTTP/access
→ raw parsing
→ source-specific schema validation
```

from:

```text
economic calculation
```

---

## E1. Comex adapter

Target:

```text
steel_indicator/sources/comex.py
```

Responsibilities:

- `/general` POST construction;
- explicit period;
- explicit metrics;
- raw response parsing;
- source schema validation.

Do not embed final product NCM baskets permanently inside the generic adapter.

Product NCM selection belongs to product configuration.

### Methodology blocker

Live POST validation remains a publication-readiness gate.

A live validation may close that blocker only if the output is actually inspected and documented.

---

## E2. BCB adapter

Target:

```text
steel_indicator/sources/bcb.py
```

Replace any ingestion/validation dependency on:

```text
/ultimos/N
```

with deterministic date-bounded retrieval.

This is an accepted source-correctness fix from later verified research.

Required tests:

- requested date range;
- returned date validation;
- no `/ultimos/N`;
- revision-window behavior where implemented.

---

## E3. Aço Brasil adapter

Target:

```text
steel_indicator/sources/aco_brasil.py
```

Prefer structured Excel ingestion.

PDF parsing may remain:

- validation tooling;
- fallback;
- legacy compatibility.

Do not make recurring production ingestion depend on PDF if the Excel source is usable.

---

## E4. IBGE adapter

Target:

```text
steel_indicator/sources/ibge.py
```

Separate:

- table/variable/classification identifiers;
- request construction;
- response parsing;
- reference-period normalization.

Do not let IPIA domestic-price logic own SIDRA request details.

---

# 13. Stage F — product configuration

Before implementing IPIA V2, create an explicit product configuration boundary.

Candidate:

```text
steel_indicator/parameters/product_config.py
```

or an equivalent accepted boundary.

It must support at least:

```text
family
NCM basket/version
domestic-price strategy
liquidity rules
required sources
parameter scope
```

Initial product families:

```text
HRC
REBAR
```

### Constraint

Avoid scattered branching such as:

```python
if product == "hrc":
    ...
elif product == "rebar":
    ...
```

across collectors/calculators.

Product variation should be centralized.

---

# 14. Stage G — stop point before methodology-changing IPIA work

At this point, architecture should support the new model.

Before implementing the new official IPIA calculation, create dedicated child specs.

At minimum:

```text
Spec — IPIA shared calculation contract
Spec — IPIA-HRC V2
Spec — IPIA-Rebar V1
```

Those specs define methodology-changing behavior.

This Spec 0003 must not silently implement them.

---

# 15. IPIA child-spec requirements

The IPIA implementation specs must resolve:

## Shared

- import parity result schema;
- historical parameter resolution;
- provenance propagation;
- monthly official series;
- legacy comparison.

## HRC

- historically valid NCM basket;
- Comex realized FOB/freight/insurance;
- CSN/Usiminas candidate evaluation;
- CVM + IPP domestic V1;
- explicit PROXY rules;
- temporal benchmarking decision;
- maximum comparable backfill.

## Rebar

- product definition;
- NCM basket;
- structured domestic price source;
- SINAPI suitability analysis if used;
- liquidity thresholds;
- maximum comparable backfill.

---

# 16. ICCS and ICS are downstream consumers of the platform

Do not implement them in this spec.

However, common abstractions created here must not assume:

```text
every index is an import-parity index
```

Shared layers must remain usable by ICCS and ICS.

Examples of valid shared concerns:

- source collection;
- vintage;
- normalized series;
- provenance;
- transformations;
- generic index engine.

Examples of IPIA-only concerns:

- NCM product basket;
- import tariff;
- import parity;
- domestic/import price ratio.

---

# 17. Orchestration migration

Only after stable source/data/domain boundaries exist, extract application workflows.

Target direction:

```text
steel_indicator/application/
```

Example:

```text
collect
→ validate
→ prepare inputs
→ calculate
→ persist
→ publish
```

Pure calculation must be invokable using already-supplied data without network calls.

---

# 18. CLI migration

Keep the current CLI as a compatibility surface during migration.

New internal flow may use:

```text
steel_indicator/cli.py
```

Do not change public CLI behavior in the same batch as a major calculation-methodology change unless explicitly specified.

---

# 19. Reporting migration

Reporting migration occurs after calculation result contracts stabilize.

Target:

```text
calculated result object
├── CSV
├── PDF
└── future API
```

Reporting must not:

- recollect sources;
- compute alternate IPIA logic;
- use independent reference periods;
- duplicate provenance classification.

Remove the legacy reporting `sys.path` hack only when package imports are stable.

---

# 20. Legacy monolith retirement

Do not remove `src/indices_setoriais.py` opportunistically.

Retirement requires a separate final migration step after:

- new workflows are stable;
- package imports are stable;
- legacy/new methodology differences are documented;
- CLI migration is complete;
- reporting uses package contracts;
- equivalent test coverage exists.

The monolith may temporarily re-export new modules.

---

# 21. Verification loop for every architecture batch

Use:

```text
inspect
  ↓
define one boundary
  ↓
add/confirm protection
  ↓
implement small change
  ↓
small relevant tests
  ↓
full deterministic pytest
  ↓
legacy --selftest
  ↓
git diff review
  ↓
stop/report
```

Do not stack new architecture work over a failing baseline.

---

# 22. Batch autonomy rules

A batch may proceed without user supervision only when:

- its scope is already approved;
- it is behavior-preserving;
- acceptance commands are explicit;
- it does not require source guessing;
- it does not change methodology;
- it must stop on failure;
- it does not commit/push automatically.

Methodology-changing batches require an approved child spec before autonomous implementation.

---

# 23. Acceptance criteria for this Spec

Spec 0003 is complete when:

- the generic engine is modular;
- provenance is a domain contract;
- normalized data contracts exist;
- vintage/manifest contracts exist;
- historical parameter representation exists;
- major source adapters have explicit package boundaries;
- product configuration supports HRC and rebar;
- new code introduces no `sys.path` hacks;
- pure calculation is separated from network I/O;
- reporting does not recollect or duplicate calculation logic;
- CLI compatibility is maintained or intentionally migrated;
- deterministic pytest remains green;
- legacy `--selftest` remains green while required;
- methodology-changing IPIA work has moved to dedicated child specs;
- `docs/architecture.md` reflects actual boundaries.

---

# 24. Immediate next batch after this revision

Do **not** resume the cancelled legacy Batch 2.

The next implementation proposal should be:

```text
Batch 2 (revised):
Extract and formalize provenance as a shared domain contract.
```

Before editing, the proposal must identify:

- current provenance/classification functions;
- current output fields;
- characterization tests protecting them;
- target contract;
- compatibility mechanism for `indices_setoriais.py`;
- exact files touched;
- exact verification commands.

No IPIA formula, source collector or methodology change belongs in this batch.

---

# 25. Final report for each batch

Report:

- files created/changed;
- behavior preserved or intentionally changed;
- tests executed;
- actual test results;
- legacy selftest result;
- diff summary;
- methodology impact;
- source-validation impact;
- unresolved risks;
- whether next batch is safe.

Do not begin the next batch unless the current batch satisfies its acceptance criteria.
