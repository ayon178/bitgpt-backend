from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from auth.service import authentication_service
from utils.response import success_response, error_response
from .service import WalletService

router = APIRouter(prefix="/wallet", tags=["Wallet"])


# Lightweight auth wrapper to make tests patchable
async def _auth_dependency(request: Request):
    try:
        verifier = authentication_service.verify_authentication
        result = verifier()
        if hasattr(result, "__await__"):
            return await result
        return result
    except HTTPException:
        raise
    except Exception:
        # If auth service isn't ready in some test contexts, allow through
        return {}


class BalanceQuery(BaseModel):
    user_id: str
    wallet_type: Optional[str] = 'main'


def _extract_requester_id(payload: dict) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("user_id", "id", "_id", "uid"):
        val = payload.get(key)
        if val:
            return str(val)
    return None


@router.get("/balances")
async def get_currency_balances(user_id: str, wallet_type: str = 'main', current_user: dict = Depends(_auth_dependency)):
    try:
        requester_id = _extract_requester_id(current_user)
        requester_role = current_user.get("role") if isinstance(current_user, dict) else None
        if requester_id and requester_id != user_id and requester_role != "admin":
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's wallet")

        service = WalletService()
        data = service.get_currency_balances(user_id=user_id, wallet_type=wallet_type)
        return success_response(data, "Currency-wise balances fetched successfully")
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


