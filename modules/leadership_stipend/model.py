from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, FloatField, ListField, EmbeddedDocumentField, EmbeddedDocument, DictField
from datetime import datetime

class LeadershipStipendTier(EmbeddedDocument):
    """Embedded document for Leadership Stipend tiers"""
    slot_number = IntField(required=True)  # 10-17
    tier_name = StringField(required=True)  # LEADER, VANGURD, etc.
    slot_value = FloatField(required=True)  # Slot value in BNB
    daily_return = FloatField(required=True)  # Double the slot value
    currency = StringField(choices=['BNB'], default='BNB')
    is_active = BooleanField(default=False)
    activated_at = DateTimeField()
    total_earned = FloatField(default=0.0)
    total_paid = FloatField(default=0.0)
    pending_amount = FloatField(default=0.0)

class LeadershipStipend(Document):
    """Leadership Stipend Program - Main document"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Program status
    is_eligible = BooleanField(default=False)
    is_active = BooleanField(default=False)
    joined_at = DateTimeField()
    qualified_at = DateTimeField()
    
    # Current stipend status
    current_tier = IntField(default=0)  # 0 = not eligible, 10-17 = slot number
    current_tier_name = StringField(default="")
    current_daily_return = FloatField(default=0.0)
    
    # Stipend tiers
    tiers = ListField(EmbeddedDocumentField(LeadershipStipendTier), default=[])
    
    # Earnings tracking
    total_earned = FloatField(default=0.0)
    total_paid = FloatField(default=0.0)
    pending_amount = FloatField(default=0.0)
    last_payment_date = DateTimeField()
    
    # Slot tracking
    highest_slot_achieved = IntField(default=0)
    slots_activated = ListField(IntField(), default=[])
    
    # Daily calculation
    daily_calculation_enabled = BooleanField(default=True)
    last_calculation_date = DateTimeField()
    calculation_frequency = StringField(choices=['daily', 'weekly', 'monthly'], default='daily')
    
    # Status
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'leadership_stipend',
        'indexes': [
            'user_id',
            'is_eligible',
            'is_active',
            'current_tier',
            'highest_slot_achieved'
        ]
    }

class LeadershipStipendEligibility(Document):
    """Track Leadership Stipend eligibility requirements"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Slot requirements
    highest_slot_activated = IntField(default=0)
    min_slot_required = IntField(default=10)  # Minimum slot 10 for eligibility
    slots_10_16_activated = ListField(IntField(), default=[])  # Tracks slots 10-17
    
    # Eligibility status
    is_eligible_for_stipend = BooleanField(default=False)
    eligibility_reasons = ListField(StringField(), default=[])
    
    # Qualification date
    qualified_at = DateTimeField()
    
    # Status
    last_checked = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'leadership_stipend_eligibility',
        'indexes': [
            'user_id',
            'is_eligible_for_stipend',
            'highest_slot_activated'
        ]
    }

class LeadershipStipendPayment(Document):
    """Track Leadership Stipend payments"""
    user_id = ObjectIdField(required=True)
    leadership_stipend_id = ObjectIdField(required=True)
    
    # Payment details
    slot_number = IntField(required=True)  # 10-17
    tier_name = StringField(required=True)
    daily_return_amount = FloatField(required=True)
    currency = StringField(choices=['BNB'], default='BNB')
    
    # Payment period
    payment_date = DateTimeField(required=True)
    payment_period_start = DateTimeField(required=True)
    payment_period_end = DateTimeField(required=True)
    
    # Payment processing
    payment_status = StringField(choices=['pending', 'processing', 'paid', 'failed'], default='pending')
    payment_method = StringField(choices=['wallet', 'blockchain', 'bonus_pool'], default='bonus_pool')
    payment_reference = StringField()  # Transaction hash or reference
    
    # Payment details
    processed_at = DateTimeField()
    paid_at = DateTimeField()
    failed_reason = StringField()
    
    # Status
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'leadership_stipend_payment',
        'indexes': [
            'user_id',
            'leadership_stipend_id',
            'slot_number',
            'payment_date',
            'payment_status',
            'created_at'
        ]
    }

class LeadershipStipendFund(Document):
    """Leadership Stipend Fund management"""
    fund_name = StringField(default='Leadership Stipend Fund', unique=True)
    
    # Fund details
    total_fund_amount = FloatField(default=0.0)
    available_amount = FloatField(default=0.0)
    distributed_amount = FloatField(default=0.0)
    currency = StringField(choices=['BNB'], default='BNB')
    
    # Fund sources
    fund_sources = DictField(default={
        'binary_contributions': 0.0,
        'matrix_contributions': 0.0,
        'global_contributions': 0.0,
        'other_contributions': 0.0
    })
    
    # Fund management
    auto_replenish = BooleanField(default=True)
    replenish_threshold = FloatField(default=100.0)  # Replenish when below 100 BNB
    max_distribution_per_day = FloatField(default=1000.0)  # Max 1000 BNB per day
    
    # Statistics
    total_participants = IntField(default=0)
    total_payments_made = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'leadership_stipend_fund',
        'indexes': ['fund_name', 'is_active']
    }

class LeadershipStipendSettings(Document):
    """Leadership Stipend system settings"""
    setting_name = StringField(default='Leadership Stipend Settings', unique=True)
    
    # General settings
    leadership_stipend_enabled = BooleanField(default=True)
    auto_eligibility_check = BooleanField(default=True)
    auto_daily_calculation = BooleanField(default=True)
    auto_payment_distribution = BooleanField(default=True)
    
    # Eligibility requirements
    min_slot_for_eligibility = IntField(default=10)
    max_slot_for_eligibility = IntField(default=17)
    
    # Calculation settings
    calculation_frequency = StringField(choices=['daily', 'weekly', 'monthly'], default='daily')
    calculation_time = StringField(default="00:00")  # Time to run daily calculation
    
    # Payment settings
    payment_currency = StringField(choices=['BNB'], default='BNB')
    payment_method = StringField(choices=['bonus_pool'], default='bonus_pool')
    payment_delay_hours = IntField(default=24)  # 24 hours delay
    
    # Tier settings
    tier_multiplier = FloatField(default=2.0)  # Double the slot value
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'leadership_stipend_settings',
        'indexes': ['setting_name', 'is_active']
    }

class LeadershipStipendLog(Document):
    """Leadership Stipend activity log"""
    user_id = ObjectIdField(required=True)
    action_type = StringField(choices=[
        'eligibility_check', 'slot_activated', 'tier_upgrade', 'daily_calculation',
        'payment_processed', 'payment_paid', 'fund_update', 'settings_change'
    ], required=True)
    
    # Action details
    action_description = StringField(required=True)
    action_data = DictField(default={})
    
    # Related entities
    slot_number = IntField()
    tier_name = StringField()
    amount = FloatField()
    
    # Status
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'leadership_stipend_log',
        'indexes': [
            'user_id',
            'action_type',
            'created_at',
            'is_processed'
        ]
    }

class LeadershipStipendStatistics(Document):
    """Leadership Stipend program statistics"""
    period = StringField(choices=['daily', 'weekly', 'monthly', 'all_time'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField()
    
    # Statistics
    total_eligible_users = IntField(default=0)
    total_active_users = IntField(default=0)
    total_payments_made = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Tier statistics
    tier_10_users = IntField(default=0)  # LEADER
    tier_11_users = IntField(default=0)  # VANGURD
    tier_12_users = IntField(default=0)  # CENTER
    tier_13_users = IntField(default=0)  # CLIMAX
    tier_14_users = IntField(default=0)  # ENTERNITY
    tier_15_users = IntField(default=0)  # KING
    tier_16_users = IntField(default=0)  # COMMENDER
    tier_17_users = IntField(default=0)  # CEO
    
    # Growth statistics
    new_eligible_users = IntField(default=0)
    new_payment_recipients = IntField(default=0)
    total_slots_activated = IntField(default=0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'leadership_stipend_statistics',
        'indexes': [
            'period',
            'period_start',
            'is_active'
        ]
    }

class LeadershipStipendCalculation(Document):
    """Track daily stipend calculations"""
    calculation_date = DateTimeField(required=True)
    calculation_type = StringField(choices=['daily', 'weekly', 'monthly'], default='daily')
    
    # Calculation results
    total_users_processed = IntField(default=0)
    total_amount_calculated = FloatField(default=0.0)
    total_payments_created = IntField(default=0)
    
    # Processing status
    processing_status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    started_at = DateTimeField()
    completed_at = DateTimeField()
    failed_reason = StringField()
    
    # Calculation details
    calculation_details = DictField(default={})
    
    # Status
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'leadership_stipend_calculation',
        'indexes': [
            'calculation_date',
            'calculation_type',
            'processing_status',
            'created_at'
        ]
    }
