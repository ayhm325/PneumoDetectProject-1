#!/usr/bin/env python3
"""
Extract embedded Playwright HTML report (a base64 ZIP inside `playwright-report/index.html`)
and produce a per-test summary with links to extracted artifacts.

Usage:
  python scripts/extract_playwright_report.py

Outputs:
  - playwright-report/extracted/ (extracted files)
  - playwright-report/extracted/summary.json
"""
import re
import os
import sys
import json
import base64
import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_HTML = ROOT / "playwright-report" / "index.html"
OUT_DIR = ROOT / "playwright-report" / "extracted"

if not REPORT_HTML.exists():
    print(f"Error: {REPORT_HTML} not found", file=sys.stderr)
    sys.exit(2)

html = REPORT_HTML.read_text(encoding="utf-8")

# Find the script tag that holds the base64 ZIP data
m = re.search(r"<script[^>]*id=\"playwrightReportBase64\"[^>]*>([\s\S]*?)</script>", html)
if not m:
    print("Error: embedded report zip not found in index.html", file=sys.stderr)
    sys.exit(3)

data_uri = m.group(1).strip()
# data URI should look like: data:application/zip;base64,....
if "," not in data_uri:
    print("Error: unexpected data URI format", file=sys.stderr)
    sys.exit(4)

prefix, b64 = data_uri.split(',', 1)
# Validate prefix briefly
if not prefix.startswith("data:") or "base64" not in prefix:
    print("Warning: data URI does not look like base64 zip; continuing anyway", file=sys.stderr)

print("Decoding base64 ZIP data...")
try:
    zipdata = base64.b64decode(b64)
except Exception as e:
    print("Error decoding base64:", e, file=sys.stderr)
    sys.exit(5)

z = zipfile.ZipFile(io.BytesIO(zipdata))
print(f"Found {len(z.namelist())} entries in embedded ZIP")

OUT_DIR.mkdir(parents=True, exist_ok=True)

# Extract all files to extracted/ preserving paths
for name in z.namelist():
    # skip directories
    if name.endswith('/'):
        continue
    target = OUT_DIR / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with z.open(name) as src, open(target, 'wb') as dst:
        dst.write(src.read())

# Read report.json if present
report_json_path = OUT_DIR / 'report.json'
if not report_json_path.exists():
    print("Error: report.json not found inside the embedded ZIP", file=sys.stderr)
    # Still exit with success code? we'll treat as failure
    sys.exit(6)

report = json.loads(report_json_path.read_text(encoding='utf-8'))

summary = []

# The ZIP also contains per-file JSON entries (fileId.json). We'll iterate those.
for entry in sorted((OUT_DIR).rglob('*.json')):
    if entry.name == 'report.json':
        continue
    try:
        data = json.loads(entry.read_text(encoding='utf-8'))
    except Exception:
        # skip non-json or large binary
        continue
    # Per-file JSON usually has a 'tests' array
    tests = data.get('tests') or []
    for t in tests:
        test_summary = {}
        test_summary['testId'] = t.get('testId')
        test_summary['title'] = t.get('title') or t.get('name') or None
        test_summary['status'] = t.get('status') or None
        # location may be under t.location or t.location.file/line
        loc = t.get('location') or t.get('location')
        if isinstance(loc, dict):
            test_summary['location'] = {k: loc.get(k) for k in ('file', 'line', 'column') if loc.get(k) is not None}
        else:
            test_summary['location'] = None

        # attachments
        atts = []
        for a in t.get('attachments', []) or []:
            att = {}
            att['name'] = a.get('name')
            att['contentType'] = a.get('contentType')
            att['pathInZip'] = a.get('path')
            if a.get('path'):
                extracted = OUT_DIR / a.get('path')
                if extracted.exists():
                    att['extractedPath'] = str(extracted.resolve())
                else:
                    att['extractedPath'] = None
            else:
                att['extractedPath'] = None
            atts.append(att)
        test_summary['attachments'] = atts

        # errors / errors array
        errs = t.get('errors') or t.get('errors')
        if errs:
            # Normalize to simple messages
            messages = []
            for e in errs:
                if isinstance(e, dict):
                    messages.append(e.get('message') or str(e))
                else:
                    messages.append(str(e))
            test_summary['errors'] = messages
        else:
            test_summary['errors'] = []

        summary.append(test_summary)

# Write summary
summary_path = OUT_DIR / 'summary.json'
summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
print(f"Wrote summary for {len(summary)} tests to: {summary_path}")
print("Extraction complete. Open playwright-report/extracted/summary.json to view results.")
