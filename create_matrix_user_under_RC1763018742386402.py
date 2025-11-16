"""
Utility script to create a new user under a specific refer code
and join that user into Matrix Slot 1.

Target referrer:
  - refer_code: RC1763018742386402

Usage (from backend directory):
  python create_matrix_user_under_RC1763018742386402.py
"""

import time
import secrets
import requests

BASE_URL = "http://localhost:8000"
REFERRER_CODE = "RC1763018742386402"


def generate_wallet_address() -> str:
    """Generate a random wallet address."""
    return "0x" + secrets.token_hex(20)


def get_user_id_from_code(refer_code: str) -> str | None:
    """Resolve MongoDB user _id from referral code via API."""
    url = f"{BASE_URL}/user/by-code/{refer_code}"
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"[ERROR] /user/by-code returned {resp.status_code}: {resp.text}")
        return None
    data = resp.json().get("data") or {}
    return data.get("_id") or data.get("id")


def create_temp_user_under_referrer(refer_code: str) -> str | None:
    """
    Create a temporary user under the given refer code using /user/temp-create.
    Returns the new user's MongoDB _id on success.
    """
    url = f"{BASE_URL}/user/temp-create"
    wallet_addr = generate_wallet_address()
    payload = {
        "refered_by": refer_code,
        "wallet_address": wallet_addr,
    }

    print(f"📤 Creating temp user under {refer_code} with wallet {wallet_addr} ...")
    resp = requests.post(url, json=payload)
    if resp.status_code not in (200, 201):
        print(f"[ERROR] temp-create failed ({resp.status_code}): {resp.text}")
        return None

    body = resp.json()
    user_data = body.get("data") or body
    user_id = (
        user_data.get("_id")
        or user_data.get("user_id")
        or user_data.get("id")
        or user_data.get("uid")
    )
    print(f"✅ Temp user created. ID={user_id}, UID={user_data.get('uid')}")
    return user_id


def join_matrix(user_id: str, referrer_id: str) -> bool:
    """Join Matrix program for user_id under referrer_id using /matrix/join."""
    url = f"{BASE_URL}/matrix/join"
    payload = {
        "user_id": user_id,
        "referrer_id": referrer_id,
        "tx_hash": f"matrix_auto_{int(time.time())}",
        "amount": 11.0,
    }

    print(f"📤 Joining Matrix for user {user_id} under referrer {referrer_id} ...")
    resp = requests.post(url, json=payload)
    if resp.status_code != 200:
        print(f"[ERROR] /matrix/join HTTP {resp.status_code}: {resp.text}")
        return False

    body = resp.json()
    if not body.get("success"):
        print(f"[ERROR] Matrix join failed: {body.get('error') or body}")
        return False

    print("✅ Matrix join successful.")
    return True


def main():
    print("=" * 80)
    print(f"Create Matrix user under refer code: {REFERRER_CODE}")
    print("=" * 80)

    # 1) Resolve referrer user_id from refer_code
    referrer_id = get_user_id_from_code(REFERRER_CODE)
    if not referrer_id:
        print(f"❌ Could not resolve user_id for refer code {REFERRER_CODE}")
        return
    print(f"✅ Referrer user_id: {referrer_id}")

    # 2) Create a new temp user under this referrer
    user_id = create_temp_user_under_referrer(REFERRER_CODE)
    if not user_id:
        print("❌ Temp user creation failed; aborting.")
        return

    # 3) Join Matrix Slot 1 for the new user
    ok = join_matrix(user_id, referrer_id)
    if not ok:
        print("❌ Matrix join failed.")
        return

    print("\n🎉 Done. New Matrix user created and joined under RC1763018742386402.")


if __name__ == "__main__":
    main()


