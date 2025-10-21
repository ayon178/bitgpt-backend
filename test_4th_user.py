import requests
import json

try:
    referrer_code = 'RC1761042853479394'
    referrer_id = '68f761a6b96865d5ce4f36a5'
    
    print('=' * 60)
    print('Creating 4th User to Test BFS Placement')
    print('=' * 60)
    
    # Create new user
    url = 'http://localhost:8000/user/temp-create'
    payload = {
        'email': 'matrix_4th_user@example.com',
        'name': 'Matrix 4th User',
        'refered_by': referrer_code
    }
    
    print('\nCreating 4th user...')
    response = requests.post(url, json=payload)
    
    if response.status_code == 201:
        user_info = response.json()['data']
        uid = user_info['uid']
        user_id = user_info['_id']
        token = user_info['token']
        
        print(f'✅ User created: {uid}')
        print(f'   User ID: {user_id}')
        
        # Join Matrix
        matrix_url = f'http://localhost:8000/matrix/join/{user_id}/{referrer_id}'
        headers = {'Authorization': f'Bearer {token}'}
        
        print(f'\nJoining Matrix...')
        print(f'Expected: Should go to Level 2 under first child (left position child)')
        
        matrix_response = requests.post(matrix_url, headers=headers)
        
        if matrix_response.status_code == 200:
            result = matrix_response.json()
            success = result.get('success')
            
            if success:
                print(f'✅ Matrix joined successfully!')
                
                # Check server console for TreePlacement creation message
                print(f'\nCheck server console for:')
                print(f'  "Created matrix SPILLOVER placement" or')
                print(f'  "Created matrix tree placement"')
            else:
                error = result.get('error', 'Unknown')
                print(f'⚠️ Matrix join failed: {error}')
        
        print(f'\n✅ 4th User: {uid}')
        
        # Wait a bit then check tree
        import time
        time.sleep(2)
        
        # Check Dream Matrix tree
        print(f'\nChecking Dream Matrix tree structure...')
        dream_url = f'http://localhost:8000/dream-matrix/earnings/{referrer_id}'
        dream_response = requests.get(dream_url)
        
        if dream_response.status_code == 200:
            data = dream_response.json()['data']
            tree = data.get('tree', {})
            total_members = tree.get('totalMembers', 0)
            levels = tree.get('levels', 0)
            
            print(f'\nTree Status:')
            print(f'  Total Members: {total_members}')
            print(f'  Levels: {levels}')
            print(f'  Expected: 4 members, 2 levels')
            
            nodes = tree.get('nodes', [])
            if nodes and len(nodes) > 0:
                root = nodes[0]
                if 'directDownline' in root:
                    downline = root['directDownline']
                    print(f'\n  Level 1 Children: {len(downline)}')
                    
                    # Check first child for level 2
                    if len(downline) > 0:
                        first_child = downline[0]
                        first_child_uid = first_child.get('userId')
                        has_children = 'directDownline' in first_child
                        
                        print(f'\n  First Child ({first_child_uid}):')
                        print(f'    Has Children: {has_children}')
                        
                        if has_children:
                            grandchildren = first_child['directDownline']
                            print(f'    Grandchildren Count: {len(grandchildren)}')
                            
                            # Check if 4th user is here
                            for gc in grandchildren:
                                gc_uid = gc.get('userId')
                                gc_pos = gc.get('position')
                                if gc_uid == uid:
                                    print(f'\\n    ✅ FOUND 4th User!')
                                    print(f'       Position: Level 2, {gc_pos}')
                                    print(f'       Under: {first_child_uid}')
                        else:
                            print(f'    ❌ No grandchildren - placement issue!')
            
            if total_members == 4 and levels == 2:
                print(f'\\n✅ SUCCESS! BFS placement working correctly!')
            else:
                print(f'\\n⚠️ Expected 4 members, 2 levels')
        
    else:
        print(f'❌ User creation failed: {response.text[:200]}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

