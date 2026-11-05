```
<!--
Thanks for contributing to DWMS. Fill in every section below.
PRs with empty sections, or with failing CI, will be sent back without review.
Read CONTRIBUTING.md → Pull Request Process before submitting.
-->
```
## Summary
```
<!-- One or two sentences: what does this PR change, and why? -->
```
**Linked issue:** Closes #

**Objective(s):**
```
<!-- Tick every objective this change advances. See README → Project Objectives. -->
```
- [ ] **1** — Collect waste‑location information
- [ ] **2** — Color‑coded map of waste amount + road condition
- [ ] **3** — Cloud service to view/update the map and request the SPF in real time
- [ ] `chore` — tooling, docs, CI, refactor (no objective)

**Services touched:**
```
<!-- e.g. locations, map, requests, realtime, gateway, frontend/dashboard, infra -->
```
---

## What changed
```
<!--
Bullet list of the concrete changes. Be specific enough that a reviewer who has
not read the diff knows what to look for.
-->
```

## Why this approach
```
<!--
Briefly: what alternatives did you consider, and why did you choose this one?
If you made a design decision others should know about, link the ADR or open one.
If this contradicts an existing ADR, say so explicitly.
-->
```
---

## How it was tested
```
<!-- Paste the actual commands you ran and their output.
"It works" is not evidence. -->
```
**Commands run:**

```bash
# e.g.
uv run pytest -q
pnpm test
pre-commit run --all-files
```
## Result:
```
<!-- Paste summary output, or "all passing" with the counts -->
```
### Manual verification steps:
```
<!-- Numbered steps a reviewer can follow to see it working themselves -->
```
### Map / visual changes
```
<!-- Required if you touched services/map/, palette.json, or any
frontend map component. Otherwise write "N/A". -->
```
+ Before screenshot attached
+ After screenshot attached
+ Screenshot at low zoom (clustered)
+ Screenshot at high zoom (unclustered)
+ Legend checked for both dimensions (waste amount + road condition)
+ Greyscale / colour‑vision check performed
+ Spatial / database changes
---
```
<!-- Required if you touched a schema, migration, or spatial query.
Otherwise write "N/A". -->
```
+ Alembic migration included and reversible
+ Spatial query uses a GiST index
+ EXPLAIN ANALYZE output reviewed (paste below, redact if needed)

### AI assistance
```
<!-- Per CODE_OF_CONDUCT.md → AI‑assisted contributions, disclose here if an AI tool
generated or substantially shaped this contribution. Disclosure is not a penalty;
concealment is the problem. -->
```
+ No AI tool was used for this contribution
+ AI tool was used — details below
*** Tool: ***
```
<!-- What it produced and How I verified it: -->
```
### Breaking changes
```
<!-- Does this change any request/response shape, endpoint path, event payload, database schema,
or palette value? If yes, describe the impact and the migration path for existing clients.
If no, write "None". -->
```
+ No breaking changes
+ Breaking change — described below
+ Impact and migration path

### Author checklist
```
<!-- Every box must be ticked before requesting review. -->
```
+ Branch name follows <type>/<objective>/<slug> (e.g. feat/obj2/road-condition-layer)
+ PR is scoped to one concern and is reasonably small (target < ~400 changed lines)
+ Commits follow the Conventional Commits format with an Objective: footer
+ Branched from an up‑to‑date upstream/main (rebased, not merged)
+ CI is green
+ Tests added or updated per CONTRIBUTING.md → Testing Requirements
+ Lint and type checks pass locally (pre-commit run --all-files)
+ README.md / docs/ updated if behaviour, endpoints, or the palette changed
+ OpenAPI spec updated in docs/api/ for any contract change
+ No secrets, credentials, .env files, or real citizen data committed
+ No hard‑coded palette hex values in components
+ Credit is accurate: co‑authors named if multiple people contributed
+ I have read CONTRIBUTING.md and CODE_OF_CONDUCT.md

### Reviewer notes
```
<!-- Optional: anything you want the reviewer to focus on, or known gaps. -->
```
Focus areas for review:

 *** Known limitations / follow‑up issues: ***
```
<!--  <details> <summary><strong>For reviewers — checklist</strong></summary> -->
```
+ Objective is correctly declared and the change is actually in scope for it
+ Branch name matches the convention
+ The approach is sound; design concerns raised as comments, not silent rewrites
+ Tests genuinely cover the change (not just "a test exists")
+ Spatial queries are indexed and reviewed for performance
+ Map changes include screenshots and a working legend
+ No secrets, no real personal data, no hard‑coded palette values
+ AI disclosure present if applicable
+ Definition of Done in CONTRIBUTING.md is satisfied
+ Comments labelled must fix vs nit
Merge: squash‑and‑merge. Author merges after approval; do not merge unreviewed work.
```
<!--  </details> -->
```
