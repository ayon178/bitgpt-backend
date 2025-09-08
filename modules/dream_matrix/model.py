from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, FloatField, ListField, EmbeddedDocumentField, EmbeddedDocument, DictField
from datetime import datetime

class DreamMatrixLevel(EmbeddedDocument):
    """Embedded document for Dream Matrix levels"""
    level_number = IntField(required=True)  # 1-5
    level_name = StringField(required=True)  # Level 1, Level 2, etc.
    member_count = IntField(required=True)  # 3, 9, 27, 81, 243
    commission_percentage = FloatField(required=True)  # 10%, 10%, 15%, 25%, 40%
    commission_amount = FloatField(required=True)  # $80, $80, $120, $200, $320
    total_profit = FloatField(required=True)  # $240, $720, $3240, $16200, $77760
    is_active = BooleanField(default=False)
    activated_at = DateTimeField()
    total_earned = FloatField(default=0.0)
    total_paid = FloatField(default=0.0)
    pending_amount = FloatField(default=0.0)

class DreamMatrix(Document):
    """Dream Matrix Program - Main document"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Program status
    is_eligible = BooleanField(default=False)
    is_active = BooleanField(default=False)
    joined_at = DateTimeField()
    qualified_at = DateTimeField()
    
    # Mandatory requirements
    has_matrix_first_slot = BooleanField(default=False)
    has_three_direct_partners = BooleanField(default=False)
    direct_partners_count = IntField(default=0)
    direct_partners = ListField(ObjectIdField(), default=[])
    
    # Dream Matrix levels
    levels = ListField(EmbeddedDocumentField(DreamMatrixLevel), default=[])
    current_level = IntField(default=0)
    max_level_reached = IntField(default=0)
    
    # Profit tracking
    total_profit_earned = FloatField(default=0.0)
    total_profit_paid = FloatField(default=0.0)
    pending_profit = FloatField(default=0.0)
    
    # Slot value (based on 5th slot = $800)
    slot_value = FloatField(default=800.0)
    currency = StringField(choices=['USDT'], default='USDT')
    
    # Commission tracking
    total_commissions_earned = FloatField(default=0.0)
    total_commissions_paid = FloatField(default=0.0)
    pending_commissions = FloatField(default=0.0)
    
    # Status
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'dream_matrix',
        'indexes': [
            'user_id',
            'is_eligible',
            'is_active',
            'has_matrix_first_slot',
            'has_three_direct_partners'
        ]
    }

class DreamMatrixEligibility(Document):
    """Track Dream Matrix eligibility requirements"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Matrix program requirements
    has_matrix_first_slot = BooleanField(default=False)
    matrix_slot_value = FloatField(default=0.0)
    matrix_currency = StringField(choices=['USDT'], default='USDT')
    
    # Direct partners requirements
    direct_partners_count = IntField(default=0)
    min_direct_partners_required = IntField(default=3)
    direct_partners = ListField(ObjectIdField(), default=[])
    
    # Eligibility status
    is_eligible_for_dream_matrix = BooleanField(default=False)
    eligibility_reasons = ListField(StringField(), default=[])
    
    # Qualification date
    qualified_at = DateTimeField()
    
    # Status
    last_checked = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'dream_matrix_eligibility',
        'indexes': [
            'user_id',
            'is_eligible_for_dream_matrix',
            'has_matrix_first_slot',
            'has_three_direct_partners'
        ]
    }

class DreamMatrixCommission(Document):
    """Track Dream Matrix commission payments"""
    user_id = ObjectIdField(required=True)  # Dream Matrix participant
    dream_matrix_id = ObjectIdField(required=True)
    
    # Commission details
    level_number = IntField(required=True)  # 1-5
    level_name = StringField(required=True)
    commission_percentage = FloatField(required=True)
    commission_amount = FloatField(required=True)
    
    # Source details
    source_user_id = ObjectIdField(required=True)  # User who generated the commission
    source_level = IntField(required=True)  # Level where commission was generated
    source_amount = FloatField(required=True)  # Original amount that generated commission
    
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
        'collection': 'dream_matrix_commission',
        'indexes': [
            'user_id',
            'dream_matrix_id',
            'level_number',
            'payment_status',
            'created_at'
        ]
    }

class DreamMatrixFund(Document):
    """Dream Matrix Fund management"""
    fund_name = StringField(default='Dream Matrix Fund', unique=True)
    
    # Fund details
    total_fund_amount = FloatField(default=0.0)
    available_amount = FloatField(default=0.0)
    distributed_amount = FloatField(default=0.0)
    currency = StringField(choices=['USDT'], default='USDT')
    
    # Fund sources
    fund_sources = DictField(default={
        'matrix_contributions': 0.0,
        'slot_purchases': 0.0,
        'level_commissions': 0.0,
        'other_contributions': 0.0
    })
    
    # Fund management
    auto_replenish = BooleanField(default=True)
    replenish_threshold = FloatField(default=1000.0)  # Replenish when below $1000
    max_distribution_per_day = FloatField(default=50000.0)  # Max $50k per day
    
    # Statistics
    total_participants = IntField(default=0)
    total_commissions_paid = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'dream_matrix_fund',
        'indexes': ['fund_name', 'is_active']
    }

class DreamMatrixSettings(Document):
    """Dream Matrix system settings"""
    setting_name = StringField(default='Dream Matrix Settings', unique=True)
    
    # General settings
    dream_matrix_enabled = BooleanField(default=True)
    auto_eligibility_check = BooleanField(default=True)
    auto_commission_distribution = BooleanField(default=True)
    
    # Eligibility requirements
    require_matrix_first_slot = BooleanField(default=True)
    min_direct_partners_required = IntField(default=3)
    
    # Commission settings
    level_commissions = DictField(default={
        'level_1': {'percentage': 10.0, 'amount': 80.0, 'members': 3},
        'level_2': {'percentage': 10.0, 'amount': 80.0, 'members': 9},
        'level_3': {'percentage': 15.0, 'amount': 120.0, 'members': 27},
        'level_4': {'percentage': 25.0, 'amount': 200.0, 'members': 81},
        'level_5': {'percentage': 40.0, 'amount': 320.0, 'members': 243}
    })
    
    # Payment settings
    payment_currency = StringField(choices=['USDT'], default='USDT')
    payment_method = StringField(choices=['bonus_pool'], default='bonus_pool')
    payment_delay_hours = IntField(default=24)  # 24 hours delay
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'dream_matrix_settings',
        'indexes': ['setting_name', 'is_active']
    }

class DreamMatrixLog(Document):
    """Dream Matrix activity log"""
    user_id = ObjectIdField(required=True)
    action_type = StringField(choices=[
        'eligibility_check', 'direct_partner_added', 'level_activated',
        'commission_earned', 'commission_paid', 'matrix_slot_purchased'
    ], required=True)
    
    # Action details
    action_description = StringField(required=True)
    action_data = DictField(default={})
    
    # Related entities
    related_user_id = ObjectIdField()  # For partner additions
    related_commission_id = ObjectIdField()  # For commission payments
    commission_amount = FloatField()
    level_number = IntField()
    
    # Status
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'dream_matrix_log',
        'indexes': [
            'user_id',
            'action_type',
            'created_at',
            'is_processed'
        ]
    }

class DreamMatrixStatistics(Document):
    """Dream Matrix program statistics"""
    period = StringField(choices=['daily', 'weekly', 'monthly', 'all_time'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField()
    
    # Statistics
    total_eligible_users = IntField(default=0)
    total_active_users = IntField(default=0)
    total_commissions_paid = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Commission breakdown by level
    level_1_commissions_paid = IntField(default=0)
    level_1_commissions_amount = FloatField(default=0.0)
    level_2_commissions_paid = IntField(default=0)
    level_2_commissions_amount = FloatField(default=0.0)
    level_3_commissions_paid = IntField(default=0)
    level_3_commissions_amount = FloatField(default=0.0)
    level_4_commissions_paid = IntField(default=0)
    level_4_commissions_amount = FloatField(default=0.0)
    level_5_commissions_paid = IntField(default=0)
    level_5_commissions_amount = FloatField(default=0.0)
    
    # Growth statistics
    new_eligible_users = IntField(default=0)
    new_commission_earners = IntField(default=0)
    total_direct_partners = IntField(default=0)
    total_level_activations = IntField(default=0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'dream_matrix_statistics',
        'indexes': [
            'period',
            'period_start',
            'is_active'
        ]
    }

class DreamMatrixLevelProgress(Document):
    """Track Dream Matrix level progress"""
    user_id = ObjectIdField(required=True)
    dream_matrix_id = ObjectIdField(required=True)
    
    # Level details
    level_number = IntField(required=True)  # 1-5
    level_name = StringField(required=True)
    member_count = IntField(required=True)
    commission_percentage = FloatField(required=True)
    commission_amount = FloatField(required=True)
    total_profit = FloatField(required=True)
    
    # Progress tracking
    members_required = IntField(required=True)
    members_achieved = IntField(default=0)
    progress_percentage = FloatField(default=0.0)
    
    # Commission tracking
    commissions_earned = FloatField(default=0.0)
    commissions_paid = FloatField(default=0.0)
    pending_commissions = FloatField(default=0.0)
    
    # Status
    is_active = BooleanField(default=True)
    is_completed = BooleanField(default=False)
    completed_at = DateTimeField()
    activated_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    last_updated = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'dream_matrix_level_progress',
        'indexes': [
            'user_id',
            'dream_matrix_id',
            'level_number',
            'is_active',
            'is_completed'
        ]
    }
