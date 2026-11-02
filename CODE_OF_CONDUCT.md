# Code of Conduct

## Our Pledge

We are a cohort of students building the **Distributed Waste Management System (DWMS)** as a capstone project in Distributed Systems and Cloud Computing. We pledge to make participation in this project a harassment‑free, genuinely educational experience for everyone — regardless of experience level, language, disability, neurotype, appearance, gender identity or expression, sexual orientation, religion, nationality, academic background, or the grade you are currently on track to receive.

We recognise that a capstone is a **learning environment before it is a product**. People will be wrong in public, will break `main`, will misunderstand the assignment, and will ask questions that seem obvious. That is the point of the exercise. Our standard is not "never make mistakes" — it is "make the mistake visible and help fix it."

---

## Scope

This Code applies to everyone participating in this project: students, maintainers, instructors, teaching assistants, and external contributors.

It applies in **all project spaces**, including but not limited to:

- the GitHub repository (issues, pull requests, code review comments, commit messages, Discussions, wiki)
- project chat channels (WhatsApp, Discord, Slack, Teams) and email threads
- stand‑ups, lab sessions, pair‑programming sessions, and design meetings
- presentations, demos, poster sessions, and capstone defence
- any public space where you are representing the project or the course

It also applies when a project participant's conduct outside these spaces creates a hostile environment for other participants inside them.

---

## Expected Behaviour

### 1. Respect the learner, critique the work

Technical disagreement is expected and welcome — design arguments are how the architecture gets good. Direct your criticism at the **design, the code, the evidence**, never at the person. Compare these:

- ✅ *"This viewport query will do a full table scan once we pass ~50k locations — can we add a GiST index and show the query plan?"*
- ❌ *"You clearly don't understand spatial indexes. Did you even read the PostGIS docs?"*

The first is a review comment. The second is a person being made to feel stupid in front of their team. The second is not tolerated here.

### 2. Assume competence, ask before explaining

Assume your teammate has a reason for the code you are reading; ask what it was before rewriting it. A PR that "fixes" someone's work without a word in the issue thread is a small act of disrespect, and it is one of the most common ways capstone teams quietly fall apart.

### 3. Make room for different levels of experience

Some students are strong in Python, others in frontend, others in documentation, others in testing and QA. **None of these is worth more than another to this project**, and none is a licence to condescend to the people whose strength is elsewhere. If you are the person who understands PostGIS, your job includes explaining it — not gatekeeping it.

### 4. Communicate in the open

Prefer issues, PR comments, and Discussions over private DMs for technical decisions. Private decisions exclude teammates, produce duplicated work, and cannot be graded fairly. It is fine to DM someone for a personal matter or to ask for help privately — just do not use private channels for project decisions.

### 5. Share the credit honestly

This project is graded, and credit matters. In every PR description, state who did what if multiple people contributed. In presentations and reports, **name the people who built the thing**. Do not present a teammate's work as your own, and do not quietly omit a contributor.

### 6. Name your branch so ownership is visible

Branch names are not cosmetic. In a shared repository, the branch name is how your teammates know **what you are working on, which objective it serves, and that the work is yours** — before they read a single line of code. Clear naming is how we avoid two students building the same thing, and how a reviewer can tell at a glance whether a change is in scope.

<type>/<objective>/<short-slug>

| Part | Values | Meaning |
|------|--------|---------|
| **type** | `feat` · `fix` · `docs` · `refactor` · `test` · `chore` · `adr` | What kind of change this is |
| **objective** | `obj1` · `obj2` · `obj3` (or `chore`) | Which project objective the work advances |
| **slug** | short, hyphenated, lowercase | What specifically you are changing |

**Examples**

```bash
feat/obj2/road-condition-layer
fix/obj1/offline-sync-duplicate-reports
adr/obj3/realtime-backplane-choice

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
The full convention, with the type prefixes and slug rules, is in [`CONTRIBUTING.md` → Branching Strategy](CONTRIBUTING.md#branching-strategy). The principle is:
