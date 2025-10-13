"""
Top Leaders Gift Claim Service - Cash reward distribution from Spark 2%
"""
from typing import Dict, Any, List
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from .payment_model import (
    TopLeadersGiftUser, TopLeadersGiftPayment, TopLeadersGiftFund,
    TopLeadersGiftDistribution, TopLeadersGiftLevel
)
from ..user.model import User
from ..rank.model import UserRank

class TopLeadersGiftClaimService:
    """Business logic for Top Leaders Gift claims"""
    
    def __init__(self):
        pass
    
    def join_program(self, user_id: str) -> Dict[str, Any]:
        """Auto-join Top Leaders Gift program"""
        try:
            existing = TopLeadersGiftUser.objects(user_id=ObjectId(user_id)).first()
            if existing:
                return {"success": True, "status": "already_joined", "user_id": user_id}
            
            user = TopLeadersGiftUser(
                user_id=ObjectId(user_id),
                levels=self._initialize_levels(),
                joined_at=datetime.utcnow()
            )
            user.save()
            
            return {
                "success": True,
                "user_id": user_id,
                "message": "Joined Top Leaders Gift program"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_eligibility(self, user_id: str) -> Dict[str, Any]:
        """Check which level user is eligible for"""
        try:
            tl_user = TopLeadersGiftUser.objects(user_id=ObjectId(user_id)).first()
            if not tl_user:
                # Auto-join
                join_result = self.join_program(user_id)
                if not join_result.get('success'):
                    return join_result
                tl_user = TopLeadersGiftUser.objects(user_id=ObjectId(user_id)).first()
            
            # Get current status
            status = self._get_user_status(user_id)
            tl_user.current_self_rank = status['self_rank']
            tl_user.current_direct_partners_count = status['direct_partners_count']
            tl_user.current_total_team_size = status['total_team_size']
            tl_user.direct_partners_with_ranks = status['direct_partners_with_ranks']
            
            # Check each level eligibility
            eligible_levels = []
            for level in tl_user.levels:
                is_eligible = self._check_level_eligibility(status, level)
                if is_eligible and not level.is_maxed_out:
                    eligible_levels.append(level.level_number)
                    if not level.is_achieved:
                        level.is_achieved = True
                        level.achieved_at = datetime.utcnow()
            
            # Update highest level
            if eligible_levels:
                tl_user.highest_level_achieved = max(eligible_levels)
                tl_user.current_level = tl_user.highest_level_achieved
                tl_user.is_eligible = True
            
            tl_user.last_updated = datetime.utcnow()
            tl_user.save()
            
            return {
                "success": True,
                "user_id": user_id,
                "is_eligible": tl_user.is_eligible,
                "eligible_levels": eligible_levels,
                "highest_level": tl_user.highest_level_achieved,
                "current_status": status
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def claim_reward(self, user_id: str, level_number: int, currency: str = 'BOTH') -> Dict[str, Any]:
        """Claim Top Leaders Gift reward for a specific level"""
        try:
            currency = (currency or 'BOTH').upper()
            if currency not in ('USDT', 'BNB', 'BOTH'):
                return {"success": False, "error": "Invalid currency; must be USDT, BNB, or BOTH"}
            
            # Get user record (auto-join if needed)
            tl_user = TopLeadersGiftUser.objects(user_id=ObjectId(user_id)).first()
            if not tl_user:
                join_result = self.join_program(user_id)
                if not join_result.get('success'):
                    return join_result
                tl_user = TopLeadersGiftUser.objects(user_id=ObjectId(user_id)).first()
            
            # Check if user is eligible (from saved status, not re-checking)
            if not tl_user.is_eligible:
                return {"success": False, "error": "You are not eligible to claim Top Leaders Gift"}
            
            if tl_user.highest_level_achieved < level_number:
                return {"success": False, "error": f"You are not eligible to claim Level {level_number}"}
            
            # Get level
            level = None
            for lv in tl_user.levels:
                if lv.level_number == level_number:
                    level = lv
                    break
            
            if not level:
                return {"success": False, "error": f"Level {level_number} not found"}
            
            # Check if maxed out
            if level.is_maxed_out:
                return {"success": False, "error": f"Level {level_number} reward limit reached"}
            
            # Get fund
            fund = TopLeadersGiftFund.objects(is_active=True).first()
            if not fund:
                return {"success": False, "error": "Top Leaders Gift fund not found"}
            
            # Calculate claimable amount from level's allocated fund
            level_allocated_usdt = fund.available_usdt * (level.fund_percentage / 100.0)
            level_allocated_bnb = fund.available_bnb * (level.fund_percentage / 100.0)
            
            # Count eligible users for this level
            eligible_count = self._count_eligible_users_for_level(level_number)
            if eligible_count == 0:
                eligible_count = 1  # At least the claimer
            
            # Per-user amount
            per_user_usdt = level_allocated_usdt / eligible_count
            per_user_bnb = level_allocated_bnb / eligible_count
            
            # Check reward limits (60% USDT, 40% BNB)
            remaining_usdt = level.max_reward_usdt - level.total_claimed_usdt
            remaining_bnb = level.max_reward_bnb - level.total_claimed_bnb
            
            # Cap by remaining limits
            claim_usdt = min(per_user_usdt, remaining_usdt) if currency in ('USDT', 'BOTH') else 0.0
            claim_bnb = min(per_user_bnb, remaining_bnb) if currency in ('BNB', 'BOTH') else 0.0
            
            if claim_usdt <= 0 and claim_bnb <= 0:
                return {"success": False, "error": f"Level {level_number} reward limit reached"}
            
            # Check fund availability
            if claim_usdt > fund.available_usdt or claim_bnb > fund.available_bnb:
                return {"success": False, "error": "Insufficient fund balance"}
            
            # Create payment
            payment = TopLeadersGiftPayment(
                user_id=ObjectId(user_id),
                level_number=level_number,
                level_name=f"Level {level_number}",
                claimed_amount_usdt=claim_usdt,
                claimed_amount_bnb=claim_bnb,
                currency=currency,
                self_rank_at_claim=tl_user.current_self_rank,
                direct_partners_at_claim=tl_user.current_direct_partners_count,
                total_team_at_claim=tl_user.current_total_team_size,
                payment_status='pending'
            )
            payment.save()
            
            # Distribute payment
            dist_result = self._distribute_payment(str(payment.id))
            if not dist_result.get('success'):
                return dist_result
            
            # Update level tracking
            level.total_claimed_usdt += claim_usdt
            level.total_claimed_bnb += claim_bnb
            
            # Check if maxed out
            if level.total_claimed_usdt >= level.max_reward_usdt and level.total_claimed_bnb >= level.max_reward_bnb:
                level.is_maxed_out = True
            
            # Update user tracking
            tl_user.total_claimed_usdt += claim_usdt
            tl_user.total_claimed_bnb += claim_bnb
            tl_user.total_claims_count += 1
            tl_user.last_claim_date = datetime.utcnow()
            tl_user.last_updated = datetime.utcnow()
            tl_user.save()
            
            return {
                "success": True,
                "user_id": user_id,
                "level": level_number,
                "claimed_usdt": claim_usdt,
                "claimed_bnb": claim_bnb,
                "currency": currency,
                "payment_id": str(payment.id),
                "message": f"Top Leaders Gift Level {level_number} claimed successfully"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _distribute_payment(self, payment_id: str) -> Dict[str, Any]:
        """Distribute payment to user wallet"""
        try:
            payment = TopLeadersGiftPayment.objects(id=ObjectId(payment_id)).first()
            if not payment:
                return {"success": False, "error": "Payment not found"}
            
            if payment.payment_status != 'pending':
                return {"success": False, "error": "Payment already processed"}
            
            # Update fund
            fund = TopLeadersGiftFund.objects(is_active=True).first()
            if not fund:
                return {"success": False, "error": "Fund not found"}
            
            fund.available_usdt -= payment.claimed_amount_usdt
            fund.distributed_usdt += payment.claimed_amount_usdt
            fund.available_bnb -= payment.claimed_amount_bnb
            fund.distributed_bnb += payment.claimed_amount_bnb
            fund.total_claims += 1
            fund.last_updated = datetime.utcnow()
            fund.save()
            
            # Credit wallet
            try:
                from modules.wallet.service import WalletService
                ws = WalletService()
                
                if payment.claimed_amount_usdt > 0:
                    ws.credit_main_wallet(
                        user_id=str(payment.user_id),
                        amount=payment.claimed_amount_usdt,
                        currency='USDT',
                        reason='top_leaders_gift',
                        tx_hash=f'TLG-{payment_id}-USDT'
                    )
                
                if payment.claimed_amount_bnb > 0:
                    ws.credit_main_wallet(
                        user_id=str(payment.user_id),
                        amount=payment.claimed_amount_bnb,
                        currency='BNB',
                        reason='top_leaders_gift',
                        tx_hash=f'TLG-{payment_id}-BNB'
                    )
            except Exception as e:
                print(f"Wallet credit failed: {str(e)}")
            
            # Update payment status
            payment.payment_status = 'paid'
            payment.paid_at = datetime.utcnow()
            payment.payment_reference = f'TLG-{payment_id}'
            payment.save()
            
            return {"success": True, "payment_id": payment_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _initialize_levels(self) -> List[TopLeadersGiftLevel]:
        """Initialize 5 levels with criteria and limits"""
        return [
            TopLeadersGiftLevel(
                level_number=1,
                level_name="Level 1",
                self_rank_required=6,
                direct_partners_required=5,
                partners_rank_required=5,
                total_team_required=300,
                fund_percentage=37.5,
                max_reward_usd=3000.0,
                max_reward_usdt=1800.0,  # 60%
                max_reward_bnb=0.91  # 40% (assuming 1 BNB = ~$1316)
            ),
            TopLeadersGiftLevel(
                level_number=2,
                level_name="Level 2",
                self_rank_required=8,
                direct_partners_required=7,
                partners_rank_required=6,
                total_team_required=500,
                fund_percentage=25.0,
                max_reward_usd=30000.0,
                max_reward_usdt=18000.0,  # 60%
                max_reward_bnb=9.12  # 40%
            ),
            TopLeadersGiftLevel(
                level_number=3,
                level_name="Level 3",
                self_rank_required=11,
                direct_partners_required=8,
                partners_rank_required=10,
                total_team_required=1000,
                fund_percentage=15.0,
                max_reward_usd=3000000.0,
                max_reward_usdt=1800000.0,  # 60%
                max_reward_bnb=912.0  # 40%
            ),
            TopLeadersGiftLevel(
                level_number=4,
                level_name="Level 4",
                self_rank_required=13,
                direct_partners_required=9,
                partners_rank_required=13,
                total_team_required=2000,
                fund_percentage=12.5,
                max_reward_usd=50000000.0,
                max_reward_usdt=30000000.0,  # 60%
                max_reward_bnb=15200.0  # 40%
            ),
            TopLeadersGiftLevel(
                level_number=5,
                level_name="Level 5",
                self_rank_required=15,
                direct_partners_required=10,
                partners_rank_required=14,
                total_team_required=3000,
                fund_percentage=10.0,
                max_reward_usd=150000000.0,
                max_reward_usdt=90000000.0,  # 60%
                max_reward_bnb=45600.0  # 40%
            )
        ]
    
    def _get_user_status(self, user_id: str) -> Dict[str, Any]:
        """Get user's current rank, direct partners, and team size"""
        try:
            # Get rank
            user_rank = UserRank.objects(user_id=ObjectId(user_id)).first()
            self_rank = user_rank.current_rank_number if user_rank else 0
            
            # Get direct partners and team
            from ..user.model import PartnerGraph
            graph = PartnerGraph.objects(user_id=ObjectId(user_id)).first()
            direct_partners = graph.directs if graph else []
            total_team_size = graph.total_team if graph else 0
            
            # Get partner ranks
            partner_ranks = {}
            if direct_partners:
                partner_rank_objs = UserRank.objects(user_id__in=direct_partners)
                partner_ranks = {str(r.user_id): r.current_rank_number for r in partner_rank_objs}
            
            # Count partners meeting rank requirements
            partners_with_required_rank = {}
            for rank_req in [5, 6, 10, 13, 14]:
                count = sum(1 for r in partner_ranks.values() if r >= rank_req)
                partners_with_required_rank[rank_req] = count
            
            return {
                "self_rank": self_rank,
                "direct_partners_count": len(direct_partners),
                "total_team_size": total_team_size,
                "direct_partners_with_ranks": partner_ranks,
                "partners_meeting_requirements": partners_with_required_rank
            }
        except Exception:
            return {
                "self_rank": 0,
                "direct_partners_count": 0,
                "total_team_size": 0,
                "direct_partners_with_ranks": {},
                "partners_meeting_requirements": {}
            }
    
    def _check_level_eligibility(self, status: Dict[str, Any], level: TopLeadersGiftLevel) -> bool:
        """Check if user meets level requirements"""
        # Check self rank
        if status['self_rank'] < level.self_rank_required:
            return False
        
        # Check direct partners count
        if status['direct_partners_count'] < level.direct_partners_required:
            return False
        
        # Check team size
        if status['total_team_size'] < level.total_team_required:
            return False
        
        # Check if required number of partners have required rank
        partners_meeting = status.get('partners_meeting_requirements', {})
        required_partners_with_rank = partners_meeting.get(level.partners_rank_required, 0)
        if required_partners_with_rank < level.direct_partners_required:
            return False
        
        return True
    
    def _count_eligible_users_for_level(self, level_number: int) -> int:
        """Count how many users are eligible for this level"""
        try:
            count = TopLeadersGiftUser.objects(
                is_eligible=True,
                highest_level_achieved__gte=level_number
            ).count()
            return max(count, 1)
        except Exception:
            return 1
    
    def get_fund_overview_for_user(self, user_id: str) -> Dict[str, Any]:
        """Get fund overview with level-wise claimable amounts for user"""
        try:
            # Get or create user record
            tl_user = TopLeadersGiftUser.objects(user_id=ObjectId(user_id)).first()
            if not tl_user:
                # Auto-join
                join_result = self.join_program(user_id)
                if not join_result.get('success'):
                    return join_result
                tl_user = TopLeadersGiftUser.objects(user_id=ObjectId(user_id)).first()
            
            # Get fund
            fund = TopLeadersGiftFund.objects(is_active=True).first()
            if not fund:
                return {"success": False, "error": "Top Leaders Gift fund not found"}
            
            # Check eligibility
            status = self._get_user_status(user_id)
            tl_user.current_self_rank = status['self_rank']
            tl_user.current_direct_partners_count = status['direct_partners_count']
            tl_user.current_total_team_size = status['total_team_size']
            tl_user.direct_partners_with_ranks = status['direct_partners_with_ranks']
            
            # Update levels eligibility
            for level in tl_user.levels:
                is_eligible = self._check_level_eligibility(status, level)
                if is_eligible and not level.is_achieved:
                    level.is_achieved = True
                    level.achieved_at = datetime.utcnow()
            
            # Calculate highest level
            eligible_levels = []
            for level in tl_user.levels:
                if self._check_level_eligibility(status, level) and not level.is_maxed_out:
                    eligible_levels.append(level.level_number)
            
            if eligible_levels:
                tl_user.highest_level_achieved = max(eligible_levels)
                tl_user.is_eligible = True
            
            tl_user.last_updated = datetime.utcnow()
            tl_user.save()
            
            # Build level-wise overview
            levels_overview = []
            
            for level in tl_user.levels:
                level_number = level.level_number
                
                # Check if user is eligible for this level
                is_eligible = self._check_level_eligibility(status, level)
                
                # Get level fund percentage
                level_percentages = {
                    1: fund.level_1_percentage,
                    2: fund.level_2_percentage,
                    3: fund.level_3_percentage,
                    4: fund.level_4_percentage,
                    5: fund.level_5_percentage
                }
                level_percentage = level_percentages.get(level_number, 0.0)
                
                # Calculate allocated fund for this level
                level_allocated_usdt = fund.available_usdt * (level_percentage / 100.0)
                level_allocated_bnb = fund.available_bnb * (level_percentage / 100.0)
                
                # Count eligible users for this level
                eligible_users_count = self._count_eligible_users_for_level(level_number) if is_eligible else 0
                
                # Calculate per-user claimable amount
                per_user_usdt = level_allocated_usdt / eligible_users_count if eligible_users_count > 0 else 0.0
                per_user_bnb = level_allocated_bnb / eligible_users_count if eligible_users_count > 0 else 0.0
                
                # Cap by max reward limits
                remaining_usdt = level.max_reward_usdt - level.total_claimed_usdt
                remaining_bnb = level.max_reward_bnb - level.total_claimed_bnb
                
                claimable_usdt = min(per_user_usdt, remaining_usdt) if is_eligible else 0.0
                claimable_bnb = min(per_user_bnb, remaining_bnb) if is_eligible else 0.0
                
                # Calculate already claimed percent
                claimed_percent_usdt = (level.total_claimed_usdt / level.max_reward_usdt * 100.0) if level.max_reward_usdt > 0 else 0.0
                claimed_percent_bnb = (level.total_claimed_bnb / level.max_reward_bnb * 100.0) if level.max_reward_bnb > 0 else 0.0
                
                # Overall claimed percent (average of both currencies)
                already_claimed_percent = (claimed_percent_usdt + claimed_percent_bnb) / 2.0
                
                levels_overview.append({
                    "level": level_number,
                    "level_name": level.level_name,
                    "is_eligible": is_eligible,
                    "is_maxed_out": level.is_maxed_out,
                    "requirements": {
                        "self_rank": level.self_rank_required,
                        "direct_partners": level.direct_partners_required,
                        "partners_rank": level.partners_rank_required,
                        "total_team": level.total_team_required
                    },
                    "current_status": {
                        "self_rank": status['self_rank'],
                        "direct_partners": status['direct_partners_count'],
                        "total_team": status['total_team_size']
                    },
                    "fund_allocation": {
                        "percentage": level_percentage,
                        "allocated_usdt": level_allocated_usdt,
                        "allocated_bnb": level_allocated_bnb
                    },
                    "eligible_users_count": eligible_users_count,
                    "claimable_amount": {
                        "usdt": claimable_usdt,
                        "bnb": claimable_bnb
                    },
                    "claimed": {
                        "usdt": level.total_claimed_usdt,
                        "bnb": level.total_claimed_bnb
                    },
                    "remaining": {
                        "usdt": remaining_usdt,
                        "bnb": remaining_bnb
                    },
                    "max_reward": {
                        "usdt": level.max_reward_usdt,
                        "bnb": level.max_reward_bnb
                    },
                    "already_claimed_percent": round(already_claimed_percent, 2)
                })
            
            return {
                "success": True,
                "user_id": user_id,
                "is_eligible": tl_user.is_eligible,
                "highest_level_achieved": tl_user.highest_level_achieved,
                "total_fund": {
                    "usdt": fund.available_usdt,
                    "bnb": fund.available_bnb
                },
                "levels": levels_overview
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

