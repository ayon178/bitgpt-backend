from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId
from .model import JackpotTicket
from .service import JackpotService
from auth.service import authentication_service
from ..wallet.service import WalletService
from utils.response import success_response, error_response


router = APIRouter(prefix="/jackpot", tags=["Jackpot"])


class TicketQuery(BaseModel):
    user_id: Optional[str] = None
    referrer_user_id: Optional[str] = None
    week_id: Optional[str] = None
    status: Optional[str] = None  # active|used|expired


class JackpotEntryRequest(BaseModel):
    user_id: str
    currency: str = "USDT"
    amount: float = 5.0


class JackpotClaimRequest(BaseModel):
    user_id: str
    pool_type: str  # "open_pool", "top_direct_promoters", "top_buyers_pool", "new_joiners_pool"
    currency: str = "USDT"
    amount: float


@router.post("/enter")
async def enter_jackpot(
    request: JackpotEntryRequest,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Enter Jackpot Program with $5 USDT payment"""
    try:
        # Validate user exists
        from ..user.model import User
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check wallet balance
        wallet_service = WalletService()
        balance_result = wallet_service.get_currency_balances(request.user_id, 'main')
        
        # Extract balance from the correct structure
        if balance_result.get('success', False):
            current_balance = balance_result.get('balances', {}).get(request.currency.upper(), 0.0)
        else:
            current_balance = balance_result.get(request.currency.upper(), 0.0)
            
        if current_balance < request.amount:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient balance. Required: {request.amount} {request.currency}, Available: {current_balance} {request.currency}"
            )
        
        # Process Jackpot entry
        result = JackpotService.process_paid_entry(
            user_id=request.user_id,
            amount=request.amount,
            currency=request.currency
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return success_response(
            data=result["data"],
            message="Successfully entered Jackpot Program"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.post("/claim-reward")
async def claim_jackpot_reward(
    request: JackpotClaimRequest
):
    """Claim Jackpot reward and update user wallet"""
    try:
        # Validate user exists
        from ..user.model import User
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Process reward claim
        result = JackpotService.process_reward_claim(
            user_id=request.user_id,
            pool_type=request.pool_type,
            amount=request.amount,
            currency=request.currency
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return success_response(
            data=result["data"],
            message="Jackpot reward claimed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/history")
async def get_jackpot_history(
    user_id: str = Query(..., description="User ID"),
    history_type: str = Query("entry", description="History type: 'entry' or 'claim'"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page")
):
    """Get Jackpot history (both entry and claim) for a user"""
    try:
        result = JackpotService.get_jackpot_history(user_id, history_type, page, limit)
        
        if result["success"]:
            return success_response(result["data"], f"Jackpot {history_type} history fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result["error"])
        
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/pools-total")
async def get_jackpot_pools_total(
    currency: str = Query("USDT", description="Currency type")
):
    """Get total accumulated amounts for all Jackpot pools"""
    try:
        result = JackpotService.get_pools_total(currency)
        
        if result["success"]:
            return success_response(result["data"], "Jackpot pools total amounts fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result["error"])
        
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))




@router.post("/tickets/query")
async def query_tickets(
    payload: TicketQuery,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    try:
        q = {}
        if payload.user_id:
            q['user_id'] = ObjectId(payload.user_id)
        if payload.referrer_user_id:
            q['referrer_user_id'] = ObjectId(payload.referrer_user_id)
        if payload.week_id:
            q['week_id'] = payload.week_id
        if payload.status:
            q['status'] = payload.status

        tickets = JackpotTicket.objects(**q).order_by('-created_at')
        data = []
        for t in tickets:
            data.append({
                "id": str(t.id),
                "user_id": str(t.user_id),
                "referrer_user_id": str(t.referrer_user_id),
                "week_id": t.week_id,
                "source": t.source,
                "free_source_slot": t.free_source_slot,
                "status": t.status,
                "created_at": t.created_at
            })
        return {"success": True, "count": len(data), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickets/by-user/{user_id}")
async def tickets_by_user(
    user_id: str,
    week_id: Optional[str] = None,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    try:
        q = {"user_id": ObjectId(user_id)}
        if week_id:
            q["week_id"] = week_id
        tickets = JackpotTicket.objects(**q).order_by('-created_at')
        return {"success": True, "count": tickets.count(), "data": [
            {
                "id": str(t.id),
                "referrer_user_id": str(t.referrer_user_id),
                "week_id": t.week_id,
                "source": t.source,
                "free_source_slot": t.free_source_slot,
                "status": t.status,
                "created_at": t.created_at
            } for t in tickets
        ]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickets/by-referrer/{referrer_user_id}")
async def tickets_by_referrer(
    referrer_user_id: str,
    week_id: Optional[str] = None,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    try:
        q = {"referrer_user_id": ObjectId(referrer_user_id)}
        if week_id:
            q["week_id"] = week_id
        tickets = JackpotTicket.objects(**q).order_by('-created_at')
        return {"success": True, "count": tickets.count(), "data": [
            {
                "id": str(t.id),
                "user_id": str(t.user_id),
                "week_id": t.week_id,
                "source": t.source,
                "free_source_slot": t.free_source_slot,
                "status": t.status,
                "created_at": t.created_at
            } for t in tickets
        ]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-sellers")
async def top_sellers(
    week_id: Optional[str] = None,
    limit: int = 10,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    try:
        res = JackpotService.compute_top_sellers(week_id=week_id, limit=limit)
        if not res.get("success"):
            raise HTTPException(status_code=500, detail=res.get("error", "Failed to compute top sellers"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top-buyers")
async def top_buyers(
    week_id: Optional[str] = None,
    limit: int = 10,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    try:
        res = JackpotService.compute_top_buyers(week_id=week_id, limit=limit)
        if not res.get("success"):
            raise HTTPException(status_code=500, detail=res.get("error", "Failed to compute top buyers"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/newcomers")
async def newcomers(
    week_id: Optional[str] = None,
    limit: int = 10,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    try:
        res = JackpotService.pick_newcomers_for_week(week_id=week_id, limit=limit)
        if not res.get("success"):
            raise HTTPException(status_code=500, detail=res.get("error", "Failed to pick newcomers"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

