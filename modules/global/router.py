from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from decimal import Decimal
from .service import GlobalService
from auth.service import authentication_service
from utils.response import success_response, error_response

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

async def _auth_dependency(request: Request):
    """Authentication dependency for Global program endpoints."""
    try:
        # Use the existing authentication service method
        from fastapi.security import OAuth2PasswordBearer
        from typing import Annotated
        
        oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # Use the existing verify_authentication method
        current_user_data = await authentication_service.verify_authentication(request, token)
        
        # More robust user_id extraction
        user_id_keys = ["user_id", "id", "_id", "uid"]
        authenticated_user_id = None
        for key in user_id_keys:
            if current_user_data and current_user_data.get(key):
                authenticated_user_id = str(current_user_data[key])
                break
        
        if not authenticated_user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        
        return current_user_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

# ==================== EXISTING GLOBAL API ENDPOINTS ====================

@router.post("/join")
async def join_global(
    request: GlobalJoinRequest,
    current_user: dict = Depends(_auth_dependency)
):
    """Join Global program with $33 (Phase-1 Slot-1) - Section 1.1 User Join Process
    
    MANDATORY JOIN SEQUENCE ENFORCEMENT:
    Users must join Binary and Matrix programs first before joining Global program.
    This enforces the required sequence: Binary → Matrix → Global
    """
    # Authorization check
    user_id_keys = ["user_id", "id", "_id", "uid"]
    authenticated_user_id = None
    for key in user_id_keys:
        if current_user and current_user.get(key):
            authenticated_user_id = str(current_user[key])
            break
    
    if not authenticated_user_id:
        return error_response("User ID not found in token", status_code=401)
    
    # Verify user can only join for themselves
    if request.user_id != authenticated_user_id:
        return error_response("Unauthorized to join Global program for this user", status_code=403)
    
    # MANDATORY JOIN SEQUENCE VALIDATION
    from ..user.sequence_service import ProgramSequenceService
    sequence_service = ProgramSequenceService()
    
    is_valid, error_msg = sequence_service.validate_program_join_sequence(
        user_id=request.user_id,
        target_program='global'
    )
    
    if not is_valid:
        return error_response(f"Join sequence violation: {error_msg}", status_code=400)
    
    service = GlobalService()
    result = service.join_global(user_id=request.user_id, tx_hash=request.tx_hash, amount=Decimal(str(request.amount)))
    if result.get("success"):
        return success_response(result, "Successfully joined Global program")
    return error_response(result.get("error", "Failed to join Global program"), status_code=400)

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

@router.get("/statistics/{user_id}")
async def get_team_statistics(user_id: str):
    """Get comprehensive team statistics for a user including total and today counts"""
    service = GlobalService()
    result = service.get_team_statistics(user_id)
    if result.get("success"):
        return {"status": "Ok", "data": result["statistics"]}
    raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch team statistics"))

@router.get("/earnings/{user_id}")
async def get_global_earnings(
    user_id: str,
    phase: str = None,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get Global program earnings data matching frontend matrixData.js structure"""
    try:
        # Extract user ID from current_user with fallback options
        authenticated_user_id = None
        user_id_keys = ["user_id", "_id", "id", "uid"]

        for key in user_id_keys:
            if current_user and current_user.get(key):
                authenticated_user_id = str(current_user[key])
                break
        
        # Authorization check - users can only access their own data
        if authenticated_user_id and authenticated_user_id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's Global earnings")

        service = GlobalService()
        result = service.get_global_earnings(user_id, phase)

        if result["success"]:
            return success_response(result["data"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))

@router.get("/earnings/details/{item_id}")
async def get_global_earnings_details(
    item_id: int,
    phase: str = None,
    user_id: str = None,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get specific Global earnings item details by item_id"""
    try:
        # Extract user ID from current_user with fallback options
        authenticated_user_id = None
        user_id_keys = ["user_id", "_id", "id", "uid"]

        for key in user_id_keys:
            if current_user and current_user.get(key):
                authenticated_user_id = str(current_user[key])
                break
        
        # Use provided user_id or authenticated user's ID
        if user_id:
            if authenticated_user_id and authenticated_user_id != user_id:
                raise HTTPException(status_code=403, detail="Unauthorized to view this user's Global earnings")
        else:
            user_id = authenticated_user_id
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found")

        service = GlobalService()
        result = service.get_global_earnings_details(user_id, item_id, phase)

        if result["success"]:
            return success_response(result["data"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))