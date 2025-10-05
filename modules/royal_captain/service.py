from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta
from ..user.model import User
from ..slot.model import SlotActivation
from ..tree.model import TreePlacement
from .model import (
    RoyalCaptain, RoyalCaptainEligibility, RoyalCaptainBonusPayment,
    RoyalCaptainFund, RoyalCaptainSettings, RoyalCaptainLog, RoyalCaptainStatistics,
    RoyalCaptainRequirement, RoyalCaptainBonus
)

class RoyalCaptainService:
    """Royal Captain Bonus Business Logic Service"""
    
    def __init__(self):
        pass
    
    def join_royal_captain_program(self, user_id: str) -> Dict[str, Any]:
        """Join Royal Captain Bonus program"""
        try:
            # Validate user exists
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check if already joined
            existing = RoyalCaptain.objects(user_id=ObjectId(user_id)).first()
            if existing:
                return {
                    "success": True,
                    "status": "already_joined",
                    "royal_captain_id": str(existing.id),
                    "current_tier": existing.current_tier,
                    "total_bonus_earned": existing.total_bonus_earned,
                    "message": "User already joined Royal Captain program"
                }
            
            # Create Royal Captain record
            royal_captain = RoyalCaptain(
                user_id=ObjectId(user_id),
                joined_at=datetime.utcnow(),
                is_active=True
            )
            
            # Initialize requirements
            royal_captain.requirements = self._initialize_requirements()
            
            # Initialize bonus tiers
            royal_captain.bonuses = self._initialize_bonus_tiers()
            
            royal_captain.save()
            
            # Create eligibility record
            eligibility = RoyalCaptainEligibility(user_id=ObjectId(user_id))
            eligibility.save()
            
            # Log the action
            self._log_action(user_id, "joined_program", "User joined Royal Captain program")
            
            return {
                "success": True,
                "royal_captain_id": str(royal_captain.id),
                "user_id": user_id,
                "current_tier": 0,
                "is_eligible": False,
                "is_active": True,
                "joined_at": royal_captain.joined_at,
                "message": "Successfully joined Royal Captain program"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_eligibility(self, user_id: str, force_check: bool = False) -> Dict[str, Any]:
        """Check Royal Captain eligibility for user"""
        try:
            # Get Royal Captain record
            royal_captain = RoyalCaptain.objects(user_id=ObjectId(user_id)).first()
            if not royal_captain:
                return {"success": False, "error": "User not in Royal Captain program"}
            
            # Get eligibility record
            eligibility = RoyalCaptainEligibility.objects(user_id=ObjectId(user_id)).first()
            if not eligibility:
                eligibility = RoyalCaptainEligibility(user_id=ObjectId(user_id))
            
            # Check package requirements
            package_status = self._check_package_requirements(user_id)
            royal_captain.matrix_package_active = package_status["matrix_active"]
            royal_captain.global_package_active = package_status["global_active"]
            royal_captain.both_packages_active = package_status["both_active"]
            
            # Check direct partners
            partners_status = self._check_direct_partners(user_id)
            royal_captain.total_direct_partners = partners_status["total_partners"]
            royal_captain.direct_partners_with_both_packages = partners_status["partners_with_both_packages"]
            royal_captain.direct_partners_list = partners_status["partners_list"]
            
            # Check global team
            team_status = self._check_global_team(user_id)
            royal_captain.total_global_team = team_status["total_team"]
            royal_captain.global_team_list = team_status["team_list"]
            
            # Update eligibility
            eligibility.has_matrix_package = royal_captain.matrix_package_active
            eligibility.has_global_package = royal_captain.global_package_active
            eligibility.has_both_packages = royal_captain.both_packages_active
            eligibility.direct_partners_count = royal_captain.total_direct_partners
            eligibility.direct_partners_with_both_packages = royal_captain.direct_partners_with_both_packages
            eligibility.global_team_count = royal_captain.total_global_team
            
            # Determine eligibility
            eligibility.is_eligible_for_royal_captain = (
                eligibility.has_both_packages and
                eligibility.direct_partners_with_both_packages >= 5
            )
            
            # Update eligibility reasons
            eligibility_reasons = self._get_eligibility_reasons(eligibility)
            eligibility.eligibility_reasons = eligibility_reasons
            
            if eligibility.is_eligible_for_royal_captain and not royal_captain.is_eligible:
                eligibility.qualified_at = datetime.utcnow()
                royal_captain.is_eligible = True
                self._log_action(user_id, "became_eligible", "User became eligible for Royal Captain bonuses")
            
            eligibility.last_checked = datetime.utcnow()
            eligibility.save()
            
            royal_captain.last_updated = datetime.utcnow()
            royal_captain.save()
            
            return {
                "success": True,
                "user_id": user_id,
                "is_eligible": eligibility.is_eligible_for_royal_captain,
                "package_status": {
                    "has_matrix_package": eligibility.has_matrix_package,
                    "has_global_package": eligibility.has_global_package,
                    "has_both_packages": eligibility.has_both_packages
                },
                "requirements": {
                    "direct_partners_count": eligibility.direct_partners_count,
                    "direct_partners_with_both_packages": eligibility.direct_partners_with_both_packages,
                    "min_direct_partners_required": eligibility.min_direct_partners_required,
                    "global_team_count": eligibility.global_team_count
                },
                "eligibility_reasons": eligibility.eligibility_reasons,
                "qualified_at": eligibility.qualified_at,
                "last_checked": eligibility.last_checked
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Backwards-compatible alias used by tests/scripts
    def check_royal_captain_eligibility(self, user_id: str, force_check: bool = False) -> Dict[str, Any]:
        """Alias for check_eligibility to preserve older call sites"""
        return self.check_eligibility(user_id, force_check)
    
    def process_bonus_tiers(self, user_id: str) -> Dict[str, Any]:
        """Process Royal Captain bonus tiers for user"""
        try:
            royal_captain = RoyalCaptain.objects(user_id=ObjectId(user_id)).first()
            if not royal_captain:
                return {"success": False, "error": "User not in Royal Captain program"}
            
            if not royal_captain.is_eligible:
                return {"success": False, "error": "User not eligible for Royal Captain bonuses"}
            
            # Check each bonus tier
            bonuses_earned = []
            new_tier = royal_captain.current_tier
            
            for bonus in royal_captain.bonuses:
                if not bonus.is_achieved:
                    # Check if requirements are met
                    if self._check_bonus_tier_requirements(royal_captain, bonus):
                        # Award bonus
                        bonus.is_achieved = True
                        bonus.achieved_at = datetime.utcnow()
                        
                        # Create bonus payment
                        bonus_payment = RoyalCaptainBonusPayment(
                            user_id=ObjectId(user_id),
                            royal_captain_id=royal_captain.id,
                            bonus_tier=bonus.bonus_tier,
                            bonus_amount=bonus.bonus_amount,
                            currency="USD",
                            direct_partners_at_payment=royal_captain.direct_partners_with_both_packages,
                            global_team_at_payment=royal_captain.total_global_team,
                            payment_status="pending"
                        )
                        bonus_payment.save()
                        
                        # Update Royal Captain record
                        royal_captain.total_bonus_earned += bonus.bonus_amount
                        royal_captain.current_tier = bonus.bonus_tier
                        new_tier = bonus.bonus_tier
                        
                        bonuses_earned.append({
                            "tier": bonus.bonus_tier,
                            "amount": bonus.bonus_amount,
                            "currency": bonus.currency,
                            "achieved_at": bonus.achieved_at
                        })
                        
                        # Log the action
                        self._log_action(user_id, "bonus_earned", f"Earned tier {bonus.bonus_tier} bonus: ${bonus.bonus_amount}")
            
            royal_captain.last_updated = datetime.utcnow()
            royal_captain.save()
            
            return {
                "success": True,
                "user_id": user_id,
                "old_tier": royal_captain.current_tier - len(bonuses_earned),
                "new_tier": new_tier,
                "bonuses_earned": bonuses_earned,
                "total_bonus_earned": royal_captain.total_bonus_earned,
                "message": f"Processed {len(bonuses_earned)} bonus tiers"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_royal_captain_status(self, user_id: str) -> Dict[str, Any]:
        """Return current Royal Captain status for a user"""
        try:
            rc = RoyalCaptain.objects(user_id=ObjectId(user_id)).first()
            if not rc:
                return {"success": False, "error": "User not in Royal Captain program"}
            return {
                "success": True,
                "user_id": user_id,
                "is_eligible": rc.is_eligible,
                "is_active": rc.is_active,
                "current_tier": rc.current_tier,
                "total_direct_partners": rc.total_direct_partners,
                "total_global_team": rc.total_global_team,
                "total_bonus_earned": rc.total_bonus_earned,
                "both_packages_active": rc.both_packages_active,
                "direct_partners_with_both_packages": rc.direct_partners_with_both_packages,
                "bonuses": [
                    {
                        "bonus_tier": b.bonus_tier,
                        "direct_partners_required": b.direct_partners_required,
                        "global_team_required": b.global_team_required,
                        "bonus_amount": b.bonus_amount,
                        "currency": getattr(b, 'currency', 'USDT'),
                        "is_achieved": b.is_achieved,
                        "achieved_at": b.achieved_at,
                    }
                    for b in rc.bonuses
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def claim_royal_captain_bonus(self, user_id: str) -> Dict[str, Any]:
        """Claim Royal Captain bonus by evaluating and awarding eligible tiers.
        This is an alias that runs tier processing and returns the updated status.
        """
        result = self.process_bonus_tiers(user_id)
        if not result.get("success"):
            return result
        # Return fresh status after processing
        status = self.get_royal_captain_status(user_id)
        if status.get("success"):
            status["message"] = "Royal Captain bonuses processed"
        return status
    
    def distribute_bonus_payment(self, bonus_payment_id: str) -> Dict[str, Any]:
        """Distribute Royal Captain bonus payment"""
        try:
            bonus_payment = RoyalCaptainBonusPayment.objects(id=ObjectId(bonus_payment_id)).first()
            if not bonus_payment:
                return {"success": False, "error": "Bonus payment not found"}
            
            if bonus_payment.payment_status != "pending":
                return {"success": False, "error": "Bonus payment already processed"}
            
            # Check fund availability
            fund = RoyalCaptainFund.objects(is_active=True).first()
            if not fund:
                return {"success": False, "error": "Royal Captain fund not found"}
            
            if fund.available_amount < bonus_payment.bonus_amount:
                return {"success": False, "error": "Insufficient fund balance"}
            
            # Process payment
            bonus_payment.payment_status = "processing"
            bonus_payment.processed_at = datetime.utcnow()
            bonus_payment.save()
            
            # Update fund
            fund.available_amount -= bonus_payment.bonus_amount
            fund.distributed_amount += bonus_payment.bonus_amount
            fund.total_bonuses_paid += 1
            fund.total_amount_distributed += bonus_payment.bonus_amount
            fund.last_updated = datetime.utcnow()
            fund.save()
            
            # Complete payment
            bonus_payment.payment_status = "paid"
            bonus_payment.paid_at = datetime.utcnow()
            bonus_payment.payment_reference = f"RC-{bonus_payment.id}"
            bonus_payment.save()
            
            # Log the action
            self._log_action(str(bonus_payment.user_id), "bonus_paid", 
                           f"Paid tier {bonus_payment.bonus_tier} bonus: ${bonus_payment.bonus_amount}")
            
            return {
                "success": True,
                "bonus_payment_id": bonus_payment_id,
                "bonus_amount": bonus_payment.bonus_amount,
                "currency": bonus_payment.currency,
                "payment_status": "paid",
                "payment_reference": bonus_payment.payment_reference,
                "paid_at": bonus_payment.paid_at,
                "message": "Bonus payment distributed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_royal_captain_statistics(self, period: str = "all_time") -> Dict[str, Any]:
        """Get Royal Captain program statistics"""
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
            total_eligible = RoyalCaptain.objects(is_eligible=True).count()
            total_active = RoyalCaptain.objects(is_active=True).count()
            
            # Get bonus payments for period
            bonus_payments = RoyalCaptainBonusPayment.objects(
                created_at__gte=start_date,
                created_at__lt=end_date,
                payment_status="paid"
            )
            
            total_bonuses_paid = bonus_payments.count()
            total_amount_distributed = sum(payment.bonus_amount for payment in bonus_payments)
            
            # Tier statistics
            tier_stats = {}
            for tier in range(1, 6):
                tier_stats[f"tier_{tier}"] = bonus_payments.filter(bonus_tier=tier).count()
            
            # Create or update statistics record
            statistics = RoyalCaptainStatistics.objects(period=period).first()
            if not statistics:
                statistics = RoyalCaptainStatistics(period=period)
            
            statistics.period_start = start_date
            statistics.period_end = end_date
            statistics.total_eligible_users = total_eligible
            statistics.total_active_users = total_active
            statistics.total_bonuses_paid = total_bonuses_paid
            statistics.total_amount_distributed = total_amount_distributed
            statistics.tier_1_achievements = tier_stats["tier_1"]
            statistics.tier_2_achievements = tier_stats["tier_2"]
            statistics.tier_3_achievements = tier_stats["tier_3"]
            statistics.tier_4_achievements = tier_stats["tier_4"]
            statistics.tier_5_achievements = tier_stats["tier_5"]
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
                    "tier_achievements": tier_stats,
                    "growth_statistics": {
                        "new_eligible_users": 0,  # Would need historical data
                        "new_bonus_earners": 0,   # Would need historical data
                        "total_direct_partners": 0,  # Would need to calculate
                        "total_global_team": 0       # Would need to calculate
                    }
                },
                "last_updated": statistics.last_updated
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _initialize_requirements(self) -> List[RoyalCaptainRequirement]:
        """Initialize Royal Captain requirements"""
        return [
            RoyalCaptainRequirement(
                requirement_type="both_packages",
                requirement_value=1,
                requirement_description="Must have both Matrix and Global packages active"
            ),
            RoyalCaptainRequirement(
                requirement_type="direct_partners",
                requirement_value=5,
                requirement_description="Must have 5 direct partners with both packages"
            ),
            RoyalCaptainRequirement(
                requirement_type="global_team",
                requirement_value=0,
                requirement_description="Global team size requirement"
            )
        ]
    
    def _initialize_bonus_tiers(self) -> List[RoyalCaptainBonus]:
        """Initialize Royal Captain bonus tiers according to PROJECT_DOCUMENTATION.md"""
        return [
            RoyalCaptainBonus(
                bonus_tier=1,
                direct_partners_required=5,
                global_team_required=0,
                bonus_amount=200.0,
                currency='USDT',
                bonus_description="Royal Captain Bonus - 5 direct partners (Binary+Matrix+Global)"
            ),
            RoyalCaptainBonus(
                bonus_tier=2,
                direct_partners_required=5,
                global_team_required=10,
                bonus_amount=200.0,
                currency='USDT',
                bonus_description="Royal Captain Bonus - 5 direct partners, 10 global team"
            ),
            RoyalCaptainBonus(
                bonus_tier=3,
                direct_partners_required=5,
                global_team_required=50,
                bonus_amount=200.0,
                currency='USDT',
                bonus_description="Royal Captain Bonus - 5 direct partners, 50 global team"
            ),
            RoyalCaptainBonus(
                bonus_tier=4,
                direct_partners_required=5,
                global_team_required=100,
                bonus_amount=200.0,
                currency='USDT',
                bonus_description="Royal Captain Bonus - 5 direct partners, 100 global team"
            ),
            RoyalCaptainBonus(
                bonus_tier=5,
                direct_partners_required=5,
                global_team_required=200,
                bonus_amount=250.0,
                currency='USDT',
                bonus_description="Royal Captain Bonus - 5 direct partners, 200 global team"
            ),
            RoyalCaptainBonus(
                bonus_tier=6,
                direct_partners_required=5,
                global_team_required=300,
                bonus_amount=250.0,
                currency='USDT',
                bonus_description="Royal Captain Bonus - 5 direct partners, 300 global team"
            )
        ]
    
    def _check_package_requirements(self, user_id: str) -> Dict[str, bool]:
        """Check if user has Matrix and Global packages active"""
        try:
            # Check Matrix package
            matrix_activations = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program="matrix",
                status="completed"
            ).count()
            
            # Check Global package
            global_activations = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program="global",
                status="completed"
            ).count()
            
            matrix_active = matrix_activations > 0
            global_active = global_activations > 0
            both_active = matrix_active and global_active
            
            return {
                "matrix_active": matrix_active,
                "global_active": global_active,
                "both_active": both_active
            }
            
        except Exception:
            return {
                "matrix_active": False,
                "global_active": False,
                "both_active": False
            }
    
    def _check_direct_partners(self, user_id: str) -> Dict[str, Any]:
        """Check direct partners with both packages using referral link (fast path)"""
        try:
            # Fetch direct partners by referral relationship
            direct_users = User.objects(refered_by=ObjectId(user_id))
            partners_with_both_packages = 0
            partners_list = []
            for u in direct_users:
                partners_list.append(u.id)
                pkg = self._check_package_requirements(str(u.id))
                if pkg["both_active"]:
                    partners_with_both_packages += 1
            return {
                "total_partners": len(direct_users),
                "partners_with_both_packages": partners_with_both_packages,
                "partners_list": partners_list
            }
        except Exception:
            return {"total_partners": 0, "partners_with_both_packages": 0, "partners_list": []}
    
    def _check_global_team(self, user_id: str) -> Dict[str, Any]:
        """Check global team size"""
        try:
            # Get all team members (simplified - would need proper global team calculation)
            team_members = TreePlacement.objects(
                parent_id=ObjectId(user_id),
                is_active=True
            ).all()
            
            team_list = [member.user_id for member in team_members]
            
            return {
                "total_team": len(team_members),
                "team_list": team_list
            }
            
        except Exception:
            return {
                "total_team": 0,
                "team_list": []
            }
    
    def _get_eligibility_reasons(self, eligibility: RoyalCaptainEligibility) -> List[str]:
        """Get eligibility reasons"""
        reasons = []
        
        if not eligibility.has_matrix_package:
            reasons.append("Matrix package not active")
        if not eligibility.has_global_package:
            reasons.append("Global package not active")
        if eligibility.direct_partners_with_both_packages < 5:
            needed = 5 - eligibility.direct_partners_with_both_packages
            reasons.append(f"Need {needed} more direct partners with both packages")
        
        return reasons
    
    def _check_bonus_tier_requirements(self, royal_captain: RoyalCaptain, bonus: RoyalCaptainBonus) -> bool:
        """Check if bonus tier requirements are met"""
        return (
            royal_captain.direct_partners_with_both_packages >= bonus.direct_partners_required and
            royal_captain.total_global_team >= bonus.global_team_required
        )
    
    def _log_action(self, user_id: str, action_type: str, description: str):
        """Log Royal Captain action"""
        try:
            log = RoyalCaptainLog(
                user_id=ObjectId(user_id),
                action_type=action_type,
                action_description=description,
                is_processed=True,
                processed_at=datetime.utcnow()
            )
            log.save()
        except Exception:
            pass  # Logging failure shouldn't break the main process
