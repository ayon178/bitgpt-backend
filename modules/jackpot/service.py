from typing import Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
from .model import JackpotTicket
from modules.user.model import User


def current_week_id() -> str:
    now = datetime.utcnow()
    return f"{now.isocalendar().year}-{now.isocalendar().week:02d}"


class JackpotService:
    """Handles jackpot entries and free coupon awards."""

    @staticmethod
    def create_entry(user_id: str, source: str, referrer_user_id: Optional[str] = None, free_source_slot: Optional[int] = None) -> Dict[str, Any]:
        try:
            # Resolve referrer if not provided
            if not referrer_user_id:
                user = User.objects(id=ObjectId(user_id)).first()
                if user and user.refered_by:
                    referrer_user_id = str(user.refered_by)
                else:
                    return {"success": False, "error": "Referrer not found for jackpot entry"}

            ticket = JackpotTicket(
                user_id=ObjectId(user_id),
                referrer_user_id=ObjectId(referrer_user_id),
                week_id=current_week_id(),
                source=source,
                free_source_slot=free_source_slot,
                status='active'
            )
            ticket.save()
            return {"success": True, "ticket_id": str(ticket.id)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def award_free_coupon_for_binary_slot(user_id: str, slot_no: int) -> None:
        """Award free jackpot coupons based on binary slot upgrades.
        Per docs: Slot 5 => 1, Slot 6 => 2, ... up to Slot 16 (progressive). Here we implement:
        - Slot 5: 1 entry, Slot 6: 2 entries, and from 7..16: (slot_no - 4) entries.
        """
        if slot_no < 5:
            return
        entries = max(1, slot_no - 4)
        user = User.objects(id=ObjectId(user_id)).first()
        referrer = str(user.refered_by) if user and user.refered_by else None
        for _ in range(entries):
            JackpotService.create_entry(user_id=user_id, source='free', referrer_user_id=referrer, free_source_slot=slot_no)


