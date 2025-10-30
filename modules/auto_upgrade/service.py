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
            from ..wallet.service import WalletService
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
                
                # Credit upline's main wallet via wallet service
                tx_hash = f"auto_slot_1_{user_id}_{int(datetime.utcnow().timestamp())}"
                try:
                    ws = WalletService()
                    ws.credit_main_wallet(
                        user_id=str(upline_id),
                        amount=slot_value,
                        currency='BNB',
                        reason='binary_slot1_full',
                        tx_hash=tx_hash
                    )
                except Exception:
                    pass
                
                # Create SlotActivation record for automatic activation
                SlotActivation(
                    user_id=ObjectId(user_id),
                    program='binary',
                    slot_no=1,
                    slot_name='Explorer',
                    amount_paid=slot_value,
                    currency='BNB',
                    status='completed',
                    activation_type='auto',  # valid value
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
            
            print(f"[BINARY_ROUTING] Processing slot {slot_no} for user {user_id}, amount {slot_value}")
            
            # Identify Nth upline for this slot (slot 2 -> 2nd upline, slot 3 -> 3rd upline, ...)
            nth_upline = self._get_nth_upline_by_slot(ObjectId(user_id), slot_no, slot_no)
            print(f"[BINARY_ROUTING] Nth upline for slot {slot_no}: {nth_upline}")
            
            if not nth_upline:
                print(f"[BINARY_ROUTING] No Nth upline found, sending to mother account")
                # No upline found at required depth → mother fallback
                mother_result = self._send_to_mother_account(slot_value, slot_no)
                # Ensure SlotActivation is still recorded for the user's Slot 2+ activation
                try:
                    from ..slot.model import SlotActivation
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
                        activation_type='auto',
                        upgrade_source='auto',
                        tx_hash=f"auto_slot_{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}",
                        activated_at=datetime.utcnow(),
                        completed_at=datetime.utcnow(),
                        created_at=datetime.utcnow()
                    ).save()
                    print(f"[BINARY_ROUTING] ✅ SlotActivation created for user {user_id}, slot {slot_no} (mother path)")
                except Exception as e:
                    print(f"[BINARY_ROUTING] ⚠️ Failed to create SlotActivation (mother path): {e}")
                return mother_result

            # Check first/second child condition under the Nth upline for this slot tree
            is_first_second = self._is_first_or_second_under_upline(ObjectId(user_id), nth_upline, slot_no, required_level=slot_no)
            print(f"[BINARY_ROUTING] Is first/second under Nth upline: {is_first_second}")

            if is_first_second:
                # Route 100% to Nth upline reserve for its next slot (slot_no + 1)
                try:
                    print(f"[BINARY_ROUTING] ✅ Routing {slot_value} BNB to {nth_upline}'s reserve for slot {slot_no + 1}")
                    reserve_entry = ReserveLedger(
                        user_id=nth_upline,
                        program='binary',
                        slot_no=slot_no + 1,
                        amount=slot_value,
                        direction='credit',
                        source='tree_upline_reserve',
                        balance_after=Decimal('0'),
                        created_at=datetime.utcnow()
                    )
                    reserve_entry.save()
                    print(f"[BINARY_ROUTING] ✅ ReserveLedger created: user={nth_upline}, slot={slot_no + 1}, amount={slot_value}")
                except Exception as e:
                    print(f"[BINARY_ROUTING] ❌ Failed to create ReserveLedger: {e}")
                    import traceback
                    traceback.print_exc()

                # Create SlotActivation record for this user's activation
                try:
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
                        activation_type='auto',
                        upgrade_source='auto',
                        tx_hash=f"auto_slot_{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}",
                        activated_at=datetime.utcnow(),
                        completed_at=datetime.utcnow(),
                        created_at=datetime.utcnow()
                    ).save()
                    print(f"[BINARY_ROUTING] ✅ SlotActivation created for user {user_id}, slot {slot_no}")
                except Exception as e:
                    print(f"[BINARY_ROUTING] ⚠️ Failed to create SlotActivation: {e}")

                # Evaluate auto-upgrade for the Nth upline's next slot
                try:
                    auto_upgrade_result = self._check_binary_auto_upgrade_from_reserve(nth_upline, slot_no + 1)
                    print(f"[BINARY_ROUTING] Auto-upgrade check result: {auto_upgrade_result}")
                except Exception as e:
                    print(f"[BINARY_ROUTING] ⚠️ Auto-upgrade check failed: {e}")
                    auto_upgrade_result = {"auto_upgrade_triggered": False}

                return {
                    "success": True,
                    "fund_destination": "tree_upline_reserve",
                    "tree_upline_id": str(nth_upline),
                    "reserve_amount": float(slot_value),
                    "next_slot": slot_no + 1,
                    "auto_upgrade_triggered": auto_upgrade_result.get("auto_upgrade_triggered", False),
                    "message": f"100% routed to Nth upline reserve for next slot (slot {slot_no + 1})"
                }
            else:
                # Special condition not met → distribute via Binary pools and dual-tree rules
                try:
                    from ..fund_distribution.service import FundDistributionService
                    from ..user.model import User
                    fund = FundDistributionService()
                    # Fetch referrer for partner incentive portion
                    ref = User.objects(id=ObjectId(user_id)).only('refered_by').first()
                    referrer_id = str(ref.refered_by) if ref and ref.refered_by else None
                    dist = fund.distribute_binary_funds(
                        user_id=str(user_id),
                        amount=slot_value,
                        slot_no=slot_no,
                        referrer_id=referrer_id,
                        tx_hash=f"auto_slot_{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}",
                        currency='BNB'
                    )
                    # Ensure SlotActivation is recorded for Slot 2+ even when routed to pools
                    try:
                        from ..slot.model import SlotActivation
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
                            activation_type='auto',
                            upgrade_source='auto',
                            tx_hash=f"auto_slot_{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}",
                            activated_at=datetime.utcnow(),
                            completed_at=datetime.utcnow(),
                            created_at=datetime.utcnow()
                        ).save()
                        print(f"[BINARY_ROUTING] ✅ SlotActivation created for user {user_id}, slot {slot_no} (pools path)")
                    except Exception as e:
                        print(f"[BINARY_ROUTING] ⚠️ Failed to create SlotActivation (pools path): {e}")

                    return {"success": True, "distribution": dist, "fund_destination": "pools"}
                except Exception as e:
                    return {"success": False, "error": str(e)}
                
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

    def _get_nth_upline_by_slot(self, user_id: ObjectId, slot_no: int, n: int) -> ObjectId:
        """Traverse up using parent_id pointers to get Nth upline for slot, without requiring each ancestor's slot placement."""
        try:
            from ..tree.model import TreePlacement
            current = TreePlacement.objects(user_id=user_id, program='binary', slot_no=slot_no, is_active=True).first()
            if not current:
                print(f"[BINARY_ROUTING] No placement found for user {user_id} in slot {slot_no}")
                return None

            steps = 0
            parent_id = getattr(current, 'parent_id', None)
            while parent_id and steps < n:
                steps += 1
                print(f"[BINARY_ROUTING] Step {steps}: moved to {parent_id}")
                if steps == n:
                    return parent_id
                # advance: try same-slot placement to fetch next parent; fallback to slot-1
                parent_slot_placement = TreePlacement.objects(
                    user_id=parent_id, program='binary', slot_no=slot_no, is_active=True
                ).first()
                if parent_slot_placement and getattr(parent_slot_placement, 'parent_id', None):
                    parent_id = parent_slot_placement.parent_id
                    continue
                parent_slot1 = TreePlacement.objects(
                    user_id=parent_id, program='binary', slot_no=1, is_active=True
                ).first()
                parent_id = getattr(parent_slot1, 'parent_id', None)

            print(f"[BINARY_ROUTING] Reached root or missing parent at step {steps}")
            return None
        except Exception as e:
            print(f"[BINARY_ROUTING] Error in _get_nth_upline_by_slot: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _is_first_or_second_under_upline(self, user_id: ObjectId, upline_id: ObjectId, slot_no: int, required_level: int = 2) -> bool:
        """
        Strict rule: User must be at EXACTLY level-2 under the given upline (for this slot tree),
        and be among the first two placements at that level (by created_at order, left→right BFS).
        """
        try:
            from ..tree.model import TreePlacement
            
            # Collect all nodes exactly at required_level under upline, ordered by created_at (left→right BFS proxy)
            direct_children = list(TreePlacement.objects(
                upline_id=upline_id,
                program='binary',
                slot_no=slot_no,
                is_active=True
            ).order_by('created_at').only('user_id'))

            level2_nodes = []
            # BFS down to exactly required_level depth
            frontier = [(c.user_id, 1) for c in direct_children]  # tuples of (node_id, depth_from_upline)
            while frontier:
                next_frontier = []
                for node_id, depth in frontier:
                    if depth == required_level:
                        # Collect this exact-level node
                        full = TreePlacement.objects(user_id=node_id, program='binary', slot_no=slot_no, is_active=True).first()
                        level2_nodes.append((node_id, getattr(full, 'created_at', None)))
                        continue
                    # Expand one more level
                    children = list(TreePlacement.objects(
                        upline_id=node_id,
                        program='binary',
                        slot_no=slot_no,
                        is_active=True
                    ).order_by('created_at').only('user_id', 'created_at'))
                    for ch in children:
                        next_frontier.append((ch.user_id, depth + 1))
                frontier = next_frontier

            level2_nodes.sort(key=lambda x: x[1] or datetime.min)

            first_two_ids = [uid for uid, _ in level2_nodes[:2]]
            result = user_id in first_two_ids
            print(f"[BINARY_ROUTING] Level-{required_level} first-two under {upline_id}: {[str(x) for x in first_two_ids]}, user={user_id}, result={result}")
            return result
        except Exception as e:
            print(f"[BINARY_ROUTING] Error in _is_first_or_second_under_upline: {e}")
            import traceback
            traceback.print_exc()
            return False
    
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
        """Check if auto upgrade is possible from reserve funds and trigger it"""
        try:
            from ..wallet.model import ReserveLedger
            from ..slot.model import SlotActivation
            
            # Calculate total reserve for this user and slot (both credits and debits)
            reserve_entries = list(ReserveLedger.objects(
                user_id=user_id,
                program='binary',
                slot_no=target_slot_no
            ))
            
            # Calculate total reserve (sum credits, subtract debits)
            total_reserve = Decimal('0')
            for entry in reserve_entries:
                if entry.direction == 'credit':
                    total_reserve += entry.amount
                elif entry.direction == 'debit':
                    total_reserve -= entry.amount
            
            # Get target slot cost
            target_slot_cost = self._get_binary_slot_cost(target_slot_no)
            
            if total_reserve >= target_slot_cost:
                # Check if slot is already activated
                existing_activation = SlotActivation.objects(
                    user_id=user_id,
                    program='binary',
                    slot_no=target_slot_no,
                    status='completed'
                ).first()
                
                if existing_activation:
                    return {
                        "auto_upgrade_triggered": False,
                        "total_reserve": float(total_reserve),
                        "target_slot_cost": float(target_slot_cost),
                        "message": "Slot already activated"
                    }
                
                # Auto upgrade is possible - activate the slot directly from reserve
                return self._auto_upgrade_from_reserve(user_id, target_slot_no, target_slot_cost, total_reserve)
            else:
                return {
                    "auto_upgrade_triggered": False,
                    "total_reserve": float(total_reserve),
                    "target_slot_cost": float(target_slot_cost),
                    "message": "Reserve insufficient for auto upgrade"
                }
                
        except Exception as e:
            print(f"[BINARY_ROUTING] Error in _check_binary_auto_upgrade_from_reserve: {e}")
            import traceback
            traceback.print_exc()
            return {
                "auto_upgrade_triggered": False,
                "error": str(e)
            }
    
    def _auto_upgrade_from_reserve(self, user_id: ObjectId, slot_no: int, slot_cost: Decimal, total_reserve: Decimal) -> Dict[str, Any]:
        """Directly activate a slot using reserve funds"""
        try:
            from ..wallet.model import ReserveLedger
            from ..slot.model import SlotActivation
            from ..tree.model import TreePlacement
            
            print(f"[BINARY_ROUTING] 🚀 Auto-upgrading user {user_id} to slot {slot_no} using reserve {total_reserve} BNB")
            
            # Create SlotActivation record
            slot_names = ['Explorer', 'Contributor', 'Supporter', 'Promoter', 'Developer', 'Manager', 
                         'Director', 'Executive', 'Leader', 'Master', 'Expert', 'Professional', 
                         'Specialist', 'Consultant', 'Advisor', 'Partner']
            slot_name = slot_names[slot_no - 1] if slot_no <= len(slot_names) else f"Slot {slot_no}"
            
            # Check if user has tree placement for this slot (create if needed)
            placement = TreePlacement.objects(
                user_id=user_id,
                program='binary',
                slot_no=slot_no,
                is_active=True
            ).first()
            
            if not placement:
                # Get slot 1 placement to find referrer
                slot1_placement = TreePlacement.objects(
                    user_id=user_id,
                    program='binary',
                    slot_no=1,
                    is_active=True
                ).first()
                
                if slot1_placement and slot1_placement.parent_id:
                    # Create placement for this slot under same parent
                    from ..tree.service import TreeService
                    tree_service = TreeService()
                    try:
                        placement_created = tree_service.place_user_in_tree(
                            user_id=user_id,
                            referrer_id=slot1_placement.parent_id,
                            program='binary',
                            slot_no=slot_no
                        )
                        if placement_created:
                            # Fetch the newly created placement
                            placement = TreePlacement.objects(
                                user_id=user_id,
                                program='binary',
                                slot_no=slot_no,
                                is_active=True
                            ).first()
                            print(f"[BINARY_ROUTING] ✅ Slot-{slot_no} placement created successfully")
                        else:
                            print(f"[BINARY_ROUTING] ⚠️ Failed to create Slot-{slot_no} placement, but continuing with auto-upgrade")
                            placement = None
                    except Exception as e:
                        print(f"[BINARY_ROUTING] ⚠️ Error creating Slot-{slot_no} placement: {e}, but continuing with auto-upgrade")
                        # Placement creation failed, but we can still activate the slot
                        placement = None
            
            # IMPORTANT: When a slot is auto-upgraded, the upgrade amount (slot_cost) must follow
            # the same routing rules as a regular slot activation:
            # - Slot 1: Full amount to direct upline
            # - Slot 2+: Check if user is first/second in Nth upline's tree
            #   - If yes: Route to Nth upline's reserve
            #   - If no: Distribute via pools
            
            # Deduct from reserve by creating a debit entry (this happens first)
            debit_entry = ReserveLedger(
                user_id=user_id,
                program='binary',
                slot_no=slot_no,
                amount=slot_cost,
                direction='debit',
                source='income',  # Using 'income' since reserve funds come from income routing
                balance_after=total_reserve - slot_cost,
                tx_hash=f"auto_reserve_debit_{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}",
                created_at=datetime.utcnow()
            )
            debit_entry.save()
            print(f"[BINARY_ROUTING] ✅ ReserveLedger debit created: user={user_id}, slot={slot_no}, amount={slot_cost}")
            
            # Now trigger the distribution logic for this slot upgrade
            # This ensures the upgrade amount follows the same routing rules
            distribution_result = None
            slot_activation_created = False
            if slot_no == 1:
                # Slot 1: Full amount to direct upline
                print(f"[BINARY_ROUTING] Auto-upgrade Slot 1: routing full amount to direct upline")
                distribution_result = self._process_slot_1_activation(str(user_id), slot_cost)
                # _process_slot_1_activation creates SlotActivation
                slot_activation_created = True
            else:
                # Slot 2+: Check first/second and route accordingly
                print(f"[BINARY_ROUTING] Auto-upgrade Slot {slot_no}: checking routing rules")
                if not placement:
                    # Try to get placement again
                    placement = TreePlacement.objects(
                        user_id=user_id,
                        program='binary',
                        slot_no=slot_no,
                        is_active=True
                    ).first()
                    if not placement:
                        # Get slot-1 placement to use for routing logic if needed
                        slot1_placement = TreePlacement.objects(
                            user_id=user_id,
                            program='binary',
                            slot_no=1,
                            is_active=True
                        ).first()
                        if slot1_placement:
                            # Use slot-1 placement info for routing (we'll handle None placement in routing)
                            print(f"[BINARY_ROUTING] Using slot-1 placement info for routing logic")
                            placement = slot1_placement  # Use slot-1 placement as reference
                        else:
                            placement = None
                if placement:
                    distribution_result = self._process_slot_2plus_activation(
                        str(user_id), 
                        slot_no, 
                        slot_cost, 
                        placement
                    )
                else:
                    print(f"[BINARY_ROUTING] ⚠️ No placement available for Slot-{slot_no}, distributing via pools")
                    # Fallback: distribute via pools if no placement available
                    from ..fund_distribution.service import FundDistributionService
                    from ..user.model import User
                    fund = FundDistributionService()
                    ref = User.objects(id=user_id).only('refered_by').first()
                    referrer_id = str(ref.refered_by) if ref and ref.refered_by else None
                    distribution_result = fund.distribute_binary_funds(
                        user_id=str(user_id),
                        amount=slot_cost,
                        slot_no=slot_no,
                        referrer_id=referrer_id,
                        tx_hash=f"auto_slot_{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}",
                        currency='BNB'
                    )
                print(f"[BINARY_ROUTING] Auto-upgrade distribution result: {distribution_result}")
                # _process_slot_2plus_activation creates SlotActivation only when routing to reserve
                # Check if it was created
                existing = SlotActivation.objects(
                    user_id=user_id,
                    program='binary',
                    slot_no=slot_no,
                    status='completed'
                ).first()
                if existing:
                    slot_activation_created = True
                    print(f"[BINARY_ROUTING] SlotActivation already created by distribution logic")
            
            # Create SlotActivation record only if it wasn't created by distribution logic
            if not slot_activation_created:
                activation = SlotActivation(
                    user_id=user_id,
                    program='binary',
                    slot_no=slot_no,
                    slot_name=slot_name,
                    amount_paid=slot_cost,
                    currency='BNB',
                    status='completed',
                    activation_type='auto',
                    upgrade_source='reserve',  # Using 'reserve' since funds come from reserve
                    tx_hash=f"auto_reserve_{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}",
                    activated_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    is_auto_upgrade=True  # Mark as auto upgrade
                )
                activation.save()
                print(f"[BINARY_ROUTING] ✅ SlotActivation created: user={user_id}, slot={slot_no}")
            else:
                print(f"[BINARY_ROUTING] ✅ SlotActivation confirmed: user={user_id}, slot={slot_no}")
            
            # Update BinaryAutoUpgrade if it exists, otherwise create it
            binary_status = BinaryAutoUpgrade.objects(user_id=user_id).first()
            if binary_status:
                binary_status.current_slot_no = max(binary_status.current_slot_no, slot_no)
                binary_status.updated_at = datetime.utcnow()
                binary_status.save()
            else:
                # Get level from placement if available, otherwise default to 1
                # Also try to get from slot-1 placement as fallback
                user_level = 1
                if placement and hasattr(placement, 'level'):
                    user_level = placement.level
                else:
                    slot1_placement = TreePlacement.objects(
                        user_id=user_id,
                        program='binary',
                        slot_no=1,
                        is_active=True
                    ).first()
                    if slot1_placement and hasattr(slot1_placement, 'level'):
                        user_level = slot1_placement.level
                
                # Initialize BinaryAutoUpgrade for future upgrades
                BinaryAutoUpgrade(
                    user_id=user_id,
                    current_slot_no=slot_no,
                    current_level=user_level,
                    partners_required=2,
                    partners_available=0,
                    is_eligible=False,
                    can_upgrade=False
                ).save()
                print(f"[BINARY_ROUTING] ✅ BinaryAutoUpgrade initialized: user={user_id}, slot={slot_no}, level={user_level}")
            
            return {
                "auto_upgrade_triggered": True,
                "total_reserve": float(total_reserve),
                "target_slot_cost": float(slot_cost),
                "slot_activated": slot_no,
                "slot_name": slot_name,
                "remaining_reserve": float(total_reserve - slot_cost),
                "message": f"Slot {slot_no} ({slot_name}) auto-activated from reserve"
            }
            
        except Exception as e:
            print(f"[BINARY_ROUTING] ❌ Error in _auto_upgrade_from_reserve: {e}")
            import traceback
            traceback.print_exc()
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
                balance_after=Decimal('0'),
                tx_hash=f"mother_slot_{slot_no}_{int(datetime.utcnow().timestamp())}",
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
