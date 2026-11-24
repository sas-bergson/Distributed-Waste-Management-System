# CI Gates Test Suite (`tests/infra/ci-gates`)

This directory contains the automated test suite for **Feature 2: CI Pipeline Quality Gates** (role: **TEST**).

---

## Purpose

The tests in this directory verify that the quality gates enforced by the DWMS GitHub Actions CI pipeline function as designed:
1. **Secrets & Sensitive Files Gate:** Asserts that forbidden secret files (`.env`, `*.key`, `*.pem`) are caught and blocked, while `.env.example` is permitted.
2. **YAML Syntax Gate:** Asserts that YAML formatting errors (such as hard tab indentation and unbalanced braces/brackets) are detected.
3. **Docker Compose Gate:** Validates Compose structure integrity (requiring valid `services` dictionaries).
4. **Semantic PR Title Gate:** Validates Conventional Commit PR title formatting (`feat:`, `fix:`, `chore:`, `test:`, `docs:`, `adr:`, etc.).

---

## Running the Tests Locally

You can run the tests using standard Python (`unittest`) without any external dependencies:

```bash
python -m unittest Platform/tests/infra/ci-gates/test_ci_gates.py -v
```

Or using `pytest` if installed in your virtual environment:

```bash
pytest Platform/tests/infra/ci-gates/test_ci_gates.py -v
```
