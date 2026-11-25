# Distributed Tracing & Trace Propagation Test Suite (`tests/infra/trace-propagation`)

This directory contains the automated test suite for **Feature 5: Distributed Tracing** (role: **TEST**).

---

## Purpose

The tests verify:
1. **W3C TraceContext Specification Compliance:** Validates proper syntax parsing and serialization of the `traceparent` header (`version-trace_id-parent_id-trace_flags`).
2. **Context Propagation Across Hops:** Verifies that a single `trace_id` is preserved through multi-hop requests (e.g. Gateway $\rightarrow$ Locations $\rightarrow$ PostGIS) while child span IDs are correctly assigned.
3. **Negative & Edge-Case Validation:** Ensures all-zero trace/span IDs, non-hex strings, and malformed header lengths are caught and rejected.
4. **Configuration Assertions:** Validates that `otel-collector-config.yaml` and `docker-compose.tracing.yml` define the necessary receivers (`4317`, `4318`), batch processors, and Jaeger exporters on `dwms-net`.

---

## Running the Tests Locally

Using Python's standard library `unittest` (no external dependencies required):

```bash
python -m unittest Platform/tests/infra/trace-propagation/test_trace_propagation.py -v
```

Or using `pytest`:

```bash
pytest Platform/tests/infra/trace-propagation/test_trace_propagation.py -v
```
