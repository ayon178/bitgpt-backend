from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta
from ..user.model import User
from ..slot.model import SlotActivation
from ..tree.model import TreePlacement
from .model import (
    LeadershipStipend, LeadershipStipendEligibility, LeadershipStipendPayment,
    LeadershipStipendFund, LeadershipStipendSettings, LeadershipStipendLog, 
    LeadershipStipendStatistics, LeadershipStipendCalculation, LeadershipStipendTier
)

class LeadershipStipendService:
    """Leadership Stipend Business Logic Service"""
    
    def __init__(self):
        pass
    
    def join_leadership_stipend_program(self, user_id: str) -> Dict[str, Any]:
        """Join Leadership Stipend program"""
        try:
            # Validate user exists
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check if already joined
            existing = LeadershipStipend.objects(user_id=ObjectId(user_id)).first()
            if existing:
                return {
                    "success": True,
                    "status": "already_joined",
                    "leadership_stipend_id": str(existing.id),
                    "current_tier": existing.current_tier,
                    "current_daily_return": existing.current_daily_return,
                    "total_earned": existing.total_earned,
                    "message": "User already joined Leadership Stipend program"
                }
            
            # Create Leadership Stipend record
            leadership_stipend = LeadershipStipend(
                user_id=ObjectId(user_id),
                joined_at=datetime.utcnow(),
                is_active=True
            )
            
            # Initialize tiers
            leadership_stipend.tiers = self._initialize_leadership_stipend_tiers()
            
            leadership_stipend.save()
            
            # Create eligibility record
            eligibility = LeadershipStipendEligibility(user_id=ObjectId(user_id))
            eligibility.save()
            
            # Log the action
            self._log_action(user_id, "joined_program", "User joined Leadership Stipend program")
            
            return {
                "success": True,
                "leadership_stipend_id": str(leadership_stipend.id),
                "user_id": user_id,
                "current_tier": 0,
                "is_eligible": False,
                "is_active": True,
                "joined_at": leadership_stipend.joined_at,
                "message": "Successfully joined Leadership Stipend program"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_eligibility(self, user_id: str, force_check: bool = False) -> Dict[str, Any]:
        """Check Leadership Stipend eligibility for user"""
        try:
            # Get Leadership Stipend record
            leadership_stipend = LeadershipStipend.objects(user_id=ObjectId(user_id)).first()
            if not leadership_stipend:
                return {"success": False, "error": "User not in Leadership Stipend program"}
            
            # Get eligibility record
            eligibility = LeadershipStipendEligibility.objects(user_id=ObjectId(user_id)).first()
            if not eligibility:
                eligibility = LeadershipStipendEligibility(user_id=ObjectId(user_id))
            
            # Check slot requirements
            slot_status = self._check_slot_requirements(user_id)
            eligibility.highest_slot_activated = slot_status["highest_slot"]
            eligibility.slots_10_16_activated = slot_status["slots_10_16"]
            
            # Update Leadership Stipend record
            leadership_stipend.highest_slot_achieved = slot_status["highest_slot"]
            leadership_stipend.slots_activated = slot_status["all_slots"]
            
            # Determine eligibility
            eligibility.is_eligible_for_stipend = (
                eligibility.highest_slot_activated >= 10
            )
            
            # Update eligibility reasons
            eligibility_reasons = self._get_eligibility_reasons(eligibility)
            eligibility.eligibility_reasons = eligibility_reasons
            
            if eligibility.is_eligible_for_stipend and not leadership_stipend.is_eligible:
                eligibility.qualified_at = datetime.utcnow()
                leadership_stipend.is_eligible = True
                leadership_stipend.qualified_at = datetime.utcnow()
                leadership_stipend.current_tier = eligibility.highest_slot_activated
                
                # Set current tier details
                current_tier_info = self._get_tier_info(eligibility.highest_slot_activated)
                leadership_stipend.current_tier_name = current_tier_info["tier_name"]
                leadership_stipend.current_daily_return = current_tier_info["daily_return"]
                
                # Activate tier
                self._activate_tier(leadership_stipend, eligibility.highest_slot_activated)
                
                self._log_action(user_id, "became_eligible", f"User became eligible for Leadership Stipend - Slot {eligibility.highest_slot_activated}")
            
            eligibility.last_checked = datetime.utcnow()
            eligibility.save()
            
            leadership_stipend.last_updated = datetime.utcnow()
            leadership_stipend.save()
            
            return {
                "success": True,
                "user_id": user_id,
                "is_eligible": eligibility.is_eligible_for_stipend,
                "slot_status": {
                    "highest_slot_activated": eligibility.highest_slot_activated,
                    "slots_10_16_activated": eligibility.slots_10_16_activated,
                    "min_slot_required": eligibility.min_slot_required
                },
                "current_tier": {
                    "slot_number": leadership_stipend.current_tier,
                    "tier_name": leadership_stipend.current_tier_name,
                    "daily_return": leadership_stipend.current_daily_return
                },
                "eligibility_reasons": eligibility.eligibility_reasons,
                "qualified_at": eligibility.qualified_at,
                "last_checked": eligibility.last_checked
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_daily_calculation(self, calculation_date: str = None) -> Dict[str, Any]:
        """Process daily stipend calculation for all eligible users"""
        try:
            if not calculation_date:
                calculation_date = datetime.utcnow().strftime("%Y-%m-%d")
            
            # Parse calculation date
            calc_date = datetime.strptime(calculation_date, "%Y-%m-%d")
            
            # Create calculation record
            calculation = LeadershipStipendCalculation(
                calculation_date=calc_date,
                calculation_type="daily",
                processing_status="processing",
                started_at=datetime.utcnow()
            )
            calculation.save()
            
            # Get all eligible users
            eligible_users = LeadershipStipend.objects(is_eligible=True, is_active=True).all()
            
            total_users_processed = 0
            total_amount_calculated = 0.0
            total_payments_created = 0
            
            for user_stipend in eligible_users:
                try:
                    # Calculate daily stipend for user
                    result = self._calculate_user_daily_stipend(user_stipend, calc_date)
                    
                    if result["success"]:
                        total_users_processed += 1
                        total_amount_calculated += result["amount"]
                        total_payments_created += result["payments_created"]
                        
                        # Update user stipend
                        user_stipend.total_earned += result["amount"]
                        user_stipend.pending_amount += result["amount"]
                        user_stipend.last_calculation_date = calc_date
                        user_stipend.save()
                        
                        # Log the action
                        self._log_action(str(user_stipend.user_id), "daily_calculation", 
                                       f"Daily stipend calculated: {result['amount']} BNB")
                
                except Exception as e:
                    # Log error but continue with other users
                    self._log_action(str(user_stipend.user_id), "calculation_error", f"Error: {str(e)}")
            
            # Update calculation record
            calculation.total_users_processed = total_users_processed
            calculation.total_amount_calculated = total_amount_calculated
            calculation.total_payments_created = total_payments_created
            calculation.processing_status = "completed"
            calculation.completed_at = datetime.utcnow()
            calculation.save()
            
            return {
                "success": True,
                "calculation_date": calculation_date,
                "total_users_processed": total_users_processed,
                "total_amount_calculated": total_amount_calculated,
                "total_payments_created": total_payments_created,
                "calculation_id": str(calculation.id),
                "message": f"Daily calculation completed for {total_users_processed} users"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def distribute_stipend_payment(self, payment_id: str) -> Dict[str, Any]:
        """Distribute Leadership Stipend payment"""
        try:
            payment = LeadershipStipendPayment.objects(id=ObjectId(payment_id)).first()
            if not payment:
                return {"success": False, "error": "Stipend payment not found"}
            
            if payment.payment_status != "pending":
                return {"success": False, "error": "Stipend payment already processed"}
            
            # Check fund availability
            fund = LeadershipStipendFund.objects(is_active=True).first()
            if not fund:
                return {"success": False, "error": "Leadership Stipend fund not found"}
            
            if fund.available_amount < payment.daily_return_amount:
                return {"success": False, "error": "Insufficient fund balance"}
            
            # Process payment
            payment.payment_status = "processing"
            payment.processed_at = datetime.utcnow()
            payment.save()
            
            # Update fund
            fund.available_amount -= payment.daily_return_amount
            fund.distributed_amount += payment.daily_return_amount
            fund.total_payments_made += 1
            fund.total_amount_distributed += payment.daily_return_amount
            fund.last_updated = datetime.utcnow()
            fund.save()
            
            # Update Leadership Stipend record
            leadership_stipend = LeadershipStipend.objects(id=payment.leadership_stipend_id).first()
            if leadership_stipend:
                leadership_stipend.total_paid += payment.daily_return_amount
                leadership_stipend.pending_amount -= payment.daily_return_amount
                leadership_stipend.last_payment_date = payment.payment_date
                leadership_stipend.last_updated = datetime.utcnow()
                leadership_stipend.save()
            
            # Complete payment
            payment.payment_status = "paid"
            payment.paid_at = datetime.utcnow()
            payment.payment_reference = f"LS-{payment.id}"
            payment.save()
            
            # Log the action
            self._log_action(str(payment.user_id), "payment_paid", 
                           f"Paid stipend: {payment.daily_return_amount} BNB for slot {payment.slot_number}")
            
            return {
                "success": True,
                "payment_id": payment_id,
                "daily_return_amount": payment.daily_return_amount,
                "currency": payment.currency,
                "payment_status": "paid",
                "payment_reference": payment.payment_reference,
                "paid_at": payment.paid_at,
                "message": "Stipend payment distributed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_leadership_stipend_statistics(self, period: str = "all_time") -> Dict[str, Any]:
        """Get Leadership Stipend program statistics"""
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
            total_eligible = LeadershipStipend.objects(is_eligible=True).count()
            total_active = LeadershipStipend.objects(is_active=True).count()
            
            # Get stipend payments for period
            stipend_payments = LeadershipStipendPayment.objects(
                created_at__gte=start_date,
                created_at__lt=end_date,
                payment_status="paid"
            )
            
            total_payments_made = stipend_payments.count()
            total_amount_distributed = sum(payment.daily_return_amount for payment in stipend_payments)
            
            # Tier statistics
            tier_stats = {
                "tier_10": stipend_payments.filter(slot_number=10).count(),
                "tier_11": stipend_payments.filter(slot_number=11).count(),
                "tier_12": stipend_payments.filter(slot_number=12).count(),
                "tier_13": stipend_payments.filter(slot_number=13).count(),
                "tier_14": stipend_payments.filter(slot_number=14).count(),
                "tier_15": stipend_payments.filter(slot_number=15).count(),
                "tier_16": stipend_payments.filter(slot_number=16).count()
            }
            
            # Create or update statistics record
            statistics = LeadershipStipendStatistics.objects(period=period).first()
            if not statistics:
                statistics = LeadershipStipendStatistics(period=period)
            
            statistics.period_start = start_date
            statistics.period_end = end_date
            statistics.total_eligible_users = total_eligible
            statistics.total_active_users = total_active
            statistics.total_payments_made = total_payments_made
            statistics.total_amount_distributed = total_amount_distributed
            statistics.tier_10_users = tier_stats["tier_10"]
            statistics.tier_11_users = tier_stats["tier_11"]
            statistics.tier_12_users = tier_stats["tier_12"]
            statistics.tier_13_users = tier_stats["tier_13"]
            statistics.tier_14_users = tier_stats["tier_14"]
            statistics.tier_15_users = tier_stats["tier_15"]
            statistics.tier_16_users = tier_stats["tier_16"]
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
                    "total_payments_made": total_payments_made,
                    "total_amount_distributed": total_amount_distributed,
                    "tier_statistics": tier_stats,
                    "growth_statistics": {
                        "new_eligible_users": 0,  # Would need historical data
                        "new_payment_recipients": 0,   # Would need historical data
                        "total_slots_activated": 0  # Would need to calculate
                    }
                },
                "last_updated": statistics.last_updated
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _initialize_leadership_stipend_tiers(self) -> List[LeadershipStipendTier]:
        """Initialize Leadership Stipend tiers based on PROJECT_DOCUMENTATION.md"""
        return [
            LeadershipStipendTier(slot_number=10, tier_name="LEADER", slot_value=1.1264, daily_return=2.2528),
            LeadershipStipendTier(slot_number=11, tier_name="VANGURD", slot_value=2.2528, daily_return=4.5056),
            LeadershipStipendTier(slot_number=12, tier_name="CENTER", slot_value=4.5056, daily_return=9.0112),
            LeadershipStipendTier(slot_number=13, tier_name="CLIMAX", slot_value=9.0112, daily_return=18.0224),
            LeadershipStipendTier(slot_number=14, tier_name="ENTERNITY", slot_value=18.0224, daily_return=36.0448),
            LeadershipStipendTier(slot_number=15, tier_name="KING", slot_value=36.0448, daily_return=72.0896),
            LeadershipStipendTier(slot_number=16, tier_name="COMMENDER", slot_value=72.0896, daily_return=144.1792)
        ]
    
    def _check_slot_requirements(self, user_id: str) -> Dict[str, Any]:
        """Check slot requirements for user"""
        try:
            # Get slot activations for user
            slot_activations = SlotActivation.objects(
                user_id=ObjectId(user_id),
                status="completed"
            ).all()
            
            highest_slot = 0
            slots_10_16 = []
            all_slots = []
            
            for activation in slot_activations:
                slot_no = activation.slot_no
                all_slots.append(slot_no)
                
                if slot_no > highest_slot:
                    highest_slot = slot_no
                
                if 10 <= slot_no <= 16:
                    slots_10_16.append(slot_no)
            
            return {
                "highest_slot": highest_slot,
                "slots_10_16": slots_10_16,
                "all_slots": all_slots
            }
            
        except Exception:
            return {
                "highest_slot": 0,
                "slots_10_16": [],
                "all_slots": []
            }
    
    def _get_tier_info(self, slot_number: int) -> Dict[str, Any]:
        """Get tier information for slot number"""
        tier_mapping = {
            10: {"tier_name": "LEADER", "daily_return": 2.2528},
            11: {"tier_name": "VANGURD", "daily_return": 4.5056},
            12: {"tier_name": "CENTER", "daily_return": 9.0112},
            13: {"tier_name": "CLIMAX", "daily_return": 18.0224},
            14: {"tier_name": "ENTERNITY", "daily_return": 36.0448},
            15: {"tier_name": "KING", "daily_return": 72.0896},
            16: {"tier_name": "COMMENDER", "daily_return": 144.1792}
        }
        return tier_mapping.get(slot_number, {"tier_name": "UNKNOWN", "daily_return": 0.0})
    
    def _activate_tier(self, leadership_stipend: LeadershipStipend, slot_number: int):
        """Activate tier for user"""
        for tier in leadership_stipend.tiers:
            if tier.slot_number == slot_number:
                tier.is_active = True
                tier.activated_at = datetime.utcnow()
                break
    
    def _calculate_user_daily_stipend(self, user_stipend: LeadershipStipend, calc_date: datetime) -> Dict[str, Any]:
        """Calculate daily stipend for a user"""
        try:
            if not user_stipend.is_eligible or user_stipend.current_tier < 10:
                return {"success": False, "amount": 0.0, "payments_created": 0}
            
            # Get current tier info
            tier_info = self._get_tier_info(user_stipend.current_tier)
            daily_amount = tier_info["daily_return"]
            
            # Create payment record
            payment = LeadershipStipendPayment(
                user_id=user_stipend.user_id,
                leadership_stipend_id=user_stipend.id,
                slot_number=user_stipend.current_tier,
                tier_name=tier_info["tier_name"],
                daily_return_amount=daily_amount,
                currency="BNB",
                payment_date=calc_date,
                payment_period_start=calc_date,
                payment_period_end=calc_date,
                payment_status="pending"
            )
            payment.save()
            
            return {
                "success": True,
                "amount": daily_amount,
                "payments_created": 1
            }
            
        except Exception as e:
            return {"success": False, "amount": 0.0, "payments_created": 0, "error": str(e)}
    
    def _get_eligibility_reasons(self, eligibility: LeadershipStipendEligibility) -> List[str]:
        """Get eligibility reasons"""
        reasons = []
        
        if eligibility.highest_slot_activated < 10:
            needed = 10 - eligibility.highest_slot_activated
            reasons.append(f"Need to activate slot {needed} more to reach slot 10")
        
        return reasons
    
    def _log_action(self, user_id: str, action_type: str, description: str):
        """Log Leadership Stipend action"""
        try:
            log = LeadershipStipendLog(
                user_id=ObjectId(user_id),
                action_type=action_type,
                action_description=description,
                is_processed=True,
                processed_at=datetime.utcnow()
            )
            log.save()
        except Exception:
            pass  # Logging failure shouldn't break the main process
