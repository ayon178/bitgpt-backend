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
            
            # Determine eligibility (documentation): 10 direct partners + 400 global team
            eligibility.is_eligible_for_president_reward = (
                eligibility.direct_partners_both_count >= 10 and
                eligibility.global_team_count >= 400
            )

            # Check tier qualifications from configured tiers
            tier_requirements = {t.tier_number: (t.direct_partners_required, t.global_team_required) for t in president_reward.tiers}
            eligibility.qualified_for_tier_1 = (
                eligibility.direct_partners_both_count >= tier_requirements.get(1, (0, 0))[0] and
                eligibility.global_team_count >= tier_requirements.get(1, (0, 0))[1]
            )
            eligibility.qualified_for_tier_6 = (
                eligibility.direct_partners_both_count >= tier_requirements.get(6, (0, 0))[0] and
                eligibility.global_team_count >= tier_requirements.get(6, (0, 0))[1]
            )
            eligibility.qualified_for_tier_10 = (
                eligibility.direct_partners_both_count >= tier_requirements.get(10, (0, 0))[0] and
                eligibility.global_team_count >= tier_requirements.get(10, (0, 0))[1]
            )
            eligibility.qualified_for_tier_15 = (
                eligibility.direct_partners_both_count >= tier_requirements.get(15, (0, 0))[0] and
                eligibility.global_team_count >= tier_requirements.get(15, (0, 0))[1]
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
                            currency=getattr(tier, 'currency', 'USDT'),
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
    
    def claim_president_reward(self, user_id: str, currency: str = 'USDT') -> Dict[str, Any]:
        """Claim President Reward for the user's current eligible tier.
        - Checks eligibility (10 direct + 400 team minimum)
        - Prevents claims within 24 hours
        - Tier progression stops lower tiers when higher tier is eligible
        - Credits wallet in USDT or BNB
        """
        try:
            currency = (currency or 'USDT').upper()
            if currency not in ('USDT', 'BNB'):
                return {"success": False, "error": "Invalid currency; must be USDT or BNB"}

            # Get President Reward record directly
            pr = PresidentReward.objects(user_id=ObjectId(user_id)).first()
            if not pr:
                return {"success": False, "error": "User not in President Reward program"}
            
            # Check eligibility from PR record (not from check_eligibility method)
            if not pr.is_eligible:
                return {"success": False, "error": "You are not eligible to claim President Reward"}

            # Prevent claims within 24h
            last_payment = PresidentRewardPayment.objects(user_id=ObjectId(user_id)).order_by('-created_at').first()
            if last_payment:
                hours_since = (datetime.utcnow() - last_payment.created_at).total_seconds() / 3600
                if hours_since < 24:
                    return {"success": False, "error": f"You can claim again in {int(24 - hours_since)} hours"}

            # Determine the highest tier the user qualifies for
            highest_tier = None
            for t in sorted(pr.tiers, key=lambda x: x.tier_number, reverse=True):
                if self._check_tier_requirements(pr, t):
                    highest_tier = t
                    break
            if not highest_tier:
                return {"success": False, "error": "Not eligible for any tier"}

            # Check if already achieved
            if highest_tier.is_achieved:
                return {"success": False, "error": f"Tier {highest_tier.tier_number} already claimed"}

            # Mark achieved
            highest_tier.is_achieved = True
            highest_tier.achieved_at = datetime.utcnow()

            # Create payment
            payment = PresidentRewardPayment(
                user_id=ObjectId(user_id),
                president_reward_id=pr.id,
                tier_number=highest_tier.tier_number,
                reward_amount=highest_tier.reward_amount,
                currency=currency,
                direct_partners_at_payment=pr.direct_partners_both,
                global_team_at_payment=pr.global_team_size,
                payment_status='pending'
            )
            payment.save()

            # Auto-distribute
            dist = self.distribute_reward_payment(str(payment.id), currency=currency)
            if not dist.get('success'):
                return {"success": False, "error": dist.get('error', 'Distribution failed')}

            # Update President Reward record
            pr.current_tier = highest_tier.tier_number
            pr.highest_tier_achieved = max(pr.highest_tier_achieved or 0, highest_tier.tier_number)
            pr.total_rewards_earned += highest_tier.reward_amount
            pr.last_updated = datetime.utcnow()
            pr.save()

            self._log_action(user_id, "reward_claimed", f"Claimed tier {highest_tier.tier_number}: ${highest_tier.reward_amount} {currency}")

            return {
                "success": True,
                "user_id": user_id,
                "tier": highest_tier.tier_number,
                "amount": highest_tier.reward_amount,
                "currency": currency,
                "payment_id": str(payment.id),
                "message": f"President Reward tier {highest_tier.tier_number} claimed successfully"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def distribute_reward_payment(self, payment_id: str, currency: str = 'USDT') -> Dict[str, Any]:
        """Distribute President Reward payment - supports USDT and BNB"""
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
            
            # Check currency-specific balance
            if currency == 'BNB':
                available = fund.available_amount_bnb or fund.available_amount
            else:
                available = fund.available_amount_usdt or fund.available_amount
            
            if available < payment.reward_amount:
                return {"success": False, "error": f"Insufficient {currency} fund balance"}
            
            # Process payment
            payment.payment_status = "processing"
            payment.processed_at = datetime.utcnow()
            payment.save()
            
            # Update fund - currency specific
            if currency == 'BNB':
                fund.available_amount_bnb -= payment.reward_amount
                fund.distributed_amount_bnb += payment.reward_amount
            else:
                fund.available_amount_usdt -= payment.reward_amount
                fund.distributed_amount_usdt += payment.reward_amount
            
            fund.total_rewards_paid += 1
            fund.total_amount_distributed += payment.reward_amount
            fund.last_updated = datetime.utcnow()
            fund.save()
            
            # Credit wallet
            try:
                from modules.wallet.service import WalletService
                ws = WalletService()
                ws.credit_main_wallet(
                    user_id=str(payment.user_id),
                    amount=payment.reward_amount,
                    currency=currency,
                    reason='president_reward',
                    tx_hash=f'PR-PAY-{payment_id}'
                )
            except Exception:
                pass
            
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
        """Initialize President Reward tiers per PROJECT_DOCUMENTATION.md (USDT)."""
        return [
            # 10 directs tier set
            PresidentRewardTier(tier_number=1, direct_partners_required=10, global_team_required=400, reward_amount=500.0, currency='USDT', tier_description="Tier 1: 10 directs, 400 team"),
            PresidentRewardTier(tier_number=2, direct_partners_required=10, global_team_required=600, reward_amount=700.0, currency='USDT', tier_description="Tier 2: 10 directs, 600 team"),
            PresidentRewardTier(tier_number=3, direct_partners_required=10, global_team_required=800, reward_amount=700.0, currency='USDT', tier_description="Tier 3: 10 directs, 800 team"),
            PresidentRewardTier(tier_number=4, direct_partners_required=10, global_team_required=1000, reward_amount=700.0, currency='USDT', tier_description="Tier 4: 10 directs, 1000 team"),
            PresidentRewardTier(tier_number=5, direct_partners_required=10, global_team_required=1200, reward_amount=700.0, currency='USDT', tier_description="Tier 5: 10 directs, 1200 team"),
            # 15 directs tier set
            PresidentRewardTier(tier_number=6, direct_partners_required=15, global_team_required=1500, reward_amount=800.0, currency='USDT', tier_description="Tier 6: 15 directs, 1500 team"),
            PresidentRewardTier(tier_number=7, direct_partners_required=15, global_team_required=1800, reward_amount=800.0, currency='USDT', tier_description="Tier 7: 15 directs, 1800 team"),
            PresidentRewardTier(tier_number=8, direct_partners_required=15, global_team_required=2100, reward_amount=800.0, currency='USDT', tier_description="Tier 8: 15 directs, 2100 team"),
            PresidentRewardTier(tier_number=9, direct_partners_required=15, global_team_required=2400, reward_amount=800.0, currency='USDT', tier_description="Tier 9: 15 directs, 2400 team"),
            # 20 directs tier set
            PresidentRewardTier(tier_number=10, direct_partners_required=20, global_team_required=2700, reward_amount=1500.0, currency='USDT', tier_description="Tier 10: 20 directs, 2700 team"),
            PresidentRewardTier(tier_number=11, direct_partners_required=20, global_team_required=3000, reward_amount=1500.0, currency='USDT', tier_description="Tier 11: 20 directs, 3000 team"),
            PresidentRewardTier(tier_number=12, direct_partners_required=20, global_team_required=3500, reward_amount=2000.0, currency='USDT', tier_description="Tier 12: 20 directs, 3500 team"),
            PresidentRewardTier(tier_number=13, direct_partners_required=20, global_team_required=4000, reward_amount=2500.0, currency='USDT', tier_description="Tier 13: 20 directs, 4000 team"),
            PresidentRewardTier(tier_number=14, direct_partners_required=20, global_team_required=5000, reward_amount=2500.0, currency='USDT', tier_description="Tier 14: 20 directs, 5000 team"),
            # 25 directs
            PresidentRewardTier(tier_number=15, direct_partners_required=25, global_team_required=6000, reward_amount=5000.0, currency='USDT', tier_description="Tier 15: 25 directs, 6000 team"),
        ]
    
    def _check_direct_partners(self, user_id: str) -> Dict[str, int]:
        """Fast direct partner check using referral link; relies on joined flags."""
        try:
            directs = User.objects(refered_by=ObjectId(user_id))
            matrix_partners = sum(1 for u in directs if getattr(u, 'matrix_joined', False))
            global_partners = sum(1 for u in directs if getattr(u, 'global_joined', False))
            both_partners = sum(1 for u in directs if getattr(u, 'matrix_joined', False) and getattr(u, 'global_joined', False))
            return {
                "matrix_partners": matrix_partners,
                "global_partners": global_partners,
                "both_partners": both_partners,
                "total_partners": directs.count()
            }
        except Exception:
            return {"matrix_partners": 0, "global_partners": 0, "both_partners": 0, "total_partners": 0}
    
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
