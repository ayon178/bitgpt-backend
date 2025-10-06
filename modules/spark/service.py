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
        """Stub: Record a contribution into the Spark/Triple Entry fund.
        Accepts optional 'program' and arbitrary kwargs for compatibility.
        """
        try:
            contributed = float(amount) if amount is not None else 0.0
            return {
                "success": True,
                "contributed": contributed,
                "source": source,
                "program": program or source,
                "metadata": metadata or {},
                "extra": {k: v for k, v in (kwargs or {}).items()}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------ Fund Info & Slot Breakdown ------------------
    def get_spark_bonus_fund_info(self) -> Dict[str, Any]:
        """Return a best-effort snapshot of Spark Bonus fund.
        Since a dedicated fund ledger isn't persisted yet, we infer from the latest
        SparkBonusDistribution record's total_fund_amount field when available.
        Fallback to 0 if none exists.
        Values are expressed in USDT.
        """
        try:
            latest = SparkBonusDistribution.objects().order_by('-distributed_at', '-created_at').first()
            total = float(getattr(latest, 'total_fund_amount', 0.0) or 0.0)
            # Treat entire amount as available for display; real implementation should
            # subtract distributed/locked portions from a persistent Spark fund.
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

        # Build a unified slots array with both currencies per slot
        slots_combined: List[Dict[str, Any]] = []
        for s in slots_usdt:
            slots_combined.append({
                "slot_number": s["slot_number"],
                "percentage": s["percentage"],
                "allocated_amount_usdt": s["allocated_amount"],
                "allocated_amount_bnb": usdt_to_bnb(s["allocated_amount"]),
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


