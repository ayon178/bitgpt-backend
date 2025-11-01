#!/usr/bin/env python3
"""
Test Binary Fund Distribution
Tests the complete distribution flow including shareholders
"""

from mongoengine import connect
from decimal import Decimal
from bson import ObjectId
from modules.fund_distribution.service import FundDistributionService
from modules.user.model import User, ShareholdersFund
from modules.income.model import IncomeEvent
from modules.wallet.model import WalletLedger
from modules.income.bonus_fund import BonusFund

# Connect to MongoDB
connect(
    host="mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt",
    alias="default"
)

print("=" * 70)
print("BINARY FUND DISTRIBUTION TEST")
print("=" * 70)

# Initialize service
fund_service = FundDistributionService()

# Test parameters
test_user_id = "690561e45e22859fec887883"  # User E
test_amount = Decimal('0.0044')  # Slot 2 amount
test_slot_no = 2
test_referrer_id = "690561765e22859fec88786b"  # User C (E's referrer)
test_currency = 'BNB'

print(f"\n📋 Test Parameters:")
print(f"   User ID: {test_user_id}")
print(f"   Amount: {test_amount} {test_currency}")
print(f"   Slot No: {test_slot_no}")
print(f"   Referrer ID: {test_referrer_id}")

# Check initial state
print(f"\n{'='*70}")
print("BEFORE DISTRIBUTION - Initial State")
print(f"{'='*70}")

# Check ShareholdersFund
shareholders_fund_before = ShareholdersFund.objects.first()
if shareholders_fund_before:
    print(f"\n✅ ShareholdersFund before:")
    print(f"   Total Contributed: {shareholders_fund_before.total_contributed}")
    print(f"   Available Amount: {shareholders_fund_before.available_amount}")
else:
    print(f"\n❌ No ShareholdersFund found (will be created)")

# Check BonusFund for binary program
bonus_funds_before = {}
for fund_type in ['spark_bonus', 'royal_captain', 'president_reward', 'leadership_stipend', 'jackpot']:
    bf = BonusFund.objects(fund_type=fund_type, program='binary').first()
    if bf:
        bonus_funds_before[fund_type] = float(bf.current_balance or 0)
        print(f"\n✅ {fund_type} (binary) before: {bf.current_balance}")
    else:
        bonus_funds_before[fund_type] = 0.0
        print(f"\n⚠️ {fund_type} (binary) not found")

# Check IncomeEvents count
income_events_before = IncomeEvent.objects.count()
print(f"\n📊 IncomeEvents count before: {income_events_before}")

# Check WalletLedger count
wallet_ledgers_before = WalletLedger.objects.count()
print(f"📊 WalletLedger count before: {wallet_ledgers_before}")

# Run distribution
print(f"\n{'='*70}")
print("RUNNING DISTRIBUTION")
print(f"{'='*70}")

try:
    result = fund_service.distribute_binary_funds(
        user_id=test_user_id,
        amount=test_amount,
        slot_no=test_slot_no,
        referrer_id=test_referrer_id,
        tx_hash=f"TEST_DIST_{test_user_id}_{test_slot_no}",
        currency=test_currency
    )
    
    print(f"\n✅ Distribution Result:")
    print(f"   Success: {result.get('success')}")
    print(f"   Total Amount: {result.get('total_amount')}")
    print(f"   Total Distributed: {result.get('total_distributed')}")
    print(f"   Distribution Type: {result.get('distribution_type')}")
    
    if result.get('distributions'):
        print(f"\n📦 Distributions ({len(result['distributions'])}):")
        for idx, dist in enumerate(result['distributions'], 1):
            print(f"\n   {idx}. Type: {dist.get('type', 'N/A')}")
            if 'amount' in dist:
                print(f"      Amount: {dist['amount']}")
            if 'shareholders_fund_updated' in dist:
                print(f"      Shareholders Fund Updated: {dist['shareholders_fund_updated']}")
            if 'error' in dist:
                print(f"      ❌ Error: {dist['error']}")
            if 'wallet_credited' in dist:
                print(f"      Wallet Credited: {dist['wallet_credited']}")
    
    if result.get('error'):
        print(f"\n❌ Error: {result['error']}")
        
except Exception as e:
    print(f"\n❌ Distribution failed with error: {e}")
    import traceback
    traceback.print_exc()
    result = None

# Check final state
print(f"\n{'='*70}")
print("AFTER DISTRIBUTION - Final State")
print(f"{'='*70}")

# Check ShareholdersFund
shareholders_fund_after = ShareholdersFund.objects.first()
if shareholders_fund_after:
    print(f"\n✅ ShareholdersFund after:")
    print(f"   Total Contributed: {shareholders_fund_after.total_contributed}")
    print(f"   Available Amount: {shareholders_fund_after.available_amount}")
    
    if shareholders_fund_before:
        diff = float(shareholders_fund_after.available_amount) - float(shareholders_fund_before.available_amount)
        expected = float(test_amount * Decimal('0.05'))  # 5% of amount
        print(f"   ✅ Increase: {diff} (Expected: {expected})")
        if abs(diff - expected) < 0.0001:
            print(f"   ✅ MATCH! Shareholders fund correctly updated")
        else:
            print(f"   ⚠️ Mismatch! Expected {expected}, got {diff}")
    else:
        expected = float(test_amount * Decimal('0.05'))
        actual = float(shareholders_fund_after.available_amount)
        print(f"   ✅ New fund created with: {actual} (Expected: {expected})")
        if abs(actual - expected) < 0.0001:
            print(f"   ✅ MATCH! Shareholders fund correctly created")
        else:
            print(f"   ⚠️ Mismatch! Expected {expected}, got {actual}")
else:
    print(f"\n❌ ShareholdersFund not found after distribution")

# Check BonusFund changes
print(f"\n📊 BonusFund Changes:")
for fund_type in ['spark_bonus', 'royal_captain', 'president_reward', 'leadership_stipend', 'jackpot']:
    bf = BonusFund.objects(fund_type=fund_type, program='binary').first()
    if bf:
        before_balance = bonus_funds_before.get(fund_type, 0)
        after_balance = float(bf.current_balance or 0)
        diff = after_balance - before_balance
        
        percentage = {
            'spark_bonus': 8.0,
            'royal_captain': 4.0,
            'president_reward': 3.0,
            'leadership_stipend': 5.0,
            'jackpot': 5.0
        }.get(fund_type, 0)
        
        expected = float(test_amount * Decimal(str(percentage / 100.0)))
        
        print(f"   {fund_type}: {before_balance} → {after_balance} (diff: {diff}, expected: {expected})")
        if abs(diff - expected) < 0.0001:
            print(f"      ✅ MATCH!")
        else:
            print(f"      ⚠️ Mismatch!")

# Check IncomeEvents
income_events_after = IncomeEvent.objects.count()
print(f"\n📊 IncomeEvents count: {income_events_before} → {income_events_after} (diff: {income_events_after - income_events_before})")

# Check specific income events
shareholders_events = IncomeEvent.objects(
    source_user_id=ObjectId(test_user_id),
    program='binary',
    slot_no=test_slot_no
).all()
print(f"\n📊 IncomeEvents for User {test_user_id} (Slot {test_slot_no}): {len(shareholders_events)}")
for ie in shareholders_events[:5]:  # Show first 5
    print(f"   - {ie.income_type}: {ie.amount} (to user: {ie.user_id})")

# Check WalletLedger
wallet_ledgers_after = WalletLedger.objects.count()
print(f"\n📊 WalletLedger count: {wallet_ledgers_before} → {wallet_ledgers_after} (diff: {wallet_ledgers_after - wallet_ledgers_before})")

# Summary
print(f"\n{'='*70}")
print("TEST SUMMARY")
print(f"{'='*70}")

if result and result.get('success'):
    print("\n✅ Distribution completed successfully")
    
    # Verify percentages sum to 100%
    total_percentage = 8 + 4 + 3 + 5 + 5 + 10 + 5 + 60  # All percentages
    print(f"\n📊 Distribution Breakdown:")
    print(f"   Spark Bonus: 8%")
    print(f"   Royal Captain: 4%")
    print(f"   President Reward: 3%")
    print(f"   Leadership Stipend: 5%")
    print(f"   Jackpot Entry: 5%")
    print(f"   Partner Incentive: 10%")
    print(f"   Shareholders: 5%")
    print(f"   Level Distribution: 60%")
    print(f"   Total: {total_percentage}%")
    
    if shareholders_fund_after and (not shareholders_fund_before or 
                                    float(shareholders_fund_after.available_amount) > float(shareholders_fund_before.available_amount or 0)):
        print(f"\n✅ Shareholders fund successfully updated!")
    else:
        print(f"\n⚠️ Shareholders fund may not have been updated correctly")
else:
    print("\n❌ Distribution failed or returned error")

print(f"\n{'='*70}")
print("TEST COMPLETE")
print(f"{'='*70}")

