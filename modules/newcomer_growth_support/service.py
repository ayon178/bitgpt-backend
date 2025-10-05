#!/usr/bin/env python3
"""
Newcomer Growth Support Service
Implements 50/50 split distribution system with 30-day distribution cycle
"""

from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from bson import ObjectId

from modules.user.model import User
from modules.income.model import IncomeEvent
from modules.wallet.model import UserWallet
from modules.tree.model import TreePlacement

class NewcomerGrowthSupportService:
    """Service for handling Newcomer Growth Support with 50/50 split and 30-day distribution"""
    
    def __init__(self):
        self.instant_claim_percentage = Decimal('50.0')  # 50% instant claim
        self.upline_fund_percentage = Decimal('50.0')    # 50% to upline fund
        self.distribution_cycle_days = 30                # 30-day distribution cycle
    
    def process_newcomer_growth_support(self, user_id: str, total_amount: Decimal, 
                                       referrer_id: str = None, tx_hash: str = None) -> Dict[str, Any]:
        """Process newcomer growth support with 50/50 split"""
        try:
            if not tx_hash:
                tx_hash = f"NGS_{user_id}_{int(datetime.now().timestamp())}"
            
            # Calculate split amounts
            instant_amount = total_amount * (self.instant_claim_percentage / Decimal('100.0'))
            upline_fund_amount = total_amount * (self.upline_fund_percentage / Decimal('100.0'))
            
            distributions = []
            
            # Step 1: Process instant claim (50%)
            instant_result = self._process_instant_claim(user_id, instant_amount, tx_hash)
            if instant_result.get("success"):
                distributions.append(instant_result.get("distribution"))
            else:
                return {"success": False, "error": f"Instant claim failed: {instant_result.get('error')}"}
            
            # Step 2: Process upline fund (50%)
            if referrer_id:
                upline_result = self._process_upline_fund(referrer_id, user_id, upline_fund_amount, tx_hash)
                if upline_result.get("success"):
                    distributions.append(upline_result.get("distribution"))
                else:
                    return {"success": False, "error": f"Upline fund failed: {upline_result.get('error')}"}
            else:
                # If no referrer, send to mother account
                mother_result = self._process_mother_account_fund(user_id, upline_fund_amount, tx_hash)
                if mother_result.get("success"):
                    distributions.append(mother_result.get("distribution"))
            
            return {
                "success": True,
                "total_amount": total_amount,
                "instant_amount": instant_amount,
                "upline_fund_amount": upline_fund_amount,
                "distributions": distributions,
                "distribution_type": "newcomer_growth_support"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Newcomer growth support processing failed: {str(e)}"}
    
    def _process_instant_claim(self, user_id: str, amount: Decimal, tx_hash: str) -> Dict[str, Any]:
        """Process instant claim for the user"""
        try:
            # Create income event for instant claim
            income_event = IncomeEvent(
                user_id=ObjectId(user_id),
                source_user_id=ObjectId(user_id),
                program='matrix',
                slot_no=1,
                income_type='newcomer_growth_instant',
                amount=amount,
                percentage=self.instant_claim_percentage,
                tx_hash=tx_hash,
                status='completed',
                description="Newcomer Growth Support - Instant Claim (50%)",
                created_at=datetime.utcnow()
            )
            income_event.save()
            
            # Update user wallet
            wallet = UserWallet.objects(user_id=ObjectId(user_id), wallet_type='main').first()
            if not wallet:
                wallet = UserWallet(
                    user_id=ObjectId(user_id),
                    wallet_type='main',
                    balance=Decimal('0.0'),
                    currency='USDT'
                )
            
            wallet.balance += amount
            wallet.last_updated = datetime.utcnow()
            wallet.save()
            
            return {
                "success": True,
                "distribution": {
                    "income_type": "newcomer_growth_instant",
                    "amount": amount,
                    "percentage": self.instant_claim_percentage,
                    "recipient_id": user_id,
                    "status": "completed",
                    "description": "Instant claim (50%)"
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Instant claim processing failed: {str(e)}"}
    
    def _process_upline_fund(self, referrer_id: str, source_user_id: str, amount: Decimal, tx_hash: str) -> Dict[str, Any]:
        """Process upline fund for 30-day distribution"""
        try:
            # Create income event for upline fund
            income_event = IncomeEvent(
                user_id=ObjectId(referrer_id),
                source_user_id=ObjectId(source_user_id),
                program='matrix',
                slot_no=1,
                income_type='newcomer_growth_upline_fund',
                amount=amount,
                percentage=self.upline_fund_percentage,
                tx_hash=tx_hash,
                status='pending_distribution',
                description="Newcomer Growth Support - Upline Fund (50%)",
                created_at=datetime.utcnow(),
                distribution_date=datetime.utcnow() + timedelta(days=self.distribution_cycle_days)
            )
            income_event.save()
            
            return {
                "success": True,
                "distribution": {
                    "income_type": "newcomer_growth_upline_fund",
                    "amount": amount,
                    "percentage": self.upline_fund_percentage,
                    "recipient_id": referrer_id,
                    "status": "pending_distribution",
                    "description": "Upline fund (50%) - 30-day distribution",
                    "distribution_date": income_event.distribution_date
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Upline fund processing failed: {str(e)}"}
    
    def _process_mother_account_fund(self, source_user_id: str, amount: Decimal, tx_hash: str) -> Dict[str, Any]:
        """Process fund to mother account when no referrer"""
        try:
            # Use mother ID as fallback
            mother_id = "68dc17f08b174277bc40d19c"
            
            # Create income event for mother account
            income_event = IncomeEvent(
                user_id=ObjectId(mother_id),
                source_user_id=ObjectId(source_user_id),
                program='matrix',
                slot_no=1,
                income_type='newcomer_growth_mother_fund',
                amount=amount,
                percentage=self.upline_fund_percentage,
                tx_hash=tx_hash,
                status='completed',
                description="Newcomer Growth Support - Mother Account Fund (50%)",
                created_at=datetime.utcnow()
            )
            income_event.save()
            
            return {
                "success": True,
                "distribution": {
                    "income_type": "newcomer_growth_mother_fund",
                    "amount": amount,
                    "percentage": self.upline_fund_percentage,
                    "recipient_id": mother_id,
                    "status": "completed",
                    "description": "Mother account fund (50%)"
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"Mother account fund processing failed: {str(e)}"}
    
    def process_monthly_distribution(self, upline_id: str) -> Dict[str, Any]:
        """Process monthly distribution of upline fund among direct referrals"""
        try:
            # Get all pending upline funds for this user
            pending_funds = IncomeEvent.objects(
                user_id=ObjectId(upline_id),
                income_type='newcomer_growth_upline_fund',
                status='pending_distribution',
                distribution_date__lte=datetime.utcnow()
            )
            
            if not pending_funds:
                return {"success": True, "message": "No pending funds for distribution"}
            
            # Get all direct referrals of the upline
            direct_referrals = User.objects(refered_by=upline_id)
            
            if not direct_referrals:
                return {"success": True, "message": "No direct referrals found for distribution"}
            
            total_distributed = Decimal('0.0')
            distributions = []
            
            for fund in pending_funds:
                # Calculate equal distribution among direct referrals
                distribution_amount = fund.amount / len(direct_referrals)
                
                for referral in direct_referrals:
                    # Create distribution income event
                    dist_income_event = IncomeEvent(
                        user_id=ObjectId(referral.id),
                        source_user_id=ObjectId(upline_id),
                        program='matrix',
                        slot_no=1,
                        income_type='newcomer_growth_monthly_distribution',
                        amount=distribution_amount,
                        percentage=Decimal('100.0'),
                        tx_hash=f"NGS_MONTHLY_{upline_id}_{int(datetime.now().timestamp())}",
                        status='completed',
                        description=f"Newcomer Growth Support - Monthly Distribution from {upline_id}",
                        created_at=datetime.utcnow()
                    )
                    dist_income_event.save()
                    
                    # Update referral wallet
                    wallet = UserWallet.objects(user_id=ObjectId(referral.id), wallet_type='main').first()
                    if not wallet:
                        wallet = UserWallet(
                            user_id=ObjectId(referral.id),
                            wallet_type='main',
                            balance=Decimal('0.0'),
                            currency='USDT'
                        )
                    
                    wallet.balance += distribution_amount
                    wallet.last_updated = datetime.utcnow()
                    wallet.save()
                    
                    distributions.append({
                        "income_type": "newcomer_growth_monthly_distribution",
                        "amount": distribution_amount,
                        "recipient_id": str(referral.id),
                        "status": "completed",
                        "description": "Monthly distribution"
                    })
                    
                    total_distributed += distribution_amount
                
                # Mark fund as distributed
                fund.status = 'completed'
                fund.updated_at = datetime.utcnow()
                fund.save()
            
            return {
                "success": True,
                "total_distributed": total_distributed,
                "distributions": distributions,
                "direct_referrals_count": len(direct_referrals),
                "funds_processed": len(pending_funds)
            }
            
        except Exception as e:
            return {"success": False, "error": f"Monthly distribution processing failed: {str(e)}"}
    
    def get_newcomer_growth_status(self, user_id: str) -> Dict[str, Any]:
        """Get newcomer growth support status for a user"""
        try:
            # Get instant claims
            instant_claims = IncomeEvent.objects(
                user_id=ObjectId(user_id),
                income_type='newcomer_growth_instant'
            )
            
            # Get upline funds
            upline_funds = IncomeEvent.objects(
                user_id=ObjectId(user_id),
                income_type='newcomer_growth_upline_fund'
            )
            
            # Get monthly distributions received
            monthly_distributions = IncomeEvent.objects(
                user_id=ObjectId(user_id),
                income_type='newcomer_growth_monthly_distribution'
            )
            
            # Get monthly distributions given (as upline)
            monthly_distributions_given = IncomeEvent.objects(
                source_user_id=ObjectId(user_id),
                income_type='newcomer_growth_monthly_distribution'
            )
            
            # Calculate totals
            total_instant_claimed = sum([claim.amount for claim in instant_claims])
            total_upline_fund = sum([fund.amount for fund in upline_funds])
            total_monthly_received = sum([dist.amount for dist in monthly_distributions])
            total_monthly_given = sum([dist.amount for dist in monthly_distributions_given])
            
            # Get pending funds for distribution
            pending_funds = IncomeEvent.objects(
                user_id=ObjectId(user_id),
                income_type='newcomer_growth_upline_fund',
                status='pending_distribution'
            )
            
            pending_amount = sum([fund.amount for fund in pending_funds])
            
            return {
                "success": True,
                "user_id": user_id,
                "total_instant_claimed": total_instant_claimed,
                "total_upline_fund": total_upline_fund,
                "total_monthly_received": total_monthly_received,
                "total_monthly_given": total_monthly_given,
                "pending_distribution_amount": pending_amount,
                "instant_claims_count": len(instant_claims),
                "upline_funds_count": len(upline_funds),
                "monthly_distributions_received_count": len(monthly_distributions),
                "monthly_distributions_given_count": len(monthly_distributions_given),
                "pending_funds_count": len(pending_funds)
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get newcomer growth status: {str(e)}"}
    
    def get_direct_referrals_for_distribution(self, upline_id: str) -> Dict[str, Any]:
        """Get direct referrals eligible for monthly distribution"""
        try:
            direct_referrals = User.objects(refered_by=upline_id)
            
            referral_data = []
            for referral in direct_referrals:
                # Get their newcomer growth status
                status = self.get_newcomer_growth_status(str(referral.id))
                if status.get("success"):
                    referral_data.append({
                        "user_id": str(referral.id),
                        "name": referral.name,
                        "uid": referral.uid,
                        "total_instant_claimed": status.get("total_instant_claimed", 0),
                        "total_monthly_received": status.get("total_monthly_received", 0)
                    })
            
            return {
                "success": True,
                "upline_id": upline_id,
                "direct_referrals_count": len(direct_referrals),
                "referrals": referral_data
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get direct referrals: {str(e)}"}
    
    def trigger_monthly_distribution_for_all(self) -> Dict[str, Any]:
        """Trigger monthly distribution for all users with pending funds"""
        try:
            # Get all users with pending upline funds
            pending_funds = IncomeEvent.objects(
                income_type='newcomer_growth_upline_fund',
                status='pending_distribution',
                distribution_date__lte=datetime.utcnow()
            )
            
            if not pending_funds:
                return {"success": True, "message": "No pending funds for distribution"}
            
            # Group by upline
            upline_funds = {}
            for fund in pending_funds:
                upline_id = str(fund.user_id)
                if upline_id not in upline_funds:
                    upline_funds[upline_id] = []
                upline_funds[upline_id].append(fund)
            
            total_distributed = Decimal('0.0')
            processed_uplines = 0
            
            for upline_id, funds in upline_funds.items():
                result = self.process_monthly_distribution(upline_id)
                if result.get("success"):
                    total_distributed += result.get("total_distributed", 0)
                    processed_uplines += 1
            
            return {
                "success": True,
                "total_distributed": total_distributed,
                "processed_uplines": processed_uplines,
                "total_uplines_with_pending_funds": len(upline_funds)
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to trigger monthly distribution: {str(e)}"}
    
    def validate_newcomer_growth_support(self, total_amount: Decimal) -> Dict[str, Any]:
        """Validate newcomer growth support percentages"""
        try:
            instant_amount = total_amount * (self.instant_claim_percentage / Decimal('100.0'))
            upline_fund_amount = total_amount * (self.upline_fund_percentage / Decimal('100.0'))
            
            total_split = instant_amount + upline_fund_amount
            is_valid = abs(total_split - total_amount) < Decimal('0.01')  # Allow small rounding differences
            
            return {
                "success": True,
                "total_amount": total_amount,
                "instant_amount": instant_amount,
                "upline_fund_amount": upline_fund_amount,
                "total_split": total_split,
                "is_valid": is_valid,
                "instant_percentage": float(self.instant_claim_percentage),
                "upline_fund_percentage": float(self.upline_fund_percentage),
                "validation_message": "Valid 50/50 split" if is_valid else f"Split should be 100%, got {float(total_split)}"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Validation failed: {str(e)}"}
