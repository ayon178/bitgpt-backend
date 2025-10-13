"""
Test script for Top Leaders Gift Fund Overview API
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.user.model import User
from modules.top_leader_gift.payment_model import TopLeadersGiftFund
import requests
import json

# Connect to database
connect_to_db()
print("✅ Database connected\n")

print("=" * 100)
print(" " * 25 + "TOP LEADERS GIFT FUND OVERVIEW API TEST")
print("=" * 100)

# Step 1: Check if fund exists, create if not
print("\n📋 STEP 1: Setting up Top Leaders Gift Fund")
print("-" * 100)

fund = TopLeadersGiftFund.objects(is_active=True).first()
if not fund:
    fund = TopLeadersGiftFund(
        fund_name='Top Leaders Gift Fund',
        total_fund_usdt=10000.0,  # Example fund
        available_usdt=10000.0,
        total_fund_bnb=7.6,  # Example BNB fund (assuming 1 BNB = $1316)
        available_bnb=7.6,
        is_active=True
    )
    fund.save()
    print("✅ Created new Top Leaders Gift Fund")
else:
    print("✅ Top Leaders Gift Fund exists")

print(f"   Available USDT: ${fund.available_usdt}")
print(f"   Available BNB: {fund.available_bnb} BNB")

# Step 2: Find a test user
print("\n📋 STEP 2: Finding test user")
print("-" * 100)

test_user = User.objects().first()
if not test_user:
    print("❌ No users found in database")
    sys.exit(1)

test_user_id = str(test_user.id)
print(f"✅ Using test user: {test_user.uid}")
print(f"   User ID: {test_user_id}")

# Step 3: Test API endpoint
print("\n📋 STEP 3: Testing /top-leader-gift/fund/overview API")
print("-" * 100)

BASE_URL = "http://localhost:8000"

# Check if server is running
try:
    health_check = requests.get(f"{BASE_URL}/docs", timeout=2)
    print("✅ Server is running\n")
except:
    print("❌ Server is not running. Please start the server:")
    print("   cd E:\\bitgpt\\backend")
    print("   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    sys.exit(1)

# Test the API
url = f"{BASE_URL}/top-leader-gift/fund/overview?user_id={test_user_id}"
print(f"🔗 URL: {url}\n")

# Note: This requires authentication token
# For testing, you'll need to add authentication

print("⚠️  Note: This API requires authentication token")
print("   You can test it using Postman or by adding authentication to this script")
print("\n📝 Example Request:")
print(f"   GET {url}")
print("   Headers:")
print("     Authorization: Bearer <your_token>")

print("\n" + "=" * 100)
print("EXPECTED RESPONSE STRUCTURE:")
print("=" * 100)
print("""
{
  "status": "Ok",
  "data": {
    "success": true,
    "user_id": "user_id_here",
    "is_eligible": false,
    "highest_level_achieved": 0,
    "total_fund": {
      "usdt": 10000.0,
      "bnb": 7.6
    },
    "levels": [
      {
        "level": 1,
        "level_name": "Level 1",
        "is_eligible": false,
        "is_maxed_out": false,
        "requirements": {
          "self_rank": 6,
          "direct_partners": 5,
          "partners_rank": 5,
          "total_team": 300
        },
        "current_status": {
          "self_rank": 0,
          "direct_partners": 0,
          "total_team": 0
        },
        "fund_allocation": {
          "percentage": 37.5,
          "allocated_usdt": 3750.0,
          "allocated_bnb": 2.85
        },
        "eligible_users_count": 0,
        "claimable_amount": {
          "usdt": 0.0,
          "bnb": 0.0
        },
        "claimed": {
          "usdt": 0.0,
          "bnb": 0.0
        },
        "remaining": {
          "usdt": 1800.0,
          "bnb": 0.91
        },
        "max_reward": {
          "usdt": 1800.0,
          "bnb": 0.91
        },
        "already_claimed_percent": 0.0
      },
      ... (similar for levels 2-5)
    ]
  },
  "message": "Fund overview retrieved successfully"
}
""")

print("\n" + "=" * 100)
print("API ENDPOINT DOCUMENTATION:")
print("=" * 100)
print("""
Endpoint: GET /top-leader-gift/fund/overview

Query Parameters:
  - user_id (required): User's MongoDB ObjectId

Headers:
  - Authorization: Bearer <token>

Features:
  ✓ Returns user's eligibility status for all 5 levels
  ✓ Shows claimable amounts in USDT and BNB per level
  ✓ Calculates fund allocation based on level percentages (37.5%, 25%, 15%, 12.5%, 10%)
  ✓ Divides allocated fund among eligible users equally
  ✓ Shows already claimed amount and percentage
  ✓ Shows remaining claimable amount capped by max reward limits
  ✓ Auto-checks eligibility based on rank, direct partners, and team size
""")

print("\n" + "=" * 100)
print("TEST SETUP COMPLETE")
print("=" * 100)

