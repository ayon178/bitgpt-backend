"""
Create a new user directly in MongoDB under the given refer code
and join that user into Matrix Slot 1, without calling the HTTP API.

Target referrer:
  - refer_code: RC1763018742386402

Usage (from backend directory):
  python create_matrix_user_under_RC1763018742386402_db.py
"""

from decimal import Decimal
import secrets
import time

from core.db import connect_to_db
from modules.user.model import User
from modules.user.service import create_temp_user_service
from modules.matrix.service import MatrixService


REFERRER_CODE = "RC1763018742386402"


def _generate_wallet_address() -> str:
    return "0x" + secrets.token_hex(20)


def main():
    print("=" * 80)
    print(f"Create Matrix user under refer code (DB direct): {REFERRER_CODE}")
    print("=" * 80)

    # 1) Connect to MongoDB (uses MONGO_URI from core.config)
    connect_to_db()

    # 2) Find referrer by refer_code
    ref_user = User.objects(refer_code=REFERRER_CODE).first()
    if not ref_user:
        print(f"❌ No user found with refer_code {REFERRER_CODE}")
        return
    referrer_id = str(ref_user.id)
    print(f"✅ Referrer found: uid={ref_user.uid}, _id={referrer_id}")

    # 3) Create temp user under this referrer
    payload = {
        "wallet_address": _generate_wallet_address(),
        "refered_by": REFERRER_CODE,
        # optional fields: keep minimal so service auto-generates the rest
        "email": "",
        "name": f"Matrix Auto {int(time.time())}",
    }
    print(f"📤 Creating temp user with wallet {payload['wallet_address']} ...")
    result, error = create_temp_user_service(payload)
    if error:
        print(f"❌ Temp user creation error: {error}")
        return

    new_user_id = str(result["_id"])
    print(f"✅ Temp user created: uid={result.get('uid')} _id={new_user_id}")

    # 4) Join Matrix Slot 1 for this user
    svc = MatrixService()
    tx_hash = f"matrix_db_{int(time.time())}"
    print(f"📤 Joining Matrix (direct DB) for user {new_user_id} under {referrer_id} ...")
    join_res = svc.join_matrix(
        user_id=new_user_id,
        referrer_id=referrer_id,
        tx_hash=tx_hash,
        amount=Decimal("11"),
    )

    if not join_res.get("success"):
        print(f"❌ Matrix join failed: {join_res.get('error') or join_res}")
        return

    print("✅ Matrix join successful.")
    print(f"   matrix_tree_id: {join_res.get('matrix_tree_id')}")
    print(f"   activation_id:  {join_res.get('activation_id')}")
    print(f"   slot_activated: {join_res.get('slot_activated')}")


if __name__ == "__main__":
    main()


