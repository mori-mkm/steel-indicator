---
paths:
  - "src/indices_setoriais.py"
  - "src/domain/**/*.py"
  - "src/ipia/**/*.py"
  - "src/indexes/**/*.py"
  - "docs/METODOLOGIA.md"
  - "docs/adr/**/*.md"
---

# Methodology rules

`docs/METODOLOGIA.md` and accepted ADRs are the methodology source of truth.

A code refactor must not change the economic/statistical definition of an indicator.

## Changes requiring an explicit spec/ADR
- IPIA formula or component inclusion;
- domestic-price anchor;
- NCM basket/scoping decision;
- tax/tariff/antidumping treatment;
- internalization parameters or their interpretation;
- reference window;
- winsorization;
- weights;
- coverage thresholds;
- interpolation/smoothing;
- confidence weighting;
- provenance classification;
- official vs nowcast semantics;
- cutoff/vintage behavior.

## Methodology version
If the published calculation changes, evaluate whether `VERSAO_METODOLOGIA` must be bumped and update methodology documentation in the same change.

## IPIA invariant
Conceptually:

`IPIA = (domestic price / import parity cost) × 100`

Do not duplicate this formula in presentation code.

## Auditability
Every published transformation must be explainable from:
- source observation;
- parameter;
- documented rule;
- code version;
- methodology version;
- vintage/cutoff.

Unknown regulatory/source status must remain explicit, never guessed.
