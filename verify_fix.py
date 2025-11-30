import sys
import os
import time
from decimal import Decimal
from bson import ObjectId

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from core.db import connect_to_db
from modules.user.model import User
from modules.matrix.service import MatrixService
from modules.dream_matrix.service import DreamMatrixService
from modules.tree.model import TreePlacement
from modules.slot.model import SlotActivation
from modules.matrix.model import MatrixActivation
from modules.auto_upgrade.model import MatrixAutoUpgrade

def run_verification():
    # Connect to DB
    connect_to_db()
    
    print("Starting Verification for Matrix Auto-Upgrade Placement Fix...")
    
    # 1. Setup: Create Users
    matrix_service = MatrixService()
    dream_matrix_service = DreamMatrixService()
    
    # Create Root User (A)
    # Create a dummy referrer for A
    dummy_ref_id = str(ObjectId())
    
    user_a = User(
        wallet_address="0xRootUserA" + str(int(time.time())),
        uid="UserA_" + str(int(time.time())),
        refer_code="REF_A_" + str(int(time.time())),
        name="UserA",
        email=f"usera_{int(time.time())}@test.com"
    ).save()
    print(f"Created User A: {user_a.id}")
    
    # Join A to Matrix Slot 1
    matrix_service.join_matrix(str(user_a.id), dummy_ref_id, "0xHashA", Decimal('11'))
    print("User A joined Matrix Slot 1")
    
    # Create L1 User (Child of A)
    user_l1 = User(
        wallet_address="0xUserL1" + str(int(time.time())),
        uid="UserL1_" + str(int(time.time())),
        refer_code="REF_L1_" + str(int(time.time())),
        name="UserL1",
        email=f"userl1_{int(time.time())}@test.com",
        refered_by=user_a.id
    ).save()
    print(f"Created User L1: {user_l1.id}")
    
    # Join L1 to Matrix Slot 1
    matrix_service.join_matrix(str(user_l1.id), str(user_a.id), "0xHashL1", Decimal('11'))
    print("User L1 joined Matrix Slot 1")
    
    # Create 3 L2 Users (Children of L1)
    l2_users = []
    for i in range(3):
        u = User(
            wallet_address=f"0xUserL2_{i}_" + str(int(time.time())),
            uid=f"UserL2_{i}_" + str(int(time.time())),
            refer_code=f"REF_L2_{i}_" + str(int(time.time())),
            name=f"UserL2_{i}",
            email=f"userl2_{i}_{int(time.time())}@test.com",
            refered_by=user_l1.id
        ).save()
        matrix_service.join_matrix(str(u.id), str(user_l1.id), f"0xHashL2_{i}", Decimal('11'))
        l2_users.append(u)
    print(f"Created 3 L2 users under L1")
    
    # Create Middle Children for each L2 User (Grandchildren of L1)
    # We need the 2nd child (position 1) for each L2 user to trigger "middle 3" logic
    # So we need to create Child 1, then Child 2 (Middle) for each L2
    
    print("Creating grandchildren to fill middle positions...")
    for idx, l2_user in enumerate(l2_users):
        # Child 1 (Left)
        c1 = User(
            wallet_address=f"0xUserL3_{idx}_1_" + str(int(time.time())),
            uid=f"UserL3_{idx}_1_" + str(int(time.time())),
            refer_code=f"REF_L3_{idx}_1_" + str(int(time.time())),
            name=f"UserL3_{idx}_1",
            email=f"userl3_{idx}_1_{int(time.time())}@test.com",
            refered_by=l2_user.id
        ).save()
        matrix_service.join_matrix(str(c1.id), str(l2_user.id), f"0xHashL3_{idx}_1", Decimal('11'))
        
        # Child 2 (Middle) - This is the one that counts for auto-upgrade
        c2 = User(
            wallet_address=f"0xUserL3_{idx}_2_" + str(int(time.time())),
            uid=f"UserL3_{idx}_2_" + str(int(time.time())),
            refer_code=f"REF_L3_{idx}_2_" + str(int(time.time())),
            name=f"UserL3_{idx}_2",
            email=f"userl3_{idx}_2_{int(time.time())}@test.com",
            refered_by=l2_user.id
        ).save()
        matrix_service.join_matrix(str(c2.id), str(l2_user.id), f"0xHashL3_{idx}_2", Decimal('11'))
        print(f"  Created middle child for L2_{idx}")

    # At this point, L1 should have 3 middle grandchildren.
    # Check eligibility
    print("Checking auto-upgrade eligibility for L1...")
    eligibility = matrix_service.detect_middle_three_members(str(user_l1.id), 1)
    print(f"Eligibility result: {eligibility.get('success')} - Found: {eligibility.get('total_found')}")
    
    if eligibility.get('total_found') != 3:
        print("❌ Setup failed: Did not find 3 middle members.")
        return

    # Trigger Auto-Upgrade for L1 to Slot 2
    print("Triggering auto-upgrade for L1 to Slot 2...")
    upgrade_result = matrix_service.process_automatic_upgrade(str(user_l1.id), 1)
    print(f"Upgrade Result: {upgrade_result}")
    
    if not upgrade_result.get('success'):
        print(f"❌ Auto-upgrade failed: {upgrade_result.get('error')}")
        return
        
    # VERIFICATION 1: Check if MatrixActivation exists (it should)
    activation = MatrixActivation.objects(user_id=user_l1.id, slot_no=2).first()
    if activation:
        print("✅ MatrixActivation for Slot 2 found.")
    else:
        print("❌ MatrixActivation for Slot 2 NOT found.")
        
    # VERIFICATION 2: Check if TreePlacement exists for Slot 2 (THE FIX)
    placement = TreePlacement.objects(
        user_id=user_l1.id,
        program='matrix',
        slot_no=2,
        is_active=True
    ).first()
    
    if placement:
        print(f"✅ TreePlacement for Slot 2 found! ID: {placement.id}")
    else:
            print(f"⚠️ L1 placed under {placement.upline_id}, expected {user_a.id}. (Might be okay if A wasn't ready when L1 upgraded)")
    
    # Check L1's earnings API for Slot 2 (should show L1 as root of their own tree)
    print("Checking Earnings API for User L1, Slot 2...")
    earnings = dream_matrix_service.get_dream_matrix_earnings(str(user_l1.id), slot_no=2)
    
    # Verify structure
    # earnings['matrix_trees'] should contain slot 2 data
    slot_2_data = next((t for t in earnings.get('matrix_trees', []) if t['slot'] == 2), None)
    
    if slot_2_data:
        print("✅ Slot 2 tree data returned in API.")
        # Check if L1 is in the tree (should be the root)
        root_node = slot_2_data.get('tree', {})
        if root_node.get('userId') == str(user_l1.id):
                print("✅ L1 is visible as root in Slot 2 tree.")
        else:
                print(f"❌ L1 not found as root. Found: {root_node.get('userId')}")
    else:
        print("❌ Slot 2 tree data MISSING in API response.")

if __name__ == "__main__":
    run_verification()
