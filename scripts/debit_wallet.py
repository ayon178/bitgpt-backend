import sys
from pathlib import Path
from decimal import Decimal
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.db import connect_to_db
from modules.wallet.service import WalletService


def main():
    if len(sys.argv) < 4:
        print("Usage: python scripts/debit_wallet.py <USER_ID> <AMOUNT> <CURRENCY>")
        return
    user_id = sys.argv[1]
    amount = Decimal(sys.argv[2])
    currency = sys.argv[3].upper()
    connect_to_db()
    svc = WalletService()
    res = svc.debit_main_wallet(user_id, amount, currency, 'matrix_manual_upgrade', f'DEBIT-{currency}-{amount}')
    print(res)


if __name__ == '__main__':
    main()


