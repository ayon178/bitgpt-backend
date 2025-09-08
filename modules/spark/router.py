from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from auth.service import authentication_service
from .service import SparkService


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


