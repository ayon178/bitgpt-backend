from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from ..user.model import User
from .model import (
    AutoUpgradeQueue, AutoUpgradeLog, BinaryAutoUpgrade, 
    MatrixAutoUpgrade, GlobalPhaseProgression, AutoUpgradeSettings,
    AutoUpgradeEarnings
)
from utils.response import success_response, error_response
from modules.slot.model import SlotActivation, SlotCatalog
from modules.binary.service import BinaryService
from modules.matrix.service import MatrixService
from modules.rank.service import RankService

router = APIRouter(prefix="/auto-upgrade", tags=["Auto Upgrade System"])

# Pydantic models for request/response
class AutoUpgradeRequest(BaseModel):
    user_id: str
    program: str
    target_slot_no: int
    trigger_type: str = "manual"

class AutoUpgradeProcessRequest(BaseModel):
    queue_id: str
    force_process: bool = False

class AutoUpgradeSettingsRequest(BaseModel):
    program: str
    auto_upgrade_enabled: bool
    check_interval_minutes: int
    batch_size: int

class EarningsContributeRequest(BaseModel):
    user_id: str
    contributor_id: str
    program: str
    amount: float
    currency: str
    earnings_type: str

# API Endpoints

@router.post("/queue")
async def queue_auto_upgrade(request: AutoUpgradeRequest, background_tasks: BackgroundTasks):
    """Queue an auto upgrade for processing"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get current slot information
        current_slot = await _get_current_slot(request.user_id, request.program)
        if not current_slot:
            raise HTTPException(status_code=400, detail="User not in program")
        
        # Validate target slot
        if request.target_slot_no <= current_slot['slot_no']:
            raise HTTPException(status_code=400, detail="Target slot must be higher than current slot")
        
        # Calculate upgrade cost
        upgrade_cost = await _calculate_upgrade_cost(request.program, request.target_slot_no)
        
        # Check if user is eligible for auto upgrade
        eligibility = await _check_auto_upgrade_eligibility(request.user_id, request.program)
        if not eligibility['is_eligible']:
            raise HTTPException(status_code=400, detail=f"User not eligible: {eligibility['reason']}")
        
        # Create auto upgrade queue entry
        queue_entry = AutoUpgradeQueue(
            user_id=ObjectId(request.user_id),
            program=request.program,
            current_slot_no=current_slot['slot_no'],
            target_slot_no=request.target_slot_no,
            upgrade_cost=upgrade_cost,
            currency=current_slot['currency'],
            earnings_available=eligibility['earnings_available'],
            status='pending',
            priority=1
        )
        
        # Set trigger information
        from .model import AutoUpgradeTrigger
        queue_entry.trigger = AutoUpgradeTrigger(
            trigger_type=request.trigger_type,
            program=request.program,
            partners_required=eligibility.get('partners_required', 0),
            partners_available=eligibility.get('partners_available', 0),
            middle_three_required=eligibility.get('middle_three_required', 0),
            middle_three_available=eligibility.get('middle_three_available', 0),
            earnings_threshold=upgrade_cost,
            current_earnings=eligibility['earnings_available'],
            is_triggered=True,
            triggered_at=datetime.utcnow()
        )
        
        queue_entry.save()
        
        # Add to background processing
        background_tasks.add_task(_process_auto_upgrade_queue, str(queue_entry.id))
        
        return success_response(
            data={
                "queue_id": str(queue_entry.id),
                "current_slot": current_slot['slot_no'],
                "target_slot": request.target_slot_no,
                "upgrade_cost": float(upgrade_cost),
                "earnings_available": float(eligibility['earnings_available']),
                "message": "Auto upgrade queued successfully"
            },
            message="Auto upgrade queued"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/process")
async def process_auto_upgrade(request: AutoUpgradeProcessRequest):
    """Process a specific auto upgrade from queue"""
    try:
        queue_entry = AutoUpgradeQueue.objects(id=ObjectId(request.queue_id)).first()
        if not queue_entry:
            raise HTTPException(status_code=404, detail="Queue entry not found")
        
        if queue_entry.status != 'pending' and not request.force_process:
            raise HTTPException(status_code=400, detail="Queue entry not in pending status")
        
        # Process the auto upgrade
        result = await _process_single_auto_upgrade(queue_entry)
        
        if result['success']:
            return success_response(
                data={
                    "queue_id": str(queue_entry.id),
                    "upgrade_log_id": result['upgrade_log_id'],
                    "from_slot": queue_entry.current_slot_no,
                    "to_slot": queue_entry.target_slot_no,
                    "earnings_used": float(queue_entry.earnings_used),
                    "message": "Auto upgrade processed successfully"
                },
                message="Auto upgrade processed"
            )
        else:
            return error_response(result['error'])
        
    except Exception as e:
        return error_response(str(e))

@router.get("/queue/{user_id}")
async def get_user_auto_upgrade_queue(user_id: str):
    """Get auto upgrade queue for a user"""
    try:
        queue_entries = AutoUpgradeQueue.objects(user_id=ObjectId(user_id)).order_by('-queued_at').all()
        
        return success_response(
            data={
                "queue_entries": [
                    {
                        "id": str(entry.id),
                        "program": entry.program,
                        "current_slot_no": entry.current_slot_no,
                        "target_slot_no": entry.target_slot_no,
                        "upgrade_cost": float(entry.upgrade_cost),
                        "currency": entry.currency,
                        "earnings_available": float(entry.earnings_available),
                        "earnings_used": float(entry.earnings_used),
                        "status": entry.status,
                        "priority": entry.priority,
                        "trigger_type": entry.trigger.trigger_type if entry.trigger else None,
                        "queued_at": entry.queued_at,
                        "processed_at": entry.processed_at,
                        "completed_at": entry.completed_at
                    } for entry in queue_entries
                ]
            },
            message="Auto upgrade queue retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/log/{user_id}")
async def get_auto_upgrade_log(user_id: str, limit: int = Query(50, le=100)):
    """Get auto upgrade log for a user"""
    try:
        upgrade_logs = AutoUpgradeLog.objects(user_id=ObjectId(user_id)).order_by('-completed_at').limit(limit)
        
        return success_response(
            data={
                "upgrade_logs": [
                    {
                        "id": str(log.id),
                        "program": log.program,
                        "from_slot_no": log.from_slot_no,
                        "to_slot_no": log.to_slot_no,
                        "from_slot_name": log.from_slot_name,
                        "to_slot_name": log.to_slot_name,
                        "upgrade_cost": float(log.upgrade_cost),
                        "currency": log.currency,
                        "earnings_used": float(log.earnings_used),
                        "profit_gained": float(log.profit_gained),
                        "trigger_type": log.trigger_type,
                        "contributors_count": len(log.contributors),
                        "status": log.status,
                        "completed_at": log.completed_at,
                        "tx_hash": log.tx_hash
                    } for log in upgrade_logs
                ]
            },
            message="Auto upgrade log retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/eligibility/{user_id}")
async def check_auto_upgrade_eligibility(user_id: str, program: str):
    """Check if user is eligible for auto upgrade"""
    try:
        eligibility = await _check_auto_upgrade_eligibility(user_id, program)
        
        return success_response(
            data={
                "user_id": user_id,
                "program": program,
                "is_eligible": eligibility['is_eligible'],
                "reason": eligibility.get('reason', ''),
                "earnings_available": float(eligibility.get('earnings_available', 0)),
                "partners_required": eligibility.get('partners_required', 0),
                "partners_available": eligibility.get('partners_available', 0),
                "middle_three_required": eligibility.get('middle_three_required', 0),
                "middle_three_available": eligibility.get('middle_three_available', 0),
                "next_upgrade_cost": float(eligibility.get('next_upgrade_cost', 0))
            },
            message="Eligibility check completed"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/binary/{user_id}")
async def get_binary_auto_upgrade_status(user_id: str):
    """Get Binary auto upgrade status for user"""
    try:
        binary_status = BinaryAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
        if not binary_status:
            raise HTTPException(status_code=404, detail="Binary auto upgrade status not found")
        
        return success_response(
            data={
                "user_id": user_id,
                "current_slot_no": binary_status.current_slot_no,
                "current_level": binary_status.current_level,
                "partners_required": binary_status.partners_required,
                "partners_available": binary_status.partners_available,
                "partner_ids": [str(pid) for pid in binary_status.partner_ids],
                "earnings_from_partners": float(binary_status.earnings_from_partners),
                "earnings_per_partner": float(binary_status.earnings_per_partner),
                "is_eligible": binary_status.is_eligible,
                "next_upgrade_cost": float(binary_status.next_upgrade_cost),
                "can_upgrade": binary_status.can_upgrade,
                "last_check_at": binary_status.last_check_at,
                "next_check_at": binary_status.next_check_at,
                "is_active": binary_status.is_active
            },
            message="Binary auto upgrade status retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/matrix/{user_id}")
async def get_matrix_auto_upgrade_status(user_id: str):
    """Get Matrix auto upgrade status for user"""
    try:
        matrix_status = MatrixAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
        if not matrix_status:
            raise HTTPException(status_code=404, detail="Matrix auto upgrade status not found")
        
        return success_response(
            data={
                "user_id": user_id,
                "current_slot_no": matrix_status.current_slot_no,
                "current_level": matrix_status.current_level,
                "middle_three_required": matrix_status.middle_three_required,
                "middle_three_available": matrix_status.middle_three_available,
                "middle_three_ids": [str(mid) for mid in matrix_status.middle_three_ids],
                "earnings_from_middle_three": float(matrix_status.earnings_from_middle_three),
                "earnings_per_member": float(matrix_status.earnings_per_member),
                "upline_reserve_amount": float(matrix_status.upline_reserve_amount),
                "upline_reserve_user_id": str(matrix_status.upline_reserve_user_id) if matrix_status.upline_reserve_user_id else None,
                "is_eligible": matrix_status.is_eligible,
                "next_upgrade_cost": float(matrix_status.next_upgrade_cost),
                "can_upgrade": matrix_status.can_upgrade,
                "last_check_at": matrix_status.last_check_at,
                "next_check_at": matrix_status.next_check_at,
                "is_active": matrix_status.is_active
            },
            message="Matrix auto upgrade status retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/global/{user_id}")
async def get_global_phase_progression(user_id: str):
    """Get Global phase progression status for user"""
    try:
        global_status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
        if not global_status:
            raise HTTPException(status_code=404, detail="Global phase progression not found")
        
        return success_response(
            data={
                "user_id": user_id,
                "current_phase": global_status.current_phase,
                "current_slot_no": global_status.current_slot_no,
                "phase_position": global_status.phase_position,
                "phase_1_members_required": global_status.phase_1_members_required,
                "phase_1_members_current": global_status.phase_1_members_current,
                "phase_2_members_required": global_status.phase_2_members_required,
                "phase_2_members_current": global_status.phase_2_members_current,
                "global_team_size": global_status.global_team_size,
                "global_team_members": [str(mid) for mid in global_status.global_team_members],
                "is_phase_complete": global_status.is_phase_complete,
                "phase_completed_at": global_status.phase_completed_at,
                "next_phase_ready": global_status.next_phase_ready,
                "total_re_entries": global_status.total_re_entries,
                "last_re_entry_at": global_status.last_re_entry_at,
                "re_entry_slot": global_status.re_entry_slot,
                "auto_progression_enabled": global_status.auto_progression_enabled,
                "progression_triggered": global_status.progression_triggered,
                "is_active": global_status.is_active
            },
            message="Global phase progression retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/earnings/contribute")
async def contribute_earnings(request: EarningsContributeRequest):
    """Contribute earnings for auto upgrade"""
    try:
        # Validate users exist
        user = User.objects(id=ObjectId(request.user_id)).first()
        contributor = User.objects(id=ObjectId(request.contributor_id)).first()
        
        if not user or not contributor:
            raise HTTPException(status_code=404, detail="User or contributor not found")
        
        # Create earnings record
        earnings = AutoUpgradeEarnings(
            user_id=ObjectId(request.user_id),
            contributor_id=ObjectId(request.contributor_id),
            program=request.program,
            earnings_amount=Decimal(str(request.amount)),
            currency=request.currency,
            earnings_type=request.earnings_type,
            remaining_amount=Decimal(str(request.amount)),
            expires_at=datetime.utcnow() + timedelta(days=30)  # Earnings expire in 30 days
        )
        earnings.save()
        
        return success_response(
            data={
                "earnings_id": str(earnings.id),
                "user_id": request.user_id,
                "contributor_id": request.contributor_id,
                "amount": request.amount,
                "currency": request.currency,
                "expires_at": earnings.expires_at,
                "message": "Earnings contributed successfully"
            },
            message="Earnings contribution successful"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/settings")
async def get_auto_upgrade_settings():
    """Get auto upgrade settings for all programs"""
    try:
        settings = AutoUpgradeSettings.objects(is_active=True).all()
        
        return success_response(
            data={
                "settings": [
                    {
                        "id": str(setting.id),
                        "program": setting.program,
                        "auto_upgrade_enabled": setting.auto_upgrade_enabled,
                        "check_interval_minutes": setting.check_interval_minutes,
                        "max_queue_size": setting.max_queue_size,
                        "binary_partners_required": setting.binary_partners_required,
                        "binary_earnings_percentage": setting.binary_earnings_percentage,
                        "matrix_middle_three_required": setting.matrix_middle_three_required,
                        "matrix_earnings_percentage": setting.matrix_earnings_percentage,
                        "matrix_upline_reserve_percentage": setting.matrix_upline_reserve_percentage,
                        "global_phase_1_members": setting.global_phase_1_members,
                        "global_phase_2_members": setting.global_phase_2_members,
                        "global_auto_progression": setting.global_auto_progression,
                        "batch_size": setting.batch_size,
                        "retry_attempts": setting.retry_attempts,
                        "retry_delay_minutes": setting.retry_delay_minutes,
                        "last_updated": setting.last_updated
                    } for setting in settings
                ]
            },
            message="Auto upgrade settings retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/settings")
async def update_auto_upgrade_settings(request: AutoUpgradeSettingsRequest):
    """Update auto upgrade settings"""
    try:
        setting = AutoUpgradeSettings.objects(program=request.program).first()
        
        if not setting:
            setting = AutoUpgradeSettings(program=request.program)
        
        setting.auto_upgrade_enabled = request.auto_upgrade_enabled
        setting.check_interval_minutes = request.check_interval_minutes
        setting.batch_size = request.batch_size
        setting.last_updated = datetime.utcnow()
        setting.save()
        
        return success_response(
            data={
                "setting_id": str(setting.id),
                "program": setting.program,
                "auto_upgrade_enabled": setting.auto_upgrade_enabled,
                "check_interval_minutes": setting.check_interval_minutes,
                "batch_size": setting.batch_size,
                "message": "Settings updated successfully"
            },
            message="Auto upgrade settings updated"
        )
        
    except Exception as e:
        return error_response(str(e))

# Helper functions
async def _get_current_slot(user_id: str, program: str) -> Optional[dict]:
    """Get current slot information for user"""
    # Determine highest activated slot for the program
    activation = (
        SlotActivation.objects(user_id=ObjectId(user_id), program=program)
        .order_by('-slot_no')
        .first()
    )
    if activation:
        return {
            "slot_no": activation.slot_no,
            "currency": activation.currency
        }
    # Fallback defaults by program
    if program == 'binary':
        return {"slot_no": 2, "currency": "BNB"}
    if program == 'matrix':
        return {"slot_no": 0, "currency": "USDT"}
    if program == 'global':
        return {"slot_no": 0, "currency": "USD"}
    return None

async def _calculate_upgrade_cost(program: str, target_slot: int) -> Decimal:
    """Calculate upgrade cost for target slot using SlotCatalog"""
    catalog = SlotCatalog.objects(program=program, slot_no=target_slot, is_active=True).first()
    if not catalog or not catalog.price:
        return Decimal('0')
    return Decimal(str(catalog.price))

async def _check_auto_upgrade_eligibility(user_id: str, program: str) -> dict:
    """Check if user is eligible for auto upgrade using program-specific trackers"""
    if program == 'binary':
        status = BinaryAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
        if not status:
            return {"is_eligible": False, "reason": "Binary auto upgrade status not found", "earnings_available": Decimal('0')}
        next_cost = await _calculate_upgrade_cost('binary', status.current_slot_no + 1)
        eligible = status.partners_available >= status.partners_required and status.earnings_from_partners >= next_cost
        return {
            "is_eligible": bool(eligible),
            "reason": "" if eligible else "Insufficient partners/earnings",
            "earnings_available": status.earnings_from_partners or Decimal('0'),
            "partners_required": status.partners_required,
            "partners_available": status.partners_available,
            "next_upgrade_cost": next_cost
        }
    if program == 'matrix':
        status = MatrixAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
        if not status:
            return {"is_eligible": False, "reason": "Matrix auto upgrade status not found", "earnings_available": Decimal('0')}
        next_cost = await _calculate_upgrade_cost('matrix', status.current_slot_no + 1)
        eligible = status.middle_three_available >= status.middle_three_required and status.earnings_from_middle_three >= next_cost
        return {
            "is_eligible": bool(eligible),
            "reason": "" if eligible else "Insufficient middle-three earnings",
            "earnings_available": status.earnings_from_middle_three or Decimal('0'),
            "middle_three_required": status.middle_three_required,
            "middle_three_available": status.middle_three_available,
            "next_upgrade_cost": next_cost
        }
    if program == 'global':
        # Simple placeholder based on phase requirements
        status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
        if not status:
            return {"is_eligible": False, "reason": "Global progression not found", "earnings_available": Decimal('0')}
        return {"is_eligible": bool(status.next_phase_ready), "reason": "" if status.next_phase_ready else "Phase not ready", "earnings_available": Decimal('0')}
    return {"is_eligible": False, "reason": "Invalid program", "earnings_available": Decimal('0')}

async def _process_auto_upgrade_queue(queue_id: str):
    """Background task to process auto upgrade queue"""
    try:
        entry = AutoUpgradeQueue.objects(id=ObjectId(queue_id)).first()
        if not entry:
            return
        if entry.status not in ['pending', 'failed']:
            return
        entry.status = 'processing'
        entry.processed_at = datetime.utcnow()
        entry.save()
        result = await _process_single_auto_upgrade(entry)
        if result.get('success'):
            entry.status = 'completed'
            entry.completed_at = datetime.utcnow()
            entry.save()
        else:
            entry.status = 'failed'
            entry.error_message = result.get('error')
            entry.save()
    except Exception as e:
        try:
            entry = AutoUpgradeQueue.objects(id=ObjectId(queue_id)).first()
            if entry:
                entry.status = 'failed'
                entry.error_message = str(e)
                entry.save()
        except Exception:
            pass

async def _process_single_auto_upgrade(queue_entry: AutoUpgradeQueue) -> dict:
    """Process a single auto upgrade by invoking the respective program service"""
    try:
        user_id_str = str(queue_entry.user_id)
        from_slot = queue_entry.current_slot_no
        to_slot = queue_entry.target_slot_no
        upgrade_cost = queue_entry.upgrade_cost
        currency = queue_entry.currency

        tx_hash = f"AUTOUP-{user_id_str}-{queue_entry.program}-S{to_slot}-{int(datetime.utcnow().timestamp())}"

        if queue_entry.program == 'binary':
            service = BinaryService()
            # For binary service, pass explicit amount
            service.upgrade_binary_slot(user_id=user_id_str, slot_no=to_slot, tx_hash=tx_hash, amount=Decimal(str(upgrade_cost)))
        elif queue_entry.program == 'matrix':
            service = MatrixService()
            # Matrix supports from->to upgrade path
            service.upgrade_matrix_slot(user_id=user_id_str, from_slot_no=from_slot, to_slot_no=to_slot, upgrade_type="auto")
        else:
            return {"success": False, "error": "Unsupported program for auto processing"}

        # Persist log
        from_catalog = SlotCatalog.objects(program=queue_entry.program, slot_no=from_slot).first()
        to_catalog = SlotCatalog.objects(program=queue_entry.program, slot_no=to_slot).first()
        log = AutoUpgradeLog(
            user_id=ObjectId(user_id_str),
            program=queue_entry.program,
            from_slot_no=from_slot,
            to_slot_no=to_slot,
            from_slot_name=from_catalog.name if from_catalog else str(from_slot),
            to_slot_name=to_catalog.name if to_catalog else str(to_slot),
            upgrade_cost=Decimal(str(upgrade_cost)),
            currency=currency,
            earnings_used=Decimal(str(upgrade_cost)),
            profit_gained=Decimal('0'),
            trigger_type=queue_entry.trigger.trigger_type if queue_entry.trigger else 'manual',
            contributors=queue_entry.earnings_source or [],
            contributor_details=[],
            tx_hash=tx_hash,
            status='completed',
            completed_at=datetime.utcnow()
        )
        log.save()

        # Trigger rank update after successful upgrade
        try:
            RankService().update_user_rank(user_id=user_id_str)
        except Exception:
            pass

        # Update queue entry aggregation
        queue_entry.earnings_used = Decimal(str(upgrade_cost))
        queue_entry.status = 'completed'
        queue_entry.completed_at = datetime.utcnow()
        queue_entry.save()

        return {"success": True, "upgrade_log_id": str(log.id)}
    except Exception as e:
        return {"success": False, "error": str(e)}
