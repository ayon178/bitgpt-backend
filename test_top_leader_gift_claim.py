"""
Test script for Top Leaders Gift Claim API
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.user.model import User
from modules.top_leader_gift.payment_model import TopLeadersGiftUser, TopLeadersGiftFund
from modules.top_leader_gift.claim_service import TopLeadersGiftClaimService
import json

# Connect to database
connect_to_db()

print("=" * 100)
print(" " * 25 + "TOP LEADERS GIFT CLAIM API TEST")
print("=" * 100)

# Step 1: Setup fund
print("\n📋 STEP 1: Verifying Top Leaders Gift Fund")
print("-" * 100)

fund = TopLeadersGiftFund.objects(is_active=True).first()
if not fund:
    fund = TopLeadersGiftFund(
        fund_name='Top Leaders Gift Fund',
        total_fund_usdt=100000.0,
        available_usdt=100000.0,
        total_fund_bnb=76.0,
        available_bnb=76.0,
        is_active=True
    )
    fund.save()
    print("✅ Created Top Leaders Gift Fund")
else:
    print("✅ Fund exists")

print(f"   Available USDT: ${fund.available_usdt:,.2f}")
print(f"   Available BNB: {fund.available_bnb:.2f}")

# Step 2: Find or create test user
print("\n📋 STEP 2: Finding Test User")
print("-" * 100)

# Look for existing eligible user
eligible_user = TopLeadersGiftUser.objects(is_eligible=True).first()

if eligible_user:
    user = User.objects(id=eligible_user.user_id).first()
    if user:
        test_user_id = str(user.id)
        print(f"✅ Found eligible user: {user.uid}")
        print(f"   User ID: {test_user_id}")
        print(f"   Highest Level: {eligible_user.highest_level_achieved}")
else:
    # Use any user for testing
    user = User.objects().first()
    if not user:
        print("❌ No users in database")
        sys.exit(1)
    test_user_id = str(user.id)
    print(f"⚠️  Using test user (may not be eligible): {user.uid}")
    print(f"   User ID: {test_user_id}")

# Step 3: Get fund overview
print("\n📋 STEP 3: Getting Fund Overview")
print("-" * 100)

service = TopLeadersGiftClaimService()
overview = service.get_fund_overview_for_user(test_user_id)

if overview.get("success"):
    print(f"✅ Fund overview retrieved")
    print(f"   Is Eligible: {overview['is_eligible']}")
    print(f"   Highest Level: {overview['highest_level_achieved']}")
    
    print("\n   Level-wise Claimable Amounts:")
    for level_data in overview['levels']:
        level = level_data['level']
        eligible = "✅" if level_data['is_eligible'] else "❌"
        maxed = "🔒" if level_data['is_maxed_out'] else "🔓"
        
        print(f"\n   Level {level} {eligible} {maxed}")
        print(f"      Eligible: {level_data['is_eligible']}")
        print(f"      Claimable USDT: ${level_data['claimable_amount']['usdt']:,.2f}")
        print(f"      Claimable BNB: {level_data['claimable_amount']['bnb']:.4f}")
        print(f"      Already Claimed: ${level_data['claimed']['usdt']:,.2f} USDT, {level_data['claimed']['bnb']:.4f} BNB")
        print(f"      Claimed %: {level_data['already_claimed_percent']:.2f}%")
else:
    print(f"❌ Failed to get overview: {overview.get('error')}")
    sys.exit(1)

# Step 4: Test claim scenarios
print("\n" + "=" * 100)
print("📋 STEP 4: Testing Claim Scenarios")
print("=" * 100)

# Find a level that is eligible and has claimable amount
claimable_level = None
for level_data in overview['levels']:
    if level_data['is_eligible'] and \
       not level_data['is_maxed_out'] and \
       (level_data['claimable_amount']['usdt'] > 0 or level_data['claimable_amount']['bnb'] > 0):
        claimable_level = level_data
        break

if claimable_level:
    level_num = claimable_level['level']
    print(f"\n✅ Found claimable level: Level {level_num}")
    print(f"   Claimable USDT: ${claimable_level['claimable_amount']['usdt']:,.2f}")
    print(f"   Claimable BNB: {claimable_level['claimable_amount']['bnb']:.4f}")
    
    # Test Scenario 1: Claim USDT only
    print(f"\n{'─'*100}")
    print(f"TEST SCENARIO 1: Claim Level {level_num} - USDT Only")
    print(f"{'─'*100}")
    
    result1 = service.claim_reward(test_user_id, level_num, 'USDT')
    
    if result1.get("success"):
        print("\n✅ Claim Successful!")
        print(f"   Payment ID: {result1['payment_id']}")
        print(f"   Claimed USDT: ${result1['claimed_usdt']:,.2f}")
        print(f"   Claimed BNB: {result1['claimed_bnb']:.4f}")
        print(f"   Currency: {result1['currency']}")
        print(f"   Message: {result1['message']}")
    else:
        print(f"\n❌ Claim Failed: {result1.get('error')}")
    
    # Test Scenario 2: Try to claim same level again (should fail or give remaining)
    print(f"\n{'─'*100}")
    print(f"TEST SCENARIO 2: Claim Level {level_num} Again - BNB Only")
    print(f"{'─'*100}")
    
    result2 = service.claim_reward(test_user_id, level_num, 'BNB')
    
    if result2.get("success"):
        print("\n✅ Claim Successful!")
        print(f"   Payment ID: {result2['payment_id']}")
        print(f"   Claimed USDT: ${result2['claimed_usdt']:,.2f}")
        print(f"   Claimed BNB: {result2['claimed_bnb']:.4f}")
        print(f"   Currency: {result2['currency']}")
    else:
        print(f"\n⚠️  {result2.get('error')}")
    
    # Test Scenario 3: Claim BOTH currencies for next eligible level
    next_claimable = None
    for level_data in overview['levels']:
        if level_data['level'] > level_num and \
           level_data['is_eligible'] and \
           not level_data['is_maxed_out'] and \
           (level_data['claimable_amount']['usdt'] > 0 or level_data['claimable_amount']['bnb'] > 0):
            next_claimable = level_data
            break
    
    if next_claimable:
        next_level = next_claimable['level']
        print(f"\n{'─'*100}")
        print(f"TEST SCENARIO 3: Claim Level {next_level} - BOTH Currencies")
        print(f"{'─'*100}")
        
        result3 = service.claim_reward(test_user_id, next_level, 'BOTH')
        
        if result3.get("success"):
            print("\n✅ Claim Successful!")
            print(f"   Payment ID: {result3['payment_id']}")
            print(f"   Claimed USDT: ${result3['claimed_usdt']:,.2f}")
            print(f"   Claimed BNB: {result3['claimed_bnb']:.4f}")
            print(f"   Currency: {result3['currency']}")
        else:
            print(f"\n❌ Claim Failed: {result3.get('error')}")

else:
    print("\n⚠️  No claimable levels found for this user")
    print("   Possible reasons:")
    print("   - User not eligible for any level")
    print("   - All eligible levels already maxed out")
    print("   - No fund available for distribution")

# Step 5: Get updated overview
print("\n" + "=" * 100)
print("📋 STEP 5: Updated Fund Overview After Claims")
print("=" * 100)

updated_overview = service.get_fund_overview_for_user(test_user_id)

if updated_overview.get("success"):
    print("\n📊 Summary:")
    print(f"   Total Claimed USDT: ${sum(l['claimed']['usdt'] for l in updated_overview['levels']):,.2f}")
    print(f"   Total Claimed BNB: {sum(l['claimed']['bnb'] for l in updated_overview['levels']):.4f}")
    
    print("\n   Level-wise Status:")
    for level_data in updated_overview['levels']:
        if level_data['claimed']['usdt'] > 0 or level_data['claimed']['bnb'] > 0:
            print(f"\n   Level {level_data['level']}:")
            print(f"      Claimed: ${level_data['claimed']['usdt']:,.2f} USDT, {level_data['claimed']['bnb']:.4f} BNB")
            print(f"      Remaining: ${level_data['remaining']['usdt']:,.2f} USDT, {level_data['remaining']['bnb']:.4f} BNB")
            print(f"      Claimed %: {level_data['already_claimed_percent']:.2f}%")

# Step 6: API endpoint info
print("\n" + "=" * 100)
print("📋 STEP 6: API Endpoint Information")
print("=" * 100)

print("""
Endpoint: POST /top-leader-gift/claim

Headers:
  Authorization: Bearer <token>
  Content-Type: application/json

Request Body:
{
  "user_id": "user_mongodb_id",
  "level": 1,
  "currency": "USDT" | "BNB" | "BOTH"
}

Response (Success):
{
  "status": "Ok",
  "data": {
    "user_id": "...",
    "level": 1,
    "currency": "USDT",
    "claimed_usdt": 750.0,
    "claimed_bnb": 0.0,
    "payment_id": "...",
    "message": "Top Leaders Gift Level 1 claimed successfully"
  },
  "message": "..."
}

Response (Error):
{
  "status": "Error",
  "message": "Error description"
}

Features:
✓ Currency-wise claiming (USDT, BNB, or BOTH)
✓ Automatic eligibility check
✓ Fund allocation calculation
✓ Max reward limit enforcement
✓ Wallet credit integration
✓ Claimed tracking and updates
""")

print("=" * 100)
print(" " * 35 + "TEST COMPLETE")
print("=" * 100)

