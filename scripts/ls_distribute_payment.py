import sys
import json
from bson import ObjectId

from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.db import connect_to_db
from modules.leadership_stipend.service import LeadershipStipendService


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ls_distribute_payment.py <PAYMENT_ID>")
        sys.exit(1)

    payment_id = sys.argv[1]

    connect_to_db()
    svc = LeadershipStipendService()
    res = svc.distribute_stipend_payment(payment_id)
    print(json.dumps({"distribution": res}, default=str, indent=2))


if __name__ == '__main__':
    main()


