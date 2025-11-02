from typing import Dict, Any, Optional, List
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta
from mongoengine.errors import ValidationError
import os
import time

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
    
    # Cache for team member counts: {user_id_str: (count, timestamp)}
    _team_count_cache = {}
    _cache_ttl_seconds = 300  # 5 minutes cache TTL
    
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
            
            # 3. Distribute funds to all bonus pools (PROJECT_DOCUMENTATION.md Section 32)
            try:
                from modules.fund_distribution.service import FundDistributionService
                fund_service = FundDistributionService()
                
                # Get referrer for partner incentive
                referrer_id = str(user.refered_by) if user.refered_by else None
                
                # Pass original BNB amount (not converted to USD) for proper wallet crediting
                distribution_result = fund_service.distribute_binary_funds(
                    user_id=user_id,
                    amount=amount,  # Original BNB amount
                    slot_no=slot_no,
                    referrer_id=referrer_id,
                    tx_hash=tx_hash,
                    currency=currency  # Pass currency (BNB)
                )
                
                if distribution_result.get('success'):
                    print(f"✅ Binary funds distributed: {distribution_result.get('total_distributed')} {currency}")
                else:
                    print(f"⚠️ Binary fund distribution failed: {distribution_result.get('error')}")
            except Exception as e:
                print(f"⚠️ Binary fund distribution error: {e}")
            
            # 3b. Process upgrade commission (30% to corresponding level upline + 70% dual tree distribution)
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
            
            # 6. Auto-join Leadership Stipend and check eligibility (slots 10-17)
            if slot_no >= 10:
                # Auto-join if not already joined
                from modules.leadership_stipend.model import LeadershipStipend
                ls_existing = LeadershipStipend.objects(user_id=ObjectId(user_id)).first()
                if not ls_existing:
                    join_result = self.leadership_stipend_service.join_leadership_stipend_program(user_id)
                    print(f"Leadership Stipend auto-join for user {user_id} slot {slot_no}: {join_result}")
                
                # Check eligibility
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
            
            # 11. Auto-upgrade is reserve-driven; no partner-count based trigger here
            try:
                # Optionally ping reserve service to process any pending auto-activations
                from modules.user.tree_reserve_service import TreeUplineReserveService
                TreeUplineReserveService().process_pending_auto_upgrades(program='binary')
            except Exception as e:
                print(f"⚠️ Reserve auto-upgrade processing skipped: {e}")
            
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
                # BinarySlotInfo does not have slot_no; compare by slot_name
                if getattr(slot_info, 'slot_name', None) == slot_name:
                    slot_info.is_active = True
                    slot_info.activated_at = datetime.utcnow()
                    slot_exists = True
                    break
            
            # Add new slot if not exists
            if not slot_exists:
                from ..user.model import BinarySlotInfo
                # derive level from catalog if available
                level = slot_no
                try:
                    catalog = SlotCatalog.objects(program='binary', slot_no=slot_no, is_active=True).first()
                    if catalog and getattr(catalog, 'level', None) is not None:
                        level = catalog.level
                except Exception:
                    pass
                new_slot = BinarySlotInfo(
                    slot_name=slot_name,
                    slot_value=float(amount),
                    level=level,
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
            # IMPORTANT: Count unique users only (ignore multiple slots)
            team_stats = {
                "total_team": 0,
                "today_team": 0,
                "today_direct": 0
            }
            try:
                # Total team count (unique users across all levels)
                def collect_all_descendant_user_ids(parent_user_id, seen_users=None):
                    """Collect unique user IDs from all levels"""
                    if seen_users is None:
                        seen_users = set()
                    
                    # Get all children using upline_id for tree structure
                    children = TreePlacement.objects(
                        program='binary',
                        upline_id=parent_user_id
                    )
                    
                    for child in children:
                        # Only add if not already seen (handles multiple slots)
                        user_id_str = str(child.user_id)
                        if user_id_str not in seen_users:
                            seen_users.add(user_id_str)
                            # Recurse for this user's children
                            collect_all_descendant_user_ids(child.user_id, seen_users)
                    
                    return seen_users
                
                unique_team_users = collect_all_descendant_user_ids(user_oid)
                team_stats["total_team"] = len(unique_team_users)
                
                # Today team count (unique users who joined today)
                def collect_today_descendant_user_ids(parent_user_id, seen_users=None):
                    """Collect unique user IDs who joined today"""
                    if seen_users is None:
                        seen_users = set()
                    
                    # Get children who joined today
                    children = TreePlacement.objects(
                        program='binary',
                        upline_id=parent_user_id,
                        created_at__gte=today_start,
                        created_at__lte=today_end
                    )
                    
                    for child in children:
                        user_id_str = str(child.user_id)
                        if user_id_str not in seen_users:
                            seen_users.add(user_id_str)
                            # Continue recursively for children of this user
                            collect_today_descendant_user_ids(child.user_id, seen_users)
                    
                    return seen_users
                
                unique_today_team = collect_today_descendant_user_ids(user_oid)
                team_stats["today_team"] = len(unique_today_team)
                
                # Today direct count (unique direct referrals today)
                # Get direct referrals using parent_id
                today_direct_placements = TreePlacement.objects(
                    program='binary',
                    parent_id=user_oid,
                    created_at__gte=today_start,
                    created_at__lte=today_end
                )
                
                # Count unique user_ids only
                unique_direct_users = set()
                for placement in today_direct_placements:
                    unique_direct_users.add(str(placement.user_id))
                
                team_stats["today_direct"] = len(unique_direct_users)
                
                print(f"Team stats for user {user_id} (unique users): {team_stats}")
                
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
            # Use parent_id for direct referrals count (not tree placement)
            direct_members = TreePlacement.objects(
                program='binary',
                parent_id=user_oid
            ).count()
            
            # Get total team members (recursive count)
            def count_total_team(parent_id):
                total = 0
                # Use upline_id for tree structure traversal
                children = TreePlacement.objects(
                    program='binary',
                    upline_id=parent_id
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
            
            # Use upline_id for tree structure
            team_members = TreePlacement.objects(
                program='binary',
                upline_id=user_oid
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
        Return Binary tree overview for a user with:
        - tree: full downline nodes under the user (binary program)
        - slots: 1..17 slot catalog with name/value and completion/progress info
        """
        try:
            from ..tree.model import TreePlacement
            from ..slot.model import SlotActivation, SlotCatalog
            from ..wallet.model import WalletLedger
            from ..user.model import User
            from ..auto_upgrade.model import BinaryAutoUpgrade
            
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
            
            # Build nested downline tree nodes (limited to 3 levels: 0, 1, 2)
            # This gives maximum 7 users: 1 + 2 + 4 = 7
            root_node, depth, total_nodes_count = self._build_nested_binary_tree_limited(user_oid, max_levels=3)
            
            # Calculate ACTUAL total team members (ALL levels, not just 3)
            # This is needed for slot progress calculation
            actual_total_team_members = self._count_all_team_members(user_oid)
            
            # Member requirements for each slot (from PROJECT_DOCUMENTATION.md)
            # Slot 1: no requirement (auto-activated)
            # Slot 2: 2 members, Slot 3: 4 members, Slot 4: 8 members, etc. (2^level pattern)
            slot_member_requirements = {
                1: 0,      # Explorer - no requirement
                2: 2,      # Contributor - Level 1
                3: 4,      # Subscriber - Level 2
                4: 8,      # Dreamer - Level 3
                5: 16,     # Planner - Level 4
                6: 32,     # Challenger - Level 5
                7: 64,     # Adventurer - Level 6
                8: 128,    # Game-Shifter - Level 7
                9: 256,    # Organizer - Level 8
                10: 512,   # Leader - Level 9
                11: 1024,  # Vanguard - Level 10
                12: 2048,  # Center - Level 11
                13: 4096,  # Climax - Level 12
                14: 8192,  # Eternity - Level 13
                15: 16384, # King - Level 14
                16: 32768, # Commander - Level 15
                17: 65536  # CEO - Level 16 (extrapolated)
            }
            
            # Gather slot catalog 1..17 for binary; fallback to defaults if catalog is empty
            catalogs = SlotCatalog.objects(program='binary').order_by('slot_no')
            catalog_by_slot = {c.slot_no: c for c in catalogs}
            # Default slot costs (BNB) when catalog is missing; slot 17 extrapolated
            default_slot_costs = {
                1: 0.0022, 2: 0.0044, 3: 0.0088, 4: 0.0176, 5: 0.0352, 6: 0.0704,
                7: 0.1408, 8: 0.2816, 9: 0.5632, 10: 1.1264, 11: 2.2528, 12: 4.5056,
                13: 9.0112, 14: 18.0224, 15: 36.0448, 16: 72.0896, 17: 144.1792
            }
            max_slot_no = max(catalog_by_slot.keys()) if catalog_by_slot else 17
            # Ensure we cover up to 17 as per documentation
            target_max_slot = max(17, max_slot_no)
            
            # Activated/completed slots for this user
            activated = SlotActivation.objects(user_id=user_oid, program='binary', status='completed')
            completed_slots = {a.slot_no for a in activated}
            
            # IMPORTANT: For completion state in UI, rely strictly on actual SlotActivation
            # to match wallet statistics and avoid inflating via team member counts.
            all_completed_slots = set(completed_slots)
            
            # Find highest completed slot
            highest_completed_slot = max(all_completed_slots) if all_completed_slots else 0
            
            # Next slot for manual upgrade (slot after highest completed)
            next_manual_upgrade_slot = highest_completed_slot + 1 if highest_completed_slot < target_max_slot else None
            
            # Build slots summary array
            slots_summary = []
            for slot_no in range(1, target_max_slot + 1):
                catalog = catalog_by_slot.get(slot_no)
                slot_name = catalog.name if catalog and getattr(catalog, 'name', None) else f"Slot {slot_no}"
                if catalog and getattr(catalog, 'price', None) is not None:
                    slot_value = float(catalog.price)
                else:
                    slot_value = float(default_slot_costs.get(slot_no, 0.0))
                
                # Check if slot is completed
                is_completed = slot_no in all_completed_slots
                
                # Check if this is the slot available for manual upgrade
                is_manual_upgrade = (slot_no == next_manual_upgrade_slot)
                
                # Calculate progress percentage
                required_members = slot_member_requirements.get(slot_no, 0)
                if is_completed:
                    # Completed slots show 100%
                    progress_percent = 100
                elif slot_no == next_manual_upgrade_slot:
                    # Next slot shows progress toward completion
                    if required_members > 0:
                        progress_percent = int(min(100, (actual_total_team_members / required_members) * 100))
                    else:
                        progress_percent = 0
                else:
                    # Other slots show 0%
                    progress_percent = 0
                
                slots_summary.append({
                    "slot_no": slot_no,
                    "slot_name": slot_name,
                    "slot_value": slot_value,
                    "isCompleted": is_completed,
                    "isManualUpgrade": is_manual_upgrade,
                    "progressPercent": progress_percent
                })
            
            # Convert root node to array format for backward compatibility if needed
            # But since we're changing the structure, we'll keep it nested
            result = {
                "tree": {
                    "userId": str(user_info.uid) if user_info and user_info.uid else str(user_oid),
                    "totalMembers": actual_total_team_members,  # Use actual total team count (all levels), not limited tree visualization
                    "levels": depth,  # Depth of the visualized tree (limited to 3 levels for performance)
                    "nodes": [root_node]  # Root node with nested directDownline structure (limited to 3 levels for visualization)
                },
                "slots": slots_summary,
                "totalSlots": len(slots_summary),
                "user_id": str(user_id)
            }
            
            print(f"Binary tree overview generated: nodes={total_nodes_count}, slots={len(slots_summary)}")
            return {"success": True, "data": result}
            
        except Exception as e:
            print(f"Error in get_duel_tree_earnings: {e}")
            return {"success": False, "error": str(e)}

    def _build_binary_downline_nodes(self, user_oid) -> (List[Dict[str, Any]], int):
        """Build a flat list of nodes representing the user's binary downline tree.
        Returns (nodes, max_depth). Each node has: id, type, userId, level, position.
        The first node is the self node (level=0)."""
        try:
            from ..tree.model import TreePlacement
            from ..user.model import User
            
            # Helper to get display id
            def display_id(oid) -> str:
                try:
                    u = User.objects(id=oid).only('uid').first()
                    return str(u.uid) if u and u.uid else str(oid)
                except Exception:
                    return str(oid)
            
            nodes: List[Dict[str, Any]] = []
            max_depth = 0
            # Add self node
            nodes.append({
                "id": 0,
                "type": "self",
                "userId": display_id(user_oid),
                "level": 0,
                "position": "root"
            })
            
            # BFS traversal across all slots combined (binary program)
            queue = [(user_oid, 0)]
            visited = {str(user_oid)}  # Deduplicate by user id string
            next_node_id = 1
            while queue:
                parent_id, level = queue.pop(0)
                max_depth = max(max_depth, level)
                # Fetch children under binary regardless of slot (aggregate view)
                # Use upline_id for tree structure traversal
                children = TreePlacement.objects(program='binary', upline_id=parent_id).order_by('created_at')
                for child in children:
                    child_id_str = str(child.user_id)
                    if child_id_str in visited:
                        continue
                    visited.add(child_id_str)
                    node = {
                        "id": next_node_id,
                        "type": "downLine",
                        "userId": display_id(child.user_id),
                        "level": level + 1,
                        "position": getattr(child, 'position', 'left')
                    }
                    nodes.append(node)
                    next_node_id += 1
                    queue.append((child.user_id, level + 1))
            return nodes, max_depth
        except Exception:
            return [{"id": 0, "type": "self", "userId": str(user_oid), "level": 0, "position": "root"}], 0

    def _build_nested_binary_tree_limited(self, user_oid, max_levels: int = 3) -> (Dict[str, Any], int):
        """
        Build a nested tree structure with directDownline arrays for binary program.
        Limited to max_levels (default 3: level 0, 1, 2).
        Maximum 7 users: 1 (root) + 2 (level 1) + 4 (level 2) = 7
        Returns (root_node, max_depth, total_count).
        Each node has: id, type, userId, level, position, directDownline (array of child nodes).
        """
        try:
            from ..tree.model import TreePlacement
            from ..user.model import User
            
            # Helper to get display id
            def display_id(oid) -> str:
                try:
                    u = User.objects(id=oid).only('uid').first()
                    return str(u.uid) if u and u.uid else str(oid)
                except Exception:
                    return str(oid)
            
            # Counter for node IDs
            node_id_counter = [0]
            total_count = [0]
            
            # Helper to build node recursively with level limit
            def build_node(parent_oid, level: int, position: str) -> Dict[str, Any]:
                # Stop if we've exceeded max levels (0-indexed, so level 0, 1, 2 for max_levels=3)
                if level >= max_levels:
                    return None
                
                # Increment total count
                total_count[0] += 1
                
                # Get current node ID and increment counter
                current_id = node_id_counter[0]
                node_id_counter[0] += 1
                
                # Determine node type
                node_type = "self" if level == 0 else "downLine"
                
                # Create the node
                node = {
                    "id": current_id,
                    "type": node_type,
                    "userId": display_id(parent_oid),
                    "level": level,
                    "position": position
                }
                
                # Only get children if we're not at the last level
                if level < max_levels - 1:
                    # Get direct children from TreePlacement (only take first left and first right)
                    # This ensures binary tree structure (max 2 children per node)
                    # Use upline_id to get actual tree placement children (not direct referrals)
                    left_child = TreePlacement.objects(
                        program='binary',
                        upline_id=parent_oid,
                        position='left'
                    ).order_by('created_at').first()
                    
                    right_child = TreePlacement.objects(
                        program='binary',
                        upline_id=parent_oid,
                        position='right'
                    ).order_by('created_at').first()
                    
                    # Build directDownline array
                    direct_downline = []
                    
                    # Add left child first
                    if left_child:
                        left_node = build_node(
                            left_child.user_id,
                            level + 1,
                            'left'
                        )
                        if left_node:
                            direct_downline.append(left_node)
                    
                    # Add right child second
                    if right_child:
                        right_node = build_node(
                            right_child.user_id,
                            level + 1,
                            'right'
                        )
                        if right_node:
                            direct_downline.append(right_node)
                    
                    # Add directDownline array to node if there are children
                    if direct_downline:
                        node["directDownline"] = direct_downline
                
                return node
            
            # Start building from root
            root_node = build_node(user_oid, 0, "root")
            
            # Calculate max depth by traversing the tree
            def calculate_depth(node: Dict[str, Any]) -> int:
                if not node:
                    return 0
                if "directDownline" not in node or not node["directDownline"]:
                    return node.get("level", 0)
                return max(calculate_depth(child) for child in node["directDownline"])
            
            max_depth = calculate_depth(root_node) if root_node else 0
            
            return root_node, max_depth, total_count[0]
            
        except Exception as e:
            print(f"Error in _build_nested_binary_tree_limited: {e}")
            return {
                "id": 0,
                "type": "self",
                "userId": str(user_oid),
                "level": 0,
                "position": "root"
            }, 0, 1

    def _count_all_team_members(self, user_oid, use_cache: bool = True, timeout_seconds: float = 10.0) -> int:
        """
        Count ALL team members under a user using optimized BFS traversal (all levels)
        Used for slot progress calculation based on member requirements.
        
        Optimizations:
        - Uses BFS instead of recursive DFS to reduce stack depth
        - Implements caching to avoid frequent recalculations
        - Uses visited set to prevent infinite loops
        - Adds timeout protection for very large trees
        - Batches queries where possible
        
        Args:
            user_oid: User ObjectId to count team members for
            use_cache: Whether to use cached values (default: True)
            timeout_seconds: Maximum time to spend counting (default: 10 seconds)
        
        Returns:
            Total count of team members, or cached/0 if timeout
        """
        try:
            from ..tree.model import TreePlacement
            
            user_id_str = str(user_oid)
            
            # Check cache first
            if use_cache:
                cache_entry = self._team_count_cache.get(user_id_str)
                if cache_entry:
                    count, timestamp = cache_entry
                    # Check if cache is still valid (within TTL)
                    if time.time() - timestamp < self._cache_ttl_seconds:
                        print(f"Using cached team count for user {user_id_str}: {count}")
                        return count
                    else:
                        # Cache expired, remove it
                        del self._team_count_cache[user_id_str]
            
            start_time = time.time()
            visited = set()
            queue = [user_oid]
            visited.add(user_id_str)
            total_count = 0
            max_depth = 50  # Safety limit to prevent infinite loops
            depth = 0
            batch_size = 1000  # Process in batches to avoid memory issues
            
            # BFS traversal instead of recursive DFS
            while queue and (time.time() - start_time) < timeout_seconds:
                # Process current level
                current_level = queue
                queue = []
                
                # Batch query: get all children for current level users at once
                if current_level:
                    # Query all children of users in current level
                    children_batch = TreePlacement.objects(
                        program='binary',
                        upline_id__in=current_level,
                        is_active=True
                    ).only('user_id', 'upline_id')
                    
                    # Count unique children
                    children_list = []
                    for child in children_batch:
                        child_id_str = str(child.user_id)
                        if child_id_str not in visited:
                            visited.add(child_id_str)
                            children_list.append(child.user_id)
                            total_count += 1
                    
                    # Add children to next level queue
                    if children_list:
                        queue.extend(children_list)
                
                depth += 1
                if depth >= max_depth:
                    print(f"Warning: Reached max depth {max_depth} for user {user_id_str}, stopping count")
                    break
                
                # Memory optimization: clear visited set if it gets too large
                if len(visited) > 50000:  # If more than 50k nodes visited
                    # Keep only recent entries to prevent memory issues
                    # This is a tradeoff - might recount some nodes but prevents OOM
                    visited.clear()
                    visited.add(user_id_str)  # Keep root user
                    print(f"Warning: Large tree detected for user {user_id_str}, cleared visited set to prevent memory issues")
            
            # Check if we hit timeout
            if (time.time() - start_time) >= timeout_seconds:
                print(f"Warning: Team count calculation timed out for user {user_id_str} after {timeout_seconds}s")
                # Return current count (may be partial)
                # Try to use cached value if available (from previous successful calculation)
                cache_entry = self._team_count_cache.get(user_id_str)
                if cache_entry:
                    cached_count, _ = cache_entry
                    print(f"Returning cached count due to timeout: {cached_count}")
                    return cached_count
                # Otherwise return partial count (better than 0)
                print(f"Returning partial count due to timeout: {total_count}")
                return total_count
            
            # Store in cache
            if use_cache:
                self._team_count_cache[user_id_str] = (total_count, time.time())
                # Clean up old cache entries (keep cache size manageable)
                if len(self._team_count_cache) > 1000:
                    current_time = time.time()
                    expired_keys = [
                        key for key, (_, ts) in self._team_count_cache.items()
                        if current_time - ts > self._cache_ttl_seconds
                    ]
                    for key in expired_keys[:500]:  # Remove up to 500 expired entries
                        del self._team_count_cache[key]
            
            print(f"Counted {total_count} team members for user {user_id_str} in {time.time() - start_time:.2f}s")
            return total_count
            
        except Exception as e:
            try:
                user_id_str = str(user_oid)
            except:
                user_id_str = "unknown"
            print(f"Error counting team members for user {user_id_str}: {e}")
            # Try to return cached value on error
            cache_entry = self._team_count_cache.get(user_id_str) if user_id_str != "unknown" else None
            if cache_entry:
                cached_count, _ = cache_entry
                print(f"Returning cached count due to error: {cached_count}")
                return cached_count
            return 0

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
            # Use upline_id for tree structure
            children = TreePlacement.objects(
                program='binary',
                upline_id=user_oid,
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
            
            # Get the tree data from the new structure
            tree_data = all_earnings["data"].get("tree")
            
            if not tree_data or not tree_data.get("nodes"):
                return {"success": False, "error": "No tree data found"}
            
            # Since we now have nested structure, we need to find node by tree_id
            # The tree_id corresponds to node id in the nested structure
            def find_node_by_id(nodes, target_id):
                """Recursively find a node by its id"""
                for node in nodes:
                    if node.get("id") == target_id:
                        return node
                    if "directDownline" in node:
                        found = find_node_by_id(node["directDownline"], target_id)
                        if found:
                            return found
                return None
            
            target_node = find_node_by_id(tree_data["nodes"], tree_id)
            
            if not target_node:
                return {"success": False, "error": f"Node with ID {tree_id} not found in tree"}
            
            return {
                "success": True,
                "data": target_node
            }
            
        except Exception as e:
            print(f"Error getting duel tree details: {e}")
            return {"success": False, "error": str(e)}
    
    def check_and_trigger_binary_auto_upgrade(self, user_id: str, slot_no: int):
        """
        Deprecated: Auto-upgrade is exclusively reserve-driven based on positional routing.
        This method intentionally does nothing to avoid partner-count-based upgrades.
        """
        try:
            print("[BINARY] check_and_trigger_binary_auto_upgrade is deprecated; skipping.")
            return None
        except Exception:
            return None