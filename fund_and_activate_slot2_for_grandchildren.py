#!/usr/bin/env python3
import sys
import os
from decimal import Decimal
from bson import ObjectId
from datetime import datetime

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

MONGODB_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

try:
    from mongoengine import connect
    try:
        connect(host=MONGODB_URI)
        print("✅ Connected to MongoDB")
    except Exception as e1:
        from core.config import MONGO_URI
        connect(db="bitgpt", host=MONGO_URI)
        print("✅ Connected to MongoDB (config)")
except Exception as e:
    print(f"❌ MongoDB connection setup failed: {e}")
    sys.exit(1)

from modules.user.model import User
from modules.wallet.service import WalletService
from modules.auto_upgrade.service import AutoUpgradeService

# Grandchildren refer codes created in the last step
GCODES = [
    "RC1762182774570153",  # MC_G1
    "RC1762182916905364",  # MC_G2
]

TOP_UP_BNB = Decimal('0.005')  # enough for Slot 2 (0.0044)
TARGET_SLOT = 2

def upgrade_to_slot2(user: User):
    ws = WalletService()
    aus = AutoUpgradeService()

    uid = str(user.id)
    # Top-up wallet
    ws.credit_main_wallet(
        user_id=uid,
        amount=TOP_UP_BNB,
        currency='BNB',
        reason='test_topup_for_slot2',
        tx_hash=f"topup_slot2_{uid}_{int(datetime.utcnow().timestamp())}"
    )
    print(f"  💳 Credited {TOP_UP_BNB} BNB to {user.refer_code}")

    # Perform manual upgrade to slot 2
    res = aus.manual_upgrade_binary_slot(
        user_id=uid,
        slot_no=TARGET_SLOT,
        tx_hash=f"manual_upgrade_s2_{uid}_{int(datetime.utcnow().timestamp())}"
    )
    if not res.get('success'):
        print(f"  ❌ Failed to upgrade {user.refer_code} to Slot 2: {res.get('error')}")
        return False
    print(f"  ✅ Upgraded {user.refer_code} to Slot 2. Paid: {res.get('amount_paid')} BNB, reserve_used={res.get('reserve_used', 0)}, wallet_used={res.get('wallet_used', 0)}")
    return True


def main():
    print("="*100)
    print("Funding grandchildren and activating Slot 2 to route reserve to target's Slot 3")
    print("="*100)

    for code in GCODES:
        user = User.objects(refer_code=code).first()
        if not user:
            print(f"❌ User not found for refer code {code}")
            continue
        print(f"\n🎯 Processing {code} ({user.id})")
        upgrade_to_slot2(user)

    print("\nNext: run `python trigger_compact_auto_checks.py` and then `python verify_slot6_auto_upgrade.py`.")

if __name__ == "__main__":
    main()
