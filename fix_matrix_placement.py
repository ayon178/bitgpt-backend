"""
Migration script to fix existing Matrix tree placements.
Reorganizes placements using the new level-wise BFS logic instead of the old DFS/BFS hybrid.

Usage:
    python fix_matrix_placement.py [user_id] [slot_no]
    python fix_matrix_placement.py 68fde1b4902f36ce233109ef 1
"""

import sys
from bson import ObjectId
from datetime import datetime
from mongoengine import connect
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def connect_db():
    """Connect to MongoDB"""
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/bitgpt")
    connect(host=mongodb_uri)
    print(f"✅ Connected to MongoDB")

def fix_matrix_placement(user_id: str, slot_no: int):
    """
    Fix matrix placements for a user using new level-wise BFS logic.
    
    Steps:
    1. Get all placements for this user/slot (sorted by creation time)
    2. Delete old placements (except root)
    3. Recreate placements using new level-wise BFS logic
    """
    from modules.tree.model import TreePlacement
    from modules.user.model import User
    
    print(f"\n🔄 Fixing Matrix placements for user {user_id}, slot {slot_no}")
    
    try:
        user_oid = ObjectId(user_id)
    except:
        print(f"❌ Invalid user_id: {user_id}")
        return False
    
    # Get root user's placement
    root_placement = TreePlacement.objects(
        user_id=user_oid,
        program='matrix',
        slot_no=slot_no,
        is_active=True,
        level=0
    ).first()
    
    if not root_placement:
        print(f"❌ Root placement not found")
        return False
    
    # Get all children placements (sorted by creation time)
    children_placements = TreePlacement.objects(
        program='matrix',
        slot_no=slot_no,
        is_active=True,
        upline_id=user_oid  # All children under this root
    ).order_by('created_at').all()
    
    print(f"📊 Found {len(children_placements)} children placements")
    
    if len(children_placements) == 0:
        print("✅ No children to reorganize")
        return True
    
    # Deactivate old placements (don't delete, just deactivate)
    for placement in children_placements:
        placement.is_active = False
        placement.save()
    
    print(f"✅ Deactivated {len(children_placements)} old placements")
    
    # Now recreate placements using new level-wise BFS logic
    positions = ['left', 'middle', 'right']
    current_level_nodes = []
    level_0_nodes = []  # Store level 0 nodes separately
    
    # First, place level 1 children (direct children of root)
    for child_placement in children_placements:
        if child_placement.level == 1:
            level_0_nodes.append(child_placement)
    
    # Place level 1 children using level-wise logic
    for pos_idx, pos in enumerate(positions):
        if pos_idx < len(level_0_nodes):
            old_placement = level_0_nodes[pos_idx]
            
            # Create new placement with correct position
            new_placement = TreePlacement(
                user_id=old_placement.user_id,
                program='matrix',
                parent_id=user_oid,  # Root as parent
                upline_id=user_oid,   # Root as upline (direct child)
                position=pos,
                level=1,
                slot_no=slot_no,
                is_active=True,
                is_spillover=False,
                created_at=old_placement.created_at  # Keep original time
            )
            new_placement.save()
            current_level_nodes.append((old_placement.user_id, 1))
            print(f"✅ Recreated {old_placement.user_id} at level 1, position {pos}")
    
    # Now place level 2+ children using level-wise BFS
    level_1_nodes = [lp for lp in children_placements if lp.level == 2]
    level_2_plus = [lp for lp in children_placements if lp.level > 2]
    
    # Place level 2 children
    for pos_idx in range(len(positions)):
        pos = positions[pos_idx]
        
        for child_oid, child_level in current_level_nodes:
            if pos_idx < len(level_1_nodes):
                old_placement = level_1_nodes[pos_idx]
                child_user_id = old_placement.user_id
                
                # Check if this position is already taken
                existing = TreePlacement.objects(
                    program='matrix',
                    upline_id=child_oid,
                    position=pos,
                    slot_no=slot_no,
                    is_active=True
                ).first()
                
                if not existing:
                    # Create new placement
                    new_placement = TreePlacement(
                        user_id=child_user_id,
                        program='matrix',
                        parent_id=user_oid,  # Root as original parent
                        upline_id=child_oid,   # Actual tree parent
                        position=pos,
                        level=child_level + 1,
                        slot_no=slot_no,
                        is_active=True,
                        is_spillover=True,
                        spillover_from=user_oid,
                        created_at=old_placement.created_at
                    )
                    new_placement.save()
                    print(f"✅ Recreated {child_user_id} at level {child_level + 1}, position {pos} under {child_oid}")
                    break
    
    # Handle deeper levels if any
    if level_2_plus:
        print(f"⚠️  Found {len(level_2_plus)} placements at level 3+ - may need manual attention")
    
    print(f"\n✅ Matrix placement reorganization complete!")
    return True


if __name__ == "__main__":
    # Connect to database
    connect_db()
    
    # Parse arguments
    if len(sys.argv) < 3:
        print("Usage: python fix_matrix_placement.py <user_id> <slot_no>")
        print("Example: python fix_matrix_placement.py 68fde1b4902f36ce233109ef 1")
        sys.exit(1)
    
    user_id = sys.argv[1]
    slot_no = int(sys.argv[2])
    
    # Run migration
    success = fix_matrix_placement(user_id, slot_no)
    
    if success:
        print("\n✅ Migration completed successfully")
    else:
        print("\n❌ Migration failed")
        sys.exit(1)

