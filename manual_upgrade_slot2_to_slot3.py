#!/usr/bin/env python3
"""
Manual upgrade a user from Slot 2 to Slot 3
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
print("MANUAL UPGRADE: Slot 2 → Slot 3")
print("=" * 80)

# Find a user with Slot 2 active but Slot 3 not active
slot2_users = SlotActivation.objects(
    program='binary',
    slot_no=2,
    status='completed'
).order_by('-created_at')

print(f"\nFound {len(slot2_users)} users with Slot 2 activated")

# Find first user without Slot 3
target_user = None
for slot2_activation in slot2_users[:10]:  # Check first 10
    user_id = slot2_activation.user_id
    slot3 = SlotActivation.objects(
        user_id=user_id,
        program='binary',
        slot_no=3,
        status='completed'
    ).first()
    
    if not slot3:
        target_user = user_id
        break

if not target_user:
    print("❌ No user found with Slot 2 active but Slot 3 inactive")
    exit(0)

user_id_str = str(target_user)
print(f"\n✅ Target User: {user_id_str}")
print("=" * 80)

try:
    # Initialize services
    auto_upgrade_service = AutoUpgradeService()
    reserve_service = TreeUplineReserveService()
    wallet_service = WalletService()
    
    # Check reserve balance for Slot 3
    reserve_balance = reserve_service.get_reserve_balance(user_id_str, 'binary', 3)
    slot3_cost = auto_upgrade_service._get_binary_slot_cost(3)
    
    print(f"\n💰 Reserve Balance (Slot 3): {reserve_balance} BNB")
    print(f"💰 Slot 3 Cost: {slot3_cost} BNB")
    
    # Check wallet balance
    wallet = wallet_service._get_or_create_wallet(user_id_str, 'main', 'BNB')
    wallet_balance = wallet.balance or Decimal('0')
    print(f"💰 Wallet Balance: {wallet_balance} BNB")
    
    # Calculate expected payments
    reserve_amount = min(reserve_balance, slot3_cost)
    wallet_amount = slot3_cost - reserve_amount
    
    print(f"\n📊 Expected Payment Breakdown:")
    print(f"   Reserve Payment: {reserve_amount} BNB")
    print(f"   Wallet Payment: {wallet_amount} BNB")
    print(f"   Total: {reserve_amount + wallet_amount} BNB")
    
    if wallet_amount > 0 and wallet_balance < wallet_amount:
        print(f"\n❌ Insufficient wallet balance! Need {wallet_amount}, have {wallet_balance}")
        exit(1)
    
    # Get reserve ledger count before
    reserve_debit_count_before = ReserveLedger.objects(
        user_id=target_user,
        program='binary',
        slot_no=3,
        direction='debit'
    ).count()
    
    # Get wallet ledger count before
    wallet_debit_count_before = WalletLedger.objects(
        user_id=target_user,
        type='debit',
        currency='BNB'
    ).count()
    
    print(f"\n📝 Before Upgrade:")
    print(f"   Reserve Debit Entries: {reserve_debit_count_before}")
    print(f"   Wallet Debit Entries: {wallet_debit_count_before}")
    
    # Perform manual upgrade
    print(f"\n🚀 Starting manual upgrade to Slot 3...")
    result = auto_upgrade_service.manual_upgrade_binary_slot(
        user_id=user_id_str,
        slot_no=3,
        tx_hash=f"manual_upgrade_slot3_{user_id_str}_{int(datetime.utcnow().timestamp())}"
    )
    
    if result.get("success"):
        print(f"\n✅ Upgrade successful!")
        print(f"   Activation ID: {result.get('activation_id')}")
        print(f"   Slot Name: {result.get('slot_name')}")
        print(f"   Amount Paid: {result.get('amount_paid')} BNB")
        print(f"   Reserve Used: {result.get('reserve_used', 0)} BNB")
        print(f"   Wallet Used: {result.get('wallet_used', 0)} BNB")
        
        # Verify reserve debit
        reserve_debit_count_after = ReserveLedger.objects(
            user_id=target_user,
            program='binary',
            slot_no=3,
            direction='debit'
        ).count()
        
        if reserve_amount > 0:
            if reserve_debit_count_after > reserve_debit_count_before:
                latest_reserve_debit = ReserveLedger.objects(
                    user_id=target_user,
                    program='binary',
                    slot_no=3,
                    direction='debit'
                ).order_by('-created_at').first()
                
                if latest_reserve_debit:
                    print(f"\n✅ Reserve Debit Verified:")
                    print(f"   Amount: {latest_reserve_debit.amount} BNB")
                    print(f"   Expected: {reserve_amount} BNB")
                    print(f"   Balance After: {latest_reserve_debit.balance_after} BNB")
                    print(f"   Match: {'✅' if latest_reserve_debit.amount == reserve_amount else '❌'}")
            else:
                print(f"\n❌ Reserve Debit NOT Created! (Expected: {reserve_amount} BNB)")
        else:
            print(f"\n⏭️  No Reserve Debit (no reserve balance)")
        
        # Verify wallet debit
        wallet_debit_count_after = WalletLedger.objects(
            user_id=target_user,
            type='debit',
            currency='BNB'
        ).count()
        
        if wallet_amount > 0:
            if wallet_debit_count_after > wallet_debit_count_before:
                latest_wallet_debit = WalletLedger.objects(
                    user_id=target_user,
                    type='debit',
                    currency='BNB'
                ).order_by('-created_at').first()
                
                if latest_wallet_debit:
                    print(f"\n✅ Wallet Debit Verified:")
                    print(f"   Amount: {latest_wallet_debit.amount} BNB")
                    print(f"   Expected: {wallet_amount} BNB")
                    print(f"   Balance After: {latest_wallet_debit.balance_after} BNB")
                    print(f"   Match: {'✅' if latest_wallet_debit.amount == wallet_amount else '❌'}")
            else:
                print(f"\n❌ Wallet Debit NOT Created! (Expected: {wallet_amount} BNB)")
        else:
            print(f"\n⏭️  No Wallet Debit (reserve covered full cost)")
        
        # Verify SlotActivation
        slot3_activation = SlotActivation.objects(
            user_id=target_user,
            program='binary',
            slot_no=3,
            status='completed'
        ).order_by('-created_at').first()
        
        if slot3_activation:
            print(f"\n✅ SlotActivation Verified:")
            print(f"   Activation Type: {slot3_activation.activation_type}")
            print(f"   Upgrade Source: {slot3_activation.upgrade_source}")
            print(f"   Amount Paid: {slot3_activation.amount_paid} BNB")
            if slot3_activation.metadata:
                print(f"   Reserve Used (metadata): {slot3_activation.metadata.get('reserve_used', 'N/A')} BNB")
                print(f"   Wallet Used (metadata): {slot3_activation.metadata.get('wallet_used', 'N/A')} BNB")
            print(f"   TX Hash: {slot3_activation.tx_hash}")
        
        print("\n" + "=" * 80)
        print("✅ MANUAL UPGRADE COMPLETED SUCCESSFULLY")
        print("=" * 80)
    else:
        print(f"\n❌ Upgrade failed: {result.get('error')}")
        exit(1)
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

