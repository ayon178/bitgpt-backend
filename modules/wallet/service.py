from decimal import Decimal
from datetime import datetime
from bson import ObjectId
from .model import UserWallet, WalletLedger, ReserveLedger
from ..slot.model import SlotActivation
import re
from typing import Dict, Any


class WalletService:
    """Wallet operations: credit/debit user main wallet with ledger entries."""

    def __init__(self) -> None:
        pass

    def _get_or_create_wallet(self, user_id: str, wallet_type: str = 'main', currency: str = 'USDT') -> UserWallet:
        wallet = UserWallet.objects(user_id=ObjectId(user_id), wallet_type=wallet_type, currency=currency).first()
        if not wallet:
            wallet = UserWallet(user_id=ObjectId(user_id), wallet_type=wallet_type, currency=currency)
            wallet.balance = Decimal('0')
            wallet.save()
        return wallet

    def credit_main_wallet(self, user_id: str, amount: Decimal, currency: str, reason: str, tx_hash: str) -> dict:
        wallet = self._get_or_create_wallet(user_id, 'main', currency)
        new_balance = (wallet.balance or Decimal('0')) + Decimal(str(amount))
        wallet.balance = new_balance
        wallet.last_updated = datetime.utcnow()
        wallet.save()
        WalletLedger(
            user_id=ObjectId(user_id),
            amount=Decimal(str(amount)),
            currency=currency,
            type='credit',
            reason=reason,
            balance_after=new_balance,
            tx_hash=tx_hash,
            created_at=datetime.utcnow()
        ).save()
        return {"success": True, "balance": float(new_balance)}

    def get_currency_balances(self, user_id: str, wallet_type: str = 'main') -> dict:
        """Return all balances for a user grouped by currency for a given wallet_type."""
        wallets = UserWallet.objects(user_id=ObjectId(user_id), wallet_type=wallet_type).only('currency', 'balance')
        # Only two supported currencies for output: USDT and BNB
        result = {"USDT": 0.0, "BNB": 0.0}
        for w in wallets:
            currency = (str(getattr(w, 'currency', '')).upper() or 'USDT')
            if currency in result:
                result[currency] = float(w.balance or Decimal('0'))

        # Today's income totals and distinct source counts per currency from WalletLedger
        start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_entries = WalletLedger.objects(
            user_id=ObjectId(user_id),
            created_at__gte=start_of_day,
            type='credit'
        ).only('amount', 'currency', 'tx_hash')

        today_income = {"USDT": 0.0, "BNB": 0.0}
        # Track unique sources across all currencies (deduplicated)
        today_sources_set = set()

        # Heuristic: extract a 24-hex substring from tx_hash to infer source user id if present
        hex24 = re.compile(r"[0-9a-fA-F]{24}")
        for entry in today_entries:
            curr = (str(getattr(entry, 'currency', '')).upper() or 'USDT')
            if curr in today_income:
                amt = float(getattr(entry, 'amount', 0) or 0)
                today_income[curr] += amt
            txh = str(getattr(entry, 'tx_hash', '') or '')
            m = hex24.search(txh)
            if m:
                today_sources_set.add(m.group(0))

        # Calculate missing profit for USDT and BNB
        missing_profit = {"USDT": 0.0, "BNB": 0.0}
        try:
            from ..missed_profit.model import MissedProfit
            
            # Get all missed profits for this user (total amounts by currency)
            missed_queryset = MissedProfit.objects(
                user_id=ObjectId(user_id)
            ).only('missed_profit_amount', 'currency')

            for missed in missed_queryset:
                currency = (str(getattr(missed, 'currency', '')).upper() or 'USDT')
                if currency in missing_profit:
                    amount = float(getattr(missed, 'missed_profit_amount', 0) or 0)
                    missing_profit[currency] += amount
            
            print(f"Missing profit for user {user_id}: USDT={missing_profit['USDT']}, BNB={missing_profit['BNB']}")
            
        except Exception as e:
            print(f"Error calculating missing profit for user {user_id}: {e}")
            # Keep missing_profit as zeros if calculation fails

        # Calculate total deposits (user debits + program join/upgrade amounts)
        total_deposit = {"USDT": 0.0, "BNB": 0.0}
        try:
            # Reserve ledger debits represent funds flowing out of the user's reserve
            # (manual deposits, auto-upgrade deductions, wallet withdrawals to reserve, etc.)
            reserve_debits = ReserveLedger.objects(
                user_id=ObjectId(user_id),
                direction='debit'
            ).only('amount', 'program')

            for entry in reserve_debits:
                amount = float(getattr(entry, 'amount', 0) or 0)
                if amount <= 0:
                    continue
                program = getattr(entry, 'program', 'binary') or 'binary'
                currency = 'BNB' if program == 'binary' else 'USDT'
                if currency not in total_deposit:
                    total_deposit[currency] = 0.0
                total_deposit[currency] += amount

            # Initial join amounts from SlotActivation records
            user_oid = ObjectId(user_id)

            # Binary join (slots 1 & 2 auto-activated)
            binary_initial = SlotActivation.objects(
                user_id=user_oid,
                program='binary',
                slot_no__in=[1, 2],
                activation_type='initial'
            ).only('amount_paid', 'currency')
            for act in binary_initial:
                amt = float(getattr(act, 'amount_paid', 0) or 0)
                curr = (str(getattr(act, 'currency', '')).upper() or 'BNB')
                if curr not in total_deposit:
                    total_deposit[curr] = 0.0
                total_deposit[curr] += amt

			# Binary manual upgrades (manual activation records)
			binary_manual = SlotActivation.objects(
				user_id=user_oid,
				program='binary',
				activation_type='manual'
			).only('amount_paid', 'currency')
			for act in binary_manual:
				amt = float(getattr(act, 'amount_paid', 0) or 0)
				if amt <= 0:
					continue
				curr = (str(getattr(act, 'currency', '')).upper() or 'BNB')
				if curr not in total_deposit:
					total_deposit[curr] = 0.0
				total_deposit[curr] += amt

            # Matrix join (slot 1 initial activation)
            matrix_initial = SlotActivation.objects(
                user_id=user_oid,
                program='matrix',
                slot_no=1,
                activation_type='initial'
            ).only('amount_paid', 'currency')
            for act in matrix_initial:
                amt = float(getattr(act, 'amount_paid', 0) or 0)
                curr = (str(getattr(act, 'currency', '')).upper() or 'USDT')
                if curr not in total_deposit:
                    total_deposit[curr] = 0.0
                total_deposit[curr] += amt

            # Matrix slot upgrades (any slot number)
            matrix_upgrades = SlotActivation.objects(
                user_id=user_oid,
                program='matrix',
                activation_type='upgrade'
            ).only('amount_paid', 'currency')
            for act in matrix_upgrades:
                amt = float(getattr(act, 'amount_paid', 0) or 0)
                if amt <= 0:
                    continue
                curr = (str(getattr(act, 'currency', '')).upper() or 'USDT')
                if curr not in total_deposit:
                    total_deposit[curr] = 0.0
                total_deposit[curr] += amt

            # Global join (slot 1 initial activation)
            global_initial = SlotActivation.objects(
                user_id=user_oid,
                program='global',
                slot_no=1,
                activation_type='initial'
            ).only('amount_paid', 'currency')
            for act in global_initial:
                amt = float(getattr(act, 'amount_paid', 0) or 0)
                curr = (str(getattr(act, 'currency', '')).upper() or 'USDT')
                if curr not in total_deposit:
                    total_deposit[curr] = 0.0
                total_deposit[curr] += amt

        except Exception as e:
            print(f"Error calculating total deposits for user {user_id}: {e}")
            # Keep totals as-is if calculation fails

        return {
            "success": True,
            "wallet_type": wallet_type,
            "balances": result,
            "today_income": today_income,
            # Single deduplicated count across currencies
            "today_sources": len(today_sources_set),
            "missing_profit": missing_profit,
            "total_deposit": total_deposit,
        }

    def reconcile_main_from_ledger(self, user_id: str) -> dict:
        """Rebuild main wallet balances per currency from wallet ledger (credits - debits)."""
        entries = WalletLedger.objects(user_id=ObjectId(user_id)).only('amount', 'currency', 'type')
        totals = {"USDT": Decimal('0'), "BNB": Decimal('0')}
        for e in entries:
            curr = (str(getattr(e, 'currency', '')).upper() or 'USDT')
            if curr not in totals:
                continue
            amt = Decimal(str(getattr(e, 'amount', 0) or 0))
            if getattr(e, 'type', '') == 'credit':
                totals[curr] += amt
            elif getattr(e, 'type', '') == 'debit':
                totals[curr] -= amt

        # Upsert UserWallet for each currency under wallet_type 'main'
        for curr, total in totals.items():
            wallet = UserWallet.objects(user_id=ObjectId(user_id), wallet_type='main', currency=curr).first()
            if not wallet:
                wallet = UserWallet(user_id=ObjectId(user_id), wallet_type='main', currency=curr)
            wallet.balance = total
            wallet.last_updated = datetime.utcnow()
            wallet.save()

        return {
            "success": True,
            "wallet_type": 'main',
            "balances": {k: float(v) for k, v in totals.items()}
        }

    def debit_main_wallet(self, user_id: str, amount: Decimal, currency: str, reason: str, tx_hash: str) -> dict:
        wallet = self._get_or_create_wallet(user_id, 'main', currency)
        new_balance = (wallet.balance or Decimal('0')) - Decimal(str(amount))
        if new_balance < 0:
            return {"success": False, "error": "Insufficient balance"}
        wallet.balance = new_balance
        wallet.last_updated = datetime.utcnow()
        wallet.save()
        WalletLedger(
            user_id=ObjectId(user_id),
            amount=Decimal(str(amount)),
            currency=currency,
            type='debit',
            reason=reason,
            balance_after=new_balance,
            tx_hash=tx_hash,
            created_at=datetime.utcnow()
        ).save()
        return {"success": True, "balance": float(new_balance)}

    def get_earning_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get earning statistics for a user from all programs (binary, matrix, global)
        Returns total earnings per program and highest activated slot for each
        OPTIMIZED: Fetch once, calculate in Python
        """
        try:
            import time
            start_time = time.time()
            
            user_oid = ObjectId(user_id)
            
            # Initialize earnings counters
            binary_earnings = {"USDT": Decimal('0'), "BNB": Decimal('0')}
            matrix_earnings = {"USDT": Decimal('0'), "BNB": Decimal('0')}
            global_earnings = {"USDT": Decimal('0'), "BNB": Decimal('0')}
            
            query_start = time.time()
            
            # Fetch ALL credit entries for this user in ONE query (faster than multiple regex queries)
            all_credits = WalletLedger.objects(
                user_id=user_oid,
                type='credit'
            ).only('amount', 'currency', 'reason')
            
            print(f"Fetched {all_credits.count()} credit entries")
            
            # Calculate earnings in Python (faster than MongoDB regex)
            for entry in all_credits:
                reason = str(entry.reason or '').lower()
                currency = str(entry.currency or 'USDT').upper()
                amount = Decimal(str(entry.amount or 0))
                
                # Ensure currency key exists
                if currency not in binary_earnings:
                    binary_earnings[currency] = Decimal('0')
                if currency not in matrix_earnings:
                    matrix_earnings[currency] = Decimal('0')
                if currency not in global_earnings:
                    global_earnings[currency] = Decimal('0')
                
                # Categorize by program
                if reason.startswith('binary_'):
                    binary_earnings[currency] += amount
                elif reason.startswith('matrix_'):
                    matrix_earnings[currency] += amount
                elif reason.startswith('global_'):
                    global_earnings[currency] += amount
            
            query_end = time.time()
            print(f"Data fetch + calculation time: {query_end - query_start:.3f}s")
            
            # Get highest activated slots - optimized with only() to fetch minimal data
            slot_start = time.time()
            
            # Binary slot (from SlotActivation)
            binary_slot_data = SlotActivation.objects(
                user_id=user_oid, program='binary', status='completed'
            ).only('slot_no', 'slot_name', 'activated_at', 'created_at').order_by('-slot_no').first()
            
            binary_slot = {}
            if binary_slot_data:
                binary_slot = {
                    "slot_no": binary_slot_data.slot_no,
                    "slot_name": binary_slot_data.slot_name,
                    "activated_at": binary_slot_data.activated_at or binary_slot_data.created_at
                }
            
            # Matrix slot (from MatrixActivation)
            from ..matrix.model import MatrixActivation
            matrix_slot_data = MatrixActivation.objects(
                user_id=user_oid, status='completed'
            ).only('slot_no', 'slot_name', 'activated_at', 'completed_at').order_by('-slot_no').first()
            
            matrix_slot = {}
            if matrix_slot_data:
                matrix_slot = {
                    "slot_no": matrix_slot_data.slot_no,
                    "slot_name": matrix_slot_data.slot_name,
                    "activated_at": matrix_slot_data.activated_at or matrix_slot_data.completed_at
                }
            
            # Global slot (from SlotActivation)
            global_slot_data = SlotActivation.objects(
                user_id=user_oid, program='global', status='completed'
            ).only('slot_no', 'slot_name', 'activated_at', 'created_at').order_by('-slot_no').first()
            
            global_slot = {}
            if global_slot_data:
                global_slot = {
                    "slot_no": global_slot_data.slot_no,
                    "slot_name": global_slot_data.slot_name,
                    "activated_at": global_slot_data.activated_at or global_slot_data.created_at
                }
            
            slot_end = time.time()
            print(f"Slot queries time: {slot_end - slot_start:.3f}s")
            
            end_time = time.time()
            total_time = end_time - start_time
            print(f"TOTAL TIME: {total_time:.3f}s")
            
            return {
                "success": True,
                "data": {
                    "binary": {
                        "total_earnings": {
                            "USDT": float(binary_earnings.get("USDT", Decimal('0'))),
                            "BNB": float(binary_earnings.get("BNB", Decimal('0')))
                        },
                        "highest_activated_slot": binary_slot.get("slot_no") if binary_slot else 0,
                        "highest_activated_slot_name": binary_slot.get("slot_name") if binary_slot else "N/A",
                        "activated_at": binary_slot.get("activated_at").isoformat() if binary_slot and binary_slot.get("activated_at") else None
                    },
                    "matrix": {
                        "total_earnings": {
                            "USDT": float(matrix_earnings.get("USDT", Decimal('0'))),
                            "BNB": float(matrix_earnings.get("BNB", Decimal('0')))
                        },
                        "highest_activated_slot": matrix_slot.get("slot_no") if matrix_slot else 0,
                        "highest_activated_slot_name": matrix_slot.get("slot_name") if matrix_slot else "N/A",
                        "activated_at": matrix_slot.get("activated_at").isoformat() if matrix_slot and matrix_slot.get("activated_at") else None
                    },
                    "global": {
                        "total_earnings": {
                            "USDT": float(global_earnings.get("USDT", Decimal('0'))),
                            "BNB": float(global_earnings.get("BNB", Decimal('0')))
                        },
                        "highest_activated_slot": global_slot.get("slot_no") if global_slot else 0,
                        "highest_activated_slot_name": global_slot.get("slot_name") if global_slot else "N/A",
                        "activated_at": global_slot.get("activated_at").isoformat() if global_slot and global_slot.get("activated_at") else None
                    }
                }
            }
            
        except Exception as e:
            print(f"Error in get_earning_statistics: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _get_highest_activated_slot(self, user_oid: ObjectId, program: str) -> Dict[str, Any]:
        """Get the highest activated slot for binary/global programs (uses SlotActivation)"""
        try:
            slot_activation = SlotActivation.objects(
                user_id=user_oid,
                program=program,
                status='completed'
            ).order_by('-slot_no').first()
            
            if slot_activation:
                return {
                    "slot_no": slot_activation.slot_no,
                    "slot_name": slot_activation.slot_name,
                    "activated_at": slot_activation.activated_at or slot_activation.created_at
                }
            return {}
        except Exception as e:
            print(f"Error getting highest slot for {program}: {e}")
            return {}
    
    def _get_highest_matrix_slot(self, user_oid: ObjectId) -> Dict[str, Any]:
        """Get the highest activated slot for matrix program (uses MatrixActivation)"""
        try:
            # Import here to avoid circular dependency
            from ..matrix.model import MatrixActivation
            
            # Matrix uses MatrixActivation collection
            matrix_activation = MatrixActivation.objects(
                user_id=user_oid,
                status='completed'
            ).order_by('-slot_no').first()
            
            if matrix_activation:
                return {
                    "slot_no": matrix_activation.slot_no,
                    "slot_name": matrix_activation.slot_name,
                    "activated_at": matrix_activation.activated_at or matrix_activation.completed_at
                }
            return {}
        except Exception as e:
            print(f"Error getting highest matrix slot: {e}")
            return {}

    def get_pools_summary(self, user_id: str = None) -> Dict[str, Any]:
        """
        User-specific pools summary. Combines:
        - WalletLedger credit reasons (BNB/USDT exact) for the specific user
        - Program-specific collections (maps USD -> USDT for reporting) for the specific user
        """
        try:
            from decimal import Decimal as _D
            from bson import ObjectId

            def _zero():
                return {"USDT": 0.0, "BNB": 0.0}

            totals: Dict[str, Dict[str, float]] = {
                "duel_tree": _zero(),
                "binary_partner_incentive": _zero(),
                "leadership_stipend": _zero(),
                "dream_matrix": _zero(),
                "matrix_partner_incentive": _zero(),
                "newcomer_growth_support": _zero(),
                "mentorship_bonus": _zero(),
                "spark_bonus": _zero(),
                "triple_entry_reward": _zero(),
                "global_phase_1": _zero(),
                "global_phase_2": _zero(),
                "global_partner_incentive": _zero(),
                "royal_captain_bonus": _zero(),
                "president_reward": _zero(),
                "top_leader_gift": _zero(),
                "jackpot_programme": _zero(),
            }

            # 1) Single aggregation over wallet_ledger credits for specific user
            pipeline = [
                {"$match": {"type": "credit", "user_id": ObjectId(user_id)}},
                {"$group": {"_id": {"reason": "$reason", "currency": "$currency"}, "total": {"$sum": "$amount"}}}
            ]
            results = list(WalletLedger.objects.aggregate(pipeline))

            # Fallback: if aggregation returns nothing (e.g., provider limitations),
            # perform a python-side rollup from ledger documents
            if not results:
                try:
                    credits = WalletLedger.objects(user_id=ObjectId(user_id), type="credit")
                    tmp_map: dict[tuple[str, str], float] = {}
                    for row in credits:
                        r = (getattr(row, 'reason', '') or '').lower()
                        c = (getattr(row, 'currency', 'USDT') or 'USDT').upper()
                        amt = float(getattr(row, 'amount', 0) or 0)
                        k = (r, c)
                        tmp_map[k] = tmp_map.get(k, 0.0) + amt
                    # Convert to results-like structure
                    results = [{"_id": {"reason": k[0], "currency": k[1]}, "total": v} for k, v in tmp_map.items()]
                except Exception:
                    results = []

            def map_reason_to_pool(reason: str) -> str | None:
                r = (reason or "").lower()
                # Duel tree: ONLY explicit slot-1 full credits
                if r == "binary_slot1_full":
                    return "duel_tree"
                # Binary Partner Incentive: ONLY partner incentive credits per user request
                if r == "binary_partner_incentive":
                    return "binary_partner_incentive"
                # Matrix Partner Incentive includes: partner incentive and level distributions (matrix_dual_tree_level_X)
                if r == "matrix_partner_incentive" or r.startswith("matrix_dual_tree_"):
                    return "matrix_partner_incentive"
                if r == "global_partner_incentive":
                    return "global_partner_incentive"
                if r.startswith("global_phase_1"):
                    return "global_phase_1"
                if r.startswith("global_phase_2"):
                    return "global_phase_2"
                if r.startswith("dream_matrix_") or r == "dream_matrix_commission":
                    return "dream_matrix"
                if r == "mentorship_bonus" or r.startswith("mentorship_"):
                    return "mentorship_bonus"
                if r == "newcomer_support" or r.startswith("ngs_"):
                    return "newcomer_growth_support"
                if r.startswith("spark_bonus_") or r == "spark_bonus":
                    return "spark_bonus"
                if r.startswith("triple_entry_"):
                    return "triple_entry_reward"
                if r.startswith("royal_captain_"):
                    return "royal_captain_bonus"
                if r.startswith("president_reward_"):
                    return "president_reward"
                if r.startswith("top_leader_gift_") or r == "top_leaders_gift":
                    return "top_leader_gift"
                if r.startswith("jackpot_"):
                    return "jackpot_programme"
                if r.startswith("leadership_stipend_"):
                    return "leadership_stipend"
                return None

            for row in results:
                reason = (row.get("_id", {}).get("reason") or "")
                currency = (row.get("_id", {}).get("currency") or "USDT").upper()
                total = float(row.get("total") or 0)
                pool_key = map_reason_to_pool(reason)
                if pool_key and currency in totals.get(pool_key, {}):
                    totals[pool_key][currency] += total

            # 2) Program-specific collections (for items not always recorded in wallet_ledger)
            try:
                from ..income.model import IncomeEvent
            except Exception:
                IncomeEvent = None
            try:
                from ..leadership_stipend.model import LeadershipStipendPayment
            except Exception:
                LeadershipStipendPayment = None
            try:
                from ..spark.model import SparkBonusDistribution, TripleEntryReward
            except Exception:
                SparkBonusDistribution = None
                TripleEntryReward = None
            try:
                from ..dream_matrix.model import DreamMatrixCommission
            except Exception:
                DreamMatrixCommission = None
            try:
                from ..royal_captain.model import RoyalCaptainBonusPayment
            except Exception:
                RoyalCaptainBonusPayment = None
            try:
                from ..president_reward.model import PresidentRewardPayment
            except Exception:
                PresidentRewardPayment = None
            try:
                from ..top_leader_gift.model import TopLeaderGiftReward
            except Exception:
                TopLeaderGiftReward = None
            try:
                from ..jackpot.model import JackpotFund
            except Exception:
                JackpotFund = None
            try:
                from ..newcomer_support.model import NewcomerSupportBonus
            except Exception:
                NewcomerSupportBonus = None

            # IncomeEvent-driven pools (report as USDT) - user specific
            if IncomeEvent:
                try:
                    def _sum_income(types: list[str]) -> float:
                        agg = [
                            {"$match": {"user_id": ObjectId(user_id), "income_type": {"$in": types}, "status": {"$in": ["pending", "completed"]}}},
                            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
                        ]
                        res = list(IncomeEvent.objects.aggregate(agg))
                        return float(res[0]["total"]) if res else 0.0
                    totals["mentorship_bonus"]["USDT"] += _sum_income(["mentorship"])  # mentorship bonus
                    # NGS is handled separately below via NewcomerSupportBonus
                    # Global phases
                    totals["global_phase_1"]["USDT"] += _sum_income(["global_phase_1"])  # Phase-1 allocation
                    totals["global_phase_2"]["USDT"] += _sum_income(["global_phase_2"])  # Phase-2 allocation
                except Exception:
                    pass

            # NewcomerSupportBonus-driven pools (user's instant claimable 50%)
            if NewcomerSupportBonus:
                try:
                    def _sum_newcomer_bonuses() -> float:
                        agg = [
                            {"$match": {"user_id": ObjectId(user_id), "bonus_type": "instant"}},
                            {"$group": {"_id": None, "total": {"$sum": "$bonus_amount"}}}
                        ]
                        res = list(NewcomerSupportBonus.objects.aggregate(agg))
                        return float(res[0]["total"]) if res else 0.0
                    totals["newcomer_growth_support"]["USDT"] += _sum_newcomer_bonuses()  # User's 50% instant claimable
                except Exception:
                    pass

            # Fallback: IncomeEvent-driven pools if not already handled
            if IncomeEvent:
                try:
                    def _sum_income(types: list[str]) -> float:
                        agg = [
                            {"$match": {"user_id": ObjectId(user_id), "income_type": {"$in": types}, "status": {"$in": ["pending", "completed"]}}},
                            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
                        ]
                        res = list(IncomeEvent.objects.aggregate(agg))
                        return float(res[0]["total"]) if res else 0.0

                    # Fallback for Binary Partner Incentive and Duel Tree when WalletLedger is missing
                    # Use IncomeEvent ONLY if WalletLedger totals are zero to avoid double counting
                    try:
                        agg_pi = [
                            {"$match": {
                                "user_id": ObjectId(user_id),
                                "program": "binary",
                                "income_type": "partner_incentive",
                                "status": {"$in": ["pending", "completed"]}
                            }},
                            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
                        ]
                        res_pi = list(IncomeEvent.objects.aggregate(agg_pi))
                        if (totals.get("binary_partner_incentive", {}).get("BNB", 0.0) or 0.0) == 0.0:
                            totals["binary_partner_incentive"]["BNB"] += float(res_pi[0]["total"]) if res_pi else 0.0
                    except Exception:
                        pass

                    # Sum duel tree level distributions for binary as BNB
                    try:
                        agg_dt = [
                            {"$match": {
                                "user_id": ObjectId(user_id),
                                "program": "binary",
                                "income_type": {"$regex": "^level_\\d+_distribution$"},
                                "status": {"$in": ["pending", "completed"]}
                            }},
                            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
                        ]
                        res_dt = list(IncomeEvent.objects.aggregate(agg_dt))
                        if (totals.get("duel_tree", {}).get("BNB", 0.0) or 0.0) == 0.0:
                            totals["duel_tree"]["BNB"] += float(res_dt[0]["total"]) if res_dt else 0.0
                    except Exception:
                        pass
                except Exception:
                    pass

            # Leadership stipend (BNB) - user specific
            if LeadershipStipendPayment:
                try:
                    agg = [
                        {"$match": {"user_id": ObjectId(user_id), "payment_status": {"$in": ["pending", "processing", "paid"]}}},
                        {"$group": {"_id": None, "total": {"$sum": "$daily_return_amount"}}}
                    ]
                    res = list(LeadershipStipendPayment.objects.aggregate(agg))
                    totals["leadership_stipend"]["BNB"] += float(res[0]["total"]) if res else 0.0
                except Exception:
                    pass

            # Spark bonus and Triple Entry (currency stored on document) - user specific
            if SparkBonusDistribution:
                try:
                    agg = [
                        {"$match": {"user_id": ObjectId(user_id), "status": {"$in": ["pending", "completed"]}}},
                        {"$group": {"_id": "$currency", "total": {"$sum": "$distribution_amount"}}}
                    ]
                    for r in SparkBonusDistribution.objects.aggregate(agg):
                        curr = (r.get('_id') or 'USDT').upper()
                        totals["spark_bonus"][curr] += float(r.get('total') or 0)
                except Exception:
                    pass
            if TripleEntryReward:
                try:
                    # Triple Entry Reward doesn't have user_id, check eligible_users list
                    agg = [
                        {"$match": {"eligible_users": ObjectId(user_id)}},
                        {"$group": {"_id": None, "total": {"$sum": "$distribution_amount"}}}
                    ]
                    res = list(TripleEntryReward.objects.aggregate(agg))
                    totals["triple_entry_reward"]["USDT"] += float(res[0]["total"]) if res else 0.0
                except Exception:
                    pass

            # Dream Matrix commissions (field is commission_amount) - user specific
            if DreamMatrixCommission:
                try:
                    agg = [
                        {"$match": {"user_id": ObjectId(user_id), "payment_status": {"$in": ["pending", "processing", "paid"]}}},
                        {"$group": {"_id": None, "total": {"$sum": "$commission_amount"}}}
                    ]
                    res = list(DreamMatrixCommission.objects.aggregate(agg))
                    totals["dream_matrix"]["USDT"] += float(res[0]["total"]) if res else 0.0
                except Exception:
                    pass

            # Royal Captain / President Reward (USD -> USDT) - user specific
            if RoyalCaptainBonusPayment:
                try:
                    agg = [
                        {"$match": {"user_id": ObjectId(user_id), "payment_status": {"$in": ["pending", "processing", "paid"]}}},
                        {"$group": {"_id": None, "total": {"$sum": "$bonus_amount"}}}
                    ]
                    res = list(RoyalCaptainBonusPayment.objects.aggregate(agg))
                    totals["royal_captain_bonus"]["USDT"] += float(res[0]["total"]) if res else 0.0
                except Exception:
                    pass
            if PresidentRewardPayment:
                try:
                    agg = [
                        {"$match": {"user_id": ObjectId(user_id), "payment_status": {"$in": ["pending", "processing", "paid"]}}},
                        {"$group": {"_id": None, "total": {"$sum": "$reward_amount"}}}
                    ]
                    res = list(PresidentRewardPayment.objects.aggregate(agg))
                    totals["president_reward"]["USDT"] += float(res[0]["total"]) if res else 0.0
                except Exception:
                    pass

            # Top Leader's Gift (USD -> USDT) - user specific
            if TopLeaderGiftReward:
                try:
                    agg = [
                        {"$match": {"user_id": ObjectId(user_id)}},
                        {"$group": {"_id": None, "total": {"$sum": "$gift_value_usd"}}}
                    ]
                    res = list(TopLeaderGiftReward.objects.aggregate(agg))
                    totals["top_leader_gift"]["USDT"] += float(res[0]["total"]) if res else 0.0
                except Exception:
                    pass

            # Jackpot winnings - user specific (JackpotWinner is embedded in JackpotDistribution)
            try:
                from ..jackpot.model import JackpotDistribution
                # Unwind winners array and filter by user_id
                agg = [
                    {"$unwind": "$winners"},
                    {"$match": {"winners.user_id": ObjectId(user_id)}},
                    {"$group": {"_id": None, "total": {"$sum": "$winners.amount_won"}}}
                ]
                res = list(JackpotDistribution.objects.aggregate(agg))
                if res:
                    # Jackpot is in BNB (entry fee is 0.0025 BNB)
                    totals["jackpot_programme"]["BNB"] += float(res[0].get("total") or 0)
            except Exception as e:
                pass

            return {"success": True, "data": totals}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_duel_tree_earnings(self, user_id: str, currency: str = "BNB", page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Return a paginated list of Duel Tree earnings for a specific user.
        Definition: Duel Tree = credits with reason == "binary_slot1_full" in wallet_ledger.
        Sorted by earning time (desc).
        Columns: uid, time, upline uid, partner count, rank, amount, reason.
        """
        try:
            from ..user.model import User, PartnerGraph
            from bson import ObjectId

            # Convert user_id to ObjectId if needed
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id

            # Get wallet ledger entries for this specific user
            # Only include Duel Tree earnings: binary_slot1_full
            match_filter = {
                "user_id": user_oid,
                "type": "credit",
                "reason": "binary_slot1_full",
                "currency": currency.upper()
            }
            
            # Count total entries
            total = WalletLedger.objects(**match_filter).count()
            
            # Paginate
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 50)))
            skip = (page - 1) * limit
            
            # Get paginated entries, sorted by created_at desc
            entries = WalletLedger.objects(**match_filter).order_by('-created_at').skip(skip).limit(limit)

            # Get user info
            user = User.objects(id=user_oid).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get partner graph for partner count
            pg = PartnerGraph.objects(user_id=user_oid).first()
            partner_count = len(getattr(pg, 'directs', []) if pg else [])
            
            # Get upline info
            ref = getattr(user, 'refered_by', None)
            upline_uid = None
            referrer_refer_code = None
            if ref:
                upline = User.objects(id=ref).only('uid', 'refer_code').first()
                if upline:
                    upline_uid = getattr(upline, 'uid', None)
                    referrer_refer_code = getattr(upline, 'refer_code', None)
            if not upline_uid:
                upline_uid = 'ROOT'
            if not referrer_refer_code:
                referrer_refer_code = 'ROOT'

            # Current user's refer code
            user_refer_code = getattr(user, 'refer_code', None)

            # Prepare source-user lookup via tx_hash (ObjectId embedded in hash)
            hex24 = re.compile(r"([0-9a-fA-F]{24})")
            entry_sources: Dict[str, str] = {}
            source_ids: set[str] = set()
            for entry in entries:
                tx_hash = str(getattr(entry, 'tx_hash', '') or '')
                match = hex24.search(tx_hash)
                if match:
                    candidate = match.group(1)
                    try:
                        oid = ObjectId(candidate)
                        entry_sources[str(entry.id)] = str(oid)
                        source_ids.add(str(oid))
                    except Exception:
                        continue

            # Fetch source users (downlines who generated the income)
            from ..slot.model import SlotActivation
            source_users = {}
            source_slot_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
            if source_ids:
                source_user_objs = User.objects(id__in=[ObjectId(sid) for sid in source_ids]).only('uid', 'refer_code')
                source_users = {str(u.id): u for u in source_user_objs}

                # Fetch slot activations for rank calculation
                slot_activations = SlotActivation.objects(
                    user_id__in=[ObjectId(sid) for sid in source_ids],
                    status='completed',
                    program__in=['binary', 'matrix']
                ).only('user_id', 'program', 'slot_no', 'slot_name')

                for act in slot_activations:
                    user_key = str(act.user_id)
                    program_slots = source_slot_map.setdefault(user_key, {})
                    current = program_slots.get(act.program)
                    if not current or act.slot_no > current['slot_no']:
                        program_slots[act.program] = {
                            'slot_no': act.slot_no,
                            'slot_name': getattr(act, 'slot_name', None)
                        }

            # Build rows from ledger entries
            rows = []
            for entry in entries:
                source_user_id = entry_sources.get(str(entry.id))
                source_user = source_users.get(source_user_id) if source_user_id else None
                source_uid = getattr(source_user, 'uid', None) if source_user else None
                source_refer_code = getattr(source_user, 'refer_code', None) if source_user else None

                # Determine rank based on active slots in both programs
                rank = None
                slot_info = source_slot_map.get(source_user_id) if source_user_id else None
                if slot_info:
                    binary_slot = slot_info.get('binary')
                    matrix_slot = slot_info.get('matrix')
                    if binary_slot and matrix_slot:
                        if binary_slot['slot_no'] <= matrix_slot['slot_no']:
                            chosen_program = 'Binary'
                            chosen_slot = binary_slot
                        else:
                            chosen_program = 'Matrix'
                            chosen_slot = matrix_slot
                        slot_name = chosen_slot.get('slot_name') or f"Slot {chosen_slot.get('slot_no')}"
                        rank = f"{chosen_program} - {slot_name}"

                rows.append({
                    "uid": getattr(user, 'uid', None),
                    "receiver_refer_code": user_refer_code,
                    "refer_code": source_refer_code,
                    "source_uid": source_uid,
                    "referrer_refer_code": referrer_refer_code,
                    "time": entry.created_at.isoformat() if entry.created_at else None,
                    "upline_uid": upline_uid,
                    "partner_count": partner_count,
                    "rank": rank,
                    "amount": float(entry.amount) if entry.amount else 0,
                    "reason": entry.reason,
                    "tx_hash": entry.tx_hash or ""
                })

            return {
                "success": True,
                "data": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "items": rows
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_binary_partner_incentive(self, user_id: str, currency: str = "BNB", page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Return a paginated list of Binary Partner Incentive earnings for a specific user.
        Per PROJECT_DOCUMENTATION.md Section 8: Binary Partner Incentive includes:
        - binary_joining_commission (10% from joining)
        - binary_partner_incentive (partner incentive)
        - binary_upgrade_* (10% from each slot upgrade)
        Columns: uid (receiver), upline_uid, amount, time, reason, tx_hash.
        """
        try:
            from ..user.model import User
            from bson import ObjectId
            from mongoengine import Q

            # Convert user_id to ObjectId if needed
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id

            # Get wallet ledger entries for this specific user
            # Include all Binary Partner Incentive related reasons per documentation
            base_filter = Q(user_id=user_oid) & Q(type="credit") & Q(currency=currency.upper())
            reason_filter = Q(reason="binary_partner_incentive") | Q(reason="binary_joining_commission") | Q(reason__startswith="binary_upgrade_")
            query = base_filter & reason_filter
            
            # Count total entries
            total = WalletLedger.objects(query).count()
            
            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 50)))
            skip = (page - 1) * limit
            
            # Get paginated entries, sorted by created_at desc
            entries = WalletLedger.objects(query).order_by('-created_at').skip(skip).limit(limit)

			# Build user lookup for all ledger entries (receiver)
            def _normalize_object_id(value):
                if not value:
                    return None
                if isinstance(value, ObjectId):
                    return str(value)
                try:
                    return str(ObjectId(value))
                except Exception:
                    return str(value)

            primary_user_id = _normalize_object_id(user_oid)

            user_ids = {
                _normalize_object_id(entry.user_id)
                for entry in entries
                if getattr(entry, "user_id", None)
            }
            if primary_user_id:
                user_ids.add(primary_user_id)

            user_map: Dict[str, Any] = {}
            if user_ids:
                valid_user_object_ids = []
                for uid in user_ids:
                    if uid and ObjectId.is_valid(uid):
                        valid_user_object_ids.append(ObjectId(uid))
                if valid_user_object_ids:
                    user_docs = User.objects(id__in=valid_user_object_ids).only('uid', 'refer_code', 'refered_by')
                    for user_doc in user_docs:
                        user_map[str(user_doc.id)] = user_doc

            if not user_map:
                fallback_user = None
                try:
                    fallback_user = User.objects(id=user_oid).only('uid', 'refer_code', 'refered_by').first()
                except Exception:
                    fallback_user = None
                if not fallback_user and primary_user_id and ObjectId.is_valid(primary_user_id):
                    fallback_user = User.objects(id=ObjectId(primary_user_id)).only('uid', 'refer_code', 'refered_by').first()
                if fallback_user:
                    user_map[str(fallback_user.id)] = fallback_user
                else:
                    return {"success": False, "error": "User not found"}

            # Extract potential source user ids from tx_hash of each entry (downline who generated income)
            # We expect a 24-char hex ObjectId embedded in tx_hash (same heuristic used elsewhere)
            import re as _re
            _hex24 = _re.compile(r"([0-9a-fA-F]{24})")
            entry_id_to_source_id: Dict[str, str] = {}
            source_user_ids: set[str] = set()
            for entry in entries:
                txh = str(getattr(entry, 'tx_hash', '') or '')
                m = _hex24.search(txh)
                if not m:
                    continue
                candidate = m.group(1)
                try:
                    oid = ObjectId(candidate)
                    entry_id_to_source_id[str(entry.id)] = str(oid)
                    source_user_ids.add(str(oid))
                except Exception:
                    continue

            # Fetch source users (downlines) and their referrers
            source_user_map: Dict[str, Any] = {}
            source_referrer_ids: set[str] = set()
            if source_user_ids:
                source_docs = User.objects(id__in=[ObjectId(sid) for sid in source_user_ids if ObjectId.is_valid(sid)]).only('uid', 'refer_code', 'refered_by')
                for s in source_docs:
                    source_user_map[str(s.id)] = s
                    if getattr(s, 'refered_by', None):
                        try:
                            source_referrer_ids.add(str(ObjectId(getattr(s, 'refered_by'))))
                        except Exception:
                            # If refered_by is already ObjectId, str() still ok
                            source_referrer_ids.add(str(getattr(s, 'refered_by')))

            source_referrer_map: Dict[str, Dict[str, Any]] = {}
            if source_referrer_ids:
                ref_docs = User.objects(id__in=[ObjectId(rid) for rid in source_referrer_ids if ObjectId.is_valid(rid)]).only('uid', 'refer_code')
                for r in ref_docs:
                    source_referrer_map[str(r.id)] = {
                        "uid": getattr(r, 'uid', None),
                        "refer_code": getattr(r, 'refer_code', None)
                    }

            # Build referrer lookup for receiver user (kept for fallback)
            referrer_ids = {
                _normalize_object_id(getattr(user_doc, 'refered_by', None))
                for user_doc in user_map.values()
                if getattr(user_doc, 'refered_by', None)
            }
            referrer_map: Dict[str, Dict[str, Any]] = {}
            if referrer_ids:
                referrer_docs = User.objects(id__in=[ObjectId(rid) for rid in referrer_ids if ObjectId.is_valid(rid)]).only('uid', 'refer_code')
                for ref_doc in referrer_docs:
                    referrer_map[str(ref_doc.id)] = {
                        "uid": getattr(ref_doc, 'uid', None),
                        "refer_code": getattr(ref_doc, 'refer_code', None),
                    }

            # Build rows from ledger entries
            rows = []
            for entry in entries:
                # Receiver (current user) - still used for uid field
                entry_user_key = _normalize_object_id(getattr(entry, 'user_id', None))
                entry_user = user_map.get(entry_user_key)

                entry_uid = getattr(entry_user, 'uid', None) if entry_user else None

                # Source user (the downline who generated this income)
                source_id = entry_id_to_source_id.get(str(entry.id))
                source_user = source_user_map.get(source_id) if source_id else None
                source_refer_code = getattr(source_user, 'refer_code', None) if source_user else None

                # Source user's referrer/upline
                upline_uid = 'ROOT'
                referrer_refer_code = 'ROOT'
                if source_user:
                    src_ref_id = _normalize_object_id(getattr(source_user, 'refered_by', None))
                    if src_ref_id and src_ref_id in source_referrer_map:
                        src_ref = source_referrer_map[src_ref_id]
                        upline_uid = src_ref.get("uid") or 'ROOT'
                        referrer_refer_code = src_ref.get("refer_code") or 'ROOT'
                else:
                    # Fallback to receiver's upline if source not found
                    if entry_user:
                        ref_key = _normalize_object_id(getattr(entry_user, 'refered_by', None))
                        if ref_key and ref_key in referrer_map:
                            ref_info = referrer_map[ref_key]
                            upline_uid = ref_info.get("uid") or 'ROOT'
                            referrer_refer_code = ref_info.get("refer_code") or 'ROOT'

                rows.append({
                    "uid": entry_uid,
                    "upline_uid": upline_uid,
                    "refer_code": source_refer_code,
                    "referrer_refer_code": referrer_refer_code,
                    "amount": float(entry.amount) if entry.amount else 0,
                    "time": entry.created_at.isoformat() if entry.created_at else None,
                    "reason": entry.reason,
                    "tx_hash": entry.tx_hash or ""
                })

            return {
                "success": True,
                "data": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "items": rows
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_dream_matrix_earnings_list(self, user_id: str, currency: str = "USDT", page: int = 1, limit: int = 50, days: int = 30) -> Dict[str, Any]:
        """
        Return a paginated list of Dream Matrix earnings events for a specific user.
        Columns: uid (receiver), upline_uid (source_user), time, partner_count, rank.
        Data source: DreamMatrixCommission (payment_status in pending/processing/paid).
        """
        try:
            from ..dream_matrix.model import DreamMatrixCommission
            from ..user.model import User, PartnerGraph
            from bson import ObjectId

            # Convert user_id to ObjectId if needed
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id

            from datetime import datetime, timedelta
            since = datetime.utcnow() - timedelta(days=max(1, int(days or 30)))
            qs = DreamMatrixCommission.objects(
                user_id=user_oid,
                payment_status__in=['pending', 'processing', 'paid'],
                created_at__gte=since
            ).only('user_id', 'source_user_id', 'created_at').order_by('-created_at')

            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 50)))
            skip = (page - 1) * limit
            entries = list(qs.skip(skip).limit(limit))
            total = qs.count()

            # Get user info (single user since we're filtering by user_id)
            user = User.objects(id=user_oid).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get partner graph for partner count
            pg = PartnerGraph.objects(user_id=user_oid).first()
            partner_count = len(getattr(pg, 'directs', []) if pg else [])

            # Get all unique source users (uplines) from entries
            src_ids = list(set([e.source_user_id for e in entries if getattr(e, 'source_user_id', None)]))
            sources = {str(u.id): u for u in User.objects(id__in=src_ids).only('uid')}

            rows = []
            for e in entries:
                src = sources.get(str(getattr(e, 'source_user_id', '')))
                rows.append({
                    "uid": getattr(user, 'uid', None),
                    "upline_uid": getattr(src, 'uid', None) or 'ROOT',
                    "time": getattr(e, 'created_at', None).isoformat() if getattr(e, 'created_at', None) else None,
                    "partner_count": partner_count,
                    "rank": getattr(user, 'current_rank', None),
                    "amount": float(getattr(e, 'amount', 0)) if hasattr(e, 'amount') else 0
                })

            # Fallback: derive data from IncomeEvent when no DreamMatrixCommission rows exist
            if total == 0:
                try:
                    from ..income.model import IncomeEvent
                    # Within the same timeframe
                    ie_q = IncomeEvent.objects(
                        user_id=user_oid,
                        program='matrix',
                        income_type__in=['partner_incentive', 'level_1_distribution', 'level_2_distribution', 'level_3_distribution'],
                        status__in=['pending', 'completed'],
                        created_at__gte=since
                    ).order_by('-created_at')

                    total = ie_q.count()
                    ie_entries = list(ie_q.skip(skip).limit(limit))

                    # Map source users
                    ie_src_ids = list(set([ie.source_user_id for ie in ie_entries if getattr(ie, 'source_user_id', None)]))
                    ie_sources = {str(u.id): u for u in User.objects(id__in=ie_src_ids).only('uid')}

                    rows = []
                    for ie in ie_entries:
                        src_u = ie_sources.get(str(getattr(ie, 'source_user_id', '')))
                        rows.append({
                            "uid": getattr(user, 'uid', None),
                            "upline_uid": getattr(src_u, 'uid', None) or 'ROOT',
                            "time": ie.created_at.isoformat() if ie.created_at else None,
                            "partner_count": partner_count,
                            "rank": getattr(user, 'current_rank', None),
                            "amount": float(ie.amount) if ie.amount else 0.0,
                            "reason": 'matrix_partner_incentive' if ie.income_type == 'partner_incentive' else f"matrix_dual_tree_{ie.income_type.replace('_distribution','')}"
                        })
                except Exception:
                    # Keep rows empty if fallback fails silently
                    pass

            return {
                "success": True,
                "data": {
                    "page": page,
                    "limit": limit,
                    "days": max(1, int(days or 30)),
                    "total": total,
                    "items": rows
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_dream_matrix_partner_incentive(self, user_id: str, currency: str = "USDT", page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Return a paginated list of Dream Matrix Partner Incentive earnings for a specific user.
        Columns: uid (receiver), upline_uid, amount, time, reason, tx_hash.
        Reasons counted: matrix_partner_incentive, dream_matrix_partner_incentive, dream_matrix_commission, 
        dream_matrix_*, matrix_partner_*, matrix_dual_tree_* (level distributions) (credits only).
        """
        try:
            from ..user.model import User
            from bson import ObjectId
            from mongoengine import Q

            # Convert user_id to ObjectId if needed
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id

            # Get wallet ledger entries for this specific user
            # Include all Dream Matrix Partner Incentive related reasons and level distributions
            base_filter = Q(user_id=user_oid) & Q(type="credit") & Q(currency=currency.upper())
            reason_filter = (
                Q(reason__in=["matrix_partner_incentive", "dream_matrix_partner_incentive", "dream_matrix_commission"]) |
                Q(reason__startswith="dream_matrix_") |
                Q(reason__startswith="matrix_partner_") |
                Q(reason__startswith="matrix_dual_tree_")  # Include level distributions
            )
            query = base_filter & reason_filter
            
            # Count total entries
            total = WalletLedger.objects(query).count()
            
            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 50)))
            skip = (page - 1) * limit
            
            # Get paginated entries, sorted by created_at desc
            entries = WalletLedger.objects(query).order_by('-created_at').skip(skip).limit(limit)

            # Get user info
            user = User.objects(id=user_oid).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get upline info
            ref = getattr(user, 'refered_by', None)
            upline_uid = None
            if ref:
                upline = User.objects(id=ref).only('uid').first()
                if upline:
                    upline_uid = getattr(upline, 'uid', None)
            if not upline_uid:
                upline_uid = 'ROOT'

            # Build rows from ledger entries
            rows = []
            for entry in entries:
                rows.append({
                    "uid": getattr(user, 'uid', None),
                    "upline_uid": upline_uid,
                    "amount": float(entry.amount) if entry.amount else 0,
                    "time": entry.created_at.isoformat() if entry.created_at else None,
                    "reason": entry.reason,
                    "tx_hash": entry.tx_hash or ""
                })

            return {
                "success": True,
                "data": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "items": rows
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_newcomer_growth_support_income(self, user_id: str, currency: str = "USDT", page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Return a paginated list of Newcomer Growth Support earnings for a specific user.
        Fetches from NewcomerSupportBonus collection (user's 50% instant claimable portion).
        """
        try:
            from ..user.model import User
            from ..newcomer_support.model import NewcomerSupportBonus
            from bson import ObjectId

            # Convert user_id to ObjectId if needed
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id

            # Get NewcomerSupportBonus entries for this specific user (user's instant claimable 50%)
            query_filter = {
                "user_id": user_oid,
                "bonus_type": "instant"  # Only instant claimable bonuses
            }
            
            # Count total entries
            total = NewcomerSupportBonus.objects(**query_filter).count()
            
            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 50)))
            skip = (page - 1) * limit
            
            # Get paginated entries, sorted by created_at desc
            entries = NewcomerSupportBonus.objects(**query_filter).order_by('-created_at').skip(skip).limit(limit)

            # Get user info
            user = User.objects(id=user_oid).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get upline info
            ref = getattr(user, 'refered_by', None)
            upline_uid = None
            if ref:
                upline = User.objects(id=ref).only('uid').first()
                if upline:
                    upline_uid = getattr(upline, 'uid', None)
            if not upline_uid:
                upline_uid = 'ROOT'

            # Build rows from bonus entries
            rows = []
            for entry in entries:
                rows.append({
                    "uid": getattr(user, 'uid', None),
                    "upline_uid": upline_uid,
                    "amount": float(entry.bonus_amount) if entry.bonus_amount else 0,
                    "time": entry.created_at.isoformat() if entry.created_at else None,
                    "income_type": "newcomer_support",
                    "status": entry.payment_status,
                    "description": entry.source_description or entry.bonus_name or ""
                })

            # Get total Newcomer Growth Support fund amount from BonusFund
            total_global_usdt = 0.0
            try:
                from ..income.bonus_fund import BonusFund
                # Get USDT fund (from matrix program - newcomer support is part of matrix)
                usdt_fund = BonusFund.objects(fund_type='newcomer_support', program='matrix').first()
                if usdt_fund:
                    total_global_usdt = float(usdt_fund.current_balance or 0.0)
            except Exception as e:
                print(f"Error fetching newcomer support fund: {e}")

            return {
                "success": True,
                "data": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_global_usdt": total_global_usdt,  # Total Newcomer Growth Support fund in USDT
                    "items": rows
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_mentorship_bonus_income(self, user_id: str, currency: str = "USDT", page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Return a paginated list of Mentorship Bonus earnings for a specific user.
        Fetches from IncomeEvent collection (consistent with pools_summary).
        Income type: mentorship
        """
        try:
            from ..user.model import User
            from ..income.model import IncomeEvent
            from bson import ObjectId

            # Convert user_id to ObjectId if needed
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id

            # Get IncomeEvent entries for this specific user (matching pools_summary logic)
            query_filter = {
                "user_id": user_oid,
                "income_type": "mentorship",
                "status__in": ["pending", "completed"]
            }
            
            # Count total entries
            total = IncomeEvent.objects(**query_filter).count()
            
            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 50)))
            skip = (page - 1) * limit
            
            # Get paginated entries, sorted by created_at desc
            entries = IncomeEvent.objects(**query_filter).order_by('-created_at').skip(skip).limit(limit)

            # Get user info
            user = User.objects(id=user_oid).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # Build rows from income events - show the source_user_id (who generated the bonus)
            rows = []
            for entry in entries:
                # Get source user info (the user who triggered this bonus)
                source_user = None
                source_uid = None
                if entry.source_user_id:
                    try:
                        source_user = User.objects(id=entry.source_user_id).only('uid').first()
                        if source_user:
                            source_uid = getattr(source_user, 'uid', None)
                    except Exception:
                        pass
                
                if not source_uid:
                    source_uid = 'ROOT'
                
                rows.append({
                    "uid": getattr(user, 'uid', None),
                    "source_uid": source_uid,  # Source user (who joined, triggering this bonus)
                    "amount": float(entry.amount) if entry.amount else 0,
                    "time": entry.created_at.isoformat() if entry.created_at else None,
                    "income_type": entry.income_type,
                    "status": entry.status,
                    "description": getattr(entry, 'description', '') or ""
                })

            return {
                "success": True,
                "data": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "items": rows
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_phase_1_income(self, user_id: str, currency: str = "USDT", page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get Global Program Phase-1 income data for a specific user, grouped by slot"""
        try:
            from ..user.model import User
            from ..tree.model import TreePlacement
            from bson import ObjectId
            
            # Convert user_id to ObjectId if needed
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id
            
            # Get user info
            user = User.objects(id=user_oid).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get all active Global slots for this user
            user_placements = TreePlacement.objects(
                user_id=user_oid,
                program='global',
                phase='PHASE-1',
                is_active=True
            ).order_by('slot_no')
            
            # Build slot-wise income data
            slots_data = []
            
            for placement in user_placements:
                slot_no = placement.slot_no
                
                # Get Phase-1 income entries for this specific slot
                phase_1_entries = WalletLedger.objects(
                    user_id=user_oid,
                    type="credit",
                    currency=currency.upper(),
                    reason__regex=f"^global_phase_1.*slot_{slot_no}"
                ).order_by('-created_at')
                
                total_entries = phase_1_entries.count()
                
                # Pagination for this slot
                page = max(1, int(page or 1))
                limit = max(1, min(100, int(limit or 50)))
                skip = (page - 1) * limit
                page_entries = phase_1_entries.skip(skip).limit(limit)
                
                # Get upline info
                ref = getattr(user, 'refered_by', None)
                upline_uid = None
                if ref:
                    upline = User.objects(id=ref).only('uid').first()
                    if upline:
                        upline_uid = getattr(upline, 'uid', None)
                if not upline_uid:
                    upline_uid = 'ROOT'
                
                # Build items for this slot
                items = []
                for entry in page_entries:
                    items.append({
                        "sl_no": len(items) + 1,
                        "uid": getattr(user, 'uid', None),
                        "upline_uid": upline_uid,
                        "rank": "Bitron",  # Default rank, can be fetched from user if needed
                        "amount": float(entry.amount) if entry.amount else 0,
                        "time": entry.created_at.isoformat() if entry.created_at else None,
                        "reason": entry.reason,
                        "tx_hash": entry.tx_hash or ""
                    })
                
                slots_data.append({
                    "slot_no": slot_no,
                    "total_records": total_entries,
                    "page": page,
                    "limit": limit,
                    "items": items
                })
            
            return {
                "success": True,
                "data": {
                    "user_id": str(user_oid),
                    "user_uid": getattr(user, 'uid', None),
                    "slots": slots_data,
                    "total_slots": len(slots_data)
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_phase_2_income(self, user_id: str, currency: str = "USDT", page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get Global Program Phase-2 income data for a specific user, grouped by slot"""
        try:
            from ..user.model import User
            from ..tree.model import TreePlacement
            from bson import ObjectId
            
            # Convert user_id to ObjectId if needed
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id
            
            # Get user info
            user = User.objects(id=user_oid).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get all active Global slots for this user in Phase-2
            user_placements = TreePlacement.objects(
                user_id=user_oid,
                program='global',
                phase='PHASE-2',
                is_active=True
            ).order_by('slot_no')
            
            # Build slot-wise income data
            slots_data = []
            
            for placement in user_placements:
                slot_no = placement.slot_no
                
                # Get Phase-2 income entries for this specific slot
                phase_2_entries = WalletLedger.objects(
                    user_id=user_oid,
                    type="credit",
                    currency=currency.upper(),
                    reason__regex=f"^global_phase_2.*slot_{slot_no}"
                ).order_by('-created_at')
                
                total_entries = phase_2_entries.count()
                
                # Pagination for this slot
                page = max(1, int(page or 1))
                limit = max(1, min(100, int(limit or 50)))
                skip = (page - 1) * limit
                page_entries = phase_2_entries.skip(skip).limit(limit)
                
                # Get upline info
                ref = getattr(user, 'refered_by', None)
                upline_uid = None
                if ref:
                    upline = User.objects(id=ref).only('uid').first()
                    if upline:
                        upline_uid = getattr(upline, 'uid', None)
                if not upline_uid:
                    upline_uid = 'ROOT'
                
                # Build items for this slot
                items = []
                for entry in page_entries:
                    items.append({
                        "sl_no": len(items) + 1,
                        "uid": getattr(user, 'uid', None),
                        "upline_uid": upline_uid,
                        "rank": "Bitron",  # Default rank, can be fetched from user if needed
                        "amount": float(entry.amount) if entry.amount else 0,
                        "time": entry.created_at.isoformat() if entry.created_at else None,
                        "reason": entry.reason,
                        "tx_hash": entry.tx_hash or ""
                    })
                
                slots_data.append({
                    "slot_no": slot_no,
                    "total_records": total_entries,
                    "page": page,
                    "limit": limit,
                    "items": items
                })
            
            return {
                "success": True,
                "data": {
                    "user_id": str(user_oid),
                    "user_uid": getattr(user, 'uid', None),
                    "slots": slots_data,
                    "total_slots": len(slots_data)
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_global_partner_incentive(self, user_id: str, currency: str = "USDT", page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get Global Partner Incentive data for a specific user"""
        try:
            from ..user.model import User
            from bson import ObjectId
            
            # Convert user_id to ObjectId if needed
            try:
                user_oid = ObjectId(user_id)
            except:
                user_oid = user_id
            
            # Get Global Partner Incentive entries for specific user from WalletLedger
            incentive_entries = WalletLedger.objects(
                user_id=user_oid,
                type="credit",
                currency=currency.upper(),
                reason="global_partner_incentive"
            ).order_by('-created_at')
            
            total_entries = incentive_entries.count()
            
            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 50)))
            skip = (page - 1) * limit
            page_entries = incentive_entries.skip(skip).limit(limit)
            
            # Get user info once (since filtering by single user)
            user = User.objects(id=user_oid).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get upline info
            ref = getattr(user, 'refered_by', None)
            upline_uid = None
            if ref:
                upline = User.objects(id=ref).only('uid').first()
                if upline:
                    upline_uid = getattr(upline, 'uid', None)
            if not upline_uid:
                upline_uid = 'ROOT'
            
            # Build rows from ledger entries
            items = []
            for entry in page_entries:
                items.append({
                    "uid": getattr(user, 'uid', None),
                    "upline_uid": upline_uid,
                    "amount": float(entry.amount) if entry.amount else 0,
                    "time": entry.created_at.isoformat() if entry.created_at else None,
                    "reason": entry.reason,
                    "tx_hash": entry.tx_hash or ""
                })
            
            return {
                "success": True,
                "data": {
                    "page": page,
                    "limit": limit,
                    "total": total_entries,
                    "items": items
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    def get_user_miss_profit_history(self, user_id: str, currency: str = "USDT", page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Get user's miss profit history with currency filtering"""
        try:
            from ..missed_profit.model import MissedProfit
            from ..user.model import User
            
            # Validate currency
            currency = currency.upper()
            if currency not in ['USDT', 'BNB']:
                return {"success": False, "error": "Invalid currency. Must be USDT or BNB"}
            
            user_oid = ObjectId(user_id)
            
            # Get missed profit entries for the user with currency filter
            currency_queryset = MissedProfit.objects(
                user_id=user_oid,
                currency=currency,
                is_active=True
            )
            missed_profits = currency_queryset.order_by('-created_at')
            
            total_entries = missed_profits.count()
            currency_total_amount = float(currency_queryset.sum('missed_profit_amount') or 0.0)
            currency_undistributed_count = currency_queryset.filter(is_distributed=False).count()
            currency_recovery_pending = currency_queryset.filter(recovery_status="pending").count()
            
            # Pre-calc totals across both currencies for convenience
            totals_by_currency = {
                "BNB": float(MissedProfit.objects(user_id=user_oid, currency='BNB', is_active=True).sum('missed_profit_amount') or 0.0),
                "USDT": float(MissedProfit.objects(user_id=user_oid, currency='USDT', is_active=True).sum('missed_profit_amount') or 0.0)
            }
            
            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 50)))
            start = (page - 1) * limit
            end = start + limit
            page_entries = missed_profits[start:end]
            
            # Pre-fetch all users (missed user + source partner) to optimize performance
            user_ids = set()
            for entry in page_entries:
                if getattr(entry, 'user_id', None):
                    user_ids.add(entry.user_id)
                if getattr(entry, 'upline_user_id', None):
                    user_ids.add(entry.upline_user_id)
            
            users = {
                str(user_doc.id): user_doc
                for user_doc in User.objects(id__in=list(user_ids)).only('id', 'uid', 'refer_code')
            }
            
            # Format data for frontend (matching the screenshot structure)
            items = []
            for i, entry in enumerate(page_entries):
                # Format date exactly like image (DD Mon YYYY (HH:MM))
                created_date = entry.created_at.strftime("%d %b %Y")
                created_time = entry.created_at.strftime("(%H:%M)")
                time_date = f"{created_date} {created_time}"
                
                # Get user info from pre-fetched data
                missed_user = users.get(str(entry.user_id))
                missed_user_id = str(entry.user_id)
                missed_user_uid = getattr(missed_user, 'uid', None) if missed_user else None
                missed_user_refer_code = getattr(missed_user, 'refer_code', None) if missed_user else None
                
                # Downline partner who triggered the miss profit
                partner = None
                partner_id = "--"
                partner_uid = None
                partner_refer_code = None
                if getattr(entry, 'upline_user_id', None):
                    partner_id = str(entry.upline_user_id)
                    partner = users.get(partner_id)
                    if partner:
                        partner_uid = getattr(partner, 'uid', None)
                        partner_refer_code = getattr(partner, 'refer_code', None)
                
                # User level/rank info
                user_level = entry.user_level
                
                # Dynamic currency field based on actual currency
                currency_field = f"miss_{currency.lower()}"
                
                items.append({
                    "user_id": missed_user_id,
                    "user_uid": missed_user_uid or "--",
                    "user_refer_code": missed_user_refer_code or "--",
                    "partner": partner_id,
                    "partner_uid": partner_uid or "--",
                    "partner_refer_code": partner_refer_code or "--",
                    "rank": user_level,
                    currency_field: float(entry.missed_profit_amount),
                    "time_date": time_date,
                    "missed_profit_type": entry.missed_profit_type,
                    "primary_reason": entry.primary_reason,
                    "reason_description": entry.reason_description,
                    "program_type": entry.program_type,
                    "recovery_status": entry.recovery_status,
                    "is_distributed": entry.is_distributed
                })
            
            page_total_amount = sum(float(item[currency_field]) for item in items)
            page_undistributed = len([item for item in items if not item["is_distributed"]])
            page_recovery_pending = len([item for item in items if item["recovery_status"] == "pending"])
            
            return {
                "success": True,
                "data": {
                    "page": page,
                    "limit": limit,
                    "total": total_entries,
                    "currency": currency,
                    "items": items,
                    "summary": {
                        "page_missed_amount": page_total_amount,
                        "page_entries": len(items),
                        "page_undistributed_count": page_undistributed,
                        "page_recovery_pending_count": page_recovery_pending,
                        "currency_totals": {
                            "currency": currency,
                            "amount": currency_total_amount,
                            "total_entries": total_entries,
                            "undistributed_count": currency_undistributed_count,
                            "recovery_pending_count": currency_recovery_pending
                        },
                        "overall_totals": totals_by_currency
                    }
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_global_miss_profit_summary(self) -> Dict[str, Any]:
        """Aggregate missed profit totals across all users by currency."""
        try:
            from ..missed_profit.model import MissedProfit
            base_queryset = MissedProfit.objects(is_active=True)
            totals: Dict[str, Dict[str, float | int]] = {}
            for currency in ['BNB', 'USDT']:
                qs = base_queryset.filter(currency=currency)
                totals[currency] = {
                    "amount": float(qs.sum('missed_profit_amount') or 0.0),
                    "count": qs.count(),
                    "undistributed_count": qs.filter(is_distributed=False).count(),
                    "recovery_pending_count": qs.filter(recovery_status='pending').count()
                }
            overall = {
                "amount": float(base_queryset.sum('missed_profit_amount') or 0.0),
                "count": base_queryset.count(),
                "undistributed_count": base_queryset.filter(is_distributed=False).count(),
                "recovery_pending_count": base_queryset.filter(recovery_status='pending').count()
            }
            return {
                "success": True,
                "data": {
                    "totals": totals,
                    "overall": overall
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_universal_claim_history(self, user_id: str, currency: str = None, claim_type: str = None, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Get universal claim history for all bonus programs
        Aggregates claims from all payment collections
        """
        try:
            from ..royal_captain.model import RoyalCaptainBonusPayment
            from ..president_reward.model import PresidentRewardPayment
            from ..leadership_stipend.model import LeadershipStipendPayment
            from ..spark.model import TripleEntryPayment
            from ..top_leader_gift.payment_model import TopLeadersGiftPayment
            
            uid = ObjectId(user_id)
            all_claims = []
            
            # 1. Royal Captain Bonus Payments
            try:
                rc_filter = {"user_id": uid, "payment_status": "paid"}
                if currency:
                    rc_filter["currency"] = currency.upper()
                
                rc_payments = RoyalCaptainBonusPayment.objects(**rc_filter).order_by('-created_at')
                
                for payment in rc_payments:
                    # Royal Captain pays in both USDT (60%) and BNB (40%)
                    if not currency or currency.upper() == 'USDT':
                        if payment.bonus_amount_usdt > 0:
                            all_claims.append({
                                "id": str(payment.id),
                                "type": "Royal Captain Bonus",
                                "amount": float(payment.bonus_amount_usdt),
                                "currency": "USDT",
                                "tier": payment.bonus_tier,
                                "status": payment.payment_status,
                                "paid_at": payment.paid_at.strftime("%d %b %Y (%H:%M)") if payment.paid_at else "--",
                                "created_at": payment.created_at.strftime("%d %b %Y (%H:%M)"),
                                "tx_hash": payment.payment_reference or "--"
                            })
                    
                    if not currency or currency.upper() == 'BNB':
                        if payment.bonus_amount_bnb > 0:
                            all_claims.append({
                                "id": str(payment.id),
                                "type": "Royal Captain Bonus",
                                "amount": float(payment.bonus_amount_bnb),
                                "currency": "BNB",
                                "tier": payment.bonus_tier,
                                "status": payment.payment_status,
                                "paid_at": payment.paid_at.strftime("%d %b %Y (%H:%M)") if payment.paid_at else "--",
                                "created_at": payment.created_at.strftime("%d %b %Y (%H:%M)"),
                                "tx_hash": payment.payment_reference or "--"
                            })
            except Exception as e:
                print(f"Error fetching Royal Captain payments: {e}")
            
            # 2. President Reward Payments
            try:
                pr_filter = {"user_id": uid, "payment_status": "paid"}
                if currency:
                    pr_filter["currency"] = currency.upper()
                
                pr_payments = PresidentRewardPayment.objects(**pr_filter).order_by('-created_at')
                
                for payment in pr_payments:
                    # President Reward also pays in both USDT (60%) and BNB (40%)
                    if not currency or currency.upper() == 'USDT':
                        if payment.reward_amount_usdt > 0:
                            all_claims.append({
                                "id": str(payment.id),
                                "type": "President Reward",
                                "amount": float(payment.reward_amount_usdt),
                                "currency": "USDT",
                                "tier": payment.reward_tier,
                                "status": payment.payment_status,
                                "paid_at": payment.paid_at.strftime("%d %b %Y (%H:%M)") if payment.paid_at else "--",
                                "created_at": payment.created_at.strftime("%d %b %Y (%H:%M)"),
                                "tx_hash": payment.payment_reference or "--"
                            })
                    
                    if not currency or currency.upper() == 'BNB':
                        if payment.reward_amount_bnb > 0:
                            all_claims.append({
                                "id": str(payment.id),
                                "type": "President Reward",
                                "amount": float(payment.reward_amount_bnb),
                                "currency": "BNB",
                                "tier": payment.reward_tier,
                                "status": payment.payment_status,
                                "paid_at": payment.paid_at.strftime("%d %b %Y (%H:%M)") if payment.paid_at else "--",
                                "created_at": payment.created_at.strftime("%d %b %Y (%H:%M)"),
                                "tx_hash": payment.payment_reference or "--"
                            })
            except Exception as e:
                print(f"Error fetching President Reward payments: {e}")
            
            # 3. Leadership Stipend Payments
            try:
                ls_filter = {"user_id": uid, "payment_status": "paid"}
                if currency:
                    ls_filter["currency"] = currency.upper()
                
                ls_payments = LeadershipStipendPayment.objects(**ls_filter).order_by('-created_at')
                
                for payment in ls_payments:
                    all_claims.append({
                        "id": str(payment.id),
                        "type": "Leadership Stipend",
                        "amount": float(payment.daily_return_amount),  # Fixed: daily_return_amount
                        "currency": payment.currency,
                        "tier": payment.tier_name,
                        "slot": payment.slot_number,
                        "status": payment.payment_status,
                        "paid_at": payment.payment_date.strftime("%d %b %Y (%H:%M)") if payment.payment_date else "--",
                        "created_at": payment.created_at.strftime("%d %b %Y (%H:%M)"),
                        "tx_hash": payment.payment_reference or "--"
                    })
            except Exception as e:
                print(f"Error fetching Leadership Stipend payments: {e}")
            
            # 4. Triple Entry Reward Payments
            try:
                ter_filter = {"user_id": uid, "status": "paid"}
                if currency:
                    ter_filter["currency"] = currency.upper()
                
                ter_payments = TripleEntryPayment.objects(**ter_filter).order_by('-created_at')
                
                for payment in ter_payments:
                    all_claims.append({
                        "id": str(payment.id),
                        "type": "Triple Entry Reward",
                        "amount": float(payment.amount),
                        "currency": payment.currency,
                        "status": payment.status,
                        "paid_at": payment.paid_at.strftime("%d %b %Y (%H:%M)") if payment.paid_at else "--",
                        "created_at": payment.created_at.strftime("%d %b %Y (%H:%M)"),
                        "tx_hash": payment.tx_hash or "--"
                    })
            except Exception as e:
                print(f"Error fetching Triple Entry Reward payments: {e}")
            
            # 5. Top Leader Gift Payments
            try:
                tlg_filter = {"user_id": uid, "payment_status": "paid"}
                if currency:
                    tlg_filter["currency"] = currency.upper()
                
                tlg_payments = TopLeadersGiftPayment.objects(**tlg_filter).order_by('-created_at')
                
                for payment in tlg_payments:
                    # Top Leader Gift pays in both USDT and BNB
                    if not currency or currency.upper() == 'USDT':
                        if payment.claimed_amount_usdt > 0:
                            all_claims.append({
                                "id": str(payment.id),
                                "type": "Top Leader Gift",
                                "amount": float(payment.claimed_amount_usdt),  # Fixed: claimed_amount_usdt
                                "currency": "USDT",
                                "level": payment.level_number,
                                "level_name": payment.level_name,
                                "status": payment.payment_status,
                                "paid_at": payment.processed_at.strftime("%d %b %Y (%H:%M)") if payment.processed_at else "--",
                                "created_at": payment.created_at.strftime("%d %b %Y (%H:%M)"),
                                "tx_hash": payment.payment_reference or "--"
                            })
                    
                    if not currency or currency.upper() == 'BNB':
                        if payment.claimed_amount_bnb > 0:
                            all_claims.append({
                                "id": str(payment.id),
                                "type": "Top Leader Gift",
                                "amount": float(payment.claimed_amount_bnb),  # Fixed: claimed_amount_bnb
                                "currency": "BNB",
                                "level": payment.level_number,
                                "level_name": payment.level_name,
                                "status": payment.payment_status,
                                "paid_at": payment.processed_at.strftime("%d %b %Y (%H:%M)") if payment.processed_at else "--",
                                "created_at": payment.created_at.strftime("%d %b %Y (%H:%M)"),
                                "tx_hash": payment.payment_reference or "--"
                            })
            except Exception as e:
                print(f"Error fetching Top Leader Gift payments: {e}")
            
            # Filter by claim_type if provided
            if claim_type:
                claim_type_map = {
                    "royal_captain": "Royal Captain Bonus",
                    "president_reward": "President Reward",
                    "leadership_stipend": "Leadership Stipend",
                    "triple_entry": "Triple Entry Reward",
                    "top_leader_gift": "Top Leader Gift"
                }
                filter_type = claim_type_map.get(claim_type.lower())
                if filter_type:
                    all_claims = [c for c in all_claims if c["type"] == filter_type]
            
            # Sort by created_at (most recent first)
            all_claims.sort(key=lambda x: x["created_at"], reverse=True)
            
            # Pagination
            total = len(all_claims)
            start = (page - 1) * limit
            end = start + limit
            paginated_claims = all_claims[start:end]
            
            # Add serial numbers
            for idx, claim in enumerate(paginated_claims, start=start + 1):
                claim["s_no"] = idx
            
            return {
                "success": True,
                "data": {
                    "claims": paginated_claims,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total,
                        "total_pages": (total + limit - 1) // limit
                    },
                    "filters": {
                        "currency": currency or "All",
                        "type": claim_type or "All"
                    },
                    "summary": {
                        "total_claims": total,
                        "total_amount_usdt": sum(c["amount"] for c in all_claims if c["currency"] == "USDT"),
                        "total_amount_bnb": sum(c["amount"] for c in all_claims if c["currency"] == "BNB")
                    }
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
