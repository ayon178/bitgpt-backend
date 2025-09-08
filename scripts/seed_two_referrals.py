import os
import json
import time
from typing import Dict, Any

import requests


BASE_URL = os.getenv("BITGPT_BASE_URL", "http://127.0.0.1:8000")


def post_json(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    resp = requests.post(url, json=payload, timeout=30)
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Non-JSON response from {url}: {resp.status_code} {resp.text}")
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status_code} {url}: {json.dumps(data)}")
    return data


def get_json(path: str, token: str | None = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = requests.get(url, headers=headers, timeout=30)
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Non-JSON response from {url}: {resp.status_code} {resp.text}")
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status_code} {url}: {json.dumps(data)}")
    return data


def create_referral(root_id: str, uid: str, ref_code: str, wallet: str, join_tx: str) -> Dict[str, Any]:
    payload = {
        "uid": uid,
        "refer_code": ref_code,
        "upline_id": root_id,  # maps to refered_by in router
        "wallet_address": wallet,
        "name": f"{uid} User",
        "role": "user",
        "email": f"{uid.lower()}@bitgpt.local",
        "password": "changeme",
        # Binary join proof (triggers slots 1 & 2 activation + commissions)
        "binary_payment_tx": join_tx,
        "network": "BSC",
    }
    return post_json("/user/create", payload)


def main():
    # 1) Expect ROOT exists already; read from env or prompt
    root_id = os.getenv("BITGPT_ROOT_ID")
    if not root_id:
        root_id = input("Enter ROOT user _id (ObjectId): ").strip()

    print("Creating USER201 under ROOT...")
    u1 = create_referral(root_id, "USER201", "RCUSER201", "0x0000000000000000000000000000000000001201", "0xjoin_tx_201")
    print(json.dumps(u1, indent=2))

    # Let async hooks settle if any background tasks run
    time.sleep(0.5)

    print("Creating USER202 under ROOT...")
    u2 = create_referral(root_id, "USER202", "RCUSER202", "0x0000000000000000000000000000000000001202", "0xjoin_tx_202")
    print(json.dumps(u2, indent=2))

    # Extract tokens for GETs where auth is required (tree endpoints)
    token1 = (u1.get("data") or {}).get("token")
    token2 = (u2.get("data") or {}).get("token")

    # 2) Verify Binary placements for ROOT (admin will access via its own token if needed)
    # Fallback: use USER201 token to view its own tree; same for USER202
    print("\nVerifying USER201 binary tree view (self)...")
    try:
        t1 = get_json(f"/tree/{(u1['data']['_id'])}/binary", token=token1)
        print(json.dumps(t1, indent=2))
    except Exception as e:
        print(f"Warning: could not fetch USER201 tree view: {e}")

    print("\nVerifying USER202 binary tree view (self)...")
    try:
        t2 = get_json(f"/tree/{(u2['data']['_id'])}/binary", token=token2)
        print(json.dumps(t2, indent=2))
    except Exception as e:
        print(f"Warning: could not fetch USER202 tree view: {e}")

    # 3) (Optional) You can inspect commissions and events using their endpoints if needed
    print("\nDone. Two referrals created under ROOT. Check DB collections:")
    print("- slot_activation (binary slots 1 & 2 for each user)")
    print("- tree_placement (binary entries under ROOT)")
    print("- blockchain_event (join_payment, slot_activated)")
    print("- commission, commission_distribution, distribution_receipt")
    print("- binary_auto_upgrade (partners count for ROOT should increment)")


if __name__ == "__main__":
    main()


