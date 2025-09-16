from decimal import Decimal
from datetime import datetime
from .company_model import CompanyWallet, CompanyWalletLedger

class CompanyWalletService:
    """Service for managing the company/root main wallet."""

    def __init__(self) -> None:
        pass

    def _get_or_create_wallet(self, currency: str = 'USDT') -> CompanyWallet:
        wallet = CompanyWallet.objects(wallet_name='main').first()
        if not wallet:
            wallet = CompanyWallet(wallet_name='main', currency=currency)
            wallet.balance = Decimal('0')
            wallet.save()
        return wallet

    def credit(self, amount: Decimal, currency: str, reason: str, tx_hash: str) -> dict:
        wallet = self._get_or_create_wallet(currency)
        new_balance = (wallet.balance or Decimal('0')) + Decimal(str(amount))
        wallet.balance = new_balance
        wallet.last_updated = datetime.utcnow()
        wallet.save()
        CompanyWalletLedger(
            amount=Decimal(str(amount)),
            currency=currency,
            type='credit',
            reason=reason,
            balance_after=new_balance,
            tx_hash=tx_hash,
            created_at=datetime.utcnow()
        ).save()
        return {"success": True, "balance": float(new_balance)}

    def debit(self, amount: Decimal, currency: str, reason: str, tx_hash: str) -> dict:
        wallet = self._get_or_create_wallet(currency)
        new_balance = (wallet.balance or Decimal('0')) - Decimal(str(amount))
        if new_balance < 0:
            return {"success": False, "error": "Insufficient company balance"}
        wallet.balance = new_balance
        wallet.last_updated = datetime.utcnow()
        wallet.save()
        CompanyWalletLedger(
            amount=Decimal(str(amount)),
            currency=currency,
            type='debit',
            reason=reason,
            balance_after=new_balance,
            tx_hash=tx_hash,
            created_at=datetime.utcnow()
        ).save()
        return {"success": True, "balance": float(new_balance)}
