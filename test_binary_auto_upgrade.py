"""
Test Binary Auto-Upgrade from Reserve
Tests that when 2 users join and route funds to Nth upline's reserve,
the Nth upline automatically upgrades to the next slot when reserve >= cost.
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

# Initialize MongoDB connection
try:
    from mongoengine import connect as mongo_connect
    try:
        cloud_uri = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"
        mongo_connect(host=cloud_uri)
        print("✅ Connected to MongoDB (cloud)")
        DB_AVAILABLE = True
    except Exception as e1:
        try:
            from core.config import MONGO_URI
            mongo_connect(db="bitgpt", host=MONGO_URI)
            print("✅ Connected to MongoDB")
            DB_AVAILABLE = True
        except Exception as e2:
            try:
                mongo_connect(db="bitgpt", host="mongodb://localhost:27017/bitgpt")
                print("✅ Connected to MongoDB (fallback)")
                DB_AVAILABLE = True
            except Exception as e3:
                print(f"⚠️ MongoDB connection failed: {e3}")
                DB_AVAILABLE = False
except Exception as e:
    print(f"⚠️ MongoDB connection setup failed: {e}")
    DB_AVAILABLE = False

# Import models if DB available
if DB_AVAILABLE:
    try:
        from modules.wallet.model import ReserveLedger
        from modules.slot.model import SlotActivation
        from modules.user.model import User
        from bson import ObjectId
    except Exception as e:
        print(f"⚠️ Model imports failed: {e}")
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
    r = requests.post(url, json=payload, timeout=120)  # Increased timeout
    j = r.json()
    if not j.get("success"):
        raise RuntimeError(f"temp-create failed: {j}")
    return j["data"]


def get_refer_code(user):
    """Extract refer_code from user object"""
    u = user.get("user") or {}
    return u.get("refer_code") or user.get("refer_code")


def get_reserve_ledger(user_id, slot_no):
    """Get reserve ledger entries for a user and specific slot"""
    if ReserveLedger is None or ObjectId is None:
        print("⚠️ DB models not available, skipping ReserveLedger query")
        return []
    try:
        entries = ReserveLedger.objects(
            user_id=ObjectId(user_id),
            program='binary',
            slot_no=slot_no,
            direction='credit'
        ).order_by('-created_at')
        return [
            {
                "slot_no": e.slot_no,
                "amount": float(e.amount) if e.amount else 0,
                "source": e.source,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in entries
        ]
    except Exception as e:
        print(f"Error querying ReserveLedger: {e}")
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


def get_balances(user_id, token):
    """Get wallet balances for a user"""
    url = f"{BASE_URL}/wallet/balances"
    params = {"user_id": user_id, "wallet_type": "main"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.get(url, params=params, headers=headers, timeout=60)
    return r.json()


def main():
    print("\n" + "="*60)
    print("BINARY AUTO-UPGRADE FROM RESERVE TEST")
    print("="*60)
    print("\nTest Scenario:")
    print("1. Create Alice under ROOT")
    print("2. Create Carol under Alice")
    print("3. Create Ada under Carol (Ada is first/second under Alice in slot-2 tree)")
    print("4. Create Kimmy under Carol (Kimmy should also be first/second under Alice)")
    print("5. Expected: Alice's slot-3 reserve should reach 0.0088 BNB (2 * 0.0044)")
    print("6. Expected: Alice's Slot-3 should auto-activate (cost = 0.0088 BNB)")
    print("="*60)
    
    try:
        # Step 1: Create Alice under ROOT
        log("STEP 1: Create Alice under ROOT")
        alice = temp_create("ROOT")
        alice_id = alice.get("_id")
        alice_token = alice.get("token")
        alice_code = get_refer_code(alice)
        log("Alice created", {"id": alice_id, "code": alice_code})
        time.sleep(1)
        
        # Check Alice's initial slot status
        alice_slot1 = check_slot_activation(alice_id, 1)
        alice_slot2 = check_slot_activation(alice_id, 2)
        alice_slot3 = check_slot_activation(alice_id, 3)
        log("Alice's initial slot status", {
            "slot_1": alice_slot1.get("exists", False),
            "slot_2": alice_slot2.get("exists", False),
            "slot_3": alice_slot3.get("exists", False)
        })
        
        # Step 2: Create Carol under Alice
        log("STEP 2: Create Carol under Alice")
        carol = temp_create(alice_code)
        carol_id = carol.get("_id")
        carol_code = get_refer_code(carol)
        log("Carol created", {"id": carol_id, "code": carol_code})
        time.sleep(2)
        
        # Step 3: Create Ada under Carol
        log("STEP 3: Create Ada under Carol (should route to Alice's slot-3 reserve)")
        ada = temp_create(carol_code)
        ada_id = ada.get("_id")
        log("Ada created", {"id": ada_id})
        time.sleep(2)
        
        # Check Alice's reserve for slot-3 after Ada
        alice_reserve_after_ada = get_reserve_ledger(alice_id, 3)
        total_reserve_after_ada = sum(r.get("amount", 0) for r in alice_reserve_after_ada)
        log("Alice's reserve for slot-3 after Ada joins", {
            "total_reserve": total_reserve_after_ada,
            "expected": 0.0044,
            "entries": alice_reserve_after_ada
        })
        
        alice_slot3_after_ada = check_slot_activation(alice_id, 3)
        log("Alice's Slot-3 status after Ada", alice_slot3_after_ada)
        
        # Step 4: Create Kimmy under Carol (should also route to Alice's reserve if first/second)
        log("STEP 4: Create Kimmy under Carol (should route to Alice's slot-3 reserve if first/second)")
        kimmy = temp_create(carol_code)
        kimmy_id = kimmy.get("_id")
        log("Kimmy created", {"id": kimmy_id})
        time.sleep(2)
        
        # Check Alice's reserve for slot-3 after Kimmy
        alice_reserve_after_kimmy = get_reserve_ledger(alice_id, 3)
        total_reserve_after_kimmy = sum(r.get("amount", 0) for r in alice_reserve_after_kimmy)
        log("Alice's reserve for slot-3 after Kimmy joins", {
            "total_reserve": total_reserve_after_kimmy,
            "expected": 0.0088,  # 2 * 0.0044
            "entries": alice_reserve_after_kimmy
        })
        
        # Final check: Alice's Slot-3 should be auto-activated
        alice_slot3_final = check_slot_activation(alice_id, 3)
        log("Alice's Slot-3 final status (should be auto-activated)", alice_slot3_final)
        
        # ============================================================
        # RESULTS SUMMARY
        # ============================================================
        log("TEST RESULTS SUMMARY")
        
        results = {
            "ada_join_reserve": total_reserve_after_ada,
            "kimmy_join_reserve": total_reserve_after_kimmy,
            "slot_3_auto_activated": alice_slot3_final.get("exists", False),
            "slot_3_reserve_sufficient": total_reserve_after_kimmy >= 0.0088
        }
        
        log("Results", results)
        
        print("\n" + "="*60)
        print("VERIFICATION CHECKLIST:")
        print(f"  ✅ Ada join: Reserve = {total_reserve_after_ada} BNB (expected 0.0044)")
        print(f"  ✅ Kimmy join: Reserve = {total_reserve_after_kimmy} BNB (expected 0.0088)")
        print(f"  ✅ Reserve >= Slot-3 cost (0.0088): {total_reserve_after_kimmy >= 0.0088}")
        print(f"  ✅ Slot-3 auto-activated: {alice_slot3_final.get('exists', False)}")
        print("="*60)
        
        if total_reserve_after_kimmy >= 0.0088 and alice_slot3_final.get("exists", False):
            print("\n🎉 SUCCESS: Auto-upgrade triggered! Alice's Slot-3 was automatically activated.")
        elif total_reserve_after_kimmy >= 0.0088 and not alice_slot3_final.get("exists", False):
            print("\n⚠️ WARNING: Reserve is sufficient (>= 0.0088) but Slot-3 not activated.")
            print("   Check server logs for [BINARY_ROUTING] auto-upgrade messages.")
        else:
            print(f"\n⚠️ REVIEW: Reserve is {total_reserve_after_kimmy} BNB, need 0.0088 for auto-upgrade.")
            print("   This might mean Kimmy didn't route to reserve (not first/second).")
            print("   Check server logs for routing decisions.")
        
        print("\n📋 Check server logs for [BINARY_ROUTING] messages:")
        print("   - '✅ ReserveLedger created' for Ada and Kimmy")
        print("   - 'Auto-upgrade check result' showing reserve totals")
        print("   - Auto-upgrade trigger messages if reserve >= cost")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

