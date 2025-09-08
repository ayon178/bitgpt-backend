from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta
from ..user.model import User
from ..slot.model import SlotActivation
from ..tree.model import TreePlacement
from .model import (
    TopLeaderGift, TopLeaderGiftEligibility, TopLeaderGiftReward,
    TopLeaderGiftFund, TopLeaderGiftSettings, TopLeaderGiftLog, 
    TopLeaderGiftStatistics, TopLeaderGiftTierProgress, TopLeaderGiftTier
)

class TopLeaderGiftService:
    """Top Leader Gift Business Logic Service"""
    
    def __init__(self):
        pass
    
    def join_top_leader_gift_program(self, user_id: str) -> Dict[str, Any]:
        """Join Top Leader Gift program"""
        try:
            # Validate user exists
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check if already joined
            existing = TopLeaderGift.objects(user_id=ObjectId(user_id)).first()
            if existing:
                return {
                    "success": True,
                    "status": "already_joined",
                    "top_leader_gift_id": str(existing.id),
                    "total_gifts_earned": existing.total_gifts_earned,
                    "total_gift_value_usd": existing.total_gift_value_usd,
                    "max_tier_achieved": existing.max_tier_achieved,
                    "message": "User already joined Top Leader Gift program"
                }
            
            # Create Top Leader Gift record
            top_leader_gift = TopLeaderGift(
                user_id=ObjectId(user_id),
                joined_at=datetime.utcnow(),
                is_active=True
            )
            
            # Initialize tiers
            top_leader_gift.tiers = self._initialize_top_leader_gift_tiers()
            
            top_leader_gift.save()
            
            # Create eligibility record
            eligibility = TopLeaderGiftEligibility(user_id=ObjectId(user_id))
            eligibility.save()
            
            # Log the action
            self._log_action(user_id, "joined_program", "User joined Top Leader Gift program")
            
            return {
                "success": True,
                "top_leader_gift_id": str(top_leader_gift.id),
                "user_id": user_id,
                "is_eligible": False,
                "is_active": True,
                "joined_at": top_leader_gift.joined_at,
                "message": "Successfully joined Top Leader Gift program"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_eligibility(self, user_id: str, force_check: bool = False) -> Dict[str, Any]:
        """Check Top Leader Gift eligibility for user"""
        try:
            # Get Top Leader Gift record
            top_leader_gift = TopLeaderGift.objects(user_id=ObjectId(user_id)).first()
            if not top_leader_gift:
                return {"success": False, "error": "User not in Top Leader Gift program"}
            
            # Get eligibility record
            eligibility = TopLeaderGiftEligibility.objects(user_id=ObjectId(user_id)).first()
            if not eligibility:
                eligibility = TopLeaderGiftEligibility(user_id=ObjectId(user_id))
            
            # Check current status
            current_status = self._check_current_status(user_id)
            eligibility.current_self_rank = current_status["self_rank"]
            eligibility.direct_partners_count = current_status["direct_partners_count"]
            eligibility.direct_partners_with_ranks = current_status["direct_partners_with_ranks"]
            eligibility.total_team_size = current_status["total_team_size"]
            
            # Update Top Leader Gift record
            top_leader_gift.current_self_rank = current_status["self_rank"]
            top_leader_gift.current_direct_partners_count = current_status["direct_partners_count"]
            top_leader_gift.direct_partners = current_status["direct_partners"]
            top_leader_gift.direct_partners_with_ranks = current_status["direct_partners_with_ranks"]
            top_leader_gift.current_total_team_size = current_status["total_team_size"]
            
            # Check eligibility for each tier
            tier_eligibility = self._check_tier_eligibility(eligibility)
            eligibility.is_eligible_for_tier_1 = tier_eligibility["tier_1"]
            eligibility.is_eligible_for_tier_2 = tier_eligibility["tier_2"]
            eligibility.is_eligible_for_tier_3 = tier_eligibility["tier_3"]
            eligibility.is_eligible_for_tier_4 = tier_eligibility["tier_4"]
            eligibility.is_eligible_for_tier_5 = tier_eligibility["tier_5"]
            
            # Update eligibility reasons
            eligibility_reasons = self._get_eligibility_reasons(eligibility)
            eligibility.eligibility_reasons = eligibility_reasons
            
            # Check if user became eligible for any tier
            if any([tier_eligibility[f"tier_{i}"] for i in range(1, 6)]) and not top_leader_gift.is_eligible:
                eligibility.qualified_at = datetime.utcnow()
                top_leader_gift.is_eligible = True
                top_leader_gift.qualified_at = datetime.utcnow()
                
                # Activate eligible tiers
                for i, tier in enumerate(top_leader_gift.tiers):
                    if tier_eligibility[f"tier_{i+1}"]:
                        tier.is_active = True
                        tier.activated_at = datetime.utcnow()
                
                self._log_action(user_id, "became_eligible", "User became eligible for Top Leader Gift rewards")
            
            eligibility.last_checked = datetime.utcnow()
            eligibility.save()
            
            top_leader_gift.last_updated = datetime.utcnow()
            top_leader_gift.save()
            
            return {
                "success": True,
                "user_id": user_id,
                "is_eligible": any([tier_eligibility[f"tier_{i}"] for i in range(1, 6)]),
                "current_status": {
                    "self_rank": eligibility.current_self_rank,
                    "direct_partners_count": eligibility.direct_partners_count,
                    "total_team_size": eligibility.total_team_size,
                    "direct_partners_with_ranks": eligibility.direct_partners_with_ranks
                },
                "tier_eligibility": {
                    "tier_1": eligibility.is_eligible_for_tier_1,
                    "tier_2": eligibility.is_eligible_for_tier_2,
                    "tier_3": eligibility.is_eligible_for_tier_3,
                    "tier_4": eligibility.is_eligible_for_tier_4,
                    "tier_5": eligibility.is_eligible_for_tier_5
                },
                "eligibility_reasons": eligibility.eligibility_reasons,
                "qualified_at": eligibility.qualified_at,
                "last_checked": eligibility.last_checked
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_tier_achievement(self, user_id: str, tier_number: int) -> Dict[str, Any]:
        """Process tier achievement"""
        try:
            # Get Top Leader Gift record
            top_leader_gift = TopLeaderGift.objects(user_id=ObjectId(user_id)).first()
            if not top_leader_gift:
                return {"success": False, "error": "User not in Top Leader Gift program"}
            
            if not top_leader_gift.is_eligible:
                return {"success": False, "error": "User not eligible for Top Leader Gift rewards"}
            
            # Validate tier number
            if tier_number < 1 or tier_number > 5:
                return {"success": False, "error": "Invalid tier number (1-5)"}
            
            # Get tier details
            tier_details = self._get_tier_details(tier_number)
            if not tier_details:
                return {"success": False, "error": "Invalid tier details"}
            
            # Check if tier is already achieved
            tier = top_leader_gift.tiers[tier_number - 1]
            if tier.is_achieved:
                return {"success": False, "error": "Tier already achieved"}
            
            # Create reward record
            reward = TopLeaderGiftReward(
                user_id=ObjectId(user_id),
                top_leader_gift_id=top_leader_gift.id,
                tier_number=tier_number,
                tier_name=tier_details["tier_name"],
                gift_name=tier_details["gift_name"],
                gift_description=tier_details["gift_description"],
                gift_value_usd=tier_details["gift_value_usd"],
                self_rank_achieved=top_leader_gift.current_self_rank,
                direct_partners_count=top_leader_gift.current_direct_partners_count,
                partners_rank_achieved=tier_details["partners_rank_required"],
                total_team_size=top_leader_gift.current_total_team_size,
                reward_status="pending"
            )
            reward.save()
            
            # Update Top Leader Gift record
            tier.is_achieved = True
            tier.achieved_at = datetime.utcnow()
            top_leader_gift.total_gifts_earned += 1
            top_leader_gift.total_gift_value_usd += tier_details["gift_value_usd"]
            top_leader_gift.pending_gift_value_usd += tier_details["gift_value_usd"]
            top_leader_gift.max_tier_achieved = max(top_leader_gift.max_tier_achieved, tier_number)
            top_leader_gift.last_updated = datetime.utcnow()
            top_leader_gift.save()
            
            # Log the action
            self._log_action(user_id, "tier_achieved", 
                           f"Achieved Tier {tier_number}: {tier_details['gift_name']} worth ${tier_details['gift_value_usd']}")
            
            return {
                "success": True,
                "reward_id": str(reward.id),
                "user_id": user_id,
                "tier_number": tier_number,
                "tier_name": tier_details["tier_name"],
                "gift_name": tier_details["gift_name"],
                "gift_description": tier_details["gift_description"],
                "gift_value_usd": tier_details["gift_value_usd"],
                "reward_status": "pending",
                "message": f"Tier {tier_number} achieved: {tier_details['gift_name']}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_reward_delivery(self, reward_id: str) -> Dict[str, Any]:
        """Process reward delivery"""
        try:
            reward = TopLeaderGiftReward.objects(id=ObjectId(reward_id)).first()
            if not reward:
                return {"success": False, "error": "Reward not found"}
            
            if reward.reward_status != "pending":
                return {"success": False, "error": "Reward already processed"}
            
            # Check fund availability
            fund = TopLeaderGiftFund.objects(is_active=True).first()
            if not fund:
                return {"success": False, "error": "Top Leader Gift fund not found"}
            
            if fund.available_amount < reward.gift_value_usd:
                return {"success": False, "error": "Insufficient fund balance"}
            
            # Process delivery
            reward.reward_status = "processing"
            reward.processed_at = datetime.utcnow()
            reward.save()
            
            # Update fund
            fund.available_amount -= reward.gift_value_usd
            fund.distributed_amount += reward.gift_value_usd
            fund.total_rewards_delivered += 1
            fund.total_amount_distributed += reward.gift_value_usd
            fund.last_updated = datetime.utcnow()
            fund.save()
            
            # Update Top Leader Gift record
            top_leader_gift = TopLeaderGift.objects(id=reward.top_leader_gift_id).first()
            if top_leader_gift:
                top_leader_gift.total_gifts_claimed += 1
                top_leader_gift.total_gift_value_claimed_usd += reward.gift_value_usd
                top_leader_gift.pending_gift_value_usd -= reward.gift_value_usd
                top_leader_gift.last_updated = datetime.utcnow()
                top_leader_gift.save()
                
                # Update tier
                tier = top_leader_gift.tiers[reward.tier_number - 1]
                tier.is_claimed = True
                tier.claimed_at = datetime.utcnow()
                top_leader_gift.save()
            
            # Complete delivery
            reward.reward_status = "delivered"
            reward.delivered_at = datetime.utcnow()
            reward.delivery_reference = f"TLG-{reward.id}"
            reward.save()
            
            # Log the action
            self._log_action(str(reward.user_id), "reward_delivered", 
                           f"Delivered Tier {reward.tier_number} reward: {reward.gift_name} worth ${reward.gift_value_usd}")
            
            return {
                "success": True,
                "reward_id": reward_id,
                "gift_value_usd": reward.gift_value_usd,
                "currency": reward.currency,
                "reward_status": "delivered",
                "delivery_reference": reward.delivery_reference,
                "delivered_at": reward.delivered_at,
                "message": "Reward delivery processed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_top_leader_gift_statistics(self, period: str = "all_time") -> Dict[str, Any]:
        """Get Top Leader Gift program statistics"""
        try:
            # Calculate period dates
            now = datetime.utcnow()
            if period == "daily":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
            elif period == "weekly":
                start_date = now - timedelta(days=now.weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(weeks=1)
            elif period == "monthly":
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1)
            else:  # all_time
                start_date = datetime(2024, 1, 1)
                end_date = now
            
            # Get statistics
            total_eligible = TopLeaderGift.objects(is_eligible=True).count()
            total_active = TopLeaderGift.objects(is_active=True).count()
            
            # Get rewards for period
            rewards = TopLeaderGiftReward.objects(
                created_at__gte=start_date,
                created_at__lt=end_date,
                reward_status="delivered"
            )
            
            total_rewards_delivered = rewards.count()
            total_amount_distributed = sum(reward.gift_value_usd for reward in rewards)
            
            # Tier breakdown
            tier_breakdown = {}
            for tier_num in range(1, 6):
                tier_rewards = rewards.filter(tier_number=tier_num)
                tier_breakdown[f"tier_{tier_num}"] = {
                    "achieved": tier_rewards.count(),
                    "delivered": tier_rewards.count(),
                    "amount": sum(r.gift_value_usd for r in tier_rewards)
                }
            
            # Create or update statistics record
            statistics = TopLeaderGiftStatistics.objects(period=period).first()
            if not statistics:
                statistics = TopLeaderGiftStatistics(period=period)
            
            statistics.period_start = start_date
            statistics.period_end = end_date
            statistics.total_eligible_users = total_eligible
            statistics.total_active_users = total_active
            statistics.total_rewards_delivered = total_rewards_delivered
            statistics.total_amount_distributed = total_amount_distributed
            
            # Update tier statistics
            statistics.tier_1_achieved = tier_breakdown["tier_1"]["achieved"]
            statistics.tier_1_delivered = tier_breakdown["tier_1"]["delivered"]
            statistics.tier_1_amount = tier_breakdown["tier_1"]["amount"]
            statistics.tier_2_achieved = tier_breakdown["tier_2"]["achieved"]
            statistics.tier_2_delivered = tier_breakdown["tier_2"]["delivered"]
            statistics.tier_2_amount = tier_breakdown["tier_2"]["amount"]
            statistics.tier_3_achieved = tier_breakdown["tier_3"]["achieved"]
            statistics.tier_3_delivered = tier_breakdown["tier_3"]["delivered"]
            statistics.tier_3_amount = tier_breakdown["tier_3"]["amount"]
            statistics.tier_4_achieved = tier_breakdown["tier_4"]["achieved"]
            statistics.tier_4_delivered = tier_breakdown["tier_4"]["delivered"]
            statistics.tier_4_amount = tier_breakdown["tier_4"]["amount"]
            statistics.tier_5_achieved = tier_breakdown["tier_5"]["achieved"]
            statistics.tier_5_delivered = tier_breakdown["tier_5"]["delivered"]
            statistics.tier_5_amount = tier_breakdown["tier_5"]["amount"]
            
            statistics.last_updated = datetime.utcnow()
            statistics.save()
            
            return {
                "success": True,
                "period": period,
                "period_start": start_date,
                "period_end": end_date,
                "statistics": {
                    "total_eligible_users": total_eligible,
                    "total_active_users": total_active,
                    "total_rewards_delivered": total_rewards_delivered,
                    "total_amount_distributed": total_amount_distributed,
                    "tier_breakdown": tier_breakdown,
                    "growth_statistics": {
                        "new_eligible_users": 0,  # Would need historical data
                        "new_tier_achievers": 0,   # Would need historical data
                        "total_rank_updates": 0,  # Would need to calculate
                        "total_team_growth": 0  # Would need to calculate
                    }
                },
                "last_updated": statistics.last_updated
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _initialize_top_leader_gift_tiers(self) -> List[TopLeaderGiftTier]:
        """Initialize Top Leader Gift tiers"""
        return [
            TopLeaderGiftTier(
                tier_number=1,
                tier_name="Tier 1",
                self_rank_required=6,
                direct_partners_required=5,
                partners_rank_required=5,
                total_team_required=300,
                gift_name="LAPTOP",
                gift_value_usd=3000.0,
                gift_description="Laptop worth $3000"
            ),
            TopLeaderGiftTier(
                tier_number=2,
                tier_name="Tier 2",
                self_rank_required=8,
                direct_partners_required=7,
                partners_rank_required=6,
                total_team_required=500,
                gift_name="PRIVATE CAR",
                gift_value_usd=30000.0,
                gift_description="Private Car worth $30000"
            ),
            TopLeaderGiftTier(
                tier_number=3,
                tier_name="Tier 3",
                self_rank_required=11,
                direct_partners_required=8,
                partners_rank_required=10,
                total_team_required=1000,
                gift_name="GLOBAL TOUR PACKAGE",
                gift_value_usd=3000000.0,
                gift_description="Global Tour Package worth $3000000"
            ),
            TopLeaderGiftTier(
                tier_number=4,
                tier_name="Tier 4",
                self_rank_required=13,
                direct_partners_required=9,
                partners_rank_required=13,
                total_team_required=2000,
                gift_name="BUSINESS INVESTMENT FUND",
                gift_value_usd=50000000.0,
                gift_description="Business Investment Fund worth $50000000"
            ),
            TopLeaderGiftTier(
                tier_number=5,
                tier_name="Tier 5",
                self_rank_required=15,
                direct_partners_required=10,
                partners_rank_required=14,
                total_team_required=3000,
                gift_name="SUPER LUXURY APARTMENT",
                gift_value_usd=150000000.0,
                gift_description="Super Luxury Apartment worth $150000000"
            )
        ]
    
    def _check_current_status(self, user_id: str) -> Dict[str, Any]:
        """Check current status for user"""
        try:
            # This would need to be implemented based on actual rank and team system
            # For now, returning mock data
            return {
                "self_rank": 0,
                "direct_partners_count": 0,
                "direct_partners": [],
                "direct_partners_with_ranks": {},
                "total_team_size": 0
            }
        except Exception:
            return {
                "self_rank": 0,
                "direct_partners_count": 0,
                "direct_partners": [],
                "direct_partners_with_ranks": {},
                "total_team_size": 0
            }
    
    def _check_tier_eligibility(self, eligibility: TopLeaderGiftEligibility) -> Dict[str, bool]:
        """Check eligibility for each tier"""
        tier_eligibility = {}
        
        # Tier 1: Rank 6, 5 partners with rank 5, team 300
        tier_eligibility["tier_1"] = (
            eligibility.current_self_rank >= 6 and
            eligibility.direct_partners_count >= 5 and
            eligibility.total_team_size >= 300
        )
        
        # Tier 2: Rank 8, 7 partners with rank 6, team 500
        tier_eligibility["tier_2"] = (
            eligibility.current_self_rank >= 8 and
            eligibility.direct_partners_count >= 7 and
            eligibility.total_team_size >= 500
        )
        
        # Tier 3: Rank 11, 8 partners with rank 10, team 1000
        tier_eligibility["tier_3"] = (
            eligibility.current_self_rank >= 11 and
            eligibility.direct_partners_count >= 8 and
            eligibility.total_team_size >= 1000
        )
        
        # Tier 4: Rank 13, 9 partners with rank 13, team 2000
        tier_eligibility["tier_4"] = (
            eligibility.current_self_rank >= 13 and
            eligibility.direct_partners_count >= 9 and
            eligibility.total_team_size >= 2000
        )
        
        # Tier 5: Rank 15, 10 partners with rank 14, team 3000
        tier_eligibility["tier_5"] = (
            eligibility.current_self_rank >= 15 and
            eligibility.direct_partners_count >= 10 and
            eligibility.total_team_size >= 3000
        )
        
        return tier_eligibility
    
    def _get_tier_details(self, tier_number: int) -> Optional[Dict[str, Any]]:
        """Get tier details for given tier number"""
        tier_details = {
            1: {
                "tier_name": "Tier 1",
                "gift_name": "LAPTOP",
                "gift_description": "Laptop worth $3000",
                "gift_value_usd": 3000.0,
                "partners_rank_required": 5
            },
            2: {
                "tier_name": "Tier 2",
                "gift_name": "PRIVATE CAR",
                "gift_description": "Private Car worth $30000",
                "gift_value_usd": 30000.0,
                "partners_rank_required": 6
            },
            3: {
                "tier_name": "Tier 3",
                "gift_name": "GLOBAL TOUR PACKAGE",
                "gift_description": "Global Tour Package worth $3000000",
                "gift_value_usd": 3000000.0,
                "partners_rank_required": 10
            },
            4: {
                "tier_name": "Tier 4",
                "gift_name": "BUSINESS INVESTMENT FUND",
                "gift_description": "Business Investment Fund worth $50000000",
                "gift_value_usd": 50000000.0,
                "partners_rank_required": 13
            },
            5: {
                "tier_name": "Tier 5",
                "gift_name": "SUPER LUXURY APARTMENT",
                "gift_description": "Super Luxury Apartment worth $150000000",
                "gift_value_usd": 150000000.0,
                "partners_rank_required": 14
            }
        }
        
        return tier_details.get(tier_number)
    
    def _get_eligibility_reasons(self, eligibility: TopLeaderGiftEligibility) -> List[str]:
        """Get eligibility reasons"""
        reasons = []
        
        if eligibility.current_self_rank < 6:
            reasons.append("Need to achieve rank 6 or higher")
        
        if eligibility.direct_partners_count < 5:
            reasons.append("Need at least 5 direct partners")
        
        if eligibility.total_team_size < 300:
            reasons.append("Need team size of at least 300")
        
        return reasons
    
    def _log_action(self, user_id: str, action_type: str, description: str):
        """Log Top Leader Gift action"""
        try:
            log = TopLeaderGiftLog(
                user_id=ObjectId(user_id),
                action_type=action_type,
                action_description=description,
                is_processed=True,
                processed_at=datetime.utcnow()
            )
            log.save()
        except Exception:
            pass  # Logging failure shouldn't break the main process
