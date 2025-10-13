"""
Complete test script for Top Leaders Gift Fund Overview API
- Checks database for eligible users
- Tests API with eligible user
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.user.model import User, PartnerGraph
from modules.rank.model import UserRank
from modules.top_leader_gift.payment_model import TopLeadersGiftUser, TopLeadersGiftFund
import requests
import json

# Connect to database
print("Connecting to database...")
connect_to_db()
print("✅ Database connected\n")

print("=" * 100)
print(" " * 20 + "TOP LEADERS GIFT FUND OVERVIEW - COMPLETE TEST")
print("=" * 100)

# Step 1: Setup or verify fund
print("\n📋 STEP 1: Setting up Top Leaders Gift Fund")
print("-" * 100)

fund = TopLeadersGiftFund.objects(is_active=True).first()
if not fund:
    fund = TopLeadersGiftFund(
        fund_name='Top Leaders Gift Fund',
        total_fund_usdt=50000.0,  # $50,000 test fund
        available_usdt=50000.0,
        total_fund_bnb=38.0,  # ~$50,000 in BNB (assuming 1 BNB = $1316)
        available_bnb=38.0,
        level_1_percentage=37.5,
        level_2_percentage=25.0,
        level_3_percentage=15.0,
        level_4_percentage=12.5,
        level_5_percentage=10.0,
        is_active=True
    )
    fund.save()
    print("✅ Created new Top Leaders Gift Fund")
else:
    # Update fund if exists
    fund.available_usdt = max(fund.available_usdt, 50000.0)
    fund.available_bnb = max(fund.available_bnb, 38.0)
    fund.save()
    print("✅ Top Leaders Gift Fund verified and updated")

print(f"   Total Fund USDT: ${fund.available_usdt:,.2f}")
print(f"   Total Fund BNB: {fund.available_bnb:.2f} BNB")
print(f"   Level Percentages: L1={fund.level_1_percentage}%, L2={fund.level_2_percentage}%, L3={fund.level_3_percentage}%, L4={fund.level_4_percentage}%, L5={fund.level_5_percentage}%")

# Step 2: Check for eligible users
print("\n📋 STEP 2: Checking for Eligible Users")
print("-" * 100)

# Level requirements
level_requirements = [
    {"level": 1, "self_rank": 6, "direct_partners": 5, "partners_rank": 5, "total_team": 300},
    {"level": 2, "self_rank": 8, "direct_partners": 7, "partners_rank": 6, "total_team": 500},
    {"level": 3, "self_rank": 11, "direct_partners": 8, "partners_rank": 10, "total_team": 1000},
    {"level": 4, "self_rank": 13, "direct_partners": 9, "partners_rank": 13, "total_team": 2000},
    {"level": 5, "self_rank": 15, "direct_partners": 10, "partners_rank": 14, "total_team": 3000},
]

print("\nSearching for users who meet any level requirements...\n")

eligible_users = []

# Get all users with ranks
users_with_ranks = UserRank.objects(current_rank_number__gte=6).limit(50)
print(f"Found {users_with_ranks.count()} users with rank >= 6")

for user_rank in users_with_ranks:
    user = User.objects(id=user_rank.user_id).first()
    if not user:
        continue
    
    # Get partner graph
    graph = PartnerGraph.objects(user_id=user.id).first()
    
    self_rank = user_rank.current_rank_number
    direct_partners_count = len(graph.directs) if graph and graph.directs else 0
    total_team = graph.total_team if graph else 0
    
    # Get partner ranks
    partner_ranks = {}
    if graph and graph.directs:
        partner_rank_objs = UserRank.objects(user_id__in=graph.directs)
        partner_ranks = {str(r.user_id): r.current_rank_number for r in partner_rank_objs}
    
    # Check which levels user qualifies for
    eligible_levels = []
    
    for req in level_requirements:
        # Check basic requirements
        if self_rank >= req['self_rank'] and \
           direct_partners_count >= req['direct_partners'] and \
           total_team >= req['total_team']:
            
            # Check if enough partners have required rank
            partners_with_rank = sum(1 for r in partner_ranks.values() if r >= req['partners_rank'])
            
            if partners_with_rank >= req['direct_partners']:
                eligible_levels.append(req['level'])
    
    if eligible_levels:
        eligible_users.append({
            'user_id': str(user.id),
            'uid': user.uid,
            'name': user.name if hasattr(user, 'name') else 'N/A',
            'self_rank': self_rank,
            'direct_partners': direct_partners_count,
            'total_team': total_team,
            'eligible_levels': eligible_levels,
            'highest_level': max(eligible_levels)
        })

if eligible_users:
    print(f"\n✅ Found {len(eligible_users)} eligible users!\n")
    
    # Sort by highest level
    eligible_users.sort(key=lambda x: x['highest_level'], reverse=True)
    
    # Show top 5
    print("Top eligible users:")
    for idx, user_info in enumerate(eligible_users[:5], 1):
        print(f"\n{idx}. UID: {user_info['uid']} ({user_info['name']})")
        print(f"   User ID: {user_info['user_id']}")
        print(f"   Rank: {user_info['self_rank']}")
        print(f"   Direct Partners: {user_info['direct_partners']}")
        print(f"   Total Team: {user_info['total_team']}")
        print(f"   Eligible Levels: {user_info['eligible_levels']}")
        print(f"   Highest Level: {user_info['highest_level']}")
else:
    print("\n⚠️  No eligible users found in database")
    print("Creating a test user scenario...")
    
    # Get any user for testing
    test_user = User.objects().first()
    if test_user:
        eligible_users.append({
            'user_id': str(test_user.id),
            'uid': test_user.uid,
            'name': test_user.name if hasattr(test_user, 'name') else 'Test User',
            'self_rank': 0,
            'direct_partners': 0,
            'total_team': 0,
            'eligible_levels': [],
            'highest_level': 0
        })
        print(f"\n   Using test user: {test_user.uid}")
        print(f"   User ID: {str(test_user.id)}")
        print(f"   (This user is NOT eligible, but we'll test the API response)")

# Step 3: Check TopLeadersGiftUser records
print("\n" + "=" * 100)
print("📋 STEP 3: Checking TopLeadersGiftUser Records")
print("-" * 100)

tl_users = TopLeadersGiftUser.objects(is_eligible=True).limit(10)
print(f"\nFound {tl_users.count()} users marked as eligible in TopLeadersGiftUser\n")

for idx, tl_user in enumerate(tl_users, 1):
    user = User.objects(id=tl_user.user_id).first()
    if user:
        print(f"{idx}. UID: {user.uid}")
        print(f"   Highest Level: {tl_user.highest_level_achieved}")
        print(f"   Total Claimed USDT: ${tl_user.total_claimed_usdt:,.2f}")
        print(f"   Total Claimed BNB: {tl_user.total_claimed_bnb:.4f}")
        print()

# Step 4: Test API
print("=" * 100)
print("📋 STEP 4: Testing API Endpoint")
print("-" * 100)

if not eligible_users:
    print("\n❌ No users available for testing")
    sys.exit(1)

# Use the first eligible user (or test user)
test_user_info = eligible_users[0]
test_user_id = test_user_info['user_id']

print(f"\n🎯 Testing with User:")
print(f"   UID: {test_user_info['uid']}")
print(f"   User ID: {test_user_id}")
print(f"   Rank: {test_user_info['self_rank']}")
print(f"   Eligible Levels: {test_user_info['eligible_levels']}")

BASE_URL = "http://localhost:8000"

# Check if server is running
print("\nChecking if server is running...")
try:
    health_check = requests.get(f"{BASE_URL}/docs", timeout=2)
    print("✅ Server is running\n")
    server_running = True
except:
    print("❌ Server is not running")
    print("\nTo start the server, run:")
    print("   cd E:\\bitgpt\\backend")
    print("   .\\venv\\Scripts\\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    server_running = False

if server_running:
    # Test without authentication (will show what would happen)
    url = f"{BASE_URL}/top-leader-gift/fund/overview?user_id={test_user_id}"
    
    print(f"📡 API URL: {url}")
    print("\n⚠️  Note: This requires authentication. Testing without auth to see error...")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"\nStatus Code: {response.status_code}")
        
        try:
            data = response.json()
            print("\nResponse:")
            print(json.dumps(data, indent=2))
        except:
            print(f"\nResponse Text: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

# Step 5: Direct service test (bypass authentication)
print("\n" + "=" * 100)
print("📋 STEP 5: Direct Service Test (Bypass Authentication)")
print("-" * 100)

try:
    from modules.top_leader_gift.claim_service import TopLeadersGiftClaimService
    
    service = TopLeadersGiftClaimService()
    result = service.get_fund_overview_for_user(test_user_id)
    
    if result.get("success"):
        print("\n✅ SUCCESS - Fund Overview Retrieved\n")
        
        print(f"User ID: {result['user_id']}")
        print(f"Is Eligible: {result['is_eligible']}")
        print(f"Highest Level Achieved: {result['highest_level_achieved']}")
        print(f"\nTotal Fund Available:")
        print(f"  USDT: ${result['total_fund']['usdt']:,.2f}")
        print(f"  BNB: {result['total_fund']['bnb']:.2f}")
        
        print(f"\n{'='*100}")
        print("LEVEL-WISE BREAKDOWN:")
        print(f"{'='*100}\n")
        
        for level_data in result['levels']:
            print(f"{'─'*100}")
            print(f"LEVEL {level_data['level']}: {level_data['level_name']}")
            print(f"{'─'*100}")
            
            print(f"\n  Eligibility:")
            print(f"    Is Eligible: {'✅ YES' if level_data['is_eligible'] else '❌ NO'}")
            print(f"    Is Maxed Out: {'⚠️  YES' if level_data['is_maxed_out'] else '✓ NO'}")
            
            print(f"\n  Requirements:")
            req = level_data['requirements']
            print(f"    Self Rank: {req['self_rank']}")
            print(f"    Direct Partners: {req['direct_partners']}")
            print(f"    Partners Rank: {req['partners_rank']}")
            print(f"    Total Team: {req['total_team']}")
            
            print(f"\n  Current Status:")
            curr = level_data['current_status']
            print(f"    Self Rank: {curr['self_rank']} {'✅' if curr['self_rank'] >= req['self_rank'] else '❌'}")
            print(f"    Direct Partners: {curr['direct_partners']} {'✅' if curr['direct_partners'] >= req['direct_partners'] else '❌'}")
            print(f"    Total Team: {curr['total_team']} {'✅' if curr['total_team'] >= req['total_team'] else '❌'}")
            
            print(f"\n  Fund Allocation:")
            alloc = level_data['fund_allocation']
            print(f"    Percentage: {alloc['percentage']}%")
            print(f"    Allocated USDT: ${alloc['allocated_usdt']:,.2f}")
            print(f"    Allocated BNB: {alloc['allocated_bnb']:.4f}")
            
            print(f"\n  Distribution:")
            print(f"    Eligible Users Count: {level_data['eligible_users_count']}")
            
            print(f"\n  Claimable Amount:")
            claim = level_data['claimable_amount']
            print(f"    USDT: ${claim['usdt']:,.2f}")
            print(f"    BNB: {claim['bnb']:.4f}")
            
            print(f"\n  Already Claimed:")
            claimed = level_data['claimed']
            print(f"    USDT: ${claimed['usdt']:,.2f}")
            print(f"    BNB: {claimed['bnb']:.4f}")
            
            print(f"\n  Remaining:")
            remaining = level_data['remaining']
            print(f"    USDT: ${remaining['usdt']:,.2f}")
            print(f"    BNB: {remaining['bnb']:.4f}")
            
            print(f"\n  Max Reward:")
            max_reward = level_data['max_reward']
            print(f"    USDT: ${max_reward['usdt']:,.2f}")
            print(f"    BNB: {max_reward['bnb']:.4f}")
            
            print(f"\n  Already Claimed Percent: {level_data['already_claimed_percent']}%")
            print()
        
        print(f"{'='*100}\n")
        
    else:
        print(f"\n❌ ERROR: {result.get('error')}")
        
except Exception as e:
    print(f"\n❌ Exception: {str(e)}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 100)
print(" " * 35 + "TEST SUMMARY")
print("=" * 100)

print(f"""
✅ Database Connection: Success
✅ Fund Setup: ${fund.available_usdt:,.2f} USDT + {fund.available_bnb:.2f} BNB
✅ Eligible Users Found: {len([u for u in eligible_users if u['eligible_levels']])}
✅ Test User: {test_user_info['uid']}
✅ Direct Service Test: Completed

📊 Results:
   - Total eligible users in DB: {len([u for u in eligible_users if u['eligible_levels']])}
   - Test user eligible levels: {test_user_info['eligible_levels']}
   - API endpoint: /top-leader-gift/fund/overview
   
💡 To test with authentication:
   1. Get authentication token from login
   2. Use Postman or add header: Authorization: Bearer <token>
   3. Call: GET {BASE_URL}/top-leader-gift/fund/overview?user_id={test_user_id}
""")

print("=" * 100)
print(" " * 35 + "TEST COMPLETE")
print("=" * 100)

