from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, DecimalField, ListField, DictField, FloatField, EmbeddedDocumentField, EmbeddedDocument
from datetime import datetime
from decimal import Decimal

class CommissionType(EmbeddedDocument):
    """Commission type information"""
    commission_type = StringField(choices=[
        'joining', 'upgrade', 'binary_partner', 'matrix_partner', 
        'global_partner', 'royal_captain', 'president_reward',
        'leadership_stipend', 'spark_bonus', 'mentorship', 'missed_profit'
    ], required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    percentage = FloatField(required=True)
    description = StringField()

class Commission(Document):
    """Centralized commission tracking and distribution"""
    user_id = ObjectIdField(required=True)  # User who receives commission
    from_user_id = ObjectIdField(required=True)  # User who generated commission
    
    # Commission details
    commission_type = StringField(choices=[
        'joining', 'upgrade', 'binary_partner', 'matrix_partner', 
        'global_partner', 'royal_captain', 'president_reward',
        'leadership_stipend', 'spark_bonus', 'mentorship', 'missed_profit'
    ], required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    
    # Amount and currency
    commission_amount = DecimalField(required=True, precision=8)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    commission_percentage = FloatField(required=True)
    
    # Source information
    source_slot_no = IntField()  # Which slot generated this commission
    source_slot_name = StringField()
    source_transaction_id = ObjectIdField()  # Reference to activation/upgrade
    
    # Level information for upgrade commissions
    level = IntField()  # Which level this commission is for
    is_direct_commission = BooleanField(default=False)  # Direct upline commission
    is_level_commission = BooleanField(default=False)  # Level-based commission (30%)
    
    # Distribution information
    distribution_type = StringField(choices=['direct', 'level', 'missed'], default='direct')
    distribution_level = IntField()  # For level-based distribution (1-16)
    
    # Status and processing
    status = StringField(choices=['pending', 'paid', 'missed', 'accumulated'], default='pending')
    paid_at = DateTimeField()
    accumulated_at = DateTimeField()  # When moved to Leadership Stipend
    
    # Transaction details
    tx_hash = StringField()
    blockchain_network = StringField(choices=['BSC', 'ETH', 'TRC20'], default='BSC')
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'commissions',
        'indexes': [
            'user_id',
            'from_user_id',
            'commission_type',
            'program',
            'status',
            'level',
            'created_at'
        ]
    }

class CommissionDistribution(Document):
    """Track commission distribution across levels 1-16"""
    source_commission_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    source_user_id = ObjectIdField(required=True)  # User who generated the commission
    source_slot_no = IntField(required=True)
    
    # Distribution details
    total_amount = DecimalField(required=True, precision=8)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    
    # Level distribution (70% distributed across levels 1-16)
    level_distributions = ListField(DictField(), default=[])  # [{level: 1, amount: 0.1, user_id: ObjectId}]
    
    # Direct commission (30% to corresponding level upline)
    direct_commission_amount = DecimalField(precision=8, default=0)
    direct_commission_user_id = ObjectIdField()
    direct_commission_level = IntField()
    
    # Status
    status = StringField(choices=['pending', 'distributed', 'partial', 'failed'], default='pending')
    distributed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'commission_distributions',
        'indexes': [
            'source_commission_id',
            'source_user_id',
            'program',
            'status'
        ]
    }

## Note: MissedProfit domain is centralized in modules/missed_profit/model.py

## Note: Leadership Stipend domain is centralized in modules/leadership_stipend/model.py

class CommissionRule(Document):
    """Define commission rules and percentages"""
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    commission_type = StringField(choices=[
        'joining', 'upgrade', 'level', 'bonus', 'stipend'
    ], required=True)
    
    # Commission structure
    percentage = FloatField(required=True)
    fixed_amount = DecimalField(precision=8)  # For fixed amount commissions
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    
    # Level-based commission rules
    level_commission_percentage = FloatField(default=30.0)  # 30% for corresponding level
    level_distribution_percentage = FloatField(default=70.0)  # 70% for levels 1-16
    
    # Conditions
    minimum_slot_level = IntField(default=1)
    maximum_slot_level = IntField(default=16)
    requires_active_status = BooleanField(default=True)
    
    # Status
    is_active = BooleanField(default=True)
    effective_from = DateTimeField(default=datetime.utcnow)
    effective_until = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'commission_rules',
        'indexes': [
            'program',
            'commission_type',
            'is_active',
            'effective_from'
        ]
    }

class CommissionAccumulation(Document):
    """Track commission accumulation for users"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    
    # Accumulation details
    total_earned = DecimalField(precision=8, default=0)
    total_paid = DecimalField(precision=8, default=0)
    total_missed = DecimalField(precision=8, default=0)
    total_accumulated = DecimalField(precision=8, default=0)
    
    # Currency breakdown
    currency_totals = DictField(default={
        'BNB': Decimal('0'),
        'USDT': Decimal('0'),
        'USD': Decimal('0')
    })
    
    # Commission type breakdown
    commission_type_totals = DictField(default={
        'joining': Decimal('0'),
        'upgrade': Decimal('0'),
        'level': Decimal('0'),
        'bonus': Decimal('0'),
        'stipend': Decimal('0')
    })
    
    # Last update
    last_commission_at = DateTimeField()
    last_payment_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'commission_accumulations',
        'indexes': [
            'user_id',
            'program',
            'last_commission_at'
        ]
    }

class CommissionPayment(Document):
    """Track commission payments to users"""
    user_id = ObjectIdField(required=True)
    commission_ids = ListField(ObjectIdField(), required=True)  # Commissions being paid
    
    # Payment details
    total_amount = DecimalField(required=True, precision=8)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    payment_method = StringField(choices=['wallet', 'bank', 'crypto'], required=True)
    
    # Transaction details
    tx_hash = StringField()
    blockchain_network = StringField(choices=['BSC', 'ETH', 'TRC20'])
    payment_reference = StringField()  # Bank reference or other payment reference
    
    # Status
    status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    processed_at = DateTimeField()
    completed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'commission_payments',
        'indexes': [
            'user_id',
            'status',
            'created_at'
        ]
    }

class DistributionReceipt(Document):
    """Receipt record for distributions at the time of commission distribution.
    Captures who received how much, when, from which event and level.
    """
    # Participants
    user_id = ObjectIdField(required=True)  # Receiver
    from_user_id = ObjectIdField(required=True)  # Originator of earnings

    # Context
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    source_type = StringField(choices=[
        'joining', 'upgrade', 'level', 'stipend', 'bonus'
    ], required=True)
    source_slot_no = IntField()
    source_slot_name = StringField()
    distribution_level = IntField()  # For level distributions (1-16)

    # Financials
    amount = DecimalField(required=True, precision=8)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)

    # Optional linkage
    commission_id = ObjectIdField()  # Direct/level commission record
    distribution_id = ObjectIdField()  # CommissionDistribution record for level splits

    # Metadata
    event = StringField(choices=[
        'joining_commission', 'upgrade_level_commission', 'level_distribution',
        'stipend_distribution', 'bonus_distribution'
    ], required=True)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'distribution_receipts',
        'indexes': [
            'user_id',
            'from_user_id',
            'program',
            'source_type',
            'distribution_level',
            'created_at'
        ]
    }