from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel

from modules.jackpot.service import JackpotService

router = APIRouter(prefix="/jackpot", tags=["Jackpot"])

class JackpotEntryRequest(BaseModel):
    user_id: str
    entry_count: int = 1
    tx_hash: Optional[str] = None

class FreeCouponRequest(BaseModel):
    user_id: str
    slot_number: int
    tx_hash: Optional[str] = None

class BinaryContributionRequest(BaseModel):
    user_id: str
    slot_fee: Decimal
    tx_hash: Optional[str] = None

@router.post("/entry")
async def process_jackpot_entry(request: JackpotEntryRequest):
    """Process jackpot entry for a user"""
    try:
        jackpot_service = JackpotService()
        result = jackpot_service.process_jackpot_entry(
            request.user_id, 
            request.entry_count, 
            request.tx_hash
        )
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Jackpot entry processing failed: {str(e)}")

@router.post("/free-coupon")
async def process_free_coupon(request: FreeCouponRequest):
    """Process free coupon entry from binary slot upgrade"""
    try:
        jackpot_service = JackpotService()
        result = jackpot_service.process_free_coupon_entry(
            request.user_id, 
            request.slot_number, 
            request.tx_hash
        )
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Free coupon processing failed: {str(e)}")

@router.post("/binary-contribution")
async def process_binary_contribution(request: BinaryContributionRequest):
    """Process binary slot activation contribution to jackpot fund"""
    try:
        jackpot_service = JackpotService()
        result = jackpot_service.process_binary_contribution(
            request.user_id, 
            request.slot_fee, 
            request.tx_hash
        )
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Binary contribution processing failed: {str(e)}")

@router.get("/status/{user_id}")
async def get_user_jackpot_status(user_id: str):
    """Get user's jackpot status for current week"""
    try:
        jackpot_service = JackpotService()
        result = jackpot_service.get_user_jackpot_status(user_id)
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user jackpot status: {str(e)}")

@router.get("/fund-status")
async def get_jackpot_fund_status():
    """Get current jackpot fund status"""
    try:
        jackpot_service = JackpotService()
        result = jackpot_service.get_jackpot_fund_status()
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get jackpot fund status: {str(e)}")

@router.post("/weekly-distribution")
async def process_weekly_distribution():
    """Process weekly jackpot distribution (4-part system)"""
    try:
        jackpot_service = JackpotService()
        result = jackpot_service.process_weekly_distribution()
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weekly distribution processing failed: {str(e)}")

@router.get("/distribution-history")
async def get_distribution_history(limit: int = Query(10, ge=1, le=100)):
    """Get jackpot distribution history"""
    try:
        jackpot_service = JackpotService()
        result = jackpot_service.get_distribution_history(limit)
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get distribution history: {str(e)}")

@router.get("/free-coupons-mapping")
async def get_free_coupons_mapping():
    """Get free coupons mapping for binary slots"""
    try:
        jackpot_service = JackpotService()
        return {
            "success": True,
            "free_coupons_mapping": jackpot_service.free_coupons_mapping,
            "description": "Free coupons earned from binary slot upgrades"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get free coupons mapping: {str(e)}")

@router.get("/pool-percentages")
async def get_pool_percentages():
    """Get jackpot pool distribution percentages"""
    try:
        jackpot_service = JackpotService()
        return {
            "success": True,
            "pool_percentages": {
                "open_pool": float(jackpot_service.open_pool_percentage * 100),
                "top_promoters_pool": float(jackpot_service.top_promoters_pool_percentage * 100),
                "top_buyers_pool": float(jackpot_service.top_buyers_pool_percentage * 100),
                "new_joiners_pool": float(jackpot_service.new_joiners_pool_percentage * 100)
            },
            "winner_counts": {
                "open_pool_winners": jackpot_service.open_pool_winners_count,
                "top_promoters_winners": jackpot_service.top_promoters_winners_count,
                "top_buyers_winners": jackpot_service.top_buyers_winners_count,
                "new_joiners_winners": jackpot_service.new_joiners_winners_count
            },
            "entry_fee": float(jackpot_service.entry_fee),
            "binary_contribution_percentage": float(jackpot_service.binary_contribution_percentage * 100)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pool percentages: {str(e)}")

@router.get("/current-stats")
async def get_current_jackpot_stats(
    user_id: str = Query(None, description="Optional: User ID to get user's own entry count")
):
    """Get current jackpot session statistics (total entries and total fund)
    If user_id is provided, also returns user's own entry count for current session"""
    try:
        jackpot_service = JackpotService()
        result = jackpot_service.get_current_jackpot_stats(user_id=user_id)
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get current jackpot stats: {str(e)}")

@router.get("/history/{user_id}")
async def get_user_jackpot_history(
    user_id: str, 
    history_type: str = Query(..., regex="^(entry|claim)$"),
    limit: int = Query(20, ge=1, le=100)
):
    """Get user's jackpot history - entry or claim based on query parameter"""
    try:
        jackpot_service = JackpotService()
        
        if history_type == "entry":
            result = jackpot_service.get_user_entry_history(user_id, limit)
        elif history_type == "claim":
            result = jackpot_service.get_user_claim_history(user_id, limit)
        else:
            raise HTTPException(status_code=400, detail="Invalid history_type. Must be 'entry' or 'claim'")
        
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user jackpot history: {str(e)}")