"""
Test simplified claim history API
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.user.model import User
from modules.top_leader_gift.payment_model import TopLeadersGiftPayment
from modules.top_leader_gift.claim_service import TopLeadersGiftClaimService
import json

# Connect to database
connect_to_db()

print("=" * 100)
print(" " * 20 + "SIMPLIFIED CLAIM HISTORY API TEST")
print("=" * 100)

# Find user with payment history
payment = TopLeadersGiftPayment.objects(payment_status='paid').first()

if not payment:
    print("\n⚠️  No paid claims found in database")
    sys.exit(1)

user = User.objects(id=payment.user_id).first()
if not user:
    print("❌ User not found")
    sys.exit(1)

test_user_id = str(user.id)

print(f"\n📋 Testing with User: {user.uid}")
print(f"   User ID: {test_user_id}")

# Test the service
service = TopLeadersGiftClaimService()
result = service.get_claim_history(test_user_id)

if result.get("success"):
    print(f"\n✅ SUCCESS!\n")
    
    print("=" * 100)
    print("📊 CLAIM HISTORY")
    print("=" * 100)
    
    claims = result.get('claims', [])
    
    print(f"\nTotal Claims: {len(claims)}\n")
    
    if claims:
        for idx, claim in enumerate(claims, 1):
            print(f"{'─'*100}")
            print(f"Claim #{idx}")
            print(f"{'─'*100}")
            print(f"   Level:    {claim['level']}")
            print(f"   Currency: {claim['currency']}")
            print(f"   Amount:")
            print(f"      USDT: ${claim['amount']['usdt']:,.2f}")
            print(f"      BNB:  {claim['amount']['bnb']:.4f}")
            print(f"   Date:     {claim['date']}")
            print(f"   Time:     {claim['time']}")
            print()
    else:
        print("   No claims found")
    
    print("=" * 100)
    print("📄 COMPLETE JSON RESPONSE")
    print("=" * 100)
    print(json.dumps(result, indent=2, default=str))
    
    print("\n" + "=" * 100)
    print("API RESPONSE STRUCTURE")
    print("=" * 100)
    print("""
{
  "success": true,
  "user_id": "...",
  "claims": [
    {
      "level": 1,
      "currency": "BOTH",
      "amount": {
        "usdt": 1800.0,
        "bnb": 0.91
      },
      "time": "02:44 PM",
      "date": "2025-10-07",
      "datetime": "2025-10-07 14:44:13.680000"
    }
  ]
}

Features:
✓ Simple claims array (no complex nested objects)
✓ Level-wise data (level field)
✓ Currency-wise data (currency field: USDT/BNB/BOTH)
✓ Amount object with USDT and BNB
✓ Time in 12-hour format (e.g., 02:44 PM)
✓ Date in YYYY-MM-DD format
✓ Full datetime for sorting/filtering
✓ Only successful (paid) claims shown
✓ Recent claims first (ordered by date)
""")
    
else:
    print(f"\n❌ ERROR: {result.get('error')}")

print("=" * 100)
print(" " * 35 + "TEST COMPLETE")
print("=" * 100)

