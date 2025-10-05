from typing import Dict, Any, Optional, List
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
                upgrade_source='wallet',
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
                earning_type='binary_slot',
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
                event_type='upgrade_triggered',
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

    def get_binary_slots_activated(self, user_id: str) -> int:
        try:
            return 0
        except Exception:
            return 0

    def get_binary_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive binary dashboard data for a user
        Includes: total profit, active slots, total earnings from wallet ledger
        """
        try:
            from ..wallet.model import WalletLedger
            from ..missed_profit.model import MissedProfit
            
            print(f"Getting binary dashboard data for user: {user_id}")
            
            # Convert user_id to ObjectId
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id
            
            # Get today's date range
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # 1. Get total binary earnings from wallet ledger (binary related reasons)
            binary_earnings = {"USDT": 0.0, "BNB": 0.0}
            try:
                binary_reasons = [
                    'binary_joining_commission', 'binary_upgrade_commission', 'binary_partner_incentive',
                    'binary_level_commission', 'binary_dual_tree_earning', 'binary_leadership_stipend',
                    'binary_royal_captain', 'binary_president_reward', 'binary_jackpot_bonus'
                ]
                
                binary_ledger_entries = WalletLedger.objects(
                    user_id=user_oid,
                    reason__in=binary_reasons,
                    type='credit'
                ).only('amount', 'currency')
                
                for entry in binary_ledger_entries:
                    currency = (str(getattr(entry, 'currency', '')).upper() or 'BNB')
                    if currency in binary_earnings:
                        amount = float(getattr(entry, 'amount', 0) or 0)
                        binary_earnings[currency] += amount
                
                print(f"Binary earnings for user {user_id}: USDT={binary_earnings['USDT']}, BNB={binary_earnings['BNB']}")
                
            except Exception as e:
                print(f"Error calculating binary earnings: {e}")
            
            # 2. Get today's binary earnings
            today_binary_earnings = {"USDT": 0.0, "BNB": 0.0}
            try:
                today_binary_entries = WalletLedger.objects(
                    user_id=user_oid,
                    reason__in=binary_reasons,
                    type='credit',
                    created_at__gte=today_start,
                    created_at__lte=today_end
                ).only('amount', 'currency')
                
                for entry in today_binary_entries:
                    currency = (str(getattr(entry, 'currency', '')).upper() or 'BNB')
                    if currency in today_binary_earnings:
                        amount = float(getattr(entry, 'amount', 0) or 0)
                        today_binary_earnings[currency] += amount
                
                print(f"Today's binary earnings for user {user_id}: USDT={today_binary_earnings['USDT']}, BNB={today_binary_earnings['BNB']}")
                
            except Exception as e:
                print(f"Error calculating today's binary earnings: {e}")
            
            # 3. Get active binary slots count
            active_slots_count = 0
            try:
                active_slots = SlotActivation.objects(
                    user_id=user_oid,
                    program='binary',
                    is_active=True
                ).count()
                active_slots_count = active_slots
                print(f"Active binary slots for user {user_id}: {active_slots_count}")
                
            except Exception as e:
                print(f"Error counting active slots: {e}")
            
            # 4. Get missing profit for binary
            missing_profit = {"USDT": 0.0, "BNB": 0.0}
            try:
                missed_profits = MissedProfit.objects(
                    user_id=user_oid,
                    program_type='binary',
                    is_active=True,
                    is_distributed=False
                ).only('missed_profit_amount', 'currency')
                
                for missed in missed_profits:
                    currency = (str(getattr(missed, 'currency', '')).upper() or 'BNB')
                    if currency in missing_profit:
                        amount = float(getattr(missed, 'missed_profit_amount', 0) or 0)
                        missing_profit[currency] += amount
                
                print(f"Missing profit for user {user_id}: USDT={missing_profit['USDT']}, BNB={missing_profit['BNB']}")
                
            except Exception as e:
                print(f"Error calculating missing profit: {e}")
            
            # 5. Get team statistics (total team, today team, today direct)
            team_stats = {
                "total_team": 0,
                "today_team": 0,
                "today_direct": 0
            }
            try:
                # Total team count (all levels under user)
                def count_all_descendants(parent_user_id):
                    count = 0
                    children = TreePlacement.objects(
                        program='binary',
                        parent_id=parent_user_id
                    )
                    for child in children:
                        count += 1
                        count += count_all_descendants(child.user_id)
                    return count
                
                team_stats["total_team"] = count_all_descendants(user_oid)
                
                # Today team count
                def count_today_descendants(parent_user_id):
                    count = 0
                    children = TreePlacement.objects(
                        program='binary',
                        parent_id=parent_user_id,
                        created_at__gte=today_start,
                        created_at__lte=today_end
                    )
                    for child in children:
                        count += 1
                        count += count_today_descendants(child.user_id)
                    return count
                
                team_stats["today_team"] = count_today_descendants(user_oid)
                
                # Today direct count
                team_stats["today_direct"] = TreePlacement.objects(
                    program='binary',
                    parent_id=user_oid,
                    created_at__gte=today_start,
                    created_at__lte=today_end
                ).count()
                
                print(f"Team stats for user {user_id}: {team_stats}")
                
            except Exception as e:
                print(f"Error calculating team stats: {e}")
            
            # Compile dashboard data
            dashboard_data = {
                "user_id": str(user_id),
                "total_profit": {
                    "USDT": binary_earnings["USDT"],
                    "BNB": binary_earnings["BNB"]
                },
                "today_income": {
                    "USDT": today_binary_earnings["USDT"],
                    "BNB": today_binary_earnings["BNB"]
                },
                "active_slots_count": active_slots_count,
                "missing_profit": {
                    "USDT": missing_profit["USDT"],
                    "BNB": missing_profit["BNB"]
                },
                "team_statistics": team_stats,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            print(f"Binary dashboard data generated successfully for user {user_id}")
            return {
                "success": True,
                "data": dashboard_data
            }
            
        except Exception as e:
            print(f"Error in get_binary_dashboard_data: {e}")
            return {"success": False, "error": str(e)}

    def get_binary_earnings_frontend_format(self, user_id: str, page: int = 1, limit: int = 10, currency: str = "BNB") -> Dict[str, Any]:
        """
        Get binary earnings in frontend format following dashboardData.js structure
        Returns data similar to incomeTableData format
        """
        try:
            from ..wallet.model import WalletLedger
            from ..user.model import User
            
            print(f"Getting binary earnings (frontend format) for user: {user_id}, page: {page}, limit: {limit}, currency: {currency}")
            
            # Convert user_id to ObjectId
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id
            
            # Debug: Check all wallet entries for this user first
            all_entries = WalletLedger.objects(user_id=user_oid).order_by('-created_at')
            print(f"DEBUG: Total wallet entries for user {user_id}: {all_entries.count()}")
            
            # Show sample entries for debugging
            for entry in all_entries[:5]:
                print(f"DEBUG: Entry - Reason: {entry.reason}, Amount: {entry.amount}, Currency: {entry.currency}, Type: {entry.type}")
            
            # Use ONLY binary-specific reasons for binary earnings API
            binary_reasons = [
                'binary_joining_commission', 'binary_upgrade_commission', 'binary_partner_incentive',
                'binary_level_commission', 'binary_dual_tree_earning', 'binary_leadership_stipend',
                'binary_royal_captain', 'binary_president_reward', 'binary_jackpot_bonus',
                'binary_upgrade_level_1', 'binary_dual_tree_L1_S1', 'binary_dual_tree_L1_S2'
            ]
            
            print(f"DEBUG: Looking for binary-specific entries with reasons: {binary_reasons}")
            
            # Get binary-specific entries only
            earnings = WalletLedger.objects(
                user_id=user_oid,
                reason__in=binary_reasons,
                type='credit'
            ).order_by('-created_at').skip((page - 1) * limit).limit(limit)
            
            total_count = WalletLedger.objects(
                user_id=user_oid,
                reason__in=binary_reasons,
                type='credit'
            ).count()
            
            print(f"DEBUG: Found {total_count} binary-specific entries")
            
            # Calculate pagination
            total_pages = (total_count + limit - 1) // limit
            
            # Format earnings data in frontend format (similar to incomeTableData)
            earnings_data = []
            for i, earning in enumerate(earnings):
                # Get user info - use FULL UID as requested
                user_info = User.objects(id=user_oid).first()
                if user_info and user_info.uid:
                    user_display_id = str(user_info.uid)  # Full UID as requested
                else:
                    user_display_id = str(user_oid)  # Fallback to ObjectId
                
                # Get upline info - use FULL UID as requested
                upline_id = "ROOT"  # Default for root users
                if user_info and user_info.refered_by:
                    try:
                        upline_user = User.objects(id=user_info.refered_by).first()
                        if upline_user and upline_user.uid:
                            upline_id = str(upline_user.uid)  # Full UID as requested
                        else:
                            upline_id = str(user_info.refered_by)  # Fallback to ObjectId
                    except:
                        upline_id = str(user_info.refered_by)  # Fallback to refered_by ObjectId
                elif earning.tx_hash:
                    # Try to extract upline from tx_hash
                    upline_id = str(earning.tx_hash)  # Full tx_hash
                elif earning.reason:
                    # Use reason as upline identifier
                    upline_id = str(earning.reason)  # Full reason
                
                # Calculate days since creation
                days_since = (datetime.utcnow() - earning.created_at).days if earning.created_at else 1
                
                # Determine level based on reason
                level = 1
                if 'level' in earning.reason:
                    try:
                        level = int(earning.reason.split('level_')[-1].split('_')[0])
                    except:
                        level = 1
                elif 'upgrade' in earning.reason:
                    level = 2
                elif 'partner' in earning.reason:
                    level = 3
                elif 'commission' in earning.reason:
                    level = 2
                elif 'earnings' in earning.reason or 'income' in earning.reason:
                    level = 1
                
                # Format date and time
                created_date = earning.created_at if earning.created_at else datetime.utcnow()
                time_str = created_date.strftime("%H:%M")
                date_str = created_date.strftime("%d %b %Y")
                
                # Determine partner and rank
                partner = 2 if 'partner' in earning.reason else 1
                rank = level if level <= 6 else 6
                
                # Format amount for frontend - show exact amount without rounding
                amount_value = float(earning.amount or 0)
                if amount_value > 0:
                    # Show exact amount as string to preserve precision
                    formatted_amount = str(amount_value)
                else:
                    formatted_amount = "0"
                
                # Debug print
                print(f"DEBUG: Processing earning - Raw Amount: {earning.amount}, Processed Amount: {amount_value}, Currency: {earning.currency}, Reason: {earning.reason}")
                print(f"DEBUG: User ID: {user_display_id}, Upline: {upline_id}")
                
                # Determine which currency field to populate based on actual currency
                usdt_amount = ""
                bnb_amount = ""
                
                # Handle currency mapping - USD should be treated as USDT
                currency_upper = str(earning.currency).upper() if earning.currency else 'USD'
                if currency_upper == 'USD':
                    currency_upper = 'USDT'  # Map USD to USDT
                
                if currency_upper == 'USDT':
                    usdt_amount = formatted_amount
                elif currency_upper == 'BNB':
                    bnb_amount = formatted_amount
                else:
                    # If no currency specified, assume based on amount value
                    if amount_value > 0:
                        # Large amounts likely USDT, small amounts likely BNB
                        if amount_value > 10:
                            usdt_amount = formatted_amount
                        else:
                            bnb_amount = formatted_amount
                
                earnings_data.append({
                    "id": i + 1 + (page - 1) * limit,  # Sequential ID for frontend
                    "days": days_since,
                    "level": level,
                    "upline": upline_id,
                    "userId": user_display_id,
                    "usdt": usdt_amount,
                    "bnb": bnb_amount,
                    "time": time_str,
                    "date": date_str,
                    "partner": partner,
                    "rank": rank
                })
            
            result = {
                "incomeTableData": earnings_data,  # Following dashboardData.js format
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_count": total_count,
                    "limit": limit,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
            
            print(f"Binary earnings (frontend format) retrieved: {len(earnings_data)} records")
            return {"success": True, "data": result}
            
        except Exception as e:
            print(f"Error in get_binary_earnings_frontend_format: {e}")
            return {"success": False, "error": str(e)}

    def get_binary_tree_structure(self, user_id: str) -> Dict[str, Any]:
        """
        Get binary tree structure data for dashboard panels
        Returns data matching frontend yourRank structure
        """
        try:
            from ..tree.model import TreePlacement
            from ..slot.model import SlotActivation
            
            print(f"Getting binary tree structure for user: {user_id}")
            
            # Convert user_id to ObjectId
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id
            
            # Get user's activated binary slots
            activated_slots = SlotActivation.objects(
                user_id=user_oid,
                program='binary',
                status='completed'
            ).order_by('slot_no')
            
            panels = []
            
            # Create panels for slots 1-6 (matching frontend yourRank)
            for slot_no in range(1, 7):
                # Check if slot is activated
                slot_activation = activated_slots.filter(slot_no=slot_no).first()
                
                # Get slot-specific earnings
                slot_earnings_breakdown = self._get_slot_specific_earnings(user_oid, slot_no)
                total_usdt = slot_earnings_breakdown.get('USDT', 0)
                total_bnb = slot_earnings_breakdown.get('BNB', 0)
                
                # Calculate progress (based on actual earnings vs expected)
                # For binary, assume 1 BNB = 100% progress for each slot
                expected_amount = 1.0  # 1 BNB per slot
                progress = min(100, (total_bnb / expected_amount) * 100) if expected_amount > 0 else 0
                
                # Determine status based on earnings
                if total_bnb >= expected_amount:
                    status = "Completed"
                elif total_bnb > 0:
                    status = "In Progress"
                else:
                    status = "Not Started"
                
                # Get team structure for this slot
                team_structure = self._get_slot_team_structure(user_oid, slot_no)
                
                # Format amount display
                if total_bnb > 0:
                    amount_display = f"{total_bnb:.6f} BNB"
                elif total_usdt > 0:
                    amount_display = f"{total_usdt:.6f} USDT"
                else:
                    amount_display = "0.000000 BNB"
                
                panel = {
                    "id": slot_no,
                    "slot_number": slot_no,
                    "amount": amount_display,
                    "level": slot_no,  # Use slot_no as level
                    "progress": progress,
                    "status": status,
                    "team_structure": team_structure,
                    "actions": {
                        "auto_update": slot_no <= 3,  # Slots 1-3 can auto-update
                        "manual_upgrade": slot_no > 3,  # Slots 4+ require manual upgrade
                        "completed": total_bnb >= expected_amount
                    }
                }
                
                panels.append(panel)
            
            result = {
                "panels": panels,
                "total_panels": len(panels),
                "user_id": str(user_id)
            }
            
            print(f"Binary tree structure generated: {len(panels)} panels")
            return {"success": True, "data": result}
            
        except Exception as e:
            print(f"Error in get_binary_tree_structure: {e}")
            return {"success": False, "error": str(e)}

    def get_binary_panel_data(self, user_id: str) -> Dict[str, Any]:
        """
        Get individual panel data for each binary slot/level
        Returns detailed data for each panel that can be rendered separately
        """
        try:
            from ..tree.model import TreePlacement
            from ..wallet.model import WalletLedger
            
            print(f"Getting binary panel data for user: {user_id}")
            
            # Convert user_id to ObjectId
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id
            
            panels_data = []
            
            # Get all binary slots for this user
            user_slots = SlotActivation.objects(
                user_id=user_oid,
                program='binary',
                status='completed'
            ).order_by('slot_no')
            
            for slot_activation in user_slots:
                slot_no = slot_activation.slot_no
                
                # Get slot-specific earnings
                slot_earnings = self._get_slot_specific_earnings(user_oid, slot_no)
                
                # Get team members for this slot
                team_members = self._get_slot_team_members(user_oid, slot_no)
                
                # Get slot status and actions
                slot_status = self._get_slot_status(user_oid, slot_no)
                
                panel_data = {
                    "slot_number": slot_no,
                    "slot_name": f"Slot {slot_no}",
                    "earnings": {
                        "total_usdt": slot_earnings.get('USDT', 0),
                        "total_bnb": slot_earnings.get('BNB', 0),
                        "display_amount": f"{slot_earnings.get('USDT', 0):.0f} USDT"
                    },
                    "team_data": {
                        "total_members": len(team_members),
                        "direct_members": len([m for m in team_members if m.get('level', 1) == 2]),
                        "members": team_members
                    },
                    "status": slot_status,
                    "actions": {
                        "can_upgrade": slot_status.get('can_upgrade', False),
                        "can_auto_update": slot_status.get('can_auto_update', False),
                        "is_completed": slot_status.get('is_completed', False)
                    },
                    "level_info": {
                        "current_level": slot_no,  # Use slot_no as level
                        "progress_percentage": slot_status.get('progress', 0)
                    }
                }
                
                panels_data.append(panel_data)
            
            result = {
                "panels": panels_data,
                "total_panels": len(panels_data),
                "user_id": str(user_id),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            print(f"Binary panel data generated: {len(panels_data)} panels")
            return {"success": True, "data": result}
            
        except Exception as e:
            print(f"Error in get_binary_panel_data: {e}")
            return {"success": False, "error": str(e)}

    def _calculate_slot_earnings(self, user_oid, slot_no: int) -> float:
        """Calculate earnings for a specific slot"""
        try:
            from ..wallet.model import WalletLedger
            
            # Try multiple reason patterns for slot earnings
            slot_patterns = [
                f'slot_{slot_no}',
                f'binary_slot_{slot_no}',
                f'binary_joining_commission',
                f'binary_upgrade_commission',
                f'binary_partner_incentive',
                f'binary_level_commission',
                f'binary_dual_tree_earning'
            ]
            
            slot_earnings = 0
            for pattern in slot_patterns:
                earnings = WalletLedger.objects(
                    user_id=user_oid,
                    reason__contains=pattern,
                    type='credit'
                ).sum('amount') or 0
                slot_earnings += float(earnings)
            
            return slot_earnings
        except Exception as e:
            print(f"Error calculating slot {slot_no} earnings: {e}")
            return 0.0

    def _get_slot_team_structure(self, user_oid, slot_no: int) -> Dict[str, Any]:
        """Get team structure for a specific slot"""
        try:
            from ..tree.model import TreePlacement
            
            # Get direct team members under this user
            direct_members = TreePlacement.objects(
                program='binary',
                parent_id=user_oid
            ).count()
            
            # Get total team members (recursive count)
            def count_total_team(parent_id):
                total = 0
                children = TreePlacement.objects(
                    program='binary',
                    parent_id=parent_id
                )
                for child in children:
                    total += 1
                    total += count_total_team(child.user_id)
                return total
            
            total_members = count_total_team(user_oid)
            
            # Calculate tree levels based on team size
            tree_levels = min(6, max(1, direct_members + 1))
            
            return {
                "total_users": total_members,
                "direct_users": direct_members,
                "tree_levels": tree_levels
            }
        except Exception as e:
            print(f"Error getting team structure for slot {slot_no}: {e}")
            return {
                "total_users": 0,
                "direct_users": 0,
                "tree_levels": 1
            }

    def _get_slot_specific_earnings(self, user_oid, slot_no: int) -> Dict[str, float]:
        """Get slot-specific earnings by currency"""
        try:
            from ..wallet.model import WalletLedger
            
            earnings = {"USDT": 0.0, "BNB": 0.0}
            
            # Get ALL binary earnings for this user (not slot-specific for now)
            binary_reasons = [
                'binary_joining_commission', 'binary_upgrade_commission', 'binary_partner_incentive',
                'binary_level_commission', 'binary_dual_tree_earning', 'binary_leadership_stipend',
                'binary_royal_captain', 'binary_president_reward', 'binary_jackpot_bonus',
                'binary_upgrade_level_1', 'binary_dual_tree_L1_S1', 'binary_dual_tree_L1_S2'
            ]
            
            binary_entries = WalletLedger.objects(
                user_id=user_oid,
                reason__in=binary_reasons,
                type='credit'
            ).only('amount', 'currency')
            
            for entry in binary_entries:
                currency = str(entry.currency).upper() if entry.currency else 'BNB'
                # Handle USD → USDT mapping
                if currency == 'USD':
                    currency = 'USDT'
                
                if currency in earnings:
                    earnings[currency] += float(entry.amount or 0)
            
            return earnings
        except Exception as e:
            print(f"Error getting slot {slot_no} specific earnings: {e}")
            return {"USDT": 0.0, "BNB": 0.0}

    def _get_slot_team_members(self, user_oid, slot_no: int) -> List[Dict[str, Any]]:
        """Get team members for a specific slot"""
        try:
            from ..tree.model import TreePlacement
            
            team_members = TreePlacement.objects(
                program='binary',
                parent_id=user_oid
            ).only('user_id', 'level', 'position', 'created_at')
            
            members = []
            for member in team_members:
                members.append({
                    "user_id": str(member.user_id),
                    "level": member.level,
                    "position": member.position,
                    "joined_at": member.created_at.isoformat() if member.created_at else None
                })
            
            return members
        except:
            return []

    def _get_slot_status(self, user_oid, slot_no: int) -> Dict[str, Any]:
        """Get status information for a specific slot"""
        try:
            # Get slot activation info
            slot_activation = SlotActivation.objects(
                user_id=user_oid,
                program='binary',
                slot_no=slot_no,
                status='completed'
            ).first()
            
            if not slot_activation:
                return {
                    "can_upgrade": True,
                    "can_auto_update": False,
                    "is_completed": False,
                    "progress": 0
                }
            
            # Calculate progress based on earnings
            earnings = self._get_slot_specific_earnings(user_oid, slot_no)
            total_earnings = earnings.get('USDT', 0) + earnings.get('BNB', 0)
            
            # Assume 1000 USDT is completion threshold
            progress = min(100, (total_earnings / 1000) * 100)
            is_completed = total_earnings >= 1000
            
            return {
                "can_upgrade": not is_completed,
                "can_auto_update": slot_no <= 3,
                "is_completed": is_completed,
                "progress": progress
            }
        except:
            return {
                "can_upgrade": True,
                "can_auto_update": False,
                "is_completed": False,
                "progress": 0
            }

    def get_binary_earnings(self, user_id: str, page: int = 1, limit: int = 10, currency: str = "BNB") -> Dict[str, Any]:
        """
        Get binary earnings with pagination and currency filtering
        """
        try:
            from ..wallet.model import WalletLedger
            
            print(f"Getting binary earnings for user: {user_id}, page: {page}, limit: {limit}, currency: {currency}")
            
            # Convert user_id to ObjectId
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id
            
            # Binary related reasons
            binary_reasons = [
                'binary_joining_commission', 'binary_upgrade_commission', 'binary_partner_incentive',
                'binary_level_commission', 'binary_dual_tree_earning', 'binary_leadership_stipend',
                'binary_royal_captain', 'binary_president_reward', 'binary_jackpot_bonus'
            ]
            
            # Get total count
            total_count = WalletLedger.objects(
                user_id=user_oid,
                reason__in=binary_reasons,
                type='credit',
                currency=currency.upper()
            ).count()
            
            # Calculate pagination
            skip = (page - 1) * limit
            total_pages = (total_count + limit - 1) // limit
            
            # Get paginated earnings
            earnings = WalletLedger.objects(
                user_id=user_oid,
                reason__in=binary_reasons,
                type='credit',
                currency=currency.upper()
            ).order_by('-created_at').skip(skip).limit(limit)
            
            # Format earnings data
            earnings_data = []
            for earning in earnings:
                earnings_data.append({
                    "id": str(earning.id),
                    "amount": float(earning.amount or 0),
                    "currency": earning.currency,
                    "reason": earning.reason,
                    "tx_hash": earning.tx_hash,
                    "created_at": earning.created_at.isoformat() if earning.created_at else None,
                    "balance_after": float(earning.balance_after or 0)
                })
            
            result = {
                "earnings": earnings_data,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_count": total_count,
                    "limit": limit,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
            
            print(f"Binary earnings retrieved: {len(earnings_data)} records")
            return {"success": True, "data": result}
            
        except Exception as e:
            print(f"Error in get_binary_earnings: {e}")
            return {"success": False, "error": str(e)}

    def get_binary_partner_incentive(self, user_id: str, page: int = 1, limit: int = 10, currency: str = "BNB") -> Dict[str, Any]:
        """
        Get binary partner incentive earnings with pagination
        """
        try:
            from ..wallet.model import WalletLedger
            
            print(f"Getting binary partner incentive for user: {user_id}, page: {page}, limit: {limit}, currency: {currency}")
            
            # Convert user_id to ObjectId
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id
            
            # Partner incentive related reasons
            partner_reasons = ['binary_partner_incentive', 'binary_joining_commission']
            
            # Get total count
            total_count = WalletLedger.objects(
                user_id=user_oid,
                reason__in=partner_reasons,
                type='credit',
                currency=currency.upper()
            ).count()
            
            # Calculate pagination
            skip = (page - 1) * limit
            total_pages = (total_count + limit - 1) // limit
            
            # Get paginated partner incentives
            incentives = WalletLedger.objects(
                user_id=user_oid,
                reason__in=partner_reasons,
                type='credit',
                currency=currency.upper()
            ).order_by('-created_at').skip(skip).limit(limit)
            
            # Format incentives data
            incentives_data = []
            for incentive in incentives:
                incentives_data.append({
                    "id": str(incentive.id),
                    "amount": float(incentive.amount or 0),
                    "currency": incentive.currency,
                    "reason": incentive.reason,
                    "tx_hash": incentive.tx_hash,
                    "created_at": incentive.created_at.isoformat() if incentive.created_at else None,
                    "balance_after": float(incentive.balance_after or 0)
                })
            
            result = {
                "partner_incentives": incentives_data,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_count": total_count,
                    "limit": limit,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
            
            print(f"Binary partner incentives retrieved: {len(incentives_data)} records")
            return {"success": True, "data": result}
            
        except Exception as e:
            print(f"Error in get_binary_partner_incentive: {e}")
            return {"success": False, "error": str(e)}

    def get_duel_tree_earnings(self, user_id: str) -> Dict[str, Any]:
        """
        Get duel tree earnings data matching frontend matrixData.js structure
        Returns data in the format expected by DualTree and DuelTreeDetails components
        """
        try:
            from ..tree.model import TreePlacement
            from ..slot.model import SlotActivation, SlotCatalog
            from ..wallet.model import WalletLedger
            from ..user.model import User
            
            print(f"Getting duel tree earnings for user: {user_id}")
            
            # Convert user_id to ObjectId
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id
            
            # Get user info
            user_info = User.objects(id=user_oid).first()
            if not user_info:
                return {"success": False, "error": "User not found"}
            
            duel_tree_data = []
            
            # Get all binary slots for this user from tree_placement
            user_slots = TreePlacement.objects(
                user_id=user_oid,
                program='binary'
            ).order_by('slot_no')
            
            # Get unique slot numbers for this user
            slot_numbers = set()
            for slot_placement in user_slots:
                slot_numbers.add(slot_placement.slot_no)
            
            # If no slots found, create default empty slots
            if not slot_numbers:
                slot_numbers = set(range(1, 7))  # Default slots 1-6
            
            for slot_no in sorted(slot_numbers):
                # Get the user's placement for this slot
                slot_placement = user_slots.filter(slot_no=slot_no).first()
                
                # Get slot catalog info for price
                slot_catalog = SlotCatalog.objects(
                    program='binary',
                    slot_no=slot_no,
                    is_active=True
                ).first()
                
                # Get total binary earnings for this user from wallet_ledger
                total_binary_earnings = self._get_total_binary_earnings(user_oid)
                # Convert BNB to USDT (assuming 1 BNB = 300 USDT for display) - keep exact amount
                price = total_binary_earnings * 300 if total_binary_earnings > 0 else (float(slot_catalog.price) if slot_catalog and slot_catalog.price else 0.0)
                
                print(f"Slot {slot_no}: Total binary earnings = {total_binary_earnings} BNB, Price = {price} USDT")
                
                # If price is still 0, use progressive pricing based on slot level
                if price == 0:
                    # Progressive pricing: 100, 200, 300, 400, etc.
                    price = 100 + (slot_no - 1) * 100
                
                # Get slot activation status
                slot_activation = SlotActivation.objects(
                    user_id=user_oid,
                    program='binary',
                    slot_no=slot_no
                ).first()
                
                # Determine status flags based on tree_placement data
                is_completed = slot_activation and slot_activation.status == 'completed'
                is_process = slot_placement and slot_placement.auto_upgrade_eligible
                is_auto_upgrade = slot_placement and slot_placement.auto_upgrade_eligible
                is_manual_upgrade = not is_auto_upgrade and not is_completed
                
                # Calculate process percentage based on children_count
                process_percent = 0
                if slot_placement:
                    # Binary tree needs 2 children (left and right)
                    required_children = 2
                    current_children = slot_placement.children_count or 0
                    process_percent = min(100, (current_children / required_children) * 100)
                
                # Get team members for this slot - create progressive tree structure
                team_members_progressive = self._get_progressive_team_members(user_oid, slot_no)
                
                # Create multiple duel tree items for progressive display
                for i, team_members in enumerate(team_members_progressive):
                    # Use progressive pricing for each level
                    progressive_price = price + (i * 50)  # Each level adds 50
                    
                    # Calculate dynamic process percent based on current level
                    current_level_members = len(team_members)
                    max_possible_members = 2 ** (i + 1)  # Binary tree: 2, 4, 8, 16, etc.
                    dynamic_process_percent = min(100, (current_level_members / max_possible_members) * 100)
                    
                    # Create duel tree data object matching matrixData.js structure
                    duel_tree_item = {
                        "id": i + 1,  # Different ID for each progressive level
                        "price": progressive_price,
                        "userId": str(user_info.uid) if user_info.uid else str(user_oid),
                        "recycle": slot_placement.children_count if slot_placement else 0,
                        "isCompleted": is_completed,
                        "isProcess": is_process,
                        "isAutoUpgrade": is_auto_upgrade,
                        "isManualUpgrade": is_manual_upgrade,
                        "processPercent": int(dynamic_process_percent),
                        "users": team_members
                    }
                    
                    duel_tree_data.append(duel_tree_item)
            
            
            result = {
                "duelTreeData": duel_tree_data,
                "totalSlots": len(duel_tree_data),
                "user_id": str(user_id)
            }
            
            print(f"Duel tree earnings generated: {len(duel_tree_data)} slots")
            return {"success": True, "data": result}
            
        except Exception as e:
            print(f"Error in get_duel_tree_earnings: {e}")
            return {"success": False, "error": str(e)}

    def _get_duel_tree_team_members(self, user_oid, slot_no: int) -> List[Dict[str, Any]]:
        """Get team members for duel tree display based on tree_placement structure"""
        try:
            from ..tree.model import TreePlacement
            from ..user.model import User
            
            # Get the user's own placement record for this slot
            user_placement = TreePlacement.objects(
                user_id=user_oid,
                program='binary',
                slot_no=slot_no
            ).first()
            
            if not user_placement:
                # If no placement found, return just the user
                user_info = User.objects(id=user_oid).first()
                if user_info:
                    user_display_id = str(user_info.uid) if user_info.uid else str(user_oid)
                    return [{
                        "id": 0,
                        "type": "self",
                        "userId": user_display_id
                    }]
                return []
            
            # Get direct children (left and right) under this user
            children = TreePlacement.objects(
                program='binary',
                parent_id=user_oid,
                slot_no=slot_no
            ).order_by('position')
            
            team_members = []
            member_id = 1
            
            # Add the user themselves first
            user_info = User.objects(id=user_oid).first()
            if user_info:
                user_display_id = str(user_info.uid) if user_info.uid else str(user_oid)
                team_members.append({
                    "id": 0,
                    "type": "self",
                    "userId": user_display_id
                })
            
            # Add children based on their position
            for child in children:
                # Get child user info
                child_user = User.objects(id=child.user_id).first()
                user_display_id = str(child_user.uid) if child_user and child_user.uid else str(child.user_id)
                
                # Determine user type based on position and status
                user_type = "self"  # Default
                if child.position == "left":
                    user_type = "downLine"
                elif child.position == "right":
                    user_type = "upLine"
                
                # Check if it's a spillover (overtaker)
                if child.is_spillover:
                    user_type = "overTaker"
                
                team_members.append({
                    "id": member_id,
                    "type": user_type,
                    "userId": user_display_id
                })
                member_id += 1
            
            # If user has a parent, add parent as upline
            if user_placement.parent_id:
                parent_user = User.objects(id=user_placement.parent_id).first()
                if parent_user:
                    parent_display_id = str(parent_user.uid) if parent_user.uid else str(user_placement.parent_id)
                    team_members.append({
                        "id": member_id,
                        "type": "upLine",
                        "userId": parent_display_id
                    })
                    member_id += 1
            
            return team_members
            
        except Exception as e:
            print(f"Error getting duel tree team members: {e}")
            return []

    def _get_user_slot_earnings(self, user_oid, slot_no: int) -> Dict[str, float]:
        """Get user's earnings for a specific slot"""
        try:
            from ..wallet.model import WalletLedger
            
            # Binary related reasons for earnings
            binary_reasons = [
                'binary_joining_commission', 'binary_upgrade_commission', 'binary_partner_incentive',
                'binary_level_commission', 'binary_dual_tree_earning', 'binary_leadership_stipend',
                'binary_royal_captain', 'binary_president_reward', 'binary_jackpot_bonus',
                'binary_upgrade_level_1', 'binary_dual_tree_L1_S1', 'binary_dual_tree_L1_S2'
            ]
            
            # Get earnings for this user
            earnings = WalletLedger.objects(
                user_id=user_oid,
                reason__in=binary_reasons,
                type='credit'
            ).only('amount', 'currency')
            
            total_earnings = {"USDT": 0.0, "BNB": 0.0}
            
            for earning in earnings:
                currency = str(earning.currency).upper() if earning.currency else 'BNB'
                # Handle USD → USDT mapping
                if currency == 'USD':
                    currency = 'USDT'
                
                if currency in total_earnings:
                    total_earnings[currency] += float(earning.amount or 0)
            
            return total_earnings
            
        except Exception as e:
            print(f"Error getting user slot earnings: {e}")
            return {"USDT": 0.0, "BNB": 0.0}

    def _get_progressive_team_members(self, user_oid, slot_no: int) -> List[List[Dict[str, Any]]]:
        """Get progressive team members for duel tree display - creates multiple levels"""
        try:
            from ..tree.model import TreePlacement
            from ..user.model import User
            
            # Get the user's own placement record for this slot
            user_placement = TreePlacement.objects(
                user_id=user_oid,
                program='binary',
                slot_no=slot_no
            ).first()
            
            if not user_placement:
                # If no placement found, return just the user
                user_info = User.objects(id=user_oid).first()
                if user_info:
                    user_display_id = str(user_info.uid) if user_info.uid else str(user_oid)
                    return [[{
                        "id": 0,
                        "type": "self",
                        "userId": user_display_id
                    }]]
                return [[]]
            
            # Get all team members
            all_team_members = self._get_duel_tree_team_members(user_oid, slot_no)
            
            # Create progressive levels - unlimited levels
            progressive_levels = []
            
            # Create progressive levels for all available team members
            for i in range(len(all_team_members)):
                level_members = all_team_members[:i+1]  # Include members up to current level
                progressive_levels.append(level_members)
            
            # If no progressive levels created, return at least the user
            if not progressive_levels:
                user_info = User.objects(id=user_oid).first()
                if user_info:
                    user_display_id = str(user_info.uid) if user_info.uid else str(user_oid)
                    progressive_levels = [[{
                        "id": 0,
                        "type": "self",
                        "userId": user_display_id
                    }]]
            
            return progressive_levels
            
        except Exception as e:
            print(f"Error getting progressive team members: {e}")
            return [[]]

    def _get_tree_income(self, user_oid, slot_no: int) -> float:
        """Get real income from this tree structure"""
        try:
            from ..wallet.model import WalletLedger
            from ..tree.model import TreePlacement
            
            # Get all team members in this tree
            all_team_members = self._get_duel_tree_team_members(user_oid, slot_no)
            
            total_income = 0.0
            
            # Calculate income from each team member
            for member in all_team_members:
                # Get user ID from member
                member_user_id = member.get('userId')
                if not member_user_id:
                    continue
                
                # Find user by UID or ObjectId
                from ..user.model import User
                user = User.objects(uid=member_user_id).first()
                if not user:
                    try:
                        user = User.objects(id=ObjectId(member_user_id)).first()
                    except:
                        continue
                
                if not user:
                    continue
                
                # Get binary earnings for this user - focus on dual tree earnings
                dual_tree_reasons = [
                    'binary_dual_tree_earning',
                    'binary_dual_tree_L1_S1', 
                    'binary_dual_tree_L1_S2',
                    'binary_dual_tree_L2_S1',
                    'binary_dual_tree_L2_S2',
                    'binary_dual_tree_L3_S1',
                    'binary_dual_tree_L3_S2'
                ]
                
                # Get dual tree earnings for this user
                user_earnings = WalletLedger.objects(
                    user_id=user.id,
                    reason__in=dual_tree_reasons,
                    type='credit'
                ).sum('amount') or 0
                
                total_income += float(user_earnings)
            
            # If no dual tree earnings, get all binary earnings
            if total_income == 0.0:
                binary_reasons = [
                    'binary_joining_commission', 'binary_upgrade_commission', 'binary_partner_incentive',
                    'binary_level_commission', 'binary_dual_tree_earning', 'binary_leadership_stipend',
                    'binary_royal_captain', 'binary_president_reward', 'binary_jackpot_bonus',
                    'binary_upgrade_level_1', 'binary_dual_tree_L1_S1', 'binary_dual_tree_L1_S2'
                ]
                
                for member in all_team_members:
                    member_user_id = member.get('userId')
                    if not member_user_id:
                        continue
                    
                    user = User.objects(uid=member_user_id).first()
                    if not user:
                        try:
                            user = User.objects(id=ObjectId(member_user_id)).first()
                        except:
                            continue
                    
                    if not user:
                        continue
                    
                    user_earnings = WalletLedger.objects(
                        user_id=user.id,
                        reason__in=binary_reasons,
                        type='credit'
                    ).sum('amount') or 0
                    
                    total_income += float(user_earnings)
            
            return total_income
            
        except Exception as e:
            print(f"Error getting tree income: {e}")
            return 0.0

    def _get_total_binary_earnings(self, user_oid) -> float:
        """Get total binary earnings for a user from wallet_ledger"""
        try:
            from ..wallet.model import WalletLedger
            
            # All binary earning reasons
            binary_reasons = [
                'binary_joining_commission', 'binary_upgrade_commission', 'binary_partner_incentive',
                'binary_level_commission', 'binary_dual_tree_earning', 'binary_leadership_stipend',
                'binary_royal_captain', 'binary_president_reward', 'binary_jackpot_bonus',
                'binary_upgrade_level_1', 'binary_dual_tree_L1_S1', 'binary_dual_tree_L1_S2'
            ]
            
            # Get total binary earnings in BNB
            total_earnings = WalletLedger.objects(
                user_id=user_oid,
                reason__in=binary_reasons,
                type='credit',
                currency='BNB'
            ).sum('amount') or 0
            
            return float(total_earnings)
            
        except Exception as e:
            print(f"Error getting total binary earnings: {e}")
            return 0.0

    def get_duel_tree_details(self, user_id: str, tree_id: int) -> Dict[str, Any]:
        """Get specific duel tree details by tree ID"""
        try:
            print(f"Getting duel tree details for user: {user_id}, tree_id: {tree_id}")
            
            # Convert user_id to ObjectId
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id
            
            # Get all duel tree earnings first
            all_earnings = self.get_duel_tree_earnings(user_id)
            
            if not all_earnings["success"]:
                return {"success": False, "error": all_earnings["error"]}
            
            # Find the specific tree by ID
            duel_tree_data = all_earnings["data"]["duelTreeData"]
            target_tree = None
            
            print(f"Available tree IDs: {[tree['id'] for tree in duel_tree_data]}")
            
            for tree in duel_tree_data:
                if tree["id"] == tree_id:
                    target_tree = tree
                    break
            
            if not target_tree:
                return {"success": False, "error": f"Tree with ID {tree_id} not found. Available IDs: {[tree['id'] for tree in duel_tree_data]}"}
            
            return {
                "success": True,
                "data": target_tree
            }
            
        except Exception as e:
            print(f"Error getting duel tree details: {e}")
            return {"success": False, "error": str(e)}