# Spec 0003 — Modularize the Steel Indicator Engine

**Status:** Ready after Spec 0002  
**Type:** Behavior-preserving architecture refactor  
**Methodology change:** No

## Preconditions

Do not start until:

- Spec 0002 external characterization tests pass;
- `--selftest` baseline passes;
- current CLI/output contracts are documented.

## Problem

`src/indices_setoriais.py` owns calculation, external collection, parsing, provenance, tests, live checks and CLI behavior.

Reporting also relies on ad-hoc `sys.path` manipulation.

## Goal

Move toward the package boundaries in `docs/architecture.md` without changing published behavior.

## Strategy

Use **extract-and-verify**, not rewrite.

Perform one extraction at a time.

Recommended order:

1. pure generic index engine;
2. pure IPIA calculation primitives/models;
3. provenance/vintage functions;
4. domestic-price pure transformations;
5. source adapters;
6. orchestration;
7. CLI;
8. reporting import cleanup.

## Target direction

```text
src/steel_indicator/
├── __init__.py
├── cli.py
├── config.py
├── domain/
├── ipia/
├── sources/
├── governance/
└── reporting/
```

The exact file split may be refined during implementation if evidence from the code shows a better boundary. Material deviations require documenting the reason.

## Constraints

- preserve CLI behavior during migration;
- preserve current output columns;
- preserve defaults;
- preserve network request count guarantees;
- preserve raw-data injection paths used for deterministic testing until replaced by a clearer equivalent;
- no network I/O in pure calculation modules;
- no reporting dependency from domain/IPIA;
- no new `sys.path` hacks;
- no methodology changes;
- no "cleanup" that removes provenance fields or comments encoding unresolved source assumptions.

## Package setup

Introduce `pyproject.toml` only as needed to create a proper package/test/import boundary.

Keep dependencies minimal.

Do not mix packaging changes and major module extraction in one large unverified step.

## BCB source correction

During the source-adapter phase, replace live source validation that depends on SGS `/ultimos/N` with deterministic date-bounded validation.

Treat this as a source-validation correctness fix and cover it with tests.

Do not alter the economic indicator formula as part of this correction.

## Verification loop for every extraction

```text
characterization test
        ↓
extract one responsibility
        ↓
small relevant tests
        ↓
full deterministic tests
        ↓
legacy --selftest
        ↓
git diff review
```

Stop and diagnose on failure.

Do not continue stacking extractions over a failing baseline.

## Acceptance criteria

- package imports work without manual `sys.path` manipulation;
- deterministic test suite passes;
- legacy `--selftest` still passes or has been explicitly replaced by proven equivalent coverage;
- CLI remains usable;
- report generation remains compatible;
- no duplicated network collection was introduced;
- no methodology output changed without an accepted change spec;
- architecture document reflects the final module boundaries.

## Final step

After the new architecture is stable, create a separate spec to:
- remove/thin the legacy monolith compatibility layer;
- remove obsolete embedded tests;
- automate persisted raw vintages/manifests.

Do not do those cleanups opportunistically during this refactor.
