from mongoengine import Document, StringField, ObjectIdField, DecimalField, DateTimeField, IntField
from datetime import datetime
from decimal import Decimal

class UserWallet(Document):
    """User wallet balances for different purposes"""
    user_id = ObjectIdField(required=True)
    wallet_type = StringField(choices=['main', 'reserve', 'matrix', 'global'], required=True)
    balance = DecimalField(default=Decimal('0.00'), precision=8)
    currency = StringField(default='USDT')
    last_updated = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'user_wallets',
        # Add currency to index to uniquely identify a balance doc per currency
        'indexes': [('user_id', 'wallet_type', 'currency')]
    }

class ReserveLedger(Document):
    """Track reserve fund movements"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    slot_no = IntField(required=True)
    amount = DecimalField(required=True, precision=8)
    direction = StringField(choices=['credit', 'debit'], required=True)
    source = StringField(choices=['income', 'manual', 'transfer'], required=True)
    balance_after = DecimalField(required=True, precision=8)
    tx_hash = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'reserve_ledger',
        'indexes': [('user_id', 'program'), 'tx_hash', ('program', 'slot_no')]
    }

class WalletLedger(Document):
    """Track main wallet transactions"""
    user_id = ObjectIdField(required=True)
    amount = DecimalField(required=True, precision=8)
    currency = StringField(default='USDT')
    type = StringField(choices=['credit', 'debit'], required=True)
    reason = StringField(required=True)
    balance_after = DecimalField(required=True, precision=8)
    tx_hash = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'wallet_ledger',
        'indexes': [('user_id', 'created_at'), 'tx_hash']
    }
