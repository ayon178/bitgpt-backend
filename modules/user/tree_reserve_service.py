#!/usr/bin/env python3
"""
Tree Upline Reserve System Service
Handles the 30% reserve fund system for automatic slot activation in Binary program
"""

from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from bson import ObjectId

from ..wallet.model import ReserveLedger, UserWallet
from ..slot.model import SlotCatalog, SlotActivation
from ..user.model import User
from ..tree.model import TreePlacement
from ..blockchain.model import BlockchainEvent
from ..income.model import IncomeEvent
from .sequence_service import ProgramSequenceService


class TreeUplineReserveService:
    """Service for managing Tree Upline Reserve System"""
    
    def __init__(self):
        self.reserve_percentage = Decimal('0.30')  # 30% of slot fee
    
    def calculate_reserve_amount(self, slot_fee: Decimal) -> Decimal:
        """Calculate 30% of slot fee for reserve"""
        return slot_fee * self.reserve_percentage
    
    def find_tree_upline(self, user_id: str, program: str, slot_no: int) -> Optional[Dict[str, Any]]:
        """
        Find the tree upline for a specific slot activation.
        Tree upline is the user who receives the 30% reserve fund.
        """
        try:
            # Get user's tree placement for this slot
            placement = TreePlacement.objects(
                user_id=ObjectId(user_id),
                program=program,
                slot_no=slot_no,
                is_active=True
            ).first()
            
            if not placement:
                return None
            
            # Get the parent (tree upline)
            if placement.parent_id:
                parent_user = User.objects(id=placement.parent_id).first()
                if parent_user:
                    return {
                        "user_id": str(parent_user.id),
                        "uid": parent_user.uid,
                        "name": parent_user.name,
                        "level": placement.level - 1 if placement.level > 0 else 0
                    }
            
            return None
            
        except Exception as e:
            print(f"Error finding tree upline: {e}")
            return None
    
    def add_to_reserve_fund(self, tree_upline_id: str, program: str, slot_no: int, 
                           amount: Decimal, source_user_id: str, tx_hash: str) -> Tuple[bool, str]:
        """
        Add funds to tree upline's reserve for next slot activation
        """
        try:
            # Get current reserve balance
            current_balance = self.get_reserve_balance(tree_upline_id, program, slot_no)
            new_balance = current_balance + amount
            
            # Create reserve ledger entry
            reserve_entry = ReserveLedger(
                user_id=ObjectId(tree_upline_id),
                program=program,
                slot_no=slot_no,
                amount=amount,
                direction='credit',
                source='income',
                balance_after=new_balance,
                tx_hash=tx_hash
            )
            reserve_entry.save()
            
            # Update or create user wallet reserve balance
            self._update_reserve_wallet(tree_upline_id, program, new_balance)
            
            # Check if reserve is sufficient for next slot activation
            self._check_auto_activation(tree_upline_id, program, slot_no, new_balance)
            
            return True, f"Added {amount} to reserve fund. New balance: {new_balance}"
            
        except Exception as e:
            return False, f"Error adding to reserve fund: {str(e)}"
    
    def get_reserve_balance(self, user_id: str, program: str, slot_no: int) -> Decimal:
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
                currency='BNB' if program == 'binary' else ('USDT' if program == 'matrix' else 'USD')
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
                    currency='BNB' if program == 'binary' else ('USDT' if program == 'matrix' else 'USD'),
                    last_updated=datetime.utcnow()
                ).save()
                
        except Exception as e:
            print(f"Error updating reserve wallet: {e}")
    
    def _check_auto_activation(self, user_id: str, program: str, current_slot: int, reserve_balance: Decimal):
        """Check if reserve balance is sufficient for next slot activation"""
        try:
            # Get next slot information
            next_slot_no = current_slot + 1
            next_slot_catalog = SlotCatalog.objects(
                program=program,
                slot_no=next_slot_no,
                is_active=True
            ).first()
            
            if not next_slot_catalog:
                return False
            
            # Calculate upgrade cost (difference between next slot and current slot)
            upgrade_cost = next_slot_catalog.price
            
            # Try to get current slot price to calculate difference
            try:
                current_slot_catalog = SlotCatalog.objects(
                    program=program,
                    slot_no=current_slot,
                    is_active=True
                ).first()
                if current_slot_catalog:
                    upgrade_cost = next_slot_catalog.price - current_slot_catalog.price
            except Exception:
                pass
            
            # Check if reserve is sufficient
            if reserve_balance >= upgrade_cost:
                # Auto-activate next slot
                return self._auto_activate_slot(user_id, program, next_slot_no, upgrade_cost, reserve_balance)
            
            return False
            
        except Exception as e:
            print(f"Error checking auto activation: {e}")
            return False
    
    def _auto_activate_slot(self, user_id: str, program: str, slot_no: int, 
                           slot_cost: Decimal, available_reserve: Decimal) -> bool:
        """Automatically activate next slot using reserve funds"""
        try:
            # Check if user already has this slot activated
            existing_activation = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program=program,
                slot_no=slot_no,
                status='completed'
            ).first()
            
            if existing_activation:
                return False  # Already activated
            
            # Get slot catalog
            catalog = SlotCatalog.objects(
                program=program,
                slot_no=slot_no,
                is_active=True
            ).first()
            
            if not catalog:
                return False
            
            # Create slot activation
            activation = SlotActivation(
                user_id=ObjectId(user_id),
                program=program,
                slot_no=slot_no,
                slot_name=catalog.name,
                activation_type='auto',
                upgrade_source='reserve',
                amount_paid=slot_cost,
                currency='BNB' if program == 'binary' else ('USDT' if program == 'matrix' else 'USD'),
                tx_hash=f"RESERVE-AUTO-{user_id}-S{slot_no}",
                is_auto_upgrade=True,
                status='completed',
                activated_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            activation.save()
            
            # Deduct from reserve fund
            remaining_reserve = available_reserve - slot_cost
            self._deduct_reserve_fund(user_id, program, slot_no - 1, slot_cost, f"RESERVE-AUTO-{user_id}-S{slot_no}")
            
            # Update user's slot information (binary-specific structure)
            self._update_user_slot_info(user_id, catalog, slot_cost)
            
            # Create blockchain event
            try:
                BlockchainEvent(
                    tx_hash=f"RESERVE-AUTO-{user_id}-S{slot_no}",
                    event_type='slot_auto_activated',
                    event_data={
                        'program': program,
                        'slot_no': slot_no,
                        'slot_name': catalog.name,
                        'amount': str(slot_cost),
                        'currency': 'BNB' if program == 'binary' else ('USDT' if program == 'matrix' else 'USD'),
                        'user_id': user_id,
                        'source': 'reserve_fund'
                    },
                    status='processed',
                    processed_at=datetime.utcnow()
                ).save()
            except Exception:
                pass
            
            # Create income event - REPLACED with full Matrix Fund Distribution
            # This ensures that "Middle Position" logic and all other commissions are triggered
            # even for auto-upgrades.
            if program == 'matrix':
                try:
                    from modules.fund_distribution.service import FundDistributionService
                    from modules.tree.model import TreePlacement as _TP
                    
                    # 1. Ensure TreePlacement exists for this slot (critical for placement_context)
                    # We do this BEFORE distribution so we can find the user's position
                    try:
                        from modules.matrix.service import MatrixService
                        MatrixService()._ensure_matrix_tree_placement_for_slot(user_id, slot_no)
                    except Exception as e:
                        print(f"[MATRIX_AUTO_RESERVE] Error ensuring TreePlacement before distribution: {e}")

                    # 2. Build placement_context
                    placement_ctx = None
                    try:
                        tp = _TP.objects(
                            user_id=ObjectId(user_id),
                            program="matrix",
                            slot_no=slot_no,
                            is_active=True,
                        ).first()
                        
                        if tp:
                            pos_map = {"left": 0, "middle": 1, "center": 1, "right": 2}
                            pos_idx = pos_map.get(getattr(tp, "position", ""), None)
                            parent_id = str(
                                getattr(tp, "upline_id", None)
                                or getattr(tp, "parent_id", None)
                                or ""
                            )
                            placement_ctx = {
                                "placed_under_user_id": parent_id,
                                "level": int(getattr(tp, "level", 0)),
                                "position": pos_idx,
                            }
                    except Exception as e:
                        print(f"[MATRIX_AUTO_RESERVE] Error building placement_context: {e}")
                        placement_ctx = None

                    # 3. Call distribute_matrix_funds
                    print(f"[MATRIX_AUTO_RESERVE] Triggering distribution for {user_id} slot {slot_no}")
                    fund_service = FundDistributionService()
                    dist_res = fund_service.distribute_matrix_funds(
                        user_id=user_id,
                        amount=slot_cost,
                        slot_no=slot_no,
                        # For auto-upgrade, referrer is the direct referrer, but distribution 
                        # logic might use placement_context for special routing.
                        # We'll pass direct referrer ID if available.
                        referrer_id=str(User.objects(id=ObjectId(user_id)).scalar('refered_by').first() or ""),
                        tx_hash=f"RESERVE-AUTO-{user_id}-S{slot_no}",
                        currency='USDT',
                        placement_context=placement_ctx
                    )
                    print(f"[MATRIX_AUTO_RESERVE] Distribution result: {dist_res.get('success')}")
                    
                except Exception as e:
                    print(f"[MATRIX_AUTO_RESERVE] Error during fund distribution: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                # For non-Matrix programs (Binary/Global), keep existing behavior or update later
                try:
                    IncomeEvent(
                        user_id=ObjectId(user_id),
                        source_user_id=ObjectId(user_id),
                        program=program,
                        slot_no=slot_no,
                        income_type='level_payout',
                        amount=slot_cost,
                        percentage=Decimal('100.0'),
                        tx_hash=f"RESERVE-AUTO-{user_id}-S{slot_no}",
                        status='completed'
                    ).save()
                except Exception:
                    pass

            # MATRIX-SPECIFIC: when a user's Matrix slot is auto-upgraded from reserve,
            # 1) ensure MatrixTree.current_slot reflects the highest activated slot
            # 2) ensure TreePlacement for that slot exists using the same sweepover rules
            #    as manual upgrades (so that per-slot trees reflect real eligible uplines).
            # 3) ensure MatrixActivation exists (required for MatrixService checks)
            if program == 'matrix':
                try:
                    from modules.matrix.model import MatrixTree as _MatrixTree
                    from modules.matrix.model import MatrixActivation as _MatrixActivation

                    # Create MatrixActivation if it doesn't exist (SlotActivation is generic)
                    # Note: SlotActivation was already created above, but MatrixService checks MatrixActivation
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
                            upgrade_source='auto',
                            amount_paid=slot_cost,
                            currency='USDT',
                            tx_hash=f"RESERVE-AUTO-{user_id}-S{slot_no}",
                            is_auto_upgrade=True,
                            status='completed',
                            activated_at=datetime.utcnow(),
                            completed_at=datetime.utcnow()
                        ).save()
                        print(f"[MATRIX_AUTO_RESERVE] Created MatrixActivation for slot {slot_no}")

                    mt = _MatrixTree.objects(user_id=ObjectId(user_id)).first()
                    if not mt:
                        mt = _MatrixTree(
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
                            reserve_fund=float(remaining_reserve),
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                    else:
                        # Only move current_slot forward
                        if not getattr(mt, "current_slot", None) or mt.current_slot < slot_no:
                            mt.current_slot = slot_no
                        mt.updated_at = datetime.utcnow()
                    mt.save()
                except Exception as e:
                    print(f"[MATRIX_AUTO_RESERVE] Error updating MatrixTree/Activation for auto-upgrade slot {slot_no}: {e}")

                try:
                    from modules.matrix.service import MatrixService
                    MatrixService()._ensure_matrix_tree_placement_for_slot(user_id, slot_no)
                except Exception as e:
                    print(f"[MATRIX_AUTO_RESERVE] Error ensuring TreePlacement for auto-upgrade slot {slot_no}: {e}")
            
            return True
            
        except Exception as e:
            print(f"Error in auto activation: {e}")
            return False
    
    def _deduct_reserve_fund(self, user_id: str, program: str, slot_no: int, amount: Decimal, tx_hash: str):
        """Deduct amount from reserve fund"""
        try:
            current_balance = self.get_reserve_balance(user_id, program, slot_no)
            new_balance = current_balance - amount
            
            # Create reserve ledger entry for deduction
            reserve_entry = ReserveLedger(
                user_id=ObjectId(user_id),
                program=program,
                slot_no=slot_no,
                amount=amount,
                direction='debit',
                source='auto_activation',
                balance_after=new_balance,
                tx_hash=tx_hash
            )
            reserve_entry.save()
            
            # Update reserve wallet
            self._update_reserve_wallet(user_id, program, new_balance)
            
        except Exception as e:
            print(f"Error deducting reserve fund: {e}")
    
    def _update_user_slot_info(self, user_id: str, catalog: SlotCatalog, amount: Decimal):
        """Update user's slot information after auto-activation"""
        try:
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return
            
            from .model import BinarySlotInfo
            
            # Create slot info
            slot_info = BinarySlotInfo(
                slot_name=catalog.name,
                slot_value=float(amount),
                level=catalog.level,
                is_active=True,
                activated_at=datetime.utcnow(),
                upgrade_cost=float(catalog.upgrade_cost or Decimal('0')),
                total_income=float(catalog.total_income or Decimal('0')),
                wallet_amount=float(catalog.wallet_amount or Decimal('0'))
            )
            
            # Check if slot already exists in user's binary_slots list
            existing_slot = None
            for i, existing_slot_info in enumerate(user.binary_slots):
                if existing_slot_info.slot_name == catalog.name:
                    existing_slot = i
                    break
            
            if existing_slot is not None:
                # Update existing slot
                user.binary_slots[existing_slot] = slot_info
            else:
                # Add new slot
                user.binary_slots.append(slot_info)
            
            user.save()
            
        except Exception as e:
            print(f"Error updating user slot info: {e}")
    
    def get_reserve_status(self, user_id: str, program: str) -> Dict[str, Any]:
        """Get comprehensive reserve status for a user"""
        try:
            status = {
                "user_id": user_id,
                "program": program,
                "total_reserve_balance": Decimal('0'),
                "slots": []
            }
            
            # Get all slots for this program
            slots = SlotCatalog.objects(program=program, is_active=True).order_by('slot_no')
            
            for slot in slots:
                reserve_balance = self.get_reserve_balance(user_id, program, slot.slot_no)
                next_slot_cost = self._get_next_slot_cost(program, slot.slot_no)
                
                slot_status = {
                    "slot_no": slot.slot_no,
                    "slot_name": slot.name,
                    "reserve_balance": float(reserve_balance),
                    "next_slot_cost": float(next_slot_cost) if next_slot_cost else None,
                    "can_auto_activate": reserve_balance >= next_slot_cost if next_slot_cost else False
                }
                
                status["slots"].append(slot_status)
                status["total_reserve_balance"] += reserve_balance
            
            return status
            
        except Exception as e:
            return {"error": f"Error getting reserve status: {str(e)}"}
    
    def _get_next_slot_cost(self, program: str, current_slot: int) -> Optional[Decimal]:
        """Get the cost of the next slot"""
        try:
            next_slot = SlotCatalog.objects(
                program=program,
                slot_no=current_slot + 1,
                is_active=True
            ).first()
            
            return next_slot.price if next_slot else None
            
        except Exception:
            return None
    
    def transfer_to_mother_account(self, user_id: str, program: str, slot_no: int, 
                                  amount: Decimal, tx_hash: str) -> Tuple[bool, str]:
        """
        Transfer reserve funds to mother account when upline doesn't activate slot.
        This is a fallback mechanism.
        """
        try:
            # Get mother account (first user or special mother ID)
            mother_user = User.objects(role='mother').first()
            if not mother_user:
                # Fallback to first user
                mother_user = User.objects().order_by('created_at').first()
            
            if not mother_user:
                return False, "Mother account not found"
            
            # Transfer to mother account's reserve
            success, message = self.add_to_reserve_fund(
                str(mother_user.id), 
                program, 
                slot_no, 
                amount, 
                user_id, 
                tx_hash
            )
            
            if success:
                # Clear original user's reserve for this slot
                self._clear_reserve_fund(user_id, program, slot_no, tx_hash)
                return True, f"Transferred {amount} to mother account. {message}"
            else:
                return False, message
                
        except Exception as e:
            return False, f"Error transferring to mother account: {str(e)}"
    
    def _clear_reserve_fund(self, user_id: str, program: str, slot_no: int, tx_hash: str):
        """Clear reserve fund for a specific slot"""
        try:
            current_balance = self.get_reserve_balance(user_id, program, slot_no)
            
            if current_balance > 0:
                # Create ledger entry for clearing
                ReserveLedger(
                    user_id=ObjectId(user_id),
                    program=program,
                    slot_no=slot_no,
                    amount=current_balance,
                    direction='debit',
                    source='transfer_to_mother',
                    balance_after=Decimal('0'),
                    tx_hash=tx_hash
                ).save()
                
                # Update wallet
                self._update_reserve_wallet(user_id, program, Decimal('0'))
                
        except Exception as e:
            print(f"Error clearing reserve fund: {e}")
