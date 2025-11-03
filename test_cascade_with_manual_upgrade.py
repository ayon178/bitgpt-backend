#!/usr/bin/env python3
"""
Test Cascade Auto-Upgrade with Manual Upgrade API
Creates controlled tree structure and uses /binary/manual-upgrade API to trigger cascades
"""

import sys
import os
import time
import secrets
import requests
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from bson import ObjectId
from mongoengine import connect

BASE_URL = "http://localhost:8000"
MONGODB_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"
ROOT_REFER_CODE = "ROOT"
REQUEST_TIMEOUT = 120
WAIT = 70

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
from modules.wallet.model import ReserveLedger
from modules.slot.model import SlotActivation
from modules.auto_upgrade.service import AutoUpgradeService
from modules.wallet.service import WalletService


def create_user(name: str, refer_code: str) -> Optional[str]:
    payload = {
        "email": f"{name.lower()}_{int(time.time()*1000)}@test.com",
        "name": name,
        "refered_by": refer_code,
        "wallet_address": f"0x{secrets.token_hex(20)}",
    }
    for attempt in range(3):
        try:
            r = requests.post(f"{BASE_URL}/user/temp-create", json=payload, timeout=REQUEST_TIMEOUT)
            j = r.json()
            if r.status_code in (200, 201) and j.get("status") == "Ok":
                code = (j.get("data", {}) or {}).get("refer_code") or (j.get("data", {}).get("user") or {}).get("refer_code")
                print(f"    ✅ Created {name}: {code}")
                print(f"    ⏳ Waiting {WAIT}s for background tasks...")
                time.sleep(WAIT)
                return code
            else:
                print(f"    ⚠️ Create fail attempt {attempt+1}: {j}")
                time.sleep(10)
        except Exception as e:
            print(f"    ⚠️ Error attempt {attempt+1}: {e}")
            time.sleep(10)
    return None


def get_reserve(user_id: ObjectId, slot_no: int) -> Decimal:
    total = Decimal('0')
    for e in ReserveLedger.objects(user_id=user_id, program='binary', slot_no=slot_no):
        if e.direction == 'credit':
            total += e.amount
        elif e.direction == 'debit':
            total -= e.amount
    return total


def manual_upgrade_via_service(user_id: str, slot_no: int) -> dict:
    """Use service directly (simulates API call)"""
    aus = AutoUpgradeService()
    result = aus.manual_upgrade_binary_slot(
        user_id=user_id,
        slot_no=slot_no,
        tx_hash=f"test_cascade_{user_id}_{slot_no}_{int(time.time())}"
    )
    return result


def check_activations(user_id: ObjectId) -> list:
    return [a.slot_no for a in SlotActivation.objects(user_id=user_id, program='binary', status='completed').order_by('slot_no')]


def print_status(user: User, label: str = ""):
    acts = check_activations(user.id)
    print(f"\n{label} {user.refer_code} ({str(user.id)})")
    print(f"  Activated slots: {acts}")
    for s in [3, 4, 5, 6]:
        reserve = get_reserve(user.id, s)
        if reserve > 0 or s <= 4:
            print(f"  Reserve for slot {s}: {reserve} BNB")


def main():
    print("="*100)
    print("Test Cascade Auto-Upgrade with Manual Upgrade")
    print("="*100)
    
    # Create controlled tree: ROOT -> A -> B -> C -> D
    print("\n📦 Step 1: Creating controlled cascade tree structure")
    a_code = create_user("CASCADE_A", ROOT_REFER_CODE)
    if not a_code:
        print("❌ Failed creating A")
        return
    
    b_code = create_user("CASCADE_B", a_code)
    if not b_code:
        print("❌ Failed creating B")
        return
    
    c_code = create_user("CASCADE_C", b_code)
    if not c_code:
        print("❌ Failed creating C")
        return
    
    d_code = create_user("CASCADE_D", c_code)
    if not d_code:
        print("❌ Failed creating D")
        return
    
    # Get users
    root = User.objects(refer_code=ROOT_REFER_CODE).first()
    a = User.objects(refer_code=a_code).first()
    b = User.objects(refer_code=b_code).first()
    c = User.objects(refer_code=c_code).first()
    d = User.objects(refer_code=d_code).first()
    
    if not all([root, a, b, c, d]):
        print("❌ Failed to retrieve all users")
        return
    
    print("\n📊 Step 2: Initial status")
    print_status(root, "ROOT:")
    print_status(a, "A:")
    print_status(b, "B:")
    print_status(c, "C:")
    print_status(d, "D:")
    
    # Fund D's wallet for manual upgrade
    ws = WalletService()
    ws.credit_main_wallet(
        user_id=str(d.id),
        amount=Decimal('0.02'),
        currency='BNB',
        reason='cascade_test_fund',
        tx_hash=f"cascade_fund_d_{int(time.time())}"
    )
    print(f"\n💳 Funded D's wallet with 0.02 BNB")
    
    # Step 3: Manual upgrade D to Slot 4
    # Expected: D's Slot 4 cost routes to 4th upline (ROOT) for Slot 5 reserve
    # Then if ROOT has enough reserve, ROOT's Slot 5 auto-upgrades
    # Then ROOT's Slot 5 cost routes to ROOT's upline (if any) for Slot 6 reserve
    print(f"\n🚀 Step 3: Manually upgrading D to Slot 4 (should cascade to 4th upline's Slot 5 reserve)")
    result = manual_upgrade_via_service(str(d.id), 4)
    
    if not result.get('success'):
        print(f"❌ Manual upgrade failed: {result.get('error')}")
        return
    
    print(f"✅ D upgraded to Slot 4: {result.get('slot_name')}")
    print(f"   Amount paid: {result.get('amount_paid')} BNB")
    
    # Wait a bit for cascades
    print("\n⏳ Waiting 10s for cascades to settle...")
    time.sleep(10)
    
    # Step 4: Find D's 4th upline and check cascades
    print("\n📊 Step 4: Finding D's 4th upline and checking cascade results")
    aus = AutoUpgradeService()
    d_4th_upline = aus._get_nth_upline_by_slot(ObjectId(d.id), 4, 4)
    if d_4th_upline:
        upline_user = User.objects(id=d_4th_upline).first()
        upline_name = upline_user.refer_code if upline_user else str(d_4th_upline)
        print(f"  D's 4th upline: {upline_name} ({str(d_4th_upline)})")
        print_status(upline_user, f"  4th upline ({upline_name}):") if upline_user else None
    
    print_status(root, "ROOT:")
    print_status(a, "A:")
    print_status(d, "D:")
    
    # Check if 4th upline's Slot 5 auto-upgraded (cascade 1)
    if d_4th_upline:
        upline_slot5 = SlotActivation.objects(user_id=d_4th_upline, program='binary', slot_no=5, status='completed').first()
        upline_reserve5 = get_reserve(d_4th_upline, 5)
        if upline_slot5:
            print(f"\n✅ CASCADE 1 SUCCESS: 4th upline's Slot 5 auto-upgraded!")
        else:
            print(f"\n⚠️ CASCADE 1: 4th upline's Slot 5 not yet upgraded. Reserve: {upline_reserve5} BNB (need 0.0352)")
            # Check if enough reserve for next payment
            if upline_reserve5 >= Decimal('0.0352'):
                print(f"   🔄 Reserve sufficient! Triggering auto-upgrade check...")
                check_result = aus._check_binary_auto_upgrade_from_reserve(d_4th_upline, 5)
                print(f"   Result: {check_result}")
    
    # Re-check auto-upgrade eligibility for all uplines
    print("\n🔍 Step 5: Re-checking auto-upgrade eligibility for all uplines")
    if d_4th_upline:
        check_u5 = aus._check_binary_auto_upgrade_from_reserve(d_4th_upline, 5)
        print(f"4th upline Slot 5: {check_u5}")
    
    # Check if cascades continue (infinite chain)
    print("\n🔗 Step 6: Checking for infinite cascade chain continuation...")
    if d_4th_upline:
        # Check if 4th upline's Slot 5 cost routed to its upline's Slot 6 reserve
        upline_5th_upline = aus._get_nth_upline_by_slot(d_4th_upline, 5, 5) if d_4th_upline else None
        if upline_5th_upline:
            upline_5th_user = User.objects(id=upline_5th_upline).first()
            if upline_5th_user:
                print(f"  4th upline's 5th upline: {upline_5th_user.refer_code}")
                reserve_6 = get_reserve(upline_5th_upline, 6)
                print(f"  Reserve for Slot 6: {reserve_6} BNB (need 0.0704)")
                if reserve_6 >= Decimal('0.0704'):
                    check_r6 = aus._check_binary_auto_upgrade_from_reserve(upline_5th_upline, 6)
                    print(f"  Slot 6 check: {check_r6}")
                    if check_r6.get('auto_upgrade_triggered'):
                        print(f"  ✅ CASCADE 2 SUCCESS: Infinite chain continues!")
    
    print("\n" + "="*100)
    print("✅ Cascade test completed!")
    print("="*100)


if __name__ == "__main__":
    main()

