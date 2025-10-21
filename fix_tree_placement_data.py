from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

MONGO_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

try:
    client = MongoClient(MONGO_URI)
    db = client['bitgpt']
    
    referrer_id = ObjectId('68f761a6b96865d5ce4f36a5')
    
    print('=' * 60)
    print('Fixing TreePlacement Data')
    print('=' * 60)
    
    # First, delete old incorrect placements
    print(f'\nDeleting old Matrix TreePlacements...')
    result = db.tree_placements.delete_many({'program': 'matrix'})
    print(f'  Deleted: {result.deleted_count} records')
    
    # Get Matrix users under this referrer
    matrix_users = list(db.users.find({
        'refered_by': referrer_id,
        'matrix_joined': True
    }).limit(5))
    
    print(f'\nFound {len(matrix_users)} Matrix users')
    
    # Create root TreePlacement for referrer
    print(f'\nCreating TreePlacement records:')
    
    # 1. Referrer as root
    root_placement = {
        'user_id': referrer_id,
        'program': 'matrix',
        'parent_id': referrer_id,
        'upline_id': referrer_id,
        'position': 'root',
        'level': 0,
        'slot_no': 1,
        'is_spillover': False,
        'is_active': True,
        'created_at': datetime.utcnow()
    }
    
    db.tree_placements.insert_one(root_placement)
    print(f'  1. Root created (Level 0)')
    
    # 2. Create children
    positions = ['left', 'middle', 'right']
    
    for i, user in enumerate(matrix_users[:3], 0):
        user_id = user['_id']
        uid = user.get('uid', str(user_id))
        position = positions[i]
        
        placement = {
            'user_id': user_id,
            'program': 'matrix',
            'parent_id': referrer_id,
            'upline_id': referrer_id,  # CRITICAL: Must match referrer
            'position': position,
            'level': 1,
            'slot_no': 1,
            'is_spillover': False,
            'is_active': True,
            'created_at': datetime.utcnow()
        }
        
        db.tree_placements.insert_one(placement)
        print(f'  {i+2}. {uid}: Level 1, Position {position}')
    
    # Verify
    print(f'\n' + '=' * 60)
    print('Verification:')
    print('=' * 60)
    
    total = db.tree_placements.count_documents({
        'program': 'matrix',
        'upline_id': referrer_id
    })
    
    print(f'\nTreePlacements with upline_id={referrer_id}: {total}')
    
    if total >= 3:
        print(f'\n✅ TreePlacement data fixed!')
        print(f'   Now test Dream Matrix API again')
    
    client.close()
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

