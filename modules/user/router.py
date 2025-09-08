from fastapi import APIRouter, status, Request, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
from utils.response import create_response
from modules.user.service import create_user_service
import asyncio
from modules.tree.service import TreeService
from modules.rank.service import RankService
from modules.user.service import create_root_user_service


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

