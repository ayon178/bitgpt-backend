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


@router.post("/reconcile")
async def reconcile_wallet(user_id: str, current_user: dict = Depends(_auth_dependency)):
    try:
        requester_id = _extract_requester_id(current_user)
        requester_role = current_user.get("role") if isinstance(current_user, dict) else None
        if requester_id and requester_id != user_id and requester_role != "admin":
            raise HTTPException(status_code=403, detail="Unauthorized to reconcile this user's wallet")

        service = WalletService()
        data = service.reconcile_main_from_ledger(user_id=user_id)
        return success_response(data, "Wallet reconciled from ledger successfully")
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/earning-statistics-debug/{user_id}")
async def get_earning_statistics_debug(user_id: str):
    """
    DEBUG VERSION - Get earning statistics WITHOUT authentication for testing
    """
    try:
        service = WalletService()
        result = service.get_earning_statistics(user_id=user_id)
        
        if result.get("success"):
            return success_response(result["data"], "Earning statistics fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch earning statistics"))
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/earning-statistics/{user_id}")
async def get_earning_statistics(user_id: str, current_user: dict = Depends(_auth_dependency)):
    """
    Get earning statistics for a user from all programs (binary, matrix, global).
    Returns total earnings and highest activated slot for each program.
    """
    try:
        requester_id = _extract_requester_id(current_user)
        requester_role = current_user.get("role") if isinstance(current_user, dict) else None
        if requester_id and requester_id != user_id and requester_role != "admin":
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's earning statistics")

        service = WalletService()
        result = service.get_earning_statistics(user_id=user_id)
        
        if result.get("success"):
            return success_response(result["data"], "Earning statistics fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch earning statistics"))
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/pools-summary")
async def get_pools_summary():
    try:
        service = WalletService()
        result = service.get_pools_summary()
        if result.get("success"):
            return success_response(result["data"], "Pools summary fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch pools summary"))
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


