#!/usr/bin/env python3
"""
Test A's Slot 4 auto-upgrade after Slot 3 auto-upgrade
Creates tree structure and activates slots to trigger cascade
"""

import requests
import json
import time
import random
from bson import ObjectId
from mongoengine import connect
from modules.user.model import User
from modules.slot.model import SlotActivation, SlotCatalog
from modules.auto_upgrade.service import AutoUpgradeService
from modules.tree.service import TreeService
from decimal import Decimal

BASE_URL = "http://localhost:8000"
A_USER_ID = "69073613a4f0f2f7a50d444b"  # A user ID from response

def temp_create_user(name: str, refer_code: str):
    """Create user using temp-create API"""
    email = f"{name.lower().replace(' ', '_')}{int(time.time() * 1000)}@test.com"
    
    payload = {
        "email": email,
        "name": name,
        "refered_by": refer_code,
        "wallet_address": f"0x{''.join(random.choices('0123456789abcdef', k=40))}"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/user/temp-create", json=payload)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "Ok":
            user_data = data.get("data", {})
            user_refer_code = user_data.get("refer_code") or user_data.get("user", {}).get("refer_code")
            user_id = user_data.get("_id") or user_data.get("user", {}).get("_id")
            print(f"✅ Created {name}: {user_refer_code} (ID: {user_id})")
            return user_refer_code, user_id
        else:
            print(f"❌ Failed to create {name}: {data.get('message', 'Unknown error')}")
            return None, None
    except Exception as e:
        print(f"❌ Error creating {name}: {str(e)}")
        return None, None

def activate_slot3_for_user(user_id: str, slot_value: Decimal):
    """Activate Slot 3 for a user using AutoUpgradeService"""
    try:
        auto_upgrade_service = AutoUpgradeService()
        result = auto_upgrade_service.process_binary_slot_activation(
            user_id=user_id,
            slot_no=3,
            slot_value=slot_value
        )
        return result
    except Exception as e:
        print(f"❌ Error activating Slot 3 for {user_id}: {e}")
        return {"success": False, "error": str(e)}

def main():
    # Connect to database
    try:
        connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')
        print("✅ Connected to MongoDB Atlas\n")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        exit(1)
    
    # Get A user
    a_user = User.objects(id=ObjectId(A_USER_ID)).first()
    if not a_user:
        print(f"❌ User A not found: {A_USER_ID}")
        exit(1)
    
    a_refer_code = a_user.refer_code
    print("=" * 80)
    print(f"TESTING A's SLOT 4 AUTO-UPGRADE")
    print(f"A User: {a_user.uid} ({a_refer_code})")
    print("=" * 80)
    
    # Wait a bit for background tasks
    print("\n⏳ Waiting 5 seconds for background tree placements...")
    time.sleep(5)
    
    # Step 1: Create Level 1 users (children of A)
    print("\n" + "=" * 80)
    print("STEP 1: Creating Level 1 users (children of A)")
    print("=" * 80)
    time.sleep(1)
    l1_left_code, l1_left_id = temp_create_user("L1_Left", a_refer_code)
    time.sleep(1)
    l1_right_code, l1_right_id = temp_create_user("L1_Right", a_refer_code)
    time.sleep(5)  # Wait for placements
    
    # Step 2: Create Level 2 users
    print("\n" + "=" * 80)
    print("STEP 2: Creating Level 2 users")
    print("=" * 80)
    time.sleep(1)
    l2_left_left_code, _ = temp_create_user("L2_LeftLeft", l1_left_code)
    time.sleep(1)
    l2_left_right_code, _ = temp_create_user("L2_LeftRight", l1_left_code)
    time.sleep(1)
    l2_right_left_code, _ = temp_create_user("L2_RightLeft", l1_right_code)
    time.sleep(5)
    
    # Step 3: Create Level 3 users (S2 and S3)
    print("\n" + "=" * 80)
    print("STEP 3: Creating Level 3 users (S2 and S3)")
    print("=" * 80)
    time.sleep(1)
    s2_code, s2_id = temp_create_user("S2", l2_left_left_code)
    time.sleep(1)
    s2_sibling_code, _ = temp_create_user("S2_Sibling", l2_left_left_code)
    time.sleep(1)
    s3_code, s3_id = temp_create_user("S3", l2_left_right_code)
    time.sleep(1)
    s3_sibling_code, _ = temp_create_user("S3_Sibling", l2_left_right_code)
    time.sleep(5)
    
    # Step 4: Create Slot 3 placements for S2 and S3
    print("\n" + "=" * 80)
    print("STEP 4: Creating Slot 3 tree placements for S2 and S3")
    print("=" * 80)
    tree_service = TreeService()
    
    l2_left_left_user = User.objects(refer_code=l2_left_left_code).first()
    l2_left_right_user = User.objects(refer_code=l2_left_right_code).first()
    s2_user = User.objects(id=ObjectId(s2_id)).first() if s2_id else None
    s3_user = User.objects(id=ObjectId(s3_id)).first() if s3_id else None
    
    if s2_user and l2_left_left_user:
        s2_placement = tree_service.place_user_in_tree(
            user_id=s2_user.id,
            referrer_id=l2_left_left_user.id,
            program='binary',
            slot_no=3
        )
        print(f"✅ S2 Slot 3 placement: {s2_placement}")
    time.sleep(1)
    
    if s3_user and l2_left_right_user:
        s3_placement = tree_service.place_user_in_tree(
            user_id=s3_user.id,
            referrer_id=l2_left_right_user.id,
            program='binary',
            slot_no=3
        )
        print(f"✅ S3 Slot 3 placement: {s3_placement}")
    time.sleep(2)
    
    # Step 5: Create S2 and S3 downline users
    print("\n" + "=" * 80)
    print("STEP 5: Creating S2 and S3 downline users")
    print("=" * 80)
    time.sleep(1)
    s2_left_code, s2_left_id = temp_create_user("S2_Left", s2_code)
    time.sleep(1)
    s2_right_code, s2_right_id = temp_create_user("S2_Right", s2_code)
    time.sleep(1)
    s3_left_code, s3_left_id = temp_create_user("S3_Left", s3_code)
    time.sleep(1)
    s3_right_code, s3_right_id = temp_create_user("S3_Right", s3_code)
    time.sleep(5)
    
    # Step 6: Create Slot 3 placements for downline users first
    print("\n" + "=" * 80)
    print("STEP 6: Creating Slot 3 placements for downline users")
    print("=" * 80)
    
    s2_user = User.objects(id=ObjectId(s2_id)).first() if s2_id else None
    s3_user = User.objects(id=ObjectId(s3_id)).first() if s3_id else None
    
    # Create placements for S2's downlines
    if s2_left_id:
        s2_left_user = User.objects(id=ObjectId(s2_left_id)).first()
        if s2_left_user and s2_user:
            placement = tree_service.place_user_in_tree(
                user_id=s2_left_user.id,
                referrer_id=s2_user.id,
                program='binary',
                slot_no=3
            )
            print(f"✅ S2_Left Slot 3 placement: {placement}")
            time.sleep(1)
    
    if s2_right_id:
        s2_right_user = User.objects(id=ObjectId(s2_right_id)).first()
        if s2_right_user and s2_user:
            placement = tree_service.place_user_in_tree(
                user_id=s2_right_user.id,
                referrer_id=s2_user.id,
                program='binary',
                slot_no=3
            )
            print(f"✅ S2_Right Slot 3 placement: {placement}")
            time.sleep(1)
    
    # Create placements for S3's downlines
    if s3_left_id:
        s3_left_user = User.objects(id=ObjectId(s3_left_id)).first()
        if s3_left_user and s3_user:
            placement = tree_service.place_user_in_tree(
                user_id=s3_left_user.id,
                referrer_id=s3_user.id,
                program='binary',
                slot_no=3
            )
            print(f"✅ S3_Left Slot 3 placement: {placement}")
            time.sleep(1)
    
    if s3_right_id:
        s3_right_user = User.objects(id=ObjectId(s3_right_id)).first()
        if s3_right_user and s3_user:
            placement = tree_service.place_user_in_tree(
                user_id=s3_right_user.id,
                referrer_id=s3_user.id,
                program='binary',
                slot_no=3
            )
            print(f"✅ S3_Right Slot 3 placement: {placement}")
            time.sleep(2)
    
    # Step 7: Activate Slot 3 for S2's downline users
    print("\n" + "=" * 80)
    print("STEP 7: Activating Slot 3 for S2's downline users")
    print("=" * 80)
    
    slot3_cost = Decimal('0.0088')  # Slot 3 cost
    
    if s2_left_id:
        s2_left_user = User.objects(id=ObjectId(s2_left_id)).first()
        if s2_left_user:
            print(f"\nActivating Slot 3 for S2_Left ({s2_left_user.uid})...")
            result = activate_slot3_for_user(s2_left_id, slot3_cost)
            if result.get("success"):
                print(f"✅ S2_Left Slot 3 activated")
                print(f"   Result: {result.get('message', 'Success')}")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown')}")
            time.sleep(2)
    
    if s2_right_id:
        s2_right_user = User.objects(id=ObjectId(s2_right_id)).first()
        if s2_right_user:
            print(f"\nActivating Slot 3 for S2_Right ({s2_right_user.uid})...")
            result = activate_slot3_for_user(s2_right_id, slot3_cost)
            if result.get("success"):
                print(f"✅ S2_Right Slot 3 activated")
                print(f"   Result: {result.get('message', 'Success')}")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown')}")
            time.sleep(2)
    
    # Step 8: Activate Slot 3 for S3's downline users
    print("\n" + "=" * 80)
    print("STEP 7: Activating Slot 3 for S3's downline users")
    print("=" * 80)
    
    if s3_left_id:
        s3_left_user = User.objects(id=ObjectId(s3_left_id)).first()
        if s3_left_user:
            print(f"\nActivating Slot 3 for S3_Left ({s3_left_user.uid})...")
            result = activate_slot3_for_user(s3_left_id, slot3_cost)
            if result.get("success"):
                print(f"✅ S3_Left Slot 3 activated")
                print(f"   Result: {result.get('message', 'Success')}")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown')}")
            time.sleep(2)
    
    if s3_right_id:
        s3_right_user = User.objects(id=ObjectId(s3_right_id)).first()
        if s3_right_user:
            print(f"\nActivating Slot 3 for S3_Right ({s3_right_user.uid})...")
            result = activate_slot3_for_user(s3_right_id, slot3_cost)
            if result.get("success"):
                print(f"✅ S3_Right Slot 3 activated")
                print(f"   Result: {result.get('message', 'Success')}")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown')}")
            time.sleep(2)
    
    # Step 9: Check A's slot activations
    print("\n" + "=" * 80)
    print("STEP 8: Checking A's Slot Activations")
    print("=" * 80)
    time.sleep(5)  # Wait for cascades
    
    a_activations = SlotActivation.objects(
        user_id=a_user.id, 
        program='binary', 
        status='completed'
    ).order_by('slot_no')
    
    print(f"\nA's Activated Slots:")
    for act in a_activations:
        print(f"  ✅ Slot {act.slot_no} ({act.slot_name}): {act.amount_paid} BNB")
        print(f"     - Upgrade Source: {act.upgrade_source}")
        print(f"     - Is Auto Upgrade: {act.is_auto_upgrade}")
        print(f"     - Activated At: {act.activated_at}")
    
    if a_activations:
        highest_slot = max([a.slot_no for a in a_activations])
        print(f"\n🎯 Highest Activated Slot: {highest_slot}")
        
        if highest_slot >= 4:
            print("\n🎉 SUCCESS! A's Slot 4 auto-upgraded!")
        else:
            print(f"\n⚠️  A's Slot 4 not yet upgraded (current: Slot {highest_slot})")
    else:
        print("\n❌ No slot activations found for A")
    
    # Check reserve funds
    from modules.wallet.model import ReserveLedger
    print("\n" + "=" * 80)
    print("STEP 10: Checking A's Reserve Funds for Slot 4")
    print("=" * 80)
    
    slot4_reserves = ReserveLedger.objects(user_id=a_user.id, program='binary', slot_no=4)
    total_reserve = Decimal('0')
    for reserve in slot4_reserves:
        if reserve.direction == 'credit':
            total_reserve += reserve.amount
        elif reserve.direction == 'debit':
            total_reserve -= reserve.amount
        print(f"  {reserve.direction.upper()}: {reserve.amount} BNB - {reserve.source}")
    
    slot4_catalog = SlotCatalog.objects(program='binary', slot_no=4, is_active=True).first()
    if slot4_catalog:
        slot4_cost = slot4_catalog.price
        print(f"\n  💵 Total Reserve: {total_reserve} BNB")
        print(f"  📋 Slot 4 Cost: {slot4_cost} BNB")
        print(f"  {'✅' if total_reserve >= slot4_cost else '❌'} Can Auto-Upgrade: {total_reserve >= slot4_cost}")
    
    print("\n" + "=" * 80)
    print("✅ Test Complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()

