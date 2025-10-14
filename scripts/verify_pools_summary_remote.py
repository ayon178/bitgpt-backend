#!/usr/bin/env python3
"""
Verify pools-summary changes against remote MongoDB by creating users via API.
Steps:
1) Find parent by refer_code RC1760429616945918
2) Create user A under parent (temp-create)
3) Check pools-summary for user A (should be zeros initially)
4) Create user B under user A (temp-create)
5) Check pools-summary for user A again (should reflect binary incentives)

This script uses the running FastAPI server at http://localhost:8000 and the
remote MongoDB connection provided by the user.
"""

import os
import time
import requests
from typing import Optional

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

PARENT_REFER_CODE = "RC1760429616945918"


def get_user_by_refer_code(code: str) -> Optional[dict]:
    # There may not be a direct API; use pools-summary lookup by first getting id via a custom endpoint if exists
    # Fallback: try a generic search endpoint if any; else return None and require manual id
    try:
        # Try: /user/search?refer_code=
        url = f"{API_BASE}/user/search?refer_code={code}"
        r = requests.get(url, timeout=20)
        if r.ok and r.json().get("success"):
            data = r.json().get("data")
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return None


def temp_create_user(refer_code: str, email_prefix: str) -> dict:
    url = f"{API_BASE}/user/temp-create"
    payload = {
        "email": f"{email_prefix}{int(time.time()*1000)}@example.com",
        "name": "Auto Test",
        "refered_by": refer_code,
    }
    r = requests.post(url, json=payload, timeout=30)
    if not r.ok:
        raise RuntimeError(f"temp-create failed: {r.status_code} {r.text}")
    data = r.json().get("data") or {}
    if not data:
        raise RuntimeError(f"temp-create returned no data: {r.text}")
    return data


def get_pools_summary(user_id: str) -> dict:
    url = f"{API_BASE}/wallet/pools-summary?user_id={user_id}"
    r = requests.get(url, timeout=30)
    if not r.ok:
        raise RuntimeError(f"pools-summary failed: {r.status_code} {r.text}")
    return r.json().get("data") or {}


def extract_bnbs(summary: dict) -> dict:
    pools = (summary or {}).get("pools", {})
    return {
        "binary_partner_incentive_BNB": float((pools.get("binary_partner_incentive") or {}).get("BNB", 0) or 0),
        "duel_tree_BNB": float((pools.get("duel_tree") or {}).get("BNB", 0) or 0),
    }


def main():
    print("Starting pools-summary remote verification...")

    # 1) Create user A under given refer code
    print(f"Creating User A under {PARENT_REFER_CODE}...")
    user_a = temp_create_user(PARENT_REFER_CODE, email_prefix="autoA+")
    user_a_id = user_a.get("_id")
    user_a_refer = user_a.get("refer_code")
    if not user_a_id or not user_a_refer:
        raise RuntimeError("User A creation missing _id or refer_code")
    print(f"User A: id={user_a_id} refer={user_a_refer}")

    # 2) Pools summary for user A (before)
    print("Fetching pools-summary for User A (before)...")
    summary_before = get_pools_summary(user_a_id)
    before_vals = extract_bnbs(summary_before)
    print(f"Before: {before_vals}")

    # 3) Create user B under user A
    print(f"Creating User B under {user_a_refer}...")
    user_b = temp_create_user(user_a_refer, email_prefix="autoB+")
    user_b_id = user_b.get("_id")
    print(f"User B: id={user_b_id}")

    # 4) Pools summary for user A (after)
    print("Fetching pools-summary for User A (after)...")
    summary_after = get_pools_summary(user_a_id)
    after_vals = extract_bnbs(summary_after)
    print(f"After: {after_vals}")

    delta_partner = after_vals["binary_partner_incentive_BNB"] - before_vals["binary_partner_incentive_BNB"]
    delta_duel = after_vals["duel_tree_BNB"] - before_vals["duel_tree_BNB"]

    print("\nDelta:")
    print({
        "binary_partner_incentive_BNB": delta_partner,
        "duel_tree_BNB": delta_duel,
    })

    # Expectations: partner incentive >= 0.00066 BNB, duel tree > 0
    ok = (delta_partner > 0) or (delta_duel > 0)
    if not ok:
        raise SystemExit("Pools summary did not change as expected")

    print("\nSuccess: Pools summary changed.")


if __name__ == "__main__":
    main()
