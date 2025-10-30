#!/usr/bin/env python3
"""
Seed Matrix middle-three scenario using existing APIs only.

Flow:
1) Create user A under ROOT (user/temp-create)
2) Join A into Matrix Slot-1 (/matrix/join)
3) Create 14 users under A (user/temp-create) and join them into Matrix Slot-1
4) Print A's auto-upgrade brief status and overall matrix status

Usage:
  python backend/scripts/matrix_seed_middle_upgrade.py [BASE_URL]

Defaults:
  BASE_URL = http://127.0.0.1:8000
  ROOT refer code = "ROOT"
"""

from __future__ import annotations

import sys
import time
import json
import secrets
import requests


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ROOT_REFER_CODE = "ROOT"


REQUEST_TIMEOUT = 300  # seconds


def post(path: str, payload: dict) -> dict:
    url = f"{BASE_URL}{path}"
    r = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    try:
        return r.json()
    except Exception:
        return {"success": False, "error": f"HTTP {r.status_code}", "raw": r.text}


def get(path: str) -> dict:
    url = f"{BASE_URL}{path}"
    r = requests.get(url, timeout=REQUEST_TIMEOUT)
    try:
        return r.json()
    except Exception:
        return {"success": False, "error": f"HTTP {r.status_code}", "raw": r.text}


def temp_create_user(refered_by_code: str, name: str, email: str = None) -> dict:
    payload = {
        "email": email or f"{name.lower()}_{int(time.time()*1000)}@example.test",
        "name": name,
        "wallet_address": "0x" + secrets.token_hex(20),
        "refered_by": refered_by_code,
    }
    return post("/user/temp-create", payload)


def join_matrix(user_id: str, referrer_id: str, amount: float = 11.0) -> dict:
    payload = {
        "user_id": user_id,
        "referrer_id": referrer_id,
        "tx_hash": f"M1-{int(time.time()*1000)}",
        "amount": amount,
    }
    return post("/matrix/join", payload)


def main() -> int:
    print(f"BASE_URL={BASE_URL}")
    print("1) Creating A under ROOT...")
    a_res = temp_create_user(ROOT_REFER_CODE, name="A")
    if not a_res or not a_res.get("data"):
        print("Failed to create A:", json.dumps(a_res, indent=2))
        return 1

    a_id = a_res["data"]["_id"]
    a_ref = a_res["data"]["user"]["refer_code"]
    root_id = str(a_res["data"]["user"]["refered_by"])  # A's upline id is ROOT
    print(f"A_ID={a_id}, A_REFER_CODE={a_ref}, ROOT_ID={root_id}")

    print("2) Joining A into Matrix Slot-1...")
    j_a = join_matrix(a_id, root_id, 11.0)
    print("Join A response:", json.dumps(j_a, indent=2))

    print("3) Creating 14 users under A and joining them into Matrix...")
    child_ids = []
    for i in range(1, 15):
        u_name = f"U{i}"
        c_res = temp_create_user(a_ref, name=u_name)
        if not c_res or not c_res.get("data"):
            print(f"  ❌ Failed to create {u_name}:", json.dumps(c_res, indent=2))
            return 1
        u_id = c_res["data"]["_id"]
        child_ids.append(u_id)
        j_u = join_matrix(u_id, a_id, 11.0)
        if not j_u or not j_u.get("success", True):
            print(f"  ⚠️ Matrix join issue for {u_name}:", json.dumps(j_u, indent=2))

    print(f"Created and joined {len(child_ids)} users.")

    print("4) Checking auto-upgrade brief status for A...")
    brief = get(f"/matrix/auto-upgrade-brief-status/{a_id}")
    print("Auto-upgrade brief:", json.dumps(brief, indent=2))

    print("5) Checking full auto-upgrade status for A (slot_no=1)...")
    status = get(f"/matrix/auto-upgrade-status/{a_id}?slot_no=1")
    print("Auto-upgrade status:", json.dumps(status, indent=2))

    print("6) Matrix status for A...")
    mstat = get(f"/matrix/status/{a_id}")
    print("Matrix status:", json.dumps(mstat, indent=2))

    print("Done. Review whether Slot-2 is active and that middle-three reserve routing occurred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


