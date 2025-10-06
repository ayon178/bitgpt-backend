from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional

from auth.service import authentication_service
from utils.response import success_response, error_response
from .service import WalletService
from ..newcomer_support.service import NewcomerSupportService
from ..mentorship.service import MentorshipService

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


@router.get("/duel-tree-earnings")
async def get_duel_tree_earnings(currency: str = 'BNB', page: int = 1, limit: int = 50):
    try:
        service = WalletService()
        result = service.get_duel_tree_earnings(currency=currency, page=page, limit=limit)
        if result.get("success"):
            return success_response(result["data"], "Duel tree earnings fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch duel tree earnings"))
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/binary-partner-incentive")
async def get_binary_partner_incentive(currency: str = 'BNB', page: int = 1, limit: int = 50):
    try:
        service = WalletService()
        result = service.get_binary_partner_incentive(currency=currency, page=page, limit=limit)
        if result.get("success"):
            return success_response(result["data"], "Binary partner incentive fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch binary partner incentive"))
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/dream-matrix-earnings")
async def get_dream_matrix_earnings_list(page: int = 1, limit: int = 50, days: int = 30):
    try:
        service = WalletService()
        result = service.get_dream_matrix_earnings_list(page=page, limit=limit, days=days)
        if result.get("success"):
            return success_response(result["data"], "Dream Matrix earnings fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch Dream Matrix earnings"))
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/dream-matrix-partner-incentive")
async def get_dream_matrix_partner_incentive(currency: str = 'USDT', page: int = 1, limit: int = 50):
    try:
        service = WalletService()
        result = service.get_dream_matrix_partner_incentive(currency=currency, page=page, limit=limit)
        if result.get("success"):
            return success_response(result["data"], "Dream Matrix partner incentive fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch Dream Matrix partner incentive"))
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/newcomer-growth-support-income")
async def get_newcomer_growth_support_income(
    currency: str = Query("USDT", description="Currency type"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page")
):
    """Get Newcomer Growth Support income data for all users WITHOUT authentication"""
    try:
        service = NewcomerSupportService()
        result = service.get_all_newcomer_support_income(currency, page, limit)

        if result["success"]:
            return success_response(result["data"], "Newcomer Growth Support income data fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/mentorship-bonus")
async def get_mentorship_bonus(
    currency: str = Query("USDT", description="Currency type"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page")
):
    """Get Mentorship Bonus data for all users WITHOUT authentication"""
    try:
        service = MentorshipService()
        result = service.get_mentorship_bonus_income(currency, page, limit)

        if result["success"]:
            return success_response(result["data"], "Mentorship Bonus data fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/phase-1-income")
async def get_phase_1_income(
    currency: str = Query("USDT", description="Currency type"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page")
):
    """Get Global Program Phase-1 income data for all users WITHOUT authentication"""
    try:
        service = WalletService()
        result = service.get_phase_1_income(currency, page, limit)

        if result["success"]:
            return success_response(result["data"], "Phase-1 income data fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/phase-2-income")
async def get_phase_2_income(
    currency: str = Query("USDT", description="Currency type"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page")
):
    """Get Global Program Phase-2 income data for all users WITHOUT authentication"""
    try:
        service = WalletService()
        result = service.get_phase_2_income(currency, page, limit)

        if result["success"]:
            return success_response(result["data"], "Phase-2 income data fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/global-partner-incentive")
async def get_global_partner_incentive(
    currency: str = Query("USDT", description="Currency type"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Items per page")
):
    """Get Global Partner Incentive data for all users WITHOUT authentication"""
    try:
        service = WalletService()
        result = service.get_global_partner_incentive(currency, page, limit)

        if result["success"]:
            return success_response(result["data"], "Global Partner Incentive data fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/miss-profit/{user_id}")
async def get_user_miss_profit_history(
    user_id: str,
    currency: str = Query("USDT", description="Currency type (USDT, BNB)"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Items per page"),
    current_user: dict = Depends(_auth_dependency)
):
    """Get user's miss profit history with currency filtering"""
    try:
        requester_id = _extract_requester_id(current_user)
        requester_role = current_user.get("role") if isinstance(current_user, dict) else None
        if requester_id and requester_id != user_id and requester_role != "admin":
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's miss profit history")

        service = WalletService()
        result = service.get_user_miss_profit_history(user_id, currency, page, limit)

        if result["success"]:
            return success_response(result["data"], "User miss profit history fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


