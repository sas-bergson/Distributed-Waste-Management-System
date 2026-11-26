"""Unit checks for Feature 8 without Docker or cloud credentials."""

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import backup


class BackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.archive = Path(self.tmp.name) / "source.dump"
        self.archive.write_bytes(b"PGDMP-test-content")
        backup.checksum_path(self.archive).write_text(backup.digest(self.archive))

    def test_valid_checksum(self) -> None:
        backup.verify(self.archive)

    def test_corruption_is_rejected(self) -> None:
        self.archive.write_bytes(b"corrupted")
        with self.assertRaises(backup.BackupError):
            backup.verify(self.archive)

    def test_missing_checksum_is_rejected(self) -> None:
        backup.checksum_path(self.archive).unlink()
        with self.assertRaises(OSError):
            backup.verify(self.archive)

    def test_existing_archive_is_never_overwritten(self) -> None:
        with self.assertRaises(backup.BackupError):
            backup.publish(self.archive, self.archive)
        self.assertEqual(self.archive.read_bytes(), b"PGDMP-test-content")

    def test_publish_pair(self) -> None:
        output = self.archive.with_name("published.dump")
        backup.publish(self.archive, output)
        backup.verify(output)

    def test_empty_archive_is_rejected(self) -> None:
        self.archive.write_bytes(b"")
        backup.checksum_path(self.archive).write_text(backup.digest(self.archive))
        with self.assertRaises(backup.BackupError):
            backup.verify(self.archive)

    @patch.object(backup, "run")
    def test_download_checks_content_before_publication(self, run) -> None:
        def transfer(command):
            destination = Path(command[4])
            destination.write_bytes(b"invalid")

        run.side_effect = transfer
        output = self.archive.with_name("download.dump")
        with self.assertRaises(backup.BackupError):
            backup.download("s3://example/unique.dump", output)
        self.assertFalse(output.exists())
        self.assertFalse(backup.checksum_path(output).exists())

    @patch.object(backup, "run")
    def test_restore_rejects_application_database(self, run) -> None:
        with self.assertRaises(backup.BackupError):
            backup.restore("db", "dwms", self.archive, "dwms")
        run.assert_not_called()

    @patch.object(backup, "run")
    def test_restore_stops_when_database_exists(self, run) -> None:
        run.side_effect = [None, backup.BackupError("createdb failed")]
        with self.assertRaises(backup.BackupError):
            backup.restore("db", "dwms", self.archive, "dwms_restore_drill")
        self.assertEqual(run.call_count, 2)
        self.assertIn("createdb", run.call_args.args[0])

    @patch.object(backup, "run")
    def test_restore_uses_transaction_and_does_not_clean(self, run) -> None:
        backup.restore("db", "dwms", self.archive, "dwms_restore_drill")
        command = run.call_args.args[0]
        self.assertIn("--single-transaction", command)
        self.assertNotIn("--clean", command)

    @patch.object(backup, "run")
    def test_upload_encrypts_both_objects(self, run) -> None:
        backup.upload(self.archive, "s3://example/unique.dump", "key-arn")
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            self.assertIn("aws:kms", call.args[0])
            self.assertIn("--sse-kms-key-id", call.args[0])

    @patch.object(backup, "run", side_effect=backup.BackupError("dump failed"))
    def test_failed_dump_publishes_nothing(self, run) -> None:
        output = self.archive.with_name("failed.dump")
        with self.assertRaises(backup.BackupError):
            backup.backup("db", "dwms", "dwms", output)
        self.assertFalse(output.exists())
        self.assertFalse(backup.checksum_path(output).exists())

    def test_reject_option_injection(self) -> None:
        for value in ["--help", "a;drop", "dwms/password"]:
            with self.subTest(value=value), self.assertRaises(backup.BackupError):
                backup.identifier(value)
        with self.assertRaises(backup.BackupError):
            backup.docker("--privileged", "pg_dump")

    def test_reject_invalid_s3_location(self) -> None:
        for uri in ["https://example/file", "s3://bucket/", "s3://bucket/a?b=1"]:
            with self.subTest(uri=uri), self.assertRaises(backup.BackupError):
                backup.s3_uri(uri)

    @patch.object(backup.subprocess, "run")
    def test_command_failure_does_not_expose_stderr(self, run) -> None:
        run.side_effect = subprocess.CalledProcessError(1, ["docker"], stderr=b"secret")
        with self.assertRaises(backup.BackupError) as error:
            backup.run(["docker", "exec"])
        self.assertNotIn("secret", str(error.exception))


if __name__ == "__main__":
    unittest.main()
