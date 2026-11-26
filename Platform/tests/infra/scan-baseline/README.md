# Security Scanning Baseline Test Suite (`tests/infra/scan-baseline/`)

This directory houses the automated test suite for **Feature 9: Security scanning (SAST/DAST)** (role: **TEST**).

---

## Purpose

The tests in this suite verify that DWMS security scanning baselines and pattern detectors function reliably:
1. **SAST Pattern Assertions:** Verifies that raw formatted SQL queries (potential SQL injection in PostGIS spatial operations) and hardcoded secret assignments are caught, while parameterized queries and `os.getenv` lookups pass.
2. **Scanner Configuration Verification:** Asserts that configuration files for Bandit (`bandit.yaml`), Semgrep (`semgrep-rules.yaml`), Trivy (`trivy.yaml`), and OWASP ZAP (`zap-baseline.conf`) exist, parse properly, and enforce severity gating on `HIGH` and `CRITICAL`.
3. **Repository Secret Baseline:** Scans the active workspace to ensure no sensitive files (`.env`, `*.key`, `*.pem`, `id_rsa`) are committed.

---

## Running the Tests Locally

Using Python's standard library `unittest` (zero external dependencies required):

```bash
python -m unittest Platform/tests/infra/scan-baseline/test_scan_baseline.py -v
```

Or using `pytest`:

```bash
pytest Platform/tests/infra/scan-baseline/test_scan_baseline.py -v
```
