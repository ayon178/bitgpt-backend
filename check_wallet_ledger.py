#!/usr/bin/env python3
"""
Check WalletLedger for recent entries for specific users
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mongoengine import connect
from modules.wallet.model import WalletLedger
from modules.user.model import User
from bson import ObjectId

# Connect to database
connect(
    db='bitgpt',
    host='localhost',
    port=27017
)

def main():
    print("\n" + "="*80)
    print("CHECKING WALLET LEDGER ENTRIES")
    print("="*80)
    
    # User IDs from the test
    user1_id = "68ee3b7d5e71eed4893dfd98"  # First new user (user17604432604716499)
    user2_id = "68ee3be85e71eed4893dfd9d"  # Second new user (user17604433677938277)
    parent_id = "68ee06323d727d9e0b204c86"  # RC1760429616945918 (Swadhin)
    
    print(f"\n1. Parent User (RC1760429616945918): {parent_id}")
    print(f"2. First New User: {user1_id}")
    print(f"3. Second New User: {user2_id}")
    
    # Check WalletLedger for parent user
    print("\n" + "="*80)
    print("PARENT USER WALLET LEDGER (Recent 10 entries):")
    print("="*80)
    
    try:
        parent_oid = ObjectId(parent_id)
        entries = WalletLedger.objects(user_id=parent_oid).order_by('-created_at').limit(10)
        
        if entries:
            for i, entry in enumerate(entries, 1):
                print(f"\n{i}. Type: {entry.type}")
                print(f"   Amount: {entry.amount} {entry.currency}")
                print(f"   Reason: {entry.reason}")
                print(f"   TX Hash: {entry.tx_hash}")
                print(f"   Created: {entry.created_at}")
        else:
            print("\n❌ No entries found for parent user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    # Check WalletLedger for first new user
    print("\n" + "="*80)
    print("FIRST NEW USER WALLET LEDGER (Recent 10 entries):")
    print("="*80)
    
    try:
        user1_oid = ObjectId(user1_id)
        entries = WalletLedger.objects(user_id=user1_oid).order_by('-created_at').limit(10)
        
        if entries:
            for i, entry in enumerate(entries, 1):
                print(f"\n{i}. Type: {entry.type}")
                print(f"   Amount: {entry.amount} {entry.currency}")
                print(f"   Reason: {entry.reason}")
                print(f"   TX Hash: {entry.tx_hash}")
                print(f"   Created: {entry.created_at}")
        else:
            print("\n❌ No entries found for first new user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    # Check all recent credits with 'partner_incentive' reason
    print("\n" + "="*80)
    print("ALL RECENT PARTNER INCENTIVE CREDITS:")
    print("="*80)
    
    try:
        incentive_entries = WalletLedger.objects(
            type='credit',
            reason__icontains='partner_incentive'
        ).order_by('-created_at').limit(10)
        
        if incentive_entries:
            for i, entry in enumerate(incentive_entries, 1):
                print(f"\n{i}. User ID: {entry.user_id}")
                print(f"   Amount: {entry.amount} {entry.currency}")
                print(f"   Reason: {entry.reason}")
                print(f"   TX Hash: {entry.tx_hash}")
                print(f"   Created: {entry.created_at}")
        else:
            print("\n❌ No partner incentive entries found")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    # Check IncomeEvent for comparison
    print("\n" + "="*80)
    print("CHECKING INCOME EVENTS (for comparison):")
    print("="*80)
    
    try:
        from modules.income.model import IncomeEvent
        
        # Check for parent user
        parent_income = IncomeEvent.objects(
            user_id=parent_oid,
            income_type='partner_incentive'
        ).order_by('-created_at').limit(5)
        
        print(f"\nParent user IncomeEvents (partner_incentive): {parent_income.count()}")
        for i, event in enumerate(parent_income, 1):
            print(f"\n{i}. Amount: {event.amount}")
            print(f"   Program: {event.program}")
            print(f"   Source User: {event.source_user_id}")
            print(f"   Status: {event.status}")
            print(f"   Created: {event.created_at}")
            
    except Exception as e:
        print(f"\n❌ Error checking IncomeEvent: {e}")

if __name__ == "__main__":
    main()

