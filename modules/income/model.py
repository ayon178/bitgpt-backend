from mongoengine import Document, StringField, ObjectIdField, DecimalField, DateTimeField, IntField, BooleanField
from datetime import datetime
from decimal import Decimal

class IncomeEvent(Document):
    """All income distributions and bonuses"""
    user_id = ObjectIdField(required=True)
    source_user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    slot_no = IntField(required=True)
    income_type = StringField(choices=[
        'level_payout', 'partner_incentive', 'spark_bonus', 'royal_captain',
        'president_reward', 'leadership_stipend', 'jackpot', 'mentorship',
        'newcomer_support', 'triple_entry', 'shareholders'
    ], required=True)
    amount = DecimalField(required=True, precision=8)
    percentage = DecimalField(required=True, precision=4)
    tx_hash = StringField(required=True)
    status = StringField(choices=['pending', 'completed', 'failed'], default='pending')
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'income_event',
        'indexes': [('user_id', 'created_at'), 'tx_hash', ('program', 'slot_no')]
    }

class SpilloverEvent(Document):
    """Track spillover occurrences"""
    from_user_id = ObjectIdField(required=True)
    to_user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    slot_no = IntField(required=True)
    amount = DecimalField(required=True, precision=8)
    spillover_type = StringField(choices=['upline_30_percent', 'leadership_stipend'], required=True)
    tx_hash = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'spillover_event',
        'indexes': [('from_user_id', 'program'), ('to_user_id', 'program'), 'tx_hash']
    }

class LeadershipStipend(Document):
    """Track leadership stipend distributions - Slot 10-16 rewards"""
    user_id = ObjectIdField(required=True)
    slot_no = IntField(required=True)
    target_amount = DecimalField(required=True, precision=8)
    current_amount = DecimalField(required=True, precision=8)
    is_active = BooleanField(default=True)
    started_at = DateTimeField(required=True)
    completed_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'leadership_stipend',
        'indexes': [('user_id', 'slot_no'), 'is_active']
    }
