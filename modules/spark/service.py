from typing import Dict, Any, List
from bson import ObjectId
from datetime import datetime, timedelta
from .model import TripleEntryReward
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


