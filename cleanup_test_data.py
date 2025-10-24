#!/usr/bin/env python3
"""
Global Program Test Data Cleanup Script
Clean up test data from database
"""

import os
import sys
from datetime import datetime

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from modules.user.model import User
from modules.tree.model import TreePlacement
from modules.global.model import GlobalTeamMember, GlobalPhaseProgression, GlobalTreeStructure, GlobalPhaseSeat
from modules.income.model import IncomeEvent
from modules.wallet.model import UserWallet, ReserveLedger, WalletLedger
from modules.income.bonus_fund import BonusFund

def cleanup_test_users():
    """Clean up test users"""
    try:
        # Find all test users
        test_users = User.objects(uid__startswith="TEST_").all()
        
        print(f"🧹 Found {test_users.count()} test users to clean up")
        
        for user in test_users:
            print(f"   Deleting user: {user.uid}")
            user.delete()
        
        print("✅ Test users cleaned up")
        return True
    except Exception as e:
        print(f"❌ Error cleaning up test users: {str(e)}")
        return False

def cleanup_global_data():
    """Clean up Global program data"""
    try:
        # Clean up Global placements
        global_placements = TreePlacement.objects(program='global').all()
        print(f"🧹 Found {global_placements.count()} Global placements to clean up")
        
        for placement in global_placements:
            placement.delete()
        
        # Clean up Global team members
        global_members = GlobalTeamMember.objects().all()
        print(f"🧹 Found {global_members.count()} Global team members to clean up")
        
        for member in global_members:
            member.delete()
        
        # Clean up Global phase progressions
        phase_progressions = GlobalPhaseProgression.objects().all()
        print(f"🧹 Found {phase_progressions.count()} Global phase progressions to clean up")
        
        for progression in phase_progressions:
            progression.delete()
        
        # Clean up Global tree structures
        tree_structures = GlobalTreeStructure.objects().all()
        print(f"🧹 Found {tree_structures.count()} Global tree structures to clean up")
        
        for structure in tree_structures:
            structure.delete()
        
        # Clean up Global phase seats
        phase_seats = GlobalPhaseSeat.objects().all()
        print(f"🧹 Found {phase_seats.count()} Global phase seats to clean up")
        
        for seat in phase_seats:
            seat.delete()
        
        print("✅ Global program data cleaned up")
        return True
    except Exception as e:
        print(f"❌ Error cleaning up Global data: {str(e)}")
        return False

def cleanup_income_data():
    """Clean up income data"""
    try:
        # Clean up income events
        income_events = IncomeEvent.objects(program='global').all()
        print(f"🧹 Found {income_events.count()} Global income events to clean up")
        
        for event in income_events:
            event.delete()
        
        # Clean up wallet ledgers
        wallet_ledgers = WalletLedger.objects(reason__contains='global').all()
        print(f"🧹 Found {wallet_ledgers.count()} Global wallet ledgers to clean up")
        
        for ledger in wallet_ledgers:
            ledger.delete()
        
        # Clean up reserve ledgers
        reserve_ledgers = ReserveLedger.objects(program='global').all()
        print(f"🧹 Found {reserve_ledgers.count()} Global reserve ledgers to clean up")
        
        for ledger in reserve_ledgers:
            ledger.delete()
        
        print("✅ Income data cleaned up")
        return True
    except Exception as e:
        print(f"❌ Error cleaning up income data: {str(e)}")
        return False

def cleanup_all_test_data():
    """Clean up all test data"""
    print("🧹 Starting Global Program Test Data Cleanup...")
    print("=" * 60)
    
    # Clean up in order
    cleanup_test_users()
    cleanup_global_data()
    cleanup_income_data()
    
    print("\n🎉 All test data cleaned up successfully!")
    print("=" * 60)

if __name__ == "__main__":
    cleanup_all_test_data()
