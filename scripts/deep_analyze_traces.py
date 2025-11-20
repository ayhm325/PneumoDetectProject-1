#!/usr/bin/env python3
"""
Deep analyze Playwright trace.zip files for failing actions/selectors.
Writes `test-results/trace-deep.json` and prints a compact actionable summary.
"""
import re
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / 'test-results'
OUT = TR / 'trace-deep.json'

patterns = [
    r"img\[data-src\]",
    r"data-src",
    r"scrollIntoViewIfNeeded",
    r"scrollIntoView",
    r"waitForFunction",
    r"getAttribute",
    r"locator\(",
    r"waitForSelector",
    r"hasAttribute\(\'data-src\'",
    r"removeAttribute\(\'data-src\'",
    r"img\[",
    r"img\.progressive-img",
]
pat = re.compile("|".join(f"({p})" for p in patterns), re.IGNORECASE)

if not TR.exists():
    print('No test-results/ directory')
    raise SystemExit(1)

trace_files = list(TR.rglob('trace.zip'))
if not trace_files:
    print('No trace.zip files found')
    raise SystemExit(0)

results = []

for tz in trace_files:
    info = {'trace_zip': str(tz.resolve()), 'test_dir': str(tz.parent.resolve()), 'video': None, 'screenshot': None, 'error_context': None, 'findings': []}
    # find video/screenshot
    for ext in ('*.webm','*.mp4'):
        found = list(tz.parent.glob(ext))
        if found:
            info['video'] = str(found[0].resolve())
            break
    sfound = list(tz.parent.glob('*.png'))
    if sfound:
        info['screenshot'] = str(sfound[0].resolve())
    ectx = tz.parent / 'error-context.md'
    if ectx.exists():
        info['error_context'] = ectx.read_text(encoding='utf-8', errors='replace')

    try:
        with zipfile.ZipFile(tz, 'r') as z:
            # examine each file in zip (limit large files)
            for name in z.namelist():
                # skip large binaries by extension
                lower = name.lower()
                try:
                    with z.open(name) as fh:
                        # only read reasonable-sized text files
                        raw = fh.read(200000)  # read up to 200KB
                except Exception:
                    continue

                # decode best-effort
                try:
                    txt = raw.decode('utf-8')
                except Exception:
                    try:
                        txt = raw.decode('utf-8', errors='replace')
                    except Exception:
                        continue

                # search for patterns
                for m in pat.finditer(txt):
                    start = max(0, m.start()-120)
                    end = min(len(txt), m.end()+120)
                    snippet = txt[start:end].replace('\r','')
                    # normalize whitespace
                    snippet = '\n'.join(line.strip() for line in snippet.splitlines() if line.strip())
                    info['findings'].append({'entry': name, 'match': m.group(0), 'snippet': snippet[:800]})

            # heuristic: try to find failing stack text inside any json files in the zip
            for name in z.namelist():
                if name.lower().endswith('.json') or name.lower().endswith('.md'):
                    try:
                        with z.open(name) as fh:
                            data = fh.read(200000).decode('utf-8', errors='replace')
                    except Exception:
                        continue
                    # look for test stack traces / "waiting for locator" / "Test timeout"
                    if 'waiting for locator' in data.lower() or 'test timeout' in data.lower() or 'locator.scrollintoviewifneeded' in data.lower():
                        # capture context lines
                        lines = data.splitlines()
                        for i,l in enumerate(lines):
                            lowerl = l.lower()
                            if 'waiting for locator' in lowerl or 'test timeout' in lowerl or 'scrollintoviewifneeded' in lowerl or 'locator(' in lowerl:
                                context = '\n'.join(lines[max(0,i-4):i+4])
                                info['findings'].append({'entry': name, 'match': l.strip(), 'snippet': context})

    except Exception as e:
        info['error'] = str(e)

    # if no explicit findings, try to infer from error_context
    if not info['findings'] and info.get('error_context'):
        txt = info['error_context']
        for m in pat.finditer(txt):
            start = max(0, m.start()-120)
            end = min(len(txt), m.end()+120)
            snippet = txt[start:end]
            info['findings'].append({'entry': 'error-context.md', 'match': m.group(0), 'snippet': snippet})

    # reduce and summarize: pick top candidate matches and try to extract selector text resembling "img[data-src]" or css
    top = []
    for f in info['findings']:
        token = f['match']
        if token:
            top.append(f)
    # dedupe by match+entry
    seen = set()
    dedup = []
    for t in top:
        key = (t['entry'], t['match'])
        if key in seen: continue
        seen.add(key)
        dedup.append(t)
    info['findings'] = dedup[:6]

    # infer probable failing selector/step: prioritize exact "img[data-src]" or scrollIntoView
    inferred = None
    for f in info['findings']:
        mm = f['match'].lower()
        if 'img[data-src]' in mm or 'data-src' in mm:
            inferred = {'type': 'lazy-image', 'selector': 'img[data-src]', 'evidence': f}
            break
        if 'scrollintoview' in mm or 'scrollintoviewifneeded' in mm:
            inferred = {'type': 'scroll', 'selector': None, 'evidence': f}
            break
        if 'getattribute' in mm or 'locator(' in mm or 'waitforselector' in mm:
            # try to find a selector-like substring inside snippet: look for css in quotes
            s = f.get('snippet', '')
            q = re.search(r'(["\'])([^"\']{3,200})\1', s)
            sel = q.group(2) if q else None
            inferred = {'type': 'locator', 'selector': sel, 'evidence': f}
            break
    info['inferred'] = inferred
    results.append(info)

# write output
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
print('Wrote', OUT)

# Print compact actionable summary
for r in results:
    print('\n-----')
    print('Test dir:', r['test_dir'])
    print('Trace:', r['trace_zip'])
    if r['video']: print('Video:', r['video'])
    if r['screenshot']: print('Screenshot:', r['screenshot'])
    if r.get('error'): print('Trace read error:', r['error'])
    if r['inferred']:
        inf = r['inferred']
        t = inf.get('type')
        sel = inf.get('selector')
        print('Inferred failure type:', t)
        if sel:
            print('Selector (inferred):', sel)
        else:
            print('Selector: (not explicit)')
        ev = inf.get('evidence')
        if ev:
            print('Evidence file:', ev.get('entry'))
            print('Evidence snippet (excerpt):')
            print(ev.get('snippet')[:600])
    else:
        print('No clear inference from trace; findings:')
        for f in r['findings']:
            print('-', f['entry'], 'match->', f['match'])

print('\nDone deep analysis.')
