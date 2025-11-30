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
                mother_result = self._send_to_mother_account(
                    slot_value,
                    slot_no,
                    missed_user_id=user_placement.parent_id,
                    from_user_id=user_id,
                    reason=f"Slot {slot_no} level payout missed by direct upline"
                )
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
            # For slot N: Check if user is in Nth level of Nth upline in slot-N tree
            is_first_second = self._is_first_or_second_under_upline(ObjectId(user_id), nth_upline, slot_no, required_level=slot_no)
            print(f"[BINARY_ROUTING] Is first/second under Nth upline (slot {slot_no}, level {slot_no}): {is_first_second}")

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
                    print(f"[BINARY_ROUTING] Failed to create ReserveLedger: {e}")
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
                    
                    # Award jackpot free entry for eligible slots (5-17)
                    if 5 <= slot_no <= 17:
                        try:
                            from modules.jackpot.service import JackpotService
                            jackpot_service = JackpotService()
                            jackpot_result = jackpot_service.process_free_coupon_entry(
                                user_id=user_id,
                                slot_number=slot_no,
                                tx_hash=f"auto_slot{slot_no}_jackpot_{user_id}_{int(datetime.utcnow().timestamp())}"
                            )
                            print(f"[BINARY_ROUTING] ✅ Jackpot free entry awarded for slot {slot_no}: {jackpot_result}")
                        except Exception as e:
                            print(f"[BINARY_ROUTING] ⚠️ Failed to award jackpot entry for slot {slot_no}: {e}")
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
                        
                        # Award jackpot free entry for eligible slots (5-17)
                        if 5 <= slot_no <= 17:
                            try:
                                from modules.jackpot.service import JackpotService
                                jackpot_service = JackpotService()
                                jackpot_result = jackpot_service.process_free_coupon_entry(
                                    user_id=user_id,
                                    slot_number=slot_no,
                                    tx_hash=f"auto_slot{slot_no}_jackpot_pools_{user_id}_{int(datetime.utcnow().timestamp())}"
                                )
                                print(f"[BINARY_ROUTING] ✅ Jackpot free entry awarded for slot {slot_no} (pools path): {jackpot_result}")
                            except Exception as e:
                                print(f"[BINARY_ROUTING] ⚠️ Failed to award jackpot entry for slot {slot_no} (pools path): {e}")
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
        """
        Resolve Nth upline using the base binary tree (slot 1) upline chain so ROOT ancestry works
        even if higher-slot placements are absent. Does not require ancestors to have slot_no placement.
        """
        try:
            from ..tree.model import TreePlacement
            # Start from user's base placement (slot 1 preferred; fallback to requested slot)
            current = TreePlacement.objects(user_id=user_id, program='binary', slot_no=1, is_active=True).first()
            if not current:
                current = TreePlacement.objects(user_id=user_id, program='binary', slot_no=slot_no, is_active=True).first()
            if not current:
                print(f"[BINARY_ROUTING] No placement found for user {user_id} in base or slot {slot_no}")
                return None

            steps = 0
            upline = getattr(current, 'upline_id', None) or getattr(current, 'parent_id', None)
            while upline and steps < n:
                steps += 1
                print(f"[BINARY_ROUTING] Step {steps}: moved to {upline}")
                if steps == n:
                    return upline
                # Get next ancestor from base tree (slot 1), fallback to same slot
                next_pl = TreePlacement.objects(user_id=upline, program='binary', slot_no=1, is_active=True).first()
                if not next_pl:
                    next_pl = TreePlacement.objects(user_id=upline, program='binary', slot_no=slot_no, is_active=True).first()
                if not next_pl:
                    break
                upline = getattr(next_pl, 'upline_id', None) or getattr(next_pl, 'parent_id', None)

            print(f"[BINARY_ROUTING] Reached root or missing upline at step {steps}")
            return None
        except Exception as e:
            print(f"[BINARY_ROUTING] Error in _get_nth_upline_by_slot: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _is_first_or_second_under_upline(self, user_id: ObjectId, upline_id: ObjectId, slot_no: int, required_level: int = 2) -> bool:
        """
        Check if user is at EXACTLY level-N under the given upline in the SPECIFIC SLOT-N tree,
        and be among the first two positions at that level by deterministic positional order (LL, LR, RL, RR ...).
        
        For slot N: Check in slot-N tree (or slot-1 as fallback).
        Required level: slot_no (Nth level for Nth upline).
        Position: First (index 0 = LL...L) or Second (index 1 = LL...R) position.
        
        Args:
            user_id: The activating user
            upline_id: The Nth upline to check under
            slot_no: The slot number (N)
            required_level: The level to check (should be slot_no = N)
        """
        try:
            from ..tree.model import TreePlacement
            from mongoengine.queryset.visitor import Q

            # Use slot_no specific tree first, fallback to slot-1 if not found
            def get_lr_for_child(child_pl, check_slot_no: int) -> str:
                # Prefer explicit position
                pos = getattr(child_pl, 'position', None)
                if pos in ('left', 'right'):
                    return 'L' if pos == 'left' else 'R'
                # Fallback: derive by parent's children created_at order
                parent_id = getattr(child_pl, 'parent_id', None) or getattr(child_pl, 'upline_id', None)
                if not parent_id:
                    return 'L'  # default
                # Check in slot-specific tree first
                sibs = list(TreePlacement.objects(
                    Q(upline_id=parent_id) | Q(parent_id=parent_id),
                    program='binary', slot_no=check_slot_no, is_active=True
                ).only('user_id', 'created_at').order_by('created_at'))
                # If no siblings in slot-N tree, check slot-1
                if not sibs:
                    sibs = list(TreePlacement.objects(
                        Q(upline_id=parent_id) | Q(parent_id=parent_id),
                        program='binary', slot_no=1, is_active=True
                    ).only('user_id', 'created_at').order_by('created_at'))
                # first child => L, second => R
                for idx, s in enumerate(sibs[:2]):
                    if str(s.user_id) == str(child_pl.user_id):
                        return 'L' if idx == 0 else 'R'
                return 'L'

            # Start from user's slot-N placement (preferred), fallback to slot-1
            user_pl = TreePlacement.objects(user_id=user_id, program='binary', slot_no=slot_no, is_active=True).first()
            if not user_pl:
                user_pl = TreePlacement.objects(user_id=user_id, program='binary', slot_no=1, is_active=True).first()
            if not user_pl:
                print(f"[BINARY_ROUTING] No placement found for user {user_id} in slot {slot_no} or slot 1")
                return False

            path_bits: List[str] = []
            steps = 0
            curr = user_pl
            check_slot = slot_no  # Use slot-specific tree
            
            while curr and steps < required_level:
                parent = getattr(curr, 'upline_id', None) or getattr(curr, 'parent_id', None)
                if not parent:
                    break
                    
                # Get L/R position for this level
                lr = get_lr_for_child(curr, check_slot)
                path_bits.append(lr)
                steps += 1
                
                if parent == upline_id:
                    break
                    
                # Move up: try slot-N tree first, then slot-1
                next_pl = TreePlacement.objects(user_id=parent, program='binary', slot_no=check_slot, is_active=True).first()
                if not next_pl:
                    next_pl = TreePlacement.objects(user_id=parent, program='binary', slot_no=1, is_active=True).first()
                curr = next_pl

            # Validate we reached the upline at exactly required_level
            if steps != required_level:
                print(f"[BINARY_ROUTING] Steps mismatch: got {steps}, required {required_level}")
                return False
                
            # Verify we reached the correct upline
            if curr:
                final_parent = getattr(curr, 'upline_id', None) or getattr(curr, 'parent_id', None)
                if final_parent != upline_id:
                    print(f"[BINARY_ROUTING] Did not reach correct upline: {final_parent} != {upline_id}")
                    return False

            path_bits = list(reversed(path_bits))  # from upline -> user

            # Compute positional index for this user (binary path value)
            idx = 0
            for b in path_bits:
                idx = (idx << 1) | (0 if b == 'L' else 1)

            # Position counting: 1-based (1, 2, 3...), not 0-based (0, 1, 2...)
            # Index 0 = Position 1 (first)
            # Index 1 = Position 2 (second)
            # So first or second position means idx in (0, 1)
            position_number = idx + 1  # Convert to 1-based position for display
            is_first_or_second = idx in (0, 1)  # Position 1 or 2 (index 0 or 1)
            print(f"[BINARY_ROUTING] User {user_id} path under {upline_id} in slot-{slot_no} tree at level {required_level}: {''.join(path_bits)} (index={idx}, position={position_number}), first/second={is_first_or_second}")
            return is_first_or_second
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

            # Guard: invalid or undefined slot costs must never trigger activation
            if target_slot_cost <= 0:
                return {
                    "auto_upgrade_triggered": False,
                    "total_reserve": float(total_reserve),
                    "target_slot_cost": float(target_slot_cost),
                    "message": "Invalid target slot cost"
                }
            
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
            
            from ..tree.service import TreeService
            placement = TreeService.ensure_binary_slot_placement(user_id, slot_no)
            if placement:
                print(f"[BINARY_ROUTING] ✅ Slot-{slot_no} placement verified")
            else:
                print(f"[BINARY_ROUTING] ⚠️ Slot-{slot_no} placement missing; proceeding without placement")
            
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
            
            # IMPORTANT: When a slot auto-upgrades from reserve, the slot_cost must follow
            # the same reserve routing rules as a regular slot activation (CASCADE):
            # - Slot 1: Full amount to direct upline
            # - Slot 2+: Check if user is first/second in Nth upline's slot-N tree
            #   - If yes: Route to Nth upline's reserve for slot N+1 (cascade)
            #   - If no: Distribute via pools
            
            # Route the slot_cost following reserve routing rules (CASCADE)
            if slot_no == 1:
                # Slot 1: Full amount to direct upline
                from ..wallet.service import WalletService
                if placement and placement.parent_id:
                    ws = WalletService()
                    ws.credit_main_wallet(
                        user_id=str(placement.parent_id),
                        amount=slot_cost,
                        currency='BNB',
                        reason='binary_slot1_full',
                        tx_hash=f"auto_cascade_slot1_{user_id}_{int(datetime.utcnow().timestamp())}"
                    )
                    print(f"[BINARY_ROUTING] ✅ Cascaded slot 1 cost to direct upline: {placement.parent_id}")
            else:
                # Slot 2+: Check reserve routing rules
                nth_upline_for_cost = self._get_nth_upline_by_slot(user_id, slot_no, slot_no)
                routed_to_mother = False
                mother_reason = None
                target_upline = nth_upline_for_cost
                if nth_upline_for_cost:
                    from ..slot.model import SlotActivation
                    upline_has_slot = SlotActivation.objects(
                        user_id=nth_upline_for_cost,
                        program='binary',
                        slot_no__gte=slot_no,
                        status='completed'
                    ).first() is not None
                    if not upline_has_slot:
                        routed_to_mother = True
                        mother_reason = f"auto_upgrade_level_insufficient_slot_{slot_no}"
                        try:
                            from ..commission.service import CommissionService
                            CommissionService().handle_missed_profit(
                                user_id=str(nth_upline_for_cost),
                                from_user_id=str(user_id),
                                program='binary',
                                slot_no=slot_no,
                                slot_name=slot_name,
                                amount=slot_cost,
                                currency='BNB',
                                reason=mother_reason
                            )
                        except Exception as exc:
                            print(f"[BINARY_ROUTING] ⚠️ Failed to record auto-upgrade missed profit for upline {nth_upline_for_cost}: {exc}")
                    else:
                        is_first_second_cost = self._is_first_or_second_under_upline(user_id, nth_upline_for_cost, slot_no, required_level=slot_no)
                        if is_first_second_cost:
                            # Route to Nth upline's reserve for slot N+1 (cascade)
                            try:
                                cascade_reserve_entry = ReserveLedger(
                                    user_id=nth_upline_for_cost,
                                    program='binary',
                                    slot_no=slot_no + 1,
                                    amount=slot_cost,
                                    direction='credit',
                                    source='tree_upline_reserve',  # Changed from 'tree_upline_reserve_cascade' (not in model choices)
                                    balance_after=Decimal('0'),
                                    created_at=datetime.utcnow()
                                )
                                cascade_reserve_entry.save()
                                print(f"[BINARY_ROUTING] ✅ Cascaded slot {slot_no} cost ({slot_cost} BNB) to {nth_upline_for_cost}'s reserve for slot {slot_no + 1}")
                                
                                # Check if this triggers another auto-upgrade (CASCADE OF CASCADE)
                                try:
                                    cascade_auto_upgrade_result = self._check_binary_auto_upgrade_from_reserve(nth_upline_for_cost, slot_no + 1)
                                    if cascade_auto_upgrade_result.get("auto_upgrade_triggered"):
                                        print(f"[BINARY_ROUTING] 🚀 CASCADE: Slot {slot_no + 1} auto-upgraded for {nth_upline_for_cost} from cascaded reserve")
                                except Exception as e:
                                    print(f"[BINARY_ROUTING] ⚠️ Cascade auto-upgrade check failed: {e}")
                            except Exception as e:
                                print(f"[BINARY_ROUTING] Failed to create cascade ReserveLedger: {e}")
                        else:
                            # Not first/second: distribute via pools
                            from ..fund_distribution.service import FundDistributionService
                            from ..user.model import User
                            fund = FundDistributionService()
                            ref = User.objects(id=user_id).only('refered_by').first()
                            referrer_id = str(ref.refered_by) if ref and ref.refered_by else None
                            fund.distribute_binary_funds(
                                user_id=str(user_id),
                                amount=slot_cost,
                                slot_no=slot_no,
                                referrer_id=referrer_id,
                                tx_hash=f"auto_cascade_pools_slot{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}",
                                currency='BNB'
                            )
                            print(f"[BINARY_ROUTING] ✅ Cascaded slot {slot_no} cost distributed via pools")
                else:
                    routed_to_mother = True
                    mother_reason = f"auto_upgrade_no_upline_slot_{slot_no}"
                if routed_to_mother:
                    self._send_to_mother_account(
                        slot_cost,
                        slot_no,
                        missed_user_id=target_upline,
                        from_user_id=user_id,
                        reason=mother_reason
                    )
                    print(f"[BINARY_ROUTING] ✅ Cascaded slot {slot_no} cost sent to mother account")
            
            # Record the activation
            activation = SlotActivation(
                user_id=user_id,
                program='binary',
                slot_no=slot_no,
                slot_name=slot_name,
                amount_paid=slot_cost,
                currency='BNB',
                status='completed',
                activation_type='auto',
                upgrade_source='reserve',
                tx_hash=f"auto_reserve_{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}",
                activated_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                is_auto_upgrade=True
            )
            activation.save()
            print(f"[BINARY_ROUTING] ✅ SlotActivation created (reserve-driven): user={user_id}, slot={slot_no}")

            # Leadership Stipend auto-join & eligibility check for higher slots (10+)
            if slot_no >= 10:
                try:
                    from modules.leadership_stipend.model import LeadershipStipend
                    from modules.leadership_stipend.service import LeadershipStipendService

                    ls_service = LeadershipStipendService()
                    ls_existing = LeadershipStipend.objects(user_id=user_id).first()

                    if not ls_existing:
                        join_result = ls_service.join_leadership_stipend_program(str(user_id))
                        print(f"[BINARY_ROUTING] Leadership Stipend auto-join for user {user_id} slot {slot_no}: {join_result}")

                    stipend_result = ls_service.check_eligibility(user_id=str(user_id), force_check=True)
                    print(f"[BINARY_ROUTING] Leadership Stipend eligibility refresh for user {user_id} slot {slot_no}: {stipend_result}")
                except Exception as e:
                    print(f"[BINARY_ROUTING] ⚠️ Leadership Stipend sync failed for user {user_id} slot {slot_no}: {e}")
            
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
            print(f"[BINARY_ROUTING] Error in _auto_upgrade_from_reserve: {e}")
            import traceback
            traceback.print_exc()
            return {
                "auto_upgrade_triggered": False,
                "error": str(e)
            }
    
    def manual_upgrade_binary_slot(self, user_id: str, slot_no: int, tx_hash: str = None) -> Dict[str, Any]:
        """
        Manual binary slot upgrade using reserve + wallet payment
        
        Flow:
        1. Get slot cost and reserve balance
        2. Deduct from reserve first (up to available)
        3. Deduct remaining from wallet
        4. Create SlotActivation
        5. Route slot_cost following cascade rules (same as auto-upgrade)
           - Check Nth upline has slot N active before routing to reserve
           - If not active: route to mother wallet
           - For distribution: check user has slot N active
           - If not active: send that portion to mother wallet
        
        Returns:
            Dict with success status and activation details
        """
        try:
            from ..wallet.model import ReserveLedger, WalletLedger
            from ..slot.model import SlotActivation
            from ..wallet.service import WalletService
            from ..user.tree_reserve_service import TreeUplineReserveService
            from ..user.model import User
            
            user_oid = ObjectId(user_id)
            slot_cost = self._get_binary_slot_cost(slot_no)
            
            print(f"[MANUAL_UPGRADE] Starting manual upgrade for user {user_id} to slot {slot_no}, cost={slot_cost}")
            
            # Get reserve balance
            reserve_service = TreeUplineReserveService()
            reserve_balance = reserve_service.get_reserve_balance(user_id, 'binary', slot_no)
            
            print(f"[MANUAL_UPGRADE] Reserve balance: {reserve_balance}, Slot cost: {slot_cost}")
            
            # Calculate amounts: reserve first, then wallet
            reserve_amount = min(reserve_balance, slot_cost)
            wallet_amount = slot_cost - reserve_amount
            
            print(f"[MANUAL_UPGRADE] Reserve payment: {reserve_amount}, Wallet payment: {wallet_amount}")
            
            # Check wallet balance if needed
            if wallet_amount > 0:
                ws = WalletService()
                wallet = ws._get_or_create_wallet(user_id, 'main', 'BNB')
                current_wallet_balance = wallet.balance or Decimal('0')
                
                if current_wallet_balance < wallet_amount:
                    return {
                        "success": False,
                        "error": f"Insufficient balance. Need {wallet_amount} BNB in wallet, have {current_wallet_balance} BNB. Reserve: {reserve_balance} BNB"
                    }
            
            # Deduct from reserve (if any)
            if reserve_amount > 0:
                # Calculate new reserve balance after debit
                reserve_entries = list(ReserveLedger.objects(
                    user_id=user_oid,
                    program='binary',
                    slot_no=slot_no
                ))
                current_reserve_total = Decimal('0')
                for entry in reserve_entries:
                    if entry.direction == 'credit':
                        current_reserve_total += entry.amount
                    elif entry.direction == 'debit':
                        current_reserve_total -= entry.amount
                
                new_reserve_balance = current_reserve_total - reserve_amount
                
                reserve_debit = ReserveLedger(
                    user_id=user_oid,
                    program='binary',
                    slot_no=slot_no,
                    amount=reserve_amount,
                    direction='debit',
                    source='manual_upgrade',
                    balance_after=new_reserve_balance,
                    tx_hash=tx_hash or f"manual_reserve_debit_{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}",
                    created_at=datetime.utcnow()
                )
                reserve_debit.save()
                print(f"[MANUAL_UPGRADE] ✅ Reserve debit: {reserve_amount} BNB, new balance: {new_reserve_balance}")
            
            # Deduct from wallet (if any)
            if wallet_amount > 0:
                ws = WalletService()
                wallet_debit_result = ws.debit_main_wallet(
                    user_id=user_id,
                    amount=wallet_amount,
                    currency='BNB',
                    reason=f'manual_binary_slot_{slot_no}_upgrade',
                    tx_hash=tx_hash or f"manual_wallet_debit_{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}"
                )
                
                if not wallet_debit_result.get("success"):
                    # Rollback reserve debit if wallet debit fails
                    if reserve_amount > 0:
                        # Create a credit to reverse the debit
                        reserve_credit = ReserveLedger(
                            user_id=user_oid,
                            program='binary',
                            slot_no=slot_no,
                            amount=reserve_amount,
                            direction='credit',
                            source='manual_upgrade_rollback',
                            balance_after=current_reserve_total,  # Restore original balance
                            tx_hash=f"rollback_{reserve_debit.tx_hash}" if reserve_amount > 0 else None,
                            created_at=datetime.utcnow()
                        )
                        reserve_credit.save()
                    
                    return {
                        "success": False,
                        "error": wallet_debit_result.get("error", "Wallet debit failed")
                    }
                
                print(f"[MANUAL_UPGRADE] ✅ Wallet debit: {wallet_amount} BNB")
            
            # Create SlotActivation record
            slot_names = ['Explorer', 'Contributor', 'Supporter', 'Promoter', 'Developer', 'Manager', 
                         'Director', 'Executive', 'Leader', 'Master', 'Expert', 'Professional', 
                         'Specialist', 'Consultant', 'Advisor', 'Partner']
            slot_name = slot_names[slot_no - 1] if slot_no <= len(slot_names) else f"Slot {slot_no}"
            
            from ..tree.service import TreeService
            TreeService.ensure_binary_slot_placement(user_oid, slot_no)

            activation = SlotActivation(
                user_id=user_oid,
                program='binary',
                slot_no=slot_no,
                slot_name=slot_name,
                amount_paid=slot_cost,
                currency='BNB',
                status='completed',
                activation_type='manual',
                upgrade_source='mixed' if (reserve_amount > 0 and wallet_amount > 0) else ('reserve' if reserve_amount > 0 else 'wallet'),
                tx_hash=tx_hash or f"manual_slot_{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}",
                activated_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                is_auto_upgrade=False,
                metadata={
                    'reserve_used': float(reserve_amount),
                    'wallet_used': float(wallet_amount),
                    'payment_method': 'reserve_wallet_combined'
                }
            )
            activation.save()
            print(f"[MANUAL_UPGRADE] ✅ SlotActivation created: user={user_id}, slot={slot_no}")
            
            # Award jackpot free entry for eligible slots (5-17)
            if 5 <= slot_no <= 17:
                try:
                    from modules.jackpot.service import JackpotService
                    jackpot_service = JackpotService()
                    jackpot_result = jackpot_service.process_free_coupon_entry(
                        user_id=user_id,
                        slot_number=slot_no,
                        tx_hash=tx_hash or f"manual_slot{slot_no}_jackpot_{user_id}_{int(datetime.utcnow().timestamp())}"
                    )
                    print(f"[MANUAL_UPGRADE] ✅ Jackpot free entry awarded for slot {slot_no}: {jackpot_result}")
                except Exception as e:
                    print(f"[MANUAL_UPGRADE] ⚠️ Failed to award jackpot entry for slot {slot_no}: {e}")

            # Leadership Stipend auto-join & eligibility check for higher slots (10+)
            if slot_no >= 10:
                try:
                    from modules.leadership_stipend.model import LeadershipStipend
                    from modules.leadership_stipend.service import LeadershipStipendService

                    ls_service = LeadershipStipendService()
                    ls_existing = LeadershipStipend.objects(user_id=user_oid).first()

                    if not ls_existing:
                        join_result = ls_service.join_leadership_stipend_program(user_id)
                        print(f"[MANUAL_UPGRADE] Leadership Stipend auto-join for user {user_id} slot {slot_no}: {join_result}")

                    stipend_result = ls_service.check_eligibility(user_id=user_id, force_check=True)
                    print(f"[MANUAL_UPGRADE] Leadership Stipend eligibility refresh for user {user_id} slot {slot_no}: {stipend_result}")
                except Exception as e:
                    print(f"[MANUAL_UPGRADE] ⚠️ Leadership Stipend sync failed for user {user_id} slot {slot_no}: {e}")

            # Route slot_cost following cascade rules (same as auto-upgrade)
            self._route_manual_upgrade_cost(user_id, slot_no, slot_cost)
            
            # Update BinaryAutoUpgrade if exists
            binary_status = BinaryAutoUpgrade.objects(user_id=user_oid).first()
            if binary_status:
                binary_status.current_slot_no = max(binary_status.current_slot_no, slot_no)
                binary_status.updated_at = datetime.utcnow()
                binary_status.save()
            
            return {
                "success": True,
                "activation_id": str(activation.id),
                "slot_no": slot_no,
                "slot_name": slot_name,
                "amount_paid": float(slot_cost),
                "reserve_used": float(reserve_amount),
                "wallet_used": float(wallet_amount),
                "message": f"Successfully upgraded to {slot_name} (Slot {slot_no})"
            }
            
        except Exception as e:
            print(f"[MANUAL_UPGRADE] Error: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _route_manual_upgrade_cost(self, user_id: str, slot_no: int, slot_cost: Decimal) -> None:
        """
        Route manual upgrade cost following cascade rules
        
        Special rules:
        - Check if Nth upline has slot N active before routing to reserve
        - If not active: route to mother wallet
        - For distribution: check if user has slot N active
        - If not active: send that portion to mother wallet (only for level distribution)
        """
        try:
            from ..wallet.model import ReserveLedger
            from ..slot.model import SlotActivation
            from ..wallet.service import WalletService
            from ..tree.model import TreePlacement
            
            user_oid = ObjectId(user_id)
            
            print(f"[MANUAL_UPGRADE] Routing slot {slot_no} cost ({slot_cost} BNB) following cascade rules")
            
            # Get user's tree placement for this slot
            placement = TreePlacement.objects(
                user_id=user_oid,
                program='binary',
                slot_no=slot_no,
                is_active=True
            ).first()
            
            if not placement:
                # Try slot 1 placement as fallback
                placement = TreePlacement.objects(
                    user_id=user_oid,
                    program='binary',
                    slot_no=1,
                    is_active=True
                ).first()
            
            if slot_no == 1:
                # Slot 1: Full amount to direct upline
                ws = WalletService()
                if placement and placement.parent_id:
                    # Check if upline has slot 1 active
                    upline_slot1 = SlotActivation.objects(
                        user_id=placement.parent_id,
                        program='binary',
                        slot_no=1,
                        status='completed'
                    ).first()
                    
                    if upline_slot1:
                        ws.credit_main_wallet(
                            user_id=str(placement.parent_id),
                            amount=slot_cost,
                            currency='BNB',
                            reason='binary_slot1_full',
                            tx_hash=f"manual_cascade_slot1_{user_id}_{int(datetime.utcnow().timestamp())}"
                        )
                        print(f"[MANUAL_UPGRADE] ✅ Routed slot 1 cost to direct upline: {placement.parent_id}")
                    else:
                        # Upline doesn't have slot 1: send to mother wallet
                        self._send_to_mother_account(slot_cost, slot_no)
                        print(f"[MANUAL_UPGRADE] ✅ Routed slot 1 cost to mother wallet (upline has no slot 1)")
            else:
                # Slot 2+: Check reserve routing rules (CASCADE LOGIC)
                # According to CASCADE_AUTO_UPGRADE_EXPLANATION.md:
                # - Route based on first/second position ONLY
                # - Do NOT require Nth upline to have slot N active
                # - This enables infinite cascade chains
                nth_upline = self._get_nth_upline_by_slot(user_oid, slot_no, slot_no)
                
                if nth_upline:
                    # Check first/second position (primary condition for cascade)
                    is_first_second = self._is_first_or_second_under_upline(user_oid, nth_upline, slot_no, required_level=slot_no)
                    
                    if is_first_second:
                        # Route to Nth upline's reserve for slot N+1 (cascade)
                        try:
                            cascade_reserve_entry = ReserveLedger(
                                user_id=nth_upline,
                                program='binary',
                                slot_no=slot_no + 1,
                                amount=slot_cost,
                                direction='credit',
                                source='tree_upline_reserve',  # Same as auto-upgrade cascade
                                balance_after=Decimal('0'),
                                created_at=datetime.utcnow()
                            )
                            cascade_reserve_entry.save()
                            print(f"[MANUAL_UPGRADE] ✅ Routed slot {slot_no} cost ({slot_cost} BNB) to {nth_upline}'s reserve for slot {slot_no + 1}")
                            
                            # Check if this triggers auto-upgrade (CASCADE)
                            try:
                                cascade_auto_upgrade_result = self._check_binary_auto_upgrade_from_reserve(nth_upline, slot_no + 1)
                                if cascade_auto_upgrade_result.get("auto_upgrade_triggered"):
                                    print(f"[MANUAL_UPGRADE] 🚀 CASCADE: Slot {slot_no + 1} auto-upgraded for {nth_upline} from cascaded reserve")
                            except Exception as e:
                                print(f"[MANUAL_UPGRADE] ⚠️ Cascade auto-upgrade check failed: {e}")
                        except Exception as e:
                            print(f"[MANUAL_UPGRADE] Failed to create cascade ReserveLedger: {e}")
                    else:
                        # Not first/second: distribute via pools (with slot N active check)
                        self._distribute_with_slot_check(user_id, slot_no, slot_cost)
                else:
                    # No Nth upline: send to mother wallet
                    self._send_to_mother_account(slot_cost, slot_no)
                    print(f"[MANUAL_UPGRADE] ✅ Routed slot {slot_no} cost to mother wallet (no Nth upline)")
            
        except Exception as e:
            print(f"[MANUAL_UPGRADE] Error routing cost: {e}")
            import traceback
            traceback.print_exc()
    
    def _distribute_with_slot_check(self, user_id: str, slot_no: int, amount: Decimal) -> None:
        """
        Distribute funds via pools, but check if user has slot N active
        If not active, send level distribution portion (60%) to mother wallet
        Only level distribution goes to mother, other pools (40%) distribute normally
        """
        try:
            from ..fund_distribution.service import FundDistributionService
            from ..user.model import User
            from ..slot.model import SlotActivation
            from ..income.model import IncomeEvent
            from ..wallet.service import WalletService
            
            user_oid = ObjectId(user_id)
            
            # Check if user has slot N active
            user_slot_n = SlotActivation.objects(
                user_id=user_oid,
                program='binary',
                slot_no=slot_no,
                status='completed'
            ).first()
            
            # Get level distribution percentage (60% of total)
            level_distribution_pct = Decimal('60.0')  # 60% for level distribution
            level_distribution_amount = amount * level_distribution_pct / Decimal('100.0')
            other_distribution_amount = amount - level_distribution_amount  # 40%
            
            if not user_slot_n:
                # User doesn't have slot N: send level distribution (60%) to mother wallet
                print(f"[MANUAL_UPGRADE] User {user_id} doesn't have slot {slot_no}, sending level distribution ({level_distribution_amount} BNB) to mother wallet")
                self._send_to_mother_account(
                    level_distribution_amount,
                    slot_no,
                    missed_user_id=user_oid,
                    from_user_id=user_id,
                    reason=f"Level distribution fallback for slot {slot_no}"
                )
                
                # Distribute remaining funds (40%: spark_bonus, royal_captain, etc.) normally
                if other_distribution_amount > 0:
                    # Manually distribute the 40% to non-level pools
                    self._distribute_non_level_funds(user_id, slot_no, other_distribution_amount)
                    print(f"[MANUAL_UPGRADE] ✅ Distributed non-level funds ({other_distribution_amount} BNB), level portion sent to mother")
            else:
                # User has slot N: distribute normally (100%)
                fund = FundDistributionService()
                ref = User.objects(id=user_oid).only('refered_by').first()
                referrer_id = str(ref.refered_by) if ref and ref.refered_by else None
                
                fund.distribute_binary_funds(
                    user_id=user_id,
                    amount=amount,
                    slot_no=slot_no,
                    referrer_id=referrer_id,
                    tx_hash=f"manual_dist_slot{slot_no}_{user_id}_{int(datetime.utcnow().timestamp())}",
                    currency='BNB'
                )
                print(f"[MANUAL_UPGRADE] ✅ Distributed via pools normally (user has slot {slot_no})")
            
        except Exception as e:
            print(f"[MANUAL_UPGRADE] Error in distribution with slot check: {e}")
            import traceback
            traceback.print_exc()
    
    def _distribute_non_level_funds(self, user_id: str, slot_no: int, amount: Decimal) -> None:
        """
        Distribute non-level funds (40%): spark_bonus, royal_captain, president_reward,
        leadership_stipend, jackpot, partner_incentive, shareholders
        """
        try:
            from ..income.model import IncomeEvent
            from ..fund_distribution.service import FundDistributionService
            
            # These percentages are out of 100%, but we're distributing only 40% total
            # So we need to scale them proportionally
            non_level_percentages = {
                "spark_bonus": Decimal('8.0'),  # 8% of original 100% = 8% of 100%
                "royal_captain": Decimal('4.0'),
                "president_reward": Decimal('3.0'),
                "leadership_stipend": Decimal('5.0'),
                "jackpot": Decimal('5.0'),
                "partner_incentive": Decimal('10.0'),
                "shareholders": Decimal('5.0')
            }
            
            # Total non-level percentage = 40% of original
            # When distributing 40% amount, we maintain same percentages
            total_non_level_pct = sum(non_level_percentages.values())  # Should be 40%
            
            for income_type, pct in non_level_percentages.items():
                # Calculate amount for this pool (maintain same percentage)
                dist_amount = amount * (pct / total_non_level_pct)
                
                if dist_amount > 0:
                    IncomeEvent(
                        user_id=ObjectId(user_id),
                        program='binary',
                        slot_no=slot_no,
                        income_type=income_type,
                        amount=dist_amount,
                        currency='BNB',
                        source='manual_upgrade_distribution',
                        created_at=datetime.utcnow()
                    ).save()
                    
            print(f"[MANUAL_UPGRADE] ✅ Distributed non-level funds: {amount} BNB across {len(non_level_percentages)} pools")
            
        except Exception as e:
            print(f"[MANUAL_UPGRADE] Error distributing non-level funds: {e}")
            import traceback
            traceback.print_exc()
    
    def _send_to_mother_account(
        self,
        amount: Decimal,
        slot_no: int,
        missed_user_id: ObjectId | str | None = None,
        from_user_id: ObjectId | str | None = None,
        reason: str | None = None
    ) -> Dict[str, Any]:
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
            
            # Record missed profit entry for audit if we know who missed the payout
            if missed_user_id and from_user_id:
                try:
                    from ..slot.model import SlotActivation
                    from ..missed_profit.model import MissedProfit, MissedProfitReason
                    missed_user_oid = ObjectId(missed_user_id) if not isinstance(missed_user_id, ObjectId) else missed_user_id
                    from_user_oid = ObjectId(from_user_id) if not isinstance(from_user_id, ObjectId) else from_user_id
                    # Determine current active slot level for the missed user
                    latest_slot = SlotActivation.objects(
                        user_id=missed_user_oid,
                        program='binary',
                        status='completed'
                    ).order_by('-slot_no').first()
                    user_level = latest_slot.slot_no if latest_slot else 0
                    description = reason or f"Slot {slot_no} commission routed to mother account"
                    missed_profit = MissedProfit(
                        user_id=missed_user_oid,
                        upline_user_id=from_user_oid,
                        missed_profit_type='commission',
                        missed_profit_amount=float(amount),
                        currency='BNB',
                        primary_reason='level_advancement',
                        reason_description=description,
                        user_level=user_level,
                        upgrade_slot_level=slot_no,
                        program_type='binary'
                    )
                    missed_profit.reasons.append(MissedProfitReason(
                        reason_type='level_advancement',
                        reason_description=description,
                        user_level=user_level,
                        upgrade_slot_level=slot_no,
                        commission_amount=float(amount),
                        currency='BNB'
                    ))
                    missed_profit.save()
                except Exception as e:
                    print(f"[MISS_PROFIT] ⚠️ Failed to record missed profit for slot {slot_no}: {e}")
            
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

    def check_cascade_auto_upgrade_up_to_17_levels(self, new_user_id: str) -> Dict[str, Any]:
        """
        Check cascade auto-upgrade for all slots up to 17 levels in the upline.
        For each level N (1-17), if that level has N slots activated, check level N+1.
        Also check auto-upgrade for each slot in each upline.
        
        Args:
            new_user_id: The newly created user ID
            
        Returns:
            Dict with results of the cascade check
        """
        try:
            from ..tree.model import TreePlacement
            from ..slot.model import SlotActivation
            
            print(f"[CASCADE_CHECK] Starting cascade auto-upgrade check for user {new_user_id} up to 17 levels")
            
            # Get the newly created user's placement to start traversing upline
            user_placement = TreePlacement.objects(
                user_id=ObjectId(new_user_id),
                program='binary',
                slot_no=1,
                is_active=True
            ).first()
            
            if not user_placement:
                print(f"[CASCADE_CHECK] No placement found for user {new_user_id}")
                return {"success": False, "error": "No placement found for new user"}
            
            # Helper function to count activated binary slots for a user
            def count_activated_slots(user_id: ObjectId) -> int:
                try:
                    return SlotActivation.objects(
                        user_id=user_id,
                        program='binary',
                        status='completed'
                    ).count()
                except Exception:
                    return 0
            
            # Helper function to get Nth upline
            def get_upline_at_level(start_user_id: ObjectId, level: int) -> Optional[ObjectId]:
                try:
                    current_placement = TreePlacement.objects(
                        user_id=start_user_id,
                        program='binary',
                        slot_no=1,
                        is_active=True
                    ).first()
                    
                    if not current_placement:
                        return None
                    
                    steps = 0
                    current_upline = getattr(current_placement, 'upline_id', None) or getattr(current_placement, 'parent_id', None)
                    
                    while current_upline and steps < level:
                        steps += 1
                        if steps == level:
                            return current_upline
                        
                        # Move to next upline
                        next_placement = TreePlacement.objects(
                            user_id=current_upline,
                            program='binary',
                            slot_no=1,
                            is_active=True
                        ).first()
                        
                        if not next_placement:
                            break
                            
                        current_upline = getattr(next_placement, 'upline_id', None) or getattr(next_placement, 'parent_id', None)
                    
                    return None
                except Exception as e:
                    print(f"[CASCADE_CHECK] Error getting upline at level {level}: {e}")
                    return None
            
            results = {
                "levels_checked": [],
                "auto_upgrades_triggered": [],
                "total_levels": 0,
                "total_checks": 0
            }
            
            # Traverse up to 17 levels
            # Logic: Check all levels up to 17, and for each level check all slots
            # If level N has N slots activated, continue checking level N+1
            max_level = 17
            checked_levels = set()  # Track which levels we've checked to avoid duplicates
            
            for level in range(1, max_level + 1):
                try:
                    # Get upline at this level
                    upline_id = get_upline_at_level(ObjectId(new_user_id), level)
                    
                    if not upline_id:
                        print(f"[CASCADE_CHECK] No upline found at level {level}")
                        break
                    
                    # Skip if we've already checked this upline at a different level
                    if str(upline_id) in checked_levels:
                        continue
                    
                    checked_levels.add(str(upline_id))
                    
                    # Count activated slots for this upline
                    activated_slots_count = count_activated_slots(upline_id)
                    
                    print(f"[CASCADE_CHECK] Level {level} - Upline {upline_id} has {activated_slots_count} slots activated")
                    
                    level_result = {
                        "level": level,
                        "upline_id": str(upline_id),
                        "activated_slots": activated_slots_count,
                        "checks_performed": []
                    }
                    
                    # Check auto-upgrade for valid binary slots only (1-16)
                    # This avoids zero-cost or undefined slots from triggering
                    slots_to_check = list(range(1, 17))  # Slots 1 to 16
                    
                    # Check auto-upgrade for each slot
                    for slot_no in slots_to_check:
                            
                        try:
                            auto_upgrade_result = self._check_binary_auto_upgrade_from_reserve(upline_id, slot_no)
                            
                            check_info = {
                                "slot_no": slot_no,
                                "auto_upgrade_triggered": auto_upgrade_result.get("auto_upgrade_triggered", False),
                                "message": auto_upgrade_result.get("message", "")
                            }
                            
                            level_result["checks_performed"].append(check_info)
                            results["total_checks"] += 1
                            
                            if auto_upgrade_result.get("auto_upgrade_triggered"):
                                results["auto_upgrades_triggered"].append({
                                    "level": level,
                                    "upline_id": str(upline_id),
                                    "slot_no": slot_no
                                })
                                print(f"[CASCADE_CHECK] ✅ Auto-upgrade triggered for upline {upline_id} at level {level}, slot {slot_no}")
                            
                        except Exception as e:
                            print(f"[CASCADE_CHECK] Error checking slot {slot_no} for upline {upline_id}: {e}")
                    
                    results["levels_checked"].append(level_result)
                    results["total_levels"] += 1
                    
                    # Log if this level has N slots activated (where N = level number)
                    # Example: If level 3 has 3 slots, continue to check level 4. If level 4 has 4 slots, continue to level 5.
                    if activated_slots_count >= level:
                        print(f"[CASCADE_CHECK] Level {level} has {activated_slots_count} slots (>= {level}), continuing to check level {level + 1}")
                    else:
                        print(f"[CASCADE_CHECK] Level {level} has {activated_slots_count} slots (< {level}), but will continue checking all levels up to 17")
                    
                except Exception as e:
                    print(f"[CASCADE_CHECK] Error checking level {level}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"[CASCADE_CHECK] Completed cascade check: {results['total_levels']} levels, {results['total_checks']} slot checks, {len(results['auto_upgrades_triggered'])} auto-upgrades triggered")
            
            return {
                "success": True,
                **results
            }
            
        except Exception as e:
            print(f"[CASCADE_CHECK] Error in check_cascade_auto_upgrade_up_to_17_levels: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}