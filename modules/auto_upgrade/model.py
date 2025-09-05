from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, DecimalField, ListField, DictField, FloatField, EmbeddedDocumentField, EmbeddedDocument
from datetime import datetime
from decimal import Decimal

class AutoUpgradeTrigger(EmbeddedDocument):
    """Auto upgrade trigger conditions"""
    trigger_type = StringField(choices=[
        'first_two_partners', 'middle_three_members', 'phase_completion',
        'earnings_threshold', 'manual'
    ], required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    
    # Binary triggers
    partners_required = IntField(default=2)  # For binary (first 2 partners)
    partners_available = IntField(default=0)
    
    # Matrix triggers
    middle_three_required = IntField(default=3)  # For matrix (middle 3 members)
    middle_three_available = IntField(default=0)
    
    # Global triggers
    phase_1_members_required = IntField(default=4)  # Phase 1 requirement
    phase_2_members_required = IntField(default=8)  # Phase 2 requirement
    current_phase_members = IntField(default=0)
    
    # Earnings triggers
    earnings_threshold = DecimalField(precision=8, default=0)
    current_earnings = DecimalField(precision=8, default=0)
    
    # Status
    is_triggered = BooleanField(default=False)
    triggered_at = DateTimeField()

class AutoUpgradeQueue(Document):
    """Queue for managing auto upgrades"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    
    # Upgrade details
    current_slot_no = IntField(required=True)
    target_slot_no = IntField(required=True)
    upgrade_cost = DecimalField(required=True, precision=8)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    
    # Trigger information
    trigger = EmbeddedDocumentField(AutoUpgradeTrigger)
    
    # Earnings calculation
    earnings_available = DecimalField(precision=8, default=0)
    earnings_used = DecimalField(precision=8, default=0)
    earnings_source = ListField(ObjectIdField())  # Users who contributed earnings
    
    # Processing
    status = StringField(choices=['pending', 'processing', 'completed', 'failed', 'cancelled'], default='pending')
    priority = IntField(default=1)  # Higher number = higher priority
    
    # Error handling
    error_message = StringField()
    retry_count = IntField(default=0)
    max_retries = IntField(default=3)
    
    # Timestamps
    queued_at = DateTimeField(default=datetime.utcnow)
    processed_at = DateTimeField()
    completed_at = DateTimeField()
    
    meta = {
        'collection': 'auto_upgrade_queue',
        'indexes': [
            'user_id',
            'program',
            'status',
            'priority',
            'queued_at'
        ]
    }

class AutoUpgradeLog(Document):
    """Track completed auto upgrades"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    
    # Upgrade details
    from_slot_no = IntField(required=True)
    to_slot_no = IntField(required=True)
    from_slot_name = StringField(required=True)
    to_slot_name = StringField(required=True)
    
    # Cost and earnings
    upgrade_cost = DecimalField(required=True, precision=8)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    earnings_used = DecimalField(required=True, precision=8)
    profit_gained = DecimalField(precision=8, default=0)
    
    # Trigger information
    trigger_type = StringField(choices=[
        'first_two_partners', 'middle_three_members', 'phase_completion',
        'earnings_threshold', 'manual'
    ], required=True)
    
    # Contributors
    contributors = ListField(ObjectIdField())  # Users who contributed earnings
    contributor_details = ListField(DictField())  # Detailed contribution info
    
    # Transaction details
    tx_hash = StringField()
    blockchain_network = StringField(choices=['BSC', 'ETH', 'TRC20'], default='BSC')
    
    # Status
    status = StringField(choices=['completed', 'failed', 'refunded'], default='completed')
    completed_at = DateTimeField(default=datetime.utcnow)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'auto_upgrade_log',
        'indexes': [
            'user_id',
            'program',
            'trigger_type',
            'status',
            'completed_at'
        ]
    }

class BinaryAutoUpgrade(Document):
    """Binary program auto upgrade tracking"""
    user_id = ObjectIdField(required=True)
    
    # Current status
    current_slot_no = IntField(required=True)
    current_level = IntField(required=True)
    
    # Partners tracking
    partners_required = IntField(default=2)
    partners_available = IntField(default=0)
    partner_ids = ListField(ObjectIdField())
    
    # Earnings from first 2 partners
    earnings_from_partners = DecimalField(precision=8, default=0)
    earnings_per_partner = DecimalField(precision=8, default=0)
    
    # Auto upgrade eligibility
    is_eligible = BooleanField(default=False)
    next_upgrade_cost = DecimalField(precision=8, default=0)
    can_upgrade = BooleanField(default=False)
    
    # Processing
    last_check_at = DateTimeField(default=datetime.utcnow)
    next_check_at = DateTimeField()
    
    # Status
    is_active = BooleanField(default=True)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'binary_auto_upgrade',
        'indexes': [
            'user_id',
            'is_eligible',
            'can_upgrade',
            'next_check_at'
        ]
    }

class MatrixAutoUpgrade(Document):
    """Matrix program auto upgrade tracking"""
    user_id = ObjectIdField(required=True)
    
    # Current status
    current_slot_no = IntField(required=True)
    current_level = IntField(required=True)
    
    # Middle 3 members tracking
    middle_three_required = IntField(default=3)
    middle_three_available = IntField(default=0)
    middle_three_ids = ListField(ObjectIdField())
    
    # Earnings from middle 3 members
    earnings_from_middle_three = DecimalField(precision=8, default=0)
    earnings_per_member = DecimalField(precision=8, default=0)
    
    # Upline Reserve tracking
    upline_reserve_amount = DecimalField(precision=8, default=0)
    upline_reserve_user_id = ObjectIdField()
    
    # Auto upgrade eligibility
    is_eligible = BooleanField(default=False)
    next_upgrade_cost = DecimalField(precision=8, default=0)
    can_upgrade = BooleanField(default=False)
    
    # Processing
    last_check_at = DateTimeField(default=datetime.utcnow)
    next_check_at = DateTimeField()
    
    # Status
    is_active = BooleanField(default=True)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'matrix_auto_upgrade',
        'indexes': [
            'user_id',
            'is_eligible',
            'can_upgrade',
            'next_check_at'
        ]
    }

class GlobalPhaseProgression(Document):
    """Global program phase progression tracking"""
    user_id = ObjectIdField(required=True)
    
    # Current phase status
    current_phase = StringField(choices=['PHASE-1', 'PHASE-2'], required=True)
    current_slot_no = IntField(required=True)
    phase_position = IntField(required=True)
    
    # Phase requirements
    phase_1_members_required = IntField(default=4)
    phase_1_members_current = IntField(default=0)
    phase_2_members_required = IntField(default=8)
    phase_2_members_current = IntField(default=0)
    
    # Global team tracking
    global_team_size = IntField(default=0)
    global_team_members = ListField(ObjectIdField())
    
    # Progression tracking
    is_phase_complete = BooleanField(default=False)
    phase_completed_at = DateTimeField()
    next_phase_ready = BooleanField(default=False)
    
    # Re-entry tracking
    total_re_entries = IntField(default=0)
    last_re_entry_at = DateTimeField()
    re_entry_slot = IntField(default=1)
    
    # Auto progression
    auto_progression_enabled = BooleanField(default=True)
    progression_triggered = BooleanField(default=False)
    
    # Status
    is_active = BooleanField(default=True)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'global_phase_progression',
        'indexes': [
            'user_id',
            'current_phase',
            'current_slot_no',
            'is_phase_complete',
            'next_phase_ready'
        ]
    }

class AutoUpgradeSettings(Document):
    """Global auto upgrade settings and configuration"""
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    
    # General settings
    auto_upgrade_enabled = BooleanField(default=True)
    check_interval_minutes = IntField(default=60)  # How often to check for upgrades
    max_queue_size = IntField(default=1000)
    
    # Binary specific settings
    binary_partners_required = IntField(default=2)
    binary_earnings_percentage = FloatField(default=100.0)  # 100% of earnings used
    
    # Matrix specific settings
    matrix_middle_three_required = IntField(default=3)
    matrix_earnings_percentage = FloatField(default=100.0)  # 100% of earnings used
    matrix_upline_reserve_percentage = FloatField(default=0.0)  # Reserve percentage
    
    # Global specific settings
    global_phase_1_members = IntField(default=4)
    global_phase_2_members = IntField(default=8)
    global_auto_progression = BooleanField(default=True)
    
    # Processing settings
    batch_size = IntField(default=10)  # Process upgrades in batches
    retry_attempts = IntField(default=3)
    retry_delay_minutes = IntField(default=30)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'auto_upgrade_settings',
        'indexes': [
            'program',
            'is_active'
        ]
    }

class AutoUpgradeEarnings(Document):
    """Track earnings used for auto upgrades"""
    user_id = ObjectIdField(required=True)  # User who earned
    contributor_id = ObjectIdField(required=True)  # User who will benefit from upgrade
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    
    # Earnings details
    earnings_amount = DecimalField(required=True, precision=8)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    earnings_type = StringField(choices=['slot_income', 'commission', 'bonus'], required=True)
    
    # Usage details
    used_for_upgrade = BooleanField(default=False)
    upgrade_queue_id = ObjectIdField()  # Reference to upgrade queue
    used_amount = DecimalField(precision=8, default=0)
    remaining_amount = DecimalField(precision=8, default=0)
    
    # Source information
    source_slot_no = IntField()
    source_slot_name = StringField()
    source_transaction_id = ObjectIdField()
    
    # Status
    status = StringField(choices=['available', 'used', 'expired'], default='available')
    used_at = DateTimeField()
    expires_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'auto_upgrade_earnings',
        'indexes': [
            'user_id',
            'contributor_id',
            'program',
            'status',
            'expires_at'
        ]
    }
