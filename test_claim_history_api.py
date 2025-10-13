"""
Test script for Top Leaders Gift Claim History API
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.user.model import User
from modules.top_leader_gift.payment_model import TopLeadersGiftUser, TopLeadersGiftPayment
from modules.top_leader_gift.claim_service import TopLeadersGiftClaimService
import json

# Connect to database
connect_to_db()

print("=" * 100)
print(" " * 20 + "TOP LEADERS GIFT CLAIM HISTORY API TEST")
print("=" * 100)

# Step 1: Find user with claim history
print("\n📋 STEP 1: Finding User with Claim History")
print("-" * 100)

# Find user who has payment records
payment = TopLeadersGiftPayment.objects().first()

if not payment:
    print("⚠️  No payment records found in database")
    print("   Creating test scenario...")
    
    # Use any user
    user = User.objects().first()
    if not user:
        print("❌ No users in database")
        sys.exit(1)
    
    test_user_id = str(user.id)
    print(f"   Using user: {user.uid} (No claims yet)")
else:
    user = User.objects(id=payment.user_id).first()
    if not user:
        print("❌ User not found for payment")
        sys.exit(1)
    
    test_user_id = str(user.id)
    
    # Count total payments for this user
    total_payments = TopLeadersGiftPayment.objects(user_id=payment.user_id).count()
    
    print(f"✅ Found user with claim history: {user.uid}")
    print(f"   User ID: {test_user_id}")
    print(f"   Total Payment Records: {total_payments}")

# Step 2: Get user's TopLeadersGiftUser record
print("\n📋 STEP 2: Checking User's Top Leaders Gift Record")
print("-" * 100)

tl_user = TopLeadersGiftUser.objects(user_id=user.id).first()
if tl_user:
    print("✅ TopLeadersGiftUser record found")
    print(f"   Total Claimed USDT: ${tl_user.total_claimed_usdt:,.2f}")
    print(f"   Total Claimed BNB: {tl_user.total_claimed_bnb:.4f}")
    print(f"   Total Claims Count: {tl_user.total_claims_count}")
    print(f"   Last Claim Date: {tl_user.last_claim_date}")
else:
    print("⚠️  No TopLeadersGiftUser record (user hasn't claimed yet)")

# Step 3: Get all payment records for user
print("\n📋 STEP 3: Fetching All Payment Records")
print("-" * 100)

payments = TopLeadersGiftPayment.objects(user_id=user.id).order_by('-created_at')
payment_count = payments.count()

print(f"\n✅ Found {payment_count} payment record(s)\n")

if payment_count > 0:
    for idx, p in enumerate(payments, 1):
        status_emoji = "✅" if p.payment_status == 'paid' else "⏳" if p.payment_status == 'pending' else "❌"
        print(f"{idx}. {status_emoji} Level {p.level_number} - {p.currency}")
        print(f"   USDT: ${p.claimed_amount_usdt:,.2f}, BNB: {p.claimed_amount_bnb:.4f}")
        print(f"   Status: {p.payment_status}")
        print(f"   Created: {p.created_at}")
        print(f"   Payment ID: {str(p.id)}")
        print()

# Step 4: Test claim history service
print("=" * 100)
print("📋 STEP 4: Testing Claim History Service")
print("=" * 100)

service = TopLeadersGiftClaimService()
result = service.get_claim_history(test_user_id)

if result.get("success"):
    print("\n✅ SUCCESS - Claim History Retrieved\n")
    
    # Overall Summary
    print("=" * 100)
    print("📊 OVERALL SUMMARY")
    print("=" * 100)
    
    summary = result['overall_summary']
    print(f"""
Total Claims:        {summary['total_claims']}
Successful Claims:   {summary['successful_claims']} ✅
Pending Claims:      {summary['pending_claims']} ⏳
Failed Claims:       {summary['failed_claims']} ❌

Total Claimed USDT:  ${summary['total_claimed_usdt']:,.2f}
Total Claimed BNB:   {summary['total_claimed_bnb']:.4f}

Highest Level Claimed: Level {summary['highest_level_claimed']}
Last Claim Date:       {summary['last_claim_date']}
""")
    
    # Level-wise Summary
    print("=" * 100)
    print("📋 LEVEL-WISE SUMMARY")
    print("=" * 100)
    
    for level_num in range(1, 6):
        level_key = f"level_{level_num}"
        level_data = result['level_summary'][level_key]
        
        if level_data['total_claims'] > 0:
            print(f"\n{'▓'*100}")
            print(f"   LEVEL {level_num}")
            print(f"{'▓'*100}")
            print(f"""
   Total Claims:      {level_data['total_claims']}
   Successful:        {level_data['successful_claims']} ✅
   Pending:           {level_data['pending_claims']} ⏳
   Failed:            {level_data['failed_claims']} ❌
   
   Total USDT:        ${level_data['total_claimed_usdt']:,.2f}
   Total BNB:         {level_data['total_claimed_bnb']:.4f}
   USD Value:         ${level_data['total_claimed_usd_value']:,.2f}
""")
            
            if level_data['claims']:
                print("   Individual Claims:")
                for claim in level_data['claims']:
                    status_emoji = "✅" if claim['status'] == 'paid' else "⏳" if claim['status'] == 'pending' else "❌"
                    print(f"      {status_emoji} {claim['currency']}: ${claim['claimed_usdt']:,.2f} USDT, {claim['claimed_bnb']:.4f} BNB")
                    print(f"         Date: {claim['claimed_at']}")
                    print(f"         Ref: {claim['payment_reference']}")
                    print()
    
    # Currency-wise Summary
    print("=" * 100)
    print("💰 CURRENCY-WISE SUMMARY")
    print("=" * 100)
    
    curr_summary = result['currency_summary']
    
    print(f"\n📈 USDT Summary:")
    print(f"   Total Claimed:  ${curr_summary['usdt']['total_claimed']:,.2f}")
    print(f"   Claim Count:    {curr_summary['usdt']['claim_count']}")
    print(f"\n   By Level:")
    for level_num in range(1, 6):
        level_key = f"level_{level_num}"
        amount = curr_summary['usdt']['claims_by_level'][level_key]
        if amount > 0:
            print(f"      Level {level_num}: ${amount:,.2f}")
    
    print(f"\n📈 BNB Summary:")
    print(f"   Total Claimed:  {curr_summary['bnb']['total_claimed']:.4f} BNB")
    print(f"   Claim Count:    {curr_summary['bnb']['claim_count']}")
    print(f"\n   By Level:")
    for level_num in range(1, 6):
        level_key = f"level_{level_num}"
        amount = curr_summary['bnb']['claims_by_level'][level_key]
        if amount > 0:
            print(f"      Level {level_num}: {amount:.4f} BNB")
    
    # All Claims
    print("\n" + "=" * 100)
    print("📜 ALL CLAIMS (Recent First)")
    print("=" * 100)
    
    if result['all_claims']:
        for idx, claim in enumerate(result['all_claims'], 1):
            status_emoji = "✅" if claim['status'] == 'paid' else "⏳" if claim['status'] == 'pending' else "❌"
            
            print(f"\n{idx}. {status_emoji} {claim['level_name']} - {claim['currency']}")
            print(f"   Claimed: ${claim['claimed_usdt']:,.2f} USDT + {claim['claimed_bnb']:.4f} BNB")
            print(f"   Status: {claim['status']}")
            print(f"   Date: {claim['claimed_at']}")
            print(f"   Payment ID: {claim['payment_id']}")
            if claim['payment_reference']:
                print(f"   Reference: {claim['payment_reference']}")
            print(f"   User Status at Claim:")
            print(f"      Rank: {claim['self_rank_at_claim']}")
            print(f"      Direct Partners: {claim['direct_partners_at_claim']}")
            print(f"      Total Team: {claim['total_team_at_claim']}")
    else:
        print("\n   No claims found for this user")
    
    # Complete JSON Response
    print("\n" + "=" * 100)
    print("📄 COMPLETE JSON RESPONSE")
    print("=" * 100)
    print("\n" + json.dumps(result, indent=2, default=str))
    
else:
    print(f"\n❌ ERROR: {result.get('error')}")

print("\n" + "=" * 100)
print(" " * 35 + "TEST COMPLETE")
print("=" * 100)

# API Info
print(f"""
📝 API Endpoint Information:

Endpoint: GET /top-leader-gift/claim/history?user_id={test_user_id}

Features:
✓ Overall summary (total/successful/pending/failed claims)
✓ Level-wise breakdown (5 levels)
✓ Currency-wise breakdown (USDT/BNB)
✓ Individual claim records
✓ Payment tracking with IDs and references
✓ User status at time of claim
""")

