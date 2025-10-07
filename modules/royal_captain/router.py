from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from ..user.model import User
from .model import (
    RoyalCaptain, RoyalCaptainEligibility, RoyalCaptainBonusPayment,
    RoyalCaptainFund, RoyalCaptainSettings, RoyalCaptainLog, RoyalCaptainStatistics,
    RoyalCaptainRequirement, RoyalCaptainBonus
)
from utils.response import success_response, error_response

router = APIRouter(prefix="/royal-captain", tags=["Royal Captain Bonus"])

# Pydantic models for request/response
class RoyalCaptainJoinRequest(BaseModel):
    user_id: str

class RoyalCaptainEligibilityRequest(BaseModel):
    user_id: str
    force_check: bool = False

class RoyalCaptainBonusRequest(BaseModel):
    user_id: str
    bonus_tier: int
    amount: float

class RoyalCaptainSettingsRequest(BaseModel):
    royal_captain_enabled: bool
    auto_eligibility_check: bool
    auto_bonus_distribution: bool
    min_direct_partners_required: int
    tier_1_bonus_amount: float
    tier_2_bonus_amount: float
    tier_3_bonus_amount: float
    tier_4_bonus_amount: float
    tier_5_bonus_amount: float

class RoyalCaptainFundRequest(BaseModel):
    fund_amount: float
    currency: str = "USD"
    source: str

# API Endpoints

@router.post("/join")
async def join_royal_captain(request: RoyalCaptainJoinRequest):
    """Join Royal Captain Bonus program"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if already joined
        existing = RoyalCaptain.objects(user_id=ObjectId(request.user_id)).first()
        if existing:
            return success_response(
                data={
                    "user_id": request.user_id,
                    "status": "already_joined",
                    "current_tier": existing.current_tier,
                    "total_bonus_earned": existing.total_bonus_earned,
                    "message": "User already joined Royal Captain program"
                },
                message="Already joined Royal Captain"
            )
        
        # Create Royal Captain record
        royal_captain = RoyalCaptain(
            user_id=ObjectId(request.user_id),
            joined_at=datetime.utcnow(),
            is_active=True
        )
        
        # Initialize requirements
        royal_captain.requirements = [
            RoyalCaptainRequirement(
                requirement_type="both_packages",
                requirement_value=1,
                requirement_description="Must have both Matrix and Global packages active"
            ),
            RoyalCaptainRequirement(
                requirement_type="direct_partners",
                requirement_value=5,
                requirement_description="Must have 5 direct partners with both packages"
            ),
            RoyalCaptainRequirement(
                requirement_type="global_team",
                requirement_value=0,
                requirement_description="Global team size requirement"
            )
        ]
        
        # Initialize bonus tiers
        royal_captain.bonuses = [
            RoyalCaptainBonus(
                bonus_tier=1,
                direct_partners_required=5,
                global_team_required=0,
                bonus_amount=200.0,
                bonus_description="First tier bonus - 5 direct partners"
            ),
            RoyalCaptainBonus(
                bonus_tier=2,
                direct_partners_required=5,
                global_team_required=10,
                bonus_amount=200.0,
                bonus_description="Second tier bonus - 5 direct partners, 10 global team"
            ),
            RoyalCaptainBonus(
                bonus_tier=3,
                direct_partners_required=5,
                global_team_required=20,
                bonus_amount=200.0,
                bonus_description="Third tier bonus - 5 direct partners, 20 global team"
            ),
            RoyalCaptainBonus(
                bonus_tier=4,
                direct_partners_required=5,
                global_team_required=30,
                bonus_amount=250.0,
                bonus_description="Fourth tier bonus - 5 direct partners, 30 global team"
            ),
            RoyalCaptainBonus(
                bonus_tier=5,
                direct_partners_required=5,
                global_team_required=40,
                bonus_amount=250.0,
                bonus_description="Fifth tier bonus - 5 direct partners, 40 global team"
            )
        ]
        
        royal_captain.save()
        
        return success_response(
            data={
                "royal_captain_id": str(royal_captain.id),
                "user_id": request.user_id,
                "current_tier": 0,
                "is_eligible": False,
                "is_active": True,
                "joined_at": royal_captain.joined_at,
                "message": "Successfully joined Royal Captain program"
            },
            message="Joined Royal Captain program"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/eligibility/{user_id}")
async def check_royal_captain_eligibility(user_id: str):
    """Check Royal Captain eligibility for user"""
    try:
        # Get Royal Captain record
        royal_captain = RoyalCaptain.objects(user_id=ObjectId(user_id)).first()
        if not royal_captain:
            raise HTTPException(status_code=404, detail="User not in Royal Captain program")
        
        # Get eligibility record
        eligibility = RoyalCaptainEligibility.objects(user_id=ObjectId(user_id)).first()
        if not eligibility:
            eligibility = RoyalCaptainEligibility(user_id=ObjectId(user_id))
        
        # Check package requirements
        eligibility.has_matrix_package = royal_captain.matrix_package_active
        eligibility.has_global_package = royal_captain.global_package_active
        eligibility.has_both_packages = royal_captain.both_packages_active
        
        # Check direct partners
        eligibility.direct_partners_count = royal_captain.total_direct_partners
        eligibility.direct_partners_with_both_packages = royal_captain.direct_partners_with_both_packages
        
        # Check global team
        eligibility.global_team_count = royal_captain.total_global_team
        
        # Determine eligibility
        eligibility.is_eligible_for_royal_captain = (
            eligibility.has_both_packages and
            eligibility.direct_partners_with_both_packages >= 5
        )
        
        # Update eligibility reasons
        eligibility_reasons = []
        if not eligibility.has_matrix_package:
            eligibility_reasons.append("Matrix package not active")
        if not eligibility.has_global_package:
            eligibility_reasons.append("Global package not active")
        if eligibility.direct_partners_with_both_packages < 5:
            eligibility_reasons.append(f"Need {5 - eligibility.direct_partners_with_both_packages} more direct partners with both packages")
        
        eligibility.eligibility_reasons = eligibility_reasons
        eligibility.last_checked = datetime.utcnow()
        eligibility.save()
        
        return success_response(
            data={
                "user_id": user_id,
                "is_eligible": eligibility.is_eligible_for_royal_captain,
                "package_status": {
                    "has_matrix_package": eligibility.has_matrix_package,
                    "has_global_package": eligibility.has_global_package,
                    "has_both_packages": eligibility.has_both_packages
                },
                "requirements": {
                    "direct_partners_count": eligibility.direct_partners_count,
                    "direct_partners_with_both_packages": eligibility.direct_partners_with_both_packages,
                    "min_direct_partners_required": eligibility.min_direct_partners_required,
                    "global_team_count": eligibility.global_team_count
                },
                "eligibility_reasons": eligibility.eligibility_reasons,
                "last_checked": eligibility.last_checked
            },
            message="Royal Captain eligibility checked"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/status/{user_id}")
async def get_royal_captain_status(user_id: str):
    """Get Royal Captain status and progress"""
    try:
        royal_captain = RoyalCaptain.objects(user_id=ObjectId(user_id)).first()
        if not royal_captain:
            raise HTTPException(status_code=404, detail="User not in Royal Captain program")
        
        return success_response(
            data={
                "user_id": user_id,
                "program_status": {
                    "is_eligible": royal_captain.is_eligible,
                    "is_active": royal_captain.is_active,
                    "current_tier": royal_captain.current_tier,
                    "joined_at": royal_captain.joined_at
                },
                "requirements_status": [
                    {
                        "type": req.requirement_type,
                        "value": req.requirement_value,
                        "description": req.requirement_description,
                        "is_met": req.is_met
                    } for req in royal_captain.requirements
                ],
                "bonus_status": [
                    {
                        "tier": bonus.bonus_tier,
                        "direct_partners_required": bonus.direct_partners_required,
                        "global_team_required": bonus.global_team_required,
                        "bonus_amount": bonus.bonus_amount,
                        "currency": bonus.currency,
                        "description": bonus.bonus_description,
                        "is_achieved": bonus.is_achieved,
                        "achieved_at": bonus.achieved_at
                    } for bonus in royal_captain.bonuses
                ],
                "current_progress": {
                    "total_direct_partners": royal_captain.total_direct_partners,
                    "direct_partners_with_both_packages": royal_captain.direct_partners_with_both_packages,
                    "total_global_team": royal_captain.total_global_team,
                    "total_bonus_earned": royal_captain.total_bonus_earned
                },
                "package_status": {
                    "matrix_package_active": royal_captain.matrix_package_active,
                    "global_package_active": royal_captain.global_package_active,
                    "both_packages_active": royal_captain.both_packages_active
                },
                "last_updated": royal_captain.last_updated
            },
            message="Royal Captain status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/bonuses/{user_id}")
async def get_royal_captain_bonuses(user_id: str, limit: int = Query(50, le=100)):
    """Get Royal Captain bonus payments for user"""
    try:
        bonuses = RoyalCaptainBonusPayment.objects(user_id=ObjectId(user_id)).order_by('-created_at').limit(limit)
        
        return success_response(
            data={
                "bonuses": [
                    {
                        "id": str(bonus.id),
                        "bonus_tier": bonus.bonus_tier,
                        "bonus_amount": bonus.bonus_amount,
                        "currency": bonus.currency,
                        "direct_partners_at_payment": bonus.direct_partners_at_payment,
                        "global_team_at_payment": bonus.global_team_at_payment,
                        "payment_status": bonus.payment_status,
                        "payment_method": bonus.payment_method,
                        "payment_reference": bonus.payment_reference,
                        "processed_at": bonus.processed_at,
                        "paid_at": bonus.paid_at,
                        "failed_reason": bonus.failed_reason,
                        "created_at": bonus.created_at
                    } for bonus in bonuses
                ],
                "total_bonuses": len(bonuses)
            },
            message="Royal Captain bonuses retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/bonus")
async def create_royal_captain_bonus(request: RoyalCaptainBonusRequest):
    """Create Royal Captain bonus payment"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get Royal Captain record
        royal_captain = RoyalCaptain.objects(user_id=ObjectId(request.user_id)).first()
        if not royal_captain:
            raise HTTPException(status_code=404, detail="User not in Royal Captain program")
        
        # Validate bonus tier
        if request.bonus_tier < 1 or request.bonus_tier > 5:
            raise HTTPException(status_code=400, detail="Invalid bonus tier (must be 1-5)")
        
        # Create bonus payment
        bonus_payment = RoyalCaptainBonusPayment(
            user_id=ObjectId(request.user_id),
            royal_captain_id=royal_captain.id,
            bonus_tier=request.bonus_tier,
            bonus_amount=request.amount,
            currency="USD",
            direct_partners_at_payment=royal_captain.direct_partners_with_both_packages,
            global_team_at_payment=royal_captain.total_global_team,
            payment_status="pending"
        )
        bonus_payment.save()
        
        return success_response(
            data={
                "bonus_id": str(bonus_payment.id),
                "user_id": request.user_id,
                "bonus_tier": request.bonus_tier,
                "bonus_amount": request.amount,
                "currency": "USD",
                "payment_status": "pending",
                "message": "Royal Captain bonus created successfully"
            },
            message="Royal Captain bonus created"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/fund")
async def get_royal_captain_fund():
    """Get Royal Captain fund status"""
    try:
        fund = RoyalCaptainFund.objects(is_active=True).first()
        if not fund:
            # Create default fund
            fund = RoyalCaptainFund()
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
                    "total_bonuses_paid": fund.total_bonuses_paid,
                    "total_amount_distributed": fund.total_amount_distributed
                },
                "last_updated": fund.last_updated
            },
            message="Royal Captain fund status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/fund")
async def update_royal_captain_fund(request: RoyalCaptainFundRequest):
    """Update Royal Captain fund"""
    try:
        fund = RoyalCaptainFund.objects(is_active=True).first()
        if not fund:
            fund = RoyalCaptainFund()
        
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
                "message": "Royal Captain fund updated successfully"
            },
            message="Royal Captain fund updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/settings")
async def get_royal_captain_settings():
    """Get Royal Captain system settings"""
    try:
        settings = RoyalCaptainSettings.objects(is_active=True).first()
        if not settings:
            # Create default settings
            settings = RoyalCaptainSettings()
            settings.save()
        
        return success_response(
            data={
                "royal_captain_enabled": settings.royal_captain_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_bonus_distribution": settings.auto_bonus_distribution,
                "requirements": {
                    "min_direct_partners_required": settings.min_direct_partners_required,
                    "require_both_packages": settings.require_both_packages,
                    "min_global_team_for_tier_1": settings.min_global_team_for_tier_1,
                    "min_global_team_for_tier_2": settings.min_global_team_for_tier_2,
                    "min_global_team_for_tier_3": settings.min_global_team_for_tier_3,
                    "min_global_team_for_tier_4": settings.min_global_team_for_tier_4,
                    "min_global_team_for_tier_5": settings.min_global_team_for_tier_5
                },
                "bonus_amounts": {
                    "tier_1_bonus_amount": settings.tier_1_bonus_amount,
                    "tier_2_bonus_amount": settings.tier_2_bonus_amount,
                    "tier_3_bonus_amount": settings.tier_3_bonus_amount,
                    "tier_4_bonus_amount": settings.tier_4_bonus_amount,
                    "tier_5_bonus_amount": settings.tier_5_bonus_amount
                },
                "payment_settings": {
                    "payment_currency": settings.payment_currency,
                    "payment_method": settings.payment_method,
                    "payment_delay_hours": settings.payment_delay_hours
                },
                "last_updated": settings.last_updated
            },
            message="Royal Captain settings retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/settings")
async def update_royal_captain_settings(request: RoyalCaptainSettingsRequest):
    """Update Royal Captain system settings"""
    try:
        settings = RoyalCaptainSettings.objects(is_active=True).first()
        if not settings:
            settings = RoyalCaptainSettings()
        
        settings.royal_captain_enabled = request.royal_captain_enabled
        settings.auto_eligibility_check = request.auto_eligibility_check
        settings.auto_bonus_distribution = request.auto_bonus_distribution
        settings.min_direct_partners_required = request.min_direct_partners_required
        settings.tier_1_bonus_amount = request.tier_1_bonus_amount
        settings.tier_2_bonus_amount = request.tier_2_bonus_amount
        settings.tier_3_bonus_amount = request.tier_3_bonus_amount
        settings.tier_4_bonus_amount = request.tier_4_bonus_amount
        settings.tier_5_bonus_amount = request.tier_5_bonus_amount
        settings.last_updated = datetime.utcnow()
        settings.save()
        
        return success_response(
            data={
                "settings_id": str(settings.id),
                "royal_captain_enabled": settings.royal_captain_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_bonus_distribution": settings.auto_bonus_distribution,
                "min_direct_partners_required": settings.min_direct_partners_required,
                "bonus_amounts": {
                    "tier_1": settings.tier_1_bonus_amount,
                    "tier_2": settings.tier_2_bonus_amount,
                    "tier_3": settings.tier_3_bonus_amount,
                    "tier_4": settings.tier_4_bonus_amount,
                    "tier_5": settings.tier_5_bonus_amount
                },
                "last_updated": settings.last_updated,
                "message": "Royal Captain settings updated successfully"
            },
            message="Royal Captain settings updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/statistics")
async def get_royal_captain_statistics(period: str = Query("all_time", regex="^(daily|weekly|monthly|all_time)$")):
    """Get Royal Captain program statistics"""
    try:
        statistics = RoyalCaptainStatistics.objects(period=period, is_active=True).order_by('-last_updated').first()
        
        if not statistics:
            return success_response(
                data={
                    "period": period,
                    "statistics": {
                        "total_eligible_users": 0,
                        "total_active_users": 0,
                        "total_bonuses_paid": 0,
                        "total_amount_distributed": 0.0,
                        "tier_achievements": {
                            "tier_1": 0,
                            "tier_2": 0,
                            "tier_3": 0,
                            "tier_4": 0,
                            "tier_5": 0
                        },
                        "growth_statistics": {
                            "new_eligible_users": 0,
                            "new_bonus_earners": 0,
                            "total_direct_partners": 0,
                            "total_global_team": 0
                        }
                    },
                    "message": "No statistics available for this period"
                },
                message="Royal Captain statistics retrieved"
            )
        
        return success_response(
            data={
                "period": statistics.period,
                "period_start": statistics.period_start,
                "period_end": statistics.period_end,
                "statistics": {
                    "total_eligible_users": statistics.total_eligible_users,
                    "total_active_users": statistics.total_active_users,
                    "total_bonuses_paid": statistics.total_bonuses_paid,
                    "total_amount_distributed": statistics.total_amount_distributed,
                    "tier_achievements": {
                        "tier_1": statistics.tier_1_achievements,
                        "tier_2": statistics.tier_2_achievements,
                        "tier_3": statistics.tier_3_achievements,
                        "tier_4": statistics.tier_4_achievements,
                        "tier_5": statistics.tier_5_achievements
                    },
                    "growth_statistics": {
                        "new_eligible_users": statistics.new_eligible_users,
                        "new_bonus_earners": statistics.new_bonus_earners,
                        "total_direct_partners": statistics.total_direct_partners,
                        "total_global_team": statistics.total_global_team
                    }
                },
                "last_updated": statistics.last_updated
            },
            message="Royal Captain statistics retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/leaderboard")
async def get_royal_captain_leaderboard(limit: int = Query(50, le=100)):
    """Get Royal Captain leaderboard"""
    try:
        # Get top Royal Captain participants
        royal_captains = RoyalCaptain.objects(is_active=True).order_by('-total_bonus_earned', '-current_tier').limit(limit)
        
        leaderboard_data = []
        for rc in royal_captains:
            leaderboard_data.append({
                "user_id": str(rc.user_id),
                "current_tier": rc.current_tier,
                "total_bonus_earned": rc.total_bonus_earned,
                "direct_partners_with_both_packages": rc.direct_partners_with_both_packages,
                "total_global_team": rc.total_global_team,
                "is_eligible": rc.is_eligible,
                "joined_at": rc.joined_at
            })
        
        return success_response(
            data={
                "leaderboard": leaderboard_data,
                "total_participants": len(leaderboard_data),
                "message": "Royal Captain leaderboard retrieved"
            },
            message="Royal Captain leaderboard retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))


@router.post("/claim")
async def claim_royal_captain_bonus(
    user_id: str = Query(...),
    currency: str = Query("USDT", description="USDT or BNB")
):
    """Claim Royal Captain bonus for the user's current eligible tier.
    - Validates eligibility (5 direct partners with all 3 programs active)
    - Prevents claims within 24 hours
    - Determines highest tier based on global team thresholds
    - Credits wallet and records history
    """
    try:
        from .service import RoyalCaptainService
        svc = RoyalCaptainService()
        res = svc.claim_royal_captain_bonus(user_id, currency)
        if not res.get("success"):
            raise HTTPException(status_code=400, detail=res.get("error", "Claim failed"))
        return success_response(res, "Royal Captain bonus claimed")
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))


@router.get("/claim/history")
async def get_royal_captain_claim_history(
    user_id: str = Query(...),
    currency: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    """Get Royal Captain bonus claim history for a user."""
    try:
        q = RoyalCaptainBonusPayment.objects(user_id=ObjectId(user_id))
        if currency:
            q = q.filter(currency=currency.upper())
        total = q.count()
        items = q.order_by('-created_at').skip((page - 1) * limit).limit(limit)
        data = []
        for it in items:
            data.append({
                "id": str(it.id),
                "tier": it.bonus_tier,
                "amount": it.bonus_amount,
                "currency": it.currency,
                "status": it.payment_status,
                "paid_at": it.paid_at,
                "created_at": it.created_at,
            })
        return success_response({
            "claims": data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit,
            }
        }, "Royal Captain claim history fetched")
    except Exception as e:
        return error_response(str(e))