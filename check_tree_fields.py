from pymongo import MongoClient
from bson import ObjectId

MONGO_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

try:
    client = MongoClient(MONGO_URI)
    db = client['bitgpt']
    
    referrer_id = ObjectId('68f761a6b96865d5ce4f36a5')
    
    print('=' * 60)
    print('Checking TreePlacement Fields')
    print('=' * 60)
    
    # Get all matrix placements
    placements = list(db.tree_placements.find({'program': 'matrix'}))
    
    print(f'\nTotal Matrix TreePlacements: {len(placements)}')
    
    for i, p in enumerate(placements, 1):
        user_id = p.get('user_id')
        parent_id = p.get('parent_id')
        upline_id = p.get('upline_id')
        position = p.get('position')
        level = p.get('level')
        
        print(f'\n{i}. TreePlacement:')
        print(f'   user_id: {user_id}')
        print(f'   parent_id: {parent_id}')
        print(f'   upline_id: {upline_id}')
        print(f'   position: {position}')
        print(f'   level: {level}')
    
    # Now check which field matches referrer
    print(f'\n' + '=' * 60)
    print('Checking which field to use for query:')
    print('=' * 60)
    
    # Count by upline_id
    by_upline = db.tree_placements.count_documents({
        'program': 'matrix',
        'upline_id': referrer_id
    })
    
    # Count by parent_id
    by_parent = db.tree_placements.count_documents({
        'program': 'matrix',
        'parent_id': referrer_id
    })
    
    print(f'\nQuery Results:')
    print(f'  By upline_id={referrer_id}: {by_upline} records')
    print(f'  By parent_id={referrer_id}: {by_parent} records')
    
    if by_upline == 0 and by_parent > 0:
        print(f'\n✅ FOUND THE ISSUE!')
        print(f'   Query should use parent_id, not upline_id')
        print(f'   Because TreePlacement records have parent_id={referrer_id}')
        print(f'   But code is querying upline_id={referrer_id}')
    
    client.close()
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

