---
paths:
  - "src/reporting/**/*.py"
  - "docs/report_design_system.md"
---

# Reporting rules

Reporting is a presentation layer.

- Do not recollect source data independently when the engine already has it.
- Do not reimplement IPIA or other methodology in charts/pages.
- Reuse the same calculated data object used by CSV/CLI outputs.
- Keep provenance labels visible where required: OBSERVADO, CALCULADO, ESTIMADO, PROXY.
- Preserve report cutoff/vintage reconciliation.
- Do not mix different reference months in one comparison without an explicit label.
- Report generation must remain testable with deterministic injected data.
- Avoid circular imports.
- Eliminate existing `sys.path` hacks only after package imports are covered by tests.
- Visual improvements must not silently alter numeric logic.
