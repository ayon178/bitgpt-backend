from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta
from ..user.model import User
from ..slot.model import SlotActivation
from ..tree.model import TreePlacement
from .model import (
    PresidentReward, PresidentRewardEligibility, PresidentRewardPayment,
    PresidentRewardFund, PresidentRewardSettings, PresidentRewardLog, 
    PresidentRewardStatistics, PresidentRewardMilestone, PresidentRewardTier
)

class PresidentRewardService:
    """President Reward Business Logic Service"""
    
    def __init__(self):
        pass
    
    def join_president_reward_program(self, user_id: str) -> Dict[str, Any]:
        """Join President Reward program"""
        try:
            # Validate user exists
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check if already joined
            existing = PresidentReward.objects(user_id=ObjectId(user_id)).first()
            if existing:
                return {
                    "success": True,
                    "status": "already_joined",
                    "president_reward_id": str(existing.id),
                    "current_tier": existing.current_tier,
                    "total_rewards_earned": existing.total_rewards_earned,
                    "message": "User already joined President Reward program"
                }
            
            # Create President Reward record
            president_reward = PresidentReward(
                user_id=ObjectId(user_id),
                joined_at=datetime.utcnow(),
                is_active=True
            )
            
            # Initialize tiers
            president_reward.tiers = self._initialize_president_reward_tiers()
            
            president_reward.save()
            
            # Create eligibility record
            eligibility = PresidentRewardEligibility(user_id=ObjectId(user_id))
            eligibility.save()
            
            # Log the action
            self._log_action(user_id, "joined_program", "User joined President Reward program")
            
            return {
                "success": True,
                "president_reward_id": str(president_reward.id),
                "user_id": user_id,
                "current_tier": 0,
                "is_eligible": False,
                "is_active": True,
                "joined_at": president_reward.joined_at,
                "message": "Successfully joined President Reward program"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_eligibility(self, user_id: str, force_check: bool = False) -> Dict[str, Any]:
        """Check President Reward eligibility for user"""
        try:
            # Get President Reward record
            president_reward = PresidentReward.objects(user_id=ObjectId(user_id)).first()
            if not president_reward:
                return {"success": False, "error": "User not in President Reward program"}
            
            # Get eligibility record
            eligibility = PresidentRewardEligibility.objects(user_id=ObjectId(user_id)).first()
            if not eligibility:
                eligibility = PresidentRewardEligibility(user_id=ObjectId(user_id))
            
            # Check direct partners
            partners_status = self._check_direct_partners(user_id)
            eligibility.direct_partners_matrix_count = partners_status["matrix_partners"]
            eligibility.direct_partners_global_count = partners_status["global_partners"]
            eligibility.direct_partners_both_count = partners_status["both_partners"]
            
            # Update President Reward record
            president_reward.direct_partners_matrix = partners_status["matrix_partners"]
            president_reward.direct_partners_global = partners_status["global_partners"]
            president_reward.direct_partners_both = partners_status["both_partners"]
            president_reward.total_direct_partners = partners_status["total_partners"]
            
            # Check global team
            team_status = self._check_global_team(user_id)
            eligibility.global_team_count = team_status["total_team"]
            president_reward.global_team_size = team_status["total_team"]
            president_reward.global_team_members = team_status["team_list"]
            
            # Determine eligibility
            eligibility.is_eligible_for_president_reward = (
                eligibility.direct_partners_both_count >= 30
            )
            
            # Check tier qualifications
            eligibility.qualified_for_tier_1 = (
                eligibility.direct_partners_both_count >= 10 and
                eligibility.global_team_count >= 80
            )
            eligibility.qualified_for_tier_6 = (
                eligibility.direct_partners_both_count >= 15 and
                eligibility.global_team_count >= 400
            )
            eligibility.qualified_for_tier_10 = (
                eligibility.direct_partners_both_count >= 20 and
                eligibility.global_team_count >= 1000
            )
            eligibility.qualified_for_tier_15 = (
                eligibility.direct_partners_both_count >= 30 and
                eligibility.global_team_count >= 40000
            )
            
            # Update eligibility reasons
            eligibility_reasons = self._get_eligibility_reasons(eligibility)
            eligibility.eligibility_reasons = eligibility_reasons
            
            if eligibility.is_eligible_for_president_reward and not president_reward.is_eligible:
                eligibility.qualified_at = datetime.utcnow()
                president_reward.is_eligible = True
                president_reward.qualified_at = datetime.utcnow()
                self._log_action(user_id, "became_eligible", "User became eligible for President Reward")
            
            eligibility.last_checked = datetime.utcnow()
            eligibility.save()
            
            president_reward.last_updated = datetime.utcnow()
            president_reward.save()
            
            return {
                "success": True,
                "user_id": user_id,
                "is_eligible": eligibility.is_eligible_for_president_reward,
                "direct_partners": {
                    "matrix_partners": eligibility.direct_partners_matrix_count,
                    "global_partners": eligibility.direct_partners_global_count,
                    "both_partners": eligibility.direct_partners_both_count,
                    "min_required": eligibility.min_direct_partners_required
                },
                "global_team": {
                    "total_team": eligibility.global_team_count
                },
                "tier_qualifications": {
                    "tier_1": eligibility.qualified_for_tier_1,
                    "tier_6": eligibility.qualified_for_tier_6,
                    "tier_10": eligibility.qualified_for_tier_10,
                    "tier_15": eligibility.qualified_for_tier_15
                },
                "eligibility_reasons": eligibility.eligibility_reasons,
                "qualified_at": eligibility.qualified_at,
                "last_checked": eligibility.last_checked
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_reward_tiers(self, user_id: str) -> Dict[str, Any]:
        """Process President Reward tiers for user"""
        try:
            president_reward = PresidentReward.objects(user_id=ObjectId(user_id)).first()
            if not president_reward:
                return {"success": False, "error": "User not in President Reward program"}
            
            if not president_reward.is_eligible:
                return {"success": False, "error": "User not eligible for President Reward"}
            
            # Check each tier
            rewards_earned = []
            new_highest_tier = president_reward.highest_tier_achieved
            
            for tier in president_reward.tiers:
                if not tier.is_achieved:
                    # Check if requirements are met
                    if self._check_tier_requirements(president_reward, tier):
                        # Award reward
                        tier.is_achieved = True
                        tier.achieved_at = datetime.utcnow()
                        tier.requirements_met = {
                            "direct_partners_at_achievement": president_reward.direct_partners_both,
                            "global_team_at_achievement": president_reward.global_team_size
                        }
                        
                        # Create reward payment
                        reward_payment = PresidentRewardPayment(
                            user_id=ObjectId(user_id),
                            president_reward_id=president_reward.id,
                            tier_number=tier.tier_number,
                            reward_amount=tier.reward_amount,
                            currency="USD",
                            direct_partners_at_payment=president_reward.direct_partners_both,
                            global_team_at_payment=president_reward.global_team_size,
                            payment_status="pending"
                        )
                        reward_payment.save()
                        
                        # Update President Reward record
                        president_reward.total_rewards_earned += tier.reward_amount
                        president_reward.pending_rewards += tier.reward_amount
                        president_reward.current_tier = tier.tier_number
                        president_reward.highest_tier_achieved = max(president_reward.highest_tier_achieved, tier.tier_number)
                        new_highest_tier = president_reward.highest_tier_achieved
                        
                        rewards_earned.append({
                            "tier": tier.tier_number,
                            "amount": tier.reward_amount,
                            "currency": tier.currency,
                            "achieved_at": tier.achieved_at
                        })
                        
                        # Add to achievements
                        president_reward.achievements.append({
                            "tier": tier.tier_number,
                            "amount": tier.reward_amount,
                            "achieved_at": tier.achieved_at,
                            "requirements_met": tier.requirements_met
                        })
                        
                        # Log the action
                        self._log_action(user_id, "tier_achieved", f"Achieved tier {tier.tier_number}: ${tier.reward_amount}")
            
            president_reward.last_updated = datetime.utcnow()
            president_reward.save()
            
            return {
                "success": True,
                "user_id": user_id,
                "old_highest_tier": president_reward.highest_tier_achieved - len(rewards_earned),
                "new_highest_tier": new_highest_tier,
                "rewards_earned": rewards_earned,
                "total_rewards_earned": president_reward.total_rewards_earned,
                "pending_rewards": president_reward.pending_rewards,
                "message": f"Processed {len(rewards_earned)} reward tiers"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def distribute_reward_payment(self, payment_id: str) -> Dict[str, Any]:
        """Distribute President Reward payment"""
        try:
            payment = PresidentRewardPayment.objects(id=ObjectId(payment_id)).first()
            if not payment:
                return {"success": False, "error": "Reward payment not found"}
            
            if payment.payment_status != "pending":
                return {"success": False, "error": "Reward payment already processed"}
            
            # Check fund availability
            fund = PresidentRewardFund.objects(is_active=True).first()
            if not fund:
                return {"success": False, "error": "President Reward fund not found"}
            
            if fund.available_amount < payment.reward_amount:
                return {"success": False, "error": "Insufficient fund balance"}
            
            # Process payment
            payment.payment_status = "processing"
            payment.processed_at = datetime.utcnow()
            payment.save()
            
            # Update fund
            fund.available_amount -= payment.reward_amount
            fund.distributed_amount += payment.reward_amount
            fund.total_rewards_paid += 1
            fund.total_amount_distributed += payment.reward_amount
            fund.last_updated = datetime.utcnow()
            fund.save()
            
            # Update President Reward record
            president_reward = PresidentReward.objects(id=payment.president_reward_id).first()
            if president_reward:
                president_reward.total_rewards_paid += payment.reward_amount
                president_reward.pending_rewards -= payment.reward_amount
                president_reward.last_updated = datetime.utcnow()
                president_reward.save()
            
            # Complete payment
            payment.payment_status = "paid"
            payment.paid_at = datetime.utcnow()
            payment.payment_reference = f"PR-{payment.id}"
            payment.save()
            
            # Log the action
            self._log_action(str(payment.user_id), "reward_paid", 
                           f"Paid tier {payment.tier_number} reward: ${payment.reward_amount}")
            
            return {
                "success": True,
                "payment_id": payment_id,
                "reward_amount": payment.reward_amount,
                "currency": payment.currency,
                "payment_status": "paid",
                "payment_reference": payment.payment_reference,
                "paid_at": payment.paid_at,
                "message": "Reward payment distributed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_president_reward_statistics(self, period: str = "all_time") -> Dict[str, Any]:
        """Get President Reward program statistics"""
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
            total_eligible = PresidentReward.objects(is_eligible=True).count()
            total_active = PresidentReward.objects(is_active=True).count()
            
            # Get reward payments for period
            reward_payments = PresidentRewardPayment.objects(
                created_at__gte=start_date,
                created_at__lt=end_date,
                payment_status="paid"
            )
            
            total_rewards_paid = reward_payments.count()
            total_amount_distributed = sum(payment.reward_amount for payment in reward_payments)
            
            # Tier statistics
            tier_stats = {
                "tier_1": reward_payments.filter(tier_number=1).count(),
                "tier_6": reward_payments.filter(tier_number=6).count(),
                "tier_10": reward_payments.filter(tier_number=10).count(),
                "tier_15": reward_payments.filter(tier_number=15).count()
            }
            
            # Create or update statistics record
            statistics = PresidentRewardStatistics.objects(period=period).first()
            if not statistics:
                statistics = PresidentRewardStatistics(period=period)
            
            statistics.period_start = start_date
            statistics.period_end = end_date
            statistics.total_eligible_users = total_eligible
            statistics.total_active_users = total_active
            statistics.total_rewards_paid = total_rewards_paid
            statistics.total_amount_distributed = total_amount_distributed
            statistics.tier_1_achievements = tier_stats["tier_1"]
            statistics.tier_6_achievements = tier_stats["tier_6"]
            statistics.tier_10_achievements = tier_stats["tier_10"]
            statistics.tier_15_achievements = tier_stats["tier_15"]
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
                    "total_rewards_paid": total_rewards_paid,
                    "total_amount_distributed": total_amount_distributed,
                    "tier_achievements": tier_stats,
                    "growth_statistics": {
                        "new_eligible_users": 0,  # Would need historical data
                        "new_reward_earners": 0,   # Would need historical data
                        "total_direct_partners": 0,  # Would need to calculate
                        "total_global_team": 0       # Would need to calculate
                    }
                },
                "last_updated": statistics.last_updated
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _initialize_president_reward_tiers(self) -> List[PresidentRewardTier]:
        """Initialize President Reward tiers based on PROJECT_DOCUMENTATION.md"""
        return [
            # Tier 1-5: $500-$700
            PresidentRewardTier(tier_number=1, direct_partners_required=10, global_team_required=80, reward_amount=500.0, tier_description="Tier 1: 10 direct partners, 80 global team"),
            PresidentRewardTier(tier_number=2, direct_partners_required=10, global_team_required=150, reward_amount=700.0, tier_description="Tier 2: 10 direct partners, 150 global team"),
            PresidentRewardTier(tier_number=3, direct_partners_required=10, global_team_required=200, reward_amount=700.0, tier_description="Tier 3: 10 direct partners, 200 global team"),
            PresidentRewardTier(tier_number=4, direct_partners_required=10, global_team_required=250, reward_amount=700.0, tier_description="Tier 4: 10 direct partners, 250 global team"),
            PresidentRewardTier(tier_number=5, direct_partners_required=10, global_team_required=300, reward_amount=700.0, tier_description="Tier 5: 10 direct partners, 300 global team"),
            
            # Tier 6-9: $800
            PresidentRewardTier(tier_number=6, direct_partners_required=15, global_team_required=400, reward_amount=800.0, tier_description="Tier 6: 15 direct partners, 400 global team"),
            PresidentRewardTier(tier_number=7, direct_partners_required=15, global_team_required=500, reward_amount=800.0, tier_description="Tier 7: 15 direct partners, 500 global team"),
            PresidentRewardTier(tier_number=8, direct_partners_required=15, global_team_required=600, reward_amount=800.0, tier_description="Tier 8: 15 direct partners, 600 global team"),
            PresidentRewardTier(tier_number=9, direct_partners_required=15, global_team_required=700, reward_amount=800.0, tier_description="Tier 9: 15 direct partners, 700 global team"),
            
            # Tier 10-14: $1500
            PresidentRewardTier(tier_number=10, direct_partners_required=20, global_team_required=1000, reward_amount=1500.0, tier_description="Tier 10: 20 direct partners, 1000 global team"),
            PresidentRewardTier(tier_number=11, direct_partners_required=20, global_team_required=1500, reward_amount=1500.0, tier_description="Tier 11: 20 direct partners, 1500 global team"),
            PresidentRewardTier(tier_number=12, direct_partners_required=20, global_team_required=2000, reward_amount=1500.0, tier_description="Tier 12: 20 direct partners, 2000 global team"),
            PresidentRewardTier(tier_number=13, direct_partners_required=20, global_team_required=2500, reward_amount=1500.0, tier_description="Tier 13: 20 direct partners, 2500 global team"),
            PresidentRewardTier(tier_number=14, direct_partners_required=20, global_team_required=3000, reward_amount=2000.0, tier_description="Tier 14: 20 direct partners, 3000 global team"),
            
            # Tier 15: $3000
            PresidentRewardTier(tier_number=15, direct_partners_required=30, global_team_required=40000, reward_amount=3000.0, tier_description="Tier 15: 30 direct partners, 40000 global team")
        ]
    
    def _check_direct_partners(self, user_id: str) -> Dict[str, int]:
        """Check direct partners for Matrix and Global programs"""
        try:
            # Get direct partners from tree
            direct_partners = TreePlacement.objects(
                parent_id=ObjectId(user_id),
                is_active=True
            ).all()
            
            matrix_partners = 0
            global_partners = 0
            both_partners = 0
            
            for partner in direct_partners:
                partner_id = partner.user_id
                
                # Check Matrix package
                matrix_activations = SlotActivation.objects(
                    user_id=partner_id,
                    program="matrix",
                    status="completed"
                ).count()
                
                # Check Global package
                global_activations = SlotActivation.objects(
                    user_id=partner_id,
                    program="global",
                    status="completed"
                ).count()
                
                if matrix_activations > 0:
                    matrix_partners += 1
                if global_activations > 0:
                    global_partners += 1
                if matrix_activations > 0 and global_activations > 0:
                    both_partners += 1
            
            return {
                "matrix_partners": matrix_partners,
                "global_partners": global_partners,
                "both_partners": both_partners,
                "total_partners": len(direct_partners)
            }
            
        except Exception:
            return {
                "matrix_partners": 0,
                "global_partners": 0,
                "both_partners": 0,
                "total_partners": 0
            }
    
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
    
    def _get_eligibility_reasons(self, eligibility: PresidentRewardEligibility) -> List[str]:
        """Get eligibility reasons"""
        reasons = []
        
        if eligibility.direct_partners_both_count < 30:
            needed = 30 - eligibility.direct_partners_both_count
            reasons.append(f"Need {needed} more direct partners with both Matrix and Global packages")
        
        return reasons
    
    def _check_tier_requirements(self, president_reward: PresidentReward, tier: PresidentRewardTier) -> bool:
        """Check if tier requirements are met"""
        return (
            president_reward.direct_partners_both >= tier.direct_partners_required and
            president_reward.global_team_size >= tier.global_team_required
        )
    
    def _log_action(self, user_id: str, action_type: str, description: str):
        """Log President Reward action"""
        try:
            log = PresidentRewardLog(
                user_id=ObjectId(user_id),
                action_type=action_type,
                action_description=description,
                is_processed=True,
                processed_at=datetime.utcnow()
            )
            log.save()
        except Exception:
            pass  # Logging failure shouldn't break the main process
