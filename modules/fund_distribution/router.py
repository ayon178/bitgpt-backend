#!/usr/bin/env python3
"""
Fund Distribution Router
API endpoints for fund distribution operations
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, Dict, Any
from bson import ObjectId
from datetime import datetime

from modules.fund_distribution.service import FundDistributionService

router = APIRouter(prefix="/fund-distribution", tags=["Fund Distribution"])

# Initialize service
fund_distribution_service = FundDistributionService()

class FundDistributionRequest(BaseModel):
    """Request model for fund distribution"""
    user_id: str
    amount: float
    slot_no: int
    program: str  # 'binary', 'matrix', 'global'
    referrer_id: Optional[str] = None
    tx_hash: Optional[str] = None

class DistributionSummaryRequest(BaseModel):
    """Request model for distribution summary"""
    program: str  # 'binary', 'matrix', 'global'

@router.post("/distribute")
async def distribute_funds(request: FundDistributionRequest):
    """Distribute funds according to program-specific percentages"""
    try:
        # Validate program
        if request.program not in ['binary', 'matrix', 'global']:
            raise HTTPException(status_code=400, detail="Invalid program. Must be 'binary', 'matrix', or 'global'")
        
        # Convert amount to Decimal
        amount = Decimal(str(request.amount))
        
        # Distribute funds based on program
        if request.program == 'binary':
            result = fund_distribution_service.distribute_binary_funds(
                request.user_id, amount, request.slot_no, request.referrer_id, request.tx_hash
            )
        elif request.program == 'matrix':
            result = fund_distribution_service.distribute_matrix_funds(
                request.user_id, amount, request.slot_no, request.referrer_id, request.tx_hash
            )
        elif request.program == 'global':
            result = fund_distribution_service.distribute_global_funds(
                request.user_id, amount, request.slot_no, request.referrer_id, request.tx_hash
            )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "success": True,
            "message": f"Fund distribution completed for {request.program} program",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fund distribution failed: {str(e)}")

@router.get("/summary/{program}")
async def get_distribution_summary(program: str):
    """Get distribution summary for a specific program"""
    try:
        if program not in ['binary', 'matrix', 'global']:
            raise HTTPException(status_code=400, detail="Invalid program. Must be 'binary', 'matrix', or 'global'")
        
        result = fund_distribution_service.get_distribution_summary(program)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "success": True,
            "message": f"Distribution summary retrieved for {program} program",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get distribution summary: {str(e)}")

@router.get("/validate/{program}")
async def validate_distribution_percentages(program: str):
    """Validate distribution percentages for a specific program"""
    try:
        if program not in ['binary', 'matrix', 'global']:
            raise HTTPException(status_code=400, detail="Invalid program. Must be 'binary', 'matrix', or 'global'")
        
        result = fund_distribution_service.validate_distribution_percentages(program)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "success": True,
            "message": f"Distribution validation completed for {program} program",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.get("/all-programs/summary")
async def get_all_programs_summary():
    """Get distribution summary for all programs"""
    try:
        programs = ['binary', 'matrix', 'global']
        summaries = {}
        
        for program in programs:
            result = fund_distribution_service.get_distribution_summary(program)
            if result.get("success"):
                summaries[program] = result
            else:
                summaries[program] = {"error": result.get("error")}
        
        return {
            "success": True,
            "message": "Distribution summaries retrieved for all programs",
            "data": summaries
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get all programs summary: {str(e)}")

@router.get("/all-programs/validate")
async def validate_all_programs_percentages():
    """Validate distribution percentages for all programs"""
    try:
        programs = ['binary', 'matrix', 'global']
        validations = {}
        
        for program in programs:
            result = fund_distribution_service.validate_distribution_percentages(program)
            if result.get("success"):
                validations[program] = result
            else:
                validations[program] = {"error": result.get("error")}
        
        return {
            "success": True,
            "message": "Distribution validation completed for all programs",
            "data": validations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.get("/test-distribution/{program}")
async def test_distribution(program: str, amount: float = 100.0):
    """Test fund distribution with sample data"""
    try:
        if program not in ['binary', 'matrix', 'global']:
            raise HTTPException(status_code=400, detail="Invalid program. Must be 'binary', 'matrix', or 'global'")
        
        # Use current user as test user
        test_user_id = str(current_user.id)
        test_amount = Decimal(str(amount))
        
        # Distribute funds based on program
        if program == 'binary':
            result = fund_distribution_service.distribute_binary_funds(
                test_user_id, test_amount, 1, None, f"TEST_{program}_{int(datetime.now().timestamp())}"
            )
        elif program == 'matrix':
            result = fund_distribution_service.distribute_matrix_funds(
                test_user_id, test_amount, 1, None, f"TEST_{program}_{int(datetime.now().timestamp())}"
            )
        elif program == 'global':
            result = fund_distribution_service.distribute_global_funds(
                test_user_id, test_amount, 1, None, f"TEST_{program}_{int(datetime.now().timestamp())}"
            )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "success": True,
            "message": f"Test distribution completed for {program} program",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test distribution failed: {str(e)}")
