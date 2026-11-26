#!/usr/bin/env bash
# Feature 8: one serialized backup, encrypted upload and verified retrieval.
set -euo pipefail
umask 077

: "${BACKUP_DIRECTORY:?Set an absolute, access-restricted backup directory}"
: "${BACKUP_CONTAINER:?Set the running PostgreSQL/PostGIS container name or ID}"
: "${BACKUP_S3_PREFIX:?Set an approved s3://bucket/prefix without a trailing slash}"
: "${BACKUP_KMS_KEY_ID:?Set the approved KMS key ARN}"
[[ "$BACKUP_DIRECTORY" == /* ]] || { echo 'FAIL: BACKUP_DIRECTORY must be absolute' >&2; exit 1; }
command -v flock >/dev/null
mkdir -p -- "$BACKUP_DIRECTORY"
exec 9>"$BACKUP_DIRECTORY/.backup.lock"
flock -n 9 || { echo 'FAIL: another backup is running' >&2; exit 1; }

script_directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
backup_id=$(python3 -c 'from datetime import datetime, timezone; import uuid; print(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex)')
archive="$BACKUP_DIRECTORY/$backup_id.dump"
object="${BACKUP_S3_PREFIX%/}/$backup_id.dump"
tool="$script_directory/backup.py"

python3 "$tool" backup --container "$BACKUP_CONTAINER" --database "${BACKUP_DATABASE:-dwms}" --user "${BACKUP_USER:-dwms}" --output "$archive"
python3 "$tool" upload --archive "$archive" --s3-uri "$object" --kms-key-id "$BACKUP_KMS_KEY_ID"
python3 "$tool" download --s3-uri "$object" --output "$BACKUP_DIRECTORY/$backup_id.retrieved.dump"
echo "PASS: offsite publication and retrieval verified for $backup_id"
# Retention and deletion require a separately approved operating policy.
