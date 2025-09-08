from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from ..user.model import User
from .model import (
    DreamMatrix, DreamMatrixEligibility, DreamMatrixCommission,
    DreamMatrixFund, DreamMatrixSettings, DreamMatrixLog, 
    DreamMatrixStatistics, DreamMatrixLevelProgress, DreamMatrixLevel
)
from utils.response import success_response, error_response

router = APIRouter(prefix="/dream-matrix", tags=["Dream Matrix"])

# Pydantic models for request/response
class DreamMatrixJoinRequest(BaseModel):
    user_id: str

class DreamMatrixEligibilityRequest(BaseModel):
    user_id: str
    force_check: bool = False

class DreamMatrixCommissionRequest(BaseModel):
    user_id: str
    level_number: int
    source_user_id: str
    source_amount: float

class DreamMatrixSettingsRequest(BaseModel):
    dream_matrix_enabled: bool
    auto_eligibility_check: bool
    auto_commission_distribution: bool
    require_matrix_first_slot: bool
    min_direct_partners_required: int
    level_commissions: dict

class DreamMatrixFundRequest(BaseModel):
    fund_amount: float
    currency: str = "USDT"
    source: str

class DreamMatrixLevelRequest(BaseModel):
    user_id: str
    level_number: int

# API Endpoints

@router.post("/join")
async def join_dream_matrix(request: DreamMatrixJoinRequest):
    """Join Dream Matrix program"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if already joined
        existing = DreamMatrix.objects(user_id=ObjectId(request.user_id)).first()
        if existing:
            return success_response(
                data={
                    "user_id": request.user_id,
                    "status": "already_joined",
                    "total_profit_earned": existing.total_profit_earned,
                    "current_level": existing.current_level,
                    "direct_partners_count": existing.direct_partners_count,
                    "message": "User already joined Dream Matrix program"
                },
                message="Already joined Dream Matrix"
            )
        
        # Create Dream Matrix record
        dream_matrix = DreamMatrix(
            user_id=ObjectId(request.user_id),
            joined_at=datetime.utcnow(),
            is_active=True
        )
        
        # Initialize levels
        dream_matrix.levels = _initialize_dream_matrix_levels()
        
        dream_matrix.save()
        
        return success_response(
            data={
                "dream_matrix_id": str(dream_matrix.id),
                "user_id": request.user_id,
                "is_eligible": False,
                "is_active": True,
                "joined_at": dream_matrix.joined_at,
                "message": "Successfully joined Dream Matrix program"
            },
            message="Joined Dream Matrix program"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/eligibility/{user_id}")
async def check_dream_matrix_eligibility(user_id: str):
    """Check Dream Matrix eligibility for user"""
    try:
        # Get Dream Matrix record
        dream_matrix = DreamMatrix.objects(user_id=ObjectId(user_id)).first()
        if not dream_matrix:
            raise HTTPException(status_code=404, detail="User not in Dream Matrix program")
        
        # Get eligibility record
        eligibility = DreamMatrixEligibility.objects(user_id=ObjectId(user_id)).first()
        if not eligibility:
            eligibility = DreamMatrixEligibility(user_id=ObjectId(user_id))
        
        # Check Matrix first slot status
        matrix_status = _check_matrix_first_slot_status(user_id)
        eligibility.has_matrix_first_slot = matrix_status["has_first_slot"]
        eligibility.matrix_slot_value = matrix_status["slot_value"]
        eligibility.matrix_currency = matrix_status["currency"]
        
        # Check direct partners
        partners_status = _check_direct_partners(user_id)
        eligibility.direct_partners_count = partners_status["partners_count"]
        eligibility.direct_partners = partners_status["partners_list"]
        
        # Update Dream Matrix record
        dream_matrix.has_matrix_first_slot = matrix_status["has_first_slot"]
        dream_matrix.slot_value = matrix_status["slot_value"]
        dream_matrix.currency = matrix_status["currency"]
        dream_matrix.direct_partners = partners_status["partners_list"]
        dream_matrix.direct_partners_count = partners_status["partners_count"]
        
        # Determine eligibility
        eligibility.is_eligible_for_dream_matrix = (
            eligibility.has_matrix_first_slot and
            eligibility.direct_partners_count >= 3
        )
        
        # Update eligibility reasons
        eligibility_reasons = _get_eligibility_reasons(eligibility)
        eligibility.eligibility_reasons = eligibility_reasons
        
        if eligibility.is_eligible_for_dream_matrix and not dream_matrix.is_eligible:
            eligibility.qualified_at = datetime.utcnow()
            dream_matrix.is_eligible = True
            dream_matrix.qualified_at = datetime.utcnow()
            dream_matrix.has_three_direct_partners = True
            
            # Activate levels
            for level in dream_matrix.levels:
                level.is_active = True
                level.activated_at = datetime.utcnow()
        
        eligibility.last_checked = datetime.utcnow()
        eligibility.save()
        
        dream_matrix.last_updated = datetime.utcnow()
        dream_matrix.save()
        
        return success_response(
            data={
                "user_id": user_id,
                "is_eligible": eligibility.is_eligible_for_dream_matrix,
                "matrix_requirements": {
                    "has_matrix_first_slot": eligibility.has_matrix_first_slot,
                    "matrix_slot_value": eligibility.matrix_slot_value,
                    "matrix_currency": eligibility.matrix_currency
                },
                "direct_partners": {
                    "direct_partners_count": eligibility.direct_partners_count,
                    "min_direct_partners_required": eligibility.min_direct_partners_required,
                    "partners_list": [str(partner_id) for partner_id in eligibility.direct_partners]
                },
                "eligibility_reasons": eligibility.eligibility_reasons,
                "qualified_at": eligibility.qualified_at,
                "last_checked": eligibility.last_checked
            },
            message="Dream Matrix eligibility checked"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/status/{user_id}")
async def get_dream_matrix_status(user_id: str):
    """Get Dream Matrix status and progress"""
    try:
        dream_matrix = DreamMatrix.objects(user_id=ObjectId(user_id)).first()
        if not dream_matrix:
            raise HTTPException(status_code=404, detail="User not in Dream Matrix program")
        
        return success_response(
            data={
                "user_id": user_id,
                "program_status": {
                    "is_eligible": dream_matrix.is_eligible,
                    "is_active": dream_matrix.is_active,
                    "joined_at": dream_matrix.joined_at,
                    "qualified_at": dream_matrix.qualified_at
                },
                "requirements_status": {
                    "has_matrix_first_slot": dream_matrix.has_matrix_first_slot,
                    "has_three_direct_partners": dream_matrix.has_three_direct_partners,
                    "direct_partners_count": dream_matrix.direct_partners_count,
                    "direct_partners": [str(partner_id) for partner_id in dream_matrix.direct_partners]
                },
                "level_status": [
                    {
                        "level_number": level.level_number,
                        "level_name": level.level_name,
                        "member_count": level.member_count,
                        "commission_percentage": level.commission_percentage,
                        "commission_amount": level.commission_amount,
                        "total_profit": level.total_profit,
                        "is_active": level.is_active,
                        "activated_at": level.activated_at,
                        "total_earned": level.total_earned,
                        "total_paid": level.total_paid,
                        "pending_amount": level.pending_amount
                    } for level in dream_matrix.levels
                ],
                "progress_summary": {
                    "current_level": dream_matrix.current_level,
                    "max_level_reached": dream_matrix.max_level_reached,
                    "total_profit_earned": dream_matrix.total_profit_earned,
                    "total_profit_paid": dream_matrix.total_profit_paid,
                    "pending_profit": dream_matrix.pending_profit
                },
                "commissions_summary": {
                    "total_commissions_earned": dream_matrix.total_commissions_earned,
                    "total_commissions_paid": dream_matrix.total_commissions_paid,
                    "pending_commissions": dream_matrix.pending_commissions
                },
                "slot_info": {
                    "slot_value": dream_matrix.slot_value,
                    "currency": dream_matrix.currency
                },
                "last_updated": dream_matrix.last_updated
            },
            message="Dream Matrix status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/commissions/{user_id}")
async def get_dream_matrix_commissions(user_id: str, limit: int = Query(50, le=100)):
    """Get Dream Matrix commissions for user"""
    try:
        commissions = DreamMatrixCommission.objects(user_id=ObjectId(user_id)).order_by('-created_at').limit(limit)
        
        return success_response(
            data={
                "commissions": [
                    {
                        "id": str(commission.id),
                        "level_number": commission.level_number,
                        "level_name": commission.level_name,
                        "commission_percentage": commission.commission_percentage,
                        "commission_amount": commission.commission_amount,
                        "source_user_id": str(commission.source_user_id),
                        "source_level": commission.source_level,
                        "source_amount": commission.source_amount,
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
            message="Dream Matrix commissions retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/commission")
async def create_dream_matrix_commission(request: DreamMatrixCommissionRequest):
    """Create Dream Matrix commission"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get Dream Matrix record
        dream_matrix = DreamMatrix.objects(user_id=ObjectId(request.user_id)).first()
        if not dream_matrix:
            raise HTTPException(status_code=404, detail="User not in Dream Matrix program")
        
        if not dream_matrix.is_eligible:
            raise HTTPException(status_code=400, detail="User not eligible for Dream Matrix bonuses")
        
        # Validate level number
        if request.level_number < 1 or request.level_number > 5:
            raise HTTPException(status_code=400, detail="Invalid level number (1-5)")
        
        # Get level details
        level_details = _get_level_details(request.level_number)
        if not level_details:
            raise HTTPException(status_code=400, detail="Invalid level details")
        
        # Calculate commission amount
        commission_amount = level_details["commission_amount"]
        
        # Create commission record
        commission = DreamMatrixCommission(
            user_id=ObjectId(request.user_id),
            dream_matrix_id=dream_matrix.id,
            level_number=request.level_number,
            level_name=level_details["level_name"],
            commission_percentage=level_details["commission_percentage"],
            commission_amount=commission_amount,
            source_user_id=ObjectId(request.source_user_id),
            source_level=request.level_number,
            source_amount=request.source_amount,
            payment_status="pending"
        )
        commission.save()
        
        # Update Dream Matrix record
        dream_matrix.total_commissions_earned += commission_amount
        dream_matrix.pending_commissions += commission_amount
        
        # Update level
        for level in dream_matrix.levels:
            if level.level_number == request.level_number:
                level.total_earned += commission_amount
                level.pending_amount += commission_amount
                break
        
        dream_matrix.last_updated = datetime.utcnow()
        dream_matrix.save()
        
        return success_response(
            data={
                "commission_id": str(commission.id),
                "user_id": request.user_id,
                "level_number": request.level_number,
                "level_name": level_details["level_name"],
                "commission_percentage": level_details["commission_percentage"],
                "commission_amount": commission_amount,
                "source_user_id": request.source_user_id,
                "source_amount": request.source_amount,
                "payment_status": "pending",
                "message": "Dream Matrix commission created successfully"
            },
            message="Dream Matrix commission created"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/fund")
async def get_dream_matrix_fund():
    """Get Dream Matrix fund status"""
    try:
        fund = DreamMatrixFund.objects(is_active=True).first()
        if not fund:
            # Create default fund
            fund = DreamMatrixFund()
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
            message="Dream Matrix fund status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/fund")
async def update_dream_matrix_fund(request: DreamMatrixFundRequest):
    """Update Dream Matrix fund"""
    try:
        fund = DreamMatrixFund.objects(is_active=True).first()
        if not fund:
            fund = DreamMatrixFund()
        
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
                "message": "Dream Matrix fund updated successfully"
            },
            message="Dream Matrix fund updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/settings")
async def get_dream_matrix_settings():
    """Get Dream Matrix system settings"""
    try:
        settings = DreamMatrixSettings.objects(is_active=True).first()
        if not settings:
            # Create default settings
            settings = DreamMatrixSettings()
            settings.save()
        
        return success_response(
            data={
                "dream_matrix_enabled": settings.dream_matrix_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_commission_distribution": settings.auto_commission_distribution,
                "eligibility_requirements": {
                    "require_matrix_first_slot": settings.require_matrix_first_slot,
                    "min_direct_partners_required": settings.min_direct_partners_required
                },
                "level_commissions": settings.level_commissions,
                "payment_settings": {
                    "payment_currency": settings.payment_currency,
                    "payment_method": settings.payment_method,
                    "payment_delay_hours": settings.payment_delay_hours
                },
                "last_updated": settings.last_updated
            },
            message="Dream Matrix settings retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/settings")
async def update_dream_matrix_settings(request: DreamMatrixSettingsRequest):
    """Update Dream Matrix system settings"""
    try:
        settings = DreamMatrixSettings.objects(is_active=True).first()
        if not settings:
            settings = DreamMatrixSettings()
        
        settings.dream_matrix_enabled = request.dream_matrix_enabled
        settings.auto_eligibility_check = request.auto_eligibility_check
        settings.auto_commission_distribution = request.auto_commission_distribution
        settings.require_matrix_first_slot = request.require_matrix_first_slot
        settings.min_direct_partners_required = request.min_direct_partners_required
        settings.level_commissions = request.level_commissions
        settings.last_updated = datetime.utcnow()
        settings.save()
        
        return success_response(
            data={
                "settings_id": str(settings.id),
                "dream_matrix_enabled": settings.dream_matrix_enabled,
                "auto_eligibility_check": settings.auto_eligibility_check,
                "auto_commission_distribution": settings.auto_commission_distribution,
                "require_matrix_first_slot": settings.require_matrix_first_slot,
                "min_direct_partners_required": settings.min_direct_partners_required,
                "level_commissions": settings.level_commissions,
                "last_updated": settings.last_updated,
                "message": "Dream Matrix settings updated successfully"
            },
            message="Dream Matrix settings updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/statistics")
async def get_dream_matrix_statistics(period: str = Query("all_time", regex="^(daily|weekly|monthly|all_time)$")):
    """Get Dream Matrix program statistics"""
    try:
        statistics = DreamMatrixStatistics.objects(period=period, is_active=True).order_by('-last_updated').first()
        
        if not statistics:
            return success_response(
                data={
                    "period": period,
                    "statistics": {
                        "total_eligible_users": 0,
                        "total_active_users": 0,
                        "total_commissions_paid": 0,
                        "total_amount_distributed": 0.0,
                        "level_breakdown": {
                            "level_1": {"commissions_paid": 0, "amount": 0.0},
                            "level_2": {"commissions_paid": 0, "amount": 0.0},
                            "level_3": {"commissions_paid": 0, "amount": 0.0},
                            "level_4": {"commissions_paid": 0, "amount": 0.0},
                            "level_5": {"commissions_paid": 0, "amount": 0.0}
                        },
                        "growth_statistics": {
                            "new_eligible_users": 0,
                            "new_commission_earners": 0,
                            "total_direct_partners": 0,
                            "total_level_activations": 0
                        }
                    },
                    "message": "No statistics available for this period"
                },
                message="Dream Matrix statistics retrieved"
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
                    "level_breakdown": {
                        "level_1": {
                            "commissions_paid": statistics.level_1_commissions_paid,
                            "amount": statistics.level_1_commissions_amount
                        },
                        "level_2": {
                            "commissions_paid": statistics.level_2_commissions_paid,
                            "amount": statistics.level_2_commissions_amount
                        },
                        "level_3": {
                            "commissions_paid": statistics.level_3_commissions_paid,
                            "amount": statistics.level_3_commissions_amount
                        },
                        "level_4": {
                            "commissions_paid": statistics.level_4_commissions_paid,
                            "amount": statistics.level_4_commissions_amount
                        },
                        "level_5": {
                            "commissions_paid": statistics.level_5_commissions_paid,
                            "amount": statistics.level_5_commissions_amount
                        }
                    },
                    "growth_statistics": {
                        "new_eligible_users": statistics.new_eligible_users,
                        "new_commission_earners": statistics.new_commission_earners,
                        "total_direct_partners": statistics.total_direct_partners,
                        "total_level_activations": statistics.total_level_activations
                    }
                },
                "last_updated": statistics.last_updated
            },
            message="Dream Matrix statistics retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/leaderboard")
async def get_dream_matrix_leaderboard(limit: int = Query(50, le=100)):
    """Get Dream Matrix leaderboard"""
    try:
        # Get top Dream Matrix participants
        dream_matrices = DreamMatrix.objects(is_active=True).order_by('-total_profit_earned', '-max_level_reached').limit(limit)
        
        leaderboard_data = []
        for dream_matrix in dream_matrices:
            leaderboard_data.append({
                "user_id": str(dream_matrix.user_id),
                "total_profit_earned": dream_matrix.total_profit_earned,
                "total_profit_paid": dream_matrix.total_profit_paid,
                "pending_profit": dream_matrix.pending_profit,
                "current_level": dream_matrix.current_level,
                "max_level_reached": dream_matrix.max_level_reached,
                "direct_partners_count": dream_matrix.direct_partners_count,
                "has_matrix_first_slot": dream_matrix.has_matrix_first_slot,
                "is_eligible": dream_matrix.is_eligible,
                "joined_at": dream_matrix.joined_at
            })
        
        return success_response(
            data={
                "leaderboard": leaderboard_data,
                "total_participants": len(leaderboard_data),
                "message": "Dream Matrix leaderboard retrieved"
            },
            message="Dream Matrix leaderboard retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/levels/{user_id}")
async def get_dream_matrix_levels(user_id: str):
    """Get Dream Matrix level progress for user"""
    try:
        dream_matrix = DreamMatrix.objects(user_id=ObjectId(user_id)).first()
        if not dream_matrix:
            raise HTTPException(status_code=404, detail="User not in Dream Matrix program")
        
        # Get level progress records
        level_progress = DreamMatrixLevelProgress.objects(user_id=ObjectId(user_id)).order_by('level_number')
        
        return success_response(
            data={
                "user_id": user_id,
                "levels": [
                    {
                        "level_number": progress.level_number,
                        "level_name": progress.level_name,
                        "member_count": progress.member_count,
                        "commission_percentage": progress.commission_percentage,
                        "commission_amount": progress.commission_amount,
                        "total_profit": progress.total_profit,
                        "members_required": progress.members_required,
                        "members_achieved": progress.members_achieved,
                        "progress_percentage": progress.progress_percentage,
                        "commissions_earned": progress.commissions_earned,
                        "commissions_paid": progress.commissions_paid,
                        "pending_commissions": progress.pending_commissions,
                        "is_active": progress.is_active,
                        "is_completed": progress.is_completed,
                        "completed_at": progress.completed_at,
                        "activated_at": progress.activated_at
                    } for progress in level_progress
                ],
                "total_levels": len(level_progress)
            },
            message="Dream Matrix levels retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

# Helper functions
def _initialize_dream_matrix_levels() -> List[DreamMatrixLevel]:
    """Initialize Dream Matrix levels"""
    return [
        DreamMatrixLevel(
            level_number=1,
            level_name="Level 1",
            member_count=3,
            commission_percentage=10.0,
            commission_amount=80.0,
            total_profit=240.0
        ),
        DreamMatrixLevel(
            level_number=2,
            level_name="Level 2",
            member_count=9,
            commission_percentage=10.0,
            commission_amount=80.0,
            total_profit=720.0
        ),
        DreamMatrixLevel(
            level_number=3,
            level_name="Level 3",
            member_count=27,
            commission_percentage=15.0,
            commission_amount=120.0,
            total_profit=3240.0
        ),
        DreamMatrixLevel(
            level_number=4,
            level_name="Level 4",
            member_count=81,
            commission_percentage=25.0,
            commission_amount=200.0,
            total_profit=16200.0
        ),
        DreamMatrixLevel(
            level_number=5,
            level_name="Level 5",
            member_count=243,
            commission_percentage=40.0,
            commission_amount=320.0,
            total_profit=77760.0
        )
    ]

def _check_matrix_first_slot_status(user_id: str) -> Dict[str, Any]:
    """Check Matrix first slot status for user"""
    try:
        # This would need to be implemented based on actual Matrix program
        # For now, returning mock data
        return {
            "has_first_slot": False,
            "slot_value": 0.0,
            "currency": "USDT"
        }
    except Exception:
        return {
            "has_first_slot": False,
            "slot_value": 0.0,
            "currency": "USDT"
        }

def _check_direct_partners(user_id: str) -> Dict[str, Any]:
    """Check direct partners for user"""
    try:
        # This would need to be implemented based on actual tree structure
        # For now, returning mock data
        return {
            "partners_count": 0,
            "partners_list": []
        }
    except Exception:
        return {
            "partners_count": 0,
            "partners_list": []
        }

def _get_level_details(level_number: int) -> Optional[Dict[str, Any]]:
    """Get level details for given level number"""
    level_details = {
        1: {"level_name": "Level 1", "commission_percentage": 10.0, "commission_amount": 80.0},
        2: {"level_name": "Level 2", "commission_percentage": 10.0, "commission_amount": 80.0},
        3: {"level_name": "Level 3", "commission_percentage": 15.0, "commission_amount": 120.0},
        4: {"level_name": "Level 4", "commission_percentage": 25.0, "commission_amount": 200.0},
        5: {"level_name": "Level 5", "commission_percentage": 40.0, "commission_amount": 320.0}
    }
    
    return level_details.get(level_number)

def _get_eligibility_reasons(eligibility: DreamMatrixEligibility) -> List[str]:
    """Get eligibility reasons"""
    reasons = []
    
    if not eligibility.has_matrix_first_slot:
        reasons.append("Matrix first slot not purchased")
    
    if eligibility.direct_partners_count < 3:
        reasons.append("Need at least 3 direct partners")
    
    return reasons
