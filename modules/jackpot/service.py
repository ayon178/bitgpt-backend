from datetime import datetime, timedelta
from decimal import Decimal
from bson import ObjectId
import random
import uuid
from typing import Dict, List, Any, Optional

from modules.user.model import User
from modules.income.model import IncomeEvent
from modules.wallet.model import UserWallet
from modules.jackpot.model import (
    JackpotDistribution, JackpotUserEntry, JackpotFreeCoupon, 
    JackpotFund, JackpotEntry, JackpotWinner
)

class JackpotService:
    """Service for managing Jackpot 4-Part Distribution System"""
    
    def __init__(self):
        self.entry_fee = Decimal('0.0025')  # 0.0025 BNB per entry
        self.binary_contribution_percentage = Decimal('0.05')  # 5% from binary slot activations
        
        # Pool distribution percentages
        self.open_pool_percentage = Decimal('0.50')  # 50%
        self.top_promoters_pool_percentage = Decimal('0.30')  # 30%
        self.top_buyers_pool_percentage = Decimal('0.10')  # 10%
        self.new_joiners_pool_percentage = Decimal('0.10')  # 10%
        
        # Winner counts
        self.open_pool_winners_count = 10
        self.top_promoters_winners_count = 20
        self.top_buyers_winners_count = 20
        self.new_joiners_winners_count = 10
        
        # Free coupons mapping for binary slots
        self.free_coupons_mapping = {
            5: 1, 6: 2, 7: 3, 8: 4, 9: 5, 10: 6, 11: 7, 12: 8,
            13: 9, 14: 10, 15: 11, 16: 12, 17: 13
        }
    
    @staticmethod
    def award_free_coupon_for_binary_slot(user_id: str, slot_no: int) -> dict:
        """Compatibility helper used by BinaryService and user joins.

        Awards free coupons for a given binary slot upgrade by delegating to
        process_free_coupon_entry. Exposed as a static method so it can be
        invoked both on the class and on an instance safely.
        """
        svc = JackpotService()
        return svc.process_free_coupon_entry(user_id=user_id, slot_number=slot_no)

    def _get_current_week_dates(self) -> tuple:
        """Get current week start and end dates (Sunday to Sunday)"""
        today = datetime.utcnow()
        # Get the start of the week (Sunday)
        days_since_sunday = today.weekday() + 1  # Monday is 0, so Sunday is 6
        if days_since_sunday == 7:  # If today is Sunday
            days_since_sunday = 0
        
        week_start = today - timedelta(days=days_since_sunday)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        return week_start, week_end
    
    def _get_or_create_user_entry(self, user_id: str, week_start: datetime, week_end: datetime) -> JackpotUserEntry:
        """Get or create user entry record for the week"""
        user_entry = JackpotUserEntry.objects(
            user_id=ObjectId(user_id),
            week_start_date=week_start,
            week_end_date=week_end
        ).first()
        
        if not user_entry:
            user_entry = JackpotUserEntry(
                user_id=ObjectId(user_id),
                week_start_date=week_start,
                week_end_date=week_end,
                paid_entries_count=0,
                free_entries_count=0,
                total_entries_count=0,
                direct_referrals_entries_count=0,
                entries=[],
                free_coupons_earned=0,
                free_coupons_used=0,
                binary_contributions=Decimal('0.0')
            )
            user_entry.save()
        
        return user_entry
    
    def _get_or_create_jackpot_fund(self, week_start: datetime, week_end: datetime) -> JackpotFund:
        """Get or create jackpot fund for the week"""
        fund = JackpotFund.objects(
            week_start_date=week_start,
            week_end_date=week_end
        ).first()
        
        if not fund:
            fund_id = f"JACKPOT_FUND_{week_start.strftime('%Y%m%d')}_{week_end.strftime('%Y%m%d')}"
            fund = JackpotFund(
                fund_id=fund_id,
                week_start_date=week_start,
                week_end_date=week_end,
                entry_fees_total=Decimal('0.0'),
                binary_contributions_total=Decimal('0.0'),
                rollover_from_previous=Decimal('0.0'),
                total_fund=Decimal('0.0'),
                open_pool_allocation=Decimal('0.0'),
                top_promoters_pool_allocation=Decimal('0.0'),
                top_buyers_pool_allocation=Decimal('0.0'),
                new_joiners_pool_allocation=Decimal('0.0'),
                status='accumulating'
            )
            fund.save()
        
        return fund
    
    def process_jackpot_entry(self, user_id: str, entry_count: int = 1, tx_hash: str = None) -> Dict[str, Any]:
        """Process jackpot entry for a user"""
        try:
            week_start, week_end = self._get_current_week_dates()
            
            # Get or create user entry record
            user_entry = self._get_or_create_user_entry(user_id, week_start, week_end)
            
            # Calculate total cost
            total_cost = self.entry_fee * entry_count
            
            # Create entry records
            new_entries = []
            for i in range(entry_count):
                entry_id = f"ENTRY_{user_id}_{int(datetime.utcnow().timestamp() * 1000)}_{i}"
                entry = JackpotEntry(
                    entry_id=entry_id,
                    entry_type='paid',
                    entry_fee=self.entry_fee,
                    tx_hash=tx_hash or f"JACKPOT_TX_{entry_id}",
                    created_at=datetime.utcnow()
                )
                new_entries.append(entry)
            
            # Update user entry record
            user_entry.entries.extend(new_entries)
            user_entry.paid_entries_count += entry_count
            user_entry.total_entries_count += entry_count
            user_entry.updated_at = datetime.utcnow()
            user_entry.save()
            
            # Update jackpot fund
            fund = self._get_or_create_jackpot_fund(week_start, week_end)
            fund.entry_fees_total += total_cost
            fund.total_fund += total_cost
            fund.updated_at = datetime.utcnow()
            fund.save()
            
            # Update user's direct referrals entries count
            self._update_direct_referrals_entries_count(user_id, week_start, week_end, entry_count)
            
            return {
                "success": True,
                "entry_count": entry_count,
                "total_cost": total_cost,
                "week_start": week_start,
                "week_end": week_end,
                "user_total_entries": user_entry.total_entries_count,
                "fund_total": fund.total_fund
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Jackpot entry processing failed: {str(e)}"
            }
    
    def process_free_coupon_entry(self, user_id: str, slot_number: int, tx_hash: str = None) -> Dict[str, Any]:
        """Process free coupon entry from binary slot upgrade"""
        try:
            if slot_number not in self.free_coupons_mapping:
                return {
                    "success": False,
                    "error": f"Slot {slot_number} does not qualify for free coupons"
                }
            
            week_start, week_end = self._get_current_week_dates()
            coupons_earned = self.free_coupons_mapping[slot_number]
            
            # Get or create user entry record
            user_entry = self._get_or_create_user_entry(user_id, week_start, week_end)
            
            # Create free coupon record
            free_coupon = JackpotFreeCoupon(
                user_id=ObjectId(user_id),
                slot_number=slot_number,
                coupons_earned=coupons_earned,
                coupons_used=0,
                week_start_date=week_start,
                week_end_date=week_end,
                earned_at=datetime.utcnow()
            )
            free_coupon.save()
            
            # Create free entry records
            new_entries = []
            for i in range(coupons_earned):
                entry_id = f"FREE_ENTRY_{user_id}_{slot_number}_{int(datetime.utcnow().timestamp() * 1000)}_{i}"
                entry = JackpotEntry(
                    entry_id=entry_id,
                    entry_type='free',
                    entry_fee=Decimal('0.0'),
                    tx_hash=tx_hash or f"FREE_COUPON_TX_{entry_id}",
                    created_at=datetime.utcnow()
                )
                new_entries.append(entry)
            
            # Update user entry record
            user_entry.entries.extend(new_entries)
            user_entry.free_entries_count += coupons_earned
            user_entry.total_entries_count += coupons_earned
            user_entry.free_coupons_earned += coupons_earned
            user_entry.updated_at = datetime.utcnow()
            user_entry.save()
            
            return {
                "success": True,
                "slot_number": slot_number,
                "coupons_earned": coupons_earned,
                "week_start": week_start,
                "week_end": week_end,
                "user_total_entries": user_entry.total_entries_count
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Free coupon processing failed: {str(e)}"
            }
    
    def process_binary_contribution(self, user_id: str, slot_fee: Decimal, tx_hash: str = None) -> Dict[str, Any]:
        """Process binary slot activation contribution to jackpot fund"""
        try:
            week_start, week_end = self._get_current_week_dates()
            contribution_amount = slot_fee * self.binary_contribution_percentage
            
            # Get or create user entry record
            user_entry = self._get_or_create_user_entry(user_id, week_start, week_end)
            user_entry.binary_contributions += contribution_amount
            user_entry.updated_at = datetime.utcnow()
            user_entry.save()
            
            # Update jackpot fund
            fund = self._get_or_create_jackpot_fund(week_start, week_end)
            fund.binary_contributions_total += contribution_amount
            fund.total_fund += contribution_amount
            fund.updated_at = datetime.utcnow()
            fund.save()
            
            return {
                "success": True,
                "slot_fee": slot_fee,
                "contribution_amount": contribution_amount,
                "contribution_percentage": self.binary_contribution_percentage,
                "week_start": week_start,
                "week_end": week_end,
                "fund_total": fund.total_fund
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Binary contribution processing failed: {str(e)}"
            }
    
    def _update_direct_referrals_entries_count(self, user_id: str, week_start: datetime, week_end: datetime, entry_count: int):
        """Update direct referrals entries count for promoters pool"""
        try:
            # Find the user's direct upline
            user = User.objects(id=ObjectId(user_id)).first()
            if not user or not user.refered_by:
                return
            
            upline_id = user.refered_by
            upline_entry = self._get_or_create_user_entry(upline_id, week_start, week_end)
            upline_entry.direct_referrals_entries_count += entry_count
            upline_entry.updated_at = datetime.utcnow()
            upline_entry.save()
                
        except Exception as e:
            print(f"Error updating direct referrals entries count: {e}")
    
    def get_user_jackpot_status(self, user_id: str) -> Dict[str, Any]:
        """Get user's jackpot status for current week"""
        try:
            week_start, week_end = self._get_current_week_dates()
            
            user_entry = JackpotUserEntry.objects(
                user_id=ObjectId(user_id),
                week_start_date=week_start,
                week_end_date=week_end
            ).first()
            
            if not user_entry:
                return {
                    "success": True,
                    "user_id": user_id,
                    "week_start": week_start,
                    "week_end": week_end,
                    "paid_entries_count": 0,
                    "free_entries_count": 0,
                    "total_entries_count": 0,
                    "direct_referrals_entries_count": 0,
                    "free_coupons_earned": 0,
                    "free_coupons_used": 0,
                    "binary_contributions": Decimal('0.0')
                }
            
            return {
                "success": True,
                "user_id": user_id,
                "week_start": week_start,
                "week_end": week_end,
                "paid_entries_count": user_entry.paid_entries_count,
                "free_entries_count": user_entry.free_entries_count,
                "total_entries_count": user_entry.total_entries_count,
                "direct_referrals_entries_count": user_entry.direct_referrals_entries_count,
                "free_coupons_earned": user_entry.free_coupons_earned,
                "free_coupons_used": user_entry.free_coupons_used,
                "binary_contributions": user_entry.binary_contributions
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get user jackpot status: {str(e)}"
            }
    
    def get_jackpot_fund_status(self) -> Dict[str, Any]:
        """Get current jackpot fund status"""
        try:
            week_start, week_end = self._get_current_week_dates()
            
            fund = JackpotFund.objects(
                week_start_date=week_start,
                week_end_date=week_end
            ).first()
            
            if not fund:
                return {
                    "success": True,
                    "week_start": week_start,
                    "week_end": week_end,
                    "total_fund": Decimal('0.0'),
                    "entry_fees_total": Decimal('0.0'),
                    "binary_contributions_total": Decimal('0.0'),
                    "rollover_from_previous": Decimal('0.0'),
                    "open_pool_allocation": Decimal('0.0'),
                    "top_promoters_pool_allocation": Decimal('0.0'),
                    "top_buyers_pool_allocation": Decimal('0.0'),
                    "new_joiners_pool_allocation": Decimal('0.0'),
                    "status": "accumulating"
                }
            
            return {
                "success": True,
                "week_start": week_start,
                "week_end": week_end,
                "total_fund": fund.total_fund,
                "entry_fees_total": fund.entry_fees_total,
                "binary_contributions_total": fund.binary_contributions_total,
                "rollover_from_previous": fund.rollover_from_previous,
                "open_pool_allocation": fund.open_pool_allocation,
                "top_promoters_pool_allocation": fund.top_promoters_pool_allocation,
                "top_buyers_pool_allocation": fund.top_buyers_pool_allocation,
                "new_joiners_pool_allocation": fund.new_joiners_pool_allocation,
                "status": fund.status
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get jackpot fund status: {str(e)}"
            }
    
    def process_weekly_distribution(self) -> Dict[str, Any]:
        """Process weekly jackpot distribution (4-part system)"""
        try:
            # Get previous week's dates
            week_start, week_end = self._get_current_week_dates()
            previous_week_start = week_start - timedelta(days=7)
            previous_week_end = week_end - timedelta(days=7)
            
            # Get jackpot fund for previous week
            fund = JackpotFund.objects(
                week_start_date=previous_week_start,
                week_end_date=previous_week_end
            ).first()
            
            if not fund or fund.total_fund <= 0:
                return {
                    "success": False,
                    "error": "No jackpot fund found for distribution"
                }
            
            # Calculate pool allocations
            open_pool_amount = fund.total_fund * self.open_pool_percentage
            top_promoters_pool_amount = fund.total_fund * self.top_promoters_pool_percentage
            top_buyers_pool_amount = fund.total_fund * self.top_buyers_pool_percentage
            new_joiners_pool_amount = fund.total_fund * self.new_joiners_pool_percentage
            
            # Update fund allocations
            fund.open_pool_allocation = open_pool_amount
            fund.top_promoters_pool_allocation = top_promoters_pool_amount
            fund.top_buyers_pool_allocation = top_buyers_pool_amount
            fund.new_joiners_pool_allocation = new_joiners_pool_amount
            fund.status = 'ready_for_distribution'
            fund.save()
            
            # Create distribution record
            distribution_id = f"JACKPOT_DIST_{previous_week_start.strftime('%Y%m%d')}_{previous_week_end.strftime('%Y%m%d')}"
            distribution = JackpotDistribution(
                distribution_id=distribution_id,
                week_start_date=previous_week_start,
                week_end_date=previous_week_end,
                total_fund=fund.total_fund,
                total_entries=0,  # Will be calculated
                open_pool_amount=open_pool_amount,
                top_promoters_pool_amount=top_promoters_pool_amount,
                top_buyers_pool_amount=top_buyers_pool_amount,
                new_joiners_pool_amount=new_joiners_pool_amount,
                winners=[],
                status='pending'
            )
            
            # Process each pool
            winners = []
            
            # 1. Open Pool (50%) - 10 random winners
            open_pool_winners = self._select_open_pool_winners(previous_week_start, previous_week_end, open_pool_amount)
            winners.extend(open_pool_winners)
            
            # 2. Top Direct Promoters Pool (30%) - 20 top promoters
            promoters_winners = self._select_top_promoters_winners(previous_week_start, previous_week_end, top_promoters_pool_amount, distribution)
            winners.extend(promoters_winners)
            
            # 3. Top Buyers Pool (10%) - 20 top buyers
            buyers_winners = self._select_top_buyers_winners(previous_week_start, previous_week_end, top_buyers_pool_amount, distribution)
            winners.extend(buyers_winners)
            
            # 4. New Joiners Pool (10%) - 10 random new joiners
            new_joiners_winners = self._select_new_joiners_winners(previous_week_start, previous_week_end, new_joiners_pool_amount)
            winners.extend(new_joiners_winners)
            
            # Update distribution with winners
            distribution.winners = winners
            distribution.total_entries = len(winners)
            distribution.status = 'completed'
            distribution.distribution_date = datetime.utcnow()
            distribution.save()
            
            # Distribute winnings to users
            self._distribute_winnings(winners)
            
            # Add rollover amounts to next week's fund
            total_rollover = distribution.promoters_rollover + distribution.buyers_rollover
            if total_rollover > 0:
                next_week_start = week_start
                next_week_end = week_end
                next_fund = self._get_or_create_jackpot_fund(next_week_start, next_week_end)
                next_fund.rollover_from_previous += total_rollover
                next_fund.total_fund += total_rollover
                next_fund.updated_at = datetime.utcnow()
                next_fund.save()
            
            return {
                "success": True,
                "distribution_id": distribution_id,
                "total_fund": fund.total_fund,
                "open_pool_amount": open_pool_amount,
                "top_promoters_pool_amount": top_promoters_pool_amount,
                "top_buyers_pool_amount": top_buyers_pool_amount,
                "new_joiners_pool_amount": new_joiners_pool_amount,
                "total_winners": len(winners),
                "rollover_to_next_week": total_rollover,
                "winners": winners
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Weekly distribution processing failed: {str(e)}"
            }
    
    def _select_open_pool_winners(self, week_start: datetime, week_end: datetime, pool_amount: Decimal) -> List[Dict]:
        """Select 10 random winners for open pool"""
        try:
            # Get all users with entries in the week
            user_entries = JackpotUserEntry.objects(
                week_start_date=week_start,
                week_end_date=week_end,
                total_entries_count__gt=0
            )
            
            if not user_entries:
                return []
            
            # Create weighted list based on entry count
            weighted_users = []
            for entry in user_entries:
                for _ in range(entry.total_entries_count):
                    weighted_users.append(entry.user_id)
            
            if len(weighted_users) == 0:
                return []
            
            # Select 10 random winners
            winners = []
            winner_amount = pool_amount / self.open_pool_winners_count
            
            selected_users = random.sample(weighted_users, min(self.open_pool_winners_count, len(weighted_users)))
            
            for i, user_id in enumerate(selected_users):
                # Count entries for this user
                user_entry = JackpotUserEntry.objects(
                    user_id=user_id,
                    week_start_date=week_start,
                    week_end_date=week_end
                ).first()
                
                entries_count = user_entry.total_entries_count if user_entry else 0
                
                winner = JackpotWinner(
                    user_id=user_id,
                    pool_type='open_pool',
                    rank=i + 1,
                    amount_won=winner_amount,
                    entries_count=entries_count
                )
                winners.append(winner)
            
            return winners
            
        except Exception as e:
            print(f"Error selecting open pool winners: {e}")
            return []
    
    def _select_top_promoters_winners(self, week_start: datetime, week_end: datetime, pool_amount: Decimal, distribution: 'JackpotDistribution') -> List[Dict]:
        """Select 20 top promoters based on direct referrals entries with rollover"""
        try:
            # Get users with direct referrals entries, sorted by count
            user_entries = JackpotUserEntry.objects(
                week_start_date=week_start,
                week_end_date=week_end,
                direct_referrals_entries_count__gt=0
            ).order_by('-direct_referrals_entries_count')
            
            if not user_entries:
                # Full pool goes to rollover
                distribution.promoters_rollover = pool_amount
                return []
            
            winners = []
            actual_winner_count = min(len(user_entries), self.top_promoters_winners_count)
            
            if actual_winner_count < self.top_promoters_winners_count:
                # Calculate rollover for missing winners
                distributed_amount = pool_amount * (actual_winner_count / self.top_promoters_winners_count)
                rollover_amount = pool_amount - distributed_amount
                distribution.promoters_rollover = rollover_amount
                winner_amount = distributed_amount / actual_winner_count if actual_winner_count > 0 else Decimal('0.0')
            else:
                winner_amount = pool_amount / self.top_promoters_winners_count
            
            # Select top promoters
            selected_entries = user_entries[:actual_winner_count]
            
            for i, entry in enumerate(selected_entries):
                winner = JackpotWinner(
                    user_id=entry.user_id,
                    pool_type='top_promoters',
                    rank=i + 1,
                    amount_won=winner_amount,
                    entries_count=entry.total_entries_count,
                    direct_referrals_count=entry.direct_referrals_entries_count
                )
                winners.append(winner)
            
            return winners
            
        except Exception as e:
            print(f"Error selecting top promoters winners: {e}")
            return []
    
    def _select_top_buyers_winners(self, week_start: datetime, week_end: datetime, pool_amount: Decimal, distribution: 'JackpotDistribution') -> List[Dict]:
        """Select 20 top buyers based on individual entries with rollover"""
        try:
            # Get users with entries, sorted by total entries count
            user_entries = JackpotUserEntry.objects(
                week_start_date=week_start,
                week_end_date=week_end,
                total_entries_count__gt=0
            ).order_by('-total_entries_count')
            
            if not user_entries:
                # Full pool goes to rollover
                distribution.buyers_rollover = pool_amount
                return []
            
            winners = []
            actual_winner_count = min(len(user_entries), self.top_buyers_winners_count)
            
            if actual_winner_count < self.top_buyers_winners_count:
                # Calculate rollover for missing winners
                distributed_amount = pool_amount * (actual_winner_count / self.top_buyers_winners_count)
                rollover_amount = pool_amount - distributed_amount
                distribution.buyers_rollover = rollover_amount
                winner_amount = distributed_amount / actual_winner_count if actual_winner_count > 0 else Decimal('0.0')
            else:
                winner_amount = pool_amount / self.top_buyers_winners_count
            
            # Select top 20 buyers
            selected_entries = user_entries[:actual_winner_count]
            
            for i, entry in enumerate(selected_entries):
                winner = JackpotWinner(
                    user_id=entry.user_id,
                    pool_type='top_buyers',
                    rank=i + 1,
                    amount_won=winner_amount,
                    entries_count=entry.total_entries_count
                )
                winners.append(winner)
            
            return winners
            
        except Exception as e:
            print(f"Error selecting top buyers winners: {e}")
            return []
    
    def _select_new_joiners_winners(self, week_start: datetime, week_end: datetime, pool_amount: Decimal) -> List[Dict]:
        """Select 10 random new joiners from last 7 days"""
        try:
            # Get users who joined Binary in the last 7 days
            new_joiners = User.objects(
                binary_joined=True,
                binary_joined_at__gte=week_start - timedelta(days=7),
                binary_joined_at__lte=week_end
            )
            
            if not new_joiners:
                return []
            
            # Convert to list and select 10 random winners
            new_joiners_list = list(new_joiners)
            winners = []
            winner_amount = pool_amount / self.new_joiners_winners_count
            
            selected_users = random.sample(new_joiners_list, min(self.new_joiners_winners_count, len(new_joiners_list)))
            
            for i, user in enumerate(selected_users):
                winner = JackpotWinner(
                    user_id=user.id,
                    pool_type='new_joiners',
                    rank=i + 1,
                    amount_won=winner_amount,
                    entries_count=0,  # New joiners don't need entries
                    is_new_joiner=True
                )
                winners.append(winner)
            
            return winners
            
        except Exception as e:
            print(f"Error selecting new joiners winners: {e}")
            return []
    
    def _distribute_winnings(self, winners: List[Dict]):
        """Distribute winnings to users' wallets"""
        try:
            for winner in winners:
                # Create income event
                income_event = IncomeEvent(
                    user_id=winner.user_id,
                    source_user_id=winner.user_id,
                    program='jackpot',
                    slot_no=0,
                    income_type='jackpot',
                    amount=winner.amount_won,
                    percentage=Decimal('100.0'),
                    tx_hash=f"JACKPOT_WIN_{winner.user_id}_{int(datetime.utcnow().timestamp())}",
                    status='completed',
                    description=f"Jackpot {winner.pool_type} winner - Rank {winner.rank}",
                    created_at=datetime.utcnow()
                )
                income_event.save()
                
                # Update user wallet
                wallet = UserWallet.objects(user_id=winner.user_id, wallet_type='main').first()
                if not wallet:
                    wallet = UserWallet(
                        user_id=winner.user_id,
                        wallet_type='main',
                        balance=Decimal('0.0'),
                        currency='BNB'
                    )
                
                wallet.balance += winner.amount_won
                wallet.last_updated = datetime.utcnow()
                wallet.save()
                
        except Exception as e:
            print(f"Error distributing winnings: {e}")
    
    def get_distribution_history(self, limit: int = 10) -> Dict[str, Any]:
        """Get jackpot distribution history"""
        try:
            distributions = JackpotDistribution.objects().order_by('-created_at').limit(limit)
            
            history = []
            for dist in distributions:
                history.append({
                    "distribution_id": dist.distribution_id,
                    "week_start": dist.week_start_date,
                    "week_end": dist.week_end_date,
                    "total_fund": dist.total_fund,
                    "open_pool_amount": dist.open_pool_amount,
                    "top_promoters_pool_amount": dist.top_promoters_pool_amount,
                    "top_buyers_pool_amount": dist.top_buyers_pool_amount,
                    "new_joiners_pool_amount": dist.new_joiners_pool_amount,
                    "total_winners": len(dist.winners),
                    "status": dist.status,
                    "distribution_date": dist.distribution_date,
                    "created_at": dist.created_at
                })
            
            return {
                "success": True,
                "distributions": history,
                "total_count": len(history)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get distribution history: {str(e)}"
            }
    
    def get_current_jackpot_stats(self, user_id: str = None) -> Dict[str, Any]:
        """Get current jackpot session statistics (total entries and total fund)
        If user_id is provided, also returns user's own entry count for current session"""
        try:
            week_start, week_end = self._get_current_week_dates()
            current_date = datetime.utcnow()
            
            # Check if current date is within the jackpot session
            is_active = week_start <= current_date <= week_end
            
            # Get total Jackpot fund amounts from BonusFund (calculate before checking is_active)
            total_global_usdt = 0.0
            total_global_bnb = 0.0
            try:
                from modules.income.bonus_fund import BonusFund
                # Get USDT fund (from matrix program)
                usdt_fund = BonusFund.objects(fund_type='jackpot_entry', program='matrix').first()
                if usdt_fund:
                    total_global_usdt = float(usdt_fund.current_balance or 0.0)
                
                # Get BNB fund (from binary program)
                bnb_fund = BonusFund.objects(fund_type='jackpot_entry', program='binary').first()
                if bnb_fund:
                    total_global_bnb = float(bnb_fund.current_balance or 0.0)
            except Exception as e:
                print(f"Error fetching jackpot global funds: {e}")
            
            if not is_active:
                response = {
                    "success": True,
                    "is_active": False,
                    "message": "No active jackpot session",
                    "total_entries": 0,
                    "total_fund": Decimal('0.0'),
                    "week_start": week_start,
                    "week_end": week_end,
                    "total_global_usdt": total_global_usdt,  # Total Jackpot fund in USDT
                    "total_global_bnb": total_global_bnb,    # Total Jackpot fund in BNB
                }
                
                # Add user entry count if user_id provided
                if user_id:
                    response["user_entry_count"] = 0
                
                return response
            
            # Get jackpot fund for current week
            fund = JackpotFund.objects(
                week_start_date=week_start,
                week_end_date=week_end
            ).first()
            
            # Get all user entries for current week
            user_entries = JackpotUserEntry.objects(
                week_start_date=week_start,
                week_end_date=week_end
            )
            
            # Calculate total entries across all users
            total_entries = 0
            for entry in user_entries:
                total_entries += entry.total_entries_count
            
            total_fund = fund.total_fund if fund else Decimal('0.0')
            
            response = {
                "success": True,
                "is_active": True,
                "total_entries": total_entries,
                "total_fund": total_fund,
                "week_start": week_start,
                "week_end": week_end,
                "entry_fees_total": fund.entry_fees_total if fund else Decimal('0.0'),
                "binary_contributions_total": fund.binary_contributions_total if fund else Decimal('0.0'),
                "rollover_from_previous": fund.rollover_from_previous if fund else Decimal('0.0'),
                "total_global_usdt": total_global_usdt,  # Total Jackpot fund in USDT
                "total_global_bnb": total_global_bnb,    # Total Jackpot fund in BNB
            }
            
            # If user_id provided, get user's own entry count for current session
            if user_id:
                try:
                    user_entry = JackpotUserEntry.objects(
                        user_id=ObjectId(user_id),
                        week_start_date=week_start,
                        week_end_date=week_end
                    ).first()
                    
                    user_entry_count = user_entry.total_entries_count if user_entry else 0
                    response["user_entry_count"] = user_entry_count
                    
                    # Calculate user's contribution to total fund (entry fees only)
                    user_contribution = Decimal(str(user_entry_count)) * self.entry_fee if user_entry_count > 0 else Decimal('0.0')
                    response["user_contribution"] = user_contribution
                    
                except Exception as e:
                    print(f"Error getting user entry count: {e}")
                    response["user_entry_count"] = 0
                    response["user_contribution"] = Decimal('0.0')
            
            return response
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get current jackpot stats: {str(e)}"
            }
    
    def get_user_entry_history(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """Get user's jackpot entry history"""
        try:
            # Get user's entries from all weeks, ordered by creation date
            user_entries = JackpotUserEntry.objects(
                user_id=ObjectId(user_id)
            ).order_by('-created_at').limit(limit)
            
            entry_history = []
            entry_counter = 1
            
            for user_entry in user_entries:
                for entry in user_entry.entries:
                    entry_history.append({
                        "entry_no": entry_counter,
                        "entry_price": float(entry.entry_fee),
                        "entry_type": entry.entry_type,
                        "time_date": entry.created_at.strftime("%d%b,%Y (%H:%M)"),
                        "week_start": user_entry.week_start_date.strftime("%d%b,%Y"),
                        "week_end": user_entry.week_end_date.strftime("%d%b,%Y"),
                        "tx_hash": entry.tx_hash
                    })
                    entry_counter += 1
            
            return {
                "success": True,
                "entry_history": entry_history,
                "total_entries": len(entry_history)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get user entry history: {str(e)}"
            }
    
    def get_user_claim_history(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """Get user's jackpot claim/winning history"""
        try:
            # Get jackpot distributions where user was a winner
            distributions = JackpotDistribution.objects(
                winners__user_id=ObjectId(user_id)
            ).order_by('-created_at').limit(limit)
            
            claim_history = []
            
            for distribution in distributions:
                # Find user's winning entries in this distribution
                user_winnings = [winner for winner in distribution.winners 
                               if winner.user_id == ObjectId(user_id)]
                
                for winning in user_winnings:
                    # Map pool type to display name
                    pool_type_mapping = {
                        'open_pool': 'OPEN POOL',
                        'top_promoters': 'TOP DIRECT PROMOTERS',
                        'top_buyers': 'TOP BUYERS POOL',
                        'new_joiners': 'NEW JOINERS POOL'
                    }
                    
                    claim_history.append({
                        "type": pool_type_mapping.get(winning.pool_type, winning.pool_type),
                        "win_price": float(winning.amount_won),
                        "time_date": distribution.distribution_date.strftime("%d%b,%Y (%H:%M)") if distribution.distribution_date else distribution.created_at.strftime("%d%b,%Y (%H:%M)"),
                        "rank": winning.rank,
                        "entries_count": winning.entries_count,
                        "week_start": distribution.week_start_date.strftime("%d%b,%Y"),
                        "week_end": distribution.week_end_date.strftime("%d%b,%Y")
                    })
            
            # Sort by date descending
            claim_history.sort(key=lambda x: x["time_date"], reverse=True)
            
            return {
                "success": True,
                "claim_history": claim_history,
                "total_claims": len(claim_history)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get user claim history: {str(e)}"
            }