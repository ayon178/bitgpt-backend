#!/usr/bin/env python3
"""
Complete Fund Distribution Percentages Implementation
This service implements all fund distribution percentages for Binary, Matrix, and Global programs
"""

from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Any, Optional
from bson import ObjectId

from modules.user.model import User
from modules.income.model import IncomeEvent
from modules.wallet.model import UserWallet, ReserveLedger
from modules.tree.model import TreePlacement

class FundDistributionService:
    """Service for handling complete fund distribution percentages across all programs"""
    
    def __init__(self):
        # Use income_type values that match IncomeEvent model choices
        self.binary_percentages = {
            "spark_bonus": Decimal('8.0'),
            "royal_captain": Decimal('4.0'),  # Changed from royal_captain_bonus
            "president_reward": Decimal('3.0'),
            "leadership_stipend": Decimal('5.0'),
            "jackpot": Decimal('5.0'),  # Changed from jackpot_entry
            "partner_incentive": Decimal('10.0'),
            "shareholders": Decimal('5.0'),  # Changed from share_holders
            "level_distribution": Decimal('60.0')
        }
        
        self.matrix_percentages = {
            "spark_bonus": Decimal('8.0'),
            "royal_captain": Decimal('4.0'),  # Changed from royal_captain_bonus
            "president_reward": Decimal('3.0'),
            "newcomer_support": Decimal('20.0'),  # Changed from newcomer_growth_support
            "mentorship": Decimal('10.0'),  # Changed from mentorship_bonus
            "partner_incentive": Decimal('10.0'),
            "shareholders": Decimal('5.0'),  # Changed from share_holders
            "level_distribution": Decimal('40.0')
        }
        
        self.global_percentages = {
            "global_phase_1": Decimal('30.0'),  # Tree upline reserve
            "global_phase_2": Decimal('30.0'),  # Tree upline wallet
            "partner_incentive": Decimal('10.0'),
            "royal_captain": Decimal('10.0'),  # Changed from royal_captain_bonus
            "president_reward": Decimal('10.0'),
            "shareholders": Decimal('5.0'),  # Changed from share_holders
            "triple_entry": Decimal('5.0')  # Handled separately via SparkService, not BonusFund
        }
        
        # Binary level distribution breakdown (60% treated as 100%)
        self.binary_level_breakdown = {
            1: Decimal('30.0'),   # Level 1: 30%
            2: Decimal('10.0'),   # Level 2: 10%
            3: Decimal('10.0'),    # Level 3: 10%
            4: Decimal('5.0'),    # Level 4: 5%
            5: Decimal('5.0'),    # Level 5: 5%
            6: Decimal('5.0'),    # Level 6: 5%
            7: Decimal('5.0'),    # Level 7: 5%
            8: Decimal('5.0'),    # Level 8: 5%
            9: Decimal('5.0'),    # Level 9: 5%
            10: Decimal('5.0'),   # Level 10: 5%
            11: Decimal('3.0'),   # Level 11: 3%
            12: Decimal('3.0'),   # Level 12: 3%
            13: Decimal('3.0'),   # Level 13: 3%
            14: Decimal('2.0'),   # Level 14: 2%
            15: Decimal('2.0'),   # Level 15: 2%
            16: Decimal('2.0')    # Level 16: 2%
        }
        
        # Matrix level distribution breakdown (40% treated as 100%)
        self.matrix_level_breakdown = {
            1: Decimal('30.0'),   # Level 1: 30%
            2: Decimal('10.0'),   # Level 2: 10%
            3: Decimal('10.0')    # Level 3: 10%
        }

    def distribute_binary_funds(self, user_id: str, amount: Decimal, slot_no: int, 
                               referrer_id: str = None, tx_hash: str = None, currency: str = 'BNB') -> Dict[str, Any]:
        """Distribute Binary program funds according to percentages"""
        try:
            # Slot 1 special rule: 100% goes to direct upline handled elsewhere (auto-upgrade/placement service)
            # Do NOT run any pool distributions or partner incentive for Slot 1 joins
            if int(slot_no) == 1:
                return {
                    "success": True,
                    "total_amount": amount,
                    "total_distributed": Decimal('0.0'),
                    "distributions": [],
                    "distribution_type": "binary",
                    "skipped": True,
                    "message": "Slot 1 distribution skipped; full fee handled by slot-1 upline commission."
                }

            if not tx_hash:
                tx_hash = f"BINARY_DIST_{user_id}_{int(datetime.now().timestamp())}"
            
            distributions = []
            total_distributed = Decimal('0.0')
            
            # Calculate each distribution
            for income_type, percentage in self.binary_percentages.items():
                if income_type == "level_distribution":
                    # Handle level distribution separately
                    level_distributions = self._distribute_binary_levels(
                        user_id, amount, percentage, slot_no, tx_hash, currency
                    )
                    distributions.extend(level_distributions)
                    total_distributed += amount * (percentage / Decimal('100.0'))
                elif income_type == "partner_incentive":
                    # Handle partner incentive separately (goes to referrer, not user)
                    if referrer_id:
                        dist_amount = amount * (percentage / Decimal('100.0'))
                        if dist_amount > 0:
                            distribution = self._create_income_event(
                                referrer_id, user_id, 'binary', slot_no, income_type,
                                dist_amount, percentage, tx_hash, "Binary Partner Incentive", currency
                            )
                            distributions.append(distribution)
                            total_distributed += dist_amount
                elif income_type == "mentorship":
                    # 10% mentorship payout to super upline (direct referrer's referrer)
                    try:
                        from modules.mentorship.service import MentorshipService
                        from modules.user.model import User
                        ref = User.objects(id=ObjectId(referrer_id)).first() if referrer_id else None
                        super_upline = str(getattr(ref, 'refered_by', '')) if ref else None
                        if super_upline:
                            ms = MentorshipService()
                            ms.process_matrix_mentorship(user_id=user_id, referrer_id=referrer_id, amount=amount * (percentage / Decimal('100.0')), currency=currency)
                            distributions.append({
                                "type": "mentorship",
                                "to_user_id": super_upline,
                                "amount": float(amount * (percentage / Decimal('100.0')))
                            })
                            total_distributed += amount * (percentage / Decimal('100.0'))
                    except Exception:
                        pass
                elif income_type == "shareholders":
                    # Route to shareholders fund/account
                    dist_amount = amount * (percentage / Decimal('100.0'))
                    if dist_amount > 0:
                        try:
                            # Use importlib because 'global' is a Python keyword
                            import importlib
                            global_service_module = importlib.import_module('modules.global.service')
                            GlobalService = global_service_module.GlobalService
                            from modules.user.model import ShareholdersFund
                            gs = GlobalService()
                            
                            # IMPORTANT: process_shareholders_fund_distribution expects full transaction amount
                            # and calculates 5% internally. Since we already have the 5% amount (dist_amount),
                            # we need to pass the full amount OR modify to pass the calculated 5% directly.
                            # For now, pass the full amount so function can calculate 5% correctly
                            shareholders_result = gs.process_shareholders_fund_distribution(
                                amount,  # Pass full amount, function will calculate 5% internally
                                transaction_type='binary_distribution'
                            )
                            
                            if shareholders_result.get("success"):
                                distributions.append({
                                    "type": "shareholders",
                                    "amount": float(dist_amount),
                                    "shareholders_fund_updated": True,
                                    "message": "Shareholders fund updated"
                                })
                                total_distributed += dist_amount
                            else:
                                print(f"[BINARY_DIST] Shareholders fund update failed: {shareholders_result.get('error')}")
                                distributions.append({
                                    "type": "shareholders",
                                    "amount": float(dist_amount),
                                    "shareholders_fund_updated": False,
                                    "error": shareholders_result.get("error")
                                })
                                total_distributed += dist_amount
                        except Exception as e:
                            print(f"[BINARY_DIST] Error routing shareholders fund: {e}")
                            import traceback
                            traceback.print_exc()
                            # Still track the distribution amount
                            total_distributed += dist_amount
                else:
                    # Direct distribution to fund pools
                    dist_amount = amount * (percentage / Decimal('100.0'))
                    if dist_amount > 0:
                        distribution = self._create_income_event(
                            user_id, user_id, 'binary', slot_no, income_type,
                            dist_amount, percentage, tx_hash, f"Binary {income_type.replace('_', ' ').title()}", currency
                        )
                        distributions.append(distribution)
                        total_distributed += dist_amount
            
            return {
                "success": True,
                "total_amount": amount,
                "total_distributed": total_distributed,
                "distributions": distributions,
                "distribution_type": "binary"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Binary fund distribution failed: {str(e)}"}

    def distribute_matrix_funds(self, user_id: str, amount: Decimal, slot_no: int,
                              referrer_id: str = None, tx_hash: str = None, currency: str = 'USDT',
                              placement_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Distribute Matrix program funds according to percentages"""
        try:
            from modules.slot.model import SlotActivation
            from modules.user.tree_reserve_service import TreeUplineReserveService
            if not tx_hash:
                tx_hash = f"MATRIX_DIST_{user_id}_{int(datetime.now().timestamp())}"
            
            distributions = []
            total_distributed = Decimal('0.0')

            # Special routing: super-upline middle position → 100% to next-slot reserve
            try:
                if placement_context:
                    try:
                        print(f"[MATRIX ROUTING] placement_context={placement_context}")
                    except Exception:
                        pass
                    placed_under_user_id = placement_context.get('placed_under_user_id')  # immediate parent in many flows
                    placement_level = placement_context.get('level')
                    placement_position = placement_context.get('position')
                    # Case A: Level-2 placement and it's the middle child (position % 3 == 1)
                    # In many code paths, placed_under_user_id is the immediate parent (Level-1 node),
                    # so resolve the tree owner as parent.parent_id for this slot.
                    if placed_under_user_id and placement_level == 2 and placement_position is not None and int(placement_position) % 3 == 1:
                        try:
                            # Resolve tree owner (super upline) via parent chain
                            parent_link = TreePlacement.objects(
                                user_id=ObjectId(placed_under_user_id),
                                program='matrix',
                                slot_no=slot_no,
                                is_active=True
                            ).first()
                            tree_owner_id = str(parent_link.parent_id) if parent_link and getattr(parent_link, 'parent_id', None) else str(placed_under_user_id)
                        except Exception:
                            tree_owner_id = str(placed_under_user_id)

                        next_slot_no = slot_no + 1
                        already_active = False
                        try:
                            act = SlotActivation.objects(user_id=ObjectId(tree_owner_id), program='matrix', slot_no=next_slot_no, status='completed').first()
                            already_active = bool(act)
                        except Exception:
                            already_active = False
                        if not already_active:
                            reserve_service = TreeUplineReserveService()
                            ok, msg = reserve_service.add_to_reserve_fund(
                                tree_upline_id=tree_owner_id,
                                program='matrix',
                                slot_no=slot_no,
                                amount=Decimal(str(amount)),
                                source_user_id=str(user_id),
                                tx_hash=tx_hash
                            )
                            distributions.append({
                                "type": "super_upline_middle_reserve",
                                "to_user_id": tree_owner_id,
                                "amount": float(amount),
                                "slot_no": slot_no,
                                "message": msg,
                                "success": ok
                            })
                            return {"success": True, "data": distributions, "total_distributed": float(amount), "routed_to_reserve": True}
                    # Case B: placement is Level-1 under a child; if child is Level-1 under a super upline and child_offset is middle → treat as Level-2 middle under super upline
                    if placed_under_user_id and placement_level == 1 and placement_position is not None:
                        try:
                            print(f"[MATRIX ROUTING] Case B check: user={user_id}, placed_under={placed_under_user_id}, level={placement_level}, position={placement_position}")
                            # Determine the tree owner (super upline) of the immediate parent for this slot
                            parent_link = TreePlacement.objects(
                                user_id=ObjectId(placed_under_user_id),
                                program='matrix',
                                slot_no=slot_no,
                                is_active=True
                            ).first()
                            print(f"[MATRIX ROUTING] Case B parent_link found: {parent_link is not None}")
                            # Placement must be the middle child under its immediate parent
                            if parent_link and int(placement_position) == 1:
                                print(f"[MATRIX ROUTING] Case B: position is middle (1)")
                                # The tree owner is the grandparent (parent of the immediate parent) in this slot
                                super_owner_id = None
                                if getattr(parent_link, 'parent_id', None):
                                    parent_parent = TreePlacement.objects(
                                        user_id=parent_link.parent_id,
                                        program='matrix',
                                        slot_no=slot_no,
                                        is_active=True
                                    ).first()
                                    if parent_parent and getattr(parent_parent, 'parent_id', None):
                                        super_owner_id = str(parent_parent.parent_id)
                                print(f"[MATRIX ROUTING] Case B: super_owner_id={super_owner_id}")
                                if super_owner_id:
                                    next_slot_no = slot_no + 1
                                    act = SlotActivation.objects(
                                        user_id=ObjectId(super_owner_id),
                                        program='matrix',
                                        slot_no=next_slot_no,
                                        status='completed'
                                    ).first()
                                    if act:
                                        print(f"[MATRIX ROUTING] Case B: super owner slot already active, skipping reserve")
                                    else:
                                        print(f"[MATRIX ROUTING] Case B: routing to reserve...")
                                        reserve_service = TreeUplineReserveService()
                                        ok, msg = reserve_service.add_to_reserve_fund(
                                            tree_upline_id=super_owner_id,
                                            program='matrix',
                                            slot_no=slot_no,
                                            amount=Decimal(str(amount)),
                                            source_user_id=str(user_id),
                                            tx_hash=tx_hash
                                        )
                                        print(f"[MATRIX ROUTING] Case B routed to reserve: owner={super_owner_id}, ok={ok}, msg={msg}")
                                        distributions.append({
                                            "type": "derived_middle_reserve",
                                            "to_user_id": super_owner_id,
                                            "amount": float(amount),
                                            "slot_no": slot_no,
                                            "message": msg,
                                            "success": ok
                                        })
                                        return {"success": True, "data": distributions, "total_distributed": float(amount), "routed_to_reserve": True}
                        except Exception as e:
                            print(f"[MATRIX ROUTING] Case B exception: {e}")
                            import traceback
                            traceback.print_exc()
                            pass
            except Exception as e:
                # Fail-safe: if special routing check fails, continue with normal distribution
                print(f"[MATRIX ROUTING] Outer exception during special routing: {e}")
                import traceback
                traceback.print_exc()
                pass
            
            # Calculate each distribution
            for income_type, percentage in self.matrix_percentages.items():
                if income_type == "level_distribution":
                    # Handle level distribution separately
                    level_distributions = self._distribute_matrix_levels(
                        user_id, amount, percentage, slot_no, tx_hash, currency
                    )
                    distributions.extend(level_distributions)
                    total_distributed += amount * (percentage / Decimal('100.0'))
                elif income_type == "partner_incentive":
                    # Handle partner incentive separately (goes to referrer, not user)
                    if referrer_id:
                        dist_amount = amount * (percentage / Decimal('100.0'))
                        if dist_amount > 0:
                            distribution = self._create_income_event(
                                referrer_id, user_id, 'matrix', slot_no, income_type,
                                dist_amount, percentage, tx_hash, "Matrix Partner Incentive", currency
                            )
                            distributions.append(distribution)
                            total_distributed += dist_amount
                elif income_type == "mentorship":
                    # Mentorship 10% → super upline (direct referrer's referrer)
                    try:
                        if referrer_id:
                            from modules.user.model import User as _User
                            super_upline = None
                            try:
                                ref_u = _User.objects(id=ObjectId(referrer_id)).first()
                                if ref_u and getattr(ref_u, 'refered_by', None):
                                    super_upline = str(ref_u.refered_by)
                            except Exception:
                                super_upline = None

                            if super_upline:
                                dist_amount = amount * (percentage / Decimal('100.0'))
                                if dist_amount > 0:
                                    # Use MentorshipService to also update program records
                                    try:
                                        from modules.mentorship.service import MentorshipService
                                        MentorshipService().process_matrix_mentorship(
                                            user_id=user_id,
                                            referrer_id=referrer_id,
                                            amount=dist_amount,
                                            currency=currency
                                        )
                                    except Exception:
                                        pass

                                    # Record income event for auditing + credit wallet
                                    distribution = self._create_income_event(
                                        super_upline, user_id, 'matrix', slot_no, 'mentorship',
                                        dist_amount, percentage, tx_hash, "Matrix Mentorship Bonus", currency
                                    )
                                    distributions.append(distribution)
                                    total_distributed += dist_amount
                    except Exception:
                        pass
                elif income_type == "newcomer_support":
                    # Newcomer Growth Support 20%: 50% to user (instant), 50% to direct upline's newcomer fund
                    try:
                        from modules.newcomer_support.service import NewcomerSupportService
                        svc = NewcomerSupportService()
                        # Call service with the full amount; it applies 20% internally per spec docs
                        # However our loop computes percentage. To avoid double-applying, compute split here.
                        ngs_amount = amount * (percentage / Decimal('100.0'))
                        user_half = ngs_amount * Decimal('0.50')
                        upline_half = ngs_amount * Decimal('0.50')

                        # Persist detailed newcomer entries
                        try:
                            svc.process_matrix_contribution(
                                user_id=user_id,
                                amount=float(amount),  # service expects total to derive 20%
                                referrer_id=referrer_id,
                                tx_hash=tx_hash,
                                currency=str(currency)
                            )
                        except Exception:
                            pass

                        # Record income events for audit and to credit user's wallet for instant claimable portion
                        if user_half > 0:
                            distribution_user = self._create_income_event(
                                user_id, user_id, 'matrix', slot_no, 'newcomer_support',
                                user_half, Decimal('50.0'), tx_hash, "Newcomer Growth Support (User 50%)", currency
                            )
                            distributions.append(distribution_user)
                            total_distributed += user_half

                        # Upline fund is reserved; record event to upline but do not credit wallet immediately
                        if referrer_id and upline_half > 0:
                            try:
                                distribution_upline = self._create_income_event(
                                    referrer_id, user_id, 'matrix', slot_no, 'newcomer_support_upline_fund',
                                    upline_half, Decimal('50.0'), tx_hash, "Newcomer Growth Support (Upline 50% Reserved)", currency
                                )
                                distributions.append(distribution_upline)
                                total_distributed += upline_half
                            except Exception:
                                pass
                    except Exception:
                        pass
                else:
                    # Direct distribution to fund pools
                    dist_amount = amount * (percentage / Decimal('100.0'))
                    if dist_amount > 0:
                        if income_type == 'shareholders':
                            # Route to shareholders fund/account
                            try:
                                import importlib
                                global_module = importlib.import_module('modules.global.service')
                                gs = global_module.GlobalService()
                                gs.process_shareholders_fund_distribution(dist_amount, transaction_type='matrix_distribution')
                            except Exception:
                                pass
                        # Create income event for non-shareholders distributions
                        if income_type != 'shareholders':
                            distribution = self._create_income_event(
                                user_id, user_id, 'matrix', slot_no, income_type,
                                dist_amount, percentage, tx_hash, f"Matrix {income_type.replace('_', ' ').title()}", currency
                            )
                            distributions.append(distribution)
                            total_distributed += dist_amount
            
            return {
                "success": True,
                "total_amount": amount,
                "total_distributed": total_distributed,
                "distributions": distributions,
                "distribution_type": "matrix"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Matrix fund distribution failed: {str(e)}"}

    def distribute_global_funds(self, user_id: str, amount: Decimal, slot_no: int,
                               referrer_id: str = None, tx_hash: str = None) -> Dict[str, Any]:
        """Distribute Global program funds according to percentages"""
        try:
            if not tx_hash:
                tx_hash = f"GLOBAL_DIST_{user_id}_{int(datetime.now().timestamp())}"
            
            distributions = []
            total_distributed = Decimal('0.0')
            
            # Calculate each distribution
            for income_type, percentage in self.global_percentages.items():
                dist_amount = amount * (percentage / Decimal('100.0'))
                if dist_amount > 0:
                    distribution = self._create_income_event(
                        user_id, user_id, 'global', slot_no, income_type,
                        dist_amount, percentage, tx_hash, f"Global {income_type.replace('_', ' ').title()}"
                    )
                    distributions.append(distribution)
                    total_distributed += dist_amount
            
            # Handle partner incentive separately if referrer provided
            if referrer_id and "partner_incentive" in self.global_percentages:
                pi_amount = amount * (self.global_percentages["partner_incentive"] / Decimal('100.0'))
                if pi_amount > 0:
                    pi_distribution = self._create_income_event(
                        referrer_id, user_id, 'global', slot_no, 'partner_incentive',
                        pi_amount, self.global_percentages["partner_incentive"], 
                        tx_hash, "Global Partner Incentive"
                    )
                    distributions.append(pi_distribution)
            
            return {
                "success": True,
                "total_amount": amount,
                "total_distributed": total_distributed,
                "distributions": distributions,
                "distribution_type": "global"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Global fund distribution failed: {str(e)}"}

    def _distribute_binary_levels(self, user_id: str, amount: Decimal, percentage: Decimal,
                                 slot_no: int, tx_hash: str, currency: str = 'BNB') -> List[Dict[str, Any]]:
        """
        Distribute Binary level distribution (60% treated as 100%)
        
        Key Logic:
        1. Find Nth upline from activating user (using base tree, slot 1)
        2. Start from Nth upline as Level 1
        3. Traverse upward for levels 1-16
        4. For each level, check if user has Slot N activated
        5. If yes → give reward to that user
        6. If no or upline not found → give to Mother Account
        """
        distributions = []
        level_amount = amount * (percentage / Decimal('100.0'))
        
        # Step 1: Find Nth upline from activating user using base tree (slot 1)
        nth_upline_id = self._get_nth_upline_by_slot_for_distribution(user_id, slot_no)
        
        if not nth_upline_id:
            # No Nth upline found → send all level distribution to Mother Account
            print(f"[BINARY_LEVEL_DIST] No {slot_no}th upline found for user {user_id}, sending all to Mother Account")
            total_level_amount = level_amount
            if total_level_amount > 0:
                distribution = self._create_mother_account_income_event(
                    source_id=user_id,
                    program='binary',
                    slot_no=slot_no,
                    amount=total_level_amount,
                    tx_hash=tx_hash,
                    description=f"Binary Level Distribution (No {slot_no}th upline) - Mother Account",
                    currency=currency
                )
                distributions.append(distribution)
            return distributions
        
        print(f"[BINARY_LEVEL_DIST] Found {slot_no}th upline: {nth_upline_id} for user {user_id}")
        
        # Step 2: Start from Nth upline (Level 1) and traverse upward for levels 1-16
        for level in range(1, 17):  # Levels 1-16
            level_percentage = self.binary_level_breakdown.get(level, Decimal('0'))
            if level_percentage <= 0:
                continue
                
            level_dist_amount = level_amount * (level_percentage / Decimal('100.0'))
            
            if level_dist_amount <= 0:
                continue
            
            # Level 1 = Nth upline itself (0 steps up)
            # Level 2 = 1 step up from Nth upline
            # Level 3 = 2 steps up from Nth upline
            # etc.
            if level == 1:
                level_user_id = nth_upline_id
            else:
                # For levels 2-16, traverse upward from Nth upline
                # Level 2 needs 1 step, Level 3 needs 2 steps, etc.
                level_user_id = self._traverse_upline_upward(nth_upline_id, level - 1)
            
            # Step 3: Check if level user has Slot N activated
            if level_user_id:
                has_slot_activated = self._check_slot_activation(level_user_id, 'binary', slot_no)
                
                if has_slot_activated:
                    # User has Slot N activated → give reward to this user
                    print(f"[BINARY_LEVEL_DIST] Level {level}: User {level_user_id} has Slot {slot_no} activated, crediting {level_dist_amount}")
                    distribution = self._create_income_event(
                        recipient_id=str(level_user_id),
                        source_id=user_id,
                        program='binary',
                        slot_no=slot_no,
                        income_type='level_payout',  # Use 'level_payout' as IncomeEvent only accepts this
                        amount=level_dist_amount,
                        percentage=level_percentage,
                        tx_hash=tx_hash,
                        description=f"Binary Level {level} Distribution",
                        currency=currency
                    )
                    distributions.append(distribution)
                else:
                    # User doesn't have Slot N activated → send to Mother Account
                    print(f"[BINARY_LEVEL_DIST] Level {level}: User {level_user_id} does NOT have Slot {slot_no} activated, sending to Mother Account")
                    distribution = self._create_mother_account_income_event(
                        source_id=user_id,
                        program='binary',
                        slot_no=slot_no,
                        amount=level_dist_amount,
                        tx_hash=tx_hash,
                        description=f"Binary Level {level} Distribution (Slot {slot_no} not activated) - Mother Account",
                        currency=currency,
                        missed_user_id=str(level_user_id),
                        from_user_id=user_id,
                        slot_name=f"Slot {slot_no}",
                        missed_reason='level_slot_inactive'
                    )
                    distributions.append(distribution)
            else:
                # No upline found at this level → send to Mother Account
                print(f"[BINARY_LEVEL_DIST] Level {level}: No upline found, sending to Mother Account")
                distribution = self._create_mother_account_income_event(
                    source_id=user_id,
                    program='binary',
                    slot_no=slot_no,
                    amount=level_dist_amount,
                    tx_hash=tx_hash,
                    description=f"Binary Level {level} Distribution (No upline) - Mother Account",
                    currency=currency,
                    missed_user_id=None,
                    from_user_id=user_id,
                    slot_name=f"Slot {slot_no}",
                    missed_reason='no_upline_found'
                )
                distributions.append(distribution)
        
        return distributions
    
    def _get_nth_upline_by_slot_for_distribution(self, user_id: str, slot_no: int) -> Optional[ObjectId]:
        """
        Find Nth upline from activating user using the Binary tree placement (`TreePlacement.upline_id`).
        
        Business rule (per latest spec):
        - Level distribution should follow the same Binary tree that first/second position logic uses,
          but ONLY for upline chain (no change to reserve routing logic elsewhere).
        - Starting point: user's placement in the slot-N tree (preferred), falling back to slot-1 base tree.
        - Each step moves to the current node's `upline_id`.
        - After N steps, we return that ancestor as the Nth upline.
        """
        try:
            from modules.tree.model import TreePlacement

            oid = ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id

            # Prefer placement in the specific slot tree; fallback to base (slot 1)
            current = TreePlacement.objects(
                user_id=oid, program='binary', slot_no=slot_no, is_active=True
            ).first()
            if not current:
                current = TreePlacement.objects(
                    user_id=oid, program='binary', slot_no=1, is_active=True
                ).first()
            if not current:
                print(f"[BINARY_LEVEL_DIST] No placement found for user {user_id} in slot {slot_no} or base tree")
                return None

            steps = 0
            upline = current.upline_id

            while upline and steps < slot_no:
                steps += 1
                if steps == slot_no:
                    return upline

                # Move one step up via upline's own placement
                next_pl = TreePlacement.objects(
                    user_id=upline, program='binary', slot_no=slot_no, is_active=True
                ).first()
                if not next_pl:
                    next_pl = TreePlacement.objects(
                        user_id=upline, program='binary', slot_no=1, is_active=True
                    ).first()
                if not next_pl:
                    break

                upline = next_pl.upline_id

            print(f"[BINARY_LEVEL_DIST] Reached top of tree or missing upline at step {steps}, needed {slot_no}")
            return None

        except Exception as e:
            print(f"[BINARY_LEVEL_DIST] Error finding {slot_no}th upline (tree upline_id): {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _traverse_upline_upward(self, start_upline_id: ObjectId, steps: int) -> Optional[ObjectId]:
        """
        Traverse upward from a starting upline for the specified number of steps.
        Uses base binary tree (slot 1) for traversal.
        """
        try:
            current_id = start_upline_id
            steps_taken = 0
            
            while steps_taken < steps:
                # Get current upline's placement in base tree (slot 1)
                current_placement = TreePlacement.objects(
                    user_id=current_id,
                    program='binary',
                    slot_no=1,
                    is_active=True
                ).first()
                
                if not current_placement:
                    return None
                
                # Get next upline (parent in base tree)
                next_upline = getattr(current_placement, 'upline_id', None) or getattr(current_placement, 'parent_id', None)
                
                if not next_upline:
                    return None
                
                current_id = next_upline
                steps_taken += 1
            
            return current_id
            
        except Exception as e:
            print(f"[BINARY_LEVEL_DIST] Error traversing upline upward: {e}")
            return None
    
    def _check_slot_activation(self, user_id: ObjectId, program: str, slot_no: int) -> bool:
        """
        Check if a user has activated a specific slot.
        Returns True if SlotActivation exists with program='binary', slot_no=slot_no, status='completed'.
        """
        try:
            from modules.slot.model import SlotActivation
            activation = SlotActivation.objects(
                user_id=user_id,
                program=program,
                slot_no=slot_no,
                status='completed'
            ).first()
            return activation is not None
        except Exception as e:
            print(f"[BINARY_LEVEL_DIST] Error checking slot activation for user {user_id}, slot {slot_no}: {e}")
            return False
    
    def _create_mother_account_income_event(
        self,
        source_id: str,
        program: str,
        slot_no: int,
        amount: Decimal,
        tx_hash: str,
        description: str,
        currency: str = 'BNB',
        missed_user_id: Optional[str] = None,
        from_user_id: Optional[str] = None,
        slot_name: Optional[str] = None,
        missed_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create income event for Mother Account when upline not found or slot not activated.
        Also credits Mother Account wallet and records missed profit if context is provided.
        """
        try:
            mother_account_id = ObjectId("000000000000000000000000")
            income_event = IncomeEvent(
                user_id=mother_account_id,
                source_user_id=ObjectId(source_id),
                program=program,
                slot_no=slot_no,
                income_type='level_payout',
                amount=amount,
                percentage=Decimal('0'),
                tx_hash=tx_hash,
                status='completed',
                description=description,
                created_at=datetime.utcnow()
            )
            income_event.save()

            wallet_credited = False
            wallet_error: Optional[str] = None
            try:
                from modules.wallet.service import WalletService
                wallet_service = WalletService()
                wallet_reason = f"{program}_mother_account_level_distribution"
                credit_result = wallet_service.credit_main_wallet(
                    user_id=str(mother_account_id),
                    amount=amount,
                    currency=currency,
                    reason=wallet_reason,
                    tx_hash=tx_hash
                )
                wallet_credited = credit_result.get("success", False)
            except Exception as e:
                wallet_error = str(e)
                print(f"[BINARY_LEVEL_DIST] Error crediting Mother Account wallet: {wallet_error}")

            response: Dict[str, Any] = {
                "success": True,
                "type": "mother_account_level_distribution",
                "recipient_id": str(mother_account_id),
                "source_id": source_id,
                "amount": float(amount),
                "wallet_credited": wallet_credited,
                "description": description
            }
            if wallet_error:
                response["error"] = wallet_error

            if missed_user_id and from_user_id:
                try:
                    from modules.commission.service import CommissionService
                    commission_service = CommissionService()
                    commission_service.handle_missed_profit(
                        user_id=str(missed_user_id),
                        from_user_id=str(from_user_id),
                        program=program,
                        slot_no=slot_no,
                        slot_name=slot_name or f"Slot {slot_no}",
                        amount=amount,
                        currency=currency,
                        reason=missed_reason or description
                    )
                    response["missed_profit_recorded"] = True
                except Exception as e:
                    print(f"[BINARY_LEVEL_DIST] Failed to record missed profit for user {missed_user_id}: {e}")
                    response["missed_profit_recorded"] = False
            else:
                response["missed_profit_recorded"] = False

            return response
        except Exception as e:
            print(f"[BINARY_LEVEL_DIST] Error creating Mother Account income event: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def _distribute_matrix_levels(self, user_id: str, amount: Decimal, percentage: Decimal,
                                 slot_no: int, tx_hash: str, currency: str = 'USDT') -> List[Dict[str, Any]]:
        """Distribute Matrix level distribution (40% treated as 100%)"""
        distributions = []
        level_amount = amount * (percentage / Decimal('100.0'))
        
        # Get user's tree upline for level distribution
        user_placement = TreePlacement.objects(user_id=ObjectId(user_id), program='matrix', is_active=True).first()
        if not user_placement:
            return distributions
        
        # Distribute to each level according to breakdown
        for level, level_percentage in self.matrix_level_breakdown.items():
            level_dist_amount = level_amount * (level_percentage / Decimal('100.0'))
            if level_dist_amount > 0:
                # Find upline at this level
                upline_id = self._find_upline_at_level(user_id, level, 'matrix', slot_no)
                if upline_id:
                    distribution = self._create_income_event(
                        upline_id, user_id, 'matrix', slot_no, f'level_{level}_distribution',
                        level_dist_amount, level_percentage, tx_hash, f"Matrix Level {level} Distribution", currency
                    )
                    distributions.append(distribution)
        
        return distributions

    def _find_upline_at_level(self, user_id: str, target_level: int, program: str, slot_no: int) -> Optional[str]:
        """Find upline at specific level for level distribution by traversing parent chain for the given slot."""
        try:
            # Start from the user's placement for this program+slot
            user_placement = TreePlacement.objects(user_id=ObjectId(user_id), program=program, slot_no=slot_no, is_active=True).first()
            if not user_placement:
                return None

            # Traverse up via parent_id pointers
            steps = 0
            curr = user_placement
            while steps < target_level and curr and getattr(curr, 'parent_id', None):
                parent_id = curr.parent_id
                # Fetch parent's placement for the same slot
                curr = TreePlacement.objects(user_id=parent_id, program=program, slot_no=slot_no, is_active=True).first()
                steps += 1

            if steps == target_level and curr:
                return str(curr.user_id)

            return None
            
        except Exception as e:
            print(f"Error finding upline at level {target_level}: {e}")
            return None

    def _map_income_type_to_fund_type(self, income_type: str) -> str:
        """Map income_type to BonusFund fund_type"""
        mapping = {
            'spark_bonus': 'spark_bonus',
            'royal_captain': 'royal_captain',
            'president_reward': 'president_reward',
            'leadership_stipend': 'leadership_stipend',
            'jackpot': 'jackpot_entry',
            'partner_incentive': 'partner_incentive',
            'shareholders': 'shareholders',
            'newcomer_support': 'newcomer_support',
            'newcomer_support_upline_fund': 'newcomer_support',
            'mentorship': 'mentorship_bonus',
            'triple_entry': 'triple_entry',
            'global_phase_1': None,  # Handled separately (tree upline reserve)
            'global_phase_2': None   # Handled separately (tree upline wallet)
        }
        return mapping.get(income_type)
    
    def _create_income_event(self, recipient_id: str, source_id: str, program: str, 
                           slot_no: int, income_type: str, amount: Decimal, 
                           percentage: Decimal, tx_hash: str, description: str, currency: str = 'USDT') -> Dict[str, Any]:
        """Create income event for distribution AND update BonusFund AND credit wallet"""
        try:
            # 1. Create IncomeEvent (for tracking/history)
            income_event = IncomeEvent(
                user_id=ObjectId(recipient_id),
                source_user_id=ObjectId(source_id),
                program=program,
                slot_no=slot_no,
                income_type=income_type,
                amount=amount,
                percentage=percentage,
                tx_hash=tx_hash,
                status='completed',
                description=description,
                created_at=datetime.utcnow()
            )
            income_event.save()
            
            # 2. Update BonusFund (for actual fund balance)
            fund_type = self._map_income_type_to_fund_type(income_type)
            fund_updated = False
            
            # Skip level distribution (level_1_distribution, level_2_distribution, etc.)
            is_level_dist = 'level_' in income_type and '_distribution' in income_type
            
            # Partner incentive, level distributions, and level_payout should credit wallet
            should_credit_wallet = (income_type == 'partner_incentive' or is_level_dist or income_type == 'level_payout')
            
            # Debug logging
            # level_payout is valid - it goes directly to wallet, not BonusFund
            # Skip warning for level_payout and level distributions
            if not fund_type and income_type not in ['global_phase_1', 'global_phase_2', 'level_payout']:
                print(f"⚠️ No mapping for income_type: {income_type}")
            elif is_level_dist or income_type == 'level_payout':
                pass  # Don't log level dist/payout skips (these go to wallet directly)
            
            if fund_type and not is_level_dist:
                try:
                    if fund_type == 'spark_bonus':
                        from modules.spark.service import SparkService

                        spark_service = SparkService()
                        spark_result = spark_service.contribute_to_spark_fund(
                            amount=amount,
                            program=program,
                            slot_number=slot_no,
                            user_id=recipient_id,
                            currency=currency,
                        )
                        fund_updated = spark_result.get("success", False)
                        if not fund_updated:
                            print(f"❌ Failed to update Spark Bonus fund via service: {spark_result.get('error')}")
                        else:
                            print(f"✅ Updated spark_bonus_{program}: +${spark_result.get('spark_contribution_8_percent')} → ${spark_result.get('new_balance')}")
                    else:
                        from modules.income.bonus_fund import BonusFund
                        
                        # Get or create BonusFund
                        bonus_fund = BonusFund.objects(
                            fund_type=fund_type,
                            program=program,
                            status='active'
                        ).first()
                        
                        if not bonus_fund:
                            print(f"Creating new BonusFund: {fund_type}_{program}")
                            bonus_fund = BonusFund(
                                fund_type=fund_type,
                                program=program,
                                total_collected=Decimal('0'),
                                total_distributed=Decimal('0'),
                                current_balance=Decimal('0'),
                                status='active'
                            )
                        
                        # Update fund balances
                        bonus_fund.total_collected += amount
                        bonus_fund.current_balance += amount
                        bonus_fund.updated_at = datetime.utcnow()
                        bonus_fund.save()
                        fund_updated = True
                        print(f"✅ Updated {fund_type}_{program}: +${amount} → ${bonus_fund.current_balance}")
                    
                except Exception as e:
                    print(f"❌ Failed to update BonusFund for {income_type} → {fund_type}: {e}")
            
            # 3. Credit wallet for partner_incentive and level distributions
            wallet_credited = False
            if should_credit_wallet and amount > 0:
                try:
                    from modules.wallet.service import WalletService
                    
                    # Create a proper reason for WalletLedger
                    if income_type == 'partner_incentive':
                        wallet_reason = f"{program}_partner_incentive"
                    elif is_level_dist:
                        # Extract level number from income_type (e.g., 'level_1_distribution' -> 'level_1')
                        level_part = income_type.replace('_distribution', '')
                        wallet_reason = f"{program}_dual_tree_{level_part}"
                    elif income_type == 'level_payout':
                        wallet_reason = f"{program}_level_payout"
                    else:
                        wallet_reason = f"{program}_{income_type}"
                    
                    wallet_service = WalletService()
                    credit_result = wallet_service.credit_main_wallet(
                        user_id=recipient_id,
                        amount=amount,
                        currency=currency,
                        reason=wallet_reason,
                        tx_hash=tx_hash
                    )
                    
                    if credit_result.get("success"):
                        wallet_credited = True
                        print(f"✅ Credited wallet for {recipient_id}: +{amount} {currency} ({wallet_reason})")
                    else:
                        print(f"⚠️ Wallet credit failed for {recipient_id}: {credit_result.get('error')}")
                        
                except Exception as e:
                    print(f"❌ Failed to credit wallet for {income_type}: {e}")
            
            return {
                "income_type": income_type,
                "amount": amount,
                "percentage": percentage,
                "recipient_id": recipient_id,
                "status": "completed",
                "description": description,
                "bonus_fund_updated": fund_updated,
                "wallet_credited": wallet_credited
            }
            
        except Exception as e:
            return {
                "income_type": income_type,
                "amount": amount,
                "percentage": percentage,
                "recipient_id": recipient_id,
                "status": "failed",
                "error": str(e)
            }

    def get_distribution_summary(self, program: str) -> Dict[str, Any]:
        """Get distribution summary for a program"""
        try:
            if program == 'binary':
                percentages = self.binary_percentages
                level_breakdown = self.binary_level_breakdown
            elif program == 'matrix':
                percentages = self.matrix_percentages
                level_breakdown = self.matrix_level_breakdown
            elif program == 'global':
                percentages = self.global_percentages
                level_breakdown = {}
            else:
                return {"success": False, "error": "Invalid program"}
            
            return {
                "success": True,
                "program": program,
                "percentages": {k: float(v) for k, v in percentages.items()},
                "level_breakdown": {k: float(v) for k, v in level_breakdown.items()},
                "total_percentage": float(sum(percentages.values()))
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get distribution summary: {str(e)}"}

    def validate_distribution_percentages(self, program: str) -> Dict[str, Any]:
        """Validate that all percentages add up to 100%"""
        try:
            if program == 'binary':
                percentages = self.binary_percentages
            elif program == 'matrix':
                percentages = self.matrix_percentages
            elif program == 'global':
                percentages = self.global_percentages
            else:
                return {"success": False, "error": "Invalid program"}
            
            total = sum(percentages.values())
            is_valid = total == Decimal('100.0')
            
            return {
                "success": True,
                "program": program,
                "total_percentage": float(total),
                "is_valid": is_valid,
                "validation_message": "Valid" if is_valid else f"Total should be 100%, got {float(total)}%"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Validation failed: {str(e)}"}
