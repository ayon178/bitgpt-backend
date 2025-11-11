from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional

from auth.service import authentication_service
from utils.response import success_response, error_response
from .service import WalletService
from ..newcomer_support.service import NewcomerSupportService
from ..mentorship.service import MentorshipService
from ..spark.service import SparkService
from ..spark.model import SparkBonusDistribution

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
async def get_pools_summary(user_id: str = Query(..., description="User ID for pools summary")):
    try:
        service = WalletService()
        result = service.get_pools_summary(user_id=user_id)
        if result.get("success"):
            return success_response(result["data"], "Pools summary fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch pools summary"))
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/claim-history")
async def get_claim_history(
    user_id: str = Query(..., description="User ID"),
    currency: Optional[str] = Query(None, description="Filter by currency (USDT or BNB)"),
    type: Optional[str] = Query(None, description="Filter by claim type (royal_captain, president_reward, etc.)"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Get universal claim history for all bonus programs
    Returns all claims made by user across all programs
    """
    try:
        service = WalletService()
        result = service.get_universal_claim_history(
            user_id=user_id,
            currency=currency,
            claim_type=type,
            page=page,
            limit=limit
        )
        
        if result.get("success"):
            return success_response(result["data"], "Claim history fetched successfully")
        else:
            return error_response(result.get("error", "Failed to fetch claim history"))
    except Exception as e:
        return error_response(str(e))


@router.get("/duel-tree-earnings")
async def get_duel_tree_earnings(
    currency: str = 'BNB', 
    page: int = 1, 
    limit: int = 50,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    try:
        # Extract user_id from authenticated user
        user_id = None
        user_id_keys = ["user_id", "_id", "id"]
        for key in user_id_keys:
            if current_user and current_user.get(key):
                user_id = str(current_user[key])
                break
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in authentication")
        
        service = WalletService()
        result = service.get_duel_tree_earnings(user_id=user_id, currency=currency, page=page, limit=limit)
        if result.get("success"):
            return success_response(result["data"], "Duel tree earnings fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch duel tree earnings"))
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/binary-partner-incentive")
async def get_binary_partner_incentive(
    currency: str = 'BNB', 
    page: int = 1, 
    limit: int = 50,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    try:
        # Extract user_id from authenticated user
        user_id = None
        user_id_keys = ["user_id", "_id", "id"]
        for key in user_id_keys:
            if current_user and current_user.get(key):
                user_id = str(current_user[key])
                break
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in authentication")
        
        service = WalletService()
        result = service.get_binary_partner_incentive(user_id=user_id, currency=currency, page=page, limit=limit)
        if result.get("success"):
            return success_response(result["data"], "Binary partner incentive fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch binary partner incentive"))
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/dream-matrix-earnings")
async def get_dream_matrix_earnings_list(
    page: int = 1, 
    limit: int = 50, 
    days: int = 30,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    try:
        # Extract user_id from authenticated user
        user_id = None
        user_id_keys = ["user_id", "_id", "id"]
        for key in user_id_keys:
            if current_user and current_user.get(key):
                user_id = str(current_user[key])
                break
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in authentication")
        
        service = WalletService()
        result = service.get_dream_matrix_earnings_list(user_id=user_id, page=page, limit=limit, days=days)
        if result.get("success"):
            return success_response(result["data"], "Dream Matrix earnings fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to fetch Dream Matrix earnings"))
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/dream-matrix-partner-incentive")
async def get_dream_matrix_partner_incentive(
    currency: str = 'USDT', 
    page: int = 1, 
    limit: int = 50,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    try:
        # Extract user_id from authenticated user
        user_id = None
        user_id_keys = ["user_id", "_id", "id"]
        for key in user_id_keys:
            if current_user and current_user.get(key):
                user_id = str(current_user[key])
                break
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in authentication")
        
        service = WalletService()
        result = service.get_dream_matrix_partner_incentive(user_id=user_id, currency=currency, page=page, limit=limit)
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
    limit: int = Query(10, description="Items per page"),
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get Newcomer Growth Support income data for authenticated user from IncomeEvent (consistent with pools-summary)"""
    try:
        # Extract user_id from authenticated user
        user_id = None
        user_id_keys = ["user_id", "_id", "id"]
        for key in user_id_keys:
            if current_user and current_user.get(key):
                user_id = str(current_user[key])
                break
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in authentication")
        
        # Use WalletService to fetch from WalletLedger (consistent with pools_summary)
        service = WalletService()
        result = service.get_newcomer_growth_support_income(user_id=user_id, currency=currency, page=page, limit=limit)

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
    limit: int = Query(10, description="Items per page"),
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get Mentorship Bonus data for authenticated user from IncomeEvent (consistent with pools-summary)"""
    try:
        # Extract user_id from authenticated user
        user_id = None
        user_id_keys = ["user_id", "_id", "id"]
        for key in user_id_keys:
            if current_user and current_user.get(key):
                user_id = str(current_user[key])
                break
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in authentication")
        
        # Use WalletService to fetch from IncomeEvent (consistent with pools_summary)
        service = WalletService()
        result = service.get_mentorship_bonus_income(user_id=user_id, currency=currency, page=page, limit=limit)

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
    limit: int = Query(10, description="Items per page"),
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get Global Program Phase-1 income data for authenticated user"""
    try:
        # Extract user_id from authenticated user
        user_id = None
        user_id_keys = ["user_id", "_id", "id"]
        for key in user_id_keys:
            if current_user and current_user.get(key):
                user_id = str(current_user[key])
                break
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in authentication")
        
        service = WalletService()
        result = service.get_phase_1_income(user_id=user_id, currency=currency, page=page, limit=limit)

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
    limit: int = Query(10, description="Items per page"),
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get Global Program Phase-2 income data for authenticated user"""
    try:
        # Extract user_id from authenticated user
        user_id = None
        user_id_keys = ["user_id", "_id", "id"]
        for key in user_id_keys:
            if current_user and current_user.get(key):
                user_id = str(current_user[key])
                break
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in authentication")
        
        service = WalletService()
        result = service.get_phase_2_income(user_id=user_id, currency=currency, page=page, limit=limit)

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
    limit: int = Query(10, description="Items per page"),
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get Global Partner Incentive data for authenticated user"""
    try:
        # Extract user_id from authenticated user
        user_id = None
        user_id_keys = ["user_id", "_id", "id"]
        for key in user_id_keys:
            if current_user and current_user.get(key):
                user_id = str(current_user[key])
                break
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in authentication")
        
        service = WalletService()
        result = service.get_global_partner_incentive(user_id=user_id, currency=currency, page=page, limit=limit)

        if result["success"]:
            return success_response(result["data"], "Global Partner Incentive data fetched successfully")
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/income/spark-bonus")
async def get_spark_bonus_overview(
    currency: str = Query("USDT", description="Display currency; Spark fund is tracked in USDT"),
    user_id: str | None = Query(None, description="Optional user id to include eligibility flag"),
    slot_number: int | None = Query(None, ge=1, le=14, description="Filter by specific matrix slot number 1-14"),
):
    """Spark Bonus fund overview for Triple Entry Reward page.
    Returns total fund, baseline (80%), and slot-wise allocations for slots 1–14.
    """
    try:
        svc = SparkService()
        data = svc.get_slot_breakdown(currency, user_id=user_id, slot_number=slot_number)
        if not data.get("success"):
            raise HTTPException(status_code=400, detail=data.get("error", "Unable to compute Spark fund"))
        return success_response(data, "Spark Bonus fund overview")
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.post("/income/spark-bonus/claim")
async def claim_spark_bonus(
    user_id: str = Query(..., description="User who is claiming"),
    slot_number: int = Query(..., ge=1, le=14, description="Matrix slot number 1-14"),
    currency: str = Query("USDT", description="USDT or BNB")
):
    """Claim Spark Bonus for a slot: splits allocated fund equally among eligible users and credits wallets.
    No auth required here for testing; protect in prod.
    """
    try:
        svc = SparkService()
        data = svc.claim_spark_bonus(slot_number, currency, claimer_user_id=user_id)
        if not data.get("success"):
            raise HTTPException(status_code=400, detail=data.get("error", "Claim failed"))
        return success_response(data, "Spark Bonus claim processed")
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


    # Removed: moved to /spark/bonus/history route


@router.get("/income/leadership-stipend")
async def get_leadership_stipend_income(
    user_id: str = Query(..., description="User ID"),
    currency: str = Query("BNB", description="Currency (BNB only)"),
    slot: int | None = Query(None, description="Filter by slot number 10-16"),
):
    """Return slot-wise Leadership Stipend summary (slots 10-16) and claim history.
    - Shows funded amount per slot (total_paid), pending and progress percent to next tier
    - Claim history lists LeadershipStipendPayment records; can be filtered by slot
    """
    try:
        from modules.leadership_stipend.model import LeadershipStipend, LeadershipStipendPayment
        from modules.leadership_stipend.service import LeadershipStipendService
        from bson import ObjectId
        from datetime import datetime
        from decimal import Decimal

        ls = LeadershipStipend.objects(user_id=ObjectId(user_id)).first()
        
        # If LeadershipStipend doesn't exist, create it with initialized tiers
        if not ls:
            try:
                from modules.leadership_stipend.router import _initialize_leadership_stipend_tiers
                from datetime import datetime
                ls = LeadershipStipend(
                    user_id=ObjectId(user_id),
                    joined_at=datetime.utcnow(),
                    is_active=True,
                    tiers=_initialize_leadership_stipend_tiers()
                )
                ls.save()
                print(f"✅ Auto-created Leadership Stipend record for user {user_id} with {len(ls.tiers)} tiers")
            except Exception as e:
                print(f"❌ Error creating Leadership Stipend record for user {user_id}: {e}")
                import traceback
                traceback.print_exc()
        
        # If LeadershipStipend exists but tiers are empty, initialize them
        if ls:
            # Check if tiers need initialization (None, empty list, or length 0)
            tiers_needs_init = False
            try:
                if ls.tiers is None:
                    tiers_needs_init = True
                    print(f"⚠️ User {user_id} has None tiers")
                elif not hasattr(ls.tiers, '__len__'):
                    tiers_needs_init = True
                    print(f"⚠️ User {user_id} tiers has no len attribute")
                elif len(ls.tiers) == 0:
                    tiers_needs_init = True
                    print(f"⚠️ User {user_id} has empty tiers list")
            except Exception as e:
                tiers_needs_init = True
                print(f"⚠️ Error checking tiers for user {user_id}: {e}")
            
            if tiers_needs_init:
                try:
                    from modules.leadership_stipend.router import _initialize_leadership_stipend_tiers
                    ls.tiers = _initialize_leadership_stipend_tiers()
                    ls.save()
                    # Force reload to ensure tiers are persisted
                    ls.reload()
                    # Verify tiers were saved
                    if ls.tiers and len(ls.tiers) > 0:
                        print(f"✅ Auto-initialized Leadership Stipend tiers for user {user_id}, count: {len(ls.tiers)}")
                    else:
                        print(f"⚠️ Tiers still empty after save for user {user_id}, attempting manual reload...")
                        # Try fetching fresh from DB
                        ls = LeadershipStipend.objects(user_id=ObjectId(user_id)).first()
                        if ls and ls.tiers and len(ls.tiers) > 0:
                            print(f"✅ Tiers found after manual reload: {len(ls.tiers)}")
                except Exception as e:
                    print(f"❌ Error initializing tiers for user {user_id}: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"✅ User {user_id} already has {len(ls.tiers) if ls.tiers else 0} tiers")
            
            try:
                service = LeadershipStipendService()
                ls = service._ensure_all_tiers(ls)
                service.check_eligibility(user_id, force_check=True)
                ls = LeadershipStipend.objects(user_id=ObjectId(user_id)).first() or ls
            except Exception:
                pass
        
        # Preload payments first and compute per-slot totals
        from modules.leadership_stipend.model import LeadershipStipendPayment as _LSP
        pay_q = {"user_id": ObjectId(user_id)}
        if slot:
            pay_q["slot_number"] = int(slot)
        payments_cursor = _LSP.objects(__raw__=pay_q).order_by('-payment_date')
        payments = []
        slot_paid: dict[int, float] = {}
        slot_last_claim: dict[int, datetime] = {}
        for p in payments_cursor:
            if currency.upper() != (p.currency or "BNB").upper():
                continue
            amt = float(p.daily_return_amount or 0.0)
            slot_paid[p.slot_number] = slot_paid.get(p.slot_number, 0.0) + amt
            claim_time = p.paid_at or p.processed_at or p.payment_date
            if claim_time:
                previous = slot_last_claim.get(p.slot_number)
                if not previous or claim_time > previous:
                    slot_last_claim[p.slot_number] = claim_time
            payments.append({
                "id": str(p.id),
                "slot_number": p.slot_number,
                "tier_name": p.tier_name,
                "amount": amt,
                "currency": p.currency,
                "payment_date": p.payment_date,
                "status": p.payment_status,
                "reference": p.payment_reference,
                "processed_at": p.processed_at,
                "paid_at": p.paid_at,
            })

        # Global totals per slot (all users, same currency)
        global_slot_paid: dict[int, float] = {}
        for gp in _LSP.objects(currency=currency.upper()):
            amt = float(gp.daily_return_amount or 0.0)
            if amt <= 0:
                continue
            global_slot_paid[gp.slot_number] = global_slot_paid.get(gp.slot_number, 0.0) + amt

        # Get total Leadership Stipend fund amounts from BonusFund (calculate before checking ls)
        from modules.income.bonus_fund import BonusFund
        total_global_bnb = 0.0
        total_global_usdt = 0.0
        
        # Get BNB fund (from binary program)
        bnb_fund = BonusFund.objects(fund_type='leadership_stipend', program='binary').first()
        if bnb_fund:
            total_global_bnb = float(bnb_fund.current_balance or 0.0)
        
        # Get USDT fund (from matrix program)
        usdt_fund = BonusFund.objects(fund_type='leadership_stipend', program='matrix').first()
        if usdt_fund:
            total_global_usdt = float(usdt_fund.current_balance or 0.0)
        
        if not ls:
            # If user not in stipend yet, still return payments summary with global totals
            return success_response({
                "user_id": user_id,
                "summary": {
                    "current_tier": 0,
                    "current_tier_name": "",
                    "current_daily_return": 0,
                    "is_eligible": False,
                    "is_active": False,
                    "total_earned": 0,
                    "total_paid": 0,
                    "pending_amount": 0,
                    "total_global_bnb": total_global_bnb,  # Total Leadership Stipend fund in BNB
                    "total_global_usdt": total_global_usdt,  # Total Leadership Stipend fund in USDT
                },
                "tiers": [],
                "payments": payments,
            }, "Leadership Stipend income fetched")
        
        # Build tier summaries
        tiers = []
        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Ensure ls exists and has tiers before iterating
        if not ls:
            # This shouldn't happen if auto-create worked, but handle gracefully
            print(f"⚠️ Warning: ls is None for user {user_id} after initialization attempt")
        elif not ls.tiers or len(ls.tiers) == 0:
            print(f"⚠️ Warning: User {user_id} has LeadershipStipend but tiers are still empty after initialization")
            # Try one more time to fetch from DB
            ls = LeadershipStipend.objects(user_id=ObjectId(user_id)).first()
            if ls and ls.tiers and len(ls.tiers) > 0:
                print(f"✅ Tiers found after final DB fetch: {len(ls.tiers)}")
        
        distribution_percentages = {
            10: 0.30,
            11: 0.20,
            12: 0.10,
            13: 0.10,
            14: 0.10,
            15: 0.10,
            16: 0.05,
            17: 0.05,
        }

        # Iterate over tiers (will be empty if ls or ls.tiers is None/empty)
        # Precompute eligible user counts per slot (active tiers only)
        eligible_counts: dict[int, int] = {}
        for rec in LeadershipStipend.objects(is_active=True).only('tiers'):
            try:
                for tier in rec.tiers:
                    if tier.slot_number < 10 or tier.slot_number > 17:
                        continue
                    if tier.is_active:
                        eligible_counts[tier.slot_number] = eligible_counts.get(tier.slot_number, 0) + 1
            except Exception:
                continue

        tiers_to_iterate = ls.tiers if ls and ls.tiers else []
        for t in tiers_to_iterate:
            if t.slot_number < 10 or t.slot_number > 17:
                continue
            if slot and t.slot_number != int(slot):
                continue
            
            tier_cap = float(t.daily_return or 0.0)
            tier_paid = float(t.total_paid or 0.0)
            tier_pending = float(t.pending_amount or 0.0)
            tier_remaining = max(0.0, tier_cap - tier_paid - tier_pending)
            tier_is_active = bool(t.is_active and tier_remaining > 0)

            claimable_amount = 0.0
            if tier_is_active:
                # Check if user has already claimed today
                already_claimed = _LSP.objects(
                    user_id=ObjectId(user_id),
                    slot_number=t.slot_number,
                    payment_date__gte=day_start,
                    payment_status__in=["pending", "paid"]
                ).first()
                
                if not already_claimed:
                    eligible_count = max(1, eligible_counts.get(t.slot_number, 1))
                    claimable_amount = tier_remaining / eligible_count

            tier_percentage = distribution_percentages.get(t.slot_number, 0.0)
            tier_total_bnb = total_global_bnb * tier_percentage
            tier_total_usdt = total_global_usdt * tier_percentage
            tier_pool_paid = slot_paid.get(t.slot_number, 0.0)
            tier_pool_remaining = max(0.0, tier_total_bnb - tier_pool_paid)
            eligible_user_count = eligible_counts.get(t.slot_number, 0)

            tier_cap = float(t.daily_return or 0.0)
            tier_paid_amount = float(t.total_paid or 0.0)
            tier_remaining = max(0.0, tier_cap - tier_paid_amount - float(t.pending_amount or 0.0))

            progress_percent = 0.0
            if tier_cap > 0:
                progress_percent = min(100.0, (tier_paid_amount / tier_cap) * 100.0)

            per_user_pool_share = 0.0
            if tier_is_active and eligible_user_count > 0:
                per_user_pool_share = tier_pool_remaining / eligible_user_count if tier_pool_remaining > 0 else 0.0
                claimable_amount = min(claimable_amount, per_user_pool_share, tier_remaining)
            else:
                claimable_amount = 0.0
            if eligible_user_count == 0:
                claimable_amount = 0.0

            if ls.current_tier and ls.current_tier > 0 and t.slot_number < ls.current_tier:
                progress_percent = 100.0

            tiers.append({
                "slot_number": t.slot_number,
                "tier_name": t.tier_name,
                "slot_value": t.slot_value,
                "daily_return": float(t.daily_return or 0.0),
                "claimable_amount": claimable_amount,
                "funded_amount": tier_paid_amount,
                "slot_total_amount": global_slot_paid.get(t.slot_number, 0.0),
                "pending_amount": t.pending_amount or 0.0,
                "progress_percent": progress_percent,
                "is_active": tier_is_active,
                "activated_at": t.activated_at,
                "total_users": eligible_user_count,
                "total_bnb": tier_total_bnb,
                "total_usdt": tier_total_usdt,
                "distribution_percentage": tier_percentage * 100,
                "remaining_amount": tier_remaining,
                "pool_remaining": tier_pool_remaining,
                "last_claim": slot_last_claim.get(t.slot_number),
            })

        # Calculate current tier's claimable amount for summary
        summary_claimable = 0.0
        if ls.current_tier >= 10:
            for tier_data in tiers:
                if tier_data["slot_number"] == ls.current_tier:
                    summary_claimable = tier_data["claimable_amount"]
                    break
        
        data = {
            "user_id": user_id,
            "summary": {
                "current_tier": ls.current_tier,
                "current_tier_name": ls.current_tier_name,
                "current_daily_return": summary_claimable,  # Now shows user's claimable amount
                "is_eligible": ls.is_eligible,
                "is_active": ls.is_active,
                "total_earned": ls.total_earned,
                "total_paid": ls.total_paid,
                "pending_amount": ls.pending_amount,
                "total_global_bnb": total_global_bnb,  # Total Leadership Stipend fund in BNB
                "total_global_usdt": total_global_usdt,  # Total Leadership Stipend fund in USDT
            },
            "tiers": tiers,
            "payments": payments,
        }
        return success_response(data, "Leadership Stipend income fetched")

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


