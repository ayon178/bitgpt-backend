from decimal import Decimal
from mongoengine import connect
import os

# Ensure we can import project modules
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from modules.slot.model import SlotCatalog


def upsert_slot(program: str, slot_no: int, name: str, price: Decimal, level: int, phase: str | None = None):
    q = {'program': program, 'slot_no': slot_no}
    slot = SlotCatalog.objects(**q).first()
    if not slot:
        slot = SlotCatalog(**q)
    slot.name = name
    slot.price = price
    slot.currency = 'BNB' if program == 'binary' else ('USDT' if program == 'matrix' else 'USDT')
    slot.level = level
    if program == 'global' and phase:
        slot.phase = phase
    slot.is_active = True
    slot.save()
    return slot


def main():
    # Connect using env MONGODB_URI or default local
    uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/bitgpt')
    connect(host=uri)

    # Binary slots 1 & 2 (Explorer, Contributor)
    upsert_slot('binary', 1, 'EXPLORER', Decimal('0.0022'), level=0)
    upsert_slot('binary', 2, 'CONTRIBUTOR', Decimal('0.0044'), level=1)

    # Matrix slot 1 (Starter) minimal
    upsert_slot('matrix', 1, 'STARTER', Decimal('11'), level=1)

    # Global slot 1 (Phase-1 Foundation minimal)
    upsert_slot('global', 1, 'FOUNDATION', Decimal('33'), level=1, phase='PHASE-1')

    print('SlotCatalog seeded/updated for binary(1,2), matrix(1), global(1).')


if __name__ == '__main__':
    main()


