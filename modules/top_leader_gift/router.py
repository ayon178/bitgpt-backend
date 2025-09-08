from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from ..user.model import User
from .model import (
    TopLeaderGift, TopLeaderGiftEligibility, TopLeaderGiftReward,
    TopLeaderGiftFund, TopLeaderGiftSettings, TopLeaderGiftLog, 
    TopLeaderGiftStatistics, TopLeaderGiftTierProgress, TopLeaderGiftTier
)
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/top-leader-gift", tags=["Top Leader Gift"])

# Pydantic models for request/response
class TopLeaderGiftJoinRequest(BaseModel):
    user_id: str

class TopLeaderGiftEligibilityRequest(BaseModel):
    user_id: str
    force_check: bool = False

class TopLeaderGiftRewardRequest(BaseModel):
    user_id: str
    tier_number: int

class TopLeaderGiftSettingsRequest(BaseModel):
    top_leader_gift_enabled: bool
    auto_eligibility_check: bool
    auto_reward_distribution: bool
    tier_requirements: dict
    delivery_method: str
    delivery_delay_days: int

class TopLeaderGiftFundRequest(BaseModel):
    fund_amount: float
    currency: str = "USD"
    source: str

class TopLeaderGiftTierRequest(BaseModel):
    user_id: str
    tier_number: int

# API Endpoints

@router.post("/join")
async def join_top_leader_gift(request: TopLeaderGiftJoinRequest):
    """Join Top Leader Gift program"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if already joined
        existing = TopLeaderGift.objects(user_id=ObjectId(request.user_id)).first()
        if existing:
            return success_response(
                data={
                    "user_id": request.user_id,
                    "status": "already_joined",
                    "total_gifts_earned": existing.total_gifts_earned,
                    "total_gift_value_usd": existing.total_gift_value_usd,
                    "max_tier_achieved": existing.max_tier_achieved,
                    "message": "User already joined Top Leader Gift program"
                },
                message="Already joined Top Leader Gift"
            )
        
        # Create Top Leader Gift record
        top_leader_gift = TopLeaderGift(
            user_id=ObjectId(request.user_id),
            joined_at=datetime.utcnow(),
            is_active=True
        )
        
        # Initialize tiers
        top_leader_gift.tiers = _initialize_top_leader_gift_tiers()
        
        top_leader_gift.save()
        
        return success_response(
            data={
                "top_leader_gift_id": str(top_leader_gift.id),
                "user_id": request.user_id,
                "is_eligible": False,
                "is_active": True,
                "joined_at": top_leader_gift.joined_at,
                "message": "Successfully joined Top Leader Gift program"
            },
            message="Joined Top Leader Gift program"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/eligibility/{user_id}")
async def check_top_leader_gift_eligibility(user_id: str):
    """Check Top Leader Gift eligibility for user"""
    try:
        # Get Top Leader Gift record
        top_leader_gift = TopLeaderGift.objects(user_id=ObjectId(user_id)).first()
        if not top_leader_gift:
            raise HTTPException(status_code=404, detail="User not in Top Leader Gift program")
        
        # Get eligibility record
        eligibility = TopLeaderGiftEligibility.objects(user_id=ObjectId(user_id)).first()
        if not eligibility:
            eligibility = TopLeaderGiftEligibility(user_id=ObjectId(user_id))
        
        # Check current status
        current_status = _check_current_status(user_id)
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
        tier_eligibility = _check_tier_eligibility(eligibility)
        eligibility.is_eligible_for_tier_1 = tier_eligibility["tier_1"]
        eligibility.is_eligible_for_tier_2 = tier_eligibility["tier_2"]
        eligibility.is_eligible_for_tier_3 = tier_eligibility["tier_3"]
        eligibility.is_eligible_for_tier_4 = tier_eligibility["tier_4"]
        eligibility.is_eligible_for_tier_5 = tier_eligibility["tier_5"]
        
        # Update eligibility reasons
        eligibility_reasons = _get_eligibility_reasons(eligibility)
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
        
        eligibility.last_checked = datetime.utcnow()
        eligibility.save()
        
        top_leader_gift.last_updated = datetime.utcnow()
        top_leader_gift.save()
        
        return success_response(
            data={
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
            },
            message="Top Leader Gift eligibility checked"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/status/{user_id}")
async def get_top_leader_gift_status(user_id: str):
    """Get Top Leader Gift status and progress"""
    try:
        top_leader_gift = TopLeaderGift.objects(user_id=ObjectId(user_id)).first()
        if not top_leader_gift:
            raise HTTPException(status_code=404, detail="User not in Top Leader Gift program")
        
        return success_response(
            data={
                "user_id": user_id,
                "program_status": {
                    "is_eligible": top_leader_gift.is_eligible,
                    "is_active": top_leader_gift.is_active,
                    "joined_at": top_leader_gift.joined_at,
                    "qualified_at": top_leader_gift.qualified_at
                },
                "current_status": {
                    "self_rank": top_leader_gift.current_self_rank,
                    "direct_partners_count": top_leader_gift.current_direct_partners_count,
                    "total_team_size": top_leader_gift.current_total_team_size,
                    "direct_partners": [str(partner_id) for partner_id in top_leader_gift.direct_partners],
                    "direct_partners_with_ranks": top_leader_gift.direct_partners_with_ranks
                },
                "tier_status": [
                    {
                        "tier_number": tier.tier_number,
                        "tier_name": tier.tier_name,
                        "self_rank_required": tier.self_rank_required,
                        "direct_partners_required": tier.direct_partners_required,
                        "partners_rank_required": tier.partners_rank_required,
                        "total_team_required": tier.total_team_required,
                        "gift_name": tier.gift_name,
                        "gift_value_usd": tier.gift_value_usd,
                        "gift_description": tier.gift_description,
                        "is_achieved": tier.is_achieved,
                        "achieved_at": tier.achieved_at,
                        "is_claimed": tier.is_claimed,
                        "claimed_at": tier.claimed_at,
                        "is_active": tier.is_active,
                        "activated_at": tier.activated_at
                    } for tier in top_leader_gift.tiers
                ],
                "progress_summary": {
                    "current_tier": top_leader_gift.current_tier,
                    "max_tier_achieved": top_leader_gift.max_tier_achieved,
                    "total_gifts_earned": top_leader_gift.total_gifts_earned,
                    "total_gifts_claimed": top_leader_gift.total_gifts_claimed,
                    "total_gift_value_usd": top_leader_gift.total_gift_value_usd,
                    "total_gift_value_claimed_usd": top_leader_gift.total_gift_value_claimed_usd,
                    "pending_gift_value_usd": top_leader_gift.pending_gift_value_usd
                },
                "last_updated": top_leader_gift.last_updated
            },
            message="Top Leader Gift status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/rewards/{user_id}")
async def get_top_leader_gift_rewards(user_id: str, limit: int = Query(50, le=100)):
    """Get Top Leader Gift rewards for user"""
    try:
        rewards = TopLeaderGiftReward.objects(user_id=ObjectId(user_id)).order_by('-created_at').limit(limit)
        
        return success_response(
            data={
                "rewards": [
                    {
                        "id": str(reward.id),
                        "tier_number": reward.tier_number,
                        "tier_name": reward.tier_name,
                        "gift_name": reward.gift_name,
                        "gift_description": reward.gift_description,
                        "gift_value_usd": reward.gift_value_usd,
                        "currency": reward.currency,
                        "self_rank_achieved": reward.self_rank_achieved,
                        "direct_partners_count": reward.direct_partners_count,
                        "partners_rank_achieved": reward.partners_rank_achieved,
                        "total_team_size": reward.total_team_size,
                        "reward_status": reward.reward_status,
                        "delivery_method": reward.delivery_method,
                        "delivery_reference": reward.delivery_reference,
                        "processed_at": reward.processed_at,
                        "delivered_at": reward.delivered_at,
                        "failed_reason": reward.failed_reason,
                        "created_at": reward.created_at
                    } for reward in rewards
                ],
                "total_rewards": len(rewards)
            },
            message="Top Leader Gift rewards retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/reward")
async def create_top_leader_gift_reward(request: TopLeaderGiftRewardRequest):
    """Create Top Leader Gift reward"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get Top Leader Gift record
        top_leader_gift = TopLeaderGift.objects(user_id=ObjectId(request.user_id)).first()
        if not top_leader_gift:
            raise HTTPException(status_code=404, detail="User not in Top Leader Gift program")
        
        if not top_leader_gift.is_eligible:
            raise HTTPException(status_code=400, detail="User not eligible for Top Leader Gift rewards")
        
        # Validate tier number
        if request.tier_number < 1 or request.tier_number > 5:
            raise HTTPException(status_code=400, detail="Invalid tier number (1-5)")
        
        # Get tier details
        tier_details = _get_tier_details(request.tier_number)
        if not tier_details:
            raise HTTPException(status_code=400, detail="Invalid tier details")
        
        # Check if tier is already achieved
        tier = top_leader_gift.tiers[request.tier_number - 1]
        if tier.is_achieved:
            return success_response(
                data={
                    "tier_number": request.tier_number,
                    "status": "already_achieved",
                    "message": "Tier already achieved"
                },
                message="Tier already achieved"
            )
        
        # Create reward record
        reward = TopLeaderGiftReward(
            user_id=ObjectId(request.user_id),
            top_leader_gift_id=top_leader_gift.id,
            tier_number=request.tier_number,
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
        top_leader_gift.max_tier_achieved = max(top_leader_gift.max_tier_achieved, request.tier_number)
        top_leader_gift.last_updated = datetime.utcnow()
        top_leader_gift.save()
        
        return success_response(
            data={
                "reward_id": str(reward.id),
                "user_id": request.user_id,
                "tier_number": request.tier_number,
                "tier_name": tier_details["tier_name"],
                "gift_name": tier_details["gift_name"],
                "gift_description": tier_details["gift_description"],
                "gift_value_usd": tier_details["gift_value_usd"],
                "reward_status": "pending",
                "message": "Top Leader Gift reward created successfully"
            },
            message="Top Leader Gift reward created"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/tier-progress/{user_id}")
async def get_tier_progress(user_id: str):
    """Get tier progress for user"""
    try:
        top_leader_gift = TopLeaderGift.objects(user_id=ObjectId(user_id)).first()
        if not top_leader_gift:
            raise HTTPException(status_code=404, detail="User not in Top Leader Gift program")
        
        # Get tier progress records
        tier_progress = TopLeaderGiftTierProgress.objects(user_id=ObjectId(user_id)).order_by('tier_number')
        
        return success_response(
            data={
                "user_id": user_id,
                "tier_progress": [
                    {
                        "tier_number": progress.tier_number,
                        "tier_name": progress.tier_name,
                        "self_rank_required": progress.self_rank_required,
                        "direct_partners_required": progress.direct_partners_required,
                        "partners_rank_required": progress.partners_rank_required,
                        "total_team_required": progress.total_team_required,
                        "gift_name": progress.gift_name,
                        "gift_value_usd": progress.gift_value_usd,
                        "current_self_rank": progress.current_self_rank,
                        "current_direct_partners": progress.current_direct_partners,
                        "current_partners_rank": progress.current_partners_rank,
                        "current_total_team": progress.current_total_team,
                        "self_rank_progress": progress.self_rank_progress,
                        "direct_partners_progress": progress.direct_partners_progress,
                        "partners_rank_progress": progress.partners_rank_progress,
                        "total_team_progress": progress.total_team_progress,
                        "overall_progress": progress.overall_progress,
                        "is_active": progress.is_active,
                        "is_achieved": progress.is_achieved,
                        "is_claimed": progress.is_claimed,
                        "achieved_at": progress.achieved_at,
                        "claimed_at": progress.claimed_at
                    } for progress in tier_progress
                ],
                "total_tiers": len(tier_progress)
            },
            message="Tier progress retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/fund")
async def get_top_leader_gift_fund():
    """Get Top Leader Gift fund status"""
    try:
        fund = TopLeaderGiftFund.objects(is_active=True).first()
        if not fund:
            # Create default fund
            fund = TopLeaderGiftFund()
            fund.save()
        
        return success_response(
            data={
                "fund_name": fund.fund_name,
                "total_fund_amount": fund.total_fund_amount,
                "available_amount": fund.available_amount,
                "distributed_amount": fund.distributed_amount,
                "currency": fund.currency,
                "fund_sources": fund.fund_sources,
                "auto_replenish": fund.auto_replenish,
                "replenish_threshold": fund.replenish_threshold,
                "max_distribution_per_day": fund.max_distribution_per_day,
                "statistics": {
                    "total_participants": fund.total_participants,
                    "total_rewards_delivered": fund.total_rewards_delivered,
                    "total_amount_distributed": fund.total_amount_distributed
                },
                "last_updated": fund.last_updated
            },
            message="Top Leader Gift fund status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/fund")
async def update_top_leader_gift_fund(request: TopLeaderGiftFundRequest):
    """Update Top Leader Gift fund"""
    try:
        fund = TopLeaderGiftFund.objects(is_active=True).first()
        if not fund:
            fund = TopLeaderGiftFund()
        
        # Update fund
        fund.total_fund_amount += request.fund_amount
        fund.available_amount += request.fund_amount
        
        # Update fund sources
        if request.source in fund.fund_sources:
            fund.fund_sources[request.source] += request.fund_amount
        else:
            fund.fund_sources[request.source] = request.fund_amount
        
        fund.last_updated = datetime.utcnow()
        fund.save()
        
        return success_response(
            data={
                "fund_id": str(fund.id),
                "total_fund_amount": fund.total_fund_amount,
                "available_amount": fund.available_amount,
                "added_amount": request.fund_amount,
                "source": request.source,
                "currency": request.currency,
                "message": "Top Leader Gift fund updated successfully"
            },
            message="Top Leader Gift fund updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/settings")
async def get_top_leader_gift_settings():
    """Get Top Leader Gift system settings"""
    try:
        settings = TopLeaderGiftSettings.objects(is_active=True).first()
        if not settings:
            # Create default settings
            settings = TopLeaderGiftSettings()
            settings.save()
        
        return success_response(
            data={
                "top_leader_gift_enabled": settings.top_leader_gift_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_reward_distribution": settings.auto_reward_distribution,
                "tier_requirements": settings.tier_requirements,
                "delivery_settings": {
                    "delivery_method": settings.delivery_method,
                    "delivery_delay_days": settings.delivery_delay_days
                },
                "last_updated": settings.last_updated
            },
            message="Top Leader Gift settings retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/settings")
async def update_top_leader_gift_settings(request: TopLeaderGiftSettingsRequest):
    """Update Top Leader Gift system settings"""
    try:
        settings = TopLeaderGiftSettings.objects(is_active=True).first()
        if not settings:
            settings = TopLeaderGiftSettings()
        
        settings.top_leader_gift_enabled = request.top_leader_gift_enabled
        settings.auto_eligibility_check = request.auto_eligibility_check
        settings.auto_reward_distribution = request.auto_reward_distribution
        settings.tier_requirements = request.tier_requirements
        settings.delivery_method = request.delivery_method
        settings.delivery_delay_days = request.delivery_delay_days
        settings.last_updated = datetime.utcnow()
        settings.save()
        
        return success_response(
            data={
                "settings_id": str(settings.id),
                "top_leader_gift_enabled": settings.top_leader_gift_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_reward_distribution": settings.auto_reward_distribution,
                "tier_requirements": settings.tier_requirements,
                "delivery_method": settings.delivery_method,
                "delivery_delay_days": settings.delivery_delay_days,
                "last_updated": settings.last_updated,
                "message": "Top Leader Gift settings updated successfully"
            },
            message="Top Leader Gift settings updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/statistics")
async def get_top_leader_gift_statistics(period: str = Query("all_time", regex="^(daily|weekly|monthly|all_time)$")):
    """Get Top Leader Gift program statistics"""
    try:
        statistics = TopLeaderGiftStatistics.objects(period=period, is_active=True).order_by('-last_updated').first()
        
        if not statistics:
            return success_response(
                data={
                    "period": period,
                    "statistics": {
                        "total_eligible_users": 0,
                        "total_active_users": 0,
                        "total_rewards_delivered": 0,
                        "total_amount_distributed": 0.0,
                        "tier_breakdown": {
                            "tier_1": {"achieved": 0, "delivered": 0, "amount": 0.0},
                            "tier_2": {"achieved": 0, "delivered": 0, "amount": 0.0},
                            "tier_3": {"achieved": 0, "delivered": 0, "amount": 0.0},
                            "tier_4": {"achieved": 0, "delivered": 0, "amount": 0.0},
                            "tier_5": {"achieved": 0, "delivered": 0, "amount": 0.0}
                        },
                        "growth_statistics": {
                            "new_eligible_users": 0,
                            "new_tier_achievers": 0,
                            "total_rank_updates": 0,
                            "total_team_growth": 0
                        }
                    },
                    "message": "No statistics available for this period"
                },
                message="Top Leader Gift statistics retrieved"
            )
        
        return success_response(
            data={
                "period": statistics.period,
                "period_start": statistics.period_start,
                "period_end": statistics.period_end,
                "statistics": {
                    "total_eligible_users": statistics.total_eligible_users,
                    "total_active_users": statistics.total_active_users,
                    "total_rewards_delivered": statistics.total_rewards_delivered,
                    "total_amount_distributed": statistics.total_amount_distributed,
                    "tier_breakdown": {
                        "tier_1": {
                            "achieved": statistics.tier_1_achieved,
                            "delivered": statistics.tier_1_delivered,
                            "amount": statistics.tier_1_amount
                        },
                        "tier_2": {
                            "achieved": statistics.tier_2_achieved,
                            "delivered": statistics.tier_2_delivered,
                            "amount": statistics.tier_2_amount
                        },
                        "tier_3": {
                            "achieved": statistics.tier_3_achieved,
                            "delivered": statistics.tier_3_delivered,
                            "amount": statistics.tier_3_amount
                        },
                        "tier_4": {
                            "achieved": statistics.tier_4_achieved,
                            "delivered": statistics.tier_4_delivered,
                            "amount": statistics.tier_4_amount
                        },
                        "tier_5": {
                            "achieved": statistics.tier_5_achieved,
                            "delivered": statistics.tier_5_delivered,
                            "amount": statistics.tier_5_amount
                        }
                    },
                    "growth_statistics": {
                        "new_eligible_users": statistics.new_eligible_users,
                        "new_tier_achievers": statistics.new_tier_achievers,
                        "total_rank_updates": statistics.total_rank_updates,
                        "total_team_growth": statistics.total_team_growth
                    }
                },
                "last_updated": statistics.last_updated
            },
            message="Top Leader Gift statistics retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/leaderboard")
async def get_top_leader_gift_leaderboard(limit: int = Query(50, le=100)):
    """Get Top Leader Gift leaderboard"""
    try:
        # Get top Top Leader Gift participants
        top_leader_gifts = TopLeaderGift.objects(is_active=True).order_by('-max_tier_achieved', '-total_gift_value_usd').limit(limit)
        
        leaderboard_data = []
        for top_leader_gift in top_leader_gifts:
            leaderboard_data.append({
                "user_id": str(top_leader_gift.user_id),
                "total_gifts_earned": top_leader_gift.total_gifts_earned,
                "total_gifts_claimed": top_leader_gift.total_gifts_claimed,
                "total_gift_value_usd": top_leader_gift.total_gift_value_usd,
                "total_gift_value_claimed_usd": top_leader_gift.total_gift_value_claimed_usd,
                "pending_gift_value_usd": top_leader_gift.pending_gift_value_usd,
                "current_tier": top_leader_gift.current_tier,
                "max_tier_achieved": top_leader_gift.max_tier_achieved,
                "current_self_rank": top_leader_gift.current_self_rank,
                "current_direct_partners_count": top_leader_gift.current_direct_partners_count,
                "current_total_team_size": top_leader_gift.current_total_team_size,
                "is_eligible": top_leader_gift.is_eligible,
                "joined_at": top_leader_gift.joined_at
            })
        
        return success_response(
            data={
                "leaderboard": leaderboard_data,
                "total_participants": len(leaderboard_data),
                "message": "Top Leader Gift leaderboard retrieved"
            },
            message="Top Leader Gift leaderboard retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

# Helper functions
def _initialize_top_leader_gift_tiers() -> List[TopLeaderGiftTier]:
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

def _check_current_status(user_id: str) -> Dict[str, Any]:
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

def _check_tier_eligibility(eligibility: TopLeaderGiftEligibility) -> Dict[str, bool]:
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

def _get_tier_details(tier_number: int) -> Optional[Dict[str, Any]]:
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

def _get_eligibility_reasons(eligibility: TopLeaderGiftEligibility) -> List[str]:
    """Get eligibility reasons"""
    reasons = []
    
    if eligibility.current_self_rank < 6:
        reasons.append("Need to achieve rank 6 or higher")
    
    if eligibility.direct_partners_count < 5:
        reasons.append("Need at least 5 direct partners")
    
    if eligibility.total_team_size < 300:
        reasons.append("Need team size of at least 300")
    
    return reasons
