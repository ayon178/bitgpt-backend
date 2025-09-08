from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta
from ..user.model import User
from ..slot.model import SlotActivation
from ..tree.model import TreePlacement
from .model import (
    MissedProfit, MissedProfitAccumulation, MissedProfitDistribution,
    MissedProfitFund, MissedProfitSettings, MissedProfitLog, 
    MissedProfitStatistics, MissedProfitRecovery, MissedProfitReason
)

class MissedProfitService:
    """Missed Profit Handling Business Logic Service"""
    
    def __init__(self):
        pass
    
    def create_missed_profit(self, user_id: str, upline_user_id: str, missed_profit_type: str, 
                           missed_profit_amount: float, primary_reason: str, reason_description: str,
                           user_level: int, upgrade_slot_level: int, program_type: str, 
                           currency: str = "BNB") -> Dict[str, Any]:
        """Create missed profit record"""
        try:
            # Validate users exist
            user = User.objects(id=ObjectId(user_id)).first()
            upline_user = User.objects(id=ObjectId(upline_user_id)).first()
            
            if not user or not upline_user:
                return {"success": False, "error": "User or upline not found"}
            
            # Validate parameters
            if missed_profit_type not in ['commission', 'bonus', 'upgrade_reward']:
                return {"success": False, "error": "Invalid missed profit type"}
            
            if primary_reason not in ['account_inactivity', 'level_advancement']:
                return {"success": False, "error": "Invalid primary reason"}
            
            if program_type not in ['binary', 'matrix', 'global']:
                return {"success": False, "error": "Invalid program type"}
            
            # Create missed profit record
            missed_profit = MissedProfit(
                user_id=ObjectId(user_id),
                upline_user_id=ObjectId(upline_user_id),
                missed_profit_type=missed_profit_type,
                missed_profit_amount=missed_profit_amount,
                currency=currency,
                primary_reason=primary_reason,
                reason_description=reason_description,
                user_level=user_level,
                upgrade_slot_level=upgrade_slot_level,
                program_type=program_type
            )
            
            # Add reason details
            reason = MissedProfitReason(
                reason_type=primary_reason,
                reason_description=reason_description,
                user_level=user_level,
                upgrade_slot_level=upgrade_slot_level,
                commission_amount=missed_profit_amount,
                currency=currency
            )
            missed_profit.reasons.append(reason)
            
            missed_profit.save()
            
            # Log the action
            self._log_action(user_id, "missed_profit_created", 
                           f"Created missed profit: ${missed_profit_amount} due to {primary_reason}")
            
            return {
                "success": True,
                "missed_profit_id": str(missed_profit.id),
                "user_id": user_id,
                "upline_user_id": upline_user_id,
                "missed_profit_type": missed_profit_type,
                "missed_profit_amount": missed_profit_amount,
                "currency": currency,
                "primary_reason": primary_reason,
                "reason_description": reason_description,
                "user_level": user_level,
                "upgrade_slot_level": upgrade_slot_level,
                "program_type": program_type,
                "recovery_status": "pending",
                "message": f"Missed profit record created: ${missed_profit_amount}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def accumulate_missed_profits(self, period: str, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """Accumulate missed profits for a period"""
        try:
            # Get missed profits for the period
            missed_profits = MissedProfit.objects(
                created_at__gte=period_start,
                created_at__lt=period_end,
                is_accumulated=False
            )
            
            # Calculate totals
            total_amount = 0.0
            total_amount_bnb = 0.0
            total_amount_usdt = 0.0
            
            account_inactivity_count = 0
            account_inactivity_amount = 0.0
            level_advancement_count = 0
            level_advancement_amount = 0.0
            
            binary_count = 0
            binary_amount = 0.0
            matrix_count = 0
            matrix_amount = 0.0
            global_count = 0
            global_amount = 0.0
            
            for missed_profit in missed_profits:
                total_amount += missed_profit.missed_profit_amount
                
                if missed_profit.currency == 'BNB':
                    total_amount_bnb += missed_profit.missed_profit_amount
                else:
                    total_amount_usdt += missed_profit.missed_profit_amount
                
                if missed_profit.primary_reason == 'account_inactivity':
                    account_inactivity_count += 1
                    account_inactivity_amount += missed_profit.missed_profit_amount
                else:
                    level_advancement_count += 1
                    level_advancement_amount += missed_profit.missed_profit_amount
                
                if missed_profit.program_type == 'binary':
                    binary_count += 1
                    binary_amount += missed_profit.missed_profit_amount
                elif missed_profit.program_type == 'matrix':
                    matrix_count += 1
                    matrix_amount += missed_profit.missed_profit_amount
                else:
                    global_count += 1
                    global_amount += missed_profit.missed_profit_amount
                
                # Mark as accumulated
                missed_profit.is_accumulated = True
                missed_profit.accumulated_at = datetime.utcnow()
                missed_profit.save()
            
            # Create accumulation record
            accumulation = MissedProfitAccumulation(
                accumulation_period=period,
                period_start=period_start,
                period_end=period_end,
                total_missed_profits=total_amount,
                total_missed_profits_bnb=total_amount_bnb,
                total_missed_profits_usdt=total_amount_usdt,
                account_inactivity_count=account_inactivity_count,
                account_inactivity_amount=account_inactivity_amount,
                level_advancement_count=level_advancement_count,
                level_advancement_amount=level_advancement_amount,
                binary_missed_count=binary_count,
                binary_missed_amount=binary_amount,
                matrix_missed_count=matrix_count,
                matrix_missed_amount=matrix_amount,
                global_missed_count=global_count,
                global_missed_amount=global_amount,
                is_processed=True,
                processed_at=datetime.utcnow()
            )
            accumulation.save()
            
            # Log the action
            self._log_action("system", "missed_profit_accumulated", 
                           f"Accumulated missed profits: ${total_amount} for {period}")
            
            return {
                "success": True,
                "accumulation_id": str(accumulation.id),
                "period": period,
                "period_start": period_start,
                "period_end": period_end,
                "total_missed_profits": total_amount,
                "total_missed_profits_bnb": total_amount_bnb,
                "total_missed_profits_usdt": total_amount_usdt,
                "account_inactivity": {
                    "count": account_inactivity_count,
                    "amount": account_inactivity_amount
                },
                "level_advancement": {
                    "count": level_advancement_count,
                    "amount": level_advancement_amount
                },
                "program_breakdown": {
                    "binary": {"count": binary_count, "amount": binary_amount},
                    "matrix": {"count": matrix_count, "amount": matrix_amount},
                    "global": {"count": global_count, "amount": global_amount}
                },
                "processed_missed_profits": len(missed_profits),
                "message": f"Missed profits accumulated: ${total_amount}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def distribute_missed_profits(self, distribution_period: str, period_start: datetime, 
                                period_end: datetime, distribution_method: str = "leadership_stipend") -> Dict[str, Any]:
        """Distribute missed profits via Leadership Stipend"""
        try:
            # Get accumulated missed profits for the period
            accumulations = MissedProfitAccumulation.objects(
                period_start__gte=period_start,
                period_end__lte=period_end,
                is_processed=True
            )
            
            total_distributed_amount = 0.0
            total_distributed_amount_bnb = 0.0
            total_distributed_amount_usdt = 0.0
            
            for accumulation in accumulations:
                total_distributed_amount += accumulation.total_missed_profits
                total_distributed_amount_bnb += accumulation.total_missed_profits_bnb
                total_distributed_amount_usdt += accumulation.total_missed_profits_usdt
            
            # Get eligible recipients (users with Leadership Stipend eligibility)
            eligible_recipients = self._get_eligible_leadership_stipend_recipients()
            
            if not eligible_recipients:
                return {"success": False, "error": "No eligible recipients found for Leadership Stipend distribution"}
            
            # Distribute to Leadership Stipend fund
            fund = MissedProfitFund.objects(is_active=True).first()
            if not fund:
                fund = MissedProfitFund()
            
            fund.total_fund_amount += total_distributed_amount
            fund.available_amount += total_distributed_amount
            fund.total_missed_profits_accumulated += len(accumulations)
            
            # Update fund sources
            fund.fund_sources['missed_commissions'] += total_distributed_amount
            fund.last_updated = datetime.utcnow()
            fund.save()
            
            # Create distribution record
            distribution = MissedProfitDistribution(
                distribution_period=distribution_period,
                period_start=period_start,
                period_end=period_end,
                total_distributed_amount=total_distributed_amount,
                total_distributed_amount_bnb=total_distributed_amount_bnb,
                total_distributed_amount_usdt=total_distributed_amount_usdt,
                total_recipients=len(eligible_recipients),
                recipients=eligible_recipients,
                leadership_stipend_distributions=len(eligible_recipients),
                leadership_stipend_amount=total_distributed_amount,
                is_processed=True,
                processed_at=datetime.utcnow()
            )
            distribution.save()
            
            # Log the action
            self._log_action("system", "missed_profit_distributed", 
                           f"Distributed missed profits: ${total_distributed_amount} to {len(eligible_recipients)} recipients")
            
            return {
                "success": True,
                "distribution_id": str(distribution.id),
                "distribution_period": distribution_period,
                "period_start": period_start,
                "period_end": period_end,
                "total_distributed_amount": total_distributed_amount,
                "total_distributed_amount_bnb": total_distributed_amount_bnb,
                "total_distributed_amount_usdt": total_distributed_amount_usdt,
                "total_recipients": len(eligible_recipients),
                "distribution_method": distribution_method,
                "leadership_stipend_amount": total_distributed_amount,
                "message": f"Missed profits distributed: ${total_distributed_amount}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def attempt_recovery(self, missed_profit_id: str, recovery_method: str, recovery_amount: float) -> Dict[str, Any]:
        """Attempt to recover missed profit"""
        try:
            # Get missed profit record
            missed_profit = MissedProfit.objects(id=ObjectId(missed_profit_id)).first()
            if not missed_profit:
                return {"success": False, "error": "Missed profit record not found"}
            
            if missed_profit.recovery_status != "pending":
                return {"success": False, "error": "Recovery already processed"}
            
            # Create recovery record
            recovery = MissedProfitRecovery(
                missed_profit_id=ObjectId(missed_profit_id),
                user_id=missed_profit.user_id,
                upline_user_id=missed_profit.upline_user_id,
                recovery_type="manual",
                recovery_method=recovery_method,
                recovery_amount=recovery_amount,
                currency=missed_profit.currency,
                recovery_status="processing"
            )
            recovery.save()
            
            # Update missed profit record
            missed_profit.recovery_status = "processing"
            missed_profit.recovery_amount = recovery_amount
            missed_profit.last_updated = datetime.utcnow()
            missed_profit.save()
            
            # Log the action
            self._log_action(str(missed_profit.user_id), "recovery_attempted", 
                           f"Recovery attempted: ${recovery_amount} via {recovery_method}")
            
            return {
                "success": True,
                "recovery_id": str(recovery.id),
                "missed_profit_id": missed_profit_id,
                "user_id": str(missed_profit.user_id),
                "upline_user_id": str(missed_profit.upline_user_id),
                "recovery_method": recovery_method,
                "recovery_amount": recovery_amount,
                "currency": missed_profit.currency,
                "recovery_status": "processing",
                "message": f"Recovery attempt initiated: ${recovery_amount}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_missed_profit_statistics(self, period: str = "all_time") -> Dict[str, Any]:
        """Get Missed Profit program statistics"""
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
            missed_profits = MissedProfit.objects(
                created_at__gte=start_date,
                created_at__lt=end_date
            )
            
            total_missed_profits = missed_profits.count()
            total_missed_amount = sum(mp.missed_profit_amount for mp in missed_profits)
            
            # Reason breakdown
            account_inactivity_count = missed_profits.filter(primary_reason="account_inactivity").count()
            account_inactivity_amount = sum(mp.missed_profit_amount for mp in missed_profits.filter(primary_reason="account_inactivity"))
            level_advancement_count = missed_profits.filter(primary_reason="level_advancement").count()
            level_advancement_amount = sum(mp.missed_profit_amount for mp in missed_profits.filter(primary_reason="level_advancement"))
            
            # Program breakdown
            binary_count = missed_profits.filter(program_type="binary").count()
            binary_amount = sum(mp.missed_profit_amount for mp in missed_profits.filter(program_type="binary"))
            matrix_count = missed_profits.filter(program_type="matrix").count()
            matrix_amount = sum(mp.missed_profit_amount for mp in missed_profits.filter(program_type="matrix"))
            global_count = missed_profits.filter(program_type="global").count()
            global_amount = sum(mp.missed_profit_amount for mp in missed_profits.filter(program_type="global"))
            
            # Distribution breakdown
            distributed_profits = missed_profits.filter(is_distributed=True)
            total_distributed_amount = sum(mp.missed_profit_amount for mp in distributed_profits)
            
            # Recovery statistics
            recovery_attempts = MissedProfitRecovery.objects(
                created_at__gte=start_date,
                created_at__lt=end_date
            )
            total_recovery_attempts = recovery_attempts.count()
            successful_recoveries = recovery_attempts.filter(recovery_status="completed").count()
            failed_recoveries = recovery_attempts.filter(recovery_status="failed").count()
            recovery_amount = sum(r.recovery_amount for r in recovery_attempts.filter(recovery_status="completed"))
            
            # Create or update statistics record
            statistics = MissedProfitStatistics.objects(period=period).first()
            if not statistics:
                statistics = MissedProfitStatistics(period=period)
            
            statistics.period_start = start_date
            statistics.period_end = end_date
            statistics.total_missed_profits = total_missed_profits
            statistics.total_missed_amount = total_missed_amount
            statistics.total_distributed_amount = total_distributed_amount
            statistics.account_inactivity_count = account_inactivity_count
            statistics.account_inactivity_amount = account_inactivity_amount
            statistics.level_advancement_count = level_advancement_count
            statistics.level_advancement_amount = level_advancement_amount
            statistics.binary_missed_count = binary_count
            statistics.binary_missed_amount = binary_amount
            statistics.matrix_missed_count = matrix_count
            statistics.matrix_missed_amount = matrix_amount
            statistics.global_missed_count = global_count
            statistics.global_missed_amount = global_amount
            statistics.total_recovery_attempts = total_recovery_attempts
            statistics.successful_recoveries = successful_recoveries
            statistics.failed_recoveries = failed_recoveries
            statistics.recovery_amount = recovery_amount
            statistics.last_updated = datetime.utcnow()
            statistics.save()
            
            return {
                "success": True,
                "period": period,
                "period_start": start_date,
                "period_end": end_date,
                "statistics": {
                    "total_missed_profits": total_missed_profits,
                    "total_missed_amount": total_missed_amount,
                    "total_distributed_amount": total_distributed_amount,
                    "reason_breakdown": {
                        "account_inactivity": {
                            "count": account_inactivity_count,
                            "amount": account_inactivity_amount
                        },
                        "level_advancement": {
                            "count": level_advancement_count,
                            "amount": level_advancement_amount
                        }
                    },
                    "program_breakdown": {
                        "binary": {"count": binary_count, "amount": binary_amount},
                        "matrix": {"count": matrix_count, "amount": matrix_amount},
                        "global": {"count": global_count, "amount": global_amount}
                    },
                    "recovery_statistics": {
                        "total_recovery_attempts": total_recovery_attempts,
                        "successful_recoveries": successful_recoveries,
                        "failed_recoveries": failed_recoveries,
                        "recovery_amount": recovery_amount
                    }
                },
                "last_updated": statistics.last_updated
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_eligible_leadership_stipend_recipients(self) -> List[ObjectId]:
        """Get eligible Leadership Stipend recipients"""
        try:
            # This would need to be implemented based on actual Leadership Stipend logic
            # For now, returning empty list
            return []
        except Exception:
            return []
    
    def _log_action(self, user_id: str, action_type: str, description: str):
        """Log Missed Profit action"""
        try:
            log = MissedProfitLog(
                user_id=ObjectId(user_id),
                action_type=action_type,
                action_description=description,
                is_processed=True,
                processed_at=datetime.utcnow()
            )
            log.save()
        except Exception:
            pass  # Logging failure shouldn't break the main process
