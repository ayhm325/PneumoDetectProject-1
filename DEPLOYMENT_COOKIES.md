# Deployment Cookies & CSRF

Purpose: Ensure session and CSRF cookies are accepted when clients access the site via different origins (e.g., `localhost`, `127.0.0.1`, or LAN IP like `192.168.x.x`). Modern browsers require `SameSite=None` + `Secure` to accept cross-site cookies.

Recommended env vars:
- `SESSION_COOKIE_SAMESITE` (e.g. `None` in production)
- `SESSION_COOKIE_SECURE` (set to `True` in production)
- `REMEMBER_COOKIE_SAMESITE` / `REMEMBER_COOKIE_SECURE` (same rules)
- `SESSION_COOKIE_DOMAIN` (optional, for sharing across subdomains)

Important: Browsers accept cookies with `SameSite=None` only when `Secure=True` (HTTPS required). Ensure TLS on production (reverse proxy/load balancer). For local testing keep `SESSION_COOKIE_SAMESITE=Lax` and `SESSION_COOKIE_SECURE=False`.

Example (PowerShell) to run with production-like cookie settings:

```powershell
$Env:FLASK_ENV='production'
$Env:SESSION_COOKIE_SAMESITE='None'
$Env:SESSION_COOKIE_SECURE='True'
$Env:REMEMBER_COOKIE_SAMESITE='None'
$Env:REMEMBER_COOKIE_SECURE='True'
.\venv\Scripts\python.exe .\run.py
```
