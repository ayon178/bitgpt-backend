#!/usr/bin/env python3
"""
Simple test for Tree Placement Logic
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.modules.tree.service import TreeService
from backend.utils.response import ResponseModel


async def test_placement_logic():
    """Test the placement logic with mock data"""
    print("Testing Tree Placement Logic")
    print("="*50)
    
    # Mock user IDs
    user_id = "507f1f77bcf86cd799439011"
    referrer_id = "507f1f77bcf86cd799439012"
    
    try:
        # Test the service method
        result = await TreeService.create_tree_placement(
            user_id=user_id,
            referrer_id=referrer_id,
            program='binary',
            slot_no=1
        )
        
        print(f"Result: {result}")
        print(f"Success: {result.success}")
        print(f"Message: {result.message}")
        
        if result.data:
            print(f"Data: {result.data}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_placement_logic())
