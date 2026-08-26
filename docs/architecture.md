# Steel Indicator — Software Architecture

## Status

This document describes the current architecture and the target boundaries for the refactor.

It does **not** redefine indicator methodology. Calculation methodology lives in `docs/METODOLOGIA.md` and accepted ADRs.

---

## 1. Current architecture

The repository currently has two effective Python areas.

### `src/indices_setoriais.py`

The monolith currently owns approximately eleven responsibilities:

1. generic index engine;
2. ICCS declarative specification;
3. IPIA calculation;
4. domestic-price anchor;
5. external-source collectors;
6. parsing and data-quality treatment;
7. report-facing aggregations;
8. provenance/vintage classification;
9. embedded `selftest()`;
10. live source checking;
11. CLI/argument handling.

This coupling makes structural changes risky because calculation, I/O, network behavior, tests and presentation contracts share the same module namespace.

### `src/reporting/`

Reporting is already partially modularized into presentation components, pages, theme and report builder.

The current implementation imports the monolithic engine through manual `sys.path` manipulation. This is a temporary compatibility mechanism and must not be copied into new modules.

### `data/`

- `data/raw/`: local/raw acquisitions, not versioned.
- `data/processed/`: generated outputs, not versioned.
- `data/curated/`: small curated inputs intentionally versioned when required for reproducibility.

---

## 2. Current data flow

### Import side

```text
Comex Stat
   ↓
raw NCM observations
   ↓
monthly HRC aggregation
   ↓
missing-month handling
   ↓
volume confidence
   ↓
selective smoothing
   ↓
published import price
```

### Domestic side

```text
curated company releases
   ↓
quarterly domestic price
   ↓
volume-weighted blend
   ↓
IBGE IPP monthly chaining
   ↓
monthly domestic price
```

### Convergence

```text
import price + freight + insurance
              ↓
         import parity cost
              ↑
        BCB exchange rate

domestic monthly price
              ↓
             IPIA
              ↓
      CSV / report outputs
```

Aço Brasil data supplements the report/indicator context including import penetration.

---

## 3. Architectural problems to remove

### Monolithic ownership
Network, parsing, calculations, governance, CLI and tests live together.

### Ad-hoc imports
Reporting modifies `sys.path` to import the engine.

### Mutable module globals
Embedded tests monkeypatch functions in the monolithic module namespace.

### Manual network de-duplication
Several functions accept the same optional raw DataFrame to prevent repeated requests instead of consuming a defined collection result.

### Relative filesystem assumptions
Curated inputs and outputs rely on working-directory-relative paths.

### Test/production co-location
The only comprehensive regression harness is embedded in the production module.

---

## 4. Refactoring principles

1. Preserve behavior before improving architecture.
2. Create external characterization tests before extraction.
3. Extract one responsibility at a time.
4. Separate pure logic from I/O.
5. Do not mix methodology changes with structural changes.
6. Keep CLI compatibility during the migration.
7. Keep the existing `--selftest` until equivalent external coverage exists.
8. Reporting consumes engine outputs; the engine never depends on reporting.
9. Collect once, validate once, pass explicit data onward.
10. Make provenance and vintage metadata part of data contracts, not presentation-only annotations.

---

## 5. Target package boundaries

Target package name: `steel_indicator`.

```text
src/
└── steel_indicator/
    ├── __init__.py
    ├── cli.py
    ├── config.py
    │
    ├── domain/
    │   ├── index_engine.py
    │   └── provenance.py
    │
    ├── ipia/
    │   ├── calculation.py
    │   ├── domestic_price.py
    │   ├── import_price.py
    │   └── models.py
    │
    ├── sources/
    │   ├── http.py
    │   ├── bcb.py
    │   ├── comex.py
    │   ├── ibge.py
    │   └── aco_brasil.py
    │
    ├── governance/
    │   └── vintage.py
    │
    └── reporting/
        ├── components.py
        ├── pages.py
        ├── report_builder.py
        └── theme.py
```

This is the target direction, not permission to move everything in one change.

---

## 6. Dependency direction

Allowed:

```text
CLI
 ↓
application/orchestration
 ↓
domain/IPIA pure calculation
 ↑
validated source adapters

reporting
 ↓
calculated result objects
```

Forbidden:

```text
domain → requests
domain → reporting
reporting → live source collection
reporting → duplicate methodology
```

Source adapters may depend on HTTP utilities.

Pure domain/IPIA calculations may depend on pandas/numpy and data models, but not network clients.

---

## 7. Migration order

### Phase A — harness and baseline
- project instructions/rules/agents;
- architecture and source contracts;
- baseline `--selftest`.

### Phase B — external characterization tests
- introduce pytest;
- reproduce critical `selftest()` behaviors externally;
- freeze representative outputs/contracts.

### Phase C — package/import boundary
- introduce `pyproject.toml`;
- create `steel_indicator` package;
- remove new need for `sys.path` hacks;
- preserve CLI compatibility.

### Phase D — pure engine extraction
- generic index engine;
- IPIA calculation primitives;
- provenance models.

### Phase E — source adapters
- BCB;
- Comex;
- IBGE;
- Aço Brasil;
- shared HTTP/retry behavior.

### Phase F — orchestration and CLI
- explicit "collect → validate → calculate → publish" application flow;
- output paths/configuration;
- compatibility CLI.

### Phase G — reporting
- switch reporting imports to package boundaries;
- keep one source of numeric truth.

---

## 8. Refactor acceptance invariant

After each extraction step:

- deterministic tests pass;
- expected CLI behavior remains compatible;
- public output columns remain compatible unless an accepted spec changes them;
- no new network call is introduced;
- no methodology constant or formula changes unintentionally;
- no provenance/vintage information is lost.

---

## 9. Future collection architecture

The intended data pipeline is:

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
QUALITY VALIDATION
  ↓
CALCULATION INPUT
  ↓
INDICATOR
  ↓
PUBLICATION VINTAGE
```

The persistent raw/vintage layer should make historical publication states reproducible.

---

## 10. Decisions that require ADRs

Create/update an ADR when a change introduces a meaningful trade-off in:

- module/package boundaries with lasting consequences;
- caching/vintage storage;
- source substitution;
- methodology;
- public schemas;
- report architecture;
- dependency additions with architectural impact.

Routine extraction that directly implements this accepted architecture does not require a new ADR unless a new trade-off is discovered.
