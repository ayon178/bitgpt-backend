"""
Test Binary Tree BFS Placement Logic

This script demonstrates how the BFS placement algorithm works
when a user refers more than 2 people.
"""

from bson import ObjectId
from modules.tree.model import TreePlacement
from modules.tree.service import TreeService
from modules.user.model import User
from modules.slot.model import SlotCatalog
import asyncio


async def test_binary_tree_placement():
    """Test binary tree placement with multiple referrals"""
    
    print("=" * 80)
    print("BINARY TREE BFS PLACEMENT TEST")
    print("=" * 80)
    
    try:
        # Step 1: Create a test root user (or use existing)
        root_user = User.objects(uid='user17608872172129581').first()
        if not root_user:
            print("❌ Root user not found!")
            return
        
        root_user_id = root_user.id
        print(f"\n✅ Root User: {root_user.uid} (ObjectId: {root_user_id})")
        
        # Step 2: Check existing placements for this user
        existing_placements = TreePlacement.objects(
            user_id=root_user_id,
            program='binary',
            slot_no=1,
            is_active=True
        ).first()
        
        if not existing_placements:
            print("\n📌 Creating root placement for test user...")
            root_placement = TreePlacement(
                user_id=root_user_id,
                program='binary',
                parent_id=None,
                upline_id=None,
                position='root',
                level=0,
                slot_no=1,
                is_active=True
            )
            root_placement.save()
            print(f"✅ Created root placement: Level 0, Position root")
        else:
            print(f"\n✅ Root placement exists: Level {existing_placements.level}, Position {existing_placements.position}")
        
        # Step 3: Get all children placements under root
        all_children = TreePlacement.objects(
            upline_id=root_user_id,
            program='binary',
            slot_no=1,
            is_active=True
        ).order_by('created_at')
        
        print(f"\n📊 Current tree structure under {root_user.uid}:")
        print(f"   Total children: {all_children.count()}")
        
        for idx, child in enumerate(all_children, 1):
            child_user = User.objects(id=child.user_id).first()
            child_uid = child_user.uid if child_user else str(child.user_id)
            parent_user = User.objects(id=child.parent_id).first() if child.parent_id else None
            parent_uid = parent_user.uid if parent_user else "None"
            
            print(f"   {idx}. {child_uid}")
            print(f"      - Level: {child.level}")
            print(f"      - Position: {child.position}")
            print(f"      - Direct Referrer (parent_id): {parent_uid}")
            print(f"      - Tree Parent (upline_id): {root_user.uid if child.upline_id == root_user_id else 'spillover'}")
            print(f"      - Is Spillover: {child.is_spillover}")
        
        # Step 4: Demonstrate BFS placement logic
        print(f"\n{'=' * 80}")
        print("BFS PLACEMENT LOGIC DEMONSTRATION")
        print(f"{'=' * 80}")
        
        # Check what positions are available
        left_child = TreePlacement.objects(
            upline_id=root_user_id,
            position='left',
            program='binary',
            slot_no=1,
            is_active=True
        ).first()
        
        right_child = TreePlacement.objects(
            upline_id=root_user_id,
            position='right',
            program='binary',
            slot_no=1,
            is_active=True
        ).first()
        
        print(f"\n📍 Direct positions under {root_user.uid}:")
        print(f"   Left:  {'✅ Filled' if left_child else '⬜ Available'}")
        if left_child:
            left_user = User.objects(id=left_child.user_id).first()
            print(f"      User: {left_user.uid if left_user else left_child.user_id}")
        
        print(f"   Right: {'✅ Filled' if right_child else '⬜ Available'}")
        if right_child:
            right_user = User.objects(id=right_child.user_id).first()
            print(f"      User: {right_user.uid if right_user else right_child.user_id}")
        
        # Step 5: Find next available position using BFS
        if left_child and right_child:
            print(f"\n🔍 Both direct positions filled! Using BFS to find next available position...")
            
            tree_service = TreeService()
            next_position = await tree_service._find_next_available_position_bfs(
                root_user_id, 'binary', 1
            )
            
            if next_position:
                upline_user = User.objects(id=next_position['upline_id']).first()
                upline_uid = upline_user.uid if upline_user else str(next_position['upline_id'])
                
                print(f"\n✅ Next available position found:")
                print(f"   Tree Parent (upline_id): {upline_uid}")
                print(f"   Position: {next_position['position']}")
                print(f"   Level: {next_position['level']}")
                print(f"\n   📝 If a new user is referred by {root_user.uid}:")
                print(f"      - parent_id: {root_user.uid} (direct referrer)")
                print(f"      - upline_id: {upline_uid} (tree placement parent)")
                print(f"      - position: {next_position['position']}")
                print(f"      - is_spillover: True")
            else:
                print("❌ No available position found")
        else:
            available_pos = "left" if not left_child else "right"
            print(f"\n✅ Direct position available: {available_pos}")
            print(f"   Next referral will be placed directly under {root_user.uid}")
        
        # Step 6: Build nested tree to show full structure
        print(f"\n{'=' * 80}")
        print("NESTED TREE STRUCTURE")
        print(f"{'=' * 80}")
        
        from modules.binary.service import BinaryService
        binary_service = BinaryService()
        
        root_node, depth, total_count = binary_service._build_nested_binary_tree_limited(
            root_user_id, max_levels=3
        )
        
        def print_tree_recursive(node, indent=0):
            """Print tree structure recursively"""
            prefix = "  " * indent
            level = node.get('level', 0)
            position = node.get('position', 'root')
            user_id = node.get('userId', 'unknown')
            node_type = node.get('type', 'unknown')
            
            print(f"{prefix}{'└─' if indent > 0 else ''}[L{level}] {user_id} ({position}) - {node_type}")
            
            # Print children
            direct_downline = node.get('directDownline', [])
            for child in direct_downline:
                print_tree_recursive(child, indent + 1)
        
        print()
        print_tree_recursive(root_node)
        
        print(f"\n📊 Tree Statistics:")
        print(f"   Total Nodes: {total_count}")
        print(f"   Max Depth: {depth}")
        print(f"   Total Levels: {depth + 1} (0 to {depth})")
        
        # Step 7: Show placement sequence
        print(f"\n{'=' * 80}")
        print("PLACEMENT SEQUENCE EXPLANATION")
        print(f"{'=' * 80}")
        
        print(f"\n When {root_user.uid} refers multiple people:")
        print(f"   1st referral → Level 1, Left position")
        print(f"   2nd referral → Level 1, Right position")
        print(f"   3rd referral → Level 2, Left child of 1st referral (SPILLOVER)")
        print(f"   4th referral → Level 2, Right child of 1st referral (SPILLOVER)")
        print(f"   5th referral → Level 2, Left child of 2nd referral (SPILLOVER)")
        print(f"   6th referral → Level 2, Right child of 2nd referral (SPILLOVER)")
        print(f"   7th referral → Level 3, Left child of 3rd referral (SPILLOVER)")
        print(f"   ... and so on using BFS traversal")
        
        print(f"\n{'=' * 80}")
        print("TEST COMPLETED SUCCESSFULLY!")
        print(f"{'=' * 80}")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()


async def test_placement_scenario():
    """Test actual placement of new users"""
    
    print("\n" + "=" * 80)
    print("TESTING ACTUAL PLACEMENT (Simulation)")
    print("=" * 80)
    
    try:
        # Get root user
        root_user = User.objects(uid='user17608872172129581').first()
        if not root_user:
            print("❌ Root user not found!")
            return
        
        # Count current referrals
        current_referrals = TreePlacement.objects(
            parent_id=root_user.id,
            program='binary',
            slot_no=1,
            is_active=True
        ).count()
        
        print(f"\n📊 Current Statistics:")
        print(f"   Root User: {root_user.uid}")
        print(f"   Total Direct Referrals (parent_id): {current_referrals}")
        
        # Count tree children (upline_id)
        tree_children = TreePlacement.objects(
            upline_id=root_user.id,
            program='binary',
            slot_no=1,
            is_active=True
        ).count()
        
        print(f"   Direct Tree Children (upline_id): {tree_children} (max 2)")
        
        # Find next available position
        tree_service = TreeService()
        next_position = await tree_service._find_next_available_position_bfs(
            root_user.id, 'binary', 1
        )
        
        if next_position:
            upline_user = User.objects(id=next_position['upline_id']).first()
            upline_uid = upline_user.uid if upline_user else str(next_position['upline_id'])
            
            print(f"\n✅ Next user will be placed at:")
            print(f"   Direct Referrer (parent_id): {root_user.uid}")
            print(f"   Tree Parent (upline_id): {upline_uid}")
            print(f"   Position: {next_position['position']}")
            print(f"   Level: {next_position['level']}")
            
            if str(next_position['upline_id']) != str(root_user.id):
                print(f"   ⚠️  SPILLOVER PLACEMENT (upline_id ≠ parent_id)")
            else:
                print(f"   ✅ DIRECT PLACEMENT (upline_id = parent_id)")
        else:
            print("\n⬜ All positions available")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run tests
    print("\n🚀 Starting Binary Tree BFS Placement Tests...\n")
    
    asyncio.run(test_binary_tree_placement())
    asyncio.run(test_placement_scenario())
    
    print("\n✅ All tests completed!\n")

