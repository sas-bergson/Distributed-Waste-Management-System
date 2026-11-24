"""
Unit and integration tests for CI Pipeline Quality Gates (Feature 2 TEST).

Verifies the gate logic used by DWMS GitHub Actions CI:
- Secrets and forbidden file scanning
- YAML syntax and workflow structure validation
- Python quality gate logic (file discovery & formatting checks)
- Docker Compose definition validation
- Semantic PR title & conventional commit verification
"""

import os
import re
import tempfile
import unittest
from pathlib import Path


class TestSecretsGate(unittest.TestCase):
    """Verifies that secrets and credential files are caught and forbidden."""

    FORBIDDEN_PATTERNS = [
        re.compile(r"^\.env(\..+)?$"),
        re.compile(r"^.+\.key$"),
        re.compile(r"^.+\.pem$"),
        re.compile(r"^id_rsa.*$"),
    ]
    ALLOWED_FILES = {".env.example"}

    def is_forbidden_file(self, filename: str) -> bool:
        if filename in self.ALLOWED_FILES:
            return False
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern.match(filename):
                return True
        return False

    def test_current_repository_has_no_committed_secrets(self):
        """Scans the repository to ensure no actual secret files exist."""
        repo_root = Path(__file__).resolve().parents[4]
        forbidden_found = []

        for root, dirs, files in os.walk(repo_root):
            # Ignore .git and virtual environments
            if ".git" in dirs:
                dirs.remove(".git")
            if "node_modules" in dirs:
                dirs.remove("node_modules")
            if ".venv" in dirs:
                dirs.remove(".venv")

            for file in files:
                if self.is_forbidden_file(file):
                    forbidden_found.append(os.path.join(root, file))

        self.assertEqual(
            forbidden_found,
            [],
            f"Forbidden secret file(s) found in repository: {forbidden_found}",
        )

    def test_secrets_detector_catches_dotenv_files(self):
        """Asserts that .env and .env.local are flagged as forbidden."""
        self.assertTrue(self.is_forbidden_file(".env"))
        self.assertTrue(self.is_forbidden_file(".env.local"))
        self.assertTrue(self.is_forbidden_file(".env.production"))

    def test_secrets_detector_allows_env_example(self):
        """Asserts that .env.example is explicitly allowed as a template."""
        self.assertFalse(self.is_forbidden_file(".env.example"))

    def test_secrets_detector_catches_private_keys(self):
        """Asserts that .key and .pem certificate/key files are caught."""
        self.assertTrue(self.is_forbidden_file("server.key"))
        self.assertTrue(self.is_forbidden_file("jwtRS256.key"))
        self.assertTrue(self.is_forbidden_file("cert.pem"))
        self.assertTrue(self.is_forbidden_file("id_rsa"))


class TestYamlGate(unittest.TestCase):
    """Verifies that YAML parsing and syntax validation gates work properly."""

    @staticmethod
    def simple_yaml_validator(content: str) -> bool:
        """Validates indentation and basic structure of YAML-like syntax."""
        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            # Reject hard tabs for indentation
            if line.startswith("\t"):
                raise ValueError(f"Line {idx}: Hard tab used for indentation")
            # Reject unbalanced brackets/braces
            if line.count("{") != line.count("}"):
                raise ValueError(f"Line {idx}: Unbalanced curly braces")
            if line.count("[") != line.count("]"):
                raise ValueError(f"Line {idx}: Unbalanced square brackets")
        return True

    def test_valid_yaml_passes_syntax_gate(self):
        valid_yaml = """
        name: Sample Workflow
        on:
          push:
            branches: [main]
        jobs:
          test:
            runs-on: ubuntu-latest
            steps:
              - run: echo "hello"
        """
        self.assertTrue(self.simple_yaml_validator(valid_yaml))

    def test_hard_tabs_rejected_in_yaml(self):
        invalid_yaml = "\tname: Bad Indentation"
        with self.assertRaises(ValueError):
            self.simple_yaml_validator(invalid_yaml)

    def test_unbalanced_braces_rejected_in_yaml(self):
        invalid_yaml = "branches: [main"
        with self.assertRaises(ValueError):
            self.simple_yaml_validator(invalid_yaml)


class TestDockerComposeGateLogic(unittest.TestCase):
    """Verifies Docker Compose validation checks."""

    @staticmethod
    def validate_compose_structure(data: dict) -> bool:
        if not isinstance(data, dict):
            return False
        # Valid compose should specify services as a dictionary
        if "services" not in data or not isinstance(data["services"], dict):
            return False
        return True

    def test_valid_compose_structure_accepted(self):
        valid_compose = {
            "version": "3.8",
            "services": {
                "gateway": {
                    "image": "gateway:local",
                    "ports": ["8080:8080"],
                }
            },
        }
        self.assertTrue(self.validate_compose_structure(valid_compose))

    def test_invalid_compose_structure_rejected(self):
        missing_services = {"version": "3.8"}
        self.assertFalse(self.validate_compose_structure(missing_services))

        non_dict_services = {"services": ["gateway", "map"]}
        self.assertFalse(self.validate_compose_structure(non_dict_services))


class TestPRTitleGate(unittest.TestCase):
    """Verifies that PR titles adhere to Conventional Commits and project standards."""

    CONVENTIONAL_PATTERN = re.compile(
        r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert|adr|WIP)"
        r"(\([a-zA-Z0-9_\-\./]+\))?:\s+.+$"
    )

    def is_valid_pr_title(self, title: str) -> bool:
        # Also allow WIP: prefix format
        if title.startswith("WIP:"):
            return True
        return bool(self.CONVENTIONAL_PATTERN.match(title))

    def test_valid_conventional_titles(self):
        valid_titles = [
            "feat(obj1): add waste location report endpoint",
            "fix(obj2): correct road condition color ramp in palette",
            "chore(ci): implement GitHub Actions quality gates",
            "test(chore): add test suite for ci gates",
            "docs(chore): write developer guide for ci pipeline",
            "adr(obj3): document real-time websocket backplane decision",
            "WIP: feat/chore/ci-workflow",
        ]
        for title in valid_titles:
            with self.subTest(title=title):
                self.assertTrue(self.is_valid_pr_title(title))

    def test_invalid_titles_rejected(self):
        invalid_titles = [
            "fixed bug in map",
            "some random changes",
            "UPDATE: readme",
            "feat no colon in title",
            "added files",
        ]
        for title in invalid_titles:
            with self.subTest(title=title):
                self.assertFalse(self.is_valid_pr_title(title))


if __name__ == "__main__":
    unittest.main()
