"""
Test Binary Reserve Routing vs Pools Distribution
Tests specific tree structure:
- Alice (main user)
- Under Alice: User1, User2 (2 direct children)
- Under User1: User1A, User1B (2 users)
- Under User2: User2A, User2B (2 users - total 4 descendants under Alice)
Checks which users' Slot-2 funds route to Alice's reserve vs pools distribution.
"""

import requests
import json
import time
import sys
import os
from decimal import Decimal

BASE_URL = "http://localhost:8000"

# Add backend to path for direct DB access
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Add parent directory to path for core module
parent_dir = os.path.dirname(backend_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Initialize MongoDB connection
DB_AVAILABLE = False
try:
    import mongoengine
    from mongoengine import connect as mongo_connect
    
    try:
        # Try cloud MongoDB first
        cloud_uri = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"
        mongo_connect(host=cloud_uri, alias='default')
        print("✅ Connected to MongoDB (cloud)")
        DB_AVAILABLE = True
    except Exception as e1:
        try:
            # Try using config
            sys.path.insert(0, backend_dir)
            from core.config import MONGO_URI
            mongo_connect(db="bitgpt", host=MONGO_URI, alias='default')
            print("✅ Connected to MongoDB (config)")
            DB_AVAILABLE = True
        except Exception as e2:
            try:
                # Try localhost fallback
                mongo_connect(db="bitgpt", host="mongodb://localhost:27017/bitgpt", alias='default')
                print("✅ Connected to MongoDB (localhost)")
                DB_AVAILABLE = True
            except Exception as e3:
                print(f"⚠️ MongoDB connection failed: {e3}")
                DB_AVAILABLE = False
except ImportError:
    print("⚠️ mongoengine not available - installing...")
    try:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mongoengine"])
        from mongoengine import connect as mongo_connect
        cloud_uri = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"
        mongo_connect(host=cloud_uri, alias='default')
        print("✅ Connected to MongoDB after install")
        DB_AVAILABLE = True
    except Exception as install_e:
        print(f"⚠️ Failed to install mongoengine: {install_e}")
        DB_AVAILABLE = False
except Exception as e:
    print(f"⚠️ MongoDB connection setup failed: {e}")
    DB_AVAILABLE = False

# Import models if DB available
if DB_AVAILABLE:
    try:
        # Import without full backend dependencies if possible
        import importlib.util
        import importlib
        
        # Try to set up minimal environment for model imports
        sys.path.insert(0, backend_dir)
        
        # Import models directly
        try:
            from modules.wallet.model import ReserveLedger
            from modules.slot.model import SlotActivation
            from modules.user.model import User
            from bson import ObjectId
            print("✅ Model imports successful")
        except Exception as import_e:
            # Try alternative import paths
            try:
                import sys
                # Add backend to path explicitly
                if backend_dir not in sys.path:
                    sys.path.insert(0, backend_dir)
                
                # Try importing with minimal dependencies
                from modules.wallet.model import ReserveLedger
                from modules.slot.model import SlotActivation
                from modules.user.model import User
                from bson import ObjectId
                print("✅ Model imports successful (alternative path)")
            except Exception as e2:
                print(f"⚠️ Model imports failed: {e2}")
                ReserveLedger = None
                SlotActivation = None
                User = None
                ObjectId = None
    except Exception as e:
        print(f"⚠️ Model import setup failed: {e}")
        ReserveLedger = None
        SlotActivation = None
        User = None
        ObjectId = None
else:
    ReserveLedger = None
    SlotActivation = None
    User = None
    ObjectId = None


def log(title, data=None):
    print(f"\n{'='*60}")
    print(f"=== {title} ===")
    print('='*60)
    if data is not None:
        try:
            print(json.dumps(data, indent=2))
        except Exception:
            print(data)


def temp_create(refered_by="ROOT"):
    """Create a temp user via API"""
    url = f"{BASE_URL}/user/temp-create"
    payload = {"refered_by": refered_by, "wallet_address": "0x" + str(int(time.time()*1000)).zfill(40)[:40]}
    r = requests.post(url, json=payload, timeout=120)
    j = r.json()
    if not j.get("success"):
        raise RuntimeError(f"temp-create failed: {j}")
    return j["data"]


def get_refer_code(user):
    """Extract refer_code from user object"""
    u = user.get("user") or {}
    return u.get("refer_code") or user.get("refer_code")


def get_reserve_ledger(user_id, slot_no, direction_filter=None):
    """Get reserve ledger entries for a user and specific slot"""
    if ReserveLedger is None or ObjectId is None:
        print("⚠️ DB models not available, skipping ReserveLedger query")
        return []
    try:
        query = {
            "user_id": ObjectId(user_id),
            "program": 'binary',
            "slot_no": slot_no
        }
        if direction_filter:
            query["direction"] = direction_filter
        
        entries = ReserveLedger.objects(**query).order_by('-created_at')
        return [
            {
                "slot_no": e.slot_no,
                "amount": float(e.amount) if e.amount else 0,
                "direction": e.direction,
                "source": e.source,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in entries
        ]
    except Exception as e:
        print(f"Error querying ReserveLedger: {e}")
        return []


def get_wallet_ledger_entries(user_id, reason_pattern):
    """Get wallet ledger entries matching a reason pattern"""
    if User is None or ObjectId is None:
        return []
    try:
        from modules.wallet.model import WalletLedger
        entries = WalletLedger.objects(
            user_id=ObjectId(user_id),
            reason__icontains=reason_pattern,
            type='credit'
        ).order_by('-created_at')
        return [
            {
                "amount": float(e.amount) if e.amount else 0,
                "reason": e.reason,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in entries
        ]
    except Exception as e:
        print(f"Error querying WalletLedger: {e}")
        return []


def check_slot_activation(user_id, slot_no):
    """Check if a user has a specific slot activated"""
    if SlotActivation is None or ObjectId is None:
        print("⚠️ DB models not available, skipping SlotActivation query")
        return {"exists": False, "error": "DB models not loaded"}
    try:
        activation = SlotActivation.objects(
            user_id=ObjectId(user_id),
            program='binary',
            slot_no=slot_no,
            status='completed'
        ).first()
        return {
            "exists": activation is not None,
            "slot_name": activation.slot_name if activation else None,
            "activated_at": activation.activated_at.isoformat() if activation and activation.activated_at else None,
            "amount_paid": float(activation.amount_paid) if activation and activation.amount_paid else None
        }
    except Exception as e:
        print(f"Error checking SlotActivation: {e}")
        return {"exists": False, "error": str(e)}


def main():
    print("\n" + "="*60)
    print("BINARY RESERVE ROUTING vs POOLS DISTRIBUTION TEST")
    print("="*60)
    print("\nTree Structure:")
    print("  Alice")
    print("    ├── User1")
    print("    │   ├── User1A")
    print("    │   └── User1B")
    print("    └── User2")
    print("        ├── User2A")
    print("        └── User2B")
    print("\nExpected:")
    print("  - User1A, User1B (first 2 at level 2+) → Alice's reserve")
    print("  - User2A, User2B (next 2 at level 2+) → Pools distribution")
    print("="*60)
    
    try:
        # Step 1: Create Alice under ROOT
        log("STEP 1: Create Alice under ROOT")
        alice = temp_create("ROOT")
        alice_id = alice.get("_id")
        alice_token = alice.get("token")
        alice_code = get_refer_code(alice)
        log("Alice created", {"id": alice_id, "code": alice_code})
        time.sleep(2)
        
        # Step 2: Create User1 and User2 under Alice
        log("STEP 2: Create User1 and User2 under Alice")
        user1 = temp_create(alice_code)
        user1_id = user1.get("_id")
        user1_code = get_refer_code(user1)
        log("User1 created", {"id": user1_id, "code": user1_code})
        time.sleep(2)
        
        user2 = temp_create(alice_code)
        user2_id = user2.get("_id")
        user2_code = get_refer_code(user2)
        log("User2 created", {"id": user2_id, "code": user2_code})
        time.sleep(2)
        
        # Step 3: Create User1A and User1B under User1
        log("STEP 3: Create User1A and User1B under User1 (should route to Alice's reserve if first/second)")
        user1a = temp_create(user1_code)
        user1a_id = user1a.get("_id")
        log("User1A created", {"id": user1a_id})
        time.sleep(2)
        
        # Check Alice's reserve after User1A
        alice_reserve_after_1a = get_reserve_ledger(alice_id, 3)
        total_reserve_1a = sum(r.get("amount", 0) for r in alice_reserve_after_1a)
        log("Alice's reserve after User1A", {
            "total_reserve": total_reserve_1a,
            "expected": 0.0044 if user1a_id else 0,
            "entries": alice_reserve_after_1a
        })
        
        user1b = temp_create(user1_code)
        user1b_id = user1b.get("_id")
        log("User1B created", {"id": user1b_id})
        time.sleep(2)
        
        # Check Alice's reserve after User1B
        alice_reserve_after_1b = get_reserve_ledger(alice_id, 3)
        total_reserve_1b = sum(r.get("amount", 0) for r in alice_reserve_after_1b)
        log("Alice's reserve after User1B", {
            "total_reserve": total_reserve_1b,
            "expected": 0.0088 if user1a_id and user1b_id else 0,
            "entries": alice_reserve_after_1b
        })
        
        # Step 4: Create User2A and User2B under User2 (should go to pools if not first/second)
        log("STEP 4: Create User2A and User2B under User2 (should go to pools if not first/second)")
        user2a = temp_create(user2_code)
        user2a_id = user2a.get("_id")
        log("User2A created", {"id": user2a_id})
        time.sleep(2)
        
        user2b = temp_create(user2_code)
        user2b_id = user2b.get("_id")
        log("User2B created", {"id": user2b_id})
        time.sleep(2)
        
        # Wait a bit for auto-upgrade to process
        time.sleep(3)
        
        # Final checks
        alice_reserve_final = get_reserve_ledger(alice_id, 3)
        # Calculate total reserve (credits - debits)
        total_reserve_final = Decimal('0')
        for r in alice_reserve_final:
            direction = r.get("direction", "credit")
            if direction == "credit":
                total_reserve_final += Decimal(str(r.get("amount", 0)))
            elif direction == "debit":
                total_reserve_final -= Decimal(str(r.get("amount", 0)))
        
        # Find ROOT user ID (Alice's 3rd upline for Slot-3)
        root_id = None
        if User is not None and ObjectId is not None:
            try:
                from modules.user.model import User as UserModel
                root_user = UserModel.objects(uid="ROOT").first()
                if root_user:
                    root_id = str(root_user.id)
            except:
                pass
        
        # Check for Slot-4 reserve (if Alice's Slot-3 auto-upgraded, check where that 0.0088 went)
        # Alice's 3rd upline is ROOT, so check ROOT's Slot-4 reserve
        root_reserve_slot4 = get_reserve_ledger(root_id, 4) if root_id else []
        alice_slot3 = check_slot_activation(alice_id, 3)
        
        # Check Alice's wallet for pools distribution entries (if upgrade amount went to pools)
        alice_wallet_entries = get_wallet_ledger_entries(alice_id, "binary_partner_incentive")
        
        # Check if Alice's Slot-3 upgrade amount (0.0088) was routed
        # This happens when Alice auto-upgrades - the upgrade amount follows routing rules
        log("STEP 5: Check Alice's Slot-3 auto-upgrade routing")
        print(f"\n🔍 Checking Alice's Slot-3 auto-upgrade routing:")
        print(f"   - Alice's Slot-3 activated: {alice_slot3.get('exists', False)}")
        print(f"   - Slot-3 cost: 0.0088 BNB")
        print(f"   - Alice's 3rd upline: ROOT (for Slot-3 tree)")
        print(f"   - If Alice is first/second in ROOT's Slot-3 tree:")
        print(f"     → Should go to ROOT's Slot-4 reserve")
        print(f"   - If not first/second:")
        print(f"     → Should distribute via pools")
        if root_id:
            print(f"   - ROOT's Slot-4 reserve entries: {len(root_reserve_slot4)}")
        else:
            print(f"   - ⚠️ Could not find ROOT user ID")
        
        log("FINAL RESULTS")
        results = {
            "alice_slot3_reserve_total": float(total_reserve_final),  # For Slot-3 before upgrade
            "alice_slot3_reserve_entries": len(alice_reserve_final),
            "alice_slot3_activated": alice_slot3.get("exists", False),
            "root_slot4_reserve_entries": len(root_reserve_slot4),  # Where Slot-3 upgrade amount went (ROOT's reserve)
            "alice_wallet_partner_incentive_entries": len(alice_wallet_entries),
            "reserve_routing_users": ["User1A", "User1B"] if total_reserve_final >= 0.0088 else [],
            "pools_distribution_users": ["User2A", "User2B"] if total_reserve_final < 0.0088 else []
        }
        
        log("Summary", results)
        
        print("\n" + "="*60)
        print("VERIFICATION:")
        print(f"  ✅ Alice's Slot-3 reserve: {total_reserve_final} BNB")
        print(f"     - Expected: 0.0088 BNB (from User1A + User1B if first/second)")
        print(f"     - Reserve entries: {len(alice_reserve_final)}")
        print(f"  ✅ Alice's Slot-3 activated: {alice_slot3.get('exists', False)}")
        print(f"     - Expected: True if reserve >= 0.0088 BNB")
        
        if alice_slot3.get("exists", False):
            print(f"  ✅ Alice's Slot-3 upgrade amount routing (0.0088 BNB):")
            if root_id:
                print(f"     - ROOT's Slot-4 reserve entries: {len(root_reserve_slot4)}")
                print(f"       → If Alice is first/second in ROOT's Slot-3 tree: should have reserve entry")
                print(f"       → If not: should have pools distribution")
            print(f"     - Alice's wallet pools entries: {len(alice_wallet_entries)}")
        
        print("="*60)
        
        if total_reserve_final >= Decimal('0.0088') and alice_slot3.get("exists", False):
            print("\n🎉 SUCCESS: Reserve routing and auto-upgrade working!")
            print(f"   - User1A and User1B routed {total_reserve_final} BNB to Alice's reserve")
            print(f"   - Alice's Slot-3 auto-activated")
            
            if len(root_reserve_slot4) > 0:
                print(f"   - ✅ Alice's Slot-3 upgrade amount ({0.0088} BNB) routed to ROOT's Slot-4 reserve")
                print(f"     → Alice is first/second in ROOT's Slot-3 tree")
            elif len(alice_wallet_entries) > 0:
                print(f"   - ✅ Alice's Slot-3 upgrade amount ({0.0088} BNB) distributed via pools")
                print(f"     → Alice is NOT first/second in ROOT's Slot-3 tree")
            else:
                print(f"   - ⚠️ Alice's Slot-3 upgrade amount routing unclear (check server logs)")
        elif total_reserve_final >= Decimal('0.0088'):
            print(f"\n⚠️ Reserve sufficient ({total_reserve_final} BNB) but Slot-3 not activated")
            print("   Check server logs for auto-upgrade trigger messages")
        elif total_reserve_final > 0:
            print(f"\n⚠️ Partial reserve routing: {total_reserve_final} BNB")
            print("   Some users routed to reserve, others may have gone to pools")
        else:
            print("\n⚠️ No reserve routing detected")
            print("   All funds may have gone to pools distribution")
        
        print("\n📋 Check server logs for [BINARY_ROUTING] messages:")
        print("   - '✅ ReserveLedger created' for User1A, User1B (if first/second)")
        print("   - '🚀 Auto-upgrading' when Alice's Slot-3 activates")
        print("   - 'Auto-upgrade Slot 3: checking routing rules' for upgrade amount routing")
        print("   - Pools distribution messages for User2A, User2B (if not first/second)")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

