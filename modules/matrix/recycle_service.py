#!/usr/bin/env python3
"""
Matrix Recycle Service
Handles the 39-member completion and automatic recycle mechanism
"""

from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from datetime import datetime
from bson import ObjectId

from ..user.model import User
from ..wallet.model import UserWallet, ReserveLedger
from ..slot.model import SlotCatalog, SlotActivation
from ..tree.model import TreePlacement
from ..blockchain.model import BlockchainEvent
from ..income.model import IncomeEvent
from .model import MatrixTree, MatrixNode, MatrixActivation, MatrixRecycleInstance, MatrixRecycleNode


class MatrixRecycleService:
    """Service for managing Matrix Recycle System with 39-member completion"""
    
    def __init__(self):
        self.max_matrix_members = 39  # 3 + 9 + 27 structure
        self.mother_id = "68dc17f08b174277bc40d19c"  # Mother ID fallback
    
    def check_recycle_completion(self, user_id: str, slot_no: int) -> Dict[str, Any]:
        """
        Check if a user's matrix tree has reached 39-member completion for recycling.
        
        Args:
            user_id: The user whose matrix tree to check
            slot_no: The slot number to check for completion
            
        Returns:
            Dict with completion status and details
        """
        try:
            # Get user's matrix tree
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return {"success": False, "error": "Matrix tree not found"}
            
            # Check if tree has reached 39 members
            if matrix_tree.total_members >= self.max_matrix_members:
                # Check if this is a new completion (not already recycled)
                existing_recycle = MatrixRecycleInstance.objects(
                    user_id=ObjectId(user_id),
                    slot_number=slot_no,
                    is_complete=True
                ).order_by('-completed_at').first()
                
                if existing_recycle:
                    # Already recycled, check if we need to create new tree
                    return self._check_new_tree_creation(user_id, slot_no)
                else:
                    # First time completion - trigger recycle
                    return self._trigger_recycle_process(user_id, slot_no, matrix_tree)
            else:
                return {
                    "success": True,
                    "is_complete": False,
                    "current_members": matrix_tree.total_members,
                    "required_members": self.max_matrix_members,
                    "remaining": self.max_matrix_members - matrix_tree.total_members
                }
                
        except Exception as e:
            return {"success": False, "error": f"Recycle completion check failed: {str(e)}"}
    
    def _trigger_recycle_process(self, user_id: str, slot_no: int, matrix_tree: MatrixTree) -> Dict[str, Any]:
        """
        Trigger the recycle process when 39 members are completed.
        """
        try:
            # Create recycle instance snapshot
            recycle_instance = self._create_recycle_snapshot(user_id, slot_no, matrix_tree)
            
            # Create new empty tree for the same slot
            new_tree = self._create_new_tree_for_recycle(user_id, slot_no)
            
            # Process recycle placement for the triggering user
            recycle_result = self._process_recycle_placement(user_id, slot_no)
            
            return {
                "success": True,
                "is_complete": True,
                "recycled": True,
                "recycle_instance_id": str(recycle_instance.id),
                "new_tree_id": str(new_tree.id),
                "placement_result": recycle_result,
                "message": f"Matrix slot {slot_no} recycled successfully with {matrix_tree.total_members} members"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Recycle process failed: {str(e)}"}
    
    def _create_recycle_snapshot(self, user_id: str, slot_no: int, matrix_tree: MatrixTree) -> MatrixRecycleInstance:
        """
        Create an immutable snapshot of the completed matrix tree.
        """
        try:
            # Get next recycle number
            recycle_no = self._get_next_recycle_number(user_id, slot_no)
            
            # Create recycle instance
            recycle_instance = MatrixRecycleInstance(
                user_id=ObjectId(user_id),
                slot_number=slot_no,
                recycle_no=recycle_no,
                is_complete=True,
                total_members=matrix_tree.total_members,
                level_1_members=matrix_tree.level_1_members,
                level_2_members=matrix_tree.level_2_members,
                level_3_members=matrix_tree.level_3_members,
                created_at=matrix_tree.created_at,
                completed_at=datetime.utcnow()
            )
            recycle_instance.save()
            
            # Create recycle nodes (immutable snapshots)
            for node in matrix_tree.nodes:
                recycle_node = MatrixRecycleNode(
                    instance_id=recycle_instance.id,
                    user_id=ObjectId(user_id),
                    slot_number=slot_no,
                    recycle_no=recycle_no,
                    level=node.level,
                    position=node.position,
                    occupant_user_id=node.user_id,
                    placed_at=node.placed_at
                )
                recycle_node.save()
            
            print(f"Created recycle snapshot: User {user_id}, Slot {slot_no}, Recycle #{recycle_no}")
            return recycle_instance
            
        except Exception as e:
            raise Exception(f"Failed to create recycle snapshot: {str(e)}")
    
    def _create_new_tree_for_recycle(self, user_id: str, slot_no: int) -> MatrixTree:
        """
        Create a new empty matrix tree for the recycled slot.
        """
        try:
            # Create new matrix tree
            new_tree = MatrixTree(
                user_id=ObjectId(user_id),
                current_slot=slot_no,
                current_level=1,
                total_members=0,
                level_1_members=0,
                level_2_members=0,
                level_3_members=0,
                is_complete=False,
                nodes=[],
                slots=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            new_tree.save()
            
            print(f"Created new matrix tree for recycle: User {user_id}, Slot {slot_no}")
            return new_tree
            
        except Exception as e:
            raise Exception(f"Failed to create new tree for recycle: {str(e)}")
    
    def _process_recycle_placement(self, user_id: str, slot_no: int) -> Dict[str, Any]:
        """
        Process the placement of the recycled user in their direct upline's tree.
        """
        try:
            # Get the user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user or not user.refered_by:
                # No direct upline, place in mother ID's tree
                return self._place_in_mother_tree(user_id, slot_no)
            
            direct_upline_id = str(user.refered_by)
            
            # Get direct upline's matrix tree for the same slot
            upline_tree = MatrixTree.objects(user_id=ObjectId(direct_upline_id)).first()
            if not upline_tree:
                # Upline doesn't have matrix tree, create one
                upline_tree = self._create_matrix_tree_for_upline(direct_upline_id, slot_no)
            
            # Place user in upline's tree using BFS
            placement_result = self._place_user_in_upline_tree(user_id, upline_tree, slot_no)
            
            return {
                "success": True,
                "placed_in_upline": True,
                "upline_id": direct_upline_id,
                "placement_details": placement_result
            }
            
        except Exception as e:
            return {"success": False, "error": f"Recycle placement failed: {str(e)}"}
    
    def _place_in_mother_tree(self, user_id: str, slot_no: int) -> Dict[str, Any]:
        """
        Place recycled user in mother ID's tree if no direct upline.
        """
        try:
            # Get or create mother's matrix tree
            mother_tree = MatrixTree.objects(user_id=ObjectId(self.mother_id)).first()
            if not mother_tree:
                mother_tree = self._create_matrix_tree_for_upline(self.mother_id, slot_no)
            
            # Place user in mother's tree
            placement_result = self._place_user_in_upline_tree(user_id, mother_tree, slot_no)
            
            return {
                "success": True,
                "placed_in_mother": True,
                "mother_id": self.mother_id,
                "placement_details": placement_result
            }
            
        except Exception as e:
            return {"success": False, "error": f"Mother tree placement failed: {str(e)}"}
    
    def _place_user_in_upline_tree(self, user_id: str, upline_tree: MatrixTree, slot_no: int) -> Dict[str, Any]:
        """
        Place user in upline's matrix tree using BFS placement algorithm.
        """
        try:
            # Find available position using BFS
            placement_position = self._find_bfs_placement_position(upline_tree)
            if not placement_position:
                return {"success": False, "error": "No available position in upline's tree"}
            
            # Create matrix node for the recycled user
            matrix_node = MatrixNode(
                level=placement_position["level"],
                position=placement_position["position"],
                user_id=ObjectId(user_id),
                placed_at=datetime.utcnow(),
                is_active=True
            )
            
            # Add node to upline's tree
            upline_tree.nodes.append(matrix_node)
            
            # Update tree statistics
            self._update_tree_statistics(upline_tree, placement_position["level"])
            
            # Check if this placement completes the upline's tree
            if upline_tree.total_members >= self.max_matrix_members:
                upline_tree.is_complete = True
                # Trigger cascade recycle for upline
                self._trigger_cascade_recycle(str(upline_tree.user_id), slot_no)
            
            upline_tree.updated_at = datetime.utcnow()
            upline_tree.save()
            
            return {
                "success": True,
                "placement_level": placement_position["level"],
                "placement_position": placement_position["position"],
                "tree_completed": upline_tree.is_complete
            }
            
        except Exception as e:
            return {"success": False, "error": f"Tree placement failed: {str(e)}"}
    
    def _find_bfs_placement_position(self, matrix_tree: MatrixTree) -> Optional[Dict[str, int]]:
        """
        Find available position using Breadth-First Search algorithm.
        """
        try:
            # Level 1: 3 positions (0, 1, 2)
            for pos in range(3):
                if not self._position_occupied(matrix_tree, 1, pos):
                    return {"level": 1, "position": pos}
            
            # Level 2: 9 positions (0-8)
            for pos in range(9):
                if not self._position_occupied(matrix_tree, 2, pos):
                    return {"level": 2, "position": pos}
            
            # Level 3: 27 positions (0-26)
            for pos in range(27):
                if not self._position_occupied(matrix_tree, 3, pos):
                    return {"level": 3, "position": pos}
            
            return None  # No available position
            
        except Exception as e:
            print(f"Error finding BFS placement: {e}")
            return None
    
    def _position_occupied(self, matrix_tree: MatrixTree, level: int, position: int) -> bool:
        """Check if a specific position in the matrix tree is occupied."""
        for node in matrix_tree.nodes:
            if node.level == level and node.position == position:
                return True
        return False
    
    def _update_tree_statistics(self, matrix_tree: MatrixTree, level: int):
        """Update matrix tree statistics after adding a new member."""
        matrix_tree.total_members += 1
        
        if level == 1:
            matrix_tree.level_1_members += 1
        elif level == 2:
            matrix_tree.level_2_members += 1
        elif level == 3:
            matrix_tree.level_3_members += 1
    
    def _create_matrix_tree_for_upline(self, upline_id: str, slot_no: int) -> MatrixTree:
        """Create a new matrix tree for an upline."""
        matrix_tree = MatrixTree(
            user_id=ObjectId(upline_id),
            current_slot=slot_no,
            current_level=1,
            total_members=0,
            level_1_members=0,
            level_2_members=0,
            level_3_members=0,
            is_complete=False,
            nodes=[],
            slots=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        matrix_tree.save()
        return matrix_tree
    
    def _get_next_recycle_number(self, user_id: str, slot_no: int) -> int:
        """Get the next recycle number for a user and slot."""
        last_recycle = MatrixRecycleInstance.objects(
            user_id=ObjectId(user_id),
            slot_number=slot_no
        ).order_by('-recycle_no').first()
        
        return (last_recycle.recycle_no + 1) if last_recycle else 1
    
    def _trigger_cascade_recycle(self, user_id: str, slot_no: int):
        """
        Trigger cascade recycle when upline's tree is completed by recycled user.
        """
        try:
            print(f"Triggering cascade recycle for user {user_id}, slot {slot_no}")
            # This will be handled by the main recycle check process
            # to avoid infinite recursion
        except Exception as e:
            print(f"Error in cascade recycle: {e}")
    
    def _check_new_tree_creation(self, user_id: str, slot_no: int) -> Dict[str, Any]:
        """
        Check if a new tree needs to be created after recycle.
        """
        try:
            # Get current matrix tree
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return {"success": False, "error": "Matrix tree not found"}
            
            # If tree is empty, it means it was already recycled and new tree created
            if matrix_tree.total_members == 0:
                return {
                    "success": True,
                    "is_complete": False,
                    "new_tree_created": True,
                    "current_members": 0,
                    "message": "New tree created after recycle"
                }
            else:
                return {
                    "success": True,
                    "is_complete": False,
                    "new_tree_created": False,
                    "current_members": matrix_tree.total_members,
                    "message": "Tree in progress"
                }
                
        except Exception as e:
            return {"success": False, "error": f"New tree check failed: {str(e)}"}
    
    def get_recycle_history(self, user_id: str, slot_no: int) -> Dict[str, Any]:
        """
        Get the complete recycle history for a user and slot.
        """
        try:
            # Get all recycle instances for the user and slot
            recycle_instances = MatrixRecycleInstance.objects(
                user_id=ObjectId(user_id),
                slot_number=slot_no
            ).order_by('recycle_no')
            
            history = {
                "user_id": user_id,
                "slot_no": slot_no,
                "total_recycles": len(recycle_instances),
                "recycles": []
            }
            
            for instance in recycle_instances:
                # Get recycle nodes for this instance
                recycle_nodes = MatrixRecycleNode.objects(
                    instance_id=instance.id
                ).order_by('level', 'position')
                
                recycle_info = {
                    "recycle_no": instance.recycle_no,
                    "is_complete": instance.is_complete,
                    "total_members": instance.total_members,
                    "level_1_members": instance.level_1_members,
                    "level_2_members": instance.level_2_members,
                    "level_3_members": instance.level_3_members,
                    "created_at": instance.created_at,
                    "completed_at": instance.completed_at,
                    "nodes": []
                }
                
                for node in recycle_nodes:
                    node_info = {
                        "level": node.level,
                        "position": node.position,
                        "occupant_user_id": str(node.occupant_user_id),
                        "placed_at": node.placed_at
                    }
                    recycle_info["nodes"].append(node_info)
                
                history["recycles"].append(recycle_info)
            
            return {"success": True, "data": history}
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get recycle history: {str(e)}"}
    
    def get_recycle_tree(self, user_id: str, slot_no: int, recycle_no: int) -> Dict[str, Any]:
        """
        Get a specific recycle tree snapshot.
        """
        try:
            # Get the specific recycle instance
            recycle_instance = MatrixRecycleInstance.objects(
                user_id=ObjectId(user_id),
                slot_number=slot_no,
                recycle_no=recycle_no
            ).first()
            
            if not recycle_instance:
                return {"success": False, "error": "Recycle instance not found"}
            
            # Get recycle nodes
            recycle_nodes = MatrixRecycleNode.objects(
                instance_id=recycle_instance.id
            ).order_by('level', 'position')
            
            tree_data = {
                "user_id": user_id,
                "slot_no": slot_no,
                "recycle_no": recycle_no,
                "is_complete": recycle_instance.is_complete,
                "total_members": recycle_instance.total_members,
                "created_at": recycle_instance.created_at,
                "completed_at": recycle_instance.completed_at,
                "nodes": []
            }
            
            for node in recycle_nodes:
                node_info = {
                    "level": node.level,
                    "position": node.position,
                    "occupant_user_id": str(node.occupant_user_id),
                    "placed_at": node.placed_at
                }
                tree_data["nodes"].append(node_info)
            
            return {"success": True, "data": tree_data}
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get recycle tree: {str(e)}"}
    
    def process_manual_recycle_trigger(self, user_id: str, slot_no: int) -> Dict[str, Any]:
        """
        Manually trigger recycle process (for testing purposes).
        """
        try:
            # Get user's matrix tree
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return {"success": False, "error": "Matrix tree not found"}
            
            # Check current member count
            if matrix_tree.total_members < self.max_matrix_members:
                return {
                    "success": False,
                    "error": f"Tree not ready for recycle. Current: {matrix_tree.total_members}, Required: {self.max_matrix_members}"
                }
            
            # Trigger recycle process
            return self._trigger_recycle_process(user_id, slot_no, matrix_tree)
            
        except Exception as e:
            return {"success": False, "error": f"Manual recycle trigger failed: {str(e)}"}
