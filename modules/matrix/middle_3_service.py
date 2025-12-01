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
                                 tx_hash: str) -> Tuple[bool, str]:
        """
        Collect 100% earnings from middle 3 users for next slot upgrade.
        This is triggered when a middle 3 user activates a slot or joins.
        """
        try:
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
                print(f"[MIDDLE3_DEBUG] Calling _auto_upgrade_slot for slot {next_slot_no}")
                result = self._auto_upgrade_slot(user_id, next_slot_no, next_slot_cost, reserve_balance)
                print(f"[MIDDLE3_DEBUG] _auto_upgrade_slot returned: {result}")
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
            print(f"[MIDDLE3_DEBUG] _auto_upgrade_slot started: user={user_id}, slot={slot_no}, cost={slot_cost}")
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
            print(f"[MIDDLE3_DEBUG] SlotActivation created successfully")
            
            # Deduct from reserve fund
            remaining_reserve = available_reserve - slot_cost
            print(f"[MIDDLE3_DEBUG] Deducting {slot_cost} from reserve, remaining: {remaining_reserve}")
            self._deduct_reserve_fund(user_id, 'matrix', slot_no - 1, slot_cost, 
                                    f"MIDDLE3-AUTO-{user_id}-S{slot_no}")
            
            # Update user's slot information
            print(f"[MIDDLE3_DEBUG] Updating user matrix slot info")
            self._update_user_matrix_slot(user_id, catalog, slot_cost)
            
            # --- FIX: Ensure TreePlacement for the new slot ---
            try:
                from .service import MatrixService
                matrix_service = MatrixService()
                
                # We need referrer_id to place the user.
                user = User.objects(id=ObjectId(user_id)).first()
                referrer_id = str(user.refered_by) if user and user.refered_by else None
                
                if referrer_id:
                    print(f"[MIDDLE3_DEBUG] Placing user {user_id} in Matrix Slot {slot_no} tree under {referrer_id}")
                    matrix_service._ensure_tp(user_id, referrer_id, slot_no)
                    print(f"[MIDDLE3_DEBUG] ✅ User placed in Slot {slot_no} tree")
                else:
                    print(f"[MIDDLE3_DEBUG] ⚠️ No referrer found for user {user_id}, skipping placement")
                    
            except Exception as e:
                print(f"[MIDDLE3_DEBUG] ❌ Error placing user in tree: {e}")
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
            
            print(f"[MIDDLE3_DEBUG] ✅ Auto-upgrade completed successfully for slot {slot_no}")
            return True
            
        except Exception as e:
            print(f"[MIDDLE3_DEBUG] ❌ Error in auto upgrade: {e}")
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
