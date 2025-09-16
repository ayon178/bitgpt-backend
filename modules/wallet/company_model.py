from mongoengine import Document, StringField, DecimalField, DateTimeField
from datetime import datetime
from decimal import Decimal

class CompanyWallet(Document):
    """Company/root wallet to accumulate company profits and missed profits."""
    wallet_name = StringField(default='main', choices=['main'], required=True)
    balance = DecimalField(default=Decimal('0.00'), precision=8)
    currency = StringField(default='USDT')
    last_updated = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'company_wallets',
        'indexes': ['wallet_name']
    }

class CompanyWalletLedger(Document):
    """Audit ledger for company wallet transactions"""
    amount = DecimalField(required=True, precision=8)
    currency = StringField(default='USDT')
    type = StringField(choices=['credit', 'debit'], required=True)
    reason = StringField(required=True)
    balance_after = DecimalField(required=True, precision=8)
    tx_hash = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'company_wallet_ledger',
        'indexes': ['created_at', 'tx_hash']
    }
