# Recovery drill record

Copy this form for each drill. Fill in observed values; leave unmeasured fields
marked `not measured`. This blank form is not a completed recovery report.

## Identification

| Field | Recorded value |
|---|---|
| Drill or incident ID | Not recorded |
| Operator and reviewer | Not recorded |
| Start and finish, with timezone | Not recorded |
| Environment | Not recorded |
| Source and recovery image versions/digests | Not recorded |
| Implementation, test and documentation commit SHAs | Not recorded |
| Database name and size | Not recorded |
| Archive identifier and SHA-256 | Not recorded |
| Backup snapshot time | Not recorded |
| Offsite completion time | Not recorded |
| S3 object version IDs, if used | Not recorded |

## Validation results

| Check | Pass/fail/not run | Evidence or issue |
|---|---|---|
| Archive and checksum available | Not run | |
| Archive listing readable | Not run | |
| Both application schemas restored | Not run | |
| Report counts and sample coordinates/SRIDs checked | Not run | |
| Spatial indexes and sequence values checked | Not run | |
| Request states and audit records checked | Not run | |
| Original database preserved | Not run | |
| Existing target and damaged archive rejected | Not run | |
| Service roles, grants and tenant isolation checked | Not run | |
| External media and message/request reconciliation completed | Not run | |
| Application reporting, map and SPF workflows checked | Not run | |
| Offsite retrieval and KMS access verified | Not run | |
| Failed-job alert received | Not run | |
| Cutover accepted by incident owner | Not run | |

## Recovery measurements

| Measurement | Observed value |
|---|---|
| Incident declaration time | Not measured |
| Selected snapshot time | Not measured |
| Replacement host ready | Not measured |
| Download and verification complete | Not measured |
| Database restore complete | Not measured |
| Reconciliation and application validation complete | Not measured |
| Service restored | Not measured |
| Measured RPO: incident time minus selected snapshot time | Not measured |
| Measured RTO: service-restored time minus incident declaration | Not measured |

The proposed six-hour RPO and sixty-minute RTO pass only if the measured results
meet those values. A CI test duration does not include all production recovery
stages and must not be entered as production RTO.

## Review and follow-up

- Result and reviewer decision:
- Missing data or failed checks:
- Corrective action, owner and due date:
- Next drill date:
- Links to redacted logs and CI evidence:

Follow the [runbook](backup-dr.md). Keep credentials and citizen data out of this
record when it is shared publicly.
