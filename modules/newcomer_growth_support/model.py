#!/usr/bin/env python3
"""
Newcomer Growth Support Models
Database models for newcomer growth support tracking
"""

from mongoengine import Document, StringField, ObjectIdField, DecimalField, IntField, BooleanField, DateTimeField, DictField, ListField
from datetime import datetime
from decimal import Decimal

class NewcomerGrowthSupport(Document):
    """Track newcomer growth support distributions"""
    user_id = ObjectIdField(required=True)
    referrer_id = ObjectIdField(required=False)
    total_amount = DecimalField(required=True)
    
    # Split amounts
    instant_amount = DecimalField(required=True)
    upline_fund_amount = DecimalField(required=True)
    
    # Distribution details
    instant_claimed = BooleanField(default=False)
    instant_claim_date = DateTimeField(required=False)
    upline_fund_created = BooleanField(default=False)
    upline_fund_creation_date = DateTimeField(required=False)
    
    # Monthly distribution tracking
    monthly_distribution_date = DateTimeField(required=False)
    monthly_distribution_completed = BooleanField(default=False)
    monthly_distribution_amount = DecimalField(required=False)
    
    # Status
    status = StringField(choices=['pending', 'instant_claimed', 'upline_fund_created', 'monthly_distributed', 'completed'], default='pending')
    
    # Transaction details
    tx_hash = StringField(required=True)
    program = StringField(choices=['matrix'], default='matrix')
    slot_no = IntField(default=1)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'newcomer_growth_support',
        'indexes': [
            'user_id',
            'referrer_id',
            'status',
            'created_at',
            'tx_hash'
        ]
    }

class NewcomerGrowthFund(Document):
    """Track upline funds for monthly distribution"""
    upline_id = ObjectIdField(required=True)
    total_fund_amount = DecimalField(required=True)
    remaining_amount = DecimalField(required=True)
    
    # Distribution cycle
    distribution_cycle_days = IntField(default=30)
    next_distribution_date = DateTimeField(required=True)
    last_distribution_date = DateTimeField(required=False)
    
    # Direct referrals count
    direct_referrals_count = IntField(default=0)
    
    # Status
    is_active = BooleanField(default=True)
    status = StringField(choices=['active', 'paused', 'completed'], default='active')
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'newcomer_growth_funds',
        'indexes': [
            'upline_id',
            'status',
            'next_distribution_date',
            'is_active'
        ]
    }

class NewcomerGrowthDistribution(Document):
    """Track individual monthly distributions"""
    upline_id = ObjectIdField(required=True)
    recipient_id = ObjectIdField(required=True)
    distribution_amount = DecimalField(required=True)
    
    # Distribution details
    distribution_cycle = IntField(required=True)  # Which cycle (1, 2, 3, etc.)
    distribution_date = DateTimeField(required=True)
    
    # Status
    status = StringField(choices=['pending', 'completed', 'failed'], default='pending')
    error_message = StringField(required=False)
    
    # Transaction details
    tx_hash = StringField(required=True)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField(required=False)
    
    meta = {
        'collection': 'newcomer_growth_distributions',
        'indexes': [
            'upline_id',
            'recipient_id',
            'distribution_date',
            'status',
            'distribution_cycle'
        ]
    }

class NewcomerGrowthAudit(Document):
    """Audit trail for newcomer growth support changes"""
    action = StringField(choices=['create', 'instant_claim', 'upline_fund', 'monthly_distribution', 'update'], required=True)
    
    # Affected users
    user_id = ObjectIdField(required=True)
    referrer_id = ObjectIdField(required=False)
    
    # Change details
    old_values = DictField(required=False)
    new_values = DictField(required=False)
    
    # Amount details
    amount = DecimalField(required=False)
    instant_amount = DecimalField(required=False)
    upline_fund_amount = DecimalField(required=False)
    
    # Additional context
    description = StringField(required=False)
    tx_hash = StringField(required=False)
    
    # Timestamp
    action_date = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'newcomer_growth_audits',
        'indexes': [
            'action',
            'user_id',
            'referrer_id',
            'action_date'
        ]
    }
