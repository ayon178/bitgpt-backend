from typing import Dict, Any, List, Set
from bson import ObjectId
from modules.user.model import User
from modules.matrix.model import MatrixTree, MatrixRecycleInstance, MatrixActivation
from modules.slot.model import SlotCatalog
from modules.tree.model import TreePlacement
import random


class DreamMatrixService:
    """Dream Matrix Business Logic Service"""

    def get_dream_matrix_earnings(self, user_id: str, slot_no: int = None, recycle_no: int = None) -> Dict[str, Any]:
        """
        Return Dream Matrix tree overview with nested structure similar to Binary:
        - tree: nested 3x3 matrix structure with directDownline arrays
        - slots: 1..15 slot catalog with name/value and completion/progress info
        """
        try:
                from ..tree.model import TreePlacement
                from ..slot.model import SlotActivation, SlotCatalog
                from ..user.model import User
                
                print(f"Getting Dream Matrix earnings for user: {user_id}")
                
                # Convert user_id to ObjectId
                try:
                    user_oid = ObjectId(user_id)
                except:
                    user_oid = user_id
                
                # Get user info
                user_info = User.objects(id=user_oid).first()
                if not user_info:
                    return {"success": False, "error": "User not found"}
                
                # Build nested downline tree nodes (limited to 3 levels: 0, 1, 2)
                # For 3x3 matrix: Level 0: 1, Level 1: 3, Level 2: 9 = 13 total
                try:
                    root_node, depth, total_nodes_count = self._build_nested_matrix_tree_limited(user_oid, max_levels=3)
                except Exception as tree_error:
                    print(f"Error building matrix tree: {tree_error}")
                    import traceback
                    traceback.print_exc()
                    # Return empty tree on error
                    root_node = {"id": 0, "type": "self", "userId": str(user_info.uid) if user_info else str(user_oid), "level": 0, "position": "root"}
                    depth = 0
                    total_nodes_count = 1
                
                # Calculate ACTUAL total team members (ALL levels, not just 3)
                actual_total_team_members = self._count_all_matrix_team_members(user_oid)
                
                # Member requirements for each slot to UPGRADE to next slot
                # Matrix recycle system: Each slot completes with 39 members (3 + 9 + 27)
                # To upgrade from Slot N to Slot N+1, you need to complete Slot N tree
                # Slot 1 → Slot 2: Need 3 members in Slot 1
                # Slot 2 → Slot 3: Need 9 members in Slot 2
                # Slot 3 → Slot 4: Need 27 members in Slot 3
                slot_member_requirements = {
                    1: 3,      # Slot 1: Need 3 members to upgrade to Slot 2
                    2: 9,      # Slot 2: Need 9 members to upgrade to Slot 3
                    3: 27,     # Slot 3: Need 27 members to upgrade to Slot 4
                    4: 81,     # Slot 4: Need 81 members to upgrade to Slot 5
                    5: 243,    # Slot 5: Need 243 members to upgrade to Slot 6
                    6: 729,    # Slot 6: Need 729 members to upgrade to Slot 7
                    7: 2187,   # Slot 7: Need 2187 members to upgrade to Slot 8
                    8: 6561,   # Slot 8: Need 6561 members to upgrade to Slot 9
                    9: 19683,  # Slot 9: Need 19683 members to upgrade to Slot 10
                    10: 59049, # Slot 10: Need 59049 members to upgrade to Slot 11
                    11: 177147, # Slot 11: Need 177147 members to upgrade to Slot 12
                    12: 531441, # Slot 12: Need 531441 members to upgrade to Slot 13
                    13: 1594323, # Slot 13: Need 1594323 members to upgrade to Slot 14
                    14: 4782969, # Slot 14: Need 4782969 members to upgrade to Slot 15
                    15: 14348907 # Slot 15: Maximum slot
                }
                
                # Gather slot catalog 1..15 for matrix
                catalogs = SlotCatalog.objects(program='matrix').order_by('slot_no')
                catalog_by_slot = {c.slot_no: c for c in catalogs}
                max_slot_no = max(catalog_by_slot.keys()) if catalog_by_slot else 15
                target_max_slot = max(15, max_slot_no)
                
                # Activated/completed slots for this user
                activated = SlotActivation.objects(user_id=user_oid, program='matrix', status='completed')
                completed_slots = {a.slot_no for a in activated}
                
                # Determine which slots are actually completed based on member count
                member_completed_slots = set()
                for slot_no in range(1, target_max_slot + 1):
                    required_members = slot_member_requirements.get(slot_no, 0)
                    if actual_total_team_members >= required_members:
                        member_completed_slots.add(slot_no)
                
                # Combine both: slot is completed if either activated OR member requirement met
                all_completed_slots = completed_slots.union(member_completed_slots)
                
                # Find highest completed slot
                highest_completed_slot = max(all_completed_slots) if all_completed_slots else 0
                
                # Next slot for manual upgrade
                next_manual_upgrade_slot = highest_completed_slot + 1 if highest_completed_slot < target_max_slot else None
                
                # Build slots summary array
                slots_summary = []
                for slot_no in range(1, target_max_slot + 1):
                    catalog = catalog_by_slot.get(slot_no)
                    slot_name = catalog.name if catalog else f"Slot {slot_no}"
                    slot_value = float(catalog.price) if catalog and catalog.price is not None else 0.0
                    
                    # Check if slot is completed
                    is_completed = slot_no in all_completed_slots
                    
                    # Check if this is the slot available for manual upgrade
                    is_manual_upgrade = (slot_no == next_manual_upgrade_slot)
                    
                    # Calculate progress percentage for CURRENT ACTIVE SLOT
                    # If user is in Slot N, progress shows how many members joined in Slot N tree
                    # to upgrade to Slot N+1
                    progress_percent = 0
                    
                    if is_completed:
                        # Completed slots always show 100%
                        progress_percent = 100
                    elif slot_no == highest_completed_slot + 1:
                        # This is the current active slot
                        # Count members in THIS specific slot's tree
                        current_slot_members = self._count_slot_specific_members(user_oid, slot_no)
                        required_members = slot_member_requirements.get(slot_no, 0)
                        
                        if required_members > 0:
                            progress_percent = int(min(100, (current_slot_members / required_members) * 100))
                        else:
                            progress_percent = 0
                    else:
                        # Future slots show 0%
                        progress_percent = 0
                    
                    slots_summary.append({
                        "slot_no": slot_no,
                        "slot_name": slot_name,
                        "slot_value": slot_value,
                        "isCompleted": is_completed,
                        "isManualUpgrade": is_manual_upgrade,
                        "progressPercent": progress_percent
                    })
                
                # Build result with nested tree structure
                result = {
                    "tree": {
                        "userId": str(user_info.uid) if user_info and user_info.uid else str(user_oid),
                        "totalMembers": max(0, total_nodes_count - 1),  # Exclude the root user
                        "levels": depth,
                        "nodes": [root_node]  # Root node with nested directDownline structure
                    },
                    "slots": slots_summary,
                    "totalSlots": len(slots_summary),
                    "user_id": str(user_id)
                }
                
                print(f"Dream Matrix tree overview generated: nodes={total_nodes_count}, slots={len(slots_summary)}")
                return {"success": True, "data": result}
                
        except Exception as e:
            print(f"Error in get_dream_matrix_earnings: {e}")
            return {"success": False, "error": str(e)}

    def _build_nested_matrix_tree_limited(self, user_oid, max_levels: int = 3) -> (Dict[str, Any], int, int):
        """
        Build a nested tree structure with directDownline arrays for matrix program.
        Uses TreePlacement model (same as Binary).
        Limited to max_levels (default 3: level 0, 1, 2).
        For 3x3 matrix: Level 0: 1, Level 1: 3, Level 2: 9 = 13 total maximum
        Returns (root_node, max_depth, total_count).
        Each node has: id, type, userId, level, position, directDownline (array of child nodes).
        """
        try:
            from ..tree.model import TreePlacement
            from ..user.model import User
            
            # Helper to get display id
            def display_id(oid) -> str:
                try:
                    u = User.objects(id=oid).only('uid').first()
                    return str(u.uid) if u and u.uid else str(oid)
                except Exception:
                    return str(oid)
            
            # Counter for node IDs
            node_id_counter = [0]
            total_count = [0]
            
            # Helper to build node recursively with level limit
            def build_node(parent_oid, level: int, position: str) -> Dict[str, Any]:
                # Stop if we've exceeded max levels
                if level >= max_levels:
                    return None
                
                # Increment total count
                total_count[0] += 1
                
                # Get current node ID and increment counter
                current_id = node_id_counter[0]
                node_id_counter[0] += 1
                
                # Determine node type
                node_type = "self" if level == 0 else "downLine"
                
                # Create the node
                node = {
                    "id": current_id,
                    "type": node_type,
                    "userId": display_id(parent_oid),
                    "level": level,
                    "position": position
                }
                
                # Only get children if we're not at the last level
                if level < max_levels - 1:
                    # Get direct children from TreePlacement for matrix program
                    # Matrix has 3 positions per level (3x3 structure)
                    # IMPORTANT: Exclude self (user_id != parent_oid) to avoid root appearing as child
                    children = TreePlacement.objects(
                        program='matrix',
                        upline_id=parent_oid,
                        user_id__ne=parent_oid  # Exclude self
                    ).order_by('created_at').limit(3)
                    
                    # Build directDownline array
                    direct_downline = []
                    
                    # Position names for matrix (3 positions)
                    positions = ['left', 'middle', 'right']
                    
                    # Add children (max 3 for matrix)
                    for idx, child in enumerate(children):
                        child_position = positions[idx] if idx < len(positions) else f"pos{idx}"
                        child_node = build_node(
                            child.user_id,
                            level + 1,
                            child_position
                        )
                        if child_node:
                            direct_downline.append(child_node)
                    
                    # Add directDownline array to node if there are children
                    if direct_downline:
                        node["directDownline"] = direct_downline
                
                return node
            
            # Start building from root
            root_node = build_node(user_oid, 0, "root")
            
            # Calculate max depth by traversing the tree
            def calculate_depth(node: Dict[str, Any]) -> int:
                if not node or "directDownline" not in node or not node["directDownline"]:
                    return node.get("level", 0) if node else 0
                return max(calculate_depth(child) for child in node["directDownline"])
            
            max_depth = calculate_depth(root_node) if root_node else 0
            
            return root_node, max_depth, total_count[0]
            
        except Exception as e:
            print(f"❌ Error building nested matrix tree: {e}")
            import traceback
            traceback.print_exc()
            # Return empty root node
            return {
                "id": 0,
                "type": "self",
                "userId": str(user_oid),
                "level": 0,
                "position": "root"
            }, 0, 1
    
    def _count_all_matrix_team_members(self, user_oid) -> int:
        """Count ALL matrix team members recursively (all levels) from TreePlacement"""
        try:
            from ..tree.model import TreePlacement
            
            visited = set()
            
            def count_recursive(parent_oid, depth=0) -> int:
                # Prevent infinite loop
                if depth > 20:
                    return 0
                
                parent_str = str(parent_oid)
                if parent_str in visited:
                    return 0
                visited.add(parent_str)
                
                # Get direct children
                children = TreePlacement.objects(
                    program='matrix',
                    upline_id=parent_oid
                )
                
                count = children.count()
                
                # Recursively count children's children
                for child in children:
                    count += count_recursive(child.user_id, depth + 1)
                
                return count
            
            # Start counting from root user's children
            total = count_recursive(user_oid)
            return total
            
        except Exception as e:
            print(f"Error counting matrix team members: {e}")
            return 0
    
    def _count_slot_specific_members(self, user_oid, slot_no: int) -> int:
        """
        Count members in a SPECIFIC slot's tree.
        This counts only users who joined in THIS particular slot.
        Used for progress calculation: current slot members / required members
        """
        try:
            from ..tree.model import TreePlacement
            
            visited = set()
            
            def count_recursive(parent_oid, depth=0) -> int:
                # Prevent infinite loop
                if depth > 20:
                    return 0
                
                parent_str = str(parent_oid)
                if parent_str in visited:
                    return 0
                visited.add(parent_str)
                
                # Get direct children for THIS specific slot
                children = TreePlacement.objects(
                    program='matrix',
                    upline_id=parent_oid,
                    slot_no=slot_no,
                    is_active=True
                )
                
                count = children.count()
                
                # Recursively count children's children in same slot
                for child in children:
                    count += count_recursive(child.user_id, depth + 1)
                
                return count
            
            # Start counting from root user's children in this slot
            total = count_recursive(user_oid)
            return total
            
        except Exception as e:
            print(f"Error counting slot {slot_no} members: {e}")
            return 0
    
    def _get_matrix_team_members(self, tree) -> List[Dict[str, Any]]:
        """Get team members for matrix tree display"""
        try:
            team_members = []
            member_id = 1
            
            # Add the user themselves first
            user_info = User.objects(id=tree.user_id).first()
            if user_info:
                user_display_id = str(user_info.uid) if user_info and user_info.uid and user_info.uid != "ROOT" else str(tree.user_id)
                team_members.append({
                    "id": 0,
                    "type": "self",
                    "userId": user_display_id
                })
            
            # Add nodes from the tree
            for i, node in enumerate(tree.nodes):
                if node.is_active:
                    # Get node user info
                    node_user = User.objects(id=node.user_id).first()
                    if node_user:
                        user_display_id = str(node_user.uid) if node_user and node_user.uid and node_user.uid != "ROOT" else str(node.user_id)
                    else:
                        user_display_id = str(node.user_id)
                    
                    # If user_display_id is "USER004" or similar, use the actual user_id
                    if user_display_id.startswith("USER"):
                        user_display_id = str(node.user_id)
                    
                    # Determine user type based on level and position
                    user_type = "self"  # Default
                    if node.level == 1:
                        if node.position == 0:
                            user_type = "downLine"
                        elif node.position == 1:
                            user_type = "upLine"
                        elif node.position == 2:
                            user_type = "overTaker"
                    elif node.level == 2:
                        user_type = "downLine"
                    elif node.level == 3:
                        user_type = "upLine"
                    
                    team_members.append({
                        "id": member_id,
                        "type": user_type,
                        "userId": user_display_id
                    })
                    member_id += 1
            
            # If no real nodes found, return empty team members (just self)
            if len(team_members) <= 1:
                return team_members
            
            return team_members
            
        except Exception as e:
            return []

    def _get_total_matrix_earnings(self, user_oid) -> float:
        """Get total matrix earnings for a user"""
        try:
            from ..wallet.model import WalletLedger
            # Include matrix-related reasons
            matrix_reasons = [
                'matrix_joining_commission', 'matrix_upgrade_commission',
                'matrix_level_income', 'matrix_mentorship_bonus',
                'dream_matrix_income', 'matrix_auto_upgrade_credit',
                'matrix_slot_income'
            ]
            total = 0.0
            entries = WalletLedger.objects(user_id=user_oid, type='credit', reason__in=matrix_reasons).only('amount')
            for e in entries:
                total += float(getattr(e, 'amount', 0) or 0)
            return total
        except Exception as e:
            return 0.0

    def _get_recycle_count(self, user_oid, slot_no: int) -> int:
        """Get recycle count for a user's slot"""
        try:
            recycle_instances = MatrixRecycleInstance.objects(
                user_id=user_oid,
                slot_number=slot_no
            )
            return len(recycle_instances)
        except Exception as e:
            return 0

    def _get_downline_user_ids(self, user_oid) -> List[ObjectId]:
        """Return all downline user ObjectIds from Matrix tree placement (recursive) - ALL SLOTS."""
        try:
            from ..tree.model import TreePlacement
            
            result: List[ObjectId] = []
            queue: List[ObjectId] = [user_oid]
            visited: Set[str] = {str(user_oid)}
            
            while queue:
                current = queue.pop(0)
                # Get tree children using upline_id (actual tree structure)
                tree_children = TreePlacement.objects(
                    program='matrix',
                    upline_id=current
                ).only('user_id')
                
                for child in tree_children:
                    child_id_str = str(child.user_id)
                    if child_id_str in visited:
                        continue
                    visited.add(child_id_str)
                    result.append(child.user_id)
                    queue.append(child.user_id)
            
            return result
        except Exception as e:
            print(f"Error getting downline user ids: {e}")
            return []
    
    def _get_downline_user_ids_for_slot(self, user_oid, slot_no: int) -> List[ObjectId]:
        """Return downline user ObjectIds for a SPECIFIC SLOT from Matrix tree placement (recursive)."""
        try:
            from ..tree.model import TreePlacement
            
            result: List[ObjectId] = []
            queue: List[ObjectId] = [user_oid]
            visited: Set[str] = {str(user_oid)}
            
            while queue:
                current = queue.pop(0)
                # Get tree children for THIS SPECIFIC SLOT using upline_id
                tree_children = TreePlacement.objects(
                    program='matrix',
                    upline_id=current,
                    slot_no=slot_no  # Filter by slot
                ).only('user_id')
                
                for child in tree_children:
                    child_id_str = str(child.user_id)
                    if child_id_str in visited:
                        continue
                    visited.add(child_id_str)
                    result.append(child.user_id)
                    queue.append(child.user_id)
            
            return result
        except Exception as e:
            print(f"Error getting downline user ids for slot {slot_no}: {e}")
            return []

    def _get_user_max_matrix_slot(self, user_oid) -> int:
        """Return the highest completed Matrix slot_no for a user."""
        try:
            max_slot = 0
            
            # Check MatrixTree.current_slot (most reliable)
            tree = MatrixTree.objects(user_id=user_oid).first()
            if tree and getattr(tree, 'current_slot', None):
                try:
                    max_slot = max(max_slot, int(tree.current_slot or 0))
                except Exception:
                    pass
            
            # Check MatrixActivation records
            activations = MatrixActivation.objects(user_id=user_oid, status='completed').only('slot_no')
            for a in activations:
                try:
                    if int(a.slot_no or 0) > max_slot:
                        max_slot = int(a.slot_no)
                except Exception:
                    continue
            
            # Check User.matrix_slots array (fallback)
            user = User.objects(id=user_oid).first()
            if user and hasattr(user, 'matrix_slots') and user.matrix_slots:
                for slot_info in user.matrix_slots:
                    if hasattr(slot_info, 'level') and slot_info.is_active:
                        try:
                            slot_level = int(slot_info.level or 0)
                            if slot_level > max_slot:
                                max_slot = slot_level
                        except Exception:
                            continue
            
            return max_slot
        except Exception as e:
            print(f"Error getting user max matrix slot: {e}")
            return 0

    def get_dream_matrix_details(self, user_id: str, tree_id: int) -> Dict[str, Any]:
        """Get specific dream matrix tree details by tree ID"""
        try:
            print(f"Getting dream matrix details for user: {user_id}, tree_id: {tree_id}")
            
            # Convert user_id to ObjectId
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id
            
            # Get all dream matrix earnings first
            all_earnings = self.get_dream_matrix_earnings(user_id, None, None)
            
            if not all_earnings["success"]:
                return {"success": False, "error": all_earnings["error"]}
            
            # Find the specific tree by ID
            matrix_tree_data = all_earnings["data"]["matrixTreeData"]
            target_tree = None
            
            print(f"Available tree IDs: {[tree['id'] for tree in matrix_tree_data]}")
            
            for tree in matrix_tree_data:
                if tree["id"] == tree_id:
                    target_tree = tree
                    break
            
            if not target_tree:
                return {"success": False, "error": f"Tree with ID {tree_id} not found. Available IDs: {[tree['id'] for tree in matrix_tree_data]}"}
            
            return {
                "success": True,
                "data": target_tree
            }
            
        except Exception as e:
            print(f"Error getting dream matrix details: {e}")
            return {"success": False, "error": str(e)}


