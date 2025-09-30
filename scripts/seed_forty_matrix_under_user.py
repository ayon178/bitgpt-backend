import os
import json
import time
from typing import Dict, Any, List
import time as _time

import requests


BASE_URL = os.getenv("BITGPT_BASE_URL", "https://bitgpt-backend.onrender.com")


def post_json(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    resp = requests.post(url, json=payload, timeout=60)
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Non-JSON response from {url}: {resp.status_code} {resp.text}")
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status_code} {url}: {json.dumps(data)}")
    return data


def create_user_under(parent_id: str, idx: int) -> Dict[str, Any]:
    # Ensure uniqueness across re-runs by using a time-based nonce
    nonce = str(_time.time_ns())[-8:]
    uid_prefix = os.getenv("BITGPT_UID_PREFIX", "MX")
    rc_prefix = os.getenv("BITGPT_RC_PREFIX", "RCMX")
    wallet_prefix = os.getenv("BITGPT_WALLET_PREFIX", "0xAUTO")

    uid = f"{uid_prefix}{idx:03d}{nonce}"
    refer_code = f"{rc_prefix}{idx:03d}{nonce}"
    wallet = f"{wallet_prefix}{idx:03d}{nonce}"
    payload = {
        "uid": uid,
        "refer_code": refer_code,
        "upline_id": parent_id,
        "wallet_address": wallet,
        "name": f"{uid} User",
        "role": "user",
        "email": f"{uid.lower()}@bitgpt.local",
        "password": "changeme",
        # Join binary by default as per platform rules
        "binary_payment_tx": f"0xjoin_bin_{idx:03d}",
        # Also flag matrix join intent on creation; router/service may set matrix_joined
        "matrix_payment_tx": f"0xjoin_mx_{idx:03d}",
        "network": "BSC",
    }
    return post_json("/user/create", payload)


def join_matrix(user_id: str, referrer_id: str, idx: int) -> Dict[str, Any]:
    payload = {
        "user_id": user_id,
        "referrer_id": referrer_id,
        "tx_hash": f"0xmx_tx_{idx:03d}",
        "amount": 11.0,
    }
    return post_json("/matrix/join", payload)


def main():
    parent_id = os.getenv("BITGPT_PARENT_ID")
    if not parent_id:
        parent_id = input("Enter parent user _id (ObjectId): ").strip()

    total = int(os.getenv("BITGPT_SEED_COUNT", "40"))
    offset = int(os.getenv("BITGPT_SEED_OFFSET", "0"))

    created: List[Dict[str, Any]] = []
    joined: List[Dict[str, Any]] = []

    # Step 1: Create users under parent
    for i in range(1, total + 1):
        logical_idx = offset + i
        print(f"Creating matrix-user {i}/{total} (idx={logical_idx}) under {parent_id}...")
        try:
            res = create_user_under(parent_id, logical_idx)
            created.append(res)
            print(json.dumps(res, indent=2))
        except Exception as e:
            print(f"Error creating user {i}: {e}")
        time.sleep(0.25)

    # Step 2: Join each created user to matrix
    for i, res in enumerate(created, start=1):
        try:
            data = res.get("data") or {}
            user_id = data.get("_id")
            if not user_id:
                print(f"Skipping matrix join for index {i}: missing user _id")
                continue
            logical_idx = offset + i
            print(f"Joining matrix for user {i}/{len(created)} (idx={logical_idx}) -> {user_id} ...")
            j = join_matrix(user_id, parent_id, logical_idx)
            joined.append(j)
            print(json.dumps(j, indent=2))
        except Exception as e:
            print(f"Error joining matrix for user index {i}: {e}")
        time.sleep(0.25)

    print("\nSummary:")
    print(f"Created: {len(created)} users; Matrix joined: {len(joined)}")


if __name__ == "__main__":
    main()


