import requests
import json

session = requests.Session()

# Get CSRF token
resp = session.get('http://localhost:5000/')
csrf_token = session.cookies.get('XSRF-TOKEN')

# Create doctor user
data = {
    'username': 'testdoctor',
    'email': 'testdoctor@test.com',
    'password': 'Test12345678',
    'userType': 'doctor'
}

resp = session.post(
    'http://localhost:5000/api/auth/register',
    json=data,
    headers={'X-CSRF-Token': csrf_token, 'XSRF-TOKEN': csrf_token}
)
print("✓ Doctor registration:", resp.status_code)

# Create another session for doctor login
doctor_session = requests.Session()
resp = doctor_session.get('http://localhost:5000/')
csrf_token_doc = doctor_session.cookies.get('XSRF-TOKEN')

# Login as doctor
login_data = {
    'username': 'testdoctor',
    'password': 'Test12345678'
}

resp = doctor_session.post(
    'http://localhost:5000/api/auth/login',
    json=login_data,
    headers={'X-CSRF-Token': csrf_token_doc, 'XSRF-TOKEN': csrf_token_doc}
)

print("\n✓ Doctor login status:", resp.status_code)
result = resp.json()
print("✓ Doctor user role:", result['data'].get('role'))

# Test doctor page access
resp = doctor_session.get('http://localhost:5000/doctor')
print("✓ GET /doctor as doctor:", resp.status_code)

# Test patient page access as doctor
resp = doctor_session.get('http://localhost:5000/patient')
print("✓ GET /patient as doctor:", resp.status_code)

print("\n" + "="*50)
print("All tests completed!")
print("="*50)
