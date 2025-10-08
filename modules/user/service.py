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
            
            # Return user data in the exact format as shown in the collection
            user_data = {
                "success": True,
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
        """Get community members (referred users) for a user"""
        try:
            # Validate program type
            if program_type not in ["binary", "matrix"]:
                return {"success": False, "error": "Invalid program type. Must be 'binary' or 'matrix'"}
            
            # Get the user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Build query for referred users
            query = {"refered_by": ObjectId(user_id)}
            
            # Get referred users with pagination
            skip = (page - 1) * limit
            referred_users = User.objects(**query).skip(skip).limit(limit).order_by('-created_at')
            
            # Get total count for pagination
            total_count = User.objects(**query).count()
            
            # Format response
            community_members = []
            for member in referred_users:
                community_members.append({
                    "id": str(member.id),
                    "uid": member.uid,
                    "refer_code": member.refer_code,
                    "name": member.name,
                    "email": member.email,
                    "role": member.role,
                    "wallet_address": member.wallet_address,
                    "created_at": member.created_at,
                    "binary_joined": member.binary_joined,
                    "matrix_joined": member.matrix_joined,
                    "global_joined": member.global_joined,
                    "current_rank": getattr(member, 'current_rank', 'Bitron')
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
            BinaryAutoUpgrade(
                user_id=ObjectId(user.id),
                current_slot_no=1,
                current_level=1,
                partners_required=2,
                partners_available=0,
                is_eligible=False,
                can_upgrade=False
            ).save()
        except Exception:
            pass

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

                # Tree Upline Reserve System - 30% of slot fee goes to tree upline's reserve
                try:
                    from .tree_reserve_service import TreeUplineReserveService
                    reserve_service = TreeUplineReserveService()
                    
                    # Find tree upline for this slot
                    tree_upline = reserve_service.find_tree_upline(str(user.id), 'binary', slot_no)
                    
                    if tree_upline:
                        # Calculate 30% reserve amount
                        reserve_amount = reserve_service.calculate_reserve_amount(amount)
                        
                        # Add to tree upline's reserve fund
                        success, message = reserve_service.add_to_reserve_fund(
                            tree_upline["user_id"],
                            'binary',
                            slot_no,
                            reserve_amount,
                            str(user.id),
                            f"AUTO-{user.uid}-S{slot_no}-RESERVE"
                        )
                        
                        if success:
                            print(f"Added {reserve_amount} to tree upline {tree_upline['uid']} reserve: {message}")
                        else:
                            print(f"Failed to add to reserve fund: {message}")
                    else:
                        # No tree upline found, transfer to mother account
                        reserve_amount = reserve_service.calculate_reserve_amount(amount)
                        success, message = reserve_service.transfer_to_mother_account(
                            str(user.id),
                            'binary',
                            slot_no,
                            reserve_amount,
                            f"AUTO-{user.uid}-S{slot_no}-MOTHER"
                        )
                        if success:
                            print(f"Transferred {reserve_amount} to mother account: {message}")
                        else:
                            print(f"Failed to transfer to mother account: {message}")
                            
                except Exception as e:
                    print(f"Error in Tree Upline Reserve System: {e}")
                    pass

                # Trigger upgrade commission logic for each activated slot
                # Upgrade commission logic for each activated slot
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

            # Joining commission once on total of slot-1 and slot-2 (expected 0.0066 BNB)
            if total_join_amount and total_join_amount > 0:
                try:
                    commission_service.calculate_joining_commission(
                        from_user_id=str(user.id),
                        program='binary',
                        amount=total_join_amount,
                        currency=currency
                    )
                except Exception:
                    pass
                
                # Spark Bonus: contribute 8% from Binary program to Spark Bonus fund
                try:
                    spark_contribution = total_join_amount * Decimal('0.08')
                    spark_service = SparkService()
                    spark_service.contribute_to_fund(
                        amount=float(spark_contribution),
                        program='binary',
                        source_user_id=str(user.id),
                        source_type='binary_join',
                        currency=currency
                    )
                except Exception:
                    pass
                # Earning history for joining commission seed (from user perspective)
                try:
                    EarningHistory(
                        user_id=ObjectId(user.id),
                        earning_type='commission',
                        program='binary',
                        amount=float(total_join_amount),
                        currency=currency,
                        description="Joining commission base amount recorded (upline paid via service)"
                    ).save()
                except Exception:
                    pass
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

        return {
            "_id": str(user.id),
            "token": token.access_token,
            "token_type": token.token_type,
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
                    position='root',
                    level=1,
                    slot_no=1,
                    is_active=True
                ).save()
        except Exception:
            pass

        # Seed BinaryAutoUpgrade tracking for root
        try:
            if not BinaryAutoUpgrade.objects(user_id=ObjectId(user.id)).first():
                BinaryAutoUpgrade(
                    user_id=ObjectId(user.id),
                    current_slot_no=1,
                    current_level=1,
                    partners_required=2,
                    partners_available=0,
                    is_eligible=False,
                    can_upgrade=False
                ).save()
        except Exception:
            pass

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
        }, None

    except Exception as e:
        return None, str(e)


