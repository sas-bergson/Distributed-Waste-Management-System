"""Tests for the repository plaintext-Kubernetes-Secret guard."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
VALIDATOR_PATH = (
    REPOSITORY_ROOT
    / "Platform/infra/security/sealed-secrets/scripts/validate_secrets.py"
)
SPEC = importlib.util.spec_from_file_location("validate_secrets", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class PlaintextSecretValidationTests(unittest.TestCase):
    """Exercise accepted and rejected YAML document types without real secrets."""

    def test_sealed_secret_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "application-sealed-secret.yaml").write_text(
                "apiVersion: bitnami.com/v1alpha1\n"
                "kind: SealedSecret\n"
                "metadata:\n"
                "  name: application\n"
                "spec:\n"
                "  encryptedData: {}\n",
                encoding="utf-8",
            )

            self.assertEqual(VALIDATOR.find_plaintext_secrets(root), [])

    def test_plaintext_kubernetes_secret_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "application-secret.yaml").write_text(
                "apiVersion: v1\nkind: Secret\nmetadata:\n  name: application\n",
                encoding="utf-8",
            )

            violations = VALIDATOR.find_plaintext_secrets(root)

            self.assertEqual(len(violations), 1)
            self.assertIn("application-secret.yaml (document 1)", violations[0])

    def test_invalid_yaml_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "invalid.yaml").write_text("kind: [\n", encoding="utf-8")

            violations = VALIDATOR.find_plaintext_secrets(root)

            self.assertEqual(len(violations), 1)
            self.assertIn("invalid.yaml: unable to inspect YAML", violations[0])

    def test_unreadable_yaml_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "unreadable.yaml").write_text("kind: ConfigMap\n", encoding="utf-8")

            with patch.object(Path, "open", side_effect=PermissionError("denied")):
                violations = VALIDATOR.find_plaintext_secrets(root)

            self.assertEqual(len(violations), 1)
            self.assertIn("unreadable.yaml: unable to inspect YAML", violations[0])

    def test_cache_and_irrelevant_directories_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            excluded_directories = (
                ".git",
                "node_modules",
                ".venv",
                "venv",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                ".cache",
                ".tox",
                ".nox",
                "__pycache__",
            )
            for directory in excluded_directories:
                excluded = root / directory
                excluded.mkdir()
                (excluded / "secret.yaml").write_text(
                    "apiVersion: v1\nkind: Secret\n", encoding="utf-8"
                )

            self.assertEqual(VALIDATOR.find_plaintext_secrets(root), [])


if __name__ == "__main__":
    unittest.main()
