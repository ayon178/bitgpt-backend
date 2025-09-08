from typing import Tuple, Optional, Dict, Any
from mongoengine.errors import NotUniqueError, ValidationError
from modules.user.model import User
from auth.service import authentication_service
from modules.tree.service import TreeService
from modules.slot.model import SlotActivation, SlotCatalog
from decimal import Decimal
from bson import ObjectId
from utils import ensure_currency_for_program
from modules.auto_upgrade.model import BinaryAutoUpgrade
from modules.commission.service import CommissionService
from modules.jackpot.service import JackpotService
from modules.newcomer_support.model import NewcomerSupport


def create_user_service(payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Create a new user if wallet_address is unique.

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

    try:
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

        # Auto tree placement (binary, slot 1)
        try:
            # Place user under their referrer in binary slot 1
            placement_resp = authentication_service.run_async(TreeService.create_tree_placement(
                user_id=str(user.id),
                referrer_id=str(user.refered_by),
                program='binary',
                slot_no=1
            ))
        except Exception:
            placement_resp = None

        # Auto-activate first two binary slots (Explorer=1, Contributor=2)
        try:
            commission_service = CommissionService()
            for slot_no in [1, 2]:
                catalog = SlotCatalog.objects(program='binary', slot_no=slot_no, is_active=True).first()
                if not catalog:
                    continue
                amount = catalog.price or Decimal('0')
                currency = ensure_currency_for_program('binary', 'BNB')
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

                # Trigger commissions
                # Joining commission only once on first slot
                if slot_no == 1 and amount > 0:
                    try:
                        commission_service.calculate_joining_commission(
                            from_user_id=str(user.id),
                            program='binary',
                            amount=amount,
                            currency=currency
                        )
                    except Exception:
                        pass
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
                    except Exception:
                        pass
                # Jackpot free coupon awards for relevant slots
                try:
                    JackpotService.award_free_coupon_for_binary_slot(user_id=str(user.id), slot_no=slot_no)
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

        return {
            "_id": str(user.id),
            "token": token.access_token,
            "token_type": token.token_type,
        }, None

    except (ValidationError, NotUniqueError) as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)


