import requests
import secrets
import time

BASE_URL = "http://localhost:8000"


def log(title, data=None):
    print(f"\n=== {title} ===")
    if data is not None:
        print(data)


def gen_wallet():
    return "0x" + secrets.token_hex(20)


def temp_create(refered_by="ROOT"):
    url = f"{BASE_URL}/user/temp-create"
    payload = {"refered_by": refered_by, "wallet_address": gen_wallet()}
    r = requests.post(url, json=payload)
    try:
        j = r.json()
    except Exception:
        log("temp-create non-JSON", r.text)
        return None
    log("temp-create response", j)
    return j.get("data") if j.get("success") else None


def by_code(code="ROOT"):
    r = requests.get(f"{BASE_URL}/user/by-code/{code}")
    try:
        j = r.json()
    except Exception:
        log("by-code non-JSON", r.text)
        return None
    return (j.get("data") or {}).get("_id")


def matrix_join(user_id, referrer_id, amount=11.0, tag=""):
    url = f"{BASE_URL}/matrix/join"
    payload = {
        "user_id": user_id,
        "referrer_id": referrer_id,
        "tx_hash": f"tx_{tag}_{int(time.time())}",
        "amount": amount,
    }
    r = requests.post(url, json=payload)
    try:
        j = r.json()
    except Exception:
        log("matrix/join non-JSON", r.text)
        return None
    log(f"matrix/join {tag}", j)
    return j


def get_bonuses(user_id):
    r = requests.get(f"{BASE_URL}/newcomer-support/bonuses/{user_id}")
    try:
        j = r.json()
    except Exception:
        log("bonuses non-JSON", r.text)
        return None
    log(f"bonuses for {user_id}", j)
    return j


def get_reserve_status(user_id, program="matrix"):
    r = requests.get(f"{BASE_URL}/user/reserve-status/{user_id}", params={"program": program})
    try:
        j = r.json()
    except Exception:
        log("reserve-status non-JSON", r.text)
        return None
    log(f"reserve-status {user_id} {program}", j)
    return j


def main():
    # Resolve ROOT id
    root_id = by_code("ROOT")

    # USER_A under ROOT
    user_a = temp_create("ROOT")
    if not user_a:
        log("Abort", "Failed to create USER_A")
        return
    user_a_id = user_a.get("_id")
    user_a_code = (user_a.get("user") or {}).get("refer_code") or user_a.get("refer_code")
    # Fallback: get ROOT_ID from embedded user.refered_by if by-code failed
    if not root_id:
        try:
            embedded = user_a.get("user") or {}
            root_id = embedded.get("refered_by") or root_id
        except Exception:
            pass
    log("ROOT_ID", root_id)
    if not root_id:
        log("Abort", "Could not resolve ROOT_ID")
        return

    matrix_join(user_a_id, root_id, tag="USER_A")

    # USER_B under USER_A
    user_b = temp_create(user_a_code)
    if not user_b:
        log("Abort", "Failed to create USER_B")
        return
    user_b_id = user_b.get("_id")
    matrix_join(user_b_id, user_a_id, tag="USER_B")

    # USER_C under USER_A (optional to fill more positions)
    user_c = temp_create(user_a_code)
    if user_c:
        user_c_id = user_c.get("_id")
        matrix_join(user_c_id, user_a_id, tag="USER_C")

    # Fill all 3 Level-1 positions under USER_A to prepare for Level-2 middle routing
    # USER_B is already placed (likely left or middle)
    # Create USER_D and USER_E to fill remaining L1 positions under USER_A
    log("Creating USER_D under USER_A (3rd L1 position)")
    user_d = temp_create(user_a_code)
    if user_d:
        user_d_id = user_d.get("_id")
        matrix_join(user_d_id, user_a_id, tag="USER_D")
    
    # Now create children under USER_B to get to Level-2
    # We need to get the middle position of USER_B's first child
    log("Creating USER_B1 under USER_B")
    user_b1 = temp_create((user_b.get("user") or {}).get("refer_code") or user_b.get("refer_code"))
    if user_b1:
        user_b1_id = user_b1.get("_id")
        matrix_join(user_b1_id, user_b_id, tag="USER_B1")
        
        # Create two children under USER_B1 so that the second child is likely placed at 'middle'
        log("Creating USER_B1A under USER_B1 (first child)")
        user_b1a = temp_create((user_b1.get("user") or {}).get("refer_code") or user_b1.get("refer_code"))
        if user_b1a:
            user_b1a_id = user_b1a.get("_id")
            matrix_join(user_b1a_id, user_b1_id, tag="USER_B1A")
        
        log("Creating USER_B1B under USER_B1 (second child to target middle)")
        user_b1b = temp_create((user_b1.get("user") or {}).get("refer_code") or user_b1.get("refer_code"))
        if user_b1b:
            user_b1b_id = user_b1b.get("_id")
            matrix_join(user_b1b_id, user_b1_id, tag="USER_B1B")
    
    # Create more children under USER_B to fill positions
    log("Creating USER_B2 under USER_B")
    user_b2 = temp_create((user_b.get("user") or {}).get("refer_code") or user_b.get("refer_code"))
    if user_b2:
        user_b2_id = user_b2.get("_id")
        matrix_join(user_b2_id, user_b_id, tag="USER_B2")
    
    log("Creating USER_B3 under USER_B")
    user_b3 = temp_create((user_b.get("user") or {}).get("refer_code") or user_b.get("refer_code"))
    if user_b3:
        user_b3_id = user_b3.get("_id")
        matrix_join(user_b3_id, user_b_id, tag="USER_B3")

    # Verify newcomer bonuses and reserve
    log("Checking bonuses for all users")
    get_bonuses(user_a_id)
    get_bonuses(user_b_id)
    get_bonuses(user_c_id if user_c else None)
    if user_d:
        get_bonuses(user_d_id)
    if user_b1:
        get_bonuses(user_b1_id)
    if 'user_b1a_id' in locals():
        get_bonuses(user_b1a_id)
    if user_b2:
        get_bonuses(user_b2_id)
    if user_b3:
        get_bonuses(user_b3_id)
    get_bonuses(root_id)

    # Upline-locked bonuses view for USER_A (should include locked 50% entries from USER_B/USER_C and possibly USER_B2 if middle routing applied)
    def get_upline_locked(uid):
        r = requests.get(f"{BASE_URL}/newcomer-support/bonuses/upline-locked/{uid}")
        try:
            j = r.json()
        except Exception:
            log("upline-locked non-JSON", r.text)
            return None
        log(f"upline-locked for {uid}", j)
        return j

    get_upline_locked(user_a_id)

    get_reserve_status(user_a_id, "matrix")
    get_reserve_status(root_id, "matrix")


if __name__ == "__main__":
    main()


