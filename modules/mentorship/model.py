from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, FloatField, ListField, EmbeddedDocumentField, EmbeddedDocument, DictField
from datetime import datetime

class MentorshipLevel(EmbeddedDocument):
    """Embedded document for Mentorship levels"""
    level_number = IntField(required=True)  # 1 = Direct, 2 = Direct-of-Direct
    level_name = StringField(required=True)  # "Direct", "Direct-of-Direct"
    commission_percentage = FloatField(required=True)  # 10% for both levels
    is_active = BooleanField(default=False)
    activated_at = DateTimeField()
    total_earned = FloatField(default=0.0)
    total_paid = FloatField(default=0.0)
    pending_amount = FloatField(default=0.0)

class Mentorship(Document):
    """Mentorship Bonus Program - Main document"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Program status
    is_eligible = BooleanField(default=False)
    is_active = BooleanField(default=False)
    joined_at = DateTimeField()
    qualified_at = DateTimeField()
    
    # Mentorship levels
    levels = ListField(EmbeddedDocumentField(MentorshipLevel), default=[])
    
    # Direct referrals tracking
    direct_referrals = ListField(ObjectIdField(), default=[])
    direct_referrals_count = IntField(default=0)
    
    # Direct-of-Direct referrals tracking
    direct_of_direct_referrals = ListField(ObjectIdField(), default=[])
    direct_of_direct_referrals_count = IntField(default=0)
    
    # Commission tracking
    total_commissions_earned = FloatField(default=0.0)
    total_commissions_paid = FloatField(default=0.0)
    pending_commissions = FloatField(default=0.0)
    
    # Matrix program status
    matrix_program_active = BooleanField(default=False)
    matrix_slots_activated = IntField(default=0)
    
    # Earnings breakdown
    direct_commissions = FloatField(default=0.0)
    direct_of_direct_commissions = FloatField(default=0.0)
    
    # Status
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'mentorship',
        'indexes': [
            'user_id',
            'is_eligible',
            'is_active',
            'matrix_program_active'
        ]
    }

class MentorshipEligibility(Document):
    """Track Mentorship eligibility requirements"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Matrix program requirements
    has_matrix_program = BooleanField(default=False)
    matrix_slots_activated = IntField(default=0)
    min_matrix_slots_required = IntField(default=1)
    
    # Direct referrals requirements
    direct_referrals_count = IntField(default=0)
    min_direct_referrals_required = IntField(default=1)
    
    # Eligibility status
    is_eligible_for_mentorship = BooleanField(default=False)
    eligibility_reasons = ListField(StringField(), default=[])
    
    # Qualification date
    qualified_at = DateTimeField()
    
    # Status
    last_checked = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'mentorship_eligibility',
        'indexes': [
            'user_id',
            'is_eligible_for_mentorship',
            'has_matrix_program'
        ]
    }

class MentorshipCommission(Document):
    """Track Mentorship commission payments"""
    user_id = ObjectIdField(required=True)  # Mentor (Super Upline)
    mentorship_id = ObjectIdField(required=True)
    
    # Commission details
    commission_type = StringField(choices=['joining', 'slot_upgrade'], required=True)
    commission_level = StringField(choices=['direct', 'direct_of_direct'], required=True)
    commission_percentage = FloatField(required=True)  # 10%
    
    # Source details
    source_user_id = ObjectIdField(required=True)  # User who generated the commission
    source_user_level = IntField(required=True)  # 1 = Direct, 2 = Direct-of-Direct
    source_amount = FloatField(required=True)  # Original amount that generated commission
    commission_amount = FloatField(required=True)  # 10% of source amount
    
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
        'collection': 'mentorship_commission',
        'indexes': [
            'user_id',
            'mentorship_id',
            'commission_type',
            'commission_level',
            'payment_status',
            'created_at'
        ]
    }

class MentorshipFund(Document):
    """Mentorship Fund management"""
    fund_name = StringField(default='Mentorship Fund', unique=True)
    
    # Fund details
    total_fund_amount = FloatField(default=0.0)
    available_amount = FloatField(default=0.0)
    distributed_amount = FloatField(default=0.0)
    currency = StringField(choices=['USDT'], default='USDT')
    
    # Fund sources
    fund_sources = DictField(default={
        'matrix_contributions': 0.0,
        'joining_fees': 0.0,
        'slot_upgrades': 0.0,
        'other_contributions': 0.0
    })
    
    # Fund management
    auto_replenish = BooleanField(default=True)
    replenish_threshold = FloatField(default=1000.0)  # Replenish when below $1000
    max_distribution_per_day = FloatField(default=10000.0)  # Max $10k per day
    
    # Statistics
    total_participants = IntField(default=0)
    total_commissions_paid = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'mentorship_fund',
        'indexes': ['fund_name', 'is_active']
    }

class MentorshipSettings(Document):
    """Mentorship system settings"""
    setting_name = StringField(default='Mentorship Settings', unique=True)
    
    # General settings
    mentorship_enabled = BooleanField(default=True)
    auto_eligibility_check = BooleanField(default=True)
    auto_commission_distribution = BooleanField(default=True)
    
    # Eligibility requirements
    require_matrix_program = BooleanField(default=True)
    min_matrix_slots_required = IntField(default=1)
    min_direct_referrals_required = IntField(default=1)
    
    # Commission settings
    direct_commission_percentage = FloatField(default=10.0)  # 10%
    direct_of_direct_commission_percentage = FloatField(default=10.0)  # 10%
    
    # Payment settings
    payment_currency = StringField(choices=['USDT'], default='USDT')
    payment_method = StringField(choices=['bonus_pool'], default='bonus_pool')
    payment_delay_hours = IntField(default=24)  # 24 hours delay
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'mentorship_settings',
        'indexes': ['setting_name', 'is_active']
    }

class MentorshipLog(Document):
    """Mentorship activity log"""
    user_id = ObjectIdField(required=True)
    action_type = StringField(choices=[
        'eligibility_check', 'direct_referral_added', 'direct_of_direct_referral_added',
        'commission_earned', 'commission_paid', 'matrix_slot_activated'
    ], required=True)
    
    # Action details
    action_description = StringField(required=True)
    action_data = DictField(default={})
    
    # Related entities
    related_user_id = ObjectIdField()  # For referral additions
    related_commission_id = ObjectIdField()  # For commission payments
    commission_amount = FloatField()
    
    # Status
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'mentorship_log',
        'indexes': [
            'user_id',
            'action_type',
            'created_at',
            'is_processed'
        ]
    }

class MentorshipStatistics(Document):
    """Mentorship program statistics"""
    period = StringField(choices=['daily', 'weekly', 'monthly', 'all_time'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField()
    
    # Statistics
    total_eligible_users = IntField(default=0)
    total_active_users = IntField(default=0)
    total_commissions_paid = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Commission breakdown
    direct_commissions_paid = IntField(default=0)
    direct_commissions_amount = FloatField(default=0.0)
    direct_of_direct_commissions_paid = IntField(default=0)
    direct_of_direct_commissions_amount = FloatField(default=0.0)
    
    # Growth statistics
    new_eligible_users = IntField(default=0)
    new_commission_earners = IntField(default=0)
    total_direct_referrals = IntField(default=0)
    total_direct_of_direct_referrals = IntField(default=0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'mentorship_statistics',
        'indexes': [
            'period',
            'period_start',
            'is_active'
        ]
    }

class MentorshipReferral(Document):
    """Track Mentorship referral relationships"""
    mentor_id = ObjectIdField(required=True)  # Super Upline (A)
    upline_id = ObjectIdField(required=True)  # Direct referral (B)
    referral_id = ObjectIdField(required=True)  # Direct-of-Direct referral (C, D, E)
    
    # Relationship details
    relationship_level = IntField(required=True)  # 1 = Direct, 2 = Direct-of-Direct
    relationship_type = StringField(choices=['direct', 'direct_of_direct'], required=True)
    
    # Commission tracking
    total_commissions_generated = FloatField(default=0.0)
    total_commissions_paid = FloatField(default=0.0)
    
    # Status
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'mentorship_referral',
        'indexes': [
            'mentor_id',
            'upline_id',
            'referral_id',
            'relationship_level',
            'is_active'
        ]
    }
