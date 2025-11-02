#!/usr/bin/env python3
"""
Batch script to manually upgrade users from Slot 3 to Slot 4
Checks reserve funds and wallet debit
"""
import sys
from mongoengine import connect
from bson import ObjectId
from decimal import Decimal
from datetime import datetime

# Connect to database
try:
    connect('bitgpt', host='mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt')
    print("✅ Connected to MongoDB Atlas\n")
except Exception as e:
    print(f"❌ Failed to connect to database: {e}")
    exit(1)

from modules.slot.model import SlotActivation
from modules.wallet.model import ReserveLedger, WalletLedger, UserWallet
from modules.auto_upgrade.service import AutoUpgradeService
from modules.user.tree_reserve_service import TreeUplineReserveService
from modules.wallet.service import WalletService

print("=" * 80)
print("BATCH MANUAL UPGRADE: Slot 3 → Slot 4")
print("=" * 80)

# Find all users with Slot 3 completed but Slot 4 not completed
slot3_users = SlotActivation.objects(
    program='binary',
    slot_no=3,
    status='completed'
).distinct('user_id')

print(f"\nFound {len(slot3_users)} users with Slot 3 activated")

# Filter: Only users who don't have Slot 4
users_to_upgrade = []
for user_id in slot3_users:
    slot4 = SlotActivation.objects(
        user_id=user_id,
        program='binary',
        slot_no=4,
        status='completed'
    ).first()
    
    if not slot4:
        users_to_upgrade.append(user_id)

print(f"Users needing Slot 4 upgrade: {len(users_to_upgrade)}\n")

if len(users_to_upgrade) == 0:
    print("No users need Slot 4 upgrade")
    exit(0)

# Initialize services
auto_upgrade_service = AutoUpgradeService()
reserve_service = TreeUplineReserveService()
wallet_service = WalletService()

# Process first 10 users (for testing)
test_users = users_to_upgrade[:10]
print(f"Processing {len(test_users)} users for testing...\n")

success_count = 0
failed_count = 0

for i, user_id in enumerate(test_users, 1):
    user_oid = user_id
    user_id_str = str(user_id)
    
    print("=" * 80)
    print(f"[{i}/{len(test_users)}] Processing User: {user_id_str}")
    print("=" * 80)
    
    try:
        # Check reserve balance for Slot 4
        reserve_balance = reserve_service.get_reserve_balance(user_id_str, 'binary', 4)
        slot4_cost = auto_upgrade_service._get_binary_slot_cost(4)
        
        print(f"\n💰 Reserve Balance (Slot 4): {reserve_balance} BNB")
        print(f"💰 Slot 4 Cost: {slot4_cost} BNB")
        
        # Check wallet balance
        wallet = wallet_service._get_or_create_wallet(user_id_str, 'main', 'BNB')
        wallet_balance = wallet.balance or Decimal('0')
        print(f"💰 Wallet Balance: {wallet_balance} BNB")
        
        # Calculate expected payments
        reserve_amount = min(reserve_balance, slot4_cost)
        wallet_amount = slot4_cost - reserve_amount
        
        print(f"\n📊 Expected Payment Breakdown:")
        print(f"   Reserve Payment: {reserve_amount} BNB")
        print(f"   Wallet Payment: {wallet_amount} BNB")
        print(f"   Total: {reserve_amount + wallet_amount} BNB")
        
        if wallet_amount > 0 and wallet_balance < wallet_amount:
            print(f"\n⚠️  Insufficient wallet balance! Need {wallet_amount}, have {wallet_balance}")
            print(f"   Skipping this user...")
            failed_count += 1
            continue
        
        # Get reserve ledger count before
        reserve_debit_count_before = ReserveLedger.objects(
            user_id=user_oid,
            program='binary',
            slot_no=4,
            direction='debit'
        ).count()
        
        # Get wallet ledger count before
        wallet_debit_count_before = WalletLedger.objects(
            user_id=user_oid,
            type='debit',
            currency='BNB'
        ).count()
        
        print(f"\n📝 Before Upgrade:")
        print(f"   Reserve Debit Entries: {reserve_debit_count_before}")
        print(f"   Wallet Debit Entries: {wallet_debit_count_before}")
        
        # Perform manual upgrade
        print(f"\n🚀 Starting manual upgrade...")
        result = auto_upgrade_service.manual_upgrade_binary_slot(
            user_id=user_id_str,
            slot_no=4,
            tx_hash=f"batch_upgrade_slot4_{user_id_str}_{int(datetime.utcnow().timestamp())}"
        )
        
        if result.get("success"):
            print(f"✅ Upgrade successful!")
            print(f"   Reserve Used: {result.get('reserve_used', 0)} BNB")
            print(f"   Wallet Used: {result.get('wallet_used', 0)} BNB")
            
            # Verify reserve debit
            reserve_debit_count_after = ReserveLedger.objects(
                user_id=user_oid,
                program='binary',
                slot_no=4,
                direction='debit'
            ).count()
            
            if reserve_amount > 0:
                if reserve_debit_count_after > reserve_debit_count_before:
                    latest_reserve_debit = ReserveLedger.objects(
                        user_id=user_oid,
                        program='binary',
                        slot_no=4,
                        direction='debit'
                    ).order_by('-created_at').first()
                    
                    if latest_reserve_debit:
                        print(f"\n✅ Reserve Debit Verified:")
                        print(f"   Amount: {latest_reserve_debit.amount} BNB")
                        print(f"   Expected: {reserve_amount} BNB")
                        print(f"   Match: {'✅' if latest_reserve_debit.amount == reserve_amount else '❌'}")
                else:
                    print(f"\n❌ Reserve Debit NOT Created! (Expected: {reserve_amount} BNB)")
            else:
                print(f"\n⏭️  No Reserve Debit (no reserve balance)")
            
            # Verify wallet debit
            wallet_debit_count_after = WalletLedger.objects(
                user_id=user_oid,
                type='debit',
                currency='BNB'
            ).count()
            
            if wallet_amount > 0:
                if wallet_debit_count_after > wallet_debit_count_before:
                    latest_wallet_debit = WalletLedger.objects(
                        user_id=user_oid,
                        type='debit',
                        currency='BNB'
                    ).order_by('-created_at').first()
                    
                    if latest_wallet_debit:
                        print(f"\n✅ Wallet Debit Verified:")
                        print(f"   Amount: {latest_wallet_debit.amount} BNB")
                        print(f"   Expected: {wallet_amount} BNB")
                        print(f"   Match: {'✅' if latest_wallet_debit.amount == wallet_amount else '❌'}")
                else:
                    print(f"\n❌ Wallet Debit NOT Created! (Expected: {wallet_amount} BNB)")
            else:
                print(f"\n⏭️  No Wallet Debit (reserve covered full cost)")
            
            # Verify SlotActivation
            slot4_activation = SlotActivation.objects(
                user_id=user_oid,
                program='binary',
                slot_no=4,
                status='completed'
            ).order_by('-created_at').first()
            
            if slot4_activation:
                print(f"\n✅ SlotActivation Verified:")
                print(f"   Activation Type: {slot4_activation.activation_type}")
                print(f"   Upgrade Source: {slot4_activation.upgrade_source}")
                print(f"   Amount Paid: {slot4_activation.amount_paid} BNB")
                if slot4_activation.metadata:
                    print(f"   Reserve Used (metadata): {slot4_activation.metadata.get('reserve_used', 'N/A')} BNB")
                    print(f"   Wallet Used (metadata): {slot4_activation.metadata.get('wallet_used', 'N/A')} BNB")
            
            success_count += 1
        else:
            print(f"\n❌ Upgrade failed: {result.get('error')}")
            failed_count += 1
        
        print()  # Empty line
        
    except Exception as e:
        print(f"\n❌ Error processing user {user_id_str}: {e}")
        import traceback
        traceback.print_exc()
        failed_count += 1
        print()

print("=" * 80)
print("BATCH UPGRADE SUMMARY")
print("=" * 80)
print(f"Total Processed: {len(test_users)}")
print(f"✅ Successful: {success_count}")
print(f"❌ Failed: {failed_count}")
print("=" * 80)

