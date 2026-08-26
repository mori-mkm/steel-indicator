# Spec 0001 — Harness Setup

**Status:** Ready for validation  
**Type:** Development infrastructure  
**Methodology change:** No

## Problem

The project has useful project instructions but they are concentrated in one `CLAUDE.md`, with no path-scoped rules or reusable specialized subagents.

This increases recurring context cost and makes the development workflow less deterministic.

## Goal

Create a lightweight Claude Code harness that:

- keeps universal instructions concise;
- loads specialized rules only for relevant paths;
- uses one main Claude session by default;
- provides three bounded subagents for exploration, data validation and code review;
- preserves explicit permission boundaries;
- makes verification the stop condition for development tasks.

## Files

- `CLAUDE.md`
- `.claude/settings.json`
- `.claude/rules/*.md`
- `.claude/agents/*.md`
- `docs/architecture.md`
- `docs/data-sources.md`

## Non-goals

- no production-code refactor;
- no methodology change;
- no new dependency;
- no agent team;
- no removal of `selftest()`.

## Acceptance criteria

- Claude Code loads the project `CLAUDE.md`;
- path-scoped rules are syntactically valid;
- the three project subagents are discoverable;
- the baseline command still runs:
  `python src/indices_setoriais.py --selftest`;
- no production Python file changed as part of harness installation.

## Validation

1. Run `git diff`.
2. Run `python src/indices_setoriais.py --selftest`.
3. In Claude Code run `/context` and confirm the project memory file is loaded.
4. If supported by the installed Claude Code version, run:
   `claude plugin validate .claude/agents`
5. Start a new Claude session before beginning Spec 0002 so the new harness is loaded cleanly.

## Done when

The harness files are committed separately from any application refactor.
