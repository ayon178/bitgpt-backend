#!/usr/bin/env python3
"""
Test script for Tree Service
This script demonstrates how the tree service works with sample data
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.tree.service import TreeService
from modules.tree.model import TreePlacement
from modules.user.model import User
from bson import ObjectId
from datetime import datetime


async def create_sample_data():
    """Create sample tree placement data for testing"""
    print("Creating sample tree data...")
    
    # Create a sample user if it doesn't exist
    user_id = ObjectId()
    user = User(
        id=user_id,
        uid="test_user_123",
        name="Test User",
        email="test@example.com",
        wallet_address="0x1234567890abcdef",
        role="user",
        status="active"
    )
    user.save()
    
    # Create sample tree placements
    placements = [
        # Binary tree structure - Slot 1
        TreePlacement(
            user_id=user_id,
            program='binary',
            parent_id=user_id,
            position='center',
            level=1,
            slot_no=1,
            is_active=True,
            created_at=datetime.utcnow()
        ),
        TreePlacement(
            user_id=user_id,
            program='binary',
            parent_id=user_id,
            position='left',
            level=2,
            slot_no=1,
            is_active=True,
            created_at=datetime.utcnow()
        ),
        TreePlacement(
            user_id=user_id,
            program='binary',
            parent_id=user_id,
            position='right',
            level=2,
            slot_no=1,
            is_active=True,
            created_at=datetime.utcnow()
        ),
        # Matrix tree structure - Slot 2
        TreePlacement(
            user_id=user_id,
            program='matrix',
            parent_id=user_id,
            position='center',
            level=1,
            slot_no=2,
            is_active=True,
            created_at=datetime.utcnow()
        ),
        TreePlacement(
            user_id=user_id,
            program='matrix',
            parent_id=user_id,
            position='left',
            level=2,
            slot_no=2,
            is_active=True,
            created_at=datetime.utcnow()
        ),
        TreePlacement(
            user_id=user_id,
            program='matrix',
            parent_id=user_id,
            position='right',
            level=2,
            slot_no=2,
            is_active=True,
            created_at=datetime.utcnow()
        ),
    ]
    
    for placement in placements:
        placement.save()
    
    print(f"Created sample data for user: {user_id}")
    return str(user_id)


async def test_tree_service():
    """Test the tree service functionality"""
    print("Testing Tree Service...")
    
    # Create sample data
    user_id = await create_sample_data()
    
    try:
        # Test binary tree data
        print("\n1. Testing Binary Tree Data:")
        binary_result = await TreeService.get_tree_data(user_id, 'binary')
        print(f"Success: {binary_result.success}")
        print(f"Message: {binary_result.message}")
        print(f"Data: {binary_result.data}")
        
        # Test matrix tree data
        print("\n2. Testing Matrix Tree Data:")
        matrix_result = await TreeService.get_tree_data(user_id, 'matrix')
        print(f"Success: {matrix_result.success}")
        print(f"Message: {matrix_result.message}")
        print(f"Data: {matrix_result.data}")
        
        # Test all tree data
        print("\n3. Testing All Tree Data:")
        all_result = await TreeService.get_all_trees_by_user(user_id)
        print(f"Success: {all_result.success}")
        print(f"Message: {all_result.message}")
        print(f"Data: {all_result.data}")
        
        # Test with non-existent user
        print("\n4. Testing Non-existent User:")
        non_existent_result = await TreeService.get_tree_data("507f1f77bcf86cd799439011", 'binary')
        print(f"Success: {non_existent_result.success}")
        print(f"Message: {non_existent_result.message}")
        
    except Exception as e:
        print(f"Error during testing: {e}")
    
    finally:
        # Clean up sample data
        print("\nCleaning up sample data...")
        User.objects(id=ObjectId(user_id)).delete()
        TreePlacement.objects(user_id=ObjectId(user_id)).delete()
        print("Cleanup completed.")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_tree_service())
