from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from ..user.model import User
from .model import (
    LeadershipStipend, LeadershipStipendEligibility, LeadershipStipendPayment,
    LeadershipStipendFund, LeadershipStipendSettings, LeadershipStipendLog, 
    LeadershipStipendStatistics, LeadershipStipendCalculation, LeadershipStipendTier
)
from utils.response import success_response, error_response

router = APIRouter(prefix="/leadership-stipend", tags=["Leadership Stipend"])

# Pydantic models for request/response
class LeadershipStipendJoinRequest(BaseModel):
    user_id: str

class LeadershipStipendEligibilityRequest(BaseModel):
    user_id: str
    force_check: bool = False

class LeadershipStipendPaymentRequest(BaseModel):
    user_id: str
    slot_number: int
    amount: float

class LeadershipStipendSettingsRequest(BaseModel):
    leadership_stipend_enabled: bool
    auto_eligibility_check: bool
    auto_daily_calculation: bool
    auto_payment_distribution: bool
    min_slot_for_eligibility: int
    max_slot_for_eligibility: int
    calculation_frequency: str
    tier_multiplier: float

class LeadershipStipendFundRequest(BaseModel):
    fund_amount: float
    currency: str = "BNB"
    source: str

class LeadershipStipendCalculationRequest(BaseModel):
    calculation_date: str
    calculation_type: str = "daily"

# API Endpoints

@router.post("/join")
async def join_leadership_stipend(request: LeadershipStipendJoinRequest):
    """Join Leadership Stipend program"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if already joined
        existing = LeadershipStipend.objects(user_id=ObjectId(request.user_id)).first()
        if existing:
            return success_response(
                data={
                    "user_id": request.user_id,
                    "status": "already_joined",
                    "current_tier": existing.current_tier,
                    "current_daily_return": existing.current_daily_return,
                    "total_earned": existing.total_earned,
                    "message": "User already joined Leadership Stipend program"
                },
                message="Already joined Leadership Stipend"
            )
        
        # Create Leadership Stipend record
        leadership_stipend = LeadershipStipend(
            user_id=ObjectId(request.user_id),
            joined_at=datetime.utcnow(),
            is_active=True
        )
        
        # Initialize tiers
        leadership_stipend.tiers = _initialize_leadership_stipend_tiers()
        
        leadership_stipend.save()
        
        return success_response(
            data={
                "leadership_stipend_id": str(leadership_stipend.id),
                "user_id": request.user_id,
                "current_tier": 0,
                "is_eligible": False,
                "is_active": True,
                "joined_at": leadership_stipend.joined_at,
                "message": "Successfully joined Leadership Stipend program"
            },
            message="Joined Leadership Stipend program"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/eligibility/{user_id}")
async def check_leadership_stipend_eligibility(user_id: str):
    """Check Leadership Stipend eligibility for user"""
    try:
        # Get Leadership Stipend record
        leadership_stipend = LeadershipStipend.objects(user_id=ObjectId(user_id)).first()
        if not leadership_stipend:
            raise HTTPException(status_code=404, detail="User not in Leadership Stipend program")
        
        # Get eligibility record
        eligibility = LeadershipStipendEligibility.objects(user_id=ObjectId(user_id)).first()
        if not eligibility:
            eligibility = LeadershipStipendEligibility(user_id=ObjectId(user_id))
        
        # Check slot requirements
        slot_status = _check_slot_requirements(user_id)
        eligibility.highest_slot_activated = slot_status["highest_slot"]
        eligibility.slots_10_16_activated = slot_status["slots_10_16"]
        
        # Determine eligibility
        eligibility.is_eligible_for_stipend = (
            eligibility.highest_slot_activated >= 10
        )
        
        # Update eligibility reasons
        eligibility_reasons = _get_eligibility_reasons(eligibility)
        eligibility.eligibility_reasons = eligibility_reasons
        
        if eligibility.is_eligible_for_stipend and not leadership_stipend.is_eligible:
            eligibility.qualified_at = datetime.utcnow()
            leadership_stipend.is_eligible = True
            leadership_stipend.qualified_at = datetime.utcnow()
            leadership_stipend.current_tier = eligibility.highest_slot_activated
            leadership_stipend.highest_slot_achieved = eligibility.highest_slot_activated
            
            # Set current tier details
            current_tier_info = _get_tier_info(eligibility.highest_slot_activated)
            leadership_stipend.current_tier_name = current_tier_info["tier_name"]
            leadership_stipend.current_daily_return = current_tier_info["daily_return"]
        
        eligibility.last_checked = datetime.utcnow()
        eligibility.save()
        
        leadership_stipend.last_updated = datetime.utcnow()
        leadership_stipend.save()
        
        return success_response(
            data={
                "user_id": user_id,
                "is_eligible": eligibility.is_eligible_for_stipend,
                "slot_status": {
                    "highest_slot_activated": eligibility.highest_slot_activated,
                    "slots_10_16_activated": eligibility.slots_10_16_activated,
                    "min_slot_required": eligibility.min_slot_required
                },
                "current_tier": {
                    "slot_number": leadership_stipend.current_tier,
                    "tier_name": leadership_stipend.current_tier_name,
                    "daily_return": leadership_stipend.current_daily_return
                },
                "eligibility_reasons": eligibility.eligibility_reasons,
                "qualified_at": eligibility.qualified_at,
                "last_checked": eligibility.last_checked
            },
            message="Leadership Stipend eligibility checked"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/status/{user_id}")
async def get_leadership_stipend_status(user_id: str):
    """Get Leadership Stipend status and progress"""
    try:
        leadership_stipend = LeadershipStipend.objects(user_id=ObjectId(user_id)).first()
        if not leadership_stipend:
            raise HTTPException(status_code=404, detail="User not in Leadership Stipend program")
        
        return success_response(
            data={
                "user_id": user_id,
                "program_status": {
                    "is_eligible": leadership_stipend.is_eligible,
                    "is_active": leadership_stipend.is_active,
                    "current_tier": leadership_stipend.current_tier,
                    "current_tier_name": leadership_stipend.current_tier_name,
                    "current_daily_return": leadership_stipend.current_daily_return,
                    "joined_at": leadership_stipend.joined_at,
                    "qualified_at": leadership_stipend.qualified_at
                },
                "tier_status": [
                    {
                        "slot_number": tier.slot_number,
                        "tier_name": tier.tier_name,
                        "slot_value": tier.slot_value,
                        "daily_return": tier.daily_return,
                        "currency": tier.currency,
                        "is_active": tier.is_active,
                        "activated_at": tier.activated_at,
                        "total_earned": tier.total_earned,
                        "total_paid": tier.total_paid,
                        "pending_amount": tier.pending_amount
                    } for tier in leadership_stipend.tiers
                ],
                "earnings_summary": {
                    "total_earned": leadership_stipend.total_earned,
                    "total_paid": leadership_stipend.total_paid,
                    "pending_amount": leadership_stipend.pending_amount,
                    "last_payment_date": leadership_stipend.last_payment_date
                },
                "slot_status": {
                    "highest_slot_achieved": leadership_stipend.highest_slot_achieved,
                    "slots_activated": leadership_stipend.slots_activated
                },
                "calculation_settings": {
                    "daily_calculation_enabled": leadership_stipend.daily_calculation_enabled,
                    "last_calculation_date": leadership_stipend.last_calculation_date,
                    "calculation_frequency": leadership_stipend.calculation_frequency
                },
                "last_updated": leadership_stipend.last_updated
            },
            message="Leadership Stipend status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/payments/{user_id}")
async def get_leadership_stipend_payments(user_id: str, limit: int = Query(50, le=100)):
    """Get Leadership Stipend payments for user"""
    try:
        payments = LeadershipStipendPayment.objects(user_id=ObjectId(user_id)).order_by('-created_at').limit(limit)
        
        return success_response(
            data={
                "payments": [
                    {
                        "id": str(payment.id),
                        "slot_number": payment.slot_number,
                        "tier_name": payment.tier_name,
                        "daily_return_amount": payment.daily_return_amount,
                        "currency": payment.currency,
                        "payment_date": payment.payment_date,
                        "payment_period_start": payment.payment_period_start,
                        "payment_period_end": payment.payment_period_end,
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
            message="Leadership Stipend payments retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/payment")
async def create_leadership_stipend_payment(request: LeadershipStipendPaymentRequest):
    """Create Leadership Stipend payment"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get Leadership Stipend record
        leadership_stipend = LeadershipStipend.objects(user_id=ObjectId(request.user_id)).first()
        if not leadership_stipend:
            raise HTTPException(status_code=404, detail="User not in Leadership Stipend program")
        
        # Validate slot number
        if request.slot_number < 10 or request.slot_number > 16:
            raise HTTPException(status_code=400, detail="Invalid slot number (must be 10-16)")
        
        # Get tier info
        tier_info = _get_tier_info(request.slot_number)
        
        # Create payment
        payment = LeadershipStipendPayment(
            user_id=ObjectId(request.user_id),
            leadership_stipend_id=leadership_stipend.id,
            slot_number=request.slot_number,
            tier_name=tier_info["tier_name"],
            daily_return_amount=request.amount,
            currency="BNB",
            payment_date=datetime.utcnow(),
            payment_period_start=datetime.utcnow(),
            payment_period_end=datetime.utcnow(),
            payment_status="pending"
        )
        payment.save()
        
        return success_response(
            data={
                "payment_id": str(payment.id),
                "user_id": request.user_id,
                "slot_number": request.slot_number,
                "tier_name": tier_info["tier_name"],
                "daily_return_amount": request.amount,
                "currency": "BNB",
                "payment_status": "pending",
                "message": "Leadership Stipend payment created successfully"
            },
            message="Leadership Stipend payment created"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/fund")
async def get_leadership_stipend_fund():
    """Get Leadership Stipend fund status"""
    try:
        fund = LeadershipStipendFund.objects(is_active=True).first()
        if not fund:
            # Create default fund
            fund = LeadershipStipendFund()
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
                    "total_payments_made": fund.total_payments_made,
                    "total_amount_distributed": fund.total_amount_distributed
                },
                "last_updated": fund.last_updated
            },
            message="Leadership Stipend fund status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/fund")
async def update_leadership_stipend_fund(request: LeadershipStipendFundRequest):
    """Update Leadership Stipend fund"""
    try:
        fund = LeadershipStipendFund.objects(is_active=True).first()
        if not fund:
            fund = LeadershipStipendFund()
        
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
                "message": "Leadership Stipend fund updated successfully"
            },
            message="Leadership Stipend fund updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/settings")
async def get_leadership_stipend_settings():
    """Get Leadership Stipend system settings"""
    try:
        settings = LeadershipStipendSettings.objects(is_active=True).first()
        if not settings:
            # Create default settings
            settings = LeadershipStipendSettings()
            settings.save()
        
        return success_response(
            data={
                "leadership_stipend_enabled": settings.leadership_stipend_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_daily_calculation": settings.auto_daily_calculation,
                "auto_payment_distribution": settings.auto_payment_distribution,
                "eligibility_requirements": {
                    "min_slot_for_eligibility": settings.min_slot_for_eligibility,
                    "max_slot_for_eligibility": settings.max_slot_for_eligibility
                },
                "calculation_settings": {
                    "calculation_frequency": settings.calculation_frequency,
                    "calculation_time": settings.calculation_time,
                    "tier_multiplier": settings.tier_multiplier
                },
                "payment_settings": {
                    "payment_currency": settings.payment_currency,
                    "payment_method": settings.payment_method,
                    "payment_delay_hours": settings.payment_delay_hours
                },
                "last_updated": settings.last_updated
            },
            message="Leadership Stipend settings retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/settings")
async def update_leadership_stipend_settings(request: LeadershipStipendSettingsRequest):
    """Update Leadership Stipend system settings"""
    try:
        settings = LeadershipStipendSettings.objects(is_active=True).first()
        if not settings:
            settings = LeadershipStipendSettings()
        
        settings.leadership_stipend_enabled = request.leadership_stipend_enabled
        settings.auto_eligibility_check = request.auto_eligibility_check
        settings.auto_daily_calculation = request.auto_daily_calculation
        settings.auto_payment_distribution = request.auto_payment_distribution
        settings.min_slot_for_eligibility = request.min_slot_for_eligibility
        settings.max_slot_for_eligibility = request.max_slot_for_eligibility
        settings.calculation_frequency = request.calculation_frequency
        settings.tier_multiplier = request.tier_multiplier
        settings.last_updated = datetime.utcnow()
        settings.save()
        
        return success_response(
            data={
                "settings_id": str(settings.id),
                "leadership_stipend_enabled": settings.leadership_stipend_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_daily_calculation": settings.auto_daily_calculation,
                "auto_payment_distribution": settings.auto_payment_distribution,
                "min_slot_for_eligibility": settings.min_slot_for_eligibility,
                "max_slot_for_eligibility": settings.max_slot_for_eligibility,
                "calculation_frequency": settings.calculation_frequency,
                "tier_multiplier": settings.tier_multiplier,
                "last_updated": settings.last_updated,
                "message": "Leadership Stipend settings updated successfully"
            },
            message="Leadership Stipend settings updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/statistics")
async def get_leadership_stipend_statistics(period: str = Query("all_time", regex="^(daily|weekly|monthly|all_time)$")):
    """Get Leadership Stipend program statistics"""
    try:
        statistics = LeadershipStipendStatistics.objects(period=period, is_active=True).order_by('-last_updated').first()
        
        if not statistics:
            return success_response(
                data={
                    "period": period,
                    "statistics": {
                        "total_eligible_users": 0,
                        "total_active_users": 0,
                        "total_payments_made": 0,
                        "total_amount_distributed": 0.0,
                        "tier_statistics": {
                            "tier_10": 0,  # LEADER
                            "tier_11": 0,  # VANGURD
                            "tier_12": 0,  # CENTER
                            "tier_13": 0,  # CLIMAX
                            "tier_14": 0,  # ENTERNITY
                            "tier_15": 0,  # KING
                            "tier_16": 0   # COMMENDER
                        },
                        "growth_statistics": {
                            "new_eligible_users": 0,
                            "new_payment_recipients": 0,
                            "total_slots_activated": 0
                        }
                    },
                    "message": "No statistics available for this period"
                },
                message="Leadership Stipend statistics retrieved"
            )
        
        return success_response(
            data={
                "period": statistics.period,
                "period_start": statistics.period_start,
                "period_end": statistics.period_end,
                "statistics": {
                    "total_eligible_users": statistics.total_eligible_users,
                    "total_active_users": statistics.total_active_users,
                    "total_payments_made": statistics.total_payments_made,
                    "total_amount_distributed": statistics.total_amount_distributed,
                    "tier_statistics": {
                        "tier_10": statistics.tier_10_users,
                        "tier_11": statistics.tier_11_users,
                        "tier_12": statistics.tier_12_users,
                        "tier_13": statistics.tier_13_users,
                        "tier_14": statistics.tier_14_users,
                        "tier_15": statistics.tier_15_users,
                        "tier_16": statistics.tier_16_users
                    },
                    "growth_statistics": {
                        "new_eligible_users": statistics.new_eligible_users,
                        "new_payment_recipients": statistics.new_payment_recipients,
                        "total_slots_activated": statistics.total_slots_activated
                    }
                },
                "last_updated": statistics.last_updated
            },
            message="Leadership Stipend statistics retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/leaderboard")
async def get_leadership_stipend_leaderboard(limit: int = Query(50, le=100)):
    """Get Leadership Stipend leaderboard"""
    try:
        # Get top Leadership Stipend participants
        leadership_stipends = LeadershipStipend.objects(is_active=True).order_by('-total_earned', '-highest_slot_achieved').limit(limit)
        
        leaderboard_data = []
        for ls in leadership_stipends:
            leaderboard_data.append({
                "user_id": str(ls.user_id),
                "current_tier": ls.current_tier,
                "current_tier_name": ls.current_tier_name,
                "current_daily_return": ls.current_daily_return,
                "total_earned": ls.total_earned,
                "total_paid": ls.total_paid,
                "pending_amount": ls.pending_amount,
                "highest_slot_achieved": ls.highest_slot_achieved,
                "is_eligible": ls.is_eligible,
                "joined_at": ls.joined_at
            })
        
        return success_response(
            data={
                "leaderboard": leaderboard_data,
                "total_participants": len(leaderboard_data),
                "message": "Leadership Stipend leaderboard retrieved"
            },
            message="Leadership Stipend leaderboard retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/calculate")
async def run_daily_calculation(request: LeadershipStipendCalculationRequest, background_tasks: BackgroundTasks):
    """Run daily stipend calculation"""
    try:
        # Add to background task for calculation
        background_tasks.add_task(_run_daily_calculation_background, request.calculation_date, request.calculation_type)
        
        return success_response(
            data={
                "calculation_date": request.calculation_date,
                "calculation_type": request.calculation_type,
                "message": "Daily calculation queued for processing"
            },
            message="Daily calculation initiated"
        )
        
    except Exception as e:
        return error_response(str(e))

# Helper functions
def _initialize_leadership_stipend_tiers() -> List[LeadershipStipendTier]:
    """Initialize Leadership Stipend tiers based on PROJECT_DOCUMENTATION.md"""
    return [
        LeadershipStipendTier(slot_number=10, tier_name="LEADER", slot_value=1.1264, daily_return=2.2528),
        LeadershipStipendTier(slot_number=11, tier_name="VANGURD", slot_value=2.2528, daily_return=4.5056),
        LeadershipStipendTier(slot_number=12, tier_name="CENTER", slot_value=4.5056, daily_return=9.0112),
        LeadershipStipendTier(slot_number=13, tier_name="CLIMAX", slot_value=9.0112, daily_return=18.0224),
        LeadershipStipendTier(slot_number=14, tier_name="ENTERNITY", slot_value=18.0224, daily_return=36.0448),
        LeadershipStipendTier(slot_number=15, tier_name="KING", slot_value=36.0448, daily_return=72.0896),
        LeadershipStipendTier(slot_number=16, tier_name="COMMENDER", slot_value=72.0896, daily_return=144.1792)
    ]

def _check_slot_requirements(user_id: str) -> Dict[str, Any]:
    """Check slot requirements for user"""
    try:
        # This would need to be implemented based on actual slot activation
        # For now, returning mock data
        return {
            "highest_slot": 0,
            "slots_10_16": []
        }
    except Exception:
        return {
            "highest_slot": 0,
            "slots_10_16": []
        }

def _get_tier_info(slot_number: int) -> Dict[str, Any]:
    """Get tier information for slot number"""
    tier_mapping = {
        10: {"tier_name": "LEADER", "daily_return": 2.2528},
        11: {"tier_name": "VANGURD", "daily_return": 4.5056},
        12: {"tier_name": "CENTER", "daily_return": 9.0112},
        13: {"tier_name": "CLIMAX", "daily_return": 18.0224},
        14: {"tier_name": "ENTERNITY", "daily_return": 36.0448},
        15: {"tier_name": "KING", "daily_return": 72.0896},
        16: {"tier_name": "COMMENDER", "daily_return": 144.1792}
    }
    return tier_mapping.get(slot_number, {"tier_name": "UNKNOWN", "daily_return": 0.0})

def _get_eligibility_reasons(eligibility: LeadershipStipendEligibility) -> List[str]:
    """Get eligibility reasons"""
    reasons = []
    
    if eligibility.highest_slot_activated < 10:
        needed = 10 - eligibility.highest_slot_activated
        reasons.append(f"Need to activate slot {needed} more to reach slot 10")
    
    return reasons

async def _run_daily_calculation_background(calculation_date: str, calculation_type: str):
    """Background task to run daily calculation"""
    # Implementation for background calculation
    pass
