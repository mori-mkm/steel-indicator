# Spec 0002 — External Characterization Tests

**Status:** Ready  
**Type:** Behavior-preserving refactor prerequisite  
**Methodology change:** No

## Problem

`src/indices_setoriais.py` contains the only broad regression harness in a ~630-line embedded `selftest()`.

The same module contains production logic, network adapters, CLI and test monkeypatching through mutable globals.

Refactoring modules before externalizing critical behavior creates unnecessary regression risk.

## Goal

Introduce pytest-based external characterization tests that lock down current behavior before module extraction.

Keep `--selftest` working during the migration.

## Non-goals

- do not change formulas;
- do not change public output schemas;
- do not modularize all production code yet;
- do not rewrite tests from scratch based on desired behavior;
- do not call live network services in unit/characterization tests.

## Required initial coverage

Externalize protections for:

1. fixed reference-window z-score behavior;
2. winsorization;
3. index anchor at 50;
4. negative orientation;
5. missing-weight redistribution and coverage threshold;
6. specification weight validation;
7. IPIA arithmetic;
8. import volume confidence;
9. selective smoothing;
10. domestic-price weighting;
11. IPP chaining / hold-flat semantics;
12. full domestic + import → IPIA round-trip using frozen inputs;
13. no duplicate collection when raw Comex data is injected;
14. spread reconciliation using the same reference month;
15. cutoff/look-ahead detection;
16. provenance classification and report badges;
17. Aço Brasil parsers using frozen representative fixtures where legally appropriate;
18. PDF report smoke test if it can remain deterministic.

## Test layout

```text
tests/
├── characterization/
│   ├── test_index_engine_current.py
│   ├── test_ipia_current.py
│   ├── test_domestic_price_current.py
│   ├── test_provenance_current.py
│   └── test_reporting_current.py
├── unit/
└── integration/
```

Use actual names discovered from the implementation; do not force this exact split if a smaller clear structure is better.

## Dependency decision

Adding pytest is allowed by this spec, but do it explicitly as a development/test dependency.

Do not add broad frameworks.

## Migration strategy

For each group:

1. copy the behavioral intent from `selftest()`;
2. express it as an external pytest test;
3. run old `--selftest`;
4. run new test;
5. compare;
6. only then proceed to the next group.

Do not delete the original check during this spec unless there is a one-to-one equivalent and keeping both creates a clear maintenance problem. Prefer temporary duplication over losing regression protection.

## Acceptance criteria

- `python src/indices_setoriais.py --selftest` passes;
- external deterministic pytest suite passes;
- tests contain no live network calls;
- no published formula/parameter/default changed;
- no output column disappeared;
- failures identify specific behavior rather than only returning one aggregate status.

## Final report

Report:
- selftest checks externalized;
- checks intentionally still embedded;
- commands run and results;
- any behavior that was impossible to characterize without changing architecture.

Do not begin module extraction until this spec is complete.
