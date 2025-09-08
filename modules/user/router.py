from fastapi import APIRouter, status, Request
from pydantic import BaseModel, Field
from typing import Optional
from utils.response import create_response
from modules.user.service import create_user_service


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


@user_router.post("/create")
async def create_user(payload: CreateUserRequest):
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

    return create_response(
        status="Ok",
        status_code=status.HTTP_201_CREATED,
        message="User created successfully",
        data=result,
    )

