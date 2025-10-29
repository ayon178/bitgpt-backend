from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from ..user.model import User
from .model import (
    NewcomerSupport, NewcomerSupportEligibility, NewcomerSupportBonus,
    NewcomerSupportFund, NewcomerSupportSettings, NewcomerSupportLog, 
    NewcomerSupportStatistics, NewcomerSupportMonthlyOpportunity, NewcomerBonus
)
from utils.response import success_response, error_response
from .service import NewcomerSupportService
from auth.service import authentication_service

router = APIRouter(prefix="/newcomer-support", tags=["Newcomer Growth Support"])

# Pydantic models for request/response
class NewcomerSupportJoinRequest(BaseModel):
    user_id: str

class NewcomerSupportEligibilityRequest(BaseModel):
    user_id: str
    force_check: bool = False

class NewcomerSupportBonusRequest(BaseModel):
    user_id: str
    bonus_type: str
    bonus_amount: float

class NewcomerSupportSettingsRequest(BaseModel):
    newcomer_support_enabled: bool
    auto_eligibility_check: bool
    auto_bonus_distribution: bool
    require_matrix_program: bool
    newcomer_period_days: int
    instant_bonus_amount: float
    monthly_opportunities_count: int
    upline_rank_bonus_percentage: float

class NewcomerSupportFundRequest(BaseModel):
    fund_amount: float
    currency: str = "USDT"
    source: str

class NewcomerSupportMonthlyOpportunityRequest(BaseModel):
    user_id: str
    opportunity_month: str
    opportunity_type: str
    opportunity_value: float

# API Endpoints

@router.post("/join")
async def join_newcomer_support(request: NewcomerSupportJoinRequest):
    """Join Newcomer Growth Support program"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if already joined
        existing = NewcomerSupport.objects(user_id=ObjectId(request.user_id)).first()
        if existing:
            return success_response(
                data={
                    "user_id": request.user_id,
                    "status": "already_joined",
                    "total_bonuses_earned": existing.total_bonuses_earned,
                    "instant_bonus_claimed": existing.instant_bonus_claimed,
                    "monthly_opportunities_count": existing.monthly_opportunities_count,
                    "message": "User already joined Newcomer Support program"
                },
                message="Already joined Newcomer Support"
            )
        
        # Create Newcomer Support record
        newcomer_support = NewcomerSupport(
            user_id=ObjectId(request.user_id),
            joined_at=datetime.utcnow(),
            is_active=True
        )
        
        # Initialize bonuses
        newcomer_support.bonuses = _initialize_newcomer_bonuses()
        
        newcomer_support.save()
        
        return success_response(
            data={
                "newcomer_support_id": str(newcomer_support.id),
                "user_id": request.user_id,
                "is_eligible": False,
                "is_active": True,
                "joined_at": newcomer_support.joined_at,
                "message": "Successfully joined Newcomer Support program"
            },
            message="Joined Newcomer Support program"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/eligibility/{user_id}")
async def check_newcomer_support_eligibility(user_id: str):
    """Check Newcomer Support eligibility for user"""
    try:
        # Get Newcomer Support record
        newcomer_support = NewcomerSupport.objects(user_id=ObjectId(user_id)).first()
        if not newcomer_support:
            raise HTTPException(status_code=404, detail="User not in Newcomer Support program")
        
        # Get eligibility record
        eligibility = NewcomerSupportEligibility.objects(user_id=ObjectId(user_id)).first()
        if not eligibility:
            eligibility = NewcomerSupportEligibility(user_id=ObjectId(user_id))
        
        # Check Matrix program status
        matrix_status = _check_matrix_program_status(user_id)
        eligibility.has_matrix_program = matrix_status["has_matrix"]
        eligibility.matrix_join_date = matrix_status["join_date"]
        eligibility.matrix_slots_activated = matrix_status["slots_activated"]
        
        # Check newcomer status
        newcomer_status = _check_newcomer_status(user_id)
        eligibility.is_newcomer = newcomer_status["is_newcomer"]
        eligibility.newcomer_end_date = newcomer_status["end_date"]
        
        # Update Newcomer Support record
        newcomer_support.has_matrix_program = matrix_status["has_matrix"]
        newcomer_support.matrix_join_date = matrix_status["join_date"]
        newcomer_support.matrix_slots_activated = matrix_status["slots_activated"]
        
        # Determine eligibility for different bonuses
        eligibility.is_eligible_for_instant_bonus = (
            eligibility.has_matrix_program and
            eligibility.is_newcomer
        )
        
        eligibility.is_eligible_for_monthly_opportunities = (
            eligibility.has_matrix_program and
            eligibility.is_newcomer
        )
        
        eligibility.is_eligible_for_upline_rank_bonus = (
            eligibility.has_matrix_program and
            eligibility.is_newcomer
        )
        
        # Update eligibility reasons
        eligibility_reasons = _get_eligibility_reasons(eligibility)
        eligibility.eligibility_reasons = eligibility_reasons
        
        if eligibility.is_eligible_for_instant_bonus and not newcomer_support.is_eligible:
            eligibility.qualified_at = datetime.utcnow()
            newcomer_support.is_eligible = True
            newcomer_support.qualified_at = datetime.utcnow()
            newcomer_support.instant_bonus_eligible = True
            newcomer_support.monthly_opportunities_eligible = True
            newcomer_support.upline_rank_bonus_eligible = True
            
            # Activate bonuses
            for bonus in newcomer_support.bonuses:
                bonus.is_active = True
                bonus.activated_at = datetime.utcnow()
        
        eligibility.last_checked = datetime.utcnow()
        eligibility.save()
        
        newcomer_support.last_updated = datetime.utcnow()
        newcomer_support.save()
        
        return success_response(
            data={
                "user_id": user_id,
                "is_eligible": eligibility.is_eligible_for_instant_bonus,
                "matrix_program": {
                    "has_matrix_program": eligibility.has_matrix_program,
                    "matrix_join_date": eligibility.matrix_join_date,
                    "matrix_slots_activated": eligibility.matrix_slots_activated
                },
                "newcomer_status": {
                    "is_newcomer": eligibility.is_newcomer,
                    "newcomer_period_days": eligibility.newcomer_period_days,
                    "newcomer_end_date": eligibility.newcomer_end_date
                },
                "bonus_eligibility": {
                    "instant_bonus": eligibility.is_eligible_for_instant_bonus,
                    "monthly_opportunities": eligibility.is_eligible_for_monthly_opportunities,
                    "upline_rank_bonus": eligibility.is_eligible_for_upline_rank_bonus
                },
                "eligibility_reasons": eligibility.eligibility_reasons,
                "qualified_at": eligibility.qualified_at,
                "last_checked": eligibility.last_checked
            },
            message="Newcomer Support eligibility checked"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/status/{user_id}")
async def get_newcomer_support_status(user_id: str):
    """Get Newcomer Support status and progress"""
    try:
        newcomer_support = NewcomerSupport.objects(user_id=ObjectId(user_id)).first()
        if not newcomer_support:
            raise HTTPException(status_code=404, detail="User not in Newcomer Support program")
        
        return success_response(
            data={
                "user_id": user_id,
                "program_status": {
                    "is_eligible": newcomer_support.is_eligible,
                    "is_active": newcomer_support.is_active,
                    "joined_at": newcomer_support.joined_at,
                    "qualified_at": newcomer_support.qualified_at
                },
                "matrix_status": {
                    "has_matrix_program": newcomer_support.has_matrix_program,
                    "matrix_join_date": newcomer_support.matrix_join_date,
                    "matrix_slots_activated": newcomer_support.matrix_slots_activated
                },
                "instant_bonus": {
                    "eligible": newcomer_support.instant_bonus_eligible,
                    "amount": newcomer_support.instant_bonus_amount,
                    "claimed": newcomer_support.instant_bonus_claimed,
                    "claimed_at": newcomer_support.instant_bonus_claimed_at
                },
                "monthly_opportunities": {
                    "eligible": newcomer_support.monthly_opportunities_eligible,
                    "count": newcomer_support.monthly_opportunities_count,
                    "last_opportunity": newcomer_support.last_monthly_opportunity,
                    "next_opportunity": newcomer_support.next_monthly_opportunity
                },
                "upline_rank_bonus": {
                    "eligible": newcomer_support.upline_rank_bonus_eligible,
                    "upline_user_id": str(newcomer_support.upline_user_id) if newcomer_support.upline_user_id else None,
                    "upline_rank": newcomer_support.upline_rank,
                    "user_rank": newcomer_support.user_rank,
                    "bonus_percentage": newcomer_support.upline_rank_bonus_percentage,
                    "bonus_amount": newcomer_support.upline_rank_bonus_amount,
                    "claimed": newcomer_support.upline_rank_bonus_claimed,
                    "claimed_at": newcomer_support.upline_rank_bonus_claimed_at
                },
                "bonuses_summary": {
                    "total_bonuses_earned": newcomer_support.total_bonuses_earned,
                    "total_bonuses_claimed": newcomer_support.total_bonuses_claimed,
                    "pending_bonuses": newcomer_support.pending_bonuses
                },
                "bonuses": [
                    {
                        "bonus_type": bonus.bonus_type,
                        "bonus_name": bonus.bonus_name,
                        "bonus_amount": bonus.bonus_amount,
                        "bonus_percentage": bonus.bonus_percentage,
                        "currency": bonus.currency,
                        "is_claimed": bonus.is_claimed,
                        "claimed_at": bonus.claimed_at,
                        "is_active": bonus.is_active,
                        "activated_at": bonus.activated_at
                    } for bonus in newcomer_support.bonuses
                ],
                "last_updated": newcomer_support.last_updated
            },
            message="Newcomer Support status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/bonuses/{user_id}")
async def get_newcomer_support_bonuses(user_id: str, limit: int = Query(50, le=100)):
    """Get Newcomer Support bonuses for user"""
    try:
        bonuses = NewcomerSupportBonus.objects(user_id=ObjectId(user_id)).order_by('-created_at').limit(limit)
        
        return success_response(
            data={
                "bonuses": [
                    {
                        "id": str(bonus.id),
                        "bonus_type": bonus.bonus_type,
                        "bonus_name": bonus.bonus_name,
                        "bonus_amount": bonus.bonus_amount,
                        "bonus_percentage": bonus.bonus_percentage,
                        "currency": bonus.currency,
                        "source_type": bonus.source_type,
                        "source_description": bonus.source_description,
                        "upline_user_id": str(bonus.upline_user_id) if bonus.upline_user_id else None,
                        "upline_rank": bonus.upline_rank,
                        "user_rank": bonus.user_rank,
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
            message="Newcomer Support bonuses retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/bonuses/upline-locked/{user_id}")
async def get_upline_locked_bonuses(user_id: str, limit: int = Query(50, le=100)):
    """Get upline-locked Newcomer Support bonuses (locked until available_from)."""
    try:
        # Filter by bonus_type 'upline_reserve' or available_from in the future
        bonuses = NewcomerSupportBonus.objects(user_id=ObjectId(user_id)).order_by('-created_at')
        locked = []
        now = datetime.utcnow()
        for b in bonuses:
            is_locked = False
            if getattr(b, 'bonus_type', None) == 'upline_reserve':
                is_locked = True
            if getattr(b, 'available_from', None) and b.available_from > now:
                is_locked = True
            if is_locked:
                locked.append(b)
            if len(locked) >= limit:
                break
        return success_response(
            data={
                "bonuses": [
                    {
                        "id": str(b.id),
                        "bonus_type": b.bonus_type,
                        "bonus_name": b.bonus_name,
                        "bonus_amount": b.bonus_amount,
                        "currency": b.currency,
                        "payment_status": b.payment_status,
                        "available_from": b.available_from,
                        "created_at": b.created_at,
                    } for b in locked
                ],
                "total_locked": len(locked)
            },
            message="Upline locked bonuses retrieved"
        )
    except Exception as e:
        return error_response(str(e))

@router.post("/bonus")
async def create_newcomer_support_bonus(request: NewcomerSupportBonusRequest):
    """Create Newcomer Support bonus"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get Newcomer Support record
        newcomer_support = NewcomerSupport.objects(user_id=ObjectId(request.user_id)).first()
        if not newcomer_support:
            raise HTTPException(status_code=404, detail="User not in Newcomer Support program")
        
        if not newcomer_support.is_eligible:
            raise HTTPException(status_code=400, detail="User not eligible for Newcomer Support bonuses")
        
        # Validate bonus type
        if request.bonus_type not in ['instant', 'monthly', 'upline_rank']:
            raise HTTPException(status_code=400, detail="Invalid bonus type")
        
        # Create bonus record
        bonus = NewcomerSupportBonus(
            user_id=ObjectId(request.user_id),
            newcomer_support_id=newcomer_support.id,
            bonus_type=request.bonus_type,
            bonus_name=_get_bonus_name(request.bonus_type),
            bonus_amount=request.bonus_amount,
            source_type=_get_source_type(request.bonus_type),
            source_description=_get_source_description(request.bonus_type),
            payment_status="pending"
        )
        bonus.save()
        
        # Update Newcomer Support record
        newcomer_support.total_bonuses_earned += request.bonus_amount
        newcomer_support.pending_bonuses += request.bonus_amount
        
        # Update specific bonus type
        if request.bonus_type == 'instant':
            newcomer_support.instant_bonus_amount = request.bonus_amount
        elif request.bonus_type == 'monthly':
            newcomer_support.monthly_opportunities_count += 1
        elif request.bonus_type == 'upline_rank':
            newcomer_support.upline_rank_bonus_amount = request.bonus_amount
        
        newcomer_support.last_updated = datetime.utcnow()
        newcomer_support.save()
        
        return success_response(
            data={
                "bonus_id": str(bonus.id),
                "user_id": request.user_id,
                "bonus_type": request.bonus_type,
                "bonus_name": bonus.bonus_name,
                "bonus_amount": request.bonus_amount,
                "source_type": bonus.source_type,
                "source_description": bonus.source_description,
                "payment_status": "pending",
                "message": "Newcomer Support bonus created successfully"
            },
            message="Newcomer Support bonus created"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/bonus/claim-instant")
async def claim_instant_bonus(payload: NewcomerSupportJoinRequest):
    """Claim Instant Bonus (Matrix-only, API-triggered)"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(payload.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Validate program enrollment
        newcomer_support = NewcomerSupport.objects(user_id=ObjectId(payload.user_id)).first()
        if not newcomer_support:
            raise HTTPException(status_code=404, detail="User not in Newcomer Support program")

        # Check eligibility first
        eligibility = NewcomerSupportEligibility.objects(user_id=ObjectId(payload.user_id)).first()
        if not eligibility:
            eligibility = NewcomerSupportEligibility(user_id=ObjectId(payload.user_id))
            eligibility.save()

        # Refresh matrix/newcomer eligibility
        matrix_status = _check_matrix_program_status(payload.user_id)
        newcomer_status = _check_newcomer_status(payload.user_id)
        is_eligible = bool(matrix_status.get("has_matrix")) and bool(newcomer_status.get("is_newcomer"))
        if not is_eligible:
            raise HTTPException(status_code=400, detail="Not eligible for instant bonus")

        # Determine bonus amount from settings (fallback to 50 USDT)
        settings = NewcomerSupportSettings.objects(is_active=True).first()
        amount = settings.instant_bonus_amount if settings else 50.0

        # Create bonus record
        bonus = NewcomerSupportBonus(
            user_id=ObjectId(payload.user_id),
            newcomer_support_id=newcomer_support.id,
            bonus_type="instant",
            bonus_name="Instant Bonus",
            bonus_amount=amount,
            source_type="matrix_join",
            source_description="Instant bonus upon joining Matrix program",
            payment_status="pending"
        )
        bonus.save()

        # Update user NGS state
        newcomer_support.instant_bonus_amount = amount
        newcomer_support.instant_bonus_claimed = True
        newcomer_support.instant_bonus_claimed_at = datetime.utcnow()
        newcomer_support.total_bonuses_earned += amount
        newcomer_support.pending_bonuses += amount
        newcomer_support.last_updated = datetime.utcnow()
        newcomer_support.save()

        return success_response(
            data={
                "bonus_id": str(bonus.id),
                "user_id": payload.user_id,
                "bonus_type": "instant",
                "bonus_amount": amount,
                "currency": "USDT",
                "payment_status": "pending",
                "message": f"Instant bonus processed: ${amount}"
            },
            message="Instant bonus claimed"
        )

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))

@router.get("/monthly-opportunities/{user_id}")
async def get_monthly_opportunities(user_id: str):
    """Get monthly earning opportunities for user"""
    try:
        opportunities = NewcomerSupportMonthlyOpportunity.objects(
            user_id=ObjectId(user_id),
            is_available=True
        ).order_by('-created_at')
        
        return success_response(
            data={
                "opportunities": [
                    {
                        "id": str(opportunity.id),
                        "opportunity_month": opportunity.opportunity_month,
                        "opportunity_type": opportunity.opportunity_type,
                        "opportunity_description": opportunity.opportunity_description,
                        "opportunity_value": opportunity.opportunity_value,
                        "currency": opportunity.currency,
                        "upline_user_id": str(opportunity.upline_user_id) if opportunity.upline_user_id else None,
                        "upline_activity_score": opportunity.upline_activity_score,
                        "upline_rank": opportunity.upline_rank,
                        "is_available": opportunity.is_available,
                        "is_claimed": opportunity.is_claimed,
                        "claimed_at": opportunity.claimed_at,
                        "expires_at": opportunity.expires_at,
                        "created_at": opportunity.created_at
                    } for opportunity in opportunities
                ],
                "total_opportunities": len(opportunities)
            },
            message="Monthly opportunities retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/monthly-opportunity")
async def create_monthly_opportunity(request: NewcomerSupportMonthlyOpportunityRequest):
    """Create monthly earning opportunity"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get Newcomer Support record
        newcomer_support = NewcomerSupport.objects(user_id=ObjectId(request.user_id)).first()
        if not newcomer_support:
            raise HTTPException(status_code=404, detail="User not in Newcomer Support program")
        
        if not newcomer_support.monthly_opportunities_eligible:
            raise HTTPException(status_code=400, detail="User not eligible for monthly opportunities")
        
        # Validate opportunity type
        if request.opportunity_type not in ['upline_activity', 'team_growth', 'personal_achievement']:
            raise HTTPException(status_code=400, detail="Invalid opportunity type")
        
        # Create opportunity record
        opportunity = NewcomerSupportMonthlyOpportunity(
            user_id=ObjectId(request.user_id),
            newcomer_support_id=newcomer_support.id,
            opportunity_month=request.opportunity_month,
            opportunity_type=request.opportunity_type,
            opportunity_description=_get_opportunity_description(request.opportunity_type),
            opportunity_value=request.opportunity_value,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        opportunity.save()
        
        # Update Newcomer Support record
        newcomer_support.last_monthly_opportunity = datetime.utcnow()
        newcomer_support.next_monthly_opportunity = datetime.utcnow() + timedelta(days=30)
        newcomer_support.last_updated = datetime.utcnow()
        newcomer_support.save()
        
        return success_response(
            data={
                "opportunity_id": str(opportunity.id),
                "user_id": request.user_id,
                "opportunity_month": request.opportunity_month,
                "opportunity_type": request.opportunity_type,
                "opportunity_description": opportunity.opportunity_description,
                "opportunity_value": request.opportunity_value,
                "expires_at": opportunity.expires_at,
                "message": "Monthly opportunity created successfully"
            },
            message="Monthly opportunity created"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/fund")
async def get_newcomer_support_fund():
    """Get Newcomer Support fund status"""
    try:
        fund = NewcomerSupportFund.objects(is_active=True).first()
        if not fund:
            # Create default fund
            fund = NewcomerSupportFund()
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
            message="Newcomer Support fund status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/fund")
async def update_newcomer_support_fund(request: NewcomerSupportFundRequest):
    """Update Newcomer Support fund"""
    try:
        fund = NewcomerSupportFund.objects(is_active=True).first()
        if not fund:
            fund = NewcomerSupportFund()
        
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
                "message": "Newcomer Support fund updated successfully"
            },
            message="Newcomer Support fund updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/settings")
async def get_newcomer_support_settings():
    """Get Newcomer Support system settings"""
    try:
        settings = NewcomerSupportSettings.objects(is_active=True).first()
        if not settings:
            # Create default settings
            settings = NewcomerSupportSettings()
            settings.save()
        
        return success_response(
            data={
                "newcomer_support_enabled": settings.newcomer_support_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_bonus_distribution": settings.auto_bonus_distribution,
                "eligibility_requirements": {
                    "require_matrix_program": settings.require_matrix_program,
                    "newcomer_period_days": settings.newcomer_period_days
                },
                "bonus_settings": {
                    "instant_bonus_amount": settings.instant_bonus_amount,
                    "monthly_opportunities_count": settings.monthly_opportunities_count,
                    "upline_rank_bonus_percentage": settings.upline_rank_bonus_percentage
                },
                "payment_settings": {
                    "payment_currency": settings.payment_currency,
                    "payment_method": settings.payment_method,
                    "payment_delay_hours": settings.payment_delay_hours
                },
                "last_updated": settings.last_updated
            },
            message="Newcomer Support settings retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/settings")
async def update_newcomer_support_settings(request: NewcomerSupportSettingsRequest):
    """Update Newcomer Support system settings"""
    try:
        settings = NewcomerSupportSettings.objects(is_active=True).first()
        if not settings:
            settings = NewcomerSupportSettings()
        
        settings.newcomer_support_enabled = request.newcomer_support_enabled
        settings.auto_eligibility_check = request.auto_eligibility_check
        settings.auto_bonus_distribution = request.auto_bonus_distribution
        settings.require_matrix_program = request.require_matrix_program
        settings.newcomer_period_days = request.newcomer_period_days
        settings.instant_bonus_amount = request.instant_bonus_amount
        settings.monthly_opportunities_count = request.monthly_opportunities_count
        settings.upline_rank_bonus_percentage = request.upline_rank_bonus_percentage
        settings.last_updated = datetime.utcnow()
        settings.save()
        
        return success_response(
            data={
                "settings_id": str(settings.id),
                "newcomer_support_enabled": settings.newcomer_support_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_bonus_distribution": settings.auto_bonus_distribution,
                "require_matrix_program": settings.require_matrix_program,
                "newcomer_period_days": settings.newcomer_period_days,
                "instant_bonus_amount": settings.instant_bonus_amount,
                "monthly_opportunities_count": settings.monthly_opportunities_count,
                "upline_rank_bonus_percentage": settings.upline_rank_bonus_percentage,
                "last_updated": settings.last_updated,
                "message": "Newcomer Support settings updated successfully"
            },
            message="Newcomer Support settings updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/statistics")
async def get_newcomer_support_statistics(period: str = Query("all_time", regex="^(daily|weekly|monthly|all_time)$")):
    """Get Newcomer Support program statistics"""
    try:
        statistics = NewcomerSupportStatistics.objects(period=period, is_active=True).order_by('-last_updated').first()
        
        if not statistics:
            return success_response(
                data={
                    "period": period,
                    "statistics": {
                        "total_eligible_users": 0,
                        "total_active_users": 0,
                        "total_bonuses_paid": 0,
                        "total_amount_distributed": 0.0,
                        "bonus_breakdown": {
                            "instant_bonuses_paid": 0,
                            "instant_bonuses_amount": 0.0,
                            "monthly_opportunities_given": 0,
                            "monthly_opportunities_amount": 0.0,
                            "upline_rank_bonuses_paid": 0,
                            "upline_rank_bonuses_amount": 0.0
                        },
                        "growth_statistics": {
                            "new_eligible_users": 0,
                            "new_bonus_earners": 0,
                            "total_newcomers": 0,
                            "total_matrix_joins": 0
                        }
                    },
                    "message": "No statistics available for this period"
                },
                message="Newcomer Support statistics retrieved"
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
                    "bonus_breakdown": {
                        "instant_bonuses_paid": statistics.instant_bonuses_paid,
                        "instant_bonuses_amount": statistics.instant_bonuses_amount,
                        "monthly_opportunities_given": statistics.monthly_opportunities_given,
                        "monthly_opportunities_amount": statistics.monthly_opportunities_amount,
                        "upline_rank_bonuses_paid": statistics.upline_rank_bonuses_paid,
                        "upline_rank_bonuses_amount": statistics.upline_rank_bonuses_amount
                    },
                    "growth_statistics": {
                        "new_eligible_users": statistics.new_eligible_users,
                        "new_bonus_earners": statistics.new_bonus_earners,
                        "total_newcomers": statistics.total_newcomers,
                        "total_matrix_joins": statistics.total_matrix_joins
                    }
                },
                "last_updated": statistics.last_updated
            },
            message="Newcomer Support statistics retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/leaderboard")
async def get_newcomer_support_leaderboard(limit: int = Query(50, le=100)):
    """Get Newcomer Support leaderboard"""
    try:
        # Get top Newcomer Support participants
        newcomer_supports = NewcomerSupport.objects(is_active=True).order_by('-total_bonuses_earned', '-monthly_opportunities_count').limit(limit)
        
        leaderboard_data = []
        for newcomer_support in newcomer_supports:
            leaderboard_data.append({
                "user_id": str(newcomer_support.user_id),
                "total_bonuses_earned": newcomer_support.total_bonuses_earned,
                "total_bonuses_claimed": newcomer_support.total_bonuses_claimed,
                "pending_bonuses": newcomer_support.pending_bonuses,
                "instant_bonus_claimed": newcomer_support.instant_bonus_claimed,
                "monthly_opportunities_count": newcomer_support.monthly_opportunities_count,
                "upline_rank_bonus_claimed": newcomer_support.upline_rank_bonus_claimed,
                "has_matrix_program": newcomer_support.has_matrix_program,
                "is_eligible": newcomer_support.is_eligible,
                "joined_at": newcomer_support.joined_at
            })
        
        return success_response(
            data={
                "leaderboard": leaderboard_data,
                "total_participants": len(leaderboard_data),
                "message": "Newcomer Support leaderboard retrieved"
            },
            message="Newcomer Support leaderboard retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

# Helper functions
def _initialize_newcomer_bonuses() -> List[NewcomerBonus]:
    """Initialize Newcomer bonuses"""
    return [
        NewcomerBonus(
            bonus_type="instant",
            bonus_name="Instant Bonus",
            bonus_amount=50.0,
            currency="USDT"
        ),
        NewcomerBonus(
            bonus_type="monthly",
            bonus_name="Monthly Opportunities",
            bonus_amount=0.0,
            currency="USDT"
        ),
        NewcomerBonus(
            bonus_type="upline_rank",
            bonus_name="Upline Rank Bonus",
            bonus_amount=0.0,
            bonus_percentage=10.0,
            currency="USDT"
        )
    ]

def _check_matrix_program_status(user_id: str) -> Dict[str, Any]:
    """Check Matrix program status for user"""
    try:
        # This would need to be implemented based on actual Matrix program
        # For now, returning mock data
        return {
            "has_matrix": False,
            "join_date": None,
            "slots_activated": 0
        }
    except Exception:
        return {
            "has_matrix": False,
            "join_date": None,
            "slots_activated": 0
        }

def _check_newcomer_status(user_id: str) -> Dict[str, Any]:
    """Check newcomer status for user"""
    try:
        # Check if user is within 30 days of joining
        user = User.objects(id=ObjectId(user_id)).first()
        if user and user.created_at:
            days_since_join = (datetime.utcnow() - user.created_at).days
            is_newcomer = days_since_join <= 30
            end_date = user.created_at + timedelta(days=30) if is_newcomer else None
        else:
            is_newcomer = False
            end_date = None
        
        return {
            "is_newcomer": is_newcomer,
            "end_date": end_date
        }
    except Exception:
        return {
            "is_newcomer": False,
            "end_date": None
        }

def _get_bonus_name(bonus_type: str) -> str:
    """Get bonus name for given type"""
    bonus_names = {
        "instant": "Instant Bonus",
        "monthly": "Monthly Opportunity",
        "upline_rank": "Upline Rank Bonus"
    }
    return bonus_names.get(bonus_type, "Unknown Bonus")

def _get_source_type(bonus_type: str) -> str:
    """Get source type for given bonus type"""
    source_types = {
        "instant": "matrix_join",
        "monthly": "monthly_activity",
        "upline_rank": "upline_rank_match"
    }
    return source_types.get(bonus_type, "unknown")

def _get_source_description(bonus_type: str) -> str:
    """Get source description for given bonus type"""
    descriptions = {
        "instant": "Instant bonus upon joining Matrix program",
        "monthly": "Monthly earning opportunity based on upline activity",
        "upline_rank": "Bonus for achieving same rank as upline"
    }
    return descriptions.get(bonus_type, "Unknown source")

def _get_opportunity_description(opportunity_type: str) -> str:
    """Get opportunity description for given type"""
    descriptions = {
        "upline_activity": "Monthly opportunity based on upline activity",
        "team_growth": "Monthly opportunity based on team growth",
        "personal_achievement": "Monthly opportunity based on personal achievement"
    }
    return descriptions.get(opportunity_type, "Unknown opportunity")

def _get_eligibility_reasons(eligibility: NewcomerSupportEligibility) -> List[str]:
    """Get eligibility reasons"""
    reasons = []
    
    if not eligibility.has_matrix_program:
        reasons.append("Matrix program not joined")
    
    if not eligibility.is_newcomer:
        reasons.append("Not within newcomer period (30 days)")
    
    return reasons

