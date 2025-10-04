from typing import Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
import random
from decimal import Decimal
from .model import JackpotTicket, JackpotFund
from modules.user.model import User
from modules.wallet.service import WalletService


def current_week_id() -> str:
    now = datetime.utcnow()
    return f"{now.isocalendar().year}-{now.isocalendar().week:02d}"


class JackpotService:
    """Handles jackpot entries and free coupon awards."""

    @staticmethod
    def process_paid_entry(user_id: str, amount: float, currency: str = "USDT") -> Dict[str, Any]:
        """Process paid Jackpot entry with $5 USDT payment and fund distribution"""
        try:
            # Get user and referrer info
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            referrer_user_id = str(user.refered_by) if user.refered_by else None
            if not referrer_user_id:
                return {"success": False, "error": "Referrer not found for jackpot entry"}
            
            # Deduct amount from wallet
            wallet_service = WalletService()
            deduction_result = wallet_service.debit_main_wallet(
                user_id=user_id,
                amount=Decimal(str(amount)),
                currency=currency,
                reason="jackpot_entry",
                tx_hash=f"jackpot_entry_{user_id}_{datetime.utcnow().timestamp()}"
            )
            
            if not deduction_result["success"]:
                return {"success": False, "error": f"Wallet deduction failed: {deduction_result['error']}"}
            
            # Create Jackpot ticket
            ticket_result = JackpotService.create_entry(
                user_id=user_id,
                source="paid",
                referrer_user_id=referrer_user_id
            )
            
            if not ticket_result["success"]:
                # Refund the wallet deduction if ticket creation fails
                wallet_service.credit_main_wallet(
                    user_id=user_id,
                    amount=Decimal(str(amount)),
                    currency=currency,
                    reason="jackpot_entry_refund",
                    tx_hash=f"jackpot_refund_{user_id}_{datetime.utcnow().timestamp()}"
                )
                return {"success": False, "error": f"Ticket creation failed: {ticket_result['error']}"}
            
            # Update Jackpot fund with proper distribution
            fund_result = JackpotService.update_jackpot_fund(amount, currency)
            
            if not fund_result["success"]:
                return {"success": False, "error": f"Fund update failed: {fund_result['error']}"}
            
            return {
                "success": True,
                "data": {
                    "ticket_id": ticket_result["ticket_id"],
                    "amount_paid": amount,
                    "currency": currency,
                    "week_id": current_week_id(),
                    "fund_distribution": fund_result["data"]["distribution"],
                    "transaction_id": f"jackpot_entry_{user_id}_{datetime.utcnow().timestamp()}"
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def update_jackpot_fund(amount: float, currency: str = "USDT") -> Dict[str, Any]:
        """Update Jackpot fund with proper distribution according to documentation"""
        try:
            week_id = current_week_id()
            
            # Get or create JackpotFund for current week
            fund = JackpotFund.objects(week_id=week_id).first()
            if not fund:
                fund = JackpotFund(
                    week_id=week_id,
                    total_pool=Decimal('0'),
                    open_winners_pool=Decimal('0'),
                    seller_pool=Decimal('0'),
                    buyer_pool=Decimal('0'),
                    newcomer_pool=Decimal('0'),
                    winners={'open': [], 'top_sellers': [], 'top_buyers': [], 'newcomers': []}
                )
            
            # Fund distribution according to documentation:
            # 50% Open Pool, 30% Top Direct Promoters, 10% Top Buyers, 10% System
            open_pool_amount = Decimal(str(amount * 0.50))      # 50%
            seller_pool_amount = Decimal(str(amount * 0.30))     # 30% 
            buyer_pool_amount = Decimal(str(amount * 0.10))      # 10%
            newcomer_pool_amount = Decimal(str(amount * 0.10))   # 10% (system/admin)
            
            # Update fund amounts
            fund.total_pool += Decimal(str(amount))
            fund.open_winners_pool += open_pool_amount
            fund.seller_pool += seller_pool_amount
            fund.buyer_pool += buyer_pool_amount
            fund.newcomer_pool += newcomer_pool_amount
            
            fund.save()
            
            return {
                "success": True,
                "data": {
                    "week_id": week_id,
                    "total_pool": float(fund.total_pool),
                    "distribution": {
                        "open_pool": float(fund.open_winners_pool),
                        "seller_pool": float(fund.seller_pool),
                        "buyer_pool": float(fund.buyer_pool),
                        "newcomer_pool": float(fund.newcomer_pool)
                    }
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

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
    def get_pools_total(currency: str = "USDT") -> Dict[str, Any]:
        """Get total accumulated amounts for all Jackpot pools"""
        try:
            # Get all JackpotFund records for the given currency
            funds = JackpotFund.objects().order_by('-created_at')
            
            # Initialize totals for all pools
            total_open_pool = Decimal('0')
            total_seller_pool = Decimal('0') 
            total_buyer_pool = Decimal('0')
            total_newcomer_pool = Decimal('0')
            total_overall = Decimal('0')
            
            # Sum up all funds from all weeks
            for fund in funds:
                total_open_pool += fund.open_winners_pool
                total_seller_pool += fund.seller_pool
                total_buyer_pool += fund.buyer_pool
                total_newcomer_pool += fund.newcomer_pool
                total_overall += fund.total_pool
            
            return {
                "success": True,
                "data": {
                    "currency": currency.upper(),
                    "pools": {
                        "open_pool": {
                            "percentage": 50,
                            "name": "50% OPEN POOL",
                            "total_amount": float(total_open_pool)
                        },
                        "top_direct_promoters": {
                            "percentage": 30,
                            "name": "30% TOP DIRECT PROMOTERS",
                            "total_amount": float(total_seller_pool)
                        },
                        "top_buyers_pool": {
                            "percentage": 10,
                            "name": "10% TOP BUYERS POOL", 
                            "total_amount": float(total_buyer_pool)
                        },
                        "new_joiners_pool": {
                            "percentage": 10,
                            "name": "10% New Joiners Pool",
                            "total_amount": float(total_newcomer_pool)
                        }
                    },
                    "total_overall": float(total_overall),
                    "last_updated": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

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


