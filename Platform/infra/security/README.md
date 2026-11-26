# Security Scanning Infrastructure (`infra/security/`)

This directory houses the Static Application Security Testing (SAST), Dynamic Application Security Testing (DAST), and dependency vulnerability auditing configurations for DWMS (Feature 9: Security scanning, role **IMP**).

---

## Tooling & Responsibilities

| Tool | Type | Configuration | Scope | Focus |
| :--- | :--- | :--- | :--- | :--- |
| **Bandit** | SAST | `bandit.yaml` | Python services (`locations`, `map`, `requests`) | SQL injection, unsafe deserialization, insecure subprocess, weak cryptography |
| **Semgrep** | SAST | `semgrep-rules.yaml` | Polyglot (Python, TypeScript) | Unparameterized raw PostGIS queries, hardcoded secrets, wildcard CORS |
| **Trivy** | SAST/SCA | `trivy.yaml` | Filesystem & containers | HIGH/CRITICAL CVEs, secret leak detection, container misconfiguration |
| **OWASP ZAP** | DAST | `zap-baseline.conf` | API Gateway (`http://localhost:8080`) | Missing security headers, XSS injection, CORS reflection, sensitive disclosures |
| **pip-audit / pnpm audit** | SCA | CLI | Python & Node manifests | Known CVEs in third-party package dependencies |

---

## Running Scans Locally

A runner script is provided in this directory:

### Run all SAST & Dependency Audits:
```bash
bash Platform/infra/security/run-security-scans.sh --sast
```

### Run OWASP ZAP Baseline DAST against running local Gateway:
```bash
# Ensure DWMS Gateway is running on port 8080 first
bash Platform/infra/security/run-security-scans.sh --dast
```

---

## Policy & Severity Thresholds

- **Blockers:** Any finding with severity `CRITICAL` or `HIGH` blocks the pipeline and must be remediated or formally documented in an ADR exception.
- **Allowed:** `.env.example` is explicitly allowed as an environment template; real `.env` files are rejected.
- **Exclusions:** Test suites (`tests/`) and temporary build directories are excluded from SAST false positives (e.g., Bandit `B101` for `assert`).
