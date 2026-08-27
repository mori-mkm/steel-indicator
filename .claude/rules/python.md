---
paths:
  - "src/**/*.py"
---

# Python architecture rules

- Preserve behavior during refactoring unless an accepted spec explicitly changes it.
- Prefer pure functions for calculation and transformations.
- Network, filesystem and presentation side effects belong behind explicit boundaries.
- Do not add new `sys.path` manipulation.
- Prefer dependency injection or explicit inputs over mutating module globals.
- Reuse existing dependencies before adding a new package.
- Constants that affect published calculations must be named, documented and tested.
- Do not catch broad exceptions merely to continue with fabricated/default output.
- Keep public return schemas stable during extraction steps unless the spec says otherwise.
- New modules should have one primary responsibility.
- Avoid circular imports; reporting may depend on domain/calculation outputs, never the reverse.
