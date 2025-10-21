import requests
import json

referrer_code = 'RC1761042853479394'
referrer_id = '68f761a6b96865d5ce4f36a5'

# Create user via temp-create
url = 'http://localhost:8000/user/temp-create'
payload = {
    'email': 'matrix_4th_final@example.com',
    'name': 'Matrix 4th Final User',
    'refered_by': referrer_code
}

print('Creating 4th user...')
r = requests.post(url, json=payload)

if r.status_code == 201:
    user_info = r.json()['data']
    uid = user_info['uid']
    user_id = user_info['_id']
    token = user_info['token']
    
    print(f'✅ User created: {uid}')
    print(f'   ID: {user_id}')
    print(f'   Token: {token[:50]}...')
    
    # Save to file
    with open('4th_user_data.json', 'w') as f:
        json.dump({'uid': uid, 'user_id': user_id, 'token': token}, f, indent=2)
    print(f'   ✅ Token saved to 4th_user_data.json')
    
    # Join Matrix
    matrix_url = f'http://localhost:8000/matrix/join/{user_id}/{referrer_id}'
    headers = {'Authorization': f'Bearer {token}'}
    
    print(f'\nJoining Matrix...')
    mr = requests.post(matrix_url, headers=headers)
    
    if mr.status_code == 200:
        result = mr.json()
        success = result.get('success')
        
        if success:
            print(f'✅ Matrix joined successfully!')
            print(f'\nCheck server console for TreePlacement message:')
            print(f'  Expected: Level 2 under first child (left position)')
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f'❌ Matrix join failed: {error_msg}')
    else:
        print(f'❌ Matrix join HTTP error: {mr.status_code}')
else:
    error_text = r.text
    print(f'❌ User creation failed: {error_text}')

