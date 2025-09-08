from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta
from ..user.model import User
from ..slot.model import SlotActivation
from ..tree.model import TreePlacement
from .model import (
    PhaseSystem, PhaseSystemEligibility, PhaseSystemUpgrade,
    PhaseSystemFund, PhaseSystemSettings, PhaseSystemLog, 
    PhaseSystemStatistics, PhaseSystemMember, PhaseSlot, PhaseProgress
)

class PhaseSystemService:
    """Phase-1 and Phase-2 System Business Logic Service"""
    
    def __init__(self):
        pass
    
    def join_phase_system(self, user_id: str, global_package_value: float = 33.0, currency: str = "USD") -> Dict[str, Any]:
        """Join Phase System"""
        try:
            # Validate user exists
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check if already joined
            existing = PhaseSystem.objects(user_id=ObjectId(user_id)).first()
            if existing:
                return {
                    "success": True,
                    "status": "already_joined",
                    "phase_system_id": str(existing.id),
                    "current_phase": existing.current_phase,
                    "current_slot": existing.current_slot,
                    "total_slots_completed": existing.total_slots_completed,
                    "message": "User already joined Phase System"
                }
            
            # Create Phase System record
            phase_system = PhaseSystem(
                user_id=ObjectId(user_id),
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
            phase_system.phase_slots = self._initialize_phase_slots()
            
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
                user_id=ObjectId(user_id),
                has_global_package=True,
                global_package_value=global_package_value,
                global_package_currency=currency,
                is_eligible_for_phase_1=True,
                qualified_at=datetime.utcnow()
            )
            eligibility.save()
            
            # Log the action
            self._log_action(user_id, "joined_phase_system", "User joined Phase System")
            
            return {
                "success": True,
                "phase_system_id": str(phase_system.id),
                "user_id": user_id,
                "is_joined": True,
                "is_active": True,
                "joined_at": phase_system.joined_at,
                "current_phase": "phase_1",
                "current_slot": 1,
                "current_slot_name": "FOUNDATION",
                "current_slot_value": 30.0,
                "current_required_members": 4,
                "message": "Successfully joined Phase System"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_eligibility(self, user_id: str) -> Dict[str, Any]:
        """Check Phase System eligibility for user"""
        try:
            # Get Phase System record
            phase_system = PhaseSystem.objects(user_id=ObjectId(user_id)).first()
            if not phase_system:
                return {"success": False, "error": "User not in Phase System"}
            
            # Get eligibility record
            eligibility = PhaseSystemEligibility.objects(user_id=ObjectId(user_id)).first()
            if not eligibility:
                eligibility = PhaseSystemEligibility(user_id=ObjectId(user_id))
            
            # Check current status
            current_status = self._check_current_phase_status(user_id)
            eligibility.global_team_size = current_status["global_team_size"]
            eligibility.direct_global_referrals = current_status["direct_global_referrals"]
            
            # Update Phase System record
            phase_system.global_team_size = current_status["global_team_size"]
            phase_system.direct_global_referrals = current_status["direct_global_referrals"]
            phase_system.current_members_count = current_status["current_members_count"]
            
            # Check eligibility for next phase/slot
            next_requirements = self._get_next_upgrade_requirements(phase_system)
            eligibility.is_eligible_for_phase_1 = next_requirements["phase_1_eligible"]
            eligibility.is_eligible_for_phase_2 = next_requirements["phase_2_eligible"]
            eligibility.is_eligible_for_next_slot = next_requirements["next_slot_eligible"]
            
            # Update eligibility reasons
            eligibility_reasons = self._get_eligibility_reasons(eligibility, phase_system)
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
            
            return {
                "success": True,
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
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_phase_upgrade(self, user_id: str, target_phase: str, target_slot: int) -> Dict[str, Any]:
        """Process Phase System upgrade"""
        try:
            # Validate user exists
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get Phase System record
            phase_system = PhaseSystem.objects(user_id=ObjectId(user_id)).first()
            if not phase_system:
                return {"success": False, "error": "User not in Phase System"}
            
            if not phase_system.is_active:
                return {"success": False, "error": "User not active in Phase System"}
            
            # Validate upgrade parameters
            if target_phase not in ['phase_1', 'phase_2']:
                return {"success": False, "error": "Invalid target phase"}
            
            if target_slot < 1 or target_slot > 16:
                return {"success": False, "error": "Invalid target slot (1-16)"}
            
            # Check if upgrade is possible
            current_slot = phase_system.current_slot
            current_phase = phase_system.current_phase
            
            if target_phase == current_phase and target_slot <= current_slot:
                return {"success": False, "error": "No upgrade needed"}
            
            # Get upgrade requirements
            upgrade_requirements = self._get_upgrade_requirements(target_phase, target_slot)
            if not upgrade_requirements:
                return {"success": False, "error": "Invalid upgrade requirements"}
            
            # Check if user meets requirements
            if phase_system.current_members_count < upgrade_requirements["required_members"]:
                return {"success": False, "error": "Insufficient members for upgrade"}
            
            # Create upgrade record
            upgrade = PhaseSystemUpgrade(
                user_id=ObjectId(user_id),
                phase_system_id=phase_system.id,
                from_phase=current_phase,
                from_slot=current_slot,
                to_phase=target_phase,
                to_slot=target_slot,
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
            phase_system.current_phase = target_phase
            phase_system.current_slot = target_slot
            phase_system.current_slot_name = upgrade_requirements["slot_name"]
            phase_system.current_slot_value = upgrade_requirements["slot_value"]
            phase_system.current_required_members = upgrade_requirements["required_members"]
            phase_system.total_slots_completed += 1
            phase_system.total_upgrade_costs += upgrade_requirements["upgrade_cost"]
            phase_system.last_updated = datetime.utcnow()
            
            # Update phase progress
            if phase_system.phase_progress:
                phase_system.phase_progress.current_phase = target_phase
                phase_system.phase_progress.current_slot = target_slot
                phase_system.phase_progress.total_slots_completed += 1
                phase_system.phase_progress.last_upgrade_at = datetime.utcnow()
                
                # Add to progression history
                progression_entry = {
                    "from_phase": current_phase,
                    "from_slot": current_slot,
                    "to_phase": target_phase,
                    "to_slot": target_slot,
                    "upgraded_at": datetime.utcnow(),
                    "upgrade_cost": upgrade_requirements["upgrade_cost"]
                }
                phase_system.phase_progress.progression_history.append(progression_entry)
            
            phase_system.save()
            
            # Log the action
            self._log_action(user_id, "phase_upgraded", 
                           f"Upgraded from {current_phase} Slot {current_slot} to {target_phase} Slot {target_slot}")
            
            return {
                "success": True,
                "upgrade_id": str(upgrade.id),
                "user_id": user_id,
                "from_phase": current_phase,
                "from_slot": current_slot,
                "to_phase": target_phase,
                "to_slot": target_slot,
                "upgrade_cost": upgrade_requirements["upgrade_cost"],
                "currency": "USD",
                "upgrade_status": "completed",
                "completed_at": upgrade.completed_at,
                "message": f"Successfully upgraded to {target_phase} Slot {target_slot}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def add_phase_system_member(self, user_id: str, upline_user_id: str, member_type: str, 
                              referral_level: int, contribution_amount: float) -> Dict[str, Any]:
        """Add member to Phase System"""
        try:
            # Validate users exist
            user = User.objects(id=ObjectId(user_id)).first()
            upline_user = User.objects(id=ObjectId(upline_user_id)).first()
            
            if not user or not upline_user:
                return {"success": False, "error": "User or upline not found"}
            
            # Get Phase System record
            phase_system = PhaseSystem.objects(user_id=ObjectId(upline_user_id)).first()
            if not phase_system:
                return {"success": False, "error": "Upline not in Phase System"}
            
            # Create member record
            member = PhaseSystemMember(
                user_id=ObjectId(user_id),
                phase_system_id=phase_system.id,
                member_type=member_type,
                referral_level=referral_level,
                upline_user_id=ObjectId(upline_user_id),
                joined_at=datetime.utcnow(),
                contribution_amount=contribution_amount,
                contribution_currency="USD",
                contribution_type="global_package"
            )
            member.save()
            
            # Update Phase System record
            phase_system.global_team_members.append(ObjectId(user_id))
            phase_system.global_team_size += 1
            phase_system.current_members_count += 1
            
            if referral_level == 1:
                phase_system.direct_global_referrals += 1
            
            phase_system.last_updated = datetime.utcnow()
            phase_system.save()
            
            # Log the action
            self._log_action(user_id, "members_added", 
                           f"Added member to Phase System: {member_type} level {referral_level}")
            
            return {
                "success": True,
                "member_id": str(member.id),
                "user_id": user_id,
                "upline_user_id": upline_user_id,
                "member_type": member_type,
                "referral_level": referral_level,
                "contribution_amount": contribution_amount,
                "currency": "USD",
                "joined_at": member.joined_at,
                "message": "Member added to Phase System"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_phase_system_statistics(self, period: str = "all_time") -> Dict[str, Any]:
        """Get Phase System statistics"""
        try:
            # Calculate period dates
            now = datetime.utcnow()
            if period == "daily":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
            elif period == "weekly":
                start_date = now - timedelta(days=now.weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(weeks=1)
            elif period == "monthly":
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1)
            else:  # all_time
                start_date = datetime(2024, 1, 1)
                end_date = now
            
            # Get statistics
            phase_systems = PhaseSystem.objects(
                created_at__gte=start_date,
                created_at__lt=end_date
            )
            
            total_participants = phase_systems.count()
            total_active_participants = phase_systems.filter(is_active=True).count()
            
            # Get upgrades for period
            upgrades = PhaseSystemUpgrade.objects(
                created_at__gte=start_date,
                created_at__lt=end_date,
                upgrade_status="completed"
            )
            
            total_upgrades_processed = upgrades.count()
            total_amount_distributed = sum(upgrade.upgrade_cost for upgrade in upgrades)
            
            # Phase breakdown
            phase_1_participants = phase_systems.filter(current_phase="phase_1").count()
            phase_1_upgrades = upgrades.filter(to_phase="phase_1").count()
            phase_1_amount = sum(upgrade.upgrade_cost for upgrade in upgrades.filter(to_phase="phase_1"))
            phase_2_participants = phase_systems.filter(current_phase="phase_2").count()
            phase_2_upgrades = upgrades.filter(to_phase="phase_2").count()
            phase_2_amount = sum(upgrade.upgrade_cost for upgrade in upgrades.filter(to_phase="phase_2"))
            
            # Slot breakdown
            slot_completions = {}
            for slot_num in range(1, 17):
                slot_completions[f"slot_{slot_num}"] = upgrades.filter(to_slot=slot_num).count()
            
            # Create or update statistics record
            statistics = PhaseSystemStatistics.objects(period=period).first()
            if not statistics:
                statistics = PhaseSystemStatistics(period=period)
            
            statistics.period_start = start_date
            statistics.period_end = end_date
            statistics.total_participants = total_participants
            statistics.total_active_participants = total_active_participants
            statistics.total_upgrades_processed = total_upgrades_processed
            statistics.total_amount_distributed = total_amount_distributed
            statistics.phase_1_participants = phase_1_participants
            statistics.phase_1_upgrades = phase_1_upgrades
            statistics.phase_1_amount = phase_1_amount
            statistics.phase_2_participants = phase_2_participants
            statistics.phase_2_upgrades = phase_2_upgrades
            statistics.phase_2_amount = phase_2_amount
            
            # Update slot statistics
            for slot_num in range(1, 17):
                setattr(statistics, f"slot_{slot_num}_completions", slot_completions[f"slot_{slot_num}"])
            
            statistics.last_updated = datetime.utcnow()
            statistics.save()
            
            return {
                "success": True,
                "period": period,
                "period_start": start_date,
                "period_end": end_date,
                "statistics": {
                    "total_participants": total_participants,
                    "total_active_participants": total_active_participants,
                    "total_upgrades_processed": total_upgrades_processed,
                    "total_amount_distributed": total_amount_distributed,
                    "phase_breakdown": {
                        "phase_1": {
                            "participants": phase_1_participants,
                            "upgrades": phase_1_upgrades,
                            "amount": phase_1_amount
                        },
                        "phase_2": {
                            "participants": phase_2_participants,
                            "upgrades": phase_2_upgrades,
                            "amount": phase_2_amount
                        }
                    },
                    "slot_breakdown": slot_completions,
                    "growth_statistics": {
                        "new_participants": total_participants,
                        "new_upgrades": total_upgrades_processed,
                        "total_global_team_growth": 0  # Would need to calculate
                    }
                },
                "last_updated": statistics.last_updated
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _initialize_phase_slots(self) -> List[PhaseSlot]:
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
    
    def _check_current_phase_status(self, user_id: str) -> Dict[str, Any]:
        """Check current phase status for user"""
        try:
            # This would need to be implemented based on actual team system
            # For now, returning mock data
            return {
                "global_team_size": 0,
                "direct_global_referrals": 0,
                "current_members_count": 0
            }
        except Exception:
            return {
                "global_team_size": 0,
                "direct_global_referrals": 0,
                "current_members_count": 0
            }
    
    def _get_next_upgrade_requirements(self, phase_system: PhaseSystem) -> Dict[str, Any]:
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
    
    def _get_upgrade_requirements(self, target_phase: str, target_slot: int) -> Optional[Dict[str, Any]]:
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
    
    def _get_eligibility_reasons(self, eligibility: PhaseSystemEligibility, phase_system: PhaseSystem) -> List[str]:
        """Get eligibility reasons"""
        reasons = []
        
        if not eligibility.has_global_package:
            reasons.append("Need to purchase Global package")
        
        if eligibility.global_team_size < 4:
            reasons.append("Need at least 4 global team members")
        
        if phase_system.current_members_count < phase_system.current_required_members:
            reasons.append(f"Need {phase_system.current_required_members} members for current slot")
        
        return reasons
    
    def _log_action(self, user_id: str, action_type: str, description: str):
        """Log Phase System action"""
        try:
            log = PhaseSystemLog(
                user_id=ObjectId(user_id),
                action_type=action_type,
                action_description=description,
                is_processed=True,
                processed_at=datetime.utcnow()
            )
            log.save()
        except Exception:
            pass  # Logging failure shouldn't break the main process
