from typing import Dict, Any, Optional
from bson import ObjectId
from decimal import Decimal
from datetime import datetime
from mongoengine.errors import ValidationError

from ..user.model import User, EarningHistory
from ..slot.model import SlotActivation, SlotCatalog
from ..commission.service import CommissionService
from ..auto_upgrade.model import BinaryAutoUpgrade
from ..rank.service import RankService
from ..jackpot.service import JackpotService
from ..leadership_stipend.service import LeadershipStipendService
from ..spark.service import SparkService
from ..blockchain.model import BlockchainEvent
from ..tree.model import TreePlacement
from utils import ensure_currency_for_program


class BinaryService:
    """Binary Program Business Logic Service"""
    
    def __init__(self):
        self.commission_service = CommissionService()
        self.rank_service = RankService()
        self.jackpot_service = JackpotService()
        self.leadership_stipend_service = LeadershipStipendService()
        self.spark_service = SparkService()
    
    def upgrade_binary_slot(self, user_id: str, slot_no: int, tx_hash: str, amount: Decimal) -> Dict[str, Any]:
        """
        Upgrade Binary slot with all auto calculations and distributions
        
        This method ensures all the following happen automatically:
        1. Slot activation record creation
        2. Upgrade commission calculation (30% to corresponding level upline)
        3. Dual tree earning distribution (70% across levels 1-16)
        4. User rank update
        5. Jackpot free coupon awards (slots 5-16)
        6. Leadership stipend eligibility check (slots 10-16)
        7. Spark bonus fund contribution
        8. Auto-upgrade status update
        9. Earning history recording
        10. Blockchain event logging
        """
        try:
            # Validate user exists
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                raise ValueError("User not found")
            
            # Validate slot upgrade
            if slot_no < 3 or slot_no > 16:
                raise ValueError("Invalid slot number. Must be between 3-16")
            
            # Get current binary status
            binary_status = BinaryAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
            if not binary_status:
                raise ValueError("User not in Binary program")
            
            # Validate slot progression
            if slot_no <= binary_status.current_slot_no:
                raise ValueError(f"Cannot upgrade to slot {slot_no}. Current slot is {binary_status.current_slot_no}")
            
            # Get slot catalog
            catalog = SlotCatalog.objects(program='binary', slot_no=slot_no, is_active=True).first()
            if not catalog:
                raise ValueError(f"Slot {slot_no} catalog not found")
            
            # Validate amount
            expected_amount = catalog.price or Decimal('0')
            if amount != expected_amount:
                raise ValueError(f"Upgrade amount must be {expected_amount} BNB")
            
            currency = ensure_currency_for_program('binary', 'BNB')
            
            # 1. Create slot activation record
            activation = SlotActivation(
                user_id=ObjectId(user_id),
                program='binary',
                slot_no=slot_no,
                slot_name=catalog.name,
                activation_type='upgrade',
                upgrade_source='manual',
                amount_paid=amount,
                currency=currency,
                tx_hash=tx_hash,
                is_auto_upgrade=False,
                status='completed',
                activated_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            activation.save()
            
            # 2. Update binary auto upgrade status
            binary_status.current_slot_no = slot_no
            binary_status.current_level = slot_no
            binary_status.last_updated = datetime.utcnow()
            binary_status.save()
            
            # 3. Process upgrade commission (30% to corresponding level upline + 70% dual tree distribution)
            commission_result = self.commission_service.calculate_upgrade_commission(
                from_user_id=user_id,
                program='binary',
                slot_no=slot_no,
                slot_name=catalog.name,
                amount=amount,
                currency=currency
            )
            
            # 4. Update user rank
            rank_result = self.rank_service.update_user_rank(user_id=user_id)
            
            # 5. Award jackpot free coupons (slots 5-16)
            if slot_no >= 5:
                jackpot_result = self.jackpot_service.award_free_coupon_for_binary_slot(
                    user_id=user_id, 
                    slot_no=slot_no
                )
            
            # 6. Check leadership stipend eligibility (slots 10-16)
            if slot_no >= 10:
                stipend_result = self.leadership_stipend_service.check_eligibility(
                    user_id=user_id, 
                    force_check=True
                )
            
            # 7. Contribute to Spark bonus fund (8% of binary earnings)
            spark_result = self.spark_service.contribute_to_fund(
                program='binary',
                amount=amount,
                currency=currency,
                source_user_id=user_id,
                source_type='slot_upgrade',
                source_slot_no=slot_no
            )
            
            # 8. Record earning history
            earning_history = EarningHistory(
                user_id=ObjectId(user_id),
                earning_type='binary_slot_upgrade',
                program='binary',
                amount=float(amount),
                currency=currency,
                slot_name=catalog.name,
                slot_level=catalog.level,
                description=f"Manual upgrade to binary slot {slot_no} ({catalog.name})"
            )
            earning_history.save()
            
            # 9. Record blockchain event
            blockchain_event = BlockchainEvent(
                tx_hash=tx_hash,
                event_type='slot_upgraded',
                event_data={
                    'program': 'binary',
                    'slot_no': slot_no,
                    'slot_name': catalog.name,
                    'amount': str(amount),
                    'currency': currency,
                    'user_id': user_id,
                    'upgrade_type': 'manual'
                },
                status='processed',
                processed_at=datetime.utcnow()
            )
            blockchain_event.save()
            
            # 10. Update user's binary slot info
            self._update_user_binary_slot_info(user, slot_no, catalog.name, amount)
            
            return {
                "success": True,
                "activation_id": str(activation.id),
                "new_slot": catalog.name,
                "slot_no": slot_no,
                "amount": float(amount),
                "currency": currency,
                "commission_result": commission_result,
                "rank_result": rank_result,
                "jackpot_result": jackpot_result if slot_no >= 5 else None,
                "stipend_result": stipend_result if slot_no >= 10 else None,
                "spark_result": spark_result,
                "message": f"Successfully upgraded to {catalog.name} (Slot {slot_no})"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _update_user_binary_slot_info(self, user: User, slot_no: int, slot_name: str, amount: Decimal):
        """Update user's binary slot information"""
        try:
            # Update user's current binary slot
            user.current_binary_slot = slot_no
            user.current_binary_slot_name = slot_name
            
            # Add to binary slots list if not exists
            if not hasattr(user, 'binary_slots') or not user.binary_slots:
                user.binary_slots = []
            
            # Check if slot already exists
            slot_exists = False
            for slot_info in user.binary_slots:
                if slot_info.slot_no == slot_no:
                    slot_info.is_active = True
                    slot_info.activated_at = datetime.utcnow()
                    slot_exists = True
                    break
            
            # Add new slot if not exists
            if not slot_exists:
                from ..user.model import BinarySlotInfo
                new_slot = BinarySlotInfo(
                    slot_no=slot_no,
                    slot_name=slot_name,
                    slot_value=float(amount),
                    is_active=True,
                    activated_at=datetime.utcnow()
                )
                user.binary_slots.append(new_slot)
            
            user.updated_at = datetime.utcnow()
            user.save()
            
        except Exception as e:
            # Log error but don't fail the upgrade
            print(f"Error updating user binary slot info: {str(e)}")
    
    def get_binary_upgrade_status(self, user_id: str) -> Dict[str, Any]:
        """Get user's binary upgrade status and next available slots"""
        try:
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                raise ValueError("User not found")
            
            binary_status = BinaryAutoUpgrade.objects(user_id=ObjectId(user_id)).first()
            if not binary_status:
                raise ValueError("User not in Binary program")
            
            # Get available slots for upgrade
            available_slots = []
            current_slot = binary_status.current_slot_no
            
            for slot_no in range(current_slot + 1, 17):  # Slots 3-16
                catalog = SlotCatalog.objects(program='binary', slot_no=slot_no, is_active=True).first()
                if catalog:
                    available_slots.append({
                        "slot_no": slot_no,
                        "slot_name": catalog.name,
                        "slot_value": float(catalog.price or Decimal('0')),
                        "currency": "BNB",
                        "level": catalog.level
                    })
            
            return {
                "success": True,
                "user_id": user_id,
                "current_slot": current_slot,
                "current_level": binary_status.current_level,
                "partners_required": binary_status.partners_required,
                "partners_available": binary_status.partners_available,
                "is_eligible_for_auto_upgrade": binary_status.is_eligible,
                "can_upgrade": binary_status.can_upgrade,
                "available_slots": available_slots,
                "last_updated": binary_status.last_updated
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def calculate_dual_tree_earnings(self, slot_no: int, slot_value: Decimal) -> Dict[str, Any]:
        """
        Calculate dual tree earnings distribution according to PROJECT_DOCUMENTATION.md
        
        Level 1: 30%
        Level 2-3: 10% each
        Level 4-10: 5% each
        Level 11-13: 3% each
        Level 14-16: 2% each
        Total: 100%
        """
        try:
            # Calculate total income based on slot value and level members
            level_members = {
                1: 2, 2: 4, 3: 8, 4: 16, 5: 32, 6: 64, 7: 128, 8: 256,
                9: 512, 10: 1024, 11: 2048, 12: 4096, 13: 8192, 14: 16384, 15: 32768, 16: 65536
            }
            
            total_income = slot_value * level_members.get(slot_no, 0)
            
            # Distribution percentages
            distributions = {
                1: 0.30,   # 30%
                2: 0.10,   # 10%
                3: 0.10,   # 10%
                4: 0.05,   # 5%
                5: 0.05,   # 5%
                6: 0.05,   # 5%
                7: 0.05,   # 5%
                8: 0.05,   # 5%
                9: 0.05,   # 5%
                10: 0.05,  # 5%
                11: 0.03,  # 3%
                12: 0.03,  # 3%
                13: 0.03,  # 3%
                14: 0.02,  # 2%
                15: 0.02,  # 2%
                16: 0.02   # 2%
            }
            
            # Calculate level earnings
            level_earnings = {}
            for level in range(1, min(slot_no + 1, 17)):
                percentage = distributions.get(level, 0)
                level_amount = total_income * Decimal(str(percentage))
                level_earnings[level] = {
                    "percentage": percentage * 100,
                    "amount": float(level_amount),
                    "members": level_members.get(level, 0)
                }
            
            return {
                "success": True,
                "slot_no": slot_no,
                "slot_value": float(slot_value),
                "total_income": float(total_income),
                "level_earnings": level_earnings,
                "total_distribution": sum(level_earnings[level]["amount"] for level in level_earnings)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
