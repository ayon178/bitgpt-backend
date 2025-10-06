import os
import sys
import json
import time
from datetime import datetime

import requests

BASE = "http://127.0.0.1:8000"


def post(path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.post(f"{BASE}{path}", data=json.dumps(data or {}), headers=headers)
    return resp.status_code, resp.json()


def get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(f"{BASE}{path}", headers=headers)
    return resp.status_code, resp.json()


def login(wallet):
    code, data = post("/auth/login", {"wallet_address": wallet})
    assert code == 200 and data.get("success"), f"login failed: {data}"
    return data["data"]["token"]["access_token"], data["data"].get("user")


def ensure_root():
    """Ensure ROOT exists; return its user_id."""
    wallet = "0x0000000000000000000000000000000000000001"
    payload = {
        "uid": "ROOT",
        "refer_code": "ROOT001",
        "wallet_address": wallet,
        "name": "Root User"
    }
    code, data = post("/user/create-root", payload)
    if data.get("success") and data.get("data") and data["data"].get("_id"):
        return data["data"]["_id"]
    # If already exists, try to fetch by login
    code2, login_data = post("/auth/login", {"wallet_address": wallet})
    if code2 == 200 and login_data.get("success"):
        return login_data["data"]["user"]["_id"]
    # Fallback: return None and let caller provide upline
    return None


def create_user(uid, refer_code, wallet, upline_id):
    payload = {
        "uid": uid,
        "refer_code": refer_code,
        "wallet_address": wallet,
        "name": uid,
        # map to refered_by per backend requirement, and mandatory binary tx
        "refered_by": upline_id,
        "binary_payment_tx": f"JOIN-{uid}-{int(time.time())}",
        "network": "BSC"
    }
    code, data = post("/user/create", payload)
    assert code in (200, 201) and data.get("success"), f"create_user failed: {data}"
    return data["data"]["_id"]


def get_slot_price(slot_no, token):
    code, data = get("/binary/slot-catalog", token=token)
    assert code == 200 and data.get("success"), data
    for c in data["data"]["slots"]:
        if c["slot_no"] == slot_no:
            return c["slot_value"]
    raise RuntimeError("slot price not found")


def upgrade_slot10(user_id, token):
    price = get_slot_price(10, token)
    body = {
        "user_id": user_id,
        "slot_no": 10,
        "tx_hash": f"TEST-{user_id[:6]}-S10-{int(time.time())}",
        "amount": price
    }
    code, data = post("/binary/upgrade", body, token=token)
    assert code == 200 and data.get("success"), f"upgrade failed: {data}"
    return data


def stipend_income(user_id):
    code, data = get(f"/user/income/leadership-stipend?user_id={user_id}&currency=BNB")
    assert code == 200 and data.get("success"), data
    return data["data"]


def claim_and_distribute(user_id):
    # Omit amount to auto-claim remaining per business rule
    code, data = post("/leadership-stipend/claim", {"user_id": user_id, "slot_number": 10})
    assert code == 200 and data.get("success"), f"claim failed: {data}"
    payment_id = data["data"]["payment_id"]
    code2, data2 = post(f"/leadership-stipend/claim/{payment_id}/distribute")
    assert code2 == 200 and data2.get("success"), f"distribute failed: {data2}"
    return data2


def main():
    # Accept upline_id from argv or env UPLINE_ID; if none, ensure root
    upline_id = None
    if len(sys.argv) > 1:
        upline_id = sys.argv[1]
    if not upline_id:
        upline_id = os.environ.get('UPLINE_ID')
    if not upline_id:
        print("Ensuring root...")
        upline_id = ensure_root()
    assert upline_id, "upline_id is required"

    # Create two users under provided upline
    print("Creating users under upline:", upline_id)
    suffix = str(int(time.time()))
    uid1 = f"userLS1_{suffix}"
    uid2 = f"userLS2_{suffix}"
    w1 = "0x000000000000000000000000000000000000" + str(5000 + int(suffix[-3:]) % 4000)
    w2 = "0x000000000000000000000000000000000000" + str(6000 + int(suffix[-3:]) % 3000)
    user1_id = create_user(uid1, f"LS{suffix[-3:]}1", w1, upline_id=upline_id)
    user2_id = create_user(uid2, f"LS{suffix[-3:]}2", w2, upline_id=upline_id)

    print("Login users...")
    token1, _ = login(w1)
    token2, _ = login(w2)

    print("Upgrade slot 10 for both users...")
    upgrade_slot10(user1_id, token1)
    upgrade_slot10(user2_id, token2)

    print("Check stipend income before claim...")
    inc1 = stipend_income(user1_id)
    inc2 = stipend_income(user2_id)
    print(json.dumps({"user1": inc1, "user2": inc2}, default=str, indent=2))

    # Per your rule: for 2 users, each claims 1.1264 (half of 2.2528)
    print("Create and distribute claims...")
    dist1 = claim_and_distribute(user1_id)
    dist2 = claim_and_distribute(user2_id)
    print(json.dumps({"dist1": dist1, "dist2": dist2}, default=str, indent=2))

    print("Check stipend income after claim...")
    inc1b = stipend_income(user1_id)
    inc2b = stipend_income(user2_id)
    print(json.dumps({"user1": inc1b, "user2": inc2b}, default=str, indent=2))


if __name__ == "__main__":
    main()


