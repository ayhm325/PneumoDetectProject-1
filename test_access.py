import requests

session = requests.Session()

# Get CSRF token
resp = session.get('http://localhost:5000/')
csrf_token = session.cookies.get('XSRF-TOKEN')

# Login as patient
data = {
    'username': 'testpatient',
    'password': 'Test12345678',
}

resp = session.post(
    'http://localhost:5000/api/auth/login',
    json=data,
    headers={'X-CSRF-Token': csrf_token, 'XSRF-TOKEN': csrf_token}
)

print("✓ Login Status:", resp.status_code)

# Test /patient page access
resp = session.get('http://localhost:5000/patient')
print("✓ GET /patient Status:", resp.status_code, "(should be 200)")

# Test /doctor page access (should be forbidden)
resp = session.get('http://localhost:5000/doctor')
print("✓ GET /doctor Status:", resp.status_code, "(should be 403 or 302)")

# Test /admin page access (should be forbidden)
resp = session.get('http://localhost:5000/admin')
print("✓ GET /admin Status:", resp.status_code, "(should be 403 or 302)")

print("\n✓ Page access control tests completed!")
