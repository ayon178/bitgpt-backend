from typing import Dict, Any, List, Optional
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from .model import TripleEntryReward, SparkCycle, SparkBonusDistribution
from ..user.model import User
import os


class SparkService:
    """Business logic for Spark/Triple Entry Reward"""

    @staticmethod
    def compute_triple_entry_eligibles(target_date: datetime) -> Dict[str, Any]:
        """Find users who joined all three programs (binary, matrix, global) on the same calendar day.
        Assumption: We infer join by checking the first active slot activation timestamps embedded in user.
        Fallback: use User.created_at for baseline if slot timestamps are missing.
        """
        try:
            # Normalize to date boundaries UTC
            day_start = datetime(target_date.year, target_date.month, target_date.day)
            day_end = day_start + timedelta(days=1)

            # Query users who have joined flags set for all three programs
            users = User.objects(
                binary_joined=True,
                matrix_joined=True,
                global_joined=True,
                created_at__gte=day_start,
                created_at__lt=day_end
            ).only('id')

            eligible_ids: List[ObjectId] = [u.id for u in users]

            # Create/update a TER record for that cycle (use yyyymmdd as cycle_no)
            cycle_no = int(target_date.strftime('%Y%m%d'))
            ter = TripleEntryReward.objects(cycle_no=cycle_no).first()
            if not ter:
                ter = TripleEntryReward(
                    cycle_no=cycle_no,
                    pool_amount=0,
                    eligible_users=[],
                    distribution_amount=0,
                    status='active'
                )
            ter.eligible_users = eligible_ids
            ter.save()

            return {
                "success": True,
                "cycle_no": cycle_no,
                "eligible_user_count": len(eligible_ids),
                "eligible_users": [str(_id) for _id in eligible_ids]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def contribute_to_fund(self, amount: float, source: str = "matrix", metadata: Dict[str, Any] | None = None, program: str | None = None, **kwargs) -> Dict[str, Any]:
        """Record contribution to Spark fund and distribute to Triple Entry (18%) and Top Leaders Gift (2%).
        Matrix distribution gets remaining 80%.
        """
        try:
            contributed = float(amount) if amount is not None else 0.0
            
            # Deduct 2% for Top Leaders Gift Fund
            top_leaders_amount = contributed * 0.02
            
            # Contribute to Top Leaders Gift Fund
            try:
                from modules.top_leader_gift.payment_model import TopLeadersGiftFund
                fund = TopLeadersGiftFund.objects(is_active=True).first()
                if not fund:
                    fund = TopLeadersGiftFund()
                
                # Determine currency from program/source
                currency = kwargs.get('currency', 'USDT')
                if currency == 'BNB' or program == 'binary':
                    fund.total_fund_bnb += top_leaders_amount
                    fund.available_bnb += top_leaders_amount
                else:
                    fund.total_fund_usdt += top_leaders_amount
                    fund.available_usdt += top_leaders_amount
                
                fund.last_updated = datetime.utcnow()
                fund.save()
            except Exception as e:
                print(f"Failed to contribute to Top Leaders Gift Fund: {str(e)}")
            
            return {
                "success": True,
                "contributed": contributed,
                "top_leaders_gift_contribution": top_leaders_amount,
                "remaining_for_distribution": contributed - top_leaders_amount,
                "source": source,
                "program": program or source,
                "metadata": metadata or {},
                "extra": {k: v for k, v in (kwargs or {}).items()}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------ Fund Info & Slot Breakdown ------------------
    def get_spark_bonus_fund_info(self) -> Dict[str, Any]:
        """Return Spark Bonus fund totals.
        For stability, read from env `SPARK_POOL_TOTAL_USDT` (default 1000) instead of
        inferring from distribution history. Values are in USDT.
        """
        try:
            import os
            total_env = os.getenv('SPARK_POOL_TOTAL_USDT', '1000')
            total = float(total_env) if total_env else 1000.0
            return {
                "success": True,
                "currency": "USDT",
                "total_fund_amount": total,
                "available_amount": total,
                "updated_at": datetime.utcnow(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_slot_breakdown(self, currency: str = "USDT", user_id: str | None = None, slot_number: int | None = None) -> Dict[str, Any]:
        """Compute slot-wise Spark fund breakdown for UI display.
        - Uses 80% of the total Spark fund as baseline per documentation
        - Distributes across slots 1-14 by documented percentages
        - Returns both per-slot allocation and summary totals
        - Always returns BOTH currencies (USDT and BNB) in a "funds" object
        """
        info = self.get_spark_bonus_fund_info()
        if not info.get("success"):
            return {"success": False, "error": info.get("error", "Fund info not available")}

        total_usdt = Decimal(str(info.get("available_amount", 0)))
        baseline_usdt = (total_usdt * Decimal('0.80'))

        slots_usdt: List[Dict[str, Any]] = []
        total_allocated = Decimal('0')
        slot_range = range(1, 15) if slot_number is None else [int(slot_number)]

        # Determine user's eligible matrix slots (1-14) based on completed activations
        eligible_slots: List[int] = []
        if user_id:
            try:
                from modules.slot.model import SlotActivation  # lazy import
                from modules.matrix.model import MatrixActivation as _MA
                slots_a = [
                    int(sa.slot_no) for sa in SlotActivation.objects(
                        user_id=ObjectId(user_id),
                        program='matrix',
                        status='completed',
                        slot_no__gte=1,
                        slot_no__lte=14
                    ).only('slot_no')
                ]
                slots_b = [
                    int(ma.slot_no) for ma in _MA.objects(
                        user_id=ObjectId(user_id)
                    ).only('slot_no')
                ]
                eligible_slots = sorted(list(set(slots_a + slots_b)))
            except Exception:
                eligible_slots = []
        for slot_no in slot_range:
            pct = self._slot_percentage(slot_no)
            alloc = (baseline_usdt * pct / Decimal('100')) if pct > 0 else Decimal('0')
            total_allocated += alloc
            slots_usdt.append({
                "slot_number": slot_no,
                "percentage": float(pct),
                "allocated_amount": float(alloc),  # USDT value
                "user_eligible": (slot_no in eligible_slots) if user_id else None,
            })

        # Eligibility: Triple Entry for this user (joined all three)
        is_user_eligible = False
        if user_id:
            try:
                u = User.objects(id=ObjectId(user_id)).first()
                is_user_eligible = bool(u and u.binary_joined and u.matrix_joined and u.global_joined)
            except Exception:
                is_user_eligible = False

        # Build BOTH currencies views
        try:
            rate = Decimal(os.getenv('SPARK_USDT_PER_BNB', '300'))
            if rate <= 0:
                rate = Decimal('300')
        except Exception:
            rate = Decimal('300')

        def usdt_to_bnb(val: Decimal | float) -> float:
            d = Decimal(str(val))
            return float((d / rate).quantize(Decimal('0.00000001')))

        # Build a unified slots array with both currencies per slot, adjusted by claim ledger
        slots_combined: List[Dict[str, Any]] = []
        # Fetch per-slot deductions
        try:
            from modules.spark.model import SparkSlotClaimLedger as _SSCL
            from datetime import datetime as _DT
            day_start = _DT.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            ledgers = list(_SSCL.objects(created_at__gte=day_start))
        except Exception:
            ledgers = []
        def deducted(slot_no: int, curr: str, base: float) -> float:
            try:
                from decimal import Decimal as _D
                total = _D('0')
                for l in ledgers:
                    if int(getattr(l, 'slot_number', 0)) == int(slot_no) and str(getattr(l, 'currency','')).upper() == curr:
                        total += _D(str(getattr(l, 'amount', 0) or 0))
                val = _D(str(base)) - total
                return float(max(_D('0'), val))
            except Exception:
                return base
        for s in slots_usdt:
            slots_combined.append({
                "slot_number": s["slot_number"],
                "percentage": s["percentage"],
                "allocated_amount_usdt": deducted(s["slot_number"], 'USDT', s["allocated_amount"]),
                "allocated_amount_bnb": deducted(s["slot_number"], 'BNB', usdt_to_bnb(s["allocated_amount"])) ,
                "user_eligible": s.get("user_eligible"),
            })

        funds = {
            "USDT": {
                "total_fund_amount": float(total_usdt),
                "baseline_amount": float(baseline_usdt),
                "total_allocated": float(total_allocated),
                "unallocated": float(max(Decimal('0'), baseline_usdt - total_allocated)),
            },
            "BNB": {
                "total_fund_amount": usdt_to_bnb(total_usdt),
                "baseline_amount": usdt_to_bnb(baseline_usdt),
                "total_allocated": usdt_to_bnb(total_allocated),
                "unallocated": usdt_to_bnb(max(Decimal('0'), baseline_usdt - total_allocated)),
            }
        }

        return {
            "success": True,
            "funds": funds,
            "slots": slots_combined,
            "user": {
                "user_id": user_id,
                "is_triple_entry_eligible": is_user_eligible,
                "eligible_slots": eligible_slots
            } if user_id else None,
            # Backward-compat single-currency view (defaults to requested or USDT)
            "currency": (currency or "USDT").upper(),
            "total_fund_amount": funds.get((currency or "USDT").upper(), {}).get("total_fund_amount"),
            "baseline_amount": funds.get((currency or "USDT").upper(), {}).get("baseline_amount"),
            "total_allocated": funds.get((currency or "USDT").upper(), {}).get("total_allocated"),
            "unallocated": funds.get((currency or "USDT").upper(), {}).get("unallocated"),
        }

    # ------------------ Claim Processing ------------------
    def get_slot_eligible_user_ids(self, slot_no: int) -> List[str]:
        """Return user ids eligible for Spark Bonus for a given Matrix slot.
        Eligibility = any of:
          - SlotActivation(program='matrix', slot_no, status='completed')
          - MatrixActivation(slot_no)
        """
        try:
            from modules.slot.model import SlotActivation
            from modules.matrix.model import MatrixActivation as _MA
            from bson import ObjectId
            ids1 = [str(a.user_id) for a in SlotActivation.objects(program='matrix', slot_no=slot_no, status='completed').only('user_id')]
            ids2 = [str(a.user_id) for a in _MA.objects(slot_no=slot_no).only('user_id')]
            return sorted(list(set(ids1 + ids2)))
        except Exception:
            return []

    def claim_spark_bonus(self, slot_no: int, currency: str = 'USDT', claimer_user_id: str | None = None) -> Dict[str, Any]:
        """Distribute the allocated fund for a slot equally among eligible users and credit wallets.
        - currency: 'USDT' or 'BNB'
        - uses current slot breakdown to get allocated amount per slot
        """
        try:
            currency = (currency or 'USDT').upper()
            if currency not in ('USDT', 'BNB'):
                return {"success": False, "error": "Invalid currency"}

            # Get allocated amount for this slot (exact, not per-day fraction)
            br = self.get_slot_breakdown('USDT')  # baseline in USDT
            slots = br.get('slots', [])
            alloc_usdt = 0.0
            for s in slots:
                if int(s.get('slot_number')) == int(slot_no):
                    alloc_usdt = float(s.get('allocated_amount_usdt') or 0.0)
                    break
            if alloc_usdt <= 0:
                return {"success": False, "error": "No allocated fund for this slot"}

            # Get eligible users
            user_ids = self.get_slot_eligible_user_ids(slot_no)
            if not user_ids:
                return {"success": False, "error": "No eligible users for this slot"}

            # If claimer is provided, enforce they are eligible
            if claimer_user_id and claimer_user_id not in user_ids:
                return {"success": False, "error": "Claimer is not eligible for this slot"}

            # Idempotency: prevent duplicate claim for this claimer+slot+currency per day
            try:
                from datetime import datetime as _DT
                from modules.spark.model import SparkBonusDistribution as _SBD
                if claimer_user_id:
                    day_start = _DT.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                    dup = _SBD.objects(user_id=ObjectId(claimer_user_id), slot_number=slot_no, currency=currency, created_at__gte=day_start).first()
                    if dup:
                        return {"success": False, "error": "Already claimed for this slot today"}
            except Exception:
                pass

            from decimal import Decimal as _D
            # Full slot allocation divided by the number of eligible users
            per_user_usdt = (_D(str(alloc_usdt)) / _D(str(len(user_ids)))).quantize(_D('0.00000001'))

            # Convert if needed
            import os
            rate = _D(os.getenv('SPARK_USDT_PER_BNB', '300') or '300')
            if rate <= 0:
                rate = _D('300')
            if currency == 'BNB':
                per_user_amount = (per_user_usdt / rate).quantize(_D('0.00000001'))
            else:
                per_user_amount = per_user_usdt

            # Credit wallets and record distribution history
            from modules.wallet.service import WalletService
            from modules.spark.model import SparkBonusDistribution, SparkSlotClaimLedger
            ws = WalletService()
            credited = []
            for uid in user_ids:
                r = ws.credit_main_wallet(uid, per_user_amount, currency, 'spark_bonus_distribution', f'SPARK-{slot_no}-{currency}')
                # Save history
                try:
                    SparkBonusDistribution(
                        user_id=ObjectId(uid),
                        slot_number=int(slot_no),
                        distribution_amount=per_user_amount,
                        currency=currency,
                        fund_source='spark_bonus',
                        distribution_percentage=self._slot_percentage(slot_no),
                        total_fund_amount=_D(str(alloc_usdt)),
                        matrix_slot_name='',
                        matrix_slot_level=int(slot_no),
                        status='completed',
                        distributed_at=_DT.utcnow(),
                        wallet_credit_tx_hash=f'SPARK-{slot_no}-{currency}',
                        wallet_credit_status='completed',
                    ).save()
                except Exception:
                    pass
                credited.append({"user_id": uid, "amount": float(per_user_amount), "currency": currency, "result": r})

            # Write one ledger row reducing the visible allocated amount for this slot
            try:
                SparkSlotClaimLedger(slot_number=int(slot_no), currency=currency, amount=per_user_amount * len(user_ids)).save()
            except Exception:
                pass

            return {
                "success": True,
                "slot_no": slot_no,
                "currency": currency,
                "eligible_users": len(user_ids),
                "per_user_amount": float(per_user_amount),
                "total_distributed": float(per_user_amount) * len(user_ids),
                "details": credited,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _slot_percentage(slot_no: int) -> Decimal:
        """Return Spark Bonus distribution percentage for Matrix slot (treated as 100% baseline of Spark pool).
        Per docs: 1:15, 2-5:10, 6:7, 7-9:6, 10-14:4
        """
        if slot_no == 1:
            return Decimal('15')
        if 2 <= slot_no <= 5:
            return Decimal('10')
        if slot_no == 6:
            return Decimal('7')
        if 7 <= slot_no <= 9:
            return Decimal('6')
        if 10 <= slot_no <= 14:
            return Decimal('4')
        return Decimal('0')

    def distribute_spark_for_slot(self, cycle_no: int, slot_no: int, total_spark_pool: Decimal, participant_user_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Distribute Spark Bonus for a given cycle and matrix slot.
        - total_spark_pool: Decimal amount representing 80% Spark pool baseline (treated as 100%).
        - participant_user_ids: optional list of user ids; if None, no-op distribution.
        """
        try:
            pct = self._slot_percentage(slot_no)
            if pct <= 0:
                return {"success": False, "error": "Invalid slot number for Spark distribution"}
            if not participant_user_ids:
                return {"success": True, "cycle_no": cycle_no, "slot_no": slot_no, "participants": 0, "payout_per_participant": str(Decimal('0'))}

            slot_pool = (total_spark_pool * pct) / Decimal('100')
            count = len(participant_user_ids)
            if count == 0:
                return {"success": True, "cycle_no": cycle_no, "slot_no": slot_no, "participants": 0, "payout_per_participant": str(Decimal('0'))}
            payout_each = (slot_pool / Decimal(count)).quantize(Decimal('0.00000001'))

            # Create SparkCycle record
            cycle = SparkCycle(
                cycle_no=cycle_no,
                slot_no=slot_no,
                pool_amount=slot_pool,
                participants=[ObjectId(uid) for uid in participant_user_ids],
                distribution_percentage=pct,
                payout_per_participant=payout_each,
                status='completed',
                payout_at=datetime.utcnow()
            )
            cycle.save()

            # Create distributions
            total_fund_amount = total_spark_pool
            for uid in participant_user_ids:
                SparkBonusDistribution(
                    user_id=ObjectId(uid),
                    slot_number=slot_no,
                    distribution_amount=payout_each,
                    currency='USDT',
                    fund_source='spark_bonus',
                    distribution_percentage=pct,
                    total_fund_amount=total_fund_amount,
                    matrix_slot_name='',
                    matrix_slot_level=slot_no,
                    status='completed',
                    distributed_at=datetime.utcnow()
                ).save()

            return {
                "success": True,
                "cycle_no": cycle_no,
                "slot_no": slot_no,
                "participants": count,
                "slot_percentage": str(pct),
                "payout_per_participant": str(payout_each)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


