from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGO_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

try:
    client = MongoClient(MONGO_URI)
    db = client['bitgpt']
    
    print('=' * 60)
    print('DIRECT DATABASE CHECK')
    print('=' * 60)
    
    referrer_id = '68f761a6b96865d5ce4f36a5'
    
    # 1. Check User
    print(f'\n1. Checking User:')
    user = db.users.find_one({'_id': ObjectId(referrer_id)})
    if user:
        print(f'   UID: {user.get("uid")}')
        print(f'   Name: {user.get("name")}')
        print(f'   Matrix Joined: {user.get("matrix_joined")}')
        print(f'   Binary Joined: {user.get("binary_joined")}')
    else:
        print(f'   ❌ User not found')
    
    # 2. Check MatrixTree
    print(f'\n2. Checking MatrixTree:')
    matrix_tree = db.matrix_trees.find_one({'user_id': ObjectId(referrer_id)})
    if matrix_tree:
        total_members = matrix_tree.get('total_members', 0)
        nodes_count = len(matrix_tree.get('nodes', []))
        print(f'   Total Members: {total_members}')
        print(f'   Nodes Count: {nodes_count}')
        
        if nodes_count > 0:
            print(f'\n   First 3 Nodes:')
            for i, node in enumerate(matrix_tree.get('nodes', [])[:3], 1):
                node_user_id = node.get('user_id')
                node_level = node.get('level')
                node_position = node.get('position')
                print(f'     {i}. User: {node_user_id}, Level: {node_level}, Position: {node_position}')
    else:
        print(f'   ❌ MatrixTree not found')
    
    # 3. Check TreePlacement for Matrix
    print(f'\n3. Checking TreePlacement (Matrix):')
    tree_placements = list(db.tree_placements.find({
        'upline_id': ObjectId(referrer_id),
        'program': 'matrix'
    }).limit(5))
    
    if tree_placements:
        print(f'   Found {len(tree_placements)} placements')
        for i, placement in enumerate(tree_placements, 1):
            user_id = placement.get('user_id')
            position = placement.get('position')
            level = placement.get('level')
            slot_no = placement.get('slot_no')
            print(f'     {i}. User: {user_id}, Position: {position}, Level: {level}, Slot: {slot_no}')
    else:
        print(f'   ❌ No TreePlacement records found for Matrix!')
        print(f'   This is why Dream Matrix shows 0 members')
    
    # 4. Check all TreePlacement records for Matrix (any upline)
    print(f'\n4. Checking ALL Matrix TreePlacements:')
    all_matrix_placements = db.tree_placements.count_documents({'program': 'matrix'})
    print(f'   Total Matrix TreePlacements in DB: {all_matrix_placements}')
    
    if all_matrix_placements == 0:
        print(f'\n   ❌ PROBLEM IDENTIFIED:')
        print(f'      Matrix join does NOT create TreePlacement records!')
        print(f'      MatrixTree has nodes, but TreePlacement is empty')
    
    # 5. Check SlotActivation
    print(f'\n5. Checking SlotActivation (Matrix):')
    slot_activations = list(db.slot_activation.find({
        'user_id': ObjectId(referrer_id),
        'program': 'matrix'
    }))
    
    if slot_activations:
        print(f'   Found {len(slot_activations)} activations')
        for activation in slot_activations:
            slot_no = activation.get('slot_no')
            status = activation.get('status')
            print(f'     Slot {slot_no}: {status}')
    else:
        print(f'   No slot activations')
    
    print('\n' + '=' * 60)
    print('DIAGNOSIS:')
    print('=' * 60)
    
    if all_matrix_placements == 0 and matrix_tree:
        print('\n✅ MatrixTree exists with nodes')
        print('❌ TreePlacement records NOT created')
        print('\nSOLUTION:')
        print('  Matrix join should create TreePlacement records')
        print('  OR Dream Matrix should use MatrixTree.nodes instead')
    
    client.close()
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

