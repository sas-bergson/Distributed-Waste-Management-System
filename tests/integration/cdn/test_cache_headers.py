"""Contract tests for DWMS CDN cache policy (Feature 7, TEST role).

Offline: parses infrastructure/cdn/_headers and nginx.conf and checks them
against infrastructure/cdn/cache-policy.json. Run from the repo root:

    python3 -m unittest discover -s tests/integration/cdn -v
"""
import json
import re
import unittest
from pathlib import Path

CDN = Path(__file__).resolve().parents[3] / "infrastructure" / "cdn"


def parse_headers_file(text):
    """Parse a Cloudflare/Netlify _headers file into {pattern: {header: value}}."""
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


class CachePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((CDN / "cache-policy.json").read_text())
        cls.headers = parse_headers_file((CDN / "_headers").read_text())
        cls.nginx = (CDN / "nginx.conf").read_text()
        cls.security = (CDN / "security-headers.conf").read_text()

    def cache_control_for(self, path):
        """Return every Cache-Control value that would apply to `path`
        (Cloudflare Pages merges all matching rules)."""
        return [
            h["Cache-Control"]
            for pattern, h in self.headers.items()
            if matches(pattern, path) and "Cache-Control" in h
        ]

    # --- policy -> _headers ---------------------------------------------
    def test_every_policy_path_is_declared_in_headers_file(self):
        for rule in self.policy["rules"]:
            for p in rule["paths"]:
                self.assertIn(p, self.headers, f"{p} ({rule['name']}) missing in _headers")
                self.assertEqual(
                    self.headers[p].get("Cache-Control"), rule["cache_control"],
                    f"wrong Cache-Control for {p}")

    def test_exactly_one_cache_control_applies_to_each_example(self):
        for rule in self.policy["rules"]:
            for ex in rule["examples"]:
                found = self.cache_control_for(ex)
                self.assertEqual(
                    found, [rule["cache_control"]],
                    f"{ex}: expected exactly one rule, got {found}")

    def test_catch_all_never_sets_cache_control(self):
        self.assertNotIn("Cache-Control", self.headers["/*"])

    # --- safety properties ----------------------------------------------
    def test_html_and_service_worker_are_never_immutable_or_long_lived(self):
        for path in ["/", "/index.html", "/sw.js", "/service-worker.js"]:
            (value,) = self.cache_control_for(path)
            self.assertNotIn("immutable", value)
            self.assertIn("max-age=0", value)
            self.assertIn("must-revalidate", value)

    def test_hashed_assets_are_immutable_for_one_year(self):
        (value,) = self.cache_control_for("/assets/index-3f2a9c1b.js")
        self.assertIn("immutable", value)
        self.assertIn("max-age=31536000", value)

    def test_only_hashed_assets_are_immutable(self):
        for rule in self.policy["rules"]:
            if rule["name"] != "hashed-assets":
                self.assertNotIn("immutable", rule["cache_control"], rule["name"])

    def test_no_rule_uses_private_or_no_store_on_public_static_files(self):
        for rule in self.policy["rules"]:
            self.assertTrue(rule["cache_control"].startswith("public"), rule["name"])

    def test_unlisted_paths_get_no_cache_control_so_cdn_default_applies(self):
        self.assertEqual(self.cache_control_for("/dashboard/map"), [])

    # --- security headers -----------------------------------------------
    def test_security_headers_present_in_catch_all(self):
        for name, value in self.policy["security_headers"].items():
            self.assertEqual(self.headers["/*"].get(name), value, name)

    def test_permissions_policy_allows_geolocation_for_reporter_gps(self):
        self.assertIn("geolocation=(self)", self.headers["/*"]["Permissions-Policy"])

    # --- policy -> nginx ------------------------------------------------
    def test_nginx_contains_every_cache_control_value(self):
        for rule in self.policy["rules"]:
            self.assertIn(f'add_header Cache-Control "{rule["cache_control"]}"',
                          self.nginx, f"{rule['name']} missing in nginx.conf")

    def test_nginx_includes_security_headers_in_every_location(self):
        locations = self.nginx.count("location ")
        self.assertEqual(self.nginx.count("security-headers.conf"), locations)

    def test_nginx_security_snippet_matches_policy(self):
        for name, value in self.policy["security_headers"].items():
            self.assertIn(f'add_header {name} "{value}" always;', self.security)

    # --- sanity ---------------------------------------------------------
    def test_no_two_rules_share_a_path(self):
        seen = {}
        for rule in self.policy["rules"]:
            for p in rule["paths"]:
                self.assertNotIn(p, seen, f"{p} in both {seen.get(p)} and {rule['name']}")
                seen[p] = rule["name"]


if __name__ == "__main__":
    unittest.main()
