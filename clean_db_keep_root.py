#!/usr/bin/env python3
"""
Clean database except ROOT user
"""

from mongoengine import connect
from modules.user.model import User
from bson import ObjectId

from core.config import MONGO_URI
from pymongo import MongoClient

# Connect to database using config URI
connect('bitgpt', host=MONGO_URI)

print(f"🧹 Cleaning database (keeping ROOT user) at {MONGO_URI.split('@')[1] if '@' in MONGO_URI else 'localhost'}...")

# Find ROOT user (using known ID from remote DB)
ROOT_ID = "68bee3aec1eac053757f5cf1"
print(f"✅ Using ROOT user: {ROOT_ID}")

# Use MongoDB directly for efficient cleanup
client = MongoClient(MONGO_URI)
db = client['bitgpt']

# Delete all users except ROOT
result = db.users.delete_many({'_id': {'$ne': ObjectId(ROOT_ID)}})
print(f"✅ Deleted {result.deleted_count} users (kept ROOT)")

# Delete all slot activations
result = db.slot_activation.delete_many({})
print(f"✅ Deleted {result.deleted_count} slot activations")

# Delete all matrix activations
result = db.matrix_activation.delete_many({})
print(f"✅ Deleted {result.deleted_count} matrix activations")

# Delete all tree placements
result = db.tree_placement.delete_many({})
print(f"✅ Deleted {result.deleted_count} tree placements")

# Delete all matrix trees
result = db.matrix_tree.delete_many({})
print(f"✅ Deleted {result.deleted_count} matrix trees")

# Delete all reserve ledgers
result = db.reserve_ledger.delete_many({})
print(f"✅ Deleted {result.deleted_count} reserve ledgers")

# Delete all income events
result = db.income_event.delete_many({})
print(f"✅ Deleted {result.deleted_count} income events")

# Delete all user wallets except ROOT's
result = db.user_wallet.delete_many({'user_id': {'$ne': ObjectId(ROOT_ID)}})
print(f"✅ Deleted {result.deleted_count} user wallets (kept ROOT's)")

print("\n✅ Database cleaned successfully!")
print(f"Only ROOT user ({ROOT_ID}) remains")
