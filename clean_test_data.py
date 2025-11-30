#!/usr/bin/env python3
"""
Clean test data from database before running fresh test
"""

from mongoengine import connect
from modules.slot.model import SlotActivation
from modules.matrix.model import MatrixActivation, MatrixTree
from modules.tree.model import TreePlacement
from modules.user.model import User
from modules.wallet.model import ReserveLedger, UserWallet
from bson import ObjectId

# Connect to database
connect('bitgpt', host='mongodb://localhost:27017/')

print("🧹 Cleaning test data...")

# Delete test users (those with tx_hash starting with tx_join_D)
deleted_activations = SlotActivation.objects(tx_hash__startswith='tx_join_D').delete()
print("✅ Database cleaned!")
print("Ready for fresh test run")
