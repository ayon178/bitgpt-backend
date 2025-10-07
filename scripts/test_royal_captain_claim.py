import sys
import time
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.db import connect_to_db
from modules.user.model import User
from modules.royal_captain.service import RoyalCaptainService
from modules.slot.model import SlotCatalog, SlotActivation
from bson import ObjectId
from decimal import Decimal
from datetime import datetime


def ensure_slot_activation(user_id, program, slot_no):
    """Ensure a slot activation exists for user."""
    existing = SlotActivation.objects(user_id=user_id, program=program, slot_no=slot_no, status='completed').first()
    if existing:
        return existing
    
    cat = SlotCatalog.objects(program=program, slot_no=slot_no, is_active=True).first()
    slot_name = cat.name if cat else f"{program.upper()} Slot {slot_no}"
    amount = cat.price if (cat and cat.price) else Decimal('0')
    
    act = SlotActivation(
        user_id=user_id,
        program=program,
        slot_no=slot_no,
        slot_name=slot_name,
        activation_type='upgrade',
        upgrade_source='wallet',
        amount_paid=Decimal(amount),
        currency=('BNB' if program == 'binary' else ('USDT' if program == 'matrix' else 'USDT')),
        tx_hash=f"ENSURE-{program.upper()}-{user_id}-{slot_no}-{int(datetime.utcnow().timestamp())}",
        status='completed',
        activated_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    act.save()
    return act


def create_partner(upline_id, uid_suffix):
    """Create a partner under upline with all 3 programs active."""
    suffix = str(int(time.time()))[-4:] + uid_suffix
    user = User(
        uid=f"RCPART{suffix}",
        refer_code=f"RC{suffix}",
        refered_by=upline_id,
        wallet_address=f"0x0000000000000000000000000000000000RC{suffix}",
        name=f"Partner{suffix}",
        role="user",
        status="active",
        binary_joined=True,
        matrix_joined=True,
        global_joined=True,
        binary_joined_at=datetime.utcnow(),
        matrix_joined_at=datetime.utcnow(),
        global_joined_at=datetime.utcnow(),
    )
    user.save()
    # Ensure slot activations for each program
    ensure_slot_activation(user.id, 'binary', 1)
    ensure_slot_activation(user.id, 'matrix', 1)
    ensure_slot_activation(user.id, 'global', 1)
    return user


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_royal_captain_claim.py <USER_ID>")
        return
    
    user_id_str = sys.argv[1]
    user_id = ObjectId(user_id_str)
    
    connect_to_db()
    
    user = User.objects(id=user_id).first()
    if not user:
        print({"error": "User not found"})
        return
    
    print(f"Testing Royal Captain for user: {user_id_str}")
    
    # 1. Ensure user has all 3 programs active
    print("Step 1: Ensuring user has Binary, Matrix, Global active...")
    ensure_slot_activation(user_id, 'binary', 1)
    ensure_slot_activation(user_id, 'matrix', 1)
    ensure_slot_activation(user_id, 'global', 1)
    
    user.binary_joined = True
    user.matrix_joined = True
    user.global_joined = True
    user.binary_joined_at = datetime.utcnow()
    user.matrix_joined_at = datetime.utcnow()
    user.global_joined_at = datetime.utcnow()
    user.save()
    print("User programs activated.")
    
    # 2. Ensure user has 5 direct partners with all 3 programs
    print("Step 2: Checking direct partners...")
    directs = list(User.objects(refered_by=user_id))
    needed = max(0, 5 - len(directs))
    if needed > 0:
        print(f"Creating {needed} direct partners with all 3 programs...")
        for i in range(needed):
            create_partner(user_id, str(i))
    else:
        # Ensure existing partners have all 3 programs
        print(f"Found {len(directs)} direct partners; ensuring they have all 3 programs...")
        for p in directs[:5]:
            ensure_slot_activation(p.id, 'binary', 1)
            ensure_slot_activation(p.id, 'matrix', 1)
            ensure_slot_activation(p.id, 'global', 1)
            p.binary_joined = True
            p.matrix_joined = True
            p.global_joined = True
            p.save()
    print("Direct partners ready.")
    
    # 3. Check eligibility
    print("Step 3: Checking Royal Captain eligibility...")
    svc = RoyalCaptainService()
    # Ensure joined
    svc.join_royal_captain_program(user_id_str)
    # Check eligibility
    elig = svc.check_eligibility(user_id_str, force_check=True)
    print(elig)
    
    # 4. Claim
    if elig.get('is_eligible'):
        print("Step 4: Claiming Royal Captain bonus in USDT...")
        claim = svc.claim_royal_captain_bonus(user_id_str, 'USDT')
        print(claim)
        
        if claim.get('success'):
            print("\nSuccess! Wallet credited. Testing history...")
            # Optional: query claim history via model
            from modules.royal_captain.model import RoyalCaptainBonusPayment
            payments = RoyalCaptainBonusPayment.objects(user_id=user_id).order_by('-created_at').limit(5)
            for p in payments:
                print({
                    "tier": p.bonus_tier,
                    "amount": p.bonus_amount,
                    "currency": p.currency,
                    "status": p.payment_status,
                    "paid_at": p.paid_at
                })
    else:
        print("User not eligible. Reasons:", elig.get('eligibility_reasons'))


if __name__ == '__main__':
    main()

