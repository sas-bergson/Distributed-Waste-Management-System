# Practice a database recovery

Feature 8 — Backup & DR, DOC role.

This exercise starts a temporary PostGIS database, saves a backup, deletes a sample
report and restores the report into a new database. It uses no cloud account,
published ports, mounted data directories or real citizen data.

## Requirements

- Python 3.11+ available as `python`.
- Docker running Linux containers, with permission to pull `postgis/postgis:16-3.4`.
- Bash, `mktemp`, `cp` and `tee`. Use Linux, WSL or Git Bash for these commands.
- The Feature 8 IMP script at `infrastructure/backup/backup.py`.

Start in the project root and use the same Bash session for every step. If only
the DOC branch is checked out, open the combined local review folder or set
`DWMS_BACKUP_TOOL` to a checked-out copy of the IMP script. Do not merge another
role's source files into the DOC branch just to run this exercise.

## 1. Start a temporary database

The unique container name prevents a clash with another student's environment.
The exit trap removes only this container when the shell ends. Backup files remain
in the printed temporary directory for inspection.

```bash
set -euo pipefail
tool="${DWMS_BACKUP_TOOL:-infrastructure/backup/backup.py}"
test -f "$tool"
python -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
container="dwms-tutorial-$(python -c 'import uuid; print(uuid.uuid4().hex[:12])')"
work=$(mktemp -d "${TMPDIR:-/tmp}/dwms-tutorial.XXXXXX")
trap 'docker rm -f "$container" >/dev/null 2>&1 || true' EXIT
docker run -d --name "$container" \
  -e POSTGRES_USER=dwms -e POSTGRES_DB=dwms \
  -e POSTGRES_PASSWORD=tutorial-only-password postgis/postgis:16-3.4
ready=false
for attempt in $(seq 1 60); do
  if docker exec "$container" pg_isready -h 127.0.0.1 -U dwms -d dwms; then
    ready=true
    break
  fi
  sleep 1
done
test "$ready" = true
echo "Backup directory: $work"
```

The password above is for the temporary exercise container only. Readiness should
end with `accepting connections`; failure stops the exercise.

## 2. Add a report and collection request

```bash
docker exec -i "$container" psql -X -U dwms -d dwms -v ON_ERROR_STOP=1 <<'SQL'
CREATE SCHEMA locations;
CREATE SCHEMA requests;
CREATE TABLE locations.reports (
  id serial PRIMARY KEY,
  label text NOT NULL,
  position geometry(Point,4326) NOT NULL
);
CREATE INDEX reports_position_idx ON locations.reports USING gist(position);
CREATE TABLE requests.dispatches (id serial PRIMARY KEY, status text NOT NULL);
INSERT INTO locations.reports(label, position)
  VALUES ('Douala', ST_SetSRID(ST_Point(9.7,4.0),4326));
INSERT INTO requests.dispatches(status) VALUES ('REQUESTED');
SQL
```

The two schemas represent the storage used by the reporting and request services.
These are test fixtures, not the application's production migrations.

## 3. Back up, then simulate a deleted report

```bash
python "$tool" backup --container "$container" --output "$work/snapshot.dump"
python "$tool" verify --archive "$work/snapshot.dump"
test -s "$work/snapshot.dump"
test -s "$work/snapshot.dump.sha256"
docker exec "$container" psql -X -U dwms -d dwms -v ON_ERROR_STOP=1 \
  -c 'DELETE FROM locations.reports;'
test "$(docker exec "$container" psql -X -U dwms -d dwms -Atc 'SELECT count(*) FROM locations.reports')" = 0
```

Expect `PASS: backup completed`, `PASS: verify completed` and `DELETE 1`.
Only the sample row in the temporary container is deleted.

## 4. Recover and check the result

```bash
python "$tool" restore --container "$container" --archive "$work/snapshot.dump" \
  --target-database dwms_restore_tutorial
recovered=$(docker exec "$container" psql -X -U dwms -d dwms_restore_tutorial -Atc \
  "SELECT label || ':' || ST_AsText(position) || ':SRID=' || ST_SRID(position) FROM locations.reports")
test "$recovered" = 'Douala:POINT(9.7 4):SRID=4326'
test "$(docker exec "$container" psql -X -U dwms -d dwms_restore_tutorial -Atc 'SELECT status FROM requests.dispatches')" = REQUESTED
test "$(docker exec "$container" psql -X -U dwms -d dwms_restore_tutorial -Atc "SELECT nextval('locations.reports_id_seq')")" = 2
test "$(docker exec "$container" psql -X -U dwms -d dwms_restore_tutorial -Atc "SELECT count(*) FROM pg_indexes WHERE schemaname='locations' AND indexname='reports_position_idx' AND indexdef LIKE '%USING gist%'")" = 1
test "$(docker exec "$container" psql -X -U dwms -d dwms -Atc 'SELECT count(*) FROM locations.reports')" = 0
echo "$recovered"
```

The report, request state, sequence and spatial index must be recovered. The
source database remains at zero reports: the restore does not alter it.

## 5. Check two failure cases

The next two failures are expected. The script fails if either operation is
incorrectly accepted.

```bash
if python "$tool" restore --container "$container" --archive "$work/snapshot.dump" \
  --target-database dwms_restore_tutorial; then
  echo 'FAIL: an existing recovery database was accepted' >&2
  exit 1
fi
test "$(docker exec "$container" psql -X -U dwms -d dwms_restore_tutorial -Atc 'SELECT count(*) FROM locations.reports')" = 1
cp "$work/snapshot.dump" "$work/damaged.dump"
cp "$work/snapshot.dump.sha256" "$work/damaged.dump.sha256"
printf 'damaged' >> "$work/damaged.dump"
if python "$tool" verify --archive "$work/damaged.dump"; then
  echo 'FAIL: a damaged archive was accepted' >&2
  exit 1
fi
echo 'PASS: tutorial checks complete'
```

The final line confirms that the recovery and failure checks passed. Exit the
exercise shell to remove the temporary container, or run the next command now:

```bash
docker rm -f "$container"
```

Keep the output as drill evidence. This small exercise does not measure production
RPO/RTO, verify S3 permissions or switch application traffic. Continue with the
[operating runbook](../runbooks/backup-dr.md) and [command reference](../api/backup-cli.md).
