"""
Test Top Leaders Gift API with specific eligible user
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.user.model import User
from modules.top_leader_gift.payment_model import TopLeadersGiftUser
from modules.top_leader_gift.claim_service import TopLeadersGiftClaimService
import json

# Connect to database
connect_to_db()

print("=" * 100)
print(" " * 20 + "TOP LEADERS GIFT - SPECIFIC USER TEST")
print("=" * 100)

# Find the eligible user we discovered
uid_to_test = "LSUSER2_1759746644"

print(f"\n🔍 Looking for user: {uid_to_test}")

user = User.objects(uid=uid_to_test).first()
if not user:
    print(f"❌ User {uid_to_test} not found")
    sys.exit(1)

user_id = str(user.id)
print(f"✅ Found user: {uid_to_test}")
print(f"   User ID: {user_id}\n")

# Get TopLeadersGiftUser record
tl_user = TopLeadersGiftUser.objects(user_id=user.id).first()
if tl_user:
    print("📊 TopLeadersGiftUser Record:")
    print(f"   Is Eligible: {tl_user.is_eligible}")
    print(f"   Highest Level: {tl_user.highest_level_achieved}")
    print(f"   Total Claimed USDT: ${tl_user.total_claimed_usdt:,.2f}")
    print(f"   Total Claimed BNB: {tl_user.total_claimed_bnb:.4f}")
    print(f"   Total Claims Count: {tl_user.total_claims_count}")
    print()

# Test the service directly
print("=" * 100)
print("🧪 TESTING SERVICE DIRECTLY")
print("=" * 100)

service = TopLeadersGiftClaimService()
result = service.get_fund_overview_for_user(user_id)

if result.get("success"):
    print("\n✅ SUCCESS!\n")
    
    print(f"User ID: {result['user_id']}")
    print(f"Is Eligible: {result['is_eligible']}")
    print(f"Highest Level Achieved: {result['highest_level_achieved']}")
    
    print(f"\n💰 Total Fund Available:")
    print(f"   USDT: ${result['total_fund']['usdt']:,.2f}")
    print(f"   BNB: {result['total_fund']['bnb']:.2f}")
    
    print(f"\n{'='*100}")
    print("📋 LEVEL-BY-LEVEL BREAKDOWN")
    print(f"{'='*100}\n")
    
    for level_data in result['levels']:
        level = level_data['level']
        
        # Emoji for eligibility
        eligible_emoji = "✅" if level_data['is_eligible'] else "❌"
        maxed_emoji = "🔒" if level_data['is_maxed_out'] else "🔓"
        
        print(f"{'▓'*100}")
        print(f"   LEVEL {level}: {level_data['level_name']} {eligible_emoji} {maxed_emoji}")
        print(f"{'▓'*100}")
        
        # Eligibility Status
        print(f"\n   🎯 ELIGIBILITY STATUS:")
        print(f"      Eligible: {eligible_emoji} {'YES' if level_data['is_eligible'] else 'NO'}")
        print(f"      Maxed Out: {maxed_emoji} {'YES' if level_data['is_maxed_out'] else 'NO'}")
        
        # Requirements vs Current Status
        req = level_data['requirements']
        curr = level_data['current_status']
        
        print(f"\n   📋 REQUIREMENTS vs CURRENT STATUS:")
        print(f"      Self Rank:       Need {req['self_rank']:2d} | Current {curr['self_rank']:2d} {'✅' if curr['self_rank'] >= req['self_rank'] else '❌'}")
        print(f"      Direct Partners: Need {req['direct_partners']:2d} | Current {curr['direct_partners']:2d} {'✅' if curr['direct_partners'] >= req['direct_partners'] else '❌'}")
        print(f"      Partners Rank:   Need {req['partners_rank']:2d}")
        print(f"      Total Team:      Need {req['total_team']:4d} | Current {curr['total_team']:4d} {'✅' if curr['total_team'] >= req['total_team'] else '❌'}")
        
        # Fund Details
        alloc = level_data['fund_allocation']
        print(f"\n   💵 FUND ALLOCATION ({alloc['percentage']}% of total):")
        print(f"      Allocated USDT: ${alloc['allocated_usdt']:,.2f}")
        print(f"      Allocated BNB:  {alloc['allocated_bnb']:.4f}")
        
        # Distribution
        print(f"\n   👥 DISTRIBUTION:")
        print(f"      Eligible Users: {level_data['eligible_users_count']}")
        
        if level_data['eligible_users_count'] > 0:
            per_user_usdt = alloc['allocated_usdt'] / level_data['eligible_users_count']
            per_user_bnb = alloc['allocated_bnb'] / level_data['eligible_users_count']
            print(f"      Per User USDT:  ${per_user_usdt:,.2f}")
            print(f"      Per User BNB:   {per_user_bnb:.4f}")
        
        # Claimable
        claim = level_data['claimable_amount']
        if claim['usdt'] > 0 or claim['bnb'] > 0:
            print(f"\n   💎 CLAIMABLE AMOUNT:")
            print(f"      USDT: ${claim['usdt']:,.2f}")
            print(f"      BNB:  {claim['bnb']:.4f}")
        
        # Already Claimed
        claimed = level_data['claimed']
        if claimed['usdt'] > 0 or claimed['bnb'] > 0:
            print(f"\n   ✅ ALREADY CLAIMED:")
            print(f"      USDT: ${claimed['usdt']:,.2f}")
            print(f"      BNB:  {claimed['bnb']:.4f}")
            print(f"      Claimed %: {level_data['already_claimed_percent']:.2f}%")
        
        # Remaining
        remaining = level_data['remaining']
        print(f"\n   📊 REMAINING (Max - Claimed):")
        print(f"      USDT: ${remaining['usdt']:,.2f}")
        print(f"      BNB:  {remaining['bnb']:.4f}")
        
        # Max Reward
        max_reward = level_data['max_reward']
        print(f"\n   🏆 MAX REWARD LIMIT:")
        print(f"      USDT: ${max_reward['usdt']:,.2f}")
        print(f"      BNB:  {max_reward['bnb']:.4f}")
        
        print()
    
    print(f"{'='*100}\n")
    
    # Summary
    print("📊 SUMMARY FOR THIS USER:")
    print(f"   Total Eligible Levels: {len([l for l in result['levels'] if l['is_eligible']])}")
    print(f"   Total Claimable USDT: ${sum(l['claimable_amount']['usdt'] for l in result['levels']):,.2f}")
    print(f"   Total Claimable BNB: {sum(l['claimable_amount']['bnb'] for l in result['levels']):.4f}")
    print(f"   Total Already Claimed USDT: ${sum(l['claimed']['usdt'] for l in result['levels']):,.2f}")
    print(f"   Total Already Claimed BNB: {sum(l['claimed']['bnb'] for l in result['levels']):.4f}")
    
    # Show JSON for API response
    print(f"\n{'='*100}")
    print("📄 COMPLETE JSON RESPONSE:")
    print(f"{'='*100}\n")
    print(json.dumps(result, indent=2, default=str))
    
else:
    print(f"\n❌ ERROR: {result.get('error')}")

print(f"\n{'='*100}")
print(" " * 35 + "TEST COMPLETE")
print(f"{'='*100}")

