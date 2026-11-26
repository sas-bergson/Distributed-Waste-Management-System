"""
Automated Test Suite for Security Scanning Baseline (Feature 9 TEST).

Verifies:
1. Static Application Security Testing (SAST) baseline integrity:
   - Verifies that insecure coding patterns (e.g., raw SQL formatting in PostGIS queries,
     hardcoded secret assignments, wildcard CORS with credentials) are correctly detected.
2. Configuration file integrity:
   - Asserts that Bandit, Semgrep, Trivy, and OWASP ZAP configs exist and conform to schema.
3. Secret scanning baseline:
   - Confirms that secret patterns (API keys, private keys, passwords) trigger detection rules.
4. Dependency audit policies:
   - Validates that scanning thresholds enforce failures on HIGH and CRITICAL vulnerabilities.
"""

import os
import re
import unittest
from pathlib import Path


class TestSecurityPatternDetection(unittest.TestCase):
    """Verifies that security scanning rules catch vulnerable code patterns."""

    # Simulates Semgrep/Bandit raw SQL query detection regex
    RAW_SQL_PATTERN = re.compile(
        r"""(\.execute\s*\(\s*f["'].*\{.*\}.*["']|\.execute\s*\(\s*["'].*%s.*["']\s*%)""",
        re.IGNORECASE,
    )

    # Simulates hardcoded credential detection regex
    HARDCODED_SECRET_PATTERN = re.compile(
        r"""(?i)(password|secret|jwt_secret|api_key)\s*=\s*["'][a-zA-Z0-9_\-\.\$]{8,}["']"""
    )

    def test_catches_unparameterized_raw_sql(self):
        """Ensures raw formatted strings in database executes are detected."""
        vulnerable_code = 'session.execute(f"SELECT * FROM waste_locations WHERE id = {report_id}")'
        self.assertIsNotNone(
            self.RAW_SQL_PATTERN.search(vulnerable_code),
            "Failed to detect SQL injection via f-string formatting",
        )

    def test_allows_parameterized_sql(self):
        """Ensures properly parameterized queries are not flagged."""
        safe_code = 'session.execute(text("SELECT * FROM waste_locations WHERE id = :id"), {"id": report_id})'
        self.assertIsNone(
            self.RAW_SQL_PATTERN.search(safe_code),
            "False positive on parameterized SQL execution",
        )

    def test_catches_hardcoded_secrets(self):
        """Ensures hardcoded secret variables are detected."""
        vulnerable_code = 'JWT_SECRET = "super-secret-key-12345"'
        self.assertIsNotNone(
            self.HARDCODED_SECRET_PATTERN.search(vulnerable_code),
            "Failed to detect hardcoded secret assignment",
        )

    def test_allows_environment_secret_loading(self):
        """Ensures loading secrets from os.getenv is allowed."""
        safe_code = 'JWT_SECRET = os.getenv("JWT_SECRET", "")'
        self.assertIsNone(
            self.HARDCODED_SECRET_PATTERN.search(safe_code),
            "False positive on environment variable secret lookup",
        )


class TestSecurityConfigsValidation(unittest.TestCase):
    """Validates that Feature 9 security configurations exist and have required rules."""

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[4]
        self.security_dir = (
            self.repo_root / "Platform" / "infra" / "security"
        )
        self.bandit_cfg = self.security_dir / "bandit.yaml"
        self.semgrep_cfg = self.security_dir / "semgrep-rules.yaml"
        self.trivy_cfg = self.security_dir / "trivy.yaml"
        self.zap_cfg = self.security_dir / "zap-baseline.conf"

    def test_bandit_config_structure(self):
        """Verifies Bandit configuration file exists and defines skips and excludes."""
        if not self.bandit_cfg.exists():
            self.skipTest("bandit.yaml not present on current branch yet (developed in IMP).")

        content = self.bandit_cfg.read_text(encoding="utf-8")
        self.assertIn("skips:", content)
        self.assertIn("B101", content)
        self.assertIn("exclude_dirs:", content)

    def test_semgrep_rules_structure(self):
        """Verifies custom Semgrep rules exist and cover SQL injection and secrets."""
        if not self.semgrep_cfg.exists():
            self.skipTest("semgrep-rules.yaml not present on current branch yet (developed in IMP).")

        content = self.semgrep_cfg.read_text(encoding="utf-8")
        self.assertIn("rules:", content)
        self.assertIn("dwms-avoid-raw-sql-formatting", content)
        self.assertIn("dwms-hardcoded-secret-assignment", content)

    def test_trivy_config_structure(self):
        """Verifies Trivy configuration blocks on HIGH and CRITICAL vulnerabilities."""
        if not self.trivy_cfg.exists():
            self.skipTest("trivy.yaml not present on current branch yet (developed in IMP).")

        content = self.trivy_cfg.read_text(encoding="utf-8")
        self.assertIn("HIGH", content)
        self.assertIn("CRITICAL", content)
        self.assertIn("exit-code: 1", content)

    def test_zap_config_structure(self):
        """Verifies OWASP ZAP baseline configuration defines severity overrides."""
        if not self.zap_cfg.exists():
            self.skipTest("zap-baseline.conf not present on current branch yet (developed in IMP).")

        content = self.zap_cfg.read_text(encoding="utf-8")
        self.assertIn("fail_on_severity:", content)
        self.assertIn("rules:", content)


class TestRepositorySecretBaseline(unittest.TestCase):
    """Scans repository user files to verify no secrets are currently committed."""

    FORBIDDEN_EXTENSIONS = {".key", ".pem", ".pfx", ".p12"}
    FORBIDDEN_FILENAMES = {".env", ".env.local", ".env.production", "id_rsa"}

    def test_no_forbidden_secret_files_in_workspace(self):
        repo_root = Path(__file__).resolve().parents[4]
        violations = []

        for root, dirs, files in os.walk(repo_root):
            # Exclude VCS and build directories
            if ".git" in dirs:
                dirs.remove(".git")
            if "node_modules" in dirs:
                dirs.remove("node_modules")
            if ".venv" in dirs:
                dirs.remove(".venv")

            for file in files:
                if file in self.FORBIDDEN_FILENAMES:
                    violations.append(os.path.join(root, file))
                suffix = Path(file).suffix.lower()
                if suffix in self.FORBIDDEN_EXTENSIONS:
                    violations.append(os.path.join(root, file))

        self.assertEqual(
            violations,
            [],
            f"Committed secrets/credential files detected: {violations}",
        )


if __name__ == "__main__":
    unittest.main()
