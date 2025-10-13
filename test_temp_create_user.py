"""
Test script for /user/temp-create endpoint
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.user.model import User
from modules.user.service import create_temp_user_service
import json

# Connect to database
connect_to_db()

print("=" * 100)
print(" " * 25 + "TEMP USER CREATE API TEST")
print("=" * 100)

# Step 1: Find a referral code for testing
print("\n📋 STEP 1: Finding Referral Code for Testing")
print("-" * 100)

# Get a user with refer_code
ref_user = User.objects(refer_code__exists=True).first()
if not ref_user:
    print("❌ No users with referral code found")
    print("   Please create a root user first")
    sys.exit(1)

ref_code = ref_user.refer_code
print(f"✅ Found referral code: {ref_code}")
print(f"   Referrer: {ref_user.name} ({ref_user.uid})")

# Step 2: Test temp user creation
print("\n📋 STEP 2: Testing Temp User Creation Service")
print("-" * 100)

import time
test_payload = {
    "email": f"temp_test_{int(time.time())}@example.com",
    "name": "Temp Test User",
    "refered_by": ref_code
}

print(f"\n📤 Request Payload:")
print(json.dumps(test_payload, indent=2))

result, error = create_temp_user_service(test_payload)

if error:
    print(f"\n❌ ERROR: {error}")
else:
    print(f"\n✅ SUCCESS - User Created!\n")
    
    print("=" * 100)
    print("📊 USER DATA")
    print("=" * 100)
    
    print(f"\n🔐 Auto-Generated Credentials (SAVE THESE!):")
    print(f"   Email:          {result['email']}")
    print(f"   Password:       {result['auto_password']} ⚠️  IMPORTANT!")
    print(f"   Wallet Address: {result['wallet_address']}")
    
    print(f"\n👤 User Information:")
    print(f"   User ID:        {result['_id']}")
    print(f"   UID:            {result['uid']}")
    print(f"   Refer Code:     {result['refer_code']}")
    print(f"   Name:           {result['name']}")
    
    print(f"\n🔗 Referral Information:")
    print(f"   Referred By ID:   {result['refered_by']}")
    print(f"   Referred By Code: {result['refered_by_code']}")
    if result.get('refered_by_name'):
        print(f"   Referred By Name: {result['refered_by_name']}")
    
    print(f"\n📋 Program Status:")
    print(f"   Binary Joined:  {result['binary_joined']} ✅")
    print(f"   Matrix Joined:  {result['matrix_joined']}")
    print(f"   Global Joined:  {result['global_joined']}")
    
    print(f"\n🔑 Access Token:")
    if result.get('token'):
        print(f"   Token Type: {result['token_type']}")
        token_str = str(result['token'])
        if len(token_str) > 50:
            print(f"   Token: {token_str[:50]}... (truncated)")
        else:
            print(f"   Token: {token_str}")
        print(f"   ✅ User can login immediately with this token!")
    else:
        print(f"   ⚠️  No token generated")
    
    print(f"\n📅 Created At: {result['created_at']}")
    
    print("\n" + "=" * 100)
    print("📄 COMPLETE JSON RESPONSE")
    print("=" * 100)
    print(json.dumps(result, indent=2, default=str))

# Step 3: Verify user in database
print("\n" + "=" * 100)
print("📋 STEP 3: Verifying User in Database")
print("=" * 100)

if result:
    created_user = User.objects(id=result['_id']).first()
    if created_user:
        print(f"\n✅ User verified in database!")
        print(f"   UID: {created_user.uid}")
        print(f"   Email: {created_user.email}")
        print(f"   Wallet: {created_user.wallet_address}")
        print(f"   Refer Code: {created_user.refer_code}")
        print(f"   Binary Joined: {created_user.binary_joined}")
    else:
        print(f"\n❌ User not found in database (error occurred)")

# Step 4: API endpoint info
print("\n" + "=" * 100)
print("📋 STEP 4: API Endpoint Information")
print("=" * 100)

print("""
Endpoint: POST /user/temp-create

Request Body:
{
  "email": "user@example.com",
  "name": "User Name",
  "refered_by": "RC12345"
}

Response (Success):
{
  "status": "Ok",
  "message": "User created successfully with auto-generated credentials",
  "data": {
    "_id": "user_mongodb_id",
    "uid": "user1234567890",
    "refer_code": "RC1234567890",
    "name": "User Name",
    "email": "user@example.com",
    "wallet_address": "0xABCD...",
    "auto_password": "generated_password",
    "refered_by": "referrer_id",
    "refered_by_code": "RC12345",
    "refered_by_name": "Referrer Name",
    "binary_joined": true,
    "matrix_joined": false,
    "global_joined": false,
    "created_at": "2025-10-13T...",
    "token": "eyJhbGci...",
    "token_type": "bearer"
  }
}

Features:
✓ Auto-generates wallet_address
✓ Auto-generates strong password
✓ Auto-generates uid
✓ Auto-generates refer_code
✓ Returns access token for immediate login
✓ Returns full user data
✓ Binary program auto-joined
✓ Same background processes as /user/create
✓ PartnerGraph auto-created
✓ Referrer's PartnerGraph updated

Differences from /user/create:
- No need for wallet_address (auto-generated)
- No need for password (auto-generated)
- No need for binary_payment_tx (for testing/temp purposes)
- Returns auto_password in response (user should save this)
""")

print("=" * 100)
print(" " * 35 + "TEST COMPLETE")
print("=" * 100)

