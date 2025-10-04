from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta
from ..user.model import User
from ..slot.model import SlotActivation
from ..tree.model import TreePlacement
from .model import (
    NewcomerSupport, NewcomerSupportEligibility, NewcomerSupportBonus,
    NewcomerSupportFund, NewcomerSupportSettings, NewcomerSupportLog, 
    NewcomerSupportStatistics, NewcomerSupportMonthlyOpportunity, NewcomerBonus
)

class NewcomerSupportService:
    """Newcomer Growth Support Business Logic Service"""
    
    def __init__(self):
        pass
    
    def join_newcomer_support_program(self, user_id: str) -> Dict[str, Any]:
        """Join Newcomer Growth Support program"""
        try:
            # Validate user exists
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check if already joined
            existing = NewcomerSupport.objects(user_id=ObjectId(user_id)).first()
            if existing:
                return {
                    "success": True,
                    "status": "already_joined",
                    "newcomer_support_id": str(existing.id),
                    "total_bonuses_earned": existing.total_bonuses_earned,
                    "instant_bonus_claimed": existing.instant_bonus_claimed,
                    "monthly_opportunities_count": existing.monthly_opportunities_count,
                    "message": "User already joined Newcomer Support program"
                }
            
            # Create Newcomer Support record
            newcomer_support = NewcomerSupport(
                user_id=ObjectId(user_id),
                joined_at=datetime.utcnow(),
                is_active=True
            )
            
            # Initialize bonuses
            newcomer_support.bonuses = self._initialize_newcomer_bonuses()
            
            newcomer_support.save()
            
            # Create eligibility record
            eligibility = NewcomerSupportEligibility(user_id=ObjectId(user_id))
            eligibility.save()
            
            # Log the action
            self._log_action(user_id, "joined_program", "User joined Newcomer Support program")
            
            return {
                "success": True,
                "newcomer_support_id": str(newcomer_support.id),
                "user_id": user_id,
                "is_eligible": False,
                "is_active": True,
                "joined_at": newcomer_support.joined_at,
                "message": "Successfully joined Newcomer Support program"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_matrix_contribution(self, user_id: str, amount: float, **kwargs) -> Dict[str, Any]:
        """Stub: record a Matrix contribution into NGS context for compatibility."""
        try:
            return {
                "success": True,
                "user_id": user_id,
                "amount": float(amount) if amount is not None else 0.0,
                "context": {k: v for k, v in (kwargs or {}).items()}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_eligibility(self, user_id: str, force_check: bool = False) -> Dict[str, Any]:
        """Check Newcomer Support eligibility for user"""
        try:
            # Get Newcomer Support record
            newcomer_support = NewcomerSupport.objects(user_id=ObjectId(user_id)).first()
            if not newcomer_support:
                return {"success": False, "error": "User not in Newcomer Support program"}
            
            # Get eligibility record
            eligibility = NewcomerSupportEligibility.objects(user_id=ObjectId(user_id)).first()
            if not eligibility:
                eligibility = NewcomerSupportEligibility(user_id=ObjectId(user_id))
            
            # Check Matrix program status
            matrix_status = self._check_matrix_program_status(user_id)
            eligibility.has_matrix_program = matrix_status["has_matrix"]
            eligibility.matrix_join_date = matrix_status["join_date"]
            eligibility.matrix_slots_activated = matrix_status["slots_activated"]
            
            # Check newcomer status
            newcomer_status = self._check_newcomer_status(user_id)
            eligibility.is_newcomer = newcomer_status["is_newcomer"]
            eligibility.newcomer_end_date = newcomer_status["end_date"]
            
            # Update Newcomer Support record
            newcomer_support.has_matrix_program = matrix_status["has_matrix"]
            newcomer_support.matrix_join_date = matrix_status["join_date"]
            newcomer_support.matrix_slots_activated = matrix_status["slots_activated"]
            
            # Determine eligibility for different bonuses
            eligibility.is_eligible_for_instant_bonus = (
                eligibility.has_matrix_program and
                eligibility.is_newcomer
            )
            
            eligibility.is_eligible_for_monthly_opportunities = (
                eligibility.has_matrix_program and
                eligibility.is_newcomer
            )
            
            eligibility.is_eligible_for_upline_rank_bonus = (
                eligibility.has_matrix_program and
                eligibility.is_newcomer
            )
            
            # Update eligibility reasons
            eligibility_reasons = self._get_eligibility_reasons(eligibility)
            eligibility.eligibility_reasons = eligibility_reasons
            
            if eligibility.is_eligible_for_instant_bonus and not newcomer_support.is_eligible:
                eligibility.qualified_at = datetime.utcnow()
                newcomer_support.is_eligible = True
                newcomer_support.qualified_at = datetime.utcnow()
                newcomer_support.instant_bonus_eligible = True
                newcomer_support.monthly_opportunities_eligible = True
                newcomer_support.upline_rank_bonus_eligible = True
                
                # Activate bonuses
                for bonus in newcomer_support.bonuses:
                    bonus.is_active = True
                    bonus.activated_at = datetime.utcnow()
                
                self._log_action(user_id, "became_eligible", "User became eligible for Newcomer Support bonuses")
            
            eligibility.last_checked = datetime.utcnow()
            eligibility.save()
            
            newcomer_support.last_updated = datetime.utcnow()
            newcomer_support.save()
            
            return {
                "success": True,
                "user_id": user_id,
                "is_eligible": eligibility.is_eligible_for_instant_bonus,
                "matrix_program": {
                    "has_matrix_program": eligibility.has_matrix_program,
                    "matrix_join_date": eligibility.matrix_join_date,
                    "matrix_slots_activated": eligibility.matrix_slots_activated
                },
                "newcomer_status": {
                    "is_newcomer": eligibility.is_newcomer,
                    "newcomer_period_days": eligibility.newcomer_period_days,
                    "newcomer_end_date": eligibility.newcomer_end_date
                },
                "bonus_eligibility": {
                    "instant_bonus": eligibility.is_eligible_for_instant_bonus,
                    "monthly_opportunities": eligibility.is_eligible_for_monthly_opportunities,
                    "upline_rank_bonus": eligibility.is_eligible_for_upline_rank_bonus
                },
                "eligibility_reasons": eligibility.eligibility_reasons,
                "qualified_at": eligibility.qualified_at,
                "last_checked": eligibility.last_checked
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_instant_bonus(self, user_id: str) -> Dict[str, Any]:
        """Process instant bonus for newcomer"""
        try:
            # Get Newcomer Support record
            newcomer_support = NewcomerSupport.objects(user_id=ObjectId(user_id)).first()
            if not newcomer_support:
                return {"success": False, "error": "User not in Newcomer Support program"}
            
            if not newcomer_support.instant_bonus_eligible:
                return {"success": False, "error": "User not eligible for instant bonus"}
            
            if newcomer_support.instant_bonus_claimed:
                return {"success": False, "error": "Instant bonus already claimed"}
            
            # Get settings for instant bonus amount
            settings = NewcomerSupportSettings.objects(is_active=True).first()
            instant_bonus_amount = settings.instant_bonus_amount if settings else 50.0
            
            # Create bonus record
            bonus = NewcomerSupportBonus(
                user_id=ObjectId(user_id),
                newcomer_support_id=newcomer_support.id,
                bonus_type="instant",
                bonus_name="Instant Bonus",
                bonus_amount=instant_bonus_amount,
                source_type="matrix_join",
                source_description="Instant bonus upon joining Matrix program",
                payment_status="pending"
            )
            bonus.save()
            
            # Update Newcomer Support record
            newcomer_support.instant_bonus_amount = instant_bonus_amount
            newcomer_support.instant_bonus_claimed = True
            newcomer_support.instant_bonus_claimed_at = datetime.utcnow()
            newcomer_support.total_bonuses_earned += instant_bonus_amount
            newcomer_support.pending_bonuses += instant_bonus_amount
            newcomer_support.last_updated = datetime.utcnow()
            newcomer_support.save()
            
            # Log the action
            self._log_action(user_id, "instant_bonus_earned", f"Earned instant bonus: ${instant_bonus_amount}")
            
            return {
                "success": True,
                "bonus_id": str(bonus.id),
                "user_id": user_id,
                "bonus_type": "instant",
                "bonus_amount": instant_bonus_amount,
                "currency": "USDT",
                "payment_status": "pending",
                "message": f"Instant bonus processed: ${instant_bonus_amount}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_monthly_opportunity(self, user_id: str, opportunity_type: str) -> Dict[str, Any]:
        """Process monthly earning opportunity"""
        try:
            # Get Newcomer Support record
            newcomer_support = NewcomerSupport.objects(user_id=ObjectId(user_id)).first()
            if not newcomer_support:
                return {"success": False, "error": "User not in Newcomer Support program"}
            
            if not newcomer_support.monthly_opportunities_eligible:
                return {"success": False, "error": "User not eligible for monthly opportunities"}
            
            # Get current month
            current_month = datetime.utcnow().strftime("%Y-%m")
            
            # Check if opportunity already exists for this month
            existing_opportunity = NewcomerSupportMonthlyOpportunity.objects(
                user_id=ObjectId(user_id),
                opportunity_month=current_month,
                opportunity_type=opportunity_type
            ).first()
            
            if existing_opportunity:
                return {"success": False, "error": "Monthly opportunity already exists for this month"}
            
            # Calculate opportunity value based on type
            opportunity_value = self._calculate_opportunity_value(opportunity_type, user_id)
            
            # Create opportunity record
            opportunity = NewcomerSupportMonthlyOpportunity(
                user_id=ObjectId(user_id),
                newcomer_support_id=newcomer_support.id,
                opportunity_month=current_month,
                opportunity_type=opportunity_type,
                opportunity_description=self._get_opportunity_description(opportunity_type),
                opportunity_value=opportunity_value,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            opportunity.save()
            
            # Update Newcomer Support record
            newcomer_support.monthly_opportunities_count += 1
            newcomer_support.last_monthly_opportunity = datetime.utcnow()
            newcomer_support.next_monthly_opportunity = datetime.utcnow() + timedelta(days=30)
            newcomer_support.total_bonuses_earned += opportunity_value
            newcomer_support.pending_bonuses += opportunity_value
            newcomer_support.last_updated = datetime.utcnow()
            newcomer_support.save()
            
            # Log the action
            self._log_action(user_id, "monthly_opportunity_gained", 
                           f"Gained monthly opportunity: ${opportunity_value}")
            
            return {
                "success": True,
                "opportunity_id": str(opportunity.id),
                "user_id": user_id,
                "opportunity_month": current_month,
                "opportunity_type": opportunity_type,
                "opportunity_value": opportunity_value,
                "expires_at": opportunity.expires_at,
                "message": f"Monthly opportunity processed: ${opportunity_value}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_upline_rank_bonus(self, user_id: str, upline_user_id: str) -> Dict[str, Any]:
        """Process upline rank bonus"""
        try:
            # Get Newcomer Support record
            newcomer_support = NewcomerSupport.objects(user_id=ObjectId(user_id)).first()
            if not newcomer_support:
                return {"success": False, "error": "User not in Newcomer Support program"}
            
            if not newcomer_support.upline_rank_bonus_eligible:
                return {"success": False, "error": "User not eligible for upline rank bonus"}
            
            # Check if user has achieved same rank as upline
            rank_match = self._check_rank_match(user_id, upline_user_id)
            if not rank_match["is_match"]:
                return {"success": False, "error": "User has not achieved same rank as upline"}
            
            # Get settings for upline rank bonus percentage
            settings = NewcomerSupportSettings.objects(is_active=True).first()
            bonus_percentage = settings.upline_rank_bonus_percentage if settings else 10.0
            
            # Calculate bonus amount (10% of upline's earnings)
            bonus_amount = self._calculate_upline_rank_bonus_amount(upline_user_id, bonus_percentage)
            
            # Create bonus record
            bonus = NewcomerSupportBonus(
                user_id=ObjectId(user_id),
                newcomer_support_id=newcomer_support.id,
                bonus_type="upline_rank",
                bonus_name="Upline Rank Bonus",
                bonus_amount=bonus_amount,
                bonus_percentage=bonus_percentage,
                source_type="upline_rank_match",
                source_description="Bonus for achieving same rank as upline",
                upline_user_id=ObjectId(upline_user_id),
                upline_rank=rank_match["upline_rank"],
                user_rank=rank_match["user_rank"],
                payment_status="pending"
            )
            bonus.save()
            
            # Update Newcomer Support record
            newcomer_support.upline_user_id = ObjectId(upline_user_id)
            newcomer_support.upline_rank = rank_match["upline_rank"]
            newcomer_support.user_rank = rank_match["user_rank"]
            newcomer_support.upline_rank_bonus_percentage = bonus_percentage
            newcomer_support.upline_rank_bonus_amount = bonus_amount
            newcomer_support.upline_rank_bonus_claimed = True
            newcomer_support.upline_rank_bonus_claimed_at = datetime.utcnow()
            newcomer_support.total_bonuses_earned += bonus_amount
            newcomer_support.pending_bonuses += bonus_amount
            newcomer_support.last_updated = datetime.utcnow()
            newcomer_support.save()
            
            # Log the action
            self._log_action(user_id, "upline_rank_bonus_earned", 
                           f"Earned upline rank bonus: ${bonus_amount}")
            
            return {
                "success": True,
                "bonus_id": str(bonus.id),
                "user_id": user_id,
                "upline_user_id": upline_user_id,
                "bonus_type": "upline_rank",
                "bonus_amount": bonus_amount,
                "bonus_percentage": bonus_percentage,
                "upline_rank": rank_match["upline_rank"],
                "user_rank": rank_match["user_rank"],
                "currency": "USDT",
                "payment_status": "pending",
                "message": f"Upline rank bonus processed: ${bonus_amount}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def distribute_bonus_payment(self, bonus_id: str) -> Dict[str, Any]:
        """Distribute Newcomer Support bonus payment"""
        try:
            bonus = NewcomerSupportBonus.objects(id=ObjectId(bonus_id)).first()
            if not bonus:
                return {"success": False, "error": "Bonus not found"}
            
            if bonus.payment_status != "pending":
                return {"success": False, "error": "Bonus already processed"}
            
            # Check fund availability
            fund = NewcomerSupportFund.objects(is_active=True).first()
            if not fund:
                return {"success": False, "error": "Newcomer Support fund not found"}
            
            if fund.available_amount < bonus.bonus_amount:
                return {"success": False, "error": "Insufficient fund balance"}
            
            # Process payment
            bonus.payment_status = "processing"
            bonus.processed_at = datetime.utcnow()
            bonus.save()
            
            # Update fund
            fund.available_amount -= bonus.bonus_amount
            fund.distributed_amount += bonus.bonus_amount
            fund.total_bonuses_paid += 1
            fund.total_amount_distributed += bonus.bonus_amount
            fund.last_updated = datetime.utcnow()
            fund.save()
            
            # Update Newcomer Support record
            newcomer_support = NewcomerSupport.objects(id=bonus.newcomer_support_id).first()
            if newcomer_support:
                newcomer_support.total_bonuses_claimed += bonus.bonus_amount
                newcomer_support.pending_bonuses -= bonus.bonus_amount
                newcomer_support.last_updated = datetime.utcnow()
                newcomer_support.save()
            
            # Complete payment
            bonus.payment_status = "paid"
            bonus.paid_at = datetime.utcnow()
            bonus.payment_reference = f"NS-{bonus.id}"
            bonus.save()
            
            # Log the action
            self._log_action(str(bonus.user_id), "bonus_paid", 
                           f"Paid {bonus.bonus_type} bonus: ${bonus.bonus_amount}")
            
            return {
                "success": True,
                "bonus_id": bonus_id,
                "bonus_amount": bonus.bonus_amount,
                "currency": bonus.currency,
                "payment_status": "paid",
                "payment_reference": bonus.payment_reference,
                "paid_at": bonus.paid_at,
                "message": "Bonus payment distributed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_newcomer_support_statistics(self, period: str = "all_time") -> Dict[str, Any]:
        """Get Newcomer Support program statistics"""
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
            total_eligible = NewcomerSupport.objects(is_eligible=True).count()
            total_active = NewcomerSupport.objects(is_active=True).count()
            
            # Get bonuses for period
            bonuses = NewcomerSupportBonus.objects(
                created_at__gte=start_date,
                created_at__lt=end_date,
                payment_status="paid"
            )
            
            total_bonuses_paid = bonuses.count()
            total_amount_distributed = sum(bonus.bonus_amount for bonus in bonuses)
            
            # Bonus breakdown
            instant_bonuses = bonuses.filter(bonus_type="instant")
            monthly_opportunities = bonuses.filter(bonus_type="monthly")
            upline_rank_bonuses = bonuses.filter(bonus_type="upline_rank")
            
            bonus_breakdown = {
                "instant_bonuses_paid": instant_bonuses.count(),
                "instant_bonuses_amount": sum(b.bonus_amount for b in instant_bonuses),
                "monthly_opportunities_given": monthly_opportunities.count(),
                "monthly_opportunities_amount": sum(b.bonus_amount for b in monthly_opportunities),
                "upline_rank_bonuses_paid": upline_rank_bonuses.count(),
                "upline_rank_bonuses_amount": sum(b.bonus_amount for b in upline_rank_bonuses)
            }
            
            # Create or update statistics record
            statistics = NewcomerSupportStatistics.objects(period=period).first()
            if not statistics:
                statistics = NewcomerSupportStatistics(period=period)
            
            statistics.period_start = start_date
            statistics.period_end = end_date
            statistics.total_eligible_users = total_eligible
            statistics.total_active_users = total_active
            statistics.total_bonuses_paid = total_bonuses_paid
            statistics.total_amount_distributed = total_amount_distributed
            statistics.instant_bonuses_paid = bonus_breakdown["instant_bonuses_paid"]
            statistics.instant_bonuses_amount = bonus_breakdown["instant_bonuses_amount"]
            statistics.monthly_opportunities_given = bonus_breakdown["monthly_opportunities_given"]
            statistics.monthly_opportunities_amount = bonus_breakdown["monthly_opportunities_amount"]
            statistics.upline_rank_bonuses_paid = bonus_breakdown["upline_rank_bonuses_paid"]
            statistics.upline_rank_bonuses_amount = bonus_breakdown["upline_rank_bonuses_amount"]
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
                    "total_bonuses_paid": total_bonuses_paid,
                    "total_amount_distributed": total_amount_distributed,
                    "bonus_breakdown": bonus_breakdown,
                    "growth_statistics": {
                        "new_eligible_users": 0,  # Would need historical data
                        "new_bonus_earners": 0,   # Would need historical data
                        "total_newcomers": 0,  # Would need to calculate
                        "total_matrix_joins": 0  # Would need to calculate
                    }
                },
                "last_updated": statistics.last_updated
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _initialize_newcomer_bonuses(self) -> List[NewcomerBonus]:
        """Initialize Newcomer bonuses"""
        return [
            NewcomerBonus(
                bonus_type="instant",
                bonus_name="Instant Bonus",
                bonus_amount=50.0,
                currency="USDT"
            ),
            NewcomerBonus(
                bonus_type="monthly",
                bonus_name="Monthly Opportunities",
                bonus_amount=0.0,
                currency="USDT"
            ),
            NewcomerBonus(
                bonus_type="upline_rank",
                bonus_name="Upline Rank Bonus",
                bonus_amount=0.0,
                bonus_percentage=10.0,
                currency="USDT"
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
            ).order_by('created_at')
            
            has_matrix = matrix_activations.count() > 0
            join_date = None
            
            if has_matrix:
                first_slot = matrix_activations.first()
                join_date = first_slot.created_at
            
            return {
                "has_matrix": has_matrix,
                "join_date": join_date,
                "slots_activated": matrix_activations.count()
            }
            
        except Exception:
            return {
                "has_matrix": False,
                "join_date": None,
                "slots_activated": 0
            }
    
    def _check_newcomer_status(self, user_id: str) -> Dict[str, Any]:
        """Check newcomer status for user"""
        try:
            # Check if user is within 30 days of joining
            user = User.objects(id=ObjectId(user_id)).first()
            if user and user.created_at:
                days_since_join = (datetime.utcnow() - user.created_at).days
                is_newcomer = days_since_join <= 30
                end_date = user.created_at + timedelta(days=30) if is_newcomer else None
            else:
                is_newcomer = False
                end_date = None
            
            return {
                "is_newcomer": is_newcomer,
                "end_date": end_date
            }
        except Exception:
            return {
                "is_newcomer": False,
                "end_date": None
            }
    
    def _calculate_opportunity_value(self, opportunity_type: str, user_id: str) -> float:
        """Calculate opportunity value based on type"""
        try:
            # Base values for different opportunity types
            base_values = {
                "upline_activity": 25.0,
                "team_growth": 50.0,
                "personal_achievement": 75.0
            }
            
            base_value = base_values.get(opportunity_type, 25.0)
            
            # Add some variation based on user activity
            # This would be implemented based on actual business logic
            return base_value
            
        except Exception:
            return 25.0
    
    def _check_rank_match(self, user_id: str, upline_user_id: str) -> Dict[str, Any]:
        """Check if user has achieved same rank as upline"""
        try:
            # This would need to be implemented based on actual rank system
            # For now, returning mock data
            return {
                "is_match": False,
                "user_rank": "Unknown",
                "upline_rank": "Unknown"
            }
        except Exception:
            return {
                "is_match": False,
                "user_rank": "Unknown",
                "upline_rank": "Unknown"
            }
    
    def _calculate_upline_rank_bonus_amount(self, upline_user_id: str, bonus_percentage: float) -> float:
        """Calculate upline rank bonus amount"""
        try:
            # This would need to be implemented based on actual upline earnings
            # For now, returning mock data
            return 100.0  # Mock amount
        except Exception:
            return 100.0
    
    def _get_opportunity_description(self, opportunity_type: str) -> str:
        """Get opportunity description for given type"""
        descriptions = {
            "upline_activity": "Monthly opportunity based on upline activity",
            "team_growth": "Monthly opportunity based on team growth",
            "personal_achievement": "Monthly opportunity based on personal achievement"
        }
        return descriptions.get(opportunity_type, "Unknown opportunity")
    
    def _get_eligibility_reasons(self, eligibility: NewcomerSupportEligibility) -> List[str]:
        """Get eligibility reasons"""
        reasons = []
        
        if not eligibility.has_matrix_program:
            reasons.append("Matrix program not joined")
        
        if not eligibility.is_newcomer:
            reasons.append("Not within newcomer period (30 days)")
        
        return reasons
    
    def _log_action(self, user_id: str, action_type: str, description: str):
        """Log Newcomer Support action"""
        try:
            log = NewcomerSupportLog(
                user_id=ObjectId(user_id),
                action_type=action_type,
                action_description=description,
                is_processed=True,
                processed_at=datetime.utcnow()
            )
            log.save()
        except Exception:
            pass  # Logging failure shouldn't break the main process

    def get_newcomer_support_income(self, user_id: str, currency: str = "USDT", page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get Newcomer Growth Support income data for user"""
        try:
            # Validate user exists
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get Newcomer Support record
            newcomer_support = NewcomerSupport.objects(user_id=ObjectId(user_id)).first()
            if not newcomer_support:
                return {
                    "success": True,
                    "data": {
                        "income_data": [],
                        "total_count": 0,
                        "page": page,
                        "limit": limit,
                        "total_pages": 0,
                        "currency": currency,
                        "total_earned": 0.0,
                        "total_claimed": 0.0,
                        "pending_amount": 0.0
                    }
                }
            
            # Calculate pagination
            skip = (page - 1) * limit
            
            # Get bonus payments for this user
            bonuses = NewcomerSupportBonus.objects(user_id=ObjectId(user_id)).order_by('-created_at').skip(skip).limit(limit)
            total_bonuses = NewcomerSupportBonus.objects(user_id=ObjectId(user_id)).count()
            
            # Format income data similar to the screenshot format
            income_data = []
            for bonus in bonuses:
                # Format date similar to screenshot (DD Mon YYYY (HH:MM))
                created_date = bonus.created_at.strftime("%d %b %Y")
                created_time = bonus.created_at.strftime("(%H:%M)")
                time_date = f"{created_date} {created_time}"
                
                income_data.append({
                    "sl_no": len(income_data) + 1 + skip,  # Sequential number
                    "usdt": bonus.bonus_amount,
                    "time_date": time_date,
                    "bonus_type": bonus.bonus_type,
                    "bonus_name": bonus.bonus_name,
                    "payment_status": bonus.payment_status,
                    "currency": bonus.currency,
                    "created_at": bonus.created_at.isoformat()
                })
            
            # Calculate totals
            total_earned = newcomer_support.total_bonuses_earned
            total_claimed = newcomer_support.total_bonuses_claimed
            pending_amount = newcomer_support.pending_bonuses
            
            # Calculate total pages
            total_pages = (total_bonuses + limit - 1) // limit
            
            return {
                "success": True,
                "data": {
                    "income_data": income_data,
                    "total_count": total_bonuses,
                    "page": page,
                    "limit": limit,
                    "total_pages": total_pages,
                    "currency": currency,
                    "total_earned": total_earned,
                    "total_claimed": total_claimed,
                    "pending_amount": pending_amount,
                    "newcomer_support_status": {
                        "is_eligible": newcomer_support.is_eligible,
                        "is_active": newcomer_support.is_active,
                        "has_matrix_program": newcomer_support.has_matrix_program,
                        "instant_bonus_eligible": newcomer_support.instant_bonus_eligible,
                        "monthly_opportunities_eligible": newcomer_support.monthly_opportunities_eligible,
                        "upline_rank_bonus_eligible": newcomer_support.upline_rank_bonus_eligible,
                        "joined_at": newcomer_support.joined_at.isoformat() if newcomer_support.joined_at else None,
                        "qualified_at": newcomer_support.qualified_at.isoformat() if newcomer_support.qualified_at else None
                    }
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_all_newcomer_support_income(self, currency: str = "USDT", page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get Newcomer Growth Support income data for all users - following dream matrix pattern"""
        try:
            # Get all bonus payments across all users
            bonuses = NewcomerSupportBonus.objects().order_by('-created_at')
            total_bonuses = bonuses.count()
            
            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 10)))
            start = (page - 1) * limit
            end = start + limit
            page_bonuses = bonuses[start:end]
            
            # Format income data exactly like the image (SL.No, USDT, Time & Date)
            items = []
            for i, bonus in enumerate(page_bonuses):
                # Format date exactly like image (DD Mon YYYY (HH:MM))
                created_date = bonus.created_at.strftime("%d %b %Y")
                created_time = bonus.created_at.strftime("(%H:%M)")
                time_date = f"{created_date} {created_time}"
                
                items.append({
                    "sl_no": start + i + 1,  # Sequential number starting from page offset
                    "usdt": float(bonus.bonus_amount),
                    "time_date": time_date
                })
            
            return {
                "success": True,
                "data": {
                    "page": page,
                    "limit": limit,
                    "total": total_bonuses,
                    "items": items
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
