#!/usr/bin/env python3
"""
Newcomer Growth Support Router
API endpoints for newcomer growth support operations
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, Dict, Any
from bson import ObjectId
from datetime import datetime

from modules.newcomer_growth_support.service import NewcomerGrowthSupportService

router = APIRouter(prefix="/newcomer-growth-support", tags=["Newcomer Growth Support"])

# Initialize service
newcomer_service = NewcomerGrowthSupportService()

class NewcomerGrowthSupportRequest(BaseModel):
    """Request model for newcomer growth support"""
    user_id: str
    total_amount: float
    referrer_id: Optional[str] = None
    tx_hash: Optional[str] = None

class MonthlyDistributionRequest(BaseModel):
    """Request model for monthly distribution"""
    upline_id: str

@router.post("/process")
async def process_newcomer_growth_support(request: NewcomerGrowthSupportRequest):
    """Process newcomer growth support with 50/50 split"""
    try:
        # Convert amount to Decimal
        amount = Decimal(str(request.total_amount))
        
        result = newcomer_service.process_newcomer_growth_support(
            request.user_id, amount, request.referrer_id, request.tx_hash
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "success": True,
            "message": "Newcomer growth support processed successfully",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Newcomer growth support processing failed: {str(e)}")

@router.post("/monthly-distribution")
async def process_monthly_distribution(request: MonthlyDistributionRequest):
    """Process monthly distribution for a specific upline"""
    try:
        result = newcomer_service.process_monthly_distribution(request.upline_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "success": True,
            "message": "Monthly distribution processed successfully",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monthly distribution processing failed: {str(e)}")

@router.get("/status/{user_id}")
async def get_newcomer_growth_status(user_id: str):
    """Get newcomer growth support status for a user"""
    try:
        result = newcomer_service.get_newcomer_growth_status(user_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "success": True,
            "message": "Newcomer growth status retrieved successfully",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get newcomer growth status: {str(e)}")

@router.get("/direct-referrals/{upline_id}")
async def get_direct_referrals_for_distribution(upline_id: str):
    """Get direct referrals eligible for monthly distribution"""
    try:
        result = newcomer_service.get_direct_referrals_for_distribution(upline_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "success": True,
            "message": "Direct referrals retrieved successfully",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get direct referrals: {str(e)}")

@router.post("/trigger-monthly-distribution")
async def trigger_monthly_distribution_for_all():
    """Trigger monthly distribution for all users with pending funds"""
    try:
        result = newcomer_service.trigger_monthly_distribution_for_all()
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "success": True,
            "message": "Monthly distribution triggered for all users",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger monthly distribution: {str(e)}")

@router.get("/validate/{amount}")
async def validate_newcomer_growth_support(amount: float):
    """Validate newcomer growth support percentages"""
    try:
        result = newcomer_service.validate_newcomer_growth_support(Decimal(str(amount)))
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "success": True,
            "message": "Newcomer growth support validation completed",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.get("/test-distribution")
async def test_newcomer_growth_support(amount: float = 100.0, user_id: str = None, referrer_id: str = None):
    """Test newcomer growth support with sample data"""
    try:
        if not user_id:
            # Create a test user ID
            user_id = f"test_user_{int(datetime.now().timestamp())}"
        
        if not referrer_id:
            # Use mother ID as default referrer
            referrer_id = "68dc17f08b174277bc40d19c"
        
        result = newcomer_service.process_newcomer_growth_support(
            user_id, Decimal(str(amount)), referrer_id, f"TEST_NGS_{int(datetime.now().timestamp())}"
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "success": True,
            "message": "Test newcomer growth support completed",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")
