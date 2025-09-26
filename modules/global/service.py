from typing import Dict, Any
from bson import ObjectId
from datetime import datetime
from decimal import Decimal
from modules.auto_upgrade.model import GlobalPhaseProgression
from modules.slot.model import SlotCatalog, SlotActivation
from modules.user.model import User, EarningHistory
from modules.commission.service import CommissionService
from modules.spark.service import SparkService
from modules.royal_captain.model import RoyalCaptainFund
from modules.president_reward.model import PresidentRewardFund
from modules.royal_captain.service import RoyalCaptainService
from modules.president_reward.service import PresidentRewardService
from modules.income.bonus_fund import BonusFund
from modules.tree.model import TreePlacement
from modules.wallet.company_service import CompanyWalletService
from utils import ensure_currency_for_program


class GlobalService:
    """Global Program Business Logic Service (Phase-1/Phase-2 progression)."""

    def __init__(self) -> None:
        self.commission_service = CommissionService()
        self.spark_service = SparkService()
        self.company_wallet = CompanyWalletService()

    def _count_phase_children(self, parent_id: ObjectId, phase: str) -> int:
        return TreePlacement.objects(parent_id=parent_id, program='global', phase=phase, is_active=True).count()

    def _find_phase1_parent_bfs(self) -> ObjectId | None:
        """
        Find the earliest Global participant whose PHASE-1 has < 4 children using BFS algorithm
        """
        candidates = GlobalPhaseProgression.objects(is_active=True).order_by('created_at')
        for status in candidates:
            # Ensure candidate is in PHASE-1 or at least accepts Phase-1 seats initially
            if status.current_phase not in ['PHASE-1', None]:
                continue
            pid = status.user_id
            if self._count_phase_children(pid, 'PHASE-1') < 4:
                return pid
        return None

    def _find_phase1_parent_escalation(self, user_id: str) -> ObjectId | None:
        """
        Escalate up to 60 levels to find eligible upline with available Phase-1 positions
        """
        try:
            user_oid = ObjectId(user_id)
            current_user = user_oid
            escalation_level = 0
            max_escalation = 60
            
            while escalation_level < max_escalation:
                # Find direct upline
                upline_placement = TreePlacement.objects(user_id=current_user, program='global').first()
                if not upline_placement or not upline_placement.parent_id:
                    break
                
                current_user = upline_placement.parent_id
                escalation_level += 1
                
                # Check if this upline has available Phase-1 positions
                if self._count_phase_children(current_user, 'PHASE-1') < 4:
                    return current_user
            
            return None
        except Exception as e:
            print(f"Escalation failed for user {user_id}: {str(e)}")
            return None

    def _get_mother_id(self) -> ObjectId | None:
        """
        Get Mother ID as fallback when no eligible upline found
        """
        try:
            # Try to find a system user or admin user as Mother ID
            from modules.user.model import User
            mother_user = User.objects(role='admin').first() or User.objects().first()
            if mother_user:
                return mother_user.id
            return None
        except Exception as e:
            print(f"Failed to get Mother ID: {str(e)}")
            return None

    def _find_phase2_parent_bfs(self) -> ObjectId | None:
        # Find the earliest participant currently in PHASE-2 whose PHASE-2 has < 8 children
        candidates = GlobalPhaseProgression.objects(current_phase='PHASE-2', is_active=True).order_by('created_at')
        for status in candidates:
            pid = status.user_id
            if self._count_phase_children(pid, 'PHASE-2') < 8:
                return pid
        return None

    def _place_in_phase1(self, user_id: str) -> Dict[str, Any]:
        """
        1.1.4 Phase-1 BFS Placement - Section 1.1.4 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        - Place user in Phase-1 tree using BFS algorithm
        - Find eligible upline with available Phase-1 positions
        - Escalate up to 60 levels if needed
        - Fallback to Mother ID if no eligible upline found
        """
        try:
            user_oid = ObjectId(user_id)
            
            # Find eligible upline with available Phase-1 positions using BFS
            parent_id = self._find_phase1_parent_bfs()
            
            # If no eligible upline found, escalate up to 60 levels
            if not parent_id:
                parent_id = self._find_phase1_parent_escalation(user_id)
            
            # Fallback to Mother ID if no eligible upline found
            if not parent_id:
                parent_id = self._get_mother_id()
                print(f"No eligible upline found for user {user_id}, using Mother ID: {parent_id}")
            
            # Determine position index for UI (1..4)
            position_label = 'root'
            level = 1
            if parent_id:
                count = self._count_phase_children(parent_id, 'PHASE-1')
                idx = (count + 1)
                position_label = f'position_{idx}'  # position_1..position_4
                # infer parent level
                parent_node = TreePlacement.objects(user_id=parent_id, program='global', phase='PHASE-1').first()
                level = (parent_node.level + 1) if parent_node else 2
            
            # Create placement record
            placement = TreePlacement(
                user_id=user_oid,
                program='global',
                parent_id=parent_id,
                position=position_label,
                level=level,
                slot_no=1,
                phase='PHASE-1',
                phase_position=int(position_label.split('_')[1]) if position_label != 'root' else 0,
                is_active=True,
                is_activated=True,
                activation_date=datetime.utcnow()
            )
            placement.save()
            
            # Update parent's counters and readiness
            if parent_id:
                parent_status = GlobalPhaseProgression.objects(user_id=parent_id).first()
                if parent_status:
                    parent_status.phase_1_members_current = int(parent_status.phase_1_members_current or 0) + 1
                    if parent_status.phase_1_members_current >= (parent_status.phase_1_members_required or 4):
                        parent_status.is_phase_complete = True
                        parent_status.next_phase_ready = True
                        parent_status.phase_completed_at = datetime.utcnow()
                        print(f"Parent {parent_id} Phase-1 completed with {parent_status.phase_1_members_current} members")
                    parent_status.updated_at = datetime.utcnow()
                    parent_status.save()
            
            return {"success": True, "parent_id": str(parent_id) if parent_id else None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _place_in_phase2(self, user_id: str) -> Dict[str, Any]:
        """Place user into PHASE-2 tree under earliest PHASE-2 parent with <8 seats.
        If none exists yet (first entrant into PHASE-2), place as root of PHASE-2.
        """
        try:
            user_oid = ObjectId(user_id)
            parent_id = self._find_phase2_parent_bfs()
            position_label = 'root'
            level = 1
            if parent_id:
                count = self._count_phase_children(parent_id, 'PHASE-2')
                idx = (count + 1)
                position_label = f'position_{idx}'  # 1..8
                parent_node = TreePlacement.objects(user_id=parent_id, program='global', phase='PHASE-2').first()
                level = (parent_node.level + 1) if parent_node else 2
            TreePlacement(
                user_id=user_oid,
                program='global',
                parent_id=parent_id,
                position=position_label,
                level=level,
                slot_no=1,
                phase='PHASE-2',
                phase_position=int(position_label.split('_')[1]) if position_label != 'root' else 0,
                is_active=True,
                is_activated=True,
                activation_date=datetime.utcnow()
            ).save()
            if parent_id:
                parent_status = GlobalPhaseProgression.objects(user_id=parent_id).first()
                if parent_status:
                    parent_status.phase_2_members_current = int(parent_status.phase_2_members_current or 0) + 1
                    if parent_status.phase_2_members_current >= (parent_status.phase_2_members_required or 8):
                        parent_status.is_phase_complete = True
                        parent_status.next_phase_ready = True
                        parent_status.phase_completed_at = datetime.utcnow()
                    parent_status.last_updated = datetime.utcnow()
                    parent_status.save()
            return {"success": True, "parent_id": str(parent_id) if parent_id else None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def join_global(self, user_id: str, tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        try:
            # 1.1.1 User Validation - Section 1.1.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # 1. Validate user exists
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # 2. Check if user already joined Global program
            if getattr(user, 'global_joined', False):
                return {"success": False, "error": "User has already joined Global program"}
            
            # Check if user has existing GlobalPhaseProgression record
            existing_progression = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if existing_progression:
                return {"success": False, "error": "User already has Global program progression record"}
            
            # 3. Verify amount matches Phase-1 Slot-1 price ($33)
            catalog = SlotCatalog.objects(program='global', slot_no=1, is_active=True).first()
            if not catalog:
                return {"success": False, "error": "Global slot catalog missing"}
            expected_amount = catalog.price or Decimal('0')
            if amount != expected_amount:
                return {"success": False, "error": f"Join amount must be {expected_amount} (Phase-1 Slot-1 price)"}

            currency = ensure_currency_for_program('global', 'USD')
            
            # Generate unique tx_hash to avoid duplicate key errors
            import random, string
            unique_suffix = datetime.utcnow().strftime('%Y%m%d%H%M%S%f') + '_' + ''.join(random.choices(string.ascii_lowercase+string.digits, k=6))
            unique_tx_hash = f"{tx_hash}_{unique_suffix}"

            # 1.1.2 Slot Activation - Section 1.1.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Create SlotActivation record for Global Slot-1
            current_time = datetime.utcnow()
            activation = SlotActivation(
                user_id=ObjectId(user.id),
                program='global',
                slot_no=1,
                slot_name=catalog.name,
                activation_type='initial',  # Set activation_type: 'initial'
                upgrade_source='wallet',
                amount_paid=expected_amount,
                currency=currency,  # Set currency: 'USD'
                tx_hash=unique_tx_hash,
                blockchain_network='BSC',  # Default blockchain network
                commission_paid=Decimal('0'),  # No commission for initial join
                commission_percentage=0.0,  # No commission percentage for initial join
                is_auto_upgrade=False,
                partners_contributed=[],
                earnings_used=Decimal('0'),
                status='completed',  # Set status: 'completed'
                activated_at=current_time,
                completed_at=current_time,
                created_at=current_time,
                metadata={
                    'join_type': 'initial',
                    'phase': 'PHASE-1',
                    'slot_level': catalog.level,
                    'validation_passed': True
                }
            )
            activation.save()

            # 1.1.3 Global Phase Progression Setup - Section 1.1.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Create GlobalPhaseProgression record if not exists
            progression = GlobalPhaseProgression.objects(user_id=ObjectId(user.id)).first()
            if not progression:
                progression = GlobalPhaseProgression(
                    user_id=ObjectId(user.id),
                    current_phase='PHASE-1',  # Set current_phase: 'PHASE-1'
                    current_slot_no=1,  # Set current_slot_no: 1
                    phase_position=1,  # Set phase_position: 1
                    phase_1_members_required=4,  # Set phase_1_members_required: 4
                    phase_1_members_current=0,  # Set phase_1_members_current: 0
                    phase_2_members_required=8,  # Set phase_2_members_required: 8
                    phase_2_members_current=0,  # Set phase_2_members_current: 0
                    global_team_size=0,
                    global_team_members=[],
                    is_phase_complete=False,
                    phase_completed_at=None,
                    next_phase_ready=False,
                    total_re_entries=0,
                    last_re_entry_at=None,
                    re_entry_slot=1,
                    auto_progression_enabled=True,  # Set auto_progression_enabled: true
                    progression_triggered=False,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                progression.save()
                
                # Log phase progression setup
                print(f"Global Phase Progression setup for user {user.id}: PHASE-1, Slot-1")

            # 1.1.4 Phase-1 BFS Placement - Section 1.1.4 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Place user in Phase-1 tree using BFS algorithm
            placement_result = self._place_in_phase1(user_id)
            if not placement_result.get("success"):
                return {"success": False, "error": f"Phase-1 placement failed: {placement_result.get('error')}"}
            
            # Log placement result
            parent_id = placement_result.get("parent_id")
            if parent_id:
                print(f"User {user_id} placed in Phase-1 under parent {parent_id}")
            else:
                print(f"User {user_id} placed as root in Phase-1")

            # 1.1.5 Commission Calculations - Section 1.1.5 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Joining Commission (10%): Calculate and distribute to upline
            try:
                joining_commission_result = self.commission_service.calculate_joining_commission(
                    from_user_id=str(user.id),
                    program='global',
                    amount=expected_amount,
                    currency=currency
                )
                print(f"Joining commission calculated for user {user.id}: {joining_commission_result}")
            except Exception as e:
                print(f"Joining commission failed for user {user.id}: {str(e)}")

            # Partner Incentive (10%): Calculate and distribute to direct upline
            try:
                partner_incentive_result = self.commission_service.calculate_partner_incentive(
                    from_user_id=str(user.id),
                    program='global',
                    amount=expected_amount,
                    currency=currency
                )
                print(f"Partner incentive calculated for user {user.id}: {partner_incentive_result}")
            except Exception as e:
                print(f"Partner incentive failed for user {user.id}: {str(e)}")

            # 1.1.6 Global Distribution (100% breakdown) - Section 1.1.6 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Global distribution (100% breakdown)
            distribution_result = self.process_distribution(user_id=str(user.id), amount=expected_amount, currency=currency)
            if not distribution_result.get("success"):
                print(f"Global distribution failed for user {user.id}: {distribution_result.get('error')}")
            else:
                print(f"Global distribution completed for user {user.id}: {distribution_result.get('distribution_breakdown')}")

            # 1.1.7 Triple Entry Eligibility Check - Section 1.1.7 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # If user has Binary + Matrix + Global: Compute triple-entry eligibles
            try:
                # Check if user has all three programs (Binary, Matrix, Global)
                has_binary = getattr(user, 'binary_joined', False)
                has_matrix = getattr(user, 'matrix_joined', False)
                has_global = getattr(user, 'global_joined', False)  # Will be True after this join
                
                print(f"Triple Entry Check for user {user.id}: Binary={has_binary}, Matrix={has_matrix}, Global={has_global}")
                
                # Since we're setting global_joined=True after this check, we need to check if user will have all three
                if has_binary and has_matrix:
                    # User will have all three programs after this Global join
                    print(f"User {user.id} eligible for Triple Entry Reward - has Binary + Matrix + Global")
                    triple_entry_result = SparkService.compute_triple_entry_eligibles(datetime.utcnow())
                    print(f"Triple Entry eligibility computed: {triple_entry_result}")
                else:
                    print(f"User {user.id} not yet eligible for Triple Entry Reward - missing programs")
            except Exception as e:
                print(f"Triple Entry eligibility check failed for user {user.id}: {str(e)}")

            # Update user's global_joined flag
            user.global_joined = True
            user.save()

            # 1.1.8 Earning History Record - Section 1.1.8 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Create EarningHistory record
            try:
                # Convert currency to USDT (since we only support USDT and BNB)
                earning_currency = 'USDT' if currency == 'USD' else currency
                
                earning_history = EarningHistory(
                    user_id=ObjectId(user.id),
                    earning_type='global_slot',  # Set earning_type: 'global_slot'
                    program='global',  # Set program: 'global'
                    amount=float(expected_amount),  # Set amount: $33
                    currency=earning_currency,  # Set currency: 'USDT' (converted from USD)
                    slot_name=catalog.name,  # Set slot_name: 'FOUNDATION'
                    slot_level=catalog.level,
                    description='Joined Global program, activated Phase-1 Slot-1'  # Set description
                )
                earning_history.save()
                
                print(f"Earning history record created for user {user.id}: {earning_currency} {expected_amount} - {catalog.name}")
            except Exception as e:
                print(f"Earning history record creation failed for user {user.id}: {str(e)}")

            return {"success": True, "slot_no": 1, "amount": float(expected_amount)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def upgrade_global_slot(self, user_id: str, to_slot_no: int, tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        """
        2.1 Slot Upgrade Process - Section 2.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        **Trigger**: User upgrades to next Global slot (2-16)
        **Endpoint**: `POST /global/upgrade`
        """
        try:
            # 2.1.1 Upgrade Validation - Section 2.1.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # 1. Validate user exists and has Global program access
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                print(f"Upgrade validation failed: User {user_id} not found")
                return {"success": False, "error": "User not found"}
            
            if not getattr(user, 'global_joined', False):
                print(f"Upgrade validation failed: User {user_id} has not joined Global program")
                return {"success": False, "error": "User has not joined Global program"}

            # 2. Check if target slot is valid (2-16)
            if to_slot_no < 2 or to_slot_no > 16:
                print(f"Upgrade validation failed: Invalid target slot {to_slot_no} (must be 2-16)")
                return {"success": False, "error": "Target slot must be between 2 and 16"}

            # 3. Verify amount matches target slot price from catalog
            catalog = SlotCatalog.objects(program='global', slot_no=to_slot_no, is_active=True).first()
            if not catalog:
                print(f"Upgrade validation failed: Global slot catalog missing for slot {to_slot_no}")
                return {"success": False, "error": "Global slot catalog missing"}
            expected_amount = catalog.price or Decimal('0')
            if amount != expected_amount:
                print(f"Upgrade validation failed: Amount mismatch - provided: {amount}, expected: {expected_amount}")
                return {"success": False, "error": f"Upgrade amount must be {expected_amount}"}

            # 4. Check if user already has this slot activated
            existing_activation = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program='global',
                slot_no=to_slot_no,
                status='completed'
            ).first()
            if existing_activation:
                print(f"Upgrade validation failed: User {user_id} already has slot {to_slot_no} activated")
                return {"success": False, "error": f"User already has slot {to_slot_no} activated"}

            # Additional validation: Check if user has previous slots activated
            previous_slots = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program='global',
                slot_no__lt=to_slot_no,
                status='completed'
            ).count()
            
            if previous_slots < (to_slot_no - 1):
                print(f"Upgrade validation failed: User {user_id} missing previous slots (has {previous_slots}, needs {to_slot_no - 1})")
                return {"success": False, "error": f"User must activate previous slots before upgrading to slot {to_slot_no}"}

            print(f"Upgrade validation passed for user {user_id}: slot {to_slot_no}, amount {expected_amount}")

            currency = ensure_currency_for_program('global', 'USD')
            
            # Generate unique tx_hash to avoid duplicate key errors
            import random, string
            unique_suffix = datetime.utcnow().strftime('%Y%m%d%H%M%S%f') + '_' + ''.join(random.choices(string.ascii_lowercase+string.digits, k=6))
            unique_tx_hash = f"{tx_hash}_{unique_suffix}"

            # 2.1.2 Slot Activation Record - Section 2.1.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Create SlotActivation record for target slot
            try:
                current_time = datetime.utcnow()
                activation = SlotActivation(
                    user_id=ObjectId(user.id),
                    program='global',
                    slot_no=to_slot_no,
                    slot_name=catalog.name,
                    activation_type='upgrade',  # Set activation_type: 'upgrade'
                    upgrade_source='wallet',  # Set upgrade_source: 'wallet' or 'auto'
                    amount_paid=expected_amount,
                    currency=currency,  # Set currency: 'USD'
                    tx_hash=unique_tx_hash,
                    blockchain_network='BSC',
                    commission_paid=Decimal('0'),
                    commission_percentage=0.0,
                    is_auto_upgrade=False,
                    partners_contributed=[],
                    earnings_used=Decimal('0'),
                    status='completed',  # Set status: 'completed'
                    activated_at=current_time,
                    completed_at=current_time,
                    created_at=current_time,
                    metadata={
                        'upgrade_type': 'manual',
                        'slot_level': catalog.level,
                        'validation_passed': True,
                        'upgrade_sequence': to_slot_no,
                        'previous_slots_verified': True
                    }
                )
                activation.save()
                
                print(f"Slot activation record created for user {user.id}: slot {to_slot_no} ({catalog.name}) - {currency} {expected_amount}")
            except Exception as e:
                print(f"Slot activation record creation failed for user {user.id}, slot {to_slot_no}: {str(e)}")
                return {"success": False, "error": f"Failed to create slot activation record: {str(e)}"}

            # 2.1.3 Commission Calculations - Section 2.1.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Partner Incentive (10%): Calculate and distribute to direct upline
            try:
                partner_incentive_result = self.commission_service.calculate_partner_incentive(
                    from_user_id=str(user.id),
                    program='global',
                    amount=expected_amount,
                    currency=currency
                )
                print(f"Partner incentive calculated for slot upgrade {to_slot_no}: {partner_incentive_result}")
            except Exception as e:
                print(f"Partner incentive failed for slot upgrade {to_slot_no}: {str(e)}")

            # Upgrade Commission: Calculate based on slot value
            try:
                upgrade_commission_result = self.commission_service.calculate_upgrade_commission(
                    from_user_id=str(user.id),
                    program='global',
                    slot_no=to_slot_no,
                    amount=expected_amount,
                    currency=currency
                )
                print(f"Upgrade commission calculated for slot {to_slot_no}: {upgrade_commission_result}")
            except Exception as e:
                print(f"Upgrade commission failed for slot {to_slot_no}: {str(e)}")

            # Additional commission calculations for Global program
            try:
                # Level Commission: Calculate based on slot level
                level_commission_result = self.commission_service.calculate_level_commission(
                    from_user_id=str(user.id),
                    program='global',
                    slot_no=to_slot_no,
                    amount=expected_amount,
                    currency=currency
                )
                print(f"Level commission calculated for slot {to_slot_no}: {level_commission_result}")
            except Exception as e:
                print(f"Level commission failed for slot {to_slot_no}: {str(e)}")

            # Commission summary
            commission_summary = {
                "partner_incentive": partner_incentive_result if 'partner_incentive_result' in locals() else None,
                "upgrade_commission": upgrade_commission_result if 'upgrade_commission_result' in locals() else None,
                "level_commission": level_commission_result if 'level_commission_result' in locals() else None,
                "total_commission_amount": float(expected_amount * Decimal('0.10')),  # 10% partner incentive
                "currency": currency
            }
            print(f"Commission calculations completed for slot upgrade {to_slot_no}: {commission_summary}")

            # 2.1.4 Global Distribution (100% breakdown) - Section 2.1.4 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Global distribution (100% breakdown)
            try:
                distribution_result = self.process_distribution(user_id=str(user.id), amount=expected_amount, currency=currency)
                if not distribution_result.get("success"):
                    print(f"Global distribution failed for slot upgrade {to_slot_no}: {distribution_result.get('error')}")
                else:
                    print(f"Global distribution completed for slot upgrade {to_slot_no}: {distribution_result.get('distribution_breakdown')}")
                    
                    # Log detailed distribution breakdown
                    breakdown = distribution_result.get('distribution_breakdown', {})
                    print(f"Distribution breakdown for slot {to_slot_no}:")
                    print(f"  - Level Reserved (30%): {breakdown.get('level_reserved', 0)}")
                    print(f"  - Partner Incentive (10%): {breakdown.get('partner_incentive', 0)}")
                    print(f"  - Profit (30%): {breakdown.get('profit', 0)}")
                    print(f"  - Royal Captain Bonus (10%): {breakdown.get('royal_captain', 0)}")
                    print(f"  - President Reward (10%): {breakdown.get('president_reward', 0)}")
                    print(f"  - Triple Entry Reward (5%): {breakdown.get('triple_entry', 0)}")
                    print(f"  - Shareholders (5%): {breakdown.get('shareholders', 0)}")
                    
            except Exception as e:
                print(f"Global distribution process failed for slot upgrade {to_slot_no}: {str(e)}")
                # Continue with the process even if distribution fails

            # 2.1.5 Earning History Record - Section 2.1.5 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Create EarningHistory record for upgrade
            try:
                # Convert currency to USDT (since we only support USDT and BNB)
                earning_currency = 'USDT' if currency == 'USD' else currency
                
                earning_history = EarningHistory(
                    user_id=ObjectId(user.id),
                    earning_type='global_slot',  # Set earning_type: 'global_slot'
                    program='global',  # Set program: 'global'
                    amount=float(expected_amount),  # Set amount: slot_value
                    currency=earning_currency,  # Set currency: 'USDT' (converted from USD)
                    slot_name=catalog.name,  # Set slot_name: target_slot_name
                    slot_level=catalog.level,
                    description=f'Upgraded Global slot {to_slot_no} ({catalog.name})'  # Set description: 'Upgraded Global slot'
                )
                earning_history.save()
                
                print(f"Earning history record created for slot upgrade {to_slot_no}: {earning_currency} {expected_amount} - {catalog.name}")
                print(f"Earning history details: user_id={user.id}, earning_type=global_slot, program=global, amount={expected_amount}, currency={earning_currency}, slot_name={catalog.name}, slot_level={catalog.level}")
                
            except Exception as e:
                print(f"Earning history record creation failed for slot upgrade {to_slot_no}: {str(e)}")
                # Continue with the process even if earning history fails

            return {"success": True, "slot_no": to_slot_no, "amount": float(expected_amount)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_status(self, user_id: str) -> Dict[str, Any]:
        try:
            status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not status:
                return {"success": False, "error": "Global status not found"}
            return {
                "success": True,
                "status": {
                    "current_phase": status.current_phase,
                    "current_slot_no": status.current_slot_no,
                    "phase_position": status.phase_position,
                    "phase_1_members_current": status.phase_1_members_current,
                    "phase_1_members_required": status.phase_1_members_required,
                    "phase_2_members_current": status.phase_2_members_current,
                    "phase_2_members_required": status.phase_2_members_required,
                    "next_phase_ready": status.next_phase_ready,
                    "is_phase_complete": status.is_phase_complete,
                    "total_re_entries": status.total_re_entries,
                    "global_team_size": status.global_team_size
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_team_member(self, user_id: str, member_id: str) -> Dict[str, Any]:
        """Add a global team member and update phase counters; mark readiness when thresholds hit."""
        try:
            status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not status:
                return {"success": False, "error": "Global status not found"}

            # Update aggregates
            members = status.global_team_members or []
            oid = ObjectId(member_id)
            if oid not in members:
                members.append(oid)
                status.global_team_members = members
                status.global_team_size = (status.global_team_size or 0) + 1

            if status.current_phase == 'PHASE-1':
                status.phase_1_members_current = (status.phase_1_members_current or 0) + 1
                if status.phase_1_members_current >= (status.phase_1_members_required or 4):
                    status.is_phase_complete = True
                    status.next_phase_ready = True
                    status.phase_completed_at = datetime.utcnow()
            else:
                status.phase_2_members_current = (status.phase_2_members_current or 0) + 1
                if status.phase_2_members_current >= (status.phase_2_members_required or 8):
                    status.is_phase_complete = True
                    status.next_phase_ready = True
                    status.phase_completed_at = datetime.utcnow()

            status.updated_at = datetime.utcnow()
            status.save()

            return {"success": True, "status": self.get_status(user_id).get("status")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_team(self, user_id: str) -> Dict[str, Any]:
        try:
            status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not status:
                return {"success": False, "error": "Global status not found"}
            return {
                "success": True,
                "team": {
                    "size": status.global_team_size or 0,
                    "members": [str(mid) for mid in (status.global_team_members or [])]
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_progression(self, user_id: str) -> Dict[str, Any]:
        """Progress Phase-1 (4) -> Phase-2 (8) -> re-entry as per spec when ready."""
        try:
            status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not status:
                return {"success": False, "error": "Global status not found"}

            if status.current_phase == 'PHASE-1':
                if status.phase_1_members_current < status.phase_1_members_required:
                    return {"success": False, "error": "Phase-1 not complete"}
                status.current_phase = 'PHASE-2'
                status.current_slot_no = 1
                status.phase_position = 1
                status.is_phase_complete = False
                status.next_phase_ready = False
                status.phase_completed_at = datetime.utcnow()
                status.phase_2_members_current = 0
                status.save()
                # Place user into PHASE-2 tree
                self._place_in_phase2(user_id)
                return {"success": True, "moved_to": "PHASE-2", "slot_no": 1}
            else:
                if status.phase_2_members_current < status.phase_2_members_required:
                    return {"success": False, "error": "Phase-2 not complete"}
                status.current_phase = 'PHASE-1'
                status.current_slot_no = min((status.current_slot_no or 1) + 1, 16)
                status.phase_position = 1
                status.is_phase_complete = False
                status.next_phase_ready = False
                status.total_re_entries = (status.total_re_entries or 0) + 1
                status.last_re_entry_at = datetime.utcnow()
                status.re_entry_slot = status.current_slot_no
                status.phase_completed_at = datetime.utcnow()
                status.phase_1_members_current = 0
                status.save()
                # Place user again at PHASE-1 root queue (handled in next joins via BFS)
                return {"success": True, "reentered_phase": "PHASE-1", "slot_no": status.current_slot_no}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_current_global_slot(self, user_id: str) -> int:
        activation = (
            SlotActivation.objects(user_id=ObjectId(user_id), program='global')
            .order_by('-slot_no')
            .first()
        )
        return activation.slot_no if activation else 0

    def _attempt_reserved_auto_upgrade(self, user_id: str, currency: str) -> Dict[str, Any]:
        try:
            status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not status:
                return {"success": False, "error": "Global status not found"}

            reserved = Decimal(str(getattr(status, 'reserved_upgrade_amount', 0) or 0))
            if reserved <= 0:
                return {"success": False, "error": "No reserved funds"}

            # Must be ready to progress per Phase rules
            if not status.next_phase_ready:
                return {"success": False, "error": "Next phase not ready"}

            # Determine next slot number based on highest activated slot
            current_slot = self._get_current_global_slot(user_id)
            next_slot = min((current_slot or 1) + 1, 16)
            catalog = SlotCatalog.objects(program='global', slot_no=next_slot, is_active=True).first()
            if not catalog or not catalog.price:
                return {"success": False, "error": "Next slot catalog missing"}
            price = Decimal(str(catalog.price))

            if reserved < price:
                return {"success": False, "error": "Insufficient reserved funds"}

            # Progress phase status first (Phase-1 -> Phase-2 or Phase-2 -> Phase-1 next)
            self.process_progression(user_id)

            # Auto-upgrade using reserved funds
            tx_hash = f"GLOBAL-AUTO-UP-{user_id}-S{next_slot}-{int(datetime.utcnow().timestamp())}"
            upgrade_result = self.upgrade_global_slot(user_id=user_id, to_slot_no=next_slot, tx_hash=tx_hash, amount=price)
            if not upgrade_result.get('success'):
                return upgrade_result

            # Deduct reserved
            new_reserved = reserved - price
            setattr(status, 'reserved_upgrade_amount', float(new_reserved))
            status.save()

            return {"success": True, "next_slot": next_slot, "reserved_remaining": float(new_reserved)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_distribution(self, user_id: str, amount: Decimal, currency: str) -> Dict[str, Any]:
        """Global distribution per GLOBAL_PROGRAM_AUTO_ACTIONS.md Section 1.1.6.
        Breakdown:
        - Level (30%): Reserve for Phase-2 slot upgrade
        - Partner Incentive (10%): Direct upline commission (already handled)
        - Profit (30%): Net profit portion
        - Royal Captain Bonus (10%): Add to RC fund
        - President Reward (10%): Add to PR fund
        - Triple Entry Reward (5%): Add to TER fund (part of 25% total TER)
        - Shareholders (5%): Add to shareholders fund
        """
        try:
            total = Decimal(str(amount))
            reserved_upgrade = total * Decimal('0.30')  # Level 30%
            profit_portion = total * Decimal('0.30')    # Profit 30%
            royal_captain_portion = total * Decimal('0.10')  # RC 10%
            president_reward_portion = total * Decimal('0.10')  # PR 10%
            triple_entry_portion = total * Decimal('0.05')  # TER 5%
            shareholders_portion = total * Decimal('0.05')  # Shareholders 5%

            # Update reserved for upgrade on status
            try:
                status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
                if status:
                    current_reserved = Decimal(str(getattr(status, 'reserved_upgrade_amount', 0) or 0))
                    current_reserved += reserved_upgrade
                    setattr(status, 'reserved_upgrade_amount', float(current_reserved))
                    status.last_updated = datetime.utcnow()
                    status.save()
            except Exception:
                pass

            # Profit → BonusFund and CompanyWallet
            try:
                bf = BonusFund.objects(fund_type='net_profit', program='global').first()
                if not bf:
                    bf = BonusFund(fund_type='net_profit', program='global', status='active')
                bf.total_amount = float(getattr(bf, 'total_amount', 0.0) + float(profit_portion))
                bf.available_amount = float(getattr(bf, 'available_amount', 0.0) + float(profit_portion))
                bf.updated_at = datetime.utcnow()
                bf.save()
                # Company wallet credit
                self.company_wallet.credit(profit_portion, currency, 'global_net_profit_topup', f'GLB-NETPROFIT-{user_id}-{datetime.utcnow().timestamp()}')
            except Exception:
                pass

            # Update Royal Captain fund
            try:
                rc_fund = RoyalCaptainFund.objects(is_active=True).first()
                if not rc_fund:
                    from modules.royal_captain.model import RoyalCaptainFund as RCF
                    rc_fund = RCF()
                rc_fund.total_fund_amount += float(royal_captain_portion)
                rc_fund.available_amount += float(royal_captain_portion)
                rc_fund.fund_sources['global_contributions'] = rc_fund.fund_sources.get('global_contributions', 0.0) + float(royal_captain_portion)
                rc_fund.last_updated = datetime.utcnow()
                rc_fund.save()
            except Exception:
                pass

            # Update President Reward fund
            try:
                pr_fund = PresidentRewardFund.objects(is_active=True).first()
                if not pr_fund:
                    from modules.president_reward.model import PresidentRewardFund as PRF
                    pr_fund = PRF()
                pr_fund.total_fund_amount += float(president_reward_portion)
                pr_fund.available_amount += float(president_reward_portion)
                pr_fund.fund_sources['global_contributions'] = pr_fund.fund_sources.get('global_contributions', 0.0) + float(president_reward_portion)
                pr_fund.last_updated = datetime.utcnow()
                pr_fund.save()
            except Exception:
                pass

            # Triple Entry Reward (Spark) - Section 1.1.6
            try:
                self.spark_service.contribute_to_fund(
                    amount=float(triple_entry_portion),
                    program='global',
                    source_user_id=str(user_id),
                    source_type='global_join',
                    currency=currency
                )
            except Exception:
                pass

            # Shareholders → BonusFund and CompanyWallet
            try:
                bf_sh = BonusFund.objects(fund_type='shareholders', program='global').first()
                if not bf_sh:
                    bf_sh = BonusFund(fund_type='shareholders', program='global', status='active')
                bf_sh.total_amount = float(getattr(bf_sh, 'total_amount', 0.0) + float(shareholders_portion))
                bf_sh.available_amount = float(getattr(bf_sh, 'available_amount', 0.0) + float(shareholders_portion))
                bf_sh.updated_at = datetime.utcnow()
                bf_sh.save()
                # Company wallet credit
                self.company_wallet.credit(shareholders_portion, currency, 'global_shareholders_topup', f'GLB-SHAREHOLDERS-{user_id}-{datetime.utcnow().timestamp()}')
            except Exception:
                pass

            # Attempt reserved auto-upgrade if phase ready and balance sufficient
            auto_result = self._attempt_reserved_auto_upgrade(user_id, currency)

            # Trigger eligibility checks (best-effort)
            try:
                RoyalCaptainService().process_bonus_tiers(user_id)
            except Exception:
                pass
            try:
                PresidentRewardService().process_reward_tiers(user_id)
            except Exception:
                pass

            return {
                "success": True,
                "distribution_breakdown": {
                    "level_reserved": float(reserved_upgrade),  # 30%
                    "partner_incentive": float(total * Decimal('0.10')),  # 10% (already handled)
                    "profit": float(profit_portion),  # 30%
                    "royal_captain": float(royal_captain_portion),  # 10%
                    "president_reward": float(president_reward_portion),  # 10%
                    "triple_entry": float(triple_entry_portion),  # 5%
                    "shareholders": float(shareholders_portion)  # 5%
                },
                "auto_upgrade": auto_result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_phase_seats(self, user_id: str, phase: str) -> Dict[str, Any]:
        try:
            if phase not in ['PHASE-1', 'PHASE-2']:
                return {"success": False, "error": "Invalid phase"}
            parent_oid = ObjectId(user_id)
            expected = 4 if phase == 'PHASE-1' else 8
            children = TreePlacement.objects(parent_id=parent_oid, program='global', phase=phase, is_active=True)
            seats = {str(i): None for i in range(1, expected + 1)}
            for ch in children:
                if ch.phase_position and 1 <= ch.phase_position <= expected:
                    seats[str(ch.phase_position)] = str(ch.user_id)
            return {"success": True, "phase": phase, "seats": seats}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def preview_distribution(self, amount: Decimal) -> Dict[str, Any]:
        try:
            total = Decimal(str(amount))
            return {
                "success": True,
                "distribution_breakdown": {
                    "level_reserved": float(total * Decimal('0.30')),  # 30%
                    "partner_incentive": float(total * Decimal('0.10')),  # 10%
                    "profit": float(total * Decimal('0.30')),  # 30%
                    "royal_captain": float(total * Decimal('0.10')),  # 10%
                    "president_reward": float(total * Decimal('0.10')),  # 10%
                    "triple_entry": float(total * Decimal('0.05')),  # 5%
                    "shareholders": float(total * Decimal('0.05'))  # 5%
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_global_tree(self, user_id: str, phase: str) -> Dict[str, Any]:
        """Return usersData array for GlobalMatrixGraph: [{id:position, type, userId}]"""
        try:
            if phase not in ['phase-1', 'phase-2']:
                return {"success": False, "error": "phase must be 'phase-1' or 'phase-2'"}
            phase_key = 'PHASE-1' if phase == 'phase-1' else 'PHASE-2'
            parent_oid = ObjectId(user_id)
            expected = 4 if phase_key == 'PHASE-1' else 8
            children = TreePlacement.objects(parent_id=parent_oid, program='global', phase=phase_key, is_active=True)
            pos_to_user: Dict[int, str] = {}
            for ch in children:
                if ch.phase_position and 1 <= ch.phase_position <= expected:
                    pos_to_user[ch.phase_position] = str(ch.user_id)
            users_data = []
            for i in range(1, expected + 1):
                occupant = pos_to_user.get(i)
                users_data.append({
                    "id": i,
                    "type": "active" if occupant else "empty",
                    "userId": occupant
                })
            return {
                "success": True,
                "user_id": user_id,
                "phase": phase,
                "usersData": users_data
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_phase_progression(self, user_id: str) -> Dict[str, Any]:
        """
        3.1 Phase-1 to Phase-2 Progression - Section 3.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        **Trigger**: User has 4 people in Phase-1 under them
        **Auto Action**: `process_progression()`
        """
        try:
            # Get user's GlobalPhaseProgression record
            progression = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not progression:
                return {"success": False, "error": "GlobalPhaseProgression record not found"}

            # 3.1.1 Phase Completion Check - Section 3.1.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Check if phase_1_members_current >= phase_1_members_required (4)
            if progression.phase_1_members_current < progression.phase_1_members_required:
                print(f"Phase-1 completion check failed for user {user_id}: {progression.phase_1_members_current}/{progression.phase_1_members_required} members")
                return {"success": False, "error": f"Phase-1 not complete: {progression.phase_1_members_current}/{progression.phase_1_members_required} members"}

            # Verify next_phase_ready is true
            if not progression.next_phase_ready:
                print(f"Phase-1 completion check failed for user {user_id}: next_phase_ready is false")
                return {"success": False, "error": "Next phase not ready"}

            print(f"Phase-1 completion check passed for user {user_id}: {progression.phase_1_members_current}/{progression.phase_1_members_required} members, next_phase_ready={progression.next_phase_ready}")

            # 3.1.2 Phase Status Update - Section 3.1.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Set current_phase: 'PHASE-2'
            progression.current_phase = 'PHASE-2'
            # Set current_slot_no: 1 (Phase-2 first slot)
            progression.current_slot_no = 1
            # Set is_phase_complete: true
            progression.is_phase_complete = True
            # Set phase_completed_at: current_timestamp
            progression.phase_completed_at = datetime.utcnow()
            # Set next_phase_ready: false
            progression.next_phase_ready = False
            # Update timestamp
            progression.updated_at = datetime.utcnow()
            progression.save()

            print(f"Phase status updated for user {user_id}: PHASE-1 -> PHASE-2, slot 1, phase_completed_at={progression.phase_completed_at}")

            # 3.1.3 Phase-2 Placement - Section 3.1.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Place user in Phase-2 tree using BFS algorithm
            placement_result = self._place_in_phase2(user_id)
            if not placement_result.get("success"):
                print(f"Phase-2 placement failed for user {user_id}: {placement_result.get('error')}")
                return {"success": False, "error": f"Phase-2 placement failed: {placement_result.get('error')}"}

            print(f"Phase-2 placement completed for user {user_id}: parent={placement_result.get('parent_id')}")

            # 3.1.4 Reserved Funds Usage - Section 3.1.4 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Use reserved_upgrade_amount for Phase-2 slot activation
            if progression.reserved_upgrade_amount and progression.reserved_upgrade_amount > 0:
                try:
                    # Get Phase-2 Slot-1 catalog
                    catalog = SlotCatalog.objects(program='global', slot_no=1, phase='PHASE-2').first()
                    if catalog and progression.reserved_upgrade_amount >= catalog.price:
                        # Create SlotActivation record for Phase-2 Slot-1
                        current_time = datetime.utcnow()
                        activation = SlotActivation(
                            user_id=ObjectId(user_id),
                            program='global',
                            slot_no=1,
                            slot_name=catalog.name,
                            activation_type='auto_upgrade',
                            upgrade_source='reserved',
                            amount_paid=catalog.price,
                            currency='USD',
                            tx_hash=f"PHASE2_AUTO_{user_id}_{current_time.strftime('%Y%m%d%H%M%S')}",
                            blockchain_network='BSC',
                            commission_paid=Decimal('0'),
                            commission_percentage=0.0,
                            is_auto_upgrade=True,
                            partners_contributed=[],
                            earnings_used=progression.reserved_upgrade_amount,
                            status='completed',
                            activated_at=current_time,
                            completed_at=current_time,
                            created_at=current_time,
                            metadata={
                                'upgrade_type': 'auto',
                                'slot_level': catalog.level,
                                'validation_passed': True,
                                'upgrade_sequence': 1,
                                'phase_progression': True,
                                'reserved_funds_used': float(progression.reserved_upgrade_amount)
                            }
                        )
                        activation.save()

                        # Update reserved amount
                        progression.reserved_upgrade_amount -= catalog.price
                        progression.save()

                        print(f"Phase-2 Slot-1 auto-activated for user {user_id}: {catalog.name} - ${catalog.price} (reserved funds used)")
                    else:
                        print(f"Insufficient reserved funds for Phase-2 Slot-1: {progression.reserved_upgrade_amount} < {catalog.price if catalog else 'N/A'}")
                except Exception as e:
                    print(f"Reserved funds usage failed for user {user_id}: {str(e)}")

            return {
                "success": True,
                "user_id": user_id,
                "old_phase": "PHASE-1",
                "new_phase": "PHASE-2",
                "new_slot_no": 1,
                "phase_completed_at": progression.phase_completed_at,
                "placement_result": placement_result
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _place_in_phase2(self, user_id: str) -> Dict[str, Any]:
        """
        Place user in Phase-2 tree using BFS algorithm
        Find eligible upline with available Phase-2 positions
        Update parent's phase_2_members_current count
        """
        try:
            # Find eligible upline with available Phase-2 positions
            parent = self._find_phase2_parent_bfs(user_id)
            if not parent:
                # Try escalation if no direct parent found
                parent = self._find_phase2_parent_escalation(user_id)
                if not parent:
                    # Fallback to Mother ID
                    parent = self._get_mother_id()
                    if not parent:
                        return {"success": False, "error": "No eligible parent found for Phase-2 placement"}

            # Create TreePlacement record for Phase-2
            placement = TreePlacement(
                user_id=ObjectId(user_id),
                program='global',
                phase='PHASE-2',
                slot_no=1,
                parent_id=ObjectId(parent.id),
                placement_type='phase_progression',
                placed_at=datetime.utcnow()
            )
            placement.save()

            # Update parent's Phase-2 member count
            parent_progression = GlobalPhaseProgression.objects(user_id=ObjectId(parent.id)).first()
            if parent_progression:
                parent_progression.phase_2_members_current += 1
                parent_progression.updated_at = datetime.utcnow()
                parent_progression.save()

                # Check if parent's Phase-2 is complete (8 members)
                if parent_progression.phase_2_members_current >= parent_progression.phase_2_members_required:
                    parent_progression.is_phase_complete = True
                    parent_progression.next_phase_ready = True
                    parent_progression.save()
                    print(f"Parent {parent.id} Phase-2 completed: {parent_progression.phase_2_members_current}/{parent_progression.phase_2_members_required} members")

            return {
                "success": True,
                "parent_id": str(parent.id),
                "placement_id": str(placement.id),
                "phase": "PHASE-2",
                "slot_no": 1
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _find_phase2_parent_bfs(self, user_id: str):
        """
        Find eligible upline with available Phase-2 positions using BFS
        """
        try:
            # Get user's direct upline
            user = User.objects(id=ObjectId(user_id)).first()
            if not user or not user.referrer_id:
                return None

            # Start BFS from direct upline
            queue = [user.referrer_id]
            visited = set()

            while queue:
                current_id = queue.pop(0)
                if current_id in visited:
                    continue
                visited.add(current_id)

                # Check if current user has available Phase-2 positions
                progression = GlobalPhaseProgression.objects(user_id=current_id).first()
                if progression and progression.phase_2_members_current < progression.phase_2_members_required:
                    return User.objects(id=current_id).first()

                # Add upline to queue
                current_user = User.objects(id=current_id).first()
                if current_user and current_user.referrer_id:
                    queue.append(current_user.referrer_id)

            return None

        except Exception as e:
            print(f"Phase-2 BFS parent search failed: {str(e)}")
            return None

    def _find_phase2_parent_escalation(self, user_id: str):
        """
        Find eligible upline with available Phase-2 positions using escalation
        """
        try:
            # Get user's direct upline
            user = User.objects(id=ObjectId(user_id)).first()
            if not user or not user.referrer_id:
                return None

            current_id = user.referrer_id
            level = 0
            max_levels = 60

            while level < max_levels:
                # Check if current user has available Phase-2 positions
                progression = GlobalPhaseProgression.objects(user_id=current_id).first()
                if progression and progression.phase_2_members_current < progression.phase_2_members_required:
                    return User.objects(id=current_id).first()

                # Move to next upline
                current_user = User.objects(id=current_id).first()
                if not current_user or not current_user.referrer_id:
                    break

                current_id = current_user.referrer_id
                level += 1

            return None

        except Exception as e:
            print(f"Phase-2 escalation parent search failed: {str(e)}")
            return None
