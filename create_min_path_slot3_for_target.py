#!/usr/bin/env python3
"""
Create minimal path to credit Target user's Slot 3 reserve:
Target -> C1 -> (G1, G2)  [G* slot2 routes to Target's Slot 3 reserve if first/second at level 2]
"""

import os
import sys
import time
import secrets
import requests
from typing import Tuple, Optional

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
    print("Creating minimal path for Target's Slot 3 reserve")
    print("="*100)

    # C1 (child of Target)
    c1_code, _ = create_user("MC_C1", TARGET_REFER_CODE)
    if not c1_code:
        print("❌ Failed at C1")
        return

    # G1, G2 (grandchildren under C1) -> should occupy first two positions at level 2 of Target
    g1_code, _ = create_user("MC_G1", c1_code)
    g2_code, _ = create_user("MC_G2", c1_code)
    if not g1_code or not g2_code:
        print("❌ Failed creating G1/G2")
        return

    print("\n✅ Minimal path created for Slot 3 reserve. Now run:\n  python trigger_compact_auto_checks.py\n  python verify_slot6_auto_upgrade.py")


if __name__ == "__main__":
    main()
