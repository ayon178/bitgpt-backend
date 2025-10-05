#!/usr/bin/env python3
"""
Matrix Sweepover Service
Handles the 60-level search mechanism for eligible upline placement
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
from .model import MatrixTree, MatrixNode, MatrixActivation


class SweepoverService:
    """Service for managing Matrix Sweepover Mechanism with 60-level search"""
    
    def __init__(self):
        self.max_escalation_depth = 60  # Maximum levels to search upward
        self.mother_id = "68dc17f08b174277bc40d19c"  # Mother ID fallback
    
    def process_sweepover_placement(self, user_id: str, slot_no: int, 
                                  referrer_id: str, tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        """
        Process sweepover placement with 60-level search for eligible upline.
        
        This is the main method that handles the complete sweepover logic:
        1. Check direct upline eligibility
        2. If not eligible, search up to 60 levels
        3. Place user in eligible upline's tree
        4. Handle missed income for skipped uplines
        """
        try:
            # Step 1: Check direct upline eligibility
            direct_upline = User.objects(id=ObjectId(referrer_id)).first()
            if not direct_upline:
                return {"success": False, "error": "Direct upline not found"}
            
            direct_eligible = self._is_upline_eligible(direct_upline.id, slot_no)
            
            if direct_eligible:
                # Normal placement under direct upline
                placement_result = self._place_user_in_tree(direct_upline.id, user_id, slot_no, tx_hash, amount)
                placement_result["placement_type"] = "direct"
                placement_result["tree_upline"] = str(direct_upline.id)
                return placement_result
            else:
                # Need to search for eligible upline up to 60 levels
                eligible_upline = self._find_eligible_upline(referrer_id, slot_no)
                
                if eligible_upline:
                    # Place in eligible upline's tree (sweepover)
                    placement_result = self._place_user_in_tree(eligible_upline["user_id"], user_id, slot_no, tx_hash, amount)
                    placement_result["placement_type"] = "sweepover"
                    placement_result["tree_upline"] = str(eligible_upline["user_id"])
                    placement_result["swept_over_uplines"] = eligible_upline["swept_over_count"]
                    
                    # Log missed income for skipped uplines
                    self._log_missed_income(referrer_id, eligible_upline["user_id"], slot_no, amount)
                    
                    return placement_result
                else:
                    # No eligible upline found within 60 levels, place in Mother ID's tree
                    placement_result = self._place_user_in_tree(self.mother_id, user_id, slot_no, tx_hash, amount)
                    placement_result["placement_type"] = "mother_fallback"
                    placement_result["tree_upline"] = self.mother_id
                    placement_result["swept_over_uplines"] = 60  # All 60 levels swept
                    
                    # Log missed income for all skipped uplines
                    self._log_missed_income(referrer_id, self.mother_id, slot_no, amount)
                    
                    return placement_result
                    
        except Exception as e:
            return {"success": False, "error": f"Sweepover placement failed: {str(e)}"}
    
    def _is_upline_eligible(self, upline_id: str, slot_no: int) -> bool:
        """
        Check if an upline is eligible to receive placement for a specific slot.
        Upline is eligible if they have the target slot active or any higher slot.
        """
        try:
            # Check if upline has the target slot active
            activation = SlotActivation.objects(
                user_id=ObjectId(upline_id),
                program='matrix',
                slot_no__lte=slot_no,  # Target slot or higher
                status='completed'
            ).order_by('-slot_no').first()
            
            return activation is not None
            
        except Exception as e:
            print(f"Error checking upline eligibility: {e}")
            return False
    
    def _find_eligible_upline(self, start_upline_id: str, slot_no: int) -> Optional[Dict[str, Any]]:
        """
        Search up to 60 levels for an eligible upline with target slot active.
        Returns the eligible upline information and count of swept-over levels.
        """
        try:
            current_upline_id = start_upline_id
            swept_over_count = 0
            
            for level in range(self.max_escalation_depth):
                # Get current upline's upline (go up one level)
                current_upline = User.objects(id=ObjectId(current_upline_id)).first()
                if not current_upline or not current_upline.refered_by:
                    break  # No more uplines to check
                
                # Move to next upline level
                current_upline_id = str(current_upline.refered_by)
                swept_over_count += 1
                
                # Check if this upline is eligible
                if self._is_upline_eligible(current_upline_id, slot_no):
                    # Check if this upline's matrix tree has space for the slot
                    if self._has_tree_space(current_upline_id, slot_no):
                        return {
                            "user_id": current_upline_id,
                            "level": level + 1,
                            "swept_over_count": swept_over_count,
                            "eligible_at_level": level + 1
                        }
            
            return None  # No eligible upline found within 60 levels
            
        except Exception as e:
            print(f"Error finding eligible upline: {e}")
            return None
    
    def _has_tree_space(self, upline_id: str, slot_no: int) -> bool:
        """
        Check if an upline's matrix tree has space for a new user in the specified slot.
        """
        try:
            # Get upline's matrix tree for the slot
            matrix_tree = MatrixTree.objects(user_id=ObjectId(upline_id)).first()
            if not matrix_tree:
                return True  # No tree exists, can create one
            
            # Check if tree is complete (39 members for matrix)
            return not matrix_tree.is_complete
            
        except Exception as e:
            print(f"Error checking tree space: {e}")
            return False
    
    def _place_user_in_tree(self, tree_upline_id: str, user_id: str, slot_no: int, 
                          tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        """
        Place user in the specified upline's matrix tree using BFS placement algorithm.
        """
        try:
            # Get or create matrix tree for the upline
            matrix_tree = MatrixTree.objects(user_id=ObjectId(tree_upline_id)).first()
            if not matrix_tree:
                matrix_tree = self._create_matrix_tree_for_slot(tree_upline_id, slot_no)
            
            # Find available position using BFS algorithm
            placement_position = self._find_bfs_placement_position(matrix_tree)
            if not placement_position:
                return {"success": False, "error": "No available position in tree"}
            
            # Create matrix node for the user
            matrix_node = MatrixNode(
                level=placement_position["level"],
                position=placement_position["position"],
                user_id=ObjectId(user_id),
                placed_at=datetime.utcnow(),
                is_active=True
            )
            
            # Add node to tree
            matrix_tree.nodes.append(matrix_node)
            
            # Update tree statistics
            self._update_tree_statistics(matrix_tree, placement_position["level"])
            
            # Check if tree is now complete (39 members)
            if matrix_tree.total_members >= 39:
                matrix_tree.is_complete = True
                # Trigger recycle process
                self._trigger_recycle_process(matrix_tree, user_id, slot_no, tx_hash, amount)
            
            matrix_tree.updated_at = datetime.utcnow()
            matrix_tree.save()
            
            # Create matrix activation record
            self._create_matrix_activation(user_id, slot_no, tx_hash, amount, tree_upline_id)
            
            # Distribute level income
            self._distribute_level_income(tree_upline_id, user_id, slot_no, amount, placement_position)
            
            return {
                "success": True,
                "message": f"User placed in level {placement_position['level']}, position {placement_position['position']}",
                "placement_level": placement_position["level"],
                "placement_position": placement_position["position"],
                "tree_upline_id": tree_upline_id,
                "tree_complete": matrix_tree.is_complete
            }
            
        except Exception as e:
            return {"success": False, "error": f"Tree placement failed: {str(e)}"}
    
    def _find_bfs_placement_position(self, matrix_tree: MatrixTree) -> Optional[Dict[str, int]]:
        """
        Find available position using Breadth-First Search algorithm.
        Matrix structure: Level 1 (3 positions), Level 2 (9 positions), Level 3 (27 positions)
        """
        try:
            # Level 1: 3 positions (0, 1, 2)
            level_1_positions = [0, 1, 2]
            for pos in level_1_positions:
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
    
    def _create_matrix_tree_for_slot(self, upline_id: str, slot_no: int) -> MatrixTree:
        """Create a new matrix tree for an upline and slot."""
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
    
    def _update_tree_statistics(self, matrix_tree: MatrixTree, level: int):
        """Update matrix tree statistics after adding a new member."""
        matrix_tree.total_members += 1
        
        if level == 1:
            matrix_tree.level_1_members += 1
        elif level == 2:
            matrix_tree.level_2_members += 1
        elif level == 3:
            matrix_tree.level_3_members += 1
    
    def _trigger_recycle_process(self, matrix_tree: MatrixTree, triggering_user_id: str, 
                               slot_no: int, tx_hash: str, amount: Decimal):
        """Trigger recycle process when matrix tree reaches 39 members."""
        try:
            # Create recycle instance
            from .model import MatrixRecycleInstance, MatrixRecycleNode
            
            recycle_instance = MatrixRecycleInstance(
                user_id=matrix_tree.user_id,
                slot_number=slot_no,
                recycle_no=self._get_next_recycle_number(matrix_tree.user_id, slot_no),
                is_complete=True,
                completed_at=datetime.utcnow()
            )
            recycle_instance.save()
            
            # Create recycle nodes snapshot
            for node in matrix_tree.nodes:
                recycle_node = MatrixRecycleNode(
                    instance_id=recycle_instance.id,
                    occupant_user_id=node.user_id,
                    level_index=node.level,
                    position_index=node.position,
                    placed_at=node.placed_at
                )
                recycle_node.save()
            
            # Create new in-progress tree
            self._create_matrix_tree_for_slot(str(matrix_tree.user_id), slot_no)
            
            # Log recycle completion
            print(f"Matrix recycle completed for user {matrix_tree.user_id}, slot {slot_no}")
            
        except Exception as e:
            print(f"Error triggering recycle process: {e}")
    
    def _get_next_recycle_number(self, user_id: ObjectId, slot_no: int) -> int:
        """Get the next recycle number for a user and slot."""
        from .model import MatrixRecycleInstance
        
        last_recycle = MatrixRecycleInstance.objects(
            user_id=user_id,
            slot_number=slot_no
        ).order_by('-recycle_no').first()
        
        return (last_recycle.recycle_no + 1) if last_recycle else 1
    
    def _create_matrix_activation(self, user_id: str, slot_no: int, tx_hash: str, 
                                amount: Decimal, tree_upline_id: str):
        """Create matrix activation record for the user."""
        try:
            # Get slot catalog information
            catalog = SlotCatalog.objects(
                program='matrix',
                slot_no=slot_no,
                is_active=True
            ).first()
            
            if catalog:
                activation = MatrixActivation(
                    user_id=ObjectId(user_id),
                    program='matrix',
                    slot_no=slot_no,
                    slot_name=catalog.name,
                    activation_type='join',
                    upgrade_source='sweepover',
                    amount_paid=amount,
                    currency='USDT',
                    tx_hash=tx_hash,
                    is_auto_upgrade=False,
                    status='completed'
                )
                activation.save()
                
        except Exception as e:
            print(f"Error creating matrix activation: {e}")
    
    def _distribute_level_income(self, tree_upline_id: str, user_id: str, slot_no: int, 
                               amount: Decimal, placement_position: Dict[str, int]):
        """
        Distribute level income according to Matrix rules: 20% / 20% / 60%
        """
        try:
            # Calculate income distribution
            level_1_amount = amount * Decimal('0.20')  # 20%
            level_2_amount = amount * Decimal('0.20')  # 20%
            level_3_amount = amount * Decimal('0.60')  # 60%
            
            # Find the three upline levels for income distribution
            upline_levels = self._get_upline_levels_for_income(tree_upline_id, placement_position["level"])
            
            # Distribute to Level 1 upline (20%)
            if upline_levels.get("level_1"):
                self._create_income_event(
                    upline_levels["level_1"], user_id, slot_no, level_1_amount, "level_1_income"
                )
            
            # Distribute to Level 2 upline (20%)
            if upline_levels.get("level_2"):
                self._create_income_event(
                    upline_levels["level_2"], user_id, slot_no, level_2_amount, "level_2_income"
                )
            
            # Distribute to Level 3 upline (60%)
            if upline_levels.get("level_3"):
                self._create_income_event(
                    upline_levels["level_3"], user_id, slot_no, level_3_amount, "level_3_income"
                )
                
        except Exception as e:
            print(f"Error distributing level income: {e}")
    
    def _get_upline_levels_for_income(self, tree_upline_id: str, user_level: int) -> Dict[str, str]:
        """
        Get the three upline levels for income distribution based on user's placement level.
        """
        try:
            upline_levels = {}
            
            # For Matrix, income distribution is relative to the placed position
            # Level 1 upline is the tree upline (who owns the tree)
            upline_levels["level_1"] = tree_upline_id
            
            # Level 2 and 3 uplines are the ancestors of the tree upline
            tree_upline = User.objects(id=ObjectId(tree_upline_id)).first()
            if tree_upline and tree_upline.refered_by:
                upline_levels["level_2"] = str(tree_upline.refered_by)
                
                # Level 3 upline
                level_2_upline = User.objects(id=tree_upline.refered_by).first()
                if level_2_upline and level_2_upline.refered_by:
                    upline_levels["level_3"] = str(level_2_upline.refered_by)
            
            return upline_levels
            
        except Exception as e:
            print(f"Error getting upline levels for income: {e}")
            return {}
    
    def _create_income_event(self, recipient_id: str, source_user_id: str, slot_no: int, 
                           amount: Decimal, income_type: str):
        """Create income event for level distribution."""
        try:
            income_event = IncomeEvent(
                user_id=ObjectId(recipient_id),
                source_user_id=ObjectId(source_user_id),
                program='matrix',
                slot_no=slot_no,
                income_type=income_type,
                amount=amount,
                percentage=Decimal('100.0'),
                tx_hash=f"SWEEPOVER-{source_user_id}-S{slot_no}",
                status='completed'
            )
            income_event.save()
            
        except Exception as e:
            print(f"Error creating income event: {e}")
    
    def _log_missed_income(self, direct_upline_id: str, eligible_upline_id: str, 
                         slot_no: int, amount: Decimal):
        """
        Log missed income for uplines who were skipped during sweepover.
        This income goes to Leadership Stipend for distribution to eligible members.
        """
        try:
            # Calculate missed income (would have been 20% for Level 1)
            missed_amount = amount * Decimal('0.20')
            
            # Create missed income record
            IncomeEvent(
                user_id=ObjectId("000000000000000000000000"),  # System/Missed income
                source_user_id=ObjectId(direct_upline_id),
                program='matrix',
                slot_no=slot_no,
                income_type='missed_income',
                amount=missed_amount,
                percentage=Decimal('20.0'),
                tx_hash=f"MISSED-{direct_upline_id}-S{slot_no}",
                status='missed',
                notes=f"Missed income due to sweepover to {eligible_upline_id}"
            ).save()
            
            print(f"Logged missed income: {missed_amount} for upline {direct_upline_id} on slot {slot_no}")
            
        except Exception as e:
            print(f"Error logging missed income: {e}")
    
    def get_sweepover_status(self, user_id: str, slot_no: int) -> Dict[str, Any]:
        """Get comprehensive sweepover status for a user and slot."""
        try:
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"error": "User not found"}
            
            status = {
                "user_id": user_id,
                "slot_no": slot_no,
                "direct_upline": str(user.refered_by) if user.refered_by else None,
                "direct_upline_eligible": False,
                "eligible_upline_found": False,
                "sweepover_required": False,
                "placement_type": "unknown"
            }
            
            # Check direct upline eligibility
            if user.refered_by:
                direct_eligible = self._is_upline_eligible(str(user.refered_by), slot_no)
                status["direct_upline_eligible"] = direct_eligible
                
                if not direct_eligible:
                    # Check for eligible upline via sweepover
                    eligible_upline = self._find_eligible_upline(str(user.refered_by), slot_no)
                    status["eligible_upline_found"] = eligible_upline is not None
                    status["sweepover_required"] = True
                    
                    if eligible_upline:
                        status["placement_type"] = "sweepover"
                        status["eligible_upline_id"] = eligible_upline["user_id"]
                        status["swept_over_levels"] = eligible_upline["swept_over_count"]
                    else:
                        status["placement_type"] = "mother_fallback"
                        status["swept_over_levels"] = 60
                else:
                    status["placement_type"] = "direct"
            
            return status
            
        except Exception as e:
            return {"error": f"Error getting sweepover status: {str(e)}"}
    
    def check_future_restoration(self, user_id: str, slot_no: int) -> Dict[str, Any]:
        """
        Check if normal distribution can be restored if skipped upline upgrades.
        """
        try:
            user = User.objects(id=ObjectId(user_id)).first()
            if not user or not user.refered_by:
                return {"restoration_possible": False}
            
            direct_upline_id = str(user.refered_by)
            
            # Check if direct upline now has the slot active
            if self._is_upline_eligible(direct_upline_id, slot_no):
                return {
                    "restoration_possible": True,
                    "message": "Direct upline now eligible for normal placement",
                    "upline_id": direct_upline_id,
                    "slot_no": slot_no
                }
            
            return {"restoration_possible": False}
            
        except Exception as e:
            return {"error": f"Error checking future restoration: {str(e)}"}
