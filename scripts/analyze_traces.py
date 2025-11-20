#!/usr/bin/env python3
"""
Analyze Playwright trace.zip files and error-context to produce a concise failure summary.
Outputs `test-results/trace-analysis.json` and prints a readable report.
"""
import json
import zipfile
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / 'test-results'
OUT = TR / 'trace-analysis.json'

results = []

if not TR.exists():
    print('No test-results directory found')
    raise SystemExit(1)

trace_zips = list(TR.rglob('trace.zip'))
if not trace_zips:
    print('No trace.zip files found under test-results/')
    raise SystemExit(0)

for tz in trace_zips:
    item = {
        'trace_zip': str(tz.resolve()),
        'test_dir': str(tz.parent.resolve()),
        'video': None,
        'screenshot': None,
        'error_context': None,
        'inferred_failure': None,
        'trace_actions': []
    }
    # find video and screenshot in same dir
    for ext in ['*.webm', '*.mp4']:
        for f in tz.parent.glob(ext):
            item['video'] = str(f.resolve())
            break
        if item['video']:
            break
    # screenshot
    for f in tz.parent.glob('*.png'):
        item['screenshot'] = str(f.resolve())
        break
    # error-context.md
    ectx = tz.parent / 'error-context.md'
    if ectx.exists():
        item['error_context'] = ectx.read_text(encoding='utf-8')
    # unzip trace and try to find trace.json or trace.*.json files
    try:
        with zipfile.ZipFile(tz, 'r') as z:
            namelist = z.namelist()
            # heuristics: look for 'trace.json' or files under 'trace/' or any .json containing 'events'
            candidate = None
            for n in namelist:
                ln = n.lower()
                if ln.endswith('trace.json') or ln.endswith('trace.events.json'):
                    candidate = n
                    break
            if not candidate:
                # find first large json in root
                for n in namelist:
                    if n.endswith('.json') and ('report' not in n.lower()):
                        candidate = n
                        break
            if candidate:
                with z.open(candidate) as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        # fallback: read as text and extract lines mentioning 'callsite' or 'action' or 'apiName'
                        txt = f.read().decode('utf-8', errors='replace')
                        data = None
                # If parsed JSON, try to find events/actions
                if isinstance(data, dict):
                    # different trace formats; try to find 'events' or 'actions'
                    if 'events' in data:
                        events = data.get('events')
                    elif 'frames' in data:
                        events = data.get('frames')
                    else:
                        events = None
                    if events and isinstance(events, list):
                        # look for failing actions: waitForFunction, scrollIntoView, getAttribute, locator
                        patterns = [r'waitForFunction', r'scrollIntoView', r'getAttribute', r'locator', r'waitForSelector']
                        for ev in events:
                            # stringify event
                            s = json.dumps(ev)
                            for p in patterns:
                                if re.search(p, s, re.IGNORECASE):
                                    item['trace_actions'].append({'pattern': p, 'event': ev})
                                    break
                    else:
                        # search JSON text for keywords
                        jtxt = json.dumps(data)
                        if re.search(r'waitForFunction|scrollIntoView|getAttribute|locator|waitForSelector', jtxt, re.IGNORECASE):
                            item['trace_actions'].append({'note': 'keyword found in trace JSON (unstructured)'} )
            else:
                item['trace_actions'].append({'note': 'no JSON candidate found inside trace.zip; listing files', 'files': namelist})
    except Exception as e:
        item['trace_actions'].append({'error': str(e)})

    # Infer failure from error_context or screenshot name
    inferred = None
    if item['error_context']:
        # attempt to extract the top error line
        m = re.search(r'Error:\s*(.+)', item['error_context'])
        if not m:
            # fallback to first non-empty line
            for line in item['error_context'].splitlines():
                line = line.strip()
                if line:
                    m = re.match(r'(.+)', line)
                    break
        if m:
            inferred = m.group(1).strip()
    # if trace_actions have patterns, include the first as inferred cause
    if not inferred and item['trace_actions']:
        first = item['trace_actions'][0]
        inferred = first.get('pattern') or first.get('note') or str(first)
    item['inferred_failure'] = inferred

    results.append(item)

# write JSON
OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
print('Wrote', OUT)
# Print concise human-readable report
for r in results:
    print('\n----')
    print('Test dir:', r['test_dir'])
    print('Trace zip:', r['trace_zip'])
    if r['video']:
        print('Video:', r['video'])
    if r['screenshot']:
        print('Screenshot:', r['screenshot'])
    if r['error_context']:
        print('Error (excerpt):')
        print('\n'.join([l for l in r['error_context'].splitlines() if l.strip()][:6]))
    print('Inferred failure:', r['inferred_failure'])
    if r['trace_actions']:
        print('Trace actions / keywords found (sample):')
        for a in r['trace_actions'][:3]:
            if 'pattern' in a:
                print('-', a['pattern'])
            else:
                print('-', a.get('note') or a)

print('\nDone.')
