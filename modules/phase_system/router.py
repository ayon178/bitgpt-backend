from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from ..user.model import User, PartnerGraph
from .model import (
    PhaseSystem, PhaseSystemEligibility, PhaseSystemUpgrade,
    PhaseSystemFund, PhaseSystemSettings, PhaseSystemLog, 
    PhaseSystemStatistics, PhaseSystemMember, PhaseSlot, PhaseProgress
)
from utils.response import success_response, error_response
from auth.service import authentication_service

router = APIRouter(prefix="/phase-system", tags=["Phase System"])

# Pydantic models for request/response
class PhaseSystemJoinRequest(BaseModel):
    user_id: str
    global_package_value: float = 33.0
    currency: str = "USD"

class PhaseSystemUpgradeRequest(BaseModel):
    user_id: str
    target_phase: str
    target_slot: int

class PhaseSystemMemberRequest(BaseModel):
    user_id: str
    upline_user_id: str
    member_type: str
    referral_level: int
    contribution_amount: float

class PhaseSystemSettingsRequest(BaseModel):
    phase_system_enabled: bool
    auto_upgrade_enabled: bool
    auto_progression_enabled: bool
    phase_1_member_requirement: int
    phase_2_member_requirement: int
    slot_requirements: dict
    upgrade_delay_hours: int
    max_upgrades_per_day: int

class PhaseSystemFundRequest(BaseModel):
    fund_amount: float
    currency: str = "USD"
    source: str

# API Endpoints

@router.post("/join")
async def join_phase_system(request: PhaseSystemJoinRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    """Join Phase System"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if already joined
        existing = PhaseSystem.objects(user_id=ObjectId(request.user_id)).first()
        if existing:
            return success_response(
                data={
                    "user_id": request.user_id,
                    "status": "already_joined",
                    "current_phase": existing.current_phase,
                    "current_slot": existing.current_slot,
                    "total_slots_completed": existing.total_slots_completed,
                    "message": "User already joined Phase System"
                },
                message="Already joined Phase System"
            )
        
        # Create Phase System record
        phase_system = PhaseSystem(
            user_id=ObjectId(request.user_id),
            joined_at=datetime.utcnow(),
            is_joined=True,
            is_active=True,
            activated_at=datetime.utcnow(),
            current_phase="phase_1",
            current_slot=1,
            current_slot_name="FOUNDATION",
            current_slot_value=30.0,
            current_required_members=4
        )
        
        # Initialize phase slots
        phase_system.phase_slots = _initialize_phase_slots()
        
        # Initialize phase progress
        phase_system.phase_progress = PhaseProgress(
            current_phase="phase_1",
            current_slot=1,
            total_phases_completed=0,
            total_slots_completed=0
        )
        
        phase_system.save()
        
        # Create eligibility record
        eligibility = PhaseSystemEligibility(
            user_id=ObjectId(request.user_id),
            has_global_package=True,
            global_package_value=request.global_package_value,
            global_package_currency=request.currency,
            is_eligible_for_phase_1=True,
            qualified_at=datetime.utcnow()
        )
        eligibility.save()
        
        return success_response(
            data={
                "phase_system_id": str(phase_system.id),
                "user_id": request.user_id,
                "is_joined": True,
                "is_active": True,
                "joined_at": phase_system.joined_at,
                "current_phase": "phase_1",
                "current_slot": 1,
                "current_slot_name": "FOUNDATION",
                "current_slot_value": 30.0,
                "current_required_members": 4,
                "message": "Successfully joined Phase System"
            },
            message="Joined Phase System"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/status/{user_id}")
async def get_phase_system_status(user_id: str, current_user: dict = Depends(authentication_service.verify_authentication)):
    """Get Phase System status for user"""
    try:
        phase_system = PhaseSystem.objects(user_id=ObjectId(user_id)).first()
        if not phase_system:
            raise HTTPException(status_code=404, detail="User not in Phase System")
        
        return success_response(
            data={
                "user_id": user_id,
                "program_status": {
                    "is_joined": phase_system.is_joined,
                    "is_active": phase_system.is_active,
                    "joined_at": phase_system.joined_at,
                    "activated_at": phase_system.activated_at
                },
                "current_status": {
                    "current_phase": phase_system.current_phase,
                    "current_slot": phase_system.current_slot,
                    "current_slot_name": phase_system.current_slot_name,
                    "current_slot_value": phase_system.current_slot_value,
                    "current_required_members": phase_system.current_required_members,
                    "current_members_count": phase_system.current_members_count,
                    "global_team_size": phase_system.global_team_size,
                    "direct_global_referrals": phase_system.direct_global_referrals
                },
                "phase_slots": [
                    {
                        "slot_number": slot.slot_number,
                        "slot_name": slot.slot_name,
                        "slot_value": slot.slot_value,
                        "phase_type": slot.phase_type,
                        "required_members": slot.required_members,
                        "current_members": slot.current_members,
                        "is_active": slot.is_active,
                        "is_completed": slot.is_completed,
                        "activated_at": slot.activated_at,
                        "completed_at": slot.completed_at,
                        "total_income": slot.total_income,
                        "upgrade_cost": slot.upgrade_cost,
                        "wallet_amount": slot.wallet_amount
                    } for slot in phase_system.phase_slots
                ],
                "progress_summary": {
                    "total_phases_completed": phase_system.total_phases_completed,
                    "total_slots_completed": phase_system.total_slots_completed,
                    "total_income_earned": phase_system.total_income_earned,
                    "total_upgrade_costs": phase_system.total_upgrade_costs,
                    "total_wallet_amount": phase_system.total_wallet_amount
                },
                "last_updated": phase_system.last_updated
            },
            message="Phase System status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/eligibility/{user_id}")
async def check_phase_system_eligibility(user_id: str, current_user: dict = Depends(authentication_service.verify_authentication)):
    """Check Phase System eligibility for user"""
    try:
        # Get Phase System record
        phase_system = PhaseSystem.objects(user_id=ObjectId(user_id)).first()
        if not phase_system:
            raise HTTPException(status_code=404, detail="User not in Phase System")
        
        # Get eligibility record
        eligibility = PhaseSystemEligibility.objects(user_id=ObjectId(user_id)).first()
        if not eligibility:
            eligibility = PhaseSystemEligibility(user_id=ObjectId(user_id))
        
        # Check current status
        current_status = _check_current_phase_status(user_id)
        eligibility.global_team_size = current_status["global_team_size"]
        eligibility.direct_global_referrals = current_status["direct_global_referrals"]
        
        # Update Phase System record
        phase_system.global_team_size = current_status["global_team_size"]
        phase_system.direct_global_referrals = current_status["direct_global_referrals"]
        phase_system.current_members_count = current_status["current_members_count"]
        
        # Check eligibility for next phase/slot
        next_requirements = _get_next_upgrade_requirements(phase_system)
        eligibility.is_eligible_for_phase_1 = next_requirements["phase_1_eligible"]
        eligibility.is_eligible_for_phase_2 = next_requirements["phase_2_eligible"]
        eligibility.is_eligible_for_next_slot = next_requirements["next_slot_eligible"]
        
        # Update eligibility reasons
        eligibility_reasons = _get_eligibility_reasons(eligibility, phase_system)
        eligibility.eligibility_reasons = eligibility_reasons
        
        # Check if user became eligible for next upgrade
        if next_requirements["next_slot_eligible"] and not phase_system.is_active:
            eligibility.qualified_at = datetime.utcnow()
            phase_system.is_active = True
            phase_system.activated_at = datetime.utcnow()
        
        eligibility.last_checked = datetime.utcnow()
        eligibility.save()
        
        phase_system.last_updated = datetime.utcnow()
        phase_system.save()
        
        return success_response(
            data={
                "user_id": user_id,
                "is_eligible_for_phase_1": eligibility.is_eligible_for_phase_1,
                "is_eligible_for_phase_2": eligibility.is_eligible_for_phase_2,
                "is_eligible_for_next_slot": eligibility.is_eligible_for_next_slot,
                "current_status": {
                    "global_team_size": eligibility.global_team_size,
                    "direct_global_referrals": eligibility.direct_global_referrals,
                    "current_phase": phase_system.current_phase,
                    "current_slot": phase_system.current_slot,
                    "current_members_count": phase_system.current_members_count
                },
                "next_requirements": next_requirements,
                "eligibility_reasons": eligibility.eligibility_reasons,
                "qualified_at": eligibility.qualified_at,
                "last_checked": eligibility.last_checked
            },
            message="Phase System eligibility checked"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/upgrade")
async def process_phase_upgrade(request: PhaseSystemUpgradeRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    """Process Phase System upgrade"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get Phase System record
        phase_system = PhaseSystem.objects(user_id=ObjectId(request.user_id)).first()
        if not phase_system:
            raise HTTPException(status_code=404, detail="User not in Phase System")
        
        if not phase_system.is_active:
            raise HTTPException(status_code=400, detail="User not active in Phase System")
        
        # Validate upgrade parameters
        if request.target_phase not in ['phase_1', 'phase_2']:
            raise HTTPException(status_code=400, detail="Invalid target phase")
        
        if request.target_slot < 1 or request.target_slot > 16:
            raise HTTPException(status_code=400, detail="Invalid target slot (1-16)")
        
        # Check if upgrade is possible
        current_slot = phase_system.current_slot
        current_phase = phase_system.current_phase
        
        if request.target_phase == current_phase and request.target_slot <= current_slot:
            return success_response(
                data={
                    "user_id": request.user_id,
                    "status": "no_upgrade_needed",
                    "message": "No upgrade needed"
                },
                message="No upgrade needed"
            )
        
        # Get upgrade requirements
        upgrade_requirements = _get_upgrade_requirements(request.target_phase, request.target_slot)
        if not upgrade_requirements:
            raise HTTPException(status_code=400, detail="Invalid upgrade requirements")
        
        # Check if user meets requirements
        if phase_system.current_members_count < upgrade_requirements["required_members"]:
            raise HTTPException(status_code=400, detail="Insufficient members for upgrade")
        
        # Create upgrade record
        upgrade = PhaseSystemUpgrade(
            user_id=ObjectId(request.user_id),
            phase_system_id=phase_system.id,
            from_phase=current_phase,
            from_slot=current_slot,
            to_phase=request.target_phase,
            to_slot=request.target_slot,
            required_members=upgrade_requirements["required_members"],
            actual_members=phase_system.current_members_count,
            upgrade_cost=upgrade_requirements["upgrade_cost"],
            upgrade_status="processing"
        )
        upgrade.save()
        
        # Process upgrade
        upgrade.upgrade_status = "completed"
        upgrade.processed_at = datetime.utcnow()
        upgrade.completed_at = datetime.utcnow()
        upgrade.save()
        
        # Update Phase System record
        phase_system.current_phase = request.target_phase
        phase_system.current_slot = request.target_slot
        phase_system.current_slot_name = upgrade_requirements["slot_name"]
        phase_system.current_slot_value = upgrade_requirements["slot_value"]
        phase_system.current_required_members = upgrade_requirements["required_members"]
        phase_system.total_slots_completed += 1
        phase_system.total_upgrade_costs += upgrade_requirements["upgrade_cost"]
        phase_system.last_updated = datetime.utcnow()
        
        # Update phase progress
        if phase_system.phase_progress:
            phase_system.phase_progress.current_phase = request.target_phase
            phase_system.phase_progress.current_slot = request.target_slot
            phase_system.phase_progress.total_slots_completed += 1
            phase_system.phase_progress.last_upgrade_at = datetime.utcnow()
            
            # Add to progression history
            progression_entry = {
                "from_phase": current_phase,
                "from_slot": current_slot,
                "to_phase": request.target_phase,
                "to_slot": request.target_slot,
                "upgraded_at": datetime.utcnow(),
                "upgrade_cost": upgrade_requirements["upgrade_cost"]
            }
            phase_system.phase_progress.progression_history.append(progression_entry)
        
        phase_system.save()
        
        return success_response(
            data={
                "upgrade_id": str(upgrade.id),
                "user_id": request.user_id,
                "from_phase": current_phase,
                "from_slot": current_slot,
                "to_phase": request.target_phase,
                "to_slot": request.target_slot,
                "upgrade_cost": upgrade_requirements["upgrade_cost"],
                "currency": "USD",
                "upgrade_status": "completed",
                "completed_at": upgrade.completed_at,
                "message": f"Successfully upgraded to {request.target_phase} Slot {request.target_slot}"
            },
            message="Phase System upgrade processed"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/add-member")
async def add_phase_system_member(request: PhaseSystemMemberRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    """Add member to Phase System"""
    try:
        # Validate users exist
        user = User.objects(id=ObjectId(request.user_id)).first()
        upline_user = User.objects(id=ObjectId(request.upline_user_id)).first()
        
        if not user or not upline_user:
            raise HTTPException(status_code=404, detail="User or upline not found")
        
        # Get Phase System record
        phase_system = PhaseSystem.objects(user_id=ObjectId(request.upline_user_id)).first()
        if not phase_system:
            raise HTTPException(status_code=404, detail="Upline not in Phase System")
        
        # Create member record
        member = PhaseSystemMember(
            user_id=ObjectId(request.user_id),
            phase_system_id=phase_system.id,
            member_type=request.member_type,
            referral_level=request.referral_level,
            upline_user_id=ObjectId(request.upline_user_id),
            joined_at=datetime.utcnow(),
            contribution_amount=request.contribution_amount,
            contribution_currency="USD",
            contribution_type="global_package"
        )
        member.save()
        
        # Update Phase System record
        phase_system.global_team_members.append(ObjectId(request.user_id))
        phase_system.global_team_size += 1
        phase_system.current_members_count += 1
        
        if request.referral_level == 1:
            phase_system.direct_global_referrals += 1
        
        phase_system.last_updated = datetime.utcnow()
        phase_system.save()
        
        return success_response(
            data={
                "member_id": str(member.id),
                "user_id": request.user_id,
                "upline_user_id": request.upline_user_id,
                "member_type": request.member_type,
                "referral_level": request.referral_level,
                "contribution_amount": request.contribution_amount,
                "currency": "USD",
                "joined_at": member.joined_at,
                "message": "Member added to Phase System"
            },
            message="Member added to Phase System"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/fund")
async def get_phase_system_fund(current_user: dict = Depends(authentication_service.verify_authentication)):
    """Get Phase System fund status"""
    try:
        fund = PhaseSystemFund.objects(is_active=True).first()
        if not fund:
            # Create default fund
            fund = PhaseSystemFund()
            fund.save()
        
        return success_response(
            data={
                "fund_name": fund.fund_name,
                "total_fund_amount": fund.total_fund_amount,
                "available_amount": fund.available_amount,
                "distributed_amount": fund.distributed_amount,
                "currency": fund.currency,
                "fund_sources": fund.fund_sources,
                "auto_replenish": fund.auto_replenish,
                "replenish_threshold": fund.replenish_threshold,
                "max_distribution_per_day": fund.max_distribution_per_day,
                "statistics": {
                    "total_participants": fund.total_participants,
                    "total_upgrades_processed": fund.total_upgrades_processed,
                    "total_amount_distributed": fund.total_amount_distributed
                },
                "last_updated": fund.last_updated
            },
            message="Phase System fund status retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/fund")
async def update_phase_system_fund(request: PhaseSystemFundRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    """Update Phase System fund"""
    try:
        fund = PhaseSystemFund.objects(is_active=True).first()
        if not fund:
            fund = PhaseSystemFund()
        
        # Update fund
        fund.total_fund_amount += request.fund_amount
        fund.available_amount += request.fund_amount
        
        # Update fund sources
        if request.source in fund.fund_sources:
            fund.fund_sources[request.source] += request.fund_amount
        else:
            fund.fund_sources[request.source] = request.fund_amount
        
        fund.last_updated = datetime.utcnow()
        fund.save()
        
        return success_response(
            data={
                "fund_id": str(fund.id),
                "total_fund_amount": fund.total_fund_amount,
                "available_amount": fund.available_amount,
                "added_amount": request.fund_amount,
                "source": request.source,
                "currency": request.currency,
                "message": "Phase System fund updated successfully"
            },
            message="Phase System fund updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/settings")
async def get_phase_system_settings(current_user: dict = Depends(authentication_service.verify_authentication)):
    """Get Phase System settings"""
    try:
        settings = PhaseSystemSettings.objects(is_active=True).first()
        if not settings:
            # Create default settings
            settings = PhaseSystemSettings()
            settings.save()
        
        return success_response(
            data={
                "phase_system_enabled": settings.phase_system_enabled,
                "auto_upgrade_enabled": settings.auto_upgrade_enabled,
                "auto_progression_enabled": settings.auto_progression_enabled,
                "phase_requirements": {
                    "phase_1_member_requirement": settings.phase_1_member_requirement,
                    "phase_2_member_requirement": settings.phase_2_member_requirement
                },
                "slot_requirements": settings.slot_requirements,
                "upgrade_settings": {
                    "upgrade_delay_hours": settings.upgrade_delay_hours,
                    "max_upgrades_per_day": settings.max_upgrades_per_day
                },
                "last_updated": settings.last_updated
            },
            message="Phase System settings retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/settings")
async def update_phase_system_settings(request: PhaseSystemSettingsRequest, current_user: dict = Depends(authentication_service.verify_authentication)):
    """Update Phase System settings"""
    try:
        settings = PhaseSystemSettings.objects(is_active=True).first()
        if not settings:
            settings = PhaseSystemSettings()
        
        settings.phase_system_enabled = request.phase_system_enabled
        settings.auto_upgrade_enabled = request.auto_upgrade_enabled
        settings.auto_progression_enabled = request.auto_progression_enabled
        settings.phase_1_member_requirement = request.phase_1_member_requirement
        settings.phase_2_member_requirement = request.phase_2_member_requirement
        settings.slot_requirements = request.slot_requirements
        settings.upgrade_delay_hours = request.upgrade_delay_hours
        settings.max_upgrades_per_day = request.max_upgrades_per_day
        settings.last_updated = datetime.utcnow()
        settings.save()
        
        return success_response(
            data={
                "settings_id": str(settings.id),
                "phase_system_enabled": settings.phase_system_enabled,
                "auto_upgrade_enabled": settings.auto_upgrade_enabled,
                "auto_progression_enabled": settings.auto_progression_enabled,
                "phase_1_member_requirement": settings.phase_1_member_requirement,
                "phase_2_member_requirement": settings.phase_2_member_requirement,
                "slot_requirements": settings.slot_requirements,
                "upgrade_delay_hours": settings.upgrade_delay_hours,
                "max_upgrades_per_day": settings.max_upgrades_per_day,
                "last_updated": settings.last_updated,
                "message": "Phase System settings updated successfully"
            },
            message="Phase System settings updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/statistics")
async def get_phase_system_statistics(period: str = Query("all_time", regex="^(daily|weekly|monthly|all_time)$"), current_user: dict = Depends(authentication_service.verify_authentication)):
    """Get Phase System statistics"""
    try:
        statistics = PhaseSystemStatistics.objects(period=period, is_active=True).order_by('-last_updated').first()
        
        if not statistics:
            return success_response(
                data={
                    "period": period,
                    "statistics": {
                        "total_participants": 0,
                        "total_active_participants": 0,
                        "total_upgrades_processed": 0,
                        "total_amount_distributed": 0.0,
                        "phase_breakdown": {
                            "phase_1": {"participants": 0, "upgrades": 0, "amount": 0.0},
                            "phase_2": {"participants": 0, "upgrades": 0, "amount": 0.0}
                        },
                        "slot_breakdown": {
                            "slot_1": 0, "slot_2": 0, "slot_3": 0, "slot_4": 0,
                            "slot_5": 0, "slot_6": 0, "slot_7": 0, "slot_8": 0,
                            "slot_9": 0, "slot_10": 0, "slot_11": 0, "slot_12": 0,
                            "slot_13": 0, "slot_14": 0, "slot_15": 0, "slot_16": 0
                        },
                        "growth_statistics": {
                            "new_participants": 0,
                            "new_upgrades": 0,
                            "total_global_team_growth": 0
                        }
                    },
                    "message": "No statistics available for this period"
                },
                message="Phase System statistics retrieved"
            )
        
        return success_response(
            data={
                "period": statistics.period,
                "period_start": statistics.period_start,
                "period_end": statistics.period_end,
                "statistics": {
                    "total_participants": statistics.total_participants,
                    "total_active_participants": statistics.total_active_participants,
                    "total_upgrades_processed": statistics.total_upgrades_processed,
                    "total_amount_distributed": statistics.total_amount_distributed,
                    "phase_breakdown": {
                        "phase_1": {
                            "participants": statistics.phase_1_participants,
                            "upgrades": statistics.phase_1_upgrades,
                            "amount": statistics.phase_1_amount
                        },
                        "phase_2": {
                            "participants": statistics.phase_2_participants,
                            "upgrades": statistics.phase_2_upgrades,
                            "amount": statistics.phase_2_amount
                        }
                    },
                    "slot_breakdown": {
                        "slot_1": statistics.slot_1_completions,
                        "slot_2": statistics.slot_2_completions,
                        "slot_3": statistics.slot_3_completions,
                        "slot_4": statistics.slot_4_completions,
                        "slot_5": statistics.slot_5_completions,
                        "slot_6": statistics.slot_6_completions,
                        "slot_7": statistics.slot_7_completions,
                        "slot_8": statistics.slot_8_completions,
                        "slot_9": statistics.slot_9_completions,
                        "slot_10": statistics.slot_10_completions,
                        "slot_11": statistics.slot_11_completions,
                        "slot_12": statistics.slot_12_completions,
                        "slot_13": statistics.slot_13_completions,
                        "slot_14": statistics.slot_14_completions,
                        "slot_15": statistics.slot_15_completions,
                        "slot_16": statistics.slot_16_completions
                    },
                    "growth_statistics": {
                        "new_participants": statistics.new_participants,
                        "new_upgrades": statistics.new_upgrades,
                        "total_global_team_growth": statistics.total_global_team_growth
                    }
                },
                "last_updated": statistics.last_updated
            },
            message="Phase System statistics retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/leaderboard")
async def get_phase_system_leaderboard(limit: int = Query(50, le=100), current_user: dict = Depends(authentication_service.verify_authentication)):
    """Get Phase System leaderboard"""
    try:
        # Get top Phase System participants
        phase_systems = PhaseSystem.objects(is_active=True).order_by('-total_slots_completed', '-total_income_earned').limit(limit)
        
        leaderboard_data = []
        for phase_system in phase_systems:
            leaderboard_data.append({
                "user_id": str(phase_system.user_id),
                "current_phase": phase_system.current_phase,
                "current_slot": phase_system.current_slot,
                "current_slot_name": phase_system.current_slot_name,
                "current_slot_value": phase_system.current_slot_value,
                "total_phases_completed": phase_system.total_phases_completed,
                "total_slots_completed": phase_system.total_slots_completed,
                "total_income_earned": phase_system.total_income_earned,
                "total_upgrade_costs": phase_system.total_upgrade_costs,
                "total_wallet_amount": phase_system.total_wallet_amount,
                "global_team_size": phase_system.global_team_size,
                "direct_global_referrals": phase_system.direct_global_referrals,
                "is_active": phase_system.is_active,
                "joined_at": phase_system.joined_at
            })
        
        return success_response(
            data={
                "leaderboard": leaderboard_data,
                "total_participants": len(leaderboard_data),
                "message": "Phase System leaderboard retrieved"
            },
            message="Phase System leaderboard retrieved"
        )
        
    except Exception as e:
        return error_response(str(e))

# Helper functions
def _initialize_phase_slots() -> List[PhaseSlot]:
    """Initialize Phase System slots"""
    return [
        PhaseSlot(slot_number=1, slot_name="FOUNDATION", slot_value=30.0, phase_type="phase_1", required_members=4),
        PhaseSlot(slot_number=2, slot_name="APEX", slot_value=36.0, phase_type="phase_2", required_members=8),
        PhaseSlot(slot_number=3, slot_name="SUMMIT", slot_value=86.0, phase_type="phase_1", required_members=4),
        PhaseSlot(slot_number=4, slot_name="RADIANCE", slot_value=103.0, phase_type="phase_2", required_members=8),
        PhaseSlot(slot_number=5, slot_name="HORIZON", slot_value=247.0, phase_type="phase_1", required_members=4),
        PhaseSlot(slot_number=6, slot_name="PARAMOUNT", slot_value=296.0, phase_type="phase_2", required_members=8),
        PhaseSlot(slot_number=7, slot_name="CATALYST", slot_value=710.0, phase_type="phase_1", required_members=4),
        PhaseSlot(slot_number=8, slot_name="ODYSSEY", slot_value=852.0, phase_type="phase_2", required_members=8),
        PhaseSlot(slot_number=9, slot_name="PINNACLE", slot_value=2044.0, phase_type="phase_1", required_members=4),
        PhaseSlot(slot_number=10, slot_name="PRIME", slot_value=2452.0, phase_type="phase_2", required_members=8),
        PhaseSlot(slot_number=11, slot_name="MOMENTUM", slot_value=5884.0, phase_type="phase_1", required_members=4),
        PhaseSlot(slot_number=12, slot_name="CREST", slot_value=7060.0, phase_type="phase_2", required_members=8),
        PhaseSlot(slot_number=13, slot_name="VERTEX", slot_value=16944.0, phase_type="phase_1", required_members=4),
        PhaseSlot(slot_number=14, slot_name="LEGACY", slot_value=20332.0, phase_type="phase_2", required_members=8),
        PhaseSlot(slot_number=15, slot_name="ASCEND", slot_value=48796.0, phase_type="phase_1", required_members=4),
        PhaseSlot(slot_number=16, slot_name="EVEREST", slot_value=58555.0, phase_type="phase_2", required_members=8)
    ]

def _check_current_phase_status(user_id: str) -> Dict[str, Any]:
    """Use PartnerGraph to derive team and directs for Global program"""
    try:
        graph = PartnerGraph.objects(user_id=ObjectId(user_id)).first()
        global_team_size = graph.total_team if graph else 0
        # If program‑wise direct counts are tracked
        direct_global = 0
        if graph and graph.directs_count_by_program and 'global' in graph.directs_count_by_program:
            direct_global = graph.directs_count_by_program['global'] or 0
        else:
            # Fallback: direct children in tree for global
            from ..tree.model import TreePlacement
            direct_global = TreePlacement.objects(parent_id=ObjectId(user_id), program='global', is_active=True).count()

        return {
            "global_team_size": global_team_size,
            "direct_global_referrals": direct_global,
            "current_members_count": direct_global,  # used as current members for slot progression
        }
    except Exception:
        return {
            "global_team_size": 0,
            "direct_global_referrals": 0,
            "current_members_count": 0,
        }

def _get_next_upgrade_requirements(phase_system: PhaseSystem) -> Dict[str, Any]:
    """Get next upgrade requirements"""
    current_slot = phase_system.current_slot
    current_phase = phase_system.current_phase
    
    # Determine next slot
    if current_phase == "phase_1":
        next_phase = "phase_2"
        next_slot = current_slot
        required_members = 8
    else:
        next_phase = "phase_1"
        next_slot = current_slot + 1
        required_members = 4
    
    return {
        "phase_1_eligible": current_phase == "phase_2" and phase_system.current_members_count >= 8,
        "phase_2_eligible": current_phase == "phase_1" and phase_system.current_members_count >= 4,
        "next_slot_eligible": phase_system.current_members_count >= required_members,
        "next_phase": next_phase,
        "next_slot": next_slot,
        "required_members": required_members
    }

def _get_upgrade_requirements(target_phase: str, target_slot: int) -> Optional[Dict[str, Any]]:
    """Get upgrade requirements for target phase and slot"""
    slot_requirements = {
        1: {"phase_1": 4, "phase_2": 8, "value": 30.0, "name": "FOUNDATION"},
        2: {"phase_1": 4, "phase_2": 8, "value": 36.0, "name": "APEX"},
        3: {"phase_1": 4, "phase_2": 8, "value": 86.0, "name": "SUMMIT"},
        4: {"phase_1": 4, "phase_2": 8, "value": 103.0, "name": "RADIANCE"},
        5: {"phase_1": 4, "phase_2": 8, "value": 247.0, "name": "HORIZON"},
        6: {"phase_1": 4, "phase_2": 8, "value": 296.0, "name": "PARAMOUNT"},
        7: {"phase_1": 4, "phase_2": 8, "value": 710.0, "name": "CATALYST"},
        8: {"phase_1": 4, "phase_2": 8, "value": 852.0, "name": "ODYSSEY"},
        9: {"phase_1": 4, "phase_2": 8, "value": 2044.0, "name": "PINNACLE"},
        10: {"phase_1": 4, "phase_2": 8, "value": 2452.0, "name": "PRIME"},
        11: {"phase_1": 4, "phase_2": 8, "value": 5884.0, "name": "MOMENTUM"},
        12: {"phase_1": 4, "phase_2": 8, "value": 7060.0, "name": "CREST"},
        13: {"phase_1": 4, "phase_2": 8, "value": 16944.0, "name": "VERTEX"},
        14: {"phase_1": 4, "phase_2": 8, "value": 20332.0, "name": "LEGACY"},
        15: {"phase_1": 4, "phase_2": 8, "value": 48796.0, "name": "ASCEND"},
        16: {"phase_1": 4, "phase_2": 8, "value": 58555.0, "name": "EVEREST"}
    }
    
    if target_slot not in slot_requirements:
        return None
    
    slot_info = slot_requirements[target_slot]
    return {
        "required_members": slot_info[target_phase],
        "slot_value": slot_info["value"],
        "slot_name": slot_info["name"],
        "upgrade_cost": slot_info["value"]
    }

def _get_eligibility_reasons(eligibility: PhaseSystemEligibility, phase_system: PhaseSystem) -> List[str]:
    """Get eligibility reasons"""
    reasons = []
    
    if not eligibility.has_global_package:
        reasons.append("Need to purchase Global package")
    
    if eligibility.global_team_size < 4:
        reasons.append("Need at least 4 global team members")
    
    if phase_system.current_members_count < phase_system.current_required_members:
        reasons.append(f"Need {phase_system.current_required_members} members for current slot")
    
    return reasons
