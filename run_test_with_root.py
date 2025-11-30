#!/usr/bin/env python3
"""
Test Matrix middle child detection and auto-upgrade with ROOT user
"""

from mongoengine import connect
from modules.matrix.service import MatrixService
from modules.user.model import User
from modules.wallet.model import ReserveLedger
from modules.matrix.model import MatrixActivation
from modules.tree.model import TreePlacement
from decimal import Decimal
from datetime import datetime
from bson import ObjectId

# Connect to database
connect('bitgpt', host='mongodb://localhost:27017/')

def get_reserve_balance(user_id, slot_no):
    """Get reserve balance for a user and slot"""
    ledger_entries = ReserveLedger.objects(
        user_id=ObjectId(user_id),
        program='matrix',
        slot_no=slot_no
    ).order_by('-created_at')
    
    if ledger_entries:
        return ledger_entries[0].balance_after
    return Decimal('0')

def check_slot_activated(user_id, slot_no):
    """Check if a slot is activated"""
    activation = MatrixActivation.objects(
        user_id=ObjectId(user_id),
        slot_no=slot_no,
        status='completed'
    ).first()
    return activation is not None

print("🧪 Testing Matrix Middle Child Detection and Auto-Upgrade")
print("=" * 70)

# Find ROOT user
root = User.objects(refer_code='ROOT').first()
if not root:
    print("❌ ROOT user not found! Please create a user with refer_code='ROOT'")
    exit(1)

ROOT_ID = str(root.id)
print(f"✅ Found ROOT user: {ROOT_ID}")

svc = MatrixService()

# Use the existing reproduce_matrix_issue.py script
print("\n📝 Running reproduce_matrix_issue.py...")
import subprocess
result = subprocess.run(['python', '-X', 'utf8', 'reproduce_matrix_issue.py'], 
                       capture_output=True, text=True, encoding='utf-8')

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

print("\n" + "=" * 70)
print("✅ Test completed! Check output above for results.")
