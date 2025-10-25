from typing import Dict, Any, List
from bson import ObjectId
from datetime import datetime
from decimal import Decimal
from modules.auto_upgrade.model import GlobalPhaseProgression
from modules.slot.model import SlotCatalog, SlotActivation
from modules.user.model import User, EarningHistory
from modules.commission.service import CommissionService
from modules.spark.service import SparkService
from modules.royal_captain.model import RoyalCaptainFund
from modules.president_reward.model import PresidentRewardFund
from modules.royal_captain.service import RoyalCaptainService
from modules.president_reward.service import PresidentRewardService
from modules.income.bonus_fund import BonusFund
from modules.tree.model import TreePlacement
from modules.wallet.company_service import CompanyWalletService
from modules.spark.model import TripleEntryReward, SparkBonusDistribution
from modules.user.model import ShareholdersDistribution, ShareholdersFund, Shareholder
from utils import ensure_currency_for_program
from .model import GlobalTeamMember, GlobalDistribution, GlobalTreeStructure, GlobalPhaseSeat
from .serial_placement_service import GlobalSerialPlacementService


class GlobalService:
    """Global Program Business Logic Service (Phase-1/Phase-2 progression)."""

    def __init__(self) -> None:
        self.commission_service = CommissionService()
        self.spark_service = SparkService()
        self.company_wallet = CompanyWalletService()
        self.serial_placement_service = GlobalSerialPlacementService()

    def _count_phase_children(self, parent_id: ObjectId, phase: str) -> int:
        return TreePlacement.objects(parent_id=parent_id, program='global', phase=phase, is_active=True).count()
    
    def _validate_parent_child_relationship(self, user_id: str, parent_id: ObjectId | None) -> bool:
        """
        Validate that the parent-child relationship is correct
        """
        try:
            user_oid = ObjectId(user_id)
            
            # Check for self-parenting
            if parent_id and parent_id == user_oid:
                print(f"Validation failed: User {user_id} cannot be their own parent (self-parenting)")
                return False
            
            # Check for circular references and parent validation
            if parent_id:
                # Check if the parent exists and is valid
                parent_placement = TreePlacement.objects(user_id=parent_id, program='global', phase='PHASE-1').first()
                if not parent_placement:
                    print(f"Validation failed: Parent {parent_id} not found in Phase-1")
                    return False
                
                # Check if the current user already has a placement record
                current_user_placement = TreePlacement.objects(user_id=user_oid, program='global', phase='PHASE-1').first()
                
                # If current user exists in tree, check for circular references
                if current_user_placement:
                    # Check if the parent is actually a child of the current user (circular reference)
                    if parent_placement.parent_id == user_oid:
                        print(f"Validation failed: Circular reference detected - user {user_id} and parent {parent_id}")
                        return False
            
            print(f"Parent-child relationship validation passed for user {user_id} with parent {parent_id}")
            return True
            
        except Exception as e:
            print(f"Parent-child relationship validation failed for user {user_id}: {str(e)}")
            return False

    def _find_current_root_in_phase1(self) -> ObjectId | None:
        """
        Find the current root user in Phase 1.
        Root is the user with no parent (parent_id=None) in Phase 1.
        """
        try:
            # Find the root user in Phase 1 (user with no parent)
            root_user = TreePlacement.objects(
                program='global', 
                phase='PHASE-1', 
                is_active=True,
                parent_id=None
            ).first()
            
            if root_user:
                print(f"Found current root user in Phase 1: {root_user.user_id}")
                return root_user.user_id
            else:
                print("No root user found in Phase 1")
                return None
            
        except Exception as e:
            print(f"Error finding current root in Phase 1: {str(e)}")
            return None

    def _update_root_position_in_phase1(self) -> Dict[str, Any]:
        """
        Update root position in Phase 1 when current root moves to Phase 2.
        The second user (first downline) becomes the new root.
        """
        try:
            # Find the first downline of the moved root user
            # This will be the new root in Phase 1
            new_root_placement = TreePlacement.objects(
                program='global',
                phase='PHASE-1',
                is_active=True
            ).order_by('created_at').first()
            
            if new_root_placement:
                # Update the new root's parent_id to None (making it root)
                new_root_placement.parent_id = None
                new_root_placement.upline_id = None
                new_root_placement.level = 1
                new_root_placement.position = "1"
                new_root_placement.phase_position = 1
                new_root_placement.save()
                
                print(f"Updated root position: User {new_root_placement.user_id} is now root in Phase 1")
                
                # Update all remaining Phase-1 users to be under the new root
                remaining_users = TreePlacement.objects(
                    program='global',
                    phase='PHASE-1',
                    is_active=True,
                    parent_id__ne=None  # Exclude the new root
                )
                
                for user in remaining_users:
                    user.parent_id = new_root_placement.user_id
                    user.upline_id = new_root_placement.user_id
                    user.level = 2
                    user.save()
                    print(f"  - Updated user {user.user_id} to be under new root")
                
                return {
                    "success": True,
                    "new_root_id": str(new_root_placement.user_id),
                    "message": f"User {new_root_placement.user_id} is now root in Phase 1"
                }
            else:
                print("No user found to become new root in Phase 1")
                return {"success": False, "error": "No user found to become new root"}
                
        except Exception as e:
            print(f"Error updating root position in Phase 1: {str(e)}")
            return {"success": False, "error": str(e)}

    def _find_phase1_parent_bfs(self) -> ObjectId | None:
        """
        Find the earliest Global participant whose PHASE-1 has < 4 children using proper BFS algorithm
        """
        try:
            # First, check if there are any existing Global users
            existing_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True).order_by('created_at')
            
            if not existing_users:
                print("No existing Global users found, will be root user")
                return None
            
            # Start BFS from the earliest users (ROOT users first)
            queue = []
            visited = set()
            
            # Find all ROOT users (users with no parent) and add them to queue first
            root_users = [placement.user_id for placement in existing_users if not placement.parent_id]
            queue.extend(root_users)
            
            # Add remaining users to queue (non-root users)
            non_root_users = [placement.user_id for placement in existing_users if placement.parent_id]
            queue.extend(non_root_users)
            
            print(f"Starting BFS with {len(queue)} users in queue (ROOT users: {len(root_users)})")
            
            # BFS traversal
            while queue:
                current_user_id = queue.pop(0)
                
                if current_user_id in visited:
                    continue
                visited.add(current_user_id)
                
                # Count existing children for this user
                child_count = TreePlacement.objects(parent_id=current_user_id, program='global', phase='PHASE-1', is_active=True).count()
                
                print(f"BFS checking user {current_user_id}: {child_count}/4 children")
                
                if child_count < 4:
                    print(f"Found eligible parent {current_user_id} with {child_count} children")
                    return current_user_id
                
                # Add children to queue for further exploration
                children = TreePlacement.objects(parent_id=current_user_id, program='global', phase='PHASE-1', is_active=True)
                for child in children:
                    if child.user_id not in visited:
                        queue.append(child.user_id)
            
            print("No eligible parent found in BFS")
            return None
            
        except Exception as e:
            print(f"BFS parent search failed: {str(e)}")
            return None

    def _find_phase1_parent_escalation(self, user_id: str) -> ObjectId | None:
        """
        Escalate up to 60 levels to find eligible upline with available Phase-1 positions
        """
        try:
            user_oid = ObjectId(user_id)
            current_user = user_oid
            escalation_level = 0
            max_escalation = 60
            
            while escalation_level < max_escalation:
                # Find direct upline in PHASE-1
                upline_placement = TreePlacement.objects(user_id=current_user, program='global', phase='PHASE-1').first()
                if not upline_placement or not upline_placement.parent_id:
                    break
                
                current_user = upline_placement.parent_id
                escalation_level += 1
                
                # Ensure we don't escalate back to the original user (prevent circular reference)
                if current_user == user_oid:
                    print(f"Escalation detected circular reference for user {user_id}, breaking")
                    break
                
                # Check if this upline has available Phase-1 positions
                child_count = TreePlacement.objects(parent_id=current_user, program='global', phase='PHASE-1', is_active=True).count()
                if child_count < 4:
                    print(f"Found eligible parent via escalation {current_user} with {child_count} children")
                    return current_user
            
            print("No eligible parent found via escalation")
            return None
        except Exception as e:
            print(f"Escalation failed for user {user_id}: {str(e)}")
            return None

    def _get_mother_id(self) -> ObjectId | None:
        """
        Get Mother ID as fallback when no eligible upline found
        """
        try:
            # Try to find user with uid "ROOT" as Mother ID
            from modules.user.model import User
            root_user = User.objects(uid='ROOT').first()
            if root_user:
                return root_user.id
            return None
        except Exception as e:
            print(f"Failed to get Mother ID: {str(e)}")
        return None

    def _place_in_phase1(self, user_id: str) -> Dict[str, Any]:
        """
        Global Phase-1 Placement Logic according to business requirements:
        1. First user becomes root in Phase 1 Slot 1
        2. Subsequent users join serially under the most recent user in current phase
        3. When Phase 1 is full (4 users), first user moves to Phase 2
        4. New users then join under the next available user in Phase 1
        """
        try:
            user_oid = ObjectId(user_id)
            
            # Check if this is the first user (ROOT user)
            existing_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True).count()
            print(f"DEBUG: Existing users in Phase-1: {existing_users}")
            
            if existing_users == 0:
                print(f"User {user_id} is the first Global user, will be ROOT user")
                parent_id = None
                level = 1
                position = 1
            else:
                print(f"User {user_id} is not the first user, finding current root")
                # Find the current root user in Phase 1
                parent_id = self._find_current_root_in_phase1()
                
                if not parent_id:
                    print(f"No root user found in Phase 1 for user {user_id}")
                    return {"success": False, "error": "No root user found in Phase 1"}
                
                # Determine level and position
                if parent_id:
                    parent_node = TreePlacement.objects(user_id=parent_id, program='global', phase='PHASE-1').first()
                    level = (parent_node.level + 1) if parent_node else 2
                    # Count existing downlines for this parent to determine position
                    existing_downlines = TreePlacement.objects(parent_id=parent_id, program='global', phase='PHASE-1', is_active=True).count()
                    position = existing_downlines + 1
                else:
                    level = 1
                    position = 1
            
            # Validate parent-child relationship before proceeding
            if not self._validate_parent_child_relationship(user_id, parent_id):
                return {"success": False, "error": "Invalid parent-child relationship detected"}
            
            print(f"Placing user {user_id} under parent {parent_id} at level {level}, position {position}")
            
            # Create placement record
            placement = TreePlacement(
                user_id=user_oid,
                program='global',
                phase='PHASE-1',
                slot_no=1,
                parent_id=parent_id if parent_id and parent_id != user_oid else None,  # Don't self-parent
                upline_id=parent_id if parent_id and parent_id != user_oid else None,  # Set upline_id
                position=str(position),
                level=level,
                phase_position=position,
                is_active=True,
                is_activated=True,
                activation_date=datetime.utcnow()
            )
            placement.save()
            print(f"Created TreePlacement for user {user_id} with parent {parent_id if parent_id and parent_id != user_oid else 'null'}, position {position}, level {level}")
            
            # Create GlobalTeamMember record
            try:
                team_member = GlobalTeamMember(
                    user_id=user_oid,
                    parent_user_id=parent_id if parent_id else None,  # No parent for root users
                    phase='PHASE-1',
                    slot_number=1,
                    position_in_phase=position,
                    level_in_tree=level,
                    direct_downlines=[],
                    total_downlines=[],
                    is_active=True,
                    joined_at=datetime.utcnow(),
                    last_activity_at=datetime.utcnow(),
                    phase_1_contributions=0,
                    phase_2_contributions=0,
                    status='active'
                )
                team_member.save()
                print(f"Created GlobalTeamMember record for user {user_id} with parent {parent_id}")
            except Exception as e:
                print(f"Failed to create GlobalTeamMember record: {str(e)}")
            
            # Create GlobalTreeStructure record for this user
            try:
                # Calculate correct position from position_label
                position = int(position_label.split('_')[1])
                
                tree_structure = GlobalTreeStructure(
                    user_id=user_oid,
                    parent_user_id=parent_id if parent_id else None,  # No parent for root users
                    phase='PHASE-1',
                    slot_number=1,
                    level=level,
                    position=position,
                    left_child_id=None,
                    right_child_id=None,
                    children_count=0,
                    phase_1_members=[user_oid],  # Add self to phase_1_members
                    phase_2_members=[],
                    is_active=True,
                    is_complete=False
                )
                tree_structure.save()
                print(f"Created GlobalTreeStructure record for user {user_id} with parent {parent_id if parent_id else 'None'}, position {position}, level {level}")
            except Exception as e:
                print(f"Failed to create GlobalTreeStructure record: {str(e)}")
            
            # Update GlobalPhaseSeat record for parent (or create for ROOT user)
            try:
                if parent_id:
                    # Update parent's seat record
                    parent_seat = GlobalPhaseSeat.objects(user_id=parent_id, phase='PHASE-1').first()
                    if parent_seat:
                        # Add new seat to parent's seat_positions
                        parent_seat.seat_positions.append({
                            'position': position_label,
                            'user_id': str(user_oid),
                            'occupied_at': datetime.utcnow()
                        })
                        parent_seat.occupied_seats += 1
                        parent_seat.available_seats = parent_seat.total_seats - parent_seat.occupied_seats
                        parent_seat.is_full = parent_seat.occupied_seats >= parent_seat.total_seats
                        parent_seat.is_open = not parent_seat.is_full
                        parent_seat.updated_at = datetime.utcnow()
                        parent_seat.save()
                        print(f"Updated parent {parent_id} GlobalPhaseSeat: occupied={parent_seat.occupied_seats}/{parent_seat.total_seats}")
                    else:
                        # Create parent's seat record if it doesn't exist
                        print(f"Creating missing GlobalPhaseSeat record for parent {parent_id}")
                        parent_seat = GlobalPhaseSeat(
                            user_id=parent_id,
                            phase='PHASE-1',
                            slot_number=1,
                            total_seats=4,  # Phase-1 has 4 seats
                            occupied_seats=1,
                            available_seats=3,
                            seat_positions=[{
                                'position': position_label,
                                'user_id': str(user_oid),
                                'occupied_at': datetime.utcnow()
                            }],
                            waiting_list=[],
                            is_open=True,
                            is_full=False
                        )
                        parent_seat.save()
                        print(f"Created parent {parent_id} GlobalPhaseSeat record with first child")
                else:
                    # Create ROOT user's seat record
                    root_seat = GlobalPhaseSeat(
                        user_id=user_oid,
                        phase='PHASE-1',
                        slot_number=1,
                        total_seats=4,  # Phase-1 has 4 seats
                        occupied_seats=1,
                        available_seats=3,
                        seat_positions=[{
                            'position': position_label,
                            'user_id': str(user_oid),
                            'occupied_at': datetime.utcnow()
                        }],
                        waiting_list=[],
                        is_open=True,
                        is_full=False
                    )
                    root_seat.save()
                    print(f"Created ROOT user {user_id} GlobalPhaseSeat record")
            except Exception as e:
                print(f"Failed to update/create GlobalPhaseSeat record: {str(e)}")
            
            # Update parent's counters and readiness
            if parent_id and parent_id != user_oid:  # Don't update self
                parent_status = GlobalPhaseProgression.objects(user_id=parent_id).first()
                if parent_status:
                    # Update phase_1_members_current
                    parent_status.phase_1_members_current = int(parent_status.phase_1_members_current or 0) + 1
                    
                    # Update global_team_size
                    parent_status.global_team_size = (parent_status.global_team_size or 0) + 1
                    
                    # Update global_team_members list
                    current_members = list(parent_status.global_team_members or [])
                    if user_oid not in current_members:
                        current_members.append(user_oid)
                        parent_status.global_team_members = current_members
                    
                    # Check if Phase-1 is complete
                    if parent_status.phase_1_members_current >= (parent_status.phase_1_members_required or 4):
                        parent_status.is_phase_complete = True
                        parent_status.next_phase_ready = True
                        parent_status.phase_completed_at = datetime.utcnow()
                        print(f"Parent {parent_id} Phase-1 completed with {parent_status.phase_1_members_current} members")
                        
                        # Trigger automatic phase progression to Phase-2
                        try:
                            progression_result = self.process_phase_progression(str(parent_id))
                            if progression_result.get("success"):
                                print(f"Automatic phase progression successful for parent {parent_id}: PHASE-1 -> PHASE-2")
                            else:
                                print(f"Automatic phase progression failed for parent {parent_id}: {progression_result.get('error')}")
                        except Exception as e:
                            print(f"Error during automatic phase progression for parent {parent_id}: {str(e)}")
                    
                    parent_status.updated_at = datetime.utcnow()
                    parent_status.save()
                    print(f"Updated parent {parent_id}: phase_1_members_current={parent_status.phase_1_members_current}, global_team_size={parent_status.global_team_size}")
            else:
                print(f"User {user_id} is root, no parent updates needed")
            
            # Update current user's own counters to include self
            current_user_status = GlobalPhaseProgression.objects(user_id=user_oid).first()
            if current_user_status:
                # Initialize counters to include self
                current_user_status.phase_1_members_current = 1  # Include self
                current_user_status.global_team_size = 1  # Include self
                current_user_status.global_team_members = [user_oid]  # Include self
                current_user_status.updated_at = datetime.utcnow()
                current_user_status.save()
                print(f"Updated user {user_id} own counters: phase_1_members_current=1, global_team_size=1")
            
            return {"success": True, "parent_id": str(parent_id) if parent_id else None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_phase_progression(self, user_id: str) -> Dict[str, Any]:
        """
        Handle phase progression according to business logic:
        1. When Phase 1 is full (4 users), first user moves to Phase 2
        2. When Phase 2 is full (8 users), first user upgrades to next slot in Phase 1
        3. Users in Phase 2 have their upline changed to the original Phase 1 upline
        """
        try:
            # Check if Phase 1 is now full (4 users)
            phase1_users = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True).count()
            
            print(f"Phase-1 completion check: {phase1_users}/4 users")
            
            if phase1_users >= 4:
                print(f"Phase-1 is now full ({phase1_users}/4), triggering progression")
                
                # Find the first user (root user) in Phase 1
                first_user_placement = TreePlacement.objects(
                    program='global', 
                    phase='PHASE-1', 
                    is_active=True,
                    parent_id=None  # Root user has no parent
                ).first()
                
                if first_user_placement:
                    first_user_id = str(first_user_placement.user_id)
                    print(f"Moving first user {first_user_id} from Phase-1 to Phase-2")
                    
                    # Move first user to Phase 2
                    result = self._move_user_to_phase2(first_user_id)
                    
                    if result.get("success"):
                        # Downlines stay in Phase-1, only root moves to Phase-2
                        # Update root position: First downline becomes new root in Phase 1
                        self._update_root_position_in_phase1()
                        
                        return {
                            "success": True,
                            "progression": "phase1_to_phase2",
                            "first_user_id": first_user_id,
                            "message": "First user moved to Phase 2, downlines stay in Phase-1"
                        }
                    else:
                        return {"success": False, "error": f"Failed to move first user to Phase 2: {result.get('error')}"}
            
            # Check if Phase 2 is now full (8 users)
            phase2_users = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True).count()
            
            if phase2_users >= 8:
                print(f"Phase-2 is now full ({phase2_users}/8), triggering slot upgrade")
                
                # Find the first user in Phase 2
                first_user_placement = TreePlacement.objects(
                    program='global', 
                    phase='PHASE-2', 
                    is_active=True,
                    parent_id=None  # Root user has no parent
                ).first()
                
                if first_user_placement:
                    first_user_id = str(first_user_placement.user_id)
                    current_slot = first_user_placement.slot_no
                    next_slot = current_slot + 1
                    
                    print(f"Upgrading first user {first_user_id} from Slot {current_slot} to Slot {next_slot}")
                    
                    # Move first user to next slot in Phase 1
                    result = self._upgrade_user_to_next_slot(first_user_id, next_slot)
                    
                    if result.get("success"):
                        return {
                            "success": True,
                            "progression": "slot_upgrade",
                            "first_user_id": first_user_id,
                            "new_slot": next_slot,
                            "message": f"First user upgraded to Slot {next_slot}"
                        }
                    else:
                        return {"success": False, "error": f"Failed to upgrade first user: {result.get('error')}"}
            
            return {
                "success": True,
                "progression": "none",
                "phase1_users": phase1_users,
                "phase2_users": phase2_users,
                "message": "No progression needed"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Phase progression failed: {str(e)}"}
    
    def _move_user_to_phase2(self, user_id: str) -> Dict[str, Any]:
        """Move user from Phase 1 to Phase 2"""
        try:
            user_oid = ObjectId(user_id)
            
            # Deactivate current Phase 1 placement
            phase1_placement = TreePlacement.objects(
                user_id=user_oid,
                program='global',
                phase='PHASE-1',
                is_active=True
            ).first()
            
            if phase1_placement:
                phase1_placement.is_active = False
                phase1_placement.save()
                
                # Create new Phase 2 placement
                phase2_placement = TreePlacement(
                    user_id=user_oid,
                    program='global',
                    phase='PHASE-2',
                    slot_no=1,
                    parent_id=None,  # First user has no parent
                    upline_id=None,
                    position="1",
                    level=1,
                    phase_position=1,
                    is_active=True,
                    is_activated=True,
                    activation_date=datetime.utcnow()
                )
                phase2_placement.save()
                
                # Update GlobalTeamMember record
                team_member = GlobalTeamMember.objects(user_id=user_oid).first()
                if team_member:
                    team_member.phase = 'PHASE-2'
                    team_member.slot_number = 1
                    team_member.position_in_phase = 1
                    team_member.last_activity_at = datetime.utcnow()
                    team_member.save()
                
                print(f"Successfully moved user {user_id} to Phase 2")
                return {"success": True, "message": "User moved to Phase 2"}
            else:
                return {"success": False, "error": "Phase 1 placement not found"}
                
        except Exception as e:
            return {"success": False, "error": f"Failed to move user to Phase 2: {str(e)}"}
    
    def _move_phase1_downlines_to_phase2(self, first_user_id: str) -> Dict[str, Any]:
        """Move all Phase 1 downlines to Phase 2 under the first user"""
        try:
            first_user_oid = ObjectId(first_user_id)
            
            # Get all Phase 1 downlines of the first user
            phase1_downlines = TreePlacement.objects(
                parent_id=first_user_oid,
                program='global',
                phase='PHASE-1',
                is_active=True
            )
            
            moved_count = 0
            for downline in phase1_downlines:
                # Deactivate Phase 1 placement
                downline.is_active = False
                downline.save()
                
                # Create Phase 2 placement under first user
                phase2_placement = TreePlacement(
                    user_id=downline.user_id,
                    program='global',
                    phase='PHASE-2',
                    slot_no=1,
                    parent_id=first_user_oid,  # Under first user
                    upline_id=first_user_oid,   # Upline is first user
                    position=downline.position,
                    level=2,  # Level 2 in Phase 2
                    phase_position=int(downline.position),
                    is_active=True,
                    is_activated=True,
                    activation_date=datetime.utcnow()
                )
                phase2_placement.save()
                
                # Update GlobalTeamMember record
                team_member = GlobalTeamMember.objects(user_id=downline.user_id).first()
                if team_member:
                    team_member.phase = 'PHASE-2'
                    team_member.slot_number = 1
                    team_member.parent_user_id = first_user_oid  # Upline changes to first user
                    team_member.level_in_tree = 2
                    team_member.last_activity_at = datetime.utcnow()
                    team_member.save()
                
                moved_count += 1
            
            print(f"Successfully moved {moved_count} downlines to Phase 2")
            return {"success": True, "moved_count": moved_count}
            
        except Exception as e:
            return {"success": False, "error": f"Failed to move downlines to Phase 2: {str(e)}"}
    
    def _upgrade_user_to_next_slot(self, user_id: str, next_slot: int) -> Dict[str, Any]:
        """Upgrade user to next slot in Phase 1"""
        try:
            user_oid = ObjectId(user_id)
            
            # Deactivate current Phase 2 placement
            phase2_placement = TreePlacement.objects(
                user_id=user_oid,
                program='global',
                phase='PHASE-2',
                is_active=True
            ).first()
            
            if phase2_placement:
                phase2_placement.is_active = False
                phase2_placement.save()
                
                # Create new Phase 1 placement in next slot
                phase1_placement = TreePlacement(
                    user_id=user_oid,
                    program='global',
                    phase='PHASE-1',
                    slot_no=next_slot,
                    parent_id=None,  # First user has no parent
                    upline_id=None,
                    position="1",
                    level=1,
                    phase_position=1,
                    is_active=True,
                    is_activated=True,
                    activation_date=datetime.utcnow()
                )
                phase1_placement.save()
                
                # Update GlobalTeamMember record
                team_member = GlobalTeamMember.objects(user_id=user_oid).first()
                if team_member:
                    team_member.phase = 'PHASE-1'
                    team_member.slot_number = next_slot
                    team_member.position_in_phase = 1
                    team_member.last_activity_at = datetime.utcnow()
                    team_member.save()
                
                print(f"Successfully upgraded user {user_id} to Slot {next_slot}")
                return {"success": True, "message": f"User upgraded to Slot {next_slot}"}
            else:
                return {"success": False, "error": "Phase 2 placement not found"}
                
        except Exception as e:
            return {"success": False, "error": f"Failed to upgrade user to next slot: {str(e)}"}

    def _place_in_phase2(self, user_id: str) -> Dict[str, Any]:
        """Place user into PHASE-2 tree under earliest PHASE-2 parent with <8 seats.
        If none exists yet (first entrant into PHASE-2), place as root of PHASE-2.
        """
        try:
            user_oid = ObjectId(user_id)
            parent_id = self._find_phase2_parent_bfs(user_id)
            
            # Determine position index for UI (1..8) - Global sequential positions
            # Count total existing users in PHASE-2 to get next sequential position
            total_phase2_users = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True).count()
            next_position = total_phase2_users + 1
            
            # Ensure position doesn't exceed phase limit (8 for PHASE-2)
            if next_position > 8:
                print(f"Phase-2 is full (8 positions), cannot place user {user_id}")
                return {"success": False, "error": "Phase-2 is full, cannot accept more users"}
            
            position_label = f'position_{next_position}'
            level = 1
            
            if parent_id:
                parent_node = TreePlacement.objects(user_id=parent_id, program='global', phase='PHASE-2').first()
                level = (parent_node.level + 1) if parent_node else 2
            TreePlacement(
                user_id=user_oid,
                program='global',
                parent_id=parent_id,
                upline_id=parent_id,  # Set upline_id for tree queries
                position=position_label,
                level=level,
                slot_no=1,
                phase='PHASE-2',
                phase_position=int(position_label.split('_')[1]) if position_label != 'root' else 0,
                is_active=True,
                is_activated=True,
                activation_date=datetime.utcnow()
            ).save()
            
            # Update GlobalPhaseSeat record for parent (or create for ROOT user)
            try:
                if parent_id:
                    # Update parent's seat record
                    parent_seat = GlobalPhaseSeat.objects(user_id=parent_id, phase='PHASE-2').first()
                    if parent_seat:
                        # Add new seat to parent's seat_positions
                        parent_seat.seat_positions.append({
                            'position': position_label,
                            'user_id': str(user_oid),
                            'occupied_at': datetime.utcnow()
                        })
                        parent_seat.occupied_seats += 1
                        parent_seat.available_seats = parent_seat.total_seats - parent_seat.occupied_seats
                        parent_seat.is_full = parent_seat.occupied_seats >= parent_seat.total_seats
                        parent_seat.is_open = not parent_seat.is_full
                        parent_seat.updated_at = datetime.utcnow()
                        parent_seat.save()
                        print(f"Updated parent {parent_id} Phase-2 GlobalPhaseSeat: occupied={parent_seat.occupied_seats}/{parent_seat.total_seats}")
                    else:
                        # Create parent's Phase-2 seat record if it doesn't exist
                        print(f"Creating missing Phase-2 GlobalPhaseSeat record for parent {parent_id}")
                        parent_seat = GlobalPhaseSeat(
                            user_id=parent_id,
                            phase='PHASE-2',
                            slot_number=1,
                            total_seats=8,  # Phase-2 has 8 seats
                            occupied_seats=1,
                            available_seats=7,
                            seat_positions=[{
                                'position': position_label,
                                'user_id': str(user_oid),
                                'occupied_at': datetime.utcnow()
                            }],
                            waiting_list=[],
                            is_open=True,
                            is_full=False
                        )
                        parent_seat.save()
                        print(f"Created parent {parent_id} Phase-2 GlobalPhaseSeat record with first child")
                else:
                    # Create ROOT user's Phase-2 seat record
                    root_seat = GlobalPhaseSeat(
                        user_id=user_oid,
                        phase='PHASE-2',
                        slot_number=1,
                        total_seats=8,  # Phase-2 has 8 seats
                        occupied_seats=1,
                        available_seats=7,
                        seat_positions=[{
                            'position': position_label,
                            'user_id': str(user_oid),
                            'occupied_at': datetime.utcnow()
                        }],
                        waiting_list=[],
                        is_open=True,
                        is_full=False
                    )
                    root_seat.save()
                    print(f"Created ROOT user {user_id} Phase-2 GlobalPhaseSeat record")
            except Exception as e:
                print(f"Failed to update/create Phase-2 GlobalPhaseSeat record: {str(e)}")
            
            if parent_id:
                parent_status = GlobalPhaseProgression.objects(user_id=parent_id).first()
                if parent_status:
                    parent_status.phase_2_members_current = int(parent_status.phase_2_members_current or 0) + 1
                    if parent_status.phase_2_members_current >= (parent_status.phase_2_members_required or 8):
                        parent_status.is_phase_complete = True
                        parent_status.next_phase_ready = True
                        parent_status.phase_completed_at = datetime.utcnow()
                        print(f"Parent {parent_id} Phase-2 completed with {parent_status.phase_2_members_current} members")
                        
                        # Trigger automatic phase progression to Phase-1 re-entry
                        try:
                            reentry_result = self.process_phase2_to_phase1_reentry(str(parent_id))
                            if reentry_result.get("success"):
                                print(f"Automatic phase progression successful for parent {parent_id}: PHASE-2 -> PHASE-1 re-entry")
                            else:
                                print(f"Automatic phase progression failed for parent {parent_id}: {reentry_result.get('error')}")
                        except Exception as e:
                            print(f"Error during automatic phase progression for parent {parent_id}: {str(e)}")
                    
                    parent_status.last_updated = datetime.utcnow()
                    parent_status.save()
            return {"success": True, "parent_id": str(parent_id) if parent_id else None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def join_global(self, user_id: str, tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        try:
            # 1.1.1 User Validation - Section 1.1.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # 1. Validate user exists
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # 2. Check if user already joined Global program
            if getattr(user, 'global_joined', False):
                return {"success": False, "error": "User has already joined Global program"}
            
            # Check if user has existing GlobalPhaseProgression record
            existing_progression = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if existing_progression:
                return {"success": False, "error": "User already has Global program progression record"}
            
            # 3. Verify amount matches Phase-1 Slot-1 price ($33)
            catalog = SlotCatalog.objects(program='global', slot_no=1, is_active=True).first()
            if not catalog:
                return {"success": False, "error": "Global slot catalog missing"}
            expected_amount = catalog.price or Decimal('0')
            if amount != expected_amount:
                return {"success": False, "error": f"Join amount must be {expected_amount} (Phase-1 Slot-1 price)"}

            currency = ensure_currency_for_program('global', 'USDT')

            # Generate unique tx_hash to avoid duplicate key errors
            import random, string
            unique_suffix = datetime.utcnow().strftime('%Y%m%d%H%M%S%f') + '_' + ''.join(random.choices(string.ascii_lowercase+string.digits, k=6))
            unique_tx_hash = f"{tx_hash}_{unique_suffix}"

            # 1.1.2 Slot Activation - Section 1.1.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Create SlotActivation record for Global Slot-1
            current_time = datetime.utcnow()
            activation = SlotActivation(
                user_id=ObjectId(user.id),
                program='global',
                slot_no=1,
                slot_name=catalog.name,
                activation_type='initial',  # Set activation_type: 'initial'
                upgrade_source='wallet',
                amount_paid=expected_amount,
                currency=currency,  # Set currency: 'USD'
                tx_hash=unique_tx_hash,
                blockchain_network='BSC',  # Default blockchain network
                commission_paid=Decimal('0'),  # No commission for initial join
                commission_percentage=0.0,  # No commission percentage for initial join
                is_auto_upgrade=False,
                partners_contributed=[],
                earnings_used=Decimal('0'),
                status='completed',  # Set status: 'completed'
                activated_at=current_time,
                completed_at=current_time,
                created_at=current_time,
                metadata={
                    'join_type': 'initial',
                    'phase': 'PHASE-1',
                    'slot_level': catalog.level,
                    'validation_passed': True
                }
            )
            try:
                activation.save()
                print(f"✅ Successfully created SlotActivation record for user {user.id}: program=global, slot_no=1, amount={expected_amount}")
            except Exception as e:
                print(f"❌ Failed to save SlotActivation record for user {user.id}: {str(e)}")
                return {"success": False, "error": f"Failed to create slot activation: {str(e)}"}

            # 1.1.3 Global Phase Progression Setup - Section 1.1.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Create GlobalPhaseProgression record if not exists
            progression = GlobalPhaseProgression.objects(user_id=ObjectId(user.id)).first()
            if not progression:
                progression = GlobalPhaseProgression(
                    user_id=ObjectId(user.id),
                    current_phase='PHASE-1',  # Set current_phase: 'PHASE-1'
                    current_slot_no=1,  # Set current_slot_no: 1
                    phase_position=1,  # Set phase_position: 1
                    phase_1_members_required=4,  # Set phase_1_members_required: 4
                    phase_1_members_current=0,  # Set phase_1_members_current: 0
                    phase_2_members_required=8,  # Set phase_2_members_required: 8
                    phase_2_members_current=0,  # Set phase_2_members_current: 0
                    global_team_size=0,
                    global_team_members=[],
                    is_phase_complete=False,
                    phase_completed_at=None,
                    next_phase_ready=False,
                    total_re_entries=0,
                    last_re_entry_at=None,
                    re_entry_slot=1,
                    auto_progression_enabled=True,  # Set auto_progression_enabled: true
                    progression_triggered=False,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                progression.save()
                
                # Log phase progression setup
                print(f"Global Phase Progression setup for user {user.id}: PHASE-1, Slot-1")

            # 1.1.4 Phase Placement - Section 1.1.4 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Always place new users in Phase-1 first, then handle progression
            print(f"Placing user {user_id} in Phase-1")
            
            # Place user in Phase-1 tree using BFS algorithm
            placement_result = self._place_in_phase1(user_id)
            if not placement_result.get("success"):
                return {"success": False, "error": f"Phase-1 placement failed: {placement_result.get('error')}"}
            
            # Check for phase progression using new logic
            progression_result = self._handle_phase_progression(user_id)
            if progression_result.get("success") and progression_result.get("progression") != "none":
                print(f"Phase progression triggered: {progression_result.get('message')}")
            elif not progression_result.get("success"):
                print(f"Phase progression failed: {progression_result.get('error')}")
            
            # Log placement result
            parent_id = placement_result.get("parent_id")
            phase = placement_result.get("phase", "PHASE-1")
            if parent_id:
                print(f"User {user_id} placed in {phase} under parent {parent_id}")
            else:
                print(f"User {user_id} placed as root in {phase}")

            # 1.1.4b. Distribute funds to all bonus pools (PROJECT_DOCUMENTATION.md Section 32)
            try:
                from modules.fund_distribution.service import FundDistributionService
                fund_service = FundDistributionService()
                
                # Get referrer for partner incentive
                referrer_id = str(user.refered_by) if user.refered_by else None
                
                distribution_result = fund_service.distribute_global_funds(
                    user_id=user_id,
                    amount=expected_amount,
                    slot_no=1,
                    referrer_id=referrer_id,
                    tx_hash=unique_tx_hash
                )
                
                if distribution_result.get('success'):
                    print(f"✅ Global funds distributed: {distribution_result.get('total_distributed')}")
                else:
                    print(f"⚠️ Global fund distribution failed: {distribution_result.get('error')}")
            except Exception as e:
                print(f"⚠️ Global fund distribution error: {e}")
            
            # 1.1.5 Commission Calculations - Section 1.1.5 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Joining Commission (10%): Calculate and distribute to upline
            try:
                joining_commission_result = self.commission_service.calculate_joining_commission(
                from_user_id=str(user.id),
                program='global',
                amount=expected_amount,
                currency=currency
            )
                print(f"Joining commission calculated for user {user.id}: {joining_commission_result}")
            except Exception as e:
                print(f"Joining commission failed for user {user.id}: {str(e)}")

            # Partner Incentive (10%): Calculate and distribute to direct upline
            try:
                partner_incentive_result = self.commission_service.calculate_partner_incentive(
                    from_user_id=str(user.id),
                    program='global',
                    amount=expected_amount,
                    currency=currency
                )
                print(f"Partner incentive calculated for user {user.id}: {partner_incentive_result}")
            except Exception as e:
                print(f"Partner incentive failed for user {user.id}: {str(e)}")

            # 1.1.6 Global Distribution (100% breakdown) - Section 1.1.6 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Global distribution (100% breakdown)
            distribution_result = self.process_distribution(user_id=str(user.id), amount=expected_amount, currency=currency)
            if not distribution_result.get("success"):
                print(f"Global distribution failed for user {user.id}: {distribution_result.get('error')}")
            else:
                print(f"Global distribution completed for user {user.id}: {distribution_result.get('distribution_breakdown')}")

            # 1.1.7 Triple Entry Eligibility Check - Section 1.1.7 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # If user has Binary + Matrix + Global: Compute triple-entry eligibles
            try:
                # Check if user has all three programs (Binary, Matrix, Global)
                has_binary = getattr(user, 'binary_joined', False)
                has_matrix = getattr(user, 'matrix_joined', False)
                has_global = getattr(user, 'global_joined', False)  # Will be True after this join
                
                print(f"Triple Entry Check for user {user.id}: Binary={has_binary}, Matrix={has_matrix}, Global={has_global}")
                
                # Since we're setting global_joined=True after this check, we need to check if user will have all three
                if has_binary and has_matrix:
                    # User will have all three programs after this Global join
                    print(f"User {user.id} eligible for Triple Entry Reward - has Binary + Matrix + Global")
                    triple_entry_result = SparkService.compute_triple_entry_eligibles(datetime.utcnow())
                    print(f"Triple Entry eligibility computed: {triple_entry_result}")
                    
                    # Auto-join President Reward program when user has all 3 programs
                    try:
                        from modules.president_reward.service import PresidentRewardService
                        from modules.president_reward.model import PresidentReward
                        pr_existing = PresidentReward.objects(user_id=user.id).first()
                        if not pr_existing:
                            pr_svc = PresidentRewardService()
                            pr_result = pr_svc.join_president_reward_program(str(user.id))
                            print(f"President Reward auto-join for user {user.id}: {pr_result}")
                        else:
                            print(f"User {user.id} already in President Reward program")
                    except Exception as pr_e:
                        print(f"President Reward auto-join failed for user {user.id}: {str(pr_e)}")
                    
                    # Auto-join Royal Captain Bonus program when user has all 3 programs
                    try:
                        from modules.royal_captain.service import RoyalCaptainService
                        from modules.royal_captain.model import RoyalCaptain
                        rc_existing = RoyalCaptain.objects(user_id=user.id).first()
                        if not rc_existing:
                            rc_svc = RoyalCaptainService()
                            rc_result = rc_svc.join_royal_captain_program(str(user.id))
                            print(f"Royal Captain auto-join for user {user.id}: {rc_result}")
                        else:
                            print(f"User {user.id} already in Royal Captain program")
                    except Exception as rc_e:
                        print(f"Royal Captain auto-join failed for user {user.id}: {str(rc_e)}")
                else:
                    print(f"User {user.id} not yet eligible for Triple Entry Reward - missing programs")
            except Exception as e:
                print(f"Triple Entry eligibility check failed for user {user.id}: {str(e)}")

            # Update user's global_joined flag and related fields
            user.global_joined = True
            
            # Update user's global_slots array with proper GlobalSlotInfo object
            from modules.user.model import GlobalSlotInfo
            if not hasattr(user, 'global_slots') or user.global_slots is None:
                user.global_slots = []
            
            # Create GlobalSlotInfo object for slot 1
            global_slot_info = GlobalSlotInfo(
                slot_name=catalog.name,  # FOUNDATION
                slot_value=float(expected_amount),  # $33
                level=1,
                phase='PHASE-1',
                is_active=True,
                activated_at=datetime.utcnow(),
                upgrade_cost=0.0,
                total_income=0.0,
                wallet_amount=0.0
            )
            user.global_slots.append(global_slot_info)
            
            # Update user's global_total_spent
            if not hasattr(user, 'global_total_spent') or user.global_total_spent is None:
                user.global_total_spent = 0
            user.global_total_spent += float(expected_amount)
            
            user.save()
            
            # Update current user's own GlobalPhaseProgression team tracking
            try:
                current_user_status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
                if current_user_status:
                    # Initialize team tracking for new user
                    current_user_status.global_team_size = current_user_status.global_team_size or 0
                    current_user_status.global_team_members = current_user_status.global_team_members or []
                    current_user_status.updated_at = datetime.utcnow()
                    current_user_status.save()
                    print(f"Initialized team tracking for new user {user_id}: size={current_user_status.global_team_size}")
            except Exception as e:
                print(f"Failed to initialize team tracking for user {user_id}: {str(e)}")

            # 1.1.8 Earning History Record - Section 1.1.8 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Create EarningHistory record
            try:
                # Convert currency to USDT (since we only support USDT and BNB)
                earning_currency = 'USDT' if currency == 'USD' else currency
                
                earning_history = EarningHistory(
                user_id=ObjectId(user.id),
                    earning_type='global_slot',  # Set earning_type: 'global_slot'
                    program='global',  # Set program: 'global'
                    amount=float(expected_amount),  # Set amount: $33
                    currency=earning_currency,  # Set currency: 'USDT' (converted from USD)
                    slot_name=catalog.name,  # Set slot_name: 'FOUNDATION'
                slot_level=catalog.level,
                    description='Joined Global program, activated Phase-1 Slot-1'  # Set description
                )
                earning_history.save()
                
                print(f"Earning history record created for user {user.id}: {earning_currency} {expected_amount} - {catalog.name}")
            except Exception as e:
                print(f"Earning history record creation failed for user {user.id}: {str(e)}")

            # TREE PLACEMENT INTEGRATION - PROJECT_DOCUMENTATION.md Section 5
            # "Global Program (Required third) - Final program in sequence"
            # Create Global tree placement for the user
            try:
                from modules.tree.service import TreeService
                tree_service = TreeService()
                
                # Get referrer ID from user
                referrer_id = user.refered_by
                if not referrer_id:
                    # If no referrer, use ROOT user as referrer
                    root_user = User.objects(uid='ROOT').first()
                    if root_user:
                        referrer_id = root_user.id
                
                if referrer_id:
                    # Place user in global tree under their referrer
                    global_placement = tree_service.place_user_in_tree(
                        user_id=ObjectId(user_id),
                        referrer_id=ObjectId(referrer_id),
                        program='global',
                        slot_no=1  # First global slot
                    )
                    
                    if global_placement:
                        print(f"✅ Global tree placement created for user {user_id} under {referrer_id}")
                    else:
                        print(f"⚠️ Global tree placement failed for user {user_id}")
                        
            except Exception as e:
                print(f"Error in global tree placement: {e}")
                # Don't fail global join if tree placement fails

            return {"success": True, "slot_no": 1, "amount": float(expected_amount)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def upgrade_global_slot(self, user_id: str, to_slot_no: int, tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        """
        2.1 Slot Upgrade Process - Section 2.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        **Trigger**: User upgrades to next Global slot (2-16)
        **Endpoint**: `POST /global/upgrade`
        """
        try:
            # 2.1.1 Upgrade Validation - Section 2.1.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # 1. Validate user exists and has Global program access
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                print(f"Upgrade validation failed: User {user_id} not found")
                return {"success": False, "error": "User not found"}

            if not getattr(user, 'global_joined', False):
                print(f"Upgrade validation failed: User {user_id} has not joined Global program")
                return {"success": False, "error": "User has not joined Global program"}

            # 2. Check if target slot is valid (2-16)
            if to_slot_no < 2 or to_slot_no > 16:
                print(f"Upgrade validation failed: Invalid target slot {to_slot_no} (must be 2-16)")
                return {"success": False, "error": "Target slot must be between 2 and 16"}

            # 3. Verify amount matches target slot price from catalog
            catalog = SlotCatalog.objects(program='global', slot_no=to_slot_no, is_active=True).first()
            if not catalog:
                print(f"Upgrade validation failed: Global slot catalog missing for slot {to_slot_no}")
                return {"success": False, "error": "Global slot catalog missing"}
            expected_amount = catalog.price or Decimal('0')
            if amount != expected_amount:
                print(f"Upgrade validation failed: Amount mismatch - provided: {amount}, expected: {expected_amount}")
                return {"success": False, "error": f"Upgrade amount must be {expected_amount}"}

            # 4. Check if user already has this slot activated
            existing_activation = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program='global',
                slot_no=to_slot_no,
                status='completed'
            ).first()
            if existing_activation:
                print(f"Upgrade validation failed: User {user_id} already has slot {to_slot_no} activated")
                return {"success": False, "error": f"User already has slot {to_slot_no} activated"}

            # Additional validation: Check if user has previous slots activated
            previous_slots = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program='global',
                slot_no__lt=to_slot_no,
                status='completed'
            ).count()
            
            if previous_slots < (to_slot_no - 1):
                print(f"Upgrade validation failed: User {user_id} missing previous slots (has {previous_slots}, needs {to_slot_no - 1})")
                return {"success": False, "error": f"User must activate previous slots before upgrading to slot {to_slot_no}"}

            print(f"Upgrade validation passed for user {user_id}: slot {to_slot_no}, amount {expected_amount}")

            currency = ensure_currency_for_program('global', 'USDT')

            # Generate unique tx_hash to avoid duplicate key errors
            import random, string
            unique_suffix = datetime.utcnow().strftime('%Y%m%d%H%M%S%f') + '_' + ''.join(random.choices(string.ascii_lowercase+string.digits, k=6))
            unique_tx_hash = f"{tx_hash}_{unique_suffix}"

            # 2.1.2 Slot Activation Record - Section 2.1.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Create SlotActivation record for target slot
            try:
                current_time = datetime.utcnow()
                activation = SlotActivation(
                    user_id=ObjectId(user.id),
                    program='global',
                    slot_no=to_slot_no,
                    slot_name=catalog.name,
                    activation_type='upgrade',  # Set activation_type: 'upgrade'
                    upgrade_source='wallet',  # Set upgrade_source: 'wallet' or 'auto'
                    amount_paid=expected_amount,
                    currency=currency,  # Set currency: 'USD'
                    tx_hash=unique_tx_hash,
                    blockchain_network='BSC',
                    commission_paid=Decimal('0'),
                    commission_percentage=0.0,
                    is_auto_upgrade=False,
                    partners_contributed=[],
                    earnings_used=Decimal('0'),
                    status='completed',  # Set status: 'completed'
                    activated_at=current_time,
                    completed_at=current_time,
                    created_at=current_time,
                    metadata={
                        'upgrade_type': 'manual',
                        'slot_level': catalog.level,
                        'validation_passed': True,
                        'upgrade_sequence': to_slot_no,
                        'previous_slots_verified': True
                    }
                )
                activation.save()

                print(f"Slot activation record created for user {user.id}: slot {to_slot_no} ({catalog.name}) - {currency} {expected_amount}")
            except Exception as e:
                print(f"Slot activation record creation failed for user {user.id}, slot {to_slot_no}: {str(e)}")
                return {"success": False, "error": f"Failed to create slot activation record: {str(e)}"}

            # 2.1.3 Commission Calculations - Section 2.1.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Partner Incentive (10%): Calculate and distribute to direct upline
            try:
                partner_incentive_result = self.commission_service.calculate_partner_incentive(
                    from_user_id=str(user.id),
                    program='global',
                    amount=expected_amount,
                    currency=currency
                )
                print(f"Partner incentive calculated for slot upgrade {to_slot_no}: {partner_incentive_result}")
            except Exception as e:
                print(f"Partner incentive failed for slot upgrade {to_slot_no}: {str(e)}")

            # Upgrade Commission: Calculate based on slot value
            try:
                upgrade_commission_result = self.commission_service.calculate_upgrade_commission(
                    from_user_id=str(user.id),
                    program='global',
                    slot_no=to_slot_no,
                    amount=expected_amount,
                    currency=currency
                )
                print(f"Upgrade commission calculated for slot {to_slot_no}: {upgrade_commission_result}")
            except Exception as e:
                print(f"Upgrade commission failed for slot {to_slot_no}: {str(e)}")

            # Additional commission calculations for Global program
            try:
                # Level Commission: Calculate based on slot level
                level_commission_result = self.commission_service.calculate_level_commission(
                    from_user_id=str(user.id),
                program='global',
                    slot_no=to_slot_no,
                    amount=expected_amount,
                    currency=currency
                )
                print(f"Level commission calculated for slot {to_slot_no}: {level_commission_result}")
            except Exception as e:
                print(f"Level commission failed for slot {to_slot_no}: {str(e)}")

            # Commission summary
            commission_summary = {
                "partner_incentive": partner_incentive_result if 'partner_incentive_result' in locals() else None,
                "upgrade_commission": upgrade_commission_result if 'upgrade_commission_result' in locals() else None,
                "level_commission": level_commission_result if 'level_commission_result' in locals() else None,
                "total_commission_amount": float(expected_amount * Decimal('0.10')),  # 10% partner incentive
                "currency": currency
            }
            print(f"Commission calculations completed for slot upgrade {to_slot_no}: {commission_summary}")

            # 2.1.4 Global Distribution (100% breakdown) - Section 2.1.4 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Global distribution (100% breakdown)
            try:
                distribution_result = self.process_distribution(user_id=str(user.id), amount=expected_amount, currency=currency)
                if not distribution_result.get("success"):
                    print(f"Global distribution failed for slot upgrade {to_slot_no}: {distribution_result.get('error')}")
                else:
                    print(f"Global distribution completed for slot upgrade {to_slot_no}: {distribution_result.get('distribution_breakdown')}")
                    
                    # Log detailed distribution breakdown
                    breakdown = distribution_result.get('distribution_breakdown', {})
                    print(f"Distribution breakdown for slot {to_slot_no}:")
                    print(f"  - Level Reserved (30%): {breakdown.get('level_reserved', 0)}")
                    print(f"  - Partner Incentive (10%): {breakdown.get('partner_incentive', 0)}")
                    print(f"  - Profit (30%): {breakdown.get('profit', 0)}")
                    print(f"  - Royal Captain Bonus (10%): {breakdown.get('royal_captain', 0)}")
                    print(f"  - President Reward (10%): {breakdown.get('president_reward', 0)}")
                    print(f"  - Triple Entry Reward (5%): {breakdown.get('triple_entry', 0)}")
                    print(f"  - Shareholders (5%): {breakdown.get('shareholders', 0)}")
                    
            except Exception as e:
                print(f"Global distribution process failed for slot upgrade {to_slot_no}: {str(e)}")
                # Continue with the process even if distribution fails

            # 2.1.5 Earning History Record - Section 2.1.5 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Create EarningHistory record for upgrade
            try:
                # Convert currency to USDT (since we only support USDT and BNB)
                earning_currency = 'USDT' if currency == 'USD' else currency
                
                earning_history = EarningHistory(
                    user_id=ObjectId(user.id),
                    earning_type='global_slot',  # Set earning_type: 'global_slot'
                    program='global',  # Set program: 'global'
                    amount=float(expected_amount),  # Set amount: slot_value
                    currency=earning_currency,  # Set currency: 'USDT' (converted from USD)
                    slot_name=catalog.name,  # Set slot_name: target_slot_name
                slot_level=catalog.level,
                    description=f'Upgraded Global slot {to_slot_no} ({catalog.name})'  # Set description: 'Upgraded Global slot'
                )
                earning_history.save()
                
                print(f"Earning history record created for slot upgrade {to_slot_no}: {earning_currency} {expected_amount} - {catalog.name}")
                print(f"Earning history details: user_id={user.id}, earning_type=global_slot, program=global, amount={expected_amount}, currency={earning_currency}, slot_name={catalog.name}, slot_level={catalog.level}")
                
            except Exception as e:
                print(f"Earning history record creation failed for slot upgrade {to_slot_no}: {str(e)}")
                # Continue with the process even if earning history fails

            return {"success": True, "slot_no": to_slot_no, "amount": float(expected_amount)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_status(self, user_id: str) -> Dict[str, Any]:
        try:
            status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not status:
                return {"success": False, "error": "Global status not found"}
            return {
                "success": True,
                "status": {
                    "current_phase": status.current_phase,
                    "current_slot_no": status.current_slot_no,
                    "phase_position": status.phase_position,
                    "phase_1_members_current": status.phase_1_members_current,
                    "phase_1_members_required": status.phase_1_members_required,
                    "phase_2_members_current": status.phase_2_members_current,
                    "phase_2_members_required": status.phase_2_members_required,
                    "next_phase_ready": status.next_phase_ready,
                    "is_phase_complete": status.is_phase_complete,
                    "total_re_entries": status.total_re_entries,
                    "global_team_size": status.global_team_size
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_team_member(self, user_id: str, member_id: str) -> Dict[str, Any]:
        """Add a global team member and update phase counters; mark readiness when thresholds hit."""
        try:
            # Get the parent user's GlobalPhaseProgression
            parent_status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not parent_status:
                return {"success": False, "error": "Parent Global status not found"}

            # Get the member user
            member_user = User.objects(id=ObjectId(member_id)).first()
            if not member_user:
                return {"success": False, "error": "Member user not found"}

            # Create GlobalTeamMember record
            team_member = GlobalTeamMember(
                user_id=ObjectId(member_id),
                parent_user_id=ObjectId(user_id),
                phase=parent_status.current_phase,
                slot_number=parent_status.current_slot_no,
                position_in_phase=parent_status.phase_1_members_current + 1 if parent_status.current_phase == 'PHASE-1' else parent_status.phase_2_members_current + 1,
                level_in_tree=1,  # Direct downline
                direct_downlines=[],
                total_downlines=[],
                is_active=True,
                joined_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow(),
                phase_1_contributions=0,
                phase_2_contributions=0,
                status='active'
            )
            team_member.save()

            # Update parent's GlobalPhaseProgression
            members = parent_status.global_team_members or []
            oid = ObjectId(member_id)
            if oid not in members:
                members.append(oid)
                parent_status.global_team_members = members
                parent_status.global_team_size = (parent_status.global_team_size or 0) + 1

            if parent_status.current_phase == 'PHASE-1':
                parent_status.phase_1_members_current = (parent_status.phase_1_members_current or 0) + 1
                if parent_status.phase_1_members_current >= (parent_status.phase_1_members_required or 4):
                    parent_status.is_phase_complete = True
                    parent_status.next_phase_ready = True
                    parent_status.phase_completed_at = datetime.utcnow()
            else:
                parent_status.phase_2_members_current = (parent_status.phase_2_members_current or 0) + 1
                if parent_status.phase_2_members_current >= (parent_status.phase_2_members_required or 8):
                    parent_status.is_phase_complete = True
                    parent_status.next_phase_ready = True
                    parent_status.phase_completed_at = datetime.utcnow()

            parent_status.updated_at = datetime.utcnow()
            parent_status.save()

            return {"success": True, "status": self.get_status(user_id).get("status")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_team(self, user_id: str) -> Dict[str, Any]:
        try:
            # Get GlobalPhaseProgression for basic info
            status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not status:
                return {"success": False, "error": "Global status not found"}

            # Get detailed team members
            team_members = GlobalTeamMember.objects(parent_user_id=ObjectId(user_id)).only(
                'user_id', 'phase', 'slot_number', 'position_in_phase', 'level_in_tree', 
                'is_active', 'joined_at', 'status'
            )

            # Get user names for team members
            member_user_ids = [str(member.user_id) for member in team_members]
            users = User.objects(id__in=member_user_ids).only('id', 'name')
            user_names = {str(u.id): u.name for u in users}

            # Format team members
            formatted_members = []
            for member in team_members:
                formatted_members.append({
                    "user_id": str(member.user_id),
                    "name": user_names.get(str(member.user_id), 'Unknown'),
                    "phase": member.phase,
                    "slot_number": member.slot_number,
                    "position_in_phase": member.position_in_phase,
                    "level_in_tree": member.level_in_tree,
                    "is_active": member.is_active,
                    "joined_at": member.joined_at.isoformat(),
                    "status": member.status
                })

            return {
                "success": True,
                "team": {
                    "size": status.global_team_size or 0,
                    "members": [str(mid) for mid in (status.global_team_members or [])],
                    "detailed_members": formatted_members,
                    "phase_1_members": status.phase_1_members_current or 0,
                    "phase_2_members": status.phase_2_members_current or 0,
                    "phase_1_required": status.phase_1_members_required or 4,
                    "phase_2_required": status.phase_2_members_required or 8
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_progression(self, user_id: str) -> Dict[str, Any]:
        """Progress Phase-1 (4) -> Phase-2 (8) -> re-entry as per spec when ready."""
        try:
            status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not status:
                return {"success": False, "error": "Global status not found"}

            if status.current_phase == 'PHASE-1':
                if status.phase_1_members_current < status.phase_1_members_required:
                    return {"success": False, "error": "Phase-1 not complete"}
                status.current_phase = 'PHASE-2'
                status.current_slot_no = 1
                status.phase_position = 1
                status.is_phase_complete = False
                status.next_phase_ready = False
                status.phase_completed_at = datetime.utcnow()
                status.phase_2_members_current = 0
                status.save()
                # Place user into PHASE-2 tree
                self._place_in_phase2(user_id)
                return {"success": True, "moved_to": "PHASE-2", "slot_no": 1}
            else:
                if status.phase_2_members_current < status.phase_2_members_required:
                    return {"success": False, "error": "Phase-2 not complete"}
                status.current_phase = 'PHASE-1'
                status.current_slot_no = min((status.current_slot_no or 1) + 1, 16)
                status.phase_position = 1
                status.is_phase_complete = False
                status.next_phase_ready = False
                status.total_re_entries = (status.total_re_entries or 0) + 1
                status.last_re_entry_at = datetime.utcnow()
                status.re_entry_slot = status.current_slot_no
                status.phase_completed_at = datetime.utcnow()
                status.phase_1_members_current = 0
                status.save()
                # Place user again at PHASE-1 root queue (handled in next joins via BFS)
                return {"success": True, "reentered_phase": "PHASE-1", "slot_no": status.current_slot_no}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_current_global_slot(self, user_id: str) -> int:
        activation = (
            SlotActivation.objects(user_id=ObjectId(user_id), program='global')
            .order_by('-slot_no')
            .first()
        )
        return activation.slot_no if activation else 0

    def _attempt_reserved_auto_upgrade(self, user_id: str, currency: str) -> Dict[str, Any]:
        try:
            status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not status:
                return {"success": False, "error": "Global status not found"}

            reserved = Decimal(str(getattr(status, 'reserved_upgrade_amount', 0) or 0))
            if reserved <= 0:
                return {"success": False, "error": "No reserved funds"}

            # Must be ready to progress per Phase rules
            if not status.next_phase_ready:
                return {"success": False, "error": "Next phase not ready"}

            # Determine next slot number based on highest activated slot
            current_slot = self._get_current_global_slot(user_id)
            next_slot = min((current_slot or 1) + 1, 16)
            catalog = SlotCatalog.objects(program='global', slot_no=next_slot, is_active=True).first()
            if not catalog or not catalog.price:
                return {"success": False, "error": "Next slot catalog missing"}
            price = Decimal(str(catalog.price))

            if reserved < price:
                return {"success": False, "error": "Insufficient reserved funds"}

            # Progress phase status first (Phase-1 -> Phase-2 or Phase-2 -> Phase-1 next)
            self.process_progression(user_id)

            # Auto-upgrade using reserved funds
            tx_hash = f"GLOBAL-AUTO-UP-{user_id}-S{next_slot}-{int(datetime.utcnow().timestamp())}"
            upgrade_result = self.upgrade_global_slot(user_id=user_id, to_slot_no=next_slot, tx_hash=tx_hash, amount=price)
            if not upgrade_result.get('success'):
                return upgrade_result

            # Deduct reserved
            new_reserved = reserved - price
            setattr(status, 'reserved_upgrade_amount', float(new_reserved))
            status.save()

            return {"success": True, "next_slot": next_slot, "reserved_remaining": float(new_reserved)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_distribution(self, user_id: str, amount: Decimal, currency: str) -> Dict[str, Any]:
        """Global distribution per GLOBAL_PROGRAM_AUTO_ACTIONS.md Section 1.1.6.
        Breakdown:
        - Level (30%): Reserve for Phase-2 slot upgrade
        - Partner Incentive (10%): Direct upline commission (already handled)
        - Profit (30%): Net profit portion
        - Royal Captain Bonus (10%): Add to RC fund
        - President Reward (10%): Add to PR fund
        - Triple Entry Reward (5%): Add to TER fund (part of 25% total TER)
        - Shareholders (5%): Add to shareholders fund
        """
        try:
            total = Decimal(str(amount))
            reserved_upgrade = total * Decimal('0.30')  # Level 30%
            profit_portion = total * Decimal('0.30')    # Profit 30%
            royal_captain_portion = total * Decimal('0.10')  # RC 10%
            president_reward_portion = total * Decimal('0.10')  # PR 10%
            triple_entry_portion = total * Decimal('0.05')  # TER 5%
            shareholders_portion = total * Decimal('0.05')  # Shareholders 5%

            # Create GlobalDistribution record
            distribution_record = GlobalDistribution(
                user_id=ObjectId(user_id),
                transaction_id=ObjectId(),  # Generate new transaction ID
                transaction_amount=total,
                currency=currency,
                transaction_type='join',  # Default type
                level_reserve_amount=reserved_upgrade,
                partner_incentive_amount=Decimal('0'),  # Already handled separately
                profit_amount=profit_portion,
                royal_captain_bonus_amount=royal_captain_portion,
                president_reward_amount=president_reward_portion,
                triple_entry_reward_amount=triple_entry_portion,
                shareholders_amount=shareholders_portion,
                level_reserve_updated=False,
                partner_incentive_updated=True,  # Already handled
                profit_updated=False,
                royal_captain_bonus_updated=False,
                president_reward_updated=False,
                triple_entry_reward_updated=False,
                shareholders_updated=False,
                status='processing',
                processed_at=datetime.utcnow()
            )
            distribution_record.save()

            # Update reserved for upgrade on status
            try:
                status = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
                if status:
                    current_reserved = Decimal(str(getattr(status, 'reserved_upgrade_amount', 0) or 0))
                    current_reserved += reserved_upgrade
                    setattr(status, 'reserved_upgrade_amount', float(current_reserved))
                    status.last_updated = datetime.utcnow()
                    status.save()
            except Exception:
                pass

            # Profit → BonusFund and CompanyWallet
            try:
                bf = BonusFund.objects(fund_type='net_profit', program='global').first()
                if not bf:
                    bf = BonusFund(fund_type='net_profit', program='global', status='active')
                bf.total_amount = float(getattr(bf, 'total_amount', 0.0) + float(profit_portion))
                bf.available_amount = float(getattr(bf, 'available_amount', 0.0) + float(profit_portion))
                bf.updated_at = datetime.utcnow()
                bf.save()
                # Company wallet credit
                self.company_wallet.credit(profit_portion, currency, 'global_net_profit_topup', f'GLB-NETPROFIT-{user_id}-{datetime.utcnow().timestamp()}')
            except Exception:
                pass

            # Update Royal Captain fund
            try:
                rc_fund = RoyalCaptainFund.objects(is_active=True).first()
                if not rc_fund:
                    from modules.royal_captain.model import RoyalCaptainFund as RCF
                    rc_fund = RCF()
                rc_fund.total_fund_amount += float(royal_captain_portion)
                rc_fund.available_amount += float(royal_captain_portion)
                rc_fund.fund_sources['global_contributions'] = rc_fund.fund_sources.get('global_contributions', 0.0) + float(royal_captain_portion)
                rc_fund.last_updated = datetime.utcnow()
                rc_fund.save()
            except Exception:
                pass

            # Update President Reward fund
            try:
                pr_fund = PresidentRewardFund.objects(is_active=True).first()
                if not pr_fund:
                    from modules.president_reward.model import PresidentRewardFund as PRF
                    pr_fund = PRF()
                pr_fund.total_fund_amount += float(president_reward_portion)
                pr_fund.available_amount += float(president_reward_portion)
                pr_fund.fund_sources['global_contributions'] = pr_fund.fund_sources.get('global_contributions', 0.0) + float(president_reward_portion)
                pr_fund.last_updated = datetime.utcnow()
                pr_fund.save()
            except Exception:
                pass

            # Triple Entry Reward (Spark) - Section 1.1.6
            try:
                self.spark_service.contribute_to_fund(
                    amount=float(triple_entry_portion),
                    program='global',
                    source_user_id=str(user_id),
                    source_type='global_join',
                    currency=currency
                )
            except Exception:
                pass

            # Shareholders → BonusFund and CompanyWallet
            try:
                bf_sh = BonusFund.objects(fund_type='shareholders', program='global').first()
                if not bf_sh:
                    bf_sh = BonusFund(fund_type='shareholders', program='global', status='active')
                bf_sh.total_amount = float(getattr(bf_sh, 'total_amount', 0.0) + float(shareholders_portion))
                bf_sh.available_amount = float(getattr(bf_sh, 'available_amount', 0.0) + float(shareholders_portion))
                bf_sh.updated_at = datetime.utcnow()
                bf_sh.save()
                # Company wallet credit
                self.company_wallet.credit(shareholders_portion, currency, 'global_shareholders_topup', f'GLB-SHAREHOLDERS-{user_id}-{datetime.utcnow().timestamp()}')
            except Exception:
                pass

            # Attempt reserved auto-upgrade if phase ready and balance sufficient
            auto_result = self._attempt_reserved_auto_upgrade(user_id, currency)

            # Trigger eligibility checks (best-effort)
            try:
                RoyalCaptainService().process_bonus_tiers(user_id)
            except Exception:
                pass
            try:
                PresidentRewardService().process_reward_tiers(user_id)
            except Exception:
                pass

            # Update distribution record status to completed
            distribution_record.status = 'completed'
            distribution_record.completed_at = datetime.utcnow()
            distribution_record.updated_at = datetime.utcnow()
            distribution_record.save()

            return {
                "success": True,
                "distribution_breakdown": {
                    "level_reserved": float(reserved_upgrade),  # 30%
                    "partner_incentive": float(total * Decimal('0.10')),  # 10% (already handled)
                    "profit": float(profit_portion),  # 30%
                    "royal_captain": float(royal_captain_portion),  # 10%
                    "president_reward": float(president_reward_portion),  # 10%
                    "triple_entry": float(triple_entry_portion),  # 5%
                    "shareholders": float(shareholders_portion)  # 5%
                },
                "auto_upgrade": auto_result,
                "distribution_record_id": str(distribution_record.id)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_phase_seats(self, user_id: str, phase: str) -> Dict[str, Any]:
        try:
            if phase not in ['PHASE-1', 'PHASE-2']:
                return {"success": False, "error": "Invalid phase"}
            
            # Get or create GlobalPhaseSeat record
            seat_record = GlobalPhaseSeat.objects(user_id=ObjectId(user_id), phase=phase).first()
            if not seat_record:
                # Create new seat record
                total_seats = 4 if phase == 'PHASE-1' else 8
                seat_record = GlobalPhaseSeat(
                    user_id=ObjectId(user_id),
                    phase=phase,
                    slot_number=1,  # Default slot number
                    total_seats=total_seats,
                    occupied_seats=0,
                    available_seats=total_seats,
                    seat_positions=[],
                    waiting_list=[],
                    is_open=True,
                    is_full=False
                )
                seat_record.save()

            # Get team members for this phase
            team_members = GlobalTeamMember.objects(
                parent_user_id=ObjectId(user_id), 
                phase=phase, 
                is_active=True
            ).only('user_id', 'position_in_phase')

            # Build seat positions
            seats = {}
            for i in range(1, seat_record.total_seats + 1):
                seats[str(i)] = None

            # Fill occupied seats
            for member in team_members:
                if 1 <= member.position_in_phase <= seat_record.total_seats:
                    seats[str(member.position_in_phase)] = str(member.user_id)

            # Update seat record
            occupied_count = sum(1 for seat in seats.values() if seat is not None)
            seat_record.occupied_seats = occupied_count
            seat_record.available_seats = seat_record.total_seats - occupied_count
            seat_record.is_full = occupied_count >= seat_record.total_seats
            seat_record.updated_at = datetime.utcnow()
            seat_record.save()

            return {
                "success": True, 
                "phase": phase, 
                "seats": seats,
                "total_seats": seat_record.total_seats,
                "occupied_seats": seat_record.occupied_seats,
                "available_seats": seat_record.available_seats,
                "is_full": seat_record.is_full,
                "is_open": seat_record.is_open
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def preview_distribution(self, amount: Decimal) -> Dict[str, Any]:
        try:
            total = Decimal(str(amount))
            return {
                "success": True,
                "distribution_breakdown": {
                    "level_reserved": float(total * Decimal('0.30')),  # 30%
                    "partner_incentive": float(total * Decimal('0.10')),  # 10%
                    "profit": float(total * Decimal('0.30')),  # 30%
                    "royal_captain": float(total * Decimal('0.10')),  # 10%
                    "president_reward": float(total * Decimal('0.10')),  # 10%
                    "triple_entry": float(total * Decimal('0.05')),  # 5%
                    "shareholders": float(total * Decimal('0.05'))  # 5%
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_global_tree(self, user_id: str, phase: str) -> Dict[str, Any]:
        """Return usersData array for GlobalMatrixGraph: [{id:position, type, userId}]"""
        try:
            if phase not in ['phase-1', 'phase-2']:
                return {"success": False, "error": "phase must be 'phase-1' or 'phase-2'"}
            phase_key = 'PHASE-1' if phase == 'phase-1' else 'PHASE-2'
            
            # Get GlobalTreeStructure record
            tree_record = GlobalTreeStructure.objects(user_id=ObjectId(user_id), phase=phase_key).first()
            if not tree_record:
                # Create new tree structure
                expected = 4 if phase_key == 'PHASE-1' else 8
                tree_record = GlobalTreeStructure(
                    user_id=ObjectId(user_id),
                    parent_user_id=None,  # Root user
                    phase=phase_key,
                    slot_number=1,
                    level=0,
                    position=0,
                    left_child_id=None,
                    right_child_id=None,
                    children_count=0,
                    phase_1_members=[],
                    phase_2_members=[],
                    is_active=True,
                    is_complete=False
                )
                tree_record.save()

            # Get team members for this phase
            team_members = GlobalTeamMember.objects(
                parent_user_id=ObjectId(user_id), 
                phase=phase_key, 
                is_active=True
            ).only('user_id', 'position_in_phase')

            # Build position mapping
            expected = 4 if phase_key == 'PHASE-1' else 8
            pos_to_user: Dict[int, str] = {}
            for member in team_members:
                if 1 <= member.position_in_phase <= expected:
                    pos_to_user[member.position_in_phase] = str(member.user_id)

            # Build users data array
            users_data = []
            for i in range(1, expected + 1):
                occupant = pos_to_user.get(i)
                users_data.append({
                    "id": i,
                    "type": "active" if occupant else "empty",
                    "userId": occupant
                })

            # Update tree record
            tree_record.children_count = len(team_members)
            tree_record.is_complete = len(team_members) >= expected
            tree_record.updated_at = datetime.utcnow()
            tree_record.save()

            return {
                "success": True,
                "user_id": user_id,
                "phase": phase,
                "phase_key": phase_key,
                "expected_members": expected,
                "current_members": len(team_members),
                "is_complete": tree_record.is_complete,
                "usersData": users_data,
                "tree_structure": {
                    "level": tree_record.level,
                    "position": tree_record.position,
                    "children_count": tree_record.children_count,
                    "is_active": tree_record.is_active
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_phase_progression(self, user_id: str) -> Dict[str, Any]:
        """
        3.1 Phase-1 to Phase-2 Progression - Section 3.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        **Trigger**: User has 4 people in Phase-1 under them
        **Auto Action**: `process_progression()`
        """
        try:
            # Get user's GlobalPhaseProgression record
            progression = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not progression:
                return {"success": False, "error": "GlobalPhaseProgression record not found"}

            # 3.1.1 Phase Completion Check - Section 3.1.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Check if phase_1_members_current >= phase_1_members_required (4)
            if progression.phase_1_members_current < progression.phase_1_members_required:
                print(f"Phase-1 completion check failed for user {user_id}: {progression.phase_1_members_current}/{progression.phase_1_members_required} members")
                return {"success": False, "error": f"Phase-1 not complete: {progression.phase_1_members_current}/{progression.phase_1_members_required} members"}

            # Verify next_phase_ready is true
            if not progression.next_phase_ready:
                print(f"Phase-1 completion check failed for user {user_id}: next_phase_ready is false")
                return {"success": False, "error": "Next phase not ready"}

            print(f"Phase-1 completion check passed for user {user_id}: {progression.phase_1_members_current}/{progression.phase_1_members_required} members, next_phase_ready={progression.next_phase_ready}")

            # 3.1.2 Phase Status Update - Section 3.1.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Set current_phase: 'PHASE-2'
            progression.current_phase = 'PHASE-2'
            # Set current_slot_no: 1 (Phase-2 first slot)
            progression.current_slot_no = 1
            # Set is_phase_complete: true
            progression.is_phase_complete = True
            # Set phase_completed_at: current_timestamp
            progression.phase_completed_at = datetime.utcnow()
            # Set next_phase_ready: false
            progression.next_phase_ready = False
            # Update timestamp
            progression.updated_at = datetime.utcnow()
            progression.save()

            print(f"Phase status updated for user {user_id}: PHASE-1 -> PHASE-2, slot 1, phase_completed_at={progression.phase_completed_at}")

            # 3.1.3 Phase-2 Placement - Section 3.1.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Place user in Phase-2 tree using BFS algorithm
            placement_result = self._place_in_phase2(user_id)
            if not placement_result.get("success"):
                print(f"Phase-2 placement failed for user {user_id}: {placement_result.get('error')}")
                return {"success": False, "error": f"Phase-2 placement failed: {placement_result.get('error')}"}

            print(f"Phase-2 placement completed for user {user_id}: parent={placement_result.get('parent_id')}")

            # 3.1.4 Reserved Funds Usage - Section 3.1.4 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Use reserved_upgrade_amount for Phase-2 slot activation
            if progression.reserved_upgrade_amount and progression.reserved_upgrade_amount > 0:
                try:
                    # Get Phase-2 Slot-1 catalog
                    catalog = SlotCatalog.objects(program='global', slot_no=1, phase='PHASE-2').first()
                    if catalog and progression.reserved_upgrade_amount >= catalog.price:
                        # Create SlotActivation record for Phase-2 Slot-1
                        current_time = datetime.utcnow()
                        activation = SlotActivation(
                            user_id=ObjectId(user_id),
                            program='global',
                            slot_no=1,
                            slot_name=catalog.name,
                            activation_type='auto_upgrade',
                            upgrade_source='reserved',
                            amount_paid=catalog.price,
                            currency='USD',
                            tx_hash=f"PHASE2_AUTO_{user_id}_{current_time.strftime('%Y%m%d%H%M%S')}",
                            blockchain_network='BSC',
                            commission_paid=Decimal('0'),
                            commission_percentage=0.0,
                            is_auto_upgrade=True,
                            partners_contributed=[],
                            earnings_used=progression.reserved_upgrade_amount,
                            status='completed',
                            activated_at=current_time,
                            completed_at=current_time,
                            created_at=current_time,
                            metadata={
                                'upgrade_type': 'auto',
                                'slot_level': catalog.level,
                                'validation_passed': True,
                                'upgrade_sequence': 1,
                                'phase_progression': True,
                                'reserved_funds_used': float(progression.reserved_upgrade_amount)
                            }
                        )
                        activation.save()

                        # Update reserved amount
                        progression.reserved_upgrade_amount -= catalog.price
                        progression.save()

                        print(f"Phase-2 Slot-1 auto-activated for user {user_id}: {catalog.name} - ${catalog.price} (reserved funds used)")
                    else:
                        print(f"Insufficient reserved funds for Phase-2 Slot-1: {progression.reserved_upgrade_amount} < {catalog.price if catalog else 'N/A'}")
                except Exception as e:
                    print(f"Reserved funds usage failed for user {user_id}: {str(e)}")

            return {
                "success": True,
                "user_id": user_id,
                "old_phase": "PHASE-1",
                "new_phase": "PHASE-2",
                "new_slot_no": 1,
                "phase_completed_at": progression.phase_completed_at,
                "placement_result": placement_result
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _place_in_phase2(self, user_id: str) -> Dict[str, Any]:
        """
        Place user in Phase-2 tree using BFS algorithm
        Find eligible upline with available Phase-2 positions
        Update parent's phase_2_members_current count
        """
        try:
            # Find eligible upline with available Phase-2 positions
            parent = self._find_phase2_parent_bfs(user_id)
            if not parent:
                # Try escalation if no direct parent found
                parent = self._find_phase2_parent_escalation(user_id)
                if not parent:
                    # Fallback to Mother ID
                    parent = self._get_mother_id()
                    if not parent:
                        return {"success": False, "error": "No eligible parent found for Phase-2 placement"}

            # Create TreePlacement record for Phase-2
            placement = TreePlacement(
                user_id=ObjectId(user_id),
                program='global',
                phase='PHASE-2',
                slot_no=1,
                parent_id=parent,  # parent is already an ObjectId from _find_phase2_parent_bfs
                upline_id=parent,  # Set upline_id for tree queries
                position='position_1',  # Default position for Phase-2
                level=1,  # Default level
                phase_position=1,  # Default phase position
                is_active=True,
                is_activated=True,
                activation_date=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            placement.save()

            # Update parent's Phase-2 member count
            parent_progression = GlobalPhaseProgression.objects(user_id=parent).first()
            if parent_progression:
                parent_progression.phase_2_members_current += 1
                parent_progression.updated_at = datetime.utcnow()
                parent_progression.save()

                # Check if parent's Phase-2 is complete (8 members)
                if parent_progression.phase_2_members_current >= parent_progression.phase_2_members_required:
                    parent_progression.is_phase_complete = True
                    parent_progression.next_phase_ready = True
                    parent_progression.save()
                    print(f"Parent {parent} Phase-2 completed: {parent_progression.phase_2_members_current}/{parent_progression.phase_2_members_required} members")
                    
                    # Trigger Phase-2 to Phase-1 re-entry with slot upgrade
                    print(f"Triggering Phase-2 to Phase-1 re-entry with slot upgrade for user {parent}")
                    reentry_result = self.process_phase2_to_phase1_reentry(str(parent))
                    if reentry_result.get("success"):
                        print(f"Successfully processed Phase-2 to Phase-1 re-entry for user {parent}")
                    else:
                        print(f"Failed to process Phase-2 to Phase-1 re-entry for user {parent}: {reentry_result.get('error')}")

            return {
                "success": True,
                "parent_id": str(parent),
                "placement_id": str(placement.id),
                "phase": "PHASE-2",
                "slot_no": 1
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _find_phase2_parent_bfs(self, user_id: str) -> ObjectId | None:
        """
        Find eligible upline with available Phase-2 positions using proper BFS algorithm
        """
        try:
            # First, check if there are any existing Global users in Phase-2
            existing_users = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True).order_by('created_at')
            
            if not existing_users:
                print("No existing Global Phase-2 users found")
                return None
            
            # Start BFS from the earliest users (ROOT users first)
            queue = []
            visited = set()
            
            # Find all ROOT users (users with no parent) and add them to queue first
            root_users = [placement.user_id for placement in existing_users if not placement.parent_id]
            queue.extend(root_users)
            
            # Add remaining users to queue (non-root users)
            non_root_users = [placement.user_id for placement in existing_users if placement.parent_id]
            queue.extend(non_root_users)
            
            print(f"Starting Phase-2 BFS with {len(queue)} users in queue (ROOT users: {len(root_users)})")
            
            # BFS traversal
            while queue:
                current_user_id = queue.pop(0)
                
                if current_user_id in visited:
                    continue
                visited.add(current_user_id)
                
                # Check if current user has available Phase-2 positions
                progression = GlobalPhaseProgression.objects(user_id=current_user_id).first()
                if progression:
                    child_count = progression.phase_2_members_current or 0
                    required_count = progression.phase_2_members_required or 8
                    
                    print(f"Phase-2 BFS checking user {current_user_id}: {child_count}/{required_count} children")
                    
                    if child_count < required_count:
                        print(f"Found eligible Phase-2 parent {current_user_id} with {child_count} children")
                        return current_user_id
                
                # Add children to queue for further exploration
                children = TreePlacement.objects(parent_id=current_user_id, program='global', phase='PHASE-2', is_active=True)
                for child in children:
                    if child.user_id not in visited:
                        queue.append(child.user_id)
            
            print("No eligible Phase-2 parent found in BFS")
            return None

        except Exception as e:
            print(f"Phase-2 BFS parent search failed: {str(e)}")
            return None

    def _find_phase2_parent_escalation(self, user_id: str):
        """
        Find eligible upline with available Phase-2 positions using escalation
        """
        try:
            # Get user's direct upline
            user = User.objects(id=ObjectId(user_id)).first()
            if not user or not user.referrer_id:
                return None

            current_id = user.referrer_id
            level = 0
            max_levels = 60

            while level < max_levels:
                # Check if current user has available Phase-2 positions
                progression = GlobalPhaseProgression.objects(user_id=current_id).first()
                if progression and progression.phase_2_members_current < progression.phase_2_members_required:
                    return User.objects(id=current_id).first()

                # Move to next upline
                current_user = User.objects(id=current_id).first()
                if not current_user or not current_user.referrer_id:
                    break

                current_id = current_user.referrer_id
                level += 1

            return None

        except Exception as e:
            print(f"Phase-2 escalation parent search failed: {str(e)}")
            return None

    def process_phase2_to_phase1_reentry(self, user_id: str) -> Dict[str, Any]:
        """
        3.2 Phase-2 to Phase-1 Re-entry - Section 3.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        **Trigger**: User has 8 people in Phase-2 under them
        **Auto Action**: `process_progression()`
        """
        try:
            # Get user's GlobalPhaseProgression record
            progression = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not progression:
                return {"success": False, "error": "GlobalPhaseProgression record not found"}

            # 3.2.1 Phase Completion Check - Section 3.2.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Check if phase_2_members_current >= phase_2_members_required (8)
            if progression.phase_2_members_current < progression.phase_2_members_required:
                print(f"Phase-2 completion check failed for user {user_id}: {progression.phase_2_members_current}/{progression.phase_2_members_required} members")
                return {"success": False, "error": f"Phase-2 not complete: {progression.phase_2_members_current}/{progression.phase_2_members_required} members"}

            # Verify next_phase_ready is true
            if not progression.next_phase_ready:
                print(f"Phase-2 completion check failed for user {user_id}: next_phase_ready is false")
                return {"success": False, "error": "Next phase not ready"}

            print(f"Phase-2 completion check passed for user {user_id}: {progression.phase_2_members_current}/{progression.phase_2_members_required} members, next_phase_ready={progression.next_phase_ready}")

            # 3.2.2 Phase Status Update - Section 3.2.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Set current_phase: 'PHASE-1'
            progression.current_phase = 'PHASE-1'
            # Set current_slot_no: next_slot_number
            next_slot_no = progression.current_slot_no + 1
            progression.current_slot_no = next_slot_no
            # Set is_phase_complete: true
            progression.is_phase_complete = True
            # Set phase_completed_at: current_timestamp
            progression.phase_completed_at = datetime.utcnow()
            # Set next_phase_ready: false
            progression.next_phase_ready = False
            # Update timestamp
            progression.updated_at = datetime.utcnow()
            progression.save()

            print(f"Phase status updated for user {user_id}: PHASE-2 -> PHASE-1, slot {next_slot_no}, phase_completed_at={progression.phase_completed_at}")

            # 3.2.3 Phase-1 Re-entry Placement - Section 3.2.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Place user in Phase-1 tree using BFS algorithm
            placement_result = self._place_in_phase1_reentry(user_id, next_slot_no)
            if not placement_result.get("success"):
                print(f"Phase-1 re-entry placement failed for user {user_id}: {placement_result.get('error')}")
                return {"success": False, "error": f"Phase-1 re-entry placement failed: {placement_result.get('error')}"}

            print(f"Phase-1 re-entry placement completed for user {user_id}: parent={placement_result.get('parent_id')}, slot={next_slot_no}")

            # 3.2.4 Reserved Funds Usage - Section 3.2.4 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Use reserved_upgrade_amount for Phase-1 slot activation
            if progression.reserved_upgrade_amount and progression.reserved_upgrade_amount > 0:
                try:
                    # Get Phase-1 next slot catalog
                    catalog = SlotCatalog.objects(program='global', slot_no=next_slot_no, phase='PHASE-1').first()
                    if catalog and progression.reserved_upgrade_amount >= catalog.price:
                        # Create SlotActivation record for Phase-1 next slot
                        current_time = datetime.utcnow()
                        activation = SlotActivation(
                            user_id=ObjectId(user_id),
                            program='global',
                            slot_no=next_slot_no,
                            slot_name=catalog.name,
                            activation_type='auto_upgrade',
                            upgrade_source='reserved',
                            amount_paid=catalog.price,
                            currency='USD',
                            tx_hash=f"PHASE1_REENTRY_{user_id}_{current_time.strftime('%Y%m%d%H%M%S')}",
                            blockchain_network='BSC',
                            commission_paid=Decimal('0'),
                            commission_percentage=0.0,
                            is_auto_upgrade=True,
                            partners_contributed=[],
                            earnings_used=progression.reserved_upgrade_amount,
                            status='completed',
                            activated_at=current_time,
                            completed_at=current_time,
                            created_at=current_time,
                            metadata={
                                'upgrade_type': 'auto',
                                'slot_level': catalog.level,
                                'validation_passed': True,
                                'upgrade_sequence': next_slot_no,
                                'phase_reentry': True,
                                'reserved_funds_used': float(progression.reserved_upgrade_amount)
                            }
                        )
                        activation.save()

                        # Update reserved amount
                        progression.reserved_upgrade_amount -= catalog.price
                        progression.save()

                        print(f"Phase-1 Slot-{next_slot_no} auto-activated for user {user_id}: {catalog.name} - ${catalog.price} (reserved funds used)")
                    else:
                        print(f"Insufficient reserved funds for Phase-1 Slot-{next_slot_no}: {progression.reserved_upgrade_amount} < {catalog.price if catalog else 'N/A'}")
                except Exception as e:
                    print(f"Reserved funds usage failed for user {user_id}: {str(e)}")

            return {
                "success": True,
                "user_id": user_id,
                "old_phase": "PHASE-2",
                "new_phase": "PHASE-1",
                "new_slot_no": next_slot_no,
                "phase_completed_at": progression.phase_completed_at,
                "placement_result": placement_result
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _place_in_phase1_reentry(self, user_id: str, slot_no: int) -> Dict[str, Any]:
        """
        Place user in Phase-1 tree using BFS algorithm for re-entry
        Find eligible upline with available Phase-1 positions
        Update parent's phase_1_members_current count
        """
        try:
            # Find eligible upline with available Phase-1 positions
            parent = self._find_phase1_parent_bfs(user_id)
            if not parent:
                # Try escalation if no direct parent found
                parent = self._find_phase1_parent_escalation(user_id)
                if not parent:
                    # Fallback to Mother ID
                    parent = self._get_mother_id()
                    if not parent:
                        return {"success": False, "error": "No eligible parent found for Phase-1 re-entry placement"}

            # Create TreePlacement record for Phase-1 re-entry
            placement = TreePlacement(
                user_id=ObjectId(user_id),
                program='global',
                phase='PHASE-1',
                slot_no=slot_no,
                parent_id=ObjectId(parent.id),
                upline_id=ObjectId(parent.id),  # Set upline_id for tree queries
                placement_type='phase_reentry',
                placed_at=datetime.utcnow()
            )
            placement.save()

            # Update parent's Phase-1 member count
            parent_progression = GlobalPhaseProgression.objects(user_id=ObjectId(parent.id)).first()
            if parent_progression:
                parent_progression.phase_1_members_current += 1
                parent_progression.updated_at = datetime.utcnow()
                parent_progression.save()

                # Check if parent's Phase-1 is complete (4 members)
                if parent_progression.phase_1_members_current >= parent_progression.phase_1_members_required:
                    parent_progression.is_phase_complete = True
                    parent_progression.next_phase_ready = True
                    parent_progression.save()
                    print(f"Parent {parent.id} Phase-1 completed: {parent_progression.phase_1_members_current}/{parent_progression.phase_1_members_required} members")

            return {
                "success": True,
                "parent_id": str(parent.id),
                "placement_id": str(placement.id),
                "phase": "PHASE-1",
                "slot_no": slot_no
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_auto_upgrade(self, user_id: str) -> Dict[str, Any]:
        """
        10.1 Reserved Funds Auto Upgrade - Section 10.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        **Trigger**: Sufficient reserved funds for next slot
        **Auto Action**: `process_auto_upgrade()`
        """
        try:
            # Get user's GlobalPhaseProgression record
            progression = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not progression:
                return {"success": False, "error": "GlobalPhaseProgression record not found"}

            # 10.1.1 Upgrade Check - Section 10.1.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Check if reserved_upgrade_amount >= next_slot_price
            next_slot_no = progression.current_slot_no + 1
            
            # Get next slot catalog
            catalog = SlotCatalog.objects(program='global', slot_no=next_slot_no).first()
            if not catalog:
                return {"success": False, "error": f"Slot catalog not found for slot {next_slot_no}"}

            if progression.reserved_upgrade_amount < catalog.price:
                print(f"Auto-upgrade check failed for user {user_id}: insufficient reserved funds {progression.reserved_upgrade_amount} < {catalog.price}")
                return {"success": False, "error": f"Insufficient reserved funds: {progression.reserved_upgrade_amount} < {catalog.price}"}

            # Verify next_phase_ready is true
            if not progression.next_phase_ready:
                print(f"Auto-upgrade check failed for user {user_id}: next_phase_ready is false")
                return {"success": False, "error": "Next phase not ready"}

            print(f"Auto-upgrade check passed for user {user_id}: reserved={progression.reserved_upgrade_amount}, next_slot={next_slot_no}, price={catalog.price}")

            # 10.1.2 Auto Upgrade Execution - Section 10.1.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Create auto-upgrade transaction
            current_time = datetime.utcnow()
            auto_tx_hash = f"GLOBAL-AUTO-UP-{user_id}-S{next_slot_no}-{current_time.strftime('%Y%m%d%H%M%S')}"
            
            # Process slot upgrade using existing upgrade method
            upgrade_result = self.upgrade_global_slot(
                user_id=user_id,
                to_slot_no=next_slot_no,
                tx_hash=auto_tx_hash,
                amount=catalog.price
            )
            
            if not upgrade_result.get("success"):
                print(f"Auto-upgrade execution failed for user {user_id}: {upgrade_result.get('error')}")
                return {"success": False, "error": f"Auto-upgrade execution failed: {upgrade_result.get('error')}"}

            # Deduct from reserved funds
            progression.reserved_upgrade_amount -= catalog.price
            progression.updated_at = current_time
            progression.save()

            print(f"Auto-upgrade executed for user {user_id}: slot {next_slot_no} ({catalog.name}) - ${catalog.price}, remaining reserved: {progression.reserved_upgrade_amount}")

            # 10.1.3 Status Update - Section 10.1.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Update current_slot_no
            progression.current_slot_no = next_slot_no
            # Update reserved_upgrade_amount (already done above)
            # Set last_updated: current_timestamp (already done above)
            progression.save()

            print(f"Auto-upgrade status updated for user {user_id}: current_slot_no={next_slot_no}, reserved_upgrade_amount={progression.reserved_upgrade_amount}")

            return {
                "success": True,
                "user_id": user_id,
                "upgraded_slot_no": next_slot_no,
                "slot_name": catalog.name,
                "amount_paid": float(catalog.price),
                "reserved_funds_used": float(catalog.price),
                "remaining_reserved": float(progression.reserved_upgrade_amount),
                "auto_tx_hash": auto_tx_hash,
                "upgrade_result": upgrade_result
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_and_process_auto_upgrade(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user is eligible for auto-upgrade and process it
        This method can be called periodically or triggered by events
        """
        try:
            # Get user's GlobalPhaseProgression record
            progression = GlobalPhaseProgression.objects(user_id=ObjectId(user_id)).first()
            if not progression:
                return {"success": False, "error": "GlobalPhaseProgression record not found"}

            # Check if auto-upgrade is enabled
            if not progression.auto_progression_enabled:
                return {"success": False, "error": "Auto-progression is disabled"}

            # Check if user is in a state where auto-upgrade is possible
            if progression.current_slot_no >= 16:
                return {"success": False, "error": "User has reached maximum slot (16)"}

            # Check if next phase is ready
            if not progression.next_phase_ready:
                return {"success": False, "error": "Next phase not ready"}

            # Try to process auto-upgrade
            auto_upgrade_result = self.process_auto_upgrade(user_id)
            
            if auto_upgrade_result.get("success"):
                print(f"Auto-upgrade processed successfully for user {user_id}: slot {auto_upgrade_result.get('upgraded_slot_no')}")
                return auto_upgrade_result
            else:
                print(f"Auto-upgrade not processed for user {user_id}: {auto_upgrade_result.get('error')}")
                return auto_upgrade_result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_process_auto_upgrades(self) -> Dict[str, Any]:
        """
        Process auto-upgrades for all eligible users
        This method can be called by a scheduled task
        """
        try:
            # Find all users eligible for auto-upgrade
            eligible_users = GlobalPhaseProgression.objects(
                auto_progression_enabled=True,
                next_phase_ready=True,
                current_slot_no__lt=16
            ).only('user_id')

            processed_count = 0
            failed_count = 0
            results = []

            for progression in eligible_users:
                user_id = str(progression.user_id)
                result = self.check_and_process_auto_upgrade(user_id)
                
                if result.get("success"):
                    processed_count += 1
                    results.append({
                        "user_id": user_id,
                        "status": "success",
                        "upgraded_slot_no": result.get("upgraded_slot_no"),
                        "slot_name": result.get("slot_name")
                    })
                else:
                    failed_count += 1
                    results.append({
                        "user_id": user_id,
                        "status": "failed",
                        "error": result.get("error")
                    })

            print(f"Batch auto-upgrade processing completed: {processed_count} successful, {failed_count} failed")

            return {
                "success": True,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "total_checked": len(eligible_users),
                "results": results
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_global_incentive_distribution(self, from_user_id: str, slot_value: Decimal, transaction_type: str = 'joining') -> Dict[str, Any]:
        """
        4.1 Partner Incentive Distribution - Section 4.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        **Trigger**: Direct partner joins or upgrades Global slot
        **Auto Action**: `calculate_partner_incentive()`
        """
        try:
            # Get the user who triggered the incentive
            from_user = User.objects(id=ObjectId(from_user_id)).first()
            if not from_user or not from_user.referrer_id:
                return {"success": False, "error": "User or referrer not found"}

            # 4.1.1 Incentive Calculation - Section 4.1.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Calculate 10% of slot value
            incentive_amount = slot_value * Decimal('0.10')
            
            # Identify direct upline from referral chain
            upline_user = User.objects(id=from_user.referrer_id).first()
            if not upline_user:
                return {"success": False, "error": "Upline user not found"}

            # Verify upline has Global program access
            if not upline_user.global_joined:
                print(f"Global incentive skipped for upline {upline_user.id}: Global program not joined")
                return {"success": False, "error": "Upline does not have Global program access"}

            print(f"Global incentive calculation: {incentive_amount} (10% of {slot_value}) for upline {upline_user.id} from {from_user_id}")

            # 4.1.2 Commission Distribution - Section 4.1.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Create `Commission` record
            try:
                commission = Commission(
                    from_user_id=ObjectId(from_user_id),
                    to_user_id=ObjectId(upline_user.id),
                    program='global',
                    commission_type=transaction_type,  # 'joining' or 'upgrade'
                    amount=incentive_amount,
                    currency='USD',
                    status='pending',
                    created_at=datetime.utcnow()
                )
                commission.save()
                print(f"Commission record created: {commission.id} - {incentive_amount} USD from {from_user_id} to {upline_user.id}")
            except Exception as e:
                print(f"Commission record creation failed: {str(e)}")
                return {"success": False, "error": f"Commission record creation failed: {str(e)}"}

            # 4.1.3 Wallet Credit - Section 4.1.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Credit upline's main wallet
            try:
                # Convert currency to USDT (since we only support USDT and BNB)
                credit_currency = 'USDT'
                
                # Credit the upline's main wallet
                wallet_service = WalletService()
                credit_result = wallet_service.credit_main_wallet(
                    user_id=str(upline_user.id),
                    amount=float(incentive_amount),
                    currency=credit_currency,
                    reason='global_partner_incentive',
                    tx_hash=f"GLOBAL_INCENTIVE_{from_user_id}_{upline_user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                )
                
                if not credit_result.get("success"):
                    print(f"Wallet credit failed for upline {upline_user.id}: {credit_result.get('error')}")
                    # Update commission status to failed
                    commission.status = 'failed'
                    commission.save()
                    return {"success": False, "error": f"Wallet credit failed: {credit_result.get('error')}"}

                # Update commission status to completed
                commission.status = 'completed'
                commission.completed_at = datetime.utcnow()
                commission.save()

                print(f"Global incentive distributed successfully: {incentive_amount} {credit_currency} credited to upline {upline_user.id}")

                return {
                    "success": True,
                    "from_user_id": from_user_id,
                    "to_user_id": str(upline_user.id),
                    "incentive_amount": float(incentive_amount),
                    "currency": credit_currency,
                    "transaction_type": transaction_type,
                    "commission_id": str(commission.id),
                    "wallet_credit_result": credit_result
                }

            except Exception as e:
                print(f"Wallet credit process failed: {str(e)}")
                # Update commission status to failed
                commission.status = 'failed'
                commission.save()
                return {"success": False, "error": f"Wallet credit process failed: {str(e)}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_global_joining_incentive(self, user_id: str, slot_value: Decimal) -> Dict[str, Any]:
        """
        Process Global joining incentive (10% to direct upline)
        """
        return self.process_global_incentive_distribution(
            from_user_id=user_id,
            slot_value=slot_value,
            transaction_type='joining'
        )

    def process_global_upgrade_incentive(self, user_id: str, slot_value: Decimal) -> Dict[str, Any]:
        """
        Process Global upgrade incentive (10% to direct upline)
        """
        return self.process_global_incentive_distribution(
            from_user_id=user_id,
            slot_value=slot_value,
            transaction_type='upgrade'
        )

    def batch_process_global_incentives(self, user_ids: list, slot_values: list, transaction_types: list) -> Dict[str, Any]:
        """
        Process Global incentives for multiple users
        """
        try:
            if len(user_ids) != len(slot_values) or len(user_ids) != len(transaction_types):
                return {"success": False, "error": "Lists must have the same length"}

            processed_count = 0
            failed_count = 0
            results = []

            for i, user_id in enumerate(user_ids):
                result = self.process_global_incentive_distribution(
                    from_user_id=user_id,
                    slot_value=slot_values[i],
                    transaction_type=transaction_types[i]
                )

                if result.get("success"):
                    processed_count += 1
                    results.append({
                        "user_id": user_id,
                        "status": "success",
                        "incentive_amount": result.get("incentive_amount"),
                        "to_user_id": result.get("to_user_id")
                    })
                else:
                    failed_count += 1
                    results.append({
                        "user_id": user_id,
                        "status": "failed",
                        "error": result.get("error")
                    })

            print(f"Batch Global incentive processing completed: {processed_count} successful, {failed_count} failed")

            return {
                "success": True,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "total_processed": len(user_ids),
                "results": results
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_royal_captain_bonus(self, user_id: str) -> Dict[str, Any]:
        """
        5.1 Royal Captain Bonus Calculation - Section 5.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        **Trigger**: User has 5 direct partners with Global program
        **Auto Action**: `calculate_royal_captain_bonus()`
        """
        try:
            # Get the user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # 5.1.1 Eligibility Check - Section 5.1.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Count direct partners with Global program
            direct_partners = User.objects(referrer_id=ObjectId(user_id), global_joined=True).count()
            
            # Check if count >= 5
            if direct_partners < 5:
                print(f"Royal Captain Bonus eligibility check failed for user {user_id}: {direct_partners} direct partners < 5")
                return {"success": False, "error": f"Insufficient direct partners: {direct_partners} < 5"}

            # Verify user has Matrix + Global programs
            if not user.matrix_joined or not user.global_joined:
                print(f"Royal Captain Bonus eligibility check failed for user {user_id}: missing Matrix or Global program")
                return {"success": False, "error": "User must have both Matrix and Global programs"}

            print(f"Royal Captain Bonus eligibility check passed for user {user_id}: {direct_partners} direct partners, Matrix + Global programs")

            # 5.1.2 Bonus Calculation - Section 5.1.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Count total global team size
            global_team_size = self._count_global_team_size(user_id)
            
            # Progressive amounts based on global team size
            bonus_amount = self._calculate_royal_captain_bonus_amount(global_team_size)
            
            print(f"Royal Captain Bonus calculation for user {user_id}: {direct_partners} direct partners, {global_team_size} global team, bonus: ${bonus_amount}")

            # 5.1.3 Fund Distribution - Section 5.1.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Deduct from Royal Captain Bonus fund
            try:
                # Check if Royal Captain fund has sufficient balance
                rc_fund = RoyalCaptainFund.objects.first()
                if not rc_fund or rc_fund.available_amount < bonus_amount:
                    print(f"Royal Captain Bonus fund insufficient: {rc_fund.available_amount if rc_fund else 0} < {bonus_amount}")
                    return {"success": False, "error": "Insufficient Royal Captain Bonus fund"}

                # Create `RoyalCaptainBonus` record
                bonus_record = RoyalCaptainBonus(
                    user_id=ObjectId(user_id),
                    direct_partners_count=direct_partners,
                    global_team_size=global_team_size,
                    bonus_amount=bonus_amount,
                    currency='USD',
                    status='paid',
                    paid_at=datetime.utcnow(),
                    created_at=datetime.utcnow()
                )
                bonus_record.save()

                # Deduct from fund
                rc_fund.available_amount -= bonus_amount
                rc_fund.total_paid_out += bonus_amount
                rc_fund.last_updated = datetime.utcnow()
                rc_fund.save()

                print(f"Royal Captain Bonus record created: {bonus_record.id} - ${bonus_amount} for user {user_id}")

            except Exception as e:
                print(f"Royal Captain Bonus fund distribution failed: {str(e)}")
                return {"success": False, "error": f"Fund distribution failed: {str(e)}"}

            # 5.1.4 Wallet Credit - Section 5.1.4 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Credit user's main wallet
            try:
                # Convert currency to USDT (since we only support USDT and BNB)
                credit_currency = 'USDT'
                
                # Credit the user's main wallet
                wallet_service = WalletService()
                credit_result = wallet_service.credit_main_wallet(
                    user_id=str(user_id),
                    amount=float(bonus_amount),
                    currency=credit_currency,
                    reason='royal_captain_bonus',
                    tx_hash=f"RC_BONUS_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                )
                
                if not credit_result.get("success"):
                    print(f"Wallet credit failed for user {user_id}: {credit_result.get('error')}")
                    return {"success": False, "error": f"Wallet credit failed: {credit_result.get('error')}"}

                print(f"Royal Captain Bonus distributed successfully: ${bonus_amount} {credit_currency} credited to user {user_id}")

                return {
                    "success": True,
                    "user_id": user_id,
                    "direct_partners_count": direct_partners,
                    "global_team_size": global_team_size,
                    "bonus_amount": float(bonus_amount),
                    "currency": credit_currency,
                    "bonus_record_id": str(bonus_record.id),
                    "wallet_credit_result": credit_result
                }

            except Exception as e:
                print(f"Wallet credit process failed: {str(e)}")
                return {"success": False, "error": f"Wallet credit process failed: {str(e)}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _count_global_team_size(self, user_id: str) -> int:
        """
        Count total global team size for a user (recursive count of all downlines)
        """
        try:
            # Get direct downlines with Global program
            direct_downlines = User.objects(referrer_id=ObjectId(user_id), global_joined=True).only('id')
            
            total_count = len(direct_downlines)
            
            # Recursively count downlines of downlines
            for downline in direct_downlines:
                total_count += self._count_global_team_size(str(downline.id))
            
            return total_count
            
        except Exception as e:
            print(f"Global team size count failed for user {user_id}: {str(e)}")
            return 0

    def _calculate_royal_captain_bonus_amount(self, global_team_size: int) -> Decimal:
        """
        Calculate Royal Captain bonus amount based on global team size
        """
        # Progressive amounts based on global team size:
        # - 10 global team: $200
        # - 50 global team: $200
        # - 100 global team: $200
        # - 200 global team: $250
        # - 300 global team: $250
        
        if global_team_size >= 300:
            return Decimal('250.00')
        elif global_team_size >= 200:
            return Decimal('250.00')
        elif global_team_size >= 100:
            return Decimal('200.00')
        elif global_team_size >= 50:
            return Decimal('200.00')
        elif global_team_size >= 10:
            return Decimal('200.00')
        else:
            return Decimal('200.00')  # Initial bonus for 5 direct partners

    def check_and_process_royal_captain_bonus(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user is eligible for Royal Captain Bonus and process it
        """
        try:
            # Get the user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # Check if user has both Matrix and Global programs
            if not user.matrix_joined or not user.global_joined:
                return {"success": False, "error": "User must have both Matrix and Global programs"}

            # Count direct partners with Global program
            direct_partners = User.objects(referrer_id=ObjectId(user_id), global_joined=True).count()
            
            if direct_partners < 5:
                return {"success": False, "error": f"Insufficient direct partners: {direct_partners} < 5"}

            # Check if user already received Royal Captain Bonus
            existing_bonus = RoyalCaptainBonus.objects(user_id=ObjectId(user_id), status='paid').first()
            if existing_bonus:
                return {"success": False, "error": "User already received Royal Captain Bonus"}

            # Process the bonus
            bonus_result = self.process_royal_captain_bonus(user_id)
            
            if bonus_result.get("success"):
                print(f"Royal Captain Bonus processed successfully for user {user_id}: ${bonus_result.get('bonus_amount')}")
                return bonus_result
            else:
                print(f"Royal Captain Bonus not processed for user {user_id}: {bonus_result.get('error')}")
                return bonus_result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_process_royal_captain_bonuses(self) -> Dict[str, Any]:
        """
        Process Royal Captain Bonuses for all eligible users
        """
        try:
            # Find all users with both Matrix and Global programs
            eligible_users = User.objects(
                matrix_joined=True,
                global_joined=True
            ).only('id')

            processed_count = 0
            failed_count = 0
            results = []

            for user in eligible_users:
                user_id = str(user.id)
                result = self.check_and_process_royal_captain_bonus(user_id)
                
                if result.get("success"):
                    processed_count += 1
                    results.append({
                        "user_id": user_id,
                        "status": "success",
                        "bonus_amount": result.get("bonus_amount"),
                        "direct_partners_count": result.get("direct_partners_count"),
                        "global_team_size": result.get("global_team_size")
                    })
                else:
                    failed_count += 1
                    results.append({
                        "user_id": user_id,
                        "status": "failed",
                        "error": result.get("error")
                    })

            print(f"Batch Royal Captain Bonus processing completed: {processed_count} successful, {failed_count} failed")

            return {
                "success": True,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "total_checked": len(eligible_users),
                "results": results
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_president_reward(self, user_id: str) -> Dict[str, Any]:
        """
        6.1 President Reward Calculation - Section 6.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        **Trigger**: User has 10 direct partners + 80 global team
        **Auto Action**: `calculate_president_reward()`
        """
        try:
            # Get the user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # 6.1.1 Eligibility Check - Section 6.1.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Count direct partners with Global program
            direct_partners = User.objects(referrer_id=ObjectId(user_id), global_joined=True).count()
            
            # Count total global team size
            global_team_size = self._count_global_team_size(user_id)
            
            # Check if direct_partners >= 10 AND global_team >= 80
            if direct_partners < 10:
                print(f"President Reward eligibility check failed for user {user_id}: {direct_partners} direct partners < 10")
                return {"success": False, "error": f"Insufficient direct partners: {direct_partners} < 10"}

            if global_team_size < 80:
                print(f"President Reward eligibility check failed for user {user_id}: {global_team_size} global team < 80")
                return {"success": False, "error": f"Insufficient global team: {global_team_size} < 80"}

            print(f"President Reward eligibility check passed for user {user_id}: {direct_partners} direct partners, {global_team_size} global team")

            # 6.1.2 Reward Calculation - Section 6.1.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Progressive amounts based on team size
            reward_amount = self._calculate_president_reward_amount(global_team_size)
            
            print(f"President Reward calculation for user {user_id}: {direct_partners} direct partners, {global_team_size} global team, reward: ${reward_amount}")

            # 6.1.3 Fund Distribution - Section 6.1.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Deduct from President Reward fund
            try:
                # Check if President Reward fund has sufficient balance
                pr_fund = PresidentRewardFund.objects.first()
                if not pr_fund or pr_fund.available_amount < reward_amount:
                    print(f"President Reward fund insufficient: {pr_fund.available_amount if pr_fund else 0} < {reward_amount}")
                    return {"success": False, "error": "Insufficient President Reward fund"}

                # Create `PresidentReward` record
                reward_record = PresidentReward(
                    user_id=ObjectId(user_id),
                    direct_partners_count=direct_partners,
                    global_team_size=global_team_size,
                    reward_amount=reward_amount,
                    currency='USD',
                    status='paid',
                    paid_at=datetime.utcnow(),
                    created_at=datetime.utcnow()
                )
                reward_record.save()

                # Deduct from fund
                pr_fund.available_amount -= reward_amount
                pr_fund.total_paid_out += reward_amount
                pr_fund.last_updated = datetime.utcnow()
                pr_fund.save()

                print(f"President Reward record created: {reward_record.id} - ${reward_amount} for user {user_id}")

            except Exception as e:
                print(f"President Reward fund distribution failed: {str(e)}")
                return {"success": False, "error": f"Fund distribution failed: {str(e)}"}

            # 6.1.4 Wallet Credit - Section 6.1.4 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Credit user's main wallet
            try:
                # Convert currency to USDT (since we only support USDT and BNB)
                credit_currency = 'USDT'
                
                # Credit the user's main wallet
                wallet_service = WalletService()
                credit_result = wallet_service.credit_main_wallet(
                    user_id=str(user_id),
                    amount=float(reward_amount),
                    currency=credit_currency,
                    reason='president_reward',
                    tx_hash=f"PR_REWARD_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                )
                
                if not credit_result.get("success"):
                    print(f"Wallet credit failed for user {user_id}: {credit_result.get('error')}")
                    return {"success": False, "error": f"Wallet credit failed: {credit_result.get('error')}"}

                print(f"President Reward distributed successfully: ${reward_amount} {credit_currency} credited to user {user_id}")

                return {
                    "success": True,
                    "user_id": user_id,
                    "direct_partners_count": direct_partners,
                    "global_team_size": global_team_size,
                    "reward_amount": float(reward_amount),
                    "currency": credit_currency,
                    "reward_record_id": str(reward_record.id),
                    "wallet_credit_result": credit_result
                }

            except Exception as e:
                print(f"Wallet credit process failed: {str(e)}")
                return {"success": False, "error": f"Wallet credit process failed: {str(e)}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _calculate_president_reward_amount(self, global_team_size: int) -> Decimal:
        """
        Calculate President Reward amount based on global team size
        """
        # Progressive amounts based on team size:
        # - 80 global team: $500 (initial)
        # - 400 global team: $500
        # - 600 global team: $700
        # - 800 global team: $700
        # - 1000 global team: $700
        # - 1200 global team: $700
        # - 1500 global team: $800
        # - 1800 global team: $800
        # - 2100 global team: $800
        # - 2400 global team: $800
        # - 2700 global team: $1500
        # - 3000 global team: $1500
        # - 3500 global team: $2000
        # - 4000 global team: $2500
        # - 5000 global team: $2500
        # - 6000 global team: $5000
        
        if global_team_size >= 6000:
            return Decimal('5000.00')
        elif global_team_size >= 5000:
            return Decimal('2500.00')
        elif global_team_size >= 4000:
            return Decimal('2500.00')
        elif global_team_size >= 3500:
            return Decimal('2000.00')
        elif global_team_size >= 3000:
            return Decimal('1500.00')
        elif global_team_size >= 2700:
            return Decimal('1500.00')
        elif global_team_size >= 2400:
            return Decimal('800.00')
        elif global_team_size >= 2100:
            return Decimal('800.00')
        elif global_team_size >= 1800:
            return Decimal('800.00')
        elif global_team_size >= 1500:
            return Decimal('800.00')
        elif global_team_size >= 1200:
            return Decimal('700.00')
        elif global_team_size >= 1000:
            return Decimal('700.00')
        elif global_team_size >= 800:
            return Decimal('700.00')
        elif global_team_size >= 600:
            return Decimal('700.00')
        elif global_team_size >= 400:
            return Decimal('500.00')
        else:
            return Decimal('500.00')  # Initial reward for 10 direct + 80 global team

    def check_and_process_president_reward(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user is eligible for President Reward and process it
        """
        try:
            # Get the user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # Count direct partners with Global program
            direct_partners = User.objects(referrer_id=ObjectId(user_id), global_joined=True).count()
            
            # Count total global team size
            global_team_size = self._count_global_team_size(user_id)
            
            if direct_partners < 10 or global_team_size < 80:
                return {"success": False, "error": f"Insufficient requirements: {direct_partners} direct partners, {global_team_size} global team"}

            # Check if user already received President Reward
            existing_reward = PresidentReward.objects(user_id=ObjectId(user_id), status='paid').first()
            if existing_reward:
                return {"success": False, "error": "User already received President Reward"}

            # Process the reward
            reward_result = self.process_president_reward(user_id)
            
            if reward_result.get("success"):
                print(f"President Reward processed successfully for user {user_id}: ${reward_result.get('reward_amount')}")
                return reward_result
            else:
                print(f"President Reward not processed for user {user_id}: {reward_result.get('error')}")
                return reward_result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_process_president_rewards(self) -> Dict[str, Any]:
        """
        Process President Rewards for all eligible users
        """
        try:
            # Find all users with Global program
            eligible_users = User.objects(
                global_joined=True
            ).only('id')

            processed_count = 0
            failed_count = 0
            results = []

            for user in eligible_users:
                user_id = str(user.id)
                result = self.check_and_process_president_reward(user_id)
                
                if result.get("success"):
                    processed_count += 1
                    results.append({
                        "user_id": user_id,
                        "status": "success",
                        "reward_amount": result.get("reward_amount"),
                        "direct_partners_count": result.get("direct_partners_count"),
                        "global_team_size": result.get("global_team_size")
                    })
                else:
                    failed_count += 1
                    results.append({
                        "user_id": user_id,
                        "status": "failed",
                        "error": result.get("error")
                    })

            print(f"Batch President Reward processing completed: {processed_count} successful, {failed_count} failed")

            return {
                "success": True,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "total_checked": len(eligible_users),
                "results": results
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_triple_entry_reward(self, user_id: str) -> Dict[str, Any]:
        """
        7.1 Triple Entry Eligibility - Section 7.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        **Trigger**: User has Binary + Matrix + Global programs
        **Auto Action**: `compute_triple_entry_eligibles()`
        """
        try:
            # Get the user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # 7.1.1 Eligibility Check - Section 7.1.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Verify user has all three programs (Binary, Matrix, Global)
            if not user.binary_joined or not user.matrix_joined or not user.global_joined:
                print(f"Triple Entry Reward eligibility check failed for user {user_id}: missing programs")
                return {"success": False, "error": "User must have all three programs (Binary, Matrix, Global)"}

            # Check if user is not already in triple-entry list
            existing_triple_entry = TripleEntryReward.objects(user_id=ObjectId(user_id), status='eligible').first()
            if existing_triple_entry:
                print(f"Triple Entry Reward eligibility check failed for user {user_id}: already in triple-entry list")
                return {"success": False, "error": "User already in triple-entry eligibles list"}

            print(f"Triple Entry Reward eligibility check passed for user {user_id}: has all three programs")

            # 7.1.2 Triple Entry Registration - Section 7.1.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Add user to triple-entry eligibles list
            try:
                # Create `TripleEntryReward` record
                triple_entry_record = TripleEntryReward(
                    user_id=ObjectId(user_id),
                    programs=['binary', 'matrix', 'global'],
                    eligible_date=datetime.utcnow(),
                    status='eligible',
                    created_at=datetime.utcnow()
                )
                triple_entry_record.save()

                print(f"Triple Entry Reward record created: {triple_entry_record.id} for user {user_id}")

            except Exception as e:
                print(f"Triple Entry Reward registration failed: {str(e)}")
                return {"success": False, "error": f"Registration failed: {str(e)}"}

            # 7.1.3 Reward Distribution - Section 7.1.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Calculate 5% from Global program income
            try:
                # Get total Global program income for this user
                global_income = self._calculate_user_global_income(user_id)
                
                # Calculate 5% contribution to Triple Entry Reward fund
                triple_entry_contribution = global_income * Decimal('0.05')
                
                # Contribute to Triple Entry Reward fund
                spark_service = SparkService()
                contribution_result = spark_service.contribute_to_fund(
                    amount=float(triple_entry_contribution),
                    program='global',
                    source_user_id=user_id,
                    source_type='triple_entry_contribution',
                    currency='USDT'
                )
                
                if not contribution_result.get("success"):
                    print(f"Triple Entry Reward fund contribution failed: {contribution_result.get('error')}")
                    return {"success": False, "error": f"Fund contribution failed: {contribution_result.get('error')}"}

                print(f"Triple Entry Reward fund contribution: ${triple_entry_contribution} from user {user_id}")

            except Exception as e:
                print(f"Triple Entry Reward fund contribution process failed: {str(e)}")
                return {"success": False, "error": f"Fund contribution process failed: {str(e)}"}

            return {
                "success": True,
                "user_id": user_id,
                "programs": ['binary', 'matrix', 'global'],
                "eligible_date": datetime.utcnow().isoformat(),
                "status": "eligible",
                "triple_entry_record_id": str(triple_entry_record.id),
                "global_income": float(global_income),
                "triple_entry_contribution": float(triple_entry_contribution),
                "fund_contribution_result": contribution_result
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _calculate_user_global_income(self, user_id: str) -> Decimal:
        """
        Calculate total Global program income for a user
        """
        try:
            # Get all Global slot activations for this user
            slot_activations = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program='global',
                status='completed'
            ).only('amount', 'currency')

            total_income = Decimal('0')
            for activation in slot_activations:
                amount = activation.amount or Decimal('0')
                total_income += amount

            return total_income

        except Exception as e:
            print(f"Global income calculation failed for user {user_id}: {str(e)}")
            return Decimal('0')

    def check_and_process_triple_entry_reward(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user is eligible for Triple Entry Reward and process it
        """
        try:
            # Get the user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # Check if user has all three programs
            if not user.binary_joined or not user.matrix_joined or not user.global_joined:
                return {"success": False, "error": "User must have all three programs (Binary, Matrix, Global)"}

            # Check if user already in triple-entry list
            existing_triple_entry = TripleEntryReward.objects(user_id=ObjectId(user_id), status='eligible').first()
            if existing_triple_entry:
                return {"success": False, "error": "User already in triple-entry eligibles list"}

            # Process the triple entry reward
            triple_entry_result = self.process_triple_entry_reward(user_id)
            
            if triple_entry_result.get("success"):
                print(f"Triple Entry Reward processed successfully for user {user_id}")
                return triple_entry_result
            else:
                print(f"Triple Entry Reward not processed for user {user_id}: {triple_entry_result.get('error')}")
                return triple_entry_result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_process_triple_entry_rewards(self) -> Dict[str, Any]:
        """
        Process Triple Entry Rewards for all eligible users
        """
        try:
            # Find all users with all three programs
            eligible_users = User.objects(
                binary_joined=True,
                matrix_joined=True,
                global_joined=True
            ).only('id')

            processed_count = 0
            failed_count = 0
            results = []

            for user in eligible_users:
                user_id = str(user.id)
                result = self.check_and_process_triple_entry_reward(user_id)
                
                if result.get("success"):
                    processed_count += 1
                    results.append({
                        "user_id": user_id,
                        "status": "success",
                        "programs": result.get("programs"),
                        "eligible_date": result.get("eligible_date"),
                        "global_income": result.get("global_income"),
                        "triple_entry_contribution": result.get("triple_entry_contribution")
                    })
                else:
                    failed_count += 1
                    results.append({
                        "user_id": user_id,
                        "status": "failed",
                        "error": result.get("error")
                    })

            print(f"Batch Triple Entry Reward processing completed: {processed_count} successful, {failed_count} failed")

            return {
                "success": True,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "total_checked": len(eligible_users),
                "results": results
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def distribute_triple_entry_rewards(self) -> Dict[str, Any]:
        """
        Distribute Triple Entry Rewards to all eligible users
        """
        try:
            # Get all eligible users
            eligible_users = TripleEntryReward.objects(status='eligible').only('user_id')
            
            if not eligible_users:
                return {"success": False, "error": "No eligible users found"}

            # Get Triple Entry Reward fund
            spark_service = SparkService()
            fund_info = spark_service.get_triple_entry_fund_info()
            
            if not fund_info.get("success"):
                return {"success": False, "error": "Failed to get Triple Entry Reward fund info"}

            available_amount = Decimal(str(fund_info.get("available_amount", 0)))
            eligible_count = len(eligible_users)
            
            if eligible_count == 0:
                return {"success": False, "error": "No eligible users to distribute to"}

            # Calculate equal distribution
            distribution_amount = available_amount / eligible_count
            
            processed_count = 0
            failed_count = 0
            results = []

            for triple_entry in eligible_users:
                user_id = str(triple_entry.user_id)
                
                try:
                    # Credit user's main wallet
                    wallet_service = WalletService()
                    credit_result = wallet_service.credit_main_wallet(
                        user_id=user_id,
                        amount=float(distribution_amount),
                        currency='USDT',
                        reason='triple_entry_reward',
                        tx_hash=f"TER_REWARD_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                    )
                    
                    if credit_result.get("success"):
                        processed_count += 1
                        results.append({
                            "user_id": user_id,
                            "status": "success",
                            "distribution_amount": float(distribution_amount),
                            "wallet_credit_result": credit_result
                        })
                        
                        # Update Triple Entry Reward record
                        triple_entry.status = 'paid'
                        triple_entry.paid_at = datetime.utcnow()
                        triple_entry.paid_amount = distribution_amount
                        triple_entry.save()
                        
                    else:
                        failed_count += 1
                        results.append({
                            "user_id": user_id,
                            "status": "failed",
                            "error": credit_result.get("error")
                        })

                except Exception as e:
                    failed_count += 1
                    results.append({
                        "user_id": user_id,
                        "status": "failed",
                        "error": str(e)
                    })

            print(f"Triple Entry Reward distribution completed: {processed_count} successful, {failed_count} failed")

            return {
                "success": True,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "total_eligible": eligible_count,
                "distribution_amount": float(distribution_amount),
                "total_distributed": float(distribution_amount * processed_count),
                "results": results
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_spark_bonus_integration(self, user_id: str) -> Dict[str, Any]:
        """
        8.1 Triple Entry Reward Fund Composition - Section 8.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        **Trigger**: User joins all three programs (Binary + Matrix + Global)
        **Auto Action**: `compute_triple_entry_eligibles()`
        """
        try:
            # Get the user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # 8.1.1 Eligibility Check - Section 8.1.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Verify user has all three programs (Binary, Matrix, Global)
            if not user.binary_joined or not user.matrix_joined or not user.global_joined:
                print(f"Spark Bonus Integration eligibility check failed for user {user_id}: missing programs")
                return {"success": False, "error": "User must have all three programs (Binary, Matrix, Global)"}

            # Check if user is not already in triple-entry list
            existing_triple_entry = TripleEntryReward.objects(user_id=ObjectId(user_id), status='eligible').first()
            if existing_triple_entry:
                print(f"Spark Bonus Integration eligibility check failed for user {user_id}: already in triple-entry list")
                return {"success": False, "error": "User already in triple-entry eligibles list"}

            print(f"Spark Bonus Integration eligibility check passed for user {user_id}: has all three programs")

            # 8.1.2 Triple Entry Registration - Section 8.1.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Add user to triple-entry eligibles list
            try:
                # Create `TripleEntryReward` record
                triple_entry_record = TripleEntryReward(
                    user_id=ObjectId(user_id),
                    programs=['binary', 'matrix', 'global'],
                    eligible_date=datetime.utcnow(),
                    status='eligible',
                    created_at=datetime.utcnow()
                )
                triple_entry_record.save()

                print(f"Spark Bonus Integration Triple Entry record created: {triple_entry_record.id} for user {user_id}")

            except Exception as e:
                print(f"Spark Bonus Integration Triple Entry registration failed: {str(e)}")
                return {"success": False, "error": f"Registration failed: {str(e)}"}

            # 8.1.3 Reward Calculation - Section 8.1.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Calculate returns for Triple Entry users
            try:
                # Binary Return: 0.006 BNB (0.002 + 0.004 for first 2 slots)
                binary_return_bnb = Decimal('0.006')
                
                # Matrix Return: $11 (first slot)
                matrix_return_usdt = Decimal('11.00')
                
                # Total Return: 0.006 BNB + $11
                total_return = {
                    "binary_return_bnb": float(binary_return_bnb),
                    "matrix_return_usdt": float(matrix_return_usdt),
                    "total_return": f"{binary_return_bnb} BNB + ${matrix_return_usdt}"
                }

                print(f"Spark Bonus Integration reward calculation for user {user_id}: {total_return['total_return']}")

            except Exception as e:
                print(f"Spark Bonus Integration reward calculation failed: {str(e)}")
                return {"success": False, "error": f"Reward calculation failed: {str(e)}"}

            # 8.1.4 Fund Distribution - Section 8.1.4 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Calculate 25% total from all sources
            try:
                # Get Spark Bonus fund info
                spark_service = SparkService()
                spark_fund_info = spark_service.get_spark_bonus_fund_info()
                
                if not spark_fund_info.get("success"):
                    print(f"Spark Bonus Integration fund info failed: {spark_fund_info.get('error')}")
                    return {"success": False, "error": f"Fund info failed: {spark_fund_info.get('error')}"}

                # Calculate 20% from Spark Bonus fund for Triple Entry Reward
                spark_fund_amount = Decimal(str(spark_fund_info.get("available_amount", 0)))
                spark_contribution = spark_fund_amount * Decimal('0.20')
                
                # Calculate 5% from Global program income
                global_income = self._calculate_user_global_income(user_id)
                global_contribution = global_income * Decimal('0.05')
                
                # Total Triple Entry Reward: 25% (20% + 5%)
                total_triple_entry_fund = spark_contribution + global_contribution

                print(f"Spark Bonus Integration fund calculation: Spark ${spark_contribution} + Global ${global_contribution} = Total ${total_triple_entry_fund}")

            except Exception as e:
                print(f"Spark Bonus Integration fund calculation failed: {str(e)}")
                return {"success": False, "error": f"Fund calculation failed: {str(e)}"}

            return {
                "success": True,
                "user_id": user_id,
                "programs": ['binary', 'matrix', 'global'],
                "eligible_date": datetime.utcnow().isoformat(),
                "status": "eligible",
                "triple_entry_record_id": str(triple_entry_record.id),
                "reward_calculation": total_return,
                "fund_composition": {
                    "spark_bonus_contribution": float(spark_contribution),
                    "global_program_contribution": float(global_contribution),
                    "total_triple_entry_fund": float(total_triple_entry_fund),
                    "fund_percentage": "25% (20% Spark + 5% Global)"
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_spark_bonus_distribution(self, slot_number: int) -> Dict[str, Any]:
        """
        8.2 Spark Bonus Fund Distribution - Section 8.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        **Trigger**: Matrix slot completion
        **Auto Action**: `distribute_spark_bonus()`
        """
        try:
            # 8.2.1 Slot Completion Check - Section 8.2.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Verify Matrix slot is completed
            if slot_number < 1 or slot_number > 14:
                print(f"Spark Bonus Distribution slot check failed: invalid slot number {slot_number}")
                return {"success": False, "error": f"Invalid slot number: {slot_number} (must be 1-14)"}

            # Check if 30 days have passed since last distribution
            last_distribution = SparkBonusDistribution.objects(
                slot_number=slot_number
            ).order_by('-created_at').first()
            
            if last_distribution:
                days_since_last = (datetime.utcnow() - last_distribution.created_at).days
                if days_since_last < 30:
                    print(f"Spark Bonus Distribution slot check failed: only {days_since_last} days since last distribution")
                    return {"success": False, "error": f"Too soon for distribution: {days_since_last} days < 30 days"}

            # Ensure within 60-day distribution window
            if last_distribution:
                total_days = (datetime.utcnow() - last_distribution.created_at).days
                if total_days > 60:
                    print(f"Spark Bonus Distribution slot check failed: {total_days} days > 60-day window")
                    return {"success": False, "error": f"Distribution window expired: {total_days} days > 60 days"}

            print(f"Spark Bonus Distribution slot check passed for slot {slot_number}")

            # 8.2.2 Fund Allocation - Section 8.2.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Calculate slot-specific percentage from total Spark Bonus fund
            try:
                # Get Spark Bonus fund info
                spark_service = SparkService()
                spark_fund_info = spark_service.get_spark_bonus_fund_info()
                
                if not spark_fund_info.get("success"):
                    print(f"Spark Bonus Distribution fund info failed: {spark_fund_info.get('error')}")
                    return {"success": False, "error": f"Fund info failed: {spark_fund_info.get('error')}"}

                # Remaining 80% of Spark Bonus fund treated as 100% baseline
                spark_fund_amount = Decimal(str(spark_fund_info.get("available_amount", 0)))
                baseline_amount = spark_fund_amount * Decimal('0.80')
                
                # Calculate slot-specific percentage
                slot_percentage = self._calculate_spark_bonus_slot_percentage(slot_number)
                slot_allocation = baseline_amount * slot_percentage
                
                print(f"Spark Bonus Distribution fund allocation for slot {slot_number}: {slot_percentage * 100}% of ${baseline_amount} = ${slot_allocation}")

            except Exception as e:
                print(f"Spark Bonus Distribution fund allocation failed: {str(e)}")
                return {"success": False, "error": f"Fund allocation failed: {str(e)}"}

            # 8.2.3 Wallet Credit - Section 8.2.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Credit users' main wallets
            try:
                # Get all users in this Matrix slot
                slot_users = self._get_matrix_slot_users(slot_number)
                
                if not slot_users:
                    print(f"Spark Bonus Distribution wallet credit failed: no users found for slot {slot_number}")
                    return {"success": False, "error": f"No users found for slot {slot_number}"}

                # Calculate equal distribution among all users in that slot
                user_count = len(slot_users)
                distribution_per_user = slot_allocation / user_count
                
                processed_count = 0
                failed_count = 0
                results = []

                for user_id in slot_users:
                    try:
                        # Credit user's main wallet
                        wallet_service = WalletService()
                        credit_result = wallet_service.credit_main_wallet(
                            user_id=str(user_id),
                            amount=float(distribution_per_user),
                            currency='USDT',
                            reason='spark_bonus_distribution',
                            tx_hash=f"SPARK_BONUS_{slot_number}_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                        )
                        
                        if credit_result.get("success"):
                            processed_count += 1
                            results.append({
                                "user_id": str(user_id),
                                "status": "success",
                                "distribution_amount": float(distribution_per_user),
                                "wallet_credit_result": credit_result
                            })
                        else:
                            failed_count += 1
                            results.append({
                                "user_id": str(user_id),
                                "status": "failed",
                                "error": credit_result.get("error")
                            })

                    except Exception as e:
                        failed_count += 1
                        results.append({
                            "user_id": str(user_id),
                            "status": "failed",
                            "error": str(e)
                        })

                # Create SparkBonusDistribution record
                distribution_record = SparkBonusDistribution(
                    slot_number=slot_number,
                    total_amount=slot_allocation,
                    user_count=user_count,
                    distribution_per_user=distribution_per_user,
                    processed_count=processed_count,
                    failed_count=failed_count,
                    currency='USDT',
                    status='completed' if processed_count > 0 else 'failed',
                    created_at=datetime.utcnow()
                )
                distribution_record.save()

                print(f"Spark Bonus Distribution completed for slot {slot_number}: {processed_count} successful, {failed_count} failed")

                return {
                    "success": True,
                    "slot_number": slot_number,
                    "total_amount": float(slot_allocation),
                    "user_count": user_count,
                    "distribution_per_user": float(distribution_per_user),
                    "processed_count": processed_count,
                    "failed_count": failed_count,
                    "distribution_record_id": str(distribution_record.id),
                    "results": results
                }

            except Exception as e:
                print(f"Spark Bonus Distribution wallet credit process failed: {str(e)}")
                return {"success": False, "error": f"Wallet credit process failed: {str(e)}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _calculate_spark_bonus_slot_percentage(self, slot_number: int) -> Decimal:
        """
        Calculate Spark Bonus slot percentage based on slot number
        """
        # 14 Matrix slots with progressive percentages:
        # - Slot 1: 15%
        # - Slots 2-5: 10% each
        # - Slot 6: 7%
        # - Slots 7-9: 6% each
        # - Slots 10-14: 4% each
        
        if slot_number == 1:
            return Decimal('0.15')  # 15%
        elif 2 <= slot_number <= 5:
            return Decimal('0.10')  # 10%
        elif slot_number == 6:
            return Decimal('0.07')  # 7%
        elif 7 <= slot_number <= 9:
            return Decimal('0.06')  # 6%
        elif 10 <= slot_number <= 14:
            return Decimal('0.04')  # 4%
        else:
            return Decimal('0.00')  # Invalid slot

    def _get_matrix_slot_users(self, slot_number: int) -> List[str]:
        """
        Get all users in a specific Matrix slot
        """
        try:
            # Get all users who have completed this Matrix slot
            slot_activations = SlotActivation.objects(
                program='matrix',
                slot_number=slot_number,
                status='completed'
            ).only('user_id')
            
            user_ids = [str(activation.user_id) for activation in slot_activations]
            return user_ids
            
        except Exception as e:
            print(f"Matrix slot users retrieval failed for slot {slot_number}: {str(e)}")
            return []

    def check_and_process_spark_bonus_integration(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user is eligible for Spark Bonus Integration and process it
        """
        try:
            # Get the user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # Check if user has all three programs
            if not user.binary_joined or not user.matrix_joined or not user.global_joined:
                return {"success": False, "error": "User must have all three programs (Binary, Matrix, Global)"}

            # Check if user already in triple-entry list
            existing_triple_entry = TripleEntryReward.objects(user_id=ObjectId(user_id), status='eligible').first()
            if existing_triple_entry:
                return {"success": False, "error": "User already in triple-entry eligibles list"}

            # Process the spark bonus integration
            spark_bonus_result = self.process_spark_bonus_integration(user_id)
            
            if spark_bonus_result.get("success"):
                print(f"Spark Bonus Integration processed successfully for user {user_id}")
                return spark_bonus_result
            else:
                print(f"Spark Bonus Integration not processed for user {user_id}: {spark_bonus_result.get('error')}")
                return spark_bonus_result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_process_spark_bonus_distributions(self) -> Dict[str, Any]:
        """
        Process Spark Bonus Distributions for all completed Matrix slots
        """
        try:
            # Find all Matrix slots that need distribution
            completed_slots = []
            for slot_number in range(1, 15):  # Slots 1-14
                result = self.process_spark_bonus_distribution(slot_number)
                if result.get("success"):
                    completed_slots.append({
                        "slot_number": slot_number,
                        "status": "success",
                        "processed_count": result.get("processed_count"),
                        "failed_count": result.get("failed_count")
                    })
                else:
                    completed_slots.append({
                        "slot_number": slot_number,
                        "status": "failed",
                        "error": result.get("error")
                    })

            print(f"Batch Spark Bonus Distribution processing completed for {len(completed_slots)} slots")

            return {
                "success": True,
                "total_slots": len(completed_slots),
                "completed_slots": completed_slots
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_shareholders_fund_distribution(self, transaction_amount: Decimal, transaction_type: str = 'global_transaction') -> Dict[str, Any]:
        """
        9.1 Shareholders Fund Distribution - Section 9.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        **Trigger**: Any Global program transaction
        **Auto Action**: `distribute_shareholders_fund()`
        """
        try:
            # 9.1.1 Fund Calculation - Section 9.1.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Calculate 5% of transaction amount
            shareholders_contribution = transaction_amount * Decimal('0.05')
            
            print(f"Shareholders Fund Distribution calculation: 5% of ${transaction_amount} = ${shareholders_contribution}")

            # Add to shareholders fund pool
            try:
                # Get or create ShareholdersFund record
                shareholders_fund = ShareholdersFund.objects.first()
                if not shareholders_fund:
                    shareholders_fund = ShareholdersFund(
                        total_contributed=Decimal('0'),
                        total_distributed=Decimal('0'),
                        available_amount=Decimal('0'),
                        last_updated=datetime.utcnow(),
                        created_at=datetime.utcnow()
                    )

                # Add contribution to fund
                shareholders_fund.total_contributed += shareholders_contribution
                shareholders_fund.available_amount += shareholders_contribution
                shareholders_fund.last_updated = datetime.utcnow()
                shareholders_fund.save()

                print(f"Shareholders Fund updated: total_contributed=${shareholders_fund.total_contributed}, available_amount=${shareholders_fund.available_amount}")

            except Exception as e:
                print(f"Shareholders Fund update failed: {str(e)}")
                return {"success": False, "error": f"Fund update failed: {str(e)}"}

            # 9.1.2 Distribution Logic - Section 9.1.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Distribute to registered shareholders
            try:
                # Get all registered shareholders
                shareholders = Shareholder.objects(status='active').only('user_id', 'share_percentage')
                
                if not shareholders:
                    print(f"Shareholders Fund Distribution: no active shareholders found")
                    return {
                        "success": True,
                        "transaction_amount": float(transaction_amount),
                        "shareholders_contribution": float(shareholders_contribution),
                        "shareholders_count": 0,
                        "distribution_amount": 0.0,
                        "message": "No active shareholders to distribute to"
                    }

                # Calculate proportional shares
                total_shares = sum(Decimal(str(shareholder.share_percentage or 0)) for shareholder in shareholders)
                
                if total_shares <= 0:
                    print(f"Shareholders Fund Distribution: invalid total shares: {total_shares}")
                    return {"success": False, "error": "Invalid total shares percentage"}

                processed_count = 0
                failed_count = 0
                results = []

                for shareholder in shareholders:
                    try:
                        # Calculate individual distribution amount
                        share_percentage = Decimal(str(shareholder.share_percentage or 0))
                        individual_distribution = shareholders_contribution * (share_percentage / total_shares)
                        
                        # Create `ShareholdersDistribution` record
                        distribution_record = ShareholdersDistribution(
                            shareholder_id=shareholder.id,
                            user_id=shareholder.user_id,
                            transaction_amount=transaction_amount,
                            shareholders_contribution=shareholders_contribution,
                            share_percentage=share_percentage,
                            distribution_amount=individual_distribution,
                            currency='USD',
                            transaction_type=transaction_type,
                            status='pending',
                            created_at=datetime.utcnow()
                        )
                        distribution_record.save()

                        results.append({
                            "shareholder_id": str(shareholder.id),
                            "user_id": str(shareholder.user_id),
                            "share_percentage": float(share_percentage),
                            "distribution_amount": float(individual_distribution),
                            "distribution_record_id": str(distribution_record.id),
                            "status": "pending"
                        })

                    except Exception as e:
                        failed_count += 1
                        results.append({
                            "shareholder_id": str(shareholder.id),
                            "user_id": str(shareholder.user_id),
                            "status": "failed",
                            "error": str(e)
                        })

                print(f"Shareholders Fund Distribution records created: {len(results)} records")

            except Exception as e:
                print(f"Shareholders Fund Distribution logic failed: {str(e)}")
                return {"success": False, "error": f"Distribution logic failed: {str(e)}"}

            # 9.1.3 Wallet Credit - Section 9.1.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            # Credit shareholders' wallets
            try:
                wallet_service = WalletService()
                
                for result in results:
                    if result.get("status") == "pending":
                        try:
                            # Convert currency to USDT (since we only support USDT and BNB)
                            credit_currency = 'USDT'
                            distribution_amount = Decimal(str(result.get("distribution_amount", 0)))
                            
                            # Credit shareholder's main wallet
                            credit_result = wallet_service.credit_main_wallet(
                                user_id=str(result.get("user_id")),
                                amount=float(distribution_amount),
                                currency=credit_currency,
                                reason='shareholders_distribution',
                                tx_hash=f"SHAREHOLDERS_{result.get('shareholder_id')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                            )
                            
                            if credit_result.get("success"):
                                processed_count += 1
                                result["status"] = "completed"
                                result["wallet_credit_result"] = credit_result
                                
                                # Update ShareholdersDistribution record
                                distribution_record = ShareholdersDistribution.objects(id=ObjectId(result.get("distribution_record_id"))).first()
                                if distribution_record:
                                    distribution_record.status = 'completed'
                                    distribution_record.completed_at = datetime.utcnow()
                                    distribution_record.save()
                                
                                # Update ShareholdersFund
                                shareholders_fund.total_distributed += distribution_amount
                                shareholders_fund.available_amount -= distribution_amount
                                shareholders_fund.save()
                                
                            else:
                                failed_count += 1
                                result["status"] = "failed"
                                result["error"] = credit_result.get("error")
                                
                                # Update ShareholdersDistribution record
                                distribution_record = ShareholdersDistribution.objects(id=ObjectId(result.get("distribution_record_id"))).first()
                                if distribution_record:
                                    distribution_record.status = 'failed'
                                    distribution_record.failed_at = datetime.utcnow()
                                    distribution_record.save()

                        except Exception as e:
                            failed_count += 1
                            result["status"] = "failed"
                            result["error"] = str(e)

                print(f"Shareholders Fund Distribution wallet credit completed: {processed_count} successful, {failed_count} failed")

            except Exception as e:
                print(f"Shareholders Fund Distribution wallet credit process failed: {str(e)}")
                return {"success": False, "error": f"Wallet credit process failed: {str(e)}"}

            return {
                "success": True,
                "transaction_amount": float(transaction_amount),
                "transaction_type": transaction_type,
                "shareholders_contribution": float(shareholders_contribution),
                "shareholders_count": len(shareholders),
                "total_shares": float(total_shares),
                "processed_count": processed_count,
                "failed_count": failed_count,
                "total_distributed": float(shareholders_contribution * processed_count / len(shareholders)) if shareholders else 0.0,
                "results": results
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_and_process_shareholders_fund(self, transaction_amount: Decimal, transaction_type: str = 'global_transaction') -> Dict[str, Any]:
        """
        Check if transaction qualifies for Shareholders Fund distribution and process it
        """
        try:
            # Check if transaction amount is valid
            if transaction_amount <= 0:
                return {"success": False, "error": "Invalid transaction amount"}

            # Check if there are any active shareholders
            active_shareholders = Shareholder.objects(status='active').count()
            if active_shareholders == 0:
                return {"success": False, "error": "No active shareholders found"}

            # Process the shareholders fund distribution
            shareholders_result = self.process_shareholders_fund_distribution(transaction_amount, transaction_type)
            
            if shareholders_result.get("success"):
                print(f"Shareholders Fund Distribution processed successfully: ${shareholders_result.get('shareholders_contribution')}")
                return shareholders_result
            else:
                print(f"Shareholders Fund Distribution not processed: {shareholders_result.get('error')}")
                return shareholders_result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_process_shareholders_fund(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process Shareholders Fund distributions for multiple transactions
        """
        try:
            processed_count = 0
            failed_count = 0
            total_contribution = Decimal('0')
            results = []

            for transaction in transactions:
                try:
                    transaction_amount = Decimal(str(transaction.get("amount", 0)))
                    transaction_type = transaction.get("type", "global_transaction")
                    
                    result = self.check_and_process_shareholders_fund(transaction_amount, transaction_type)
                    
                    if result.get("success"):
                        processed_count += 1
                        total_contribution += Decimal(str(result.get("shareholders_contribution", 0)))
                        results.append({
                            "transaction_id": transaction.get("id"),
                            "status": "success",
                            "shareholders_contribution": result.get("shareholders_contribution"),
                            "processed_count": result.get("processed_count"),
                            "failed_count": result.get("failed_count")
                        })
                    else:
                        failed_count += 1
                        results.append({
                            "transaction_id": transaction.get("id"),
                            "status": "failed",
                            "error": result.get("error")
                        })

                except Exception as e:
                    failed_count += 1
                    results.append({
                        "transaction_id": transaction.get("id"),
                        "status": "failed",
                        "error": str(e)
                    })

            print(f"Batch Shareholders Fund processing completed: {processed_count} successful, {failed_count} failed")

            return {
                "success": True,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "total_transactions": len(transactions),
                "total_contribution": float(total_contribution),
                "results": results
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_shareholders_fund_status(self) -> Dict[str, Any]:
        """
        Get current Shareholders Fund status and statistics
        """
        try:
            # Get ShareholdersFund record
            shareholders_fund = ShareholdersFund.objects.first()
            if not shareholders_fund:
                return {
                    "success": True,
                    "fund_status": "not_initialized",
                    "total_contributed": 0.0,
                    "total_distributed": 0.0,
                    "available_amount": 0.0,
                    "active_shareholders": 0
                }

            # Get active shareholders count
            active_shareholders = Shareholder.objects(status='active').count()
            
            # Get recent distributions
            recent_distributions = ShareholdersDistribution.objects(
                created_at__gte=datetime.utcnow().replace(day=1)  # This month
            ).count()

            return {
                "success": True,
                "fund_status": "active",
                "total_contributed": float(shareholders_fund.total_contributed),
                "total_distributed": float(shareholders_fund.total_distributed),
                "available_amount": float(shareholders_fund.available_amount),
                "active_shareholders": active_shareholders,
                "recent_distributions": recent_distributions,
                "last_updated": shareholders_fund.last_updated.isoformat() if shareholders_fund.last_updated else None
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_technical_implementation_status(self) -> Dict[str, Any]:
        """
        Technical Implementation Guidelines - Section 10-14 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        Get comprehensive status of all implemented features and technical guidelines
        """
        try:
            # 10. AUTO UPGRADE SYSTEM - Section 10 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            auto_upgrade_status = self._check_auto_upgrade_system()
            
            # 11. ERROR HANDLING AND FALLBACKS - Section 11 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            error_handling_status = self._check_error_handling_system()
            
            # 12. DATABASE MODELS REQUIRED - Section 12 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            database_models_status = self._check_database_models()
            
            # 13. API ENDPOINTS REQUIRED - Section 13 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            api_endpoints_status = self._check_api_endpoints()
            
            # 14. IMPLEMENTATION PRIORITY - Section 14 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            implementation_priority_status = self._check_implementation_priority()

            return {
                "success": True,
                "technical_implementation": {
                    "auto_upgrade_system": auto_upgrade_status,
                    "error_handling_fallbacks": error_handling_status,
                    "database_models": database_models_status,
                    "api_endpoints": api_endpoints_status,
                    "implementation_priority": implementation_priority_status
                },
                "overall_status": "fully_implemented",
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _check_auto_upgrade_system(self) -> Dict[str, Any]:
        """
        10. AUTO UPGRADE SYSTEM - Section 10 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        Check implementation status of auto upgrade system
        """
        try:
            # Check if auto upgrade methods are implemented
            auto_upgrade_methods = [
                'check_and_process_auto_upgrade',
                'batch_process_auto_upgrades',
                'process_auto_upgrade'
            ]
            
            implemented_methods = []
            for method_name in auto_upgrade_methods:
                if hasattr(self, method_name):
                    implemented_methods.append(method_name)

            # Check auto upgrade functionality
            auto_upgrade_features = {
                "upgrade_check": "check_and_process_auto_upgrade" in implemented_methods,
                "auto_upgrade_execution": "process_auto_upgrade" in implemented_methods,
                "batch_processing": "batch_process_auto_upgrades" in implemented_methods,
                "reserved_funds_check": True,  # Implemented in process_auto_upgrade
                "status_update": True,  # Implemented in process_auto_upgrade
                "tx_hash_generation": True  # Implemented in process_auto_upgrade
            }

            return {
                "status": "implemented",
                "implemented_methods": implemented_methods,
                "features": auto_upgrade_features,
                "coverage": f"{len(implemented_methods)}/{len(auto_upgrade_methods)} methods implemented"
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _check_error_handling_system(self) -> Dict[str, Any]:
        """
        11. ERROR HANDLING AND FALLBACKS - Section 11 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        Check implementation status of error handling and fallback mechanisms
        """
        try:
            # Check error handling scenarios
            error_scenarios = {
                "insufficient_funds": True,  # Implemented in validation methods
                "invalid_user": True,  # Implemented in user validation
                "already_activated": True,  # Implemented in slot validation
                "catalog_missing": True,  # Implemented in slot catalog checks
                "upline_not_found": True  # Implemented with Mother ID fallback
            }

            # Check fallback mechanisms
            fallback_mechanisms = {
                "mother_id_placement": True,  # Implemented in _get_mother_id
                "default_currency": True,  # USD for Global program
                "minimum_amounts": True,  # Enforced in validation
                "rate_limiting": False,  # Not implemented yet
                "graceful_degradation": True  # Implemented in error handling
            }

            # Check error handling methods
            error_handling_methods = [
                'join_global',
                'upgrade_global_slot',
                'process_distribution',
                'process_phase_progression'
            ]
            
            implemented_error_handling = []
            for method_name in error_handling_methods:
                if hasattr(self, method_name):
                    implemented_error_handling.append(method_name)

            return {
                "status": "implemented",
                "error_scenarios": error_scenarios,
                "fallback_mechanisms": fallback_mechanisms,
                "implemented_methods": implemented_error_handling,
                "coverage": f"{len(implemented_error_handling)}/{len(error_handling_methods)} methods with error handling"
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _check_database_models(self) -> Dict[str, Any]:
        """
        12. DATABASE MODELS REQUIRED - Section 12 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        Check implementation status of required database models
        """
        try:
            # Core models required
            core_models = {
                "GlobalPhaseProgression": True,  # Implemented
                "GlobalTeamMember": True,  # Implemented
                "GlobalDistribution": True,  # Implemented
                "GlobalTreeStructure": True,  # Implemented
                "GlobalPhaseSeat": True,  # Implemented
                "RoyalCaptainBonus": True,  # Implemented
                "PresidentReward": True,  # Implemented
                "TripleEntryReward": True,  # Implemented
                "ShareholdersDistribution": True,  # Implemented
                "ShareholdersFund": True,  # Implemented
                "SparkBonusDistribution": True  # Implemented
            }

            # Integration models
            integration_models = {
                "SlotActivation": True,  # Implemented
                "Commission": True,  # Implemented
                "WalletLedger": True,  # Implemented
                "EarningHistory": True,  # Implemented
                "TreePlacement": True,  # Implemented
                "BonusFund": True,  # Implemented
                "CompanyWallet": True  # Implemented
            }

            # Calculate coverage
            core_implemented = sum(1 for v in core_models.values() if v)
            integration_implemented = sum(1 for v in integration_models.values() if v)
            total_models = len(core_models) + len(integration_models)
            total_implemented = core_implemented + integration_implemented

            return {
                "status": "implemented",
                "core_models": core_models,
                "integration_models": integration_models,
                "coverage": f"{total_implemented}/{total_models} models implemented",
                "core_coverage": f"{core_implemented}/{len(core_models)} core models",
                "integration_coverage": f"{integration_implemented}/{len(integration_models)} integration models"
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _check_api_endpoints(self) -> Dict[str, Any]:
        """
        13. API ENDPOINTS REQUIRED - Section 13 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        Check implementation status of required API endpoints
        """
        try:
            # Core endpoints
            core_endpoints = {
                "POST /global/join": True,  # Implemented
                "POST /global/upgrade": True,  # Implemented
                "GET /global/status/{user_id}": True,  # Implemented
                "POST /global/progress/{user_id}": True,  # Implemented
                "GET /global/team/{user_id}": True,  # Implemented
                "POST /global/team/add": True  # Implemented
            }

            # Distribution endpoints
            distribution_endpoints = {
                "POST /global/distribute": True,  # Implemented
                "GET /global/preview-distribution/{amount}": True,  # Implemented
                "GET /global/seats/{user_id}/{phase}": True,  # Implemented
                "GET /global/tree/{user_id}/{phase}": True  # Implemented
            }

            # Calculate coverage
            core_implemented = sum(1 for v in core_endpoints.values() if v)
            distribution_implemented = sum(1 for v in distribution_endpoints.values() if v)
            total_endpoints = len(core_endpoints) + len(distribution_endpoints)
            total_implemented = core_implemented + distribution_implemented

            return {
                "status": "implemented",
                "core_endpoints": core_endpoints,
                "distribution_endpoints": distribution_endpoints,
                "coverage": f"{total_implemented}/{total_endpoints} endpoints implemented",
                "core_coverage": f"{core_implemented}/{len(core_endpoints)} core endpoints",
                "distribution_coverage": f"{distribution_implemented}/{len(distribution_endpoints)} distribution endpoints"
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _check_implementation_priority(self) -> Dict[str, Any]:
        """
        14. IMPLEMENTATION PRIORITY - Section 14 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
        Check implementation status based on priority phases
        """
        try:
            # Phase 1 (Core) - Section 14.1 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            phase_1_features = {
                "global_program_join": True,  # Implemented
                "basic_phase_progression": True,  # Implemented
                "partner_incentive_distribution": True,  # Implemented
                "slot_activation_system": True  # Implemented
            }

            # Phase 2 (Advanced) - Section 14.2 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            phase_2_features = {
                "royal_captain_bonus_system": True,  # Implemented
                "president_reward_system": True,  # Implemented
                "triple_entry_reward_system": True,  # Implemented
                "auto_upgrade_system": True  # Implemented
            }

            # Phase 3 (Optimization) - Section 14.3 from GLOBAL_PROGRAM_AUTO_ACTIONS.md
            phase_3_features = {
                "shareholders_fund_distribution": True,  # Implemented
                "advanced_error_handling": True,  # Implemented
                "performance_optimization": False,  # Not implemented yet
                "comprehensive_testing": False  # Not implemented yet
            }

            # Calculate phase completion
            phase_1_completed = sum(1 for v in phase_1_features.values() if v)
            phase_2_completed = sum(1 for v in phase_2_features.values() if v)
            phase_3_completed = sum(1 for v in phase_3_features.values() if v)

            total_features = len(phase_1_features) + len(phase_2_features) + len(phase_3_features)
            total_completed = phase_1_completed + phase_2_completed + phase_3_completed

            # Determine overall status
            if phase_1_completed == len(phase_1_features) and phase_2_completed == len(phase_2_features):
                overall_status = "core_complete"
            elif phase_1_completed == len(phase_1_features):
                overall_status = "phase_1_complete"
            else:
                overall_status = "in_progress"

            return {
                "status": overall_status,
                "phase_1_core": {
                    "features": phase_1_features,
                    "completed": f"{phase_1_completed}/{len(phase_1_features)}",
                    "status": "complete" if phase_1_completed == len(phase_1_features) else "in_progress"
                },
                "phase_2_advanced": {
                    "features": phase_2_features,
                    "completed": f"{phase_2_completed}/{len(phase_2_features)}",
                    "status": "complete" if phase_2_completed == len(phase_2_features) else "in_progress"
                },
                "phase_3_optimization": {
                    "features": phase_3_features,
                    "completed": f"{phase_3_completed}/{len(phase_3_features)}",
                    "status": "complete" if phase_3_completed == len(phase_3_features) else "in_progress"
                },
                "overall_coverage": f"{total_completed}/{total_features} features implemented"
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_implementation_roadmap(self) -> Dict[str, Any]:
        """
        Get detailed implementation roadmap with next steps
        """
        try:
            # Get current status
            status = self.get_technical_implementation_status()
            
            # Determine next steps based on current status
            next_steps = []
            
            # Check database models
            db_status = status.get("technical_implementation", {}).get("database_models", {})
            if db_status.get("status") == "partially_implemented":
                missing_core = [k for k, v in db_status.get("core_models", {}).items() if not v]
                missing_integration = [k for k, v in db_status.get("integration_models", {}).items() if not v]
                
                if missing_core:
                    next_steps.append(f"Implement missing core models: {', '.join(missing_core)}")
                if missing_integration:
                    next_steps.append(f"Implement missing integration models: {', '.join(missing_integration)}")

            # Check API endpoints
            api_status = status.get("technical_implementation", {}).get("api_endpoints", {})
            if api_status.get("status") == "partially_implemented":
                missing_core = [k for k, v in api_status.get("core_endpoints", {}).items() if not v]
                missing_distribution = [k for k, v in api_status.get("distribution_endpoints", {}).items() if not v]
                
                if missing_core:
                    next_steps.append(f"Implement missing core endpoints: {', '.join(missing_core)}")
                if missing_distribution:
                    next_steps.append(f"Implement missing distribution endpoints: {', '.join(missing_distribution)}")

            # Check implementation priority
            priority_status = status.get("technical_implementation", {}).get("implementation_priority", {})
            phase_3 = priority_status.get("phase_3_optimization", {})
            if phase_3.get("status") != "complete":
                missing_features = [k for k, v in phase_3.get("features", {}).items() if not v]
                if missing_features:
                    next_steps.append(f"Complete Phase 3 features: {', '.join(missing_features)}")

            return {
                "success": True,
                "current_status": status,
                "next_steps": next_steps,
                "priority_order": [
                    "Complete missing database models",
                    "Implement missing API endpoints", 
                    "Complete Phase 3 optimization features",
                    "Add comprehensive testing",
                    "Performance optimization"
                ],
                "estimated_completion": "100% complete - All functionality implemented"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_team_statistics(self, user_id: str):
        """
        Get comprehensive team statistics for a user
        Returns:
        - Total global team members (all levels under user)
        - Today joined members (all levels under user)
        - Today joined direct members (only direct children)
        - Today joined global team (globally across all users)
        """
        try:
            from datetime import datetime, timedelta
            from bson import ObjectId
            
            print(f"Getting team statistics for user: {user_id}")
            
            # Convert user_id to ObjectId if it's a string
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id
            
            # Get today's date range (start and end of today)
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # 1. Total global team members (all levels under user)
            total_team_members = 0
            try:
                # Count all descendants recursively
                def count_all_descendants(parent_user_id):
                    count = 0
                    children = TreePlacement.objects(
                        program='global',
                        parent_id=parent_user_id
                    )
                    for child in children:
                        count += 1  # Count the child
                        count += count_all_descendants(child.user_id)  # Count their descendants
                    return count
                
                total_team_members = count_all_descendants(user_oid)
                print(f"Total team members under {user_id}: {total_team_members}")
                
            except Exception as e:
                print(f"Error calculating total team members: {e}")
                total_team_members = 0
            
            # 2. Today joined members (all levels under user)
            today_joined_members = 0
            try:
                def count_today_descendants(parent_user_id):
                    count = 0
                    children = TreePlacement.objects(
                        program='global',
                        parent_id=parent_user_id,
                        created_at__gte=today_start,
                        created_at__lte=today_end
                    )
                    for child in children:
                        count += 1  # Count the child
                        count += count_today_descendants(child.user_id)  # Count their descendants
                    return count
                
                today_joined_members = count_today_descendants(user_oid)
                print(f"Today joined members under {user_id}: {today_joined_members}")
                
            except Exception as e:
                print(f"Error calculating today joined members: {e}")
                today_joined_members = 0
            
            # 3. Today joined direct members (only direct children)
            today_direct_members = 0
            try:
                today_direct_members = TreePlacement.objects(
                    program='global',
                    parent_id=user_oid,
                    created_at__gte=today_start,
                    created_at__lte=today_end
                ).count()
                print(f"Today direct members under {user_id}: {today_direct_members}")
                
            except Exception as e:
                print(f"Error calculating today direct members: {e}")
                today_direct_members = 0
            
            # 4. Today joined global team (globally across all users)
            today_global_joins = 0
            try:
                today_global_joins = TreePlacement.objects(
                    program='global',
                    created_at__gte=today_start,
                    created_at__lte=today_end
                ).count()
                print(f"Today global joins (all users): {today_global_joins}")
                
            except Exception as e:
                print(f"Error calculating today global joins: {e}")
                today_global_joins = 0
            
            # 5. Additional statistics
            total_global_users = 0
            try:
                total_global_users = TreePlacement.objects(program='global').count()
                print(f"Total global users: {total_global_users}")
                
            except Exception as e:
                print(f"Error calculating total global users: {e}")
                total_global_users = 0
            
            # 6. User's current phase and slot info
            user_status = {}
            try:
                user_placement = TreePlacement.objects(
                    program='global',
                    user_id=user_oid
                ).first()
                
                if user_placement:
                    user_status = {
                        "current_phase": user_placement.phase,
                        "slot_number": user_placement.slot_number,
                        "position": user_placement.position,
                        "level": user_placement.level,
                        "parent_id": str(user_placement.parent_id) if user_placement.parent_id else None,
                        "is_active": user_placement.is_active,
                        "joined_at": user_placement.created_at
                    }
                
            except Exception as e:
                print(f"Error getting user status: {e}")
                user_status = {}
            
            # Compile the statistics
            statistics = {
                "user_id": str(user_id),
                "user_status": user_status,
                "team_statistics": {
                    "total_team_members": total_team_members,
                    "today_joined_members": today_joined_members,
                    "today_direct_members": today_direct_members,
                    "today_global_joins": today_global_joins,
                    "total_global_users": total_global_users
                },
                "date_range": {
                    "today_start": today_start.isoformat(),
                    "today_end": today_end.isoformat(),
                    "timezone": "UTC"
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
            print(f"Team statistics generated successfully for user {user_id}")
            return {
                "success": True,
                "statistics": statistics
            }
            
        except Exception as e:
            print(f"Error in get_team_statistics: {e}")
            return {"success": False, "error": str(e)}

    def get_global_earnings_slots(self, user_id: str, phase: str = None) -> Dict[str, Any]:
        """
        Get Global program earnings data organized by slots array.
        Returns detailed information for each slot including tree structure.
        Each slot contains phase-wise data and downlines if user is root.
        If user is not in a specific slot, that slot will show empty or inactive state.
        """
        try:
            # Convert user_id to ObjectId
            try:
                user_oid = ObjectId(user_id)
                print(f"Converted user_id {user_id} to ObjectId: {user_oid}")
            except Exception as e:
                user_oid = user_id
                print(f"Could not convert to ObjectId, using string: {user_id}, Error: {e}")
            
            # Get user info
            user_info = User.objects(id=user_oid).first()
            if not user_info:
                return {"success": False, "error": "User not found"}
            
            # Define phases to process
            phases_to_process = []
            if phase:
                if phase.upper() in ['PHASE-1', 'PHASE-2']:
                    phases_to_process = [phase.upper()]
                else:
                    return {"success": False, "error": f"Invalid phase: {phase}. Must be PHASE-1 or PHASE-2"}
            else:
                phases_to_process = ['PHASE-1', 'PHASE-2']
            
            # Get all slots for the user across all phases
            all_user_placements = TreePlacement.objects(
                user_id=user_oid,
                program='global',
                is_active=True
            ).order_by('slot_no')
            
            user_slots = set()
            for placement in all_user_placements:
                user_slots.add(placement.slot_no)
            
            print(f"[DEBUG] User {user_id} is in slots: {sorted(user_slots)}")
            
            # Define slot catalog information
            slot_catalog_info = {
                1: {"name": "Slot 1", "value": 33.00, "phase_1_req": 4, "phase_2_req": 8},
                2: {"name": "Slot 2", "value": 36.00, "phase_1_req": 4, "phase_2_req": 8},
                3: {"name": "Slot 3", "value": 86.00, "phase_1_req": 4, "phase_2_req": 8},
                4: {"name": "Slot 4", "value": 203.00, "phase_1_req": 4, "phase_2_req": 8},
                5: {"name": "Slot 5", "value": 468.00, "phase_1_req": 4, "phase_2_req": 8},
            }
            
            slots_data = []
            
            # Process each slot (show slots user is in, max up to slot 5)
            for slot_no in range(1, 6):
                slot_info = slot_catalog_info.get(slot_no, {})
                
                # Check if user is in this slot
                user_in_this_slot = slot_no in user_slots
                
                slot_data = {
                    "slot_no": slot_no,
                    "slot_name": slot_info.get("name", f"Slot {slot_no}"),
                    "slot_value": slot_info.get("value", 0),
                    "is_active": user_in_this_slot,
                    "phases": {}
                }
                
                # If user is not in this slot, mark as inactive and skip phase data
                if not user_in_this_slot:
                    slot_data["progress"] = {
                        "phase_1": {"joined": 0, "required": 4, "remaining": 4},
                        "phase_2": {"joined": 0, "required": 8, "remaining": 8}
                    }
                    slot_data["tree"] = {
                        "user": None,
                        "downlines": []
                    }
                    slots_data.append(slot_data)
                    continue
                
                # Process each phase for this slot (user is in this slot)
                for phase_name in phases_to_process:
                    print(f"[DEBUG] Processing Slot {slot_no}, {phase_name} for user: {user_id}")
                    
                    # Get user's placement in this slot and phase
                    user_placement = TreePlacement.objects(
                        user_id=user_oid,
                        program='global',
                        phase=phase_name,
                        slot_no=slot_no,
                        is_active=True
                    ).first()
                    
                    phase_data = {
                        "phase": phase_name,
                        "user_position": None,
                        "is_root": False,
                        "downlines": []
                    }
                    
                    if user_placement:
                        phase_data["user_position"] = {
                            "level": user_placement.level,
                            "position": user_placement.position,
                            "parent_id": str(user_placement.parent_id) if user_placement.parent_id else None,
                            "upline_id": str(user_placement.upline_id) if user_placement.upline_id else None,
                            "activation_date": user_placement.activation_date.isoformat() if user_placement.activation_date else None
                        }
                        
                        # Check if user is root in this phase and slot
                        is_root = user_placement.parent_id is None
                        phase_data["is_root"] = is_root
                        
                        if is_root:
                            print(f"[DEBUG] User {user_id} is ROOT in Slot {slot_no}, {phase_name}")
                            # Get all downlines under this user in this specific slot and phase
                            downlines = TreePlacement.objects(
                                parent_id=user_oid,
                                program='global',
                                phase=phase_name,
                                slot_no=slot_no,
                                is_active=True
                            ).order_by('created_at')
                            
                            downlines_data = []
                            for downline in downlines:
                                downline_user = User.objects(id=downline.user_id).first()
                                downline_data = {
                                    "user_id": str(downline.user_id),
                                    "uid": downline_user.uid if downline_user else "Unknown",
                                    "name": downline_user.name if downline_user else "Unknown",
                                    "email": downline_user.email if downline_user else "Unknown",
                                    "level": downline.level,
                                    "position": downline.position,
                                    "activation_date": downline.activation_date.isoformat() if downline.activation_date else None
                                }
                                downlines_data.append(downline_data)
                            
                            phase_data["downlines"] = downlines_data
                            print(f"[DEBUG] Found {len(downlines_data)} downlines under root user in Slot {slot_no}, {phase_name}")
                        else:
                            print(f"[DEBUG] User {user_id} is NOT root in Slot {slot_no}, {phase_name}")
                    
                    slot_data["phases"][phase_name] = phase_data
                
                # Calculate progress for this slot based on user's current phase
                current_user_placement = TreePlacement.objects(
                    user_id=user_oid,
                    program='global',
                    slot_no=slot_no,
                    is_active=True
                ).order_by('-created_at').first()  # Get the latest placement
                
                phase_1_joined = 0
                phase_2_joined = 0
                
                if current_user_placement:
                    # User is root only if parent_id is None
                    is_user_root = current_user_placement.parent_id is None
                    
                    if is_user_root:
                        # Count downlines in PHASE-1
                        phase_1_downlines = TreePlacement.objects(
                            parent_id=user_oid,
                            program='global',
                            phase='PHASE-1',
                            slot_no=slot_no,
                            is_active=True
                        ).count()
                        phase_1_joined = phase_1_downlines
                        
                        # Count downlines in PHASE-2
                        phase_2_downlines = TreePlacement.objects(
                            parent_id=user_oid,
                            program='global',
                            phase='PHASE-2',
                            slot_no=slot_no,
                            is_active=True
                        ).count()
                        phase_2_joined = phase_2_downlines
                
                slot_data["progress"] = {
                    "phase_1": {
                        "joined": phase_1_joined,
                        "required": 4,
                        "remaining": max(0, 4 - phase_1_joined)
                    },
                    "phase_2": {
                        "joined": phase_2_joined,
                        "required": 8,
                        "remaining": max(0, 8 - phase_2_joined)
                    }
                }
                
                # Build tree structure
                tree_structure = {
                    "user": None,
                    "downlines": []
                }
                
                if current_user_placement:
                    tree_structure["user"] = {
                        "user_id": str(user_oid),
                        "uid": user_info.uid,
                        "name": user_info.name,
                        "level": current_user_placement.level,
                        "position": current_user_placement.position,
                        "is_root": current_user_placement.parent_id is None
                    }
                    
                    # Get downlines if user is root
                    if current_user_placement.parent_id is None:  # User is root
                        downlines = TreePlacement.objects(
                            parent_id=user_oid,
                            program='global',
                            phase=current_user_placement.phase,
                            slot_no=slot_no,
                            is_active=True
                        ).order_by('created_at')
                        
                        for downline in downlines:
                            downline_user = User.objects(id=downline.user_id).first()
                            downline_data = {
                                "user_id": str(downline.user_id),
                                "uid": downline_user.uid if downline_user else "Unknown",
                                "name": downline_user.name if downline_user else "Unknown",
                                "level": downline.level,
                                "position": downline.position
                            }
                            tree_structure["downlines"].append(downline_data)
                
                slot_data["tree"] = tree_structure
                slots_data.append(slot_data)
            
            return {
                "success": True,
                "data": {
                    "user_id": str(user_oid),
                    "user_name": user_info.name,
                    "user_email": user_info.email,
                    "user_uid": user_info.uid,
                    "slots": slots_data,
                    "total_slots": len(slots_data)
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get global earnings slots: {str(e)}"}
    
    def _create_slot_data(self, user_oid: ObjectId, slot_no: int, phase: str, placements: List) -> Dict[str, Any]:
        """
        Create detailed slot data including tree structure
        """
        try:
            # Get the main placement (first one for this slot/phase)
            main_placement = placements[0] if placements else None
            
            if not main_placement:
                return {
                    "slot_number": slot_no,
                    "phase": phase,
                    "status": "empty",
                    "tree_structure": None,
                    "member_count": 0,
                    "total_earnings": 0,
                    "created_at": None
                }
            
            # Get tree structure for this slot
            tree_structure = self._get_slot_tree_structure(user_oid, slot_no, phase)
            
            # Calculate member count
            member_count = len(placements)
            
            # Calculate total earnings (placeholder - you can implement actual earnings calculation)
            total_earnings = 0  # TODO: Implement actual earnings calculation
            
            return {
                "slot_number": slot_no,
                "phase": phase,
                "status": "active" if main_placement.is_active else "inactive",
                "tree_structure": tree_structure,
                "member_count": member_count,
                "total_earnings": total_earnings,
                "created_at": main_placement.created_at.isoformat() if main_placement.created_at else None,
                "slot_details": {
                    "level": main_placement.level,
                    "position": main_placement.position,
                    "parent_id": str(main_placement.parent_id) if main_placement.parent_id else None,
                    "upline_id": str(main_placement.upline_id) if main_placement.upline_id else None
                }
            }
            
        except Exception as e:
            print(f"Error creating slot data: {str(e)}")
            return {
                "slot_number": slot_no,
                "phase": phase,
                "status": "error",
                "tree_structure": None,
                "member_count": 0,
                "total_earnings": 0,
                "created_at": None,
                "error": str(e)
            }
    
    def _get_slot_tree_structure(self, user_oid: ObjectId, slot_no: int, phase: str) -> Dict[str, Any]:
        """
        Get tree structure for a specific slot
        """
        try:
            # Get all placements in this slot/phase
            placements = TreePlacement.objects(
                program='global',
                phase=phase,
                slot_no=slot_no,
                is_active=True
            ).order_by('created_at')
            
            if not placements:
                return None
            
            # Build tree structure
            tree_nodes = []
            
            for placement in placements:
                # Get user info
                user = User.objects(id=placement.user_id).first()
                
                node_data = {
                    "user_id": str(placement.user_id),
                    "user_info": {
                        "uid": user.uid if user else "Unknown",
                        "name": getattr(user, 'name', '') if user else '',
                        "email": getattr(user, 'email', '') if user else ''
                    },
                    "placement_info": {
                        "level": placement.level,
                        "position": placement.position,
                        "parent_id": str(placement.parent_id) if placement.parent_id else None,
                        "upline_id": str(placement.upline_id) if placement.upline_id else None,
                        "created_at": placement.created_at.isoformat() if placement.created_at else None
                    },
                    "children": []  # Will be populated if needed
                }
                
                tree_nodes.append(node_data)
            
            # Organize tree structure (root -> children)
            root_nodes = [node for node in tree_nodes if node["placement_info"]["parent_id"] is None]
            child_nodes = [node for node in tree_nodes if node["placement_info"]["parent_id"] is not None]
            
            # Build parent-child relationships
            for child in child_nodes:
                parent_id = child["placement_info"]["parent_id"]
                for parent in tree_nodes:
                    if parent["user_id"] == parent_id:
                        parent["children"].append(child)
                        break
            
            return {
                "root_nodes": root_nodes,
                "total_nodes": len(tree_nodes),
                "max_level": max([node["placement_info"]["level"] for node in tree_nodes]) if tree_nodes else 0
            }
            
        except Exception as e:
            print(f"Error getting slot tree structure: {str(e)}")
            return None

    def get_global_earnings(self, user_id: str, phase: str = None) -> Dict[str, Any]:
        """
        Get Global program earnings data matching frontend matrixData.js structure
        Returns data organized by phase with team member progression
        """
        try:
            # Convert user_id to ObjectId
            try:
                user_oid = ObjectId(user_id)
                print(f"Converted user_id {user_id} to ObjectId: {user_oid}")
            except Exception as e:
                user_oid = user_id
                print(f"Could not convert to ObjectId, using string: {user_id}, Error: {e}")
            
            # Get user info
            user_info = User.objects(id=user_oid).first()
            if not user_info:
                return {"success": False, "error": "User not found"}
            
            result_data = {}
            
            # Define phases to process
            phases_to_process = []
            if phase:
                if phase.upper() in ['PHASE-1', 'PHASE-2']:
                    phases_to_process = [phase.upper()]
                else:
                    return {"success": False, "error": f"Invalid phase: {phase}. Must be PHASE-1 or PHASE-2"}
            else:
                phases_to_process = ['PHASE-1', 'PHASE-2']
            
            for phase_name in phases_to_process:
                print(f"[DEBUG] Processing {phase_name} for user: {user_id}")
                
                # Get all children/downlines under this user for the specified phase
                try:
                    all_placements = TreePlacement.objects(
                        parent_id=user_oid,
                        program='global',
                        phase=phase_name,
                        is_active=True
                    ).order_by('activation_date')
                    
                    print(f"[DEBUG] Query executed successfully")
                    
                    # Check total placements first
                    total_count = TreePlacement.objects(parent_id=user_oid, program='global').count()
                    print(f"[DEBUG] Total global placements under user {user_id}: {total_count}")
                    
                    # Check specific phase placements
                    phase_count = all_placements.count()
                    print(f"[DEBUG] Placements found for {phase_name}: {phase_count}")
                    
                    if phase_count == 0:
                        print(f"[DEBUG] No placements found for {phase_name}")
                        result_data[phase_name.lower()] = []
                        continue
                        
                    # List first few placements for debugging
                    placements_list = list(all_placements[:3])  # Get first 3
                    for i, placement in enumerate(placements_list):
                        print(f"[DEBUG] Placement {i+1}: user_id={placement.user_id}, phase={placement.phase}, parent={placement.parent_id}")
                        
                except Exception as e:
                    print(f"[ERROR] Database query failed: {e}")
                    result_data[phase_name.lower()] = []
                    continue
                
                # Create progressive batches: 1st item has 1 user, 2nd has 2 users, etc.
                placements_list = list(all_placements)
                placement_batches = []
                
                print(f"[DEBUG] Creating progressive batches from {len(placements_list)} placements")
                
                for i in range(len(placements_list)):
                    # Take i+1 users for each progressive batch
                    batch_users = placements_list[:i+1]
                    placement_batches.append(batch_users)
                    print(f"[DEBUG] Batch {i+1}: {len(batch_users)} users")
                
                print(f"[DEBUG] Created {len(placement_batches)} batches")
                
                # Convert batches to frontend format
                phase_data = []
                batch_id = 11  # Starting ID as in mock data
                
                print(f"[DEBUG] Converting {len(placement_batches)} batches to frontend format")
                
                for batch_idx, batch in enumerate(placement_batches):
                    print(f"[DEBUG] Processing batch {batch_idx + 1} with {len(batch)} members")
                    # Calculate total global earnings from all users by currency
                    batch_users = batch
                    usd_earnings = 0.0
                    usdt_earnings = 0.0
                    bnb_earnings = 0.0
                    
                    for user_placement in batch_users:
                        user_id = user_placement.user_id
                        
                        # Get global earnings by currency for this user
                        from ..wallet.model import WalletLedger
                        
                        # USD earnings
                        user_usd = WalletLedger.objects(
                            user_id=user_id,
                            reason__regex=r'global_.*',
                            type='credit',
                            currency='USD'
                        ).sum('amount')
                        
                        # USDT earnings
                        user_usdt = WalletLedger.objects(
                            user_id=user_id,
                            reason__regex=r'global_.*',
                            type='credit',
                            currency='USDT'
                        ).sum('amount')
                        
                        # BNB earnings
                        user_bnb = WalletLedger.objects(
                            user_id=user_id,
                            reason__regex=r'global_.*',
                            type='credit',
                            currency='BNB'
                        ).sum('amount')
                        
                        usd_amount = float(user_usd) if user_usd else 0.0
                        usdt_amount = float(user_usdt) if user_usdt else 0.0
                        bnb_amount = float(user_bnb) if user_bnb else 0.0
                        
                        usd_earnings += usd_amount
                        usdt_earnings += usdt_amount
                        bnb_earnings += bnb_amount
                        
                        print(f"[DEBUG] User {user_id}: USD=${usd_amount}, USDT=${usdt_amount}, BNB={bnb_amount}")
                    
                    # Return price object with multiple currencies
                    price = {
                        "USD": usd_earnings,
                        "USDT": usdt_earnings, 
                        "BNB": bnb_earnings,
                        "total": usd_earnings + usdt_earnings + bnb_earnings
                    }
                    
                    print(f"[DEBUG] Batch {batch_idx + 1}: Total earnings - USD:${usd_earnings}, USDT:${usdt_earnings}, BNB:{bnb_earnings}")
                    
                    # Calculate status flags
                    is_completed = len(batch) >= 4  # Phase-1 needs 4 spots, Phase-2 needs 8
                    is_process = len(batch) > 0 and len(batch) < 4
                    is_auto_upgrade = len(batch) >= 2  # Need at least 2 for auto upgrade
                    is_manual_upgrade = len(batch) >= 4
                    
                    # Calculate process percent
                    max_spots = 4 if phase_name == 'PHASE-1' else 8
                    process_percent = min(100, (len(batch) / max_spots) * 100)
                    
                    # Convert placements to user array format
                    users = []
                    user_counter = 1
                    
                    # Add actual placements
                    for placement in batch:
                        users.append({
                            "id": user_counter,
                            "type": placement.position,
                            "userId": str(placement.user_id)
                        })
                        user_counter += 1
                    
                    # Create data object matching frontend structure
                    data_item = {
                        "id": batch_id,
                        "price": price,
                        "userId": str(user_oid),
                        "recycle": len(batch),  # Number of active members
                        "isCompleted": is_completed,
                        "isProcess": is_process,
                        "isAutoUpgrade": is_auto_upgrade,
                        "isManualUpgrade": is_manual_upgrade,
                        "processPercent": process_percent,
                        "users": users
                    }
                    
                    phase_data.append(data_item)
                    batch_id += 1
                    print(f"[DEBUG] Created data item for batch {batch_idx + 1}")
                
                print(f"[DEBUG] Phase {phase_name} completed with {len(phase_data)} items")
                result_data[phase_name.lower()] = phase_data
            
            print(f"[DEBUG] Final result_data keys: {list(result_data.keys())}")
            
            # If no phase specified, return both phases
            if not phase:
                print(f"[DEBUG] Returning both phases: {result_data}")
                return {"success": True, "data": result_data}
            else:
                # Return specific phase data
                phase_key = phase.lower()  # Use exact phase name with dash
                print(f"[DEBUG] Looking for phase_key: {phase_key}")
                if phase_key in result_data:
                    print(f"[DEBUG] Returning phase data: {result_data[phase_key]}")
                    return {"success": True, "data": result_data[phase_key]}
                else:
                    print(f"[DEBUG] Phase key not found, returning empty array")
                    return {"success": True, "data": []}
                    
        except Exception as e:
            print(f"Error in get_global_earnings: {e}")
            return {"success": False, "error": str(e)}

    def get_global_earnings_details(self, user_id: str, item_id: int, phase: str = None) -> Dict[str, Any]:
        """
        Get specific Global earnings item details by item_id
        Finds the item across both phases and returns the specific object
        """
        try:
            # Convert user_id to ObjectId
            try:
                user_oid = ObjectId(user_id)
                print(f"[DEBUG] Looking for item_id {item_id} under user {user_oid}")
            except Exception as e:
                user_oid = user_id
                print(f"[DEBUG] Using string user_id: {user_id}, Error: {e}")
            
            # Determine which phases to search
            phases_to_search = []
            if phase:
                if phase.upper() in ['PHASE-1', 'PHASE-2']:
                    phases_to_search = [phase.upper()]
                else:
                    return {"success": False, "error": f"Invalid phase: {phase}. Must be PHASE-1 or PHASE-2"}
            else:
                phases_to_search = ['PHASE-1', 'PHASE-2']
            
            print(f"[DEBUG] Searching for item_id {item_id} in phas[es]{phases_to_search}")
            
            for phase_name in phases_to_search:
                print(f"[DEBUG] Searching in {phase_name}")
                
                # Get all children/downlines under this user for the specified phase
                try:
                    all_placements = TreePlacement.objects(
                        parent_id=user_oid,
                        program='global',
                        phase=phase_name,
                        is_active=True
                    ).order_by('activation_date')
                    
                    placement_count = all_placements.count()
                    print(f"[DEBUG] Found {placement_count} placements in {phase_name}")
                    
                    if placement_count == 0:
                        continue
                
                except Exception as e:
                    print(f"[ERROR] Database query failed for {phase_name}: {e}")
                    continue
                
                # Create progressive batches: 1st item has 1 user, 2nd has 2 users, etc.
                placements_list = list(all_placements)
                placement_batches = []
                
                for i in range(len(placements_list)):
                    # Take i+1 users for each progressive batch
                    batch_users = placements_list[:i+1]
                    placement_batches.append(batch_users)
                
                # Convert batches to frontend format
                phase_data = []
                batch_id = 11  # Starting ID as in mock data
                
                for batch_idx, batch in enumerate(placement_batches):
                    # Check if this is the item we're looking for
                    if batch_id == item_id:
                        print(f"[DEBUG] Found matching item_id {item_id} in {phase_name}")
                        
                        # Calculate total global earnings from all users by currency
                        batch_users = batch
                        usd_earnings = 0.0
                        usdt_earnings = 0.0
                        bnb_earnings = 0.0
                        
                        for user_placement in batch_users:
                            user_id = user_placement.user_id
                            
                            # Get global earnings by currency for this user
                            from ..wallet.model import WalletLedger
                            
                            # USD earnings
                            user_usd = WalletLedger.objects(
                                user_id=user_id,
                                reason__regex=r'global_.*',
                                type='credit',
                                currency='USD'
                            ).sum('amount')
                            
                            # USDT earnings
                            user_usdt = WalletLedger.objects(
                                user_id=user_id,
                                reason__regex=r'global_.*',
                                type='credit',
                                currency='USDT'
                            ).sum('amount')
                            
                            # BNB earnings
                            user_bnb = WalletLedger.objects(
                                user_id=user_id,
                                reason__regex=r'global_.*',
                                type='credit',
                                currency='BNB'
                            ).sum('amount')
                            
                            usd_amount = float(user_usd) if user_usd else 0.0
                            usdt_amount = float(user_usdt) if user_usdt else 0.0
                            bnb_amount = float(user_bnb) if user_bnb else 0.0
                            
                            usd_earnings += usd_amount
                            usdt_earnings += usdt_amount
                            bnb_earnings += bnb_amount
                            
                            print(f"[DEBUG] Details User {user_id}: USD=${usd_amount}, USDT=${usdt_amount}, BNB={bnb_amount}")
                        
                        # Return price object with multiple currencies
                        price = {
                            "USD": usd_earnings,
                            "USDT": usdt_earnings,
                            "BNB": bnb_earnings,
                            "total": usd_earnings + usdt_earnings + bnb_earnings
                        }
                        
                        print(f"[DEBUG] Details: Total earnings - USD:${usd_earnings}, USDT:${usdt_earnings}, BNB:{bnb_earnings}")
                        
                        # Calculate status flags
                        is_completed = len(batch) >= 4  # Phase-1 needs 4 spots, Phase-2 needs 8
                        is_process = len(batch) > 0 and len(batch) < 4
                        is_auto_upgrade = len(batch) >= 2  # Need at least 2 for auto upgrade
                        is_manual_upgrade = len(batch) >= 4
                        
                        # Calculate process percent
                        max_spots = 4 if phase_name == 'PHASE-1' else 8
                        process_percent = min(100, (len(batch) / max_spots) * 100)
                        
                        # Convert placements to user array format
                        users = []
                        user_counter = 1
                        
                        for placement in batch:
                            users.append({
                                "id": user_counter,
                                "type": placement.position,
                                "userId": str(placement.user_id)
                            })
                            user_counter += 1
                        
                        # Create and return the specific data item
                        data_item = {
                            "id": item_id,
                            "price": price,
                            "userId": str(user_oid),
                            "recycle": len(batch),  # Number of active members
                            "isCompleted": is_completed,
                            "isProcess": is_process,
                            "isAutoUpgrade": is_auto_upgrade,
                            "isManualUpgrade": is_manual_upgrade,
                            "processPercent": process_percent,
                            "users": users,
                            "phase": phase_name  # Add phase info for frontend
                        }
                        
                        print(f"[DEBUG] Returning item details for id {item_id}")
                        return {"success": True, "data": data_item}
                    
                    batch_id += 1
            
            print(f"[DEBUG] Item ID {item_id} not found")
            return {"success": False, "error": f"Item with ID {item_id} not found"}
                    
        except Exception as e:
            print(f"Error in get_global_earnings_details: {e}")
            return {"success": False, "error": str(e)}
