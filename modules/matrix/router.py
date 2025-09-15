from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional
from bson import ObjectId

from auth.service import authentication_service
from ..user.model import User
from .service import MatrixService
from utils.response import success_response, error_response
from ..auto_upgrade.model import MatrixAutoUpgrade

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

@router.get("/tree-graph/{user_id}")
async def get_matrix_tree_graph(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Return Matrix tree in frontend graph-friendly structure."""
    try:
        from .model import MatrixTree
        from .model import MatrixRecycleInstance

        matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
        if not matrix_tree:
            raise HTTPException(status_code=404, detail="User not in Matrix program")

        # Helper to compute graph id from level/position according to frontend MatrixGraph
        def compute_graph_id(level: int, position: int) -> int | None:
            if level == 0:
                return 1
            if level == 1:
                # Level-1 three positions map to ids 2,3,4? Frontend expects 2 and 3 and then children 4,10,16 under 1
                # Based on MatrixGraph usage: ids used explicitly are 1,2,3 for top row
                return 2 + position  # 2,3,4
            if level == 2:
                # Under parent id p in {2,3,4}, children are p+3, p+9, p+15
                parent_l1_index = position // 3  # 0..2
                child_offset = position % 3      # 0..2
                parent_id = 2 + parent_l1_index  # 2,3,4
                return parent_id + (3 + 6 * child_offset)  # 4/10/16, 5/11/17, 6/12/18
            return None  # Deeper levels not displayed by current frontend graph

        # Build users array
        users = []
        for node in matrix_tree.nodes:
            gid = compute_graph_id(node.level, node.position)
            if gid is None:
                continue
            node_type = "self" if str(node.user_id) == user_id and node.level == 0 else "downLine"
            users.append({
                "id": gid,
                "type": node_type,
                "userId": str(node.user_id)
            })

        # Ensure root exists in users
        if not any(u.get("id") == 1 for u in users):
            users.append({"id": 1, "type": "self", "userId": user_id})

        # Meta fields for compatibility with mock data
        ms = MatrixService()
        current_slot = matrix_tree.current_slot or 1
        slot_info = ms.MATRIX_SLOTS.get(current_slot, {"value": 11})
        price = float(slot_info["value"]) if isinstance(slot_info["value"], (int, float)) else 11.0
        recycle_count = MatrixRecycleInstance.objects(user_id=ObjectId(user_id), slot_number=current_slot).count()

        payload = {
            "id": current_slot * 10 + 1,  # synthetic id similar to mocks
            "price": price,
            "userId": str(user_id),
            "recycle": recycle_count,
            "isCompleted": bool(matrix_tree.is_complete),
            "isProcess": False,
            "isAutoUpgrade": False,
            "isManualUpgrade": False,
            "processPercent": 0,
            "users": sorted(users, key=lambda x: x["id"])  # stable order
        }

        return success_response(payload, "Matrix tree graph data fetched successfully")
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
            "last_updated": (auto_upgrade.updated_at.isoformat() if getattr(auto_upgrade, 'updated_at', None) else (auto_upgrade.last_check_at.isoformat() if getattr(auto_upgrade, 'last_check_at', None) else None))
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

# ==================== DREAM MATRIX SYSTEM API ENDPOINTS ====================

@router.get("/dream-matrix-status/{user_id}")
async def get_dream_matrix_status_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive Dream Matrix status for a user."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's Dream Matrix status")
        
        service = MatrixService()
        result = service.get_dream_matrix_status(user_id)
        
        if result.get("success"):
            return success_response(result.get("status"), "Dream Matrix status fetched successfully")
        return error_response(result.get("error", "Failed to get Dream Matrix status"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/dream-matrix-earnings/{user_id}")
async def get_dream_matrix_earnings_endpoint(
    user_id: str,
    slot_no: int = 5,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Calculate Dream Matrix earnings based on 5th slot ($800 total value)."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's Dream Matrix earnings")
        
        if slot_no < 1 or slot_no > 15:
            raise HTTPException(status_code=400, detail="Slot number must be between 1 and 15")
        
        service = MatrixService()
        result = service.calculate_dream_matrix_earnings(user_id, slot_no)
        
        if result.get("success"):
            return success_response(result, "Dream Matrix earnings calculated successfully")
        return error_response(result.get("error", "Failed to calculate Dream Matrix earnings"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.post("/dream-matrix-distribute")
async def distribute_dream_matrix_endpoint(
    user_id: str,
    slot_no: int = 5,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Process Dream Matrix distribution when user meets requirements."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to process Dream Matrix distribution for this user")
        
        if slot_no < 1 or slot_no > 15:
            raise HTTPException(status_code=400, detail="Slot number must be between 1 and 15")
        
        service = MatrixService()
        result = service.process_dream_matrix_distribution(user_id, slot_no)
        
        if result.get("success"):
            return success_response(result, "Dream Matrix distribution processed successfully")
        return error_response(result.get("error", "Failed to process Dream Matrix distribution"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/dream-matrix-eligibility/{user_id}")
async def check_dream_matrix_eligibility_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Check if user meets Dream Matrix eligibility (3 direct partners)."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to check this user's Dream Matrix eligibility")
        
        service = MatrixService()
        result = service.check_dream_matrix_eligibility(user_id)
        
        if result.get("success"):
            return success_response(result, "Dream Matrix eligibility checked successfully")
        return error_response(result.get("error", "Failed to check Dream Matrix eligibility"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

# ==================== MENTORSHIP BONUS SYSTEM API ENDPOINTS ====================

@router.get("/mentorship-status/{user_id}")
async def get_mentorship_status_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive mentorship status for a user."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's mentorship status")
        
        service = MatrixService()
        result = service.get_mentorship_status(user_id)
        
        if result.get("success"):
            return success_response(result.get("status"), "Mentorship status fetched successfully")
        return error_response(result.get("error", "Failed to get mentorship status"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/mentorship-bonus/{super_upline_id}")
async def calculate_mentorship_bonus_endpoint(
    super_upline_id: str,
    direct_referral_id: str,
    amount: float,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Calculate 10% mentorship bonus for super upline."""
    try:
        if str(current_user["user_id"]) != super_upline_id:
            raise HTTPException(status_code=403, detail="Unauthorized to calculate mentorship bonus for this user")
        
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        service = MatrixService()
        result = service.calculate_mentorship_bonus(super_upline_id, direct_referral_id, amount)
        
        if result.get("success"):
            return success_response(result, "Mentorship bonus calculated successfully")
        return error_response(result.get("error", "Failed to calculate mentorship bonus"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.post("/mentorship-bonus-distribute")
async def distribute_mentorship_bonus_endpoint(
    super_upline_id: str,
    direct_referral_id: str,
    amount: float,
    activity_type: str = "joining",
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Process mentorship bonus distribution to super upline."""
    try:
        if str(current_user["user_id"]) != super_upline_id:
            raise HTTPException(status_code=403, detail="Unauthorized to process mentorship bonus for this user")
        
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")
        
        if activity_type not in ["joining", "upgrade"]:
            raise HTTPException(status_code=400, detail="Activity type must be 'joining' or 'upgrade'")
        
        service = MatrixService()
        result = service.process_mentorship_bonus(super_upline_id, direct_referral_id, amount, activity_type)
        
        if result.get("success"):
            return success_response(result, "Mentorship bonus distributed successfully")
        return error_response(result.get("error", "Failed to distribute mentorship bonus"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.post("/track-mentorship")
async def track_mentorship_relationship_endpoint(
    user_id: str,
    direct_referral_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Track mentorship relationships when a direct referral joins."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to track mentorship for this user")
        
        service = MatrixService()
        result = service.track_mentorship_relationships(user_id, direct_referral_id)
        
        if result.get("success"):
            return success_response(result, "Mentorship relationship tracked successfully")
        return error_response(result.get("error", "Failed to track mentorship relationship"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

# ==================== MATRIX UPGRADE SYSTEM API ENDPOINTS ====================

@router.post("/upgrade-slot")
async def upgrade_matrix_slot_endpoint(
    user_id: str,
    from_slot_no: int,
    to_slot_no: int,
    upgrade_type: str = "manual",
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Upgrade user from one Matrix slot to another."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to upgrade this user's Matrix slot")
        
        if from_slot_no < 1 or from_slot_no > 15:
            raise HTTPException(status_code=400, detail="From slot number must be between 1 and 15")
        
        if to_slot_no < 1 or to_slot_no > 15:
            raise HTTPException(status_code=400, detail="To slot number must be between 1 and 15")
        
        if upgrade_type not in ["manual", "auto"]:
            raise HTTPException(status_code=400, detail="Upgrade type must be 'manual' or 'auto'")
        
        service = MatrixService()
        result = service.upgrade_matrix_slot(user_id, from_slot_no, to_slot_no, upgrade_type)
        
        if result.get("success"):
            return success_response(result, "Matrix slot upgraded successfully")
        return error_response(result.get("error", "Failed to upgrade Matrix slot"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/upgrade-options/{user_id}")
async def get_upgrade_options_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get available upgrade options for a user."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's upgrade options")
        
        service = MatrixService()
        result = service.get_upgrade_options(user_id)
        
        if result.get("success"):
            return success_response(result, "Upgrade options fetched successfully")
        return error_response(result.get("error", "Failed to get upgrade options"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/upgrade-history/{user_id}")
async def get_upgrade_history_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get user's Matrix upgrade history."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's upgrade history")
        
        service = MatrixService()
        result = service.get_upgrade_history(user_id)
        
        if result.get("success"):
            return success_response(result, "Upgrade history fetched successfully")
        return error_response(result.get("error", "Failed to get upgrade history"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/upgrade-status/{user_id}")
async def get_matrix_upgrade_status_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive Matrix upgrade status for a user."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's upgrade status")
        
        service = MatrixService()
        result = service.get_matrix_upgrade_status(user_id)
        
        if result.get("success"):
            return success_response(result.get("status"), "Matrix upgrade status fetched successfully")
        return error_response(result.get("error", "Failed to get Matrix upgrade status"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

# ==================== RANK SYSTEM API ENDPOINTS ====================

@router.get("/rank-status/{user_id}")
async def get_user_rank_status_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive rank status for a user."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's rank status")
        
        service = MatrixService()
        result = service.get_user_rank_status(user_id)
        
        if result.get("success"):
            return success_response(result.get("status"), "Rank status fetched successfully")
        return error_response(result.get("error", "Failed to get rank status"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.post("/update-rank/{user_id}")
async def update_user_rank_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Update user rank based on Binary and Matrix slot activations."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to update this user's rank")
        
        service = MatrixService()
        result = service.update_user_rank_from_programs(user_id)
        
        if result.get("success"):
            return success_response(result, "Rank updated successfully")
        return error_response(result.get("error", "Failed to update rank"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/rank-system-info")
async def get_rank_system_info_endpoint(
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive rank system information."""
    try:
        rank_system_info = {
            "total_ranks": 15,
            "rank_names": ["Bitron", "Cryzen", "Neura", "Glint", "Stellar", 
                          "Ignis", "Quanta", "Lumix", "Arion", "Nexus",
                          "Fyre", "Axion", "Trion", "Spectra", "Omega"],
            "rank_descriptions": {
                "Bitron": "1 slot activated",
                "Cryzen": "2 slots activated", 
                "Neura": "3 slots activated",
                "Glint": "4 slots activated",
                "Stellar": "5 slots activated",
                "Ignis": "6 slots activated",
                "Quanta": "7 slots activated",
                "Lumix": "8 slots activated",
                "Arion": "9 slots activated",
                "Nexus": "10 slots activated",
                "Fyre": "11 slots activated",
                "Axion": "12 slots activated",
                "Trion": "13 slots activated",
                "Spectra": "14 slots activated",
                "Omega": "15 slots activated (Max Rank)"
            },
            "slot_sources": {
                "binary_program": "Binary slot activations",
                "matrix_program": "Matrix slot activations"
            },
            "calculation_method": "Total slots = Binary slots + Matrix slots",
            "max_slots": 15,
            "description": "Ranks are achieved by activating slots in Binary and Matrix programs. Each rank represents leadership and growth within the platform."
        }
        
        return success_response(rank_system_info, "Rank system information fetched successfully")
    except Exception as e:
        return error_response(str(e))

# ==================== GLOBAL PROGRAM INTEGRATION API ENDPOINTS ====================

@router.get("/global-program-status/{user_id}")
async def get_global_program_status_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive Global Program status for a user."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's Global Program status")
        
        service = MatrixService()
        result = service.get_global_program_status(user_id)
        
        if result.get("success"):
            return success_response(result.get("status"), "Global Program status fetched successfully")
        return error_response(result.get("error", "Failed to get Global Program status"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.post("/integrate-global-program/{user_id}")
async def integrate_global_program_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Integrate Matrix user with Global Program."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to integrate this user with Global Program")
        
        service = MatrixService()
        result = service.integrate_with_global_program(user_id)
        
        if result.get("success"):
            return success_response(result, "Global Program integration completed successfully")
        return error_response(result.get("error", "Failed to integrate with Global Program"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/global-distribution-info")
async def get_global_distribution_info_endpoint(
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive Global Distribution information."""
    try:
        global_distribution_info = {
            "distribution_percentages": {
                "level_distribution": {
                    "partner_incentive": "10%",
                    "reserved_upgrade": "30%",
                    "total_level": "40%"
                },
                "profit_distribution": {
                    "net_profit": "30%"
                },
                "special_bonuses": {
                    "royal_captain_bonus": "15%",
                    "president_reward": "15%",
                    "triple_entry_reward": "5%",
                    "shareholders": "5%"
                },
                "total_distributed": "100%"
            },
            "contribution_rate": "5% of Matrix slot value",
            "integration_points": {
                "matrix_join": "Automatic Global Program integration on Matrix join",
                "matrix_upgrade": "Automatic Global Program integration on Matrix upgrade"
            },
            "description": "Global Program integration with Matrix provides cross-program benefits and unified earning opportunities"
        }
        
        return success_response(global_distribution_info, "Global Distribution information fetched successfully")
    except Exception as e:
        return error_response(str(e))

# ==================== LEADERSHIP STIPEND INTEGRATION API ENDPOINTS ====================

@router.get("/leadership-stipend-status/{user_id}")
async def get_leadership_stipend_status_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive Leadership Stipend status for a user."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's Leadership Stipend status")
        
        service = MatrixService()
        result = service.get_leadership_stipend_status(user_id)
        
        if result.get("success"):
            return success_response(result.get("status"), "Leadership Stipend status fetched successfully")
        return error_response(result.get("error", "Failed to get Leadership Stipend status"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.post("/integrate-leadership-stipend/{user_id}")
async def integrate_leadership_stipend_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Integrate Matrix user with Leadership Stipend program."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to integrate this user with Leadership Stipend")
        
        service = MatrixService()
        result = service.integrate_with_leadership_stipend(user_id)
        
        if result.get("success"):
            return success_response(result, "Leadership Stipend integration completed successfully")
        return error_response(result.get("error", "Failed to integrate with Leadership Stipend"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/leadership-stipend-info")
async def get_leadership_stipend_info_endpoint(
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive Leadership Stipend information."""
    try:
        leadership_stipend_info = {
            "eligibility": "Matrix slots 10-16 only",
            "slot_values": {
                "slot_10": "1.1264 BNB (LEADER)",
                "slot_11": "2.2528 BNB (VANGURD)",
                "slot_12": "4.5056 BNB (CENTER)",
                "slot_13": "9.0112 BNB (CLIMAX)",
                "slot_14": "18.0224 BNB (ENTERNITY)",
                "slot_15": "36.0448 BNB (KING)",
                "slot_16": "72.0896 BNB (COMMENDER)"
            },
            "daily_return_rate": "Double the slot value as daily return",
            "distribution_percentages": {
                "level_10": "1.5%",
                "level_11": "1.0%",
                "level_12": "0.5%",
                "level_13": "0.5%",
                "level_14": "0.5%",
                "level_15": "0.5%",
                "level_16": "0.5%"
            },
            "integration_points": {
                "matrix_upgrade": "Automatic Leadership Stipend integration on Matrix upgrade to slots 10-16"
            },
            "description": "Leadership Stipend provides daily returns for Matrix slots 10-16. Users receive double the slot value as daily return with specific distribution percentages."
        }
        
        return success_response(leadership_stipend_info, "Leadership Stipend information fetched successfully")
    except Exception as e:
        return error_response(str(e))

# ==================== JACKPOT PROGRAM INTEGRATION API ENDPOINTS ====================

@router.get("/jackpot-program-status/{user_id}")
async def get_jackpot_program_status_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive Jackpot Program status for a user."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's Jackpot Program status")
        
        service = MatrixService()
        result = service.get_jackpot_program_status(user_id)
        
        if result.get("success"):
            return success_response(result.get("status"), "Jackpot Program status fetched successfully")
        return error_response(result.get("error", "Failed to get Jackpot Program status"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.post("/integrate-jackpot-program/{user_id}")
async def integrate_jackpot_program_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Integrate Matrix user with Jackpot Program."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to integrate this user with Jackpot Program")
        
        service = MatrixService()
        result = service.integrate_with_jackpot_program(user_id)
        
        if result.get("success"):
            return success_response(result, "Jackpot Program integration completed successfully")
        return error_response(result.get("error", "Failed to integrate with Jackpot Program"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/jackpot-program-info")
async def get_jackpot_program_info_endpoint(
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive Jackpot Program information."""
    try:
        jackpot_program_info = {
            "eligibility": "All Matrix slots",
            "contribution_rate": "2% of Matrix slot value",
            "fund_structure": {
                "open_pool": "50%",
                "top_direct_promoters": "30%",
                "top_buyers": "10%",
                "binary_contribution": "5%"
            },
            "free_coupons": {
                "slot_5": "1 FREE COUPON",
                "slot_6": "2 FREE COUPON",
                "slot_7": "3 FREE COUPON",
                "slot_8": "4 FREE COUPON",
                "slot_9": "5 FREE COUPON",
                "slot_10": "6 FREE COUPON",
                "slot_11": "7 FREE COUPON",
                "slot_12": "8 FREE COUPON",
                "slot_13": "9 FREE COUPON",
                "slot_14": "10 FREE COUPON",
                "slot_15": "11 FREE COUPON",
                "slot_16": "12 FREE COUPON"
            },
            "integration_points": {
                "matrix_join": "Automatic Jackpot Program integration on Matrix join",
                "matrix_upgrade": "Automatic Jackpot Program integration on Matrix upgrade"
            },
            "description": "Jackpot Program provides free coupons for Binary slot upgrades. Users contribute 2% of Matrix slot value to Jackpot fund with specific distribution percentages."
        }
        
        return success_response(jackpot_program_info, "Jackpot Program information fetched successfully")
    except Exception as e:
        return error_response(str(e))

# ==================== NEWCOMER GROWTH SUPPORT (NGS) INTEGRATION API ENDPOINTS ====================

@router.get("/ngs-status/{user_id}")
async def get_ngs_status_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive NGS status for a user."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's NGS status")
        
        service = MatrixService()
        result = service.get_ngs_status(user_id)
        
        if result.get("success"):
            return success_response(result.get("status"), "NGS status fetched successfully")
        return error_response(result.get("error", "Failed to get NGS status"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.post("/integrate-ngs/{user_id}")
async def integrate_ngs_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Integrate Matrix user with NGS."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to integrate this user with NGS")
        
        service = MatrixService()
        result = service.integrate_with_newcomer_growth_support(user_id)
        
        if result.get("success"):
            return success_response(result, "NGS integration completed successfully")
        return error_response(result.get("error", "Failed to integrate with NGS"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/ngs-info")
async def get_ngs_info_endpoint(
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive NGS information."""
    try:
        ngs_info = {
            "eligibility": "All Matrix slots",
            "benefit_structure": {
                "instant_bonus": "5% of Matrix slot value - Can be cashed out instantly",
                "extra_earning": "3% of Matrix slot value - Monthly opportunities based on upline activity",
                "upline_rank_bonus": "2% of Matrix slot value - 10% bonus when achieving same rank as upline"
            },
            "total_benefits": "10% of Matrix slot value",
            "benefit_types": {
                "instant_reward": "Immediate cash-out bonus",
                "extra_income": "Monthly earning opportunities",
                "long_term_support": "Upline rank bonus system"
            },
            "integration_points": {
                "matrix_join": "Automatic NGS integration on Matrix join",
                "matrix_upgrade": "Automatic NGS integration on Matrix upgrade"
            },
            "description": "Newcomer Growth Support provides instant bonuses, extra earning opportunities, and upline rank bonuses for Matrix joiners. All benefits are designed to boost non-working income for new members."
        }
        
        return success_response(ngs_info, "NGS information fetched successfully")
    except Exception as e:
        return error_response(str(e))

# ==================== MENTORSHIP BONUS INTEGRATION API ENDPOINTS ====================

@router.get("/mentorship-bonus-status/{user_id}")
async def get_mentorship_bonus_status_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive Mentorship Bonus status for a user."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's Mentorship Bonus status")
        
        service = MatrixService()
        result = service.get_mentorship_bonus_status(user_id)
        
        if result.get("success"):
            return success_response(result.get("status"), "Mentorship Bonus status fetched successfully")
        return error_response(result.get("error", "Failed to get Mentorship Bonus status"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.post("/integrate-mentorship-bonus/{user_id}")
async def integrate_mentorship_bonus_endpoint(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Integrate Matrix user with Mentorship Bonus."""
    try:
        if str(current_user["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to integrate this user with Mentorship Bonus")
        
        service = MatrixService()
        result = service.integrate_with_mentorship_bonus(user_id)
        
        if result.get("success"):
            return success_response(result, "Mentorship Bonus integration completed successfully")
        return error_response(result.get("error", "Failed to integrate with Mentorship Bonus"))
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(str(e))

@router.get("/mentorship-bonus-info")
async def get_mentorship_bonus_info_endpoint(
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive Mentorship Bonus information."""
    try:
        mentorship_bonus_info = {
            "eligibility": "All Matrix slots",
            "benefit_structure": {
                "direct_of_direct_commission": "10% of Matrix slot value - Commission from direct-of-direct partners' joining fees and slot upgrades"
            },
            "total_benefits": "10% of Matrix slot value",
            "program_type": "Direct-of-Direct income program",
            "commission_rate": "10%",
            "example": {
                "scenario": "A invites B, B invites C, D, E",
                "result": "A gets 10% commission from C, D, E's joining fees and slot upgrades"
            },
            "integration_points": {
                "matrix_join": "Automatic Mentorship Bonus integration on Matrix join",
                "matrix_upgrade": "Automatic Mentorship Bonus integration on Matrix upgrade"
            },
            "description": "Mentorship Bonus is a Direct-of-Direct income program within the Matrix program. The Super Upline receives 10% commission from their direct referrals' direct referrals' joining fees and slot upgrades."
        }
        
        return success_response(mentorship_bonus_info, "Mentorship Bonus information fetched successfully")
    except Exception as e:
        return error_response(str(e))