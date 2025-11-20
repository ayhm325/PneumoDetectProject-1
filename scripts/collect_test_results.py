#!/usr/bin/env python3
"""
Scan `test-results/` for Playwright artifacts (screenshots, videos, traces, error-context) and write a summary JSON.
"""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / 'test-results'
OUT = TR / 'artifact-summary.json'
summary = []
if not TR.exists():
    print('No test-results/ directory found')
    raise SystemExit(1)

# per-run folders (those containing trace/video/test-failed-1.png etc.)
for child in TR.iterdir():
    if child.is_dir() and child.name != 'screenshots':
        entry = {'name': child.name, 'path': str(child.resolve()), 'artifacts': []}
        for f in child.iterdir():
            if f.is_file():
                name = f.name.lower()
                if name.endswith('.png'):
                    t='screenshot'
                elif name.endswith('.webm') or name.endswith('.mp4'):
                    t='video'
                elif name.endswith('.zip'):
                    t='trace'
                elif name.endswith('.md'):
                    t='error-context'
                else:
                    t='other'
                entry['artifacts'].append({'type':t,'file':str(f.resolve())})
        summary.append(entry)

# include loose screenshots
screens = TR / 'screenshots'
if screens.exists():
    for f in screens.iterdir():
        if f.is_file():
            summary.append({'name':'screenshots/'+f.name, 'path': str(f.resolve()), 'artifacts':[{'type':'screenshot','file':str(f.resolve())}]})

OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
print('Wrote', OUT)
