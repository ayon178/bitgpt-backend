from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta
from ..user.model import User
from ..slot.model import SlotActivation
from ..tree.model import TreePlacement
from .model import (
    Mentorship, MentorshipEligibility, MentorshipCommission,
    MentorshipFund, MentorshipSettings, MentorshipLog, 
    MentorshipStatistics, MentorshipReferral, MentorshipLevel
)
from ..wallet.service import WalletService

class MentorshipService:
    """Mentorship Bonus Business Logic Service"""
    
    def __init__(self):
        pass
    
    def join_mentorship_program(self, user_id: str) -> Dict[str, Any]:
        """Join Mentorship Bonus program"""
        try:
            # Validate user exists
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check if already joined
            existing = Mentorship.objects(user_id=ObjectId(user_id)).first()
            if existing:
                return {
                    "success": True,
                    "status": "already_joined",
                    "mentorship_id": str(existing.id),
                    "total_commissions_earned": existing.total_commissions_earned,
                    "direct_referrals_count": existing.direct_referrals_count,
                    "direct_of_direct_referrals_count": existing.direct_of_direct_referrals_count,
                    "message": "User already joined Mentorship program"
                }
            
            # Create Mentorship record
            mentorship = Mentorship(
                user_id=ObjectId(user_id),
                joined_at=datetime.utcnow(),
                is_active=True
            )
            
            # Initialize levels
            mentorship.levels = self._initialize_mentorship_levels()
            
            mentorship.save()
            
            # Create eligibility record
            eligibility = MentorshipEligibility(user_id=ObjectId(user_id))
            eligibility.save()
            
            # Log the action
            self._log_action(user_id, "joined_program", "User joined Mentorship program")
            
            return {
                "success": True,
                "mentorship_id": str(mentorship.id),
                "user_id": user_id,
                "is_eligible": False,
                "is_active": True,
                "joined_at": mentorship.joined_at,
                "message": "Successfully joined Mentorship program"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_matrix_mentorship(self, user_id: str, referrer_id: str, amount: Decimal, currency: str) -> Dict[str, Any]:
        """Process Matrix Mentorship Bonus (10%) to super upline, referral-based and independent of tree.

        - user_id: the user who joined/upgraded (source of amount)
        - referrer_id: the direct sponsor of user_id
        - super upline: sponsor of referrer_id (referrer.refered_by)
        """
        try:
            # Validate users
            user = User.objects(id=ObjectId(user_id)).first()
            referrer = User.objects(id=ObjectId(referrer_id)).first()
            if not user or not referrer:
                return {"success": False, "error": "User or referrer not found"}

            super_upline_id = getattr(referrer, 'refered_by', None)
            if not super_upline_id:
                # No super upline → nothing to distribute (as per rules)
                return {"success": True, "status": "no_super_upline"}

            # Calculate 10% mentorship bonus on the Matrix amount
            source_amount = float(amount)
            commission_result = self.process_commission(
                mentor_id=str(super_upline_id),
                source_user_id=str(user.id),
                commission_type="matrix",
                source_amount=source_amount
            )

            return {"success": True, "result": commission_result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_eligibility(self, user_id: str, force_check: bool = False) -> Dict[str, Any]:
        """Check Mentorship eligibility for user"""
        try:
            # Get Mentorship record
            mentorship = Mentorship.objects(user_id=ObjectId(user_id)).first()
            if not mentorship:
                return {"success": False, "error": "User not in Mentorship program"}
            
            # Get eligibility record
            eligibility = MentorshipEligibility.objects(user_id=ObjectId(user_id)).first()
            if not eligibility:
                eligibility = MentorshipEligibility(user_id=ObjectId(user_id))
            
            # Check Matrix program status
            matrix_status = self._check_matrix_program_status(user_id)
            eligibility.has_matrix_program = matrix_status["has_matrix"]
            eligibility.matrix_slots_activated = matrix_status["slots_activated"]
            
            # Check direct referrals
            referrals_status = self._check_direct_referrals(user_id)
            eligibility.direct_referrals_count = referrals_status["direct_count"]
            
            # Update Mentorship record
            mentorship.matrix_program_active = matrix_status["has_matrix"]
            mentorship.matrix_slots_activated = matrix_status["slots_activated"]
            mentorship.direct_referrals = referrals_status["direct_list"]
            mentorship.direct_referrals_count = referrals_status["direct_count"]
            
            # Determine eligibility
            eligibility.is_eligible_for_mentorship = (
                eligibility.has_matrix_program and
                eligibility.direct_referrals_count >= 1
            )
            
            # Update eligibility reasons
            eligibility_reasons = self._get_eligibility_reasons(eligibility)
            eligibility.eligibility_reasons = eligibility_reasons
            
            if eligibility.is_eligible_for_mentorship and not mentorship.is_eligible:
                eligibility.qualified_at = datetime.utcnow()
                mentorship.is_eligible = True
                mentorship.qualified_at = datetime.utcnow()
                
                # Activate levels
                for level in mentorship.levels:
                    level.is_active = True
                    level.activated_at = datetime.utcnow()
                
                self._log_action(user_id, "became_eligible", "User became eligible for Mentorship bonuses")
            
            eligibility.last_checked = datetime.utcnow()
            eligibility.save()
            
            mentorship.last_updated = datetime.utcnow()
            mentorship.save()
            
            return {
                "success": True,
                "user_id": user_id,
                "is_eligible": eligibility.is_eligible_for_mentorship,
                "matrix_program": {
                    "has_matrix_program": eligibility.has_matrix_program,
                    "matrix_slots_activated": eligibility.matrix_slots_activated,
                    "min_matrix_slots_required": eligibility.min_matrix_slots_required
                },
                "direct_referrals": {
                    "direct_referrals_count": eligibility.direct_referrals_count,
                    "min_direct_referrals_required": eligibility.min_direct_referrals_required
                },
                "eligibility_reasons": eligibility.eligibility_reasons,
                "qualified_at": eligibility.qualified_at,
                "last_checked": eligibility.last_checked
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_commission(self, mentor_id: str, source_user_id: str, commission_type: str, source_amount: float) -> Dict[str, Any]:
        """Process Mentorship commission"""
        try:
            # Get Mentorship record
            mentorship = Mentorship.objects(user_id=ObjectId(mentor_id)).first()
            if not mentorship:
                return {"success": False, "error": "Mentor not in Mentorship program"}
            
            if not mentorship.is_eligible:
                return {"success": False, "error": "Mentor not eligible for Mentorship bonuses"}
            
            # Determine commission level
            commission_level = self._determine_commission_level(mentor_id, source_user_id)
            if not commission_level:
                return {"success": False, "error": "Unable to determine commission level"}
            
            # Calculate commission amount
            commission_percentage = 10.0  # 10% commission
            commission_amount = source_amount * (commission_percentage / 100)
            
            # Create commission record
            commission = MentorshipCommission(
                user_id=ObjectId(mentor_id),
                mentorship_id=mentorship.id,
                commission_type=commission_type,
                commission_level=commission_level,
                commission_percentage=commission_percentage,
                source_user_id=ObjectId(source_user_id),
                source_user_level=1 if commission_level == 'direct' else 2,
                source_amount=source_amount,
                commission_amount=commission_amount,
                payment_status="pending"
            )
            commission.save()
            
            # Update Mentorship record
            mentorship.total_commissions_earned += commission_amount
            mentorship.pending_commissions += commission_amount
            
            if commission_level == 'direct':
                mentorship.direct_commissions += commission_amount
            else:
                mentorship.direct_of_direct_commissions += commission_amount
            
            mentorship.last_updated = datetime.utcnow()
            mentorship.save()
            
            # Log the action
            self._log_action(mentor_id, "commission_earned", 
                           f"Earned {commission_level} commission: ${commission_amount} from {commission_type}")
            
            return {
                "success": True,
                "commission_id": str(commission.id),
                "mentor_id": mentor_id,
                "source_user_id": source_user_id,
                "commission_type": commission_type,
                "commission_level": commission_level,
                "commission_percentage": commission_percentage,
                "source_amount": source_amount,
                "commission_amount": commission_amount,
                "payment_status": "pending",
                "message": f"Mentorship commission processed: ${commission_amount}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def distribute_commission_payment(self, commission_id: str) -> Dict[str, Any]:
        """Distribute Mentorship commission payment"""
        try:
            commission = MentorshipCommission.objects(id=ObjectId(commission_id)).first()
            if not commission:
                return {"success": False, "error": "Commission not found"}
            
            if commission.payment_status != "pending":
                return {"success": False, "error": "Commission already processed"}
            
            # Check fund availability
            fund = MentorshipFund.objects(is_active=True).first()
            if not fund:
                return {"success": False, "error": "Mentorship fund not found"}
            
            if fund.available_amount < commission.commission_amount:
                return {"success": False, "error": "Insufficient fund balance"}
            
            # Process payment
            commission.payment_status = "processing"
            commission.processed_at = datetime.utcnow()
            commission.save()
            
            # Update fund
            fund.available_amount -= commission.commission_amount
            fund.distributed_amount += commission.commission_amount
            fund.total_commissions_paid += 1
            fund.total_amount_distributed += commission.commission_amount
            fund.last_updated = datetime.utcnow()
            fund.save()
            
            # Update Mentorship record
            mentorship = Mentorship.objects(id=commission.mentorship_id).first()
            if mentorship:
                mentorship.total_commissions_paid += commission.commission_amount
                mentorship.pending_commissions -= commission.commission_amount
                mentorship.last_updated = datetime.utcnow()
                mentorship.save()
            
            # Credit mentor's main wallet
            try:
                WalletService().credit_main_wallet(
                    user_id=str(commission.user_id),
                    amount=Decimal(str(commission.commission_amount)),
                    currency='USDT',
                    reason=f"mentorship_{commission.commission_level}",
                    tx_hash=f"MNT-PAY-{commission.id}-{datetime.utcnow().timestamp()}"
                )
            except Exception:
                pass
            
            # Complete payment
            commission.payment_status = "paid"
            commission.paid_at = datetime.utcnow()
            commission.payment_reference = f"MNT-{commission.id}"
            commission.save()
            
            # Log the action
            self._log_action(str(commission.user_id), "commission_paid", 
                           f"Paid {commission.commission_level} commission: ${commission.commission_amount}")
            
            return {
                "success": True,
                "commission_id": commission_id,
                "commission_amount": commission.commission_amount,
                "currency": 'USDT',
                "payment_status": "paid",
                "payment_reference": commission.payment_reference,
                "paid_at": commission.paid_at,
                "message": "Commission payment distributed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_mentorship_statistics(self, period: str = "all_time") -> Dict[str, Any]:
        """Get Mentorship program statistics"""
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
            total_eligible = Mentorship.objects(is_eligible=True).count()
            total_active = Mentorship.objects(is_active=True).count()
            
            # Get commissions for period
            commissions = MentorshipCommission.objects(
                created_at__gte=start_date,
                created_at__lt=end_date,
                payment_status="paid"
            )
            
            total_commissions_paid = commissions.count()
            total_amount_distributed = sum(commission.commission_amount for commission in commissions)
            
            # Commission breakdown
            direct_commissions = commissions.filter(commission_level="direct")
            direct_of_direct_commissions = commissions.filter(commission_level="direct_of_direct")
            
            commission_breakdown = {
                "direct_commissions_paid": direct_commissions.count(),
                "direct_commissions_amount": sum(c.commission_amount for c in direct_commissions),
                "direct_of_direct_commissions_paid": direct_of_direct_commissions.count(),
                "direct_of_direct_commissions_amount": sum(c.commission_amount for c in direct_of_direct_commissions)
            }
            
            # Create or update statistics record
            statistics = MentorshipStatistics.objects(period=period).first()
            if not statistics:
                statistics = MentorshipStatistics(period=period)
            
            statistics.period_start = start_date
            statistics.period_end = end_date
            statistics.total_eligible_users = total_eligible
            statistics.total_active_users = total_active
            statistics.total_commissions_paid = total_commissions_paid
            statistics.total_amount_distributed = total_amount_distributed
            statistics.direct_commissions_paid = commission_breakdown["direct_commissions_paid"]
            statistics.direct_commissions_amount = commission_breakdown["direct_commissions_amount"]
            statistics.direct_of_direct_commissions_paid = commission_breakdown["direct_of_direct_commissions_paid"]
            statistics.direct_of_direct_commissions_amount = commission_breakdown["direct_of_direct_commissions_amount"]
            statistics.last_updated = datetime.utcnow()
            statistics.save()
            
            return {
                "success": True,
                "period": period,
                "period_start": start_date,
                "period_end": end_date,
                "statistics": {
                    "total_eligible_users": total_eligible,
                    "total_active_users": total_active,
                    "total_commissions_paid": total_commissions_paid,
                    "total_amount_distributed": total_amount_distributed,
                    "commission_breakdown": commission_breakdown,
                    "growth_statistics": {
                        "new_eligible_users": 0,  # Would need historical data
                        "new_commission_earners": 0,   # Would need historical data
                        "total_direct_referrals": 0,  # Would need to calculate
                        "total_direct_of_direct_referrals": 0  # Would need to calculate
                    }
                },
                "last_updated": statistics.last_updated
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _initialize_mentorship_levels(self) -> List[MentorshipLevel]:
        """Initialize Mentorship levels"""
        return [
            MentorshipLevel(
                level_number=1,
                level_name="Direct",
                commission_percentage=10.0
            ),
            MentorshipLevel(
                level_number=2,
                level_name="Direct-of-Direct",
                commission_percentage=10.0
            )
        ]
    
    def _check_matrix_program_status(self, user_id: str) -> Dict[str, Any]:
        """Check Matrix program status for user"""
        try:
            # Check Matrix slot activations
            matrix_activations = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program="matrix",
                status="completed"
            ).count()
            
            has_matrix = matrix_activations > 0
            
            return {
                "has_matrix": has_matrix,
                "slots_activated": matrix_activations
            }
            
        except Exception:
            return {
                "has_matrix": False,
                "slots_activated": 0
            }
    
    def _check_direct_referrals(self, user_id: str) -> Dict[str, Any]:
        """Check direct referrals for user"""
        try:
            # Get direct referrals from tree
            direct_referrals = TreePlacement.objects(
                parent_id=ObjectId(user_id),
                is_active=True
            ).all()
            
            direct_list = [ref.user_id for ref in direct_referrals]
            
            return {
                "direct_count": len(direct_referrals),
                "direct_list": direct_list
            }
            
        except Exception:
            return {
                "direct_count": 0,
                "direct_list": []
            }
    
    def _determine_commission_level(self, mentor_id: str, source_user_id: str) -> Optional[str]:
        """Determine commission level (direct or direct_of_direct)"""
        try:
            # Check if source_user is a direct referral of mentor
            direct_referral = TreePlacement.objects(
                parent_id=ObjectId(mentor_id),
                user_id=ObjectId(source_user_id),
                is_active=True
            ).first()
            
            if direct_referral:
                return "direct"
            
            # Check if source_user is a direct-of-direct referral
            # Get all direct referrals of mentor
            mentor_directs = TreePlacement.objects(
                parent_id=ObjectId(mentor_id),
                is_active=True
            ).all()
            
            for direct_ref in mentor_directs:
                # Check if source_user is under this direct referral
                direct_of_direct = TreePlacement.objects(
                    parent_id=direct_ref.user_id,
                    user_id=ObjectId(source_user_id),
                    is_active=True
                ).first()
                
                if direct_of_direct:
                    return "direct_of_direct"
            
            return None
            
        except Exception:
            return None
    
    def _get_eligibility_reasons(self, eligibility: MentorshipEligibility) -> List[str]:
        """Get eligibility reasons"""
        reasons = []
        
        if not eligibility.has_matrix_program:
            reasons.append("Matrix program not active")
        
        if eligibility.direct_referrals_count < 1:
            reasons.append("Need at least 1 direct referral")
        
        return reasons
    
    def _log_action(self, user_id: str, action_type: str, description: str):
        """Log Mentorship action"""
        try:
            log = MentorshipLog(
                user_id=ObjectId(user_id),
                action_type=action_type,
                action_description=description,
                is_processed=True,
                processed_at=datetime.utcnow()
            )
            log.save()
        except Exception:
            pass  # Logging failure shouldn't break the main process
