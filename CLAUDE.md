# Steel Indicator — Project Instructions

## Mission
Build a reliable, reproducible and auditable engine for Brazilian steel-sector indicators, starting with the IPIA (Índice de Paridade de Importação do Aço).

Reliability is more important than speed. A published number must be reproducible from versioned methodology, source data, parameters and vintage metadata.

## Source of truth
Use this precedence when instructions conflict:

1. Tests and executable contracts for current behavior.
2. `docs/METODOLOGIA.md` for published calculation methodology.
3. Accepted ADRs in `docs/adr/`.
4. Accepted specs in `docs/specs/`.
5. `docs/architecture.md` for software boundaries.
6. `docs/data-sources.md` for source status and collection constraints.
7. Existing implementation.

Do not silently change methodology to make code cleaner.

## Default workflow
Use the simplest execution mode that can reliably solve the task.

### Trivial change
Inspect → edit → run relevant verification.

### Medium change
Inspect → short plan → edit → verify.

### Complex/refactoring/methodology change
Inspect → write or update a spec → define acceptance criteria → implement in small steps → verify after each step → final review.

Do not create an agent team by default.

Use a subagent only when isolated exploration, validation or review materially reduces main-context noise or improves coverage.

## Completion criteria
Implementation is not completion.

A task is complete only when:
- requested behavior is implemented;
- acceptance criteria are satisfied;
- relevant automated verification actually ran;
- real test output was inspected;
- known regressions are resolved;
- remaining uncertainty is explicitly reported.

Never claim a command, API call, test or source validation succeeded unless it actually ran and its output was observed.

## Verification
Current baseline command:

```bash
python src/indices_setoriais.py --selftest
```

During the test migration, preserve this command until external characterization tests cover the same behavior.

When pytest exists, run the smallest relevant test first, then the broader suite when appropriate.

Network checks are integration verification, not unit tests.

## Refactoring rule
Before moving behavior out of `src/indices_setoriais.py`, create characterization coverage for that behavior.

Refactor by extraction, not rewrite.

Keep each step:
- small;
- behavior-preserving;
- testable;
- reversible.

Do not combine architecture refactoring with methodology changes in the same step.

## Methodology invariants
Do not change these without an explicit accepted spec/ADR and corresponding tests:

- frozen reference window behavior;
- theoretical fixed weights;
- missing-data weight redistribution;
- minimum coverage rules;
- IPIA economic formula;
- domestic-price anchoring/chain methodology;
- volume-based confidence treatment;
- interpolation/smoothing semantics;
- data provenance taxonomy;
- vintage/cutoff rules;
- published methodology versioning.

Methodology-specific rules live in `.claude/rules/methodology.md`.

## Data integrity
Never fabricate, silently estimate or silently interpolate source data.

Every non-observed value must preserve explicit provenance.

Source availability is not source validity.

A successful HTTP response does not prove that a series, identifier, schema or observation is correct.

Do not use BCB SGS `/ultimos/N` as an ingestion or validation mechanism. Use deterministic date-bounded retrieval and validate the returned dates and values.

Every persistent raw collection must eventually support:
- collection timestamp;
- reference period;
- source identifier;
- observation count;
- validation status;
- content hash/vintage.

## Architecture
The current monolith is temporary.

Target boundaries are documented in `docs/architecture.md`.

Pure calculation code must not perform network or filesystem I/O.

Reporting must consume calculated outputs and must not independently recollect or recalculate business logic.

Do not introduce new `sys.path` manipulation.

## Git
You may inspect:
- `git status`
- `git diff`
- `git log`

Do not push without explicit user authorization.

Do not rewrite history or execute destructive Git commands without explicit authorization.

Do not remove tests to make verification pass.

## Security
Never read, edit, print or commit secrets, `.env` files or credentials.

Do not commit external client materials, private commercial strategy documents or the original research reports used to derive this project's technical rules.

Only distilled, project-specific technical knowledge belongs in this repository.

## Durable knowledge
Do not leave durable architectural or methodological decisions only in chat.

Use:
- `docs/specs/` before significant work;
- `docs/adr/` for accepted trade-off decisions;
- `docs/METODOLOGIA.md` for current published calculation methodology;
- `docs/data-sources.md` for source contracts/status;
- `docs/architecture.md` for software boundaries.

## Reporting at task end
Report:
- files changed;
- behavior changed or explicitly preserved;
- tests/commands executed;
- actual result;
- architecture or methodology decisions;
- unresolved risks or unverified assumptions.
