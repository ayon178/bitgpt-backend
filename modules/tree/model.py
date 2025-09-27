from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, DecimalField, ListField, DictField, FloatField
from datetime import datetime

class TreePlacement(Document):
    """Binary/Matrix/Global tree structure and positioning"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    parent_id = ObjectIdField(required=False)  # Allow null for root users
    
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
    
    # Binary child pointers (required for spillover traversal/BFS)
    left_child_id = ObjectIdField()
    right_child_id = ObjectIdField()
    
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
            'is_active',
            'left_child_id',
            'right_child_id'
        ]
    }

## Note: AutoUpgradeLog is centralized in modules/auto_upgrade/model.py

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

## NOTE: MatrixRecycle has been centralized under modules/matrix/model.py to avoid duplication.

## Note: Global phase progression is centralized in modules/auto_upgrade/model.py (GlobalPhaseProgression)
