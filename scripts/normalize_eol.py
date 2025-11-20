from pathlib import Path
p = Path('.github/workflows/playwright.yml')
text = p.read_text(encoding='utf-8')
new = text.replace('\r\n', '\n').replace('\r', '\n')
p.write_text(new, encoding='utf-8', newline='\n')
print('Normalized EOL for', p)
