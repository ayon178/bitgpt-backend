#!/usr/bin/env python3
import sys
import os
from bson import ObjectId

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

MONGODB_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

try:
    from mongoengine import connect
    try:
        connect(host=MONGODB_URI)
        print("✅ Connected to MongoDB")
    except Exception as e1:
        try:
            from core.config import MONGO_URI
            connect(db="bitgpt", host=MONGO_URI)
            print("✅ Connected to MongoDB (config)")
        except Exception as e2:
            print(f"❌ MongoDB connection failed: {e2}")
            sys.exit(1)
except Exception as e:
    print(f"❌ MongoDB connection setup failed: {e}")
    sys.exit(1)

from modules.user.model import User
from modules.slot.model import SlotActivation

TARGET_USER_REFER_CODE = "RC1762150704576515"
TARGET_USER_ID = "690849321d19c24e852d38b2"


def main():
    # Resolve target user
    user = User.objects(refer_code=TARGET_USER_REFER_CODE).first()
    if not user and TARGET_USER_ID:
        try:
            user = User.objects(id=ObjectId(TARGET_USER_ID)).first()
        except Exception:
            user = None

    if not user:
        print("❌ Target user not found")
        return

    print(f"🎯 Target: {user.refer_code} ({user.id})")

    # Find Slot 17 binary activation(s)
    acts = list(SlotActivation.objects(
        user_id=user.id,
        program='binary',
        slot_no=17
    ))

    if not acts:
        print("ℹ️ No Slot 17 activation found; nothing to delete.")
        return

    print(f"🧹 Found {len(acts)} Slot 17 activation(s). Deleting...")
    deleted = 0
    for act in acts:
        try:
            act.delete()
            deleted += 1
        except Exception as e:
            print(f"⚠️ Failed to delete {act.id}: {e}")

    print(f"✅ Deleted {deleted} Slot 17 activation(s) for user {user.refer_code}.")


if __name__ == "__main__":
    main()
