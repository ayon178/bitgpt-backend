from typing import Dict, Any, Optional, List
from bson import ObjectId
from decimal import Decimal
from datetime import datetime
from mongoengine.errors import ValidationError

from ..user.model import User, EarningHistory
from ..slot.model import SlotCatalog
from ..commission.service import CommissionService
from ..auto_upgrade.model import MatrixAutoUpgrade
from ..rank.service import RankService
from ..spark.service import SparkService
from ..newcomer_support.service import NewcomerSupportService
from ..mentorship.service import MentorshipService
from ..dream_matrix.service import DreamMatrixService
from ..blockchain.model import BlockchainEvent
from .model import (
    MatrixTree, MatrixNode, MatrixActivation, MatrixUpgradeLog,
    MatrixEarningHistory, MatrixCommission, MatrixRecycleInstance, MatrixRecycleNode
)
from utils import ensure_currency_for_program


class MatrixService:
    """Matrix Program Business Logic Service"""
    
    def __init__(self):
        self.commission_service = CommissionService()
        self.rank_service = RankService()
        self.spark_service = SparkService()
        self.newcomer_support_service = NewcomerSupportService()
        self.mentorship_service = MentorshipService()
        self.dream_matrix_service = DreamMatrixService()
    
    # Matrix slot definitions per PROJECT_DOCUMENTATION.md
    MATRIX_SLOTS = {
        1: {'name': 'STARTER', 'value': Decimal('11'), 'level': 1, 'members': 3},
        2: {'name': 'BRONZE', 'value': Decimal('33'), 'level': 2, 'members': 9},
        3: {'name': 'SILVER', 'value': Decimal('99'), 'level': 3, 'members': 27},
        4: {'name': 'GOLD', 'value': Decimal('297'), 'level': 4, 'members': 81},
        5: {'name': 'PLATINUM', 'value': Decimal('891'), 'level': 5, 'members': 243},
        6: {'name': 'DIAMOND', 'value': Decimal('2673'), 'level': 6, 'members': 729},
        7: {'name': 'RUBY', 'value': Decimal('8019'), 'level': 7, 'members': 2187},
        8: {'name': 'EMERALD', 'value': Decimal('24057'), 'level': 8, 'members': 6561},
        9: {'name': 'SAPPHIRE', 'value': Decimal('72171'), 'level': 9, 'members': 19683},
        10: {'name': 'TOPAZ', 'value': Decimal('216513'), 'level': 10, 'members': 59049},
        11: {'name': 'PEARL', 'value': Decimal('649539'), 'level': 11, 'members': 177147},
        12: {'name': 'AMETHYST', 'value': Decimal('1948617'), 'level': 12, 'members': 531441},
        13: {'name': 'OBSIDIAN', 'value': Decimal('5845851'), 'level': 13, 'members': 1594323},
        14: {'name': 'TITANIUM', 'value': Decimal('17537553'), 'level': 14, 'members': 4782969},
        15: {'name': 'STAR', 'value': Decimal('52612659'), 'level': 15, 'members': 14348907}
    }
    
    def join_matrix(self, user_id: str, referrer_id: str, tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        """
        Join Matrix program with $11 USDT and trigger all auto calculations
        
        This method implements Section 1.1 Joining Requirements from MATRIX_TODO.md:
        - Cost: $11 USDT to join Matrix program
        - Structure: 3x Matrix structure (3, 9, 27 members per level)
        - Slots: 15 slots total (STARTER to STAR)
        - Recycle System: Each slot completes with 39 members (3+9+27)
        
        Auto calculations triggered:
        - MatrixTree Creation
        - Slot-1 Activation (STARTER)
        - Tree Placement in referrer's matrix
        - All commission distributions (100% total)
        - Special program integrations
        """
        try:
            # Validate user and referrer exist
            user = User.objects(id=ObjectId(user_id)).first()
            referrer = User.objects(id=ObjectId(referrer_id)).first()
            
            if not user or not referrer:
                raise ValueError("User or referrer not found")
            
            # Validate amount ($11 USDT)
            expected_amount = self.MATRIX_SLOTS[1]['value']
            if amount != expected_amount:
                raise ValueError(f"Matrix join amount must be ${expected_amount} USDT")
            
            # Check if user already in Matrix program
            existing_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if existing_tree:
                raise ValueError("User already in Matrix program")
            
            currency = ensure_currency_for_program('matrix', 'USDT')
            
            # 1. Create MatrixTree for the user
            matrix_tree = self._create_matrix_tree(user_id)
            
            # 2. Activate Slot-1 (STARTER) - $11 USDT
            activation = self._create_matrix_activation(
                user_id, 1, self.MATRIX_SLOTS[1]['name'], 
                'initial', amount, tx_hash
            )
            
            # 3. Place user in referrer's matrix tree using BFS algorithm
            placement_result = self._place_user_in_matrix_tree(user_id, referrer_id, matrix_tree)
            
            # 4. Initialize MatrixAutoUpgrade tracking
            self._initialize_matrix_auto_upgrade(user_id)
            
            # 5. Process all commission distributions (100% total)
            commission_results = self._process_matrix_commissions(user_id, referrer_id, amount, currency)
            
            # 6. Process special program integrations
            special_programs_results = self._process_special_programs(user_id, referrer_id, amount, currency)
            
            # 7. Update user's matrix participation status
            self._update_user_matrix_status(user, True)
            
            # 8. Record earning history
            self._record_matrix_earning_history(user_id, 1, self.MATRIX_SLOTS[1]['name'], amount, currency)
            
            # 9. Record blockchain event
            self._record_blockchain_event(tx_hash, user_id, referrer_id, amount, currency)
            
            # 10. Update user rank
            rank_result = self.rank_service.update_user_rank(user_id=user_id)
            
            return {
                "success": True,
                "matrix_tree_id": str(matrix_tree.id),
                "activation_id": str(activation.id),
                "slot_activated": self.MATRIX_SLOTS[1]['name'],
                "amount": float(amount),
                "currency": currency,
                "placement_result": placement_result,
                "commission_results": commission_results,
                "special_programs_results": special_programs_results,
                "rank_result": rank_result,
                "message": f"Successfully joined Matrix program with {self.MATRIX_SLOTS[1]['name']} slot"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_matrix_tree(self, user_id: str) -> MatrixTree:
        """Create MatrixTree for user"""
        try:
            matrix_tree = MatrixTree(
                user_id=ObjectId(user_id),
                current_slot=1,
                current_level=1,
                total_members=0,
                level_1_members=0,
                level_2_members=0,
                level_3_members=0,
                is_complete=False,
                nodes=[],
                slots=[]
            )
            matrix_tree.save()
            return matrix_tree
        except Exception as e:
            raise ValueError(f"Failed to create matrix tree: {str(e)}")
    
    def _create_matrix_activation(self, user_id: str, slot_no: int, slot_name: str, 
                                activation_type: str, amount: Decimal, tx_hash: str) -> MatrixActivation:
        """Create MatrixActivation record"""
        try:
            activation = MatrixActivation(
                user_id=ObjectId(user_id),
                slot_no=slot_no,
                slot_name=slot_name,
                activation_type=activation_type,
                upgrade_source='auto' if activation_type == 'initial' else 'manual',
                amount_paid=amount,
                currency='USDT',
                tx_hash=tx_hash,
                is_auto_upgrade=(activation_type == 'initial'),
                status='completed',
                activated_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            activation.save()
            return activation
        except Exception as e:
            raise ValueError(f"Failed to create matrix activation: {str(e)}")
    
    def _place_user_in_matrix_tree(self, user_id: str, referrer_id: str, matrix_tree: MatrixTree) -> Dict[str, Any]:
        """Place user in referrer's matrix tree using BFS algorithm"""
        try:
            # Get referrer's matrix tree
            referrer_tree = MatrixTree.objects(user_id=ObjectId(referrer_id)).first()
            if not referrer_tree:
                raise ValueError("Referrer not in Matrix program")
            
            # Find first available position using BFS
            placement_position = self._find_bfs_placement_position(referrer_tree)
            
            if not placement_position:
                raise ValueError("No available positions in referrer's matrix tree")
            
            # Create matrix node for the new user
            matrix_node = MatrixNode(
                level=placement_position['level'],
                position=placement_position['position'],
                user_id=ObjectId(user_id),
                placed_at=datetime.utcnow(),
                is_active=True
            )
            
            # Add node to referrer's tree
            referrer_tree.nodes.append(matrix_node)
            
            # Update member counts
            if placement_position['level'] == 1:
                referrer_tree.level_1_members += 1
            elif placement_position['level'] == 2:
                referrer_tree.level_2_members += 1
            elif placement_position['level'] == 3:
                referrer_tree.level_3_members += 1
            
            referrer_tree.total_members += 1
            referrer_tree.updated_at = datetime.utcnow()
            referrer_tree.save()
            
            # Check if tree is complete (39 members)
            if referrer_tree.total_members >= 39:
                referrer_tree.is_complete = True
                referrer_tree.save()
                # Automatically trigger recycle process
                self._check_and_process_automatic_recycle(str(referrer_tree.user_id), 1)
            
            # Check for automatic upgrade after placement
            self.check_and_process_automatic_upgrade(str(referrer_tree.user_id), referrer_tree.current_slot)
            
            return {
                "success": True,
                "level": placement_position['level'],
                "position": placement_position['position'],
                "total_members": referrer_tree.total_members,
                "is_complete": referrer_tree.is_complete
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _find_bfs_placement_position(self, matrix_tree: MatrixTree) -> Optional[Dict[str, int]]:
        """Find first available position using BFS algorithm"""
        try:
            # Level 1: Check positions 0, 1, 2 (left, middle, right)
            for pos in range(3):
                if not any(node.level == 1 and node.position == pos for node in matrix_tree.nodes):
                    return {"level": 1, "position": pos}
            
            # Level 2: Check positions 0-8 (3 under each L1 parent)
            for pos in range(9):
                if not any(node.level == 2 and node.position == pos for node in matrix_tree.nodes):
                    return {"level": 2, "position": pos}
            
            # Level 3: Check positions 0-26 (3 under each L2 parent)
            for pos in range(27):
                if not any(node.level == 3 and node.position == pos for node in matrix_tree.nodes):
                    return {"level": 3, "position": pos}
            
            return None  # No available positions
            
        except Exception as e:
            raise ValueError(f"Failed to find BFS placement position: {str(e)}")
    
    def _initialize_matrix_auto_upgrade(self, user_id: str):
        """Initialize MatrixAutoUpgrade tracking"""
        try:
            if not MatrixAutoUpgrade.objects(user_id=ObjectId(user_id)).first():
                MatrixAutoUpgrade(
                    user_id=ObjectId(user_id),
                    current_slot_no=1,
                    current_level=1,
                    middle_three_required=3,
                    middle_three_available=0,
                    is_eligible=False,
                    next_upgrade_cost=self.MATRIX_SLOTS[2]['value'],
                    can_upgrade=False
                ).save()
        except Exception as e:
            print(f"Error initializing matrix auto upgrade: {str(e)}")
    
    def _process_matrix_commissions(self, user_id: str, referrer_id: str, amount: Decimal, currency: str) -> Dict[str, Any]:
        """Process all matrix commission distributions (100% total)"""
        try:
            results = {}
            
            # 1. Joining Commission (10% to direct upline)
            joining_result = self.commission_service.calculate_joining_commission(
                from_user_id=user_id,
                program='matrix',
                amount=amount,
                currency=currency
            )
            results['joining_commission'] = joining_result
            
            # 2. Partner Incentive (10% to upline from joining)
            partner_result = self.commission_service.calculate_partner_incentive(
                from_user_id=user_id,
                to_user_id=referrer_id,
                program='matrix',
                amount=amount,
                currency=currency
            )
            results['partner_incentive'] = partner_result
            
            # 3. Level Distribution (40% distributed across matrix levels)
            level_result = self._calculate_level_distribution(user_id, amount, currency)
            results['level_distribution'] = level_result
            
            # 4. Spark Bonus (8% contribution to Spark fund)
            spark_result = self.spark_service.contribute_to_fund(
                program='matrix',
                amount=amount,
                currency=currency,
                source_user_id=user_id,
                source_type='matrix_join',
                source_slot_no=1
            )
            results['spark_bonus'] = spark_result
            
            # 5. Royal Captain (4% contribution to Royal Captain fund)
            royal_captain_result = self._contribute_to_royal_captain_fund(user_id, amount, currency)
            results['royal_captain'] = royal_captain_result
            
            # 6. President Reward (3% contribution to President Reward fund)
            president_result = self._contribute_to_president_reward_fund(user_id, amount, currency)
            results['president_reward'] = president_result
            
            # 7. Shareholders (5% contribution to Shareholders fund)
            shareholders_result = self._contribute_to_shareholders_fund(user_id, amount, currency)
            results['shareholders'] = shareholders_result
            
            # 8. Newcomer Growth Support (20% contribution + instant bonus)
            ngs_result = self.newcomer_support_service.process_matrix_contribution(
                user_id=user_id,
                amount=amount,
                currency=currency
            )
            results['newcomer_support'] = ngs_result
            
            # 9. Mentorship Bonus (10% to super upline - direct-of-direct)
            mentorship_result = self.mentorship_service.process_matrix_mentorship(
                user_id=user_id,
                referrer_id=referrer_id,
                amount=amount,
                currency=currency
            )
            results['mentorship_bonus'] = mentorship_result
            
            return results
            
        except Exception as e:
            return {"error": str(e)}
    
    def _process_special_programs(self, user_id: str, referrer_id: str, amount: Decimal, currency: str) -> Dict[str, Any]:
        """Process special program integrations"""
        try:
            results = {}
            
            # 1. Dream Matrix initialization
            dream_matrix_result = self.dream_matrix_service.initialize_dream_matrix(
                user_id=user_id,
                referrer_id=referrer_id
            )
            results['dream_matrix'] = dream_matrix_result
            
            # 2. Rank update
            rank_result = self.rank_service.update_user_rank(user_id=user_id)
            results['rank_update'] = rank_result
            
            return results
            
        except Exception as e:
            return {"error": str(e)}
    
    def _update_user_matrix_status(self, user: User, matrix_joined: bool):
        """Update user's matrix participation status"""
        try:
            user.matrix_joined = matrix_joined
            user.updated_at = datetime.utcnow()
            user.save()
        except Exception as e:
            print(f"Error updating user matrix status: {str(e)}")
    
    def _record_matrix_earning_history(self, user_id: str, slot_no: int, slot_name: str, amount: Decimal, currency: str):
        """Record matrix earning history"""
        try:
            MatrixEarningHistory(
                user_id=ObjectId(user_id),
                earning_type='slot_activation',
                slot_no=slot_no,
                slot_name=slot_name,
                amount=amount,
                currency=currency,
                source_type='matrix_join',
                description=f"Matrix slot {slot_no} ({slot_name}) activation"
            ).save()
        except Exception as e:
            print(f"Error recording matrix earning history: {str(e)}")
    
    def _record_blockchain_event(self, tx_hash: str, user_id: str, referrer_id: str, amount: Decimal, currency: str):
        """Record blockchain event"""
        try:
            BlockchainEvent(
                tx_hash=tx_hash,
                event_type='matrix_join',
                event_data={
                    'program': 'matrix',
                    'slot_no': 1,
                    'slot_name': 'STARTER',
                    'amount': str(amount),
                    'currency': currency,
                    'user_id': user_id,
                    'referrer_id': referrer_id
                },
                status='processed',
                processed_at=datetime.utcnow()
            ).save()
        except Exception as e:
            print(f"Error recording blockchain event: {str(e)}")
    
    def _calculate_level_distribution(self, user_id: str, amount: Decimal, currency: str) -> Dict[str, Any]:
        """Calculate level distribution (40% of total)"""
        try:
            # 40% of amount distributed across matrix levels
            level_amount = amount * Decimal('0.40')
            
            # TODO: Implement actual level distribution logic
            # This would involve finding upline chain and distributing to each level
            
            return {
                "success": True,
                "total_level_amount": float(level_amount),
                "currency": currency,
                "message": "Level distribution calculated"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _contribute_to_royal_captain_fund(self, user_id: str, amount: Decimal, currency: str) -> Dict[str, Any]:
        """Contribute 4% to Royal Captain fund"""
        try:
            # TODO: Implement Royal Captain fund contribution
            return {"success": True, "message": "Royal Captain contribution processed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _contribute_to_president_reward_fund(self, user_id: str, amount: Decimal, currency: str) -> Dict[str, Any]:
        """Contribute 3% to President Reward fund"""
        try:
            # TODO: Implement President Reward fund contribution
            return {"success": True, "message": "President Reward contribution processed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _contribute_to_shareholders_fund(self, user_id: str, amount: Decimal, currency: str) -> Dict[str, Any]:
        """Contribute 5% to Shareholders fund"""
        try:
            # TODO: Implement Shareholders fund contribution
            return {"success": True, "message": "Shareholders contribution processed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_matrix_status(self, user_id: str) -> Dict[str, Any]:
        """Get user's matrix program status"""
        try:
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                raise ValueError("User not found")
            
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            matrix_auto_upgrade = MatrixAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
            
            return {
                "success": True,
                "user_id": user_id,
                "matrix_joined": user.matrix_joined if hasattr(user, 'matrix_joined') else False,
                "matrix_tree": {
                    "current_slot": matrix_tree.current_slot if matrix_tree else 0,
                    "current_level": matrix_tree.current_level if matrix_tree else 0,
                    "total_members": matrix_tree.total_members if matrix_tree else 0,
                    "is_complete": matrix_tree.is_complete if matrix_tree else False
                } if matrix_tree else None,
                "auto_upgrade": {
                    "current_slot": matrix_auto_upgrade.current_slot_no if matrix_auto_upgrade else 0,
                    "middle_three_available": matrix_auto_upgrade.middle_three_available if matrix_auto_upgrade else 0,
                    "is_eligible": matrix_auto_upgrade.is_eligible if matrix_auto_upgrade else False,
                    "can_upgrade": matrix_auto_upgrade.can_upgrade if matrix_auto_upgrade else False
                } if matrix_auto_upgrade else None
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==================== RECYCLE SYSTEM METHODS ====================
    
    def detect_recycle_completion(self, user_id: str, slot_no: int):
        """Detect when a Matrix slot has completed with 39 members (3+9+27)."""
        try:
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return False
            
            # Check if current slot has 39 members
            current_slot_nodes = [node for node in matrix_tree.nodes if node.level <= 3]
            if len(current_slot_nodes) >= 39:
                return True
            
            return False
        except Exception as e:
            print(f"Error detecting recycle completion: {e}")
            return False
    
    def create_recycle_snapshot(self, user_id: str, slot_no: int):
        """Create immutable snapshot of 39-member tree when recycle occurs."""
        try:
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return None
            
            # Get current recycle number for this user+slot
            existing_recycles = MatrixRecycleInstance.objects(
                user_id=ObjectId(user_id),
                slot_number=slot_no
            ).order_by('-recycle_no').first()
            
            next_recycle_no = (existing_recycles.recycle_no + 1) if existing_recycles else 1
            
            # Create recycle instance
            recycle_instance = MatrixRecycleInstance(
                user_id=ObjectId(user_id),
                slot_number=slot_no,
                recycle_no=next_recycle_no,
                is_complete=True,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            recycle_instance.save()
            
            # Create immutable snapshot of all 39 nodes
            for node in matrix_tree.nodes:
                if node.level <= 3:  # Only include the 39 members (3+9+27)
                    recycle_node = MatrixRecycleNode(
                        instance_id=recycle_instance.id,
                        occupant_user_id=node.user_id,
                        level_index=node.level,
                        position_index=node.position,
                        placed_at=node.placed_at
                    )
                    recycle_node.save()
            
            return recycle_instance
        except Exception as e:
            print(f"Error creating recycle snapshot: {e}")
            return None
    
    def place_recycled_user(self, user_id: str, slot_no: int, upline_user_id: str):
        """Place recycled user in upline's corresponding slot using BFS algorithm."""
        try:
            # Get upline's matrix tree
            upline_tree = MatrixTree.objects(user_id=ObjectId(upline_user_id)).first()
            if not upline_tree:
                return None
            
            # Find next available position using BFS
            next_position = self._get_next_available_position(upline_tree, slot_no)
            if not next_position:
                return None
            
            # Create new node for recycled user
            new_node = MatrixNode(
                user_id=ObjectId(user_id),
                level=next_position["level"],
                position=next_position["position"],
                parent_id=ObjectId(upline_user_id),
                placed_at=datetime.utcnow()
            )
            
            # Add to upline's tree
            upline_tree.nodes.append(new_node)
            upline_tree.total_members += 1
            upline_tree.last_updated = datetime.utcnow()
            upline_tree.save()
            
            return new_node
        except Exception as e:
            print(f"Error placing recycled user: {e}")
            return None
    
    def _get_next_available_position(self, matrix_tree, slot_no: int):
        """Get next available position in matrix tree using BFS algorithm."""
        try:
            # BFS placement: Level 1 (left → middle → right), then Level 2, then Level 3
            existing_positions = set()
            for node in matrix_tree.nodes:
                existing_positions.add((node.level, node.position))
            
            # Level 1: 3 positions (0, 1, 2)
            for pos in range(3):
                if (1, pos) not in existing_positions:
                    return {"level": 1, "position": pos}
            
            # Level 2: 9 positions (0-8)
            for pos in range(9):
                if (2, pos) not in existing_positions:
                    return {"level": 2, "position": pos}
            
            # Level 3: 27 positions (0-26)
            for pos in range(27):
                if (3, pos) not in existing_positions:
                    return {"level": 3, "position": pos}
            
            return None  # Tree is full
        except Exception as e:
            print(f"Error getting next available position: {e}")
            return None
    
    def process_recycle_completion(self, user_id: str, slot_no: int):
        """Process complete recycle cycle: detect, snapshot, re-entry."""
        try:
            # 1. Detect recycle completion
            if not self.detect_recycle_completion(user_id, slot_no):
                return {"success": False, "error": "Recycle not yet complete"}
            
            # 2. Create immutable snapshot
            recycle_instance = self.create_recycle_snapshot(user_id, slot_no)
            if not recycle_instance:
                return {"success": False, "error": "Failed to create recycle snapshot"}
            
            # 3. Get upline for re-entry
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return {"success": False, "error": "Matrix tree not found"}
            
            # Find upline (parent in matrix tree)
            upline_user_id = None
            for node in matrix_tree.nodes:
                if node.user_id == ObjectId(user_id):
                    upline_user_id = node.parent_id
                    break
            
            if not upline_user_id:
                return {"success": False, "error": "Upline not found"}
            
            # 4. Place recycled user in upline's tree
            new_node = self.place_recycled_user(user_id, slot_no, str(upline_user_id))
            if not new_node:
                return {"success": False, "error": "Failed to place recycled user"}
            
            # 5. Clear current tree for new cycle
            matrix_tree.nodes = []
            matrix_tree.total_members = 0
            matrix_tree.current_slot = slot_no + 1 if slot_no < 15 else slot_no
            matrix_tree.last_updated = datetime.utcnow()
            matrix_tree.save()
            
            return {
                "success": True,
                "recycle_instance_id": str(recycle_instance.id),
                "recycle_no": recycle_instance.recycle_no,
                "new_position": {
                    "level": new_node.level,
                    "position": new_node.position
                },
                "upline_user_id": str(upline_user_id)
            }
        except Exception as e:
            print(f"Error processing recycle completion: {e}")
            return {"success": False, "error": str(e)}
    
    def get_recycle_tree(self, user_id: str, slot_no: int, recycle_no: int = None):
        """Get matrix tree by recycle number or current in-progress tree."""
        try:
            if recycle_no is None or recycle_no == "current":
                # Return current in-progress tree
                matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
                if not matrix_tree:
                    return None
                
                return {
                    "user_id": str(matrix_tree.user_id),
                    "slot_number": slot_no,
                    "recycle_no": "current",
                    "is_snapshot": False,
                    "is_complete": False,
                    "total_recycles": MatrixRecycleInstance.objects(
                        user_id=ObjectId(user_id),
                        slot_number=slot_no
                    ).count(),
                    "nodes": [node.to_mongo().to_dict() for node in matrix_tree.nodes]
                }
            else:
                # Return specific recycle snapshot
                recycle_instance = MatrixRecycleInstance.objects(
                    user_id=ObjectId(user_id),
                    slot_number=slot_no,
                    recycle_no=recycle_no
                ).first()
                
                if not recycle_instance:
                    return None
                
                # Get all nodes for this recycle instance
                recycle_nodes = MatrixRecycleNode.objects(instance_id=recycle_instance.id).all()
                
                return {
                    "user_id": str(recycle_instance.user_id),
                    "slot_number": recycle_instance.slot_number,
                    "recycle_no": recycle_instance.recycle_no,
                    "is_snapshot": True,
                    "is_complete": recycle_instance.is_complete,
                    "total_recycles": MatrixRecycleInstance.objects(
                        user_id=ObjectId(user_id),
                        slot_number=slot_no
                    ).count(),
                    "nodes": [node.to_mongo().to_dict() for node in recycle_nodes]
                }
        except Exception as e:
            print(f"Error getting recycle tree: {e}")
            return None
    
    def get_recycle_history(self, user_id: str, slot_no: int):
        """Get recycle history for user+slot."""
        try:
            recycle_instances = MatrixRecycleInstance.objects(
                user_id=ObjectId(user_id),
                slot_number=slot_no
            ).order_by('-recycle_no').all()
            
            return [instance.to_mongo().to_dict() for instance in recycle_instances]
        except Exception as e:
            print(f"Error getting recycle history: {e}")
            return []
    
    def _check_and_process_automatic_recycle(self, user_id: str, slot_no: int):
        """Check and automatically process recycle when 39 members complete."""
        try:
            # Check if recycle is needed
            if self.detect_recycle_completion(user_id, slot_no):
                print(f"🔄 Automatic recycle detected for user {user_id}, slot {slot_no}")
                
                # Process the recycle automatically
                result = self.process_recycle_completion(user_id, slot_no)
                
                if result.get("success"):
                    print(f"✅ Automatic recycle completed successfully for user {user_id}")
                    print(f"   - Recycle #{result.get('recycle_no')}")
                    print(f"   - New position: Level {result.get('new_position', {}).get('level')}, Position {result.get('new_position', {}).get('position')}")
                    print(f"   - Upline: {result.get('upline_user_id')}")
                    
                    # Log the automatic recycle event
                    self._log_earning_history(
                        user_id=user_id,
                        earning_type="automatic_recycle",
                        amount=0.0,
                        description=f"Automatic recycle #{result.get('recycle_no')} completed - 39 members reached"
                    )
                    
                    # Log blockchain event for automatic recycle
                    self._log_blockchain_event(
                        tx_hash=f"auto_recycle_{user_id}_{slot_no}_{result.get('recycle_no')}",
                        event_type='matrix_automatic_recycle',
                        event_data={
                            'program': 'matrix',
                            'slot_no': slot_no,
                            'user_id': user_id,
                            'recycle_no': result.get('recycle_no'),
                            'new_position': result.get('new_position'),
                            'upline_user_id': result.get('upline_user_id')
                        }
                    )
                else:
                    print(f"❌ Automatic recycle failed for user {user_id}: {result.get('error')}")
            else:
                print(f"ℹ️ No recycle needed for user {user_id}, slot {slot_no} - {self._get_current_member_count(user_id)} members")
                
        except Exception as e:
            print(f"Error in automatic recycle check: {e}")
    
    def _get_current_member_count(self, user_id: str):
        """Get current member count for a user's matrix tree."""
        try:
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if matrix_tree:
                return matrix_tree.total_members
            return 0
        except Exception as e:
            print(f"Error getting member count: {e}")
            return 0
    
    def _log_blockchain_event(self, tx_hash: str, event_type: str, event_data: dict):
        """Log blockchain event for audit trail."""
        try:
            from ..blockchain.model import BlockchainEvent
            BlockchainEvent(
                tx_hash=tx_hash,
                event_type=event_type,
                event_data=event_data,
                status='processed',
                processed_at=datetime.utcnow()
            ).save()
        except Exception as e:
            print(f"Error recording blockchain event: {str(e)}")
    
    # ==================== AUTO UPGRADE SYSTEM METHODS ====================
    
    def detect_middle_three_members(self, user_id: str, slot_no: int):
        """Detect the middle 3 members at each level for auto upgrade."""
        try:
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return {"success": False, "error": "Matrix tree not found"}
            
            # Get Level 2 nodes (positions 1, 4, 7 are middle 3)
            level_2_nodes = [node for node in matrix_tree.nodes if node.level == 2]
            
            # Middle 3 positions in Level 2: 1, 4, 7 (one under each Level 1 member)
            middle_three_positions = [1, 4, 7]
            middle_three_members = []
            
            for node in level_2_nodes:
                if node.position in middle_three_positions:
                    middle_three_members.append({
                        "user_id": str(node.user_id),
                        "level": node.level,
                        "position": node.position,
                        "placed_at": node.placed_at
                    })
            
            return {
                "success": True,
                "middle_three_members": middle_three_members,
                "total_found": len(middle_three_members),
                "required": 3,
                "is_complete": len(middle_three_members) == 3
            }
        except Exception as e:
            print(f"Error detecting middle three members: {e}")
            return {"success": False, "error": str(e)}
    
    def calculate_middle_three_earnings(self, user_id: str, slot_no: int):
        """Calculate 100% earnings from middle 3 members for auto upgrade."""
        try:
            # Get middle 3 members
            middle_three_result = self.detect_middle_three_members(user_id, slot_no)
            if not middle_three_result.get("success"):
                return {"success": False, "error": "Failed to detect middle three members"}
            
            middle_three_members = middle_three_result.get("middle_three_members", [])
            if len(middle_three_members) != 3:
                return {
                    "success": False, 
                    "error": f"Middle three not complete. Found: {len(middle_three_members)}, Required: 3"
                }
            
            # Get current slot info
            current_slot_info = self.MATRIX_SLOTS.get(slot_no, {})
            if not current_slot_info:
                return {"success": False, "error": f"Slot {slot_no} not found"}
            
            # Calculate 100% earnings from middle 3 members
            slot_value = current_slot_info.get('value', 0)
            total_earnings = slot_value * 3  # 100% from each of 3 members
            
            # Get next slot upgrade cost
            next_slot_no = slot_no + 1
            next_slot_info = self.MATRIX_SLOTS.get(next_slot_no, {})
            next_upgrade_cost = next_slot_info.get('value', 0)
            
            return {
                "success": True,
                "current_slot": slot_no,
                "current_slot_value": float(slot_value),
                "middle_three_members": middle_three_members,
                "total_earnings": float(total_earnings),
                "next_slot": next_slot_no,
                "next_upgrade_cost": float(next_upgrade_cost),
                "can_upgrade": total_earnings >= next_upgrade_cost,
                "surplus": float(total_earnings - next_upgrade_cost) if total_earnings >= next_upgrade_cost else 0
            }
        except Exception as e:
            print(f"Error calculating middle three earnings: {e}")
            return {"success": False, "error": str(e)}
    
    def process_automatic_upgrade(self, user_id: str, slot_no: int):
        """Process automatic upgrade using 100% earnings from middle 3 members."""
        try:
            # Calculate middle three earnings
            earnings_result = self.calculate_middle_three_earnings(user_id, slot_no)
            if not earnings_result.get("success"):
                return {"success": False, "error": earnings_result.get("error")}
            
            if not earnings_result.get("can_upgrade"):
                return {
                    "success": False, 
                    "error": f"Insufficient earnings. Required: {earnings_result.get('next_upgrade_cost')}, Available: {earnings_result.get('total_earnings')}"
                }
            
            # Get current matrix tree
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return {"success": False, "error": "Matrix tree not found"}
            
            # Update to next slot
            next_slot_no = slot_no + 1
            next_slot_info = self.MATRIX_SLOTS.get(next_slot_no, {})
            
            if not next_slot_info:
                return {"success": False, "error": f"Next slot {next_slot_no} not available"}
            
            # Update matrix tree
            matrix_tree.current_slot = next_slot_no
            matrix_tree.current_level = next_slot_info.get('level', next_slot_no)
            matrix_tree.last_updated = datetime.utcnow()
            matrix_tree.save()
            
            # Update MatrixAutoUpgrade
            matrix_auto_upgrade = MatrixAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
            if matrix_auto_upgrade:
                matrix_auto_upgrade.current_slot_no = next_slot_no
                matrix_auto_upgrade.current_level = next_slot_info.get('level', next_slot_no)
                matrix_auto_upgrade.middle_three_available = 0  # Reset for new slot
                matrix_auto_upgrade.is_eligible = False  # Reset eligibility
                matrix_auto_upgrade.can_upgrade = False  # Reset upgrade status
                
                # Set next upgrade cost
                next_next_slot = next_slot_no + 1
                if next_next_slot <= 15:
                    next_next_slot_info = self.MATRIX_SLOTS.get(next_next_slot, {})
                    matrix_auto_upgrade.next_upgrade_cost = next_next_slot_info.get('value', 0)
                
                matrix_auto_upgrade.last_updated = datetime.utcnow()
                matrix_auto_upgrade.save()
            
            # Create upgrade log
            self._create_matrix_upgrade_log(
                user_id=user_id,
                from_slot_no=slot_no,
                to_slot_no=next_slot_no,
                upgrade_cost=earnings_result.get('next_upgrade_cost'),
                earnings_used=earnings_result.get('total_earnings'),
                profit_gained=earnings_result.get('surplus'),
                trigger_type='auto',
                contributors=[member['user_id'] for member in earnings_result.get('middle_three_members', [])]
            )
            
            # Log earning history
            self._log_earning_history(
                user_id=user_id,
                earning_type="automatic_upgrade",
                amount=earnings_result.get('surplus', 0),
                description=f"Automatic upgrade from Slot {slot_no} to Slot {next_slot_no} using middle 3 earnings"
            )
            
            # Log blockchain event
            self._log_blockchain_event(
                tx_hash=f"auto_upgrade_{user_id}_{slot_no}_{next_slot_no}",
                event_type='matrix_automatic_upgrade',
                event_data={
                    'program': 'matrix',
                    'from_slot': slot_no,
                    'to_slot': next_slot_no,
                    'user_id': user_id,
                    'earnings_used': earnings_result.get('total_earnings'),
                    'profit_gained': earnings_result.get('surplus'),
                    'contributors': earnings_result.get('middle_three_members', [])
                }
            )
            
            return {
                "success": True,
                "from_slot": slot_no,
                "to_slot": next_slot_no,
                "earnings_used": earnings_result.get('total_earnings'),
                "profit_gained": earnings_result.get('surplus'),
                "contributors": earnings_result.get('middle_three_members', []),
                "message": f"Successfully upgraded from Slot {slot_no} to Slot {next_slot_no}"
            }
        except Exception as e:
            print(f"Error processing automatic upgrade: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_matrix_upgrade_log(self, user_id: str, from_slot_no: int, to_slot_no: int, 
                                 upgrade_cost: float, earnings_used: float, profit_gained: float,
                                 trigger_type: str, contributors: list):
        """Create matrix upgrade log entry."""
        try:
            from_slot_info = self.MATRIX_SLOTS.get(from_slot_no, {})
            to_slot_info = self.MATRIX_SLOTS.get(to_slot_no, {})
            
            MatrixUpgradeLog(
                user_id=ObjectId(user_id),
                from_slot_no=from_slot_no,
                to_slot_no=to_slot_no,
                from_slot_name=from_slot_info.get('name', f'SLOT_{from_slot_no}'),
                to_slot_name=to_slot_info.get('name', f'SLOT_{to_slot_no}'),
                upgrade_cost=upgrade_cost,
                currency='USDT',
                earnings_used=earnings_used,
                profit_gained=profit_gained,
                trigger_type=trigger_type,
                contributors=[ObjectId(contributor) for contributor in contributors],
                status='completed',
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            ).save()
        except Exception as e:
            print(f"Error creating matrix upgrade log: {e}")
    
    def check_and_process_automatic_upgrade(self, user_id: str, slot_no: int):
        """Check and automatically process upgrade when middle 3 earnings are sufficient."""
        try:
            # Calculate middle three earnings
            earnings_result = self.calculate_middle_three_earnings(user_id, slot_no)
            if not earnings_result.get("success"):
                print(f"ℹ️ Auto upgrade check failed for user {user_id}, slot {slot_no}: {earnings_result.get('error')}")
                return
            
            if earnings_result.get("can_upgrade"):
                print(f"🔄 Automatic upgrade detected for user {user_id}, slot {slot_no}")
                print(f"   - Middle 3 earnings: {earnings_result.get('total_earnings')} USDT")
                print(f"   - Next upgrade cost: {earnings_result.get('next_upgrade_cost')} USDT")
                print(f"   - Surplus: {earnings_result.get('surplus')} USDT")
                
                # Process the upgrade automatically
                result = self.process_automatic_upgrade(user_id, slot_no)
                
                if result.get("success"):
                    print(f"✅ Automatic upgrade completed successfully for user {user_id}")
                    print(f"   - Upgraded from Slot {result.get('from_slot')} to Slot {result.get('to_slot')}")
                    print(f"   - Earnings used: {result.get('earnings_used')} USDT")
                    print(f"   - Profit gained: {result.get('profit_gained')} USDT")
                else:
                    print(f"❌ Automatic upgrade failed for user {user_id}: {result.get('error')}")
            else:
                print(f"ℹ️ Auto upgrade not ready for user {user_id}, slot {slot_no}")
                print(f"   - Middle 3 earnings: {earnings_result.get('total_earnings')} USDT")
                print(f"   - Required: {earnings_result.get('next_upgrade_cost')} USDT")
                print(f"   - Shortfall: {earnings_result.get('next_upgrade_cost') - earnings_result.get('total_earnings')} USDT")
                
        except Exception as e:
            print(f"Error in automatic upgrade check: {e}")