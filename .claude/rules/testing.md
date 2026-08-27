---
paths:
  - "tests/**/*.py"
  - "src/indices_setoriais.py"
---

# Testing rules

Before structural refactoring, characterize current behavior externally.

## Test layers

### Unit
- deterministic;
- no network;
- no external mutable data;
- small behavior surface.

### Characterization
- capture current behavior of the monolith before extraction;
- use representative frozen inputs;
- protect public schemas and known bug fixes.

### Integration
- may call external sources;
- validate contracts, identifiers, schema and dates;
- must fail clearly when the source contract changes.

### Reporting
- deterministic fixtures for core report calculations and provenance;
- PDF smoke tests may remain, but numeric logic belongs outside presentation.

## Migration from selftest
- Do not delete `selftest()` first.
- Reproduce its protections in external tests.
- Compare old and new results.
- Remove or thin the embedded selftest only after equivalent coverage exists.

## Refactoring loop
1. make characterization test pass on old code;
2. extract one responsibility;
3. run smallest relevant tests;
4. run full deterministic suite;
5. inspect diff;
6. continue.

A failing test is evidence to diagnose, not something to bypass.
