#!/usr/bin/env python3
"""
Standalone test for Matrix middle child detection and auto-upgrade
This test works regardless of existing tree data
"""

from mongoengine import connect
from modules.matrix.service import MatrixService
from modules.user.model import User
from modules.wallet.model import UserWallet, ReserveLedger
from modules.matrix.model import MatrixActivation, MatrixTree
from modules.tree.model import TreePlacement
from decimal import Decimal
from datetime import datetime
from bson import ObjectId
import sys

# Connect to database
connect('bitgpt', host='mongodb://localhost:27017/')

def create_test_user(name, refered_by_id):
    """Create a test user"""
    import random
    import string
    
    # Generate unique UID and refer code
    uid = ''.join(random.choices(string.digits, k=10))
    refer_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    wallet_address = '0x' + ''.join(random.choices(string.hexdigits.lower(), k=40))
    
    user = User(
        name=name,
        email=f"{name.lower()}@test.com",
        refered_by=ObjectId(refered_by_id),
        password="test123",
        uid=uid,
        refer_code=refer_code,
        wallet_address=wallet_address
    )
    user.save()
    
    # Create wallet
    wallet = UserWallet(user_id=user.id)
    wallet.save()
    
    return str(user.id)

def get_reserve_balance(user_id, slot_no):
    """Get reserve balance for a user and slot"""
    ledger_entries = ReserveLedger.objects(
        user_id=ObjectId(user_id),
        program='matrix',
        slot_no=slot_no
    ).order_by('-created_at')
    
    if ledger_entries:
        return ledger_entries[0].balance_after
    return Decimal('0')

def check_slot_activated(user_id, slot_no):
    """Check if a slot is activated"""
    activation = MatrixActivation.objects(
        user_id=ObjectId(user_id),
        slot_no=slot_no,
        status='completed'
    ).first()
    return activation is not None

def main():
    print("🧪 Testing Matrix Middle Child Detection and Auto-Upgrade")
    print("=" * 60)
    
    # Find root user (try different possible names)
    root = User.objects(id=ObjectId('000000000000000000000001')).first()
    if not root:
        root = User.objects(name='Mother').first()
    if not root:
        root = User.objects(name='Root').first()
    if not root:
        # Get any user with minimal ID
        root = User.objects().order_by('id').first()
    
    if not root:
        print("❌ No root account found!")
        return
    
    ROOT_ID = str(root.id)
    print(f"✅ Found root account: {ROOT_ID} ({root.name})")
    
    svc = MatrixService()
    
    # Create main user (Tree Owner)
    print("\n--- Step 1: Creating Tree Owner ---")
    owner_id = create_test_user(f"TestOwner_{int(datetime.utcnow().timestamp())}", ROOT_ID)
    print(f"✅ Created Owner: {owner_id}")
    
    # Join owner to Slot 1
    print("\n--- Step 2: Joining Owner to Slot 1 ---")
    tx_owner = f"tx_owner_{datetime.utcnow().timestamp()}"
    res = svc.join_matrix(user_id=owner_id, referrer_id=ROOT_ID, tx_hash=tx_owner, amount=Decimal("11"))
    if not res.get("success"):
        print(f"❌ Failed to join Owner: {res}")
        return
    print("✅ Owner joined Slot 1")
    
    # Get owner's tree
    owner_tree = MatrixTree.objects(user_id=ObjectId(owner_id), slot_no=1).first()
    if not owner_tree:
        print("❌ Owner tree not found!")
        return
    
    print(f"✅ Owner tree ID: {owner_tree.id}")
    
    # Create 12 downline users and join them
    print("\n--- Step 3: Creating 12 Downline Users ---")
    downline_ids = []
    for i in range(1, 13):
        uid = create_test_user(f"TestD{i}_{int(datetime.utcnow().timestamp())}", owner_id)
        downline_ids.append(uid)
        print(f"✅ Created D{i}: {uid}")
    
    # Join downlines to Slot 1
    print("\n--- Step 4: Joining Downlines to Slot 1 ---")
    middle_children_count = 0
    for i, uid in enumerate(downline_ids, 1):
        tx = f"tx_d{i}_{datetime.utcnow().timestamp()}"
        res = svc.join_matrix(user_id=uid, referrer_id=owner_id, tx_hash=tx, amount=Decimal("11"))
        if not res.get("success"):
            print(f"❌ D{i} failed: {res}")
        else:
            # Check placement
            placement = TreePlacement.objects(
                user_id=ObjectId(uid),
                program='matrix',
                slot_no=1
            ).first()
            
            if placement:
                level = placement.level
                position = placement.position
                is_middle = (level == 2 and position in [1, 4, 7])
                
                if is_middle:
                    middle_children_count += 1
                    print(f"✅ D{i} joined - Level {level}, Position {position} [MIDDLE CHILD #{middle_children_count}]")
                else:
                    print(f"✅ D{i} joined - Level {level}, Position {position}")
            else:
                print(f"✅ D{i} joined")
    
    # Check reserve balance
    print("\n--- Step 5: Checking Reserve Balance ---")
    reserve_balance = get_reserve_balance(owner_id, 1)
    print(f"Reserve Balance for Owner (Slot 1): {reserve_balance} USDT")
    print(f"Middle Children Detected: {middle_children_count}")
    print(f"Expected Reserve: {middle_children_count * 11} USDT")
    
    # Check if Slot 2 is activated
    print("\n--- Step 6: Checking Slot 2 Activation ---")
    slot2_activated = check_slot_activated(owner_id, 2)
    
    if slot2_activated:
        print("✅ Slot 2 ACTIVATED (Auto-Upgrade Success!)")
    else:
        print("❌ Slot 2 NOT ACTIVATED")
        
        if reserve_balance >= 33:
            print(f"⚠️ Reserve ({reserve_balance}) >= 33 but auto-upgrade didn't trigger!")
        else:
            print(f"ℹ️ Reserve ({reserve_balance}) < 33, auto-upgrade not expected yet")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Middle Children Detected: {middle_children_count} / 3")
    print(f"Reserve Balance: {reserve_balance} USDT")
    print(f"Slot 2 Activated: {'YES ✅' if slot2_activated else 'NO ❌'}")
    
    if middle_children_count == 3 and reserve_balance == 33 and slot2_activated:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("\n❌ TESTS FAILED")
        if middle_children_count != 3:
            print(f"  - Expected 3 middle children, got {middle_children_count}")
        if reserve_balance != 33:
            print(f"  - Expected 33 USDT reserve, got {reserve_balance}")
        if not slot2_activated:
            print(f"  - Slot 2 should be auto-activated")
        return 1

if __name__ == "__main__":
    sys.exit(main())
