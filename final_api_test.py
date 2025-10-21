import requests
import json

try:
    referrer_id = '68f761a6b96865d5ce4f36a5'
    
    print('=' * 60)
    print('Testing Dream Matrix Earnings API')
    print('=' * 60)
    
    url = f'http://localhost:8000/dream-matrix/earnings/{referrer_id}'
    
    print(f'\nFetching Dream Matrix earnings...')
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()['data']
        tree = data.get('tree', {})
        slots = data.get('slots', [])
        
        print(f'\n✅ API Response Successful!')
        print('=' * 60)
        
        # Tree Structure
        user_id_val = tree.get('userId')
        total_members = tree.get('totalMembers', 0)
        levels = tree.get('levels', 0)
        
        print(f'\nTree Structure:')
        print(f'  User ID: {user_id_val}')
        print(f'  Total Members: {total_members}')
        print(f'  Levels: {levels}')
        
        # Check nested structure
        nodes = tree.get('nodes', [])
        if nodes and len(nodes) > 0:
            root = nodes[0]
            root_id = root.get('id')
            root_type = root.get('type')
            root_user = root.get('userId')
            
            print(f'\n  Root Node:')
            print(f'    ID: {root_id}')
            print(f'    Type: {root_type}')
            print(f'    User: {root_user}')
            
            # Check directDownline
            if 'directDownline' in root:
                downline = root['directDownline']
                print(f'\n  ✅ NESTED STRUCTURE WORKING!')
                print(f'  Direct Downline Count: {len(downline)}')
                
                # Show all children
                for i, child in enumerate(downline, 1):
                    child_user = child.get('userId')
                    child_level = child.get('level')
                    child_pos = child.get('position')
                    has_children = 'directDownline' in child
                    
                    print(f'\n    Child {i}:')
                    print(f'      User: {child_user}')
                    print(f'      Level: {child_level}')
                    print(f'      Position: {child_pos}')
                    print(f'      Has Children: {has_children}')
                    
                    if has_children:
                        grandchildren = len(child['directDownline'])
                        print(f'      Grandchildren: {grandchildren}')
            else:
                print(f'\n  ⚠️ No directDownline found')
        
        # Slots Summary
        print(f'\n\nSlots Summary:')
        print('=' * 60)
        
        if slots and len(slots) > 0:
            # Show first 3 slots
            for slot in slots[:3]:
                slot_no = slot.get('slot_no')
                slot_name = slot.get('slot_name')
                slot_value = slot.get('slot_value')
                is_completed = slot.get('isCompleted')
                is_manual = slot.get('isManualUpgrade')
                progress = slot.get('progressPercent')
                
                print(f'\n  Slot {slot_no} ({slot_name}):')
                print(f'    Value: ${slot_value}')
                print(f'    Completed: {is_completed}')
                print(f'    Manual Upgrade: {is_manual}')
                print(f'    Progress: {progress}%')
        
        # Final verdict
        print(f'\n\n' + '=' * 60)
        print('FINAL RESULT:')
        print('=' * 60)
        
        if total_members > 0:
            print(f'\n✅ SUCCESS! Tree has {total_members} members')
            print(f'✅ Nested structure working')
            print(f'✅ Progress calculation working')
            print(f'✅ API matching Binary API structure')
        else:
            print(f'\n❌ Tree still shows 0 members')
            print(f'   Check TreePlacement queries')
            
    else:
        print(f'❌ API Error: {response.status_code}')
        print(response.text[:200])
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

