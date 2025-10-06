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
    """Background task to handle tree placement for both auto-activated Binary slots"""
    try:
        # Create tree placement for Slot 1 (Explorer)
        _run_async(TreeService.create_tree_placement(
            user_id=user_id,
            referrer_id=referrer_id,
            program='binary',
            slot_no=1
        ))
    except Exception:
        pass
    
    try:
        # Create tree placement for Slot 2 (Contributor)
        _run_async(TreeService.create_tree_placement(
            user_id=user_id,
            referrer_id=referrer_id,
            program='binary',
            slot_no=2
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


# Tree Upline Reserve System Endpoints

@user_router.get("/reserve-status/{user_id}")
async def get_reserve_status(
    user_id: str,
    program: str = "binary",
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get tree upline reserve status for a user"""
    try:
        from .tree_reserve_service import TreeUplineReserveService
        
        reserve_service = TreeUplineReserveService()
        status = reserve_service.get_reserve_status(user_id, program)
        
        if "error" in status:
            return error_response(status["error"])
        
        return success_response(status, "Reserve status retrieved successfully")
        
    except Exception as e:
        return error_response(str(e))


@user_router.post("/reserve/manual-add")
async def manually_add_to_reserve(
    payload: dict,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Manually add funds to a user's reserve"""
    try:
        from .tree_reserve_service import TreeUplineReserveService
        
        user_id = payload.get("user_id")
        program = payload.get("program", "binary")
        slot_no = payload.get("slot_no")
        amount = payload.get("amount")
        tx_hash = payload.get("tx_hash", f"MANUAL-{datetime.now().timestamp()}")
        
        if not all([user_id, slot_no, amount]):
            return error_response("Missing required fields: user_id, slot_no, amount")
        
        reserve_service = TreeUplineReserveService()
        success, message = reserve_service.add_to_reserve_fund(
            user_id, program, slot_no, Decimal(str(amount)), user_id, tx_hash
        )
        
        if success:
            return success_response({"message": message}, "Funds added to reserve successfully")
        else:
            return error_response(message)
            
    except Exception as e:
        return error_response(str(e))


@user_router.post("/reserve/auto-activate/{user_id}")
async def trigger_auto_activation(
    user_id: str,
    payload: dict,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Manually trigger auto-activation check for a user's reserve funds"""
    try:
        from .tree_reserve_service import TreeUplineReserveService
        
        program = payload.get("program", "binary")
        slot_no = payload.get("slot_no")
        
        reserve_service = TreeUplineReserveService()
        
        if slot_no:
            # Check specific slot
            reserve_balance = reserve_service.get_reserve_balance(user_id, program, slot_no)
            next_slot_cost = reserve_service._get_next_slot_cost(program, slot_no)
            
            if next_slot_cost and reserve_balance >= next_slot_cost:
                success = reserve_service._auto_activate_slot(
                    user_id, program, slot_no + 1, next_slot_cost, reserve_balance
                )
                
                if success:
                    return success_response(
                        {"message": f"Auto-activated slot {slot_no + 1}"}, 
                        "Auto-activation successful"
                    )
                else:
                    return error_response("Auto-activation failed")
            else:
                return success_response(
                    {"message": "Insufficient reserve funds for auto-activation"},
                    "Check completed"
                )
        else:
            # Check all slots
            status = reserve_service.get_reserve_status(user_id, program)
            activated_slots = []
            
            for slot in status.get("slots", []):
                if slot.get("can_auto_activate", False):
                    success = reserve_service._auto_activate_slot(
                        user_id, program, slot["slot_no"] + 1, 
                        Decimal(str(slot["next_slot_cost"])), 
                        Decimal(str(slot["reserve_balance"]))
                    )
                    if success:
                        activated_slots.append(slot["slot_no"] + 1)
            
            return success_response(
                {"activated_slots": activated_slots}, 
                f"Auto-activation check completed. Activated {len(activated_slots)} slots."
            )
            
    except Exception as e:
        return error_response(str(e))


@user_router.get("/reserve/ledger/{user_id}")
async def get_reserve_ledger(
    user_id: str,
    program: str = "binary",
    limit: int = 50,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get reserve fund transaction ledger for a user"""
    try:
        from ..wallet.model import ReserveLedger
        
        ledger_entries = ReserveLedger.objects(
            user_id=ObjectId(user_id),
            program=program
        ).order_by('-created_at').limit(limit)
        
        entries = []
        for entry in ledger_entries:
            entries.append({
                "id": str(entry.id),
                "slot_no": entry.slot_no,
                "amount": float(entry.amount),
                "direction": entry.direction,
                "source": entry.source,
                "balance_after": float(entry.balance_after),
                "tx_hash": entry.tx_hash,
                "created_at": entry.created_at
            })
        
        return success_response({
            "user_id": user_id,
            "program": program,
            "entries": entries,
            "total_entries": len(entries)
        }, "Reserve ledger retrieved successfully")
        
    except Exception as e:
        return error_response(str(e))


@user_router.get("/income/leadership-stipend")
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
        from bson import ObjectId
        from datetime import datetime
        from decimal import Decimal

        ls = LeadershipStipend.objects(user_id=ObjectId(user_id)).first()
        # Preload payments first and compute per-slot totals
        from modules.leadership_stipend.model import LeadershipStipendPayment as _LSP
        pay_q = {"user_id": ObjectId(user_id)}
        if slot:
            pay_q["slot_number"] = int(slot)
        payments_cursor = _LSP.objects(__raw__=pay_q).order_by('-payment_date')
        payments = []
        slot_paid: dict[int, float] = {}
        for p in payments_cursor:
            if currency.upper() != (p.currency or "BNB").upper():
                continue
            amt = float(p.daily_return_amount or 0.0)
            slot_paid[p.slot_number] = slot_paid.get(p.slot_number, 0.0) + amt
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

        if not ls:
            # If user not in stipend yet, still return payments summary
            total_paid = sum(slot_paid.values())
            return success_response({
                "user_id": user_id,
                "currency": currency.upper(),
                "tiers": [],
                "payments": payments,
                "summary": {"total_paid": round(total_paid, 8), "total_target": 0.0, "pending": 0.0, "overall_progress_percent": 0.0}
            }, "Leadership Stipend income (from payments only)")

        # Slot wise breakdown for slots 10..16
        tiers = []
        slot_min, slot_max = 10, 16
        # Load real activations for eligibility/activation timestamp
        try:
            from modules.slot.model import SlotActivation as _SA
            from bson import ObjectId as _OID
            activations_cur = _SA.objects(user_id=_OID(user_id), program='binary', status='completed').only('slot_no','activated_at','completed_at').all()
            slot_to_latest_activation = {}
            for a in activations_cur:
                when = getattr(a, 'activated_at', None) or getattr(a, 'completed_at', None)
                if when:
                    prev = slot_to_latest_activation.get(a.slot_no)
                    if not prev or when > prev:
                        slot_to_latest_activation[a.slot_no] = when
        except Exception:
            slot_to_latest_activation = {}
        for t in (ls.tiers or []):
            if t.slot_number < slot_min or t.slot_number > slot_max:
                continue
            if currency.upper() != (t.currency or "BNB").upper():
                continue
            if slot and t.slot_number != slot:
                continue
            # Progress: paid / daily_return (target) capped at 100
            target = float(t.daily_return or 0.0)
            paid = float(slot_paid.get(t.slot_number, 0.0))
            progress = 0.0
            if target > 0:
                progress = min(100.0, round((paid / target) * 100.0, 2))
            # Eligibility: slot is considered eligible if user has completed activation for that slot (>=10)
            eligible = bool(slot_to_latest_activation.get(t.slot_number))
            act_ts = t.activated_at or slot_to_latest_activation.get(t.slot_number)
            tiers.append({
                "slot_number": t.slot_number,
                "tier_name": t.tier_name,
                "slot_value": float(t.slot_value or 0.0),
                "daily_return": target,
                "funded_amount": paid,
                "pending_amount": max(0.0, round(target - paid, 8)) if target > 0 else 0.0,
                "progress_percent": progress,
                "eligible": eligible,
                "is_active": eligible or bool(t.is_active),
                "activated_at": act_ts,
            })

        # Overall summary
        total_paid = sum(t.get("funded_amount", 0.0) for t in tiers)
        total_target = sum(t.get("daily_return", 0.0) for t in tiers)
        total_pending = max(0.0, total_target - total_paid)

        return success_response({
            "user_id": user_id,
            "currency": currency.upper(),
            "tiers": tiers,
            "payments": payments,
            "summary": {
                "total_paid": round(total_paid, 8),
                "total_target": round(total_target, 8),
                "pending": round(total_pending, 8),
                "overall_progress_percent": round((total_paid / total_target) * 100.0, 2) if total_target > 0 else 0.0
            }
        }, "Leadership Stipend income fetched successfully")

    except Exception as e:
        return error_response(str(e))

