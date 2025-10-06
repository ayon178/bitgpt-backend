import sys
import json
from datetime import datetime
from bson import ObjectId
from decimal import Decimal

from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.db import connect_to_db
from modules.leadership_stipend.model import LeadershipStipend, LeadershipStipendFund, LeadershipStipendPayment
from modules.leadership_stipend.service import LeadershipStipendService


def ensure_stipend_fund(min_available: float = 100.0) -> LeadershipStipendFund:
    fund = LeadershipStipendFund.objects(is_active=True).first()
    if not fund:
        fund = LeadershipStipendFund(
            total_fund_amount=min_available,
            available_amount=min_available,
            distributed_amount=0.0,
            currency="BNB",
            is_active=True,
        )
        fund.save()
    return fund


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ls_claim_one.py <USER_ID>")
        sys.exit(1)

    user_id_str = sys.argv[1]
    user_id = ObjectId(user_id_str)

    connect_to_db()
    ensure_stipend_fund(100.0)

    svc = LeadershipStipendService()

    # Ensure LS record exists
    ls = LeadershipStipend.objects(user_id=user_id).first()
    if not ls:
        print(json.dumps({"success": False, "error": "Leadership Stipend record not found for user"}))
        sys.exit(2)

    # Refresh eligibility and tier info
    svc.check_eligibility(user_id_str, force_check=True)

    # Create today's pending payment (if capacity remains)
    svc.process_daily_calculation(datetime.utcnow().strftime("%Y-%m-%d"))

    # Find most recent pending payment for this user (any eligible slot 10-16)
    pay = LeadershipStipendPayment.objects(user_id=user_id, payment_status='pending').order_by('-created_at').first()
    if not pay:
        print(json.dumps({"success": False, "error": "No pending stipend payment found for user"}))
        sys.exit(3)

    # Distribute
    res = svc.distribute_stipend_payment(str(pay.id))
    print(json.dumps({"claim": res}, default=str, indent=2))


if __name__ == '__main__':
    main()


