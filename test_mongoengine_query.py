from mongoengine import connect
from bson import ObjectId
from modules.tree.model import TreePlacement

# Connect to MongoDB
connect(
    db='bitgpt',
    host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt?retryWrites=true&w=majority'
)

try:
    referrer_id = ObjectId('68f761a6b96865d5ce4f36a5')
    
    print('=' * 60)
    print('Testing MongoEngine TreePlacement Query')
    print('=' * 60)
    
    # Test query
    print(f'\nQuerying TreePlacement:')
    print(f'  program: matrix')
    print(f'  upline_id: {referrer_id}')
    
    children = TreePlacement.objects(
        program='matrix',
        upline_id=referrer_id
    )
    
    count = children.count()
    print(f'\nResult: {count} records')
    
    if count > 0:
        print(f'\n✅ MongoEngine query working!')
        print(f'\nChildren:')
        for i, child in enumerate(children, 1):
            child_user = child.user_id
            child_pos = child.position
            child_level = child.level
            print(f'  {i}. User: {child_user}, Position: {child_pos}, Level: {child_level}')
    else:
        print(f'\n❌ MongoEngine query returned 0!')
        print(f'\nTrying alternative query...')
        
        # Try without ObjectId conversion
        alt_children = TreePlacement.objects(
            program='matrix',
            upline_id='68f761a6b96865d5ce4f36a5'
        )
        alt_count = alt_children.count()
        print(f'  String ID query: {alt_count} records')
        
        # Try getting all matrix placements
        all_matrix = TreePlacement.objects(program='matrix')
        all_count = all_matrix.count()
        print(f'  All Matrix placements: {all_count} records')
        
        if all_count > 0:
            print(f'\n  Sample record:')
            sample = all_matrix.first()
            print(f'    user_id type: {type(sample.user_id)}')
            print(f'    upline_id type: {type(sample.upline_id)}')
            print(f'    upline_id value: {sample.upline_id}')
            print(f'    referrer_id type: {type(referrer_id)}')
            print(f'    referrer_id value: {referrer_id}')
            print(f'    Are equal? {sample.upline_id == referrer_id}')
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

