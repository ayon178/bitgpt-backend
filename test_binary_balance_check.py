import requests
import json
import time

BASE_URL = "http://localhost:8000"


def log(title, data=None):
    print(f"\n=== {title} ===")
    if data is not None:
        try:
            print(json.dumps(data, indent=2))
        except Exception:
            print(data)


def temp_create(refered_by="ROOT"):
    url = f"{BASE_URL}/user/temp-create"
    payload = {"refered_by": refered_by, "wallet_address": "0x" + str(int(time.time()*1000)).zfill(40)[:40]}
    r = requests.post(url, json=payload, timeout=60)
    j = r.json()
    if not j.get("success"):
        raise RuntimeError(f"temp-create failed: {j}")
    return j["data"]


def get_refer_code(user):
    u = user.get("user") or {}
    return u.get("refer_code") or user.get("refer_code")


def main():
    # 1) Create USER_X under ROOT
    user_x = temp_create("ROOT")
    user_x_id = user_x.get("_id")
    user_x_token = user_x.get("token")
    user_x_code = get_refer_code(user_x)
    log("USER_X created under ROOT", {"id": user_x_id, "refer_code": user_x_code})

    # 2) Create USER_Y under USER_X
    user_y = temp_create(user_x_code)
    user_y_id = user_y.get("_id")
    log("USER_Y created under USER_X", {"id": user_y_id})

    # 3) Call /wallet/balances for USER_X to verify Slot-1 upline credit (should be +0.0022 BNB)
    target_user_id = user_x_id
    url = f"{BASE_URL}/wallet/balances"
    params = {"user_id": target_user_id, "wallet_type": "main"}
    headers = {"Authorization": f"Bearer {user_x_token}", "Content-Type": "application/json"}
    r = requests.get(url, params=params, headers=headers, timeout=60)
    try:
        resp = r.json()
    except Exception:
        resp = {"status_code": r.status_code, "text": r.text}
    log("/wallet/balances response", resp)


if __name__ == "__main__":
    main()
