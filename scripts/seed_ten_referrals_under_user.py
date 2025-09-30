import os
import json
import time
from typing import Dict, Any, List

import requests


# Configure base URL: default to live API, can override with env BITGPT_BASE_URL
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


def create_referral(parent_id: str, idx: int) -> Dict[str, Any]:
    uid = f"AUTO{idx:03d}"
    refer_code = f"RCAUTO{idx:03d}"
    wallet = f"0x000000000000000000000000000000000000{2000 + idx:04d}"
    payload = {
        "uid": uid,
        "refer_code": refer_code,
        "upline_id": parent_id,  # mapped to refered_by in router
        "wallet_address": wallet,
        "name": f"{uid} User",
        "role": "user",
        "email": f"{uid.lower()}@bitgpt.local",
        "password": "changeme",
        # Provide a dummy tx to trigger binary join initialization
        "binary_payment_tx": f"0xjoin_tx_{idx:03d}",
        "network": "BSC",
    }
    return post_json("/user/create", payload)


def main():
    # Parent/upline user _id
    parent_id = os.getenv("BITGPT_PARENT_ID")
    if not parent_id:
        parent_id = input("Enter parent user _id (ObjectId): ").strip()

    # How many users to create
    total = int(os.getenv("BITGPT_SEED_COUNT", "10"))

    results: List[Dict[str, Any]] = []
    for i in range(1, total + 1):
        label = f"Creating referral {i}/{total} under {parent_id}..."
        print(label)
        try:
            result = create_referral(parent_id, i)
            results.append(result)
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error creating referral {i}: {e}")

        # brief pause for any async processes and to be gentle on the API
        time.sleep(0.3)

    print("\nSummary (created users):")
    for r in results:
        try:
            data = r.get("data") or {}
            print(f"- _id={data.get('_id')} uid={data.get('uid')} token={'yes' if data.get('token') else 'no'}")
        except Exception:
            pass


if __name__ == "__main__":
    main()


