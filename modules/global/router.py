from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from decimal import Decimal
from .service import GlobalService

router = APIRouter(prefix="/global", tags=["Global Program"])

class GlobalJoinRequest(BaseModel):
    user_id: str
    tx_hash: str
    amount: float

class AddTeamRequest(BaseModel):
    user_id: str
    member_id: str

class DistributionRequest(BaseModel):
    user_id: str
    amount: float

class GlobalUpgradeRequest(BaseModel):
    user_id: str
    to_slot_no: int
    tx_hash: str
    amount: float

@router.post("/join")
async def join_global(request: GlobalJoinRequest):
    service = GlobalService()
    result = service.join_global(user_id=request.user_id, tx_hash=request.tx_hash, amount=Decimal(str(request.amount)))
    if result.get("success"):
        return {"status": "Ok", "data": result}
    raise HTTPException(status_code=400, detail=result.get("error", "Failed to join Global program"))

@router.post("/upgrade")
async def upgrade_global(request: GlobalUpgradeRequest):
    service = GlobalService()
    result = service.upgrade_global_slot(user_id=request.user_id, to_slot_no=request.to_slot_no, tx_hash=request.tx_hash, amount=Decimal(str(request.amount)))
    if result.get("success"):
        return {"status": "Ok", "data": result}
    raise HTTPException(status_code=400, detail=result.get("error", "Failed to upgrade Global slot"))

@router.get("/status/{user_id}")
async def get_global_status(user_id: str):
    service = GlobalService()
    result = service.get_status(user_id)
    if result.get("success"):
        return {"status": "Ok", "data": result["status"]}
    raise HTTPException(status_code=404, detail=result.get("error", "Global status not found"))

@router.post("/progress/{user_id}")
async def process_progress(user_id: str):
    service = GlobalService()
    result = service.process_progression(user_id)
    if result.get("success"):
        return {"status": "Ok", "data": result}
    raise HTTPException(status_code=400, detail=result.get("error", "Progression not ready"))

@router.post("/team/add")
async def add_global_team_member(request: AddTeamRequest):
    service = GlobalService()
    result = service.add_team_member(request.user_id, request.member_id)
    if result.get("success"):
        return {"status": "Ok", "data": result["status"]}
    raise HTTPException(status_code=400, detail=result.get("error", "Failed to add team member"))

@router.get("/team/{user_id}")
async def get_global_team(user_id: str):
    service = GlobalService()
    result = service.get_team(user_id)
    if result.get("success"):
        return {"status": "Ok", "data": result["team"]}
    raise HTTPException(status_code=404, detail=result.get("error", "Team not found"))

@router.post("/distribute")
async def distribute_global(request: DistributionRequest):
    service = GlobalService()
    result = service.process_distribution(request.user_id, Decimal(str(request.amount)), currency='USD')
    if result.get("success"):
        return {"status": "Ok", "data": result["distribution_breakdown"]}
    raise HTTPException(status_code=400, detail=result.get("error", "Distribution failed"))

@router.get("/seats/{user_id}/{phase}")
async def get_phase_seats(user_id: str, phase: str):
    service = GlobalService()
    result = service.get_phase_seats(user_id, phase)
    if result.get("success"):
        return {"status": "Ok", "data": result}
    raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch seats"))

@router.get("/preview-distribution/{amount}")
async def preview_distribution(amount: float):
    service = GlobalService()
    result = service.preview_distribution(Decimal(str(amount)))
    if result.get("success"):
        return {"status": "Ok", "data": result["distribution_breakdown"]}
    raise HTTPException(status_code=400, detail=result.get("error", "Failed to preview distribution"))

@router.get("/tree/{user_id}/{phase}")
async def get_global_tree(user_id: str, phase: str):
    service = GlobalService()
    result = service.get_global_tree(user_id, phase)
    if result.get("success"):
        return {"status": "Ok", "data": result}
    raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch global tree"))
