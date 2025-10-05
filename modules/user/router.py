from fastapi import APIRouter, Depends, status, Request, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Optional
from utils.response import create_response, success_response, error_response
from modules.user.service import create_user_service
import asyncio
from modules.tree.service import TreeService
from modules.rank.service import RankService
from modules.user.service import create_root_user_service
from auth.service import authentication_service
# import Depends



class CreateUserRequest(BaseModel):
    uid: str = Field(..., description="Unique user identifier")
    refer_code: str = Field(..., description="Unique referral code for the user")
    # Accept both for backward compatibility; prefer upline_id per docs
    upline_id: Optional[str] = Field(None, description="Mongo ObjectId string of the upline (docs preferred)")
    refered_by: Optional[str] = Field(None, description="Mongo ObjectId string of the referrer (legacy)")
    wallet_address: str = Field(..., description="Unique blockchain wallet address")
    name: str = Field(..., description="Full name of the user")
    role: Optional[str] = Field(None, description="Role: user | admin | shareholder")
    email: Optional[str] = Field(None, description="Email address")
    password: Optional[str] = Field(None, description="Plain password if applicable")
    # Blockchain payment proofs (frontend passes on-chain tx proofs)
    binary_payment_tx: Optional[str] = Field(None, description="On-chain tx hash for 0.0066 BNB binary join")
    matrix_payment_tx: Optional[str] = Field(None, description="On-chain tx hash for $11 matrix join (optional)")
    global_payment_tx: Optional[str] = Field(None, description="On-chain tx hash for $33 global join (optional)")
    network: Optional[str] = Field(None, description="Blockchain network identifier, e.g., BSC, ETH, TESTNET")

    class Config:
        json_schema_extra = {
            "example": {
                "uid": "user123",
                "refer_code": "RC12345",
                "upline_id": "66f1aab2c1f3a2a9c0b4e123",
                "wallet_address": "0xABCDEF0123456789",
                "name": "John Doe",
                "role": "user",
                "email": "john@example.com",
                "password": "secret123"
            }
        }

user_router = APIRouter()


def _run_async(coro):
    try:
        asyncio.run(coro)
    except Exception:
        pass


def _post_create_background(user_id: str, referrer_id: str):
    try:
        _run_async(TreeService.create_tree_placement(
            user_id=user_id,
            referrer_id=referrer_id,
            program='binary',
            slot_no=1
        ))
    except Exception:
        pass
    try:
        RankService().update_user_rank(user_id=user_id)
    except Exception:
        pass


@user_router.post("/create")
async def create_user(payload: CreateUserRequest, background_tasks: BackgroundTasks):
    # Map upline_id -> refered_by (Option B)
    payload_dict = payload.dict()
    if payload_dict.get("upline_id") and not payload_dict.get("refered_by"):
        payload_dict["refered_by"] = payload_dict["upline_id"]
    result, error = create_user_service(payload_dict)

    if error:
        return create_response(
            status="Error",
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error,
            data=None,
        )

    # Schedule background placement (non-blocking)
    try:
        background_tasks.add_task(_post_create_background, result.get("_id"), payload_dict.get("refered_by"))
    except Exception:
        pass

    return create_response(
        status="Ok",
        status_code=status.HTTP_201_CREATED,
        message="User created successfully",
        data=result,
    )


class CreateRootUserRequest(BaseModel):
    uid: str = Field(..., description="Unique user identifier (e.g., ROOT)")
    refer_code: str = Field(..., description="Referral code for root (e.g., ROOT001)")
    wallet_address: str = Field(..., description="Blockchain wallet address for root")
    name: str = Field(..., description="Display name for root user")
    role: Optional[str] = Field("admin", description="Role, defaults to admin")
    email: Optional[str] = Field(None, description="Email address")
    password: Optional[str] = Field(None, description="Optional password")


@user_router.post("/create-root")
async def create_root_user(payload: CreateRootUserRequest):
    result, error = create_root_user_service(payload.dict())

    if error:
        return create_response(
            status="Error",
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error,
            data=None,
        )

    return create_response(
        status="Ok",
        status_code=status.HTTP_201_CREATED,
        message="Root user created successfully",
        data=result,
    )


@user_router.get("/my-community")
async def get_my_community(
    user_id: str = Query(..., description="User ID"),
    program_type: str = Query("binary", description="Program type: 'binary' or 'matrix'"),
    slot_number: Optional[int] = Query(None, description="Slot number filter"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page"),
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get community members (referred users) for a user"""
    try:
        from modules.user.service import UserService
        
        service = UserService()
        result = service.get_my_community(
            user_id=user_id,
            program_type=program_type,
            slot_number=slot_number,
            page=page,
            limit=limit
        )
        
        if result["success"]:
            return success_response(result["data"], "Community members fetched successfully")
        else:
            return error_response(result["error"])
        
    except Exception as e:
        return error_response(str(e))


@user_router.get("/program-sequence-status/{user_id}")
async def get_program_sequence_status(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get user's program sequence status and next allowed programs"""
    try:
        from modules.user.sequence_service import ProgramSequenceService
        
        # Authorization check - users can only access their own data
        authenticated_user_id = None
        user_id_keys = ["user_id", "_id", "id", "uid"]
        
        for key in user_id_keys:
            if current_user and current_user.get(key):
                authenticated_user_id = str(current_user[key])
                break
        
        if authenticated_user_id and authenticated_user_id != user_id:
            return error_response("Unauthorized to view this user's program sequence status", status_code=403)
        
        sequence_service = ProgramSequenceService()
        result = sequence_service.get_user_program_sequence_status(user_id)
        
        if result["success"]:
            return success_response(result["data"], "Program sequence status fetched successfully")
        else:
            return error_response(result["error"])
        
    except Exception as e:
        return error_response(str(e))


@user_router.get("/program-sequence-info")
async def get_program_sequence_info(
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get information about the mandatory program sequence"""
    try:
        from modules.user.sequence_service import ProgramSequenceService
        
        sequence_service = ProgramSequenceService()
        result = sequence_service.get_program_sequence_info()
        
        if result["success"]:
            return success_response(result["data"], "Program sequence info fetched successfully")
        else:
            return error_response(result["error"])
        
    except Exception as e:
        return error_response(str(e))


@user_router.get("/sequence-compliance/{user_id}")
async def check_sequence_compliance(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Check if user's program participation follows the mandatory sequence"""
    try:
        from modules.user.sequence_service import ProgramSequenceService
        
        # Authorization check - users can only access their own data or admin can access any
        authenticated_user_id = None
        user_id_keys = ["user_id", "_id", "id", "uid"]
        
        for key in user_id_keys:
            if current_user and current_user.get(key):
                authenticated_user_id = str(current_user[key])
                break
        
        # Allow admin to check any user's compliance
        is_admin = current_user.get("role") == "admin"
        
        if not is_admin and authenticated_user_id and authenticated_user_id != user_id:
            return error_response("Unauthorized to check this user's sequence compliance", status_code=403)
        
        sequence_service = ProgramSequenceService()
        result = sequence_service.check_user_sequence_compliance(user_id)
        
        if result["success"]:
            return success_response(result["data"], "Sequence compliance checked successfully")
        else:
            return error_response(result["error"])
        
    except Exception as e:
        return error_response(str(e))


@user_router.post("/validate-program-join/{user_id}")
async def validate_program_join(
    user_id: str,
    target_program: str = Query(..., description="Target program: 'binary', 'matrix', or 'global'"),
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Validate if user can join a specific program based on mandatory sequence"""
    try:
        from modules.user.sequence_service import ProgramSequenceService
        
        # Authorization check - users can only validate for themselves or admin can validate any
        authenticated_user_id = None
        user_id_keys = ["user_id", "_id", "id", "uid"]
        
        for key in user_id_keys:
            if current_user and current_user.get(key):
                authenticated_user_id = str(current_user[key])
                break
        
        # Allow admin to validate for any user
        is_admin = current_user.get("role") == "admin"
        
        if not is_admin and authenticated_user_id and authenticated_user_id != user_id:
            return error_response("Unauthorized to validate program join for this user", status_code=403)
        
        sequence_service = ProgramSequenceService()
        is_valid, error_msg = sequence_service.validate_program_join_sequence(user_id, target_program)
        
        result = {
            "user_id": user_id,
            "target_program": target_program,
            "is_valid": is_valid,
            "error_message": error_msg,
            "can_join": is_valid
        }
        
        if is_valid:
            return success_response(result, "Program join validation successful")
        else:
            return error_response(error_msg, status_code=400)
        
    except Exception as e:
        return error_response(str(e))

