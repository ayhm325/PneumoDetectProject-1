from pathlib import Path
import sys
p = Path('.github/workflows/playwright.yml')
text = p.read_text(encoding='utf-8')
try:
    import yaml
except Exception as e:
    print('PyYAML not installed. Install with: pip install pyyaml')
    sys.exit(2)
try:
    doc = yaml.safe_load(text)
    print('Parsed OK. Top-level type:', type(doc))
    if isinstance(doc, dict):
        print('Top keys:', list(doc.keys()))
        print('\nFull parsed structure:')
        try:
            print(yaml.dump(doc, sort_keys=False))
        except Exception:
            print(repr(doc))
except Exception as e:
    print('YAML parse error:', repr(e))
    sys.exit(1)
