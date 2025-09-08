from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from ..user.model import User
from .model import (
    Mentorship, MentorshipEligibility, MentorshipCommission,
    MentorshipFund, MentorshipSettings, MentorshipLog, 
    MentorshipStatistics, MentorshipReferral, MentorshipLevel
)
from utils.response import success_response, error_response

router = APIRouter(prefix="/mentorship", tags=["Mentorship Bonus"])

# Pydantic models for request/response
class MentorshipJoinRequest(BaseModel):
    user_id: str

class MentorshipEligibilityRequest(BaseModel):
    user_id: str
    force_check: bool = False

class MentorshipCommissionRequest(BaseModel):
    user_id: str
    commission_type: str
    commission_level: str
    source_user_id: str
    source_amount: float

class MentorshipSettingsRequest(BaseModel):
    mentorship_enabled: bool
    auto_eligibility_check: bool
    auto_commission_distribution: bool
    require_matrix_program: bool
    min_matrix_slots_required: int
    min_direct_referrals_required: int
    direct_commission_percentage: float
    direct_of_direct_commission_percentage: float

class MentorshipFundRequest(BaseModel):
    fund_amount: float
    currency: str = "USDT"
    source: str

class MentorshipReferralRequest(BaseModel):
    mentor_id: str
    upline_id: str
    referral_id: str
    relationship_level: int

# API Endpoints

@router.post("/join")
async def join_mentorship(request: MentorshipJoinRequest):
    """Join Mentorship Bonus program"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if already joined
        existing = Mentorship.objects(user_id=ObjectId(request.user_id)).first()
        if existing:
            return success_response(
                data={
                    "user_id": request.user_id,
                    "status": "already_joined",
                    "total_commissions_earned": existing.total_commissions_earned,
                    "direct_referrals_count": existing.direct_referrals_count,
                    "direct_of_direct_referrals_count": existing.direct_of_direct_referrals_count,
                    "message": "User already joined Mentorship program"
                },
                message="Already joined Mentorship"
            )
        
        # Create Mentorship record
        mentorship = Mentorship(
            user_id=ObjectId(request.user_id),
            joined_at=datetime.utcnow(),
            is_active=True
        )
        
        # Initialize levels
        mentorship.levels = _initialize_mentorship_levels()
        
        mentorship.save()
        
        return success_response(
            data={
                "mentorship_id": str(mentorship.id),
                "user_id": request.user_id,
                "is_eligible": False,
                "is_active": True,
                "joined_at": mentorship.joined_at,
                "message": "Successfully joined Mentorship program"
            },
            message="Joined Mentorship program"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/eligibility/{user_id}")
async def check_mentorship_eligibility(user_id: str):
    """Check Mentorship eligibility for user"""
    try:
        # Get Mentorship record
        mentorship = Mentorship.objects(user_id=ObjectId(user_id)).first()
        if not mentorship:
            raise HTTPException(status_code=404, detail="User not in Mentorship program")
        
        # Get eligibility record
        eligibility = MentorshipEligibility.objects(user_id=ObjectId(user_id)).first()
        if not eligibility:
            eligibility = MentorshipEligibility(user_id=ObjectId(user_id))
        
        # Check Matrix program status
        matrix_status = _check_matrix_program_status(user_id)
        eligibility.has_matrix_program = matrix_status["has_matrix"]
        eligibility.matrix_slots_activated = matrix_status["slots_activated"]
        
        # Check direct referrals
        referrals_status = _check_direct_referrals(user_id)
        eligibility.direct_referrals_count = referrals_status["direct_count"]
        
        # Update Mentorship record
        mentorship.matrix_program_active = matrix_status["has_matrix"]
        mentorship.matrix_slots_activated = matrix_status["slots_activated"]
        mentorship.direct_referrals = referrals_status["direct_list"]
        mentorship.direct_referrals_count = referrals_status["direct_count"]
        
        # Determine eligibility
        eligibility.is_eligible_for_mentorship = (
            eligibility.has_matrix_program and
            eligibility.direct_referrals_count >= 1
        )
        
        # Update eligibility reasons
        eligibility_reasons = _get_eligibility_reasons(eligibility)
        eligibility.eligibility_reasons = eligibility_reasons
        
        if eligibility.is_eligible_for_mentorship and not mentorship.is_eligible:
            eligibility.qualified_at = datetime.utcnow()
            mentorship.is_eligible = True
            mentorship.qualified_at = datetime.utcnow()
            
            # Activate levels
            for level in mentorship.levels:
                level.is_active = True
                level.activated_at = datetime.utcnow()
        
        eligibility.last_checked = datetime.utcnow()
        eligibility.save()
        
        mentorship.last_updated = datetime.utcnow()
        mentorship.save()
        
        return success_response(
            data={
                "user_id": user_id,
                "is_eligible": eligibility.is_eligible_for_mentorship,
                "matrix_program": {
                    "has_matrix_program": eligibility.has_matrix_program,
                    "matrix_slots_activated": eligibility.matrix_slots_activated,
                    "min_matrix_slots_required": eligibility.min_matrix_slots_required
                },
                "direct_referrals": {
                    "direct_referrals_count": eligibility.direct_referrals_count,
                    "min_direct_referrals_required": eligibility.min_direct_referrals_required
                },
                "eligibility_reasons": eligibility.eligibility_reasons,
                "qualified_at": eligibility.qualified_at,
                "last_checked": eligibility.last_checked
            },
            message="Mentorship eligibility checked"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/status/{user_id}")
async def get_mentorship_status(user_id: str):
    """Get Mentorship status and progress"""
    try:
        mentorship = Mentorship.objects(user_id=ObjectId(user_id)).first()
        if not mentorship:
            raise HTTPException(status_code=404, detail="User not in Mentorship program")
        
        return success_response(
            data={
                "user_id": user_id,
                "program_status": {
                    "is_eligible": mentorship.is_eligible,
                    "is_active": mentorship.is_active,
                    "joined_at": mentorship.joined_at,
                    "qualified_at": mentorship.qualified_at
                },
                "level_status": [
                    {
                        "level_number": level.level_number,
                        "level_name": level.level_name,
                        "commission_percentage": level.commission_percentage,
                        "is_active": level.is_active,
                        "activated_at": level.activated_at,
                        "total_earned": level.total_earned,
                        "total_paid": level.total_paid,
                        "pending_amount": level.pending_amount
                    } for level in mentorship.levels
                ],
                "referrals_summary": {
                    "direct_referrals_count": mentorship.direct_referrals_count,
                    "direct_of_direct_referrals_count": mentorship.direct_of_direct_referrals_count,
                    "total_referrals": mentorship.direct_referrals_count + mentorship.direct_of_direct_referrals_count
                },
                "commissions_summary": {
                    "total_commissions_earned": mentorship.total_commissions_earned,
                    "total_commissions_paid": mentorship.total_commissions_paid,
                    "pending_commissions": mentorship.pending_commissions,
                    "direct_commissions": mentorship.direct_commissions,
                    "direct_of_direct_commissions": mentorship.direct_of_direct_commissions
                },
                "matrix_status": {
                    "matrix_program_active": mentorship.matrix_program_active,
                    "matrix_slots_activated": mentorship.matrix_slots_activated
                },
                "last_updated": mentorship.last_updated
            },
            message="Mentorship status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/commissions/{user_id}")
async def get_mentorship_commissions(user_id: str, limit: int = Query(50, le=100)):
    """Get Mentorship commissions for user"""
    try:
        commissions = MentorshipCommission.objects(user_id=ObjectId(user_id)).order_by('-created_at').limit(limit)
        
        return success_response(
            data={
                "commissions": [
                    {
                        "id": str(commission.id),
                        "commission_type": commission.commission_type,
                        "commission_level": commission.commission_level,
                        "commission_percentage": commission.commission_percentage,
                        "source_user_id": str(commission.source_user_id),
                        "source_user_level": commission.source_user_level,
                        "source_amount": commission.source_amount,
                        "commission_amount": commission.commission_amount,
                        "payment_status": commission.payment_status,
                        "payment_method": commission.payment_method,
                        "payment_reference": commission.payment_reference,
                        "processed_at": commission.processed_at,
                        "paid_at": commission.paid_at,
                        "failed_reason": commission.failed_reason,
                        "created_at": commission.created_at
                    } for commission in commissions
                ],
                "total_commissions": len(commissions)
            },
            message="Mentorship commissions retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/commission")
async def create_mentorship_commission(request: MentorshipCommissionRequest):
    """Create Mentorship commission"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get Mentorship record
        mentorship = Mentorship.objects(user_id=ObjectId(request.user_id)).first()
        if not mentorship:
            raise HTTPException(status_code=404, detail="User not in Mentorship program")
        
        # Validate commission type and level
        if request.commission_type not in ['joining', 'slot_upgrade']:
            raise HTTPException(status_code=400, detail="Invalid commission type")
        
        if request.commission_level not in ['direct', 'direct_of_direct']:
            raise HTTPException(status_code=400, detail="Invalid commission level")
        
        # Calculate commission amount
        commission_percentage = 10.0  # 10% commission
        commission_amount = request.source_amount * (commission_percentage / 100)
        
        # Create commission
        commission = MentorshipCommission(
            user_id=ObjectId(request.user_id),
            mentorship_id=mentorship.id,
            commission_type=request.commission_type,
            commission_level=request.commission_level,
            commission_percentage=commission_percentage,
            source_user_id=ObjectId(request.source_user_id),
            source_user_level=1 if request.commission_level == 'direct' else 2,
            source_amount=request.source_amount,
            commission_amount=commission_amount,
            payment_status="pending"
        )
        commission.save()
        
        # Update Mentorship record
        mentorship.total_commissions_earned += commission_amount
        mentorship.pending_commissions += commission_amount
        
        if request.commission_level == 'direct':
            mentorship.direct_commissions += commission_amount
        else:
            mentorship.direct_of_direct_commissions += commission_amount
        
        mentorship.last_updated = datetime.utcnow()
        mentorship.save()
        
        return success_response(
            data={
                "commission_id": str(commission.id),
                "user_id": request.user_id,
                "commission_type": request.commission_type,
                "commission_level": request.commission_level,
                "commission_percentage": commission_percentage,
                "source_amount": request.source_amount,
                "commission_amount": commission_amount,
                "payment_status": "pending",
                "message": "Mentorship commission created successfully"
            },
            message="Mentorship commission created"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/fund")
async def get_mentorship_fund():
    """Get Mentorship fund status"""
    try:
        fund = MentorshipFund.objects(is_active=True).first()
        if not fund:
            # Create default fund
            fund = MentorshipFund()
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
                    "total_commissions_paid": fund.total_commissions_paid,
                    "total_amount_distributed": fund.total_amount_distributed
                },
                "last_updated": fund.last_updated
            },
            message="Mentorship fund status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/fund")
async def update_mentorship_fund(request: MentorshipFundRequest):
    """Update Mentorship fund"""
    try:
        fund = MentorshipFund.objects(is_active=True).first()
        if not fund:
            fund = MentorshipFund()
        
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
                "message": "Mentorship fund updated successfully"
            },
            message="Mentorship fund updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/settings")
async def get_mentorship_settings():
    """Get Mentorship system settings"""
    try:
        settings = MentorshipSettings.objects(is_active=True).first()
        if not settings:
            # Create default settings
            settings = MentorshipSettings()
            settings.save()
        
        return success_response(
            data={
                "mentorship_enabled": settings.mentorship_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_commission_distribution": settings.auto_commission_distribution,
                "eligibility_requirements": {
                    "require_matrix_program": settings.require_matrix_program,
                    "min_matrix_slots_required": settings.min_matrix_slots_required,
                    "min_direct_referrals_required": settings.min_direct_referrals_required
                },
                "commission_settings": {
                    "direct_commission_percentage": settings.direct_commission_percentage,
                    "direct_of_direct_commission_percentage": settings.direct_of_direct_commission_percentage
                },
                "payment_settings": {
                    "payment_currency": settings.payment_currency,
                    "payment_method": settings.payment_method,
                    "payment_delay_hours": settings.payment_delay_hours
                },
                "last_updated": settings.last_updated
            },
            message="Mentorship settings retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/settings")
async def update_mentorship_settings(request: MentorshipSettingsRequest):
    """Update Mentorship system settings"""
    try:
        settings = MentorshipSettings.objects(is_active=True).first()
        if not settings:
            settings = MentorshipSettings()
        
        settings.mentorship_enabled = request.mentorship_enabled
        settings.auto_eligibility_check = request.auto_eligibility_check
        settings.auto_commission_distribution = request.auto_commission_distribution
        settings.require_matrix_program = request.require_matrix_program
        settings.min_matrix_slots_required = request.min_matrix_slots_required
        settings.min_direct_referrals_required = request.min_direct_referrals_required
        settings.direct_commission_percentage = request.direct_commission_percentage
        settings.direct_of_direct_commission_percentage = request.direct_of_direct_commission_percentage
        settings.last_updated = datetime.utcnow()
        settings.save()
        
        return success_response(
            data={
                "settings_id": str(settings.id),
                "mentorship_enabled": settings.mentorship_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_commission_distribution": settings.auto_commission_distribution,
                "require_matrix_program": settings.require_matrix_program,
                "min_matrix_slots_required": settings.min_matrix_slots_required,
                "min_direct_referrals_required": settings.min_direct_referrals_required,
                "direct_commission_percentage": settings.direct_commission_percentage,
                "direct_of_direct_commission_percentage": settings.direct_of_direct_commission_percentage,
                "last_updated": settings.last_updated,
                "message": "Mentorship settings updated successfully"
            },
            message="Mentorship settings updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/statistics")
async def get_mentorship_statistics(period: str = Query("all_time", regex="^(daily|weekly|monthly|all_time)$")):
    """Get Mentorship program statistics"""
    try:
        statistics = MentorshipStatistics.objects(period=period, is_active=True).order_by('-last_updated').first()
        
        if not statistics:
            return success_response(
                data={
                    "period": period,
                    "statistics": {
                        "total_eligible_users": 0,
                        "total_active_users": 0,
                        "total_commissions_paid": 0,
                        "total_amount_distributed": 0.0,
                        "commission_breakdown": {
                            "direct_commissions_paid": 0,
                            "direct_commissions_amount": 0.0,
                            "direct_of_direct_commissions_paid": 0,
                            "direct_of_direct_commissions_amount": 0.0
                        },
                        "growth_statistics": {
                            "new_eligible_users": 0,
                            "new_commission_earners": 0,
                            "total_direct_referrals": 0,
                            "total_direct_of_direct_referrals": 0
                        }
                    },
                    "message": "No statistics available for this period"
                },
                message="Mentorship statistics retrieved"
            )
        
        return success_response(
            data={
                "period": statistics.period,
                "period_start": statistics.period_start,
                "period_end": statistics.period_end,
                "statistics": {
                    "total_eligible_users": statistics.total_eligible_users,
                    "total_active_users": statistics.total_active_users,
                    "total_commissions_paid": statistics.total_commissions_paid,
                    "total_amount_distributed": statistics.total_amount_distributed,
                    "commission_breakdown": {
                        "direct_commissions_paid": statistics.direct_commissions_paid,
                        "direct_commissions_amount": statistics.direct_commissions_amount,
                        "direct_of_direct_commissions_paid": statistics.direct_of_direct_commissions_paid,
                        "direct_of_direct_commissions_amount": statistics.direct_of_direct_commissions_amount
                    },
                    "growth_statistics": {
                        "new_eligible_users": statistics.new_eligible_users,
                        "new_commission_earners": statistics.new_commission_earners,
                        "total_direct_referrals": statistics.total_direct_referrals,
                        "total_direct_of_direct_referrals": statistics.total_direct_of_direct_referrals
                    }
                },
                "last_updated": statistics.last_updated
            },
            message="Mentorship statistics retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/leaderboard")
async def get_mentorship_leaderboard(limit: int = Query(50, le=100)):
    """Get Mentorship leaderboard"""
    try:
        # Get top Mentorship participants
        mentorships = Mentorship.objects(is_active=True).order_by('-total_commissions_earned', '-direct_of_direct_referrals_count').limit(limit)
        
        leaderboard_data = []
        for mentorship in mentorships:
            leaderboard_data.append({
                "user_id": str(mentorship.user_id),
                "total_commissions_earned": mentorship.total_commissions_earned,
                "total_commissions_paid": mentorship.total_commissions_paid,
                "pending_commissions": mentorship.pending_commissions,
                "direct_commissions": mentorship.direct_commissions,
                "direct_of_direct_commissions": mentorship.direct_of_direct_commissions,
                "direct_referrals_count": mentorship.direct_referrals_count,
                "direct_of_direct_referrals_count": mentorship.direct_of_direct_referrals_count,
                "matrix_program_active": mentorship.matrix_program_active,
                "is_eligible": mentorship.is_eligible,
                "joined_at": mentorship.joined_at
            })
        
        return success_response(
            data={
                "leaderboard": leaderboard_data,
                "total_participants": len(leaderboard_data),
                "message": "Mentorship leaderboard retrieved"
            },
            message="Mentorship leaderboard retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/referral")
async def add_mentorship_referral(request: MentorshipReferralRequest):
    """Add Mentorship referral relationship"""
    try:
        # Validate users exist
        mentor = User.objects(id=ObjectId(request.mentor_id)).first()
        upline = User.objects(id=ObjectId(request.upline_id)).first()
        referral = User.objects(id=ObjectId(request.referral_id)).first()
        
        if not mentor or not upline or not referral:
            raise HTTPException(status_code=404, detail="One or more users not found")
        
        # Check if referral relationship already exists
        existing = MentorshipReferral.objects(
            mentor_id=ObjectId(request.mentor_id),
            upline_id=ObjectId(request.upline_id),
            referral_id=ObjectId(request.referral_id)
        ).first()
        
        if existing:
            return success_response(
                data={
                    "referral_id": str(existing.id),
                    "mentor_id": request.mentor_id,
                    "upline_id": request.upline_id,
                    "referral_id": request.referral_id,
                    "relationship_level": existing.relationship_level,
                    "message": "Referral relationship already exists"
                },
                message="Referral relationship already exists"
            )
        
        # Create referral relationship
        referral_rel = MentorshipReferral(
            mentor_id=ObjectId(request.mentor_id),
            upline_id=ObjectId(request.upline_id),
            referral_id=ObjectId(request.referral_id),
            relationship_level=request.relationship_level,
            relationship_type="direct" if request.relationship_level == 1 else "direct_of_direct"
        )
        referral_rel.save()
        
        # Update Mentorship records
        mentor_mentorship = Mentorship.objects(user_id=ObjectId(request.mentor_id)).first()
        if mentor_mentorship:
            if request.relationship_level == 1:
                mentor_mentorship.direct_referrals.append(ObjectId(request.referral_id))
                mentor_mentorship.direct_referrals_count += 1
            else:
                mentor_mentorship.direct_of_direct_referrals.append(ObjectId(request.referral_id))
                mentor_mentorship.direct_of_direct_referrals_count += 1
            
            mentor_mentorship.last_updated = datetime.utcnow()
            mentor_mentorship.save()
        
        return success_response(
            data={
                "referral_id": str(referral_rel.id),
                "mentor_id": request.mentor_id,
                "upline_id": request.upline_id,
                "referral_id": request.referral_id,
                "relationship_level": request.relationship_level,
                "relationship_type": referral_rel.relationship_type,
                "message": "Referral relationship created successfully"
            },
            message="Referral relationship created"
        )
        
    except Exception as e:
        return error_response(str(e))

# Helper functions
def _initialize_mentorship_levels() -> List[MentorshipLevel]:
    """Initialize Mentorship levels"""
    return [
        MentorshipLevel(
            level_number=1,
            level_name="Direct",
            commission_percentage=10.0
        ),
        MentorshipLevel(
            level_number=2,
            level_name="Direct-of-Direct",
            commission_percentage=10.0
        )
    ]

def _check_matrix_program_status(user_id: str) -> Dict[str, Any]:
    """Check Matrix program status for user"""
    try:
        # This would need to be implemented based on actual Matrix program
        # For now, returning mock data
        return {
            "has_matrix": False,
            "slots_activated": 0
        }
    except Exception:
        return {
            "has_matrix": False,
            "slots_activated": 0
        }

def _check_direct_referrals(user_id: str) -> Dict[str, Any]:
    """Check direct referrals for user"""
    try:
        # This would need to be implemented based on actual tree structure
        # For now, returning mock data
        return {
            "direct_count": 0,
            "direct_list": []
        }
    except Exception:
        return {
            "direct_count": 0,
            "direct_list": []
        }

def _get_eligibility_reasons(eligibility: MentorshipEligibility) -> List[str]:
    """Get eligibility reasons"""
    reasons = []
    
    if not eligibility.has_matrix_program:
        reasons.append("Matrix program not active")
    
    if eligibility.direct_referrals_count < 1:
        reasons.append("Need at least 1 direct referral")
    
    return reasons
