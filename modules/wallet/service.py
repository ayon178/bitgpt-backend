from decimal import Decimal
from datetime import datetime
from bson import ObjectId
from .model import UserWallet, WalletLedger
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
            
            # Get all missed profits for this user
            missed_profits = MissedProfit.objects(
                user_id=ObjectId(user_id),
                is_active=True,
                is_distributed=False  # Only count undistributed missed profits
            ).only('missed_profit_amount', 'currency')
            
            for missed in missed_profits:
                currency = (str(getattr(missed, 'currency', '')).upper() or 'USDT')
                if currency in missing_profit:
                    amount = float(getattr(missed, 'missed_profit_amount', 0) or 0)
                    missing_profit[currency] += amount
            
            print(f"Missing profit for user {user_id}: USDT={missing_profit['USDT']}, BNB={missing_profit['BNB']}")
            
        except Exception as e:
            print(f"Error calculating missing profit for user {user_id}: {e}")
            # Keep missing_profit as zeros if calculation fails

        return {
            "success": True,
            "wallet_type": wallet_type,
            "balances": result,
            "today_income": today_income,
            # Single deduplicated count across currencies
            "today_sources": len(today_sources_set),
            "missing_profit": missing_profit,
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
                if r.startswith("binary_dual_tree_"):
                    return "duel_tree"
                if r == "binary_partner_incentive":
                    return "binary_partner_incentive"
                if r == "matrix_partner_incentive":
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
                    totals["newcomer_growth_support"]["USDT"] += _sum_income(["newcomer_support"])  # NGS
                    # Global phases
                    totals["global_phase_1"]["USDT"] += _sum_income(["global_phase_1"])  # Phase-1 allocation
                    totals["global_phase_2"]["USDT"] += _sum_income(["global_phase_2"])  # Phase-2 allocation

                    # Fallback for Binary Partner Incentive and Duel Tree when WalletLedger is missing
                    # Sum partner incentive for binary as BNB-equivalent (amounts recorded in native amount)
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

    def get_duel_tree_earnings(self, currency: str = "BNB", page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Return a paginated list of DISTINCT users who received Duel Tree earnings (binary_dual_tree_* credits),
        one row per user, sorted by latest earning time (desc).
        Columns: uid, time (latest), upline uid, partner count, rank.
        """
        try:
            from ..user.model import User, PartnerGraph

            # Aggregate distinct users with latest created_at
            pipeline = [
                {"$match": {
                    "type": "credit",
                    "reason": {"$regex": "^binary_dual_tree_"},
                    "currency": currency.upper()
                }},
                {"$group": {
                    "_id": "$user_id",
                    "latest_at": {"$max": "$created_at"},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"latest_at": -1}}
            ]
            agg = list(WalletLedger.objects.aggregate(pipeline))

            # Pagination over aggregated distinct users
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 50)))
            start = (page - 1) * limit
            end = start + limit
            page_rows = agg[start:end]
            total = len(agg)

            user_ids = [r.get("_id") for r in page_rows if r.get("_id")]
            users = {str(u.id): u for u in User.objects(id__in=user_ids).only('uid', 'refered_by', 'current_rank')}
            graphs = {str(g.user_id): g for g in PartnerGraph.objects(user_id__in=user_ids).only('user_id', 'directs')}

            # Prefetch uplines
            upline_ids = []
            for u in users.values():
                rid = getattr(u, 'refered_by', None)
                if rid:
                    upline_ids.append(rid)
            upline_map = {str(u.id): u for u in User.objects(id__in=upline_ids).only('uid')}

            rows = []
            for r in page_rows:
                uid_oid = r.get("_id")
                latest_at = r.get("latest_at")
                u = users.get(str(uid_oid))
                if not u:
                    continue
                pg = graphs.get(str(uid_oid))
                partner_count = len(getattr(pg, 'directs', []) if pg else [])
                ref = getattr(u, 'refered_by', None)
                upline_uid = None
                if ref and str(ref) in upline_map:
                    upline_uid = getattr(upline_map[str(ref)], 'uid', None)
                if not upline_uid:
                    upline_uid = 'ROOT'

                rows.append({
                    "uid": getattr(u, 'uid', None),
                    "time": latest_at.isoformat() if latest_at else None,
                    "upline_uid": upline_uid,
                    "partner_count": partner_count,
                    "rank": getattr(u, 'current_rank', None)
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

    def get_binary_partner_incentive(self, currency: str = "BNB", page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Return a paginated list of DISTINCT users who received Binary Partner Incentive-type earnings.
        Columns: uid (receiver), upline_uid (from latest tx), total_amount, time (latest earning).
        Reasons counted: binary_partner_incentive, binary_joining_commission, binary_upgrade_* (credits only).
        """
        try:
            import re
            from ..user.model import User

            # Aggregate by user: sum amounts, pick latest created_at and latest tx_hash
            pipeline = [
                {"$match": {
                    "type": "credit",
                    "currency": currency.upper(),
                    "$or": [
                        {"reason": {"$in": ["binary_partner_incentive", "binary_joining_commission"]}},
                        {"reason": {"$regex": "^binary_upgrade_"}}
                    ]
                }},
                {"$sort": {"created_at": -1}},  # so $first gets latest tx
                {"$group": {
                    "_id": "$user_id",
                    "total_amount": {"$sum": "$amount"},
                    "latest_at": {"$first": "$created_at"},
                    "latest_tx": {"$first": "$tx_hash"}
                }},
                {"$sort": {"latest_at": -1}}
            ]
            agg = list(WalletLedger.objects.aggregate(pipeline))

            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 50)))
            start = (page - 1) * limit
            end = start + limit
            page_rows = agg[start:end]
            total = len(agg)

            # Fetch users and uplines
            user_ids = [r.get("_id") for r in page_rows if r.get("_id")]
            users_map = {str(u.id): u for u in User.objects(id__in=user_ids).only('uid', 'refered_by')}
            # Collect possible uplines (from referrer fallback)
            ref_ids = []
            for u in users_map.values():
                rid = getattr(u, 'refered_by', None)
                if rid:
                    ref_ids.append(rid)
            ref_map = {str(u.id): u for u in User.objects(id__in=ref_ids).only('uid')}

            # Parse upline from latest tx_hash if present
            hex24 = re.compile(r"[0-9a-fA-F]{24}")
            rows = []
            for r in page_rows:
                uid_oid = r.get("_id")
                u = users_map.get(str(uid_oid))
                if not u:
                    continue
                latest_tx = str(r.get("latest_tx") or '')
                m = hex24.search(latest_tx)
                upline_uid = None
                if m and ref_map.get(m.group(0)):
                    upline_uid = getattr(ref_map[m.group(0)], 'uid', None)
                if not upline_uid and getattr(u, 'refered_by', None):
                    rid = str(getattr(u, 'refered_by'))
                    if rid in ref_map:
                        upline_uid = getattr(ref_map[rid], 'uid', None)

                rows.append({
                    "uid": getattr(u, 'uid', None),
                    "upline_uid": upline_uid or 'ROOT',
                    "amount": float(r.get("total_amount") or 0),
                    "time": r.get("latest_at").isoformat() if r.get("latest_at") else None
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

    def get_dream_matrix_earnings_list(self, currency: str = "USDT", page: int = 1, limit: int = 50, days: int = 30) -> Dict[str, Any]:
        """
        Return a paginated list of Dream Matrix earnings events (not aggregated).
        Columns: uid (receiver), upline_uid (source_user), time, partner_count, rank.
        Data source: DreamMatrixCommission (payment_status in pending/processing/paid).
        """
        try:
            from ..dream_matrix.model import DreamMatrixCommission
            from ..user.model import User, PartnerGraph

            from datetime import datetime, timedelta
            since = datetime.utcnow() - timedelta(days=max(1, int(days or 30)))
            qs = DreamMatrixCommission.objects(
                payment_status__in=['pending', 'processing', 'paid'],
                created_at__gte=since
            ).only('user_id', 'source_user_id', 'created_at').order_by('-created_at')

            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 50)))
            skip = (page - 1) * limit
            entries = list(qs.skip(skip).limit(limit))
            total = qs.count()

            user_ids = [e.user_id for e in entries if getattr(e, 'user_id', None)]
            src_ids = [e.source_user_id for e in entries if getattr(e, 'source_user_id', None)]

            users = {str(u.id): u for u in User.objects(id__in=user_ids).only('uid', 'refered_by', 'current_rank')}
            sources = {str(u.id): u for u in User.objects(id__in=src_ids).only('uid')}
            graphs = {str(g.user_id): g for g in PartnerGraph.objects(user_id__in=user_ids).only('user_id', 'directs')}

            rows = []
            for e in entries:
                recv = users.get(str(getattr(e, 'user_id', '')))
                if not recv:
                    continue
                src = sources.get(str(getattr(e, 'source_user_id', '')))
                pg = graphs.get(str(getattr(e, 'user_id', '')))
                partner_count = len(getattr(pg, 'directs', []) if pg else [])
                rows.append({
                    "uid": getattr(recv, 'uid', None),
                    "upline_uid": getattr(src, 'uid', None) or 'ROOT',
                    "time": getattr(e, 'created_at', None).isoformat() if getattr(e, 'created_at', None) else None,
                    "partner_count": partner_count,
                    "rank": getattr(recv, 'current_rank', None)
                })

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

    def get_dream_matrix_partner_incentive(self, currency: str = "USDT", page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Return a paginated list of DISTINCT users who received Dream Matrix Partner Incentive-type earnings.
        Columns: uid (receiver), upline_uid (from latest tx), total_amount, time (latest earning).
        Reasons counted: matrix_partner_incentive, dream_matrix_partner_incentive, dream_matrix_commission, dream_matrix_*, matrix_partner_* (credits only).
        """
        try:
            import re
            from ..user.model import User

            # Aggregate by user: sum amounts, pick latest created_at and latest tx_hash
            pipeline = [
                {"$match": {
                    "type": "credit",
                    "currency": currency.upper(),
                    "$or": [
                        {"reason": {"$in": ["matrix_partner_incentive", "dream_matrix_partner_incentive", "dream_matrix_commission"]}},
                        {"reason": {"$regex": "^dream_matrix_"}},
                        {"reason": {"$regex": "^matrix_partner_"}}
                    ]
                }},
                {"$sort": {"created_at": -1}},  # so $first gets latest tx
                {"$group": {
                    "_id": "$user_id",
                    "total_amount": {"$sum": "$amount"},
                    "latest_at": {"$first": "$created_at"},
                    "latest_tx": {"$first": "$tx_hash"}
                }},
                {"$sort": {"latest_at": -1}}
            ]
            agg = list(WalletLedger.objects.aggregate(pipeline))

            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 50)))
            start = (page - 1) * limit
            end = start + limit
            page_rows = agg[start:end]
            total = len(agg)

            # Fetch users and uplines
            user_ids = [r.get("_id") for r in page_rows if r.get("_id")]
            users_map = {str(u.id): u for u in User.objects(id__in=user_ids).only('uid', 'refered_by')}
            # Collect possible uplines (from referrer fallback)
            ref_ids = []
            for u in users_map.values():
                rid = getattr(u, 'refered_by', None)
                if rid:
                    ref_ids.append(rid)
            ref_map = {str(u.id): u for u in User.objects(id__in=ref_ids).only('uid')}

            # Parse upline from latest tx_hash if present
            hex24 = re.compile(r"[0-9a-fA-F]{24}")
            rows = []
            for r in page_rows:
                uid_oid = r.get("_id")
                u = users_map.get(str(uid_oid))
                if not u:
                    continue
                latest_tx = str(r.get("latest_tx") or '')
                m = hex24.search(latest_tx)
                upline_uid = None
                if m and ref_map.get(m.group(0)):
                    upline_uid = getattr(ref_map[m.group(0)], 'uid', None)
                if not upline_uid and getattr(u, 'refered_by', None):
                    rid = str(getattr(u, 'refered_by'))
                    if rid in ref_map:
                        upline_uid = getattr(ref_map[rid], 'uid', None)

                rows.append({
                    "uid": getattr(u, 'uid', None),
                    "upline_uid": upline_uid or 'ROOT',
                    "amount": float(r.get("total_amount") or 0),
                    "time": r.get("latest_at").isoformat() if r.get("latest_at") else None
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
    def get_phase_1_income(self, currency: str = "USDT", page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get Global Program Phase-1 income data for all users - following dream matrix pattern"""
        try:
            from ..user.model import User
            
            # Get all Phase-1 income entries from WalletLedger
            phase_1_entries = WalletLedger.objects(
                type="credit",
                currency=currency.upper(),
                reason__regex="^global_phase_1"
            ).order_by('-created_at')
            
            total_entries = phase_1_entries.count()
            
            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 10)))
            start = (page - 1) * limit
            end = start + limit
            page_entries = phase_1_entries[start:end]
            
            # Format income data exactly like the image (User ID, Partner, Rank, USDT, Time & Date)
            items = []
            for i, entry in enumerate(page_entries):
                # Format date exactly like image (DD Mon YYYY (HH:MM))
                created_date = entry.created_at.strftime("%d %b %Y")
                created_time = entry.created_at.strftime("(%H:%M)")
                time_date = f"{created_date} {created_time}"
                
                # Get user info
                user = User.objects(id=entry.user_id).first()
                user_id = user.uid if user and hasattr(user, 'uid') else "Unknown"
                
                # Get partner count (direct referrals)
                partner_count = 0
                if user and hasattr(user, 'referrals'):
                    partner_count = len(user.referrals) if user.referrals else 0
                
                # Get rank (this would need to be calculated based on business logic)
                # For now, using a simple calculation based on partner count
                rank = min(partner_count + 1, 5) if partner_count > 0 else 1
                
                items.append({
                    "user_id": user_id,
                    "partner": partner_count,
                    "rank": rank,
                    "usdt": float(entry.amount),
                    "time_date": time_date
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
    def get_phase_2_income(self, currency: str = "USDT", page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get Global Program Phase-2 income data for all users - following dream matrix pattern"""
        try:
            from ..user.model import User
            
            # Get all Phase-2 income entries from WalletLedger
            phase_2_entries = WalletLedger.objects(
                type="credit",
                currency=currency.upper(),
                reason__regex="^global_phase_2"
            ).order_by('-created_at')
            
            total_entries = phase_2_entries.count()
            
            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 10)))
            start = (page - 1) * limit
            end = start + limit
            page_entries = phase_2_entries[start:end]
            
            # Format income data exactly like the image (User ID, Partner, Rank, USDT, Time & Date)
            items = []
            for i, entry in enumerate(page_entries):
                # Format date exactly like image (DD Mon YYYY (HH:MM))
                created_date = entry.created_at.strftime("%d %b %Y")
                created_time = entry.created_at.strftime("(%H:%M)")
                time_date = f"{created_date} {created_time}"
                
                # Get user info
                user = User.objects(id=entry.user_id).first()
                user_id = user.uid if user and hasattr(user, 'uid') else "Unknown"
                
                # Get partner count (direct referrals)
                partner_count = 0
                if user and hasattr(user, 'referrals'):
                    partner_count = len(user.referrals) if user.referrals else 0
                
                # Get rank (this would need to be calculated based on business logic)
                # For now, using a simple calculation based on partner count
                rank = min(partner_count + 1, 5) if partner_count > 0 else 1
                
                items.append({
                    "user_id": user_id,
                    "partner": partner_count,
                    "rank": rank,
                    "usdt": float(entry.amount),
                    "time_date": time_date
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
    def get_global_partner_incentive(self, currency: str = "USDT", page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get Global Partner Incentive data for all users - following dream matrix pattern"""
        try:
            from ..user.model import User
            
            # Get all Global Partner Incentive entries from WalletLedger
            incentive_entries = WalletLedger.objects(
                type="credit",
                currency=currency.upper(),
                reason="global_partner_incentive"
            ).order_by('-created_at')
            
            total_entries = incentive_entries.count()
            
            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 10)))
            start = (page - 1) * limit
            end = start + limit
            page_entries = incentive_entries[start:end]
            
            # Format income data exactly like the image (SL.No, ID, Upline, USDT, Time & Date)
            items = []
            for i, entry in enumerate(page_entries):
                # Format date exactly like image (DD Mon YYYY (HH:MM))
                created_date = entry.created_at.strftime("%d %b %Y")
                created_time = entry.created_at.strftime("(%H:%M)")
                time_date = f"{created_date} {created_time}"
                
                # Get user info
                user = User.objects(id=entry.user_id).first()
                user_id = user.uid if user and hasattr(user, 'uid') else "Unknown"
                
                # Get upline info (referrer of the user)
                upline_id = None
                if user and hasattr(user, 'refered_by') and user.refered_by:
                    upline = User.objects(id=user.refered_by).first()
                    if upline and hasattr(upline, 'uid'):
                        upline_id = upline.uid
                
                items.append({
                    "sl_no": start + i + 1,  # Sequential number starting from page offset
                    "id": user_id,
                    "upline": upline_id or "ROOT",
                    "usdt": float(entry.amount),
                    "time_date": time_date
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
            
            # Get missed profit entries for the user with currency filter
            missed_profits = MissedProfit.objects(
                user_id=ObjectId(user_id),
                currency=currency,
                is_active=True
            ).order_by('-created_at')
            
            total_entries = missed_profits.count()
            
            # Pagination
            page = max(1, int(page or 1))
            limit = max(1, min(100, int(limit or 50)))
            start = (page - 1) * limit
            end = start + limit
            page_entries = missed_profits[start:end]
            
            # Pre-fetch all users to optimize performance
            user_ids = set()
            for entry in page_entries:
                user_ids.add(entry.user_id)
                if hasattr(entry, 'upline_user_id') and entry.upline_user_id:
                    user_ids.add(entry.upline_user_id)
            
            # Batch fetch all users
            users = {str(u.id): u for u in User.objects(id__in=list(user_ids)).only('id', 'uid')}
            
            # Format data for frontend (matching the screenshot structure)
            items = []
            for i, entry in enumerate(page_entries):
                # Format date exactly like image (DD Mon YYYY (HH:MM))
                created_date = entry.created_at.strftime("%d %b %Y")
                created_time = entry.created_at.strftime("(%H:%M)")
                time_date = f"{created_date} {created_time}"
                
                # Get user info from pre-fetched data
                user = users.get(str(entry.user_id))
                user_display_id = str(entry.user_id)  # Show ObjectId instead of uid
                
                # Get partner info (the user who caused the miss profit - from_user_id)
                partner_id = None
                if hasattr(entry, 'upline_user_id') and entry.upline_user_id:
                    partner_id = str(entry.upline_user_id)  # Show ObjectId instead of uid
                
                # Get user's current rank/level for display
                user_level = entry.user_level
                
                # Dynamic currency field based on actual currency
                currency_field = f"miss_{currency.lower()}"
                
                items.append({
                    "user_id": user_display_id,
                    "partner": partner_id or "--",
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
            
            return {
                "success": True,
                "data": {
                    "page": page,
                    "limit": limit,
                    "total": total_entries,
                    "currency": currency,
                    "items": items,
                    "summary": {
                        "total_missed_amount": sum(float(item[currency_field]) for item in items),
                        "total_entries": len(items),
                        "undistributed_count": len([item for item in items if not item["is_distributed"]]),
                        "recovery_pending_count": len([item for item in items if item["recovery_status"] == "pending"])
                    }
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
