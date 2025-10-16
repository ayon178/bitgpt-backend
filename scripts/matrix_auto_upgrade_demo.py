import json
import os
import sys
import time
from urllib import request, parse, error


BASE_URL = os.environ.get("MATRIX_API_BASE", "http://127.0.0.1:8001")
# Optional in-process mode using FastAPI TestClient to avoid needing a running server
USE_TESTCLIENT = os.environ.get("MATRIX_USE_TESTCLIENT", "0") == "1"
_CLIENT = None
if USE_TESTCLIENT:
    try:
        from fastapi.testclient import TestClient  # type: ignore
        from main import app  # FastAPI app
        _CLIENT = TestClient(app)
    except Exception as _e:
        # Fall back to HTTP mode if import fails
        USE_TESTCLIENT = False


def _http(method: str, path: str, body: dict | None = None, headers: dict | None = None) -> dict:
    if USE_TESTCLIENT and _CLIENT is not None:
        try:
            resp = _CLIENT.request(method.upper(), path, json=body, headers=headers or {})
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    # Fallback to HTTP mode
    url = f"{BASE_URL}{path}"
    data = None
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = request.Request(url, data=data, headers=req_headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {"status": "empty"}
    except error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8")
            return {"error": f"HTTP {e.code}", "body": raw}
        except Exception:
            return {"error": f"HTTP {e.code}", "body": None}
    except Exception as e:
        return {"error": str(e)}


def temp_create_user(name: str, refer_code: str) -> dict:
    email = f"{name.lower().replace(' ', '_')}_{int(time.time()*1000)}@example.com"
    payload = {"email": email, "name": name, "refered_by": refer_code}
    return _http("POST", "/user/temp-create", body=payload)


def join_matrix(user_id: str, referrer_id: str, token: str | None) -> dict:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = {"user_id": user_id, "referrer_id": referrer_id, "tx_hash": "tx", "amount": 11.0}
    return _http("POST", "/matrix/join", body=body, headers=headers)


def middle_three_earnings(user_id: str, slot_no: int, token: str | None) -> dict:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _http("GET", f"/matrix/middle-three-earnings/{user_id}?slot_no={slot_no}", headers=headers)


def trigger_auto_upgrade(user_id: str, slot_no: int, token: str | None) -> dict:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = {"user_id": user_id, "slot_no": slot_no}
    return _http("POST", "/matrix/trigger-auto-upgrade", body=body, headers=headers)


def main():
    # 1) Create parent under RCMX013
    parent = temp_create_user("Matrix Parent", "RCMX013")
    if not parent or parent.get("status") == "Error" or not parent.get("data"):
        print(json.dumps({"step": "create_parent", "result": parent}, separators=(",", ":")))
        sys.exit(1)
    pdata = parent["data"]
    parent_id = pdata.get("_id")
    parent_token = pdata.get("token")
    parent_ref = pdata.get("refer_code")
    parent_upline = pdata.get("refered_by")

    # 2) Join parent to Matrix (slot 1)
    jparent = join_matrix(parent_id, parent_upline, parent_token)

    # 3) Create 3 children under parent refer_code and join them
    children = []
    for i in range(1, 4):
        c = temp_create_user(f"Child {i}", parent_ref)
        if not c or c.get("status") == "Error" or not c.get("data"):
            print(json.dumps({"step": f"create_child_{i}", "result": c}, separators=(",", ":")))
            sys.exit(1)
        cdata = c["data"]
        cid = cdata.get("_id")
        ctoken = cdata.get("token")
        cref = cdata.get("refer_code")
        children.append({"id": cid, "token": ctoken, "ref": cref})
        jchild = join_matrix(cid, parent_id, ctoken)

    # 4) For each child, create 2 grandchildren and join them under the child
    for idx, child in enumerate(children, start=1):
        for j in range(1, 3):
            gc = temp_create_user(f"GC {idx}-{j}", child["ref"])
            if not gc or gc.get("status") == "Error" or not gc.get("data"):
                print(json.dumps({"step": f"create_gc_{idx}_{j}", "result": gc}, separators=(",", ":")))
                sys.exit(1)
            gdata = gc["data"]
            gid = gdata.get("_id")
            gtoken = gdata.get("token")
            jgc = join_matrix(gid, child["id"], gtoken)

    # 5) Check middle-three earnings and trigger auto-upgrade
    m3 = middle_three_earnings(parent_id, 1, parent_token)
    auto = trigger_auto_upgrade(parent_id, 1, parent_token)

    out = {
        "parent_id": parent_id,
        "parent_join": jparent,
        "children_count": len(children),
        "m3": m3,
        "auto": auto,
    }
    print(json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    main()


