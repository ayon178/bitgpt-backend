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

    def claim_royal_captain_bonus(self, user_id: str, currency: str = 'USDT') -> Dict[str, Any]:
        """Claim Royal Captain bonus for the user's current eligible tier.
        - Checks eligibility and tier thresholds
        - Prevents claims within 24 hours of last claim
        - When eligible for a higher tier, stops previous tier and starts new tier
        - Credits wallet in the requested currency (USDT or BNB)
        """
        try:
            currency = (currency or 'USDT').upper()
            if currency not in ('USDT', 'BNB'):
                return {"success": False, "error": "Invalid currency; must be USDT or BNB"}

            # Check eligibility using our new method
            elig = self.check_user_eligibility_without_record(user_id)
            if not elig.get('success') or not elig.get('is_eligible'):
                return {"success": False, "error": "You are not eligible to claim Royal Captain bonus"}

            # Get claimable amount info
            claimable_info = self.get_claimable_amount(user_id)
            if not claimable_info.get('is_eligible') or not claimable_info.get('can_claim_now'):
                return {"success": False, "error": claimable_info.get('message', 'Cannot claim now')}

            # Prevent claims within 24h
            last_payment = RoyalCaptainBonusPayment.objects(user_id=ObjectId(user_id)).order_by('-created_at').first()
            if last_payment:
                hours_since = (datetime.utcnow() - last_payment.created_at).total_seconds() / 3600
                if hours_since < 24:
                    return {"success": False, "error": f"You can claim again in {int(24 - hours_since)} hours"}

            # Get claimable amounts
            claimable_amounts = claimable_info.get('claimable_amounts', {})
            eligible_tier = claimable_info.get('eligible_tier', 1)
            
            # Determine amounts based on currency
            if currency == 'USDT':
                claim_usdt = claimable_amounts.get('USDT', 0.0)
                claim_bnb = 0.0
            elif currency == 'BNB':
                claim_usdt = 0.0
                claim_bnb = claimable_amounts.get('BNB', 0.0)
            else:
                return {"success": False, "error": "Invalid currency"}

            if claim_usdt == 0.0 and claim_bnb == 0.0:
                return {"success": False, "error": "No claimable amount available"}

            # Check if RoyalCaptain record exists using direct MongoDB query
            from pymongo import MongoClient
            client = MongoClient('mongodb://localhost:27017/')
            db = client['bitgpt']
            rc_exists = db['royal_captain'].find_one({"user_id": ObjectId(user_id)}) is not None
            
            rc = None
            if rc_exists:
                try:
                    rc = RoyalCaptain.objects(user_id=ObjectId(user_id)).first()
                except Exception:
                    # If there's a field mismatch error, delete the old record and create new one
                    db['royal_captain'].delete_one({"user_id": ObjectId(user_id)})
                    rc = None
            
            if not rc:
                
                # Use upsert to avoid duplicate key error
                rc_data = {
                    "user_id": ObjectId(user_id),
                    "joined_at": datetime.utcnow(),
                    "is_active": True,
                    "current_tier": eligible_tier,
                    "total_bonus_earned": 0.0,
                    "matrix_package_active": elig.get('has_both_packages', False),
                    "global_package_active": elig.get('has_both_packages', False),
                    "both_packages_active": elig.get('has_both_packages', False),
                    "direct_partners_with_both_packages": elig.get('direct_partners_with_both', 0),
                    "total_global_team": elig.get('global_team_count', 0),
                    "bonuses": [
                        {
                            "bonus_tier": 1,
                            "direct_partners_required": 5,
                            "global_team_required": 0,
                            "bonus_amount_usd": 200.0,
                            "bonus_amount_usdt": 120.0,
                            "bonus_amount_bnb": 80.0,
                            "bonus_description": "Tier 1 bonus - 200 USD",
                            "is_achieved": False
                        },
                        {
                            "bonus_tier": 2,
                            "direct_partners_required": 5,
                            "global_team_required": 10,
                            "bonus_amount_usd": 200.0,
                            "bonus_amount_usdt": 120.0,
                            "bonus_amount_bnb": 80.0,
                            "bonus_description": "Tier 2 bonus - 200 USD",
                            "is_achieved": False
                        },
                        {
                            "bonus_tier": 3,
                            "direct_partners_required": 5,
                            "global_team_required": 20,
                            "bonus_amount_usd": 200.0,
                            "bonus_amount_usdt": 120.0,
                            "bonus_amount_bnb": 80.0,
                            "bonus_description": "Tier 3 bonus - 200 USD",
                            "is_achieved": False
                        },
                        {
                            "bonus_tier": 4,
                            "direct_partners_required": 5,
                            "global_team_required": 30,
                            "bonus_amount_usd": 250.0,
                            "bonus_amount_usdt": 150.0,
                            "bonus_amount_bnb": 100.0,
                            "bonus_description": "Tier 4 bonus - 250 USD",
                            "is_achieved": False
                        },
                        {
                            "bonus_tier": 5,
                            "direct_partners_required": 5,
                            "global_team_required": 40,
                            "bonus_amount_usd": 250.0,
                            "bonus_amount_usdt": 150.0,
                            "bonus_amount_bnb": 100.0,
                            "bonus_description": "Tier 5 bonus - 250 USD",
                            "is_achieved": False
                        }
                    ]
                }
                
                # Use upsert to create or update
                result = db['royal_captain'].replace_one(
                    {"user_id": ObjectId(user_id)},
                    rc_data,
                    upsert=True
                )
                
                # Load the record back without bonuses field to avoid field mismatch
                rc = RoyalCaptain.objects(user_id=ObjectId(user_id)).exclude('bonuses').first()

            # Create payment
            payment = RoyalCaptainBonusPayment(
                user_id=ObjectId(user_id),
                royal_captain_id=rc.id,
                bonus_tier=eligible_tier,
                bonus_amount=claim_usdt + claim_bnb,
                bonus_amount_usdt=claim_usdt,
                bonus_amount_bnb=claim_bnb,
                currency=currency,
                direct_partners_at_payment=elig.get('direct_partners_with_both', 0),
                global_team_at_payment=elig.get('global_team_count', 0),
                payment_status='pending'
            )
            payment.save()

            # Auto-distribute (credit wallet)
            dist = self.distribute_bonus_payment(str(payment.id))
            if not dist.get('success'):
                return {"success": False, "error": dist.get('error', 'Distribution failed')}

            # Update Royal Captain record
            rc.current_tier = eligible_tier
            rc.total_bonus_earned += (claim_usdt + claim_bnb)
            rc.last_updated = datetime.utcnow()
            rc.save()

            self._log_action(user_id, "bonus_earned", f"Claimed tier {eligible_tier}: {claim_usdt} USDT + {claim_bnb} BNB")

            return {
                "success": True,
                "user_id": user_id,
                "tier": eligible_tier,
                "amount_usd": claim_usdt + claim_bnb,
                "amount_usdt": claim_usdt,
                "amount_bnb": claim_bnb,
                "currency": currency,
                "payment_id": str(payment.id),
                "message": f"Royal Captain bonus tier {eligible_tier} claimed successfully"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_user_eligibility_without_record(self, user_id: str) -> Dict[str, Any]:
        """Check Royal Captain eligibility for user without requiring RoyalCaptain record"""
        try:
            # Check package requirements directly
            package_status = self._check_package_requirements(user_id)
            has_both_packages = package_status.get("both_active", False)
            
            # Check direct partners
            partners_status = self._check_direct_partners(user_id)
            partners_with_both = partners_status.get("partners_with_both_packages", 0)
            
            # Check global team
            team_status = self._check_global_team(user_id)
            global_team_count = team_status.get("total_team", 0)
            
            # Determine eligibility based on requirements
            is_eligible = has_both_packages and partners_with_both >= 5
            
            return {
                "success": True,
                "is_eligible": is_eligible,
                "has_both_packages": has_both_packages,
                "direct_partners_with_both": partners_with_both,
                "global_team_count": global_team_count,
                "requirements_met": {
                    "both_packages": has_both_packages,
                    "five_partners": partners_with_both >= 5
                },
                "message": f"Packages: {has_both_packages}, Partners with both: {partners_with_both}/5, Global team: {global_team_count}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_claimable_amount(self, user_id: str) -> Dict[str, Any]:
        """Get claimable Royal Captain bonus amounts for user by tier and currency"""
        try:
            # Check if user has any past payments (indicates they were eligible before)
            past_payments = RoyalCaptainBonusPayment.objects(user_id=ObjectId(user_id))
            has_past_payments = past_payments.count() > 0
            
            # Check current eligibility (use new method for all users to avoid model issues)
            # Always use the new method since RoyalCaptain model has field issues
            elig = self.check_user_eligibility_without_record(user_id)
            is_currently_eligible = elig.get('success') and elig.get('is_eligible')
            
            # Check if RoyalCaptain record exists (using direct MongoDB query to avoid model issues)
            from pymongo import MongoClient
            client = MongoClient('mongodb://localhost:27017/')
            db = client['bitgpt']
            rc_exists = db['royal_captain'].find_one({"user_id": ObjectId(user_id)}) is not None
            
            # If no past payments and not currently eligible, return not eligible
            if not has_past_payments and not is_currently_eligible:
                return {
                    "success": True,
                    "is_eligible": False,
                    "claimable_amounts": {"USDT": 0, "BNB": 0},
                    "message": "Not eligible for Royal Captain bonus",
                    "eligibility_details": {
                        "has_both_packages": elig.get("has_both_packages", False),
                        "direct_partners_with_both": elig.get("direct_partners_with_both", 0),
                        "global_team_count": elig.get("global_team_count", 0),
                        "requirements_met": elig.get("requirements_met", {})
                    }
                }
            
            # rc already defined above in eligibility check
            
            # Scenario 1: User has past payments but no current RoyalCaptain record
            if has_past_payments and not rc_exists:
                # If user is currently eligible, calculate claimable amounts
                if is_currently_eligible:
                    # Continue to normal flow to calculate claimable amounts
                    pass  # Don't return here, continue to normal flow
                else:
                    return {
                        "success": True,
                        "is_eligible": True,  # Show as eligible since they had past payments
                        "can_claim_now": False,
                        "claimable_amounts": {"USDT": 0, "BNB": 0},
                        "message": "Had past payments but missing RoyalCaptain record - contact support"
                    }
            
            # Scenario 2: User has past payments but current eligibility unclear
            if has_past_payments and not is_currently_eligible:
                return {
                    "success": True,
                    "is_eligible": True,  # Show as eligible since they had past payments
                    "can_claim_now": False,
                    "claimable_amounts": {"USDT": 0, "BNB": 0},
                    "message": "Had past payments but current eligibility unclear - contact support"
                }
            
            # Scenario 3: New user - no past payments, no RoyalCaptain record
            if not has_past_payments and not rc_exists:
                if is_currently_eligible:
                    # User meets requirements but not in program yet
                    eligibility_details = elig if 'elig' in locals() else {}
                    return {
                        "success": True,
                        "is_eligible": True,
                        "can_claim_now": False,
                        "claimable_amounts": {"USDT": 0, "BNB": 0},
                        "message": "Meets requirements but not in Royal Captain program - join program first",
                        "eligibility_details": {
                            "has_both_packages": eligibility_details.get("has_both_packages", False),
                            "direct_partners_with_both": eligibility_details.get("direct_partners_with_both", 0),
                            "global_team_count": eligibility_details.get("global_team_count", 0),
                            "requirements_met": eligibility_details.get("requirements_met", {})
                        }
                    }
                else:
                    # User doesn't meet requirements
                    eligibility_details = elig if 'elig' in locals() else {}
                    return {
                        "success": True,
                        "is_eligible": False,
                        "claimable_amounts": {"USDT": 0, "BNB": 0},
                        "message": "Does not meet Royal Captain requirements - need both Matrix & Global packages + 5 direct partners with both packages",
                        "eligibility_details": {
                            "has_both_packages": eligibility_details.get("has_both_packages", False),
                            "direct_partners_with_both": eligibility_details.get("direct_partners_with_both", 0),
                            "global_team_count": eligibility_details.get("global_team_count", 0),
                            "requirements_met": eligibility_details.get("requirements_met", {})
                        }
                    }
            
            # Scenario 4: User has RoyalCaptain record but no past payments (new program member)
            if not has_past_payments and rc_exists:
                if not is_currently_eligible:
                    return {
                        "success": True,
                        "is_eligible": False,
                        "claimable_amounts": {"USDT": 0, "BNB": 0},
                        "message": "In Royal Captain program but does not meet current requirements"
                    }
                # Continue to normal flow for eligible users with RoyalCaptain record
            
            # Check if claimed within 24h
            last_payment = RoyalCaptainBonusPayment.objects(user_id=ObjectId(user_id)).order_by('-created_at').first()
            can_claim_now = True
            if last_payment:
                hours_since = (datetime.utcnow() - last_payment.created_at).total_seconds() / 3600
                if hours_since < 24:
                    can_claim_now = False
            
            # Calculate claimable amounts based on eligibility and tier requirements
            # Since user is eligible, they should be able to claim Tier 1 bonus
            # According to PROJECT_DOCUMENTATION.md: 5 direct partners = $200 USDT
            
            global_team_count = elig.get("global_team_count", 0)
            partners_with_both = elig.get("direct_partners_with_both", 0)
            
            # Determine eligible tier based on requirements
            eligible_tier = None
            claimable_usdt = 0.0
            claimable_bnb = 0.0
            
            # Tier 1: 5 direct partners, 0 global team = $200 USDT
            if partners_with_both >= 5 and global_team_count >= 0:
                eligible_tier = 1
                claimable_usdt = 200.0  # 60% of $200 = $120 USDT
                claimable_bnb = 0.0     # 40% of $200 = $80 BNB (converted)
            
            # Tier 2: 5 direct partners, 10 global team = $200 USDT  
            elif partners_with_both >= 5 and global_team_count >= 10:
                eligible_tier = 2
                claimable_usdt = 200.0
                claimable_bnb = 0.0
            
            # Tier 3: 5 direct partners, 20 global team = $200 USDT
            elif partners_with_both >= 5 and global_team_count >= 20:
                eligible_tier = 3
                claimable_usdt = 200.0
                claimable_bnb = 0.0
            
            # Tier 4: 5 direct partners, 30 global team = $250 USDT
            elif partners_with_both >= 5 and global_team_count >= 30:
                eligible_tier = 4
                claimable_usdt = 250.0
                claimable_bnb = 0.0
            
            # Tier 5: 5 direct partners, 40 global team = $250 USDT
            elif partners_with_both >= 5 and global_team_count >= 40:
                eligible_tier = 5
                claimable_usdt = 250.0
                claimable_bnb = 0.0
            
            if not eligible_tier:
                return {
                    "success": True,
                    "is_eligible": True,
                    "can_claim_now": can_claim_now,
                    "claimable_amounts": {"USDT": 0, "BNB": 0},
                    "message": "No eligible tier found based on current requirements"
                }
            
            return {
                "success": True,
                "is_eligible": True,
                "can_claim_now": can_claim_now,
                "eligible_tier": eligible_tier,
                "claimable_amounts": {
                    "USDT": claimable_usdt,
                    "BNB": claimable_bnb
                },
                "total_usd": claimable_usdt + claimable_bnb,
                "message": f"Eligible for tier {eligible_tier} bonus" + ("" if can_claim_now else " (wait 24h)"),
                "eligibility_details": {
                    "has_both_packages": elig.get("has_both_packages", False),
                    "direct_partners_with_both": elig.get("direct_partners_with_both", 0),
                    "global_team_count": elig.get("global_team_count", 0),
                    "requirements_met": elig.get("requirements_met", {})
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def distribute_bonus_payment(self, bonus_payment_id: str) -> Dict[str, Any]:
        """Distribute Royal Captain bonus payment - credits both USDT and BNB to wallet"""
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
            
            # Credit wallet - both USDT and BNB
            try:
                from modules.wallet.service import WalletService
                ws = WalletService()
                
                # Credit USDT if amount > 0
                if bonus_payment.bonus_amount_usdt > 0:
                    ws.credit_main_wallet(
                        user_id=str(bonus_payment.user_id),
                        amount=bonus_payment.bonus_amount_usdt,
                        currency='USDT',
                        reason='royal_captain_bonus',
                        tx_hash=f'RC-PAY-{bonus_payment_id}-USDT'
                    )
                
                # Credit BNB if amount > 0
                if bonus_payment.bonus_amount_bnb > 0:
                    ws.credit_main_wallet(
                        user_id=str(bonus_payment.user_id),
                        amount=bonus_payment.bonus_amount_bnb,
                        currency='BNB',
                        reason='royal_captain_bonus',
                        tx_hash=f'RC-PAY-{bonus_payment_id}-BNB'
                    )
            except Exception as e:
                print(f"Wallet credit failed: {str(e)}")
            
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
        """Initialize Royal Captain bonus tiers - 60% USDT + 40% BNB"""
        return [
            RoyalCaptainBonus(
                bonus_tier=1,
                direct_partners_required=5,
                global_team_required=0,
                bonus_amount_usd=200.0,
                bonus_amount_usdt=120.0,  # 60%
                bonus_amount_bnb=0.061,  # 40%
                bonus_description="Royal Captain Tier 1 - 5 direct, 0 team"
            ),
            RoyalCaptainBonus(
                bonus_tier=2,
                direct_partners_required=5,
                global_team_required=10,
                bonus_amount_usd=200.0,
                bonus_amount_usdt=120.0,  # 60%
                bonus_amount_bnb=0.061,  # 40%
                bonus_description="Royal Captain Tier 2 - 5 direct, 10 team"
            ),
            RoyalCaptainBonus(
                bonus_tier=3,
                direct_partners_required=5,
                global_team_required=50,
                bonus_amount_usd=200.0,
                bonus_amount_usdt=120.0,  # 60%
                bonus_amount_bnb=0.061,  # 40%
                bonus_description="Royal Captain Tier 3 - 5 direct, 50 team"
            ),
            RoyalCaptainBonus(
                bonus_tier=4,
                direct_partners_required=5,
                global_team_required=100,
                bonus_amount_usd=200.0,
                bonus_amount_usdt=120.0,  # 60%
                bonus_amount_bnb=0.061,  # 40%
                bonus_description="Royal Captain Tier 4 - 5 direct, 100 team"
            ),
            RoyalCaptainBonus(
                bonus_tier=5,
                direct_partners_required=5,
                global_team_required=200,
                bonus_amount_usd=250.0,
                bonus_amount_usdt=150.0,  # 60%
                bonus_amount_bnb=0.076,  # 40%
                bonus_description="Royal Captain Tier 5 - 5 direct, 200 team"
            ),
            RoyalCaptainBonus(
                bonus_tier=6,
                direct_partners_required=5,
                global_team_required=300,
                bonus_amount_usd=250.0,
                bonus_amount_usdt=150.0,  # 60%
                bonus_amount_bnb=0.076,  # 40%
                bonus_description="Royal Captain Tier 6 - 5 direct, 300 team"
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
