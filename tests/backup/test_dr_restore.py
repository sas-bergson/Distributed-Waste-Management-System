"""Feature 8 TEST: isolated PostgreSQL/PostGIS recovery contract."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import ClassVar
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[2]
TOOL = Path(
    os.environ.get("DWMS_BACKUP_TOOL", ROOT / "infrastructure/backup/backup.py")
)


@unittest.skipUnless(
    os.environ.get("DWMS_RUN_DR_INTEGRATION") == "1",
    "set DWMS_RUN_DR_INTEGRATION=1 to run the isolated Docker recovery drill",
)
class RecoveryContractTests(unittest.TestCase):
    container: ClassVar[str]
    tmp: ClassVar[tempfile.TemporaryDirectory[str]]
    archive: ClassVar[Path]

    @classmethod
    def setUpClass(cls) -> None:
        if not TOOL.is_file():
            raise RuntimeError("Feature 8 implementation is required; see the IMP PR")
        cls.container = "dwms-dr-test-" + uuid.uuid4().hex[:12]
        cls.tmp = tempfile.TemporaryDirectory(prefix="dwms-dr-test-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.addClassCleanup(
            subprocess.run,
            ["docker", "rm", "-f", cls.container],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                cls.container,
                "-e",
                "POSTGRES_USER=dwms",
                "-e",
                "POSTGRES_DB=dwms",
                "-e",
                "POSTGRES_PASSWORD=ci-only-password",
                "postgis/postgis:16-3.4",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        for _ in range(60):
            ready = subprocess.run(
                [
                    "docker",
                    "exec",
                    cls.container,
                    "pg_isready",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    "dwms",
                    "-d",
                    "dwms",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("isolated PostGIS container did not become ready")
        cls.sql(
            "dwms",
            """
            CREATE SCHEMA locations;
            CREATE SCHEMA requests;
            CREATE TABLE locations.reports (
                id serial PRIMARY KEY, label text NOT NULL,
                position geometry(Point,4326) NOT NULL
            );
            CREATE INDEX reports_position_idx ON locations.reports USING gist(position);
            CREATE TABLE requests.dispatches (id serial PRIMARY KEY, status text NOT NULL);
            INSERT INTO locations.reports(label,position)
                VALUES ('Douala', ST_SetSRID(ST_Point(9.7,4.0),4326));
            INSERT INTO requests.dispatches(status) VALUES ('REQUESTED');
        """,
        )
        cls.archive = Path(cls.tmp.name) / "snapshot.dump"
        result = cls.cli(
            "backup", "--container", cls.container, "--output", str(cls.archive)
        )
        if result.returncode:
            raise RuntimeError(result.stderr)

    @classmethod
    def cli(cls, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(TOOL), *arguments],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

    @classmethod
    def sql(cls, database: str, sql: str) -> str:
        result = subprocess.run(
            [
                "docker",
                "exec",
                cls.container,
                "psql",
                "-X",
                "-U",
                "dwms",
                "-d",
                database,
                "-At",
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                sql,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return result.stdout.strip()

    def test_full_spatial_recovery_and_sequence(self) -> None:
        target = "dwms_restore_" + uuid.uuid4().hex[:12]
        result = self.cli(
            "restore",
            "--container",
            self.container,
            "--archive",
            str(self.archive),
            "--target-database",
            target,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.sql(
                target,
                "SELECT label || ':' || ST_AsText(position) FROM locations.reports",
            ),
            "Douala:POINT(9.7 4)",
        )
        self.assertEqual(
            self.sql(target, "SELECT status FROM requests.dispatches"), "REQUESTED"
        )
        self.assertEqual(
            self.sql(target, "SELECT nextval('locations.reports_id_seq')"), "2"
        )
        self.assertEqual(
            self.sql(
                target,
                "SELECT count(*) FROM pg_indexes WHERE schemaname='locations' AND indexdef LIKE '%USING gist%'",
            ),
            "1",
        )
        self.assertEqual(
            self.sql("dwms", "SELECT count(*) FROM locations.reports"), "1"
        )

    def test_existing_database_is_preserved(self) -> None:
        target = "dwms_restore_" + uuid.uuid4().hex[:12]
        self.sql("dwms", f'CREATE DATABASE "{target}"')
        self.sql(
            target,
            "CREATE TABLE sentinel (value integer); INSERT INTO sentinel VALUES (42)",
        )
        result = self.cli(
            "restore",
            "--container",
            self.container,
            "--archive",
            str(self.archive),
            "--target-database",
            target,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.sql(target, "SELECT value FROM sentinel"), "42")

    def test_corruption_creates_no_database(self) -> None:
        damaged = Path(self.tmp.name) / "damaged.dump"
        damaged.write_bytes(b"damaged")
        Path(str(damaged) + ".sha256").write_bytes(
            Path(str(self.archive) + ".sha256").read_bytes()
        )
        target = "dwms_restore_" + uuid.uuid4().hex[:12]
        result = self.cli(
            "restore",
            "--container",
            self.container,
            "--archive",
            str(damaged),
            "--target-database",
            target,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            self.sql(
                "dwms", f"SELECT count(*) FROM pg_database WHERE datname='{target}'"
            ),
            "0",
        )

    def test_application_database_is_rejected(self) -> None:
        result = self.cli(
            "restore",
            "--container",
            self.container,
            "--archive",
            str(self.archive),
            "--target-database",
            "dwms",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            self.sql("dwms", "SELECT count(*) FROM locations.reports"), "1"
        )

    def test_missing_source_database_publishes_nothing(self) -> None:
        output = Path(self.tmp.name) / "absent.dump"
        result = self.cli(
            "backup",
            "--container",
            self.container,
            "--database",
            "missing_source",
            "--output",
            str(output),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())
        self.assertFalse(Path(str(output) + ".sha256").exists())

    def test_existing_backup_is_preserved(self) -> None:
        original = self.archive.read_bytes()
        result = self.cli(
            "backup", "--container", self.container, "--output", str(self.archive)
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.archive.read_bytes(), original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
