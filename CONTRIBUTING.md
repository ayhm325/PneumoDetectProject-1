CONTRIBUTING — Playwright CI & Local Test Guide

This document explains how to run the Playwright UI smoke tests locally and how the CI workflow runs them on GitHub Actions.

1) Quick overview
- Tests location: `tests/ui.spec.js`
- Playwright config: `playwright.config.js`
- CI workflow: `.github/workflows/playwright.yml`
- Artifacts (on failure): `test-results/screenshots/`, `playwright-report/`, `server.log`

2) Preconditions (local)
- Install Python (3.8+ recommended) and create a virtual environment.
- Install Node.js (LTS recommended).
- Ensure the Flask app runs locally at `http://127.0.0.1:5000` or set `TEST_BASE_URL`.

3) Install dependencies
PowerShell (from repo root):
```powershell
# python deps (optional but recommended)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# node deps
npm install
# install Playwright browsers
npx playwright install --with-deps
```

4) Starting the app (avoid MKL/NumExpr runtime aborts)
Set the environment variables in the current PowerShell session before starting the server:
```powershell
$env:MKL_NUM_THREADS = '1'
$env:NUMEXPR_MAX_THREADS = '4'
$env:OMP_NUM_THREADS = '1'

# start the app (in the active venv)
python run.py
```

5) Run Playwright tests locally
```powershell
# default: visits http://127.0.0.1:5000
npm test

# or if your server binds to a different host/port
$env:TEST_BASE_URL = 'http://0.0.0.0:5000'
npm test
```

Environment flag for strict lazy-loading checks

You can toggle strict verification that image requests occur after scroll by setting the `TEST_STRICT_LAZY` environment variable in your PowerShell session. This is useful to avoid flaky failures in headless/CI environments while allowing strict enforcement when desired.

Examples:
```powershell
# run in strict mode (assert request happened after scroll)
$env:TEST_STRICT_LAZY = 'true'
npm test

# run in non-strict (default) mode
$env:TEST_STRICT_LAZY = 'false'
npm test
```

6) What the tests verify
- Presence of a JSON-LD `<script type="application/ld+json">` block.
- Presence of `#print-btn` in the page header.
- Progressive images: `img.progressive-img` and `img[data-src]` are scrolled into view and the `data-src` is swapped to `src` (test includes a fallback manual swap if IntersectionObserver doesn't run in the test environment).
 - Caching / headers: image responses are inspected for at least one caching indicator (`ETag`, `Last-Modified`, or `Cache-Control`). If an `ETag` is present the tests issue a conditional GET (`If-None-Match`) and prefer a `304 Not Modified` response from the server (the test also accepts `200` but logs a warning if `304` isn't returned).

7) Artifacts & debugging
- Screenshots on failure: `test-results/screenshots/` (the test writes a PNG per failing test).
- Playwright HTML report / videos / traces: `playwright-report/` (Playwright default) and other `test-results/` artifacts.
- Server logs: `server.log` produced by the CI workflow and in local runs you can redirect `python run.py > server.log 2>&1` to capture logs.

8) Reproducing and debugging failures
- If a test fails, open the screenshot in `test-results/screenshots/` to see the page state at failure.
- Open `playwright-report/index.html` to see the full test report with trace/video (if captured).
- Check `server.log` for backend stack traces or startup errors (useful for 500s or startup failures).

9) CI notes
- The GitHub Actions workflow `.github/workflows/playwright.yml`:
  - Boots the app (with MKL/NumExpr env vars set) in the job runner.
  - Runs `npx playwright test` and uploads `playwright-report/`, `test-results/screenshots`, and `server.log` as artifacts.

10) Advanced: capturing network requests
- If you need to assert that the real images were fetched (not just placeholder), we can enhance tests to intercept network requests and assert `response.ok()` for image URLs. Open an issue or request and we'll add `page.on('request')`/`page.on('response')` checks to the tests.
 - The current test suite already captures image `response` headers and timestamps. Use the local `curl -I` check to validate server headers manually if the test flags a caching failure.
 - The current test suite already captures image `response` headers and timestamps. Use the local `curl -I` check to validate server headers manually if the test flags a caching failure.

Environment flag for caching strictness

- By default tests warn when caching headers are missing to remain tolerant across environments. To make caching header presence mandatory (for CI enforcement), set `TEST_CACHE_STRICT=true` in your environment before running `npm test`. When enabled, missing `ETag`/`Last-Modified`/`Cache-Control` headers will cause test failures.

Example (PowerShell):
```powershell
$env:TEST_CACHE_STRICT = 'true'
npm test
```

11) Contact
- If you encounter CI failures you can't reproduce locally, save artifacts and attach them to the issue/PR. Provide: failing test name, screenshot file, `playwright-report/`, and `server.log`.

Thank you for keeping tests green — small UI changes may affect lazy-loading and print styles. This guide helps the team reproduce and debug quickly.
