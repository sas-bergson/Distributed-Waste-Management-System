# Backup CLI reference

Feature 8 provides a command-line interface, not an HTTP service. An OpenAPI
document is therefore not applicable. Run all commands from the project root:

```text
python infrastructure/backup/backup.py COMMAND [OPTIONS]
```

## Commands and arguments

| Command | Required options | Optional options |
|---|---|---|
| `backup` | `--container`, `--output` | `--database dwms`, `--user dwms` |
| `verify` | `--archive` | None |
| `restore` | `--container`, `--archive`, `--target-database` | `--user dwms` |
| `upload` | `--archive`, `--s3-uri`, `--kms-key-id` | None |
| `download` | `--s3-uri`, `--output` | None |

`--help` is available on the CLI and each subcommand. The optional values shown
are defaults. Filenames containing spaces must be quoted in the shell.

## Input rules

- Container: a name or ID beginning with a letter or digit; subsequent characters
  may also include `_`, `.` and `-`.
- Database and role: a lowercase letter followed by lowercase letters, digits or
  underscores, up to 63 characters in total.
- Recovery target: a valid database name beginning with `dwms_restore_`, followed
  by a suffix. The database must not already exist.
- S3 URI: one object, such as `s3://bucket/dwms/unique.dump`; no trailing slash,
  query string or fragment.
- KMS key: a nonempty key identifier accepted by the AWS CLI and authorized for
  the deployment.

## Files and database effects

| Command | Result | Failure behavior |
|---|---|---|
| `backup` | Custom-format database archive and `.sha256` sidecar | Failed dump or archive-list checks publish no pair. Existing outputs are preserved. |
| `verify` | Checks a nonempty archive against its sidecar | No Docker or AWS call; missing, malformed or mismatched checksums fail. |
| `restore` | New recovery database; one restore transaction | Existing target is rejected. A target created before a restore failure remains for inspection. |
| `upload` | Two SSE-KMS S3 objects; checksum sent last | A partial remote pair may remain. Use a new key for the next attempt. |
| `download` | Locally verified archive and sidecar | Incomplete or corrupt downloads are not published to the requested output. |

Local archives are not encrypted by this tool. Use restricted, encrypted storage.
SHA-256 checks integrity, not authorship. Restore only trusted archives. The CLI
does not restore original owners or grants, delete databases, enforce remote key
uniqueness, prune backups or change application connection settings.

## Authentication and errors

PostgreSQL authentication uses the configuration inside the database container.
No database-password argument is provided. AWS CLI uses its configured credential
chain. Credentials must not appear in committed files.

| Exit status | Meaning |
|---|---|
| `0` | Requested operation completed, or help was displayed. |
| `1` | An operation, filesystem access or validation failed. |
| `2` | Missing arguments or invalid CLI syntax. |

Success prints `PASS: COMMAND completed`. Operational errors print `FAIL:` to
stderr. Client stderr from Docker/AWS commands is suppressed to avoid disclosing
sensitive values. For diagnosis, check the trusted operator environment and server
logs without pasting credentials into public PRs.

## Scheduled job

`scheduled-backup.sh` requires Bash, `flock`, `python3`, Docker and AWS CLI v2.

| Variable | Required | Meaning |
|---|---|---|
| `BACKUP_DIRECTORY` | Yes | Absolute directory for original and retrieved archive pairs. |
| `BACKUP_CONTAINER` | Yes | Running PostgreSQL/PostGIS container. |
| `BACKUP_S3_PREFIX` | Yes | Approved bucket and object prefix. |
| `BACKUP_KMS_KEY_ID` | Yes | Approved KMS key ARN. |
| `BACKUP_DATABASE` | No | Source database; default `dwms`. |
| `BACKUP_USER` | No | Database role; default `dwms`. |

The job obtains a nonblocking lock, chooses a timestamp/UUID, creates the backup,
uploads it and verifies retrieval. It exits nonzero if any stage fails or another
job holds the lock. It retains both local archive pairs. Scheduling, alerting and
retention are configured separately.

See the [tutorial](../guides/backup-dr-tutorial.md) for an executable example and
the [runbook](../runbooks/backup-dr.md) for incident handling.
