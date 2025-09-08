from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from bson import ObjectId
from ..user.model import User
from .model import (
    MatrixTree, MatrixActivation, MatrixRecycle, 
    MatrixAutoUpgrade, MatrixCommission, MatrixUplineReserve
)
from utils.response import success_response, error_response

router = APIRouter(prefix="/matrix", tags=["Matrix Program"])

# Pydantic models for request/response
class MatrixJoinRequest(BaseModel):
    user_id: str
    referrer_id: str
    tx_hash: str
    amount: float

class MatrixUpgradeRequest(BaseModel):
    user_id: str
    slot_no: int
    tx_hash: str
    amount: float

class MatrixRecycleRequest(BaseModel):
    user_id: str
    matrix_level: int
    recycle_position: str
    recycle_amount: float

class MatrixAutoUpgradeRequest(BaseModel):
    user_id: str
    from_slot: int
    to_slot: int
    tx_hash: str

# API Endpoints

@router.post("/join")
async def join_matrix(request: MatrixJoinRequest):
    """Join Matrix program with $11 USDT"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate referrer exists
        referrer = User.objects(id=ObjectId(request.referrer_id)).first()
        if not referrer:
            raise HTTPException(status_code=404, detail="Referrer not found")
        
        # Check if user already joined Matrix
        existing_matrix = MatrixTree.objects(user_id=ObjectId(request.user_id)).first()
        if existing_matrix:
            raise HTTPException(status_code=400, detail="User already joined Matrix program")
        
        # Create Matrix tree entry
        matrix_tree = MatrixTree(
            user_id=ObjectId(request.user_id),
            parent_id=ObjectId(request.referrer_id),
            current_slot=1,
            current_level=1,
            is_active=True,
            is_activated=False
        )
        
        # Initialize Matrix positions (left, center, right)
        from .model import MatrixPosition
        matrix_tree.positions = [
            MatrixPosition(position='left', is_active=False),
            MatrixPosition(position='center', is_upline_reserve=True, is_active=False),
            MatrixPosition(position='right', is_active=False)
        ]
        
        # Initialize STARTER slot
        from .model import MatrixSlotInfo
        matrix_tree.matrix_slots = [
            MatrixSlotInfo(
                slot_name='STARTER',
                slot_value=Decimal('11.0'),
                level=1,
                is_active=True,
                member_count=3,
                activated_at=datetime.utcnow()
            )
        ]
        
        matrix_tree.save()
        
        # Create activation record
        activation = MatrixActivation(
            user_id=ObjectId(request.user_id),
            slot_no=1,
            slot_name='STARTER',
            activation_type='initial',
            amount_paid=Decimal(str(request.amount)),
            tx_hash=request.tx_hash,
            status='completed',
            activated_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        activation.save()
        
        # Update user's Matrix status
        user.matrix_joined = True
        user.save()
        
        return success_response(
            data={
                "matrix_tree_id": str(matrix_tree.id),
                "activation_id": str(activation.id),
                "message": "Successfully joined Matrix program"
            },
            message="Matrix join successful"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/upgrade")
async def upgrade_matrix_slot(request: MatrixUpgradeRequest):
    """Upgrade Matrix slot"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get Matrix tree
        matrix_tree = MatrixTree.objects(user_id=ObjectId(request.user_id)).first()
        if not matrix_tree:
            raise HTTPException(status_code=404, detail="User not in Matrix program")
        
        # Validate slot upgrade
        if request.slot_no <= matrix_tree.current_slot:
            raise HTTPException(status_code=400, detail="Invalid slot upgrade")
        
        if request.slot_no > 5:
            raise HTTPException(status_code=400, detail="Maximum slot is 5 (PLATINUM)")
        
        # Create activation record
        slot_names = {1: 'STARTER', 2: 'BRONZE', 3: 'SILVER', 4: 'GOLD', 5: 'PLATINUM'}
        activation = MatrixActivation(
            user_id=ObjectId(request.user_id),
            slot_no=request.slot_no,
            slot_name=slot_names[request.slot_no],
            activation_type='upgrade',
            amount_paid=Decimal(str(request.amount)),
            tx_hash=request.tx_hash,
            status='completed',
            activated_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        activation.save()
        
        # Update Matrix tree
        matrix_tree.current_slot = request.slot_no
        matrix_tree.current_level = request.slot_no
        
        # Add new slot info
        from .model import MatrixSlotInfo
        slot_values = {1: 11, 2: 33, 3: 99, 4: 297, 5: 891}
        member_counts = {1: 3, 2: 9, 3: 27, 4: 81, 5: 243}
        
        new_slot = MatrixSlotInfo(
            slot_name=slot_names[request.slot_no],
            slot_value=Decimal(str(slot_values[request.slot_no])),
            level=request.slot_no,
            is_active=True,
            member_count=member_counts[request.slot_no],
            activated_at=datetime.utcnow()
        )
        matrix_tree.matrix_slots.append(new_slot)
        matrix_tree.save()
        
        return success_response(
            data={
                "activation_id": str(activation.id),
                "new_slot": slot_names[request.slot_no],
                "message": f"Successfully upgraded to {slot_names[request.slot_no]}"
            },
            message="Matrix upgrade successful"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/tree/{user_id}")
async def get_matrix_tree(user_id: str):
    """Get Matrix tree structure for a user"""
    try:
        matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
        if not matrix_tree:
            raise HTTPException(status_code=404, detail="Matrix tree not found")
        
        # Get children
        children = MatrixTree.objects(parent_id=ObjectId(user_id)).all()
        
        return success_response(
            data={
                "matrix_tree": {
                    "user_id": str(matrix_tree.user_id),
                    "current_slot": matrix_tree.current_slot,
                    "current_level": matrix_tree.current_level,
                    "positions": [
                        {
                            "position": pos.position,
                            "is_active": pos.is_active,
                            "is_upline_reserve": pos.is_upline_reserve,
                            "user_id": str(pos.user_id) if pos.user_id else None
                        } for pos in matrix_tree.positions
                    ],
                    "matrix_slots": [
                        {
                            "slot_name": slot.slot_name,
                            "slot_value": float(slot.slot_value),
                            "level": slot.level,
                            "is_active": slot.is_active,
                            "member_count": slot.member_count
                        } for slot in matrix_tree.matrix_slots
                    ],
                    "total_team_size": matrix_tree.total_team_size,
                    "auto_upgrade_enabled": matrix_tree.auto_upgrade_enabled,
                    "is_activated": matrix_tree.is_activated
                },
                "children": [
                    {
                        "user_id": str(child.user_id),
                        "current_slot": child.current_slot,
                        "current_level": child.current_level
                    } for child in children
                ]
            },
            message="Matrix tree retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/activations/{user_id}")
async def get_matrix_activations(user_id: str):
    """Get Matrix activation history for a user"""
    try:
        activations = MatrixActivation.objects(user_id=ObjectId(user_id)).order_by('-created_at').all()
        
        return success_response(
            data={
                "activations": [
                    {
                        "id": str(activation.id),
                        "slot_no": activation.slot_no,
                        "slot_name": activation.slot_name,
                        "activation_type": activation.activation_type,
                        "amount_paid": float(activation.amount_paid),
                        "status": activation.status,
                        "activated_at": activation.activated_at,
                        "tx_hash": activation.tx_hash
                    } for activation in activations
                ]
            },
            message="Matrix activations retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/auto-upgrade")
async def process_auto_upgrade(request: MatrixAutoUpgradeRequest):
    """Process Matrix auto upgrade using middle 3 members earnings"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get Matrix tree
        matrix_tree = MatrixTree.objects(user_id=ObjectId(request.user_id)).first()
        if not matrix_tree:
            raise HTTPException(status_code=404, detail="User not in Matrix program")
        
        # Check if auto upgrade is possible
        if not matrix_tree.auto_upgrade_enabled:
            raise HTTPException(status_code=400, detail="Auto upgrade not enabled")
        
        if request.to_slot <= matrix_tree.current_slot:
            raise HTTPException(status_code=400, detail="Invalid auto upgrade")
        
        # Create auto upgrade record
        auto_upgrade = MatrixAutoUpgrade(
            user_id=ObjectId(request.user_id),
            from_slot=request.from_slot,
            to_slot=request.to_slot,
            upgrade_cost=Decimal('0'),  # Will be calculated
            tx_hash=request.tx_hash,
            status='pending'
        )
        auto_upgrade.save()
        
        return success_response(
            data={
                "auto_upgrade_id": str(auto_upgrade.id),
                "message": "Auto upgrade initiated"
            },
            message="Matrix auto upgrade initiated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/commissions/{user_id}")
async def get_matrix_commissions(user_id: str):
    """Get Matrix commission history for a user"""
    try:
        commissions = MatrixCommission.objects(user_id=ObjectId(user_id)).order_by('-created_at').all()
        
        return success_response(
            data={
                "commissions": [
                    {
                        "id": str(commission.id),
                        "slot_no": commission.slot_no,
                        "slot_name": commission.slot_name,
                        "commission_amount": float(commission.commission_amount),
                        "commission_type": commission.commission_type,
                        "commission_percentage": commission.commission_percentage,
                        "status": commission.status,
                        "created_at": commission.created_at
                    } for commission in commissions
                ]
            },
            message="Matrix commissions retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/stats/{user_id}")
async def get_matrix_stats(user_id: str):
    """Get Matrix program statistics for a user"""
    try:
        matrix_tree = MatrixTree.objects(user_id=ObjectId(user_id)).first()
        if not matrix_tree:
            raise HTTPException(status_code=404, detail="Matrix tree not found")
        
        # Get activation count
        activation_count = MatrixActivation.objects(user_id=ObjectId(user_id)).count()
        
        # Get commission total
        total_commissions = MatrixCommission.objects(user_id=ObjectId(user_id), status='paid').sum('commission_amount')
        
        # Get team size
        team_size = MatrixTree.objects(parent_id=ObjectId(user_id)).count()
        
        return success_response(
            data={
                "current_slot": matrix_tree.current_slot,
                "current_level": matrix_tree.current_level,
                "activation_count": activation_count,
                "total_commissions": float(total_commissions) if total_commissions else 0,
                "team_size": team_size,
                "auto_upgrade_enabled": matrix_tree.auto_upgrade_enabled,
                "is_activated": matrix_tree.is_activated
            },
            message="Matrix stats retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))
