# Tests

The test suite is being migrated from the embedded `selftest()` in `src/indices_setoriais.py`.

Planned layers:

- `characterization/`: freezes current behavior before structural refactoring.
- `unit/`: pure deterministic logic after extraction.
- `integration/`: live external-source contract checks.
- reporting tests may remain under characterization/unit depending on scope.

Rules:

- no live network calls in unit or characterization tests;
- keep `--selftest` until equivalent coverage exists;
- never weaken a regression test merely to make a refactor pass.
