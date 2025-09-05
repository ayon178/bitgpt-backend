from typing import List, Optional, Dict, Any
from bson import ObjectId
from decimal import Decimal
from datetime import datetime
from ..user.model import User
from ..tree.model import TreePlacement
from .model import (
    MatrixTree, MatrixActivation, MatrixRecycle, 
    MatrixAutoUpgrade, MatrixCommission, MatrixUplineReserve,
    MatrixSlotInfo, MatrixPosition
)

class MatrixService:
    """Matrix Program Business Logic Service"""
    
    # Matrix slot configuration
    MATRIX_SLOTS = {
        1: {'name': 'STARTER', 'value': Decimal('11.0'), 'members': 3},
        2: {'name': 'BRONZE', 'value': Decimal('33.0'), 'members': 9},
        3: {'name': 'SILVER', 'value': Decimal('99.0'), 'members': 27},
        4: {'name': 'GOLD', 'value': Decimal('297.0'), 'members': 81},
        5: {'name': 'PLATINUM', 'value': Decimal('891.0'), 'members': 243}
    }
    
    COMMISSION_PERCENTAGE = 10.0  # 10% commission
    
    def __init__(self):
        pass
    
    def join_matrix(self, user_id: str, referrer_id: str, tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        """Join Matrix program with $11 USDT"""
        try:
            # Validate user and referrer
            user = User.objects(id=ObjectId(user_id)).first()
            referrer = User.objects(id=ObjectId(referrer_id)).first()
            
            if not user or not referrer:
                raise ValueError("User or referrer not found")
            
            # Check if user already joined Matrix
            existing_matrix = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if existing_matrix:
                raise ValueError("User already joined Matrix program")
            
            # Validate amount
            if amount != Decimal('11.0'):
                raise ValueError("Matrix joining fee must be $11 USDT")
            
            # Create Matrix tree entry
            matrix_tree = self._create_matrix_tree(user_id, referrer_id)
            
            # Create activation record
            activation = self._create_matrix_activation(
                user_id, 1, 'STARTER', 'initial', amount, tx_hash
            )
            
            # Update user's Matrix status
            user.matrix_joined = True
            user.save()
            
            # Process commission for referrer
            self._process_joining_commission(referrer_id, user_id, amount)
            
            return {
                "success": True,
                "matrix_tree_id": str(matrix_tree.id),
                "activation_id": str(activation.id),
                "message": "Successfully joined Matrix program"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def upgrade_matrix_slot(self, user_id: str, slot_no: int, tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        """Upgrade Matrix slot"""
        try:
            # Validate user and Matrix tree
            user = User.objects(id=ObjectId(user_id)).first()
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            
            if not user or not matrix_tree:
                raise ValueError("User or Matrix tree not found")
            
            # Validate slot upgrade
            if slot_no <= matrix_tree.current_slot or slot_no > 5:
                raise ValueError("Invalid slot upgrade")
            
            # Validate amount
            expected_amount = self.MATRIX_SLOTS[slot_no]['value']
            if amount != expected_amount:
                raise ValueError(f"Upgrade amount must be ${expected_amount} USDT")
            
            # Create activation record
            activation = self._create_matrix_activation(
                user_id, slot_no, self.MATRIX_SLOTS[slot_no]['name'], 
                'upgrade', amount, tx_hash
            )
            
            # Update Matrix tree
            self._update_matrix_tree(matrix_tree, slot_no)
            
            # Process commission for upline
            self._process_upgrade_commission(user_id, slot_no, amount)
            
            # Check for auto upgrade eligibility
            self._check_auto_upgrade_eligibility(user_id)
            
            return {
                "success": True,
                "activation_id": str(activation.id),
                "new_slot": self.MATRIX_SLOTS[slot_no]['name'],
                "message": f"Successfully upgraded to {self.MATRIX_SLOTS[slot_no]['name']}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_auto_upgrade(self, user_id: str, from_slot: int, to_slot: int) -> Dict[str, Any]:
        """Process Matrix auto upgrade using middle 3 members earnings"""
        try:
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                raise ValueError("Matrix tree not found")
            
            # Calculate earnings from middle 3 members
            middle_three_earnings = self._calculate_middle_three_earnings(user_id, from_slot)
            
            if middle_three_earnings <= 0:
                raise ValueError("Insufficient earnings for auto upgrade")
            
            # Calculate upgrade cost
            upgrade_cost = self.MATRIX_SLOTS[to_slot]['value']
            
            if middle_three_earnings < upgrade_cost:
                raise ValueError("Insufficient earnings for auto upgrade")
            
            # Create auto upgrade record
            auto_upgrade = MatrixAutoUpgrade(
                user_id=ObjectId(user_id),
                from_slot=from_slot,
                to_slot=to_slot,
                upgrade_cost=upgrade_cost,
                earnings_from_middle_three=middle_three_earnings,
                status='completed',
                completed_at=datetime.utcnow()
            )
            auto_upgrade.save()
            
            # Update Matrix tree
            self._update_matrix_tree(matrix_tree, to_slot)
            
            # Create activation record for auto upgrade
            activation = self._create_matrix_activation(
                user_id, to_slot, self.MATRIX_SLOTS[to_slot]['name'],
                'auto', upgrade_cost, f"AUTO_{auto_upgrade.id}"
            )
            
            return {
                "success": True,
                "auto_upgrade_id": str(auto_upgrade.id),
                "activation_id": str(activation.id),
                "earnings_used": float(middle_three_earnings),
                "message": f"Auto upgrade to {self.MATRIX_SLOTS[to_slot]['name']} completed"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_recycle(self, user_id: str, matrix_level: int, recycle_position: str) -> Dict[str, Any]:
        """Process Matrix recycle system"""
        try:
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                raise ValueError("Matrix tree not found")
            
            # Calculate recycle amount
            recycle_amount = self._calculate_recycle_amount(matrix_level)
            
            # Create recycle record
            recycle = MatrixRecycle(
                user_id=ObjectId(user_id),
                matrix_level=matrix_level,
                recycle_position=recycle_position,
                recycle_amount=recycle_amount,
                original_slot=self.MATRIX_SLOTS[matrix_tree.current_slot]['name'],
                recycle_reason='matrix_completion',
                is_processed=True,
                processed_at=datetime.utcnow()
            )
            recycle.save()
            
            # Find new parent for recycle
            new_parent = self._find_recycle_parent(user_id, recycle_position)
            if new_parent:
                recycle.new_parent_id = ObjectId(new_parent)
                recycle.new_position = recycle_position
                recycle.save()
            
            return {
                "success": True,
                "recycle_id": str(recycle.id),
                "recycle_amount": float(recycle_amount),
                "new_parent": new_parent,
                "message": "Matrix recycle processed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_matrix_tree_structure(self, user_id: str) -> Dict[str, Any]:
        """Get complete Matrix tree structure"""
        try:
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                raise ValueError("Matrix tree not found")
            
            # Get children
            children = MatrixTree.objects(parent_id=ObjectId(user_id)).all()
            
            # Get team statistics
            team_stats = self._calculate_team_statistics(user_id)
            
            return {
                "success": True,
                "data": {
                    "matrix_tree": {
                        "user_id": str(matrix_tree.user_id),
                        "current_slot": matrix_tree.current_slot,
                        "current_level": matrix_tree.current_level,
                        "positions": [
                            {
                                "position": pos.position,
                                "is_active": pos.is_active,
                                "is_upline_reserve": pos.is_upline_reserve,
                                "user_id": str(pos.user_id) if pos.user_id else None
                            } for pos in matrix_tree.positions
                        ],
                        "matrix_slots": [
                            {
                                "slot_name": slot.slot_name,
                                "slot_value": float(slot.slot_value),
                                "level": slot.level,
                                "is_active": slot.is_active,
                                "member_count": slot.member_count
                            } for slot in matrix_tree.matrix_slots
                        ],
                        "total_team_size": matrix_tree.total_team_size,
                        "auto_upgrade_enabled": matrix_tree.auto_upgrade_enabled,
                        "is_activated": matrix_tree.is_activated
                    },
                    "children": [
                        {
                            "user_id": str(child.user_id),
                            "current_slot": child.current_slot,
                            "current_level": child.current_level
                        } for child in children
                    ],
                    "team_stats": team_stats
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_matrix_tree(self, user_id: str, referrer_id: str) -> MatrixTree:
        """Create Matrix tree entry"""
        matrix_tree = MatrixTree(
            user_id=ObjectId(user_id),
            parent_id=ObjectId(referrer_id),
            current_slot=1,
            current_level=1,
            is_active=True,
            is_activated=False
        )
        
        # Initialize Matrix positions (left, center, right)
        matrix_tree.positions = [
            MatrixPosition(position='left', is_active=False),
            MatrixPosition(position='center', is_upline_reserve=True, is_active=False),
            MatrixPosition(position='right', is_active=False)
        ]
        
        # Initialize STARTER slot
        matrix_tree.matrix_slots = [
            MatrixSlotInfo(
                slot_name='STARTER',
                slot_value=Decimal('11.0'),
                level=1,
                is_active=True,
                member_count=3,
                activated_at=datetime.utcnow()
            )
        ]
        
        matrix_tree.save()
        return matrix_tree
    
    def _create_matrix_activation(self, user_id: str, slot_no: int, slot_name: str, 
                                activation_type: str, amount: Decimal, tx_hash: str) -> MatrixActivation:
        """Create Matrix activation record"""
        activation = MatrixActivation(
            user_id=ObjectId(user_id),
            slot_no=slot_no,
            slot_name=slot_name,
            activation_type=activation_type,
            amount_paid=amount,
            tx_hash=tx_hash,
            status='completed',
            activated_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        activation.save()
        return activation
    
    def _update_matrix_tree(self, matrix_tree: MatrixTree, new_slot: int):
        """Update Matrix tree with new slot"""
        matrix_tree.current_slot = new_slot
        matrix_tree.current_level = new_slot
        
        # Add new slot info
        new_slot_info = MatrixSlotInfo(
            slot_name=self.MATRIX_SLOTS[new_slot]['name'],
            slot_value=self.MATRIX_SLOTS[new_slot]['value'],
            level=new_slot,
            is_active=True,
            member_count=self.MATRIX_SLOTS[new_slot]['members'],
            activated_at=datetime.utcnow()
        )
        matrix_tree.matrix_slots.append(new_slot_info)
        matrix_tree.save()
    
    def _process_joining_commission(self, referrer_id: str, user_id: str, amount: Decimal):
        """Process 10% commission for referrer on joining"""
        commission_amount = amount * Decimal(str(self.COMMISSION_PERCENTAGE / 100))
        
        commission = MatrixCommission(
            user_id=ObjectId(referrer_id),
            from_user_id=ObjectId(user_id),
            slot_no=1,
            slot_name='STARTER',
            commission_amount=commission_amount,
            commission_type='joining',
            commission_percentage=self.COMMISSION_PERCENTAGE,
            status='paid',
            paid_at=datetime.utcnow()
        )
        commission.save()
    
    def _process_upgrade_commission(self, user_id: str, slot_no: int, amount: Decimal):
        """Process 10% commission for upline on upgrade"""
        # Get upline
        matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
        if not matrix_tree:
            return
        
        upline_id = matrix_tree.parent_id
        commission_amount = amount * Decimal(str(self.COMMISSION_PERCENTAGE / 100))
        
        commission = MatrixCommission(
            user_id=upline_id,
            from_user_id=ObjectId(user_id),
            slot_no=slot_no,
            slot_name=self.MATRIX_SLOTS[slot_no]['name'],
            commission_amount=commission_amount,
            commission_type='upgrade',
            commission_percentage=self.COMMISSION_PERCENTAGE,
            status='paid',
            paid_at=datetime.utcnow()
        )
        commission.save()
    
    def _calculate_middle_three_earnings(self, user_id: str, slot_level: int) -> Decimal:
        """Calculate earnings from middle 3 members for auto upgrade"""
        # This is a simplified calculation
        # In real implementation, you would calculate based on actual earnings
        base_earning = self.MATRIX_SLOTS[slot_level]['value'] * Decimal('0.1')  # 10% of slot value
        return base_earning * 3  # 3 members
    
    def _check_auto_upgrade_eligibility(self, user_id: str):
        """Check if user is eligible for auto upgrade"""
        matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
        if not matrix_tree:
            return
        
        # Check if user has enough earnings for next slot
        if matrix_tree.current_slot < 5:
            next_slot = matrix_tree.current_slot + 1
            earnings = self._calculate_middle_three_earnings(user_id, matrix_tree.current_slot)
            upgrade_cost = self.MATRIX_SLOTS[next_slot]['value']
            
            if earnings >= upgrade_cost:
                matrix_tree.auto_upgrade_ready = True
                matrix_tree.save()
    
    def _calculate_recycle_amount(self, matrix_level: int) -> Decimal:
        """Calculate recycle amount based on matrix level"""
        # Simplified calculation
        return self.MATRIX_SLOTS[matrix_level]['value'] * Decimal('0.5')  # 50% of slot value
    
    def _find_recycle_parent(self, user_id: str, recycle_position: str) -> Optional[str]:
        """Find new parent for recycle placement"""
        # Simplified implementation
        # In real implementation, you would find the next available position
        return None
    
    def _calculate_team_statistics(self, user_id: str) -> Dict[str, Any]:
        """Calculate team statistics"""
        # Get direct children count
        direct_children = MatrixTree.objects(parent_id=ObjectId(user_id)).count()
        
        # Get total team size (recursive)
        total_team = self._calculate_total_team_size(user_id)
        
        return {
            "direct_children": direct_children,
            "total_team": total_team,
            "matrix_level": MatrixTree.objects(user_id=ObjectId(user_id)).first().current_level if MatrixTree.objects(user_id=ObjectId(user_id)).first() else 0
        }
    
    def _calculate_total_team_size(self, user_id: str) -> int:
        """Calculate total team size recursively"""
        children = MatrixTree.objects(parent_id=ObjectId(user_id)).all()
        total = len(children)
        
        for child in children:
            total += self._calculate_total_team_size(str(child.user_id))
        
        return total
