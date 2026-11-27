# CDN caching in 10 minutes

A tutorial for DWMS contributors. By the end you will know what the cache rules for the dashboard and reporter apps are, why they exist, and how to check or change them safely. No CDN account is needed.

## 1. What problem are we solving?

When someone opens the dashboard, their browser downloads files (HTML, JavaScript, CSS, icons). A **cache** lets the browser or a CDN keep a copy so the next visit is faster. The risk is the opposite problem: after we deploy a new version, a stale copy keeps showing the old one.

The fix is to treat two kinds of files differently:

| Kind of file | Example | Rule |
|---|---|---|
| Name changes whenever the content changes (it contains a hash) | `/assets/index-3f2a9c1b.js` | Cache for a year. It can never be stale because a new version gets a new name. |
| Name never changes | `/index.html`, `/sw.js` | Ask the cache to re-check every time. |

Field agents use the reporter app on slow connections, so this matters: big files should download once, but a new release must reach them quickly.

## 2. What you need

- A clone of the repo with the Feature 7 files merged: `infrastructure/cdn/` and `tests/integration/cdn/`
- Python 3.8 or newer (check with `python3 --version`)
- Docker (only for the optional Step 5)

## 3. Step 1: Read the policy

Open `infrastructure/cdn/cache-policy.json`. Each rule has:

- `paths`: which URLs it covers (`*` matches anything after it)
- `cache_control`: the header value we send
- `why`: the reason, in one sentence
- `examples`: sample URLs the tests use

This file is the **single source of truth**. The CDN file (`_headers`) and the nginx file (`nginx.conf`) are copies of it in other formats.

## 4. Step 2: Run the tests

From the repo root:

```bash
python3 -m unittest discover -s tests/integration/cdn -v
```

You should see a list of tests and, at the end, `OK`. These tests read the three config files and check that they agree with each other and follow the safety rules (for example: only year-long files may be marked `immutable`).

## 5. Step 3: Break it on purpose

Seeing a test fail is the best way to trust it.

1. Make a backup and add a wrong rule at the end of `_headers`:
   ```bash
   cp infrastructure/cdn/_headers /tmp/_headers.bak
   printf '\n/assets/*\n  Cache-Control: public, max-age=60\n' >> infrastructure/cdn/_headers
   ```
2. Run the tests again. At the end you should see `FAILED`, with messages about `/assets/*` getting the wrong or a duplicated rule.
3. Put the file back:
   ```bash
   cp /tmp/_headers.bak infrastructure/cdn/_headers
   python3 -m unittest discover -s tests/integration/cdn
   ```
   It should say `OK` again.

Why it failed: some CDNs (Cloudflare Pages) **merge** the headers of every rule that matches a URL. Two rules for the same path would send two conflicting values, so the tests forbid overlaps.

## 6. Step 4: Check a real website

If the apps are deployed somewhere, run the live checker against the address:

```bash
python3 tests/integration/cdn/verify_live.py https://YOUR-SITE-ADDRESS
```

Each line shows one of three results:

| Output | Meaning |
|---|---|
| `OK    /assets/...` | The server sent exactly the expected headers |
| `SKIP  /locales/fr.json (404)` | That example file is not in this build; not an error |
| `FAIL  /: expected '...', got '...'` | The server sent something different; fix the CDN setup |

The last line is `PASS`, or the number of failures.

## 7. Step 5 (optional): Try it with nginx

This needs Docker and a built frontend folder (for example `frontend/dashboard/dist`).

```bash
docker run --rm -p 8080:80 \
  -v "$PWD/frontend/dashboard/dist:/usr/share/nginx/html:ro" \
  -v "$PWD/infrastructure/cdn/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$PWD/infrastructure/cdn/security-headers.conf:/etc/nginx/snippets/security-headers.conf:ro" \
  nginx:stable
```

In a second terminal:

```bash
curl -sI http://localhost:8080/ | grep -i cache-control
python3 tests/integration/cdn/verify_live.py http://localhost:8080
```

The first command should print `cache-control: public, max-age=0, must-revalidate`.

## 8. Change a rule

1. Edit `cache-policy.json`: add or change a rule with `paths`, `cache_control`, `why` and `examples`.
2. Make the same change in `_headers` and in `nginx.conf`.
3. Run the tests from Step 2. They fail if the three files disagree.
4. If you changed what happens on deploy (HTML, service worker, hashed files), tell the team in your PR.

## 9. Troubleshooting

| What you see | Likely cause |
|---|---|
| Users still see the old app after a deploy | `/` or `/sw.js` has a long `max-age` |
| `Cache-Control` shows two values joined by a comma | Two `_headers` rules match the same URL |
| A big file downloads again on every visit | It is not under `/assets/`, or its name has no hash |
| Camera or GPS blocked in the reporter app | `Permissions-Policy` must keep `geolocation=(self)` and `camera=(self)` |
| Tests say the Feature 7 files are missing | The IMP branch is not merged into your branch yet |

## 10. What we did not decide

- **Content-Security-Policy** is not set yet, because it depends on which map tile servers the frontends use.
- **Which CDN** hosts production is open. `_headers` works on Cloudflare Pages and Netlify; `nginx.conf` covers local and self-hosted setups.
- **API responses** are out of scope here. The gateway sets its own cache headers.

## 11. Reference

| File | Purpose |
|---|---|
| `infrastructure/cdn/cache-policy.json` | The policy (source of truth) |
| `infrastructure/cdn/_headers` | Headers for Cloudflare Pages / Netlify |
| `infrastructure/cdn/nginx.conf`, `security-headers.conf` | The same policy for nginx |
| `tests/integration/cdn/` | Tests and the live checker |
