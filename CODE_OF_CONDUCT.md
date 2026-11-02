
---

## Consistency check across your three files

The branch convention is now referenced in three places, each with a distinct job. Confirm they match before you commit:

| File | Role in branch naming | Action needed |
|------|----------------------|---------------|
| **`CODE_OF_CONDUCT.md`** | States *why* it matters and what is unacceptable (claim‑jumping, force‑push, misleading names). Defer to CONTRIBUTING as normative. | ✅ Done above |
| **`CONTRIBUTING.md`** | The normative mechanics: type prefixes, slug rules, `git fetch upstream` / rebase commands, squash‑merge. | Already present — no change needed |
| **`.github/PULL_REQUEST_TEMPLATE.md`** | Enforces it at review time. | ⚠️ **Still to do.** Add the checklist line below |

Add this to the PR template checklist so the rule survives past week one:

```markdown
- [ ] Branch name follows `<type>/<objective>/<slug>` (e.g. `feat/obj2/road-condition-layer`)
