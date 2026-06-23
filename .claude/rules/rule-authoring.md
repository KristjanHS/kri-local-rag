---
paths:
  - ".claude/rules/**/*.md"
---
# Rule Authoring

When adding a rule example that documents a *shipped* fix, grep the actual emitted form in the committed code and copy it verbatim — not the design-doc version. Design docs often carry the pre-fix form; shipping that as the rule example re-introduces the original bug as a template for the next implementer.
