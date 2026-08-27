---
paths:
  - "src/indices_setoriais.py"
  - "src/sources/**/*.py"
  - "src/data/**/*.py"
  - "src/collectors/**/*.py"
  - "data/**/*"
  - "docs/data-sources.md"
---

# Data pipeline rules

## Source truth
- Source availability does not imply source validity.
- Never mark a source VERIFIED solely because the request returned HTTP 200.
- Validate identifiers, dates, schema, units and observation semantics.
- Use the verification states defined in `docs/data-sources.md`.

## BCB SGS
- Never use `/ultimos/N` for ingestion or source validation.
- Use deterministic date-bounded retrieval and check the returned reference dates.

## Raw data
- Raw observations must remain reproducible.
- Never silently overwrite a prior vintage with a revised source response.
- Preserve enough metadata to answer: "what value did we have when this publication was produced?"

## Provenance
Never hide:
- interpolation;
- smoothing;
- proxy use;
- formula alternatives;
- estimated/hold-flat values.

Observed and derived data must remain distinguishable.

## Collection design
Collectors should:
1. retrieve;
2. preserve raw response;
3. validate contract;
4. normalize;
5. return typed/structured data.

Calculation code should not know HTTP details.

## Failure behavior
Prefer explicit FAIL/UNKNOWN states to silent fallback.

If a required source cannot be validated, do not present the resulting indicator as fully verified.
