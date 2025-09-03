from mongoengine import *
from typing import Annotated
from fastapi import Depends, APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from auth.service import Token
from auth.service import authentication_service
from utils.response import create_response
import logging

logger = logging.getLogger(__name__)


from auth.service import *

router = APIRouter()
auth_router = router

@router.post("/request_authentication", response_model=dict)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    try:
        token, msg = authentication_service.authenticate_user(form_data.username, form_data.password)

        if not token:
            return create_response(
                status="Error",
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=msg,
                data=None
            )

        return create_response(
            status="Ok",
            status_code=status.HTTP_200_OK,
            message="Login successful",
            data=token
        )
    except Exception as e:
        logger.error(f"[AUTH] Unexpected error during login: {e}", exc_info=True)
        return create_response(
            status="Error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal server error during login",
            data={"error": str(e)}
        )

@router.get("/verify_authentication", response_model=dict)
async def read_users_me(current_user: Annotated[dict, Depends(authentication_service.verify_authentication)]):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException as e:
        return create_response(
            status="Error",
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=e.detail,
            data=None
        )
    except Exception as e:
        return create_response(
            status="Error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=str(e),
            data=None
        )

    return current_user


class LoginRequest(BaseModel):
    wallet_address: str | None = Field(None, description="Wallet address for login")
    email: str | None = Field(None, description="Email for admin/shareholder login")
    password: str | None = Field(None, description="Password for admin/shareholder login")

    class Config:
        json_schema_extra = {
            "examples": [
                {"wallet_address": "0xABCDEF0123456789"},
                {"email": "admin@example.com", "password": "secret123"},
                {"wallet_address": "0xABCDEF0123456789", "password": "secret123"}
            ]
        }


@router.post("/login", response_model=dict)
async def custom_login(payload: LoginRequest):
    result, error = authentication_service.login_with_rules(
        wallet_address=payload.wallet_address,
        email=payload.email,
        password=payload.password
    )

    if error:
        return create_response(
            status="Error",
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error,
            data=None,
        )

    return create_response(
        status="Ok",
        status_code=status.HTTP_200_OK,
        message="Login successful",
        data=result,
    )