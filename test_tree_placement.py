#!/usr/bin/env python3
"""
Test script for Tree Placement Logic
This script tests the binary tree placement logic with different scenarios
"""

import asyncio
import sys
import os
from bson import ObjectId
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

# Import database connection
from core.db import connect_to_db
from modules.tree.model import TreePlacement
from modules.tree.service import TreeService
from modules.user.model import User


async def create_test_users():
    """Create test users for testing"""
    users = []
    
    # Create a root user first for referrals
    root_user = User(
        uid="test_root_user",
        refer_code="ROOT001",
        refered_by=ObjectId(),  # Self-referral for root
        wallet_address="0x1234567890abcdef1234567890abcdef12345678",
        name="Root Test User",
        email="root@test.com",
        role="user",
        status="active"
    )
    root_user.save()
    users.append(root_user)
    print(f"Created root user: {root_user.uid} (ID: {root_user.id})")
    
    # Create test users
    for i in range(1, 11):
        user = User(
            uid=f"test_user_{i}",
            refer_code=f"REF{i:03d}",
            refered_by=root_user.id,  # All users referred by root
            wallet_address=f"0x{i:040x}",
            name=f"Test User {i}",
            email=f"user{i}@test.com",
            role="user",
            status="active"
        )
        user.save()
        users.append(user)
        print(f"Created user: {user.uid} (ID: {user.id})")
    
    return users


async def test_scenario_1_direct_referral():
    """Test Scenario 1: Direct referral placement"""
    print("\n" + "="*50)
    print("TESTING SCENARIO 1: DIRECT REFERRAL")
    print("="*50)
    
    # Create test users
    users = await create_test_users()
    
    # Test 1: First user joins (should be root)
    result1 = await TreeService.create_tree_placement(
        user_id=str(users[0].id),
        referrer_id=str(users[0].id),  # Self-referral for root
        program='binary',
        slot_no=1
    )
    print(f"Test 1 - Root user: {result1.message}")
    
    # Test 2: Second user joins under first user (left position)
    result2 = await TreeService.create_tree_placement(
        user_id=str(users[1].id),
        referrer_id=str(users[0].id),
        program='binary',
        slot_no=1
    )
    print(f"Test 2 - Left position: {result2.message}")
    
    # Test 3: Third user joins under first user (right position)
    result3 = await TreeService.create_tree_placement(
        user_id=str(users[2].id),
        referrer_id=str(users[0].id),
        program='binary',
        slot_no=1
    )
    print(f"Test 3 - Right position: {result3.message}")
    
    # Test 4: Fourth user tries to join under first user (should fail - both positions filled)
    result4 = await TreeService.create_tree_placement(
        user_id=str(users[3].id),
        referrer_id=str(users[0].id),
        program='binary',
        slot_no=1
    )
    print(f"Test 4 - Both positions filled: {result4.message}")
    
    # Display tree structure
    print("\nTree Structure after Scenario 1:")
    await display_tree_structure('binary', 1)


async def test_scenario_2_indirect_referral():
    """Test Scenario 2: Indirect referral placement (spillover)"""
    print("\n" + "="*50)
    print("TESTING SCENARIO 2: INDIRECT REFERRAL (SPILLOVER)")
    print("="*50)
    
    # Create new users for this test (different UIDs to avoid conflicts)
    users = []
    
    # Create a root user first for referrals
    root_user = User(
        uid="test_root_user_2",
        refer_code="ROOT002",
        refered_by=ObjectId(),  # Self-referral for root
        wallet_address="0x2234567890abcdef1234567890abcdef12345678",
        name="Root Test User 2",
        email="root2@test.com",
        role="user",
        status="active"
    )
    root_user.save()
    users.append(root_user)
    print(f"Created root user: {root_user.uid} (ID: {root_user.id})")
    
    # Create test users
    for i in range(1, 6):
        user = User(
            uid=f"test_user_2_{i}",
            refer_code=f"REF2{i:03d}",
            refered_by=root_user.id,  # All users referred by root
            wallet_address=f"0x2{i:040x}",
            name=f"Test User 2_{i}",
            email=f"user2_{i}@test.com",
            role="user",
            status="active"
        )
        user.save()
        users.append(user)
        print(f"Created user: {user.uid} (ID: {user.id})")
    
    # Setup: Create a tree with some structure
    # Root user
    await TreeService.create_tree_placement(
        user_id=str(users[0].id),
        referrer_id=str(users[0].id),
        program='binary',
        slot_no=2
    )
    
    # Left child
    await TreeService.create_tree_placement(
        user_id=str(users[1].id),
        referrer_id=str(users[0].id),
        program='binary',
        slot_no=2
    )
    
    # Right child
    await TreeService.create_tree_placement(
        user_id=str(users[2].id),
        referrer_id=str(users[0].id),
        program='binary',
        slot_no=2
    )
    
    # Now test spillover: User joins but referrer has no space
    result = await TreeService.create_tree_placement(
        user_id=str(users[3].id),
        referrer_id=str(users[0].id),  # Referrer has no space
        program='binary',
        slot_no=2
    )
    print(f"Spillover test: {result.message}")
    
    # Display tree structure
    print("\nTree Structure after Scenario 2:")
    await display_tree_structure('binary', 2)


async def display_tree_structure(program: str, slot_no: int):
    """Display the current tree structure"""
    placements = TreePlacement.objects(
        program=program,
        slot_no=slot_no,
        is_active=True
    ).order_by('level', 'position')
    
    print(f"\nProgram: {program}, Slot: {slot_no}")
    print("-" * 40)
    
    for placement in placements:
        print(f"Level {placement.level} | Position: {placement.position} | User: {placement.user_id} | Parent: {placement.parent_id}")


async def cleanup_test_data():
    """Clean up test data"""
    print("\n" + "="*50)
    print("CLEANING UP TEST DATA")
    print("="*50)
    
    # Delete test placements
    TreePlacement.objects(program='binary', slot_no__in=[1, 2]).delete()
    print("Deleted test tree placements")
    
    # Delete test users (including both scenarios)
    User.objects(uid__startswith="test_user_").delete()
    User.objects(uid__startswith="test_root_user").delete()
    print("Deleted test users")


async def main():
    """Main test function"""
    print("Starting Tree Placement Logic Tests")
    print("="*50)
    
    # Connect to database
    connect_to_db()
    
    try:
        # Test Scenario 1
        await test_scenario_1_direct_referral()
        
        # Test Scenario 2
        await test_scenario_2_indirect_referral()
        
        # Cleanup
        await cleanup_test_data()
        
        print("\n" + "="*50)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*50)
        
    except Exception as e:
        print(f"Error during testing: {e}")
        await cleanup_test_data()


if __name__ == "__main__":
    asyncio.run(main())
