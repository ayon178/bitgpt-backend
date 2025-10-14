#!/usr/bin/env python3
"""
Complete Fund Distribution Percentages Implementation
This service implements all fund distribution percentages for Binary, Matrix, and Global programs
"""

from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Any, Optional
from bson import ObjectId

from modules.user.model import User
from modules.income.model import IncomeEvent
from modules.wallet.model import UserWallet, ReserveLedger
from modules.tree.model import TreePlacement

class FundDistributionService:
    """Service for handling complete fund distribution percentages across all programs"""
    
    def __init__(self):
        # Use income_type values that match IncomeEvent model choices
        self.binary_percentages = {
            "spark_bonus": Decimal('8.0'),
            "royal_captain": Decimal('4.0'),  # Changed from royal_captain_bonus
            "president_reward": Decimal('3.0'),
            "leadership_stipend": Decimal('5.0'),
            "jackpot": Decimal('5.0'),  # Changed from jackpot_entry
            "partner_incentive": Decimal('10.0'),
            "shareholders": Decimal('5.0'),  # Changed from share_holders
            "level_distribution": Decimal('60.0')
        }
        
        self.matrix_percentages = {
            "spark_bonus": Decimal('8.0'),
            "royal_captain": Decimal('4.0'),  # Changed from royal_captain_bonus
            "president_reward": Decimal('3.0'),
            "newcomer_support": Decimal('20.0'),  # Changed from newcomer_growth_support
            "mentorship": Decimal('10.0'),  # Changed from mentorship_bonus
            "partner_incentive": Decimal('10.0'),
            "shareholders": Decimal('5.0'),  # Changed from share_holders
            "level_distribution": Decimal('40.0')
        }
        
        self.global_percentages = {
            "global_phase_1": Decimal('30.0'),  # Tree upline reserve
            "global_phase_2": Decimal('30.0'),  # Tree upline wallet
            "partner_incentive": Decimal('10.0'),
            "royal_captain": Decimal('10.0'),  # Changed from royal_captain_bonus
            "president_reward": Decimal('10.0'),
            "shareholders": Decimal('5.0'),  # Changed from share_holders
            "triple_entry": Decimal('5.0')  # Handled separately via SparkService, not BonusFund
        }
        
        # Binary level distribution breakdown (60% treated as 100%)
        self.binary_level_breakdown = {
            1: Decimal('30.0'),   # Level 1: 30%
            2: Decimal('10.0'),   # Level 2: 10%
            3: Decimal('10.0'),    # Level 3: 10%
            4: Decimal('5.0'),    # Level 4: 5%
            5: Decimal('5.0'),    # Level 5: 5%
            6: Decimal('5.0'),    # Level 6: 5%
            7: Decimal('5.0'),    # Level 7: 5%
            8: Decimal('5.0'),    # Level 8: 5%
            9: Decimal('5.0'),    # Level 9: 5%
            10: Decimal('5.0'),   # Level 10: 5%
            11: Decimal('3.0'),   # Level 11: 3%
            12: Decimal('3.0'),   # Level 12: 3%
            13: Decimal('3.0'),   # Level 13: 3%
            14: Decimal('2.0'),   # Level 14: 2%
            15: Decimal('2.0'),   # Level 15: 2%
            16: Decimal('2.0')    # Level 16: 2%
        }
        
        # Matrix level distribution breakdown (40% treated as 100%)
        self.matrix_level_breakdown = {
            1: Decimal('20.0'),   # Level 1: 20%
            2: Decimal('20.0'),   # Level 2: 20%
            3: Decimal('60.0')    # Level 3: 60%
        }

    def distribute_binary_funds(self, user_id: str, amount: Decimal, slot_no: int, 
                               referrer_id: str = None, tx_hash: str = None, currency: str = 'BNB') -> Dict[str, Any]:
        """Distribute Binary program funds according to percentages"""
        try:
            if not tx_hash:
                tx_hash = f"BINARY_DIST_{user_id}_{int(datetime.now().timestamp())}"
            
            distributions = []
            total_distributed = Decimal('0.0')
            
            # Calculate each distribution
            for income_type, percentage in self.binary_percentages.items():
                if income_type == "level_distribution":
                    # Handle level distribution separately
                    level_distributions = self._distribute_binary_levels(
                        user_id, amount, percentage, slot_no, tx_hash, currency
                    )
                    distributions.extend(level_distributions)
                    total_distributed += amount * (percentage / Decimal('100.0'))
                elif income_type == "partner_incentive":
                    # Handle partner incentive separately (goes to referrer, not user)
                    if referrer_id:
                        dist_amount = amount * (percentage / Decimal('100.0'))
                        if dist_amount > 0:
                            distribution = self._create_income_event(
                                referrer_id, user_id, 'binary', slot_no, income_type,
                                dist_amount, percentage, tx_hash, "Binary Partner Incentive", currency
                            )
                            distributions.append(distribution)
                            total_distributed += dist_amount
                else:
                    # Direct distribution to fund pools
                    dist_amount = amount * (percentage / Decimal('100.0'))
                    if dist_amount > 0:
                        distribution = self._create_income_event(
                            user_id, user_id, 'binary', slot_no, income_type,
                            dist_amount, percentage, tx_hash, f"Binary {income_type.replace('_', ' ').title()}", currency
                        )
                        distributions.append(distribution)
                        total_distributed += dist_amount
            
            return {
                "success": True,
                "total_amount": amount,
                "total_distributed": total_distributed,
                "distributions": distributions,
                "distribution_type": "binary"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Binary fund distribution failed: {str(e)}"}

    def distribute_matrix_funds(self, user_id: str, amount: Decimal, slot_no: int,
                              referrer_id: str = None, tx_hash: str = None, currency: str = 'USDT') -> Dict[str, Any]:
        """Distribute Matrix program funds according to percentages"""
        try:
            if not tx_hash:
                tx_hash = f"MATRIX_DIST_{user_id}_{int(datetime.now().timestamp())}"
            
            distributions = []
            total_distributed = Decimal('0.0')
            
            # Calculate each distribution
            for income_type, percentage in self.matrix_percentages.items():
                if income_type == "level_distribution":
                    # Handle level distribution separately
                    level_distributions = self._distribute_matrix_levels(
                        user_id, amount, percentage, slot_no, tx_hash, currency
                    )
                    distributions.extend(level_distributions)
                    total_distributed += amount * (percentage / Decimal('100.0'))
                elif income_type == "partner_incentive":
                    # Handle partner incentive separately (goes to referrer, not user)
                    if referrer_id:
                        dist_amount = amount * (percentage / Decimal('100.0'))
                        if dist_amount > 0:
                            distribution = self._create_income_event(
                                referrer_id, user_id, 'matrix', slot_no, income_type,
                                dist_amount, percentage, tx_hash, "Matrix Partner Incentive", currency
                            )
                            distributions.append(distribution)
                            total_distributed += dist_amount
                else:
                    # Direct distribution to fund pools
                    dist_amount = amount * (percentage / Decimal('100.0'))
                    if dist_amount > 0:
                        distribution = self._create_income_event(
                            user_id, user_id, 'matrix', slot_no, income_type,
                            dist_amount, percentage, tx_hash, f"Matrix {income_type.replace('_', ' ').title()}", currency
                        )
                        distributions.append(distribution)
                        total_distributed += dist_amount
            
            return {
                "success": True,
                "total_amount": amount,
                "total_distributed": total_distributed,
                "distributions": distributions,
                "distribution_type": "matrix"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Matrix fund distribution failed: {str(e)}"}

    def distribute_global_funds(self, user_id: str, amount: Decimal, slot_no: int,
                               referrer_id: str = None, tx_hash: str = None) -> Dict[str, Any]:
        """Distribute Global program funds according to percentages"""
        try:
            if not tx_hash:
                tx_hash = f"GLOBAL_DIST_{user_id}_{int(datetime.now().timestamp())}"
            
            distributions = []
            total_distributed = Decimal('0.0')
            
            # Calculate each distribution
            for income_type, percentage in self.global_percentages.items():
                dist_amount = amount * (percentage / Decimal('100.0'))
                if dist_amount > 0:
                    distribution = self._create_income_event(
                        user_id, user_id, 'global', slot_no, income_type,
                        dist_amount, percentage, tx_hash, f"Global {income_type.replace('_', ' ').title()}"
                    )
                    distributions.append(distribution)
                    total_distributed += dist_amount
            
            # Handle partner incentive separately if referrer provided
            if referrer_id and "partner_incentive" in self.global_percentages:
                pi_amount = amount * (self.global_percentages["partner_incentive"] / Decimal('100.0'))
                if pi_amount > 0:
                    pi_distribution = self._create_income_event(
                        referrer_id, user_id, 'global', slot_no, 'partner_incentive',
                        pi_amount, self.global_percentages["partner_incentive"], 
                        tx_hash, "Global Partner Incentive"
                    )
                    distributions.append(pi_distribution)
            
            return {
                "success": True,
                "total_amount": amount,
                "total_distributed": total_distributed,
                "distributions": distributions,
                "distribution_type": "global"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Global fund distribution failed: {str(e)}"}

    def _distribute_binary_levels(self, user_id: str, amount: Decimal, percentage: Decimal,
                                 slot_no: int, tx_hash: str, currency: str = 'BNB') -> List[Dict[str, Any]]:
        """Distribute Binary level distribution (60% treated as 100%)"""
        distributions = []
        level_amount = amount * (percentage / Decimal('100.0'))
        
        # Get user's tree placement for this slot
        user_placement = TreePlacement.objects(user_id=ObjectId(user_id), program='binary', slot_no=slot_no, is_active=True).first()
        if not user_placement:
            return distributions
        
        # Distribute to each level according to breakdown
        for level, level_percentage in self.binary_level_breakdown.items():
            level_dist_amount = level_amount * (level_percentage / Decimal('100.0'))
            if level_dist_amount > 0:
                # Find upline at this level
                upline_id = self._find_upline_at_level(user_id, level, 'binary', slot_no)
                if upline_id:
                    distribution = self._create_income_event(
                        upline_id, user_id, 'binary', slot_no, f'level_{level}_distribution',
                        level_dist_amount, level_percentage, tx_hash, f"Binary Level {level} Distribution", currency
                    )
                    distributions.append(distribution)
        
        return distributions

    def _distribute_matrix_levels(self, user_id: str, amount: Decimal, percentage: Decimal,
                                 slot_no: int, tx_hash: str) -> List[Dict[str, Any]]:
        """Distribute Matrix level distribution (40% treated as 100%)"""
        distributions = []
        level_amount = amount * (percentage / Decimal('100.0'))
        
        # Get user's tree upline for level distribution
        user_placement = TreePlacement.objects(user_id=ObjectId(user_id), program='matrix', is_active=True).first()
        if not user_placement:
            return distributions
        
        # Distribute to each level according to breakdown
        for level, level_percentage in self.matrix_level_breakdown.items():
            level_dist_amount = level_amount * (level_percentage / Decimal('100.0'))
            if level_dist_amount > 0:
                # Find upline at this level
                upline_id = self._find_upline_at_level(user_id, level, 'matrix')
                if upline_id:
                    distribution = self._create_income_event(
                        upline_id, user_id, 'matrix', slot_no, f'level_{level}_distribution',
                        level_dist_amount, level_percentage, tx_hash, f"Matrix Level {level} Distribution"
                    )
                    distributions.append(distribution)
        
        return distributions

    def _find_upline_at_level(self, user_id: str, target_level: int, program: str, slot_no: int) -> Optional[str]:
        """Find upline at specific level for level distribution by traversing parent chain for the given slot."""
        try:
            # Start from the user's placement for this program+slot
            user_placement = TreePlacement.objects(user_id=ObjectId(user_id), program=program, slot_no=slot_no, is_active=True).first()
            if not user_placement:
                return None

            # Traverse up via parent_id pointers
            steps = 0
            curr = user_placement
            while steps < target_level and curr and getattr(curr, 'parent_id', None):
                parent_id = curr.parent_id
                # Fetch parent's placement for the same slot
                curr = TreePlacement.objects(user_id=parent_id, program=program, slot_no=slot_no, is_active=True).first()
                steps += 1

            if steps == target_level and curr:
                return str(curr.user_id)

            return None
            
        except Exception as e:
            print(f"Error finding upline at level {target_level}: {e}")
            return None

    def _map_income_type_to_fund_type(self, income_type: str) -> str:
        """Map income_type to BonusFund fund_type"""
        mapping = {
            'spark_bonus': 'spark_bonus',
            'royal_captain': 'royal_captain',
            'president_reward': 'president_reward',
            'leadership_stipend': 'leadership_stipend',
            'jackpot': 'jackpot_entry',
            'partner_incentive': 'partner_incentive',
            'shareholders': 'shareholders',
            'newcomer_support': 'newcomer_support',
            'mentorship': 'mentorship_bonus',
            'triple_entry': 'triple_entry',
            'global_phase_1': None,  # Handled separately (tree upline reserve)
            'global_phase_2': None   # Handled separately (tree upline wallet)
        }
        return mapping.get(income_type)
    
    def _create_income_event(self, recipient_id: str, source_id: str, program: str, 
                           slot_no: int, income_type: str, amount: Decimal, 
                           percentage: Decimal, tx_hash: str, description: str, currency: str = 'USDT') -> Dict[str, Any]:
        """Create income event for distribution AND update BonusFund AND credit wallet"""
        try:
            # 1. Create IncomeEvent (for tracking/history)
            income_event = IncomeEvent(
                user_id=ObjectId(recipient_id),
                source_user_id=ObjectId(source_id),
                program=program,
                slot_no=slot_no,
                income_type=income_type,
                amount=amount,
                percentage=percentage,
                tx_hash=tx_hash,
                status='completed',
                description=description,
                created_at=datetime.utcnow()
            )
            income_event.save()
            
            # 2. Update BonusFund (for actual fund balance)
            fund_type = self._map_income_type_to_fund_type(income_type)
            fund_updated = False
            
            # Skip level distribution (level_1_distribution, level_2_distribution, etc.)
            is_level_dist = 'level_' in income_type and '_distribution' in income_type
            
            # Partner incentive and level distributions should credit wallet
            should_credit_wallet = (income_type == 'partner_incentive' or is_level_dist)
            
            # Debug logging
            if not fund_type:
                print(f"⚠️ No mapping for income_type: {income_type}")
            elif is_level_dist:
                pass  # Don't log level dist skips
            
            if fund_type and not is_level_dist:
                try:
                    from modules.income.bonus_fund import BonusFund
                    
                    # Get or create BonusFund
                    bonus_fund = BonusFund.objects(
                        fund_type=fund_type,
                        program=program,
                        status='active'
                    ).first()
                    
                    if not bonus_fund:
                        print(f"Creating new BonusFund: {fund_type}_{program}")
                        bonus_fund = BonusFund(
                            fund_type=fund_type,
                            program=program,
                            total_collected=Decimal('0'),
                            total_distributed=Decimal('0'),
                            current_balance=Decimal('0'),
                            status='active'
                        )
                    
                    # Update fund balances
                    bonus_fund.total_collected += amount
                    bonus_fund.current_balance += amount
                    bonus_fund.updated_at = datetime.utcnow()
                    bonus_fund.save()
                    fund_updated = True
                    print(f"✅ Updated {fund_type}_{program}: +${amount} → ${bonus_fund.current_balance}")
                    
                except Exception as e:
                    print(f"❌ Failed to update BonusFund for {income_type} → {fund_type}: {e}")
            
            # 3. Credit wallet for partner_incentive and level distributions
            wallet_credited = False
            if should_credit_wallet and amount > 0:
                try:
                    from modules.wallet.service import WalletService
                    
                    # Create a proper reason for WalletLedger
                    if income_type == 'partner_incentive':
                        wallet_reason = f"{program}_partner_incentive"
                    elif is_level_dist:
                        # Extract level number from income_type (e.g., 'level_1_distribution' -> 'level_1')
                        level_part = income_type.replace('_distribution', '')
                        wallet_reason = f"{program}_dual_tree_{level_part}"
                    else:
                        wallet_reason = f"{program}_{income_type}"
                    
                    wallet_service = WalletService()
                    credit_result = wallet_service.credit_main_wallet(
                        user_id=recipient_id,
                        amount=amount,
                        currency=currency,
                        reason=wallet_reason,
                        tx_hash=tx_hash
                    )
                    
                    if credit_result.get("success"):
                        wallet_credited = True
                        print(f"✅ Credited wallet for {recipient_id}: +{amount} {currency} ({wallet_reason})")
                    else:
                        print(f"⚠️ Wallet credit failed for {recipient_id}: {credit_result.get('error')}")
                        
                except Exception as e:
                    print(f"❌ Failed to credit wallet for {income_type}: {e}")
            
            return {
                "income_type": income_type,
                "amount": amount,
                "percentage": percentage,
                "recipient_id": recipient_id,
                "status": "completed",
                "description": description,
                "bonus_fund_updated": fund_updated,
                "wallet_credited": wallet_credited
            }
            
        except Exception as e:
            return {
                "income_type": income_type,
                "amount": amount,
                "percentage": percentage,
                "recipient_id": recipient_id,
                "status": "failed",
                "error": str(e)
            }

    def get_distribution_summary(self, program: str) -> Dict[str, Any]:
        """Get distribution summary for a program"""
        try:
            if program == 'binary':
                percentages = self.binary_percentages
                level_breakdown = self.binary_level_breakdown
            elif program == 'matrix':
                percentages = self.matrix_percentages
                level_breakdown = self.matrix_level_breakdown
            elif program == 'global':
                percentages = self.global_percentages
                level_breakdown = {}
            else:
                return {"success": False, "error": "Invalid program"}
            
            return {
                "success": True,
                "program": program,
                "percentages": {k: float(v) for k, v in percentages.items()},
                "level_breakdown": {k: float(v) for k, v in level_breakdown.items()},
                "total_percentage": float(sum(percentages.values()))
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to get distribution summary: {str(e)}"}

    def validate_distribution_percentages(self, program: str) -> Dict[str, Any]:
        """Validate that all percentages add up to 100%"""
        try:
            if program == 'binary':
                percentages = self.binary_percentages
            elif program == 'matrix':
                percentages = self.matrix_percentages
            elif program == 'global':
                percentages = self.global_percentages
            else:
                return {"success": False, "error": "Invalid program"}
            
            total = sum(percentages.values())
            is_valid = total == Decimal('100.0')
            
            return {
                "success": True,
                "program": program,
                "total_percentage": float(total),
                "is_valid": is_valid,
                "validation_message": "Valid" if is_valid else f"Total should be 100%, got {float(total)}%"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Validation failed: {str(e)}"}
