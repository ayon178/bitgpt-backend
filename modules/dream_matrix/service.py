from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta
from ..user.model import User
from ..slot.model import SlotActivation
from ..tree.model import TreePlacement
from .model import (
    DreamMatrix, DreamMatrixEligibility, DreamMatrixCommission,
    DreamMatrixFund, DreamMatrixSettings, DreamMatrixLog, 
    DreamMatrixStatistics, DreamMatrixLevelProgress, DreamMatrixLevel
)

class DreamMatrixService:
    """Dream Matrix Business Logic Service"""
    
    def __init__(self):
        pass
    
    def join_dream_matrix_program(self, user_id: str) -> Dict[str, Any]:
        """Join Dream Matrix program"""
        try:
            # Validate user exists
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check if already joined
            existing = DreamMatrix.objects(user_id=ObjectId(user_id)).first()
            if existing:
                return {
                    "success": True,
                    "status": "already_joined",
                    "dream_matrix_id": str(existing.id),
                    "total_profit_earned": existing.total_profit_earned,
                    "current_level": existing.current_level,
                    "direct_partners_count": existing.direct_partners_count,
                    "message": "User already joined Dream Matrix program"
                }
            
            # Create Dream Matrix record
            dream_matrix = DreamMatrix(
                user_id=ObjectId(user_id),
                joined_at=datetime.utcnow(),
                is_active=True
            )
            
            # Initialize levels
            dream_matrix.levels = self._initialize_dream_matrix_levels()
            
            dream_matrix.save()
            
            # Create eligibility record
            eligibility = DreamMatrixEligibility(user_id=ObjectId(user_id))
            eligibility.save()
            
            # Log the action
            self._log_action(user_id, "joined_program", "User joined Dream Matrix program")
            
            return {
                "success": True,
                "dream_matrix_id": str(dream_matrix.id),
                "user_id": user_id,
                "is_eligible": False,
                "is_active": True,
                "joined_at": dream_matrix.joined_at,
                "message": "Successfully joined Dream Matrix program"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def check_eligibility(self, user_id: str, force_check: bool = False) -> Dict[str, Any]:
        """Check Dream Matrix eligibility for user"""
        try:
            # Get Dream Matrix record
            dream_matrix = DreamMatrix.objects(user_id=ObjectId(user_id)).first()
            if not dream_matrix:
                return {"success": False, "error": "User not in Dream Matrix program"}
            
            # Get eligibility record
            eligibility = DreamMatrixEligibility.objects(user_id=ObjectId(user_id)).first()
            if not eligibility:
                eligibility = DreamMatrixEligibility(user_id=ObjectId(user_id))
            
            # Check Matrix first slot status
            matrix_status = self._check_matrix_first_slot_status(user_id)
            eligibility.has_matrix_first_slot = matrix_status["has_first_slot"]
            eligibility.matrix_slot_value = matrix_status["slot_value"]
            eligibility.matrix_currency = matrix_status["currency"]
            
            # Check direct partners
            partners_status = self._check_direct_partners(user_id)
            eligibility.direct_partners_count = partners_status["partners_count"]
            eligibility.direct_partners = partners_status["partners_list"]
            
            # Update Dream Matrix record
            dream_matrix.has_matrix_first_slot = matrix_status["has_first_slot"]
            dream_matrix.slot_value = matrix_status["slot_value"]
            dream_matrix.currency = matrix_status["currency"]
            dream_matrix.direct_partners = partners_status["partners_list"]
            dream_matrix.direct_partners_count = partners_status["partners_count"]
            
            # Determine eligibility
            eligibility.is_eligible_for_dream_matrix = (
                eligibility.has_matrix_first_slot and
                eligibility.direct_partners_count >= 3
            )
            
            # Update eligibility reasons
            eligibility_reasons = self._get_eligibility_reasons(eligibility)
            eligibility.eligibility_reasons = eligibility_reasons
            
            if eligibility.is_eligible_for_dream_matrix and not dream_matrix.is_eligible:
                eligibility.qualified_at = datetime.utcnow()
                dream_matrix.is_eligible = True
                dream_matrix.qualified_at = datetime.utcnow()
                dream_matrix.has_three_direct_partners = True
                
                # Activate levels
                for level in dream_matrix.levels:
                    level.is_active = True
                    level.activated_at = datetime.utcnow()
                
                self._log_action(user_id, "became_eligible", "User became eligible for Dream Matrix bonuses")
            
            eligibility.last_checked = datetime.utcnow()
            eligibility.save()
            
            dream_matrix.last_updated = datetime.utcnow()
            dream_matrix.save()
            
            return {
                "success": True,
                "user_id": user_id,
                "is_eligible": eligibility.is_eligible_for_dream_matrix,
                "matrix_requirements": {
                    "has_matrix_first_slot": eligibility.has_matrix_first_slot,
                    "matrix_slot_value": eligibility.matrix_slot_value,
                    "matrix_currency": eligibility.matrix_currency
                },
                "direct_partners": {
                    "direct_partners_count": eligibility.direct_partners_count,
                    "min_direct_partners_required": eligibility.min_direct_partners_required,
                    "partners_list": [str(partner_id) for partner_id in eligibility.direct_partners]
                },
                "eligibility_reasons": eligibility.eligibility_reasons,
                "qualified_at": eligibility.qualified_at,
                "last_checked": eligibility.last_checked
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_commission(self, user_id: str, level_number: int, source_user_id: str, source_amount: float) -> Dict[str, Any]:
        """Process Dream Matrix commission"""
        try:
            # Get Dream Matrix record
            dream_matrix = DreamMatrix.objects(user_id=ObjectId(user_id)).first()
            if not dream_matrix:
                return {"success": False, "error": "User not in Dream Matrix program"}
            
            if not dream_matrix.is_eligible:
                return {"success": False, "error": "User not eligible for Dream Matrix bonuses"}
            
            # Validate level number
            if level_number < 1 or level_number > 5:
                return {"success": False, "error": "Invalid level number (1-5)"}
            
            # Get level details
            level_details = self._get_level_details(level_number)
            if not level_details:
                return {"success": False, "error": "Invalid level details"}
            
            # Calculate commission amount
            commission_amount = level_details["commission_amount"]
            
            # Create commission record
            commission = DreamMatrixCommission(
                user_id=ObjectId(user_id),
                dream_matrix_id=dream_matrix.id,
                level_number=level_number,
                level_name=level_details["level_name"],
                commission_percentage=level_details["commission_percentage"],
                commission_amount=commission_amount,
                source_user_id=ObjectId(source_user_id),
                source_level=level_number,
                source_amount=source_amount,
                payment_status="pending"
            )
            commission.save()
            
            # Update Dream Matrix record
            dream_matrix.total_commissions_earned += commission_amount
            dream_matrix.pending_commissions += commission_amount
            
            # Update level
            for level in dream_matrix.levels:
                if level.level_number == level_number:
                    level.total_earned += commission_amount
                    level.pending_amount += commission_amount
                    break
            
            dream_matrix.last_updated = datetime.utcnow()
            dream_matrix.save()
            
            # Log the action
            self._log_action(user_id, "commission_earned", 
                           f"Earned Level {level_number} commission: ${commission_amount}")
            
            return {
                "success": True,
                "commission_id": str(commission.id),
                "user_id": user_id,
                "level_number": level_number,
                "level_name": level_details["level_name"],
                "commission_percentage": level_details["commission_percentage"],
                "commission_amount": commission_amount,
                "source_user_id": source_user_id,
                "source_amount": source_amount,
                "payment_status": "pending",
                "message": f"Dream Matrix commission processed: ${commission_amount}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def distribute_commission_payment(self, commission_id: str) -> Dict[str, Any]:
        """Distribute Dream Matrix commission payment"""
        try:
            commission = DreamMatrixCommission.objects(id=ObjectId(commission_id)).first()
            if not commission:
                return {"success": False, "error": "Commission not found"}
            
            if commission.payment_status != "pending":
                return {"success": False, "error": "Commission already processed"}
            
            # Check fund availability
            fund = DreamMatrixFund.objects(is_active=True).first()
            if not fund:
                return {"success": False, "error": "Dream Matrix fund not found"}
            
            if fund.available_amount < commission.commission_amount:
                return {"success": False, "error": "Insufficient fund balance"}
            
            # Process payment
            commission.payment_status = "processing"
            commission.processed_at = datetime.utcnow()
            commission.save()
            
            # Update fund
            fund.available_amount -= commission.commission_amount
            fund.distributed_amount += commission.commission_amount
            fund.total_commissions_paid += 1
            fund.total_amount_distributed += commission.commission_amount
            fund.last_updated = datetime.utcnow()
            fund.save()
            
            # Update Dream Matrix record
            dream_matrix = DreamMatrix.objects(id=commission.dream_matrix_id).first()
            if dream_matrix:
                dream_matrix.total_commissions_paid += commission.commission_amount
                dream_matrix.pending_commissions -= commission.commission_amount
                
                # Update level
                for level in dream_matrix.levels:
                    if level.level_number == commission.level_number:
                        level.total_paid += commission.commission_amount
                        level.pending_amount -= commission.commission_amount
                        break
                
                dream_matrix.last_updated = datetime.utcnow()
                dream_matrix.save()
            
            # Complete payment
            commission.payment_status = "paid"
            commission.paid_at = datetime.utcnow()
            commission.payment_reference = f"DM-{commission.id}"
            commission.save()
            
            # Log the action
            self._log_action(str(commission.user_id), "commission_paid", 
                           f"Paid Level {commission.level_number} commission: ${commission.commission_amount}")
            
            return {
                "success": True,
                "commission_id": commission_id,
                "commission_amount": commission.commission_amount,
                "currency": commission.commission_amount,  # Assuming USDT
                "payment_status": "paid",
                "payment_reference": commission.payment_reference,
                "paid_at": commission.paid_at,
                "message": "Commission payment distributed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def calculate_profit_distribution(self, user_id: str) -> Dict[str, Any]:
        """Calculate Dream Matrix profit distribution"""
        try:
            dream_matrix = DreamMatrix.objects(user_id=ObjectId(user_id)).first()
            if not dream_matrix:
                return {"success": False, "error": "User not in Dream Matrix program"}
            
            if not dream_matrix.is_eligible:
                return {"success": False, "error": "User not eligible for Dream Matrix bonuses"}
            
            # Calculate total profit based on slot value ($800)
            slot_value = dream_matrix.slot_value
            total_profit = 98160.0  # Total profit from all levels
            
            # Calculate profit distribution by level
            profit_distribution = {
                "level_1": {"members": 3, "percentage": 10.0, "amount": 80.0, "total_profit": 240.0},
                "level_2": {"members": 9, "percentage": 10.0, "amount": 80.0, "total_profit": 720.0},
                "level_3": {"members": 27, "percentage": 15.0, "amount": 120.0, "total_profit": 3240.0},
                "level_4": {"members": 81, "percentage": 25.0, "amount": 200.0, "total_profit": 16200.0},
                "level_5": {"members": 243, "percentage": 40.0, "amount": 320.0, "total_profit": 77760.0}
            }
            
            # Update Dream Matrix record
            dream_matrix.total_profit_earned = total_profit
            dream_matrix.last_updated = datetime.utcnow()
            dream_matrix.save()
            
            return {
                "success": True,
                "user_id": user_id,
                "slot_value": slot_value,
                "total_profit": total_profit,
                "profit_distribution": profit_distribution,
                "message": "Dream Matrix profit distribution calculated"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_dream_matrix_statistics(self, period: str = "all_time") -> Dict[str, Any]:
        """Get Dream Matrix program statistics"""
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
            total_eligible = DreamMatrix.objects(is_eligible=True).count()
            total_active = DreamMatrix.objects(is_active=True).count()
            
            # Get commissions for period
            commissions = DreamMatrixCommission.objects(
                created_at__gte=start_date,
                created_at__lt=end_date,
                payment_status="paid"
            )
            
            total_commissions_paid = commissions.count()
            total_amount_distributed = sum(commission.commission_amount for commission in commissions)
            
            # Commission breakdown by level
            level_breakdown = {}
            for level_num in range(1, 6):
                level_commissions = commissions.filter(level_number=level_num)
                level_breakdown[f"level_{level_num}"] = {
                    "commissions_paid": level_commissions.count(),
                    "amount": sum(c.commission_amount for c in level_commissions)
                }
            
            # Create or update statistics record
            statistics = DreamMatrixStatistics.objects(period=period).first()
            if not statistics:
                statistics = DreamMatrixStatistics(period=period)
            
            statistics.period_start = start_date
            statistics.period_end = end_date
            statistics.total_eligible_users = total_eligible
            statistics.total_active_users = total_active
            statistics.total_commissions_paid = total_commissions_paid
            statistics.total_amount_distributed = total_amount_distributed
            
            # Update level statistics
            statistics.level_1_commissions_paid = level_breakdown["level_1"]["commissions_paid"]
            statistics.level_1_commissions_amount = level_breakdown["level_1"]["amount"]
            statistics.level_2_commissions_paid = level_breakdown["level_2"]["commissions_paid"]
            statistics.level_2_commissions_amount = level_breakdown["level_2"]["amount"]
            statistics.level_3_commissions_paid = level_breakdown["level_3"]["commissions_paid"]
            statistics.level_3_commissions_amount = level_breakdown["level_3"]["amount"]
            statistics.level_4_commissions_paid = level_breakdown["level_4"]["commissions_paid"]
            statistics.level_4_commissions_amount = level_breakdown["level_4"]["amount"]
            statistics.level_5_commissions_paid = level_breakdown["level_5"]["commissions_paid"]
            statistics.level_5_commissions_amount = level_breakdown["level_5"]["amount"]
            
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
                    "total_commissions_paid": total_commissions_paid,
                    "total_amount_distributed": total_amount_distributed,
                    "level_breakdown": level_breakdown,
                    "growth_statistics": {
                        "new_eligible_users": 0,  # Would need historical data
                        "new_commission_earners": 0,   # Would need historical data
                        "total_direct_partners": 0,  # Would need to calculate
                        "total_level_activations": 0  # Would need to calculate
                    }
                },
                "last_updated": statistics.last_updated
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _initialize_dream_matrix_levels(self) -> List[DreamMatrixLevel]:
        """Initialize Dream Matrix levels"""
        return [
            DreamMatrixLevel(
                level_number=1,
                level_name="Level 1",
                member_count=3,
                commission_percentage=10.0,
                commission_amount=80.0,
                total_profit=240.0
            ),
            DreamMatrixLevel(
                level_number=2,
                level_name="Level 2",
                member_count=9,
                commission_percentage=10.0,
                commission_amount=80.0,
                total_profit=720.0
            ),
            DreamMatrixLevel(
                level_number=3,
                level_name="Level 3",
                member_count=27,
                commission_percentage=15.0,
                commission_amount=120.0,
                total_profit=3240.0
            ),
            DreamMatrixLevel(
                level_number=4,
                level_name="Level 4",
                member_count=81,
                commission_percentage=25.0,
                commission_amount=200.0,
                total_profit=16200.0
            ),
            DreamMatrixLevel(
                level_number=5,
                level_name="Level 5",
                member_count=243,
                commission_percentage=40.0,
                commission_amount=320.0,
                total_profit=77760.0
            )
        ]
    
    def _check_matrix_first_slot_status(self, user_id: str) -> Dict[str, Any]:
        """Check Matrix first slot status for user"""
        try:
            # Check Matrix slot activations
            matrix_activations = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program="matrix",
                status="completed"
            ).order_by('created_at')
            
            has_first_slot = matrix_activations.count() > 0
            slot_value = 0.0
            
            if has_first_slot:
                first_slot = matrix_activations.first()
                slot_value = first_slot.amount or 0.0
            
            return {
                "has_first_slot": has_first_slot,
                "slot_value": slot_value,
                "currency": "USDT"
            }
            
        except Exception:
            return {
                "has_first_slot": False,
                "slot_value": 0.0,
                "currency": "USDT"
            }
    
    def _check_direct_partners(self, user_id: str) -> Dict[str, Any]:
        """Check direct partners for user"""
        try:
            # Get direct referrals from tree
            direct_referrals = TreePlacement.objects(
                parent_id=ObjectId(user_id),
                is_active=True
            ).all()
            
            partners_list = [ref.user_id for ref in direct_referrals]
            
            return {
                "partners_count": len(direct_referrals),
                "partners_list": partners_list
            }
            
        except Exception:
            return {
                "partners_count": 0,
                "partners_list": []
            }
    
    def _get_level_details(self, level_number: int) -> Optional[Dict[str, Any]]:
        """Get level details for given level number"""
        level_details = {
            1: {"level_name": "Level 1", "commission_percentage": 10.0, "commission_amount": 80.0},
            2: {"level_name": "Level 2", "commission_percentage": 10.0, "commission_amount": 80.0},
            3: {"level_name": "Level 3", "commission_percentage": 15.0, "commission_amount": 120.0},
            4: {"level_name": "Level 4", "commission_percentage": 25.0, "commission_amount": 200.0},
            5: {"level_name": "Level 5", "commission_percentage": 40.0, "commission_amount": 320.0}
        }
        
        return level_details.get(level_number)
    
    def _get_eligibility_reasons(self, eligibility: DreamMatrixEligibility) -> List[str]:
        """Get eligibility reasons"""
        reasons = []
        
        if not eligibility.has_matrix_first_slot:
            reasons.append("Matrix first slot not purchased")
        
        if eligibility.direct_partners_count < 3:
            reasons.append("Need at least 3 direct partners")
        
        return reasons
    
    def _log_action(self, user_id: str, action_type: str, description: str):
        """Log Dream Matrix action"""
        try:
            log = DreamMatrixLog(
                user_id=ObjectId(user_id),
                action_type=action_type,
                action_description=description,
                is_processed=True,
                processed_at=datetime.utcnow()
            )
            log.save()
        except Exception:
            pass  # Logging failure shouldn't break the main process
