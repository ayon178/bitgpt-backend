from datetime import datetime
import sys
from decimal import Decimal
from bson import ObjectId

from core.db import connect_to_db
from modules.user.model import User
from modules.tree.model import TreePlacement

# Reserved keyword 'global' prevents direct import; load via importlib
import os
import importlib.util
_gserial_path = os.path.join(os.path.dirname(__file__), 'modules', 'global', 'serial_placement_service.py')
_gserial_spec = importlib.util.spec_from_file_location('gserial', _gserial_path)
_gserial = importlib.util.module_from_spec(_gserial_spec)
_gserial_spec.loader.exec_module(_gserial)
GlobalSerialPlacementService = _gserial.GlobalSerialPlacementService


def pick_or_create_user(name_fallback: str) -> str:
    """Pick an existing active user if available; otherwise create one quickly."""
    u = User.objects(status='active').order_by('-created_at').first()
    if u:
        # Ensure minimal flags for global prerequisite
        try:
            if not getattr(u, 'binary_joined', False):
                u.binary_joined = True
            if not getattr(u, 'matrix_joined', False):
                u.matrix_joined = True
            u.save()
        except Exception:
            pass
        return str(u.id)

    uid = f"glfast_{name_fallback}_{datetime.utcnow().timestamp()}".replace('.', '')
    u = User(
        uid=uid,
        refer_code=f"RC_{uid}",
        wallet_address=f"0x{uid}",
        name=name_fallback,
        status='active',
        refered_by=None,
        binary_joined=True,
        matrix_joined=True,
        global_joined=False,
        binary_joined_at=datetime.utcnow(),
        matrix_joined_at=datetime.utcnow(),
    )
    u.save()
    return str(u.id)


def progress(msg: str):
    try:
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()
    except Exception:
        print(msg, flush=True)


def main():
    # Force line-buffered output for live progress
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass
    progress("⏳ Connecting to DB...")
    connect_to_db()
    progress("✅ DB connected (Global serial live)")

    # Quick sanity ping to ensure queries return
    try:
        _ = TreePlacement.objects(program='global').only('id').first()
        progress("🟢 DB query OK")
    except Exception as e:
        progress(f"🔴 DB query failed: {e}")

    sps = GlobalSerialPlacementService()

    # First/priority user A
    A = pick_or_create_user("A")
    progress(f"🌐 Candidate A: {A}")

    # If an existing first user exists, use that ID as A to follow the live tree
    first = None
    try:
        first = sps._get_first_user()
    except Exception as e:
        progress(f"ℹ️  _get_first_user skipped due to: {e}")
    if first:
        A = first.get('user_id', A)
        progress(f"ℹ️  Existing first user found → A reassigned: {A}")
    # Ensure first user has PHASE-1 S1 placement; if missing, create it
    if not TreePlacement.objects(user_id=ObjectId(A), program='global', phase='PHASE-1', slot_no=1).first():
        try:
            _ = sps._create_first_user_tree(user_id=A, tx_hash=f"tx_{A}", amount=Decimal('33'))
            progress("ℹ️  Initialized PHASE-1, SLOT-1 for first user")
        except Exception as e:
            progress(f"ℹ️  First user init skipped due to: {e}")

    if not first:
        try:
            # Avoid potential full-scan by directly creating the first placement
            resA = sps._create_first_user_tree(user_id=A, tx_hash=f"tx_{A}", amount=Decimal('33'))
        except Exception:
            resA = sps.process_serial_placement(user_id=A, referrer_id=A, tx_hash=f"tx_{A}", amount=Decimal('33'))
        progress(f"➡️  A init placement: {resA}")
    

    assert TreePlacement.objects(user_id=ObjectId(A), program='global', phase='PHASE-1', slot_no=1).first(), "A should be in PHASE-1 S1"
    progress("✅ A at PHASE-1, SLOT-1")

    # Fill Phase-1 Slot-1 under A with 4 users total
    names_p1 = ["B", "C", "D", "E"]
    placed = 0
    for nm in names_p1:
        uid = pick_or_create_user(nm)
        res = sps.process_serial_placement(user_id=uid, referrer_id=A, tx_hash=f"tx_{uid}", amount=Decimal('33'))
        placed += 1
        progress(f"   • P1 seat {placed}/4 → user {nm} → {res}")

    # Expect A upgraded to PHASE-2 S1
    assert TreePlacement.objects(user_id=ObjectId(A), program='global', phase='PHASE-2', slot_no=1).first(), "A should upgrade to PHASE-2 S1"
    progress("✅ Phase-1 S1 complete → A upgraded to PHASE-2, SLOT-1")

    # Fill Phase-2 Slot-1 with 8 users
    names_p2 = ["F", "G", "H", "I", "J", "K", "L", "M"]
    placed = 0
    for nm in names_p2:
        uid = pick_or_create_user(nm)
        res = sps.process_serial_placement(user_id=uid, referrer_id=A, tx_hash=f"tx_{uid}", amount=Decimal('39.6'))
        placed += 1
        progress(f"   • P2 seat {placed}/8 → user {nm} → {res}")

    # Expect A re-enters PHASE-1 SLOT-2
    assert TreePlacement.objects(user_id=ObjectId(A), program='global', phase='PHASE-1', slot_no=2).first(), "A should re-enter PHASE-1 S2"
    progress("✅ Phase-2 S1 complete → A re-entered PHASE-1, SLOT-2")

    # Print simple distribution expectations (no heavy fund writes here)
    progress("📊 Distribution policy (expected per join): 30% Reserve, 30% Wallet, 10% PI, 10% RoyalCaptain, 10% President, 5% Shareholders, 5% TripleEntry")

    progress("\n🎯 Global serial live test complete.\n")


if __name__ == "__main__":
    main()


