import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.db import connect_to_db
from modules.royal_captain.model import RoyalCaptainFund
from datetime import datetime


def main():
    amount = float(sys.argv[1]) if len(sys.argv) > 1 else 10000.0
    connect_to_db()
    fund = RoyalCaptainFund.objects(is_active=True).first()
    if not fund:
        fund = RoyalCaptainFund(
            total_fund_amount=amount,
            available_amount=amount,
            distributed_amount=0.0,
            currency='USDT',
            is_active=True
        )
    else:
        fund.total_fund_amount += amount
        fund.available_amount += amount
        fund.last_updated = datetime.utcnow()
    fund.save()
    print({"fund_id": str(fund.id), "available_amount": fund.available_amount})


if __name__ == '__main__':
    main()

