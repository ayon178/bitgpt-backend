#!/usr/bin/env python3
"""
Trigger compact auto-upgrade checks for target user (slots 4 → 6)
- Checks reserve balances and calls _check_binary_auto_upgrade_from_reserve
- Runs multiple passes to allow cascades to settle
"""

import sys
import os
import time
from bson import ObjectId
from decimal import Decimal

# Add backend path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Mongo connection
MONGODB_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

from mongoengine import connect
connect(host=MONGODB_URI)

from modules.user.model import User
from modules.slot.model import SlotActivation
from modules.wallet.model import ReserveLedger
from modules.auto_upgrade.service import AutoUpgradeService

TARGET_REFER_CODE = "RC1762150704576515"


def get_target_user():
    user = User.objects(refer_code=TARGET_REFER_CODE).first()
    if not user:
        raise RuntimeError(f"Target user not found: {TARGET_REFER_CODE}")
    return user


def reserve_for(user_id: ObjectId, slot_no: int) -> Decimal:
    total = Decimal('0')
    for e in ReserveLedger.objects(user_id=user_id, program='binary', slot_no=slot_no):
        if e.direction == 'credit':
            total += e.amount
        elif e.direction == 'debit':
            total -= e.amount
    return total


def print_status(user):
    acts = SlotActivation.objects(user_id=user.id, program='binary', status='completed').order_by('slot_no')
    active = [a.slot_no for a in acts]
    print("\n=== STATUS ===")
    print(f"Activated slots: {active}")
    for s in [4, 5, 6]:
        print(f"Reserve for slot {s}: {reserve_for(user.id, s)} BNB")


def main():
    user = get_target_user()
    svc = AutoUpgradeService()

    print(f"Target: {user.refer_code} ({str(user.id)})")
    print_status(user)

    # Try a few passes to nudge cascades
    for pass_no in range(1, 4):
        print(f"\n--- PASS {pass_no} ---")
        for slot_no in [4, 5, 6]:
            try:
                res = svc._check_binary_auto_upgrade_from_reserve(ObjectId(user.id), slot_no)
                print(f"Check slot {slot_no}: {res}")
            except Exception as e:
                print(f"Error checking slot {slot_no}: {e}")
        # small wait between passes
        time.sleep(5)
        print_status(user)

    print("\nDone. Run verify script to confirm.")


if __name__ == "__main__":
    main()
