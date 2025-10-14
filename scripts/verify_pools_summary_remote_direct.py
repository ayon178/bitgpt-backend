#!/usr/bin/env python3
"""
Direct verification against remote MongoDB using internal services.
- Connect to remote MongoDB via mongoengine
- Create User A under RC1760429616945918 (temp create service)
- Get pools-summary for User A (before)
- Create User B under User A's refer_code
- Get pools-summary for User A (after)
- Print deltas for binary_partner_incentive (BNB) and duel_tree (BNB)
"""

import os
import sys
import time
from typing import Dict

# Ensure backend root on path
ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from mongoengine import connect
from modules.user.service import create_temp_user_service
from modules.user.model import User
from modules.wallet.service import WalletService

REMOTE_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"
)
PARENT_REFER_CODE = "RC1760429616945918"


def connect_remote():
    # If URI includes DB, connect via host only
    connect(host=REMOTE_URI, alias='default')


def create_user_under(refer_code: str, email_prefix: str) -> Dict:
    payload = {
        "email": f"{email_prefix}{int(time.time()*1000)}@example.com",
        "name": "Remote Auto",
        "refered_by": refer_code,
    }
    result, err = create_temp_user_service(payload)
    if err:
        raise RuntimeError(f"create_temp_user_service error: {err}")
    return result


def get_summary_bnb(user_id: str) -> Dict[str, float]:
    svc = WalletService()
    res = svc.get_pools_summary(user_id=user_id)
    if not res.get("success"):
        raise RuntimeError(res.get("error", "pools summary failed"))
    totals = res.get("data") or {}
    # data is already the totals dict keyed by pool names
    def g(pool_key: str) -> float:
        pool = totals.get(pool_key) or {}
        return float(pool.get("BNB", 0) or 0)
    return {
        "binary_partner_incentive_BNB": g("binary_partner_incentive"),
        "duel_tree_BNB": g("duel_tree"),
    }


def main():
    print("Connecting to remote MongoDB...")
    connect_remote()

    # Ensure parent exists
    parent = User.objects(refer_code=PARENT_REFER_CODE).first()
    if not parent:
        raise SystemExit(f"Parent refer_code {PARENT_REFER_CODE} not found in remote DB")

    print(f"Creating User A under {PARENT_REFER_CODE} ...")
    user_a = create_user_under(PARENT_REFER_CODE, "remoteA+")
    user_a_id = user_a.get("_id")
    user_a_refer = user_a.get("refer_code")
    print(f"User A: id={user_a_id} refer={user_a_refer}")

    print("Fetching pools-summary BEFORE for User A ...")
    before = get_summary_bnb(user_id=user_a_id)
    print(f"Before: {before}")

    print(f"Creating User B under {user_a_refer} ...")
    user_b = create_user_under(user_a_refer, "remoteB+")
    print(f"User B: id={user_b.get('_id')}")

    print("Fetching pools-summary AFTER for User A ...")
    after = get_summary_bnb(user_id=user_a_id)
    print(f"After: {after}")

    delta = {
        k: after[k] - before[k] for k in after.keys()
    }
    print("Delta:", delta)

    # Consider success if either partner incentive or duel tree increased
    if delta["binary_partner_incentive_BNB"] > 0 or delta["duel_tree_BNB"] > 0:
        print("SUCCESS: Pools summary changed for User A")
    else:
        raise SystemExit("FAIL: Pools summary did not change for User A")


if __name__ == "__main__":
    main()
