#!/usr/bin/env python3
import os, sys, time, secrets, requests
from decimal import Decimal
from typing import Optional
from bson import ObjectId
from mongoengine import connect

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

BASE_URL = "http://localhost:8000"
MONGODB_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"
REQUEST_TIMEOUT = 120
WAIT = 70
ROOT_REFER_CODE = "ROOT"

try:
    connect(host=MONGODB_URI)
    print("Connected to MongoDB")
except Exception as e:
    from core.config import MONGO_URI
    connect(db="bitgpt", host=MONGO_URI)
    print("Connected to MongoDB (config)")

from modules.user.model import User
from modules.wallet.model import ReserveLedger
from modules.slot.model import SlotActivation
from modules.wallet.service import WalletService
from modules.auto_upgrade.service import AutoUpgradeService


def create(name: str, refer_code: str) -> Optional[str]:
    for attempt in range(3):
        try:
            # Generate unique wallet each attempt
            payload = {
                "email": f"{name.lower()}_{int(time.time()*1000)}_{attempt}@test.com",
                "name": name,
                "refered_by": refer_code,
                "wallet_address": f"0x{secrets.token_hex(20)}"
            }
            r = requests.post(f"{BASE_URL}/user/temp-create", json=payload, timeout=REQUEST_TIMEOUT)
            j = r.json()
            if r.status_code in (200, 201) and j.get("status") == "Ok":
                code = j.get("data", {}).get("refer_code") or (j.get("data", {}).get("user") or {}).get("refer_code")
                print(f"  ✅ {name}: {code}")
                print(f"  ⏳ Waiting {WAIT}s for background tasks...")
                time.sleep(WAIT)
                return code
            else:
                print(f"  ⚠️ Attempt {attempt+1} failed: {j}")
                time.sleep(10)
        except Exception as e:
            print(f"  ⚠️ Error attempt {attempt+1}: {e}")
            time.sleep(10)
    return None


def reserve(user_id: ObjectId, slot_no: int) -> Decimal:
    total = Decimal('0')
    for e in ReserveLedger.objects(user_id=user_id, program='binary', slot_no=slot_no):
        total += e.amount if e.direction == 'credit' else (-e.amount)
    return total


def ensure_slot2(user_code: str) -> None:
    u = User.objects(refer_code=user_code).first()
    if not u:
        return
    exists = SlotActivation.objects(user_id=u.id, program='binary', slot_no=2, status='completed').first()
    if exists:
        return
    ws = WalletService()
    aus = AutoUpgradeService()
    uid = str(u.id)
    ws.credit_main_wallet(user_id=uid, amount=Decimal('0.005'), currency='BNB', reason='fs_chain_s2', tx_hash=f"fs_s2_{uid}_{int(time.time())}")
    aus.manual_upgrade_binary_slot(user_id=uid, slot_no=2, tx_hash=f"fs_s2_up_{uid}_{int(time.time())}")


def main():
    print("="*100)
    print("Build controlled first/second chain and trigger cascades (Slot 3 → A's Slot 4)")
    print("="*100)

    # ROOT -> A (first child)
    a = create("FS_A", ROOT_REFER_CODE)
    if not a: return
    # Ensure A is the first child: create no other children under ROOT before

    # A -> B (first child)
    b = create("FS_B", a)
    if not b: return

    # B -> C (first child)
    c = create("FS_C", b)
    if not c: return

    # C -> D1 (first), then D2 (second)
    d1 = create("FS_D1", c)
    if not d1: return
    d2 = create("FS_D2", c)
    if not d2: return

    # Make sure D1/D2 have Slot 2 active (if needed by business rules)
    ensure_slot2(d1)
    ensure_slot2(d2)

    aus = AutoUpgradeService()
    ws = WalletService()

    # Manually upgrade D1 and D2 to Slot 3 to route to A's Slot 4 reserve
    for d_code in [d1, d2]:
        u = User.objects(refer_code=d_code).first()
        if not u: continue
        ws.credit_main_wallet(user_id=str(u.id), amount=Decimal('0.01'), currency='BNB', reason='fs_s3', tx_hash=f"fs_s3_topup_{int(time.time())}")
        print(f"🚀 Upgrading {d_code} to Slot 3...")
        res = aus.manual_upgrade_binary_slot(user_id=str(u.id), slot_no=3, tx_hash=f"fs_s3_up_{int(time.time())}")
        print(f"   Result: {res}")
        time.sleep(2)

    # Verify A's Slot 4 auto-upgrade
    a_user = User.objects(refer_code=a).first()
    a_slot4 = SlotActivation.objects(user_id=a_user.id, program='binary', slot_no=4, status='completed').first()
    a_res4 = reserve(a_user.id, 4)
    print("\n=== Step 2: A's Slot 4 Status ===")
    print(f"A ({a}) reserve for Slot 4: {a_res4} BNB (need 0.0176)")
    print(f"A Slot 4 activated: {'YES' if a_slot4 else 'NO'}")

    if not a_slot4:
        print("❌ A's Slot 4 not activated yet. Cannot proceed to Slot 5.")
        return

    # Step 3: Create parallel branch for level 4 users under A
    # B -> C2 (second child), then C2 -> D3/D4 (first/second at level 4 under A)
    print("\n=== Step 3: Creating parallel branch C2->D3/D4 at level 4 under A ===")
    c2 = create("FS_C2", b)
    if not c2: return
    
    d3 = create("FS_D3", c2)
    if not d3: return
    d4 = create("FS_D4", c2)
    if not d4: return

    # Ensure D3/D4 have Slot 2 and 3 active before upgrading to Slot 4
    for d_code in [d3, d4]:
        ensure_slot2(d_code)
        u = User.objects(refer_code=d_code).first()
        if not u: continue
        # Check if Slot 3 needed
        slot3 = SlotActivation.objects(user_id=u.id, program='binary', slot_no=3, status='completed').first()
        if not slot3:
            ws.credit_main_wallet(user_id=str(u.id), amount=Decimal('0.01'), currency='BNB', reason='fs_s3_for_s4', tx_hash=f"fs_s3_{int(time.time())}")
            aus.manual_upgrade_binary_slot(user_id=str(u.id), slot_no=3, tx_hash=f"fs_s3_{int(time.time())}")
            time.sleep(2)

    # Step 4: Manually upgrade D3 and D4 to Slot 4 to route to A's Slot 5 reserve
    print("\n=== Step 4: Upgrading D3/D4 to Slot 4 (should route to A's Slot 5) ===")
    for d_code in [d3, d4]:
        u = User.objects(refer_code=d_code).first()
        if not u: continue
        ws.credit_main_wallet(user_id=str(u.id), amount=Decimal('0.02'), currency='BNB', reason='fs_s4', tx_hash=f"fs_s4_topup_{int(time.time())}")
        print(f"🚀 Upgrading {d_code} to Slot 4...")
        res = aus.manual_upgrade_binary_slot(user_id=str(u.id), slot_no=4, tx_hash=f"fs_s4_up_{int(time.time())}")
        print(f"   Result: {res}")
        time.sleep(2)

    # Step 5: Verify A's Slot 5 auto-upgrade
    print("\n=== Step 5: Verification ===")
    time.sleep(5)  # Wait for cascades to settle
    a_slot5 = SlotActivation.objects(user_id=a_user.id, program='binary', slot_no=5, status='completed').first()
    a_res5 = reserve(a_user.id, 5)
    print(f"A ({a}) reserve for Slot 5: {a_res5} BNB (need 0.0352)")
    print(f"A Slot 5 activated: {'YES ✅' if a_slot5 else 'NO ⚠️'}")

    if a_slot5:
        print("\n🎉 SUCCESS! A's Slot 5 auto-upgraded via infinite cascade chain!")
        print("   D1/D2 Slot 3 → A's Slot 4 → E1/E2 Slot 4 → A's Slot 5")
    else:
        print("\n⚠️ A's Slot 5 not yet activated. Checking why...")
        aus_check = AutoUpgradeService()
        check_result = aus_check._check_binary_auto_upgrade_from_reserve(a_user.id, 5)
        print(f"   Auto-upgrade check: {check_result}")

    print("\nDone.")

if __name__ == "__main__":
    main()
