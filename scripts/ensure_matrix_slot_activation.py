import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.db import connect_to_db
from modules.slot.model import SlotActivation, SlotCatalog
from bson import ObjectId


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/ensure_matrix_slot_activation.py <USER_ID> <SLOT_NO>")
        return
    user_id = sys.argv[1]
    slot_no = int(sys.argv[2])

    connect_to_db()
    existing = SlotActivation.objects(
        user_id=ObjectId(user_id), program='matrix', slot_no=slot_no, status='completed'
    ).first()
    if existing:
        print({"status": "exists", "activation_id": str(existing.id)})
        return

    catalog = SlotCatalog.objects(program='matrix', slot_no=slot_no, is_active=True).first()
    slot_name = catalog.name if catalog else f"Slot {slot_no}"
    amount = catalog.price if (catalog and catalog.price) else Decimal('0')

    act = SlotActivation(
        user_id=ObjectId(user_id),
        program='matrix',
        slot_no=slot_no,
        slot_name=slot_name,
        activation_type='upgrade',
        upgrade_source='wallet',
        amount_paid=Decimal(amount),
        currency='USDT',
        tx_hash=f"ENSURE-MATRIX-{user_id}-{slot_no}-{int(datetime.utcnow().timestamp())}",
        status='completed',
        activated_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    act.save()
    print({"status": "created", "activation_id": str(act.id)})


if __name__ == '__main__':
    main()


