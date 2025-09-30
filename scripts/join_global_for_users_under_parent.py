import os
import json
import time
from typing import Dict, Any, List

import requests


BASE_URL = os.getenv("BITGPT_BASE_URL", "https://bitgpt-backend.onrender.com")


def post_json(path: str, payload: Dict[str, Any], token: str | None = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Non-JSON response from {url}: {resp.status_code} {resp.text}")
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status_code} {url}: {json.dumps(data)}")
    return data


def get_status(path: str) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    resp = requests.get(url, timeout=30)
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Non-JSON response from {url}: {resp.status_code} {resp.text}")
    return {"ok": resp.ok, "status_code": resp.status_code, "data": data}


def login_wallet(wallet: str) -> Dict[str, Any]:
    return post_json("/auth/login", {"wallet_address": wallet}, token=None)


def join_global(user_id: str, token: str, idx: int) -> Dict[str, Any]:
    payload = {
        "user_id": user_id,
        "tx_hash": f"0xglobal_tx_{idx:03d}",
        "amount": 33.0,
    }
    return post_json("/global/join", payload, token=token)


def main():
    parent_id = os.getenv("BITGPT_PARENT_ID")
    if not parent_id:
        parent_id = input("Enter parent user _id (ObjectId): ").strip()

    # Strategy: derive wallets created by matrix seeding
    # Batch A (1..26): deterministic wallets used in matrix seeding → 0x...{3000+idx}
    # Batch B (27..40): may or may not exist; attempt nonce-based wallets cannot be derived, so skip if login fails

    total = int(os.getenv("BITGPT_SEED_COUNT", "40"))
    start_idx = int(os.getenv("BITGPT_START_IDX", "1"))

    success = 0
    attempted = 0

    for idx in range(start_idx, start_idx + total):
        # Build candidate wallets
        wallet_candidates: List[str] = []
        # Deterministic pattern used for first 26 users
        deterministic = f"0x000000000000000000000000000000000000{3000 + idx:04d}"
        wallet_candidates.append(deterministic)

        # Optionally add custom prefixes if provided
        custom_prefix = os.getenv("BITGPT_WALLET_PREFIX")
        if custom_prefix:
            wallet_candidates.append(f"{custom_prefix}{idx:03d}")

        user_id = None
        token = None
        last_error = None

        for w in wallet_candidates:
            try:
                login_res = login_wallet(w)
                data = login_res.get("data") or {}
                token_obj = data.get("token") or {}
                user_obj = data.get("user") or {}
                token = token_obj.get("access_token")
                user_id = user_obj.get("_id")
                if token and user_id:
                    break
            except Exception as e:
                last_error = e
                continue

        if not token or not user_id:
            print(f"Skipping idx={idx}: could not login with any candidate wallet ({last_error})")
            continue

        attempted += 1
        # Check current global status; join only if not present
        status_res = get_status(f"/global/status/{user_id}")
        if status_res.get("ok"):
            print(f"Idx={idx} user_id={user_id} already has Global status; skipping join")
        else:
            try:
                print(f"Joining Global for idx={idx} user_id={user_id} ...")
                j = join_global(user_id, token, idx)
                print(json.dumps(j, indent=2))
                success += 1
            except Exception as e:
                print(f"Error joining global for user_id={user_id}: {e}")
        time.sleep(0.2)

    print(f"\nGlobal joined successfully for {success}/{attempted} attempted users (range idx {start_idx}..{start_idx+total-1})")


if __name__ == "__main__":
    main()


