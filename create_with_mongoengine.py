from mongoengine import connect
from bson import ObjectId
from datetime import datetime

# Connect
connect(
    db='bitgpt',
    host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt?retryWrites=true&w=majority'
)

from modules.tree.model import TreePlacement
from modules.user.model import User

try:
    referrer_id = ObjectId('68f761a6b96865d5ce4f36a5')
    
    print('=' * 60)
    print('Creating TreePlacement with MongoEngine')
    print('=' * 60)
    
    # Delete old Matrix placements
    deleted = TreePlacement.objects(program='matrix').delete()
    print(f'\nDeleted {deleted} old Matrix TreePlacements')
    
    # Create root
    root = TreePlacement(
        user_id=referrer_id,
        program='matrix',
        parent_id=referrer_id,
        upline_id=referrer_id,
        position='root',
        level=0,
        slot_no=1,
        is_spillover=False,
        is_active=True,
        created_at=datetime.utcnow()
    )
    root.save()
    print(f'1. Root created')
    
    # Get Matrix users
    matrix_users = User.objects(refered_by=referrer_id, matrix_joined=True).limit(3)
    users_list = list(matrix_users)
    print(f'\nFound {len(users_list)} Matrix users')
    
    # Create children
    positions = ['left', 'middle', 'right']
    for i, user in enumerate(users_list):
        child = TreePlacement(
            user_id=user.id,
            program='matrix',
            parent_id=referrer_id,
            upline_id=referrer_id,
            position=positions[i],
            level=1,
            slot_no=1,
            is_spillover=False,
            is_active=True,
            created_at=datetime.utcnow()
        )
        child.save()
        uid = user.uid if user.uid else str(user.id)
        print(f'{i+2}. {uid}: Level 1, Position {positions[i]}')
    
    # Verify with MongoEngine query
    print(f'\n' + '=' * 60)
    print('Verification:')
    print('=' * 60)
    
    children = TreePlacement.objects(program='matrix', upline_id=referrer_id)
    count = children.count()
    
    print(f'\nTreePlacements with upline_id={referrer_id}: {count}')
    
    if count > 0:
        print(f'\n✅ MongoEngine query working! Children:')
        for i, child in enumerate(children, 1):
            uid = child.user_id
            pos = child.position
            lvl = child.level
            print(f'  {i}. User: {uid}, Position: {pos}, Level: {lvl}')
        
        print(f'\n✅ TreePlacement data created successfully!')
        print(f'   Now test Dream Matrix API')
    else:
        print(f'\n❌ Still 0 children - something wrong')
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

