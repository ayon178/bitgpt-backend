import requests
import json
import random

# Create user via temp-create API
url = 'http://127.0.0.1:8000/user/temp-create'
data = {
    'uid': f'user{random.randint(10000000000000000, 99999999999999999)}',
    'refer_code': f'REF{random.randint(100000, 999999)}',
    'wallet_address': f'0x{random.randint(1000000000000000000000000000000000000000, 9999999999999999999999999999999999999999)}',
    'name': f'Test User {random.randint(1000, 9999)}',
    'email': f'test{random.randint(1000, 9999)}@example.com',
    'password': 'test_password',
    'refered_by': 'RC1761042853479394'
}

print('=== Creating User via API ===')
print(f'Data: {data}')

response = requests.post(url, json=data)
print(f'Status Code: {response.status_code}')
print(f'Response: {response.text}')

if response.status_code == 200:
    result = response.json()
    if result.get('success'):
        user_id = result.get('data', {}).get('user_id')
        print(f'✅ User created successfully: {user_id}')
        
        # Store user_id for next step
        with open('temp_user_id.txt', 'w') as f:
            f.write(user_id)
    else:
        print(f'❌ User creation failed: {result.get("error", "Unknown error")}')
else:
    print(f'❌ API call failed: {response.status_code}')
