from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta
from ..user.model import User
from ..tree.model import TreePlacement
from .model import (
    Commission, CommissionDistribution,
    CommissionRule, CommissionAccumulation, CommissionPayment,
    DistributionReceipt
)
from ..missed_profit.model import MissedProfit
from utils import ensure_currency_for_program
from ..leadership_stipend.model import LeadershipStipend

class CommissionService:
    """Commission Management Business Logic Service"""
    
    # Commission percentages based on PROJECT_DOCUMENTATION.md
    JOINING_COMMISSION_PERCENTAGE = 10.0  # 10% commission on joining
    UPGRADE_COMMISSION_PERCENTAGE = 10.0  # 10% commission on upgrades
    LEVEL_COMMISSION_PERCENTAGE = 30.0    # 30% to corresponding level upline
    LEVEL_DISTRIBUTION_PERCENTAGE = 70.0  # 70% distributed across levels 1-16
    
    def __init__(self):
        pass
    
    def calculate_joining_commission(self, from_user_id: str, program: str, amount: Decimal, currency: str) -> Dict[str, Any]:
        """Calculate 10% joining commission for upline"""
        try:
            # Get user and upline
            from_user = User.objects(id=ObjectId(from_user_id)).first()
            if not from_user or not from_user.refered_by:
                return {"success": False, "error": "User or upline not found"}
            
            upline_id = from_user.refered_by
            
            # Calculate commission amount
            commission_amount = amount * Decimal(str(self.JOINING_COMMISSION_PERCENTAGE / 100))
            
            # Normalize currency per program
            currency = ensure_currency_for_program(program, currency)

            # Create commission record
            commission = Commission(
                user_id=upline_id,
                from_user_id=ObjectId(from_user_id),
                commission_type='joining',
                program=program,
                commission_amount=commission_amount,
                currency=currency,
                commission_percentage=self.JOINING_COMMISSION_PERCENTAGE,
                is_direct_commission=True,
                status='pending'
            )
            commission.save()
            # Receipt for joining commission
            try:
                DistributionReceipt(
                    user_id=upline_id,
                    from_user_id=ObjectId(from_user_id),
                    program=program,
                    source_type='joining',
                    source_slot_no=1,
                    source_slot_name='JOIN',
                    distribution_level=1,
                    amount=commission_amount,
                    currency=currency,
                    commission_id=commission.id,
                    event='joining_commission'
                ).save()
            except Exception:
                pass
            
            # Update accumulation
            self._update_commission_accumulation(upline_id, program, commission_amount, currency, 'joining')
            
            return {
                "success": True,
                "commission_id": str(commission.id),
                "commission_amount": float(commission_amount),
                "upline_id": str(upline_id),
                "message": "Joining commission calculated successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def calculate_upgrade_commission(self, from_user_id: str, program: str, slot_no: int, 
                                   slot_name: str, amount: Decimal, currency: str) -> Dict[str, Any]:
        """Calculate upgrade commission with 30% to corresponding level and 70% distribution"""
        try:
            # Get user
            from_user = User.objects(id=ObjectId(from_user_id)).first()
            if not from_user:
                return {"success": False, "error": "User not found"}
            
            # Calculate total commission amount
            total_commission = amount * Decimal(str(self.UPGRADE_COMMISSION_PERCENTAGE / 100))
            
            # 30% to corresponding level upline
            level_commission = total_commission * Decimal(str(self.LEVEL_COMMISSION_PERCENTAGE / 100))
            
            # 70% for distribution across levels 1-16
            distribution_amount = total_commission * Decimal(str(self.LEVEL_DISTRIBUTION_PERCENTAGE / 100))
            
            # Get corresponding level upline
            level_upline = self._get_level_upline(from_user_id, slot_no)
            
            # Normalize currency per program
            currency = ensure_currency_for_program(program, currency)

            # Create commission for level upline (30%)
            if level_upline:
                level_commission_record = Commission(
                    user_id=ObjectId(level_upline),
                    from_user_id=ObjectId(from_user_id),
                    commission_type='upgrade',
                    program=program,
                    commission_amount=level_commission,
                    currency=currency,
                    commission_percentage=self.LEVEL_COMMISSION_PERCENTAGE,
                    source_slot_no=slot_no,
                    source_slot_name=slot_name,
                    level=slot_no,
                    is_level_commission=True,
                    status='pending'
                )
                level_commission_record.save()
                
                # Update accumulation
                self._update_commission_accumulation(level_upline, program, level_commission, currency, 'upgrade')
                # Receipt for level commission (30%)
                try:
                    DistributionReceipt(
                        user_id=ObjectId(level_upline),
                        from_user_id=ObjectId(from_user_id),
                        program=program,
                        source_type='upgrade',
                        source_slot_no=slot_no,
                        source_slot_name=slot_name,
                        distribution_level=slot_no,
                        amount=level_commission,
                        currency=currency,
                        commission_id=level_commission_record.id,
                        event='upgrade_level_commission'
                    ).save()
                except Exception:
                    pass
            
            # Create distribution record for 70%
            distribution = CommissionDistribution(
                source_user_id=ObjectId(from_user_id),
                program=program,
                source_slot_no=slot_no,
                total_amount=total_commission,
                currency=currency,
                direct_commission_amount=level_commission,
                direct_commission_user_id=ObjectId(level_upline) if level_upline else None,
                direct_commission_level=slot_no,
                status='pending'
            )
            
            # Distribute across levels 1-16
            level_distributions = self._distribute_across_levels(from_user_id, distribution_amount, currency)
            distribution.level_distributions = level_distributions
            distribution.save()
            # Receipts for level distributions (70%)
            try:
                for ld in level_distributions:
                    DistributionReceipt(
                        user_id=ObjectId(ld['user_id']),
                        from_user_id=ObjectId(from_user_id),
                        program=program,
                        source_type='level',
                        source_slot_no=slot_no,
                        source_slot_name=slot_name,
                        distribution_level=int(ld['level']),
                        amount=Decimal(str(ld['amount'])),
                        currency=currency,
                        distribution_id=distribution.id,
                        event='level_distribution'
                    ).save()
            except Exception:
                pass
            
            return {
                "success": True,
                "total_commission": float(total_commission),
                "level_commission": float(level_commission),
                "distribution_amount": float(distribution_amount),
                "level_upline": level_upline,
                "distribution_id": str(distribution.id),
                "message": "Upgrade commission calculated and distributed"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def handle_missed_profit(self, user_id: str, from_user_id: str, program: str, 
                           slot_no: int, slot_name: str, amount: Decimal, 
                           currency: str, reason: str) -> Dict[str, Any]:
        """Handle missed profit due to inactivity or level advancement"""
        try:
            # Get user's current level
            user_level = self._get_user_current_level(user_id, program)
            required_level = slot_no
            
            # Create missed profit record
            missed_profit = MissedProfit(
                user_id=ObjectId(user_id),
                from_user_id=ObjectId(from_user_id),
                program=program,
                missed_amount=amount,
                currency=currency,
                slot_no=slot_no,
                slot_name=slot_name,
                missed_reason=reason,
                user_level=user_level,
                required_level=required_level,
                handling_status='pending'
            )
            missed_profit.save()
            
            # Automatically accumulate in Leadership Stipend
            stipend_result = self._accumulate_in_leadership_stipend(missed_profit)
            
            return {
                "success": True,
                "missed_profit_id": str(missed_profit.id),
                "missed_amount": float(amount),
                "reason": reason,
                "stipend_result": stipend_result,
                "message": "Missed profit handled and accumulated in Leadership Stipend"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def distribute_leadership_stipend(self, user_id: str, amount: Decimal, 
                                   currency: str, reason: str) -> Dict[str, Any]:
        """Distribute Leadership Stipend to eligible user"""
        try:
            # Check if user is eligible
            if not self._is_eligible_for_stipend(user_id):
                return {"success": False, "error": "User not eligible for Leadership Stipend"}
            
            # Get available stipend
            stipend = LeadershipStipend.objects(
                fund_type='missed_profits',
                currency=currency,
                status='active',
                available_amount__gte=amount
            ).first()
            
            if not stipend:
                return {"success": False, "error": "Insufficient stipend funds"}
            
            # Create distribution record
            distribution_record = {
                "user_id": str(user_id),
                "amount": float(amount),
                "reason": reason,
                "date": datetime.utcnow()
            }
            
            stipend.distributions.append(distribution_record)
            stipend.available_amount -= amount
            stipend.last_distribution_at = datetime.utcnow()
            stipend.save()
            
            return {
                "success": True,
                "stipend_id": str(stipend.id),
                "distributed_amount": float(amount),
                "remaining_amount": float(stipend.available_amount),
                "message": "Leadership Stipend distributed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_commission_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive commission summary for user"""
        try:
            # Get all commissions
            commissions = Commission.objects(user_id=ObjectId(user_id)).all()
            
            # Calculate totals
            total_earned = sum(comm.commission_amount for comm in commissions)
            total_paid = sum(comm.commission_amount for comm in commissions if comm.status == 'paid')
            total_missed = sum(comm.commission_amount for comm in commissions if comm.status == 'missed')
            
            # Get missed profits
            missed_profits = MissedProfit.objects(user_id=ObjectId(user_id)).all()
            total_missed_profits = sum(mp.missed_amount for mp in missed_profits)
            
            # Get program breakdown
            program_stats = {}
            for program in ['binary', 'matrix', 'global']:
                program_commissions = [c for c in commissions if c.program == program]
                program_stats[program] = {
                    "total_earned": float(sum(c.commission_amount for c in program_commissions)),
                    "total_paid": float(sum(c.commission_amount for c in program_commissions if c.status == 'paid')),
                    "count": len(program_commissions)
                }
            
            # Get commission type breakdown
            type_stats = {}
            for comm_type in ['joining', 'upgrade', 'level', 'bonus', 'stipend']:
                type_commissions = [c for c in commissions if c.commission_type == comm_type]
                type_stats[comm_type] = {
                    "total_earned": float(sum(c.commission_amount for c in type_commissions)),
                    "count": len(type_commissions)
                }
            
            return {
                "success": True,
                "data": {
                    "total_earned": float(total_earned),
                    "total_paid": float(total_paid),
                    "total_missed": float(total_missed),
                    "total_missed_profits": float(total_missed_profits),
                    "program_stats": program_stats,
                    "type_stats": type_stats,
                    "commission_count": len(commissions),
                    "missed_profit_count": len(missed_profits)
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_level_upline(self, user_id: str, level: int) -> Optional[str]:
        """Get upline at specific level"""
        try:
            current_user_id = user_id
            for i in range(level):
                user = User.objects(id=ObjectId(current_user_id)).first()
                if not user or not user.refered_by:
                    return None
                current_user_id = str(user.refered_by)
            
            return current_user_id
            
        except Exception:
            return None
    
    def _distribute_across_levels(self, from_user_id: str, amount: Decimal, currency: str) -> List[Dict]:
        """Distribute commission across levels 1-16"""
        level_distributions = []
        amount_per_level = amount / Decimal('16')
        
        for level in range(1, 17):
            # Get user at this level
            level_user = self._get_level_upline(from_user_id, level)
            
            if level_user:
                level_distributions.append({
                    "level": level,
                    "amount": float(amount_per_level),
                    "user_id": level_user
                })
        
        return level_distributions
    
    def _update_commission_accumulation(self, user_id: str, program: str, amount: Decimal, 
                                     currency: str, commission_type: str):
        """Update commission accumulation for user"""
        accumulation = CommissionAccumulation.objects(
            user_id=ObjectId(user_id),
            program=program
        ).first()
        
        if not accumulation:
            accumulation = CommissionAccumulation(
                user_id=ObjectId(user_id),
                program=program
            )
        
        accumulation.total_earned += amount
        accumulation.currency_totals[currency] += amount
        accumulation.commission_type_totals[commission_type] += amount
        accumulation.last_commission_at = datetime.utcnow()
        accumulation.save()
    
    def _get_user_current_level(self, user_id: str, program: str) -> int:
        """Get user's current level in program"""
        # This is simplified - in real implementation, you'd get from tree placement
        return 1
    
    def _accumulate_in_leadership_stipend(self, missed_profit: MissedProfit) -> Dict[str, Any]:
        """Accumulate missed profit in Leadership Stipend"""
        try:
            stipend = LeadershipStipend.objects(
                fund_type='missed_profits',
                program=missed_profit.program,
                currency=missed_profit.currency,
                status='active'
            ).first()
            
            if not stipend:
                stipend = LeadershipStipend(
                    fund_type='missed_profits',
                    program=missed_profit.program,
                    currency=missed_profit.currency,
                    total_amount=missed_profit.missed_amount,
                    available_amount=missed_profit.missed_amount
                )
            else:
                stipend.total_amount += missed_profit.missed_amount
                stipend.available_amount += missed_profit.missed_amount
            
            stipend.save()
            
            # Update missed profit
            missed_profit.handling_status = 'accumulated'
            missed_profit.accumulated_in_stipend = True
            missed_profit.stipend_distribution_id = stipend.id
            missed_profit.handled_at = datetime.utcnow()
            missed_profit.save()
            
            return {
                "success": True,
                "stipend_id": str(stipend.id),
                "accumulated_amount": float(missed_profit.missed_amount)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _is_eligible_for_stipend(self, user_id: str) -> bool:
        """Check if user is eligible for Leadership Stipend"""
        # This is simplified - in real implementation, you'd check:
        # - User has active slots 10-16
        # - User has achieved targets
        # - User is active
        return True
    
    def create_commission_rules(self):
        """Create default commission rules"""
        try:
            # Binary program rules
            binary_rules = [
                {
                    "program": "binary",
                    "commission_type": "joining",
                    "percentage": 10.0,
                    "currency": "BNB"
                },
                {
                    "program": "binary",
                    "commission_type": "upgrade",
                    "percentage": 10.0,
                    "currency": "BNB",
                    "level_commission_percentage": 30.0,
                    "level_distribution_percentage": 70.0
                }
            ]
            
            # Matrix program rules
            matrix_rules = [
                {
                    "program": "matrix",
                    "commission_type": "joining",
                    "percentage": 10.0,
                    "currency": "USDT"
                },
                {
                    "program": "matrix",
                    "commission_type": "upgrade",
                    "percentage": 10.0,
                    "currency": "USDT"
                }
            ]
            
            # Global program rules
            global_rules = [
                {
                    "program": "global",
                    "commission_type": "joining",
                    "percentage": 10.0,
                    "currency": "USD"
                },
                {
                    "program": "global",
                    "commission_type": "upgrade",
                    "percentage": 10.0,
                    "currency": "USD"
                }
            ]
            
            all_rules = binary_rules + matrix_rules + global_rules
            
            for rule_data in all_rules:
                existing_rule = CommissionRule.objects(
                    program=rule_data["program"],
                    commission_type=rule_data["commission_type"],
                    is_active=True
                ).first()
                
                if not existing_rule:
                    rule = CommissionRule(**rule_data)
                    rule.save()
            
            return {"success": True, "message": "Commission rules created successfully"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
