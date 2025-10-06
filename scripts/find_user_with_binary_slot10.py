import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.db import connect_to_db
from modules.slot.model import SlotActivation
from modules.user.model import User

def main():
    connect_to_db()
    q = SlotActivation.objects(program='binary', slot_no=10, status='completed').order_by('-created_at').first()
    if not q:
        print('No user found with binary slot 10 completed')
        return
    u = User.objects(id=q.user_id).first()
    print({
        'user_id': str(q.user_id),
        'uid': getattr(u, 'uid', None),
        'wallet_address': getattr(u, 'wallet_address', None),
        'activated_at': getattr(q, 'activated_at', None),
    })

if __name__ == '__main__':
    main()
