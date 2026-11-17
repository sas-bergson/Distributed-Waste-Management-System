# Distributed Waste Management System (DWMS)

A multi-service platform that lets citizens and field agents report waste locations and road conditions, shows them on a color-coded map, and lets authorised users request collection services (the SPF) in real time.

> **Status:** under active development by a large multi-squad student team. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before your first pull request.

---

## Table of contents

1. [Project objectives](#project-objectives)
2. [System overview](#system-overview)
3. [Technology stack](#technology-stack)
4. [Repository layout](#repository-layout)
5. [Getting started](#getting-started)
6. [How we work](#how-we-work)
7. [Pull request format](#pull-request-format)
8. [Reviewer checklist](#reviewer-checklist)
9. [AI-assisted contributions](#ai-assisted-contributions)
10. [License](#license)

---

## Project objectives

Every change to this repository advances one of three objectives, or is a `chore` (tooling, docs, CI, refactor).

| # | Objective | Notes |
|---|---|---|
| 1 | Collect waste-location information | Primary objective. Drives the reporter app and the data model. |
| 2 | Color-coded map of waste amount and road condition | Visual layer built on the shared palette. |
| 3 | Cloud service to view/update the map and request the SPF in real time | Shared back end used by every client. |
| `chore` | Tooling, docs, CI, refactor | No objective. |

---

## System overview

The platform is split into independent services that talk to each other only through documented contracts (OpenAPI specifications in `docs/api/`).

| Service | Responsibility |
|---|---|
| `frontend/reporter` | Citizen and field-agent application (mobile and web): sign-in, waste and road-condition reports, offline operation and synchronisation, map, SPF requests, notifications. |
| `frontend/dashboard` | Operator-facing view of the map and requests. |
| `gateway` | Single entry point for clients: routing, authentication, rate limiting. |
| `locations` | Storage and retrieval of waste locations and road conditions. |
| `map` | Aggregation and styling data for the color-coded map. |
| `requests` | SPF request creation and lifecycle. |
| `realtime` | Live map updates and notifications. |
| `infra` | Containers, deployment and CI configuration. |

> The service list above comes from the contribution guidelines. Confirm each responsibility against the service's own folder and ADRs before relying on it.

### Waste-location status

A waste location moves through a defined status lifecycle as seen by the reporter, including being **reopened after collection** if the problem returns. The authoritative state diagram is in the functional requirements document under `docs/requirements/`.

---

## Technology stack

Items marked **confirmed** appear in the project's contribution tooling. Items marked **proposed** come from the technology brief and require an architecture decision record (ADR) before adoption.

| Layer | Technology | Status |
|---|---|---|
| Back-end services | Python, tested with `pytest`, dependencies managed with `uv` | Confirmed |
| Database | PostgreSQL with PostGIS (spatial queries use GiST indexes) | Confirmed |
| Schema migrations | Alembic (must be reversible) | Confirmed |
| Web front end | TypeScript, dependencies managed with `pnpm` | Confirmed |
| API contracts | OpenAPI, stored in `docs/api/` | Confirmed |
| Palette | `palette.json` as the single source of color values | Confirmed |
| Code quality | `pre-commit` hooks (lint, format, type checks) | Confirmed |
| Mobile app | Flutter (Dart) | Proposed |
| Real-time service | Go, with Redis publish/subscribe | Proposed |
| Maps | MapLibre GL with vector tiles | Proposed |
| Photo storage | S3-compatible object storage | Proposed |
| Push notifications | Firebase Cloud Messaging | Proposed |
| Containers and CI | Docker Compose, GitHub Actions | Proposed |

**Language policy.** The project uses a small, deliberate set of languages (target: five), each tied to a named role and owning squad. A new language requires an ADR.

**Design rules**

- No hard-coded palette hex values in components. Colors come from `palette.json`.
- Offline first on mobile: reports are saved locally and synchronised later.
- Geospatial work stays in the database and uses GiST indexes.
- Never commit secrets, `.env` files or real citizen data.

---

## Repository layout

Expected layout. Check the repository for the current structure.

```text
.
├── docs/
│   ├── api/              # OpenAPI specifications
│   ├── requirements/     # Functional and non-functional requirements
│   └── adr/              # Architecture decision records
├── frontend/
│   ├── reporter/         # Citizen / field-agent app
│   └── dashboard/        # Operator dashboard
├── services/
│   ├── gateway/
│   ├── locations/
│   ├── map/
│   ├── requests/
│   └── realtime/
├── infra/                # Deployment and CI configuration
├── palette.json          # Shared color palette
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
└── README.md
```

---

## Getting started

### Prerequisites

- Git
- Python and [`uv`](https://docs.astral.sh/uv/)
- Node.js and [`pnpm`](https://pnpm.io/)
- PostgreSQL with the PostGIS extension (or Docker)
- [`pre-commit`](https://pre-commit.com/)

### Set up your copy

```bash
# 1. Fork the repository on GitHub, then clone YOUR fork
git clone https://github.com/<your-username>/Distributed-Waste-Management-System.git
cd Distributed-Waste-Management-System

# 2. Add the original repository as "upstream"
git remote add upstream https://github.com/sas-bergson/Distributed-Waste-Management-System.git

# 3. Install the git hooks
pre-commit install
```

### Run the checks

```bash
uv run pytest -q              # Python tests
pnpm test                     # Front-end tests
pre-commit run --all-files    # Lint, format, type checks
```

Service-specific run instructions live in each service's own folder.

---

## How we work

### Branches

Always branch from an up-to-date `upstream/main`.

```bash
git fetch upstream
git switch -c <type>/<objective>/<slug> upstream/main
```

Format: `<type>/<objective>/<slug>`, for example `feat/obj2/road-condition-layer`. If CONTRIBUTING.md asks for a student name segment, use `<type>/<objective>/<student>/<slug>`.

### Commits

Use [Conventional Commits](https://www.conventionalcommits.org/) with an `Objective:` footer.

```text
feat(map): add road-condition layer

Objective: 2
```

### Pull requests

- One concern per pull request, target **under about 400 changed lines**.
- Rebase on `upstream/main`; do not merge it into your branch.
- CI must be green. Pull requests with empty sections or failing CI are returned without review.
- Merge strategy: **squash-and-merge**. The author merges after approval. Never merge unreviewed work.

### Decisions and contracts

- Contract first: update the OpenAPI specification in `docs/api/` before or with any contract change.
- Record significant decisions as ADRs. If your change contradicts an existing ADR, say so in the pull request.

---

## Pull request format

Every pull request must use this template. Copy it into the pull request description (or keep it as `.github/pull_request_template.md` so GitHub fills it in automatically).

````markdown
<!--
Thanks for contributing to DWMS. Fill in every section below.
PRs with empty sections, or with failing CI, will be sent back without review.
Read CONTRIBUTING.md → Pull Request Process before submitting.
-->

## Summary

<!-- One or two sentences: what does this PR change, and why? -->

**Linked issue:** Closes #

**Objective(s):**
<!-- Tick every objective this change advances. See README → Project Objectives. -->

- [ ] **1** — Collect waste-location information
- [ ] **2** — Color-coded map of waste amount + road condition
- [ ] **3** — Cloud service to view/update the map and request the SPF in real time
- [ ] `chore` — tooling, docs, CI, refactor (no objective)

**Services touched:**
<!-- e.g. locations, map, requests, realtime, gateway, frontend/dashboard, infra -->

---

## What changed

<!--
Bullet list of the concrete changes. Be specific enough that a reviewer who has
not read the diff knows what to look for.
-->

## Why this approach

<!--
Briefly: what alternatives did you consider, and why did you choose this one?
If you made a design decision others should know about, link the ADR or open one.
If this contradicts an existing ADR, say so explicitly.
-->

---

## How it was tested

<!-- Paste the actual commands you ran and their output.
"It works" is not evidence. -->

**Commands run:**

```bash
# e.g.
uv run pytest -q
pnpm test
pre-commit run --all-files
```

**Result:**

<!-- Paste summary output, or "all passing" with the counts -->

**Manual verification steps:**

<!-- Numbered steps a reviewer can follow to see it working themselves -->

### Map / visual changes

<!-- Required if you touched services/map/, palette.json, or any
frontend map component. Otherwise write "N/A". -->

- [ ] Before screenshot attached
- [ ] After screenshot attached
- [ ] Screenshot at low zoom (clustered)
- [ ] Screenshot at high zoom (unclustered)
- [ ] Legend checked for both dimensions (waste amount + road condition)
- [ ] Greyscale / colour-vision check performed

### Spatial / database changes

<!-- Required if you touched a schema, migration, or spatial query.
Otherwise write "N/A". -->

- [ ] Alembic migration included and reversible
- [ ] Spatial query uses a GiST index
- [ ] EXPLAIN ANALYZE output reviewed (paste below, redact if needed)

---

### AI assistance

<!-- Per CODE_OF_CONDUCT.md → AI-assisted contributions, disclose here if an AI tool
generated or substantially shaped this contribution. Disclosure is not a penalty;
concealment is the problem. -->

- [ ] No AI tool was used for this contribution
- [ ] AI tool was used — details below

**Tool:**

**What it produced and how I verified it:**

### Breaking changes

<!-- Does this change any request/response shape, endpoint path, event payload,
database schema, or palette value? If yes, describe the impact and the migration
path for existing clients. If no, write "None". -->

- [ ] No breaking changes
- [ ] Breaking change — described below

**Impact and migration path:**

### Author checklist

<!-- Every box must be ticked before requesting review. -->

- [ ] Branch name follows `<type>/<objective>/<slug>` (e.g. `feat/obj2/road-condition-layer`)
- [ ] PR is scoped to one concern and is reasonably small (target < ~400 changed lines)
- [ ] Commits follow the Conventional Commits format with an `Objective:` footer
- [ ] Branched from an up-to-date `upstream/main` (rebased, not merged)
- [ ] CI is green
- [ ] Tests added or updated per CONTRIBUTING.md → Testing Requirements
- [ ] Lint and type checks pass locally (`pre-commit run --all-files`)
- [ ] README.md / docs/ updated if behaviour, endpoints, or the palette changed
- [ ] OpenAPI spec updated in `docs/api/` for any contract change
- [ ] No secrets, credentials, `.env` files, or real citizen data committed
- [ ] No hard-coded palette hex values in components
- [ ] Credit is accurate: co-authors named if multiple people contributed
- [ ] I have read CONTRIBUTING.md and CODE_OF_CONDUCT.md

### Reviewer notes

<!-- Optional: anything you want the reviewer to focus on, or known gaps. -->

**Focus areas for review:**

**Known limitations / follow-up issues:**
````

---

## Reviewer checklist

Reviewers confirm that:

- The objective is correctly declared and the change is in scope for it.
- The branch name matches the convention.
- The approach is sound. Design concerns are raised as comments, not silent rewrites.
- Tests genuinely cover the change (not just "a test exists").
- Spatial queries are indexed and reviewed for performance.
- Map changes include screenshots and a working legend.
- There are no secrets, no real personal data and no hard-coded palette values.
- AI disclosure is present if applicable.
- The Definition of Done in CONTRIBUTING.md is satisfied.
- Comments are labelled **must fix** or **nit**.

**Merge:** squash-and-merge. The author merges after approval. Do not merge unreviewed work.

---

## AI-assisted contributions

AI tools are allowed. If a tool generated or substantially shaped your contribution, disclose it in the pull request: which tool, what it produced, and how you verified it. Disclosure is not a penalty; concealment is the problem. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

---

## License

See the [LICENSE](LICENSE) file in the repository.
