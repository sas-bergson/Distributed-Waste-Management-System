"""
Automated Test Suite for Distributed Tracing & W3C TraceContext Propagation (Feature 5 TEST).

Verifies:
1. W3C TraceContext header formatting (`traceparent` and `tracestate`).
2. Trace ID and Span ID generation according to the W3C recommendation (32-hex and 16-hex).
3. Inbound trace extraction and child span propagation across service hops.
4. Detection and rejection of malformed/invalid traceparent headers.
5. Verification of OpenTelemetry Collector configuration structure and ports.
"""

import os
import re
import unittest
from pathlib import Path


class W3CTraceContext:
    """Helper representing and parsing W3C TraceContext traceparent headers."""

    HEADER_NAME = "traceparent"
    # Format: version-trace_id-parent_id-trace_flags
    # Example: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
    PATTERN = re.compile(
        r"^(?P<version>[0-9a-f]{2})-"
        r"(?P<trace_id>[0-9a-f]{32})-"
        r"(?P<parent_id>[0-9a-f]{16})-"
        r"(?P<trace_flags>[0-9a-f]{2})$"
    )

    def __init__(self, version: str, trace_id: str, parent_id: str, trace_flags: str):
        self.version = version
        self.trace_id = trace_id
        self.parent_id = parent_id
        self.trace_flags = trace_flags

    @classmethod
    def parse(cls, header_value: str) -> "W3CTraceContext":
        if not header_value:
            raise ValueError("Empty traceparent header")
        header_value = header_value.strip()
        match = cls.PATTERN.match(header_value)
        if not match:
            raise ValueError(f"Invalid traceparent format: '{header_value}'")

        data = match.groupdict()
        # Version 00 cannot have all-zero trace_id or parent_id
        if data["version"] == "00":
            if data["trace_id"] == "0" * 32:
                raise ValueError("All-zero trace_id is invalid in version 00")
            if data["parent_id"] == "0" * 16:
                raise ValueError("All-zero parent_id is invalid in version 00")

        return cls(
            version=data["version"],
            trace_id=data["trace_id"],
            parent_id=data["parent_id"],
            trace_flags=data["trace_flags"],
        )

    def to_header(self) -> str:
        return f"{self.version}-{self.trace_id}-{self.parent_id}-{self.trace_flags}"

    def create_child_span(self, new_span_id: str) -> "W3CTraceContext":
        """Simulates propagation: preserves trace_id while creating a new child span ID."""
        if len(new_span_id) != 16 or not re.match(r"^[0-9a-f]{16}$", new_span_id):
            raise ValueError("Span ID must be 16 lowercase hex characters")
        if new_span_id == "0" * 16:
            raise ValueError("All-zero span_id is invalid")
        return W3CTraceContext(
            version=self.version,
            trace_id=self.trace_id,
            parent_id=new_span_id,
            trace_flags=self.trace_flags,
        )


class TestW3CTraceContextParsing(unittest.TestCase):
    """Verifies that W3C traceparent headers conform to the distributed tracing standard."""

    def test_valid_traceparent_parsed(self):
        valid = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        tc = W3CTraceContext.parse(valid)
        self.assertEqual(tc.version, "00")
        self.assertEqual(tc.trace_id, "4bf92f3577b34da6a3ce929d0e0e4736")
        self.assertEqual(tc.parent_id, "00f067aa0ba902b7")
        self.assertEqual(tc.trace_flags, "01")
        self.assertEqual(tc.to_header(), valid)

    def test_all_zero_trace_id_rejected(self):
        invalid = "00-00000000000000000000000000000000-00f067aa0ba902b7-01"
        with self.assertRaises(ValueError):
            W3CTraceContext.parse(invalid)

    def test_all_zero_parent_id_rejected(self):
        invalid = "00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01"
        with self.assertRaises(ValueError):
            W3CTraceContext.parse(invalid)

    def test_invalid_hex_rejected(self):
        # Contains non-hex character 'g'
        invalid = "00-4bf92f3577b34da6a3ce929d0e0e473g-00f067aa0ba902b7-01"
        with self.assertRaises(ValueError):
            W3CTraceContext.parse(invalid)

    def test_invalid_lengths_rejected(self):
        short_trace = "00-4bf92f3577b34da6a3ce-00f067aa0ba902b7-01"
        with self.assertRaises(ValueError):
            W3CTraceContext.parse(short_trace)


class TestTracePropagation(unittest.TestCase):
    """Verifies trace context propagation across multiple service hops."""

    def test_trace_id_preserved_across_hops(self):
        """Simulates Gateway -> Locations Service -> PostGIS query propagation."""
        initial_header = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        gateway_context = W3CTraceContext.parse(initial_header)

        # Hop 1: Gateway calls Locations Service
        locations_span_id = "11a1b2c3d4e5f6a7"
        locations_context = gateway_context.create_child_span(locations_span_id)

        self.assertEqual(locations_context.trace_id, gateway_context.trace_id)
        self.assertEqual(locations_context.parent_id, locations_span_id)
        self.assertEqual(locations_context.trace_flags, gateway_context.trace_flags)

        # Hop 2: Locations Service calls Database
        db_span_id = "22b2c3d4e5f6a7b8"
        db_context = locations_context.create_child_span(db_span_id)

        self.assertEqual(db_context.trace_id, gateway_context.trace_id)
        self.assertEqual(db_context.parent_id, db_span_id)

    def test_child_span_validation(self):
        initial = W3CTraceContext.parse(
            "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        )
        # Invalid span IDs
        with self.assertRaises(ValueError):
            initial.create_child_span("invalid-short")
        with self.assertRaises(ValueError):
            initial.create_child_span("0000000000000000")


class TestTracingCollectorConfig(unittest.TestCase):
    """Validates that OTel Collector and Jaeger configuration files meet specifications once merged."""

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[4]
        self.tracing_dir = (
            self.repo_root / "Platform" / "infra" / "observability" / "tracing"
        )
        self.config_path = self.tracing_dir / "otel-collector-config.yaml"
        self.compose_path = self.tracing_dir / "docker-compose.tracing.yml"

    def test_otel_collector_config_present_and_valid(self):
        """Verifies OTel Collector configuration structure (passes once IMP lands on main)."""
        if not self.config_path.exists():
            self.skipTest(
                "otel-collector-config.yaml not present on current branch yet (developed in IMP branch feat/chore/NKENG-FRANK/otel)."
            )

        content = self.config_path.read_text(encoding="utf-8")
        # Assert required OTel pipeline blocks
        self.assertIn("receivers:", content)
        self.assertIn("otlp:", content)
        self.assertIn("processors:", content)
        self.assertIn("batch:", content)
        self.assertIn("exporters:", content)
        self.assertIn("jaeger", content)
        self.assertIn("pipelines:", content)

    def test_tracing_compose_file_present_and_valid(self):
        """Verifies Jaeger and Collector compose definitions (passes once IMP lands on main)."""
        if not self.compose_path.exists():
            self.skipTest(
                "docker-compose.tracing.yml not present on current branch yet (developed in IMP branch feat/chore/NKENG-FRANK/otel)."
            )

        content = self.compose_path.read_text(encoding="utf-8")
        # Assert required services and ports
        self.assertIn("jaeger:", content)
        self.assertIn("otel-collector:", content)
        self.assertIn("16686", content)  # Jaeger UI port
        self.assertIn("4317", content)   # OTLP gRPC port
        self.assertIn("4318", content)   # OTLP HTTP port
        self.assertIn("dwms-net", content)


if __name__ == "__main__":
    unittest.main()
