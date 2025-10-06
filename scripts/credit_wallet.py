import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.db import connect_to_db
from modules.wallet.service import WalletService


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/credit_wallet.py <USER_ID> [amount=5000]")
        return
    user_id = sys.argv[1]
    amount = float(sys.argv[2]) if len(sys.argv) > 2 else 5000.0
    connect_to_db()
    svc = WalletService()
    r1 = svc.credit_main_wallet(user_id, amount, 'USDT', 'admin_test_credit', f'TX-ADMIN-USDT-{int(amount)}')
    r2 = svc.credit_main_wallet(user_id, amount, 'BNB', 'admin_test_credit', f'TX-ADMIN-BNB-{int(amount)}')
    print({'USDT': r1, 'BNB': r2})


if __name__ == '__main__':
    main()
