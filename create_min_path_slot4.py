#!/usr/bin/env python3
"""
Create minimal path to trigger Target user's Slot 4 reserve:
Target -> L1 -> L2 -> (L3a, L3b)  [L3 slot3 target upline depth = 3]
For each L3 -> create (L4a, L4b) to push Slot 2 payments to L3's Slot 3 reserve.
"""

import os
import sys
import time
import secrets
import requests
from typing import Tuple, Optional, Dict

BASE_URL = "http://localhost:8000"
TARGET_REFER_CODE = "RC1762150704576515"
REQUEST_TIMEOUT = 120
WAIT = 70

def create_user(name: str, refer_code: str, email: str = None) -> Tuple[Optional[str], Optional[str]]:
    if email is None:
        email = f"{name.lower()}_{int(time.time()*1000)}@test.com"
    payload = {
        "email": email,
        "name": name,
        "refered_by": refer_code,
        "wallet_address": f"0x{secrets.token_hex(20)}"
    }
    print(f"  Creating {name} under {refer_code}...")
    for attempt in range(3):
        try:
            r = requests.post(f"{BASE_URL}/user/temp-create", json=payload, timeout=REQUEST_TIMEOUT)
            j = r.json()
            if r.status_code in (200, 201) and j.get("status") == "Ok":
                data = j.get("data", {})
                code = data.get("refer_code") or (data.get("user") or {}).get("refer_code")
                uid = data.get("_id") or (data.get("user") or {}).get("_id")
                print(f"    ✅ {name}: {code}")
                print(f"    ⏳ Waiting {WAIT}s for background tasks...")
                time.sleep(WAIT)
                return code, uid
            else:
                print(f"    ⚠️ Attempt {attempt+1} failed: {j}")
                if attempt < 2:
                    time.sleep(10)
                    continue
                return None, None
        except Exception as e:
            print(f"    ⚠️ Error: {e}")
            if attempt < 2:
                time.sleep(10)
                continue
            return None, None
    return None, None


def main():
    print("="*100)
    print("Creating minimal path for Slot 4 reserve")
    print("="*100)

    # L1
    l1_code, _ = create_user("MP_L1", TARGET_REFER_CODE)
    if not l1_code:
        print("❌ Failed at L1")
        return

    # L2
    l2_code, _ = create_user("MP_L2", l1_code)
    if not l2_code:
        print("❌ Failed at L2")
        return

    # L3 a, b
    l3_codes = []
    for i in range(2):
        code, _ = create_user(f"MP_L3_{i+1}", l2_code)
        if code:
            l3_codes.append(code)
    if len(l3_codes) < 2:
        print("❌ Failed to create two L3 users")
        return

    # For each L3, create 2 L4 to push Slot 2 funds → L3 Slot 3 reserve
    for idx, l3_code in enumerate(l3_codes):
        for j in range(2):
            _code, _ = create_user(f"MP_L4_{idx+1}_{j+1}", l3_code)

    print("\n✅ Minimal path created. Now run:\n  python trigger_compact_auto_checks.py\n  python verify_slot6_auto_upgrade.py")

if __name__ == "__main__":
    main()
