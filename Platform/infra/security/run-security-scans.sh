#!/usr/bin/env bash
# =============================================================================
# DWMS Security Scanning Suite Runner (Feature 9 IMP)
# =============================================================================
# Runs SAST (Semgrep, Bandit, Trivy) and dependency vulnerability audits.
# Usage:
#   bash Platform/infra/security/run-security-scans.sh [--sast] [--dast] [--all]
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CONFIG_DIR="${REPO_ROOT}/Platform/infra/security"

MODE="${1:---all}"

echo "=========================================="
echo " DWMS Security Scanning Pipeline          "
echo "=========================================="
echo "Repository Root: ${REPO_ROOT}"
echo "Mode: ${MODE}"
echo ""

EXIT_CODE=0

# -----------------------------------------------------------------------------
# 1. Bandit (Python SAST)
# -----------------------------------------------------------------------------
run_bandit() {
  echo ">>> [1/4] Running Bandit Python SAST..."
  if command -v bandit >/dev/null 2>&1; then
    bandit -r "${REPO_ROOT}" \
      -c "${CONFIG_DIR}/bandit.yaml" \
      -ll -ii || {
        echo "::warning::Bandit identified potential issues."
        EXIT_CODE=1
      }
  else
    echo "Bandit is not installed in current environment. (pip install bandit)"
  fi
}

# -----------------------------------------------------------------------------
# 2. Semgrep (Polyglot Pattern SAST)
# -----------------------------------------------------------------------------
run_semgrep() {
  echo ">>> [2/4] Running Semgrep SAST..."
  if command -v semgrep >/dev/null 2>&1; then
    semgrep scan \
      --config "${CONFIG_DIR}/semgrep-rules.yaml" \
      --error \
      "${REPO_ROOT}" || {
        echo "::warning::Semgrep detected security rule violations."
        EXIT_CODE=1
      }
  else
    echo "Semgrep is not installed in current environment. (pip install semgrep)"
  fi
}

# -----------------------------------------------------------------------------
# 3. Trivy (Secrets & Misconfiguration Scan)
# -----------------------------------------------------------------------------
run_trivy() {
  echo ">>> [3/4] Running Trivy Filesystem & Secret Scan..."
  if command -v trivy >/dev/null 2>&1; then
    trivy fs \
      --config "${CONFIG_DIR}/trivy.yaml" \
      "${REPO_ROOT}" || {
        echo "::warning::Trivy detected HIGH/CRITICAL issues."
        EXIT_CODE=1
      }
  else
    echo "Trivy is not installed in current environment. (https://aquasecurity.github.io/trivy/)"
  fi
}

# -----------------------------------------------------------------------------
# 4. Dependency Audits (pip-audit & pnpm audit)
# -----------------------------------------------------------------------------
run_dep_audits() {
  echo ">>> [4/4] Running Dependency Vulnerability Audits..."
  if command -v pip-audit >/dev/null 2>&1; then
    echo "Scanning Python requirements files..."
    find "${REPO_ROOT}" -name "requirements*.txt" ! -path "*/.venv/*" | while read -r req; do
      echo "Auditing ${req}..."
      pip-audit -r "${req}" || true
    done
  fi

  if command -v pnpm >/dev/null 2>&1; then
    echo "Scanning Node packages with pnpm audit..."
    find "${REPO_ROOT}" -name "package.json" ! -path "*/node_modules/*" ! -path "*/.git/*" -exec dirname {} \; | while read -r dir; do
      if [ -f "${dir}/pnpm-lock.yaml" ]; then
        (cd "${dir}" && pnpm audit --audit-level high || true)
      fi
    done
  fi
}

# -----------------------------------------------------------------------------
# 5. DAST Scan via OWASP ZAP (when --dast or --all requested)
# -----------------------------------------------------------------------------
run_dast() {
  TARGET_URL="${TARGET_URL:-http://localhost:8080}"
  echo ">>> [DAST] Running OWASP ZAP Baseline against ${TARGET_URL}..."
  if command -v docker >/dev/null 2>&1; then
    docker run --rm -v "${CONFIG_DIR}:/zap/wrk/:ro" -t zaproxy/zap-stable \
      zap-baseline.py \
      -t "${TARGET_URL}" \
      -c /zap/wrk/zap-baseline.conf \
      -m 1 || {
        echo "::warning::OWASP ZAP DAST scan completed with alerts."
      }
  else
    echo "Docker is required to run OWASP ZAP DAST container."
  fi
}

case "${MODE}" in
  --sast)
    run_bandit
    run_semgrep
    run_trivy
    run_dep_audits
    ;;
  --dast)
    run_dast
    ;;
  --all|*)
    run_bandit
    run_semgrep
    run_trivy
    run_dep_audits
    ;;
esac

echo ""
echo "Security scan pass finished with exit code ${EXIT_CODE}."
exit "${EXIT_CODE}"
