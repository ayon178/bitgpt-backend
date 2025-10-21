from mongoengine import connect
from bson import ObjectId
from modules.tree.model import TreePlacement

# Connect
connect(
    db='bitgpt',
    host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt?retryWrites=true&w=majority'
)

try:
    referrer_id = ObjectId('68f761a6b96865d5ce4f36a5')
    
    print('Testing TreePlacement query directly')
    print('=' * 60)
    
    # Get all matrix placements first
    all_matrix = TreePlacement.objects(program='matrix')
    print(f'\nTotal Matrix placements: {all_matrix.count()}')
    
    # Show first few
    for i, p in enumerate(all_matrix[:5], 1):
        print(f'\n{i}. User: {p.user_id}')
        print(f'   Upline: {p.upline_id}')
        print(f'   Position: {p.position}')
        print(f'   Level: {p.level}')
        print(f'   Match referrer? {p.upline_id == referrer_id}')
    
    # Now query by upline_id
    print(f'\n' + '=' * 60)
    print(f'Query by upline_id:')
    print('=' * 60)
    
    children = TreePlacement.objects(
        program='matrix',
        upline_id=referrer_id
    )
    
    count = children.count()
    print(f'\nFound: {count} children')
    
    if count > 0:
        print(f'\n✅ Query working! Children:')
        for i, child in enumerate(children, 1):
            print(f'  {i}. User: {child.user_id}, Position: {child.position}')
    else:
        print(f'\n❌ Query returned 0')
        
        # Try filtering manually
        print(f'\nManual check:')
        for p in all_matrix:
            if p.upline_id == referrer_id:
                print(f'  Found match: {p.user_id}')
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

