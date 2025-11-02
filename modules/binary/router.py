from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional
from bson import ObjectId

from auth.service import authentication_service
from ..user.model import User
from .service import BinaryService
from utils.response import success_response, error_response

router = APIRouter(prefix="/binary", tags=["Binary Program"])

class BinaryUpgradeRequest(BaseModel):
    user_id: str
    slot_no: int
    tx_hash: str
    amount: float

class BinaryUpgradeResponse(BaseModel):
    success: bool
    activation_id: Optional[str] = None
    new_slot: Optional[str] = None
    slot_no: Optional[int] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None

@router.post("/upgrade", response_model=BinaryUpgradeResponse)
async def upgrade_binary_slot(
    request: BinaryUpgradeRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """
    Upgrade Binary slot with all auto calculations and distributions
    
    This endpoint ensures all the following happen automatically:
    1. Slot activation record creation
    2. Upgrade commission calculation (30% to corresponding level upline)
    3. Dual tree earning distribution (70% across levels 1-16)
    4. User rank update
    5. Jackpot free coupon awards (slots 5-16)
    6. Leadership stipend eligibility check (slots 10-16)
    7. Spark bonus fund contribution
    8. Auto-upgrade status update
    9. Earning history recording
    10. Blockchain event logging
    """
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate slot upgrade
        if request.slot_no < 3 or request.slot_no > 16:
            raise HTTPException(status_code=400, detail="Invalid slot number. Must be between 3-16")
        
        # Convert amount to Decimal
        amount = Decimal(str(request.amount))
        
        # Initialize service
        binary_service = BinaryService()
        
        # Process upgrade
        result = binary_service.upgrade_binary_slot(
            user_id=request.user_id,
            slot_no=request.slot_no,
            tx_hash=request.tx_hash,
            amount=amount
        )
        
        if result["success"]:
            return BinaryUpgradeResponse(
                success=True,
                activation_id=result["activation_id"],
                new_slot=result["new_slot"],
                slot_no=result["slot_no"],
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

class ManualUpgradeRequest(BaseModel):
    user_id: str
    slot_no: int
    tx_hash: Optional[str] = None

@router.post("/manual-upgrade", response_model=BinaryUpgradeResponse)
async def manual_upgrade_binary_slot(
    request: ManualUpgradeRequest,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """
    Manual binary slot upgrade using reserve + wallet payment
    
    Flow:
    1. Uses reserve funds first (if available)
    2. Deducts remaining from wallet
    3. Routes slot cost following cascade rules
    4. Checks Nth upline has slot N active before routing
    """
    try:
        from ..auto_upgrade.service import AutoUpgradeService
        
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate slot upgrade
        if request.slot_no < 1 or request.slot_no > 17:
            raise HTTPException(status_code=400, detail="Invalid slot number. Must be between 1-17")
        
        # Check authorization
        if str(current_user.get("user_id")) != request.user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to upgrade this user's slot")
        
        # Initialize service
        auto_upgrade_service = AutoUpgradeService()
        
        # Process manual upgrade
        result = auto_upgrade_service.manual_upgrade_binary_slot(
            user_id=request.user_id,
            slot_no=request.slot_no,
            tx_hash=request.tx_hash
        )
        
        if result["success"]:
            return BinaryUpgradeResponse(
                success=True,
                activation_id=result.get("activation_id"),
                new_slot=result.get("slot_name"),
                slot_no=result.get("slot_no"),
                amount=result.get("amount_paid"),
                currency="BNB",
                message=result.get("message")
            )
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Manual upgrade failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))

@router.get("/upgrade-status/{user_id}")
async def get_binary_upgrade_status(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get user's binary upgrade status and next available slots"""
    try:
        binary_service = BinaryService()
        result = binary_service.get_binary_upgrade_status(user_id)
        
        if result["success"]:
            return success_response(result)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/slot-catalog")
async def get_binary_slot_catalog(
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get all binary slot catalog information"""
    try:
        from ..slot.model import SlotCatalog
        
        catalogs = SlotCatalog.objects(program='binary', is_active=True).order_by('slot_no')
        
        slots = []
        for catalog in catalogs:
            slots.append({
                "slot_no": catalog.slot_no,
                "slot_name": catalog.name,
                "slot_value": float(catalog.price or Decimal('0')),
                "currency": "BNB",
                "level": catalog.level,
                "description": catalog.description
            })
        
        return success_response({
            "slots": slots,
            "total_slots": len(slots)
        })
        
    except Exception as e:
        return error_response(str(e))

@router.get("/dashboard/{user_id}")
async def get_binary_dashboard(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get comprehensive binary dashboard data for a user"""
    try:
        binary_service = BinaryService()
        result = binary_service.get_binary_dashboard_data(user_id)
        
        if result["success"]:
            return success_response(result["data"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))

@router.get("/earnings/{user_id}")
async def get_binary_earnings(
    user_id: str,
    page: int = 1,
    limit: int = 10,
    currency: str = "BNB",
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get binary earnings with pagination and currency filtering - following frontend data structure"""
    try:
        binary_service = BinaryService()
        result = binary_service.get_binary_earnings_frontend_format(user_id, page, limit, currency)
        
        if result["success"]:
            return success_response(result["data"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))

@router.get("/tree-structure/{user_id}")
async def get_binary_tree_structure(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get binary tree structure data for dashboard panels"""
    try:
        binary_service = BinaryService()
        result = binary_service.get_binary_tree_structure(user_id)
        
        if result["success"]:
            return success_response(result["data"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))

@router.get("/panel-data/{user_id}")
async def get_binary_panel_data(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get individual panel data for each binary slot/level"""
    try:
        binary_service = BinaryService()
        result = binary_service.get_binary_panel_data(user_id)
        
        if result["success"]:
            return success_response(result["data"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))

@router.get("/partner-incentive/{user_id}")
async def get_binary_partner_incentive(
    user_id: str,
    page: int = 1,
    limit: int = 10,
    currency: str = "BNB",
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get binary partner incentive earnings with pagination"""
    try:
        binary_service = BinaryService()
        result = binary_service.get_binary_partner_incentive(user_id, page, limit, currency)
        
        if result["success"]:
            return success_response(result["data"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))

@router.get("/duel-tree-earnings/{uid}")
async def get_duel_tree_earnings(
    uid: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get duel tree earnings data matching frontend matrixData.js structure"""
    try:
        # Find user by uid
        user = User.objects(uid=uid).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user.id)
        
        # Extract user ID from current_user with fallback options
        authenticated_user_id = None
        user_id_keys = ["user_id", "_id", "id", "uid"]

        for key in user_id_keys:
            if current_user and current_user.get(key):
                authenticated_user_id = str(current_user[key])
                break

        # Authorization check - users can only access their own data
        if authenticated_user_id and authenticated_user_id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's duel tree earnings")

        binary_service = BinaryService()
        result = binary_service.get_duel_tree_earnings(user_id)

        if result["success"]:
            return success_response(result["data"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/dual-tree-earnings/slot/{slot_no}")
async def calculate_dual_tree_earnings(
    slot_no: int,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Calculate dual tree earnings distribution for a specific slot"""
    try:
        if slot_no < 1 or slot_no > 16:
            raise HTTPException(status_code=400, detail="Invalid slot number. Must be between 1-16")
        
        binary_service = BinaryService()
        
        # Get slot value from catalog
        from ..slot.model import SlotCatalog
        catalog = SlotCatalog.objects(program='binary', slot_no=slot_no, is_active=True).first()
        if not catalog:
            raise HTTPException(status_code=404, detail=f"Slot {slot_no} catalog not found")
        
        slot_value = catalog.price or Decimal('0')
        
        result = binary_service.calculate_dual_tree_earnings(slot_no, slot_value)
        
        if result["success"]:
            return success_response(result)
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))


@router.get("/duel-tree-details")
async def get_duel_tree_details(
    uid: str,
    tree_id: Optional[int] = None
):
    """
    Get duel tree details by tree ID or all trees if tree_id not provided
    
    Examples:
    - /binary/duel-tree-details?uid=AUTO001 - Returns all trees for user
    - /binary/duel-tree-details?uid=AUTO001&tree_id=3 - Returns specific tree with ID 3
    """
    try:
        if not uid:
            raise HTTPException(status_code=400, detail="uid parameter is required")
        
        # Find user by uid
        user = User.objects(uid=uid).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user.id)

        binary_service = BinaryService()
        
        # If tree_id is provided, return specific tree
        if tree_id is not None:
            result = binary_service.get_duel_tree_details(user_id, tree_id)
            
            if result["success"]:
                return success_response(result["data"])
            else:
                raise HTTPException(status_code=404, detail=result["error"])
        
        # If tree_id is not provided, return tree data from duel_tree_earnings
        else:
            result = binary_service.get_duel_tree_earnings(user_id)
            
            if result["success"]:
                tree_data = result["data"].get("tree")
                
                if not tree_data or not tree_data.get("nodes"):
                    raise HTTPException(status_code=404, detail="No tree data found for this user")
                
                # Return the tree object directly
                return success_response(tree_data)
            else:
                raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))