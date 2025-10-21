from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime

# MongoDB connection
MONGO_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

try:
    client = MongoClient(MONGO_URI)
    db = client['bitgpt']
    
    print('=' * 60)
    print('Creating Referrer TreePlacement (Root)')
    print('=' * 60)
    
    referrer_id = '68f761a6b96865d5ce4f36a5'
    
    # Check if referrer already has TreePlacement for Matrix
    existing = db.tree_placements.find_one({
        'user_id': ObjectId(referrer_id),
        'program': 'matrix',
        'slot_no': 1
    })
    
    if existing:
        print(f'\n✅ Referrer already has TreePlacement for Matrix Slot 1')
        print(f'   Level: {existing.get("level")}')
        print(f'   Position: {existing.get("position")}')
    else:
        print(f'\n🔍 Creating TreePlacement for referrer as ROOT node...')
        
        # Create TreePlacement for referrer (as root)
        tree_placement = {
            'user_id': ObjectId(referrer_id),
            'program': 'matrix',
            'parent_id': ObjectId(referrer_id),  # Self as parent (root)
            'upline_id': ObjectId(referrer_id),  # Self as upline (root)
            'position': 'root',
            'level': 0,  # Root is level 0
            'slot_no': 1,
            'is_spillover': False,
            'is_active': True,
            'created_at': datetime.utcnow()
        }
        
        result = db.tree_placements.insert_one(tree_placement)
        print(f'✅ TreePlacement created for referrer!')
        print(f'   ID: {result.inserted_id}')
        print(f'   Program: matrix')
        print(f'   Level: 0 (root)')
        print(f'   Slot: 1')
    
    # Now check total Matrix TreePlacements
    total_matrix = db.tree_placements.count_documents({'program': 'matrix'})
    print(f'\n📊 Total Matrix TreePlacements: {total_matrix}')
    
    client.close()
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

