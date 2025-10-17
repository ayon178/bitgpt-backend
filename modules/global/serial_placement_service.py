#!/usr/bin/env python3
"""
Global Serial Placement Service
Handles the serial placement logic with first user priority for Global program
"""

from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from datetime import datetime
from bson import ObjectId

from modules.user.model import User
from modules.wallet.model import UserWallet, ReserveLedger
from modules.slot.model import SlotCatalog, SlotActivation
from modules.tree.model import TreePlacement
from modules.blockchain.model import BlockchainEvent
from modules.income.model import IncomeEvent
# Import global models using importlib to avoid keyword issues
import importlib.util
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
global_model_spec = importlib.util.spec_from_file_location("global_model", os.path.join(os.path.dirname(__file__), "model.py"))
global_model = importlib.util.module_from_spec(global_model_spec)
global_model_spec.loader.exec_module(global_model)
GlobalTeamMember = global_model.GlobalTeamMember
GlobalDistribution = global_model.GlobalDistribution
GlobalTreeStructure = global_model.GlobalTreeStructure
GlobalPhaseSeat = global_model.GlobalPhaseSeat


class GlobalSerialPlacementService:
    """Service for managing Global Serial Placement Logic with first user priority"""
    
    def __init__(self):
        self.mother_id = "68dc17f08b174277bc40d19c"  # Mother ID fallback
        self.phase_1_capacity = 4  # Phase 1 requires 4 users
        self.phase_2_capacity = 8  # Phase 2 requires 8 users
        self.max_slots = 16  # Maximum slots in Global program
    
    def process_serial_placement(self, user_id: str, referrer_id: str, 
                               tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        """
        Process serial placement with first user priority.
        
        This is the main method that handles the complete serial placement logic:
        1. Identify first user and give priority
        2. Place all subsequent users serially in first user's Phase 1 Slot 1
        3. Handle phase progression (4 users → Phase 2, 8 users → Phase 1 Slot 2)
        4. Continue cycle for all 16 slots
        """
        try:
            # Step 1: Check if this is the first user
            first_user = self._get_first_user()
            
            if not first_user:
                # This is the very first user - becomes the priority user
                return self._create_first_user_tree(user_id, tx_hash, amount)
            else:
                # This is a subsequent user - place serially in first user's tree
                return self._place_in_serial_tree(user_id, referrer_id, first_user, tx_hash, amount)
                
        except Exception as e:
            return {"success": False, "error": f"Serial placement failed: {str(e)}"}
    
    def _get_first_user(self) -> Optional[Dict[str, Any]]:
        """
        Get the first user who has priority in Global program.
        Returns the user who was the first to join Global program.
        """
        try:
            # Find the first user by creation date in Global program
            first_placement = TreePlacement.objects(
                program='global',
                is_active=True
            ).order_by('created_at').first()
            
            if first_placement:
                user = User.objects(id=first_placement.user_id).first()
                if user:
                    return {
                        "user_id": str(user.id),
                        "placement_id": str(first_placement.id),
                        "created_at": first_placement.created_at,
                        "current_phase": first_placement.phase,
                        "current_slot": first_placement.slot_no
                    }
            
            return None
            
        except Exception as e:
            print(f"Error getting first user: {e}")
            return None
    
    def _create_first_user_tree(self, user_id: str, tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        """
        Create the first user's tree with priority status.
        """
        try:
            # Create Phase 1 Slot 1 placement for first user
            placement = TreePlacement(
                user_id=ObjectId(user_id),
                program='global',
                phase='PHASE-1',
                slot_no=1,
                parent_id=None,  # First user has no parent
                upline_id=None,  # First user has no upline
                level=1,
                position=str(1),
                is_active=True,
                is_first_user=True,  # Mark as first user
                created_at=datetime.utcnow()
            )
            placement.save()
            
            # Create Global team member record
            team_member = GlobalTeamMember(
                user_id=ObjectId(user_id),
                parent_user_id=None,  # First user has no parent
                phase='PHASE-1',
                slot_number=1,
                position_in_phase=1,
                level_in_tree=1,
                direct_downlines=[],
                total_downlines=[],
                is_active=True,
                joined_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow(),
                phase_1_contributions=0,
                phase_2_contributions=0
            )
            team_member.save()
            
            # Process fund distribution for first user
            distribution_result = self._process_fund_distribution(user_id, amount, "first_user_creation")
            
            return {
                "success": True,
                "placement_type": "first_user",
                "user_id": user_id,
                "phase": "PHASE-1",
                "slot": 1,
                "level": 1,
                "position": 1,
                "is_priority": True,
                "distribution_result": distribution_result,
                "message": "First user created with priority status"
            }
            
        except Exception as e:
            return {"success": False, "error": f"First user creation failed: {str(e)}"}
    
    def _place_in_serial_tree(self, user_id: str, referrer_id: str, first_user: Dict[str, Any], 
                            tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        """
        Place subsequent users serially in first user's tree.
        """
        try:
            first_user_id = first_user["user_id"]
            current_phase = first_user["current_phase"]
            current_slot = first_user["current_slot"]
            
            # Check current phase capacity
            phase_capacity = self.phase_1_capacity if current_phase == "PHASE-1" else self.phase_2_capacity
            
            # Count current members in first user's current phase/slot
            current_members = TreePlacement.objects(
                program='global',
                phase=current_phase,
                slot_no=current_slot,
                is_active=True
            ).count()
            
            # Determine placement position
            placement_position = current_members + 1
            
            # Create placement for the user
            placement = TreePlacement(
                user_id=ObjectId(user_id),
                program='global',
                phase=current_phase,
                slot_no=current_slot,
                parent_id=ObjectId(first_user_id),  # Set parent_id to first user
                upline_id=ObjectId(first_user_id),  # Set upline_id for tree queries
                level=1,  # All users in first user's tree are level 1
                position=str(placement_position),
                is_active=True,
                is_first_user=False,
                created_at=datetime.utcnow()
            )
            placement.save()
            
            # Create Global team member record
            team_member = GlobalTeamMember(
                user_id=ObjectId(user_id),
                parent_user_id=ObjectId(first_user_id),
                phase=current_phase,
                slot_number=current_slot,
                position_in_phase=placement_position,
                level_in_tree=1,
                direct_downlines=[],
                total_downlines=[],
                is_active=True,
                joined_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow(),
                phase_1_contributions=0,
                phase_2_contributions=0
            )
            team_member.save()
            
            # Process fund distribution
            distribution_result = self._process_fund_distribution(user_id, amount, "serial_placement")
            
            # Check if phase is now complete and trigger progression
            progression_result = self._check_and_trigger_progression(first_user_id, current_phase, current_slot)
            
            return {
                "success": True,
                "placement_type": "serial",
                "user_id": user_id,
                "first_user_id": first_user_id,
                "phase": current_phase,
                "slot": current_slot,
                "level": 1,
                "position": placement_position,
                "is_priority": False,
                "distribution_result": distribution_result,
                "progression_result": progression_result,
                "message": f"User placed serially in first user's {current_phase} Slot {current_slot}"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Serial placement failed: {str(e)}"}
    
    def _check_and_trigger_progression(self, first_user_id: str, current_phase: str, current_slot: int) -> Dict[str, Any]:
        """
        Check if phase is complete and trigger progression to next phase/slot.
        """
        try:
            # Count current members in the phase/slot
            current_members = TreePlacement.objects(
                program='global',
                phase=current_phase,
                slot_no=current_slot,
                is_active=True
            ).count()
            
            phase_capacity = self.phase_1_capacity if current_phase == "PHASE-1" else self.phase_2_capacity
            
            if current_members >= phase_capacity:
                # Phase is complete, trigger progression
                if current_phase == "PHASE-1":
                    # Phase 1 complete → Move to Phase 2 Slot 1
                    return self._trigger_phase_progression(first_user_id, "PHASE-2", 1)
                else:
                    # Phase 2 complete → Move to Phase 1 Slot (current_slot + 1)
                    next_slot = current_slot + 1
                    if next_slot <= self.max_slots:
                        return self._trigger_phase_progression(first_user_id, "PHASE-1", next_slot)
                    else:
                        return {
                            "success": True,
                            "progression": "completed",
                            "message": f"First user completed all {self.max_slots} slots"
                        }
            else:
                return {
                    "success": True,
                    "progression": "pending",
                    "current_members": current_members,
                    "required_members": phase_capacity,
                    "remaining": phase_capacity - current_members
                }
                
        except Exception as e:
            return {"success": False, "error": f"Progression check failed: {str(e)}"}
    
    def _trigger_phase_progression(self, first_user_id: str, new_phase: str, new_slot: int) -> Dict[str, Any]:
        """
        Trigger phase progression for the first user.
        """
        try:
            # Update first user's placement to new phase/slot
            first_user_placement = TreePlacement.objects(
                user_id=ObjectId(first_user_id),
                program='global',
                is_active=True
            ).order_by('created_at').first()
            
            if first_user_placement:
                # Deactivate current placement
                first_user_placement.is_active = False
                first_user_placement.save()
                
                # Create new placement for next phase/slot
                new_placement = TreePlacement(
                    user_id=ObjectId(first_user_id),
                    program='global',
                    phase=new_phase,
                    slot_no=new_slot,
                    parent_id=None,  # First user has no parent
                    upline_id=None,  # First user has no upline
                    level=1,
                    position=str(1),
                    is_active=True,
                    is_first_user=True,
                    created_at=datetime.utcnow()
                )
                new_placement.save()
                
                # Update Global team member record
                team_member = GlobalTeamMember.objects(
                    user_id=ObjectId(first_user_id)
                ).first()
                
                if team_member:
                    team_member.phase = new_phase
                    team_member.slot_number = new_slot
                    team_member.position_in_phase = 1
                    team_member.last_activity_at = datetime.utcnow()
                    team_member.save()
                
                return {
                    "success": True,
                    "progression": "completed",
                    "new_phase": new_phase,
                    "new_slot": new_slot,
                    "message": f"First user progressed to {new_phase} Slot {new_slot}"
                }
            else:
                return {"success": False, "error": "First user placement not found"}
                
        except Exception as e:
            return {"success": False, "error": f"Phase progression failed: {str(e)}"}
    
    def _process_fund_distribution(self, user_id: str, amount: Decimal, distribution_type: str, phase: str = 'PHASE-1') -> Dict[str, Any]:
        """
        Process fund distribution according to Global program rules:
        30% Tree Upline Reserve + 30% Tree Upline Wallet + 10% Partner Incentive + 
        10% Royal Captain Bonus + 10% President Reward + 5% Share Holders + 5% Triple Entry Reward
        """
        try:
            # Calculate distribution amounts
            tree_upline_reserve = amount * Decimal('0.30')  # 30%
            tree_upline_wallet = amount * Decimal('0.30')   # 30%
            partner_incentive = amount * Decimal('0.10')    # 10%
            royal_captain_bonus = amount * Decimal('0.10')  # 10%
            president_reward = amount * Decimal('0.10')      # 10%
            share_holders = amount * Decimal('0.05')        # 5%
            triple_entry_reward = amount * Decimal('0.05')   # 5%
            
            # Total should equal 100%
            total_distributed = (tree_upline_reserve + tree_upline_wallet + 
                               partner_incentive + royal_captain_bonus + 
                               president_reward + share_holders + triple_entry_reward)
            
            # Create income events for each distribution
            distributions = []
            
            # Tree Upline Reserve (30%)
            distributions.append(self._create_income_event(
                user_id, self._normalize_income_type("tree_upline_reserve", phase), tree_upline_reserve, "Global Tree Upline Reserve"
            ))
            
            # Tree Upline Wallet (30%)
            distributions.append(self._create_income_event(
                user_id, self._normalize_income_type("tree_upline_wallet", phase), tree_upline_wallet, "Global Tree Upline Wallet"
            ))
            
            # Partner Incentive (10%)
            distributions.append(self._create_income_event(
                user_id, self._normalize_income_type("partner_incentive", phase), partner_incentive, "Global Partner Incentive"
            ))
            
            # Royal Captain Bonus (10%)
            distributions.append(self._create_income_event(
                user_id, self._normalize_income_type("royal_captain_bonus", phase), royal_captain_bonus, "Global Royal Captain Bonus"
            ))
            
            # President Reward (10%)
            distributions.append(self._create_income_event(
                user_id, self._normalize_income_type("president_reward", phase), president_reward, "Global President Reward"
            ))
            
            # Share Holders (5%)
            distributions.append(self._create_income_event(
                user_id, self._normalize_income_type("share_holders", phase), share_holders, "Global Share Holders"
            ))
            
            # Triple Entry Reward (5%)
            distributions.append(self._create_income_event(
                user_id, self._normalize_income_type("triple_entry_reward", phase), triple_entry_reward, "Global Triple Entry Reward"
            ))
            
            return {
                "success": True,
                "total_amount": amount,
                "total_distributed": total_distributed,
                "distributions": distributions,
                "distribution_type": distribution_type
            }
            
        except Exception as e:
            return {"success": False, "error": f"Fund distribution failed: {str(e)}"}

    def _normalize_income_type(self, income_type: str, phase: str) -> str:
        if income_type in ("tree_upline_reserve", "tree_upline_wallet"):
            return 'global_phase_1' if phase == 'PHASE-1' else 'global_phase_2'
        if income_type == "royal_captain_bonus":
            return 'royal_captain'
        if income_type == "share_holders":
            return 'shareholders'
        if income_type == "triple_entry_reward":
            return 'triple_entry'
        return income_type
    
    def _create_income_event(self, user_id: str, income_type: str, amount: Decimal, description: str) -> Dict[str, Any]:
        """Create income event for fund distribution."""
        try:
            income_event = IncomeEvent(
                user_id=ObjectId(user_id),
                source_user_id=ObjectId(user_id),
                program='global',
                slot_no=1,  # Default slot for Global program
                income_type=income_type,
                amount=amount,
                percentage=Decimal('100.0'),
                tx_hash=f"GLOBAL-{income_type}-{user_id}",
                status='completed',
                description=description
            )
            income_event.save()
            
            return {
                "income_type": income_type,
                "amount": amount,
                "description": description,
                "status": "completed"
            }
            
        except Exception as e:
            return {
                "income_type": income_type,
                "amount": amount,
                "description": description,
                "status": "failed",
                "error": str(e)
            }
    
    def get_serial_placement_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive serial placement status for a user.
        """
        try:
            # Get user's placement
            placement = TreePlacement.objects(
                user_id=ObjectId(user_id),
                program='global',
                is_active=True
            ).first()
            
            if not placement:
                return {"error": "User not found in Global program"}
            
            # Get first user information
            first_user = self._get_first_user()
            
            # Get current phase statistics
            current_phase_members = TreePlacement.objects(
                program='global',
                phase=placement.phase,
                slot_no=placement.slot_no,
                is_active=True
            ).count()
            
            phase_capacity = self.phase_1_capacity if placement.phase == "PHASE-1" else self.phase_2_capacity
            
            status = {
                "user_id": user_id,
                "is_first_user": placement.is_first_user if hasattr(placement, 'is_first_user') else False,
                "current_phase": placement.phase,
                "current_slot": placement.slot_no,
                "current_level": placement.level,
                "current_position": placement.position,
                "first_user_id": first_user["user_id"] if first_user else None,
                "current_phase_members": current_phase_members,
                "phase_capacity": phase_capacity,
                "remaining_capacity": phase_capacity - current_phase_members,
                "progression_ready": current_phase_members >= phase_capacity
            }
            
            return {"success": True, "data": status}
            
        except Exception as e:
            return {"error": f"Error getting serial placement status: {str(e)}"}
    
    def get_first_user_progression(self) -> Dict[str, Any]:
        """
        Get the progression status of the first user.
        """
        try:
            first_user = self._get_first_user()
            if not first_user:
                return {"error": "No first user found"}
            
            # Get all placements for first user
            all_placements = TreePlacement.objects(
                user_id=ObjectId(first_user["user_id"]),
                program='global'
            ).order_by('created_at')
            
            progression_history = []
            for placement in all_placements:
                progression_history.append({
                    "phase": placement.phase,
                    "slot": placement.slot_no,
                    "is_active": placement.is_active,
                    "created_at": placement.created_at
                })
            
            return {
                "success": True,
                "first_user_id": first_user["user_id"],
                "current_phase": first_user["current_phase"],
                "current_slot": first_user["current_slot"],
                "progression_history": progression_history,
                "total_slots_completed": len([p for p in progression_history if not p["is_active"]]),
                "remaining_slots": self.max_slots - len([p for p in progression_history if not p["is_active"]])
            }
            
        except Exception as e:
            return {"error": f"Error getting first user progression: {str(e)}"}
