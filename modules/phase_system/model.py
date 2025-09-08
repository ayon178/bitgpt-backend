from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, FloatField, ListField, EmbeddedDocumentField, EmbeddedDocument, DictField
from datetime import datetime

class PhaseSlot(EmbeddedDocument):
    """Embedded document for Phase slots"""
    slot_number = IntField(required=True)  # 1-16
    slot_name = StringField(required=True)  # FOUNDATION, APEX, SUMMIT, etc.
    slot_value = FloatField(required=True)  # Slot value in USD
    phase_type = StringField(choices=['phase_1', 'phase_2'], required=True)
    required_members = IntField(required=True)  # 4 for Phase 1, 8 for Phase 2
    current_members = IntField(default=0)
    is_active = BooleanField(default=False)
    is_completed = BooleanField(default=False)
    activated_at = DateTimeField()
    completed_at = DateTimeField()
    total_income = FloatField(default=0.0)
    upgrade_cost = FloatField(default=0.0)
    wallet_amount = FloatField(default=0.0)

class PhaseProgress(EmbeddedDocument):
    """Embedded document for Phase progress tracking"""
    current_phase = StringField(choices=['phase_1', 'phase_2'], required=True)
    current_slot = IntField(required=True)
    total_phases_completed = IntField(default=0)
    total_slots_completed = IntField(default=0)
    last_upgrade_at = DateTimeField()
    next_upgrade_requirements = DictField(default={})
    progression_history = ListField(DictField(), default=[])

class PhaseSystem(Document):
    """Phase-1 and Phase-2 System - Main document"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Program status
    is_joined = BooleanField(default=False)
    joined_at = DateTimeField()
    is_active = BooleanField(default=False)
    activated_at = DateTimeField()
    
    # Current status
    current_phase = StringField(choices=['phase_1', 'phase_2'], default='phase_1')
    current_slot = IntField(default=1)
    current_slot_name = StringField(default='FOUNDATION')
    current_slot_value = FloatField(default=30.0)
    current_required_members = IntField(default=4)
    current_members_count = IntField(default=0)
    
    # Phase slots
    phase_slots = ListField(EmbeddedDocumentField(PhaseSlot), default=[])
    phase_progress = EmbeddedDocumentField(PhaseProgress)
    
    # Global team tracking
    global_team_members = ListField(ObjectIdField(), default=[])
    global_team_size = IntField(default=0)
    direct_global_referrals = IntField(default=0)
    
    # Progression tracking
    total_phases_completed = IntField(default=0)
    total_slots_completed = IntField(default=0)
    total_income_earned = FloatField(default=0.0)
    total_upgrade_costs = FloatField(default=0.0)
    total_wallet_amount = FloatField(default=0.0)
    
    # Status
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'phase_system',
        'indexes': [
            'user_id',
            'is_joined',
            'is_active',
            'current_phase',
            'current_slot',
            'global_team_size'
        ]
    }

class PhaseSystemEligibility(Document):
    """Track Phase System eligibility requirements"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Eligibility requirements
    has_global_package = BooleanField(default=False)
    global_package_value = FloatField(default=0.0)
    global_package_currency = StringField(choices=['USD'], default='USD')
    
    # Team requirements
    global_team_size = IntField(default=0)
    direct_global_referrals = IntField(default=0)
    min_global_team_required = IntField(default=4)
    
    # Eligibility status
    is_eligible_for_phase_1 = BooleanField(default=False)
    is_eligible_for_phase_2 = BooleanField(default=False)
    is_eligible_for_next_slot = BooleanField(default=False)
    
    # Eligibility reasons
    eligibility_reasons = ListField(StringField(), default=[])
    
    # Qualification date
    qualified_at = DateTimeField()
    
    # Status
    last_checked = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'phase_system_eligibility',
        'indexes': [
            'user_id',
            'is_eligible_for_phase_1',
            'is_eligible_for_phase_2',
            'is_eligible_for_next_slot'
        ]
    }

class PhaseSystemUpgrade(Document):
    """Track Phase System upgrades"""
    user_id = ObjectIdField(required=True)
    phase_system_id = ObjectIdField(required=True)
    
    # Upgrade details
    from_phase = StringField(choices=['phase_1', 'phase_2'], required=True)
    from_slot = IntField(required=True)
    to_phase = StringField(choices=['phase_1', 'phase_2'], required=True)
    to_slot = IntField(required=True)
    
    # Upgrade requirements
    required_members = IntField(required=True)
    actual_members = IntField(required=True)
    upgrade_cost = FloatField(required=True)
    currency = StringField(choices=['USD'], default='USD')
    
    # Upgrade processing
    upgrade_status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    processed_at = DateTimeField()
    completed_at = DateTimeField()
    failed_reason = StringField()
    
    # Status
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'phase_system_upgrade',
        'indexes': [
            'user_id',
            'phase_system_id',
            'upgrade_status',
            'created_at'
        ]
    }

class PhaseSystemFund(Document):
    """Phase System Fund management"""
    fund_name = StringField(default='Phase System Fund', unique=True)
    
    # Fund details
    total_fund_amount = FloatField(default=0.0)
    available_amount = FloatField(default=0.0)
    distributed_amount = FloatField(default=0.0)
    currency = StringField(choices=['USD'], default='USD')
    
    # Fund sources
    fund_sources = DictField(default={
        'global_package_fees': 0.0,
        'slot_upgrade_fees': 0.0,
        'phase_completion_bonuses': 0.0,
        'other_contributions': 0.0
    })
    
    # Fund management
    auto_replenish = BooleanField(default=True)
    replenish_threshold = FloatField(default=10000.0)  # Replenish when below $10K
    max_distribution_per_day = FloatField(default=100000.0)  # Max $100K per day
    
    # Statistics
    total_participants = IntField(default=0)
    total_upgrades_processed = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'phase_system_fund',
        'indexes': ['fund_name', 'is_active']
    }

class PhaseSystemSettings(Document):
    """Phase System settings"""
    setting_name = StringField(default='Phase System Settings', unique=True)
    
    # General settings
    phase_system_enabled = BooleanField(default=True)
    auto_upgrade_enabled = BooleanField(default=True)
    auto_progression_enabled = BooleanField(default=True)
    
    # Phase requirements
    phase_1_member_requirement = IntField(default=4)
    phase_2_member_requirement = IntField(default=8)
    
    # Slot requirements
    slot_requirements = DictField(default={
        'slot_1': {'phase_1': 4, 'phase_2': 8, 'value': 30.0, 'name': 'FOUNDATION'},
        'slot_2': {'phase_1': 4, 'phase_2': 8, 'value': 36.0, 'name': 'APEX'},
        'slot_3': {'phase_1': 4, 'phase_2': 8, 'value': 86.0, 'name': 'SUMMIT'},
        'slot_4': {'phase_1': 4, 'phase_2': 8, 'value': 103.0, 'name': 'RADIANCE'},
        'slot_5': {'phase_1': 4, 'phase_2': 8, 'value': 247.0, 'name': 'HORIZON'},
        'slot_6': {'phase_1': 4, 'phase_2': 8, 'value': 296.0, 'name': 'PARAMOUNT'},
        'slot_7': {'phase_1': 4, 'phase_2': 8, 'value': 710.0, 'name': 'CATALYST'},
        'slot_8': {'phase_1': 4, 'phase_2': 8, 'value': 852.0, 'name': 'ODYSSEY'},
        'slot_9': {'phase_1': 4, 'phase_2': 8, 'value': 2044.0, 'name': 'PINNACLE'},
        'slot_10': {'phase_1': 4, 'phase_2': 8, 'value': 2452.0, 'name': 'PRIME'},
        'slot_11': {'phase_1': 4, 'phase_2': 8, 'value': 5884.0, 'name': 'MOMENTUM'},
        'slot_12': {'phase_1': 4, 'phase_2': 8, 'value': 7060.0, 'name': 'CREST'},
        'slot_13': {'phase_1': 4, 'phase_2': 8, 'value': 16944.0, 'name': 'VERTEX'},
        'slot_14': {'phase_1': 4, 'phase_2': 8, 'value': 20332.0, 'name': 'LEGACY'},
        'slot_15': {'phase_1': 4, 'phase_2': 8, 'value': 48796.0, 'name': 'ASCEND'},
        'slot_16': {'phase_1': 4, 'phase_2': 8, 'value': 58555.0, 'name': 'EVEREST'}
    })
    
    # Upgrade settings
    upgrade_delay_hours = IntField(default=24)  # 24 hours delay between upgrades
    max_upgrades_per_day = IntField(default=1)  # Max 1 upgrade per day
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'phase_system_settings',
        'indexes': ['setting_name', 'is_active']
    }

class PhaseSystemLog(Document):
    """Phase System activity log"""
    user_id = ObjectIdField(required=True)
    action_type = StringField(choices=[
        'joined_phase_system', 'phase_upgraded', 'slot_upgraded',
        'members_added', 'upgrade_processed', 'fund_updated'
    ], required=True)
    
    # Action details
    action_description = StringField(required=True)
    action_data = DictField(default={})
    
    # Related entities
    related_phase = StringField()
    related_slot = IntField()
    related_upgrade_id = ObjectIdField()
    amount = FloatField()
    currency = StringField()
    
    # Status
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'phase_system_log',
        'indexes': [
            'user_id',
            'action_type',
            'created_at',
            'is_processed'
        ]
    }

class PhaseSystemStatistics(Document):
    """Phase System program statistics"""
    period = StringField(choices=['daily', 'weekly', 'monthly', 'all_time'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField()
    
    # Statistics
    total_participants = IntField(default=0)
    total_active_participants = IntField(default=0)
    total_upgrades_processed = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Phase breakdown
    phase_1_participants = IntField(default=0)
    phase_1_upgrades = IntField(default=0)
    phase_1_amount = FloatField(default=0.0)
    phase_2_participants = IntField(default=0)
    phase_2_upgrades = IntField(default=0)
    phase_2_amount = FloatField(default=0.0)
    
    # Slot breakdown
    slot_1_completions = IntField(default=0)
    slot_2_completions = IntField(default=0)
    slot_3_completions = IntField(default=0)
    slot_4_completions = IntField(default=0)
    slot_5_completions = IntField(default=0)
    slot_6_completions = IntField(default=0)
    slot_7_completions = IntField(default=0)
    slot_8_completions = IntField(default=0)
    slot_9_completions = IntField(default=0)
    slot_10_completions = IntField(default=0)
    slot_11_completions = IntField(default=0)
    slot_12_completions = IntField(default=0)
    slot_13_completions = IntField(default=0)
    slot_14_completions = IntField(default=0)
    slot_15_completions = IntField(default=0)
    slot_16_completions = IntField(default=0)
    
    # Growth statistics
    new_participants = IntField(default=0)
    new_upgrades = IntField(default=0)
    total_global_team_growth = IntField(default=0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'phase_system_statistics',
        'indexes': [
            'period',
            'period_start',
            'is_active'
        ]
    }

class PhaseSystemMember(Document):
    """Track Phase System members"""
    user_id = ObjectIdField(required=True)
    phase_system_id = ObjectIdField(required=True)
    
    # Member details
    member_type = StringField(choices=['direct_referral', 'indirect_referral'], required=True)
    referral_level = IntField(required=True)  # 1 for direct, 2+ for indirect
    upline_user_id = ObjectIdField(required=True)
    
    # Member status
    is_active = BooleanField(default=True)
    joined_at = DateTimeField(required=True)
    activated_at = DateTimeField()
    
    # Contribution tracking
    contribution_amount = FloatField(default=0.0)
    contribution_currency = StringField(choices=['USD'], default='USD')
    contribution_type = StringField(choices=['global_package', 'slot_upgrade'], default='global_package')
    
    # Status
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'phase_system_member',
        'indexes': [
            'user_id',
            'phase_system_id',
            'member_type',
            'referral_level',
            'upline_user_id'
        ]
    }
