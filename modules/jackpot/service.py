from typing import Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
import random
from .model import JackpotTicket, JackpotFund
from modules.user.model import User


def current_week_id() -> str:
    now = datetime.utcnow()
    return f"{now.isocalendar().year}-{now.isocalendar().week:02d}"


class JackpotService:
    """Handles jackpot entries and free coupon awards."""

    @staticmethod
    def create_entry(user_id: str, source: str, referrer_user_id: Optional[str] = None, free_source_slot: Optional[int] = None) -> Dict[str, Any]:
        try:
            # Resolve referrer if not provided
            if not referrer_user_id:
                user = User.objects(id=ObjectId(user_id)).first()
                if user and user.refered_by:
                    referrer_user_id = str(user.refered_by)
                else:
                    return {"success": False, "error": "Referrer not found for jackpot entry"}

            ticket = JackpotTicket(
                user_id=ObjectId(user_id),
                referrer_user_id=ObjectId(referrer_user_id),
                week_id=current_week_id(),
                source=source,
                free_source_slot=free_source_slot,
                status='active'
            )
            ticket.save()
            return {"success": True, "ticket_id": str(ticket.id)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def award_free_coupon_for_binary_slot(user_id: str, slot_no: int) -> None:
        """Award free jackpot coupons based on binary slot upgrades.
        Per docs: Slot 5 => 1, Slot 6 => 2, ... up to Slot 16 (progressive). Here we implement:
        - Slot 5: 1 entry, Slot 6: 2 entries, and from 7..16: (slot_no - 4) entries.
        """
        if slot_no < 5:
            return
        entries = max(1, slot_no - 4)
        user = User.objects(id=ObjectId(user_id)).first()
        referrer = str(user.refered_by) if user and user.refered_by else None
        for _ in range(entries):
            JackpotService.create_entry(user_id=user_id, source='free', referrer_user_id=referrer, free_source_slot=slot_no)

    @staticmethod
    def compute_top_sellers(week_id: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Compute top sellers for a given week: referrers whose referred users bought the most tickets.
        We count tickets grouped by referrer_user_id among PAID tickets in the week.
        """
        try:
            wid = week_id or current_week_id()
            pipeline = [
                {"$match": {"week_id": wid, "source": "paid"}},
                {"$group": {"_id": "$referrer_user_id", "ticket_count": {"$sum": 1}}},
                {"$sort": {"ticket_count": -1}},
                {"$limit": int(limit)}
            ]
            # Using MongoEngine's aggregate via underlying collection
            coll = JackpotTicket._get_collection()
            result = list(coll.aggregate(pipeline))
            # Persist into JackpotFund.winners.top_sellers
            fund = JackpotFund.objects(week_id=wid).first()
            if not fund:
                fund = JackpotFund(
                    week_id=wid,
                    total_pool=Decimal('0'),
                    open_winners_pool=Decimal('0'),
                    seller_pool=Decimal('0'),
                    buyer_pool=Decimal('0'),
                    newcomer_pool=Decimal('0'),
                    winners={'open': [], 'top_sellers': [], 'top_buyers': [], 'newcomers': []}
                )
            fund.winners['top_sellers'] = [
                {"referrer_user_id": str(item.get("_id")), "tickets": int(item.get("ticket_count", 0))}
                for item in result
            ]
            fund.save()
            return {"success": True, "week_id": wid, "top_sellers": fund.winners['top_sellers']}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def compute_top_buyers_all_time(limit: int = 10) -> Dict[str, Any]:
        """Compute all-time top buyers: users with most total tickets (paid + free)."""
        try:
            pipeline = [
                {"$group": {"_id": "$user_id", "ticket_count": {"$sum": 1}}},
                {"$sort": {"ticket_count": -1}},
                {"$limit": int(limit)}
            ]
            coll = JackpotTicket._get_collection()
            result = list(coll.aggregate(pipeline))
            top_buyers = [
                {"user_id": str(item.get("_id")), "tickets": int(item.get("ticket_count", 0))}
                for item in result
            ]
            # Optionally store a snapshot in SystemConfig or a dedicated stats collection; return for now
            return {"success": True, "top_buyers": top_buyers}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def compute_top_buyers(week_id: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Compute top buyers either for a given week (if week_id provided) or all-time otherwise."""
        try:
            match_stage = {}
            if week_id:
                match_stage["week_id"] = week_id
            pipeline = []
            if match_stage:
                pipeline.append({"$match": match_stage})
            pipeline.extend([
                {"$group": {"_id": "$user_id", "ticket_count": {"$sum": 1}}},
                {"$sort": {"ticket_count": -1}},
                {"$limit": int(limit)}
            ])
            coll = JackpotTicket._get_collection()
            result = list(coll.aggregate(pipeline))
            top_buyers = [
                {"user_id": str(item.get("_id")), "tickets": int(item.get("ticket_count", 0))}
                for item in result
            ]
            return {"success": True, "week_id": week_id, "top_buyers": top_buyers}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def pick_newcomers_for_week(week_id: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Pick random newcomers for the week (users who first joined that week and have a jackpot entry).
        Definition: Users whose account creation date falls within the week, and they have at least one JackpotTicket in that same week.
        """
        try:
            wid = week_id or current_week_id()
            # Compute week boundaries (UTC Monday..Sunday per ISO week)
            now = datetime.utcnow()
            year, week, _ = now.isocalendar()
            if week_id:
                parts = week_id.split('-')
                if len(parts) == 2:
                    year = int(parts[0])
                    week = int(parts[1])
            # First day of ISO week
            # Find Monday of the given ISO week
            # Build a date from year-week-1 (Monday)
            from datetime import date, timedelta
            d = date.fromisocalendar(year, week, 1)
            week_start = datetime(d.year, d.month, d.day)
            week_end = week_start + timedelta(days=7)

            # Users created within the week
            user_coll = User._get_collection()
            new_users = list(user_coll.find({
                "created_at": {"$gte": week_start, "$lt": week_end}
            }, {"_id": 1}))
            new_user_ids = {u["_id"] for u in new_users}

            if not new_user_ids:
                return {"success": True, "week_id": wid, "newcomers": []}

            # Those who also have at least one ticket in the same week
            ticket_coll = JackpotTicket._get_collection()
            cursor = ticket_coll.aggregate([
                {"$match": {"week_id": wid, "user_id": {"$in": list(new_user_ids)}}},
                {"$group": {"_id": "$user_id"}}
            ])
            eligible = [str(doc["_id"]) for doc in cursor]

            # Randomly pick up to limit users
            if not eligible:
                return {"success": True, "week_id": wid, "newcomers": []}
            winners = random.sample(eligible, k=min(limit, len(eligible)))

            # Persist in JackpotFund
            fund = JackpotFund.objects(week_id=wid).first()
            if not fund:
                fund = JackpotFund(
                    week_id=wid,
                    total_pool=Decimal('0'),
                    open_winners_pool=Decimal('0'),
                    seller_pool=Decimal('0'),
                    buyer_pool=Decimal('0'),
                    newcomer_pool=Decimal('0'),
                    winners={'open': [], 'top_sellers': [], 'top_buyers': [], 'newcomers': []}
                )
            fund.winners['newcomers'] = winners
            fund.save()
            return {"success": True, "week_id": wid, "newcomers": winners}
        except Exception as e:
            return {"success": False, "error": str(e)}


