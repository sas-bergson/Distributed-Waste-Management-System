#!/usr/bin/env python3
"""Live check of a deployed CDN / origin against cache-policy.json.

    python3 tests/integration/cdn/verify_live.py https://dwms-dashboard.pages.dev

Exit code 0 = every reachable example path returned the expected headers.
A 404 is reported as SKIP (the file may not exist in that build).
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

POLICY = Path(__file__).resolve().parents[3] / "infrastructure" / "cdn" / "cache-policy.json"


def fetch(url):
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "dwms-cdn-check"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.headers


def main(base):
    policy = json.loads(POLICY.read_text())
    base = base.rstrip("/")
    failures = 0
    for rule in policy["rules"]:
        for path in rule["examples"]:
            status, headers = fetch(base + path)
            if status == 404:
                print(f"SKIP  {path} (404)")
                continue
            got = headers.get("Cache-Control", "")
            if got.replace(" ", "") != rule["cache_control"].replace(" ", ""):
                failures += 1
                print(f"FAIL  {path}: expected '{rule['cache_control']}', got '{got}'")
            else:
                print(f"OK    {path}")
            for name, value in policy["security_headers"].items():
                if headers.get(name) != value:
                    failures += 1
                    print(f"FAIL  {path}: {name} = {headers.get(name)!r}")
    print("PASS" if not failures else f"{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
