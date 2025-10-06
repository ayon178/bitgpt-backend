import sys
import json
from datetime import datetime
from bson import ObjectId

from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.db import connect_to_db
from modules.leadership_stipend.model import LeadershipStipendPayment
from modules.leadership_stipend.service import LeadershipStipendService


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ls_create_pending_claim.py <USER_ID>")
        sys.exit(1)

    user_id_str = sys.argv[1]
    user_id = ObjectId(user_id_str)

    connect_to_db()

    svc = LeadershipStipendService()
    # Create today's pending payment for the user if eligible and capacity remains
    result = svc.process_daily_calculation(datetime.utcnow().strftime("%Y-%m-%d"))
    # Fetch most recent pending payment for this user
    pay = LeadershipStipendPayment.objects(user_id=user_id, payment_status='pending').order_by('-created_at').first()
    if not pay:
        print(json.dumps({"success": False, "error": "No pending created (user may be ineligible or already at cap)"}))
        sys.exit(2)

    print(json.dumps({
        "success": True,
        "payment": {
            "payment_id": str(pay.id),
            "user_id": str(pay.user_id),
            "slot_number": pay.slot_number,
            "tier_name": pay.tier_name,
            "daily_return_amount": pay.daily_return_amount,
            "status": pay.payment_status,
            "created_at": pay.created_at,
        }
    }, default=str, indent=2))


if __name__ == '__main__':
    main()
