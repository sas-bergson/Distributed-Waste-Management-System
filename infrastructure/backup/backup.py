"""Feature 8: verified PostgreSQL archives and explicit S3 transfers."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import BinaryIO
from urllib.parse import urlsplit


class BackupError(Exception):
    """A backup operation could not complete safely."""


def run(
    command: list[str],
    *,
    stdin: BinaryIO | None = None,
    stdout: BinaryIO | int = subprocess.DEVNULL,
) -> None:
    """Execute without a shell; suppress potentially sensitive server errors."""
    try:
        subprocess.run(
            command, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE, check=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BackupError(
            f"{command[0]} operation failed; check availability, access and server logs"
        ) from exc


def identifier(value: str) -> str:
    """Accept ordinary PostgreSQL identifiers only, including no CLI options."""
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", value):
        raise BackupError("database/user must match [a-z][a-z0-9_]{0,62}")
    return value


def docker(container: str, *arguments: str) -> list[str]:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", container):
        raise BackupError("invalid container name or ID")
    return ["docker", "exec", "-i", container, *arguments]


def checksum_path(archive: Path) -> Path:
    return archive.with_name(archive.name + ".sha256")


def digest(archive: Path) -> str:
    with archive.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def verify(archive: Path) -> None:
    """Require a nonempty archive and an exact SHA-256 sidecar."""
    expected = checksum_path(archive).read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise BackupError("invalid SHA-256 sidecar")
    if archive.stat().st_size == 0 or digest(archive) != expected:
        raise BackupError("archive is empty or SHA-256 does not match")


def publish(source: Path, output: Path) -> None:
    """Publish without overwriting; the sidecar marks a complete archive pair."""
    sidecar = checksum_path(output)
    if output.exists() or sidecar.exists():
        raise BackupError("output archive or sidecar already exists")
    archive_created = False
    checksum_created = False
    complete = False
    try:
        with output.open("xb") as target:
            archive_created = True
            os.chmod(output, 0o600)
            with source.open("rb") as data:
                while chunk := data.read(1024 * 1024):
                    target.write(chunk)
        with sidecar.open("x", encoding="ascii") as target_hash:
            checksum_created = True
            os.chmod(sidecar, 0o600)
            target_hash.write(digest(output) + "\n")
        complete = True
    finally:
        if not complete:
            if archive_created:
                output.unlink(missing_ok=True)
            if checksum_created:
                sidecar.unlink(missing_ok=True)


def backup(container: str, database: str, user: str, output: Path) -> None:
    identifier(database)
    identifier(user)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dwms-backup-", dir=output.parent) as tmp:
        archive = Path(tmp) / "database.dump"
        with archive.open("wb") as stream:
            run(
                docker(
                    container,
                    "pg_dump",
                    "--no-password",
                    "--format=custom",
                    "--username",
                    user,
                    "--dbname",
                    database,
                ),
                stdout=stream,
            )
        with archive.open("rb") as stream:
            run(docker(container, "pg_restore", "--list"), stdin=stream)
        if archive.stat().st_size == 0:
            raise BackupError("pg_dump returned an empty archive")
        publish(archive, output)


def restore(container: str, user: str, archive: Path, target: str) -> None:
    identifier(user)
    identifier(target)
    if not target.startswith("dwms_restore_") or target == "dwms_restore_":
        raise BackupError("target must start with dwms_restore_ and be a new database")
    verify(archive)
    # Validate archive structure before creating anything in the database server.
    with archive.open("rb") as stream:
        run(docker(container, "pg_restore", "--list"), stdin=stream)
    # createdb fails if the name exists. Never drop or clean an existing database.
    run(
        docker(
            container,
            "createdb",
            "--no-password",
            "--username",
            user,
            "--template=template0",
            target,
        )
    )
    with archive.open("rb") as stream:
        run(
            docker(
                container,
                "pg_restore",
                "--no-password",
                "--username",
                user,
                "--dbname",
                target,
                "--no-owner",
                "--no-privileges",
                "--exit-on-error",
                "--single-transaction",
            ),
            stdin=stream,
        )


def s3_uri(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "s3"
        or not parsed.netloc
        or not parsed.path.strip("/")
        or parsed.query
        or parsed.fragment
        or value.endswith("/")
    ):
        raise BackupError("S3 URI must identify one object: s3://bucket/path/file.dump")
    return value


def upload(archive: Path, uri: str, kms_key_id: str) -> None:
    verify(archive)
    s3_uri(uri)
    if not kms_key_id.strip():
        raise BackupError("a KMS key ID is required")
    # The checksum is uploaded last; absent checksum means incomplete publication.
    for source, destination in [
        (archive, uri),
        (checksum_path(archive), uri + ".sha256"),
    ]:
        run(
            [
                "aws",
                "s3",
                "cp",
                str(source),
                destination,
                "--only-show-errors",
                "--sse",
                "aws:kms",
                "--sse-kms-key-id",
                kms_key_id,
            ]
        )


def download(uri: str, output: Path) -> None:
    s3_uri(uri)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dwms-download-", dir=output.parent) as tmp:
        archive = Path(tmp) / "database.dump"
        for source, destination in [
            (uri, archive),
            (uri + ".sha256", checksum_path(archive)),
        ]:
            run(["aws", "s3", "cp", source, str(destination), "--only-show-errors"])
        verify(archive)
        publish(archive, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser(
        "backup", help="create a verified custom-format archive"
    )
    create.add_argument("--container", required=True)
    create.add_argument("--database", default="dwms")
    create.add_argument("--user", default="dwms")
    create.add_argument("--output", type=Path, required=True)
    recover = commands.add_parser(
        "restore", help="restore into a new recovery database"
    )
    recover.add_argument("--container", required=True)
    recover.add_argument("--user", default="dwms")
    recover.add_argument("--archive", type=Path, required=True)
    recover.add_argument("--target-database", required=True)
    check = commands.add_parser("verify", help="verify local archive checksum")
    check.add_argument("--archive", type=Path, required=True)
    send = commands.add_parser("upload", help="explicitly upload to S3 using SSE-KMS")
    send.add_argument("--archive", type=Path, required=True)
    send.add_argument("--s3-uri", required=True)
    send.add_argument("--kms-key-id", required=True)
    fetch = commands.add_parser("download", help="download and verify an S3 archive")
    fetch.add_argument("--s3-uri", required=True)
    fetch.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "backup":
            backup(args.container, args.database, args.user, args.output)
        elif args.command == "restore":
            restore(args.container, args.user, args.archive, args.target_database)
        elif args.command == "verify":
            verify(args.archive)
        elif args.command == "upload":
            upload(args.archive, args.s3_uri, args.kms_key_id)
        else:
            download(args.s3_uri, args.output)
    except (BackupError, OSError, UnicodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {args.command} completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
