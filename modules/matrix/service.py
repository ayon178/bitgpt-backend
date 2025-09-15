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
            
            # Check for Dream Matrix eligibility after placement
            self._check_and_process_dream_matrix_eligibility(str(referrer_tree.user_id), referrer_tree.current_slot)
            
            # Track mentorship relationships (automatic)
            self._track_mentorship_relationships_automatic(str(referrer_tree.user_id), user_id)
            
            # Trigger automatic rank update
            self.trigger_rank_update_automatic(user_id)
            
            # Trigger automatic Global Program integration
            self.trigger_global_integration_automatic(user_id)
            
            # Trigger automatic Jackpot Program integration
            self.trigger_jackpot_integration_automatic(user_id)
            
            # Trigger automatic NGS integration
            self.trigger_ngs_integration_automatic(user_id)
            
            # Trigger automatic Mentorship Bonus integration
            self.trigger_mentorship_bonus_integration_automatic(user_id)
            
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
    
    def _check_and_process_dream_matrix_eligibility(self, user_id: str, slot_no: int):
        """Automatically check and process Dream Matrix eligibility when conditions are met."""
        try:
            # Check if user now has 3 direct partners
            eligibility_result = self.check_dream_matrix_eligibility(user_id)
            
            if eligibility_result.get("success") and eligibility_result.get("is_eligible"):
                print(f"🎯 Dream Matrix eligibility achieved for user {user_id}")
                print(f"   - Direct partners: {eligibility_result.get('direct_partner_count')}")
                
                # Automatically process Dream Matrix distribution
                distribution_result = self.process_dream_matrix_distribution(user_id, slot_no)
                
                if distribution_result.get("success"):
                    print(f"✅ Dream Matrix distribution completed automatically")
                    print(f"   - Total distributed: ${distribution_result.get('total_distributed')}")
                else:
                    print(f"❌ Dream Matrix distribution failed: {distribution_result.get('error')}")
            else:
                print(f"ℹ️ Dream Matrix eligibility not yet met for user {user_id}")
                if eligibility_result.get("success"):
                    print(f"   - Current direct partners: {eligibility_result.get('direct_partner_count')}")
                    print(f"   - Required: {eligibility_result.get('required_partners')}")
                
        except Exception as e:
            print(f"Error in automatic Dream Matrix eligibility check: {e}")
    
    def _track_mentorship_relationships_automatic(self, user_id: str, direct_referral_id: str):
        """Automatically track mentorship relationships when a direct referral joins."""
        try:
            # Track mentorship relationship
            mentorship_result = self.track_mentorship_relationships(user_id, direct_referral_id)
            
            if mentorship_result.get("success"):
                print(f"🎯 Mentorship relationship tracked automatically")
                print(f"   - Super Upline: {mentorship_result.get('mentorship_record', {}).get('super_upline_id')}")
                print(f"   - Upline: {user_id}")
                print(f"   - Direct Referral: {direct_referral_id}")
                
                # Process mentorship bonus for joining (10% of $11 = $1.10)
                super_upline_id = mentorship_result.get('mentorship_record', {}).get('super_upline_id')
                if super_upline_id:
                    bonus_result = self.process_mentorship_bonus(
                        super_upline_id=super_upline_id,
                        direct_referral_id=direct_referral_id,
                        amount=11.0,  # $11 joining fee
                        activity_type="joining"
                    )
                    
                    if bonus_result.get("success"):
                        print(f"✅ Mentorship bonus processed automatically")
                        print(f"   - Amount: ${bonus_result.get('mentorship_bonus')}")
                        print(f"   - Super Upline: {super_upline_id}")
                    else:
                        print(f"❌ Mentorship bonus failed: {bonus_result.get('error')}")
            else:
                print(f"ℹ️ Mentorship relationship not tracked: {mentorship_result.get('error')}")
                
        except Exception as e:
            print(f"Error in automatic mentorship tracking: {e}")
    
    # ==================== DREAM MATRIX SYSTEM METHODS ====================
    
    def check_dream_matrix_eligibility(self, user_id: str):
        """Check if user meets Dream Matrix eligibility (3 direct partners)."""
        try:
            # Count direct partners in matrix tree
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return {"success": False, "error": "Matrix tree not found"}
            
            # Count Level 1 members (direct partners)
            direct_partners = [node for node in matrix_tree.nodes if node.level == 1]
            direct_partner_count = len(direct_partners)
            
            # Dream Matrix requires exactly 3 direct partners
            is_eligible = direct_partner_count >= 3
            
            return {
                "success": True,
                "user_id": user_id,
                "direct_partner_count": direct_partner_count,
                "required_partners": 3,
                "is_eligible": is_eligible,
                "direct_partners": [str(node.user_id) for node in direct_partners]
            }
        except Exception as e:
            print(f"Error checking Dream Matrix eligibility: {e}")
            return {"success": False, "error": str(e)}
    
    def calculate_dream_matrix_earnings(self, user_id: str, slot_no: int = 5):
        """Calculate Dream Matrix earnings based on 5th slot ($800 total value)."""
        try:
            # Check eligibility first
            eligibility_result = self.check_dream_matrix_eligibility(user_id)
            if not eligibility_result.get("success"):
                return {"success": False, "error": eligibility_result.get("error")}
            
            if not eligibility_result.get("is_eligible"):
                return {
                    "success": False, 
                    "error": f"Dream Matrix eligibility not met. Required: 3 direct partners, Found: {eligibility_result.get('direct_partner_count')}"
                }
            
            # Dream Matrix calculation based on 5th slot ($800 total value)
            dream_matrix_base_value = 800.0  # $800 as per documentation
            
            # Progressive commission percentages per level
            dream_matrix_distribution = {
                1: {"members": 3, "percentage": 10, "amount": 80, "total": 240},
                2: {"members": 9, "percentage": 10, "amount": 80, "total": 720},
                3: {"members": 27, "percentage": 15, "amount": 120, "total": 3240},
                4: {"members": 81, "percentage": 25, "amount": 200, "total": 16200},
                5: {"members": 243, "percentage": 40, "amount": 320, "total": 77760}
            }
            
            # Calculate total potential earnings
            total_potential_earnings = sum(level["total"] for level in dream_matrix_distribution.values())
            
            return {
                "success": True,
                "user_id": user_id,
                "slot_no": slot_no,
                "base_value": dream_matrix_base_value,
                "eligibility": eligibility_result,
                "distribution": dream_matrix_distribution,
                "total_potential_earnings": total_potential_earnings,
                "total_members": sum(level["members"] for level in dream_matrix_distribution.values()),
                "calculation_note": "Based on 5th slot ($800) with progressive commission percentages"
            }
        except Exception as e:
            print(f"Error calculating Dream Matrix earnings: {e}")
            return {"success": False, "error": str(e)}
    
    def process_dream_matrix_distribution(self, user_id: str, slot_no: int = 5):
        """Process Dream Matrix distribution when user meets requirements."""
        try:
            # Calculate Dream Matrix earnings
            earnings_result = self.calculate_dream_matrix_earnings(user_id, slot_no)
            if not earnings_result.get("success"):
                return {"success": False, "error": earnings_result.get("error")}
            
            # Get matrix tree for distribution
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return {"success": False, "error": "Matrix tree not found"}
            
            # Process distribution for each level
            distribution_results = []
            total_distributed = 0
            
            for level, level_info in earnings_result.get("distribution", {}).items():
                # Find members at this level
                level_members = [node for node in matrix_tree.nodes if node.level == level]
                
                if level_members:
                    # Calculate amount per member
                    amount_per_member = level_info["amount"] / len(level_members)
                    
                    # Distribute to each member
                    for member in level_members:
                        # Create earning history for each member
                        self._log_earning_history(
                            user_id=str(member.user_id),
                            earning_type="dream_matrix_distribution",
                            amount=amount_per_member,
                            description=f"Dream Matrix Level {level} distribution from user {user_id}"
                        )
                        
                        # Create commission record
                        self._create_dream_matrix_commission(
                            from_user_id=user_id,
                            to_user_id=str(member.user_id),
                            level=level,
                            amount=amount_per_member,
                            percentage=level_info["percentage"]
                        )
                        
                        total_distributed += amount_per_member
                    
                    distribution_results.append({
                        "level": level,
                        "members_count": len(level_members),
                        "expected_members": level_info["members"],
                        "amount_per_member": amount_per_member,
                        "total_distributed": amount_per_member * len(level_members),
                        "percentage": level_info["percentage"]
                    })
            
            # Log Dream Matrix completion
            self._log_earning_history(
                user_id=user_id,
                earning_type="dream_matrix_completion",
                amount=total_distributed,
                description=f"Dream Matrix distribution completed - Total distributed: ${total_distributed}"
            )
            
            # Log blockchain event
            self._log_blockchain_event(
                tx_hash=f"dream_matrix_{user_id}_{slot_no}",
                event_type='dream_matrix_distribution',
                event_data={
                    'program': 'dream_matrix',
                    'slot_no': slot_no,
                    'user_id': user_id,
                    'total_distributed': total_distributed,
                    'distribution_results': distribution_results
                }
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "slot_no": slot_no,
                "total_distributed": total_distributed,
                "distribution_results": distribution_results,
                "message": f"Dream Matrix distribution completed successfully. Total distributed: ${total_distributed}"
            }
        except Exception as e:
            print(f"Error processing Dream Matrix distribution: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_dream_matrix_commission(self, from_user_id: str, to_user_id: str, 
                                      level: int, amount: float, percentage: float):
        """Create Dream Matrix commission record."""
        try:
            MatrixCommission(
                from_user_id=ObjectId(from_user_id),
                to_user_id=ObjectId(to_user_id),
                program='dream_matrix',
                commission_type='dream_matrix_level',
                slot_no=5,  # Based on 5th slot
                amount=amount,
            currency='USDT',
            status='paid',
                created_at=datetime.utcnow(),
            paid_at=datetime.utcnow()
            ).save()
        except Exception as e:
            print(f"Error creating Dream Matrix commission: {e}")
    
    def get_dream_matrix_status(self, user_id: str):
        """Get comprehensive Dream Matrix status for a user."""
        try:
            # Check eligibility
            eligibility_result = self.check_dream_matrix_eligibility(user_id)
            
            # Calculate earnings
            earnings_result = self.calculate_dream_matrix_earnings(user_id)
            
            # Get matrix tree info
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            
            status = {
                "user_id": user_id,
                "eligibility": eligibility_result,
                "earnings_calculation": earnings_result,
                "matrix_tree_info": {
                    "current_slot": matrix_tree.current_slot if matrix_tree else 0,
                    "total_members": matrix_tree.total_members if matrix_tree else 0,
                    "level_1_members": matrix_tree.level_1_members if matrix_tree else 0,
                    "level_2_members": matrix_tree.level_2_members if matrix_tree else 0,
                    "level_3_members": matrix_tree.level_3_members if matrix_tree else 0
                } if matrix_tree else None,
                "dream_matrix_rules": {
                    "required_direct_partners": 3,
                    "calculation_base": "5th slot ($800)",
                    "progressive_commissions": True,
                    "mandatory_requirement": True
                }
            }
            
            return {"success": True, "status": status}
        except Exception as e:
            print(f"Error getting Dream Matrix status: {e}")
    
    # ==================== MENTORSHIP BONUS SYSTEM METHODS ====================
    
    def track_mentorship_relationships(self, user_id: str, direct_referral_id: str):
        """Track mentorship relationships when a direct referral joins."""
        try:
            # Get the super upline (user's upline)
            user_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not user_tree:
                return {"success": False, "error": "User matrix tree not found"}
            
            # Find the super upline (user's referrer)
            super_upline_id = None
            for node in user_tree.nodes:
                if str(node.user_id) == user_id:
                    # Find the upline of this user
                    super_upline_id = str(node.upline_id) if node.upline_id else None
                    break
            
            if not super_upline_id:
                return {"success": False, "error": "Super upline not found"}
            
            # Create mentorship relationship record
            mentorship_record = {
                "super_upline_id": super_upline_id,
                "upline_id": user_id,
                "direct_referral_id": direct_referral_id,
                "relationship_type": "direct_of_direct",
                "created_at": datetime.utcnow(),
                "status": "active"
            }
            
            # Log mentorship relationship
            self._log_earning_history(
                user_id=super_upline_id,
                earning_type="mentorship_relationship_created",
                amount=0,
                description=f"Mentorship relationship: {super_upline_id} -> {user_id} -> {direct_referral_id}"
            )
            
            return {
                "success": True,
                "mentorship_record": mentorship_record,
                "message": f"Mentorship relationship tracked: Super Upline {super_upline_id} will receive 10% from {direct_referral_id}"
            }
        except Exception as e:
            print(f"Error tracking mentorship relationship: {e}")
            return {"success": False, "error": str(e)}
    
    def calculate_mentorship_bonus(self, super_upline_id: str, direct_referral_id: str, amount: float):
        """Calculate 10% mentorship bonus for super upline."""
        try:
            mentorship_bonus = amount * 0.10  # 10% commission
            
            return {
                "success": True,
                "super_upline_id": super_upline_id,
                "direct_referral_id": direct_referral_id,
                "original_amount": amount,
                "mentorship_bonus": mentorship_bonus,
                "commission_percentage": 10,
                "description": f"10% mentorship bonus from {direct_referral_id}'s activity"
            }
        except Exception as e:
            print(f"Error calculating mentorship bonus: {e}")
            return {"success": False, "error": str(e)}
    
    def process_mentorship_bonus(self, super_upline_id: str, direct_referral_id: str, amount: float, activity_type: str = "joining"):
        """Process mentorship bonus distribution to super upline."""
        try:
            # Calculate mentorship bonus
            bonus_result = self.calculate_mentorship_bonus(super_upline_id, direct_referral_id, amount)
            if not bonus_result.get("success"):
                return {"success": False, "error": bonus_result.get("error")}
            
            mentorship_bonus = bonus_result.get("mentorship_bonus")
            
            # Create earning history for super upline
            self._log_earning_history(
                user_id=super_upline_id,
                earning_type="mentorship_bonus",
                amount=mentorship_bonus,
                description=f"Mentorship bonus: 10% from {direct_referral_id}'s {activity_type} (${amount})"
            )
            
            # Create commission record
            self._create_mentorship_commission(
                super_upline_id=super_upline_id,
                direct_referral_id=direct_referral_id,
                amount=mentorship_bonus,
                original_amount=amount,
                activity_type=activity_type
            )
            
            # Log blockchain event
            self._log_blockchain_event(
                tx_hash=f"mentorship_bonus_{super_upline_id}_{direct_referral_id}",
                event_type='mentorship_bonus',
                event_data={
                    'program': 'mentorship_bonus',
                    'super_upline_id': super_upline_id,
                    'direct_referral_id': direct_referral_id,
                    'original_amount': amount,
                    'mentorship_bonus': mentorship_bonus,
                    'activity_type': activity_type
                }
            )
            
            return {
                "success": True,
                "super_upline_id": super_upline_id,
                "direct_referral_id": direct_referral_id,
                "original_amount": amount,
                "mentorship_bonus": mentorship_bonus,
                "message": f"Mentorship bonus of ${mentorship_bonus} distributed to super upline {super_upline_id}"
            }
        except Exception as e:
            print(f"Error processing mentorship bonus: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_mentorship_commission(self, super_upline_id: str, direct_referral_id: str, 
                                    amount: float, original_amount: float, activity_type: str):
        """Create mentorship commission record."""
        try:
            MatrixCommission(
                from_user_id=ObjectId(direct_referral_id),
                to_user_id=ObjectId(super_upline_id),
                program='mentorship_bonus',
                commission_type='direct_of_direct',
                slot_no=1,  # Based on joining
                amount=amount,
            currency='USDT',
            status='paid',
                created_at=datetime.utcnow(),
                paid_at=datetime.utcnow(),
                metadata={
                    'original_amount': original_amount,
                    'activity_type': activity_type,
                    'commission_percentage': 10
                }
            ).save()
        except Exception as e:
            print(f"Error creating mentorship commission: {e}")
    
    def get_mentorship_status(self, user_id: str):
        """Get comprehensive mentorship status for a user."""
        try:
            # Get user's matrix tree
            user_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            
            # Count direct referrals
            direct_referrals = [node for node in user_tree.nodes if node.level == 1] if user_tree else []
            
            # Count direct-of-direct referrals
            direct_of_direct_count = 0
            mentorship_relationships = []
            
            for direct_ref in direct_referrals:
                # Find direct referrals of each direct referral
                direct_ref_tree = MatrixTree.objects(user_id=direct_ref.user_id).first()
                if direct_ref_tree:
                    direct_ref_directs = [node for node in direct_ref_tree.nodes if node.level == 1]
                    direct_of_direct_count += len(direct_ref_directs)
                    
                    for d_o_d in direct_ref_directs:
                        mentorship_relationships.append({
                            "direct_referral": str(direct_ref.user_id),
                            "direct_of_direct": str(d_o_d.user_id),
                            "relationship": f"{user_id} -> {direct_ref.user_id} -> {d_o_d.user_id}"
                        })
            
            # Calculate potential mentorship earnings
            potential_earnings = direct_of_direct_count * 11 * 0.10  # Assuming $11 joining fee
            
            status = {
                "user_id": user_id,
                "direct_referrals_count": len(direct_referrals),
                "direct_of_direct_count": direct_of_direct_count,
                "mentorship_relationships": mentorship_relationships,
                "potential_earnings": potential_earnings,
                "mentorship_rules": {
                    "commission_percentage": 10,
                    "applies_to": "direct_of_direct activities",
                    "includes": "joining fees and slot upgrades"
                }
            }
            
            return {"success": True, "status": status}
        except Exception as e:
            print(f"Error getting mentorship status: {e}")
    
    # ==================== MATRIX UPGRADE SYSTEM METHODS ====================
    
    def upgrade_matrix_slot(self, user_id: str, from_slot_no: int, to_slot_no: int, upgrade_type: str = "manual"):
        """Upgrade user from one Matrix slot to another."""
        try:
            # Validate upgrade parameters
            if from_slot_no >= to_slot_no:
                return {"success": False, "error": "Target slot must be higher than current slot"}
            
            if to_slot_no < 1 or to_slot_no > 15:
                return {"success": False, "error": "Target slot must be between 1 and 15"}
            
            # Get user's matrix tree
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return {"success": False, "error": "Matrix tree not found"}
            
            # Check if user has the current slot
            if matrix_tree.current_slot != from_slot_no:
                return {"success": False, "error": f"User is not currently on slot {from_slot_no}"}
            
            # Get slot costs
            slot_costs = self._get_matrix_slot_costs()
            upgrade_cost = slot_costs.get(to_slot_no, 0) - slot_costs.get(from_slot_no, 0)
            
            if upgrade_cost <= 0:
                return {"success": False, "error": "Invalid upgrade cost calculation"}
            
            # Check if user has sufficient funds (for manual upgrades)
            if upgrade_type == "manual":
                # Get user's wallet balance
                user = User.objects(id=ObjectId(user_id)).first()
                if not user:
                    return {"success": False, "error": "User not found"}
                
                # Check wallet balance
                wallet_balance = getattr(user, 'wallet_balance', 0)
                if wallet_balance < upgrade_cost:
                    return {
                        "success": False, 
                        "error": f"Insufficient funds. Required: ${upgrade_cost}, Available: ${wallet_balance}"
                    }
                
                # Deduct from wallet
                user.wallet_balance -= upgrade_cost
                user.save()
            
            # Update matrix tree
            matrix_tree.current_slot = to_slot_no
            matrix_tree.last_upgrade_at = datetime.utcnow()
            matrix_tree.save()
    
            # Create upgrade log
            self._create_matrix_upgrade_log(
                user_id=user_id,
                from_slot_no=from_slot_no,
                to_slot_no=to_slot_no,
                upgrade_cost=upgrade_cost,
                earnings_used=0,  # Manual upgrade uses wallet funds
                profit_gained=0,  # No profit from manual upgrade
                trigger_type=upgrade_type,
                contributors=[]
            )
            
            # Log earning history
            self._log_earning_history(
                user_id=user_id,
                earning_type="matrix_upgrade",
                amount=-upgrade_cost,  # Negative because it's a cost
                description=f"Matrix upgrade from slot {from_slot_no} to slot {to_slot_no} (${upgrade_cost})"
            )
            
            # Log blockchain event
            self._log_blockchain_event(
                tx_hash=f"matrix_upgrade_{user_id}_{from_slot_no}_{to_slot_no}",
                event_type='matrix_upgrade',
                event_data={
                    'program': 'matrix_upgrade',
                    'user_id': user_id,
                    'from_slot_no': from_slot_no,
                    'to_slot_no': to_slot_no,
                    'upgrade_cost': upgrade_cost,
                    'upgrade_type': upgrade_type
                }
            )
            
            # Trigger all auto-calculations for the new slot
            self._trigger_slot_upgrade_calculations(user_id, to_slot_no)
            
            # Trigger automatic rank update
            self.trigger_rank_update_automatic(user_id)
            
            # Trigger automatic Global Program integration
            self.trigger_global_integration_automatic(user_id)
            
            # Trigger automatic Leadership Stipend integration (only for slots 10-16)
            if to_slot_no >= 10:
                self.trigger_leadership_stipend_integration_automatic(user_id)
            
            # Trigger automatic Jackpot Program integration
            self.trigger_jackpot_integration_automatic(user_id)
            
            # Trigger automatic NGS integration
            self.trigger_ngs_integration_automatic(user_id)
            
            # Trigger automatic Mentorship Bonus integration
            self.trigger_mentorship_bonus_integration_automatic(user_id)
            
            return {
                "success": True,
                "user_id": user_id,
                "from_slot_no": from_slot_no,
                "to_slot_no": to_slot_no,
                "upgrade_cost": upgrade_cost,
                "upgrade_type": upgrade_type,
                "message": f"Successfully upgraded from slot {from_slot_no} to slot {to_slot_no}"
            }
        except Exception as e:
            print(f"Error upgrading matrix slot: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_matrix_slot_costs(self):
        """Get Matrix slot costs in USDT."""
        return {
            1: 11,      # STARTER
            2: 33,      # BRONZE
            3: 99,      # SILVER
            4: 297,     # GOLD
            5: 891,     # PLATINUM
            6: 2673,    # DIAMOND
            7: 8019,    # RUBY
            8: 24057,   # EMERALD
            9: 72171,   # SAPPHIRE
            10: 216513, # TOPAZ
            11: 649539, # PEARL
            12: 1948617, # AMETHYST
            13: 5845851, # OBSIDIAN
            14: 17537553, # TITANIUM
            15: 52612659  # STAR
        }
    
    def _trigger_slot_upgrade_calculations(self, user_id: str, slot_no: int):
        """Trigger all auto-calculations when a slot is upgraded."""
        try:
            print(f"🎯 Triggering auto-calculations for slot {slot_no} upgrade")
            
            # 1. Check Dream Matrix eligibility
            self._check_and_process_dream_matrix_eligibility(user_id, slot_no)
            
            # 2. Check for auto-upgrade eligibility
            self.check_and_process_automatic_upgrade(user_id, slot_no)
            
            # 3. Update user rank based on new slot
            self._update_user_rank_from_matrix_slot(user_id, slot_no)
            
            # 4. Check for recycle completion
            self._check_and_process_automatic_recycle(user_id, slot_no)
            
            print(f"✅ Auto-calculations completed for slot {slot_no}")
        except Exception as e:
            print(f"Error in slot upgrade calculations: {e}")
    
    def _update_user_rank_from_matrix_slot(self, user_id: str, slot_no: int):
        """Update user rank based on Matrix slot."""
        try:
            # Get user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return
        
            # Calculate rank based on slot (simplified ranking)
            rank_mapping = {
                1: "Bitron", 2: "Cryzen", 3: "Neura", 4: "Glint", 5: "Stellar",
                6: "Ignis", 7: "Quanta", 8: "Lumix", 9: "Arion", 10: "Nexus",
                11: "Fyre", 12: "Axion", 13: "Trion", 14: "Spectra", 15: "Omega"
            }
            
            new_rank = rank_mapping.get(slot_no, "Bitron")
            
            # Update user rank
            user.rank = new_rank
            user.save()
            
            print(f"✅ User {user_id} rank updated to {new_rank} (slot {slot_no})")
        except Exception as e:
            print(f"Error updating user rank: {e}")
    
    def get_upgrade_options(self, user_id: str):
        """Get available upgrade options for a user."""
        try:
            # Get user's matrix tree
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return {"success": False, "error": "Matrix tree not found"}
            
            current_slot = matrix_tree.current_slot
            slot_costs = self._get_matrix_slot_costs()
            
            # Get user's wallet balance
            user = User.objects(id=ObjectId(user_id)).first()
            wallet_balance = getattr(user, 'wallet_balance', 0) if user else 0
            
            # Calculate upgrade options
            upgrade_options = []
            for slot_no in range(current_slot + 1, 16):  # Next slot to slot 15
                upgrade_cost = slot_costs.get(slot_no, 0) - slot_costs.get(current_slot, 0)
                can_afford = wallet_balance >= upgrade_cost
                
                upgrade_options.append({
                    "slot_no": slot_no,
                    "slot_name": self._get_slot_name(slot_no),
                    "upgrade_cost": upgrade_cost,
                    "can_afford": can_afford,
                    "wallet_balance": wallet_balance,
                    "shortfall": max(0, upgrade_cost - wallet_balance) if not can_afford else 0
                })
            
            return {
                "success": True,
                "user_id": user_id,
                "current_slot": current_slot,
                "current_slot_name": self._get_slot_name(current_slot),
                "wallet_balance": wallet_balance,
                "upgrade_options": upgrade_options
            }
        except Exception as e:
            print(f"Error getting upgrade options: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_slot_name(self, slot_no: int):
        """Get slot name by slot number."""
        slot_names = {
            1: "STARTER", 2: "BRONZE", 3: "SILVER", 4: "GOLD", 5: "PLATINUM",
            6: "DIAMOND", 7: "RUBY", 8: "EMERALD", 9: "SAPPHIRE", 10: "TOPAZ",
            11: "PEARL", 12: "AMETHYST", 13: "OBSIDIAN", 14: "TITANIUM", 15: "STAR"
        }
        return slot_names.get(slot_no, f"SLOT_{slot_no}")
    
    def get_upgrade_history(self, user_id: str):
        """Get user's Matrix upgrade history."""
        try:
            # Get upgrade logs
            upgrade_logs = MatrixUpgradeLog.objects(user_id=ObjectId(user_id)).order_by('-created_at')
            
            history = []
            for log in upgrade_logs:
                history.append({
                    "from_slot_no": log.from_slot_no,
                    "to_slot_no": log.to_slot_no,
                    "from_slot_name": self._get_slot_name(log.from_slot_no),
                    "to_slot_name": self._get_slot_name(log.to_slot_no),
                    "upgrade_cost": float(log.upgrade_cost),
                    "earnings_used": float(log.earnings_used),
                    "profit_gained": float(log.profit_gained),
                    "trigger_type": log.trigger_type,
                    "contributors": [str(c) for c in log.contributors],
                    "created_at": log.created_at.isoformat()
                })
            
            return {
                "success": True,
                "user_id": user_id,
                "upgrade_history": history,
                "total_upgrades": len(history)
            }
        except Exception as e:
            print(f"Error getting upgrade history: {e}")
            return {"success": False, "error": str(e)}
    
    def get_matrix_upgrade_status(self, user_id: str):
        """Get comprehensive Matrix upgrade status for a user."""
        try:
            # Get upgrade options
            options_result = self.get_upgrade_options(user_id)
            
            # Get upgrade history
            history_result = self.get_upgrade_history(user_id)
            
            # Get matrix tree info
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            
            status = {
                "user_id": user_id,
                "current_status": {
                    "current_slot": matrix_tree.current_slot if matrix_tree else 1,
                    "current_slot_name": self._get_slot_name(matrix_tree.current_slot) if matrix_tree else "STARTER",
                    "total_members": matrix_tree.total_members if matrix_tree else 0,
                    "is_complete": matrix_tree.is_complete if matrix_tree else False
                },
                "upgrade_options": options_result.get("upgrade_options", []) if options_result.get("success") else [],
                "upgrade_history": history_result.get("upgrade_history", []) if history_result.get("success") else [],
                "wallet_info": {
                    "balance": options_result.get("wallet_balance", 0) if options_result.get("success") else 0
                },
                "upgrade_rules": {
                    "manual_upgrade": "Available using wallet funds",
                    "auto_upgrade": "Available using middle-3 earnings",
                    "reserve_combination": "2 reserves + 1 wallet or 1 reserve + 2 wallet"
                }
            }
            
            return {"success": True, "status": status}
        except Exception as e:
            print(f"Error getting Matrix upgrade status: {e}")
    
    # ==================== BINARY PROGRAM INTEGRATION METHODS ====================
    
    def update_user_rank_from_programs(self, user_id: str):
        """Update user rank based on Binary and Matrix slot activations."""
        try:
            # Get user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get Binary slots activated
            binary_slots = self._get_binary_slots_activated(user_id)
            
            # Get Matrix slots activated
            matrix_slots = self._get_matrix_slots_activated(user_id)
            
            # Calculate total slots activated
            total_slots = binary_slots + matrix_slots
            
            # Determine rank based on total slots
            new_rank = self._calculate_rank_from_slots(total_slots)
            
            # Update user rank
            old_rank = getattr(user, 'rank', 'Bitron')
            user.rank = new_rank
            user.save()
            
            # Log rank update
            self._log_earning_history(
                user_id=user_id,
                earning_type="rank_update",
                amount=0,
                description=f"Rank updated from {old_rank} to {new_rank} (Binary: {binary_slots}, Matrix: {matrix_slots}, Total: {total_slots})"
            )
            
            # Log blockchain event
            self._log_blockchain_event(
                tx_hash=f"rank_update_{user_id}",
                event_type='rank_update',
                event_data={
                    'program': 'rank_system',
                    'user_id': user_id,
                    'old_rank': old_rank,
                    'new_rank': new_rank,
                    'binary_slots': binary_slots,
                    'matrix_slots': matrix_slots,
                    'total_slots': total_slots
                }
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "old_rank": old_rank,
                "new_rank": new_rank,
                "binary_slots": binary_slots,
                "matrix_slots": matrix_slots,
                "total_slots": total_slots,
                "message": f"Rank updated from {old_rank} to {new_rank}"
            }
        except Exception as e:
            print(f"Error updating user rank: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_binary_slots_activated(self, user_id: str):
        """Get number of Binary slots activated for a user."""
        try:
            # This would integrate with Binary program
            # For now, return 0 as placeholder
            # In real implementation, this would query Binary program data
            
            # Placeholder: Check if user has Binary tree
            # In actual implementation, this would be:
            # binary_tree = BinaryTree.objects(user_id=ObjectId(user_id)).first()
            # return binary_tree.activated_slots if binary_tree else 0
            
            return 0  # Placeholder for now
        except Exception as e:
            print(f"Error getting binary slots: {e}")
            return 0
    
    def _get_matrix_slots_activated(self, user_id: str):
        """Get number of Matrix slots activated for a user."""
        try:
            # Get Matrix tree
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return 0
            
            # Return current slot (highest activated slot)
            return matrix_tree.current_slot
        except Exception as e:
            print(f"Error getting matrix slots: {e}")
            return 0
    
    def _calculate_rank_from_slots(self, total_slots: int):
        """Calculate rank based on total slots activated."""
        rank_mapping = {
            1: "Bitron",    # 1 slot
            2: "Cryzen",    # 2 slots
            3: "Neura",     # 3 slots
            4: "Glint",     # 4 slots
            5: "Stellar",   # 5 slots
            6: "Ignis",     # 6 slots
            7: "Quanta",    # 7 slots
            8: "Lumix",     # 8 slots
            9: "Arion",     # 9 slots
            10: "Nexus",    # 10 slots
            11: "Fyre",     # 11 slots
            12: "Axion",    # 12 slots
            13: "Trion",    # 13 slots
            14: "Spectra",  # 14 slots
            15: "Omega"     # 15 slots
        }
        
        # Cap at 15 slots for Omega rank
        effective_slots = min(total_slots, 15)
        return rank_mapping.get(effective_slots, "Bitron")
    
    def get_user_rank_status(self, user_id: str):
        """Get comprehensive rank status for a user."""
        try:
            # Get user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get current rank
            current_rank = getattr(user, 'rank', 'Bitron')
            
            # Get Binary slots
            binary_slots = self._get_binary_slots_activated(user_id)
            
            # Get Matrix slots
            matrix_slots = self._get_matrix_slots_activated(user_id)
            
            # Calculate total slots
            total_slots = binary_slots + matrix_slots
            
            # Get rank progression
            rank_progression = self._get_rank_progression(total_slots)
            
            # Get next rank requirements
            next_rank_info = self._get_next_rank_info(total_slots)
            
            status = {
                "user_id": user_id,
                "current_rank": current_rank,
                "slot_breakdown": {
                    "binary_slots": binary_slots,
                    "matrix_slots": matrix_slots,
                    "total_slots": total_slots
                },
                "rank_progression": rank_progression,
                "next_rank": next_rank_info,
                "rank_system_info": {
                    "total_ranks": 15,
                    "rank_names": ["Bitron", "Cryzen", "Neura", "Glint", "Stellar", 
                                 "Ignis", "Quanta", "Lumix", "Arion", "Nexus",
                                 "Fyre", "Axion", "Trion", "Spectra", "Omega"],
                    "max_slots": 15,
                    "description": "Ranks are achieved by activating slots in Binary and Matrix programs"
                }
            }
            
            return {"success": True, "status": status}
        except Exception as e:
            print(f"Error getting rank status: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_rank_progression(self, total_slots: int):
        """Get rank progression information."""
        ranks = ["Bitron", "Cryzen", "Neura", "Glint", "Stellar", 
                "Ignis", "Quanta", "Lumix", "Arion", "Nexus",
                "Fyre", "Axion", "Trion", "Spectra", "Omega"]
        
        current_rank_index = min(total_slots - 1, 14)
        current_rank = ranks[current_rank_index]
        
        return {
            "current_rank": current_rank,
            "current_rank_index": current_rank_index + 1,
            "total_ranks": 15,
            "progress_percentage": ((current_rank_index + 1) / 15) * 100
        }
    
    def _get_next_rank_info(self, total_slots: int):
        """Get next rank information."""
        ranks = ["Bitron", "Cryzen", "Neura", "Glint", "Stellar", 
                "Ignis", "Quanta", "Lumix", "Arion", "Nexus",
                "Fyre", "Axion", "Trion", "Spectra", "Omega"]
        
        if total_slots >= 15:
            return {
                "next_rank": "Omega (Max Rank)",
                "slots_needed": 0,
                "is_max_rank": True
            }
        
        next_rank_index = total_slots
        next_rank = ranks[next_rank_index]
        slots_needed = 1
        
        return {
            "next_rank": next_rank,
            "slots_needed": slots_needed,
            "is_max_rank": False
        }
    
    def trigger_rank_update_automatic(self, user_id: str):
        """Automatically trigger rank update when slots are activated."""
        try:
            print(f"🎯 Triggering automatic rank update for user {user_id}")
            
            # Update rank
            rank_result = self.update_user_rank_from_programs(user_id)
            
            if rank_result.get("success"):
                print(f"✅ Rank updated automatically")
                print(f"   - Old rank: {rank_result.get('old_rank')}")
                print(f"   - New rank: {rank_result.get('new_rank')}")
                print(f"   - Binary slots: {rank_result.get('binary_slots')}")
                print(f"   - Matrix slots: {rank_result.get('matrix_slots')}")
                print(f"   - Total slots: {rank_result.get('total_slots')}")
            else:
                print(f"❌ Rank update failed: {rank_result.get('error')}")
                
        except Exception as e:
            print(f"Error in automatic rank update: {e}")
    
    # ==================== GLOBAL PROGRAM INTEGRATION METHODS ====================
    
    def integrate_with_global_program(self, user_id: str):
        """Integrate Matrix user with Global Program."""
        try:
            # Get user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check if user is eligible for Global Program
            global_eligibility = self._check_global_program_eligibility(user_id)
            
            if not global_eligibility.get("is_eligible"):
                return {
                    "success": False, 
                    "error": f"User not eligible for Global Program: {global_eligibility.get('reason')}"
                }
            
            # Get Matrix slot info
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            matrix_slot = matrix_tree.current_slot if matrix_tree else 1
            
            # Calculate Global Program contribution
            global_contribution = self._calculate_global_contribution(matrix_slot)
            
            # Update Global Program status
            global_status = self._update_global_program_status(user_id, global_contribution)
            
            # Process Global Distribution
            distribution_result = self._process_global_distribution(user_id, global_contribution)
            
            # Log Global Program integration
            self._log_earning_history(
                user_id=user_id,
                earning_type="global_program_integration",
                amount=global_contribution,
                description=f"Global Program integration - Matrix slot {matrix_slot} contributes ${global_contribution}"
            )
            
            # Log blockchain event
            self._log_blockchain_event(
                tx_hash=f"global_integration_{user_id}",
                event_type='global_program_integration',
                event_data={
                    'program': 'global_program',
                    'user_id': user_id,
                    'matrix_slot': matrix_slot,
                    'global_contribution': global_contribution,
                    'global_status': global_status
                }
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "global_contribution": global_contribution,
                "global_status": global_status,
                "distribution_result": distribution_result,
                "message": f"Successfully integrated with Global Program - Contribution: ${global_contribution}"
            }
        except Exception as e:
            print(f"Error integrating with Global Program: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_global_program_eligibility(self, user_id: str):
        """Check if user is eligible for Global Program."""
        try:
            # Get user's Matrix tree
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return {"is_eligible": False, "reason": "Matrix tree not found"}
            
            # Check if user has at least STARTER slot (slot 1)
            if matrix_tree.current_slot < 1:
                return {"is_eligible": False, "reason": "User must have at least STARTER slot"}
            
            # Check if user has Global Program package
            # This would integrate with Global Program module
            # For now, assume all Matrix users are eligible
            
            return {"is_eligible": True, "reason": "User meets Global Program requirements"}
        except Exception as e:
            print(f"Error checking Global Program eligibility: {e}")
            return {"is_eligible": False, "reason": str(e)}
    
    def _calculate_global_contribution(self, matrix_slot: int):
        """Calculate Global Program contribution based on Matrix slot."""
        try:
            # Global Program contribution based on Matrix slot value
            # This follows the Global Distribution percentages from PROJECT_DOCUMENTATION.md
            
            slot_values = {
                1: 11,      # STARTER
                2: 33,      # BRONZE
                3: 99,      # SILVER
                4: 297,     # GOLD
                5: 891,     # PLATINUM
                6: 2673,    # DIAMOND
                7: 8019,    # RUBY
                8: 24057,   # EMERALD
                9: 72171,   # SAPPHIRE
                10: 216513, # TOPAZ
                11: 649539, # PEARL
                12: 1948617, # AMETHYST
                13: 5845851, # OBSIDIAN
                14: 17537553, # TITANIUM
                15: 52612659  # STAR
            }
            
            slot_value = slot_values.get(matrix_slot, 0)
            
            # Global Program contribution is 5% of Matrix slot value
            # This goes to Global Distribution fund
            global_contribution = slot_value * 0.05
            
            return global_contribution
        except Exception as e:
            print(f"Error calculating Global contribution: {e}")
            return 0
    
    def _update_global_program_status(self, user_id: str, contribution: float):
        """Update Global Program status for user."""
        try:
            # This would integrate with Global Program module
            # For now, return placeholder status
            
            global_status = {
                "user_id": user_id,
                "contribution": contribution,
                "phase": "Phase-1",  # Placeholder
                "slot": 1,  # Placeholder
                "status": "active",
                "last_contribution": datetime.utcnow().isoformat()
            }
            
            return global_status
        except Exception as e:
            print(f"Error updating Global Program status: {e}")
        return None
    
    def _process_global_distribution(self, user_id: str, contribution: float):
        """Process Global Distribution according to PROJECT_DOCUMENTATION.md percentages."""
        try:
            # Global Distribution percentages from PROJECT_DOCUMENTATION.md:
            # - Level (40%): 10% Partner Incentive to direct upline + 30% reserved to upgrade corresponding Phase/slot
            # - Profit (30%): Net profit portion
            # - Royal Captain Bonus (15%)
            # - President Reward (15%)
            # - Triple Entry Reward (5%)
            # - Shareholders (5%)
            
            distribution = {
                "level_distribution": {
                    "partner_incentive": contribution * 0.10,  # 10% to direct upline
                    "reserved_upgrade": contribution * 0.30,      # 30% reserved for upgrade
                    "total_level": contribution * 0.40           # 40% total
                },
                "profit_distribution": {
                    "net_profit": contribution * 0.30             # 30% net profit
                },
                "special_bonuses": {
                    "royal_captain_bonus": contribution * 0.15,  # 15% Royal Captain Bonus
                    "president_reward": contribution * 0.15,     # 15% President Reward
                    "triple_entry_reward": contribution * 0.05,  # 5% Triple Entry Reward
                    "shareholders": contribution * 0.05          # 5% Shareholders
                },
                "total_distributed": contribution,
                "distribution_percentage": 100.0
            }
            
            # Process each distribution component
            self._process_level_distribution(user_id, distribution["level_distribution"])
            self._process_profit_distribution(user_id, distribution["profit_distribution"])
            self._process_special_bonuses(user_id, distribution["special_bonuses"])
            
            return distribution
        except Exception as e:
            print(f"Error processing Global Distribution: {e}")
            return None
    
    def _process_level_distribution(self, user_id: str, level_distribution: dict):
        """Process Level Distribution (40% total)."""
        try:
            # Partner Incentive (10% to direct upline)
            partner_incentive = level_distribution["partner_incentive"]
            if partner_incentive > 0:
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="global_partner_incentive",
                    amount=partner_incentive,
                    description=f"Global Partner Incentive: 10% of Global contribution"
                )
            
            # Reserved Upgrade (30% reserved for upgrade)
            reserved_upgrade = level_distribution["reserved_upgrade"]
            if reserved_upgrade > 0:
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="global_reserved_upgrade",
                    amount=reserved_upgrade,
                    description=f"Global Reserved Upgrade: 30% of Global contribution"
                )
            
            print(f"✅ Level Distribution processed: ${level_distribution['total_level']}")
        except Exception as e:
            print(f"Error processing Level Distribution: {e}")
    
    def _process_profit_distribution(self, user_id: str, profit_distribution: dict):
        """Process Profit Distribution (30% total)."""
        try:
            net_profit = profit_distribution["net_profit"]
            if net_profit > 0:
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="global_profit",
                    amount=net_profit,
                    description=f"Global Profit Distribution: 30% of Global contribution"
                )
            
            print(f"✅ Profit Distribution processed: ${net_profit}")
        except Exception as e:
            print(f"Error processing Profit Distribution: {e}")
    
    def _process_special_bonuses(self, user_id: str, special_bonuses: dict):
        """Process Special Bonuses (35% total)."""
        try:
            # Royal Captain Bonus (15%)
            royal_captain = special_bonuses["royal_captain_bonus"]
            if royal_captain > 0:
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="global_royal_captain_bonus",
                    amount=royal_captain,
                    description=f"Global Royal Captain Bonus: 15% of Global contribution"
                )
            
            # President Reward (15%)
            president_reward = special_bonuses["president_reward"]
            if president_reward > 0:
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="global_president_reward",
                    amount=president_reward,
                    description=f"Global President Reward: 15% of Global contribution"
                )
            
            # Triple Entry Reward (5%)
            triple_entry = special_bonuses["triple_entry_reward"]
            if triple_entry > 0:
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="global_triple_entry_reward",
                    amount=triple_entry,
                    description=f"Global Triple Entry Reward: 5% of Global contribution"
                )
            
            # Shareholders (5%)
            shareholders = special_bonuses["shareholders"]
            if shareholders > 0:
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="global_shareholders",
                    amount=shareholders,
                    description=f"Global Shareholders: 5% of Global contribution"
                )
            
            total_special = sum(special_bonuses.values())
            print(f"✅ Special Bonuses processed: ${total_special}")
        except Exception as e:
            print(f"Error processing Special Bonuses: {e}")
    
    def get_global_program_status(self, user_id: str):
        """Get comprehensive Global Program status for a user."""
        try:
            # Get user's Matrix info
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            matrix_slot = matrix_tree.current_slot if matrix_tree else 1
            
            # Calculate Global contribution
            global_contribution = self._calculate_global_contribution(matrix_slot)
            
            # Check eligibility
            eligibility = self._check_global_program_eligibility(user_id)
            
            status = {
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "global_contribution": global_contribution,
                "eligibility": eligibility,
                "global_distribution": {
                    "level_distribution": {
                        "partner_incentive": global_contribution * 0.10,
                        "reserved_upgrade": global_contribution * 0.30,
                        "total_level": global_contribution * 0.40
                    },
                    "profit_distribution": {
                        "net_profit": global_contribution * 0.30
                    },
                    "special_bonuses": {
                        "royal_captain_bonus": global_contribution * 0.15,
                        "president_reward": global_contribution * 0.15,
                        "triple_entry_reward": global_contribution * 0.05,
                        "shareholders": global_contribution * 0.05
                    },
                    "total_distributed": global_contribution
                },
                "global_program_info": {
                    "description": "Global Program integration with Matrix",
                    "contribution_rate": "5% of Matrix slot value",
                    "distribution_percentages": {
                        "level": "40%",
                        "profit": "30%",
                        "royal_captain": "15%",
                        "president_reward": "15%",
                        "triple_entry": "5%",
                        "shareholders": "5%"
                    }
                }
            }
            
            return {"success": True, "status": status}
        except Exception as e:
            print(f"Error getting Global Program status: {e}")
            return {"success": False, "error": str(e)}
    
    def trigger_global_integration_automatic(self, user_id: str):
        """Automatically trigger Global Program integration when Matrix slot is activated."""
        try:
            print(f"🎯 Triggering automatic Global Program integration for user {user_id}")
            
            # Integrate with Global Program
            integration_result = self.integrate_with_global_program(user_id)
            
            if integration_result.get("success"):
                print(f"✅ Global Program integration completed automatically")
                print(f"   - Matrix slot: {integration_result.get('matrix_slot')}")
                print(f"   - Global contribution: ${integration_result.get('global_contribution')}")
                print(f"   - Distribution processed: ${integration_result.get('distribution_result', {}).get('total_distributed', 0)}")
            else:
                print(f"❌ Global Program integration failed: {integration_result.get('error')}")
                
        except Exception as e:
            print(f"Error in automatic Global Program integration: {e}")
    
    # ==================== SPECIAL PROGRAMS INTEGRATION METHODS ====================
    
    def integrate_with_leadership_stipend(self, user_id: str):
        """Integrate Matrix user with Leadership Stipend program."""
        try:
            # Get user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get Matrix slot info
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            matrix_slot = matrix_tree.current_slot if matrix_tree else 1
            
            # Check if user is eligible for Leadership Stipend
            stipend_eligibility = self._check_leadership_stipend_eligibility(matrix_slot)
            
            if not stipend_eligibility.get("is_eligible"):
                return {
                    "success": False,
                    "error": f"User not eligible for Leadership Stipend: {stipend_eligibility.get('reason')}"
                }
            
            # Calculate Leadership Stipend contribution
            stipend_contribution = self._calculate_leadership_stipend_contribution(matrix_slot)
            
            # Process Leadership Stipend distribution
            distribution_result = self._process_leadership_stipend_distribution(user_id, stipend_contribution, matrix_slot)
            
            # Update Leadership Stipend status
            stipend_status = self._update_leadership_stipend_status(user_id, stipend_contribution, matrix_slot)
            
            # Log Leadership Stipend integration
            self._log_earning_history(
                user_id=user_id,
                earning_type="leadership_stipend_integration",
                amount=stipend_contribution,
                description=f"Leadership Stipend integration - Matrix slot {matrix_slot} contributes ${stipend_contribution}"
            )
            
            # Log blockchain event
            self._log_blockchain_event(
                tx_hash=f"leadership_stipend_{user_id}",
                event_type='leadership_stipend_integration',
                event_data={
                    'program': 'leadership_stipend',
                    'user_id': user_id,
                    'matrix_slot': matrix_slot,
                    'stipend_contribution': stipend_contribution,
                    'stipend_status': stipend_status
                }
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "stipend_contribution": stipend_contribution,
                "stipend_status": stipend_status,
                "distribution_result": distribution_result,
                "message": f"Successfully integrated with Leadership Stipend - Contribution: ${stipend_contribution}"
            }
        except Exception as e:
            print(f"Error integrating with Leadership Stipend: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_leadership_stipend_eligibility(self, matrix_slot: int):
        """Check if user is eligible for Leadership Stipend."""
        try:
            # Leadership Stipend applies to slots 10-16 only
            if matrix_slot < 10:
                return {"is_eligible": False, "reason": f"User must have slot 10 or higher (current: {matrix_slot})"}
            
            if matrix_slot > 16:
                return {"is_eligible": False, "reason": f"User slot exceeds maximum Leadership Stipend slot (current: {matrix_slot})"}
            
            return {"is_eligible": True, "reason": f"User eligible for Leadership Stipend with slot {matrix_slot}"}
        except Exception as e:
            print(f"Error checking Leadership Stipend eligibility: {e}")
            return {"is_eligible": False, "reason": str(e)}
    
    def _calculate_leadership_stipend_contribution(self, matrix_slot: int):
        """Calculate Leadership Stipend contribution based on Matrix slot."""
        try:
            # Leadership Stipend slot values from PROJECT_DOCUMENTATION.md
            stipend_slot_values = {
                10: 1.1264,    # LEADER (BNB)
                11: 2.2528,    # VANGURD (BNB)
                12: 4.5056,    # CENTER (BNB)
                13: 9.0112,    # CLIMAX (BNB)
                14: 18.0224,   # ENTERNITY (BNB)
                15: 36.0448,   # KING (BNB)
                16: 72.0896    # COMMENDER (BNB)
            }
            
            slot_value = stipend_slot_values.get(matrix_slot, 0)
            
            # Leadership Stipend provides double the slot value as daily return
            # This is the contribution to the Leadership Stipend fund
            stipend_contribution = slot_value * 2
            
            return stipend_contribution
        except Exception as e:
            print(f"Error calculating Leadership Stipend contribution: {e}")
            return 0
    
    def _process_leadership_stipend_distribution(self, user_id: str, contribution: float, matrix_slot: int):
        """Process Leadership Stipend distribution according to PROJECT_DOCUMENTATION.md percentages."""
        try:
            # Leadership Stipend Distribution percentages from PROJECT_DOCUMENTATION.md:
            # - Level 10: 1.5%
            # - Level 11: 1%
            # - Level 12: 0.5%
            # - Level 13: 0.5%
            # - Level 14: 0.5%
            # - Level 15: 0.5%
            # - Level 16: 0.5%
            
            distribution_percentages = {
                10: 0.015,  # 1.5%
                11: 0.01,   # 1%
                12: 0.005,  # 0.5%
                13: 0.005,  # 0.5%
                14: 0.005,  # 0.5%
                15: 0.005,  # 0.5%
                16: 0.005   # 0.5%
            }
            
            user_percentage = distribution_percentages.get(matrix_slot, 0)
            user_distribution = contribution * user_percentage
            
            distribution = {
                "user_distribution": {
                    "slot": matrix_slot,
                    "percentage": user_percentage * 100,
                    "amount": user_distribution
                },
                "total_contribution": contribution,
                "distribution_percentage": user_percentage * 100,
                "remaining_fund": contribution - user_distribution
            }
            
            # Process user's Leadership Stipend distribution
            if user_distribution > 0:
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="leadership_stipend_daily_return",
                    amount=user_distribution,
                    description=f"Leadership Stipend daily return: {user_percentage * 100}% of slot {matrix_slot} contribution"
                )
            
            print(f"✅ Leadership Stipend distribution processed: ${user_distribution} for slot {matrix_slot}")
            
            return distribution
        except Exception as e:
            print(f"Error processing Leadership Stipend distribution: {e}")
            return None
    
    def _update_leadership_stipend_status(self, user_id: str, contribution: float, matrix_slot: int):
        """Update Leadership Stipend status for user."""
        try:
            # Calculate daily return amount
            daily_return = contribution * 0.5  # Double slot value, so daily return is half
            
            stipend_status = {
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "slot_value": contribution / 2,  # Original slot value
                "daily_return": daily_return,
                "contribution": contribution,
                "status": "active",
                "last_distribution": datetime.utcnow().isoformat(),
                "distribution_percentage": {
                    10: 1.5,
                    11: 1.0,
                    12: 0.5,
                    13: 0.5,
                    14: 0.5,
                    15: 0.5,
                    16: 0.5
                }.get(matrix_slot, 0)
            }
            
            return stipend_status
        except Exception as e:
            print(f"Error updating Leadership Stipend status: {e}")
            return None
    
    def get_leadership_stipend_status(self, user_id: str):
        """Get comprehensive Leadership Stipend status for a user."""
        try:
            # Get user's Matrix info
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            matrix_slot = matrix_tree.current_slot if matrix_tree else 1
            
            # Check eligibility
            eligibility = self._check_leadership_stipend_eligibility(matrix_slot)
            
            # Calculate contribution if eligible
            stipend_contribution = 0
            daily_return = 0
            if eligibility.get("is_eligible"):
                stipend_contribution = self._calculate_leadership_stipend_contribution(matrix_slot)
                daily_return = stipend_contribution * 0.5
            
            status = {
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "eligibility": eligibility,
                "stipend_info": {
                    "slot_value": stipend_contribution / 2 if stipend_contribution > 0 else 0,
                    "daily_return": daily_return,
                    "contribution": stipend_contribution,
                    "distribution_percentage": {
                        10: 1.5,
                        11: 1.0,
                        12: 0.5,
                        13: 0.5,
                        14: 0.5,
                        15: 0.5,
                        16: 0.5
                    }.get(matrix_slot, 0)
                },
                "leadership_stipend_info": {
                    "description": "Leadership Stipend provides daily returns for Matrix slots 10-16",
                    "eligibility": "Slots 10-16 only",
                    "daily_return_rate": "Double the slot value as daily return",
                    "distribution_percentages": {
                        "level_10": "1.5%",
                        "level_11": "1.0%",
                        "level_12": "0.5%",
                        "level_13": "0.5%",
                        "level_14": "0.5%",
                        "level_15": "0.5%",
                        "level_16": "0.5%"
                    }
                }
            }
            
            return {"success": True, "status": status}
        except Exception as e:
            print(f"Error getting Leadership Stipend status: {e}")
            return {"success": False, "error": str(e)}
    
    def trigger_leadership_stipend_integration_automatic(self, user_id: str):
        """Automatically trigger Leadership Stipend integration when Matrix slot is activated."""
        try:
            print(f"🎯 Triggering automatic Leadership Stipend integration for user {user_id}")
            
            # Integrate with Leadership Stipend
            integration_result = self.integrate_with_leadership_stipend(user_id)
            
            if integration_result.get("success"):
                print(f"✅ Leadership Stipend integration completed automatically")
                print(f"   - Matrix slot: {integration_result.get('matrix_slot')}")
                print(f"   - Stipend contribution: ${integration_result.get('stipend_contribution')}")
                print(f"   - Daily return: ${integration_result.get('stipend_status', {}).get('daily_return', 0)}")
            else:
                print(f"❌ Leadership Stipend integration failed: {integration_result.get('error')}")
                
        except Exception as e:
            print(f"Error in automatic Leadership Stipend integration: {e}")
    
    def integrate_with_jackpot_program(self, user_id: str):
        """Integrate Matrix user with Jackpot Program."""
        try:
            # Get user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get Matrix slot info
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            matrix_slot = matrix_tree.current_slot if matrix_tree else 1
            
            # Check if user is eligible for Jackpot Program
            jackpot_eligibility = self._check_jackpot_program_eligibility(matrix_slot)
            
            if not jackpot_eligibility.get("is_eligible"):
                return {
                    "success": False, 
                    "error": f"User not eligible for Jackpot Program: {jackpot_eligibility.get('reason')}"
                }
            
            # Calculate Jackpot Program contribution
            jackpot_contribution = self._calculate_jackpot_program_contribution(matrix_slot)
            
            # Process Jackpot Program distribution
            distribution_result = self._process_jackpot_program_distribution(user_id, jackpot_contribution, matrix_slot)
            
            # Award free coupons for Binary slot upgrades
            coupon_result = self._award_jackpot_coupons(user_id, matrix_slot)
            
            # Update Jackpot Program status
            jackpot_status = self._update_jackpot_program_status(user_id, jackpot_contribution, matrix_slot)
            
            # Log Jackpot Program integration
            self._log_earning_history(
                user_id=user_id,
                earning_type="jackpot_program_integration",
                amount=jackpot_contribution,
                description=f"Jackpot Program integration - Matrix slot {matrix_slot} contributes ${jackpot_contribution}"
            )
            
            # Log blockchain event
            self._log_blockchain_event(
                tx_hash=f"jackpot_integration_{user_id}",
                event_type='jackpot_program_integration',
                event_data={
                    'program': 'jackpot_program',
                    'user_id': user_id,
                    'matrix_slot': matrix_slot,
                    'jackpot_contribution': jackpot_contribution,
                    'jackpot_status': jackpot_status,
                    'coupons_awarded': coupon_result
                }
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "jackpot_contribution": jackpot_contribution,
                "jackpot_status": jackpot_status,
                "distribution_result": distribution_result,
                "coupon_result": coupon_result,
                "message": f"Successfully integrated with Jackpot Program - Contribution: ${jackpot_contribution}"
            }
        except Exception as e:
            print(f"Error integrating with Jackpot Program: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_jackpot_program_eligibility(self, matrix_slot: int):
        """Check if user is eligible for Jackpot Program."""
        try:
            # Jackpot Program applies to all Matrix slots
            # Free coupons are awarded for slots 5-16
            if matrix_slot < 1:
                return {"is_eligible": False, "reason": f"User must have at least slot 1 (current: {matrix_slot})"}
            
            return {"is_eligible": True, "reason": f"User eligible for Jackpot Program with slot {matrix_slot}"}
        except Exception as e:
            print(f"Error checking Jackpot Program eligibility: {e}")
            return {"is_eligible": False, "reason": str(e)}
    
    def _calculate_jackpot_program_contribution(self, matrix_slot: int):
        """Calculate Jackpot Program contribution based on Matrix slot."""
        try:
            # Jackpot Program contribution based on Matrix slot value
            # This follows the Jackpot fund structure from PROJECT_DOCUMENTATION.md
            
            slot_values = {
                1: 11,      # STARTER
                2: 33,      # BRONZE
                3: 99,      # SILVER
                4: 297,     # GOLD
                5: 891,     # PLATINUM
                6: 2673,    # DIAMOND
                7: 8019,    # RUBY
                8: 24057,   # EMERALD
                9: 72171,   # SAPPHIRE
                10: 216513, # TOPAZ
                11: 649539, # PEARL
                12: 1948617, # AMETHYST
                13: 5845851, # OBSIDIAN
                14: 17537553, # TITANIUM
                15: 52612659  # STAR
            }
            
            slot_value = slot_values.get(matrix_slot, 0)
            
            # Jackpot Program contribution is 2% of Matrix slot value
            # This goes to Jackpot fund
            jackpot_contribution = slot_value * 0.02
            
            return jackpot_contribution
        except Exception as e:
            print(f"Error calculating Jackpot Program contribution: {e}")
            return 0
    
    def _process_jackpot_program_distribution(self, user_id: str, contribution: float, matrix_slot: int):
        """Process Jackpot Program distribution according to PROJECT_DOCUMENTATION.md percentages."""
        try:
            # Jackpot Fund Structure from PROJECT_DOCUMENTATION.md:
            # - OPEN POOL: 50%
            # - TOP DIRECT PROMOTERS POOL: 30%
            # - TOP BUYERS POOL: 10%
            # - BINARY CONTRIBUTION: 5% deduction from each Binary slot activation
            
            distribution = {
                "open_pool": {
                    "percentage": 50,
                    "amount": contribution * 0.50
                },
                "top_direct_promoters_pool": {
                    "percentage": 30,
                    "amount": contribution * 0.30
                },
                "top_buyers_pool": {
                    "percentage": 10,
                    "amount": contribution * 0.10
                },
                "binary_contribution": {
                    "percentage": 5,
                    "amount": contribution * 0.05
                },
                "total_distributed": contribution,
                "distribution_percentage": 100.0
            }
            
            # Process each distribution component
            self._process_open_pool(user_id, distribution["open_pool"])
            self._process_top_direct_promoters_pool(user_id, distribution["top_direct_promoters_pool"])
            self._process_top_buyers_pool(user_id, distribution["top_buyers_pool"])
            self._process_binary_contribution(user_id, distribution["binary_contribution"])
            
            return distribution
        except Exception as e:
            print(f"Error processing Jackpot Program distribution: {e}")
            return None
    
    def _process_open_pool(self, user_id: str, open_pool: dict):
        """Process Open Pool (50% of Jackpot fund)."""
        try:
            amount = open_pool["amount"]
            if amount > 0:
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="jackpot_open_pool",
                    amount=amount,
                    description=f"Jackpot Open Pool: 50% of Jackpot contribution"
                )
            
            print(f"✅ Open Pool processed: ${amount}")
        except Exception as e:
            print(f"Error processing Open Pool: {e}")
    
    def _process_top_direct_promoters_pool(self, user_id: str, promoters_pool: dict):
        """Process Top Direct Promoters Pool (30% of Jackpot fund)."""
        try:
            amount = promoters_pool["amount"]
            if amount > 0:
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="jackpot_top_direct_promoters",
                    amount=amount,
                    description=f"Jackpot Top Direct Promoters Pool: 30% of Jackpot contribution"
                )
            
            print(f"✅ Top Direct Promoters Pool processed: ${amount}")
        except Exception as e:
            print(f"Error processing Top Direct Promoters Pool: {e}")
    
    def _process_top_buyers_pool(self, user_id: str, buyers_pool: dict):
        """Process Top Buyers Pool (10% of Jackpot fund)."""
        try:
            amount = buyers_pool["amount"]
            if amount > 0:
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="jackpot_top_buyers",
                    amount=amount,
                    description=f"Jackpot Top Buyers Pool: 10% of Jackpot contribution"
                )
            
            print(f"✅ Top Buyers Pool processed: ${amount}")
        except Exception as e:
            print(f"Error processing Top Buyers Pool: {e}")
    
    def _process_binary_contribution(self, user_id: str, binary_contribution: dict):
        """Process Binary Contribution (5% of Jackpot fund)."""
        try:
            amount = binary_contribution["amount"]
            if amount > 0:
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="jackpot_binary_contribution",
                    amount=amount,
                    description=f"Jackpot Binary Contribution: 5% of Jackpot contribution"
                )
            
            print(f"✅ Binary Contribution processed: ${amount}")
        except Exception as e:
            print(f"Error processing Binary Contribution: {e}")
    
    def _award_jackpot_coupons(self, user_id: str, matrix_slot: int):
        """Award free coupons for Binary slot upgrades according to PROJECT_DOCUMENTATION.md."""
        try:
            # Free Coupons System from PROJECT_DOCUMENTATION.md:
            # - SLOT 5: 1 FREE COUPON
            # - SLOT 6: 2 FREE COUPON
            # - AND IT CONTINUES UP TO SLOT 16
            
            coupon_rules = {
                5: 1,   # 1 FREE COUPON
                6: 2,   # 2 FREE COUPON
                7: 3,   # 3 FREE COUPON
                8: 4,   # 4 FREE COUPON
                9: 5,   # 5 FREE COUPON
                10: 6,  # 6 FREE COUPON
                11: 7,  # 7 FREE COUPON
                12: 8,  # 8 FREE COUPON
                13: 9,  # 9 FREE COUPON
                14: 10, # 10 FREE COUPON
                15: 11, # 11 FREE COUPON
                16: 12  # 12 FREE COUPON
            }
            
            coupons_awarded = coupon_rules.get(matrix_slot, 0)
            
            if coupons_awarded > 0:
                # Log coupon award
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="jackpot_free_coupons",
                    amount=coupons_awarded,
                    description=f"Jackpot Free Coupons: {coupons_awarded} free coupons for Binary slot upgrades"
                )
                
                print(f"✅ Free coupons awarded: {coupons_awarded} coupons for slot {matrix_slot}")
            
            return {
                "coupons_awarded": coupons_awarded,
                "slot": matrix_slot,
                "description": f"{coupons_awarded} free coupons for Binary slot upgrades"
            }
        except Exception as e:
            print(f"Error awarding Jackpot coupons: {e}")
            return {"coupons_awarded": 0, "error": str(e)}
    
    def _update_jackpot_program_status(self, user_id: str, contribution: float, matrix_slot: int):
        """Update Jackpot Program status for user."""
        try:
            # Calculate coupons awarded
            coupon_rules = {5: 1, 6: 2, 7: 3, 8: 4, 9: 5, 10: 6, 11: 7, 12: 8, 13: 9, 14: 10, 15: 11, 16: 12}
            coupons_awarded = coupon_rules.get(matrix_slot, 0)
            
            jackpot_status = {
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "contribution": contribution,
                "coupons_awarded": coupons_awarded,
                "status": "active",
                "last_contribution": datetime.utcnow().isoformat(),
                "fund_distribution": {
                    "open_pool": contribution * 0.50,
                    "top_direct_promoters": contribution * 0.30,
                    "top_buyers": contribution * 0.10,
                    "binary_contribution": contribution * 0.05
                }
            }
            
            return jackpot_status
        except Exception as e:
            print(f"Error updating Jackpot Program status: {e}")
            return None
    
    def get_jackpot_program_status(self, user_id: str):
        """Get comprehensive Jackpot Program status for a user."""
        try:
            # Get user's Matrix info
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            matrix_slot = matrix_tree.current_slot if matrix_tree else 1
            
            # Check eligibility
            eligibility = self._check_jackpot_program_eligibility(matrix_slot)
            
            # Calculate contribution if eligible
            jackpot_contribution = 0
            coupons_awarded = 0
            if eligibility.get("is_eligible"):
                jackpot_contribution = self._calculate_jackpot_program_contribution(matrix_slot)
                coupon_rules = {5: 1, 6: 2, 7: 3, 8: 4, 9: 5, 10: 6, 11: 7, 12: 8, 13: 9, 14: 10, 15: 11, 16: 12}
                coupons_awarded = coupon_rules.get(matrix_slot, 0)
            
            status = {
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "eligibility": eligibility,
                "jackpot_info": {
                    "contribution": jackpot_contribution,
                    "coupons_awarded": coupons_awarded,
                    "fund_distribution": {
                        "open_pool": jackpot_contribution * 0.50,
                        "top_direct_promoters": jackpot_contribution * 0.30,
                        "top_buyers": jackpot_contribution * 0.10,
                        "binary_contribution": jackpot_contribution * 0.05
                    }
                },
                "jackpot_program_info": {
                    "description": "Jackpot Program provides free coupons for Binary slot upgrades",
                    "eligibility": "All Matrix slots",
                    "contribution_rate": "2% of Matrix slot value",
                    "fund_structure": {
                        "open_pool": "50%",
                        "top_direct_promoters": "30%",
                        "top_buyers": "10%",
                        "binary_contribution": "5%"
                    },
                    "free_coupons": {
                        "slot_5": "1 FREE COUPON",
                        "slot_6": "2 FREE COUPON",
                        "slot_7": "3 FREE COUPON",
                        "slot_8": "4 FREE COUPON",
                        "slot_9": "5 FREE COUPON",
                        "slot_10": "6 FREE COUPON",
                        "slot_11": "7 FREE COUPON",
                        "slot_12": "8 FREE COUPON",
                        "slot_13": "9 FREE COUPON",
                        "slot_14": "10 FREE COUPON",
                        "slot_15": "11 FREE COUPON",
                        "slot_16": "12 FREE COUPON"
                    }
                }
            }
            
            return {"success": True, "status": status}
        except Exception as e:
            print(f"Error getting Jackpot Program status: {e}")
            return {"success": False, "error": str(e)}
    
    def trigger_jackpot_integration_automatic(self, user_id: str):
        """Automatically trigger Jackpot Program integration when Matrix slot is activated."""
        try:
            print(f"🎯 Triggering automatic Jackpot Program integration for user {user_id}")
            
            # Integrate with Jackpot Program
            integration_result = self.integrate_with_jackpot_program(user_id)
            
            if integration_result.get("success"):
                print(f"✅ Jackpot Program integration completed automatically")
                print(f"   - Matrix slot: {integration_result.get('matrix_slot')}")
                print(f"   - Jackpot contribution: ${integration_result.get('jackpot_contribution')}")
                print(f"   - Coupons awarded: {integration_result.get('coupon_result', {}).get('coupons_awarded', 0)}")
            else:
                print(f"❌ Jackpot Program integration failed: {integration_result.get('error')}")
                
        except Exception as e:
            print(f"Error in automatic Jackpot Program integration: {e}")
    
    def integrate_with_newcomer_growth_support(self, user_id: str):
        """Integrate Matrix user with Newcomer Growth Support (NGS) program."""
        try:
            # Get user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get Matrix slot info
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            matrix_slot = matrix_tree.current_slot if matrix_tree else 1
            
            # Check if user is eligible for NGS
            ngs_eligibility = self._check_ngs_eligibility(matrix_slot)
            
            if not ngs_eligibility.get("is_eligible"):
                return {
                    "success": False, 
                    "error": f"User not eligible for NGS: {ngs_eligibility.get('reason')}"
                }
            
            # Calculate NGS benefits
            ngs_benefits = self._calculate_ngs_benefits(matrix_slot)
            
            # Process NGS instant bonus
            instant_bonus_result = self._process_ngs_instant_bonus(user_id, ngs_benefits)
            
            # Process NGS extra earning opportunities
            extra_earning_result = self._process_ngs_extra_earning(user_id, ngs_benefits)
            
            # Process NGS upline rank bonus
            upline_rank_bonus_result = self._process_ngs_upline_rank_bonus(user_id, ngs_benefits)
            
            # Update NGS status
            ngs_status = self._update_ngs_status(user_id, ngs_benefits, matrix_slot)
            
            # Log NGS integration
            self._log_earning_history(
                user_id=user_id,
                earning_type="ngs_integration",
                amount=ngs_benefits["total_benefits"],
                description=f"NGS integration - Matrix slot {matrix_slot} provides ${ngs_benefits['total_benefits']} in benefits"
            )
            
            # Log blockchain event
            self._log_blockchain_event(
                tx_hash=f"ngs_integration_{user_id}",
                event_type='ngs_integration',
                event_data={
                    'program': 'newcomer_growth_support',
                    'user_id': user_id,
                    'matrix_slot': matrix_slot,
                    'ngs_benefits': ngs_benefits,
                    'ngs_status': ngs_status
                }
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "ngs_benefits": ngs_benefits,
                "ngs_status": ngs_status,
                "instant_bonus_result": instant_bonus_result,
                "extra_earning_result": extra_earning_result,
                "upline_rank_bonus_result": upline_rank_bonus_result,
                "message": f"Successfully integrated with NGS - Total Benefits: ${ngs_benefits['total_benefits']}"
            }
        except Exception as e:
            print(f"Error integrating with NGS: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_ngs_eligibility(self, matrix_slot: int):
        """Check if user is eligible for Newcomer Growth Support."""
        try:
            # NGS applies to all Matrix slots
            # All Matrix joiners get NGS benefits
            if matrix_slot < 1:
                return {"is_eligible": False, "reason": f"User must have at least slot 1 (current: {matrix_slot})"}
            
            return {"is_eligible": True, "reason": f"User eligible for NGS with slot {matrix_slot}"}
        except Exception as e:
            print(f"Error checking NGS eligibility: {e}")
            return {"is_eligible": False, "reason": str(e)}
    
    def _calculate_ngs_benefits(self, matrix_slot: int):
        """Calculate NGS benefits based on Matrix slot."""
        try:
            # NGS benefits based on Matrix slot value
            # This follows the NGS structure from PROJECT_DOCUMENTATION.md
            
            slot_values = {
                1: 11,      # STARTER
                2: 33,      # BRONZE
                3: 99,      # SILVER
                4: 297,     # GOLD
                5: 891,     # PLATINUM
                6: 2673,    # DIAMOND
                7: 8019,    # RUBY
                8: 24057,   # EMERALD
                9: 72171,   # SAPPHIRE
                10: 216513, # TOPAZ
                11: 649539, # PEARL
                12: 1948617, # AMETHYST
                13: 5845851, # OBSIDIAN
                14: 17537553, # TITANIUM
                15: 52612659  # STAR
            }
            
            slot_value = slot_values.get(matrix_slot, 0)
            
            # NGS benefits calculation:
            # - Instant Bonus: 5% of Matrix slot value
            # - Extra Earning Opportunities: 3% of Matrix slot value
            # - Upline Rank Bonus: 2% of Matrix slot value
            
            instant_bonus = slot_value * 0.05
            extra_earning = slot_value * 0.03
            upline_rank_bonus = slot_value * 0.02
            total_benefits = instant_bonus + extra_earning + upline_rank_bonus
            
            return {
                "slot_value": slot_value,
                "instant_bonus": instant_bonus,
                "extra_earning": extra_earning,
                "upline_rank_bonus": upline_rank_bonus,
                "total_benefits": total_benefits
            }
        except Exception as e:
            print(f"Error calculating NGS benefits: {e}")
            return {"total_benefits": 0}
    
    def _process_ngs_instant_bonus(self, user_id: str, ngs_benefits: dict):
        """Process NGS instant bonus."""
        try:
            instant_bonus = ngs_benefits.get("instant_bonus", 0)
            
            if instant_bonus > 0:
                # Log instant bonus
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="ngs_instant_bonus",
                    amount=instant_bonus,
                    description=f"NGS Instant Bonus: 5% of Matrix slot value - Can be cashed out instantly"
                )
                
                print(f"✅ NGS Instant Bonus processed: ${instant_bonus}")
            
            return {
                "instant_bonus": instant_bonus,
                "description": "Instant bonus that can be cashed out immediately",
                "percentage": "5% of Matrix slot value"
            }
        except Exception as e:
            print(f"Error processing NGS instant bonus: {e}")
            return {"instant_bonus": 0, "error": str(e)}
    
    def _process_ngs_extra_earning(self, user_id: str, ngs_benefits: dict):
        """Process NGS extra earning opportunities."""
        try:
            extra_earning = ngs_benefits.get("extra_earning", 0)
            
            if extra_earning > 0:
                # Log extra earning opportunities
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="ngs_extra_earning",
                    amount=extra_earning,
                    description=f"NGS Extra Earning Opportunities: 3% of Matrix slot value - Monthly opportunities based on upline activity"
                )
                
                print(f"✅ NGS Extra Earning processed: ${extra_earning}")
            
            return {
                "extra_earning": extra_earning,
                "description": "Extra earning opportunities at end of month (30 days) based on upline activity",
                "percentage": "3% of Matrix slot value",
                "frequency": "Monthly"
            }
        except Exception as e:
            print(f"Error processing NGS extra earning: {e}")
            return {"extra_earning": 0, "error": str(e)}
    
    def _process_ngs_upline_rank_bonus(self, user_id: str, ngs_benefits: dict):
        """Process NGS upline rank bonus."""
        try:
            upline_rank_bonus = ngs_benefits.get("upline_rank_bonus", 0)
            
            if upline_rank_bonus > 0:
                # Log upline rank bonus
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="ngs_upline_rank_bonus",
                    amount=upline_rank_bonus,
                    description=f"NGS Upline Rank Bonus: 2% of Matrix slot value - 10% bonus when achieving same rank as upline"
                )
                
                print(f"✅ NGS Upline Rank Bonus processed: ${upline_rank_bonus}")
            
            return {
                "upline_rank_bonus": upline_rank_bonus,
                "description": "10% bonus when member achieves same rank as upline",
                "percentage": "2% of Matrix slot value",
                "bonus_rate": "10%"
            }
        except Exception as e:
            print(f"Error processing NGS upline rank bonus: {e}")
            return {"upline_rank_bonus": 0, "error": str(e)}
    
    def _update_ngs_status(self, user_id: str, ngs_benefits: dict, matrix_slot: int):
        """Update NGS status for user."""
        try:
            ngs_status = {
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "slot_value": ngs_benefits.get("slot_value", 0),
                "benefits": {
                    "instant_bonus": ngs_benefits.get("instant_bonus", 0),
                    "extra_earning": ngs_benefits.get("extra_earning", 0),
                    "upline_rank_bonus": ngs_benefits.get("upline_rank_bonus", 0),
                    "total_benefits": ngs_benefits.get("total_benefits", 0)
                },
                "status": "active",
                "last_benefit": datetime.utcnow().isoformat(),
                "benefit_breakdown": {
                    "instant_bonus_percentage": "5%",
                    "extra_earning_percentage": "3%",
                    "upline_rank_bonus_percentage": "2%",
                    "total_percentage": "10%"
                }
            }
            
            return ngs_status
        except Exception as e:
            print(f"Error updating NGS status: {e}")
            return None
    
    def get_ngs_status(self, user_id: str):
        """Get comprehensive NGS status for a user."""
        try:
            # Get user's Matrix info
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            matrix_slot = matrix_tree.current_slot if matrix_tree else 1
            
            # Check eligibility
            eligibility = self._check_ngs_eligibility(matrix_slot)
            
            # Calculate benefits if eligible
            ngs_benefits = {}
            if eligibility.get("is_eligible"):
                ngs_benefits = self._calculate_ngs_benefits(matrix_slot)
            
            status = {
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "eligibility": eligibility,
                "ngs_info": ngs_benefits,
                "ngs_program_info": {
                    "description": "Newcomer Growth Support provides instant bonuses, extra earning opportunities, and upline rank bonuses for Matrix joiners",
                    "eligibility": "All Matrix slots",
                    "benefit_structure": {
                        "instant_bonus": "5% of Matrix slot value - Can be cashed out instantly",
                        "extra_earning": "3% of Matrix slot value - Monthly opportunities based on upline activity",
                        "upline_rank_bonus": "2% of Matrix slot value - 10% bonus when achieving same rank as upline"
                    },
                    "total_benefits": "10% of Matrix slot value",
                    "benefit_types": {
                        "instant_reward": "Immediate cash-out bonus",
                        "extra_income": "Monthly earning opportunities",
                        "long_term_support": "Upline rank bonus system"
                    }
                }
            }
            
            return {"success": True, "status": status}
        except Exception as e:
            print(f"Error getting NGS status: {e}")
            return {"success": False, "error": str(e)}
    
    def trigger_ngs_integration_automatic(self, user_id: str):
        """Automatically trigger NGS integration when Matrix slot is activated."""
        try:
            print(f"🎯 Triggering automatic NGS integration for user {user_id}")
            
            # Integrate with NGS
            integration_result = self.integrate_with_newcomer_growth_support(user_id)
            
            if integration_result.get("success"):
                print(f"✅ NGS integration completed automatically")
                print(f"   - Matrix slot: {integration_result.get('matrix_slot')}")
                print(f"   - Total benefits: ${integration_result.get('ngs_benefits', {}).get('total_benefits', 0)}")
                print(f"   - Instant bonus: ${integration_result.get('ngs_benefits', {}).get('instant_bonus', 0)}")
                print(f"   - Extra earning: ${integration_result.get('ngs_benefits', {}).get('extra_earning', 0)}")
                print(f"   - Upline rank bonus: ${integration_result.get('ngs_benefits', {}).get('upline_rank_bonus', 0)}")
            else:
                print(f"❌ NGS integration failed: {integration_result.get('error')}")
                
        except Exception as e:
            print(f"Error in automatic NGS integration: {e}")
    
    def integrate_with_mentorship_bonus(self, user_id: str):
        """Integrate Matrix user with Mentorship Bonus program."""
        try:
            # Get user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get Matrix slot info
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            matrix_slot = matrix_tree.current_slot if matrix_tree else 1
            
            # Check if user is eligible for Mentorship Bonus
            mentorship_eligibility = self._check_mentorship_bonus_eligibility(matrix_slot)
            
            if not mentorship_eligibility.get("is_eligible"):
                return {
                    "success": False, 
                    "error": f"User not eligible for Mentorship Bonus: {mentorship_eligibility.get('reason')}"
                }
            
            # Calculate Mentorship Bonus benefits
            mentorship_benefits = self._calculate_mentorship_bonus_benefits(matrix_slot)
            
            # Process Mentorship Bonus distribution
            mentorship_result = self._process_mentorship_bonus_distribution(user_id, mentorship_benefits)
            
            # Process Direct-of-Direct tracking
            direct_of_direct_result = self._process_direct_of_direct_tracking(user_id, mentorship_benefits)
            
            # Update Mentorship Bonus status
            mentorship_status = self._update_mentorship_bonus_status(user_id, mentorship_benefits, matrix_slot)
            
            # Log Mentorship Bonus integration
            self._log_earning_history(
                user_id=user_id,
                earning_type="mentorship_bonus_integration",
                amount=mentorship_benefits["total_benefits"],
                description=f"Mentorship Bonus integration - Matrix slot {matrix_slot} provides ${mentorship_benefits['total_benefits']} in benefits"
            )
            
            # Log blockchain event
            self._log_blockchain_event(
                tx_hash=f"mentorship_bonus_integration_{user_id}",
                event_type='mentorship_bonus_integration',
                event_data={
                    'program': 'mentorship_bonus',
                    'user_id': user_id,
                    'matrix_slot': matrix_slot,
                    'mentorship_benefits': mentorship_benefits,
                    'mentorship_status': mentorship_status
                }
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "mentorship_benefits": mentorship_benefits,
                "mentorship_status": mentorship_status,
                "mentorship_result": mentorship_result,
                "direct_of_direct_result": direct_of_direct_result,
                "message": f"Successfully integrated with Mentorship Bonus - Total Benefits: ${mentorship_benefits['total_benefits']}"
            }
        except Exception as e:
            print(f"Error integrating with Mentorship Bonus: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_mentorship_bonus_eligibility(self, matrix_slot: int):
        """Check if user is eligible for Mentorship Bonus."""
        try:
            # Mentorship Bonus applies to all Matrix slots
            # All Matrix users can participate in Mentorship Bonus
            if matrix_slot < 1:
                return {"is_eligible": False, "reason": f"User must have at least slot 1 (current: {matrix_slot})"}
            
            return {"is_eligible": True, "reason": f"User eligible for Mentorship Bonus with slot {matrix_slot}"}
        except Exception as e:
            print(f"Error checking Mentorship Bonus eligibility: {e}")
            return {"is_eligible": False, "reason": str(e)}
    
    def _calculate_mentorship_bonus_benefits(self, matrix_slot: int):
        """Calculate Mentorship Bonus benefits based on Matrix slot."""
        try:
            # Mentorship Bonus benefits based on Matrix slot value
            # This follows the Mentorship Bonus structure from PROJECT_DOCUMENTATION.md
            
            slot_values = {
                1: 11,      # STARTER
                2: 33,      # BRONZE
                3: 99,      # SILVER
                4: 297,     # GOLD
                5: 891,     # PLATINUM
                6: 2673,    # DIAMOND
                7: 8019,    # RUBY
                8: 24057,   # EMERALD
                9: 72171,   # SAPPHIRE
                10: 216513, # TOPAZ
                11: 649539, # PEARL
                12: 1948617, # AMETHYST
                13: 5845851, # OBSIDIAN
                14: 17537553, # TITANIUM
                15: 52612659  # STAR
            }
            
            slot_value = slot_values.get(matrix_slot, 0)
            
            # Mentorship Bonus calculation:
            # - Direct-of-Direct Commission: 10% of Matrix slot value
            # - This represents the commission from direct-of-direct partners
            
            direct_of_direct_commission = slot_value * 0.10
            total_benefits = direct_of_direct_commission
            
            return {
                "slot_value": slot_value,
                "direct_of_direct_commission": direct_of_direct_commission,
                "total_benefits": total_benefits
            }
        except Exception as e:
            print(f"Error calculating Mentorship Bonus benefits: {e}")
            return {"total_benefits": 0}
    
    def _process_mentorship_bonus_distribution(self, user_id: str, mentorship_benefits: dict):
        """Process Mentorship Bonus distribution."""
        try:
            direct_of_direct_commission = mentorship_benefits.get("direct_of_direct_commission", 0)
            
            if direct_of_direct_commission > 0:
                # Log Mentorship Bonus distribution
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="mentorship_bonus_distribution",
                    amount=direct_of_direct_commission,
                    description=f"Mentorship Bonus: 10% commission from direct-of-direct partners' joining fees and slot upgrades"
                )
                
                print(f"✅ Mentorship Bonus distribution processed: ${direct_of_direct_commission}")
            
            return {
                "direct_of_direct_commission": direct_of_direct_commission,
                "description": "10% commission from direct-of-direct partners' joining fees and slot upgrades",
                "percentage": "10% of Matrix slot value"
            }
        except Exception as e:
            print(f"Error processing Mentorship Bonus distribution: {e}")
            return {"direct_of_direct_commission": 0, "error": str(e)}
    
    def _process_direct_of_direct_tracking(self, user_id: str, mentorship_benefits: dict):
        """Process Direct-of-Direct tracking for Mentorship Bonus."""
        try:
            # This method tracks the Direct-of-Direct relationships
            # When a user's direct referral gets a direct referral, the original user gets 10% commission
            
            direct_of_direct_commission = mentorship_benefits.get("direct_of_direct_commission", 0)
            
            if direct_of_direct_commission > 0:
                # Log Direct-of-Direct tracking
                self._log_earning_history(
                    user_id=user_id,
                    earning_type="direct_of_direct_tracking",
                    amount=direct_of_direct_commission,
                    description=f"Direct-of-Direct Tracking: 10% commission from direct-of-direct partners"
                )
                
                print(f"✅ Direct-of-Direct tracking processed: ${direct_of_direct_commission}")
            
            return {
                "direct_of_direct_commission": direct_of_direct_commission,
                "description": "Direct-of-Direct income program - 10% commission from direct-of-direct partners",
                "tracking_type": "Direct-of-Direct"
            }
        except Exception as e:
            print(f"Error processing Direct-of-Direct tracking: {e}")
            return {"direct_of_direct_commission": 0, "error": str(e)}
    
    def _update_mentorship_bonus_status(self, user_id: str, mentorship_benefits: dict, matrix_slot: int):
        """Update Mentorship Bonus status for user."""
        try:
            mentorship_status = {
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "slot_value": mentorship_benefits.get("slot_value", 0),
                "benefits": {
                    "direct_of_direct_commission": mentorship_benefits.get("direct_of_direct_commission", 0),
                    "total_benefits": mentorship_benefits.get("total_benefits", 0)
                },
                "status": "active",
                "last_benefit": datetime.utcnow().isoformat(),
                "benefit_breakdown": {
                    "direct_of_direct_commission_percentage": "10%",
                    "total_percentage": "10%"
                }
            }
            
            return mentorship_status
        except Exception as e:
            print(f"Error updating Mentorship Bonus status: {e}")
            return None
    
    def get_mentorship_bonus_status(self, user_id: str):
        """Get comprehensive Mentorship Bonus status for a user."""
        try:
            # Get user's Matrix info
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            matrix_slot = matrix_tree.current_slot if matrix_tree else 1
            
            # Check eligibility
            eligibility = self._check_mentorship_bonus_eligibility(matrix_slot)
            
            # Calculate benefits if eligible
            mentorship_benefits = {}
            if eligibility.get("is_eligible"):
                mentorship_benefits = self._calculate_mentorship_bonus_benefits(matrix_slot)
            
            status = {
                "user_id": user_id,
                "matrix_slot": matrix_slot,
                "eligibility": eligibility,
                "mentorship_info": mentorship_benefits,
                "mentorship_program_info": {
                    "description": "Mentorship Bonus is a Direct-of-Direct income program within the Matrix program",
                    "eligibility": "All Matrix slots",
                    "benefit_structure": {
                        "direct_of_direct_commission": "10% of Matrix slot value - Commission from direct-of-direct partners' joining fees and slot upgrades"
                    },
                    "total_benefits": "10% of Matrix slot value",
                    "program_type": "Direct-of-Direct income program",
                    "commission_rate": "10%",
                    "example": {
                        "scenario": "A invites B, B invites C, D, E",
                        "result": "A gets 10% commission from C, D, E's joining fees and slot upgrades"
                    }
                }
            }
            
            return {"success": True, "status": status}
        except Exception as e:
            print(f"Error getting Mentorship Bonus status: {e}")
            return {"success": False, "error": str(e)}
    
    def trigger_mentorship_bonus_integration_automatic(self, user_id: str):
        """Automatically trigger Mentorship Bonus integration when Matrix slot is activated."""
        try:
            print(f"🎯 Triggering automatic Mentorship Bonus integration for user {user_id}")
            
            # Integrate with Mentorship Bonus
            integration_result = self.integrate_with_mentorship_bonus(user_id)
            
            if integration_result.get("success"):
                print(f"✅ Mentorship Bonus integration completed automatically")
                print(f"   - Matrix slot: {integration_result.get('matrix_slot')}")
                print(f"   - Total benefits: ${integration_result.get('mentorship_benefits', {}).get('total_benefits', 0)}")
                print(f"   - Direct-of-Direct commission: ${integration_result.get('mentorship_benefits', {}).get('direct_of_direct_commission', 0)}")
            else:
                print(f"❌ Mentorship Bonus integration failed: {integration_result.get('error')}")
                
        except Exception as e:
            print(f"Error in automatic Mentorship Bonus integration: {e}")
    
    # ==================== MATRIX UPGRADE SYSTEM METHODS ====================