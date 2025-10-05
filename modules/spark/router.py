from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from auth.service import authentication_service
from .service import SparkService
from pydantic import BaseModel
from decimal import Decimal


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
    total_spark_pool: float
    participant_user_ids: list[str]


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

