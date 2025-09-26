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
        # Find the earliest Global participant whose PHASE-1 has < 4 children
        candidates = GlobalPhaseProgression.objects(is_active=True).order_by('created_at')
        for status in candidates:
            # Ensure candidate is in PHASE-1 or at least accepts Phase-1 seats initially
            if status.current_phase not in ['PHASE-1', None]:
                continue
            pid = status.user_id
            if self._count_phase_children(pid, 'PHASE-1') < 4:
                return pid
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
        try:
            user_oid = ObjectId(user_id)
            # If this is the first Global user, place as root
            any_global = GlobalPhaseProgression.objects().first()
            parent_id = None
            if any_global:
                parent_id = self._find_phase1_parent_bfs()
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
            # Create placement
            TreePlacement(
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
            ).save()
            # Update parent's counters and readiness
            if parent_id:
                parent_status = GlobalPhaseProgression.objects(user_id=parent_id).first()
                if parent_status:
                    parent_status.phase_1_members_current = int(parent_status.phase_1_members_current or 0) + 1
                    if parent_status.phase_1_members_current >= (parent_status.phase_1_members_required or 4):
                        parent_status.is_phase_complete = True
                        parent_status.next_phase_ready = True
                        parent_status.phase_completed_at = datetime.utcnow()
                    parent_status.last_updated = datetime.utcnow()
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
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # Expect Phase-1 Slot-1 price from catalog
            catalog = SlotCatalog.objects(program='global', slot_no=1, is_active=True).first()
            if not catalog:
                return {"success": False, "error": "Global slot catalog missing"}
            expected_amount = catalog.price or Decimal('0')
            if amount != expected_amount:
                return {"success": False, "error": f"Join amount must be {expected_amount}"}

            currency = ensure_currency_for_program('global', 'USD')
            
            # Generate unique tx_hash to avoid duplicate key errors
            import random, string
            unique_suffix = datetime.utcnow().strftime('%Y%m%d%H%M%S%f') + '_' + ''.join(random.choices(string.ascii_lowercase+string.digits, k=6))
            unique_tx_hash = f"{tx_hash}_{unique_suffix}"

            # Record activation
            activation = SlotActivation(
                user_id=ObjectId(user.id),
                program='global',
                slot_no=1,
                slot_name=catalog.name,
                activation_type='initial',
                upgrade_source='wallet',
                amount_paid=expected_amount,
                currency=currency,
                tx_hash=unique_tx_hash,
                is_auto_upgrade=False,
                status='completed'
            )
            activation.save()

            # Seed GlobalPhaseProgression if not exists
            if not GlobalPhaseProgression.objects(user_id=ObjectId(user.id)).first():
                GlobalPhaseProgression(
                    user_id=ObjectId(user.id),
                    current_phase='PHASE-1',
                    current_slot_no=1,
                    phase_position=1,
                    phase_1_members_required=4,
                    phase_1_members_current=0,
                    phase_2_members_required=8,
                    phase_2_members_current=0,
                    global_team_size=0,
                    global_team_members=[],
                    is_phase_complete=False,
                    next_phase_ready=False,
                    auto_progression_enabled=True,
                    progression_triggered=False,
                    is_active=True
                ).save()

            # Phase-1 BFS seat placement
            self._place_in_phase1(user_id)

            # Joining commission 10%
            self.commission_service.calculate_joining_commission(
                from_user_id=str(user.id),
                program='global',
                amount=expected_amount,
                currency=currency
            )

            # Partner incentive 10% to direct upline (Global)
            try:
                self.commission_service.calculate_partner_incentive(
                    from_user_id=str(user.id),
                    program='global',
                    amount=expected_amount,
                    currency=currency
                )
            except Exception:
                pass

            # Global distribution (40/30/15/15/5/5)
            self.process_distribution(user_id=str(user.id), amount=expected_amount, currency=currency)

            # Triple Entry Eligibility Check (Section 1.1.7)
            # If user has Binary + Matrix + Global: Compute triple-entry eligibles
            try:
                if getattr(user, 'binary_joined', False) and getattr(user, 'matrix_joined', False) and getattr(user, 'global_joined', False):
                    SparkService.compute_triple_entry_eligibles(datetime.utcnow())
            except Exception:
                pass

            # Earning history
            EarningHistory(
                user_id=ObjectId(user.id),
                earning_type='global_slot',
                program='global',
                amount=float(expected_amount),
                currency=currency,
                slot_name=catalog.name,
                slot_level=catalog.level,
                description='Joined Global program, activated Phase-1 Slot-1'
            ).save()

            return {"success": True, "slot_no": 1, "amount": float(expected_amount)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def upgrade_global_slot(self, user_id: str, to_slot_no: int, tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        """Upgrade Global program slot (2..16) with 10% partner incentive and distribution."""
        try:
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}

            catalog = SlotCatalog.objects(program='global', slot_no=to_slot_no, is_active=True).first()
            if not catalog:
                return {"success": False, "error": "Global slot catalog missing"}
            expected_amount = catalog.price or Decimal('0')
            if amount != expected_amount:
                return {"success": False, "error": f"Upgrade amount must be {expected_amount}"}

            currency = ensure_currency_for_program('global', 'USD')
            
            # Generate unique tx_hash to avoid duplicate key errors
            import random, string
            unique_suffix = datetime.utcnow().strftime('%Y%m%d%H%M%S%f') + '_' + ''.join(random.choices(string.ascii_lowercase+string.digits, k=6))
            unique_tx_hash = f"{tx_hash}_{unique_suffix}"

            activation = SlotActivation(
                user_id=ObjectId(user.id),
                program='global',
                slot_no=to_slot_no,
                slot_name=catalog.name,
                activation_type='upgrade',
                upgrade_source='wallet',
                amount_paid=expected_amount,
                currency=currency,
                tx_hash=unique_tx_hash,
                is_auto_upgrade=False,
                status='completed'
            )
            activation.save()

            # Partner incentive on upgrade (10%)
            try:
                self.commission_service.calculate_partner_incentive(
                    from_user_id=str(user.id),
                    program='global',
                    amount=expected_amount,
                    currency=currency
                )
            except Exception:
                pass

            # Global distribution per spec
            self.process_distribution(user_id=str(user.id), amount=expected_amount, currency=currency)

            # Earning history
            EarningHistory(
                user_id=ObjectId(user.id),
                earning_type='global_slot',
                program='global',
                amount=float(expected_amount),
                currency=currency,
                slot_name=catalog.name,
                slot_level=catalog.level,
                description=f'Global slot upgraded to {to_slot_no}'
            ).save()

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
