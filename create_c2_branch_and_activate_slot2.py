#!/usr/bin/env python3
import sys
import os
import time
import secrets
import requests
from datetime import datetime
from decimal import Decimal
from typing import Tuple, Optional

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from bson import ObjectId
from mongoengine import connect

BASE_URL = "http://localhost:8000"
MONGODB_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"
TARGET_REFER_CODE = "RC1762150704576515"
REQUEST_TIMEOUT = 120
WAIT = 70
TOP_UP_BNB = Decimal('0.005')

# DB connect (for wallet credit + manual upgrade)
try:
    connect(host=MONGODB_URI)
    print("✅ Connected to MongoDB")
except Exception as e1:
    try:
        from core.config import MONGO_URI
        connect(db="bitgpt", host=MONGO_URI)
        print("✅ Connected to MongoDB (config)")
    except Exception as e2:
        print(f"❌ MongoDB connection failed: {e2}")
        sys.exit(1)

from modules.user.model import User
from modules.wallet.service import WalletService
from modules.auto_upgrade.service import AutoUpgradeService


def create_user(name: str, refer_code: str, email: str = None) -> Tuple[Optional[str], Optional[str]]:
    if email is None:
        email = f"{name.lower()}_{int(time.time()*1000)}@test.com"
    payload_base = {
        "email": email,
        "name": name,
        "refered_by": refer_code,
    }
    print(f"  Creating {name} under {refer_code}...")
    for attempt in range(3):
        try:
            # Fresh wallet each attempt to avoid duplicate constraint
            payload = dict(payload_base)
            payload["wallet_address"] = f"0x{secrets.token_hex(20)}"
            r = requests.post(f"{BASE_URL}/user/temp-create", json=payload, timeout=REQUEST_TIMEOUT)
            j = r.json()
            if r.status_code in (200, 201) and j.get("status") == "Ok":
                data = j.get("data", {})
                code = data.get("refer_code") or (data.get("user") or {}).get("refer_code")
                uid = data.get("_id") or (data.get("user") or {}).get("_id")
                print(f"    ✅ {name}: {code}")
                print(f"    ⏳ Waiting {WAIT}s for background tasks...")
                time.sleep(WAIT)
                return code, uid
            else:
                print(f"    ⚠️ Attempt {attempt+1} failed: {j}")
                if attempt < 2:
                    time.sleep(10)
                    continue
                return None, None
        except Exception as e:
            print(f"    ⚠️ Error: {e}")
            if attempt < 2:
                time.sleep(10)
                continue
            return None, None
    return None, None


def topup_and_upgrade_slot2(refer_code: str) -> bool:
    user = User.objects(refer_code=refer_code).first()
    if not user:
        print(f"❌ User not found for refer code {refer_code}")
        return False

    ws = WalletService()
    aus = AutoUpgradeService()
    uid = str(user.id)

    ws.credit_main_wallet(
        user_id=uid,
        amount=TOP_UP_BNB,
        currency='BNB',
        reason='topup_slot2_c2_branch',
        tx_hash=f"topup_slot2_{uid}_{int(datetime.utcnow().timestamp())}"
    )
    print(f"    💳 Credited {TOP_UP_BNB} BNB to {refer_code}")

    res = aus.manual_upgrade_binary_slot(
        user_id=uid,
        slot_no=2,
        tx_hash=f"manual_upgrade_s2_{uid}_{int(datetime.utcnow().timestamp())}"
    )
    if not res.get('success'):
        print(f"    ❌ Failed to upgrade {refer_code} to Slot 2: {res.get('error')}")
        return False
    print(f"    ✅ Upgraded {refer_code} to Slot 2. Paid: {res.get('amount_paid')} BNB")
    return True


def main():
    print("="*100)
    print("Create C2 branch and activate Slot 2 for first/second grandchildren")
    print("="*100)

    c2_code, _ = create_user("C2", TARGET_REFER_CODE)
    if not c2_code:
        print("❌ Failed creating C2")
        return

    g1_code, _ = create_user("C2_G1", c2_code)
    g2_code, _ = create_user("C2_G2", c2_code)
    if not g1_code or not g2_code:
        print("❌ Failed creating grandchildren under C2")
        return

    print("  Activating Slot 2 for grandchildren to route reserve → Target's Slot 3")
    topup_and_upgrade_slot2(g1_code)
    topup_and_upgrade_slot2(g2_code)

    print("\n✅ Done. Now run:\n  python trigger_compact_auto_checks.py\n  python verify_slot6_auto_upgrade.py")


if __name__ == "__main__":
    main()
