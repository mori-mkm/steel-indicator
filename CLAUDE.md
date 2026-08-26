# Steel Indicator — Project Instructions

## Mission

Build a reliable, reproducible and auditable multi-index platform for:
- IPIA-HRC;
- IPIA-Rebar;
- ICCS;
- ICS.

IIDB is out of scope.

Published numbers must be reproducible from versioned methodology, source data, historical parameters, provenance, vintage and code version.

## Source of truth

When instructions conflict:

1. verified later findings from real source validation and accepted decisions;
2. `docs/METODOLOGIA.md`;
3. accepted ADRs in `docs/adr/`;
4. accepted specs in `docs/specs/`;
5. `docs/architecture.md`;
6. `docs/data-sources.md`;
7. original research in `references/`;
8. characterization/golden tests as evidence of legacy behavior;
9. existing implementation.

**Legacy behavior is evidence, not authority.**

Golden tests preserve the old system for comparison. If accepted methodology intentionally changes legacy behavior, update/add tests explicitly instead of forcing the new implementation to reproduce the old result.

Never change methodology silently to make code cleaner or tests pass.

## References

`references/` contains original research, not direct implementation instructions:

- `catalogo_series_coleta.xlsx` — master series catalog; read `Leia-me` first.
- `guia_de_coleta_de_series.md` — later operational research and verified source findings.
- `manual_metodologico_indices_setoriais.md` — original methodological design.

Distill accepted decisions into `docs/`, ADRs and specs. Do not rewrite original research merely to match code.

## Workflow

Trivial: Inspect → edit → verify.

Medium: Inspect → short plan → edit → verify.

Complex/refactor/methodology/source change:
Inspect → classify work → write/update spec → define acceptance criteria → implement in small batches → verify each batch → review.

Use subagents only when isolated exploration, validation or review materially reduces context noise or improves coverage. Do not create agent teams by default.

## Classify significant work

### Behavior-preserving refactor
- characterization tests protect preserved behavior;
- extract before rewriting;
- keep changes small, reversible and testable;
- do not mix methodology changes into the same batch.

### Methodology correction/upgrade
- requires accepted spec and, when appropriate, ADR;
- state which legacy behavior changes;
- add tests for new methodology;
- keep legacy output available for comparison when useful;
- bump methodology version when published behavior changes.

### New capability/index
- derive requirements from accepted methodology and source contracts;
- reuse common infrastructure;
- do not copy legacy IPIA assumptions into ICCS/ICS without justification.

## Completion

A task is complete only when:
- requested behavior is implemented;
- acceptance criteria are satisfied;
- relevant tests actually ran and output was inspected;
- regressions are resolved;
- source status is not overstated;
- uncertainty and methodology impact are explicit.

Never claim a test, API call or source validation succeeded unless it actually ran and its output was observed.

## Verification baseline

```bash
python -m pytest tests/ -v
python src/indices_setoriais.py --selftest
```

Run the smallest relevant pytest target first, then the full suite.

Preserve `--selftest` until an accepted decision removes it. Never weaken tests to make verification pass.

Network/source checks are integration verification, not unit tests.

## Methodology invariants

Do not change without accepted methodology/spec decisions and tests:
- frozen reference-window behavior where applicable;
- fixed theoretical weights unless explicitly revised;
- missing-data weight redistribution;
- minimum publication coverage;
- provenance taxonomy;
- `reference_period`;
- vintage/cutoff rules;
- methodology versioning;
- OBSERVADO / CALCULADO / ESTIMADO / PROXY semantics.

Details live in `docs/METODOLOGIA.md`.

## IPIA target

Support HRC and rebar through one shared engine with separate:
- NCM baskets;
- domestic-price references;
- historical policy parameters;
- quality rules;
- provenance metadata.

The current IPIA is a legacy baseline to evolve.

Import side:
- use realized Comex Stat value/weight;
- use observed freight and insurance when available;
- validate NCM validity by historical period;
- never apply current tariffs, quotas, antidumping or AFRMM retroactively;
- maximize only methodologically comparable history.

Domestic side:
- use the highest-quality public product-specific source available;
- CVM/company disclosures + IPP are HRC V1, not a permanent hardcoded solution;
- `receita / volume` is valid only for sufficiently homogeneous scope;
- aggregated steel-segment values remain explicit PROXY;
- a better observed source supersedes a proxy when accepted.

Implement official monthly IPIA first. Keep any future weekly nowcast strictly separate.

Do not mark the new IPIA publication-ready until:
1. Comex Stat `/general` POST is validated live;
2. historical freight/insurance/CIF availability is confirmed;
3. NCMs are validated by historical period and extinct codes excluded;
4. the structured Aço Brasil Excel source is inspected and validated.

## ICCS

Later verified operational findings supersede conflicting assumptions in the older manual.

Use a two-layer design because fine sector credit balance exists while fine sector delinquency does not exist at the same granularity.

Do not invent fine-grained delinquency from credit slowdown.

The older 30% quality-pillar design is superseded; target about 22%, with the remainder redistributed toward pillars supported by finer sector data. Freeze exact weights in `docs/METODOLOGIA.md` before implementation.

## ICS

ICS follows IPIA and ICCS.

Initial target: synthetic sector conditions index using public activity data and shared infrastructure.

Survey/panel is a later extension.

Do not call a continuous-variable synthetic index a diffusion index unless it actually uses respondent diffusion.

## Data engineering

Production ingestion preference:
1. API;
2. CSV/XLSX;
3. official structured table;
4. PDF only as last resort.

If data exists only in PDF:
PDF → curation/validation → versioned structured artifact → pipeline.

A successful HTTP response does not prove identifier, label, schema or observation correctness.

Never use BCB SGS `/ultimos/N` for ingestion or validation. Use deterministic date-bounded retrieval.

Do not sum historical Comex NCM codes blindly. Validate code validity for each period.

## Provenance and vintages

Never fabricate, silently estimate or silently interpolate source data.

Preserve:
- OBSERVADO / CALCULADO / ESTIMADO;
- PROXY;
- `reference_period`.

Persistent raw collection must support or be designed to support collection timestamp, source ID, reference period, observation count, validation status, content hash, methodology version and code version.

## Architecture

Build one shared platform:

```text
collect → raw vintage → validate → normalize → transform
→ quality checks → index calculation → publication vintage
```

Shared infrastructure must serve IPIA, ICCS and ICS.

Pure calculations must not perform network/filesystem I/O.

Reporting consumes calculated result objects and must not recollect data or duplicate formulas.

Do not introduce new `sys.path` manipulation.

## Backfill

Goal: longest methodologically comparable history possible.

- 2020-present is a minimum target where feasible, not a cap;
- preserve historical tariff/tax/policy regimes;
- record structural breaks;
- never fill gaps silently just to create continuity;
- prefer a shorter defensible series over a longer synthetic one.

## Git and security

You may inspect `git status`, `git diff` and `git log`.

Do not push, rewrite history or run destructive Git commands without explicit authorization.

Never read, print, edit or commit secrets, `.env` files or credentials.

## Durable knowledge

Use:
- `docs/specs/` for significant implementation work;
- `docs/adr/` for accepted trade-offs;
- `docs/METODOLOGIA.md` for official methodology;
- `docs/data-sources.md` for source contracts/status;
- `docs/architecture.md` for software boundaries;
- `references/` as research evidence only.

## Task-end report

Report:
- files changed;
- behavior preserved vs intentionally changed;
- tests/commands and actual results;
- methodology/version impact;
- source validations performed;
- unresolved blockers/risks;
- whether the next batch is safe to start.
