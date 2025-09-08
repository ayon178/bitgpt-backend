from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List
from bson import ObjectId
from datetime import datetime

from utils.response import success_response, error_response
from auth.service import authentication_service
from .model import RecycleQueue, RecyclePlacement, RecycleSettings, RecycleLog, RecycleStatistics, RecycleRule

router = APIRouter(prefix="/recycle", tags=["Matrix Recycle"])


class QueueRecycleRequest(BaseModel):
    user_id: str
    parent_id: str
    matrix_level: int
    slot_no: int
    recycle_reason: str
    preferred_position: Optional[str] = "center"
    recycle_amount: float = 0


class SettingsUpdateRequest(BaseModel):
    enabled: bool
    auto_recycle_enabled: bool
    max_queue_attempts: int
    queue_batch_size: int
    carry_over_earnings: bool
    lock_center_position_for_upline_reserve: bool


@router.post("/queue")
async def queue_recycle(request: QueueRecycleRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    try:
        item = RecycleQueue(
            user_id=ObjectId(request.user_id),
            parent_id=ObjectId(request.parent_id),
            matrix_level=request.matrix_level,
            slot_no=request.slot_no,
            recycle_reason=request.recycle_reason,
            preferred_position=request.preferred_position,
            recycle_amount=request.recycle_amount,
            status='queued'
        )
        item.save()

        RecycleLog(
            user_id=item.user_id,
            action_type='queued',
            description='Recycle queued',
            related_queue_id=item.id,
            data={"matrix_level": request.matrix_level, "slot_no": request.slot_no}
        ).save()

        return success_response({
            "queue_id": str(item.id),
            "status": item.status
        }, "Recycle queued")
    except Exception as e:
        return error_response(str(e))


@router.get("/queue")
async def list_queue(status: str = Query("queued"), limit: int = Query(50, le=200), current_user: dict = Depends(authentication_service.verify_authentication)):
    try:
        items = RecycleQueue.objects(status=status).order_by('created_at').limit(limit)
        return success_response({
            "items": [
                {
                    "id": str(i.id),
                    "user_id": str(i.user_id),
                    "parent_id": str(i.parent_id),
                    "matrix_level": i.matrix_level,
                    "slot_no": i.slot_no,
                    "recycle_reason": i.recycle_reason,
                    "preferred_position": i.preferred_position,
                    "status": i.status,
                    "attempts": i.attempts,
                    "created_at": i.created_at,
                } for i in items
            ],
            "count": len(items)
        }, "Recycle queue listed")
    except Exception as e:
        return error_response(str(e))


@router.get("/placements/{user_id}")
async def list_placements(user_id: str, limit: int = Query(50, le=200), current_user: dict = Depends(authentication_service.verify_authentication)):
    try:
        items = RecyclePlacement.objects(user_id=ObjectId(user_id)).order_by('-processed_at').limit(limit)
        return success_response({
            "placements": [
                {
                    "id": str(i.id),
                    "old_parent_id": str(i.old_parent_id),
                    "new_parent_id": str(i.new_parent_id),
                    "matrix_level": i.matrix_level,
                    "slot_no": i.slot_no,
                    "position": i.position,
                    "recycle_amount": float(i.recycle_amount),
                    "processed_at": i.processed_at,
                } for i in items
            ],
            "count": len(items)
        }, "Recycle placements listed")
    except Exception as e:
        return error_response(str(e))


@router.get("/settings")
async def get_settings(current_user: dict = Depends(authentication_service.verify_authentication)):
    try:
        settings = RecycleSettings.objects().first()
        if not settings:
            settings = RecycleSettings()
            settings.save()
        return success_response({
            "enabled": settings.enabled,
            "auto_recycle_enabled": settings.auto_recycle_enabled,
            "max_queue_attempts": settings.max_queue_attempts,
            "queue_batch_size": settings.queue_batch_size,
            "carry_over_earnings": settings.carry_over_earnings,
            "lock_center_position_for_upline_reserve": settings.lock_center_position_for_upline_reserve,
            "rules": [
                {
                    "slot_no": r.slot_no,
                    "required_members": r.required_members,
                    "recycle_position": r.recycle_position,
                    "auto_recycle_enabled": r.auto_recycle_enabled,
                    "carry_over_earnings": r.carry_over_earnings,
                } for r in (settings.rules or [])
            ]
        }, "Recycle settings")
    except Exception as e:
        return error_response(str(e))


@router.post("/settings")
async def update_settings(req: SettingsUpdateRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    try:
        settings = RecycleSettings.objects().first() or RecycleSettings()
        settings.enabled = req.enabled
        settings.auto_recycle_enabled = req.auto_recycle_enabled
        settings.max_queue_attempts = req.max_queue_attempts
        settings.queue_batch_size = req.queue_batch_size
        settings.carry_over_earnings = req.carry_over_earnings
        settings.lock_center_position_for_upline_reserve = req.lock_center_position_for_upline_reserve
        settings.last_updated = datetime.utcnow()
        settings.save()

        RecycleLog(user_id=ObjectId("000000000000000000000000"), action_type='settings_update', description='Recycle settings updated').save()
        return success_response({"message": "Settings updated"}, "Recycle settings updated")
    except Exception as e:
        return error_response(str(e))


@router.get("/statistics")
async def get_statistics(period: str = Query("all_time", regex="^(daily|weekly|monthly|all_time)$"), current_user: dict = Depends(authentication_service.verify_authentication)):
    try:
        stat = RecycleStatistics.objects(period=period).order_by('-last_updated').first()
        if not stat:
            return success_response({
                "period": period,
                "totals": {
                    "queued": 0, "processed": 0, "failed": 0, "attempts": 0,
                    "recycle_amount": 0, "distributed_amount": 0
                },
                "by_slot": {},
                "by_level": {}
            }, "Recycle statistics")

        return success_response({
            "period": stat.period,
            "period_start": stat.period_start,
            "period_end": stat.period_end,
            "totals": {
                "queued": stat.total_queued,
                "processed": stat.total_processed,
                "failed": stat.total_failed,
                "attempts": stat.total_attempts,
                "recycle_amount": float(stat.total_recycle_amount),
                "distributed_amount": float(stat.total_distributed_amount),
            },
            "by_slot": stat.by_slot,
            "by_level": stat.by_level
        }, "Recycle statistics")
    except Exception as e:
        return error_response(str(e))


