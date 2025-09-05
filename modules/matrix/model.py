from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, DecimalField, ListField, DictField, FloatField, EmbeddedDocumentField, EmbeddedDocument
from datetime import datetime
from decimal import Decimal

class MatrixSlotInfo(EmbeddedDocument):
    """Matrix slot information"""
    slot_name = StringField(required=True)  # STARTER, BRONZE, SILVER, GOLD, PLATINUM
    slot_value = DecimalField(required=True, precision=8)  # USDT value
    level = IntField(required=True)
    is_active = BooleanField(default=False)
    activated_at = DateTimeField()
    upgrade_cost = DecimalField(precision=8, default=0)
    total_income = DecimalField(precision=8, default=0)
    wallet_amount = DecimalField(precision=8, default=0)
    
    # Matrix specific fields
    member_count = IntField()  # Required members for this slot (3^level)
    recycle_eligible = BooleanField(default=False)  # Eligible for recycle system

class MatrixPosition(EmbeddedDocument):
    """Matrix position information"""
    position = StringField(choices=['left', 'center', 'right'], required=True)
    user_id = ObjectIdField()
    is_upline_reserve = BooleanField(default=False)  # Center position special handling
    is_active = BooleanField(default=False)
    activated_at = DateTimeField()
    
    # Auto upgrade contribution
    contributes_to_auto_upgrade = BooleanField(default=False)  # Middle 3 members
    earnings_contributed = DecimalField(precision=8, default=0)

class MatrixTree(Document):
    """Matrix tree structure and positioning"""
    user_id = ObjectIdField(required=True)
    parent_id = ObjectIdField(required=True)
    
    # Matrix positions (3 positions per user)
    positions = ListField(EmbeddedDocumentField(MatrixPosition), default=[])
    
    # Current slot information
    current_slot = IntField(default=1)  # 1-5 (STARTER to PLATINUM)
    current_level = IntField(default=1)
    
    # Matrix slots
    matrix_slots = ListField(EmbeddedDocumentField(MatrixSlotInfo), default=[])
    
    # Tree structure tracking
    total_team_size = IntField(default=0)  # Total team size including all levels
    direct_children_count = IntField(default=0)  # Direct children count
    
    # Auto upgrade tracking
    auto_upgrade_enabled = BooleanField(default=True)
    middle_three_earnings = DecimalField(precision=8, default=0)  # Earnings from middle 3 members
    auto_upgrade_ready = BooleanField(default=False)
    
    # Recycle system
    is_recycle_eligible = BooleanField(default=False)
    recycle_amount = DecimalField(precision=8, default=0)
    recycle_position = StringField(choices=['left', 'center', 'right'])
    
    # Commission tracking
    total_commissions_earned = DecimalField(precision=8, default=0)
    total_commissions_paid = DecimalField(precision=8, default=0)
    
    # Status
    is_active = BooleanField(default=True)
    is_activated = BooleanField(default=False)
    activation_date = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'matrix_tree',
        'indexes': [
            'user_id',
            'parent_id',
            'current_slot',
            'current_level',
            'is_active',
            'is_activated'
        ]
    }

class MatrixActivation(Document):
    """Track Matrix slot activations and upgrades"""
    user_id = ObjectIdField(required=True)
    slot_no = IntField(required=True)
    slot_name = StringField(required=True)
    activation_type = StringField(choices=['initial', 'upgrade', 'auto', 'manual'], required=True)
    
    # Payment details
    amount_paid = DecimalField(required=True, precision=8)
    currency = StringField(choices=['USDT'], default='USDT')
    
    # Transaction details
    tx_hash = StringField(required=True, unique=True)
    blockchain_network = StringField(choices=['TRC20', 'ERC20'], default='TRC20')
    
    # Commission details
    commission_paid = DecimalField(precision=8, default=0)
    commission_percentage = FloatField(default=10.0)  # 10% commission
    
    # Auto upgrade details
    is_auto_upgrade = BooleanField(default=False)
    middle_three_contributed = ListField(ObjectIdField())  # Middle 3 members who contributed
    earnings_used = DecimalField(precision=8, default=0)
    
    # Status
    status = StringField(choices=['pending', 'completed', 'failed', 'refunded'], default='pending')
    activated_at = DateTimeField()
    completed_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'matrix_activation',
        'indexes': [
            'user_id',
            'slot_no',
            'status',
            'activation_type',
            'created_at'
        ]
    }

class MatrixRecycle(Document):
    """Track Matrix recycle system"""
    user_id = ObjectIdField(required=True)
    matrix_level = IntField(required=True)
    recycle_position = StringField(choices=['left', 'center', 'right'], required=True)
    recycle_amount = DecimalField(required=True, precision=8)
    currency = StringField(choices=['USDT'], default='USDT')
    
    # Recycle details
    original_slot = StringField(required=True)
    recycle_reason = StringField(choices=['matrix_completion', 'auto_recycle', 'manual_recycle'], required=True)
    
    # Processing
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    processed_by = ObjectIdField()  # Admin who processed
    
    # New placement
    new_parent_id = ObjectIdField()
    new_position = StringField(choices=['left', 'center', 'right'])
    
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'matrix_recycle',
        'indexes': [
            'user_id',
            'matrix_level',
            'is_processed',
            'recycle_reason'
        ]
    }

class MatrixAutoUpgrade(Document):
    """Track Matrix auto upgrade activities"""
    user_id = ObjectIdField(required=True)
    from_slot = IntField(required=True)
    to_slot = IntField(required=True)
    upgrade_cost = DecimalField(required=True, precision=8)
    currency = StringField(choices=['USDT'], default='USDT')
    
    # Middle 3 members contribution
    middle_three_members = ListField(ObjectIdField())
    earnings_from_middle_three = DecimalField(required=True, precision=8)
    
    # Transaction details
    tx_hash = StringField(required=True)
    blockchain_network = StringField(choices=['TRC20', 'ERC20'], default='TRC20')
    
    # Status
    status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    processed_at = DateTimeField()
    completed_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'matrix_auto_upgrade',
        'indexes': [
            'user_id',
            'status',
            'created_at'
        ]
    }

class MatrixCommission(Document):
    """Track Matrix commission distribution"""
    user_id = ObjectIdField(required=True)  # User who gets commission
    from_user_id = ObjectIdField(required=True)  # User who generated commission
    slot_no = IntField(required=True)
    slot_name = StringField(required=True)
    
    # Commission details
    commission_amount = DecimalField(required=True, precision=8)
    currency = StringField(choices=['USDT'], default='USDT')
    commission_type = StringField(choices=['joining', 'upgrade', 'level'], required=True)
    commission_percentage = FloatField(required=True)
    
    # Level information
    level = IntField()  # Which level this commission is for
    is_direct_commission = BooleanField(default=False)  # Direct upline commission
    
    # Status
    status = StringField(choices=['pending', 'paid', 'missed'], default='pending')
    paid_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'matrix_commission',
        'indexes': [
            'user_id',
            'from_user_id',
            'slot_no',
            'status',
            'created_at'
        ]
    }

class MatrixUplineReserve(Document):
    """Track Matrix upline reserve (center position)"""
    user_id = ObjectIdField(required=True)
    upline_id = ObjectIdField(required=True)  # The upline who gets reserve benefits
    matrix_level = IntField(required=True)
    
    # Reserve details
    reserve_amount = DecimalField(required=True, precision=8)
    currency = StringField(choices=['USDT'], default='USDT')
    reserve_type = StringField(choices=['joining', 'upgrade', 'bonus'], required=True)
    
    # Status
    status = StringField(choices=['pending', 'paid', 'accumulated'], default='pending')
    paid_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'matrix_upline_reserve',
        'indexes': [
            'user_id',
            'upline_id',
            'matrix_level',
            'status'
        ]
    }
