#!/usr/bin/env python3
"""
Matrix Middle 3 Users Rule Service
Handles the 100% earnings from middle 3 members for next slot upgrade
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


class MatrixMiddle3Service:
    """Service for managing Matrix Middle 3 Users Rule"""
    
    def __init__(self):
        self.middle_3_percentage = Decimal('1.00')  # 100% of earnings
    
    def identify_middle_3_users(self, user_id: str, slot_no: int) -> List[Dict[str, Any]]:
        """
        Identify the middle 3 users in Level 2 of the Matrix tree.
        Middle 3 users are positions 4, 5, 6 in Level 2 (one under each Level 1 member).
        """
        try:
            # Get user's matrix tree
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if not matrix_tree:
                return []
            
            # Find Level 2 nodes (positions 4, 5, 6 are middle 3)
            level_2_nodes = []
            for node in matrix_tree.nodes:
                # Generalized logic for infinite levels:
                # Middle child is always the 2nd child (index 1) of any parent.
                # In 0-based indexing with 3 children per node:
                # Level 1: 0, 1(M), 2
                # Level 2: 0,1,2 | 3,4(M),5 | 6,7,8 -> Middle are 1, 4, 7
                # Formula: position % 3 == 1
                if node.level >= 2 and (node.position % 3 == 1):
                    level_2_nodes.append({
                        "user_id": str(node.user_id),
                        "level": node.level,
                        "position": node.position,
                        "placed_at": node.placed_at,
                        "is_active": node.is_active
                    })
            
            return level_2_nodes
            
        except Exception as e:
            print(f"Error identifying middle 3 users: {e}")
            return []
    
    def collect_middle_3_earnings(self, main_user_id: str, slot_no: int, 
                                 earning_amount: Decimal, source_user_id: str, 
                                 tx_hash: str, skip_validation: bool = False) -> Tuple[bool, str]:
        """
        Collect 100% earnings from middle 3 users for next slot upgrade.
        This is triggered when a middle 3 user activates a slot or joins.
        
        Args:
            skip_validation: If True, skip middle-3 validation (caller verified from placement_ctx)
        """
        try:
            if not skip_validation:
                # Check if the earning user is one of the middle 3 users
                middle_3_users = self.identify_middle_3_users(main_user_id, slot_no)
                
                earning_user_in_middle_3 = False
                for middle_user in middle_3_users:
                    if middle_user["user_id"] == source_user_id:
                        earning_user_in_middle_3 = True
                        break
                
                if not earning_user_in_middle_3:
                    return False, "User is not in middle 3 position"
            
            # Add 100% of earnings to main user's reserve fund
            success, message = self._add_to_reserve_fund(
                main_user_id,
                'matrix',
                slot_no,
                earning_amount,
                source_user_id,
                tx_hash
            )
            
            if success:
                # Check if reserve is sufficient for next slot upgrade
                print(f"[MIDDLE3_DEBUG] Checking auto-upgrade for user {main_user_id} after collecting {earning_amount}")
                upgrade_result = self._check_next_slot_upgrade(main_user_id, slot_no)
                print(f"[MIDDLE3_DEBUG] Auto-upgrade check returned: {upgrade_result}")
                return True, f"Collected {earning_amount} from middle 3 user for next slot upgrade"
            else:
                return False, message
                
        except Exception as e:
            return False, f"Error collecting middle 3 earnings: {str(e)}"
    
    def _add_to_reserve_fund(self, user_id: str, program: str, slot_no: int, 
                           amount: Decimal, source_user_id: str, tx_hash: str) -> Tuple[bool, str]:
        """Add funds to user's reserve for next slot upgrade"""
        try:
            # Get current reserve balance
            current_balance = self._get_reserve_balance(user_id, program, slot_no)
            new_balance = current_balance + amount
            
            # Create reserve ledger entry
            reserve_entry = ReserveLedger(
                user_id=ObjectId(user_id),
                program=program,
                slot_no=slot_no,
                amount=amount,
                direction='credit',
                source='middle_3_earnings',
                balance_after=new_balance,
                tx_hash=tx_hash
            )
            reserve_entry.save()
            
            # Update reserve wallet
            self._update_reserve_wallet(user_id, program, new_balance)
            
            return True, f"Added {amount} to reserve fund. New balance: {new_balance}"
            
        except Exception as e:
            return False, f"Error adding to reserve fund: {str(e)}"
    
    def _get_reserve_balance(self, user_id: str, program: str, slot_no: int) -> Decimal:
        """Get current reserve balance for a user's next slot"""
        try:
            # Get the most recent balance from reserve ledger
            latest_entry = ReserveLedger.objects(
                user_id=ObjectId(user_id),
                program=program,
                slot_no=slot_no
            ).order_by('-created_at').first()
            
            if latest_entry:
                return latest_entry.balance_after
            
            return Decimal('0')
            
        except Exception as e:
            print(f"Error getting reserve balance: {e}")
            return Decimal('0')
    
    def _update_reserve_wallet(self, user_id: str, program: str, balance: Decimal):
        """Update user's reserve wallet balance"""
        try:
            wallet = UserWallet.objects(
                user_id=ObjectId(user_id),
                wallet_type='reserve',
                currency='USDT'  # Matrix uses USDT
            ).first()
            
            if wallet:
                wallet.balance = balance
                wallet.last_updated = datetime.utcnow()
                wallet.save()
            else:
                # Create new reserve wallet
                UserWallet(
                    user_id=ObjectId(user_id),
                    wallet_type='reserve',
                    balance=balance,
                    currency='USDT',
                    last_updated=datetime.utcnow()
                ).save()
                
        except Exception as e:
            print(f"Error updating reserve wallet: {e}")
    
    def _check_next_slot_upgrade(self, user_id: str, current_slot: int):
        """Check if reserve balance is sufficient for next slot upgrade"""
        try:
            print(f"[MIDDLE3_DEBUG] _check_next_slot_upgrade called: user={user_id}, current_slot={current_slot}")
            # Get next slot information
            next_slot_no = current_slot + 1
            next_slot_catalog = SlotCatalog.objects(
                program='matrix',
                slot_no=next_slot_no,
                is_active=True
            ).first()
            
            if not next_slot_catalog:
                print(f"[MIDDLE3_DEBUG] No catalog found for slot {next_slot_no}")
                return False
            
            next_slot_cost = next_slot_catalog.price
            reserve_balance = self._get_reserve_balance(user_id, 'matrix', current_slot)
            
            print(f"[MIDDLE3_DEBUG] Reserve check: balance={reserve_balance}, cost={next_slot_cost}, sufficient={reserve_balance >= next_slot_cost}")
            
            # Check if reserve is sufficient
            if reserve_balance >= next_slot_cost:
                # Auto-upgrade next slot
                result = self._auto_upgrade_slot(user_id, next_slot_no, next_slot_cost, reserve_balance)
                return result
            else:
                print(f"[MIDDLE3_DEBUG] Insufficient reserve: {reserve_balance} < {next_slot_cost}")
            
            return False
            
        except Exception as e:
            print(f"Error checking next slot upgrade: {e}")
            return False
    
    def _auto_upgrade_slot(self, user_id: str, slot_no: int, slot_cost: Decimal, 
                          available_reserve: Decimal) -> bool:
        """Automatically upgrade to next slot using reserve funds"""
        try:
            # Check if user already has this slot activated
            existing_activation = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program='matrix',
                slot_no=slot_no,
                status='completed'
            ).first()
            
            if existing_activation:
                print(f"[MIDDLE3_DEBUG] Slot {slot_no} already activated for user {user_id}")
                return False  # Already activated
            
            # Get slot catalog
            catalog = SlotCatalog.objects(
                program='matrix',
                slot_no=slot_no,
                is_active=True
            ).first()
            
            if not catalog:
                print(f"[MIDDLE3_DEBUG] No catalog found for slot {slot_no}")
                return False
            
            # Create slot activation
            activation = SlotActivation(
                user_id=ObjectId(user_id),
                program='matrix',
                slot_no=slot_no,
                slot_name=catalog.name,
                activation_type='auto',
                upgrade_source='reserve',
                amount_paid=slot_cost,
                currency='USDT',
                tx_hash=f"MIDDLE3-AUTO-{user_id}-S{slot_no}",
                is_auto_upgrade=True,
                status='completed'
            )
            activation.save()
            
            # Create MatrixActivation (Required for MatrixService checks)
            try:
                from .model import MatrixActivation
                MatrixActivation(
                    user_id=ObjectId(user_id),
                    slot_no=slot_no,
                    slot_name=catalog.name,
                    activation_type='upgrade',
                    upgrade_source='auto',
                    amount_paid=slot_cost,
                    currency='USDT',
                    tx_hash=f"MIDDLE3-AUTO-{user_id}-S{slot_no}",
                    is_auto_upgrade=True,
                    status='completed',
                    activated_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                ).save()
            except Exception as e:
                print(f"Error creating MatrixActivation: {e}")

            
            # Deduct from reserve fund
            remaining_reserve = available_reserve - slot_cost
            self._deduct_reserve_fund(user_id, 'matrix', slot_no - 1, slot_cost, 
                                    f"MIDDLE3-AUTO-{user_id}-S{slot_no}")
            
            # Update user's slot information
            self._update_user_matrix_slot(user_id, catalog, slot_cost)
            
            # --- FIX: Update MatrixTree.current_slot ---
            try:
                from .model import MatrixTree
                mt = MatrixTree.objects(user_id=ObjectId(user_id)).first()
                if mt:
                    mt.current_slot = slot_no
                    mt.save()
            except Exception as e:
                print(f"Error updating MatrixTree.current_slot: {e}")
            # -------------------------------------------
            
            # --- FIX: Ensure TreePlacement (Direct logic with BFS and MatrixTree update) ---
            try:
                from modules.tree.model import TreePlacement
                from modules.matrix.model import MatrixTree, MatrixNode
                
                # 1. Resolve Active Upline (Pass-up logic)
                user = User.objects(id=ObjectId(user_id)).first()
                curr_referrer_id = str(user.refered_by) if user and user.refered_by else None
                target_upline_id = "692d90730267e8d5a4693567" # Default to ROOT
                
                # Validation loop to find nearest upline with this slot active
                while curr_referrer_id:
                    # Check if referrer has this slot active
                    # We can check MatrixActivation or TreePlacement. TreePlacement is source of truth for tree.
                    is_active = TreePlacement.objects(
                        user_id=ObjectId(curr_referrer_id),
                        program="matrix",
                        slot_no=slot_no,
                        is_active=True
                    ).count() > 0
                    
                    if is_active:
                        target_upline_id = curr_referrer_id
                        break
                    
                    # Move up
                    ref_user = User.objects(id=ObjectId(curr_referrer_id)).first()
                    curr_referrer_id = str(ref_user.refered_by) if ref_user and ref_user.refered_by else None
                    if curr_referrer_id == target_upline_id:
                        break # Reached ROOT/Loop
                
                print(f"[MIDDLE3] Resolved upline for slot {slot_no}: {target_upline_id}", flush=True)

                # 2. Find position under target_upline using BFS on MatrixTree
                upline_tree = MatrixTree.objects(user_id=ObjectId(target_upline_id)).first()
                
                # Default initialization
                immediate_parent_id = target_upline_id
                position = "left" 
                
                if not upline_tree:
                     # Should not happen for active upline, but handle safely
                     print(f"[MIDDLE3] Warning: Upline {target_upline_id} has no MatrixTree", flush=True)
                     # Fallback: Just place under them directly (Level 1)
                     immediate_parent_id = target_upline_id
                     position = "left"
                     # Create a MatrixTree for them if missing? 
                     # Better to just proceed with TreePlacement as that's what we need.
                else:
                    # BFS to find first node with < 3 children
                    queue = []
                    # Root of the sub-tree is the upline themselves (Level 0 relative)
                    # We need to find nodes in checking order.
                    # Simplification: MatrixTree.nodes stores flattened list. 
                    # We can reconstruct or just find the first available spot.
                    # Standard Matrix fills: Level 1 (3 nodes), Level 2 (9 nodes)...
                    
                    # Let's use a simple map to count children
                    # node_id -> children_count
                    children_map = {}
                    # Also map to find node objects
                    nodes_map = {target_upline_id: {'level': 0, 'id': target_upline_id}}
                    
                    # Filter nodes relevant to this slot (if MatrixTree shares slots? Usually MatrixTree is program-wide)
                    # Assuming MatrixTree.nodes contains ALL nodes for ALL slots? Or is MatrixTree specific to slot?
                    # The model usually has `current_slot`. Nodes might be slot-agnostic or filtered?
                    # Checking Service: it usually re-uses the tree structure or creates new?
                    # For Matrix, usually structure is permanent per slot? No, slots are independent trees.
                    # If slots are independent trees, MatrixTree needs to filter by slot or we rely on TreePlacement.
                    
                    # RE-CHECK: TreePlacement IS the source of truth for positions.
                    # _place_user_in_matrix_tree uses MatrixTree.nodes. 
                    # If we can't reliably use MatrixTree (complex), let's use TreePlacement BFS.
                    
                    # strategy: Check Level 1 spots under upline.
                    # If full, check Level 2 spots (children of Level 1).
                    
                    # Fetch all placements in this sub-tree? Too expensive.
                    # We will implement a localized BFS querying TreePlacement.
                    
                    q = [(target_upline_id, 1)] # (user_id, relative_level)
                    found_spot = None
                    
                    while q:
                        curr_id, curr_level = q.pop(0)
                        
                        # Get children of curr_id for this slot
                        children = list(TreePlacement.objects(
                            parent_id=ObjectId(curr_id),
                            program="matrix",
                            slot_no=slot_no
                        ))
                        
                        if len(children) < 3:
                            # Found spot!
                            immediate_parent_id = curr_id
                            level = curr_level # relative to search start? No, we need absolute tree level logic or just relative?
                            # TreePlacement.level is usually relative to root? Or uniform?
                            # Let's trust parent_id link is sufficient.
                            
                            # Determine position string
                            existing_positions = [c.position for c in children]
                            if "left" not in existing_positions: position = "left"
                            elif "middle" not in existing_positions: position = "middle"
                            else: position = "right"
                            
                            found_spot = True
                            break
                        else:
                            # Add children to queue to search next level
                            # Sort by position to ensure Left->Mid->Right filling order of subtrees? 
                            # Matrix fill order: usually fill bucket 1, then bucket 2...
                            # We just append to queue.
                             # Ordered children: Left, Middle, Right
                            sorted_children = sorted(children, key=lambda x: {"left":0, "middle":1, "right":2}.get(x.position, 99))
                            for child in sorted_children:
                                q.append((str(child.user_id), curr_level + 1))
                    
                    if not found_spot:
                        # Fallback (should not happen in infinite tree)
                        immediate_parent_id = target_upline_id
                        position = "left"

                # 3. Create TreePlacement
                existing_tp = TreePlacement.objects(
                    user_id=ObjectId(user_id),
                    program="matrix",
                    slot_no=slot_no
                ).first()

                if not existing_tp:
                    tp = TreePlacement(
                        user_id=ObjectId(user_id),
                        program="matrix",
                        slot_no=slot_no,
                        parent_id=ObjectId(immediate_parent_id),
                        upline_id=ObjectId(target_upline_id), # The "Root" of this 3x3 structure (Sponsor)
                        position=position,
                        level=1, # Todo: fetch parent level + 1 if strictly tracking
                        is_active=True,
                        is_upline_reserve=(position == "middle"),
                        created_at=datetime.utcnow()
                    )
                    tp.save()
                    print(f"[MIDDLE3] Created TreePlacement for {user_id} slot {slot_no} under {immediate_parent_id}", flush=True)
                    
                    # 4. Update MatrixTree of the UPLINE (target_upline_id) to track this new node
                    if upline_tree:
                        new_node = MatrixNode(
                            user_id=ObjectId(user_id),
                            level=0, # Relative level
                            position=0 if position=="left" else 1 if position=="middle" else 2,
                            placed_at=datetime.utcnow(),
                            is_active=True
                        )
                        upline_tree.nodes.append(new_node)
                        upline_tree.save()

            except Exception as e:
                print(f"Error placing user in tree (middle3 fix): {e}")
                import traceback
                traceback.print_exc()
            # --------------------------------------------------
            
            # Create blockchain event
            try:
                BlockchainEvent(
                    tx_hash=f"MIDDLE3-AUTO-{user_id}-S{slot_no}",
                    event_type='matrix_slot_auto_upgrade',
                    event_data={
                        'program': 'matrix',
                        'slot_no': slot_no,
                        'slot_name': catalog.name,
                        'amount': str(slot_cost),
                        'currency': 'USDT',
                        'user_id': user_id,
                        'source': 'middle_3_reserve'
                    },
                    status='processed',
                    processed_at=datetime.utcnow()
                ).save()
            except Exception:
                pass
            
            # Create income event
            try:
                IncomeEvent(
                    user_id=ObjectId(user_id),
                    source_user_id=ObjectId(user_id),
                    program='matrix',
                    slot_no=slot_no,
                    income_type='level_payout',
                    amount=slot_cost,
                    percentage=Decimal('100.0'),
                    tx_hash=f"MIDDLE3-AUTO-{user_id}-S{slot_no}",
                    status='completed'
                ).save()
            except Exception:
                pass
            
            # --- FIX: Distribute Matrix Funds (Level, Middle 3, etc.) ---
            # The user PAID for this slot (via reserve), so the network must be compensated.
            # This triggers Middle-3 earnings for the upline if applicable.
            try:
                from ..fund_distribution.service import FundDistributionService
                fds = FundDistributionService()
                
                # Get upline/referrer for distribution context
                dist_referrer_id = str(user.refered_by) if user and user.refered_by else None
                
                # Map position string to integer for service compatibility
                pos_map = {"left": 0, "middle": 1, "right": 2}
                pos_int = pos_map.get(position, 0) # Fallback to 0 if unknown
                
                # Construct Placement Context
                dist_placement_context = {
                    "placed_under_user_id": str(immediate_parent_id),
                    "level": 1, # Relative to immediate_parent_id, it is always level 1 (direct child)
                    "position": pos_int
                }
                
                print(f"[MIDDLE3-AUTO] Triggering distribution for {user_id} slot {slot_no}. Context: {dist_placement_context}", flush=True)

                fds.distribute_matrix_funds(
                    user_id=str(user_id),
                    amount=slot_cost,
                    slot_no=slot_no,
                    referrer_id=dist_referrer_id,
                    tx_hash=f"MIDDLE3-AUTO-DIST-{user_id}-S{slot_no}",
                    currency='USDT',
                    placement_context=dist_placement_context
                )
            except Exception as e:
                print(f"Error distributing funds for auto-upgrade: {e}")
                import traceback
                traceback.print_exc()
            # ------------------------------------------------------------

            # --- CRITICAL FIX: Update MatrixTree and MatrixActivation ---
            # Ensure the system recognizes the user is now at the new slot level
            try:
                from .model import MatrixTree as _MatrixTree
                from .model import MatrixActivation as _MatrixActivation

                # 1. Create MatrixActivation
                ma_exists = _MatrixActivation.objects(
                    user_id=ObjectId(user_id),
                    slot_no=slot_no,
                    status='completed'
                ).first()
                
                if not ma_exists:
                    _MatrixActivation(
                        user_id=ObjectId(user_id),
                        slot_no=slot_no,
                        slot_name=catalog.name,
                        activation_type='upgrade',
                        upgrade_source='auto_middle3',
                        amount_paid=slot_cost,
                        currency='USDT',
                        tx_hash=f"MIDDLE3-AUTO-{user_id}-S{slot_no}",
                        is_auto_upgrade=True,
                        status='completed',
                        activated_at=datetime.utcnow(),
                        completed_at=datetime.utcnow()
                    ).save()
                    print(f"[MIDDLE3_AUTO] Created MatrixActivation for user {user_id} slot {slot_no}")

                # 2. Update MatrixTree.current_slot
                mt = _MatrixTree.objects(user_id=ObjectId(user_id)).first()
                if mt:
                    if not getattr(mt, "current_slot", None) or mt.current_slot < slot_no:
                        mt.current_slot = slot_no
                        mt.updated_at = datetime.utcnow()
                        mt.save()
                        print(f"[MIDDLE3_AUTO] Updated MatrixTree current_slot to {slot_no} for user {user_id}")
                else:
                    # Should unlikely exist without MatrixTree, but responsible to create if missing
                    pass 

            except Exception as e:
                print(f"[MIDDLE3_AUTO] Error updating MatrixTree/Activation: {e}")
                import traceback
                traceback.print_exc()
            # ------------------------------------------------------------
            
            return True
            
        except Exception as e:
            print(f"Error in auto upgrade: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _deduct_reserve_fund(self, user_id: str, program: str, slot_no: int, amount: Decimal, tx_hash: str):
        """Deduct amount from reserve fund"""
        try:
            current_balance = self._get_reserve_balance(user_id, program, slot_no)
            new_balance = current_balance - amount
            
            # Create reserve ledger entry for deduction
            reserve_entry = ReserveLedger(
                user_id=ObjectId(user_id),
                program=program,
                slot_no=slot_no,
                amount=amount,
                direction='debit',
                source='auto_upgrade',
                balance_after=new_balance,
                tx_hash=tx_hash
            )
            reserve_entry.save()
            
            # Update reserve wallet
            self._update_reserve_wallet(user_id, program, new_balance)
            
        except Exception as e:
            print(f"Error deducting reserve fund: {e}")
    
    def _update_user_matrix_slot(self, user_id: str, catalog: SlotCatalog, amount: Decimal):
        """Update user's matrix slot information after auto-upgrade"""
        try:
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return
            
            from ..user.model import MatrixSlotInfo
            
            # Create slot info
            slot_info = MatrixSlotInfo(
                slot_name=catalog.name,
                slot_value=float(amount),
                level=catalog.level,
                is_active=True,
                activated_at=datetime.utcnow(),
                upgrade_cost=float(catalog.upgrade_cost or Decimal('0')),
                total_income=float(catalog.total_income or Decimal('0')),
                wallet_amount=float(catalog.wallet_amount or Decimal('0'))
            )
            
            # Check if slot already exists in user's matrix_slots list
            existing_slot = None
            for i, existing_slot_info in enumerate(user.matrix_slots):
                if existing_slot_info.slot_name == catalog.name:
                    existing_slot = i
                    break
            
            if existing_slot is not None:
                # Update existing slot
                user.matrix_slots[existing_slot] = slot_info
            else:
                # Add new slot
                user.matrix_slots.append(slot_info)
            
            user.save()
            
        except Exception as e:
            print(f"Error updating user matrix slot info: {e}")
    
    def get_middle_3_status(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive middle 3 status for a user"""
        try:
            status = {
                "user_id": user_id,
                "program": "matrix",
                "middle_3_users": [],
                "total_reserve_balance": Decimal('0'),
                "slots": []
            }
            
            # Get user's matrix tree
            matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
            if matrix_tree:
                # Get middle 3 users
                middle_3_users = self.identify_middle_3_users(user_id, matrix_tree.current_slot)
                status["middle_3_users"] = middle_3_users
                
                # Get reserve status for each slot
                for slot_no in range(1, 16):  # Matrix has 15 slots
                    reserve_balance = self._get_reserve_balance(user_id, 'matrix', slot_no)
                    next_slot_cost = self._get_next_slot_cost(slot_no)
                    
                    slot_status = {
                        "slot_no": slot_no,
                        "reserve_balance": float(reserve_balance),
                        "next_slot_cost": float(next_slot_cost) if next_slot_cost else None,
                        "can_auto_upgrade": reserve_balance >= next_slot_cost if next_slot_cost else False
                    }
                    
                    status["slots"].append(slot_status)
                    status["total_reserve_balance"] += reserve_balance
            
            return status
            
        except Exception as e:
            return {"error": f"Error getting middle 3 status: {str(e)}"}
    
    def _get_next_slot_cost(self, current_slot: int) -> Optional[Decimal]:
        """Get the cost of the next slot"""
        try:
            next_slot = SlotCatalog.objects(
                program='matrix',
                slot_no=current_slot + 1,
                is_active=True
            ).first()
            
            return next_slot.price if next_slot else None
            
        except Exception:
            return None
    
    def manually_add_reserve_fund(self, user_id: str, slot_no: int, amount: Decimal, 
                                 tx_hash: str) -> Tuple[bool, str]:
        """Manually add funds to reserve for slot upgrade"""
        try:
            success, message = self._add_to_reserve_fund(
                user_id, 'matrix', slot_no, amount, user_id, tx_hash
            )
            
            if success:
                # Check if this enables auto-upgrade
                self._check_next_slot_upgrade(user_id, slot_no)
                return True, message
            else:
                return False, message
                
        except Exception as e:
            return False, f"Error manually adding reserve fund: {str(e)}"
    
    def check_manual_upgrade_option(self, user_id: str, slot_no: int) -> Dict[str, Any]:
        """Check manual upgrade options with reserve combinations"""
        try:
            next_slot_cost = self._get_next_slot_cost(slot_no)
            if not next_slot_cost:
                return {"error": "Next slot not found"}
            
            reserve_balance = self._get_reserve_balance(user_id, 'matrix', slot_no)
            remaining_cost = next_slot_cost - reserve_balance
            
            options = {
                "user_id": user_id,
                "current_slot": slot_no,
                "next_slot_cost": float(next_slot_cost),
                "reserve_balance": float(reserve_balance),
                "remaining_cost": float(remaining_cost),
                "can_auto_upgrade": reserve_balance >= next_slot_cost,
                "manual_upgrade_options": []
            }
            
            if remaining_cost > 0:
                options["manual_upgrade_options"] = [
                    {
                        "option": "Full Manual",
                        "description": "Pay full remaining cost from wallet",
                        "amount": float(remaining_cost)
                    },
                    {
                        "option": "Reserve + Manual",
                        "description": "Use reserve + partial manual payment",
                        "reserve_amount": float(reserve_balance),
                        "manual_amount": float(remaining_cost)
                    }
                ]
            
            return options
            
        except Exception as e:
            return {"error": f"Error checking manual upgrade options: {str(e)}"}
