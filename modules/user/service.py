from typing import Tuple, Optional, Dict, Any
from mongoengine.errors import NotUniqueError, ValidationError
from modules.user.model import User, PartnerGraph, EarningHistory
from auth.service import authentication_service
import asyncio
from modules.tree.service import TreeService
from modules.slot.model import SlotActivation, SlotCatalog
from decimal import Decimal
from bson import ObjectId
from utils import ensure_currency_for_program
from modules.auto_upgrade.model import BinaryAutoUpgrade
from modules.commission.service import CommissionService
from modules.jackpot.service import JackpotService
from modules.newcomer_support.model import NewcomerSupport
from modules.mentorship.service import MentorshipService
from modules.spark.service import SparkService
from modules.auto_upgrade.model import MatrixAutoUpgrade, GlobalPhaseProgression
from modules.rank.service import RankService
from modules.blockchain.model import BlockchainEvent
from datetime import datetime
from modules.tree.model import TreePlacement


class UserService:
    """Service class for user-related operations"""
    
    def get_user_by_uid(self, uid: str) -> Dict[str, Any]:
        """Get user details by UID"""
        try:
            # Get user by UID
            user = User.objects(uid=uid).first()
            if not user:
                return {
                    "success": False,
                    "error": "User not found"
                }
            
            # Resolve referrer's refer_code
            referrer_refer_code = None
            try:
                if getattr(user, 'refered_by', None):
                    inviter = User.objects(id=user.refered_by).only('refer_code').first()
                    referrer_refer_code = getattr(inviter, 'refer_code', None) if inviter else None
            except Exception:
                referrer_refer_code = None
            
            # Return user data in the exact format as shown in the collection
            user_data = {
                "success": True,
                "user": {
                    "_id": str(user.id),
                    "uid": user.uid,
                    "refer_code": user.refer_code,
                    "refered_by": str(user.refered_by) if user.refered_by else None,
                    "referrer_refer_code": referrer_refer_code,
                    "wallet_address": user.wallet_address,
                    "name": user.name,
                    "role": user.role,
                    "email": user.email,
                    "status": user.status if hasattr(user, 'status') else "active",
                    "current_rank": user.current_rank if hasattr(user, 'current_rank') else "Bitron",
                    "is_activated": user.is_activated if hasattr(user, 'is_activated') else False,
                    "partners_required": user.partners_required if hasattr(user, 'partners_required') else 2,
                    "partners_count": user.partners_count if hasattr(user, 'partners_count') else 0,
                    "binary_joined": user.binary_joined,
                    "matrix_joined": user.matrix_joined,
                    "global_joined": user.global_joined,
                    
                    # Binary program data
                    "binary_slots": user.binary_slots if hasattr(user, 'binary_slots') else [],
                    "binary_total_earnings": user.binary_total_earnings if hasattr(user, 'binary_total_earnings') else 0,
                    "binary_total_spent": user.binary_total_spent if hasattr(user, 'binary_total_spent') else 0,
                    
                    # Matrix program data
                    "matrix_slots": user.matrix_slots if hasattr(user, 'matrix_slots') else [],
                    "matrix_total_earnings": user.matrix_total_earnings if hasattr(user, 'matrix_total_earnings') else 0,
                    "matrix_total_spent": user.matrix_total_spent if hasattr(user, 'matrix_total_spent') else 0,
                    
                    # Global program data
                    "global_slots": user.global_slots if hasattr(user, 'global_slots') else [],
                    "global_total_earnings": user.global_total_earnings if hasattr(user, 'global_total_earnings') else 0,
                    "global_total_spent": user.global_total_spent if hasattr(user, 'global_total_spent') else 0,
                    
                    # Commission and bonus data
                    "total_commissions_earned": user.total_commissions_earned if hasattr(user, 'total_commissions_earned') else 0,
                    "total_commissions_paid": user.total_commissions_paid if hasattr(user, 'total_commissions_paid') else 0,
                    "missed_profits": user.missed_profits if hasattr(user, 'missed_profits') else 0,
                    "royal_captain_qualifications": user.royal_captain_qualifications if hasattr(user, 'royal_captain_qualifications') else 0,
                    "president_reward_qualifications": user.president_reward_qualifications if hasattr(user, 'president_reward_qualifications') else 0,
                    "leadership_stipend_eligible": user.leadership_stipend_eligible if hasattr(user, 'leadership_stipend_eligible') else False,
                    
                    # Auto upgrade settings
                    "binary_auto_upgrade_enabled": user.binary_auto_upgrade_enabled if hasattr(user, 'binary_auto_upgrade_enabled') else True,
                    "matrix_auto_upgrade_enabled": user.matrix_auto_upgrade_enabled if hasattr(user, 'matrix_auto_upgrade_enabled') else True,
                    "global_auto_upgrade_enabled": user.global_auto_upgrade_enabled if hasattr(user, 'global_auto_upgrade_enabled') else True,
                    
                    # Timestamps
                    "created_at": user.created_at,
                    "updated_at": user.updated_at
                }
            }
            
            return user_data
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get user by UID: {str(e)}"
            }
    
    def get_user_full_details(self, user_id: str) -> Dict[str, Any]:
        """Get complete user details including all related information"""
        try:
            # Get basic user info
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {
                    "success": False,
                    "error": "User not found"
                }
            
            # Get user's slot activations
            slot_activations = SlotActivation.objects(user_id=ObjectId(user_id)).order_by('-activated_at')
            
            # Get user's tree placements
            tree_placements = TreePlacement.objects(user_id=ObjectId(user_id)).order_by('-created_at')
            
            # Get user's earning history
            earning_history = EarningHistory.objects(user_id=ObjectId(user_id)).order_by('-created_at').limit(10)
            
            # Get user's wallet information
            from modules.wallet.model import UserWallet
            user_wallets = UserWallet.objects(user_id=ObjectId(user_id))
            
            # Get user's rank information
            from modules.rank.service import RankService
            rank_service = RankService()
            rank_info = rank_service.get_user_rank_info(user_id)
            
            # Get user's jackpot status
            jackpot_service = JackpotService()
            jackpot_status = jackpot_service.get_user_jackpot_status(user_id)
            
            # Get user's leadership stipend info
            from modules.leadership_stipend.model import LeadershipStipend
            leadership_stipend = LeadershipStipend.objects(user_id=ObjectId(user_id)).first()
            
            # Get user's newcomer support info
            newcomer_support = NewcomerSupport.objects(user_id=ObjectId(user_id)).first()
            
            # Get user's commission summary
            from modules.commission.service import CommissionService
            commission_service = CommissionService()
            commission_summary = commission_service.get_user_commission_summary(user_id)
            
            # Get user's referral statistics
            total_referrals = User.objects(refered_by=ObjectId(user_id)).count()
            direct_referrals = User.objects(refered_by=ObjectId(user_id)).only('_id', 'uid', 'name', 'created_at').order_by('-created_at').limit(10)
            
            # Format response
            user_details = {
                "success": True,
                "user_info": {
                    "id": str(user.id),
                    "uid": user.uid,
                    "refer_code": user.refer_code,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                    "wallet_address": user.wallet_address,
                    "refered_by": str(user.refered_by) if user.refered_by else None,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at,
                    "is_active": user.is_active,
                    "binary_joined": user.binary_joined,
                    "binary_joined_at": user.binary_joined_at,
                    "matrix_joined": user.matrix_joined,
                    "matrix_joined_at": user.matrix_joined_at,
                    "global_joined": user.global_joined,
                    "global_joined_at": user.global_joined_at
                },
                "slot_activations": [
                    {
                        "id": str(slot.id),
                        "program": slot.program,
                        "slot_no": slot.slot_no,
                        "status": slot.status,
                        "activated_at": slot.activated_at,
                        "completed_at": slot.completed_at,
                        "tx_hash": slot.tx_hash
                    } for slot in slot_activations
                ],
                "tree_placements": [
                    {
                        "id": str(tree.id),
                        "program": tree.program,
                        "slot_no": tree.slot_no,
                        "referrer_id": str(tree.referrer_id),
                        "position": tree.position,
                        "level": tree.level,
                        "created_at": tree.created_at
                    } for tree in tree_placements
                ],
                "earning_history": [
                    {
                        "id": str(earning.id),
                        "program": earning.program,
                        "income_type": earning.income_type,
                        "amount": float(earning.amount),
                        "currency": earning.currency,
                        "created_at": earning.created_at,
                        "description": earning.description
                    } for earning in earning_history
                ],
                "wallets": [
                    {
                        "id": str(wallet.id),
                        "wallet_type": wallet.wallet_type,
                        "balance": float(wallet.balance),
                        "currency": wallet.currency,
                        "last_updated": wallet.last_updated
                    } for wallet in user_wallets
                ],
                "rank_info": rank_info.get("data", {}) if rank_info.get("success") else {},
                "jackpot_status": jackpot_status.get("data", {}) if jackpot_status.get("success") else {},
                "leadership_stipend": {
                    "id": str(leadership_stipend.id),
                    "is_active": leadership_stipend.is_active if leadership_stipend else False,
                    "total_earned": float(leadership_stipend.total_earned) if leadership_stipend else 0.0,
                    "last_payment_date": leadership_stipend.last_payment_date if leadership_stipend else None
                } if leadership_stipend else None,
                "newcomer_support": {
                    "id": str(newcomer_support.id),
                    "total_support": float(newcomer_support.total_support) if newcomer_support else 0.0,
                    "support_claimed": float(newcomer_support.support_claimed) if newcomer_support else 0.0,
                    "last_claim_date": newcomer_support.last_claim_date if newcomer_support else None
                } if newcomer_support else None,
                "commission_summary": commission_summary.get("data", {}) if commission_summary.get("success") else {},
                "referral_stats": {
                    "total_referrals": total_referrals,
                    "direct_referrals": [
                        {
                            "id": str(ref.id),
                            "uid": ref.uid,
                            "name": ref.name,
                            "created_at": ref.created_at
                        } for ref in direct_referrals
                    ]
                }
            }
            
            return user_details
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get user details: {str(e)}"
            }
    
    def get_my_community(self, user_id: str, program_type: str = "binary", slot_number: Optional[int] = None, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """
        Get ALL community members (all downline users, all levels) for a user
        Slot-wise filtering: Only users from specified slot tree
        Uses BFS traversal to get all descendants
        
        Slot validation logic:
        - If slot_number is provided: only return data if slot_number <= user's max active slot
        - If slot_number is None: use user's max active slot from slot_activation collection
        """
        try:
            from modules.tree.model import TreePlacement
            from modules.slot.model import SlotActivation
            
            # Validate program type
            if program_type not in ["binary", "matrix"]:
                return {"success": False, "error": "Invalid program type. Must be 'binary' or 'matrix'"}
            
            # Get the user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            user_oid = ObjectId(user_id)
            
            # Get user's max active slot from slot_activation collection
            max_active_slot = 0
            
            # Check SlotActivation collection
            slot_activations = SlotActivation.objects(
                user_id=user_oid,
                program=program_type,
                status='completed'
            ).order_by('-slot_no')
            
            if slot_activations.count() > 0:
                max_active_slot = slot_activations.first().slot_no
            
            # For matrix program, also check MatrixActivation collection
            if program_type == "matrix":
                from modules.matrix.model import MatrixActivation
                matrix_activations = MatrixActivation.objects(
                    user_id=user_oid,
                    status='completed'
                ).order_by('-slot_no')
                
                if matrix_activations.count() > 0:
                    matrix_max_slot = matrix_activations.first().slot_no
                    max_active_slot = max(max_active_slot, matrix_max_slot)
            
            # If slot_number is not provided, use max active slot
            if slot_number is None:
                if max_active_slot == 0:
                    # User has no active slots, return empty data
                    return {
                        "success": True,
                        "data": {
                            "community_members": [],
                            "pagination": {
                                "page": page,
                                "limit": limit,
                                "total_count": 0,
                                "total_pages": 0
                            }
                        }
                    }
                slot_number = max_active_slot
            else:
                # If slot_number is provided, validate it against max active slot
                if slot_number > max_active_slot:
                    # Requested slot is higher than user's max active slot, return empty data
                    return {
                        "success": True,
                        "data": {
                            "community_members": [],
                            "pagination": {
                                "page": page,
                                "limit": limit,
                                "total_count": 0,
                                "total_pages": 0
                            }
                        }
                    }
            
            # Use BFS traversal to get ALL downline users (all levels) in this slot tree
            unique_user_ids = []
            queue = [user_oid]  # Start from root user
            visited = set()
            visited.add(str(user_oid))  # Don't include root user in results
            
            print(f"[MY-COMMUNITY] Starting BFS traversal for user {user_id}, program={program_type}, slot={slot_number}")
            
            # BFS traversal: collect all descendants
            while queue:
                current_upline_id = queue.pop(0)
                
                # Get all children of current user in this slot tree
                children_query = {
                    "upline_id": current_upline_id,
                    "program": program_type,
                    "slot_no": slot_number,
                    "is_active": True
                }
                
                children = TreePlacement.objects(**children_query).order_by('created_at')
                
                for child_placement in children:
                    child_user_id_str = str(child_placement.user_id)
                    
                    # Avoid duplicates and avoid cycles
                    if child_user_id_str not in visited:
                        visited.add(child_user_id_str)
                        unique_user_ids.append(child_placement.user_id)
                        queue.append(child_placement.user_id)  # Add to queue for next level traversal
            
            print(f"[MY-COMMUNITY] Found {len(unique_user_ids)} total downline users in slot {slot_number} tree")
            
            # Filter: Only keep users who actually have placement in this slot
            # AND whose max active slot matches the requested slot_number
            
            # First, get all users with placement in this slot
            users_with_placement = []
            for user_id_obj in unique_user_ids:
                placement = TreePlacement.objects(
                    user_id=user_id_obj,
                    program=program_type,
                    slot_no=slot_number,
                    is_active=True
                ).first()
                if placement:
                    users_with_placement.append(user_id_obj)
            
            # Batch fetch max slots for all users to optimize performance
            user_max_slots_map = {}
            
            # Get max slots from SlotActivation for all users at once
            all_slot_activations = SlotActivation.objects(
                user_id__in=users_with_placement,
                program=program_type,
                status='completed'
            )
            
            # Find max slot_no for each user
            for activation in all_slot_activations:
                user_id_str = str(activation.user_id)
                current_max = user_max_slots_map.get(user_id_str, 0)
                if activation.slot_no > current_max:
                    user_max_slots_map[user_id_str] = activation.slot_no
            
            # For matrix program, also check MatrixActivation and take max
            if program_type == "matrix":
                from modules.matrix.model import MatrixActivation
                all_matrix_activations = MatrixActivation.objects(
                    user_id__in=users_with_placement,
                    status='completed'
                )
                
                for activation in all_matrix_activations:
                    user_id_str = str(activation.user_id)
                    current_max = user_max_slots_map.get(user_id_str, 0)
                    user_max_slots_map[user_id_str] = max(current_max, activation.slot_no)
            
            # Filter: Only include users whose highest active slot exactly matches the requested slot number
            users_with_slot_placement = []
            for user_id_obj in users_with_placement:
                user_id_str = str(user_id_obj)
                user_max_slot = user_max_slots_map.get(user_id_str, 0)
                
                # Include users only when their max active slot matches the requested slot
                if user_max_slot == slot_number:
                    users_with_slot_placement.append(user_id_obj)
                else:
                    print(f"[MY-COMMUNITY] Skipping user {user_id_obj}: max_slot={user_max_slot}, requested={slot_number}")
            
            print(f"[MY-COMMUNITY] After slot placement verification: {len(users_with_slot_placement)} users")
            
            # Get total count (only users with placement in this slot)
            total_count = len(users_with_slot_placement)
            
            # Apply pagination to filtered user IDs
            skip = (page - 1) * limit
            paginated_user_ids = users_with_slot_placement[skip:skip + limit]
            
            # Get User details for paginated IDs
            referred_users = User.objects(id__in=paginated_user_ids)
            
            # Create a map for quick lookup
            user_map = {str(u.id): u for u in referred_users}
            
            # Batch fetch ranks and slot activations for better performance
            from ..rank.model import UserRank, Rank
            from ..slot.model import SlotActivation
            from ..matrix.model import MatrixActivation
            
            # Get all UserRank objects in one query
            user_rank_map = {}
            user_ranks = UserRank.objects(user_id__in=paginated_user_ids)
            for ur in user_ranks:
                user_rank_map[str(ur.user_id)] = ur
            
            # Get all slot activations in batch
            binary_slots_map = {}
            matrix_slots_map = {}
            matrix_activations_map = {}
            
            # Binary slots count
            binary_activations = SlotActivation.objects(
                user_id__in=paginated_user_ids,
                program='binary',
                status='completed'
            )
            for activation in binary_activations:
                user_id_str = str(activation.user_id)
                binary_slots_map[user_id_str] = binary_slots_map.get(user_id_str, 0) + 1
            
            # Matrix slots from SlotActivation
            matrix_activations_from_slot = SlotActivation.objects(
                user_id__in=paginated_user_ids,
                program='matrix',
                status='completed'
            )
            for activation in matrix_activations_from_slot:
                user_id_str = str(activation.user_id)
                matrix_slots_map[user_id_str] = matrix_slots_map.get(user_id_str, 0) + 1
            
            # Matrix activations from MatrixActivation
            matrix_activations_list = MatrixActivation.objects(
                user_id__in=paginated_user_ids,
                status='completed'
            )
            for activation in matrix_activations_list:
                user_id_str = str(activation.user_id)
                matrix_activations_map[user_id_str] = matrix_activations_map.get(user_id_str, 0) + 1
            
            # Get all Rank objects (cache for rank name lookup)
            rank_cache = {}
            ranks = Rank.objects(rank_number__gte=1, rank_number__lte=15)
            for rank in ranks:
                rank_cache[rank.rank_number] = rank.rank_name
            
            # Format response - all users in paginated_user_ids already have slot placement
            community_members = []
            for user_id_obj in paginated_user_ids:
                member = user_map.get(str(user_id_obj))
                if member:
                    user_id_str = str(user_id_obj)
                    
                    # Fetch inviter's refer_code (who referred this member)
                    inviter_code = None
                    try:
                        if getattr(member, 'refered_by', None):
                            inviter = User.objects(id=member.refered_by).only('refer_code').first()
                            inviter_code = getattr(inviter, 'refer_code', None) if inviter else None
                    except Exception:
                        inviter_code = None
                    
                    # Count direct partners for this member (only in this slot)
                    # Only count partners who have placement in this slot
                    direct_partners_in_slot = TreePlacement.objects(
                        parent_id=member.id,
                        program=program_type,
                        slot_no=slot_number,
                        is_active=True
                    ).count()
                    
                    # Get user's actual rank (calculated based on binary + matrix slots)
                    # Rank rule: User MUST join BOTH Binary AND Matrix
                    # Rank = min(Binary Slots, Matrix Slots)
                    calculated_rank = "No Rank"
                    
                    try:
                        # Check if user has joined both Binary and Matrix
                        if member.binary_joined and member.matrix_joined:
                            # Get UserRank if exists
                            user_rank_obj = user_rank_map.get(user_id_str)
                            
                            if user_rank_obj:
                                # Use stored rank
                                if user_rank_obj.current_rank_number == 0:
                                    calculated_rank = "No Rank"
                                else:
                                    calculated_rank = user_rank_obj.current_rank_name or "No Rank"
                            else:
                                # Calculate rank on-the-fly using cached data
                                binary_slots = binary_slots_map.get(user_id_str, 0)
                                matrix_slots = max(
                                    matrix_slots_map.get(user_id_str, 0),
                                    matrix_activations_map.get(user_id_str, 0)
                                )
                                
                                # Rank = min(Binary Slots, Matrix Slots)
                                # If Matrix not joined or no Matrix slots, rank = 0
                                if matrix_slots < 1:
                                    calculated_rank = "No Rank"
                                else:
                                    rank_number = min(binary_slots, matrix_slots)
                                    rank_number = min(rank_number, 15)  # Max rank 15
                                    
                                    if rank_number == 0:
                                        calculated_rank = "No Rank"
                                    else:
                                        # Get rank name from cache
                                        calculated_rank = rank_cache.get(rank_number, f"Rank {rank_number}")
                        else:
                            # User hasn't joined both programs
                            calculated_rank = "No Rank"
                    except Exception as e:
                        # Fallback to current_rank if calculation fails
                        calculated_rank = getattr(member, 'current_rank', 'No Rank')
                        print(f"[MY-COMMUNITY] Error calculating rank for {member.uid}: {e}")
                    
                    community_members.append({
                        "id": str(member.id),
                        "uid": member.uid,
                        "refer_code": member.refer_code,
                        "inviter_refer_code": inviter_code,
                        "name": member.name,
                        "email": member.email,
                        "role": member.role,
                        "wallet_address": member.wallet_address,
                        "created_at": member.created_at,
                        "binary_joined": member.binary_joined,
                        "matrix_joined": member.matrix_joined,
                        "global_joined": member.global_joined,
                        "current_rank": calculated_rank,  # Actual calculated rank
                        "rank": calculated_rank,  # Same as current_rank
                        "direct_partner": direct_partners_in_slot  # Slot-specific count
                    })
            
            return {
                "success": True,
                "data": {
                    "community_members": community_members,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total_count": total_count,
                        "total_pages": (total_count + limit - 1) // limit
                    }
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get community members: {str(e)}"
            }

    def get_my_team(self, user_id: str, program: str, level: int = None, slot_no: int = None) -> Dict[str, Any]:
        """
        Get team members for a specific program and level
        
        If level is provided:
        - Uses upline_id for tree structure (not parent_id)
        - Level 1: Direct tree children (upline_id = user_id)
        - Level 2: Grandchildren (children of Level 1)
        - Level 3: Great-grandchildren (children of Level 2)
        
        If level is NOT provided:
        - Returns all direct referrals (parent_id = user_id) regardless of tree placement
        
        Level maximum (when level is provided):
        - Binary: L1=2, L2=4, L3=8, etc (2^level)
        - Matrix: L1=3, L2=9, L3=27, etc (3^level)
        
        Slot filtering:
        - If slot_no provided, only show that slot's tree
        - If slot_no is None, use default (Slot 1)
        """
        try:
            from modules.tree.model import TreePlacement
            from modules.user.model import User
            
            uid = ObjectId(user_id)
            program_lower = program.lower()
            
            if program_lower not in ['binary', 'matrix']:
                return {
                    "success": False,
                    "error": "Invalid program. Must be 'binary' or 'matrix'"
                }
            
            # Default to Slot 1 if not specified
            if slot_no is None:
                slot_no = 1
            
            # If level is not provided OR level=1, return ALL direct referrals (parent_id = user_id)
            # Level 1 means direct referrals (who this user directly referred)
            if level is None or level == 1:
                # Get all direct referrals (who this user directly referred)
                direct_referrals = TreePlacement.objects(
                    parent_id=uid,  # Direct referrals use parent_id
                    program=program_lower,
                    slot_no=slot_no,
                    is_active=True
                ).order_by('created_at')
                
                # If no direct referrals found, fallback to tree children (upline_id)
                # This handles cases where users were placed in tree but parent_id wasn't set
                if direct_referrals.count() == 0:
                    direct_referrals = TreePlacement.objects(
                        upline_id=uid,  # Fallback to tree structure
                        program=program_lower,
                        slot_no=slot_no,
                        is_active=True
                    ).order_by('created_at')
                    print(f"[MY-TEAM] No parent_id referrals found, using upline_id fallback for user {user_id}")
                
                team_data = []
                for member in direct_referrals:
                    user = User.objects(id=member.user_id).first()
                    if user:
                        # Fetch inviter's refer_code (should be this user)
                        inviter_code = None
                        try:
                            inviter = User.objects(id=uid).only('refer_code').first()
                            inviter_code = getattr(inviter, 'refer_code', None) if inviter else None
                        except Exception:
                            inviter_code = None
                        
                        team_data.append({
                            "s_no": len(team_data) + 1,
                            "id": str(user.id),
                            "uid": user.uid,
                            "refer_code": getattr(user, 'refer_code', None),
                            "inviter_refer_code": inviter_code,
                            "address": user.wallet_address,
                            "inviter_id": str(user.refered_by) if user.refered_by else "--",
                            "activation_date": member.created_at.strftime("%d %b %Y (%H:%M)"),
                            "rank": "--",  # TODO: Implement rank calculation
                            "direct_partner": self._count_direct_partners(str(user.id))
                        })
                
                # Store actual total count BEFORE limiting
                actual_total_members = len(team_data)
                
                # Apply level maximum limit for level=1
                if level == 1:
                    if program_lower == 'binary':
                        level_max = 2 ** 1  # Binary: Level 1 = 2
                    else:  # matrix
                        level_max = 3 ** 1  # Matrix: Level 1 = 3
                    
                    # Apply level maximum limit for display
                    limited_members = team_data[:level_max]
                    
                    return {
                        "success": True,
                        "data": {
                            "program": program_lower,
                            "level": 1,
                            "slot_no": slot_no,
                            "level_maximum": level_max,
                            "total_members": actual_total_members,  # Actual total before limit
                            "displayed_members": len(limited_members),  # Number shown (limited)
                            "team_members": limited_members  # Return limited list
                        }
                    }
                else:
                    # level is None - return all without limit
                    return {
                        "success": True,
                        "data": {
                            "program": program_lower,
                            "level": None,
                            "slot_no": slot_no,
                            "level_maximum": None,
                            "total_members": len(team_data),
                            "displayed_members": len(team_data),
                            "team_members": team_data
                        }
                    }
            
            # For level > 1, use recursive function to get descendants at specific depth using upline_id
            def get_descendants_at_depth(upline_id, current_depth, target_depth):
                """Get all descendants at target depth from upline"""
                # Get direct children using upline_id (tree structure) and slot filter
                children = TreePlacement.objects(
                    upline_id=upline_id,
                    program=program_lower,
                    slot_no=slot_no,  # Filter by slot
                    is_active=True
                ).order_by('created_at')
                
                # If we're at target depth, return these children
                if current_depth == target_depth:
                    return list(children)
                
                # If we haven't reached target depth yet, recurse deeper
                if current_depth < target_depth:
                    descendants = []
                    for child in children:
                        descendants.extend(get_descendants_at_depth(child.user_id, current_depth + 1, target_depth))
                    return descendants
                
                return []
            
            # Get team members at requested level (depth)
            # Level 1 = depth 1 (direct children)
            team_members = get_descendants_at_depth(uid, 1, level)
            
            # Remove duplicates by user_id (in case same user appears multiple times)
            seen_users = set()
            unique_members = []
            for member in team_members:
                user_id_str = str(member.user_id)
                if user_id_str not in seen_users:
                    seen_users.add(user_id_str)
                    unique_members.append(member)
            
            # Store actual total count BEFORE limiting
            actual_total_members = len(unique_members)
            
            # Calculate level maximum based on program
            if program_lower == 'binary':
                level_max = 2 ** level  # Binary: 2^level (2, 4, 8, 16, ...)
            else:  # matrix
                level_max = 3 ** level  # Matrix: 3^level (3, 9, 27, ...)
            
            # Apply level maximum limit for display (but keep actual total)
            limited_members = unique_members[:level_max]
            
            team_data = []
            for member in limited_members:
                # Get user details
                user = User.objects(id=member.user_id).first()
                if user:
                    # Fetch inviter's refer_code (who referred this member)
                    inviter_code = None
                    try:
                        if getattr(user, 'refered_by', None):
                            inviter = User.objects(id=user.refered_by).only('refer_code').first()
                            inviter_code = getattr(inviter, 'refer_code', None) if inviter else None
                    except Exception:
                        inviter_code = None
                    team_data.append({
                        "s_no": len(team_data) + 1,
                        "id": str(user.id),
                        "uid": user.uid,
                        "refer_code": getattr(user, 'refer_code', None),
                        "inviter_refer_code": inviter_code,
                        "address": user.wallet_address,
                        "inviter_id": str(user.refered_by) if user.refered_by else "--",
                        "activation_date": member.created_at.strftime("%d %b %Y (%H:%M)"),
                        "rank": "--",  # TODO: Implement rank calculation
                        "direct_partner": self._count_direct_partners(str(user.id))
                    })
            
            return {
                "success": True,
                "data": {
                    "program": program_lower,
                    "level": level,
                    "slot_no": slot_no,
                    "level_maximum": level_max,
                    "total_members": actual_total_members,  # Show actual total, not limited list size
                    "displayed_members": len(team_data),  # Number of members shown in response
                    "team_members": team_data
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get team data: {str(e)}"
            }
    
    def _count_direct_partners(self, user_id: str) -> int:
        """Count direct partners for a user"""
        try:
            uid = ObjectId(user_id)
            direct_partners = User.objects(refered_by=uid).count()
            return direct_partners
        except Exception:
            return 0
    
    def add_test_balance(self, user_id: str) -> bool:
        """
        🧪 TEMPORARY TEST METHOD - Add test balance to user wallet
        This method will be removed before production deployment.
        
        Adds 10,000,000 balance for both BNB and USDT currencies to main wallet.
        
        Args:
            user_id: User ID (string or ObjectId)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from modules.wallet.model import UserWallet
            
            user_oid = ObjectId(user_id)
            test_balance = Decimal('10000000')
            current_time = datetime.utcnow()
            
            # Add BNB balance
            bnb_wallet = UserWallet.objects(
                user_id=user_oid,
                wallet_type='main',
                currency='BNB'
            ).first()
            
            if not bnb_wallet:
                bnb_wallet = UserWallet(
                    user_id=user_oid,
                    wallet_type='main',
                    currency='BNB',
                    balance=test_balance,
                    last_updated=current_time
                )
                bnb_wallet.save()
            else:
                bnb_wallet.balance = test_balance
                bnb_wallet.last_updated = current_time
                bnb_wallet.save()
            
            # Add USDT balance
            usdt_wallet = UserWallet.objects(
                user_id=user_oid,
                wallet_type='main',
                currency='USDT'
            ).first()
            
            if not usdt_wallet:
                usdt_wallet = UserWallet(
                    user_id=user_oid,
                    wallet_type='main',
                    currency='USDT',
                    balance=test_balance,
                    last_updated=current_time
                )
                usdt_wallet.save()
            else:
                usdt_wallet.balance = test_balance
                usdt_wallet.last_updated = current_time
                usdt_wallet.save()
            
            return True
        except Exception as e:
            print(f"Error adding test balance: {str(e)}")
            return False


def create_temp_user_service(payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Temporary user creation service - simplified registration
    Auto-generates: wallet_address, password, uid, refer_code, binary_payment_tx
    Takes from frontend: email, name, refered_by
    
    Returns (result, error):
      - result: {"_id": str, "token": str, "token_type": "bearer", "user": {...}}
      - error: error message string if any
    """
    import time
    import random
    import secrets
    
    # Required fields
    required_fields = ["wallet_address", "refered_by"]
    
    missing = [f for f in required_fields if not payload.get(f)]
    if missing:
        return None, f"Missing required fields: {', '.join(missing)}"
    
    # Get wallet_address (required)
    wallet_address = payload.get("wallet_address")
    
    # Check if wallet_address already exists
    existing_wallet = User.objects(wallet_address=wallet_address).first()
    if existing_wallet:
        return None, "User with this wallet_address already exists"
    
    # Get optional fields - set to empty string if not provided
    email = payload.get("email")
    name = payload.get("name")
    
    # Handle None values and strip whitespace
    if email is None:
        email = ""
    else:
        email = str(email).strip()
    
    if name is None:
        name = ""
    else:
        name = str(name).strip()
    password = payload.get("password")
    
    # Generate password if not provided
    if not password:
        password = secrets.token_urlsafe(16)
    
    # Check if email already exists (only if email was provided and not empty)
    if email:
        existing_email = User.objects(email=email).first()
        if existing_email:
            return None, "User with this email already exists"
    
    # Look up refered_by code to get upline_id
    refered_by_code = payload.get("refered_by")
    upline_user = User.objects(refer_code=refered_by_code).first()
    if not upline_user:
        return None, f"Referral code '{refered_by_code}' not found"
    
    upline_id = str(upline_user.id)
    
    # Auto-generate unique uid
    uid = f"user{int(time.time() * 1000)}{random.randint(1000, 9999)}"
    
    # Ensure uid is unique
    while User.objects(uid=uid).first():
        uid = f"user{int(time.time() * 1000)}{random.randint(1000, 9999)}"
    
    # Auto-generate unique refer_code
    refer_code = f"RC{int(time.time() * 1000)}{random.randint(100, 999)}"
    
    # Ensure refer_code is unique
    while User.objects(refer_code=refer_code).first():
        refer_code = f"RC{int(time.time() * 1000)}{random.randint(100, 999)}"
    
    # Auto-generate password (strong random password)
    auto_password = secrets.token_urlsafe(16)
    
    try:
        # Hash password
        hashed_password = authentication_service.get_password_hash(auto_password)
        
        # Create user
        user = User(
            uid=uid,
            refer_code=refer_code,
            refered_by=upline_id,
            wallet_address=wallet_address,
            name=name,
            role="user",
            email=email,
            password=hashed_password,
        )
        user.save()
        
        # 🧪 TEMPORARY: Add test balance for development (will be removed before production)
        try:
            user_service = UserService()
            user_service.add_test_balance(str(user.id))
        except Exception as e:
            print(f"Failed to add test balance: {str(e)}")
        
        # Initialize program participation flags
        try:
            current_time = datetime.utcnow()
            updates: Dict[str, Any] = {
                'binary_joined': True,
                'binary_joined_at': current_time
            }
            User.objects(id=user.id).update_one(**{f'set__{k}': v for k, v in updates.items()})
            user.reload()
        except Exception:
            pass

        # Auto-activate first two binary slots (Explorer=1, Contributor=2) and distribute funds
        try:
            # Import TreeService for binary tree placement
            from modules.tree.service import TreeService
            from modules.auto_upgrade.service import AutoUpgradeService
            from decimal import Decimal
            
            # Create binary tree placement for the new user
            tree_service = TreeService()
            
            # First, ensure referrer has TreePlacement record for binary
            referrer_placement = TreePlacement.objects(
                user_id=ObjectId(upline_id),
                program='binary',
                slot_no=1,
                is_active=True
            ).first()
            
            if not referrer_placement:
                print(f"⚠️ Referrer {upline_id} doesn't have Binary TreePlacement record, creating one...")
                # Create TreePlacement for referrer (assuming they are root level)
                referrer_placement = TreePlacement(
                    user_id=ObjectId(upline_id),
                    program='binary',
                    parent_id=ObjectId(upline_id),
                    upline_id=ObjectId(upline_id),
                    position='root',
                    level=0,
                    slot_no=1,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                referrer_placement.save()
                print(f"✅ Created Binary TreePlacement for referrer {upline_id}")
            
            # Place user in binary tree for BOTH slots before activation
            # Slot 1 placement
            binary_placement_1 = tree_service.place_user_in_tree(
                user_id=user.id,
                referrer_id=ObjectId(upline_id),
                program='binary',
                slot_no=1  # First slot
            )
            
            # Slot 2 placement (needed for reserve routing logic)
            binary_placement_2 = tree_service.place_user_in_tree(
                user_id=user.id,
                referrer_id=ObjectId(upline_id),
                program='binary',
                slot_no=2  # Second slot
            )
            
            if binary_placement_1:
                print(f"✅ Binary tree placement created for temp user {user.id} under {upline_id} (slot 1)")
                if binary_placement_2:
                    print(f"✅ Binary tree placement created for temp user {user.id} under {upline_id} (slot 2)")
                
                # 🚀 AUTOMATIC BINARY SLOT ACTIVATION
                # When user joins, automatically activate Slot 1 and Slot 2
                auto_upgrade_service = AutoUpgradeService()
                
                # Slot costs from PROJECT_DOCUMENTATION.md
                slot_costs = [0.0022, 0.0044, 0.0088, 0.0176, 0.0352, 0.0704, 0.1408, 0.2816, 0.5632, 1.1264, 2.2528, 4.5056, 9.0112, 18.0224, 36.0448, 72.0896]
                
                # Activate Slot 1 (Explorer)
                slot_1_result = auto_upgrade_service.process_binary_slot_activation(
                    user_id=str(user.id),
                    slot_no=1,
                    slot_value=Decimal(str(slot_costs[0]))  # 0.0022 BNB
                )
                
                if slot_1_result["success"]:
                    print(f"✅ Slot 1 (Explorer) activated for temp user {user.id}")
                else:
                    print(f"⚠️ Slot 1 activation failed: {slot_1_result.get('error', 'Unknown error')}")
                
                # Activate Slot 2 (Contributor) - now with proper tree placement for reserve routing
                slot_2_result = auto_upgrade_service.process_binary_slot_activation(
                    user_id=str(user.id),
                    slot_no=2,
                    slot_value=Decimal(str(slot_costs[1]))  # 0.0044 BNB
                )
                
                if slot_2_result["success"]:
                    print(f"✅ Slot 2 (Contributor) activated for temp user {user.id}")
                else:
                    print(f"⚠️ Slot 2 activation failed: {slot_2_result.get('error', 'Unknown error')}")
                    
            else:
                print(f"⚠️ Binary tree placement failed for temp user {user.id}")
                
        except Exception as e:
            print(f"Error in temp user binary tree placement and slot activation: {e}")
            # Don't fail user creation if tree placement fails
        # Note: Binary slot activations and reserve routing are handled by AutoUpgradeService above.
        # The old catalog-based activation path is removed to avoid duplicates and ensure reserve routing works correctly.
        
        # Create PartnerGraph for the new user
        try:
            if not PartnerGraph.objects(user_id=ObjectId(user.id)).first():
                PartnerGraph(user_id=ObjectId(user.id)).save()
        except Exception:
            pass
        
        # Update referrer's PartnerGraph
        try:
            ref_pg = PartnerGraph.objects(user_id=ObjectId(upline_user.id)).first()
            if not ref_pg:
                ref_pg = PartnerGraph(user_id=ObjectId(upline_user.id))
            directs = ref_pg.directs or []
            if ObjectId(user.id) not in [ObjectId(d) for d in directs]:
                directs.append(ObjectId(user.id))
            ref_pg.directs = directs
            ref_pg.directs_count_by_program = ref_pg.directs_count_by_program or {}
            ref_pg.directs_count_by_program['binary'] = int(ref_pg.directs_count_by_program.get('binary', 0)) + 1
            ref_pg.last_updated = datetime.utcnow()
            ref_pg.save()
        except Exception:
            pass
        
        # Update referrer's partners_count in User collection
        try:
            # Count total direct partners for the referrer
            total_direct_partners = User.objects(refered_by=ObjectId(upline_user.id)).count()
            
            # Update the referrer's partners_count
            User.objects(id=ObjectId(upline_user.id)).update_one(
                set__partners_count=total_direct_partners,
                set__updated_at=datetime.utcnow()
            )
            
            print(f"✅ Updated partners_count for referrer {upline_user.uid}: {total_direct_partners}")
        except Exception as e:
            print(f"⚠️ Failed to update partners_count for referrer: {str(e)}")
            pass
        
        # Update user's rank based on slot activations
        try:
            from ..rank.service import RankService
            rank_service = RankService()
            
            # Update the new user's rank
            user_rank_result = rank_service.update_user_rank(str(user.id))
            if user_rank_result.get("success"):
                new_rank = user_rank_result.get('new_rank', {})
                rank_name = new_rank.get('name', 'Unknown') if isinstance(new_rank, dict) else 'Unknown'
                print(f"✅ Updated rank for new user {user.uid}: {rank_name}")
            else:
                print(f"⚠️ Failed to update rank for new user: {user_rank_result.get('error', 'Unknown error')}")
                
            # Update the referrer's rank
            referrer_rank_result = rank_service.update_user_rank(str(upline_user.id))
            if referrer_rank_result.get("success"):
                new_rank = referrer_rank_result.get('new_rank', {})
                rank_name = new_rank.get('name', 'Unknown') if isinstance(new_rank, dict) else 'Unknown'
                print(f"✅ Updated rank for referrer {upline_user.uid}: {rank_name}")
            else:
                print(f"⚠️ Failed to update rank for referrer: {referrer_rank_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"⚠️ Failed to update ranks: {str(e)}")
            pass
        
        # Generate access token
        try:
            token_obj = authentication_service.create_access_token(data={"user_id": str(user.id)})
            # Extract actual token string
            if hasattr(token_obj, 'access_token'):
                access_token = token_obj.access_token
            elif isinstance(token_obj, str):
                access_token = token_obj
            else:
                access_token = str(token_obj)
        except Exception:
            access_token = None
        
        # Return full user data + token + auto-generated credentials
        user_data = {
            "_id": str(user.id),
            "token": access_token,
            "token_type": "bearer",
            "user": {
                "_id": str(user.id),
                "uid": user.uid,
                "refer_code": user.refer_code,
                "refered_by": str(user.refered_by) if user.refered_by else None,
                "wallet_address": user.wallet_address,
                "name": user.name,
                "role": user.role,
                "email": user.email,
                "status": user.status if hasattr(user, 'status') else "active",
                "is_activated": user.is_activated if hasattr(user, 'is_activated') else False,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            },
            "auto_password": auto_password,  # Return generated password (user should save this)
            "refered_by_code": refered_by_code,
            "refered_by_name": upline_user.name if upline_user else None,
            "binary_joined": user.binary_joined,
            "matrix_joined": user.matrix_joined if hasattr(user, 'matrix_joined') else False,
            "global_joined": user.global_joined if hasattr(user, 'global_joined') else False
        }
        
        return user_data, None
        
    except Exception as e:
        return None, str(e)


def create_user_service(payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Create a new user if wallet_address is unique.
    Auto-generates uid and refer_code.
    Looks up refered_by code to get upline_id.

    Returns (result, error):
      - result: {"_id": str, "token": str, "token_type": "bearer"}
      - error: error message string if any
    """
    required_fields = ["email", "name", "password", "refered_by", "wallet_address"]

    missing = [f for f in required_fields if not payload.get(f)]
    if missing:
        return None, f"Missing required fields: {', '.join(missing)}"

    wallet_address = payload.get("wallet_address")

    # Uniqueness check by wallet_address
    existing = User.objects(wallet_address=wallet_address).first()
    if existing:
        return None, "User with this wallet_address already exists"
    
    # Look up refered_by code to get upline_id
    refered_by_code = payload.get("refered_by")
    upline_user = User.objects(refer_code=refered_by_code).first()
    if not upline_user:
        return None, f"Referral code '{refered_by_code}' not found"
    
    upline_id = str(upline_user.id)
    
    # Auto-generate unique uid
    import time
    import random
    uid = f"user{int(time.time() * 1000)}{random.randint(1000, 9999)}"
    
    # Ensure uid is unique
    while User.objects(uid=uid).first():
        uid = f"user{int(time.time() * 1000)}{random.randint(1000, 9999)}"
    
    # Auto-generate unique refer_code
    refer_code = f"RC{int(time.time() * 1000)}{random.randint(100, 999)}"
    
    # Ensure refer_code is unique
    while User.objects(refer_code=refer_code).first():
        refer_code = f"RC{int(time.time() * 1000)}{random.randint(100, 999)}"
    
    # MANDATORY BINARY JOIN ENFORCEMENT
    # According to PROJECT_DOCUMENTATION.md Section 5: "Users MUST follow this exact sequence: Binary → Matrix → Global"
    binary_payment_tx = payload.get("binary_payment_tx")
    if not binary_payment_tx:
        return None, "Binary program join is mandatory. Must provide binary_payment_tx (0.0066 BNB payment proof)"

    try:
        # Step 0: Preconditions - Validate referrer exists
        # Note: refered_by is now a referral code, not ObjectId
        # The upline_id was already validated and set above
        pass  # Validation already done above when looking up upline_user

        # Step 0: Record blockchain payments (frontend passes tx hashes)
        binary_payment_tx = payload.get("binary_payment_tx")
        matrix_payment_tx = payload.get("matrix_payment_tx")
        global_payment_tx = payload.get("global_payment_tx")
        network = payload.get("network") or "BSC"
        # Hash password if provided
        raw_password = payload.get("password")
        hashed_password = None
        if raw_password:
            hashed_password = authentication_service.get_password_hash(raw_password)

        user = User(
            uid=uid,
            refer_code=refer_code,
            refered_by=upline_id,
            wallet_address=wallet_address,
            name=payload.get("name"),
            role="user",  # Always set to user
            email=payload.get("email"),
            password=hashed_password,
        )
        user.save()

        # Initialize program participation flags based on provided payments
        # Set join timestamps for mandatory sequence tracking
        try:
            current_time = datetime.utcnow()
            updates: Dict[str, Any] = {
                'binary_joined': True,  # Binary is required per docs; first 2 slots will activate
                'binary_joined_at': current_time
            }
            if matrix_payment_tx:
                updates['matrix_joined'] = True
                updates['matrix_joined_at'] = current_time
            if global_payment_tx:
                updates['global_joined'] = True
                updates['global_joined_at'] = current_time
            if updates:
                User.objects(id=user.id).update_one(**{f'set__{k}': v for k, v in updates.items()})
                user.reload()
        except Exception:
            pass

        # Create PartnerGraph for the new user (if not exists)
        try:
            if not PartnerGraph.objects(user_id=ObjectId(user.id)).first():
                PartnerGraph(user_id=ObjectId(user.id)).save()
        except Exception:
            pass

        # Update referrer's PartnerGraph to add this user as a direct
        try:
            ref_pg = PartnerGraph.objects(user_id=ObjectId(upline_user.id)).first()
            if not ref_pg:
                ref_pg = PartnerGraph(user_id=ObjectId(upline_user.id))
            directs = ref_pg.directs or []
            if ObjectId(user.id) not in [ObjectId(d) for d in directs]:
                directs.append(ObjectId(user.id))
            ref_pg.directs = directs
            ref_pg.directs_count_by_program = ref_pg.directs_count_by_program or {}
            # Increment counts by program where joined
            ref_pg.directs_count_by_program['binary'] = int(ref_pg.directs_count_by_program.get('binary', 0)) + 1
            if user.matrix_joined:
                ref_pg.directs_count_by_program['matrix'] = int(ref_pg.directs_count_by_program.get('matrix', 0)) + 1
            if user.global_joined:
                ref_pg.directs_count_by_program['global'] = int(ref_pg.directs_count_by_program.get('global', 0)) + 1
            ref_pg.last_updated = datetime.utcnow()
            ref_pg.save()
            
            # Update referrer's partners_count in User collection
            # Count total direct partners for the referrer
            total_direct_partners = User.objects(refered_by=ObjectId(upline_user.id)).count()
            
            # Update the referrer's partners_count
            User.objects(id=ObjectId(upline_user.id)).update_one(
                set__partners_count=total_direct_partners,
                set__updated_at=datetime.utcnow()
            )
            
            print(f"✅ Updated partners_count for referrer {upline_user.uid}: {total_direct_partners}")
            
            # Update user's rank based on slot activations
            try:
                from ..rank.service import RankService
                rank_service = RankService()
                
                # Update the new user's rank
                user_rank_result = rank_service.update_user_rank(str(user.id))
                if user_rank_result.get("success"):
                    new_rank = user_rank_result.get('new_rank', {})
                    rank_name = new_rank.get('name', 'Unknown') if isinstance(new_rank, dict) else 'Unknown'
                    print(f"✅ Updated rank for new user {user.uid}: {rank_name}")
                else:
                    print(f"⚠️ Failed to update rank for new user: {user_rank_result.get('error', 'Unknown error')}")
                    
                # Update the referrer's rank
                referrer_rank_result = rank_service.update_user_rank(str(upline_user.id))
                if referrer_rank_result.get("success"):
                    new_rank = referrer_rank_result.get('new_rank', {})
                    rank_name = new_rank.get('name', 'Unknown') if isinstance(new_rank, dict) else 'Unknown'
                    print(f"✅ Updated rank for referrer {upline_user.uid}: {rank_name}")
                else:
                    print(f"⚠️ Failed to update rank for referrer: {referrer_rank_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"⚠️ Failed to update ranks: {str(e)}")
                pass
            
            # Royal Captain / President counters on join (Matrix+Global for Royal Captain; direct invites for President)
            try:
                # Royal Captain Bonus Tracking
                if user.matrix_joined and user.global_joined:
                    # Increment referrer's direct Matrix+Global referral count
                    if hasattr(upline_user, 'royal_captain_qualifications'):
                        upline_user.royal_captain_qualifications = int(getattr(upline_user, 'royal_captain_qualifications', 0) or 0) + 1
                    
                    # Check if referrer maintains 5 direct Matrix+Global referrals
                    if upline_user.royal_captain_qualifications >= 5:
                        # Get referrer's global team size
                        ref_pg = PartnerGraph.objects(user_id=ObjectId(upline_user.id)).first()
                        global_team_size = len(ref_pg.global_team_members) if ref_pg and ref_pg.global_team_members else 0
                        
                        # Check global team size thresholds: 0/10/20/30/40/50
                        if global_team_size >= 0 and global_team_size < 10:
                            award_amount = 200
                        elif global_team_size >= 10 and global_team_size < 20:
                            award_amount = 200
                        elif global_team_size >= 20 and global_team_size < 30:
                            award_amount = 200
                        elif global_team_size >= 30 and global_team_size < 40:
                            award_amount = 200
                        elif global_team_size >= 40 and global_team_size < 50:
                            award_amount = 250
                        elif global_team_size >= 50:
                            award_amount = 250
                        else:
                            award_amount = 0
                        
                        # Create RoyalCaptainBonus record if threshold met
                        if award_amount > 0:
                            try:
                                from modules.royal_captain.model import RoyalCaptainBonus
                                RoyalCaptainBonus(
                                    user_id=ObjectId(upline_user.id),
                                    award_amount=award_amount,
                                    global_team_size=global_team_size,
                                    matrix_global_referrals=upline_user.royal_captain_qualifications,
                                    status='pending',
                                    created_at=datetime.utcnow()
                                ).save()
                            except Exception:
                                pass
                
                # President Reward Tracking
                if hasattr(upline_user, 'president_reward_qualifications'):
                    upline_user.president_reward_qualifications = int(getattr(upline_user, 'president_reward_qualifications', 0) or 0) + 1
                
                # Get referrer's global team size for President Reward
                ref_pg = PartnerGraph.objects(user_id=ObjectId(upline_user.id)).first()
                global_team_size = len(ref_pg.global_team_members) if ref_pg and ref_pg.global_team_members else 0
                direct_invites = upline_user.president_reward_qualifications
                
                # Evaluate qualification tiers
                award_amount = 0
                if direct_invites >= 10 and global_team_size >= 80:
                    award_amount = 500  # Tier 1
                elif global_team_size >= 150 and global_team_size < 200:
                    award_amount = 700  # Tier 2
                elif global_team_size >= 200 and global_team_size < 250:
                    award_amount = 700  # Tier 2
                elif global_team_size >= 250 and global_team_size < 300:
                    award_amount = 700  # Tier 2
                elif global_team_size >= 300 and global_team_size < 400:
                    award_amount = 700  # Tier 2
                elif direct_invites >= 15 and global_team_size >= 400 and global_team_size < 500:
                    award_amount = 800  # Tier 3
                elif direct_invites >= 15 and global_team_size >= 500 and global_team_size < 600:
                    award_amount = 800  # Tier 3
                elif direct_invites >= 15 and global_team_size >= 600 and global_team_size < 700:
                    award_amount = 800  # Tier 3
                elif direct_invites >= 15 and global_team_size >= 700 and global_team_size < 1000:
                    award_amount = 800  # Tier 3
                elif direct_invites >= 20 and global_team_size >= 1000 and global_team_size < 1500:
                    award_amount = 1500  # Tier 4
                elif global_team_size >= 1500 and global_team_size < 2000:
                    award_amount = 1500  # Tier 5
                elif global_team_size >= 2000 and global_team_size < 2500:
                    award_amount = 2000  # Tier 5
                elif global_team_size >= 2500 and global_team_size < 3000:
                    award_amount = 2500  # Tier 5
                elif global_team_size >= 3000 and global_team_size < 4000:
                    award_amount = 2500  # Tier 5
                elif direct_invites >= 30 and global_team_size >= 4000:
                    award_amount = 5000  # Tier 6
                
                # Create PresidentReward record if any threshold met
                if award_amount > 0:
                    try:
                        from modules.president_reward.model import PresidentReward
                        PresidentReward(
                            user_id=ObjectId(upline_user.id),
                            award_amount=award_amount,
                            global_team_size=global_team_size,
                            direct_invites=direct_invites,
                            status='pending',
                            created_at=datetime.utcnow()
                        ).save()
                    except Exception:
                        pass
                
                upline_user.updated_at = datetime.utcnow()
                upline_user.save()
            except Exception:
                pass
        except Exception:
            pass

        # Persist blockchain join payments as events (idempotency via tx_hash unique)
        try:
            if binary_payment_tx:
                BlockchainEvent(
                    tx_hash=binary_payment_tx,
                    event_type='join_payment',
                    event_data={
                        'program': 'binary',
                        'expected_amount': '0.0066',
                        'currency': 'BNB',
                        'network': network,
                        'user_id': str(user.id),
                        'referrer_id': str(upline_user.id)
                    },
                    status='processed',
                    processed_at=datetime.utcnow()
                ).save()
        except Exception:
            pass
        try:
            if matrix_payment_tx:
                BlockchainEvent(
                    tx_hash=matrix_payment_tx,
                    event_type='join_payment',
                    event_data={
                        'program': 'matrix',
                        'expected_amount': '11',
                        'currency': 'USDT',
                        'network': network,
                        'user_id': str(user.id),
                        'referrer_id': str(upline_user.id)
                    },
                    status='processed',
                    processed_at=datetime.utcnow()
                ).save()
        except Exception:
            pass
        try:
            if global_payment_tx:
                BlockchainEvent(
                    tx_hash=global_payment_tx,
                    event_type='join_payment',
                    event_data={
                        'program': 'global',
                        'expected_amount': '33',
                        'currency': 'USD',
                        'network': network,
                        'user_id': str(user.id),
                        'referrer_id': str(upline_user.id)
                    },
                    status='processed',
                    processed_at=datetime.utcnow()
                ).save()
        except Exception:
            pass

        # Initialize BinaryAutoUpgrade tracking
        try:
            BinaryAutoUpgrade.objects(user_id=ObjectId(user.id)).update_one(
                set__current_slot_no=1,
                set__current_level=1,
                set__partners_required=2,
                set__partners_available=0,
                set__is_eligible=False,
                set__can_upgrade=False,
                set__is_active=True,
                set__updated_at=datetime.utcnow(),
                upsert=True
            )
        except Exception as e:
            print(f"⚠️ Failed to seed BinaryAutoUpgrade for user {user.id}: {e}")

        # Create Newcomer Support record (one per user)
        try:
            if not NewcomerSupport.objects(user_id=ObjectId(user.id)).first():
                NewcomerSupport(
                    user_id=ObjectId(user.id),
                    is_eligible=False,
                    is_active=False,
                    joined_at=datetime.utcnow()
                ).save()
        except Exception:
            pass

        # Auto tree placement handled via BackgroundTasks in router to avoid blocking
        placement_resp = None

        # Auto-activate first two binary slots (Explorer=1, Contributor=2)
        try:
            commission_service = CommissionService()
            total_join_amount = Decimal('0')
            currency = ensure_currency_for_program('binary', 'BNB')
            for slot_no in [1, 2]:
                catalog = SlotCatalog.objects(program='binary', slot_no=slot_no, is_active=True).first()
                if not catalog:
                    continue
                amount = catalog.price or Decimal('0')
                # Sum for joining commission (computed once after both slots)
                total_join_amount += (amount or Decimal('0'))
                activation = SlotActivation(
                    user_id=ObjectId(user.id),
                    program='binary',
                    slot_no=slot_no,
                    slot_name=catalog.name,
                    activation_type='initial',
                    upgrade_source='auto',
                    amount_paid=amount,
                    currency=currency,
                    tx_hash=f"AUTO-{user.uid}-S{slot_no}",
                    is_auto_upgrade=True,
                    status='completed'
                )
                activation.save()

                # Update user's binary_slots list with auto-activated slot
                from .model import BinarySlotInfo
                slot_info = BinarySlotInfo(
                    slot_name=catalog.name,
                    slot_value=float(amount or Decimal('0')),
                    level=catalog.level,
                    is_active=True,
                    activated_at=datetime.utcnow(),
                    upgrade_cost=float(catalog.upgrade_cost or Decimal('0')),
                    total_income=float(catalog.total_income or Decimal('0')),
                    wallet_amount=float(catalog.wallet_amount or Decimal('0'))
                )
                
                # Check if slot already exists in user's binary_slots list
                existing_slot = None
                for i, existing_slot_info in enumerate(user.binary_slots):
                    if existing_slot_info.slot_name == catalog.name:
                        existing_slot = i
                        break
                
                if existing_slot is not None:
                    # Update existing slot
                    user.binary_slots[existing_slot] = slot_info
                else:
                    # Add new slot
                    user.binary_slots.append(slot_info)
                
                user.save()

                # Blockchain event for slot activation (idempotent via tx_hash in BlockchainEvent)
                try:
                    BlockchainEvent(
                        tx_hash=f"AUTO-{user.uid}-S{slot_no}",
                        event_type='slot_activated',
                        event_data={
                            'program': 'binary',
                            'slot_no': slot_no,
                            'slot_name': catalog.name,
                            'amount': str(amount or Decimal('0')),
                            'currency': currency,
                            'user_id': str(user.id)
                        },
                        status='processed',
                        processed_at=datetime.utcnow()
                    ).save()
                except Exception:
                    pass

                # Earning history for slot activation
                try:
                    EarningHistory(
                        user_id=ObjectId(user.id),
                        earning_type='binary_slot',
                        program='binary',
                        amount=float(amount or Decimal('0')),
                        currency=currency,
                        slot_name=catalog.name,
                        slot_level=catalog.level,
                        description=f"Auto activation of binary slot {slot_no}"
                    ).save()
                except Exception:
                    pass

                # Tree Upline Reserve System handled inside AutoUpgradeService routing.
                # Skipping legacy 30% reserve flow to prevent double-credit and wrong PI on slot 2.

                # Distribute funds handled inside AutoUpgradeService for Binary:
                # - Slot 1: full to direct upline (already implemented)
                # - Slot 2+: reserve routing or pools inside AutoUpgradeService
                # Intentionally skip duplicate distribution here for binary
                
                # Trigger upgrade commission logic for each activated slot
                if amount > 0:
                    try:
                        commission_service.calculate_upgrade_commission(
                            from_user_id=str(user.id),
                            program='binary',
                            slot_no=slot_no,
                            slot_name=catalog.name,
                            amount=amount,
                            currency=currency
                        )
                        # Update user rank after each slot activation
                        try:
                            RankService().update_user_rank(user_id=str(user.id))
                        except Exception:
                            pass
                    except Exception:
                        pass
                # Jackpot free coupon awards for relevant slots
                try:
                    JackpotService.award_free_coupon_for_binary_slot(user_id=str(user.id), slot_no=slot_no)
                except Exception:
                    pass

            # Skipping legacy joining commission on Slot 1+2 bundle to avoid PI on reserve-routed Slot 2.
        except Exception:
            pass

        # Issue JWT token for frontend
        token = authentication_service.create_access_token(
            data={
                "sub": user.uid,
                "user_id": str(user.id),
            }
        )

        # STEP 3: Matrix join (optional): placement, slot-1 activation, joining commission
        try:
            if matrix_payment_tx:
                # Placement in Matrix tree (slot 1)
                # Placement scheduled via router background task
                pass

                # Activate Matrix Slot-1 using provided tx
                matrix_catalog = SlotCatalog.objects(program='matrix', slot_no=1, is_active=True).first()
                if matrix_catalog:
                    matrix_currency = ensure_currency_for_program('matrix', 'USDT')
                    matrix_amount = matrix_catalog.price or Decimal('0')
                    activation = SlotActivation(
                        user_id=ObjectId(user.id),
                        program='matrix',
                        slot_no=1,
                        slot_name=matrix_catalog.name,
                        activation_type='initial',
                        upgrade_source='auto',
                        amount_paid=matrix_amount,
                        currency=matrix_currency,
                        tx_hash=matrix_payment_tx,
                        is_auto_upgrade=True,
                        status='completed'
                    )
                    activation.save()

                    # Blockchain event
                    try:
                        BlockchainEvent(
                            tx_hash=matrix_payment_tx,
                            event_type='slot_activated',
                            event_data={
                                'program': 'matrix',
                                'slot_no': 1,
                                'slot_name': matrix_catalog.name,
                                'amount': str(matrix_amount or Decimal('0')),
                                'currency': matrix_currency,
                                'user_id': str(user.id)
                            },
                            status='processed',
                            processed_at=datetime.utcnow()
                        ).save()
                    except Exception:
                        pass

                    # Earning history for matrix slot activation
                    try:
                        EarningHistory(
                            user_id=ObjectId(user.id),
                            earning_type='matrix_slot',
                            program='matrix',
                            amount=float(matrix_amount or Decimal('0')),
                            currency=matrix_currency,
                            slot_name=matrix_catalog.name,
                            slot_level=matrix_catalog.level,
                            description="Activation of matrix slot 1"
                        ).save()
                    except Exception:
                        pass

                    # Joining commission 10%
                    try:
                        commission_service.calculate_joining_commission(
                            from_user_id=str(user.id),
                            program='matrix',
                            amount=matrix_amount,
                            currency=matrix_currency
                        )
                    except Exception:
                        pass
                    
                    # Spark Bonus: contribute 8% from Matrix program to Spark Bonus fund
                    try:
                        spark_contribution = matrix_amount * Decimal('0.08')
                        spark_service = SparkService()
                        spark_service.contribute_to_fund(
                            amount=float(spark_contribution),
                            program='matrix',
                            source_user_id=str(user.id),
                            source_type='matrix_join',
                            currency=matrix_currency
                        )
                    except Exception:
                        pass

                    # Update user rank based on new matrix activation
                    try:
                        RankService().update_user_rank(user_id=str(user.id))
                    except Exception:
                        pass

                    # Mentorship program join & eligibility check for this user
                    try:
                        ms = MentorshipService()
                        ms.join_mentorship_program(user_id=str(user.id))
                        ms.check_eligibility(user_id=str(user.id), force_check=True)
                    except Exception:
                        pass

                    # Spark: compute triple-entry eligibility for today when user has all three
                    try:
                        if user.binary_joined and user.matrix_joined and user.global_joined:
                            SparkService.compute_triple_entry_eligibles(datetime.utcnow())
                    except Exception:
                        pass

                    # Seed MatrixAutoUpgrade tracking for this user (slot 1 active)
                    try:
                        if not MatrixAutoUpgrade.objects(user_id=ObjectId(user.id)).first():
                            MatrixAutoUpgrade(
                                user_id=ObjectId(user.id),
                                current_slot_no=1,
                                current_level=1,
                                middle_three_required=3,
                                middle_three_available=0,
                                is_eligible=False,
                                next_upgrade_cost=Decimal('0'),
                                can_upgrade=False
                            ).save()
                    except Exception:
                        pass
        except Exception:
            pass

        # STEP 4: Global join (optional): placement, slot-1 activation, joining commission
        try:
            if global_payment_tx:
                # Placement in Global tree (Phase-1 Slot-1)
                # Placement scheduled via router background task
                pass

                # Activate Global Slot-1 using provided tx
                global_catalog = SlotCatalog.objects(program='global', slot_no=1, is_active=True).first()
                if global_catalog:
                    global_currency = ensure_currency_for_program('global', 'USDT')
                    global_amount = global_catalog.price or Decimal('0')
                    activation = SlotActivation(
                        user_id=ObjectId(user.id),
                        program='global',
                        slot_no=1,
                        slot_name=global_catalog.name,
                        activation_type='initial',
                        upgrade_source='auto',
                        amount_paid=global_amount,
                        currency=global_currency,
                        tx_hash=global_payment_tx,
                        is_auto_upgrade=True,
                        status='completed'
                    )
                    activation.save()

                    # Blockchain event
                    try:
                        BlockchainEvent(
                            tx_hash=global_payment_tx,
                            event_type='slot_activated',
                            event_data={
                                'program': 'global',
                                'slot_no': 1,
                                'slot_name': global_catalog.name,
                                'amount': str(global_amount or Decimal('0')),
                                'currency': global_currency,
                                'user_id': str(user.id)
                            },
                            status='processed',
                            processed_at=datetime.utcnow()
                        ).save()
                    except Exception:
                        pass

                    # Earning history for global slot activation
                    try:
                        EarningHistory(
                            user_id=ObjectId(user.id),
                            earning_type='global_slot',
                            program='global',
                            amount=float(global_amount or Decimal('0')),
                            currency=global_currency,
                            slot_name=global_catalog.name,
                            slot_level=global_catalog.level,
                            description="Activation of global slot 1"
                        ).save()
                    except Exception:
                        pass

                    # Joining commission 10%
                    try:
                        commission_service.calculate_joining_commission(
                            from_user_id=str(user.id),
                            program='global',
                            amount=global_amount,
                            currency=global_currency
                        )
                    except Exception:
                        pass
                    
                    # Spark Bonus: contribute 5% from Global program to Triple Entry Reward fund
                    try:
                        triple_entry_contribution = global_amount * Decimal('0.05')
                        spark_service = SparkService()
                        spark_service.contribute_to_fund(
                            amount=float(triple_entry_contribution),
                            program='global',
                            source_user_id=str(user.id),
                            source_type='global_join',
                            currency=global_currency
                        )
                    except Exception:
                        pass

                    # Update user rank based on new global activation
                    try:
                        RankService().update_user_rank(user_id=str(user.id))
                    except Exception:
                        pass

                    # Seed GlobalPhaseProgression tracking for this user (Phase-1 Slot-1)
                    try:
                        if not GlobalPhaseProgression.objects(user_id=ObjectId(user.id)).first():
                            GlobalPhaseProgression(
                                user_id=ObjectId(user.id),
                                current_phase='PHASE-1',
                                current_slot_no=1,
                                phase_position=1,
                                phase_1_members_required=4,
                                phase_1_members_current=0,
                                phase_2_members_required=8,
                                phase_2_members_current=0,
                                global_team_size=0,
                                global_team_members=[],
                                is_phase_complete=False,
                                next_phase_ready=False,
                                auto_progression_enabled=True,
                                progression_triggered=False,
                                is_active=True
                            ).save()
                    except Exception:
                        pass
        except Exception:
            pass

        # TREE PLACEMENT INTEGRATION - PROJECT_DOCUMENTATION.md Section 6
        # "When a user joins, the first 2 slots of the binary program should become active"
        try:
            # Import TreeService for binary tree placement
            from modules.tree.service import TreeService
            from modules.auto_upgrade.service import AutoUpgradeService
            from decimal import Decimal
            
            # Create binary tree placement for the new user
            tree_service = TreeService()
            
            # Place user in binary tree for BOTH slots before activation
            # Slot 1 placement
            binary_placement_1 = tree_service.place_user_in_tree(
                user_id=user.id,
                referrer_id=ObjectId(upline_id),
                program='binary',
                slot_no=1  # First slot
            )
            
            # Slot 2 placement (needed for reserve routing logic)
            binary_placement_2 = tree_service.place_user_in_tree(
                user_id=user.id,
                referrer_id=ObjectId(upline_id),
                program='binary',
                slot_no=2  # Second slot
            )
            
            if binary_placement_1:
                print(f"✅ Binary tree placement created for user {user.id} under {upline_id} (slot 1)")
                if binary_placement_2:
                    print(f"✅ Binary tree placement created for user {user.id} under {upline_id} (slot 2)")
                
                # 🚀 AUTOMATIC BINARY SLOT ACTIVATION
                # When user joins, automatically activate Slot 1 and Slot 2
                auto_upgrade_service = AutoUpgradeService()
                
                # Slot costs from PROJECT_DOCUMENTATION.md
                slot_costs = [0.0022, 0.0044, 0.0088, 0.0176, 0.0352, 0.0704, 0.1408, 0.2816, 0.5632, 1.1264, 2.2528, 4.5056, 9.0112, 18.0224, 36.0448, 72.0896]
                
                # Activate Slot 1 (Explorer)
                slot_1_result = auto_upgrade_service.process_binary_slot_activation(
                    user_id=str(user.id),
                    slot_no=1,
                    slot_value=Decimal(str(slot_costs[0]))  # 0.0022 BNB
                )
                
                if slot_1_result["success"]:
                    print(f"✅ Slot 1 (Explorer) activated for user {user.id}")
                else:
                    print(f"⚠️ Slot 1 activation failed: {slot_1_result.get('error', 'Unknown error')}")
                
                # Activate Slot 2 (Contributor)
                slot_2_result = auto_upgrade_service.process_binary_slot_activation(
                    user_id=str(user.id),
                    slot_no=2,
                    slot_value=Decimal(str(slot_costs[1]))  # 0.0044 BNB
                )
                
                if slot_2_result["success"]:
                    print(f"✅ Slot 2 (Contributor) activated for user {user.id}")
                else:
                    print(f"⚠️ Slot 2 activation failed: {slot_2_result.get('error', 'Unknown error')}")
                    
            else:
                print(f"⚠️ Binary tree placement failed for user {user.id}")
                
        except Exception as e:
            print(f"Error in binary tree placement and slot activation: {e}")
            # Don't fail user creation if tree placement fails

        return {
            "_id": str(user.id),
            "token": token.access_token,
            "token_type": token.token_type,
            "user": {
                "_id": str(user.id),
                "uid": user.uid,
                "refer_code": user.refer_code,
                "refered_by": str(user.refered_by) if user.refered_by else None,
                "wallet_address": user.wallet_address,
                "name": user.name,
                "role": user.role,
                "email": user.email,
                "status": user.status if hasattr(user, 'status') else "active",
                "is_activated": user.is_activated if hasattr(user, 'is_activated') else False,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
        }, None

    except (ValidationError, NotUniqueError) as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)


def create_root_user_service(payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Create a root (mother) account without requiring a referrer/upline."""
    try:
        required_fields = ["uid", "refer_code", "wallet_address", "name"]
        missing = [f for f in required_fields if not payload.get(f)]
        if missing:
            return None, f"Missing required fields: {', '.join(missing)}"

        # Prevent duplicates
        if User.objects(uid=payload["uid"]).first() or User.objects(refer_code=payload["refer_code"]).first() or User.objects(wallet_address=payload["wallet_address"]).first():
            return None, "Root user with uid/refer_code/wallet already exists"

        # Create a self-referenced root upline to satisfy schema where needed
        raw_password = payload.get("password")
        hashed_password = authentication_service.get_password_hash(raw_password) if raw_password else None

        user = User(
            uid=payload.get("uid"),
            refer_code=payload.get("refer_code"),
            refered_by=None,
            wallet_address=payload.get("wallet_address"),
            name=payload.get("name"),
            role=payload.get("role") or "admin",
            email=payload.get("email"),
            password=hashed_password,
            status='active',
            binary_joined=True
        )
        user.save()

        # Initialize partner graph
        try:
            if not PartnerGraph.objects(user_id=ObjectId(user.id)).first():
                PartnerGraph(user_id=ObjectId(user.id)).save()
        except Exception:
            pass

        # Seed a self tree placement for ROOT so binary tree view works for ROOT
        try:
            existing_root_placement = TreePlacement.objects(
                user_id=ObjectId(user.id), program='binary', slot_no=1, is_active=True
            ).first()
            if not existing_root_placement:
                TreePlacement(
                    user_id=ObjectId(user.id),
                    program='binary',
                    parent_id=None,
                    upline_id=None,  # Root has no upline
                    position='root',
                    level=1,
                    slot_no=1,
                    is_active=True
                ).save()
        except Exception:
            pass

        # Seed BinaryAutoUpgrade tracking for root
        try:
            BinaryAutoUpgrade.objects(user_id=ObjectId(user.id)).update_one(
                set__current_slot_no=1,
                set__current_level=1,
                set__partners_required=2,
                set__partners_available=0,
                set__is_eligible=False,
                set__can_upgrade=False,
                set__is_active=True,
                set__updated_at=datetime.utcnow(),
                upsert=True
            )
        except Exception as e:
            print(f"⚠️ Failed to seed BinaryAutoUpgrade for root {user.id}: {e}")

        # Issue token
        token = authentication_service.create_access_token(
            data={
                "sub": user.uid,
                "user_id": str(user.id),
            }
        )

        return {
            "_id": str(user.id),
            "token": token.access_token,
            "token_type": token.token_type,
            "user": {
                "_id": str(user.id),
                "uid": user.uid,
                "refer_code": user.refer_code,
                "refered_by": str(user.refered_by) if user.refered_by else None,
                "wallet_address": user.wallet_address,
                "name": user.name,
                "role": user.role,
                "email": user.email,
                "status": user.status if hasattr(user, 'status') else "active",
                "is_activated": user.is_activated if hasattr(user, 'is_activated') else False,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
        }, None

    except Exception as e:
        return None, str(e)


