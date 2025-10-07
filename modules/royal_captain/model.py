from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, FloatField, ListField, EmbeddedDocumentField, EmbeddedDocument, DictField
from datetime import datetime

class RoyalCaptainRequirement(EmbeddedDocument):
    """Embedded document for Royal Captain requirements"""
    requirement_type = StringField(choices=[
        'both_packages', 'direct_partners', 'global_team', 'maintenance'
    ], required=True)
    requirement_value = IntField(required=True)
    requirement_description = StringField(required=True)
    is_met = BooleanField(default=False)

class RoyalCaptainBonus(EmbeddedDocument):
    """Embedded document for Royal Captain bonus details - 60% USDT + 40% BNB"""
    bonus_tier = IntField(required=True)  # 1, 2, 3, 4, 5, 6
    direct_partners_required = IntField(required=True)
    global_team_required = IntField(required=True)
    bonus_amount_usd = FloatField(required=True)  # Total USD value
    bonus_amount_usdt = FloatField(required=True)  # 60% in USDT
    bonus_amount_bnb = FloatField(required=True)  # 40% in BNB
    bonus_description = StringField(required=True)
    is_achieved = BooleanField(default=False)
    achieved_at = DateTimeField()

class RoyalCaptain(Document):
    """Royal Captain Bonus Program - Main document"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Program status
    is_eligible = BooleanField(default=False)
    is_active = BooleanField(default=False)
    joined_at = DateTimeField()
    
    # Requirements tracking
    requirements = ListField(EmbeddedDocumentField(RoyalCaptainRequirement), default=[])
    
    # Bonus tracking
    bonuses = ListField(EmbeddedDocumentField(RoyalCaptainBonus), default=[])
    
    # Current status
    current_tier = IntField(default=0)  # 0 = not eligible, 1-5 = bonus tiers
    total_direct_partners = IntField(default=0)
    total_global_team = IntField(default=0)
    total_bonus_earned = FloatField(default=0.0)
    
    # Qualification tracking
    matrix_package_active = BooleanField(default=False)
    global_package_active = BooleanField(default=False)
    both_packages_active = BooleanField(default=False)
    
    # Direct partners tracking
    direct_partners_with_both_packages = IntField(default=0)
    direct_partners_list = ListField(ObjectIdField(), default=[])
    
    # Global team tracking
    global_team_members = IntField(default=0)
    global_team_list = ListField(ObjectIdField(), default=[])
    
    # Bonus history
    bonus_history = ListField(DictField(), default=[])
    
    # Status
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'royal_captain',
        'indexes': [
            'user_id',
            'is_eligible',
            'is_active',
            'current_tier',
            'both_packages_active'
        ]
    }

class RoyalCaptainEligibility(Document):
    """Track Royal Captain eligibility requirements"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Package requirements
    has_matrix_package = BooleanField(default=False)
    has_global_package = BooleanField(default=False)
    has_both_packages = BooleanField(default=False)
    
    # Direct partners requirements
    direct_partners_count = IntField(default=0)
    direct_partners_with_both_packages = IntField(default=0)
    min_direct_partners_required = IntField(default=5)
    
    # Global team requirements
    global_team_count = IntField(default=0)
    min_global_team_required = IntField(default=0)
    
    # Eligibility status
    is_eligible_for_royal_captain = BooleanField(default=False)
    eligibility_reasons = ListField(StringField(), default=[])
    
    # Qualification date
    qualified_at = DateTimeField()
    
    # Status
    last_checked = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'royal_captain_eligibility',
        'indexes': [
            'user_id',
            'is_eligible_for_royal_captain',
            'has_both_packages'
        ]
    }

class RoyalCaptainBonusPayment(Document):
    """Track Royal Captain bonus payments - 60% USDT + 40% BNB"""
    user_id = ObjectIdField(required=True)
    royal_captain_id = ObjectIdField(required=True)
    
    # Bonus details
    bonus_tier = IntField(required=True)  # 1-6
    bonus_amount = FloatField(required=True)  # Total USD value
    bonus_amount_usdt = FloatField(default=0.0)  # 60%
    bonus_amount_bnb = FloatField(default=0.0)  # 40%
    currency = StringField(choices=['USDT', 'BNB', 'BOTH'], default='BOTH')
    
    # Requirements met
    direct_partners_at_payment = IntField(required=True)
    global_team_at_payment = IntField(required=True)
    
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
        'collection': 'royal_captain_bonus_payment',
        'indexes': [
            'user_id',
            'royal_captain_id',
            'bonus_tier',
            'payment_status',
            'created_at'
        ]
    }

class RoyalCaptainFund(Document):
    """Royal Captain Fund management"""
    fund_name = StringField(default='Royal Captain Fund', unique=True)
    
    # Fund details
    total_fund_amount = FloatField(default=0.0)
    available_amount = FloatField(default=0.0)
    distributed_amount = FloatField(default=0.0)
    currency = StringField(choices=['USD', 'USDT'], default='USDT')
    
    # Fund sources
    fund_sources = DictField(default={
        'matrix_contributions': 0.0,
        'global_contributions': 0.0,
        'other_contributions': 0.0
    })
    
    # Fund management
    auto_replenish = BooleanField(default=True)
    replenish_threshold = FloatField(default=1000.0)  # Replenish when below $1000
    max_distribution_per_day = FloatField(default=10000.0)  # Max $10k per day
    
    # Statistics
    total_participants = IntField(default=0)
    total_bonuses_paid = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'royal_captain_fund',
        'indexes': ['fund_name', 'is_active']
    }

class RoyalCaptainSettings(Document):
    """Royal Captain system settings"""
    setting_name = StringField(default='Royal Captain Settings', unique=True)
    
    # General settings
    royal_captain_enabled = BooleanField(default=True)
    auto_eligibility_check = BooleanField(default=True)
    auto_bonus_distribution = BooleanField(default=True)
    
    # Requirements
    min_direct_partners_required = IntField(default=5)
    require_both_packages = BooleanField(default=True)
    min_global_team_for_tier_1 = IntField(default=0)
    min_global_team_for_tier_2 = IntField(default=10)
    min_global_team_for_tier_3 = IntField(default=20)
    min_global_team_for_tier_4 = IntField(default=30)
    min_global_team_for_tier_5 = IntField(default=40)
    
    # Bonus amounts
    tier_1_bonus_amount = FloatField(default=200.0)
    tier_2_bonus_amount = FloatField(default=200.0)
    tier_3_bonus_amount = FloatField(default=200.0)
    tier_4_bonus_amount = FloatField(default=250.0)
    tier_5_bonus_amount = FloatField(default=250.0)
    
    # Payment settings
    payment_currency = StringField(choices=['USD'], default='USD')
    payment_method = StringField(choices=['bonus_pool'], default='bonus_pool')
    payment_delay_hours = IntField(default=24)  # 24 hours delay
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'royal_captain_settings',
        'indexes': ['setting_name', 'is_active']
    }

class RoyalCaptainLog(Document):
    """Royal Captain activity log"""
    user_id = ObjectIdField(required=True)
    action_type = StringField(choices=[
        'eligibility_check', 'requirement_met', 'bonus_earned', 'bonus_paid',
        'tier_upgrade', 'partner_added', 'team_growth', 'package_activation'
    ], required=True)
    
    # Action details
    action_description = StringField(required=True)
    action_data = DictField(default={})
    
    # Related entities
    related_user_id = ObjectIdField()  # For partner additions
    related_bonus_id = ObjectIdField()  # For bonus payments
    
    # Status
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'royal_captain_log',
        'indexes': [
            'user_id',
            'action_type',
            'created_at',
            'is_processed'
        ]
    }

class RoyalCaptainStatistics(Document):
    """Royal Captain program statistics"""
    period = StringField(choices=['daily', 'weekly', 'monthly', 'all_time'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField()
    
    # Statistics
    total_eligible_users = IntField(default=0)
    total_active_users = IntField(default=0)
    total_bonuses_paid = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Tier statistics
    tier_1_achievements = IntField(default=0)
    tier_2_achievements = IntField(default=0)
    tier_3_achievements = IntField(default=0)
    tier_4_achievements = IntField(default=0)
    tier_5_achievements = IntField(default=0)
    
    # Growth statistics
    new_eligible_users = IntField(default=0)
    new_bonus_earners = IntField(default=0)
    total_direct_partners = IntField(default=0)
    total_global_team = IntField(default=0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'royal_captain_statistics',
        'indexes': [
            'period',
            'period_start',
            'is_active'
        ]
    }
