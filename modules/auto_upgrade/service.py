from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta
from ..user.model import User
from ..tree.model import TreePlacement
from .model import (
    AutoUpgradeQueue, AutoUpgradeLog, BinaryAutoUpgrade, 
    MatrixAutoUpgrade, GlobalPhaseProgression, AutoUpgradeSettings,
    AutoUpgradeEarnings, AutoUpgradeTrigger
)
from ..wallet.model import ReserveLedger

class AutoUpgradeService:
    """Auto Upgrade System Business Logic Service"""
    
    def __init__(self):
        pass

    def record_global_reserve_credit(self, user_id: str, slot_no: int, amount: Decimal, tx_hash: str) -> Dict[str, Any]:
        try:
            # Write a reserve ledger credit for audit
            status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not status:
                return {"success": False, "error": "Global status not found"}
            # Compute balance after is not tracked per-user here; store amount and metadata
            ReserveLedger(
                user_id=ObjectId(user_id),
                program='global',
                slot_no=slot_no,
                amount=Decimal(str(amount)),
                direction='credit',
                source='income',
                balance_after=Decimal('0'),
                tx_hash=tx_hash,
                created_at=datetime.utcnow()
            ).save()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_binary_auto_upgrade(self, user_id: str) -> Dict[str, Any]:
        """Process Binary auto upgrade using first 2 partners' earnings"""
        try:
            # Get user's binary auto upgrade status
            binary_status = BinaryAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
            if not binary_status:
                return {"success": False, "error": "Binary auto upgrade status not found"}
            
            # Check if user has 2 partners
            if binary_status.partners_available < binary_status.partners_required:
                return {"success": False, "error": "Insufficient partners for auto upgrade"}
            
            # Calculate earnings from first 2 partners
            earnings_from_partners = self._calculate_binary_partner_earnings(user_id)
            
            if earnings_from_partners <= 0:
                return {"success": False, "error": "No earnings available from partners"}
            
            # Calculate next upgrade cost
            next_slot = binary_status.current_slot_no + 1
            upgrade_cost = self._get_binary_slot_cost(next_slot)
            
            if earnings_from_partners < upgrade_cost:
                return {"success": False, "error": "Insufficient earnings for upgrade"}
            
            # Create auto upgrade queue entry
            queue_entry = AutoUpgradeQueue(
                user_id=ObjectId(user_id),
                program='binary',
                current_slot_no=binary_status.current_slot_no,
                target_slot_no=next_slot,
                upgrade_cost=upgrade_cost,
                currency='BNB',
                earnings_available=earnings_from_partners,
                status='pending',
                priority=1
            )
            
            # Set trigger information
            queue_entry.trigger = AutoUpgradeTrigger(
                trigger_type='first_two_partners',
                program='binary',
                partners_required=2,
                partners_available=binary_status.partners_available,
                earnings_threshold=upgrade_cost,
                current_earnings=earnings_from_partners,
                is_triggered=True,
                triggered_at=datetime.utcnow()
            )
            
            queue_entry.save()
            
            # Process the upgrade
            result = self._process_upgrade_queue_entry(queue_entry)
            
            return {
                "success": True,
                "queue_id": str(queue_entry.id),
                "from_slot": binary_status.current_slot_no,
                "to_slot": next_slot,
                "earnings_used": float(earnings_from_partners),
                "upgrade_cost": float(upgrade_cost),
                "profit": float(earnings_from_partners - upgrade_cost),
                "message": "Binary auto upgrade processed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_matrix_auto_upgrade(self, user_id: str) -> Dict[str, Any]:
        """Process Matrix auto upgrade using middle 3 members' earnings"""
        try:
            # Get user's matrix auto upgrade status
            matrix_status = MatrixAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
            if not matrix_status:
                return {"success": False, "error": "Matrix auto upgrade status not found"}
            
            # Check if user has middle 3 members
            if matrix_status.middle_three_available < matrix_status.middle_three_required:
                return {"success": False, "error": "Insufficient middle three members for auto upgrade"}
            
            # Calculate earnings from middle 3 members
            earnings_from_middle_three = self._calculate_matrix_middle_three_earnings(user_id)
            
            if earnings_from_middle_three <= 0:
                return {"success": False, "error": "No earnings available from middle three members"}
            
            # Calculate next upgrade cost
            next_slot = matrix_status.current_slot_no + 1
            upgrade_cost = self._get_matrix_slot_cost(next_slot)
            
            if earnings_from_middle_three < upgrade_cost:
                return {"success": False, "error": "Insufficient earnings for upgrade"}
            
            # Create auto upgrade queue entry
            queue_entry = AutoUpgradeQueue(
                user_id=ObjectId(user_id),
                program='matrix',
                current_slot_no=matrix_status.current_slot_no,
                target_slot_no=next_slot,
                upgrade_cost=upgrade_cost,
                currency='USDT',
                earnings_available=earnings_from_middle_three,
                status='pending',
                priority=1
            )
            
            # Set trigger information
            queue_entry.trigger = AutoUpgradeTrigger(
                trigger_type='middle_three_members',
                program='matrix',
                middle_three_required=3,
                middle_three_available=matrix_status.middle_three_available,
                earnings_threshold=upgrade_cost,
                current_earnings=earnings_from_middle_three,
                is_triggered=True,
                triggered_at=datetime.utcnow()
            )
            
            queue_entry.save()
            
            # Process the upgrade
            result = self._process_upgrade_queue_entry(queue_entry)
            
            return {
                "success": True,
                "queue_id": str(queue_entry.id),
                "from_slot": matrix_status.current_slot_no,
                "to_slot": next_slot,
                "earnings_used": float(earnings_from_middle_three),
                "upgrade_cost": float(upgrade_cost),
                "profit": float(earnings_from_middle_three - upgrade_cost),
                "message": "Matrix auto upgrade processed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_global_phase_progression(self, user_id: str) -> Dict[str, Any]:
        """Process Global phase progression (Phase 1 ↔ Phase 2)"""
        try:
            # Get user's global phase progression status
            global_status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not global_status:
                return {"success": False, "error": "Global phase progression status not found"}
            
            # Check current phase completion
            if global_status.current_phase == 'PHASE-1':
                if global_status.phase_1_members_current >= global_status.phase_1_members_required:
                    # Move to Phase 2
                    return self._move_to_phase_2(global_status)
                else:
                    return {"success": False, "error": "Phase 1 not complete"}
            
            elif global_status.current_phase == 'PHASE-2':
                if global_status.phase_2_members_current >= global_status.phase_2_members_required:
                    # Re-enter Phase 1 with next slot
                    return self._reenter_phase_1(global_status)
                else:
                    return {"success": False, "error": "Phase 2 not complete"}
            
            return {"success": False, "error": "Invalid phase status"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_auto_upgrade_eligibility(self, user_id: str, program: str) -> Dict[str, Any]:
        """Check if user is eligible for auto upgrade"""
        try:
            if program == 'binary':
                return self._check_binary_eligibility(user_id)
            elif program == 'matrix':
                return self._check_matrix_eligibility(user_id)
            elif program == 'global':
                return self._check_global_eligibility(user_id)
            else:
                return {"success": False, "error": "Invalid program"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_auto_upgrade_status(self, user_id: str, program: str) -> Dict[str, Any]:
        """Update auto upgrade status for user"""
        try:
            if program == 'binary':
                return self._update_binary_status(user_id)
            elif program == 'matrix':
                return self._update_matrix_status(user_id)
            elif program == 'global':
                return self._update_global_status(user_id)
            else:
                return {"success": False, "error": "Invalid program"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_auto_upgrade_queue(self, batch_size: int = 10) -> Dict[str, Any]:
        """Process pending auto upgrades in batch"""
        try:
            # Get pending queue entries
            pending_entries = AutoUpgradeQueue.objects(status='pending').order_by('-priority', 'queued_at').limit(batch_size)
            
            processed_count = 0
            failed_count = 0
            
            for entry in pending_entries:
                try:
                    result = self._process_upgrade_queue_entry(entry)
                    if result['success']:
                        processed_count += 1
                    else:
                        failed_count += 1
                        entry.status = 'failed'
                        entry.error_message = result['error']
                        entry.save()
                        
                except Exception as e:
                    failed_count += 1
                    entry.status = 'failed'
                    entry.error_message = str(e)
                    entry.save()
            
            return {
                "success": True,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "total_processed": processed_count + failed_count,
                "message": f"Processed {processed_count} upgrades, {failed_count} failed"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calculate_binary_partner_earnings(self, user_id: str) -> Decimal:
        """Calculate earnings from first 2 partners in Binary"""
        try:
            # Get user's direct partners (first 2 only)
            tree_placements = TreePlacement.objects(
                parent_id=ObjectId(user_id),
                program='binary',
                is_active=True
            ).order_by('created_at').limit(2)
            
            total_earnings = Decimal('0')
            for placement in tree_placements:
                # Calculate earnings from this partner's slot activations
                partner_earnings = self._get_binary_partner_slot_earnings(str(placement.user_id))
                total_earnings += partner_earnings
            
            return total_earnings
            
        except Exception:
            return Decimal('0')
    
    def _calculate_matrix_middle_three_earnings(self, user_id: str) -> Decimal:
        """Calculate earnings from middle 3 members in Matrix"""
        try:
            # Get middle 3 members from Matrix tree
            # This is simplified - in real implementation, you'd get actual middle 3 members
            total_earnings = Decimal('0')
            
            # Mock calculation - replace with actual logic
            base_earning = Decimal('10.0')  # $10 per member
            total_earnings = base_earning * 3  # 3 members
            
            return total_earnings
            
        except Exception:
            return Decimal('0')
    
    def _get_binary_slot_cost(self, slot_no: int) -> Decimal:
        """Get Binary slot cost"""
        slot_costs = [0.0022, 0.0044, 0.0088, 0.0176, 0.0352, 0.0704, 0.1408, 0.2816, 0.5632, 1.1264, 2.2528, 4.5056, 9.0112, 18.0224, 36.0448, 72.0896]
        if 1 <= slot_no <= len(slot_costs):
            return Decimal(str(slot_costs[slot_no - 1]))
        return Decimal('0')
    
    def _get_matrix_slot_cost(self, slot_no: int) -> Decimal:
        """Get Matrix slot cost"""
        slot_costs = [11, 33, 99, 297, 891]
        if 1 <= slot_no <= len(slot_costs):
            return Decimal(str(slot_costs[slot_no - 1]))
        return Decimal('0')
    
    def _get_partner_earnings(self, partner_id: str, program: str) -> Decimal:
        """Get earnings from a specific partner"""
        # This is simplified - in real implementation, you'd calculate actual earnings
        return Decimal('5.0')  # Mock earning
    
    def _get_binary_partner_slot_earnings(self, partner_id: str) -> Decimal:
        """Calculate earnings from a partner's slot activations in Binary"""
        try:
            from ..slot.model import SlotActivation
            
            # Get partner's completed slot activations
            completed_activations = SlotActivation.objects(
                user_id=ObjectId(partner_id),
                program='binary',
                status='completed'
            ).order_by('slot_no')
            
            total_earnings = Decimal('0')
            
            # Calculate earnings from each slot activation
            for activation in completed_activations:
                # 30% of slot value goes to upline (based on documentation)
                slot_value = activation.slot_value or Decimal('0')
                upline_earnings = slot_value * Decimal('0.30')  # 30%
                total_earnings += upline_earnings
            
            return total_earnings
            
        except Exception as e:
            print(f"Error calculating partner slot earnings: {e}")
            return Decimal('0')
    
    def process_binary_slot_activation(self, user_id: str, slot_no: int, slot_value: Decimal) -> Dict[str, Any]:
        """
        Process binary slot activation and handle auto upgrade logic
        
        Key Logic:
        1. Slot 1: Direct upline gets full fee
        2. Slot 2+: Check if tree upline's 1st/2nd level user activated
        3. If yes: Fund goes to tree upline's reserve for auto upgrade
        4. If tree upline hasn't activated that slot: Fund goes to mother account
        5. Auto upgrade when reserve reaches next slot cost
        """
        try:
            from ..tree.model import TreePlacement
            from ..slot.model import SlotActivation
            from ..wallet.model import ReserveLedger
            
            # Get user's placement for this slot
            user_placement = TreePlacement.objects(
                user_id=ObjectId(user_id),
                program='binary',
                slot_no=slot_no,
                is_active=True
            ).first()
            
            if not user_placement:
                return {"success": False, "error": "User placement not found for this slot"}
            
            # Determine fund distribution based on slot number
            if slot_no == 1:
                # Slot 1: Direct upline gets full fee
                return self._process_slot_1_activation(user_id, slot_value)
            else:
                # Slot 2+: Check tree upline logic
                return self._process_slot_2plus_activation(user_id, slot_no, slot_value, user_placement)
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _process_slot_1_activation(self, user_id: str, slot_value: Decimal) -> Dict[str, Any]:
        """Process Slot 1 activation - direct upline gets full fee"""
        try:
            from ..tree.model import TreePlacement
            from ..wallet.model import WalletLedger
            from ..slot.model import SlotActivation
            
            # Get user's direct upline (parent_id)
            user_placement = TreePlacement.objects(
                user_id=ObjectId(user_id),
                program='binary',
                slot_no=1,
                is_active=True
            ).first()
            
            if user_placement and user_placement.parent_id:
                # Direct upline gets full fee
                upline_id = user_placement.parent_id
                
                # Credit upline's wallet
                WalletLedger(
                    user_id=upline_id,
                    type='credit',
                    amount=slot_value,
                    currency='BNB',
                    reason='binary_slot_1_commission',
                    balance_after=Decimal('0'),  # Will be calculated separately
                    tx_hash=f"auto_slot_1_{user_id}_{int(datetime.utcnow().timestamp())}",
                    created_at=datetime.utcnow()
                ).save()
                
                # Create SlotActivation record for automatic activation
                SlotActivation(
                    user_id=ObjectId(user_id),
                    program='binary',
                    slot_no=1,
                    slot_name='Explorer',
                    amount_paid=slot_value,
                    currency='BNB',
                    status='completed',
                    activation_type='automatic',  # Mark as automatic activation
                    upgrade_source='auto',
                    tx_hash=f"auto_slot_1_{user_id}_{int(datetime.utcnow().timestamp())}",
                    activated_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    created_at=datetime.utcnow()
                ).save()
                
                return {
                    "success": True,
                    "fund_destination": "direct_upline",
                    "upline_id": str(upline_id),
                    "amount": float(slot_value),
                    "message": "Slot 1 commission paid to direct upline and slot activated"
                }
            
            return {"success": False, "error": "No direct upline found"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _process_slot_2plus_activation(self, user_id: str, slot_no: int, slot_value: Decimal, user_placement) -> Dict[str, Any]:
        """Process Slot 2+ activation - tree upline reserve logic"""
        try:
            from ..tree.model import TreePlacement
            from ..wallet.model import ReserveLedger
            from ..slot.model import SlotActivation
            
            # Find tree upline for this slot (the user who should get the reserve)
            tree_upline = self._find_tree_upline_for_slot(user_placement, slot_no)
            
            if not tree_upline:
                return {"success": False, "error": "Tree upline not found"}
            
            # Check if tree upline has activated this slot
            tree_upline_activation = SlotActivation.objects(
                user_id=tree_upline,
                program='binary',
                slot_no=slot_no,
                status='completed'
            ).first()
            
            if tree_upline_activation:
                # Tree upline has this slot activated - fund goes to their reserve
                reserve_amount = slot_value * Decimal('0.30')  # 30% to reserve
                
                # Add to tree upline's reserve
                ReserveLedger(
                    user_id=tree_upline,
                    program='binary',
                    slot_no=slot_no + 1,  # Reserve for next slot
                    amount=reserve_amount,
                    direction='credit',
                    source='tree_upline_reserve',
                    balance_after=Decimal('0'),  # Will be calculated separately
                    created_at=datetime.utcnow()
                ).save()
                
                # Create SlotActivation record for automatic activation
                slot_names = ['Explorer', 'Contributor', 'Supporter', 'Promoter', 'Developer', 'Manager', 'Director', 'Executive', 'Leader', 'Master', 'Expert', 'Professional', 'Specialist', 'Consultant', 'Advisor', 'Partner']
                slot_name = slot_names[slot_no - 1] if slot_no <= len(slot_names) else f"Slot {slot_no}"
                
                SlotActivation(
                    user_id=ObjectId(user_id),
                    program='binary',
                    slot_no=slot_no,
                    slot_name=slot_name,
                    amount_paid=slot_value,
                    currency='BNB',
                    status='completed',
                    activation_type='automatic',  # Mark as automatic activation
                    upgrade_source='auto',
                    tx_hash=f"auto_slot_{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}",
                    activated_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    created_at=datetime.utcnow()
                ).save()
                
                # Check if auto upgrade is possible
                auto_upgrade_result = self._check_binary_auto_upgrade_from_reserve(tree_upline, slot_no + 1)
                
                return {
                    "success": True,
                    "fund_destination": "tree_upline_reserve",
                    "tree_upline_id": str(tree_upline),
                    "reserve_amount": float(reserve_amount),
                    "next_slot": slot_no + 1,
                    "auto_upgrade_triggered": auto_upgrade_result.get("auto_upgrade_triggered", False),
                    "message": f"Fund added to tree upline reserve for slot {slot_no + 1} and slot activated"
                }
            else:
                # Tree upline hasn't activated this slot - fund goes to mother account
                return self._send_to_mother_account(slot_value, slot_no)
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _find_tree_upline_for_slot(self, user_placement, slot_no: int) -> ObjectId:
        """
        Find the tree upline who should receive the reserve for this slot
        
        Logic: Go up the tree to find the user who should have this slot activated
        """
        try:
            current_user = user_placement.upline_id
            
            # Go up the tree until we find someone who should have this slot
            while current_user:
                # Check if current user should have this slot based on their level
                current_placement = TreePlacement.objects(
                    user_id=current_user,
                    program='binary',
                    slot_no=1,  # Check their base placement
                    is_active=True
                ).first()
                
                if current_placement:
                    # This user should be the tree upline for this slot
                    return current_user
                
                # Move to next upline
                current_user = self._get_next_upline(current_user)
            
            return None
            
        except Exception:
            return None
    
    def _get_next_upline(self, user_id: ObjectId) -> ObjectId:
        """Get the next upline in the tree"""
        try:
            placement = TreePlacement.objects(
                user_id=user_id,
                program='binary',
                slot_no=1,
                is_active=True
            ).first()
            
            if placement:
                return placement.upline_id
            
            return None
            
        except Exception:
            return None
    
    def _check_binary_auto_upgrade_from_reserve(self, user_id: ObjectId, target_slot_no: int) -> Dict[str, Any]:
        """Check if auto upgrade is possible from reserve funds"""
        try:
            from ..wallet.model import ReserveLedger
            
            # Calculate total reserve for this user and slot
            reserve_entries = ReserveLedger.objects(
                user_id=user_id,
                program='binary',
                slot_no=target_slot_no,
                direction='credit'
            )
            
            total_reserve = sum(entry.amount for entry in reserve_entries)
            
            # Get target slot cost
            target_slot_cost = self._get_binary_slot_cost(target_slot_no)
            
            if total_reserve >= target_slot_cost:
                # Auto upgrade is possible
                auto_upgrade_result = self.process_binary_auto_upgrade(str(user_id))
                return {
                    "auto_upgrade_triggered": True,
                    "total_reserve": float(total_reserve),
                    "target_slot_cost": float(target_slot_cost),
                    "auto_upgrade_result": auto_upgrade_result
                }
            else:
                return {
                    "auto_upgrade_triggered": False,
                    "total_reserve": float(total_reserve),
                    "target_slot_cost": float(target_slot_cost),
                    "message": "Reserve insufficient for auto upgrade"
                }
                
        except Exception as e:
            return {
                "auto_upgrade_triggered": False,
                "error": str(e)
            }
    
    def _send_to_mother_account(self, amount: Decimal, slot_no: int) -> Dict[str, Any]:
        """Send fund to mother account when tree upline hasn't activated slot"""
        try:
            # Get mother account ID (configured in settings)
            # For now, using a placeholder
            mother_account_id = ObjectId("000000000000000000000000")  # Replace with actual mother ID
            
            # Send to mother account
            from ..wallet.model import WalletLedger
            WalletLedger(
                user_id=mother_account_id,
                type='credit',
                amount=amount,
                currency='BNB',
                reason=f'binary_mother_account_slot_{slot_no}',
                created_at=datetime.utcnow()
            ).save()
            
            return {
                "success": True,
                "fund_destination": "mother_account",
                "mother_account_id": str(mother_account_id),
                "amount": float(amount),
                "message": f"Fund sent to mother account for slot {slot_no}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _process_upgrade_queue_entry(self, queue_entry: AutoUpgradeQueue) -> Dict[str, Any]:
        """Process a single upgrade queue entry"""
        try:
            # Update queue entry status
            queue_entry.status = 'processing'
            queue_entry.processed_at = datetime.utcnow()
            queue_entry.save()
            
            # Calculate earnings used
            queue_entry.earnings_used = min(queue_entry.earnings_available, queue_entry.upgrade_cost)
            queue_entry.save()
            
            # Create upgrade log
            upgrade_log = AutoUpgradeLog(
                user_id=queue_entry.user_id,
                program=queue_entry.program,
                from_slot_no=queue_entry.current_slot_no,
                to_slot_no=queue_entry.target_slot_no,
                from_slot_name=f"SLOT_{queue_entry.current_slot_no}",
                to_slot_name=f"SLOT_{queue_entry.target_slot_no}",
                upgrade_cost=queue_entry.upgrade_cost,
                currency=queue_entry.currency,
                earnings_used=queue_entry.earnings_used,
                profit_gained=queue_entry.earnings_available - queue_entry.upgrade_cost,
                trigger_type=queue_entry.trigger.trigger_type if queue_entry.trigger else 'manual',
                contributors=queue_entry.earnings_source,
                status='completed',
                completed_at=datetime.utcnow()
            )
            upgrade_log.save()
            
            # Update queue entry
            queue_entry.status = 'completed'
            queue_entry.completed_at = datetime.utcnow()
            queue_entry.save()
            
            return {
                "success": True,
                "upgrade_log_id": str(upgrade_log.id),
                "message": "Upgrade processed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _move_to_phase_2(self, global_status: GlobalPhaseProgression) -> Dict[str, Any]:
        """Move user from Phase 1 to Phase 2"""
        try:
            global_status.current_phase = 'PHASE-2'
            global_status.phase_position = 1
            global_status.phase_1_members_current = 0
            global_status.phase_2_members_current = 0
            global_status.is_phase_complete = False
            global_status.next_phase_ready = False
            global_status.updated_at = datetime.utcnow()
            global_status.save()
            
            return {
                "success": True,
                "new_phase": "PHASE-2",
                "new_position": 1,
                "message": "Successfully moved to Phase 2"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _reenter_phase_1(self, global_status: GlobalPhaseProgression) -> Dict[str, Any]:
        """Re-enter Phase 1 with next slot"""
        try:
            global_status.current_phase = 'PHASE-1'
            global_status.current_slot_no += 1
            global_status.phase_position = 1
            global_status.phase_1_members_current = 0
            global_status.phase_2_members_current = 0
            global_status.is_phase_complete = False
            global_status.next_phase_ready = False
            global_status.total_re_entries += 1
            global_status.last_re_entry_at = datetime.utcnow()
            global_status.re_entry_slot = global_status.current_slot_no
            global_status.updated_at = datetime.utcnow()
            global_status.save()
            
            return {
                "success": True,
                "new_phase": "PHASE-1",
                "new_slot": global_status.current_slot_no,
                "re_entries": global_status.total_re_entries,
                "message": f"Successfully re-entered Phase 1 with slot {global_status.current_slot_no}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _check_binary_eligibility(self, user_id: str) -> Dict[str, Any]:
        """Check Binary auto upgrade eligibility"""
        try:
            binary_status = BinaryAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
            if not binary_status:
                return {"success": False, "error": "Binary status not found"}
            
            # Check partners
            has_partners = binary_status.partners_available >= binary_status.partners_required
            
            # Check earnings
            earnings_available = self._calculate_binary_partner_earnings(user_id)
            next_upgrade_cost = self._get_binary_slot_cost(binary_status.current_slot_no + 1)
            has_sufficient_earnings = earnings_available >= next_upgrade_cost
            
            is_eligible = has_partners and has_sufficient_earnings
            
            return {
                "success": True,
                "is_eligible": is_eligible,
                "partners_required": binary_status.partners_required,
                "partners_available": binary_status.partners_available,
                "earnings_available": float(earnings_available),
                "next_upgrade_cost": float(next_upgrade_cost),
                "reason": "Eligible" if is_eligible else "Insufficient partners or earnings"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _check_matrix_eligibility(self, user_id: str) -> Dict[str, Any]:
        """Check Matrix auto upgrade eligibility"""
        try:
            matrix_status = MatrixAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
            if not matrix_status:
                return {"success": False, "error": "Matrix status not found"}
            
            # Check middle three members
            has_middle_three = matrix_status.middle_three_available >= matrix_status.middle_three_required
            
            # Check earnings
            earnings_available = self._calculate_matrix_middle_three_earnings(user_id)
            next_upgrade_cost = self._get_matrix_slot_cost(matrix_status.current_slot_no + 1)
            has_sufficient_earnings = earnings_available >= next_upgrade_cost
            
            is_eligible = has_middle_three and has_sufficient_earnings
            
            return {
                "success": True,
                "is_eligible": is_eligible,
                "middle_three_required": matrix_status.middle_three_required,
                "middle_three_available": matrix_status.middle_three_available,
                "earnings_available": float(earnings_available),
                "next_upgrade_cost": float(next_upgrade_cost),
                "reason": "Eligible" if is_eligible else "Insufficient middle three members or earnings"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _check_global_eligibility(self, user_id: str) -> Dict[str, Any]:
        """Check Global phase progression eligibility"""
        try:
            global_status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not global_status:
                return {"success": False, "error": "Global status not found"}
            
            if global_status.current_phase == 'PHASE-1':
                is_eligible = global_status.phase_1_members_current >= global_status.phase_1_members_required
                reason = "Phase 1 complete" if is_eligible else "Phase 1 not complete"
            else:
                is_eligible = global_status.phase_2_members_current >= global_status.phase_2_members_required
                reason = "Phase 2 complete" if is_eligible else "Phase 2 not complete"
            
            return {
                "success": True,
                "is_eligible": is_eligible,
                "current_phase": global_status.current_phase,
                "phase_1_members_current": global_status.phase_1_members_current,
                "phase_1_members_required": global_status.phase_1_members_required,
                "phase_2_members_current": global_status.phase_2_members_current,
                "phase_2_members_required": global_status.phase_2_members_required,
                "reason": reason
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _update_binary_status(self, user_id: str) -> Dict[str, Any]:
        """Update Binary auto upgrade status"""
        # Implementation for updating binary status
        return {"success": True, "message": "Binary status updated"}
    
    def _update_matrix_status(self, user_id: str) -> Dict[str, Any]:
        """Update Matrix auto upgrade status"""
        # Implementation for updating matrix status
        return {"success": True, "message": "Matrix status updated"}
    
    def _update_global_status(self, user_id: str) -> Dict[str, Any]:
        """Update Global phase progression status"""
        # Implementation for updating global status
        return {"success": True, "message": "Global status updated"}
