from mongoengine import Document, StringField, DecimalField, DateTimeField, IntField
from datetime import datetime
from decimal import Decimal

class BonusFund(Document):
    """Track bonus funds for different types - Separate Fund Tracking"""
    fund_type = StringField(choices=[
        'spark_bonus', 'royal_captain', 'president_reward', 
        'leadership_stipend', 'jackpot_entry', 'partner_incentive',
        'shareholders', 'newcomer_support', 'mentorship_bonus'
    ], required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    total_collected = DecimalField(default=Decimal('0.00'), precision=8)
    total_distributed = DecimalField(default=Decimal('0.00'), precision=8)
    current_balance = DecimalField(default=Decimal('0.00'), precision=8)
    status = StringField(choices=['active', 'paused'], default='active')
    last_distribution = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'bonus_fund',
        'indexes': [('fund_type', 'program'), 'status']
    }

class FundDistribution(Document):
    """Track when and how funds are distributed - Distribution Control"""
    fund_type = StringField(required=True)
    program = StringField(required=True)
    distribution_amount = DecimalField(required=True, precision=8)
    distribution_type = StringField(choices=['daily', 'weekly', 'monthly', 'on_demand'], required=True)
    beneficiaries_count = IntField(required=True)
    distribution_date = DateTimeField(required=True)
    status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    tx_hash = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'fund_distribution',
        'indexes': [('fund_type', 'program'), 'distribution_date', 'status']
    }
