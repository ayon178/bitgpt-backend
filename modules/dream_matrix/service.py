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
        Return Dream Matrix tree overview with slot-wise nested structure:
        - slots: Each slot contains its own tree structure with directDownline arrays
        - Each slot shows its specific downline members and progress
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
                
                # Member requirements for each slot to UPGRADE to next slot
                # Matrix recycle system: Each slot completes with 39 members (3 + 9 + 27)
                # ALL SLOTS complete at 39 members - then automatic recycle happens
                # Level 1: 3 members, Level 2: 9 members, Level 3: 27 members = Total 39
                # This is SAME for ALL slots (1-15)
                MEMBERS_PER_SLOT = 39  # Universal completion requirement for all Matrix slots
                
                slot_member_requirements = {
                    1: MEMBERS_PER_SLOT,   # Slot 1: Need 39 members to complete/recycle
                    2: MEMBERS_PER_SLOT,   # Slot 2: Need 39 members to complete/recycle
                    3: MEMBERS_PER_SLOT,   # Slot 3: Need 39 members to complete/recycle
                    4: MEMBERS_PER_SLOT,   # Slot 4: Need 39 members to complete/recycle
                    5: MEMBERS_PER_SLOT,   # Slot 5: Need 39 members to complete/recycle
                    6: MEMBERS_PER_SLOT,   # Slot 6: Need 39 members to complete/recycle
                    7: MEMBERS_PER_SLOT,   # Slot 7: Need 39 members to complete/recycle
                    8: MEMBERS_PER_SLOT,   # Slot 8: Need 39 members to complete/recycle
                    9: MEMBERS_PER_SLOT,   # Slot 9: Need 39 members to complete/recycle
                    10: MEMBERS_PER_SLOT,  # Slot 10: Need 39 members to complete/recycle
                    11: MEMBERS_PER_SLOT,  # Slot 11: Need 39 members to complete/recycle
                    12: MEMBERS_PER_SLOT,  # Slot 12: Need 39 members to complete/recycle
                    13: MEMBERS_PER_SLOT,  # Slot 13: Need 39 members to complete/recycle
                    14: MEMBERS_PER_SLOT,  # Slot 14: Need 39 members to complete/recycle
                    15: MEMBERS_PER_SLOT   # Slot 15: Need 39 members to complete/recycle
                }
                
                # Gather slot catalog 1..15 for matrix; fallback to defaults if catalog empty
                catalogs = SlotCatalog.objects(program='matrix').order_by('slot_no')
                catalog_by_slot = {c.slot_no: c for c in catalogs}
                # Default Matrix slot costs in USDT
                default_slot_costs = {
                    1: 11, 2: 33, 3: 99, 4: 297, 5: 891,
                    6: 2673, 7: 8019, 8: 24057, 9: 72171, 10: 216513,
                    11: 649539, 12: 1948617, 13: 5845851, 14: 17537553, 15: 52612659
                }
                max_slot_no = max(catalog_by_slot.keys()) if catalog_by_slot else 15
                target_max_slot = max(15, max_slot_no)
                
                # Get user's current active Matrix slot from MatrixTree
                matrix_tree_obj = MatrixTree.objects(user_id=user_oid).first()
                user_current_slot = matrix_tree_obj.current_slot if matrix_tree_obj else 1
                
                # Activated/completed slots for this user (from slot activations)
                activated = SlotActivation.objects(user_id=user_oid, program='matrix', status='completed')
                completed_slots = {a.slot_no for a in activated}
                
                # Determine which slots are actually completed based on user's own progress
                # A slot is completed if:
                # 1. User has SlotActivation with status 'completed' for that slot
                # 2. User's current slot (from MatrixTree) is higher than the slot being checked
                # 3. User has MatrixActivation with status 'completed' for that slot
                
                # Get MatrixActivation completed slots
                matrix_activations = MatrixActivation.objects(user_id=user_oid, status='completed')
                matrix_completed_slots = {a.slot_no for a in matrix_activations}
                
                # Combine all completion sources
                all_completed_slots = completed_slots.union(matrix_completed_slots)
                
                # Use user's current active slot from MatrixTree as the baseline
                # If user is on slot N, then slots 1 to N-1 are completed
                for s in range(1, user_current_slot):
                    all_completed_slots.add(s)
                
                # Find highest completed slot (but don't exceed user's current slot)
                highest_completed_slot = user_current_slot - 1 if user_current_slot > 1 else 0
                
                # Next slot for manual upgrade
                next_manual_upgrade_slot = highest_completed_slot + 1 if highest_completed_slot < target_max_slot else None
                
                # Build slots summary array with individual tree structures
                slots_summary = []
                
                # Store original slot_no parameter to avoid variable conflicts
                requested_slot_no = slot_no
                
                # If slot_no parameter is provided, only process that specific slot
                if requested_slot_no is not None:
                    try:
                        slot_no_int = int(requested_slot_no)
                        if 1 <= slot_no_int <= target_max_slot:
                            slot_range = [slot_no_int]
                        else:
                            slot_range = []
                    except (ValueError, TypeError):
                        slot_range = []
                else:
                    slot_range = range(1, target_max_slot + 1)
                
                for current_slot_no in slot_range:
                    catalog = catalog_by_slot.get(current_slot_no)
                    slot_name = catalog.name if catalog and getattr(catalog, 'name', None) else f"Slot {current_slot_no}"
                    if catalog and getattr(catalog, 'price', None) is not None:
                        slot_value = float(catalog.price)
                    else:
                        slot_value = float(default_slot_costs.get(current_slot_no, 0))
                    
                    # Check if slot is completed
                    is_completed = current_slot_no in all_completed_slots
                    
                    # Check if this is the slot available for manual upgrade
                    is_manual_upgrade = (current_slot_no == next_manual_upgrade_slot)
                    
                    # Calculate progress percentage for each slot
                    # Progress shows: (current members in this slot / 39) * 100
                    # User's CURRENT ACTIVE slot (from MatrixTree.current_slot) shows real-time progress
                    progress_percent = 0
                    
                    if is_completed:
                        # Completed/past slots always show 100%
                        progress_percent = 100
                    elif current_slot_no == user_current_slot:
                        # This is the CURRENT ACTIVE slot - show real-time progress
                        # Count members in THIS specific slot's tree
                        current_slot_members = self._count_slot_specific_members(user_oid, current_slot_no)
                        required_members = slot_member_requirements.get(current_slot_no, 39)  # Always 39 for Matrix
                        
                        if required_members > 0:
                            progress_percent = int(min(100, (current_slot_members / required_members) * 100))
                        else:
                            progress_percent = 0
                        
                        # Debug log
                        print(f"📊 Slot {current_slot_no} Progress: {current_slot_members}/{required_members} members = {progress_percent}%")
                    else:
                        # Future slots (not yet reached) show 0%
                        progress_percent = 0
                    
                    # Build slot object
                    slot_obj = {
                        "slot_no": current_slot_no,
                        "slot_name": slot_name,
                        "slot_value": slot_value,
                        "isCompleted": is_completed,
                        "isManualUpgrade": is_manual_upgrade,
                        "progressPercent": progress_percent
                    }
                    
                    # Add tree structure for completed slots AND the current active slot
                    if is_completed or current_slot_no == user_current_slot:
                        try:
                            # Build up to Level 10 (root=0 plus 10 levels)
                            slot_root_node, slot_depth, slot_total_nodes_count = self._build_nested_matrix_tree_limited(user_oid, max_levels=11, slot_no=current_slot_no)
                        except Exception as tree_error:
                            print(f"Error building matrix tree for slot {current_slot_no}: {tree_error}")
                            import traceback
                            traceback.print_exc()
                            # Return empty tree on error
                            slot_root_node = {
                                "id": 0, 
                                "type": "self", 
                                "userId": str(user_info.uid) if user_info and user_info.uid else str(user_oid),
                                "objectId": str(user_oid),
                                "level": 0, 
                                "position": "root"
                            }
                            slot_depth = 0
                            slot_total_nodes_count = 1
                        
                        # Build tree structure for this slot
                        slot_tree = {
                            "userId": str(user_info.uid) if user_info and user_info.uid else str(user_oid),
                            "totalMembers": max(0, slot_total_nodes_count - 1),  # Exclude the root user
                            "levels": slot_depth,
                            "nodes": [slot_root_node]  # Root node with nested directDownline structure
                        }
                        
                        slot_obj["tree"] = slot_tree
                    
                    slots_summary.append(slot_obj)
                
                # Build result with slot-wise tree structures
                result = {
                    "slots": slots_summary,
                    "totalSlots": len(slots_summary),
                    "user_id": str(user_id)
                }
                
                print(f"Dream Matrix slot-wise tree overview generated: slots={len(slots_summary)}")
                return {"success": True, "data": result}
                
        except Exception as e:
            print(f"Error in get_dream_matrix_earnings: {e}")
            return {"success": False, "error": str(e)}

    def _build_nested_matrix_tree_limited(self, user_oid, max_levels: int = 3, slot_no: int = None) -> (Dict[str, Any], int, int):
        """
        Build a nested tree structure with directDownline arrays for matrix program.
        Uses TreePlacement model (same as Binary).
        Limited to max_levels (default 3: level 0, 1, 2).
        For 3x3 matrix: Level 0: 1, Level 1: 3, Level 2: 9 = 13 total maximum
        Returns (root_node, max_depth, total_count).
        Each node has: id, type, userId, level, position, directDownline (array of child nodes).
        If slot_no is provided, only shows members from that specific slot.
        """
        try:
            from ..tree.model import TreePlacement
            from ..user.model import User
            
            # Helper to get user basic display info + refer codes
            def get_user_info(oid) -> dict:
                try:
                    u = User.objects(id=oid).only('uid', 'refer_code', 'refered_by').first()
                    uid_val = str(u.uid) if u and getattr(u, 'uid', None) else str(oid)
                    refer_code_val = getattr(u, 'refer_code', None) if u else None
                    referrer_code_val = None
                    try:
                        if u and getattr(u, 'refered_by', None):
                            inviter = User.objects(id=u.refered_by).only('refer_code').first()
                            referrer_code_val = getattr(inviter, 'refer_code', None) if inviter else None
                    except Exception:
                        referrer_code_val = None
                    return {
                        "uid": uid_val,
                        "object_id": str(oid),
                        "refer_code": refer_code_val,
                        "referrer_refer_code": referrer_code_val
                    }
                except Exception:
                    return {
                        "uid": str(oid),
                        "object_id": str(oid),
                        "refer_code": None,
                        "referrer_refer_code": None
                    }
            
            # Counter for node IDs
            node_id_counter = [0]
            total_count = [0]
            
            # Helper to build node recursively with level limit
            def build_node(current_oid, level: int, position: str, tree_parent_oid=None) -> Dict[str, Any]:
                """
                Build a node recursively.
                current_oid: The user whose node we're building
                tree_parent_oid: The actual tree parent (for parent_id display)
                """
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
                
                # Get user info
                user_info = get_user_info(current_oid)
                
                # Create the node
                node = {
                    "id": current_id,
                    "type": node_type,
                    "userId": user_info["uid"],
                    "objectId": user_info["object_id"],
                    "refer_code": user_info.get("refer_code"),
                    "referrer_refer_code": user_info.get("referrer_refer_code"),
                    "level": level,
                    "position": position
                }
                
                # Add parent_id for non-root nodes (the actual tree parent)
                if level > 0 and tree_parent_oid:
                    node["parent_id"] = str(tree_parent_oid)
                
                # Only get children if we're not at the last level
                if level < max_levels - 1:
                    # Build query filter for TreePlacement
                    query_filter = {
                        "program": 'matrix',
                        "upline_id": current_oid,  # Changed from parent_oid to current_oid
                        "user_id__ne": current_oid  # Exclude self
                    }
                    
                    # Add slot filter if slot_no is provided
                    if slot_no is not None:
                        query_filter["slot_no"] = slot_no
                        query_filter["is_active"] = True
                    
                    # Fetch children and map by saved position to enforce left→middle→right ordering
                    children = TreePlacement.objects(**query_filter).only('user_id', 'position', 'created_at').order_by('created_at')
                    children_by_position = { 'left': None, 'middle': None, 'right': None }
                    for ch in children:
                        pos_key = getattr(ch, 'position', None)
                        if pos_key in children_by_position and children_by_position[pos_key] is None:
                            children_by_position[pos_key] = ch

                    # Build directDownline in fixed order
                    direct_downline = []
                    for pos_key in ['left', 'middle', 'right']:
                        ch = children_by_position[pos_key]
                        if not ch:
                            continue
                        child_node = build_node(
                            ch.user_id,
                            level + 1,
                            pos_key,
                            tree_parent_oid=current_oid
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
            # Return empty root node with user info
            user_info = get_user_info(user_oid)
            return {
                "id": 0,
                "type": "self",
                "userId": user_info["uid"],
                "objectId": user_info["object_id"],
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


