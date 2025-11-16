import requests
import json

session = requests.Session()

# Get CSRF token
resp = session.get('http://localhost:5000/')
csrf_token = session.cookies.get('XSRF-TOKEN')
print('✓ Got CSRF token:', csrf_token[:20] + '...')

# Login
data = {
    'username': 'testpatient',
    'password': 'Test12345678',
    'remember_me': False
}

resp = session.post(
    'http://localhost:5000/api/auth/login',
    json=data,
    headers={'X-CSRF-Token': csrf_token, 'XSRF-TOKEN': csrf_token}
)
print('\n✓ Login Response Status:', resp.status_code)
result = resp.json()
print('\n✓ Response JSON:')
print(json.dumps(result, ensure_ascii=False, indent=2))

if result.get('success') and result.get('data'):
    user_role = result['data'].get('role')
    print('\n' + '='*50)
    print('✓ Login SUCCESS!')
    print('✓ User role detected:', user_role)
    print('✓ User ID:', result['data'].get('user_id'))
    print('✓ Username:', result['data'].get('username'))
    print('='*50)
    
    # Test role-based redirect URL
    redirect_url = '/doctor' if user_role == 'doctor' else '/admin' if user_role == 'admin' else '/patient'
    print(f'\n✓ Redirect URL should be: {redirect_url}')
else:
    print('\n✗ Login FAILED!')
    print(result.get('message', 'Unknown error'))
