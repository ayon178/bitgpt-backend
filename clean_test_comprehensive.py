#!/usr/bin/env python3
"""
Comprehensive database cleanup for fresh test
"""

from mongoengine import connect
from modules.slot.model import SlotActivation
from modules.matrix.model import MatrixActivation, MatrixTree
from modules.tree.model import TreePlacement
from modules.user.model import User
from modules.wallet.model import ReserveLedger, UserWallet
from modules.income.model import IncomeEvent
from bson import ObjectId

# Connect to database
connect('bitgpt', host='mongodb://localhost:27017/')

print("🧹 Comprehensive database cleanup...")

# Get ROOT_ID
root_user = User.objects(name='Root').first()
if not root_user:
    print("❌ Root user not found!")
    exit(1)

ROOT_ID = str(root_user.id)
print(f"Root ID: {ROOT_ID}")

# Find User A
user_a = User.objects(name='UserA').first()
if user_a:
    user_a_id = str(user_a.id)
    print(f"Found User A: {user_a_id}")
    
    # Delete all downline users (D1-D12)
    downline_users = User.objects(refered_by=ObjectId(user_a_id)).delete()
    print(f"✅ Deleted {downline_users} downline users")
    
    # Delete User A
    user_a.delete()
    print("✅ Deleted User A")
    
    # Delete all tree placements for User A and downlines
    TreePlacement.objects(user_id=ObjectId(user_a_id)).delete()
    print("✅ Deleted User A tree placements")
    
    # Delete all matrix trees for User A
    MatrixTree.objects(user_id=ObjectId(user_a_id)).delete()
    print("✅ Deleted User A matrix trees")
    
    # Delete all matrix activations for User A
    MatrixActivation.objects(user_id=ObjectId(user_a_id)).delete()
    print("✅ Deleted User A matrix activations")
    
    # Delete all slot activations for User A
    SlotActivation.objects(user_id=ObjectId(user_a_id)).delete()
    print("✅ Deleted User A slot activations")
    
    # Delete all reserve ledgers for User A
    ReserveLedger.objects(user_id=ObjectId(user_a_id)).delete()
    print("✅ Deleted User A reserve ledgers")
    
    # Delete all income events for User A
    IncomeEvent.objects(user_id=ObjectId(user_a_id)).delete()
    print("✅ Deleted User A income events")

else:
    print("ℹ️ User A not found (already clean)")

# Delete any orphaned test data
SlotActivation.objects(tx_hash__startswith='tx_join_').delete()
MatrixActivation.objects(tx_hash__startswith='tx_join_').delete()

print("✅ Database fully cleaned!")
print("Ready for fresh test run")
