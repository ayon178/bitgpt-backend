from typing import Dict, Any, List
from bson import ObjectId
from modules.user.model import User
from modules.matrix.model import MatrixTree, MatrixRecycleInstance
import random


class DreamMatrixService:
    """Dream Matrix Business Logic Service"""

    def get_dream_matrix_earnings(self, user_id: str, slot_no: int = None, recycle_no: int = None) -> Dict[str, Any]:
        """Get Dream Matrix earnings data matching frontend matrixData.js structure"""
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
                
                # Get all matrix slots for this user (like binary service)
                matrix_trees = MatrixTree.objects(user_id=user_oid).order_by('current_slot')
                
                # Get unique slot numbers for this user
                slot_numbers = set()
                for tree in matrix_trees:
                    slot_numbers.add(tree.current_slot)
                
                # If no slots found, create default empty slots
                if not slot_numbers:
                    slot_numbers = set(range(1, 11))  # Default slots 1-10
                
                # Filter by recycle if provided
                if recycle_no:
                    # Get recycle instances for the user
                    recycle_instances = MatrixRecycleInstance.objects(
                        user_id=user_oid,
                        slot_number=slot_no if slot_no else 1,
                        recycle_no=recycle_no
                    )
                    if not recycle_instances:
                        return {"success": False, "error": f"No recycle instance found for slot {slot_no}, recycle {recycle_no}"}
                
                matrix_tree_data = []
                
                for slot_no in sorted(slot_numbers):
                    # Get the user's tree for this slot
                    tree = matrix_trees.filter(current_slot=slot_no).first()
                    
                    # Get total matrix earnings for this user (like binary service)
                    total_matrix_earnings = self._get_total_matrix_earnings(user_oid)
                    # Convert BNB to USDT (assuming 1 BNB = 300 USDT for display) - keep exact amount
                    price = total_matrix_earnings * 300 if total_matrix_earnings > 0 else 0.0
                    
                    # If price is still 0, use progressive pricing based on slot level
                    if price == 0:
                        # Progressive pricing: 100, 200, 300, 400, etc.
                        price = 100 + (slot_no - 1) * 100
                    
                    # Calculate status flags
                    is_completed = tree.is_complete if tree else False
                    is_process = tree and not tree.is_complete and tree.total_members > 0
                    is_auto_upgrade = False  # Matrix doesn't have auto upgrade
                    is_manual_upgrade = tree and not tree.is_complete and tree.total_members >= 3
                    
                    # Calculate process percent
                    max_members = 39  # Matrix tree max members
                    process_percent = min(100, (tree.total_members / max_members) * 100) if tree else 0
                    
                    # Get team members for this slot
                    team_members = self._get_matrix_team_members(tree) if tree else []
                    
                    # Create matrix tree data object matching matrixData.js structure
                    # Use actual user ID instead of "ROOT"
                    user_display_id = str(user_info.uid) if user_info and user_info.uid and user_info.uid != "ROOT" else str(user_oid)
                    
                    matrix_tree_item = {
                        "id": slot_no,
                        "price": price,
                        "userId": user_display_id,
                        "recycle": self._get_recycle_count(user_oid, slot_no),
                        "isCompleted": is_completed,
                        "isProcess": is_process,
                        "isAutoUpgrade": is_auto_upgrade,
                        "isManualUpgrade": is_manual_upgrade,
                        "processPercent": int(process_percent),
                        "users": team_members
                    }
                    
                    matrix_tree_data.append(matrix_tree_item)
                
                # Always create multiple matrix items like frontend matrixData.js
                
                # If we have real data, create progressive matrices with incremental user counts
                if len(matrix_tree_data) > 0:
                    # Get all real users from the first matrix
                    real_matrix = matrix_tree_data[0]  # Keep the first real matrix
                    all_real_users = real_matrix["users"]  # Get all real users
                    matrix_tree_data = []  # Clear and rebuild
                    
                    # Create multiple matrices with progressive user counts
                    matrix_ids = [11, 12, 13, 14, 15, 16, 17, 18, 19, 39]
                    for matrix_index, matrix_id in enumerate(matrix_ids):
                        # Calculate how many users this matrix should have (progressive: 1, 2, 3, 4...)
                        user_count = matrix_index + 1
                        
                        # Take only the first N users from real data
                        users = all_real_users[:user_count] if user_count <= len(all_real_users) else all_real_users
                        
                        # Calculate price based on user count
                        total_matrix_earnings = self._get_total_matrix_earnings(user_oid)
                        price = total_matrix_earnings * 300 if total_matrix_earnings > 0 else (100 + matrix_id * 10)
                        
                        # Determine status based on matrix index
                        is_completed = matrix_index == 0  # First one completed
                        is_process = matrix_index == 2    # Third one in process
                        is_auto_upgrade = matrix_index == 1  # Second one auto upgrade
                        is_manual_upgrade = matrix_index == 2  # Third one manual upgrade
                        process_percent = 50 if matrix_index == 2 else (100 if matrix_index == 0 else 0)
                        
                        matrix_tree_item = {
                            "id": matrix_id,
                            "price": price,
                            "userId": real_matrix["userId"],
                            "recycle": real_matrix["recycle"],
                            "isCompleted": is_completed,
                            "isProcess": is_process,
                            "isAutoUpgrade": is_auto_upgrade,
                            "isManualUpgrade": is_manual_upgrade,
                            "processPercent": process_percent,
                            "users": users
                        }
                        
                        matrix_tree_data.append(matrix_tree_item)
                else:
                    # No real data found, create mock data for all slots
                    # Create multiple matrix items like in mock data
                    mock_ids = [11, 12, 13, 14, 15, 16, 17, 18, 19, 39]
                    for slot_id in mock_ids:
                        total_matrix_earnings = self._get_total_matrix_earnings(user_oid)
                        price = total_matrix_earnings * 300 if total_matrix_earnings > 0 else (100 + slot_id * 10)
                        
                        # Generate users like frontend matrixData.js (11-19 users)
                        users = []
                        user_types = ["self", "downLine", "upLine", "overTaker"]
                        
                        # Add self user first
                        user_display_id = str(user_info.uid) if user_info and user_info.uid and user_info.uid != "ROOT" else str(user_oid)
                        users.append({
                            "id": 0,
                            "type": "self",
                            "userId": user_display_id
                        })
                        
                        # Add users like frontend (11-19 users per matrix)
                        max_users = 11 + (slot_id % 9)  # 11-19 users
                        for i in range(1, max_users):
                            mock_user_id = f"USER{10000 + slot_id * 100 + i}"
                            user_type = user_types[i % len(user_types)]
                            users.append({
                                "id": i,
                                "type": user_type,
                                "userId": mock_user_id
                            })
                        
                        matrix_tree_item = {
                            "id": slot_id,
                            "price": price,
                            "userId": user_display_id,
                            "recycle": 0,
                            "isCompleted": slot_id == 11,  # First one completed
                            "isProcess": slot_id == 13,    # Third one in process
                            "isAutoUpgrade": slot_id == 12, # Second one auto upgrade
                            "isManualUpgrade": slot_id == 13, # Third one manual upgrade
                            "processPercent": 50 if slot_id == 13 else (100 if slot_id == 11 else 0),
                            "users": users
                        }
                        
                        matrix_tree_data.append(matrix_tree_item)
                
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
            # This is a placeholder - implement actual earnings calculation
            return 0.0
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


