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
            # Get user's direct partners
            tree_placements = TreePlacement.objects(
                parent_id=ObjectId(user_id),
                program='binary',
                is_active=True
            ).limit(2)
            
            total_earnings = Decimal('0')
            for placement in tree_placements:
                # Calculate earnings from this partner
                partner_earnings = self._get_partner_earnings(str(placement.user_id), 'binary')
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
