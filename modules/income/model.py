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
        'newcomer_support', 'triple_entry', 'shareholders',
        'global_phase_1', 'global_phase_2', 'newcomer_growth_instant',
        'newcomer_growth_upline_fund', 'newcomer_growth_mother_fund',
        'newcomer_growth_monthly_distribution'
    ], required=True)
    amount = DecimalField(required=True, precision=8)
    percentage = DecimalField(required=True, precision=4)
    tx_hash = StringField(required=True)
    status = StringField(choices=['pending', 'completed', 'failed', 'pending_distribution'], default='pending')
    description = StringField(required=False)
    distribution_date = DateTimeField(required=False)
    updated_at = DateTimeField(required=False)
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

## Note: Leadership Stipend is centralized in modules/leadership_stipend/model.py
