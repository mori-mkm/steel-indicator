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
- whether the next batch is safe to start;
- autonomy level used;
- whether escalation occurred;
- final autonomy level, if different from initial;
- user decisions still required, if any.

## Autonomy Policy

Classify every significant task as Level 1, 2 or 3 before implementation.

### Classification header

State briefly before starting:

```
AUTONOMY CLASSIFICATION
Level: <1|2|3>
Reason: <one sentence>
Potential escalation triggers:
- ...
```

Not an approval gate. Level 1/2: state it, begin immediately. Level 3: investigate, present the decision (format below), stop before implementation.

### LEVEL 1 — AUTONOMOUS

Inspect, edit, test, review, continue to the next safe substep — no approval needed.

Typical work: behavior-preserving refactors; moving code without changing behavior; characterization/unit tests; deterministic bug fixes caused by the current refactor; structural extraction; documenting already-verified facts; formatting/cleanup with no behavior change.

Rules: behavior and methodology unchanged; no new economic assumption; no new data source; no commit/push without explicit authorization.

Loop: inspect → characterize if needed → implement → test → review → continue if safe. Don't stop between safe substeps.

**Multi-batch autonomy**: run consecutive micro-batches toward the same authorized objective without asking between them.
- test after each micro-batch; continue if passing and behavior-preserving;
- fix only regressions caused by this work;
- escalate to Level 2/3 the moment a concern of that level appears;
- don't stop just to ask permission already granted;
- don't invent extra work to keep going;
- stop when the objective is done.

### LEVEL 2 — AUTONOMOUS + REVIEW GATE

Implement autonomously; result must pass a read-only review before the task is complete.

Typical work: new source adapter; integration with an existing source; temporal parameter model after methodology is decided; new deterministic transformation; new data validation layer; wiring an approved contract into production; replacing legacy code with an approved equivalent.

Loop: inspect → characterize → implement → test → code-reviewer → fix only local behavior-preserving issues → test again → stop with report.

Reviewer checks: accidental methodology change, behavior regression, premature abstraction, source/domain boundary violations, unintended network/I/O, compatibility, missing tests, import cycles.

**Review result**:
- APPROVE → final verification, report, stop.
- BLOCK, technical/local → fix, test, re-review.
- BLOCK, methodology/product/economics/publication → escalate to Level 3, do not implement.

No commit/push without explicit authorization.

### LEVEL 3 — USER DECISION REQUIRED

Do not choose the answer autonomously.

Typical work: methodology; index weights; proxy selection; economic rules; publication criteria; product scope; treatment of economically meaningful missing data; historical comparability decisions; assumptions that change published values; choosing between competing official interpretations; judging whether uncertain evidence is publication-grade; changing an index's meaning.

Process: investigate → present evidence → identify the decision → present options and consequences → recommend if useful → **STOP before implementation**. Implementation starts only after the user explicitly chooses.

**Decision output format** — use when a Level 3 decision blocks implementation:

```
DECISION: <what needs to be decided>
WHY IT MATTERS: <what behavior/result changes>
EVIDENCE:
- FACT:
- DOC:
- INFERENCE:
- UNKNOWN:
OPTION A: <description>
Impact: <impact>
OPTION B: <description>
Impact: <impact>
OPTION C (only if genuinely reasonable): <description>
Impact: <impact>
RECOMMENDATION: <option and why>
IMPLEMENTATION BLOCKED: <what can't proceed until decided>
```

Don't invent options to fill the format. OPTION C is optional. Separate fact/doc/inference/unknown. Claude may recommend; the user decides. No implementation before the explicit choice.

### Escalation, default classification, efficiency

Escalate upward only, never silently downward: Level 1 finding a Level 2 concern → apply Level 2; Level 1/2 finding a Level 3 decision → stop and ask. Never convert a Level 3 decision into a technical assumption to keep working.

If uncertain: behavior-only → Level 1; new implementation of already-approved behavior → Level 2; change to meaning/economics/publication → Level 3. Still uncertain → pick the higher level.

Autonomy levels exist to cut unnecessary approval loops — don't ask permission for work already authorized. Stop only when the level requires it, an escalation requires it, a stop condition is hit, or the authorized scope is done. Don't keep working just to spend tokens.

### Git Policy

Autonomy level never authorizes Git publication.

Allowed anytime: `git status`, `git diff`, `git diff --stat`, `git log`.

Never without explicit authorization: `git add`, `git commit`, `git push`, merge, rebase, `reset --hard`, force push.

The user creates the final checkpoint after reviewing the batch.