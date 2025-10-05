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


def create_user_service(payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Create a new user if wallet_address is unique.
    Enforces mandatory Binary program join requirement.

    Returns (result, error):
      - result: {"_id": str, "token": str, "token_type": "bearer"}
      - error: error message string if any
    """
    required_fields = ["uid", "refer_code", "refered_by", "wallet_address", "name"]

    missing = [f for f in required_fields if not payload.get(f)]
    if missing:
        return None, f"Missing required fields: {', '.join(missing)}"

    wallet_address = payload.get("wallet_address")

    # Uniqueness check by wallet_address
    existing = User.objects(wallet_address=wallet_address).first()
    if existing:
        return None, "User with this wallet_address already exists"
    
    # MANDATORY BINARY JOIN ENFORCEMENT
    # According to PROJECT_DOCUMENTATION.md Section 5: "Users MUST follow this exact sequence: Binary → Matrix → Global"
    binary_payment_tx = payload.get("binary_payment_tx")
    if not binary_payment_tx:
        return None, "Binary program join is mandatory. Must provide binary_payment_tx (0.0066 BNB payment proof)"

    try:
        # Step 0: Preconditions - Validate referrer exists
        referrer_id = payload.get("refered_by")
        try:
            referrer = User.objects(id=ObjectId(referrer_id)).first()
        except Exception:
            referrer = None
        if not referrer:
            return None, "Invalid referrer/upline provided"

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
            uid=payload.get("uid"),
            refer_code=payload.get("refer_code"),
            refered_by=payload.get("refered_by"),
            wallet_address=wallet_address,
            name=payload.get("name"),
            role=payload.get("role") or "user",
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
            ref_pg = PartnerGraph.objects(user_id=ObjectId(referrer.id)).first()
            if not ref_pg:
                ref_pg = PartnerGraph(user_id=ObjectId(referrer.id))
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
                    if hasattr(referrer, 'royal_captain_qualifications'):
                        referrer.royal_captain_qualifications = int(getattr(referrer, 'royal_captain_qualifications', 0) or 0) + 1
                    
                    # Check if referrer maintains 5 direct Matrix+Global referrals
                    if referrer.royal_captain_qualifications >= 5:
                        # Get referrer's global team size
                        ref_pg = PartnerGraph.objects(user_id=ObjectId(referrer.id)).first()
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
                                    user_id=ObjectId(referrer.id),
                                    award_amount=award_amount,
                                    global_team_size=global_team_size,
                                    matrix_global_referrals=referrer.royal_captain_qualifications,
                                    status='pending',
                                    created_at=datetime.utcnow()
                                ).save()
                            except Exception:
                                pass
                
                # President Reward Tracking
                if hasattr(referrer, 'president_reward_qualifications'):
                    referrer.president_reward_qualifications = int(getattr(referrer, 'president_reward_qualifications', 0) or 0) + 1
                
                # Get referrer's global team size for President Reward
                ref_pg = PartnerGraph.objects(user_id=ObjectId(referrer.id)).first()
                global_team_size = len(ref_pg.global_team_members) if ref_pg and ref_pg.global_team_members else 0
                direct_invites = referrer.president_reward_qualifications
                
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
                            user_id=ObjectId(referrer.id),
                            award_amount=award_amount,
                            global_team_size=global_team_size,
                            direct_invites=direct_invites,
                            status='pending',
                            created_at=datetime.utcnow()
                        ).save()
                    except Exception:
                        pass
                
                referrer.updated_at = datetime.utcnow()
                referrer.save()
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
                        'referrer_id': str(referrer.id)
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
                        'referrer_id': str(referrer.id)
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
                        'referrer_id': str(referrer.id)
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


class UserService:
    """Service class for user-related operations"""
    
    def get_my_community(self, user_id: str, program_type: str = "binary", slot_number: Optional[int] = None, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get community members (referred users) for a user - SINGLE QUERY VERSION"""
        try:
            # Validate program type
            if program_type not in ["binary", "matrix"]:
                return {"success": False, "error": "Invalid program type. Must be 'binary' or 'matrix'"}
            
            # Get the user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # SINGLE QUERY: Use aggregation pipeline for everything
            pipeline = []
            
            # Match referred users
            pipeline.append({
                "$match": {
                    "refered_by": ObjectId(user_id)
                }
            })
            
            # If slot filtering is needed
            if slot_number is not None:
                # Lookup slot activations
                pipeline.append({
                    "$lookup": {
                        "from": "slot_activation",
                        "let": {"userId": "$_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$eq": ["$user_id", "$$userId"]},
                                            {"$eq": ["$program", program_type]},
                                            {"$eq": ["$slot_no", slot_number]}
                                        ]
                                    }
                                }
                            }
                        ],
                        "as": "slot_activations"
                    }
                })
                
                # Filter only users with matching slot activations
                pipeline.append({
                    "$match": {
                        "slot_activations": {"$ne": []}
                    }
                })
            
            # Add direct partner count
            pipeline.append({
                "$lookup": {
                    "from": "user",
                    "let": {"userId": "$_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {"$eq": ["$refered_by", "$$userId"]}
                            }
                        },
                        {"$count": "count"}
                    ],
                    "as": "direct_partners"
                }
            })
            
            # Add computed fields
            pipeline.append({
                "$addFields": {
                    "direct_partner_count": {
                        "$ifNull": [{"$arrayElemAt": ["$direct_partners.count", 0]}, 0]
                    },
                    "rank": {
                        "$add": [
                            {"$ifNull": [{"$arrayElemAt": ["$direct_partners.count", 0]}, 0]},
                            1
                        ]
                    }
                }
            })
            
            # Sort by creation date
            pipeline.append({
                "$sort": {"created_at": -1}
            })
            
            # Count total
            count_pipeline = pipeline + [{"$count": "total"}]
            total_result = list(User.objects.aggregate(count_pipeline))
            total_users = total_result[0]["total"] if total_result else 0
            
            # Add pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 10)))
            skip = (page - 1) * limit
            
            pipeline.extend([
                {"$skip": skip},
                {"$limit": limit}
            ])
            
            # Execute aggregation
            results = list(User.objects.aggregate(pipeline))
            
            # Format data
            items = []
            for i, result in enumerate(results):
                # Format wallet address
                wallet_address = result.get("wallet_address", "")
                if len(wallet_address) > 8:
                    masked_address = f"{wallet_address[:4]}...{wallet_address[-4:]}"
                else:
                    masked_address = wallet_address
                
                # Format date
                created_at = result.get("created_at")
                if created_at:
                    activation_date = created_at.strftime("%d %b,%Y")
                    activation_time = created_at.strftime("(%H:%M)")
                    formatted_date = f"{activation_date} {activation_time}"
                else:
                    formatted_date = "Unknown"
                
                # Slot info
                slot_info = str(slot_number) if slot_number is not None else "--"
                
                items.append({
                    "sl_no": skip + i + 1,
                    "id": result.get("uid", "Unknown"),
                    "_id": str(result["_id"]),
                    "address": masked_address,
                    "inviter_id": user.uid,
                    "activation_date": formatted_date,
                    "slot": slot_info,
                    "rank": result.get("rank", 1),
                    "direct_partner": result.get("direct_partner_count", 0),
                    "created_at": created_at.isoformat() if created_at else None
                })
            
            return {
                "success": True,
                "data": {
                    "program_type": program_type,
                    "slot_number": slot_number,
                    "page": page,
                    "limit": limit,
                    "total": total_users,
                    "items": items
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

