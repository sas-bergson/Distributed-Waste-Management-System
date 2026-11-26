"""Edge-case tests for the DWMS CDN cache policy (Feature 7, TEST role).

Self-contained on purpose: this file must not import from the IMP unit tests,
because the TEST branch is created from upstream/main, where they may not exist.

These tests need the Feature 7 IMP files (infrastructure/cdn/). Until the IMP
branch (feat/chore/cdn-config) is merged they FAIL with a clear message; that
is the expected "first failing test" for the TEST role.

Run from the repo root:
    python3 -m unittest discover -s tests/integration/cdn -v
"""
import json
import re
import unittest
from pathlib import Path

CDN = Path(__file__).resolve().parents[3] / "infrastructure" / "cdn"
NEEDED = ["cache-policy.json", "_headers", "nginx.conf", "security-headers.conf"]

ONE_YEAR = 31536000
ONE_DAY = 86400


def parse_headers_file(text):
    rules, current = {}, None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw[0].isspace():
            current = raw.strip()
            rules.setdefault(current, {})
        else:
            name, _, value = raw.strip().partition(":")
            rules[current][name.strip()] = value.strip()
    return rules


def matches(pattern, path):
    regex = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
    return re.match(regex, path) is not None


def merged_headers(rules, path):
    """Simulate Cloudflare Pages: every matching rule contributes; a header set
    by several rules gets its values joined with a comma."""
    merged = {}
    for pattern, hdrs in rules.items():
        if matches(pattern, path):
            for name, value in hdrs.items():
                merged[name] = f"{merged[name]}, {value}" if name in merged else value
    return merged


def max_age(value):
    m = re.search(r"max-age=(\d+)", value)
    return int(m.group(1)) if m else None


class EdgeCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        missing = [f for f in NEEDED if not (CDN / f).exists()]
        if missing:
            raise AssertionError(
                f"Missing {missing} in {CDN}. Feature 7 IMP "
                "(branch feat/chore/cdn-config) must be merged before these tests can pass.")
        cls.policy = json.loads((CDN / "cache-policy.json").read_text())
        cls.rules = parse_headers_file((CDN / "_headers").read_text())
        cls.headers_text = (CDN / "_headers").read_text()
        cls.nginx = (CDN / "nginx.conf").read_text()

    # ---- policy file shape --------------------------------------------------
    def test_policy_rules_have_required_fields(self):
        for rule in self.policy["rules"]:
            for key in ("name", "paths", "cache_control", "why", "examples"):
                self.assertIn(key, rule, f"{rule.get('name')} lacks {key}")
            self.assertTrue(rule["paths"] and rule["examples"], rule["name"])

    def test_every_example_matches_one_of_its_own_rule_paths(self):
        for rule in self.policy["rules"]:
            for ex in rule["examples"]:
                self.assertTrue(any(matches(p, ex) for p in rule["paths"]),
                                f"{ex} does not match {rule['paths']}")

    # ---- _headers file syntax ----------------------------------------------
    def test_no_duplicate_patterns_in_headers_file(self):
        patterns = [l.strip() for l in self.headers_text.splitlines()
                    if l and not l[0].isspace() and not l.startswith("#")]
        self.assertEqual(len(patterns), len(set(patterns)))

    def test_every_header_line_is_name_colon_value(self):
        for l in self.headers_text.splitlines():
            if l and l[0].isspace() and l.strip():
                self.assertRegex(l.strip(), r"^[A-Za-z-]+: .+$", l)

    def test_every_path_pattern_starts_with_slash(self):
        for p in self.rules:
            self.assertTrue(p.startswith("/"), p)

    # ---- directive sanity ---------------------------------------------------
    def test_no_private_or_no_store_on_static_files(self):
        for r in self.policy["rules"]:
            for bad in ("private", "no-store"):
                self.assertNotIn(bad, r["cache_control"], r["name"])

    def test_immutable_only_with_at_least_one_year(self):
        for r in self.policy["rules"]:
            if "immutable" in r["cache_control"]:
                self.assertGreaterEqual(max_age(r["cache_control"]), ONE_YEAR, r["name"])

    def test_must_revalidate_rules_use_max_age_zero(self):
        for r in self.policy["rules"]:
            if "must-revalidate" in r["cache_control"]:
                self.assertEqual(max_age(r["cache_control"]), 0, r["name"])

    def test_unhashed_files_never_cached_longer_than_a_year(self):
        for r in self.policy["rules"]:
            if "immutable" not in r["cache_control"]:
                self.assertLess(max_age(r["cache_control"]), ONE_YEAR, r["name"])

    def test_editable_content_is_cached_at_most_one_day(self):
        for r in self.policy["rules"]:
            if r["name"] in ("manifest", "locales"):
                self.assertLessEqual(max_age(r["cache_control"]), ONE_DAY, r["name"])

    # ---- path matching edge cases ------------------------------------------
    def test_nested_asset_paths_are_covered(self):
        self.assertEqual(
            merged_headers(self.rules, "/assets/chunks/vendor-9f8e7d.js")["Cache-Control"],
            "public, max-age=31536000, immutable")

    def test_assets_without_trailing_slash_gets_no_long_cache(self):
        self.assertNotIn("Cache-Control", merged_headers(self.rules, "/assets"))

    def test_paths_are_case_sensitive(self):
        self.assertNotIn("Cache-Control", merged_headers(self.rules, "/Assets/app.js"))

    def test_spa_route_gets_no_cache_control_from_headers_file(self):
        self.assertNotIn("Cache-Control", merged_headers(self.rules, "/dashboard/map"))

    def test_hashed_filename_outside_assets_is_not_immutable(self):
        value = merged_headers(self.rules, "/static/app-3f2a9c1b.js").get("Cache-Control", "")
        self.assertNotIn("immutable", value)

    # ---- Cloudflare merge simulation ---------------------------------------
    def test_merged_cache_control_is_a_single_value_for_every_example(self):
        for r in self.policy["rules"]:
            for ex in r["examples"]:
                got = merged_headers(self.rules, ex)["Cache-Control"]
                self.assertEqual(got, r["cache_control"], f"{ex}: merged to '{got}'")

    def test_security_headers_survive_merge_on_every_example(self):
        for r in self.policy["rules"]:
            for ex in r["examples"]:
                merged = merged_headers(self.rules, ex)
                for name, value in self.policy["security_headers"].items():
                    self.assertEqual(merged.get(name), value, f"{ex}: {name}")

    # ---- nginx edge cases ---------------------------------------------------
    def test_nginx_has_a_location_for_every_policy_group(self):
        for needle in ("location = /", "location = /index.html", "sw|service-worker",
                       "manifest.webmanifest", "location /assets/", "icons|fonts",
                       "location /locales/"):
            self.assertIn(needle, self.nginx, needle)

    def test_nginx_spa_fallback_serves_index_and_revalidates(self):
        block = self.nginx.split("# SPA fallback", 1)[1]
        self.assertIn("try_files $uri /index.html", block)
        self.assertIn("must-revalidate", block)

    def test_nginx_uses_always_so_errors_also_carry_headers(self):
        for line in self.nginx.splitlines():
            if "add_header" in line:
                self.assertIn("always", line, line)


if __name__ == "__main__":
    unittest.main()
