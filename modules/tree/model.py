from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, DecimalField, ListField, DictField, FloatField
from datetime import datetime

class TreePlacement(Document):
    """Binary/Matrix/Global tree structure and positioning"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    parent_id = ObjectIdField(required=True)
    
    # Position based on program type
    # Binary: left, right
    # Matrix: left, center, right
    # Global: position_1, position_2, position_3, position_4 (for PHASE-1) or position_1-8 (for PHASE-2)
    position = StringField(required=True)
    
    level = IntField(required=True)
    slot_no = IntField(required=True)
    
    # Global program specific fields
    phase = StringField(choices=['PHASE-1', 'PHASE-2'])  # For Global program
    phase_position = IntField()  # Position within the phase (1-4 for PHASE-1, 1-8 for PHASE-2)
    
    # Matrix program specific fields
    is_upline_reserve = BooleanField(default=False)  # Center position in Matrix
    is_recycle_eligible = BooleanField(default=False)  # For Matrix recycle system
    
    # Binary program specific fields
    is_spillover = BooleanField(default=False)  # Spillover placement
    spillover_from = ObjectIdField()  # Original parent for spillover
    
    # Tree structure tracking
    children_count = IntField(default=0)  # Number of direct children
    total_team_size = IntField(default=0)  # Total team size including all levels
    
    # Auto upgrade tracking
    auto_upgrade_eligible = BooleanField(default=False)
    partners_for_auto_upgrade = IntField(default=0)  # Partners needed for auto upgrade
    
    # Status
    is_active = BooleanField(default=True)
    is_activated = BooleanField(default=False)  # User activation status
    activation_date = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'tree_placement',
        'indexes': [
            ('user_id', 'program'), 
            ('parent_id', 'program'), 
            ('program', 'level'),
            'phase',
            'is_spillover',
            'is_upline_reserve',
            'is_active'
        ]
    }

class AutoUpgradeLog(Document):
    """Track automatic slot upgrades"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    from_slot = IntField(required=True)
    to_slot = IntField(required=True)
    upgrade_source = StringField(choices=['level_income', 'reserve', 'mixed', 'partners_earnings'], required=True)
    triggered_by = StringField(choices=['first_two_people', 'middle_three', 'phase_completion', 'manual'], required=True)
    amount_used = DecimalField(required=True, precision=8)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    
    # Partners who contributed to auto upgrade
    partners_contributed = ListField(ObjectIdField())
    earnings_from_partners = DecimalField(precision=8, default=0)
    
    # Transaction details
    tx_hash = StringField(required=True)
    blockchain_network = StringField(choices=['BSC', 'ETH', 'TRC20'], default='BSC')
    
    # Status
    status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    processed_at = DateTimeField()
    completed_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'auto_upgrade_log',
        'indexes': [
            ('user_id', 'program'), 
            'tx_hash',
            'status',
            'triggered_by',
            'created_at'
        ]
    }

class TreeSpillover(Document):
    """Track spillover placements in Binary tree"""
    user_id = ObjectIdField(required=True)
    original_parent_id = ObjectIdField(required=True)
    spillover_parent_id = ObjectIdField(required=True)
    spillover_level = IntField(required=True)
    spillover_position = StringField(choices=['left', 'right'], required=True)
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'tree_spillover',
        'indexes': [
            'user_id',
            'original_parent_id',
            'spillover_parent_id',
            'is_processed'
        ]
    }

class MatrixRecycle(Document):
    """Track Matrix recycle system"""
    user_id = ObjectIdField(required=True)
    matrix_level = IntField(required=True)
    recycle_position = StringField(choices=['left', 'center', 'right'], required=True)
    recycle_amount = DecimalField(required=True, precision=8)
    currency = StringField(choices=['USDT'], default='USDT')
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'matrix_recycle',
        'indexes': [
            'user_id',
            'matrix_level',
            'is_processed'
        ]
    }

class GlobalPhaseProgress(Document):
    """Track Global program phase progression"""
    user_id = ObjectIdField(required=True)
    current_phase = StringField(choices=['PHASE-1', 'PHASE-2'], required=True)
    current_slot = IntField(required=True)
    phase_position = IntField(required=True)
    
    # Phase completion tracking
    phase_1_members_required = IntField(default=4)
    phase_1_members_current = IntField(default=0)
    phase_2_members_required = IntField(default=8)
    phase_2_members_current = IntField(default=0)
    
    # Re-entry tracking
    total_re_entries = IntField(default=0)
    last_re_entry_at = DateTimeField()
    
    # Status
    is_phase_complete = BooleanField(default=False)
    phase_completed_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'global_phase_progress',
        'indexes': [
            'user_id',
            'current_phase',
            'current_slot',
            'is_phase_complete'
        ]
    }
