import requests
import json
import time

try:
    print('Testing server connection...')
    
    # Test server health
    try:
        r = requests.get('http://localhost:8000/docs', timeout=5)
        print(f'Server status: OK (docs accessible)')
    except:
        print(f'Server status: NOT RESPONDING')
        exit(1)
    
    referrer_code = 'RC1761042853479394'
    referrer_id = '68f761a6b96865d5ce4f36a5'
    
    # Create user
    url = 'http://localhost:8000/user/temp-create'
    payload = {
        'email': f'test_matrix_user_{int(time.time())}@example.com',
        'name': 'Test Matrix User',
        'refered_by': referrer_code
    }
    
    print('\nCreating user...')
    r = requests.post(url, json=payload, timeout=60)
    
    print(f'Response status: {r.status_code}')
    
    if r.status_code == 201:
        user_info = r.json()['data']
        uid = user_info['uid']
        user_id = user_info['_id']
        token = user_info['token']
        
        print(f'✅ User: {uid}')
        
        # Save token
        with open('4th_user_data.json', 'w') as f:
            json.dump({'uid': uid, 'user_id': user_id, 'token': token}, f)
        
        # Join Matrix
        print(f'\nJoining Matrix...')
        matrix_url = f'http://localhost:8000/matrix/join/{user_id}/{referrer_id}'
        headers = {'Authorization': f'Bearer {token}'}
        
        mr = requests.post(matrix_url, headers=headers, timeout=30)
        
        print(f'Matrix response: {mr.status_code}')
        
        if mr.status_code == 200:
            result = mr.json()
            print(f'✅ Matrix joined: {result.get("success")}')
            
            # Wait and check tree
            time.sleep(2)
            
            tree_url = f'http://localhost:8000/dream-matrix/earnings/{referrer_id}'
            tr = requests.get(tree_url, timeout=10)
            
            if tr.status_code == 200:
                tree_data = tr.json()['data']['tree']
                print(f'\nTree Members: {tree_data.get("totalMembers")}')
                print(f'Levels: {tree_data.get("levels")}')
    else:
        print(f'Failed: {r.text}')

except Exception as e:
    print(f'Error: {e}')
