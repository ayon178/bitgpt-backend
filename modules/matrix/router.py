from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional
from bson import ObjectId

from auth.service import authentication_service
from ..user.model import User
from .service import MatrixService
from utils.response import success_response, error_response

router = APIRouter(prefix="/matrix", tags=["Matrix Program"])

class MatrixJoinRequest(BaseModel):
    user_id: str
    referrer_id: str
    tx_hash: str
    amount: float

class MatrixJoinResponse(BaseModel):
    success: bool
    matrix_tree_id: Optional[str] = None
    activation_id: Optional[str] = None
    slot_activated: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None

@router.post("/join", response_model=MatrixJoinResponse)
async def join_matrix(
    request: MatrixJoinRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """
    Join Matrix program with $11 USDT and trigger all auto calculations
    
    This endpoint implements Section 1.1 Joining Requirements from MATRIX_TODO.md:
    - Cost: $11 USDT to join Matrix program
    - Structure: 3x Matrix structure (3, 9, 27 members per level)
    - Slots: 15 slots total (STARTER to STAR)
    - Recycle System: Each slot completes with 39 members (3+9+27)
    
    Auto calculations triggered:
    - MatrixTree Creation
    - Slot-1 Activation (STARTER)
    - Tree Placement in referrer's matrix
    - All commission distributions (100% total)
    - Special program integrations
    """
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate referrer exists
        referrer = User.objects(id=ObjectId(request.referrer_id)).first()
        if not referrer:
            raise HTTPException(status_code=404, detail="Referrer not found")
        
        # Convert amount to Decimal
        amount = Decimal(str(request.amount))
        
        # Initialize service
        matrix_service = MatrixService()
        
        # Process Matrix join
        result = matrix_service.join_matrix(
            user_id=request.user_id,
            referrer_id=request.referrer_id,
            tx_hash=request.tx_hash,
            amount=amount
        )
        
        if result["success"]:
            return MatrixJoinResponse(
                success=True,
                matrix_tree_id=result["matrix_tree_id"],
                activation_id=result["activation_id"],
                slot_activated=result["slot_activated"],
                amount=result["amount"],
                currency=result["currency"],
                message=result["message"]
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))

@router.get("/status/{user_id}")
async def get_matrix_status(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get user's matrix program status"""
    try:
        matrix_service = MatrixService()
        result = matrix_service.get_matrix_status(user_id)
        
        if result["success"]:
            return success_response(result)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))

@router.get("/slots")
async def get_matrix_slots(
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get all matrix slot information"""
    try:
        matrix_service = MatrixService()
        slots = []
        
        for slot_no, slot_info in matrix_service.MATRIX_SLOTS.items():
            slots.append({
                "slot_no": slot_no,
                "slot_name": slot_info['name'],
                "slot_value": float(slot_info['value']),
                "level": slot_info['level'],
                "members": slot_info['members'],
                "currency": "USDT"
            })
        
        return success_response({
            "slots": slots,
            "total_slots": len(slots)
        })
        
    except Exception as e:
        return error_response(str(e))

@router.get("/tree/{user_id}")
async def get_matrix_tree(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get user's matrix tree structure"""
    try:
        from .model import MatrixTree
        
        matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
        if not matrix_tree:
            raise HTTPException(status_code=404, detail="User not in Matrix program")
        
        # Convert nodes to serializable format
        nodes = []
        for node in matrix_tree.nodes:
            nodes.append({
                "level": node.level,
                "position": node.position,
                "user_id": str(node.user_id),
                "placed_at": node.placed_at.isoformat(),
                "is_active": node.is_active
            })
        
        # Convert slots to serializable format
        slots = []
        for slot in matrix_tree.slots:
            slots.append({
                "slot_no": slot.slot_no,
                "slot_name": slot.slot_name,
                "slot_value": float(slot.slot_value),
                "level": slot.level,
                "members_count": slot.members_count,
                "is_active": slot.is_active,
                "activated_at": slot.activated_at.isoformat() if slot.activated_at else None,
                "total_income": float(slot.total_income),
                "upgrade_cost": float(slot.upgrade_cost),
                "wallet_amount": float(slot.wallet_amount)
            })
        
        return success_response({
            "user_id": user_id,
            "current_slot": matrix_tree.current_slot,
            "current_level": matrix_tree.current_level,
            "total_members": matrix_tree.total_members,
            "level_1_members": matrix_tree.level_1_members,
            "level_2_members": matrix_tree.level_2_members,
            "level_3_members": matrix_tree.level_3_members,
            "is_complete": matrix_tree.is_complete,
            "nodes": nodes,
            "slots": slots,
            "created_at": matrix_tree.created_at.isoformat(),
            "updated_at": matrix_tree.updated_at.isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))

@router.get("/auto-upgrade-status/{user_id}")
async def get_matrix_auto_upgrade_status(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get user's matrix auto upgrade status"""
    try:
        from ..auto_upgrade.model import MatrixAutoUpgrade
        
        auto_upgrade = MatrixAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
        if not auto_upgrade:
            raise HTTPException(status_code=404, detail="User not in Matrix auto upgrade system")
        
        return success_response({
            "user_id": user_id,
            "current_slot_no": auto_upgrade.current_slot_no,
            "current_level": auto_upgrade.current_level,
            "middle_three_required": auto_upgrade.middle_three_required,
            "middle_three_available": auto_upgrade.middle_three_available,
            "is_eligible": auto_upgrade.is_eligible,
            "next_upgrade_cost": float(auto_upgrade.next_upgrade_cost),
            "can_upgrade": auto_upgrade.can_upgrade,
            "last_updated": auto_upgrade.last_updated.isoformat() if auto_upgrade.last_updated else None
        })
        
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))

# ==================== RECYCLE SYSTEM API ENDPOINTS ====================

@router.get("/recycle-tree")
async def get_recycle_tree_endpoint(
    user_id: str,
    slot: int,
    recycle_no: Optional[int] = None,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get matrix tree by recycle number or current in-progress tree."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's tree")
        
        if slot < 1 or slot > 15:
            raise HTTPException(status_code=400, detail="Slot number must be between 1 and 15")
        
        service = MatrixService()
        tree_data = service.get_recycle_tree(user_id, slot, recycle_no)
        
        if tree_data:
            return success_response(tree_data, "Recycle tree fetched successfully")
        return error_response("Recycle tree not found", status_code=404)
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/recycles")
async def get_recycle_history_endpoint(
    user_id: str,
    slot: int,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get recycle history for user+slot."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's recycle history")
        
        if slot < 1 or slot > 15:
            raise HTTPException(status_code=400, detail="Slot number must be between 1 and 15")
        
        service = MatrixService()
        recycle_history = service.get_recycle_history(user_id, slot)
        
        return success_response(recycle_history, "Recycle history fetched successfully")
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.post("/process-recycle")
async def process_recycle_completion_endpoint(
    user_id: str,
    slot_no: int,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Process recycle completion: detect, snapshot, re-entry."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to process recycle for this user")
        
        if slot_no < 1 or slot_no > 15:
            raise HTTPException(status_code=400, detail="Slot number must be between 1 and 15")
        
        service = MatrixService()
        result = service.process_recycle_completion(user_id, slot_no)
        
        if result.get("success"):
            return success_response(result, "Recycle completion processed successfully")
        return error_response(result.get("error", "Failed to process recycle completion"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

# ==================== AUTO UPGRADE SYSTEM API ENDPOINTS ====================

@router.get("/middle-three-earnings/{user_id}")
async def get_middle_three_earnings_endpoint(
    user_id: str,
    slot_no: int,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get middle 3 earnings calculation for auto upgrade."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's earnings")
        
        if slot_no < 1 or slot_no > 15:
            raise HTTPException(status_code=400, detail="Slot number must be between 1 and 15")
        
        service = MatrixService()
        earnings_result = service.calculate_middle_three_earnings(user_id, slot_no)
        
        if earnings_result.get("success"):
            return success_response(earnings_result, "Middle three earnings calculated successfully")
        return error_response(earnings_result.get("error", "Failed to calculate middle three earnings"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.post("/trigger-auto-upgrade")
async def trigger_automatic_upgrade_endpoint(
    user_id: str,
    slot_no: int,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Trigger automatic upgrade using middle 3 earnings."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to trigger upgrade for this user")
        
        if slot_no < 1 or slot_no > 15:
            raise HTTPException(status_code=400, detail="Slot number must be between 1 and 15")
        
        service = MatrixService()
        result = service.process_automatic_upgrade(user_id, slot_no)
        
        if result.get("success"):
            return success_response(result, "Automatic upgrade processed successfully")
        return error_response(result.get("error", "Failed to process automatic upgrade"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/auto-upgrade-status/{user_id}")
async def get_auto_upgrade_status_endpoint(
    user_id: str,
    slot_no: int,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive auto upgrade status for a user."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's auto upgrade status")
        
        if slot_no < 1 or slot_no > 15:
            raise HTTPException(status_code=400, detail="Slot number must be between 1 and 15")
        
        service = MatrixService()
        
        # Get middle three members
        middle_three_result = service.detect_middle_three_members(user_id, slot_no)
        
        # Get earnings calculation
        earnings_result = service.calculate_middle_three_earnings(user_id, slot_no)
        
        # Get matrix auto upgrade status
        matrix_auto_upgrade = MatrixAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
        
        status = {
            "user_id": user_id,
            "current_slot": slot_no,
            "middle_three_detection": middle_three_result,
            "earnings_calculation": earnings_result,
            "auto_upgrade_status": {
                "current_slot_no": matrix_auto_upgrade.current_slot_no if matrix_auto_upgrade else slot_no,
                "current_level": matrix_auto_upgrade.current_level if matrix_auto_upgrade else 1,
                "middle_three_available": matrix_auto_upgrade.middle_three_available if matrix_auto_upgrade else 0,
                "is_eligible": matrix_auto_upgrade.is_eligible if matrix_auto_upgrade else False,
                "can_upgrade": matrix_auto_upgrade.can_upgrade if matrix_auto_upgrade else False,
                "next_upgrade_cost": float(matrix_auto_upgrade.next_upgrade_cost) if matrix_auto_upgrade else 0
            } if matrix_auto_upgrade else None
        }
        
        return success_response(status, "Auto upgrade status fetched successfully")
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))