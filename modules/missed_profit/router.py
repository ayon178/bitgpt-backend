from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from ..user.model import User
from .model import (
    MissedProfit, MissedProfitAccumulation, MissedProfitDistribution,
    MissedProfitFund, MissedProfitSettings, MissedProfitLog, 
    MissedProfitStatistics, MissedProfitRecovery, MissedProfitReason
)
from ..utils.response import success_response, error_response
from ..auth.service import authentication_service

router = APIRouter(prefix="/missed-profit", tags=["Missed Profit Handling"])

# Pydantic models for request/response
class MissedProfitCreateRequest(BaseModel):
    user_id: str
    upline_user_id: str
    missed_profit_type: str
    missed_profit_amount: float
    currency: str = "BNB"
    primary_reason: str
    reason_description: str
    user_level: int
    upgrade_slot_level: int
    program_type: str

class MissedProfitAccumulationRequest(BaseModel):
    period: str
    period_start: datetime
    period_end: datetime

class MissedProfitDistributionRequest(BaseModel):
    distribution_period: str
    period_start: datetime
    period_end: datetime
    distribution_method: str = "leadership_stipend"

class MissedProfitSettingsRequest(BaseModel):
    missed_profit_enabled: bool
    auto_accumulation: bool
    auto_distribution: bool
    accumulation_period: str
    accumulation_threshold: float
    distribution_method: str
    distribution_period: str
    distribution_threshold: float
    recovery_enabled: bool
    recovery_period_days: int

class MissedProfitFundRequest(BaseModel):
    fund_amount: float
    currency: str = "BNB"
    source: str

class MissedProfitRecoveryRequest(BaseModel):
    missed_profit_id: str
    recovery_method: str
    recovery_amount: float

# API Endpoints

@router.post("/create")
async def create_missed_profit(request: MissedProfitCreateRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    """Create missed profit record"""
    try:
        # Validate users exist
        user = User.objects(id=ObjectId(request.user_id)).first()
        upline_user = User.objects(id=ObjectId(request.upline_user_id)).first()
        
        if not user or not upline_user:
            raise HTTPException(status_code=404, detail="User or upline not found")
        
        # Validate request parameters
        if request.missed_profit_type not in ['commission', 'bonus', 'upgrade_reward']:
            raise HTTPException(status_code=400, detail="Invalid missed profit type")
        
        if request.primary_reason not in ['account_inactivity', 'level_advancement']:
            raise HTTPException(status_code=400, detail="Invalid primary reason")
        
        if request.program_type not in ['binary', 'matrix', 'global']:
            raise HTTPException(status_code=400, detail="Invalid program type")
        
        # Create missed profit record
        missed_profit = MissedProfit(
            user_id=ObjectId(request.user_id),
            upline_user_id=ObjectId(request.upline_user_id),
            missed_profit_type=request.missed_profit_type,
            missed_profit_amount=request.missed_profit_amount,
            currency=request.currency,
            primary_reason=request.primary_reason,
            reason_description=request.reason_description,
            user_level=request.user_level,
            upgrade_slot_level=request.upgrade_slot_level,
            program_type=request.program_type
        )
        
        # Add reason details
        reason = MissedProfitReason(
            reason_type=request.primary_reason,
            reason_description=request.reason_description,
            user_level=request.user_level,
            upgrade_slot_level=request.upgrade_slot_level,
            commission_amount=request.missed_profit_amount,
            currency=request.currency
        )
        missed_profit.reasons.append(reason)
        
        missed_profit.save()
        
        return success_response(
            data={
                "missed_profit_id": str(missed_profit.id),
                "user_id": request.user_id,
                "upline_user_id": request.upline_user_id,
                "missed_profit_type": request.missed_profit_type,
                "missed_profit_amount": request.missed_profit_amount,
                "currency": request.currency,
                "primary_reason": request.primary_reason,
                "reason_description": request.reason_description,
                "user_level": request.user_level,
                "upgrade_slot_level": request.upgrade_slot_level,
                "program_type": request.program_type,
                "recovery_status": "pending",
                "message": "Missed profit record created successfully"
            },
            message="Missed profit record created"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/list/{user_id}")
async def get_missed_profits(user_id: str, limit: int = Query(50, le=100), current_user: dict = Depends(authentication_service.verify_authentication)):
    """Get missed profits for user"""
    try:
        missed_profits = MissedProfit.objects(
            user_id=ObjectId(user_id)
        ).order_by('-created_at').limit(limit)
        
        return success_response(
            data={
                "missed_profits": [
                    {
                        "id": str(missed_profit.id),
                        "user_id": str(missed_profit.user_id),
                        "upline_user_id": str(missed_profit.upline_user_id),
                        "missed_profit_type": missed_profit.missed_profit_type,
                        "missed_profit_amount": missed_profit.missed_profit_amount,
                        "currency": missed_profit.currency,
                        "primary_reason": missed_profit.primary_reason,
                        "reason_description": missed_profit.reason_description,
                        "user_level": missed_profit.user_level,
                        "upgrade_slot_level": missed_profit.upgrade_slot_level,
                        "program_type": missed_profit.program_type,
                        "is_accumulated": missed_profit.is_accumulated,
                        "accumulated_at": missed_profit.accumulated_at,
                        "is_distributed": missed_profit.is_distributed,
                        "distributed_at": missed_profit.distributed_at,
                        "distribution_method": missed_profit.distribution_method,
                        "recovery_status": missed_profit.recovery_status,
                        "recovery_amount": missed_profit.recovery_amount,
                        "recovery_reference": missed_profit.recovery_reference,
                        "created_at": missed_profit.created_at
                    } for missed_profit in missed_profits
                ],
                "total_missed_profits": len(missed_profits)
            },
            message="Missed profits retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/accumulate")
async def accumulate_missed_profits(request: MissedProfitAccumulationRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    """Accumulate missed profits for a period"""
    try:
        # Get missed profits for the period
        missed_profits = MissedProfit.objects(
            created_at__gte=request.period_start,
            created_at__lt=request.period_end,
            is_accumulated=False
        )
        
        # Calculate totals
        total_amount = 0.0
        total_amount_bnb = 0.0
        total_amount_usdt = 0.0
        
        account_inactivity_count = 0
        account_inactivity_amount = 0.0
        level_advancement_count = 0
        level_advancement_amount = 0.0
        
        binary_count = 0
        binary_amount = 0.0
        matrix_count = 0
        matrix_amount = 0.0
        global_count = 0
        global_amount = 0.0
        
        for missed_profit in missed_profits:
            total_amount += missed_profit.missed_profit_amount
            
            if missed_profit.currency == 'BNB':
                total_amount_bnb += missed_profit.missed_profit_amount
            else:
                total_amount_usdt += missed_profit.missed_profit_amount
            
            if missed_profit.primary_reason == 'account_inactivity':
                account_inactivity_count += 1
                account_inactivity_amount += missed_profit.missed_profit_amount
            else:
                level_advancement_count += 1
                level_advancement_amount += missed_profit.missed_profit_amount
            
            if missed_profit.program_type == 'binary':
                binary_count += 1
                binary_amount += missed_profit.missed_profit_amount
            elif missed_profit.program_type == 'matrix':
                matrix_count += 1
                matrix_amount += missed_profit.missed_profit_amount
            else:
                global_count += 1
                global_amount += missed_profit.missed_profit_amount
            
            # Mark as accumulated
            missed_profit.is_accumulated = True
            missed_profit.accumulated_at = datetime.utcnow()
            missed_profit.save()
        
        # Create accumulation record
        accumulation = MissedProfitAccumulation(
            accumulation_period=request.period,
            period_start=request.period_start,
            period_end=request.period_end,
            total_missed_profits=total_amount,
            total_missed_profits_bnb=total_amount_bnb,
            total_missed_profits_usdt=total_amount_usdt,
            account_inactivity_count=account_inactivity_count,
            account_inactivity_amount=account_inactivity_amount,
            level_advancement_count=level_advancement_count,
            level_advancement_amount=level_advancement_amount,
            binary_missed_count=binary_count,
            binary_missed_amount=binary_amount,
            matrix_missed_count=matrix_count,
            matrix_missed_amount=matrix_amount,
            global_missed_count=global_count,
            global_missed_amount=global_amount,
            is_processed=True,
            processed_at=datetime.utcnow()
        )
        accumulation.save()
        
        return success_response(
            data={
                "accumulation_id": str(accumulation.id),
                "period": request.period,
                "period_start": request.period_start,
                "period_end": request.period_end,
                "total_missed_profits": total_amount,
                "total_missed_profits_bnb": total_amount_bnb,
                "total_missed_profits_usdt": total_amount_usdt,
                "account_inactivity": {
                    "count": account_inactivity_count,
                    "amount": account_inactivity_amount
                },
                "level_advancement": {
                    "count": level_advancement_count,
                    "amount": level_advancement_amount
                },
                "program_breakdown": {
                    "binary": {"count": binary_count, "amount": binary_amount},
                    "matrix": {"count": matrix_count, "amount": matrix_amount},
                    "global": {"count": global_count, "amount": global_amount}
                },
                "processed_missed_profits": len(missed_profits),
                "message": "Missed profits accumulated successfully"
            },
            message="Missed profits accumulated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/distribute")
async def distribute_missed_profits(request: MissedProfitDistributionRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    """Distribute missed profits via Leadership Stipend"""
    try:
        # Get accumulated missed profits for the period
        accumulations = MissedProfitAccumulation.objects(
            period_start__gte=request.period_start,
            period_end__lte=request.period_end,
            is_processed=True
        )
        
        total_distributed_amount = 0.0
        total_distributed_amount_bnb = 0.0
        total_distributed_amount_usdt = 0.0
        
        recipients = []
        
        for accumulation in accumulations:
            total_distributed_amount += accumulation.total_missed_profits
            total_distributed_amount_bnb += accumulation.total_missed_profits_bnb
            total_distributed_amount_usdt += accumulation.total_missed_profits_usdt
        
        # Get eligible recipients (users with Leadership Stipend eligibility)
        # This would need to be implemented based on actual Leadership Stipend logic
        eligible_recipients = _get_eligible_leadership_stipend_recipients()
        
        if not eligible_recipients:
            return success_response(
                data={
                    "message": "No eligible recipients found for Leadership Stipend distribution"
                },
                message="No eligible recipients"
            )
        
        # Distribute to Leadership Stipend fund
        fund = MissedProfitFund.objects(is_active=True).first()
        if not fund:
            fund = MissedProfitFund()
        
        fund.total_fund_amount += total_distributed_amount
        fund.available_amount += total_distributed_amount
        fund.total_missed_profits_accumulated += len(accumulations)
        
        # Update fund sources
        fund.fund_sources['missed_commissions'] += total_distributed_amount
        fund.last_updated = datetime.utcnow()
        fund.save()
        
        # Create distribution record
        distribution = MissedProfitDistribution(
            distribution_period=request.distribution_period,
            period_start=request.period_start,
            period_end=request.period_end,
            total_distributed_amount=total_distributed_amount,
            total_distributed_amount_bnb=total_distributed_amount_bnb,
            total_distributed_amount_usdt=total_distributed_amount_usdt,
            total_recipients=len(eligible_recipients),
            recipients=eligible_recipients,
            leadership_stipend_distributions=len(eligible_recipients),
            leadership_stipend_amount=total_distributed_amount,
            is_processed=True,
            processed_at=datetime.utcnow()
        )
        distribution.save()
        
        return success_response(
            data={
                "distribution_id": str(distribution.id),
                "distribution_period": request.distribution_period,
                "period_start": request.period_start,
                "period_end": request.period_end,
                "total_distributed_amount": total_distributed_amount,
                "total_distributed_amount_bnb": total_distributed_amount_bnb,
                "total_distributed_amount_usdt": total_distributed_amount_usdt,
                "total_recipients": len(eligible_recipients),
                "distribution_method": request.distribution_method,
                "leadership_stipend_amount": total_distributed_amount,
                "message": "Missed profits distributed successfully"
            },
            message="Missed profits distributed"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/fund")
async def get_missed_profit_fund(current_user: dict = Depends(authentication_service.verify_authentication)):
    """Get Missed Profit fund status"""
    try:
        fund = MissedProfitFund.objects(is_active=True).first()
        if not fund:
            # Create default fund
            fund = MissedProfitFund()
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
                    "total_missed_profits_accumulated": fund.total_missed_profits_accumulated,
                    "total_distributions_made": fund.total_distributions_made,
                    "total_amount_distributed": fund.total_amount_distributed
                },
                "last_updated": fund.last_updated
            },
            message="Missed Profit fund status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/fund")
async def update_missed_profit_fund(request: MissedProfitFundRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    """Update Missed Profit fund"""
    try:
        fund = MissedProfitFund.objects(is_active=True).first()
        if not fund:
            fund = MissedProfitFund()
        
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
                "message": "Missed Profit fund updated successfully"
            },
            message="Missed Profit fund updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/settings")
async def get_missed_profit_settings(current_user: dict = Depends(authentication_service.verify_authentication)):
    """Get Missed Profit system settings"""
    try:
        settings = MissedProfitSettings.objects(is_active=True).first()
        if not settings:
            # Create default settings
            settings = MissedProfitSettings()
            settings.save()
        
        return success_response(
            data={
                "missed_profit_enabled": settings.missed_profit_enabled,
                "auto_accumulation": settings.auto_accumulation,
                "auto_distribution": settings.auto_distribution,
                "accumulation_settings": {
                    "accumulation_period": settings.accumulation_period,
                    "accumulation_threshold": settings.accumulation_threshold
                },
                "distribution_settings": {
                    "distribution_method": settings.distribution_method,
                    "distribution_period": settings.distribution_period,
                    "distribution_threshold": settings.distribution_threshold
                },
                "recovery_settings": {
                    "recovery_enabled": settings.recovery_enabled,
                    "recovery_period_days": settings.recovery_period_days
                },
                "last_updated": settings.last_updated
            },
            message="Missed Profit settings retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/settings")
async def update_missed_profit_settings(request: MissedProfitSettingsRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    """Update Missed Profit system settings"""
    try:
        settings = MissedProfitSettings.objects(is_active=True).first()
        if not settings:
            settings = MissedProfitSettings()
        
        settings.missed_profit_enabled = request.missed_profit_enabled
        settings.auto_accumulation = request.auto_accumulation
        settings.auto_distribution = request.auto_distribution
        settings.accumulation_period = request.accumulation_period
        settings.accumulation_threshold = request.accumulation_threshold
        settings.distribution_method = request.distribution_method
        settings.distribution_period = request.distribution_period
        settings.distribution_threshold = request.distribution_threshold
        settings.recovery_enabled = request.recovery_enabled
        settings.recovery_period_days = request.recovery_period_days
        settings.last_updated = datetime.utcnow()
        settings.save()
        
        return success_response(
            data={
                "settings_id": str(settings.id),
                "missed_profit_enabled": settings.missed_profit_enabled,
                "auto_accumulation": settings.auto_accumulation,
                "auto_distribution": settings.auto_distribution,
                "accumulation_period": settings.accumulation_period,
                "accumulation_threshold": settings.accumulation_threshold,
                "distribution_method": settings.distribution_method,
                "distribution_period": settings.distribution_period,
                "distribution_threshold": settings.distribution_threshold,
                "recovery_enabled": settings.recovery_enabled,
                "recovery_period_days": settings.recovery_period_days,
                "last_updated": settings.last_updated,
                "message": "Missed Profit settings updated successfully"
            },
            message="Missed Profit settings updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/statistics")
async def get_missed_profit_statistics(period: str = Query("all_time", regex="^(daily|weekly|monthly|all_time)$"), current_user: dict = Depends(authentication_service.verify_authentication)):
    """Get Missed Profit program statistics"""
    try:
        statistics = MissedProfitStatistics.objects(period=period, is_active=True).order_by('-last_updated').first()
        
        if not statistics:
            return success_response(
                data={
                    "period": period,
                    "statistics": {
                        "total_missed_profits": 0,
                        "total_missed_amount": 0.0,
                        "total_accumulated_amount": 0.0,
                        "total_distributed_amount": 0.0,
                        "reason_breakdown": {
                            "account_inactivity": {"count": 0, "amount": 0.0},
                            "level_advancement": {"count": 0, "amount": 0.0}
                        },
                        "program_breakdown": {
                            "binary": {"count": 0, "amount": 0.0},
                            "matrix": {"count": 0, "amount": 0.0},
                            "global": {"count": 0, "amount": 0.0}
                        },
                        "distribution_breakdown": {
                            "leadership_stipend": {"count": 0, "amount": 0.0},
                            "direct_distribution": {"count": 0, "amount": 0.0}
                        },
                        "recovery_statistics": {
                            "total_recovery_attempts": 0,
                            "successful_recoveries": 0,
                            "failed_recoveries": 0,
                            "recovery_amount": 0.0
                        }
                    },
                    "message": "No statistics available for this period"
                },
                message="Missed Profit statistics retrieved"
            )
        
        return success_response(
            data={
                "period": statistics.period,
                "period_start": statistics.period_start,
                "period_end": statistics.period_end,
                "statistics": {
                    "total_missed_profits": statistics.total_missed_profits,
                    "total_missed_amount": statistics.total_missed_amount,
                    "total_accumulated_amount": statistics.total_accumulated_amount,
                    "total_distributed_amount": statistics.total_distributed_amount,
                    "reason_breakdown": {
                        "account_inactivity": {
                            "count": statistics.account_inactivity_count,
                            "amount": statistics.account_inactivity_amount
                        },
                        "level_advancement": {
                            "count": statistics.level_advancement_count,
                            "amount": statistics.level_advancement_amount
                        }
                    },
                    "program_breakdown": {
                        "binary": {
                            "count": statistics.binary_missed_count,
                            "amount": statistics.binary_missed_amount
                        },
                        "matrix": {
                            "count": statistics.matrix_missed_count,
                            "amount": statistics.matrix_missed_amount
                        },
                        "global": {
                            "count": statistics.global_missed_count,
                            "amount": statistics.global_missed_amount
                        }
                    },
                    "distribution_breakdown": {
                        "leadership_stipend": {
                            "count": statistics.leadership_stipend_distributions,
                            "amount": statistics.leadership_stipend_amount
                        },
                        "direct_distribution": {
                            "count": statistics.direct_distributions,
                            "amount": statistics.direct_distribution_amount
                        }
                    },
                    "recovery_statistics": {
                        "total_recovery_attempts": statistics.total_recovery_attempts,
                        "successful_recoveries": statistics.successful_recoveries,
                        "failed_recoveries": statistics.failed_recoveries,
                        "recovery_amount": statistics.recovery_amount
                    }
                },
                "last_updated": statistics.last_updated
            },
            message="Missed Profit statistics retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/recovery")
async def attempt_recovery(request: MissedProfitRecoveryRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    """Attempt to recover missed profit"""
    try:
        # Get missed profit record
        missed_profit = MissedProfit.objects(id=ObjectId(request.missed_profit_id)).first()
        if not missed_profit:
            raise HTTPException(status_code=404, detail="Missed profit record not found")
        
        if missed_profit.recovery_status != "pending":
            return success_response(
                data={
                    "missed_profit_id": request.missed_profit_id,
                    "status": "already_processed",
                    "message": "Recovery already processed"
                },
                message="Recovery already processed"
            )
        
        # Create recovery record
        recovery = MissedProfitRecovery(
            missed_profit_id=ObjectId(request.missed_profit_id),
            user_id=missed_profit.user_id,
            upline_user_id=missed_profit.upline_user_id,
            recovery_type="manual",
            recovery_method=request.recovery_method,
            recovery_amount=request.recovery_amount,
            currency=missed_profit.currency,
            recovery_status="processing"
        )
        recovery.save()
        
        # Update missed profit record
        missed_profit.recovery_status = "processing"
        missed_profit.recovery_amount = request.recovery_amount
        missed_profit.last_updated = datetime.utcnow()
        missed_profit.save()
        
        return success_response(
            data={
                "recovery_id": str(recovery.id),
                "missed_profit_id": request.missed_profit_id,
                "user_id": str(missed_profit.user_id),
                "upline_user_id": str(missed_profit.upline_user_id),
                "recovery_method": request.recovery_method,
                "recovery_amount": request.recovery_amount,
                "currency": missed_profit.currency,
                "recovery_status": "processing",
                "message": "Recovery attempt initiated"
            },
            message="Recovery attempt initiated"
        )
        
    except Exception as e:
        return error_response(str(e))

# Helper functions
def _get_eligible_leadership_stipend_recipients() -> List[ObjectId]:
    """Get eligible Leadership Stipend recipients"""
    try:
        # This would need to be implemented based on actual Leadership Stipend logic
        # For now, returning empty list
        return []
    except Exception:
        return []
