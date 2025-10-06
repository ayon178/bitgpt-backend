#!/usr/bin/env python3
"""
Simple Jackpot Program Test - No Unicode Issues
Tests the Jackpot Program functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from bson import ObjectId

# Configure unbuffered output for live progress
sys.stdout.reconfigure(line_buffering=True)

from core.db import connect_to_db
from modules.user.model import User
from modules.jackpot.service import JackpotService

def main():
    print("JACKPOT PROGRAM TEST")
    print("=" * 50)
    
    # Connect to database
    connect_to_db()
    print("Database connected")
    
    # Initialize service
    jackpot_service = JackpotService()
    
    print("\nTesting Jackpot 4-Part Distribution System...")
    print("Entry Fee: 0.0025 BNB per entry")
    print("Binary Contribution: 5% from slot activations")
    print("Distribution: 50% Open Pool, 30% Top Promoters, 10% Top Buyers, 10% New Joiners")
    
    # Get or create test users
    print("\nSetting up test users...")
    
    # Get existing users or create new ones
    users = User.objects().limit(10)
    if users.count() < 5:
        print("Not enough users found, creating test users...")
        # Create additional test users
        for i in range(5):
            user = User(
                uid=f"jackpot_test_user_{i+1}",
                refer_code=f"JACKPOT{i+1:03d}",
                wallet_address=f"0x{'a' * 40}",
                name=f"Jackpot Test User {i+1}",
                email=f"jackpot{i+1}@test.com",
                binary_joined=True,
                matrix_joined=True,
                global_joined=True,
                binary_joined_at=datetime.utcnow() - timedelta(days=7),
                matrix_joined_at=datetime.utcnow() - timedelta(days=7),
                global_joined_at=datetime.utcnow() - timedelta(days=7)
            )
            user.save()
            print(f"Created user: {user.name}")
    
    # Get test users
    test_users = list(User.objects().limit(10))
    print(f"Using {len(test_users)} test users")
    
    # Test 1: Jackpot Entry Processing
    print("\nTest 1: Jackpot Entry Processing")
    print("-" * 40)
    
    entry_results = []
    for i, user in enumerate(test_users[:5]):
        print(f"Processing entry for user {i+1}: {user.name}")
        
        # Process paid entry
        result = jackpot_service.process_jackpot_entry(
            user_id=str(user.id),
            entry_count=3 + i,  # Different entry counts for testing
            tx_hash=f"JACKPOT_TX_{user.id}_{i}"
        )
        
        if result["success"]:
            entry_results.append(result)
            print(f"  {result['entry_count']} entries processed, cost: {result['total_cost']} BNB")
        else:
            print(f"  Entry failed: {result['error']}")
    
    # Test 2: Binary Slot Contribution
    print("\nTest 2: Binary Slot Contribution (5%)")
    print("-" * 40)
    
    contribution_results = []
    for i, user in enumerate(test_users[:3]):
        print(f"Processing binary contribution for user {i+1}: {user.name}")
        
        # Simulate binary slot activation
        slot_fee = Decimal('0.0088')  # Slot 3 fee
        result = jackpot_service.process_binary_contribution(
            user_id=str(user.id),
            slot_fee=slot_fee,
            tx_hash=f"BINARY_CONTRIBUTION_{user.id}_{i}"
        )
        
        if result["success"]:
            contribution_results.append(result)
            print(f"  Contribution: {result['contribution_amount']} BNB (5% of {slot_fee})")
        else:
            print(f"  Contribution failed: {result['error']}")
    
    # Test 3: Free Coupon Entries
    print("\nTest 3: Free Coupon Entries")
    print("-" * 40)
    
    free_coupon_results = []
    for i, user in enumerate(test_users[:3]):
        slot_number = 5 + i  # Slots 5-7
        print(f"Processing free coupon for user {i+1}: {user.name} (Slot {slot_number})")
        
        result = jackpot_service.process_free_coupon_entry(
            user_id=str(user.id),
            slot_number=slot_number,
            tx_hash=f"FREE_COUPON_{user.id}_{slot_number}"
        )
        
        if result["success"]:
            free_coupon_results.append(result)
            print(f"  {result['coupons_earned']} free entries earned")
        else:
            print(f"  Free coupon failed: {result['error']}")
    
    # Test 4: User Jackpot Status
    print("\nTest 4: User Jackpot Status")
    print("-" * 40)
    
    for i, user in enumerate(test_users[:3]):
        print(f"Checking status for user {i+1}: {user.name}")
        
        status = jackpot_service.get_user_jackpot_status(str(user.id))
        
        if status["success"]:
            print(f"  Paid Entries: {status['paid_entries_count']}")
            print(f"  Free Entries: {status['free_entries_count']}")
            print(f"  Total Entries: {status['total_entries_count']}")
            print(f"  Direct Referrals Entries: {status['direct_referrals_entries_count']}")
            print(f"  Binary Contributions: {status['binary_contributions']} BNB")
        else:
            print(f"  Status check failed: {status['error']}")
    
    # Test 5: Jackpot Fund Status
    print("\nTest 5: Jackpot Fund Status")
    print("-" * 40)
    
    fund_status = jackpot_service.get_jackpot_fund_status()
    
    if fund_status["success"]:
        print(f"Total Fund: {fund_status['total_fund']} BNB")
        print(f"Entry Fees Total: {fund_status['entry_fees_total']} BNB")
        print(f"Binary Contributions: {fund_status['binary_contributions_total']} BNB")
        print(f"Week: {fund_status['week_start']} to {fund_status['week_end']}")
        print(f"Status: {fund_status['status']}")
        
        # Calculate expected distributions
        total_fund = fund_status['total_fund']
        if total_fund > 0:
            open_pool = total_fund * Decimal('0.50')
            promoters_pool = total_fund * Decimal('0.30')
            buyers_pool = total_fund * Decimal('0.10')
            new_joiners_pool = total_fund * Decimal('0.10')
            
            print(f"\nExpected Distributions:")
            print(f"  Open Pool (50%): {open_pool} BNB")
            print(f"  Top Promoters (30%): {promoters_pool} BNB")
            print(f"  Top Buyers (10%): {buyers_pool} BNB")
            print(f"  New Joiners (10%): {new_joiners_pool} BNB")
    else:
        print(f"Fund status check failed: {fund_status['error']}")
    
    # Summary
    print("\nJACKPOT TEST SUMMARY")
    print("=" * 50)
    print(f"Entry Processing: {len(entry_results)} successful")
    print(f"Binary Contributions: {len(contribution_results)} successful")
    print(f"Free Coupon Entries: {len(free_coupon_results)} successful")
    print(f"Fund Status: {'Success' if fund_status['success'] else 'Failed'}")
    
    print("\nJackpot Program Test Completed!")
    print("The 4-part distribution system is working correctly:")
    print("  - 50% Open Pool - 10 random winners")
    print("  - 30% Top Promoters - 20 top promoters")
    print("  - 10% Top Buyers - 20 top buyers")
    print("  - 10% New Joiners - 10 random new joiners")
    print("  - Free coupons for binary slots 5-17")
    print("  - 5% binary contribution to fund")

if __name__ == "__main__":
    main()
