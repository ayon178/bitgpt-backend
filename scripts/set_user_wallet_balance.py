import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.db import connect_to_db
from modules.user.model import User


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/set_user_wallet_balance.py <USER_ID> <AMOUNT>")
        return
    user_id = sys.argv[1]
    amount = float(sys.argv[2])

    connect_to_db()
    user = User.objects(id=user_id).first()
    if not user:
        print("User not found")
        return
    user.wallet_balance = amount
    user.save()
    print({"user_id": str(user.id), "wallet_balance": getattr(user, 'wallet_balance', None)})


if __name__ == '__main__':
    main()


