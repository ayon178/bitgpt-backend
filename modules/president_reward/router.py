from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from ..user.model import User
from .model import (
    PresidentReward, PresidentRewardEligibility, PresidentRewardPayment,
    PresidentRewardFund, PresidentRewardSettings, PresidentRewardLog, 
    PresidentRewardStatistics, PresidentRewardMilestone, PresidentRewardTier
)
from .service import PresidentRewardService
from utils.response import success_response, error_response

router = APIRouter(prefix="/president-reward", tags=["President Reward"])

# Pydantic models for request/response
class PresidentRewardJoinRequest(BaseModel):
    user_id: str

class PresidentRewardEligibilityRequest(BaseModel):
    user_id: str
    force_check: bool = False

class PresidentRewardPaymentRequest(BaseModel):
    user_id: str
    tier_number: int
    amount: float

class PresidentRewardSettingsRequest(BaseModel):
    president_reward_enabled: bool
    auto_eligibility_check: bool
    auto_reward_distribution: bool
    min_direct_partners_for_qualification: int
    tier_1_reward_amount: float
    tier_2_5_reward_amount: float
    tier_6_9_reward_amount: float
    tier_10_14_reward_amount: float
    tier_15_reward_amount: float

class PresidentRewardFundRequest(BaseModel):
    fund_amount: float
    currency: str = "USD"
    source: str

# API Endpoints

@router.post("/join")
async def join_president_reward(request: PresidentRewardJoinRequest):
    """Join President Reward program"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if already joined
        existing = PresidentReward.objects(user_id=ObjectId(request.user_id)).first()
        if existing:
            return success_response(
                data={
                    "user_id": request.user_id,
                    "status": "already_joined",
                    "current_tier": existing.current_tier,
                    "total_rewards_earned": existing.total_rewards_earned,
                    "message": "User already joined President Reward program"
                },
                message="Already joined President Reward"
            )
        
        # Create President Reward record
        president_reward = PresidentReward(
            user_id=ObjectId(request.user_id),
            joined_at=datetime.utcnow(),
            is_active=True
        )
        
        # Initialize tiers
        president_reward.tiers = _initialize_president_reward_tiers()
        
        president_reward.save()
        
        return success_response(
            data={
                "president_reward_id": str(president_reward.id),
                "user_id": request.user_id,
                "current_tier": 0,
                "is_eligible": False,
                "is_active": True,
                "joined_at": president_reward.joined_at,
                "message": "Successfully joined President Reward program"
            },
            message="Joined President Reward program"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/eligibility/{user_id}")
async def check_president_reward_eligibility(user_id: str):
    """Check President Reward eligibility for user"""
    try:
        # Get President Reward record
        president_reward = PresidentReward.objects(user_id=ObjectId(user_id)).first()
        if not president_reward:
            raise HTTPException(status_code=404, detail="User not in President Reward program")
        
        # Get eligibility record
        eligibility = PresidentRewardEligibility.objects(user_id=ObjectId(user_id)).first()
        if not eligibility:
            eligibility = PresidentRewardEligibility(user_id=ObjectId(user_id))
        
        # Check direct partners
        partners_status = _check_direct_partners(user_id)
        eligibility.direct_partners_matrix_count = partners_status["matrix_partners"]
        eligibility.direct_partners_global_count = partners_status["global_partners"]
        eligibility.direct_partners_both_count = partners_status["both_partners"]
        
        # Check global team
        team_status = _check_global_team(user_id)
        eligibility.global_team_count = team_status["total_team"]
        
        # Determine eligibility
        eligibility.is_eligible_for_president_reward = (
            eligibility.direct_partners_both_count >= 30
        )
        
        # Check tier qualifications
        eligibility.qualified_for_tier_1 = (
            eligibility.direct_partners_both_count >= 10 and
            eligibility.global_team_count >= 80
        )
        eligibility.qualified_for_tier_6 = (
            eligibility.direct_partners_both_count >= 15 and
            eligibility.global_team_count >= 400
        )
        eligibility.qualified_for_tier_10 = (
            eligibility.direct_partners_both_count >= 20 and
            eligibility.global_team_count >= 1000
        )
        eligibility.qualified_for_tier_15 = (
            eligibility.direct_partners_both_count >= 30 and
            eligibility.global_team_count >= 40000
        )
        
        # Update eligibility reasons
        eligibility_reasons = _get_eligibility_reasons(eligibility)
        eligibility.eligibility_reasons = eligibility_reasons
        
        if eligibility.is_eligible_for_president_reward and not president_reward.is_eligible:
            eligibility.qualified_at = datetime.utcnow()
            president_reward.is_eligible = True
            president_reward.qualified_at = datetime.utcnow()
        
        eligibility.last_checked = datetime.utcnow()
        eligibility.save()
        
        president_reward.last_updated = datetime.utcnow()
        president_reward.save()
        
        return success_response(
            data={
                "user_id": user_id,
                "is_eligible": eligibility.is_eligible_for_president_reward,
                "direct_partners": {
                    "matrix_partners": eligibility.direct_partners_matrix_count,
                    "global_partners": eligibility.direct_partners_global_count,
                    "both_partners": eligibility.direct_partners_both_count,
                    "min_required": eligibility.min_direct_partners_required
                },
                "global_team": {
                    "total_team": eligibility.global_team_count
                },
                "tier_qualifications": {
                    "tier_1": eligibility.qualified_for_tier_1,
                    "tier_6": eligibility.qualified_for_tier_6,
                    "tier_10": eligibility.qualified_for_tier_10,
                    "tier_15": eligibility.qualified_for_tier_15
                },
                "eligibility_reasons": eligibility.eligibility_reasons,
                "qualified_at": eligibility.qualified_at,
                "last_checked": eligibility.last_checked
            },
            message="President Reward eligibility checked"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/status/{user_id}")
async def get_president_reward_status(user_id: str):
    """Get President Reward status and progress"""
    try:
        president_reward = PresidentReward.objects(user_id=ObjectId(user_id)).first()
        if not president_reward:
            raise HTTPException(status_code=404, detail="User not in President Reward program")
        
        return success_response(
            data={
                "user_id": user_id,
                "program_status": {
                    "is_eligible": president_reward.is_eligible,
                    "is_active": president_reward.is_active,
                    "current_tier": president_reward.current_tier,
                    "highest_tier_achieved": president_reward.highest_tier_achieved,
                    "joined_at": president_reward.joined_at,
                    "qualified_at": president_reward.qualified_at
                },
                "tier_status": [
                    {
                        "tier_number": tier.tier_number,
                        "direct_partners_required": tier.direct_partners_required,
                        "global_team_required": tier.global_team_required,
                        "reward_amount": tier.reward_amount,
                        "currency": tier.currency,
                        "description": tier.tier_description,
                        "is_achieved": tier.is_achieved,
                        "achieved_at": tier.achieved_at,
                        "requirements_met": tier.requirements_met
                    } for tier in president_reward.tiers
                ],
                "current_progress": {
                    "direct_partners_matrix": president_reward.direct_partners_matrix,
                    "direct_partners_global": president_reward.direct_partners_global,
                    "direct_partners_both": president_reward.direct_partners_both,
                    "total_direct_partners": president_reward.total_direct_partners,
                    "global_team_size": president_reward.global_team_size
                },
                "rewards_summary": {
                    "total_rewards_earned": president_reward.total_rewards_earned,
                    "total_rewards_paid": president_reward.total_rewards_paid,
                    "pending_rewards": president_reward.pending_rewards
                },
                "achievements": president_reward.achievements,
                "milestones": president_reward.milestone_reached,
                "last_updated": president_reward.last_updated
            },
            message="President Reward status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/payments/{user_id}")
async def get_president_reward_payments(user_id: str, limit: int = Query(50, le=100)):
    """Get President Reward payments for user"""
    try:
        payments = PresidentRewardPayment.objects(user_id=ObjectId(user_id)).order_by('-created_at').limit(limit)
        
        return success_response(
            data={
                "payments": [
                    {
                        "id": str(payment.id),
                        "tier_number": payment.tier_number,
                        "reward_amount": payment.reward_amount,
                        "currency": payment.currency,
                        "direct_partners_at_payment": payment.direct_partners_at_payment,
                        "global_team_at_payment": payment.global_team_at_payment,
                        "payment_status": payment.payment_status,
                        "payment_method": payment.payment_method,
                        "payment_reference": payment.payment_reference,
                        "processed_at": payment.processed_at,
                        "paid_at": payment.paid_at,
                        "failed_reason": payment.failed_reason,
                        "created_at": payment.created_at
                    } for payment in payments
                ],
                "total_payments": len(payments)
            },
            message="President Reward payments retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/payment")
async def create_president_reward_payment(request: PresidentRewardPaymentRequest):
    """Create President Reward payment"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get President Reward record
        president_reward = PresidentReward.objects(user_id=ObjectId(request.user_id)).first()
        if not president_reward:
            raise HTTPException(status_code=404, detail="User not in President Reward program")
        
        # Validate tier number
        if request.tier_number < 1 or request.tier_number > 15:
            raise HTTPException(status_code=400, detail="Invalid tier number (must be 1-15)")
        
        # Create payment
        payment = PresidentRewardPayment(
            user_id=ObjectId(request.user_id),
            president_reward_id=president_reward.id,
            tier_number=request.tier_number,
            reward_amount=request.amount,
            currency="USD",
            direct_partners_at_payment=president_reward.direct_partners_both,
            global_team_at_payment=president_reward.global_team_size,
            payment_status="pending"
        )
        payment.save()
        
        return success_response(
            data={
                "payment_id": str(payment.id),
                "user_id": request.user_id,
                "tier_number": request.tier_number,
                "reward_amount": request.amount,
                "currency": "USD",
                "payment_status": "pending",
                "message": "President Reward payment created successfully"
            },
            message="President Reward payment created"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/fund")
async def get_president_reward_fund():
    """Get President Reward fund status"""
    try:
        fund = PresidentRewardFund.objects(is_active=True).first()
        if not fund:
            # Create default fund
            fund = PresidentRewardFund()
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
                    "total_rewards_paid": fund.total_rewards_paid,
                    "total_amount_distributed": fund.total_amount_distributed
                },
                "last_updated": fund.last_updated
            },
            message="President Reward fund status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/fund")
async def update_president_reward_fund(request: PresidentRewardFundRequest):
    """Update President Reward fund"""
    try:
        fund = PresidentRewardFund.objects(is_active=True).first()
        if not fund:
            fund = PresidentRewardFund()
        
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
                "message": "President Reward fund updated successfully"
            },
            message="President Reward fund updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/settings")
async def get_president_reward_settings():
    """Get President Reward system settings"""
    try:
        settings = PresidentRewardSettings.objects(is_active=True).first()
        if not settings:
            # Create default settings
            settings = PresidentRewardSettings()
            settings.save()
        
        return success_response(
            data={
                "president_reward_enabled": settings.president_reward_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_reward_distribution": settings.auto_reward_distribution,
                "qualification_requirements": {
                    "min_direct_partners_for_qualification": settings.min_direct_partners_for_qualification,
                    "require_both_matrix_and_global": settings.require_both_matrix_and_global
                },
                "tier_requirements": {
                    "tier_1_direct_partners": settings.tier_1_direct_partners,
                    "tier_1_global_team": settings.tier_1_global_team,
                    "tier_6_direct_partners": settings.tier_6_direct_partners,
                    "tier_6_global_team": settings.tier_6_global_team,
                    "tier_10_direct_partners": settings.tier_10_direct_partners,
                    "tier_10_global_team": settings.tier_10_global_team,
                    "tier_15_direct_partners": settings.tier_15_direct_partners,
                    "tier_15_global_team": settings.tier_15_global_team
                },
                "reward_amounts": {
                    "tier_1_reward_amount": settings.tier_1_reward_amount,
                    "tier_2_5_reward_amount": settings.tier_2_5_reward_amount,
                    "tier_6_9_reward_amount": settings.tier_6_9_reward_amount,
                    "tier_10_14_reward_amount": settings.tier_10_14_reward_amount,
                    "tier_15_reward_amount": settings.tier_15_reward_amount
                },
                "payment_settings": {
                    "payment_currency": settings.payment_currency,
                    "payment_method": settings.payment_method,
                    "payment_delay_hours": settings.payment_delay_hours
                },
                "last_updated": settings.last_updated
            },
            message="President Reward settings retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/settings")
async def update_president_reward_settings(request: PresidentRewardSettingsRequest):
    """Update President Reward system settings"""
    try:
        settings = PresidentRewardSettings.objects(is_active=True).first()
        if not settings:
            settings = PresidentRewardSettings()
        
        settings.president_reward_enabled = request.president_reward_enabled
        settings.auto_eligibility_check = request.auto_eligibility_check
        settings.auto_reward_distribution = request.auto_reward_distribution
        settings.min_direct_partners_for_qualification = request.min_direct_partners_for_qualification
        settings.tier_1_reward_amount = request.tier_1_reward_amount
        settings.tier_2_5_reward_amount = request.tier_2_5_reward_amount
        settings.tier_6_9_reward_amount = request.tier_6_9_reward_amount
        settings.tier_10_14_reward_amount = request.tier_10_14_reward_amount
        settings.tier_15_reward_amount = request.tier_15_reward_amount
        settings.last_updated = datetime.utcnow()
        settings.save()
        
        return success_response(
            data={
                "settings_id": str(settings.id),
                "president_reward_enabled": settings.president_reward_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_reward_distribution": settings.auto_reward_distribution,
                "min_direct_partners_for_qualification": settings.min_direct_partners_for_qualification,
                "reward_amounts": {
                    "tier_1": settings.tier_1_reward_amount,
                    "tier_2_5": settings.tier_2_5_reward_amount,
                    "tier_6_9": settings.tier_6_9_reward_amount,
                    "tier_10_14": settings.tier_10_14_reward_amount,
                    "tier_15": settings.tier_15_reward_amount
                },
                "last_updated": settings.last_updated,
                "message": "President Reward settings updated successfully"
            },
            message="President Reward settings updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/statistics")
async def get_president_reward_statistics(period: str = Query("all_time", regex="^(daily|weekly|monthly|all_time)$")):
    """Get President Reward program statistics"""
    try:
        statistics = PresidentRewardStatistics.objects(period=period, is_active=True).order_by('-last_updated').first()
        
        if not statistics:
            return success_response(
                data={
                    "period": period,
                    "statistics": {
                        "total_eligible_users": 0,
                        "total_active_users": 0,
                        "total_rewards_paid": 0,
                        "total_amount_distributed": 0.0,
                        "tier_achievements": {
                            "tier_1": 0,
                            "tier_6": 0,
                            "tier_10": 0,
                            "tier_15": 0
                        },
                        "growth_statistics": {
                            "new_eligible_users": 0,
                            "new_reward_earners": 0,
                            "total_direct_partners": 0,
                            "total_global_team": 0
                        }
                    },
                    "message": "No statistics available for this period"
                },
                message="President Reward statistics retrieved"
            )
        
        return success_response(
            data={
                "period": statistics.period,
                "period_start": statistics.period_start,
                "period_end": statistics.period_end,
                "statistics": {
                    "total_eligible_users": statistics.total_eligible_users,
                    "total_active_users": statistics.total_active_users,
                    "total_rewards_paid": statistics.total_rewards_paid,
                    "total_amount_distributed": statistics.total_amount_distributed,
                    "tier_achievements": {
                        "tier_1": statistics.tier_1_achievements,
                        "tier_6": statistics.tier_6_achievements,
                        "tier_10": statistics.tier_10_achievements,
                        "tier_15": statistics.tier_15_achievements
                    },
                    "growth_statistics": {
                        "new_eligible_users": statistics.new_eligible_users,
                        "new_reward_earners": statistics.new_reward_earners,
                        "total_direct_partners": statistics.total_direct_partners,
                        "total_global_team": statistics.total_global_team
                    }
                },
                "last_updated": statistics.last_updated
            },
            message="President Reward statistics retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/leaderboard")
async def get_president_reward_leaderboard(limit: int = Query(50, le=100)):
    """Get President Reward leaderboard"""
    try:
        # Get top President Reward participants
        president_rewards = PresidentReward.objects(is_active=True).order_by('-total_rewards_earned', '-highest_tier_achieved').limit(limit)
        
        leaderboard_data = []
        for pr in president_rewards:
            leaderboard_data.append({
                "user_id": str(pr.user_id),
                "current_tier": pr.current_tier,
                "highest_tier_achieved": pr.highest_tier_achieved,
                "total_rewards_earned": pr.total_rewards_earned,
                "direct_partners_both": pr.direct_partners_both,
                "global_team_size": pr.global_team_size,
                "is_eligible": pr.is_eligible,
                "joined_at": pr.joined_at
            })
        
        return success_response(
            data={
                "leaderboard": leaderboard_data,
                "total_participants": len(leaderboard_data),
                "message": "President Reward leaderboard retrieved"
            },
            message="President Reward leaderboard retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/milestones/{user_id}")
async def get_president_reward_milestones(user_id: str):
    """Get President Reward milestones for user"""
    try:
        milestones = PresidentRewardMilestone.objects(user_id=ObjectId(user_id)).order_by('-achieved_at').all()
        
        return success_response(
            data={
                "milestones": [
                    {
                        "id": str(milestone.id),
                        "milestone_type": milestone.milestone_type,
                        "milestone_name": milestone.milestone_name,
                        "milestone_description": milestone.milestone_description,
                        "achieved_at": milestone.achieved_at,
                        "requirements_met": milestone.requirements_met,
                        "tier_number": milestone.tier_number,
                        "reward_type": milestone.reward_type,
                        "reward_value": milestone.reward_value,
                        "reward_description": milestone.reward_description,
                        "is_claimed": milestone.is_claimed,
                        "claimed_at": milestone.claimed_at
                    } for milestone in milestones
                ]
            },
            message="President Reward milestones retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

# Helper functions
def _initialize_president_reward_tiers() -> List[PresidentRewardTier]:
    """Initialize President Reward tiers - 60% USDT + 40% BNB"""
    return [
        # 10 direct partners tiers
        PresidentRewardTier(tier_number=1, direct_partners_required=10, global_team_required=400, reward_amount_usd=500.0, reward_amount_usdt=300.0, reward_amount_bnb=0.15, tier_description="Tier 1: 10 direct, 400 team"),
        PresidentRewardTier(tier_number=2, direct_partners_required=10, global_team_required=600, reward_amount_usd=700.0, reward_amount_usdt=420.0, reward_amount_bnb=0.21, tier_description="Tier 2: 10 direct, 600 team"),
        PresidentRewardTier(tier_number=3, direct_partners_required=10, global_team_required=800, reward_amount_usd=700.0, reward_amount_usdt=420.0, reward_amount_bnb=0.21, tier_description="Tier 3: 10 direct, 800 team"),
        PresidentRewardTier(tier_number=4, direct_partners_required=10, global_team_required=1000, reward_amount_usd=700.0, reward_amount_usdt=420.0, reward_amount_bnb=0.21, tier_description="Tier 4: 10 direct, 1000 team"),
        PresidentRewardTier(tier_number=5, direct_partners_required=10, global_team_required=1200, reward_amount_usd=700.0, reward_amount_usdt=420.0, reward_amount_bnb=0.21, tier_description="Tier 5: 10 direct, 1200 team"),
        
        # 15 direct partners tiers
        PresidentRewardTier(tier_number=6, direct_partners_required=15, global_team_required=1500, reward_amount_usd=800.0, reward_amount_usdt=480.0, reward_amount_bnb=0.24, tier_description="Tier 6: 15 direct, 1500 team"),
        PresidentRewardTier(tier_number=7, direct_partners_required=15, global_team_required=1800, reward_amount_usd=800.0, reward_amount_usdt=480.0, reward_amount_bnb=0.24, tier_description="Tier 7: 15 direct, 1800 team"),
        PresidentRewardTier(tier_number=8, direct_partners_required=15, global_team_required=2100, reward_amount_usd=800.0, reward_amount_usdt=480.0, reward_amount_bnb=0.24, tier_description="Tier 8: 15 direct, 2100 team"),
        PresidentRewardTier(tier_number=9, direct_partners_required=15, global_team_required=2400, reward_amount_usd=800.0, reward_amount_usdt=480.0, reward_amount_bnb=0.24, tier_description="Tier 9: 15 direct, 2400 team"),
        
        # 20 direct partners tiers
        PresidentRewardTier(tier_number=10, direct_partners_required=20, global_team_required=2700, reward_amount_usd=1500.0, reward_amount_usdt=900.0, reward_amount_bnb=0.46, tier_description="Tier 10: 20 direct, 2700 team"),
        PresidentRewardTier(tier_number=11, direct_partners_required=20, global_team_required=3000, reward_amount_usd=1500.0, reward_amount_usdt=900.0, reward_amount_bnb=0.46, tier_description="Tier 11: 20 direct, 3000 team"),
        PresidentRewardTier(tier_number=12, direct_partners_required=20, global_team_required=3500, reward_amount_usd=2000.0, reward_amount_usdt=1200.0, reward_amount_bnb=0.61, tier_description="Tier 12: 20 direct, 3500 team"),
        PresidentRewardTier(tier_number=13, direct_partners_required=20, global_team_required=4000, reward_amount_usd=2500.0, reward_amount_usdt=1500.0, reward_amount_bnb=0.76, tier_description="Tier 13: 20 direct, 4000 team"),
        PresidentRewardTier(tier_number=14, direct_partners_required=20, global_team_required=5000, reward_amount_usd=2500.0, reward_amount_usdt=1500.0, reward_amount_bnb=0.76, tier_description="Tier 14: 20 direct, 5000 team"),
        
        # 25 direct partners tier
        PresidentRewardTier(tier_number=15, direct_partners_required=25, global_team_required=6000, reward_amount_usd=5000.0, reward_amount_usdt=3000.0, reward_amount_bnb=1.52, tier_description="Tier 15: 25 direct, 6000 team")
    ]

def _check_direct_partners(user_id: str) -> Dict[str, int]:
    """Check direct partners for Matrix and Global programs"""
    try:
        # This would need to be implemented based on actual tree structure
        # For now, returning mock data
        return {
            "matrix_partners": 0,
            "global_partners": 0,
            "both_partners": 0
        }
    except Exception:
        return {
            "matrix_partners": 0,
            "global_partners": 0,
            "both_partners": 0
        }

def _check_global_team(user_id: str) -> Dict[str, Any]:
    """Check global team size"""
    try:
        # This would need to be implemented based on actual team calculation
        # For now, returning mock data
        return {
            "total_team": 0,
            "team_list": []
        }
    except Exception:
        return {
            "total_team": 0,
            "team_list": []
        }

def _get_eligibility_reasons(eligibility: PresidentRewardEligibility) -> List[str]:
    """Get eligibility reasons"""
    reasons = []
    
    if eligibility.direct_partners_both_count < 30:
        needed = 30 - eligibility.direct_partners_both_count
        reasons.append(f"Need {needed} more direct partners with both Matrix and Global packages")
    
    return reasons

@router.post("/claim")
async def claim_president_reward(
    user_id: str = Query(..., description="User ID"),
    currency: str = Query('USDT', description="Currency (USDT or BNB)")
):
    """Claim President Reward for eligible user"""
    try:
        svc = PresidentRewardService()
        result = svc.claim_president_reward(user_id=user_id, currency=currency)
        
        if not result.get('success'):
            return error_response(result.get('error', 'Claim failed'))
        
        return success_response(
            data={
                "user_id": result.get('user_id'),
                "tier": result.get('tier'),
                "amount": result.get('amount'),
                "currency": result.get('currency'),
                "payment_id": result.get('payment_id')
            },
            message=result.get('message', 'President Reward claimed successfully')
        )
    except Exception as e:
        return error_response(str(e))

@router.get("/claim/history")
async def get_president_reward_claim_history(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    currency: Optional[str] = Query(None, description="Filter by currency (USDT or BNB)"),
    tier_number: Optional[int] = Query(None, description="Filter by tier number"),
    status: Optional[str] = Query(None, description="Filter by payment status"),
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page")
):
    """Get President Reward claim history"""
    try:
        # Build query
        query_filter = {}
        
        if user_id:
            query_filter['user_id'] = ObjectId(user_id)
        if currency:
            query_filter['currency'] = currency.upper()
        if tier_number:
            query_filter['tier_number'] = tier_number
        if status:
            query_filter['payment_status'] = status
        
        # Date range
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter['$gte'] = datetime.strptime(start_date, '%Y-%m-%d')
            if end_date:
                date_filter['$lte'] = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query_filter['created_at'] = date_filter
        
        # Pagination
        skip = (page - 1) * limit
        total = PresidentRewardPayment.objects(**query_filter).count()
        
        claims = PresidentRewardPayment.objects(**query_filter).order_by('-created_at').skip(skip).limit(limit)
        
        claims_list = []
        for c in claims:
            claims_list.append({
                "id": str(c.id),
                "user_id": str(c.user_id),
                "tier": c.tier_number,
                "amount": c.reward_amount,
                "currency": getattr(c, 'currency', 'USDT'),
                "status": c.payment_status,
                "paid_at": c.paid_at,
                "created_at": c.created_at
            })
        
        return success_response(
            data={
                "claims": claims_list,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": (total + limit - 1) // limit
                }
            },
            message="President Reward claim history fetched"
        )
    except Exception as e:
        return error_response(str(e))
