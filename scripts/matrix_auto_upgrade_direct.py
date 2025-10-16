import asyncio
import json
import time
from decimal import Decimal

from core.db import connect_to_db
from modules.user.service import create_temp_user_service
from modules.matrix.service import MatrixService


def ensure_seed_data():
    # Call the app's async startup initializer to ensure SlotCatalog, configs, etc.
    try:
        from main import startup_initializer
        asyncio.run(startup_initializer())
    except Exception:
        pass


def create_temp(name: str, refer_code: str) -> dict:
    email = f"{name.lower().replace(' ', '_')}_{int(time.time()*1000)}@example.com"
    payload = {"email": email, "name": name, "refered_by": refer_code}
    data, error = create_temp_user_service(payload)
    if error:
        raise RuntimeError(f"temp-create failed: {error}")
    return data


def _safe(obj):
    if isinstance(obj, (list, tuple)):
        return [_safe(o) for o in obj]
    if isinstance(obj, dict):
        return {k: _safe(v) for k, v in obj.items()}
    try:
        import datetime as _dt
        if isinstance(obj, (_dt.datetime, _dt.date)):
            return obj.isoformat()
    except Exception:
        pass
    return obj


def main():
    # 1) Connect to DB and seed baseline data
    connect_to_db()
    ensure_seed_data()

    svc = MatrixService()

    # 2) Create parent under provided referral code
    parent = create_temp("Matrix Parent", "RCMX013")
    parent_id = parent["_id"]
    parent_ref = parent["refer_code"]
    parent_upline = parent["refered_by"]

    # Persist parent id for verification script
    try:
        with open("scripts/.last_parent_id", "w", encoding="utf-8") as f:
            f.write(parent_id)
    except Exception:
        pass

    # 3) Join parent to Matrix (slot 1)
    svc.join_matrix(user_id=parent_id, referrer_id=parent_upline, tx_hash="tx-parent", amount=Decimal("11"))

    # 4) Create 3 children and join them under the parent; also 2 grandchildren per child
    children = []
    for i in range(1, 4):
        c = create_temp(f"Child {i}", parent_ref)
        children.append(c)
        svc.join_matrix(user_id=c["_id"], referrer_id=parent_id, tx_hash=f"tx-child-{i}", amount=Decimal("11"))
        # two grandchildren to fill left and middle under each L1
        gc1 = create_temp(f"GC {i}-1", c["refer_code"])
        svc.join_matrix(user_id=gc1["_id"], referrer_id=c["_id"], tx_hash=f"tx-gc-{i}-1", amount=Decimal("11"))
        gc2 = create_temp(f"GC {i}-2", c["refer_code"])
        svc.join_matrix(user_id=gc2["_id"], referrer_id=c["_id"], tx_hash=f"tx-gc-{i}-2", amount=Decimal("11"))

    # 5) Calculate middle-three earnings and attempt auto-upgrade
    m3 = svc.calculate_middle_three_earnings(parent_id, 1)
    # Force the path that persists state
    auto = svc.process_automatic_upgrade(parent_id, 1)

    print(json.dumps(_safe({
        "parent_id": parent_id,
        "m3": m3,
        "auto": auto,
    }), separators=(",", ":")))


if __name__ == "__main__":
    main()



