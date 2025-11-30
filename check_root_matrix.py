from mongoengine import connect
from modules.matrix.model import MatrixActivation, MatrixTree
from modules.user.model import User
from bson import ObjectId
from core.config import MONGO_URI
from decimal import Decimal
from datetime import datetime

connect('bitgpt', host=MONGO_URI)

ROOT_ID = "68bee3aec1eac053757f5cf1"

print(f"Checking Matrix status for ROOT user: {ROOT_ID}")

# Check MatrixActivation
activation = MatrixActivation.objects(user_id=ObjectId(ROOT_ID), slot_no=1).first()
if activation:
    print(f"✅ Matrix Slot 1 Activated: {activation.status}")
else:
    print("❌ Matrix Slot 1 NOT Activated")

# Check MatrixTree
tree = MatrixTree.objects(user_id=ObjectId(ROOT_ID)).first()
if tree:
    print(f"✅ Matrix Tree Exists: {tree.id}, Current Slot: {tree.current_slot}")
else:
    print("❌ Matrix Tree NOT Found. Creating...")
    tree = MatrixTree(user_id=ObjectId(ROOT_ID), current_slot=1, is_complete=False)
    tree.save()
    print(f"✅ Created Matrix Tree for ROOT: {tree.id}")

# Check MatrixActivation again/create if missing
if not activation:
    print("Creating MatrixActivation for Slot 1...")
    activation = MatrixActivation(
        user_id=ObjectId(ROOT_ID),
        slot_no=1,
        slot_name="STARTER",
        activation_type="initial",
        amount_paid=Decimal("11"),
        tx_hash="tx_root_init",
        status="completed",
        completed_at=datetime.utcnow()
    )
    activation.save()
    print(f"✅ Created MatrixActivation for ROOT Slot 1: {activation.id}")

# Ensure Slot 1 is in MatrixTree slots
slot_exists = False
for slot in tree.slots:
    if slot.slot_no == 1:
        slot_exists = True
        break

if not slot_exists:
    from modules.matrix.model import MatrixSlotInfo
    print("Adding Slot 1 to MatrixTree slots...")
    slot_info = MatrixSlotInfo(
        slot_no=1,
        slot_name="STARTER",
        slot_value=Decimal("11"),
        level=1,
        members_count=0,
        is_active=True,
        activated_at=datetime.utcnow()
    )
    tree.slots.append(slot_info)
    tree.save()
    print("✅ Added Slot 1 to MatrixTree")
