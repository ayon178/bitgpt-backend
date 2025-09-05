from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from ..user.model import User
from .model import (
    Commission, CommissionDistribution, MissedProfit, 
    LeadershipStipend, CommissionRule, CommissionAccumulation, CommissionPayment
)
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/commission", tags=["Commission Management"])

# Pydantic models for request/response
class CommissionCalculateRequest(BaseModel):
    from_user_id: str
    program: str
    commission_type: str
    amount: float
    currency: str
    slot_no: Optional[int] = None
    slot_name: Optional[str] = None

class CommissionDistributeRequest(BaseModel):
    commission_id: str
    distribute_to_levels: bool = True
    distribute_direct: bool = True

class MissedProfitHandleRequest(BaseModel):
    missed_profit_id: str
    handling_action: str  # 'accumulate' or 'distribute'

class LeadershipStipendRequest(BaseModel):
    user_id: str
    amount: float
    currency: str
    reason: str

# API Endpoints

@router.post("/calculate")
async def calculate_commission(request: CommissionCalculateRequest):
    """Calculate commission for a user"""
    try:
        # Validate user exists
        from_user = User.objects(id=ObjectId(request.from_user_id)).first()
        if not from_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get commission rule
        commission_rule = CommissionRule.objects(
            program=request.program,
            commission_type=request.commission_type,
            is_active=True
        ).first()
        
        if not commission_rule:
            raise HTTPException(status_code=400, detail="Commission rule not found")
        
        # Calculate commission amount
        commission_amount = Decimal(str(request.amount)) * Decimal(str(commission_rule.percentage / 100))
        
        # Get upline for direct commission
        upline_id = from_user.refered_by
        if not upline_id:
            raise HTTPException(status_code=400, detail="No upline found")
        
        # Create commission record
        commission = Commission(
            user_id=upline_id,
            from_user_id=ObjectId(request.from_user_id),
            commission_type=request.commission_type,
            program=request.program,
            commission_amount=commission_amount,
            currency=request.currency,
            commission_percentage=commission_rule.percentage,
            source_slot_no=request.slot_no,
            source_slot_name=request.slot_name,
            is_direct_commission=True,
            status='pending'
        )
        commission.save()
        
        # Update commission accumulation
        accumulation = CommissionAccumulation.objects(
            user_id=upline_id,
            program=request.program
        ).first()
        
        if not accumulation:
            accumulation = CommissionAccumulation(
                user_id=upline_id,
                program=request.program
            )
        
        accumulation.total_earned += commission_amount
        accumulation.currency_totals[request.currency] += commission_amount
        accumulation.commission_type_totals[request.commission_type] += commission_amount
        accumulation.last_commission_at = datetime.utcnow()
        accumulation.save()
        
        return success_response(
            data={
                "commission_id": str(commission.id),
                "commission_amount": float(commission_amount),
                "commission_percentage": commission_rule.percentage,
                "upline_id": str(upline_id),
                "message": "Commission calculated successfully"
            },
            message="Commission calculation successful"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/distribute")
async def distribute_commission(request: CommissionDistributeRequest):
    """Distribute commission across levels 1-16"""
    try:
        # Get commission
        commission = Commission.objects(id=ObjectId(request.commission_id)).first()
        if not commission:
            raise HTTPException(status_code=404, detail="Commission not found")
        
        # Calculate distribution amounts
        total_amount = commission.commission_amount
        direct_amount = total_amount * Decimal('0.30')  # 30% to direct upline
        level_amount = total_amount * Decimal('0.70')  # 70% to levels 1-16
        
        # Create distribution record
        distribution = CommissionDistribution(
            source_commission_id=commission.id,
            program=commission.program,
            source_user_id=commission.from_user_id,
            source_slot_no=commission.source_slot_no,
            total_amount=total_amount,
            currency=commission.currency,
            direct_commission_amount=direct_amount,
            direct_commission_user_id=commission.user_id,
            direct_commission_level=commission.level or 1,
            status='pending'
        )
        
        # Distribute to levels 1-16
        if request.distribute_to_levels:
            level_distributions = []
            amount_per_level = level_amount / Decimal('16')
            
            # Get users at each level
            for level in range(1, 17):
                # This is simplified - in real implementation, you'd get actual users at each level
                level_distributions.append({
                    "level": level,
                    "amount": float(amount_per_level),
                    "user_id": str(commission.user_id)  # Simplified
                })
            
            distribution.level_distributions = level_distributions
        
        distribution.save()
        
        # Update commission status
        commission.status = 'paid'
        commission.paid_at = datetime.utcnow()
        commission.save()
        
        return success_response(
            data={
                "distribution_id": str(distribution.id),
                "total_amount": float(total_amount),
                "direct_amount": float(direct_amount),
                "level_amount": float(level_amount),
                "message": "Commission distributed successfully"
            },
            message="Commission distribution successful"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/history/{user_id}")
async def get_commission_history(
    user_id: str,
    program: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100)
):
    """Get commission history for a user"""
    try:
        query = {"user_id": ObjectId(user_id)}
        
        if program:
            query["program"] = program
        if status:
            query["status"] = status
        
        commissions = Commission.objects(**query).order_by('-created_at').limit(limit)
        
        return success_response(
            data={
                "commissions": [
                    {
                        "id": str(commission.id),
                        "commission_type": commission.commission_type,
                        "program": commission.program,
                        "commission_amount": float(commission.commission_amount),
                        "currency": commission.currency,
                        "commission_percentage": commission.commission_percentage,
                        "source_slot_no": commission.source_slot_no,
                        "source_slot_name": commission.source_slot_name,
                        "level": commission.level,
                        "status": commission.status,
                        "created_at": commission.created_at,
                        "paid_at": commission.paid_at
                    } for commission in commissions
                ]
            },
            message="Commission history retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/accumulation/{user_id}")
async def get_commission_accumulation(user_id: str):
    """Get commission accumulation for a user"""
    try:
        accumulations = CommissionAccumulation.objects(user_id=ObjectId(user_id)).all()
        
        return success_response(
            data={
                "accumulations": [
                    {
                        "program": acc.program,
                        "total_earned": float(acc.total_earned),
                        "total_paid": float(acc.total_paid),
                        "total_missed": float(acc.total_missed),
                        "total_accumulated": float(acc.total_accumulated),
                        "currency_totals": {
                            currency: float(amount) for currency, amount in acc.currency_totals.items()
                        },
                        "commission_type_totals": {
                            comm_type: float(amount) for comm_type, amount in acc.commission_type_totals.items()
                        },
                        "last_commission_at": acc.last_commission_at,
                        "last_payment_at": acc.last_payment_at
                    } for acc in accumulations
                ]
            },
            message="Commission accumulation retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/missed-profits/{user_id}")
async def get_missed_profits(user_id: str):
    """Get missed profits for a user"""
    try:
        missed_profits = MissedProfit.objects(user_id=ObjectId(user_id)).order_by('-created_at').all()
        
        return success_response(
            data={
                "missed_profits": [
                    {
                        "id": str(mp.id),
                        "program": mp.program,
                        "missed_amount": float(mp.missed_amount),
                        "currency": mp.currency,
                        "slot_no": mp.slot_no,
                        "slot_name": mp.slot_name,
                        "missed_reason": mp.missed_reason,
                        "user_level": mp.user_level,
                        "required_level": mp.required_level,
                        "handling_status": mp.handling_status,
                        "accumulated_in_stipend": mp.accumulated_in_stipend,
                        "created_at": mp.created_at,
                        "handled_at": mp.handled_at
                    } for mp in missed_profits
                ]
            },
            message="Missed profits retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/missed-profit/handle")
async def handle_missed_profit(request: MissedProfitHandleRequest):
    """Handle missed profit (accumulate or distribute)"""
    try:
        missed_profit = MissedProfit.objects(id=ObjectId(request.missed_profit_id)).first()
        if not missed_profit:
            raise HTTPException(status_code=404, detail="Missed profit not found")
        
        if request.handling_action == 'accumulate':
            # Move to Leadership Stipend
            stipend = LeadershipStipend.objects(
                fund_type='missed_profits',
                program=missed_profit.program,
                status='active'
            ).first()
            
            if not stipend:
                stipend = LeadershipStipend(
                    fund_type='missed_profits',
                    program=missed_profit.program,
                    total_amount=missed_profit.missed_amount,
                    currency=missed_profit.currency,
                    available_amount=missed_profit.missed_amount
                )
            else:
                stipend.total_amount += missed_profit.missed_amount
                stipend.available_amount += missed_profit.missed_amount
            
            stipend.save()
            
            # Update missed profit
            missed_profit.handling_status = 'accumulated'
            missed_profit.accumulated_in_stipend = True
            missed_profit.stipend_distribution_id = stipend.id
            missed_profit.handled_at = datetime.utcnow()
            missed_profit.save()
            
            return success_response(
                data={
                    "missed_profit_id": str(missed_profit.id),
                    "stipend_id": str(stipend.id),
                    "accumulated_amount": float(missed_profit.missed_amount),
                    "message": "Missed profit accumulated in Leadership Stipend"
                },
                message="Missed profit handling successful"
            )
        
        elif request.handling_action == 'distribute':
            # Distribute directly to user
            # Implementation for direct distribution
            missed_profit.handling_status = 'distributed'
            missed_profit.handled_at = datetime.utcnow()
            missed_profit.save()
            
            return success_response(
                data={
                    "missed_profit_id": str(missed_profit.id),
                    "distributed_amount": float(missed_profit.missed_amount),
                    "message": "Missed profit distributed directly"
                },
                message="Missed profit distribution successful"
            )
        
        else:
            raise HTTPException(status_code=400, detail="Invalid handling action")
        
    except Exception as e:
        return error_response(str(e))

@router.get("/leadership-stipend")
async def get_leadership_stipend_funds():
    """Get Leadership Stipend funds"""
    try:
        stipends = LeadershipStipend.objects(status='active').all()
        
        return success_response(
            data={
                "stipends": [
                    {
                        "id": str(stipend.id),
                        "fund_type": stipend.fund_type,
                        "program": stipend.program,
                        "total_amount": float(stipend.total_amount),
                        "available_amount": float(stipend.available_amount),
                        "currency": stipend.currency,
                        "distributions_count": len(stipend.distributions),
                        "last_distribution_at": stipend.last_distribution_at,
                        "created_at": stipend.created_at
                    } for stipend in stipends
                ]
            },
            message="Leadership Stipend funds retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/leadership-stipend/distribute")
async def distribute_leadership_stipend(request: LeadershipStipendRequest):
    """Distribute Leadership Stipend to user"""
    try:
        # Validate user
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get available stipend
        stipend = LeadershipStipend.objects(
            program='binary',  # Assuming binary for now
            status='active',
            available_amount__gte=Decimal(str(request.amount))
        ).first()
        
        if not stipend:
            raise HTTPException(status_code=400, detail="Insufficient stipend funds")
        
        # Create distribution record
        distribution_record = {
            "user_id": str(user.id),
            "amount": float(request.amount),
            "reason": request.reason,
            "date": datetime.utcnow()
        }
        
        stipend.distributions.append(distribution_record)
        stipend.available_amount -= Decimal(str(request.amount))
        stipend.last_distribution_at = datetime.utcnow()
        stipend.save()
        
        return success_response(
            data={
                "stipend_id": str(stipend.id),
                "distributed_amount": request.amount,
                "remaining_amount": float(stipend.available_amount),
                "message": "Leadership Stipend distributed successfully"
            },
            message="Leadership Stipend distribution successful"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/rules")
async def get_commission_rules():
    """Get all commission rules"""
    try:
        rules = CommissionRule.objects(is_active=True).all()
        
        return success_response(
            data={
                "rules": [
                    {
                        "id": str(rule.id),
                        "program": rule.program,
                        "commission_type": rule.commission_type,
                        "percentage": rule.percentage,
                        "fixed_amount": float(rule.fixed_amount) if rule.fixed_amount else None,
                        "currency": rule.currency,
                        "level_commission_percentage": rule.level_commission_percentage,
                        "level_distribution_percentage": rule.level_distribution_percentage,
                        "minimum_slot_level": rule.minimum_slot_level,
                        "maximum_slot_level": rule.maximum_slot_level,
                        "effective_from": rule.effective_from,
                        "effective_until": rule.effective_until
                    } for rule in rules
                ]
            },
            message="Commission rules retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/stats/{user_id}")
async def get_commission_stats(user_id: str):
    """Get commission statistics for a user"""
    try:
        # Get total commissions
        total_commissions = Commission.objects(user_id=ObjectId(user_id)).sum('commission_amount')
        
        # Get paid commissions
        paid_commissions = Commission.objects(
            user_id=ObjectId(user_id),
            status='paid'
        ).sum('commission_amount')
        
        # Get missed profits
        missed_profits = MissedProfit.objects(user_id=ObjectId(user_id)).sum('missed_amount')
        
        # Get commission by program
        program_stats = {}
        for program in ['binary', 'matrix', 'global']:
            program_total = Commission.objects(
                user_id=ObjectId(user_id),
                program=program
            ).sum('commission_amount')
            program_stats[program] = float(program_total) if program_total else 0
        
        return success_response(
            data={
                "total_commissions": float(total_commissions) if total_commissions else 0,
                "paid_commissions": float(paid_commissions) if paid_commissions else 0,
                "missed_profits": float(missed_profits) if missed_profits else 0,
                "program_stats": program_stats,
                "commission_count": Commission.objects(user_id=ObjectId(user_id)).count()
            },
            message="Commission statistics retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))
