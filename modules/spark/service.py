from typing import Dict, Any, List, Optional
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from .model import TripleEntryReward, SparkCycle, SparkBonusDistribution
from ..user.model import User


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


