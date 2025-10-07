import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.db import connect_to_db
from modules.royal_captain.model import RoyalCaptainBonusPayment, RoyalCaptain
from bson import ObjectId


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/clear_royal_captain_payments.py <USER_ID>")
        return
    user_id = ObjectId(sys.argv[1])
    connect_to_db()
    
    # Clear payments
    count = RoyalCaptainBonusPayment.objects(user_id=user_id).delete()
    print(f"Deleted {count} payments")
    
    # Reset achieved flags on bonuses
    rc = RoyalCaptain.objects(user_id=user_id).first()
    if rc:
        for b in rc.bonuses:
            b.is_achieved = False
            b.achieved_at = None
        rc.save()
        print("Reset bonus achieved flags")


if __name__ == '__main__':
    main()

