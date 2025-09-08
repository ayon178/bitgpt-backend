from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId
from .model import JackpotTicket
from .service import JackpotService
from auth.service import authentication_service


router = APIRouter(prefix="/jackpot", tags=["Jackpot"])


class TicketQuery(BaseModel):
    user_id: Optional[str] = None
    referrer_user_id: Optional[str] = None
    week_id: Optional[str] = None
    status: Optional[str] = None  # active|used|expired


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

