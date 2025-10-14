#!/usr/bin/env python3
import os, sys, time
from mongoengine import connect

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from modules.slot.model import SlotCatalog
from modules.wallet.model import WalletLedger
from modules.income.model import IncomeEvent
from modules.user.model import User
from bson import ObjectId

REMOTE_URI = os.getenv("MONGODB_URI", "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt")

PARENT_REFER = "RC1760429616945918"


def main():
    connect(host=REMOTE_URI, alias='default')

    print("Binary SlotCatalog (program='binary'):")
    for sc in SlotCatalog.objects(program='binary').order_by('slot_no'):
        print(f" - slot_no={sc.slot_no} name={sc.name} price={sc.price} active={sc.is_active}")

    parent = User.objects(refer_code=PARENT_REFER).first()
    print(f"\nParent by refer_code {PARENT_REFER}: id={getattr(parent, 'id', None)}")

    # Find most recent child under parent to use as User A
    user_a = User.objects(refered_by=parent.id).order_by('-created_at').first() if parent else None
    if user_a:
        print(f"User A: id={user_a.id} uid={user_a.uid} refer={user_a.refer_code}")
        # Find most recent child under user A as B
        user_b = User.objects(refered_by=user_a.id).order_by('-created_at').first()
        if user_b:
            print(f"User B: id={user_b.id} uid={user_b.uid} refer={user_b.refer_code}")
        else:
            print("No User B under User A yet")

        print("\nRecent WalletLedger credits for User A:")
        for wl in WalletLedger.objects(user_id=user_a.id, type='credit').order_by('-created_at').limit(10):
            print(f" - {wl.created_at} {wl.amount} {wl.currency} reason={wl.reason}")

        print("\nRecent IncomeEvents for User A:")
        for ev in IncomeEvent.objects(user_id=user_a.id).order_by('-created_at').limit(10):
            print(f" - {ev.created_at} {ev.amount} program={ev.program} type={ev.income_type} from={ev.source_user_id}")
    else:
        print("No User A found under parent")

if __name__ == '__main__':
    main()
