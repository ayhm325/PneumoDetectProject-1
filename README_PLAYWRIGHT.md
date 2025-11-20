Playwright smoke tests for PneumoDetectProject

Overview

This repository includes a small Playwright smoke-test that verifies key UI features:

- Progressive images (images using `data-src` and `class="progressive-img"`) are swapped into `src` when they enter the viewport (or via a fallback manual swap in the test).
- The `#print-btn` exists on pages.
- A JSON-LD block (`<script type="application/ld+json">`) is present.

Preparation & installation (Windows / PowerShell)

1. Install Node.js (recommended LTS) from https://nodejs.org
2. From the project root open PowerShell and run:

```powershell
# install dependencies
npm install
# install Playwright browsers (recommended)
npx playwright install --with-deps
```

Note: `npx playwright install --with-deps` installs browser binaries. If you cannot run browser installs, you can still run tests with `--headed=false` if a browser is already available.

Running the app locally

Make sure the Flask app is running locally at `http://127.0.0.1:5000` (default). Example PowerShell snippet:

```powershell
# create venv (optional but recommended)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# set reasonable MKL/numexpr thread limits (helps avoid runtime aborts on some systems)
$env:MKL_NUM_THREADS = '1'
$env:NUMEXPR_MAX_THREADS = '4'
$env:OMP_NUM_THREADS = '1'
# run the flask app
python run.py
```

Running the Playwright tests

Open a new PowerShell terminal (after the app is running) and from the project root run:

```powershell
# run playwright tests
npm test
```

If your app is served at a different host/port, set the `TEST_BASE_URL` environment variable before running the tests, for example:

```powershell
$env:TEST_BASE_URL = 'http://0.0.0.0:5000'
npm test
```

What the test does

- Visits `/`, `/patient`, and `/doctor` pages
- Confirms the presence of `<script type="application/ld+json">`
- Confirms that `#print-btn` exists
- Finds `img[data-src]` and attempts to scroll each into view and waits for the `data-src` attribute to be removed by the page's IntersectionObserver. If the page does not auto-swap (e.g., IntersectionObserver not triggered in headless environment), the test will attempt a manual swap as a fallback and still assert the image got a `src` value.

Output

Playwright will print test results to the terminal. Any failures will be shown with stack traces and the test's console output may include warnings about images that didn't auto-swap.

Artifacts (screenshots / video / trace)

On failure Playwright will now save artifacts. Screenshots are written to `test-results/screenshots/` and Playwright may save video/trace files under its default `playwright-report` or `test-results` folders depending on the run. Check those folders for debugging artifacts after a failing run.

Strict lazy-load mode

The tests include a strict validation that an image's network request occurs after the test scrolls it into view. This can be toggled using the `TEST_STRICT_LAZY` environment variable.

Examples (PowerShell):
```powershell
# strict mode (assert request happened after scroll)
$env:TEST_STRICT_LAZY = 'true'
npm test

# non-strict mode (default - more tolerant to timing variations)
$env:TEST_STRICT_LAZY = 'false'
npm test
```

Closing notes

If you want, I can also provide a GitHub Actions workflow to run these tests in CI (useful after you push), or tune the test to capture screenshots on failure for easier debugging.

Caching / header verification

- The Playwright tests now validate that image responses include at least one caching indicator: `ETag`, `Last-Modified`, or `Cache-Control`.
- If an `ETag` is present the tests will make a conditional request using `If-None-Match` and expect `304 Not Modified` ideally. The test will accept `200` as a fallback but logs a warning when `304` is not returned.
- If your server does not return caching headers for static image assets the test will fail the caching assertion. To fix this, configure your static file responses (Flask static file serving, CDN, or reverse proxy) to return `Cache-Control` and/or `ETag`/`Last-Modified` headers.

Quick manual header check (PowerShell):
```powershell
curl -I http://127.0.0.1:5000/static/assets/images/your-image.png
```

Look for `ETag:`, `Last-Modified:`, or `Cache-Control:` in the output.

Optional: `TEST_CACHE_STRICT` env flag
- The tests accept missing caching headers by default to be tolerant across environments.
- If you want CI to enforce caching headers as a requirement, set `TEST_CACHE_STRICT=true` before running tests. In that mode the test will fail when image responses do not include `ETag`, `Last-Modified`, or `Cache-Control`.

Example (PowerShell):
```powershell
# enforce caching header presence in CI or locally
$env:TEST_CACHE_STRICT = 'true'
npm test
```