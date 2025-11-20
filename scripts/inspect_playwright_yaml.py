from pathlib import Path
p = Path('.github/workflows/playwright.yml')
b = p.read_bytes()
print('Bytes length:', len(b))
print('First 64 bytes (hex):', b[:64].hex(' '))
text = b.decode('utf-8', errors='replace')
lines = text.splitlines()
for i, line in enumerate(lines[:10], start=1):
    print(f"{i:02d}: {repr(line)}")
    print('   bytes:', list(line.encode('utf-8'))[:80])
print('--- full top 20 lines ---')
for i, line in enumerate(lines[:20], start=1):
    print(f'{i:02d}:', line)
