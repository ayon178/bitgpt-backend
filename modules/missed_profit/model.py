from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, FloatField, ListField, EmbeddedDocumentField, EmbeddedDocument, DictField
from datetime import datetime

class MissedProfitReason(EmbeddedDocument):
    """Embedded document for missed profit reasons"""
    reason_type = StringField(choices=['account_inactivity', 'level_advancement'], required=True)
    reason_description = StringField(required=True)
    user_level = IntField(required=True)
    upgrade_slot_level = IntField(required=True)
    commission_amount = FloatField(required=True)
    currency = StringField(choices=['BNB', 'USDT'], default='BNB')
    is_recovered = BooleanField(default=False)
    recovered_at = DateTimeField()
    recovery_method = StringField(choices=['leadership_stipend', 'direct_distribution'], default='leadership_stipend')

class MissedProfit(Document):
    """Missed Profit Handling - Main document"""
    user_id = ObjectIdField(required=True)  # User who missed the profit
    upline_user_id = ObjectIdField(required=True)  # Upline who should have received commission
    
    # Missed profit details
    missed_profit_type = StringField(choices=['commission', 'bonus', 'upgrade_reward'], required=True)
    missed_profit_amount = FloatField(required=True)
    currency = StringField(choices=['BNB', 'USDT'], default='BNB')
    
    # Reason for missed profit
    reasons = ListField(EmbeddedDocumentField(MissedProfitReason), default=[])
    primary_reason = StringField(choices=['account_inactivity', 'level_advancement'], required=True)
    reason_description = StringField(required=True)
    
    # Context details
    user_level = IntField(required=True)
    upgrade_slot_level = IntField(required=True)
    program_type = StringField(choices=['binary', 'matrix', 'global'], required=True)
    
    # Status
    is_accumulated = BooleanField(default=False)
    accumulated_at = DateTimeField()
    is_distributed = BooleanField(default=False)
    distributed_at = DateTimeField()
    distribution_method = StringField(choices=['leadership_stipend', 'direct_distribution'], default='leadership_stipend')
    
    # Recovery tracking
    recovery_status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    recovery_amount = FloatField(default=0.0)
    recovery_reference = StringField()
    
    # Status
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    last_updated = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'missed_profit',
        'indexes': [
            'user_id',
            'upline_user_id',
            'primary_reason',
            'program_type',
            'is_accumulated',
            'is_distributed',
            'recovery_status'
        ]
    }

class MissedProfitAccumulation(Document):
    """Track missed profit accumulation"""
    accumulation_period = StringField(choices=['daily', 'weekly', 'monthly'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField(required=True)
    
    # Accumulation details
    total_missed_profits = FloatField(default=0.0)
    total_missed_profits_bnb = FloatField(default=0.0)
    total_missed_profits_usdt = FloatField(default=0.0)
    
    # Reason breakdown
    account_inactivity_count = IntField(default=0)
    account_inactivity_amount = FloatField(default=0.0)
    level_advancement_count = IntField(default=0)
    level_advancement_amount = FloatField(default=0.0)
    
    # Program breakdown
    binary_missed_count = IntField(default=0)
    binary_missed_amount = FloatField(default=0.0)
    matrix_missed_count = IntField(default=0)
    matrix_missed_amount = FloatField(default=0.0)
    global_missed_count = IntField(default=0)
    global_missed_amount = FloatField(default=0.0)
    
    # Status
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'missed_profit_accumulation',
        'indexes': [
            'accumulation_period',
            'period_start',
            'period_end',
            'is_processed'
        ]
    }

class MissedProfitDistribution(Document):
    """Track missed profit distribution via Leadership Stipend"""
    distribution_period = StringField(choices=['daily', 'weekly', 'monthly'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField(required=True)
    
    # Distribution details
    total_distributed_amount = FloatField(default=0.0)
    total_distributed_amount_bnb = FloatField(default=0.0)
    total_distributed_amount_usdt = FloatField(default=0.0)
    
    # Recipients
    total_recipients = IntField(default=0)
    recipients = ListField(ObjectIdField(), default=[])
    
    # Distribution breakdown
    leadership_stipend_distributions = IntField(default=0)
    leadership_stipend_amount = FloatField(default=0.0)
    direct_distributions = IntField(default=0)
    direct_distribution_amount = FloatField(default=0.0)
    
    # Status
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'missed_profit_distribution',
        'indexes': [
            'distribution_period',
            'period_start',
            'period_end',
            'is_processed'
        ]
    }

class MissedProfitFund(Document):
    """Missed Profit Fund management"""
    fund_name = StringField(default='Missed Profit Fund', unique=True)
    
    # Fund details
    total_fund_amount = FloatField(default=0.0)
    available_amount = FloatField(default=0.0)
    distributed_amount = FloatField(default=0.0)
    currency = StringField(choices=['BNB', 'USDT'], default='BNB')
    
    # Fund sources
    fund_sources = DictField(default={
        'missed_commissions': 0.0,
        'missed_bonuses': 0.0,
        'missed_upgrade_rewards': 0.0,
        'account_inactivity': 0.0,
        'level_advancement': 0.0,
        'other_contributions': 0.0
    })
    
    # Fund management
    auto_replenish = BooleanField(default=True)
    replenish_threshold = FloatField(default=1000.0)  # Replenish when below threshold
    max_distribution_per_day = FloatField(default=10000.0)  # Max distribution per day
    
    # Statistics
    total_missed_profits_accumulated = IntField(default=0)
    total_distributions_made = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'missed_profit_fund',
        'indexes': ['fund_name', 'is_active']
    }

class MissedProfitSettings(Document):
    """Missed Profit system settings"""
    setting_name = StringField(default='Missed Profit Settings', unique=True)
    
    # General settings
    missed_profit_enabled = BooleanField(default=True)
    auto_accumulation = BooleanField(default=True)
    auto_distribution = BooleanField(default=True)
    
    # Accumulation settings
    accumulation_period = StringField(choices=['daily', 'weekly', 'monthly'], default='daily')
    accumulation_threshold = FloatField(default=100.0)  # Minimum amount to accumulate
    
    # Distribution settings
    distribution_method = StringField(choices=['leadership_stipend', 'direct_distribution'], default='leadership_stipend')
    distribution_period = StringField(choices=['daily', 'weekly', 'monthly'], default='weekly')
    distribution_threshold = FloatField(default=500.0)  # Minimum amount to distribute
    
    # Recovery settings
    recovery_enabled = BooleanField(default=True)
    recovery_period_days = IntField(default=30)  # Days to attempt recovery
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'missed_profit_settings',
        'indexes': ['setting_name', 'is_active']
    }

class MissedProfitLog(Document):
    """Missed Profit activity log"""
    user_id = ObjectIdField(required=True)
    action_type = StringField(choices=[
        'missed_profit_created', 'missed_profit_accumulated', 'missed_profit_distributed',
        'recovery_attempted', 'recovery_completed', 'fund_updated'
    ], required=True)
    
    # Action details
    action_description = StringField(required=True)
    action_data = DictField(default={})
    
    # Related entities
    related_missed_profit_id = ObjectIdField()
    related_upline_id = ObjectIdField()
    amount = FloatField()
    currency = StringField()
    
    # Status
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'missed_profit_log',
        'indexes': [
            'user_id',
            'action_type',
            'created_at',
            'is_processed'
        ]
    }

class MissedProfitStatistics(Document):
    """Missed Profit program statistics"""
    period = StringField(choices=['daily', 'weekly', 'monthly', 'all_time'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField()
    
    # Statistics
    total_missed_profits = IntField(default=0)
    total_missed_amount = FloatField(default=0.0)
    total_accumulated_amount = FloatField(default=0.0)
    total_distributed_amount = FloatField(default=0.0)
    
    # Reason breakdown
    account_inactivity_count = IntField(default=0)
    account_inactivity_amount = FloatField(default=0.0)
    level_advancement_count = IntField(default=0)
    level_advancement_amount = FloatField(default=0.0)
    
    # Program breakdown
    binary_missed_count = IntField(default=0)
    binary_missed_amount = FloatField(default=0.0)
    matrix_missed_count = IntField(default=0)
    matrix_missed_amount = FloatField(default=0.0)
    global_missed_count = IntField(default=0)
    global_missed_amount = FloatField(default=0.0)
    
    # Distribution breakdown
    leadership_stipend_distributions = IntField(default=0)
    leadership_stipend_amount = FloatField(default=0.0)
    direct_distributions = IntField(default=0)
    direct_distribution_amount = FloatField(default=0.0)
    
    # Recovery statistics
    total_recovery_attempts = IntField(default=0)
    successful_recoveries = IntField(default=0)
    failed_recoveries = IntField(default=0)
    recovery_amount = FloatField(default=0.0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'missed_profit_statistics',
        'indexes': [
            'period',
            'period_start',
            'is_active'
        ]
    }

class MissedProfitRecovery(Document):
    """Track missed profit recovery attempts"""
    missed_profit_id = ObjectIdField(required=True)
    user_id = ObjectIdField(required=True)
    upline_user_id = ObjectIdField(required=True)
    
    # Recovery details
    recovery_type = StringField(choices=['automatic', 'manual'], required=True)
    recovery_method = StringField(choices=['leadership_stipend', 'direct_distribution', 'bonus_adjustment'], required=True)
    recovery_amount = FloatField(required=True)
    currency = StringField(choices=['BNB', 'USDT'], default='BNB')
    
    # Recovery status
    recovery_status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    recovery_reference = StringField()
    
    # Recovery processing
    processed_at = DateTimeField()
    completed_at = DateTimeField()
    failed_reason = StringField()
    
    # Status
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    last_updated = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'missed_profit_recovery',
        'indexes': [
            'missed_profit_id',
            'user_id',
            'upline_user_id',
            'recovery_status',
            'created_at'
        ]
    }
