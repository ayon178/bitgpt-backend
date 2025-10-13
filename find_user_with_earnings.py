"""
Find users who have earnings data in global program
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.tree.model import TreePlacement
from modules.user.model import User
from modules.income.model import Income

connect_to_db()

print("=" * 80)
print("SEARCHING FOR USERS WITH GLOBAL EARNINGS")
print("=" * 80)

# Find users in global program
global_placements = TreePlacement.objects(program='global').limit(20)

print("\nChecking users for earnings data...")

users_with_earnings = []

for placement in global_placements:
    user = User.objects(id=placement.user_id).first()
    if user:
        # Check if user has income records for global
        income_records = Income.objects(
            user_id=placement.user_id,
            program='global'
        ).limit(1)
        
        if income_records:
            print(f"✅ Found: {user.uid} has global earnings")
            users_with_earnings.append({
                'uid': user.uid,
                'user_id': str(user.id),
                'earnings_count': Income.objects(user_id=placement.user_id, program='global').count()
            })

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

if users_with_earnings:
    print(f"\nFound {len(users_with_earnings)} users with global earnings:\n")
    for idx, user_info in enumerate(users_with_earnings, 1):
        print(f"{idx}. UID: {user_info['uid']}")
        print(f"   User ID: {user_info['user_id']}")
        print(f"   Earnings Count: {user_info['earnings_count']}")
        print()
else:
    print("\n⚠️  No users found with global earnings data")
    print("   Users have joined global but may not have received earnings yet")

# Also check total global income records
total_global_income = Income.objects(program='global').count()
print(f"\nTotal global income records in database: {total_global_income}")


