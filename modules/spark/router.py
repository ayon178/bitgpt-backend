from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime
from auth.service import authentication_service
from .service import SparkService
from pydantic import BaseModel
from decimal import Decimal
from .model import SparkBonusDistribution
from bson import ObjectId
from datetime import datetime, timedelta
from utils.response import success_response, error_response


router = APIRouter(prefix="/spark", tags=["Spark / Triple Entry Reward"])


@router.get("/triple-entry/eligibles")
async def triple_entry_eligibles(
    date: str,  # format YYYY-MM-DD
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    try:
        target_date = datetime.strptime(date, '%Y-%m-%d')
        res = SparkService.compute_triple_entry_eligibles(target_date)
        if not res.get("success"):
            raise HTTPException(status_code=500, detail=res.get("error", "Failed to compute eligibles"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



class SparkDistributeRequest(BaseModel):
    cycle_no: int
    slot_no: int


@router.get("/bonus/history")
async def get_spark_bonus_history(
    user_id: str = Query(..., description="User ID"),
    currency: str | None = Query(None, description="Filter by currency (USDT or BNB)"),
    slot_number: int | None = Query(None, ge=1, le=14, description="Filter by matrix slot 1-14"),
    start_date: str | None = Query(None, description="YYYY-MM-DD inclusive"),
    end_date: str | None = Query(None, description="YYYY-MM-DD inclusive"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    try:
        q = SparkBonusDistribution.objects(user_id=ObjectId(user_id))
        if currency:
            q = q.filter(currency=currency.upper())
        if slot_number:
            q = q.filter(slot_number=int(slot_number))
        if start_date:
            sd = datetime.strptime(start_date, "%Y-%m-%d")
            q = q.filter(created_at__gte=sd)
        if end_date:
            ed = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            q = q.filter(created_at__lt=ed)

        total = q.count()
        items = q.order_by('-created_at').skip((page - 1) * limit).limit(limit)

        data = []
        for it in items:
            data.append({
                "id": str(it.id),
                "slot_number": it.slot_number,
                "amount": float(it.distribution_amount or 0),
                "currency": it.currency,
                "status": it.status,
                "distributed_at": it.distributed_at,
                "created_at": it.created_at,
                "wallet_credit_tx_hash": it.wallet_credit_tx_hash,
            })

        return {
            "success": True,
            "data": {
                "claims": data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": (total + limit - 1) // limit,
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    total_spark_pool: float
    participant_user_ids: list[str]


@router.get("/triple-entry/claim/history")
async def get_triple_entry_claim_history(
    user_id: str = Query(..., description="User ID for Triple Entry Reward history")
):
    """
    Get Triple Entry Reward claim history and claimable amounts for a user
    Returns both USDT and BNB data with claimable amounts and claim history
    """
    try:
        service = SparkService()
        
        # Get claimable amounts
        claimable_info = service.get_triple_entry_claimable_amount(user_id)
        if not claimable_info.get("success"):
            return error_response(claimable_info.get("error", "Failed to get claimable amount"))
        
        # Get claim history (both currencies)
        history = service.get_triple_entry_claim_history(user_id)
        if not history.get("success"):
            return error_response(history.get("error", "Failed to get claim history"))
        
        # Build response with currency-wise data
        response_data = {
            "USDT": {
                "claimable_amount": claimable_info.get("claimable_amounts", {}).get("USDT", 0),
                "claims": history.get("USDT", {}).get("claims", []),
                "total_claims": history.get("USDT", {}).get("total_claims", 0)
            },
            "BNB": {
                "claimable_amount": claimable_info.get("claimable_amounts", {}).get("BNB", 0),
                "claims": history.get("BNB", {}).get("claims", []),
                "total_claims": history.get("BNB", {}).get("total_claims", 0)
            },
            "eligibility": {
                "is_eligible": claimable_info.get("is_eligible", False),
                "eligible_users_count": claimable_info.get("eligible_users_count", 0),
                "total_fund_usdt": claimable_info.get("total_fund_usdt", 0),
                "already_claimed": claimable_info.get("already_claimed", {"USDT": False, "BNB": False}),
                "message": claimable_info.get("message", "")
            }
        }
        
        return success_response(response_data, "Triple Entry Reward data fetched successfully")
    except Exception as e:
        return error_response(str(e))


@router.post("/triple-entry/claim")
async def claim_triple_entry_reward(
    user_id: str = Query(..., description="User ID"),
    currency: str = Query(..., description="Currency (USDT or BNB)")
):
    """Claim Triple Entry Reward for a specific currency"""
    try:
        service = SparkService()
        result = service.claim_triple_entry_reward(user_id, currency)
        
        if result.get("success"):
            return success_response(result, result.get("message", "Triple Entry Reward claimed successfully"))
        else:
            return error_response(result.get("error", "Failed to claim reward"))
    except Exception as e:
        return error_response(str(e))


@router.post("/distribute")
async def distribute_spark_bonus(req: SparkDistributeRequest):
    try:
        svc = SparkService()
        res = svc.distribute_spark_for_slot(
            cycle_no=req.cycle_no,
            slot_no=req.slot_no,
            total_spark_pool=Decimal(str(req.total_spark_pool)),
            participant_user_ids=req.participant_user_ids,
        )
        if not res.get("success"):
            raise HTTPException(status_code=400, detail=res.get("error", "Distribution failed"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

