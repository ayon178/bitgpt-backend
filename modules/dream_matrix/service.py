from typing import Dict, Any, List, Set
from bson import ObjectId
from modules.user.model import User
from modules.matrix.model import MatrixTree, MatrixRecycleInstance, MatrixActivation
from modules.slot.model import SlotCatalog
import random


class DreamMatrixService:
    """Dream Matrix Business Logic Service"""

    def get_dream_matrix_earnings(self, user_id: str, slot_no: int = None, recycle_no: int = None) -> Dict[str, Any]:
        """Return slot-wise Dream Matrix data:
        - For each Matrix slot (1..15 or catalog max):
          - Include slot details (name/value)
          - If the root user has upgraded up to that slot, include tree 'users' list
            with only the root and downline users who have that slot upgraded.
          - If not, include empty 'users'.
        """
        try:
                # Convert user_id to ObjectId
                try:
                    user_oid = ObjectId(user_id)
                except:
                    user_oid = user_id
                
                # Get user info
                user_info = User.objects(id=user_oid).first()
                if not user_info:
                    return {"success": False, "error": "User not found"}
                # Slot catalog and limits
                catalogs = SlotCatalog.objects(program='matrix').order_by('slot_no')
                catalog_by_slot = {c.slot_no: c for c in catalogs}
                max_catalog_slot = max(catalog_by_slot.keys()) if catalog_by_slot else 15
                target_max_slot = max(15, max_catalog_slot)

                # Root user's current (max) completed matrix slot
                root_current_slot = self._get_user_max_matrix_slot(user_oid)

                user_display_id = str(user_info.uid) if user_info and user_info.uid and user_info.uid != "ROOT" else str(user_oid)

                matrix_tree_data = []

                # Build slot-wise items
                for s in range(1, target_max_slot + 1):
                    catalog = catalog_by_slot.get(s)
                    slot_name = catalog.name if catalog else f"Slot {s}"
                    price = float(catalog.price) if catalog and catalog.price is not None else 0.0

                    # Determine completion for root
                    is_completed = s <= root_current_slot

                    # Users list only if root has this slot - GET USERS FOR THIS SPECIFIC SLOT
                    users_list: List[Dict[str, Any]] = []
                    if is_completed:
                        # Add root user
                        users_list.append({"id": 0, "type": "self", "userId": user_display_id})
                        
                        # Get downline users from TreePlacement for THIS SPECIFIC SLOT
                        slot_downline_ids = self._get_downline_user_ids_for_slot(user_oid, s)
                        
                        idx = 1
                        # Include all users in this slot's tree
                        for did in slot_downline_ids:
                            # Resolve uid
                            try:
                                du = User.objects(id=did).only('uid').first()
                                duid = str(du.uid) if du and du.uid else str(did)
                            except Exception:
                                duid = str(did)
                            users_list.append({"id": idx, "type": "downLine", "userId": duid})
                            idx += 1
                        
                        # Optional cap to 39 to match 3x matrix tree size
                        if len(users_list) > 39:
                            users_list = users_list[:39]

                    matrix_tree_data.append({
                        "id": s,
                        "price": price,
                        "userId": user_display_id,
                        "recycle": self._get_recycle_count(user_oid, s),
                        "isCompleted": is_completed,
                        "isProcess": False,
                        "isAutoUpgrade": False,
                        "isManualUpgrade": False,
                        "processPercent": 0,
                        "users": users_list
                    })

                result = {
                    "matrixTreeData": matrix_tree_data,
                    "totalSlots": len(matrix_tree_data),
                    "user_id": str(user_id)
                }
                
                return {"success": True, "data": result}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

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


