from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, FloatField, ListField, EmbeddedDocumentField, EmbeddedDocument, DictField
from datetime import datetime

class NewcomerBonus(EmbeddedDocument):
    """Embedded document for Newcomer bonuses"""
    bonus_type = StringField(choices=['instant', 'monthly', 'upline_rank'], required=True)
    bonus_name = StringField(required=True)
    bonus_amount = FloatField(required=True)
    bonus_percentage = FloatField(default=0.0)
    currency = StringField(choices=['USDT'], default='USDT')
    is_claimed = BooleanField(default=False)
    claimed_at = DateTimeField()
    is_active = BooleanField(default=True)
    activated_at = DateTimeField()

class NewcomerSupport(Document):
    """Newcomer Growth Support Program - Main document"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Program status
    is_eligible = BooleanField(default=False)
    is_active = BooleanField(default=False)
    joined_at = DateTimeField()
    qualified_at = DateTimeField()
    
    # Matrix program status
    has_matrix_program = BooleanField(default=False)
    matrix_join_date = DateTimeField()
    matrix_slots_activated = IntField(default=0)
    
    # Newcomer bonuses
    bonuses = ListField(EmbeddedDocumentField(NewcomerBonus), default=[])
    
    # Instant bonus
    instant_bonus_eligible = BooleanField(default=False)
    instant_bonus_amount = FloatField(default=0.0)
    instant_bonus_claimed = BooleanField(default=False)
    instant_bonus_claimed_at = DateTimeField()
    
    # Monthly opportunities
    monthly_opportunities_eligible = BooleanField(default=False)
    monthly_opportunities_count = IntField(default=0)
    last_monthly_opportunity = DateTimeField()
    next_monthly_opportunity = DateTimeField()
    
    # Upline rank bonus
    upline_rank_bonus_eligible = BooleanField(default=False)
    upline_user_id = ObjectIdField()
    upline_rank = StringField()
    user_rank = StringField()
    upline_rank_bonus_percentage = FloatField(default=10.0)
    upline_rank_bonus_amount = FloatField(default=0.0)
    upline_rank_bonus_claimed = BooleanField(default=False)
    upline_rank_bonus_claimed_at = DateTimeField()
    
    # Earning tracking
    total_bonuses_earned = FloatField(default=0.0)
    total_bonuses_claimed = FloatField(default=0.0)
    pending_bonuses = FloatField(default=0.0)
    
    # Status
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'newcomer_support',
        'indexes': [
            'user_id',
            'is_eligible',
            'is_active',
            'has_matrix_program',
            'instant_bonus_eligible',
            'monthly_opportunities_eligible',
            'upline_rank_bonus_eligible'
        ]
    }

class NewcomerSupportEligibility(Document):
    """Track Newcomer Support eligibility requirements"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Matrix program requirements
    has_matrix_program = BooleanField(default=False)
    matrix_join_date = DateTimeField()
    matrix_slots_activated = IntField(default=0)
    
    # Newcomer status
    is_newcomer = BooleanField(default=True)
    newcomer_period_days = IntField(default=30)  # 30 days newcomer period
    newcomer_end_date = DateTimeField()
    
    # Eligibility status
    is_eligible_for_instant_bonus = BooleanField(default=False)
    is_eligible_for_monthly_opportunities = BooleanField(default=False)
    is_eligible_for_upline_rank_bonus = BooleanField(default=False)
    
    # Eligibility reasons
    eligibility_reasons = ListField(StringField(), default=[])
    
    # Qualification date
    qualified_at = DateTimeField()
    
    # Status
    last_checked = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'newcomer_support_eligibility',
        'indexes': [
            'user_id',
            'is_newcomer',
            'is_eligible_for_instant_bonus',
            'is_eligible_for_monthly_opportunities',
            'is_eligible_for_upline_rank_bonus'
        ]
    }

class NewcomerSupportBonus(Document):
    """Track Newcomer Support bonus payments"""
    user_id = ObjectIdField(required=True)  # Newcomer
    newcomer_support_id = ObjectIdField(required=True)
    
    # Bonus details
    bonus_type = StringField(choices=['instant', 'monthly', 'upline_rank'], required=True)
    bonus_name = StringField(required=True)
    bonus_amount = FloatField(required=True)
    bonus_percentage = FloatField(default=0.0)
    currency = StringField(choices=['USDT'], default='USDT')
    
    # Source details
    source_type = StringField(choices=['matrix_join', 'monthly_activity', 'upline_rank_match'], required=True)
    source_description = StringField(required=True)
    
    # Upline details (for upline rank bonus)
    upline_user_id = ObjectIdField()
    upline_rank = StringField()
    user_rank = StringField()
    
    # Payment details
    payment_status = StringField(choices=['pending', 'processing', 'paid', 'failed'], default='pending')
    payment_method = StringField(choices=['wallet', 'blockchain', 'bonus_pool'], default='bonus_pool')
    payment_reference = StringField()  # Transaction hash or reference
    
    # Payment processing
    processed_at = DateTimeField()
    paid_at = DateTimeField()
    failed_reason = StringField()
    
    # Status
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'newcomer_support_bonus',
        'indexes': [
            'user_id',
            'newcomer_support_id',
            'bonus_type',
            'payment_status',
            'created_at'
        ]
    }

class NewcomerSupportFund(Document):
    """Newcomer Support Fund management"""
    fund_name = StringField(default='Newcomer Support Fund', unique=True)
    
    # Fund details
    total_fund_amount = FloatField(default=0.0)
    available_amount = FloatField(default=0.0)
    distributed_amount = FloatField(default=0.0)
    currency = StringField(choices=['USDT'], default='USDT')
    
    # Fund sources
    fund_sources = DictField(default={
        'matrix_contributions': 0.0,
        'instant_bonus_pool': 0.0,
        'monthly_opportunities_pool': 0.0,
        'upline_rank_bonus_pool': 0.0,
        'other_contributions': 0.0
    })
    
    # Fund management
    auto_replenish = BooleanField(default=True)
    replenish_threshold = FloatField(default=5000.0)  # Replenish when below $5000
    max_distribution_per_day = FloatField(default=25000.0)  # Max $25k per day
    
    # Statistics
    total_participants = IntField(default=0)
    total_bonuses_paid = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'newcomer_support_fund',
        'indexes': ['fund_name', 'is_active']
    }

class NewcomerSupportSettings(Document):
    """Newcomer Support system settings"""
    setting_name = StringField(default='Newcomer Support Settings', unique=True)
    
    # General settings
    newcomer_support_enabled = BooleanField(default=True)
    auto_eligibility_check = BooleanField(default=True)
    auto_bonus_distribution = BooleanField(default=True)
    
    # Eligibility requirements
    require_matrix_program = BooleanField(default=True)
    newcomer_period_days = IntField(default=30)
    
    # Bonus settings
    instant_bonus_amount = FloatField(default=50.0)  # $50 instant bonus
    monthly_opportunities_count = IntField(default=3)  # 3 monthly opportunities
    upline_rank_bonus_percentage = FloatField(default=10.0)  # 10% bonus
    
    # Payment settings
    payment_currency = StringField(choices=['USDT'], default='USDT')
    payment_method = StringField(choices=['bonus_pool'], default='bonus_pool')
    payment_delay_hours = IntField(default=24)  # 24 hours delay
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'newcomer_support_settings',
        'indexes': ['setting_name', 'is_active']
    }

class NewcomerSupportLog(Document):
    """Newcomer Support activity log"""
    user_id = ObjectIdField(required=True)
    action_type = StringField(choices=[
        'eligibility_check', 'instant_bonus_earned', 'instant_bonus_claimed',
        'monthly_opportunity_gained', 'upline_rank_bonus_earned', 'upline_rank_bonus_claimed',
        'matrix_joined', 'slot_upgraded'
    ], required=True)
    
    # Action details
    action_description = StringField(required=True)
    action_data = DictField(default={})
    
    # Related entities
    related_user_id = ObjectIdField()  # For upline references
    related_bonus_id = ObjectIdField()  # For bonus payments
    bonus_amount = FloatField()
    bonus_type = StringField()
    
    # Status
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'newcomer_support_log',
        'indexes': [
            'user_id',
            'action_type',
            'created_at',
            'is_processed'
        ]
    }

class NewcomerSupportStatistics(Document):
    """Newcomer Support program statistics"""
    period = StringField(choices=['daily', 'weekly', 'monthly', 'all_time'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField()
    
    # Statistics
    total_eligible_users = IntField(default=0)
    total_active_users = IntField(default=0)
    total_bonuses_paid = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Bonus breakdown
    instant_bonuses_paid = IntField(default=0)
    instant_bonuses_amount = FloatField(default=0.0)
    monthly_opportunities_given = IntField(default=0)
    monthly_opportunities_amount = FloatField(default=0.0)
    upline_rank_bonuses_paid = IntField(default=0)
    upline_rank_bonuses_amount = FloatField(default=0.0)
    
    # Growth statistics
    new_eligible_users = IntField(default=0)
    new_bonus_earners = IntField(default=0)
    total_newcomers = IntField(default=0)
    total_matrix_joins = IntField(default=0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'newcomer_support_statistics',
        'indexes': [
            'period',
            'period_start',
            'is_active'
        ]
    }

class NewcomerSupportMonthlyOpportunity(Document):
    """Track monthly earning opportunities"""
    user_id = ObjectIdField(required=True)
    newcomer_support_id = ObjectIdField(required=True)
    
    # Opportunity details
    opportunity_month = StringField(required=True)  # YYYY-MM format
    opportunity_type = StringField(choices=['upline_activity', 'team_growth', 'personal_achievement'], required=True)
    opportunity_description = StringField(required=True)
    opportunity_value = FloatField(required=True)
    currency = StringField(choices=['USDT'], default='USDT')
    
    # Upline activity details
    upline_user_id = ObjectIdField()
    upline_activity_score = FloatField(default=0.0)
    upline_rank = StringField()
    
    # Status
    is_available = BooleanField(default=True)
    is_claimed = BooleanField(default=False)
    claimed_at = DateTimeField()
    expires_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    last_updated = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'newcomer_support_monthly_opportunity',
        'indexes': [
            'user_id',
            'newcomer_support_id',
            'opportunity_month',
            'is_available',
            'is_claimed'
        ]
    }
