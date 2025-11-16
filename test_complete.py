#!/usr/bin/env python
"""
اختبار شامل لسير العمل الكامل للتطبيق
Testing: Registration, Login, Role-based Access Control, API Endpoints
"""
import requests
import json

BASE_URL = 'http://localhost:5000'
RESULTS = []

def test_case(name, condition, expected=True):
    """تسجيل نتيجة الاختبار"""
    status = "✓ PASS" if condition == expected else "✗ FAIL"
    RESULTS.append((status, name))
    print(f"{status}: {name}")
    return condition == expected

print("\n" + "="*70)
print("🧪 COMPREHENSIVE LOGIN & ROLE-BASED ACCESS TEST")
print("="*70)

# ============================================================================
# 1. TEST: Register Patient User
# ============================================================================
print("\n[1] REGISTRATION TESTS")
print("-" * 70)

session = requests.Session()
resp = session.get(f'{BASE_URL}/')
csrf_token = session.cookies.get('XSRF-TOKEN')

patient_data = {
    'username': 'patient_final_test',
    'email': 'patient@test.com',
    'password': 'Test12345678',
    'userType': 'patient'
}

resp = session.post(
    f'{BASE_URL}/api/auth/register',
    json=patient_data,
    headers={'X-CSRF-Token': csrf_token, 'XSRF-TOKEN': csrf_token}
)
test_case("Patient registration returns 201", resp.status_code, 201)
patient_user_id = resp.json()['data']['user_id']

# ============================================================================
# 2. TEST: Patient Login
# ============================================================================
print("\n[2] LOGIN TESTS")
print("-" * 70)

# Fresh session for login test
login_session = requests.Session()
resp = login_session.get(f'{BASE_URL}/')
csrf_token = login_session.cookies.get('XSRF-TOKEN')

login_data = {
    'username': 'patient_final_test',
    'password': 'Test12345678'
}

resp = login_session.post(
    f'{BASE_URL}/api/auth/login',
    json=login_data,
    headers={'X-CSRF-Token': csrf_token, 'XSRF-TOKEN': csrf_token}
)

test_case("Login returns 200", resp.status_code, 200)
result = resp.json()
test_case("Login returns success=true", result.get('success'), True)

user_role = result['data'].get('role')
test_case("Login returns role='patient'", user_role, 'patient')
test_case("Login returns user_id", bool(result['data'].get('user_id')), True)
test_case("Login returns username", bool(result['data'].get('username')), True)

# ============================================================================
# 3. TEST: Role-Based Page Access Control
# ============================================================================
print("\n[3] ROLE-BASED ACCESS CONTROL TESTS")
print("-" * 70)

# Patient accessing /patient page
resp = login_session.get(f'{BASE_URL}/patient')
test_case("Patient can access /patient (200)", resp.status_code, 200)

# Patient accessing /doctor page (should be forbidden or redirect)
resp = login_session.get(f'{BASE_URL}/doctor', allow_redirects=False)
test_case("Patient cannot access /doctor (should be 403/302)", 
          resp.status_code in [302, 403], True)

# Patient accessing /admin page (should be forbidden or redirect)
resp = login_session.get(f'{BASE_URL}/admin', allow_redirects=False)
test_case("Patient cannot access /admin (should be 403/302)", 
          resp.status_code in [302, 403], True)

# ============================================================================
# 4. TEST: Doctor User Registration and Access
# ============================================================================
print("\n[4] DOCTOR USER TESTS")
print("-" * 70)

doc_session = requests.Session()
resp = doc_session.get(f'{BASE_URL}/')
csrf_token_doc = doc_session.cookies.get('XSRF-TOKEN')

doctor_data = {
    'username': 'doctor_final_test',
    'email': 'doctor@test.com',
    'password': 'Test12345678',
    'userType': 'doctor'
}

resp = doc_session.post(
    f'{BASE_URL}/api/auth/register',
    json=doctor_data,
    headers={'X-CSRF-Token': csrf_token_doc, 'XSRF-TOKEN': csrf_token_doc}
)
test_case("Doctor registration returns 201", resp.status_code, 201)

# Login as doctor
resp = doc_session.get(f'{BASE_URL}/')
csrf_token_doc = doc_session.cookies.get('XSRF-TOKEN')

resp = doc_session.post(
    f'{BASE_URL}/api/auth/login',
    json={'username': 'doctor_final_test', 'password': 'Test12345678'},
    headers={'X-CSRF-Token': csrf_token_doc, 'XSRF-TOKEN': csrf_token_doc}
)

test_case("Doctor login returns 200", resp.status_code, 200)
test_case("Doctor role is 'doctor'", resp.json()['data'].get('role'), 'doctor')

# Doctor page access
resp = doc_session.get(f'{BASE_URL}/doctor')
test_case("Doctor can access /doctor (200)", resp.status_code, 200)

# Doctor cannot access patient page
resp = doc_session.get(f'{BASE_URL}/patient')
test_case("Doctor cannot access /patient (403)", resp.status_code, 403)

# ============================================================================
# 5. TEST: API Endpoints
# ============================================================================
print("\n[5] API ENDPOINT TESTS")
print("-" * 70)

# Get auth status
resp = login_session.get(f'{BASE_URL}/api/auth/status')
test_case("Auth status returns 200", resp.status_code, 200)
test_case("Auth status shows authenticated", resp.json()['data'].get('is_authenticated'), True)
test_case("Auth status shows correct role", resp.json()['data'].get('role'), 'patient')

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*70)
print("📋 TEST SUMMARY")
print("="*70)

pass_count = sum(1 for status, _ in RESULTS if "PASS" in status)
fail_count = sum(1 for status, _ in RESULTS if "FAIL" in status)

for status, name in RESULTS:
    print(f"{status}: {name}")

print("\n" + "="*70)
print(f"Total: {pass_count + fail_count} | Passed: {pass_count} | Failed: {fail_count}")
if fail_count == 0:
    print("🎉 ALL TESTS PASSED!")
else:
    print(f"⚠️  {fail_count} tests failed")
print("="*70)
