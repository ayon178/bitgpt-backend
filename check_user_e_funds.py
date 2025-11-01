#!/usr/bin/env python3
"""
Check User E's fund distribution and shareholders_fund status
"""

from mongoengine import connect
from bson import ObjectId
from modules.user.model import User, ShareholdersFund
from modules.wallet.model import WalletLedger, UserWallet
from modules.income.model import IncomeEvent
from modules.slot.model import SlotActivation
from modules.tree.model import TreePlacement

# Connect to MongoDB
connect(
    host="mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt",
    alias="default"
)

# User E ID
user_e_id = ObjectId("690561e45e22859fec887883")

print("=" * 60)
print("USER E FUND DISTRIBUTION CHECK")
print("=" * 60)
print(f"\nUser E ID: {user_e_id}")
print(f"User E Refer Code: RC1761960419758485")

# Check User E
user_e = User.objects(id=user_e_id).first()
if user_e:
    print(f"\n✅ User E found:")
    print(f"   Name: {user_e.name}")
    print(f"   Refer Code: {user_e.refer_code}")
    print(f"   Refered By: {user_e.refered_by}")
else:
    print(f"\n❌ User E not found")

# Check Slot Activations for User E
print(f"\n{'='*60}")
print("SLOT ACTIVATIONS FOR USER E")
print(f"{'='*60}")
slot_activations = SlotActivation.objects(user_id=user_e_id).all()
if slot_activations:
    for sa in slot_activations:
        print(f"\nSlot {sa.slot_no} ({sa.slot_name}):")
        print(f"   Program: {sa.program}")
        print(f"   Status: {sa.status}")
        print(f"   Amount Paid: {sa.amount_paid}")
        print(f"   Activation Type: {sa.activation_type}")
        print(f"   Created: {sa.created_at}")
else:
    print("\n❌ No slot activations found for User E")

# Check Wallet Ledger for User E
print(f"\n{'='*60}")
print("WALLET LEDGER FOR USER E")
print(f"{'='*60}")
wallet_ledgers = WalletLedger.objects(user_id=user_e_id).all()
if wallet_ledgers:
    print(f"\n✅ Found {len(wallet_ledgers)} wallet ledger entries:")
    for wl in wallet_ledgers:
        print(f"\n   Type: {wl.type}, Amount: {wl.amount} {wl.currency}")
        print(f"   Reason: {wl.reason}")
        print(f"   TX Hash: {wl.tx_hash}")
        print(f"   Created: {wl.created_at}")
else:
    print("\n❌ No wallet ledger entries found for User E")

# Check Income Events for User E
print(f"\n{'='*60}")
print("INCOME EVENTS FOR USER E")
print(f"{'='*60}")
income_events = IncomeEvent.objects(user_id=user_e_id).all()
if income_events:
    print(f"\n✅ Found {len(income_events)} income events:")
    for ie in income_events:
        print(f"\n   Type: {ie.income_type}, Amount: {ie.amount}")
        print(f"   Program: {ie.program}, Slot: {ie.slot_no}")
        print(f"   Source User: {ie.source_user_id}")
        print(f"   TX Hash: {ie.tx_hash}")
        print(f"   Created: {ie.created_at}")
else:
    print("\n❌ No income events found for User E")

# Check Income Events where User E is the SOURCE (distributions FROM E)
print(f"\n{'='*60}")
print("DISTRIBUTIONS FROM USER E (E is source)")
print(f"{'='*60}")
distributions_from_e = IncomeEvent.objects(source_user_id=user_e_id).all()
if distributions_from_e:
    print(f"\n✅ Found {len(distributions_from_e)} distributions from User E:")
    for ie in distributions_from_e:
        print(f"\n   To User: {ie.user_id}, Type: {ie.income_type}")
        print(f"   Amount: {ie.amount}, Program: {ie.program}, Slot: {ie.slot_no}")
        print(f"   TX Hash: {ie.tx_hash}")
else:
    print("\n❌ No distributions found from User E")

# Check Tree Placement for User E
print(f"\n{'='*60}")
print("TREE PLACEMENT FOR USER E")
print(f"{'='*60}")
tree_placements = TreePlacement.objects(user_id=user_e_id).all()
if tree_placements:
    print(f"\n✅ Found {len(tree_placements)} tree placements:")
    for tp in tree_placements:
        print(f"\n   Program: {tp.program}, Slot: {tp.slot_no}")
        print(f"   Parent ID: {tp.parent_id}, Upline ID: {tp.upline_id}")
        print(f"   Position: {tp.position}, Level: {tp.level}")
        print(f"   Is Active: {tp.is_active}")
else:
    print("\n❌ No tree placements found for User E")

# Check Shareholders Fund
print(f"\n{'='*60}")
print("SHAREHOLDERS FUND STATUS")
print(f"{'='*60}")
shareholders_fund = ShareholdersFund.objects.first()
if shareholders_fund:
    print(f"\n✅ Shareholders Fund found:")
    print(f"   Total Contributed: {shareholders_fund.total_contributed}")
    print(f"   Total Distributed: {shareholders_fund.total_distributed}")
    print(f"   Available Amount: {shareholders_fund.available_amount}")
    print(f"   Last Updated: {shareholders_fund.last_updated}")
    print(f"   Created: {shareholders_fund.created_at}")
else:
    print("\n❌ Shareholders Fund is EMPTY (no document found)")

# Check Income Events with shareholders type
print(f"\n{'='*60}")
print("INCOME EVENTS WITH SHAREHOLDERS TYPE")
print(f"{'='*60}")
shareholders_events = IncomeEvent.objects(income_type='shareholders').all()
if shareholders_events:
    print(f"\n✅ Found {len(shareholders_events)} shareholders income events:")
    for ie in shareholders_events[:10]:  # Show first 10
        print(f"\n   User: {ie.user_id}, Amount: {ie.amount}")
        print(f"   Program: {ie.program}, Slot: {ie.slot_no}")
        print(f"   Source: {ie.source_user_id}, TX: {ie.tx_hash}")
else:
    print("\n❌ No shareholders income events found")

# Check all wallet ledgers with shareholders reason
print(f"\n{'='*60}")
print("WALLET LEDGERS WITH SHAREHOLDERS REASON")
print(f"{'='*60}")
shareholders_ledgers = WalletLedger.objects(reason__icontains='shareholder').all()
if shareholders_ledgers:
    print(f"\n✅ Found {len(shareholders_ledgers)} shareholders wallet ledger entries:")
    for wl in shareholders_ledgers[:10]:  # Show first 10
        print(f"\n   User: {wl.user_id}, Amount: {wl.amount} {wl.currency}")
        print(f"   Reason: {wl.reason}, TX: {wl.tx_hash}")
else:
    print("\n❌ No shareholders wallet ledger entries found")

print(f"\n{'='*60}")
print("CHECK COMPLETE")
print(f"{'='*60}")

