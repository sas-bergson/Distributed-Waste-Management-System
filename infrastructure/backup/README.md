# Database backup tooling

Feature 8, IMP role. Requires Python 3.11+ and a running PostgreSQL/PostGIS
container with its matching `pg_dump` and `pg_restore` clients. AWS CLI v2 is
required only for explicit S3 transfers. No Python packages are required.

```bash
python infrastructure/backup/backup.py --help
python infrastructure/backup/backup.py backup --container dwms-postgis --user dwms --database dwms --output /secure/backups/dwms-20261125T120000Z.dump
python infrastructure/backup/backup.py verify --archive /secure/backups/dwms-20261125T120000Z.dump
python infrastructure/backup/backup.py restore --container dwms-postgis --user dwms --archive /secure/backups/dwms-20261125T120000Z.dump --target-database dwms_restore_drill
```

Use the actual container name/ID and database role from your Compose environment;
the pending Compose scaffold currently uses `dwms-postgis`. Credentials remain
in the container's authentication configuration. No password CLI flag is provided.
Archive bytes pass through Docker stdin/stdout without a pseudo-terminal.

The archive covers one database, including all its application schemas, data,
sequences and extension definitions. It excludes cluster roles, tablespaces,
external media, Redis, MQTT and infrastructure configuration. Restoration omits
original ownership/ACLs; an operator must separately provision roles and grants.

Every complete archive has a `.sha256` sidecar. SHA-256 detects accidental
corruption; it does not authenticate an untrusted archive. Restore only backups
from a trusted source. Outputs never overwrite local files. Failed restores leave
the new recovery database for inspection; the tool never drops a database.

For optional managed storage, use unique timestamp/UUID object keys in an
operator-provisioned private, versioned S3 bucket and an approved KMS key:

```bash
python infrastructure/backup/backup.py upload --archive /secure/backups/dwms-20261125T120000Z.dump --s3-uri s3://YOUR-BUCKET/dwms/UNIQUE-ID.dump --kms-key-id YOUR-KMS-KEY-ARN
python infrastructure/backup/backup.py download --s3-uri s3://YOUR-BUCKET/dwms/UNIQUE-ID.dump --output /secure/recovery/UNIQUE-ID.dump
```

AWS authentication uses the AWS CLI credential chain. Upload sends both objects
with SSE-KMS and publishes the checksum last. A failed upload may leave a partial
remote pair; do not reuse that key. Downloads publish locally only after validation.
The tool does not create cloud resources, install a production schedule, prune
objects, or switch application traffic. Production deployment requires an approved
bucket policy, KMS/IAM configuration, schedule, monitoring and recovery drill.

`scheduled-backup.sh` runs one serialized backup/upload/download-verification job
on a trusted Linux host. It requires Bash, `flock`, Python 3.11+ as `python3`,
Docker, AWS CLI v2 and the `BACKUP_DIRECTORY`, `BACKUP_CONTAINER`,
`BACKUP_S3_PREFIX`, `BACKUP_KMS_KEY_ID` environment variables. Optional
`BACKUP_DATABASE` and `BACKUP_USER` default to `dwms`. It keeps the original and
retrieved archive pairs for inspection. An operator must install the schedule,
configure failure alerts and enforce retention; no schedule is installed by CI.

Run unit tests with `python -m unittest discover -s infrastructure/backup -p 'test_*.py' -v`.

References: [pg_dump](https://www.postgresql.org/docs/16/app-pgdump.html),
[pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html),
[AWS S3 copy](https://docs.aws.amazon.com/cli/latest/reference/s3/cp.html).
