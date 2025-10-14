#!/usr/bin/env python3
"""
Test script to verify pools-summary shows changes when new users are created
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mongoengine import connect
from modules.user.model import User
from modules.wallet.service import WalletService
from bson import ObjectId
import json

# Connect to database
connect(
    db=os.getenv('MONGODB_NAME', 'bitgpt'),
    host=os.getenv('MONGODB_HOST', 'localhost'),
    port=int(os.getenv('MONGODB_PORT', 27017)),
    username=os.getenv('MONGODB_USERNAME'),
    password=os.getenv('MONGODB_PASSWORD'),
    authentication_source=os.getenv('MONGODB_AUTH_SOURCE', 'admin')
)

def main():
    print("\n" + "="*80)
    print("TESTING POOLS SUMMARY FIX")
    print("="*80)
    
    # 1. Find user with refer_code RC1760429616945918
    refer_code = "RC1760429616945918"
    user = User.objects(refer_code=refer_code).first()
    
    if not user:
        print(f"\n❌ User with refer_code {refer_code} not found!")
        return
    
    print(f"\n✅ Found user:")
    print(f"   ID: {user.id}")
    print(f"   UID: {user.uid}")
    print(f"   Refer Code: {user.refer_code}")
    print(f"   Name: {user.name}")
    
    # 2. Get pools-summary BEFORE
    print(f"\n📊 Getting pools-summary BEFORE new user creation...")
    wallet_service = WalletService()
    result_before = wallet_service.get_pools_summary(user_id=str(user.id))
    
    if result_before.get("success"):
        data_before = result_before.get("data", {})
        pools_before = data_before.get("pools", {})
        
        print("\n🔍 Pools Summary BEFORE:")
        print(f"   Binary Partner Incentive (BNB): {pools_before.get('binary_partner_incentive', {}).get('BNB', 0)}")
        print(f"   Binary Partner Incentive (USDT): {pools_before.get('binary_partner_incentive', {}).get('USDT', 0)}")
        print(f"   Duel Tree (BNB): {pools_before.get('duel_tree', {}).get('BNB', 0)}")
        print(f"   Duel Tree (USDT): {pools_before.get('duel_tree', {}).get('USDT', 0)}")
    else:
        print(f"\n❌ Failed to get pools summary: {result_before.get('error')}")
        return
    
    # 3. Count existing children
    children_count = User.objects(refered_by=user.id).count()
    print(f"\n👥 User currently has {children_count} direct referrals")
    
    # 4. Instructions
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print(f"\n1. Create a new user under {refer_code}")
    print(f"2. The new user will automatically:")
    print(f"   - Join Binary program")
    print(f"   - Activate Slot 1 & 2")
    print(f"   - Distribute 10% partner incentive to upline")
    print(f"   - Distribute 60% level distribution (dual tree earning)")
    print(f"\n3. After creating new user, run this script again to see changes")
    print("\n" + "="*80)
    
    # 5. Show recent children if any
    if children_count > 0:
        print(f"\nRecent referrals under {user.uid}:")
        children = User.objects(refered_by=user.id).order_by('-created_at').limit(5)
        for i, child in enumerate(children, 1):
            print(f"   {i}. {child.uid} (created: {child.created_at})")

if __name__ == "__main__":
    main()

