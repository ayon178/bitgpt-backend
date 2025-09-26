from decimal import Decimal
from datetime import datetime
from bson import ObjectId
from .model import UserWallet, WalletLedger
import re


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

        return {
            "success": True,
            "wallet_type": wallet_type,
            "balances": result,
            "today_income": today_income,
            # Single deduplicated count across currencies
            "today_sources": len(today_sources_set),
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
