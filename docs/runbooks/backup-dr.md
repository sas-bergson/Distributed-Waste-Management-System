# Backup and disaster recovery runbook

| Field | Value |
|---|---|
| Feature | 8 — Backup & DR |
| Owner | Platform; submission by `lekeanyiKerring` |
| Role | DOC — `docs/chore/dr-runbook` |
| Status | Proposed operating procedure; production rollout pending |
| Dependency | Feature 1 Compose orchestration and Feature 8 IMP |
| Decision | [ADR-0008](../architecture/adr/0008-backup-dr.md) |

For a first run, follow the [sample recovery tutorial](../guides/backup-dr-tutorial.md).
Use the [CLI reference](../api/backup-cli.md) for arguments and exit codes, and
copy the [drill record](backup-drill-record.md) when collecting recovery evidence.

## What the backup covers

Recover the DWMS PostgreSQL database, including the `locations` and `requests`
schemas, spatial columns, indexes, sequences and PostGIS extension definitions.
Both schemas are captured in the same database snapshot. Their normal service
access rules remain in place.

Cluster roles, tablespaces, authentication configuration, application secrets,
container images, external photographs, Redis and MQTT state are outside the
archive. Recreate approved roles and grants separately. Redis must be rebuilt or
reconciled, and pending MQTT/events/notifications assessed before application
cutover. Do not replay external collection dispatches without checking for
duplicate requests. External media needs its own backup policy.

## Recovery targets

The proposed targets are an **RPO of six hours** and an **RTO of sixty minutes**.
Measure both before production acceptance. Complete a backup and its offsite
upload within every six-hour window, allowing time for execution and retries.

RPO is measured from the incident to the snapshot time of the selected usable
backup. RTO runs from incident declaration to verified service restoration,
including provisioning, transfer, database recovery, reconciliation and cutover.
Measure both during a representative drill; revise cadence or architecture if
the measured results miss either target. Logical backups provide no point-in-time
recovery between snapshots.

## Before you start

1. Verify Feature 1 is deployed and locate the actual database container:
   `docker compose ps`. The pending scaffold uses `dwms-postgis`; other deployments
   may use a different name or ID.
2. Install Python 3.11+ and Docker access on a trusted operator host. The database
   image provides the matching PostgreSQL clients. AWS CLI v2 is needed for S3.
3. Use a database role with sufficient dump and recovery privileges. Examples use
   `dwms`; use the actual `POSTGRES_USER` from the deployment. Authentication must
   work inside the container without an interactive password prompt.
4. Allocate an access-restricted backup directory on encrypted storage with space
   for an archive, temporary copy and recovered database. Archives contain
   application data and are not encrypted by the local Python tool.
5. Before offsite operation, provision a private S3 bucket, versioning, an approved
   KMS key, TLS-only policy, retention policy and least-privilege workload identity.
   The operator needs PutObject/GetObject for the approved prefix and the relevant
   KMS permissions. Use temporary credentials; never commit credentials or dumps.
6. Record the source image version, database name, role/grant provisioning source,
   backup identifier and incident/drill owner outside the database being protected.

## Create and verify a backup

Run these commands from the project root. Use a new timestamp or UUID for every
backup and replace the example paths with your backup directory.

```bash
python infrastructure/backup/backup.py backup --container dwms-postgis --user dwms --database dwms --output /secure/backups/dwms-20261125T120000Z.dump
python infrastructure/backup/backup.py verify --archive /secure/backups/dwms-20261125T120000Z.dump
```

Keep the `.dump` and `.dump.sha256` files together. Backup creation checks the
archive listing; verification checks its checksum. A restore test is still needed
to confirm recovery. Use archives from trusted administrators and storage.

## Upload and retrieve the offsite copy

```bash
python infrastructure/backup/backup.py upload --archive /secure/backups/dwms-20261125T120000Z.dump --s3-uri s3://YOUR-BUCKET/dwms/UNIQUE-ID.dump --kms-key-id YOUR-KMS-KEY-ARN
python infrastructure/backup/backup.py download --s3-uri s3://YOUR-BUCKET/dwms/UNIQUE-ID.dump --output /secure/recovery/UNIQUE-ID.dump
```

Upload explicitly requests SSE-KMS for both objects. The checksum is published
last. A failed upload can leave an incomplete pair; record the failure and retry
with a new unique key. Never replace an existing remote key. The CLI does not
enforce remote key uniqueness, so bucket versioning and the operating procedure
are required. A successful download validates both objects before publishing the
local output. Retain the selected S3 version identifiers in the recovery record.

An approved scheduler can invoke `bash infrastructure/backup/scheduled-backup.sh`
on a trusted Linux host with access to the database. The job requires Bash,
`flock`, Python 3.11+ as `python3`, Docker and AWS CLI v2. Set `BACKUP_DIRECTORY`
to an absolute restricted directory, `BACKUP_CONTAINER` to the database container,
`BACKUP_S3_PREFIX` to the approved bucket/prefix and `BACKUP_KMS_KEY_ID` to the KMS
key ARN. Optional `BACKUP_DATABASE` and `BACKUP_USER` default to `dwms`.
The job prevents overlapping runs, generates unique names and fails if backup,
upload or verified retrieval fails. It retains both local archive pairs. Configure
alerts on any nonzero exit or missing successful offsite backup. This contribution
does not install a production scheduler or cloud resources.

Proposed retention: retain all six-hour snapshots for seven days and designated
daily snapshots for thirty days. Configure and test S3 lifecycle/version retention
before rollout. This tool never deletes backups. Remove local copies only after
offsite retrieval is verified and retention requirements are satisfied.

## Restore into an isolated database

1. Declare the incident and stop automated application writes using the approved
   application maintenance procedure. Preserve the source database and logs.
2. Select the newest trusted, complete backup preceding the unwanted change. For
   corruption, this may be older than the newest available archive.
3. Provision a recovery PostgreSQL/PostGIS instance using the approved compatible
   image version. Recreate the required database role and authentication. For
   a drill, the source instance may host a separate recovery database if capacity
   permits; a real host-loss incident requires a replacement instance.
4. Download and verify the archive, then restore:

```bash
python infrastructure/backup/backup.py restore --container RECOVERY-CONTAINER --user dwms --archive /secure/recovery/UNIQUE-ID.dump --target-database dwms_restore_incident_20261125
```

The command accepts only new names prefixed `dwms_restore_`. An existing database
is rejected. Restore uses one transaction and fails on SQL errors; it never drops
or cleans an existing database. If recovery fails after database creation, the new
database remains for diagnosis. Investigate and use a new target name for a retry.
Deletion of a failed recovery database is a separate operator action.

## Validate, reconcile and cut over

Run application-specific checks before permitting traffic:

```bash
docker exec RECOVERY-CONTAINER psql -X -U dwms -d dwms_restore_incident_20261125 -v ON_ERROR_STOP=1 -c "SELECT PostGIS_Version(); SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('locations','requests');"
```

Verify actual application table counts, selected report coordinates/SRIDs, spatial
indexes, request states, audit records and sequence values against the backup
record and known samples. The automated drill uses sample tables. Repeat the
checks against the actual application schema when migrations change.

Restore required grants separately: recovery deliberately does not reinstate
original owners or ACLs. Verify tenant isolation and service access with the real
application roles. Reconcile outstanding SPF requests and asynchronous messages.

After the incident owner accepts validation, update the approved database
connection configuration to the new database, restart dependent services, check
health endpoints, and verify reporting, mapping and collection-request workflows.
Record the exact cutover time. Preserve the previous instance for investigation.
Rollback to the old instance requires an explicit data reconciliation decision;
new writes after cutover must not be silently discarded.

## Tests and recovery drills

```bash
python -m unittest discover -s infrastructure/backup -p 'test_*.py' -v
DWMS_RUN_DR_INTEGRATION=1 python -m unittest discover -s tests/backup -p 'test_*.py' -v
```

In PowerShell, set `$env:DWMS_RUN_DR_INTEGRATION = '1'` before the second Python
command. Without opt-in, integration tests are skipped, not passed. The integration
suite belongs to the separate TEST contribution and must be present to run it.

Run a recovery drill before production acceptance and at least monthly thereafter.
Record commit/image versions, backup snapshot time, offsite completion time,
archive hash, S3 versions, database size, restore duration, validation results,
measured RPO/RTO, owner and follow-up actions. Do not attach citizen data or
credentials to a public PR. Cloud access and production recovery times still need
testing in the deployment environment.

## Troubleshooting

| Failure | Response |
|---|---|
| Docker unavailable or database authentication fails | Confirm container identity, running state and role/authentication configuration; do not put passwords in command arguments. |
| Existing local output | Choose a new unique backup name; preserve existing copies. |
| Missing or mismatched checksum | Quarantine the pair and choose another trusted backup. Do not regenerate a checksum to hide corruption. |
| Existing target database | Inspect it and choose a fresh `dwms_restore_` name. |
| Unsupported archive/PostGIS version | Recover with a compatible approved PostgreSQL/PostGIS image and matching clients. |
| S3/KMS access denied | Confirm identity, prefix policy, key region and KMS grants; do not make the bucket public. |
| Restore SQL failure | Preserve diagnostics, check extension availability and disk space, and retry into a fresh target after correction. |

## References

- [PostgreSQL 16 pg_dump](https://www.postgresql.org/docs/16/app-pgdump.html)
- [PostgreSQL 16 pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html)
- [AWS CLI S3 copy and encryption options](https://docs.aws.amazon.com/cli/latest/reference/s3/cp.html)
