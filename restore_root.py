from pymongo import MongoClient
from core.config import MONGO_URI
from bson import ObjectId
from datetime import datetime

client = MongoClient(MONGO_URI)
db = client['bitgpt']

ROOT_ID = ObjectId("68bee3aec1eac053757f5cf1")

print(f"Restoring ROOT user: {ROOT_ID}")

# 1. Create User
user_doc = {
    "_id": ROOT_ID,
    "uid": "1000000001",
    "refer_code": "ROOT001",
    "wallet_address": "0x0000000000000000000000000000000000000000",
    "name": "Mother Account",
    "role": "admin",
    "status": "active",
    "current_rank": "Bitron",
    "is_activated": True,
    "activation_date": datetime.utcnow(),
    "binary_joined": True,
    "matrix_joined": True,
    "global_joined": True,
    "binary_joined_at": datetime.utcnow(),
    "matrix_joined_at": datetime.utcnow(),
    "global_joined_at": datetime.utcnow(),
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}

try:
    db.users.insert_one(user_doc)
    print("✅ ROOT user restored")
except Exception as e:
    print(f"⚠️ ROOT user insert failed (maybe exists): {e}")

# 2. Create Matrix Tree
tree_doc = {
    "user_id": ROOT_ID,
    "current_slot": 1,
    "current_level": 1,
    "total_members": 0,
    "level_1_members": 0,
    "level_2_members": 0,
    "level_3_members": 0,
    "is_complete": False,
    "nodes": [],
    "slots": [
        {
            "slot_no": 1,
            "slot_name": "STARTER",
            "slot_value": 11.0,
            "level": 1,
            "members_count": 0,
            "is_active": True,
            "activated_at": datetime.utcnow(),
            "total_income": 0.0,
            "upgrade_cost": 0.0,
            "wallet_amount": 0.0
        }
    ],
    "reserve_fund": 0.0,
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}

try:
    db.matrix_trees.insert_one(tree_doc)
    print("✅ Matrix Tree restored")
except Exception as e:
    print(f"⚠️ Matrix Tree insert failed: {e}")

# 3. Create Matrix Activation
activation_doc = {
    "user_id": ROOT_ID,
    "slot_no": 1,
    "slot_name": "STARTER",
    "activation_type": "initial",
    "upgrade_source": "manual",
    "amount_paid": 11.0,
    "currency": "USDT",
    "tx_hash": "tx_root_restore",
    "is_auto_upgrade": False,
    "status": "completed",
    "activated_at": datetime.utcnow(),
    "completed_at": datetime.utcnow()
}

try:
    db.matrix_activations.insert_one(activation_doc)
    print("✅ Matrix Activation restored")
except Exception as e:
    print(f"⚠️ Matrix Activation insert failed: {e}")

# 4. Create User Wallet
wallet_doc = {
    "user_id": ROOT_ID,
    "wallet_type": "main",
    "currency": "USDT",
    "balance": 1000.0,
    "total_earnings": 0.0,
    "total_withdrawals": 0.0,
    "is_frozen": False,
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}

try:
    db.user_wallets.insert_one(wallet_doc)
    print("✅ User Wallet restored")
except Exception as e:
    print(f"⚠️ User Wallet insert failed: {e}")
