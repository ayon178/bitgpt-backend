"""
Integration test: Matrix fund distribution flow
Creates users via /user/temp-create and joins them to Matrix via /matrix/join.
Prints responses to verify placement and distribution hooks executed.
"""

import requests
import time
import secrets
import os

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def generate_wallet_address() -> str:
    return "0x" + secrets.token_hex(20)


def temp_create_user(refered_by: str = "ROOT"):
    url = f"{BASE_URL}/user/temp-create"
    payload = {
        "refered_by": refered_by,
        "wallet_address": generate_wallet_address(),
    }
    r = requests.post(url, json=payload)
    try:
        data = r.json()
    except Exception:
        print("[temp-create] non-JSON response:", r.text)
        return None
    if r.status_code in (200, 201) and data.get("success"):
        return data["data"]
    print("[temp-create] failed:", data)
    return None


def matrix_join(user_id: str, referrer_id: str, amount: float = 11.0, tx_hash: str = None):
    url = f"{BASE_URL}/matrix/join"
    payload = {
        "user_id": user_id,
        "referrer_id": referrer_id,
        "tx_hash": tx_hash or f"tx_{int(time.time())}",
        "amount": amount,
    }
    r = requests.post(url, json=payload)
    try:
        data = r.json()
    except Exception:
        print("[matrix/join] non-JSON response:", r.text)
        return None
    if r.status_code == 200:
        return data
    print("[matrix/join] failed:", data)
    return None


def main():
    print("=== Matrix Distribution Test ===")

    # 1) Join the provided fresh user (if env vars are set), else skip
    provided_user_id = os.getenv("PROVIDED_USER_ID")
    provided_referrer_id = os.getenv("PROVIDED_REFERRER_ID")
    if provided_user_id and provided_referrer_id:
        print(f"Joining provided user {provided_user_id} under {provided_referrer_id}...")
        res = matrix_join(provided_user_id, provided_referrer_id, amount=11.0, tx_hash="gfdgfgfh565fgd")
        print("join result:", res)
        time.sleep(0.5)

    # 2) Create a few new users and join them under a referrer
    referrer_id = provided_referrer_id or os.getenv("DEFAULT_REFERRER_ID", "ROOT")
    # If referrer is ROOT code, look up its user id via /user/by-code/ROOT
    if referrer_id == "ROOT":
        try:
            r = requests.get(f"{BASE_URL}/user/by-code/ROOT")
            rc = r.json()
            if r.status_code == 200 and rc.get("data", {}).get("_id"):
                referrer_id = rc["data"]["_id"]
        except Exception:
            pass

    created = []
    for i in range(3):  # create and join 3 users for quick verification
        info = temp_create_user("ROOT")
        if not info:
            continue
        uid = info.get("_id")
        print(f"[#{i+1}] created user {uid} → joining matrix under {referrer_id}")
        j = matrix_join(uid, referrer_id, amount=11.0)
        print("  join resp:", j)
        created.append(uid)
        time.sleep(0.5)

    print("=== Done ===")


if __name__ == "__main__":
    main()


