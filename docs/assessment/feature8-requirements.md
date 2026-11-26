# Feature 8 requirement review

Standard: [DWMS Sub-Module Catalogue](../../SUB_MODULES.md), Feature 8 — Backup & DR.
This review maps the assignment requirements to evidence. The catalogue does not
provide numeric grading weights.

## Assignment

| Item | Catalogue requirement | Submission |
|---|---|---|
| Group | 1 — Platform | Backup & DR only; no unrelated application features. |
| Feature | 8 | PostgreSQL/PostGIS backup and recovery. |
| IMP branch | `feat/chore/backup-dr` | [Upstream PR #47](https://github.com/sas-bergson/Distributed-Waste-Management-System/pull/47). |
| TEST branch | `test/chore/dr-restore` | [Upstream PR #48](https://github.com/sas-bergson/Distributed-Waste-Management-System/pull/48). |
| DOC branch | `docs/chore/dr-runbook` | [Upstream PR #49](https://github.com/sas-bergson/Distributed-Waste-Management-System/pull/49). |
| Container/deployment | CI+MS; N/A runtime deployment | CI recovery checks and AWS S3 transfer commands; no additional application container. |
| Dependency | Feature 1 | Integration remains pending; the CLI accepts the actual database container name. |
| Week | W1 | Teaching-week eligibility needs confirmation from the course. |

## Role evidence

| Requirement | Evidence | Assessment |
|---|---|---|
| IMP: working code | `infrastructure/backup/backup.py` and `scheduled-backup.sh`; PR #1 | Implemented. Creates and checks archives, restores to new databases and provides S3 upload/download. |
| IMP: API contract | [CLI reference](../api/backup-cli.md) | All commands, arguments, defaults, effects and exit codes documented. No HTTP API was added; OpenAPI is not applicable. |
| IMP: unit tests | `infrastructure/backup/test_backup.py`; PR #1 checks | 15 tests passed. |
| TEST: integration and edge cases | `tests/backup/test_dr_restore.py`; PR #2 checks | Six real PostGIS tests passed. Recovery, corruption and preservation checks are covered. |
| DOC: tutorial | [Recovery exercise](../guides/backup-dr-tutorial.md) | Includes requirements, complete commands, sample data, expected results, failure checks and cleanup. The IMP-owned documentation workflow runs the actual Bash blocks. |
| DOC: operating procedure | [Runbook](../runbooks/backup-dr.md) | Includes backup, offsite transfer, restore, validation, reconciliation, cutover, targets, retention and troubleshooting. |
| DOC: architecture decision | [ADR-0008](../architecture/adr/0008-backup-dr.md) | Explains the choice, alternatives, trade-offs and acceptance conditions. |
| DOC: docstrings | CLI module, exception and helper docstrings | Present. Comments explain safety decisions rather than repeating every statement. |
| DOC: repeatable evidence | [Drill record](../runbooks/backup-drill-record.md) | Blank form separates measured results from untested targets. |

All Feature 8 workflows belong to the IMP branch. The documentation workflow
checks these six pages and runs the tutorial. Before integration, it resolves
missing DOC/IMP branches to exact commits and records their SHAs in the run log;
after integration, it uses files in the checkout. Review the
[IMP branch checks](https://github.com/lekeanyiKerring/Distributed-Waste-Management-System/pull/1/checks)
for results and the downloadable tutorial output.

## Submission process

| Catalogue rule | Record or remaining issue |
|---|---|
| One branch and PR per role | Three prescribed branches and three separate PRs. |
| Role boundaries | DOC changes only `docs/`; TEST changes only `tests/`; all `.github/workflows/` changes belong to IMP. |
| WIP title and `wip` label | The submissions started as draft/WIP and were later marked ready for review at the author's request. The author cannot apply upstream labels. Fork review records carry the initial `wip` label. |
| Discussion claim for each role | [IMP #4](https://github.com/lekeanyiKerring/Distributed-Waste-Management-System/discussions/4), [TEST #5](https://github.com/lekeanyiKerring/Distributed-Waste-Management-System/discussions/5), [DOC #6](https://github.com/lekeanyiKerring/Distributed-Waste-Management-System/discussions/6). |
| Claim before branch creation | Claims were posted after publication because repository/CLI authorization was completed later. The timestamps must not be represented as a different sequence. |
| First TEST artifact | The test file precedes the README in branch history. The workflow has been moved to IMP. Missing implementation causes an explicit failure. |
| First DOC artifact | The outline commit precedes the completed runbook. |
| First IMP artifact | Infrastructure commands and usage were committed. The required first OpenAPI artifact is not applicable to a CLI; the lecturer must accept this interpretation. |
| 48-hour first deliverable | Commit and Discussion timestamps are available; no earlier claim time is asserted. |
| Ready set and merged dependencies | The referenced ready-set file is absent from the baseline. Feature 1 is unmerged. Maintainer/course confirmation is required. |
| Merge target | Upstream `main`: PRs #47, #48 and #49. The earlier fork-local PRs remain review records. |
| Reviewer and definition of done | WIP PRs await independent review. No approval or merge is claimed. |

## Remaining acceptance work

1. Agree on the deployed PostgreSQL/PostGIS version with Feature 1 and repeat the
   recovery checks against that image.
2. Exercise the real S3/KMS account, encryption, versioning and retrieval path.
3. Configure and test the deployed schedule, failed-job alerts and retention.
4. Run the drill with representative data, service roles and application traffic.
   Record measured RPO/RTO, reconciliation and cutover results.
5. Confirm the CLI-contract interpretation, obtain the required reviewer approval
   and have maintainers apply the requested upstream `wip` labels.

These gaps cannot be closed by wording changes or invented test results. The
completed checks support the implemented scope; production acceptance remains
separate.
