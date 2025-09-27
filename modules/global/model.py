from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, ListField, DecimalField, DictField, FloatField
from datetime import datetime
from decimal import Decimal

## Note: Global phase progression is centralized in modules/auto_upgrade/model.py (GlobalPhaseProgression)

class GlobalTeamMember(Document):
    """Track Global program team members"""
    user_id = ObjectIdField(required=True)
    parent_user_id = ObjectIdField(required=True)  # Direct upline
    
    # Team position
    phase = StringField(choices=['PHASE-1', 'PHASE-2'], required=True)
    slot_number = IntField(required=True)
    position_in_phase = IntField(required=True)  # Position within the phase
    
    # Team hierarchy
    level_in_tree = IntField(required=True)  # Level in the global tree
    direct_downlines = ListField(ObjectIdField())  # Direct referrals
    total_downlines = ListField(ObjectIdField())  # All downlines
    
    # Performance tracking
    is_active = BooleanField(default=True)
    joined_at = DateTimeField(default=datetime.utcnow)
    last_activity_at = DateTimeField(default=datetime.utcnow)
    
    # Phase progression
    phase_1_contributions = IntField(default=0)  # How many Phase-1 members brought
    phase_2_contributions = IntField(default=0)  # How many Phase-2 members brought
    
    # Status
    status = StringField(choices=['active', 'inactive', 'suspended'], default='active')
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'global_team_members',
        'indexes': [
            'user_id',
            'parent_user_id',
            'phase',
            'slot_number',
            'level_in_tree',
            'status',
            'joined_at'
        ]
    }

class GlobalDistribution(Document):
    """Track Global program fund distributions"""
    user_id = ObjectIdField(required=True)
    transaction_id = ObjectIdField(required=True)  # Reference to original transaction
    
    # Distribution details
    transaction_amount = DecimalField(required=True, precision=8)
    currency = StringField(choices=['USD', 'USDT', 'BNB'], required=True)
    transaction_type = StringField(choices=['join', 'upgrade', 'commission'], required=True)
    
    # Distribution breakdown (100% total)
    level_reserve_amount = DecimalField(precision=8, default=0)  # 30%
    partner_incentive_amount = DecimalField(precision=8, default=0)  # 10%
    profit_amount = DecimalField(precision=8, default=0)  # 30%
    royal_captain_bonus_amount = DecimalField(precision=8, default=0)  # 10%
    president_reward_amount = DecimalField(precision=8, default=0)  # 10%
    triple_entry_reward_amount = DecimalField(precision=8, default=0)  # 5%
    shareholders_amount = DecimalField(precision=8, default=0)  # 5%
    
    # Fund updates
    level_reserve_updated = BooleanField(default=False)
    partner_incentive_updated = BooleanField(default=False)
    profit_updated = BooleanField(default=False)
    royal_captain_bonus_updated = BooleanField(default=False)
    president_reward_updated = BooleanField(default=False)
    triple_entry_reward_updated = BooleanField(default=False)
    shareholders_updated = BooleanField(default=False)
    
    # Processing status
    status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    processed_at = DateTimeField()
    completed_at = DateTimeField()
    
    # Error handling
    error_message = StringField()
    retry_count = IntField(default=0)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'global_distributions',
        'indexes': [
            'user_id',
            'transaction_id',
            'transaction_type',
            'status',
            'created_at'
        ]
    }

class GlobalTreeStructure(Document):
    """Track Global program tree structure"""
    user_id = ObjectIdField(required=True)
    parent_user_id = ObjectIdField()  # Null for root users
    
    # Tree position
    phase = StringField(choices=['PHASE-1', 'PHASE-2'], required=True)
    slot_number = IntField(required=True)
    level = IntField(required=True)
    position = IntField(required=True)  # Position within the level
    
    # Tree metadata
    left_child_id = ObjectIdField()
    right_child_id = ObjectIdField()
    children_count = IntField(default=0)
    
    # Phase-specific data
    phase_1_members = ListField(ObjectIdField())
    phase_2_members = ListField(ObjectIdField())
    
    # Status
    is_active = BooleanField(default=True)
    is_complete = BooleanField(default=False)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'global_tree_structure',
        'indexes': [
            'user_id',
            'parent_user_id',
            'phase',
            'slot_number',
            'level',
            'is_active'
        ]
    }

class GlobalPhaseSeat(Document):
    """Track available seats in Global program phases"""
    user_id = ObjectIdField(required=True)
    phase = StringField(choices=['PHASE-1', 'PHASE-2'], required=True)
    slot_number = IntField(required=True)
    
    # Seat availability
    total_seats = IntField(required=True)  # 4 for Phase-1, 8 for Phase-2
    occupied_seats = IntField(default=0)
    available_seats = IntField(required=True)
    
    # Seat details
    seat_positions = ListField(DictField())  # Detailed seat information
    waiting_list = ListField(ObjectIdField())  # Users waiting for seats
    
    # Status
    is_open = BooleanField(default=True)
    is_full = BooleanField(default=False)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'global_phase_seats',
        'indexes': [
            'user_id',
            'phase',
            'slot_number',
            'is_open',
            'is_full'
        ]
    }
