from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId
from datetime import datetime

from ..utils.response import success_response, error_response
from ..auth.service import authentication_service
from .model import SpilloverQueue, SpilloverPlacement, SpilloverSettings, SpilloverLog, SpilloverStatistics

router = APIRouter(prefix="/spillover", tags=["Binary Spillover"])


class QueueSpilloverRequest(BaseModel):
    user_id: str
    original_parent_id: str
    intended_parent_id: str
    spillover_reason: str
    preferred_side: Optional[str] = "left"


class SettingsUpdateRequest(BaseModel):
    enabled: bool
    bfs_search_limit: int
    prefer_balance: bool
    max_queue_attempts: int
    queue_batch_size: int
    far_left_strategy: bool


@router.post("/queue")
async def queue_spillover(request: QueueSpilloverRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    try:
        item = SpilloverQueue(
            user_id=ObjectId(request.user_id),
            original_parent_id=ObjectId(request.original_parent_id),
            intended_parent_id=ObjectId(request.intended_parent_id),
            spillover_reason=request.spillover_reason,
            preferred_side=request.preferred_side,
            status='queued'
        )
        item.save()

        SpilloverLog(
            user_id=item.user_id,
            action_type='queued',
            description='Spillover queued',
            related_queue_id=item.id,
            data={"intended_parent_id": request.intended_parent_id}
        ).save()

        return success_response({"queue_id": str(item.id), "status": item.status}, "Spillover queued")
    except Exception as e:
        return error_response(str(e))


@router.get("/queue")
async def list_queue(status: str = Query("queued"), limit: int = Query(50, le=200), current_user: dict = Depends(authentication_service.verify_authentication)):
    try:
        items = SpilloverQueue.objects(status=status).order_by('created_at').limit(limit)
        return success_response({
            "items": [
                {
                    "id": str(i.id),
                    "user_id": str(i.user_id),
                    "original_parent_id": str(i.original_parent_id),
                    "intended_parent_id": str(i.intended_parent_id),
                    "status": i.status,
                    "attempts": i.attempts,
                    "created_at": i.created_at
                } for i in items
            ],
            "count": len(items)
        }, "Spillover queue listed")
    except Exception as e:
        return error_response(str(e))


@router.get("/placements/{user_id}")
async def list_placements(user_id: str, limit: int = Query(50, le=200), current_user: dict = Depends(authentication_service.verify_authentication)):
    try:
        items = SpilloverPlacement.objects(user_id=ObjectId(user_id)).order_by('-processed_at').limit(limit)
        return success_response({
            "placements": [
                {
                    "id": str(i.id),
                    "original_parent_id": str(i.original_parent_id),
                    "spillover_parent_id": str(i.spillover_parent_id),
                    "position": i.position,
                    "spillover_level": i.spillover_level,
                    "processed_at": i.processed_at
                } for i in items
            ],
            "count": len(items)
        }, "Spillover placements listed")
    except Exception as e:
        return error_response(str(e))


@router.get("/settings")
async def get_settings(current_user: dict = Depends(authentication_service.verify_authentication)):
    try:
        settings = SpilloverSettings.objects().first()
        if not settings:
            settings = SpilloverSettings()
            settings.save()
        return success_response({
            "enabled": settings.enabled,
            "bfs_search_limit": settings.bfs_search_limit,
            "prefer_balance": settings.prefer_balance,
            "max_queue_attempts": settings.max_queue_attempts,
            "queue_batch_size": settings.queue_batch_size,
            "far_left_strategy": settings.far_left_strategy
        }, "Spillover settings")
    except Exception as e:
        return error_response(str(e))


@router.post("/settings")
async def update_settings(req: SettingsUpdateRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    try:
        settings = SpilloverSettings.objects().first() or SpilloverSettings()
        settings.enabled = req.enabled
        settings.bfs_search_limit = req.bfs_search_limit
        settings.prefer_balance = req.prefer_balance
        settings.max_queue_attempts = req.max_queue_attempts
        settings.queue_batch_size = req.queue_batch_size
        settings.far_left_strategy = req.far_left_strategy
        settings.last_updated = datetime.utcnow()
        settings.save()

        SpilloverLog(user_id=ObjectId("000000000000000000000000"), action_type='settings_update', description='Spillover settings updated').save()
        return success_response({"message": "Settings updated"}, "Spillover settings updated")
    except Exception as e:
        return error_response(str(e))


@router.get("/statistics")
async def get_statistics(period: str = Query("all_time", regex="^(daily|weekly|monthly|all_time)$"), current_user: dict = Depends(authentication_service.verify_authentication)):
    try:
        stat = SpilloverStatistics.objects(period=period).order_by('-last_updated').first()
        if not stat:
            return success_response({
                "period": period,
                "totals": {"queued": 0, "processed": 0, "failed": 0, "attempts": 0},
                "by_level": {},
                "by_position": {"left": 0, "right": 0}
            }, "Spillover statistics")

        return success_response({
            "period": stat.period,
            "period_start": stat.period_start,
            "period_end": stat.period_end,
            "totals": {
                "queued": stat.total_queued,
                "processed": stat.total_processed,
                "failed": stat.total_failed,
                "attempts": stat.total_attempts,
            },
            "by_level": stat.by_level,
            "by_position": stat.by_position
        }, "Spillover statistics")
    except Exception as e:
        return error_response(str(e))


