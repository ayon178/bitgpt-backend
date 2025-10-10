from mongoengine import Document, StringField, IntField, DecimalField, DateTimeField, ListField, ObjectIdField
from datetime import datetime
from decimal import Decimal

class SparkCycle(Document):
    """Matrix slot-based distribution - Spark Bonus 8%"""
    cycle_no = IntField(required=True)
    slot_no = IntField(required=True)
    pool_amount = DecimalField(required=True, precision=8)
    participants = ListField(ObjectIdField(), default=[])
    distribution_percentage = DecimalField(required=True, precision=4)
    payout_per_participant = DecimalField(required=True, precision=8)
    status = StringField(choices=['active', 'completed'], default='active')
    payout_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'spark_cycle',
        'indexes': [('cycle_no', 'slot_no'), 'status']
    }

class TripleEntryReward(Document):
    """Track TER fund distributions"""
    cycle_no = IntField(required=True)
    pool_amount = DecimalField(required=True, precision=8)
    eligible_users = ListField(ObjectIdField(), default=[])
    distribution_amount = DecimalField(required=True, precision=8)
    status = StringField(choices=['active', 'distributed'], default='active')
    distributed_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'triple_entry_reward',
        'indexes': ['cycle_no', 'status']
    }

class SparkBonusDistribution(Document):
    """Track Spark Bonus fund distributions to Matrix slot users"""
    user_id = ObjectIdField(required=True)
    slot_number = IntField(required=True)
    distribution_amount = DecimalField(required=True, precision=8)
    currency = StringField(choices=['USDT', 'BNB', 'USD'], default='USDT')
    
    # Distribution details
    fund_source = StringField(choices=['spark_bonus', 'triple_entry'], required=True)
    distribution_percentage = DecimalField(required=True, precision=4)
    total_fund_amount = DecimalField(required=True, precision=8)
    
    # Matrix slot details
    matrix_slot_name = StringField()
    matrix_slot_level = IntField()
    
    # Status
    status = StringField(choices=['pending', 'completed', 'failed'], default='pending')
    distributed_at = DateTimeField()
    
    # Transaction details
    wallet_credit_tx_hash = StringField()
    wallet_credit_status = StringField(choices=['pending', 'completed', 'failed'], default='pending')
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'spark_bonus_distributions',
        'indexes': [
            'user_id',
            'slot_number',
            'fund_source',
            'status',
            'created_at'
        ]
    }


class SparkSlotClaimLedger(Document):
    """Track per-slot claim deductions to adjust allocated amounts in the UI.
    This does NOT change the total Spark fund summary; it only reduces the
    slot's displayed allocated_amount for the current cycle/day.
    """
    slot_number = IntField(required=True)
    currency = StringField(choices=['USDT', 'BNB'], required=True)
    amount = DecimalField(required=True, precision=8)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'spark_slot_claim_ledger',
        'indexes': [
            ('slot_number', 'currency', 'created_at')
        ]
    }


class TripleEntryPayment(Document):
    """Track Triple Entry Reward claim/payment history"""
    user_id = ObjectIdField(required=True)
    amount = DecimalField(required=True, precision=8)
    currency = StringField(choices=['USDT', 'BNB'], required=True)
    
    # Payment details
    status = StringField(choices=['pending', 'paid', 'failed'], default='paid')
    paid_at = DateTimeField()
    
    # Transaction details
    tx_hash = StringField()
    
    # Eligibility info
    eligible_users_count = IntField()  # Total eligible users at time of claim
    total_fund_amount = DecimalField(precision=8)  # Total TER fund at time of claim
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'triple_entry_payments',
        'indexes': [
            'user_id',
            'currency',
            'status',
            'created_at'
        ]
    }