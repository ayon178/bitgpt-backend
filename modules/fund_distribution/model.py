#!/usr/bin/env python3
"""
Fund Distribution Models
Database models for fund distribution tracking
"""

from mongoengine import Document, StringField, ObjectIdField, DecimalField, IntField, BooleanField, DateTimeField, DictField, ListField
from datetime import datetime
from decimal import Decimal

class FundDistribution(Document):
    """Track fund distributions across all programs"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    slot_no = IntField(required=True)
    total_amount = DecimalField(required=True)
    distribution_type = StringField(required=True)  # 'slot_activation', 'upgrade', 'bonus', etc.
    tx_hash = StringField(required=True)
    
    # Distribution breakdown
    distributions = ListField(DictField(), required=True)
    total_distributed = DecimalField(required=True)
    
    # Status tracking
    status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    error_message = StringField(required=False)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField(required=False)
    
    # Metadata
    referrer_id = ObjectIdField(required=False)
    source_user_id = ObjectIdField(required=True)
    
    meta = {
        'collection': 'fund_distributions',
        'indexes': [
            'user_id',
            'program',
            'slot_no',
            'status',
            'created_at',
            'tx_hash'
        ]
    }

class DistributionBreakdown(Document):
    """Detailed breakdown of individual distributions"""
    distribution_id = ObjectIdField(required=True)  # Reference to FundDistribution
    recipient_id = ObjectIdField(required=True)
    income_type = StringField(required=True)
    amount = DecimalField(required=True)
    percentage = DecimalField(required=True)
    description = StringField(required=True)
    
    # Status
    status = StringField(choices=['pending', 'completed', 'failed'], default='pending')
    error_message = StringField(required=False)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField(required=False)
    
    meta = {
        'collection': 'distribution_breakdowns',
        'indexes': [
            'distribution_id',
            'recipient_id',
            'income_type',
            'status',
            'created_at'
        ]
    }

class ProgramDistributionConfig(Document):
    """Configuration for program-specific distribution percentages"""
    program = StringField(choices=['binary', 'matrix', 'global'], required=True, unique=True)
    
    # Distribution percentages
    spark_bonus = DecimalField(default=Decimal('0.0'))
    royal_captain_bonus = DecimalField(default=Decimal('0.0'))
    president_reward = DecimalField(default=Decimal('0.0'))
    leadership_stipend = DecimalField(default=Decimal('0.0'))
    jackpot_entry = DecimalField(default=Decimal('0.0'))
    newcomer_growth_support = DecimalField(default=Decimal('0.0'))
    mentorship_bonus = DecimalField(default=Decimal('0.0'))
    partner_incentive = DecimalField(default=Decimal('0.0'))
    share_holders = DecimalField(default=Decimal('0.0'))
    level_distribution = DecimalField(default=Decimal('0.0'))
    tree_upline_reserve = DecimalField(default=Decimal('0.0'))
    tree_upline_wallet = DecimalField(default=Decimal('0.0'))
    triple_entry_reward = DecimalField(default=Decimal('0.0'))
    
    # Level breakdown (for programs that use it)
    level_breakdown = DictField(required=False)
    
    # Metadata
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'program_distribution_configs',
        'indexes': [
            'program',
            'is_active'
        ]
    }

class DistributionAudit(Document):
    """Audit trail for distribution changes"""
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    action = StringField(choices=['create', 'update', 'delete', 'distribute'], required=True)
    
    # Change details
    old_values = DictField(required=False)
    new_values = DictField(required=False)
    
    # User who made the change
    changed_by = ObjectIdField(required=True)
    
    # Timestamp
    changed_at = DateTimeField(default=datetime.utcnow)
    
    # Additional context
    description = StringField(required=False)
    
    meta = {
        'collection': 'distribution_audits',
        'indexes': [
            'program',
            'action',
            'changed_by',
            'changed_at'
        ]
    }
