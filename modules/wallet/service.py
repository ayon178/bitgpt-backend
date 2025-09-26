from decimal import Decimal
from datetime import datetime
from bson import ObjectId
from .model import UserWallet, WalletLedger


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
        return {"success": True, "wallet_type": wallet_type, "balances": result}

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
