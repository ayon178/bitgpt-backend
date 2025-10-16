from mongoengine import Document, ObjectIdField, StringField, IntField, FloatField, BooleanField, DateTimeField, ListField, DictField, EmbeddedDocument, EmbeddedDocumentField, DecimalField
from datetime import datetime
from decimal import Decimal

class MatrixNode(EmbeddedDocument):
    """Individual matrix node in the 3x structure"""
    level = IntField(required=True)  # 1, 2, or 3
    position = IntField(required=True)  # 0-based position within level
    user_id = ObjectIdField(required=True)  # User occupying this position
    placed_at = DateTimeField(default=datetime.utcnow)
    is_active = BooleanField(default=True)
    
    meta = {
        'indexes': [
            'level',
            'position',
            'user_id'
        ]
    }

class MatrixSlotInfo(EmbeddedDocument):
    """Matrix slot information for a user"""
    slot_no = IntField(required=True)
    slot_name = StringField(required=True)
    slot_value = DecimalField(required=True)
    level = IntField(required=True)
    members_count = IntField(required=True)  # 3, 9, 27, 81, 243, etc.
    is_active = BooleanField(default=False)
    activated_at = DateTimeField()
    total_income = DecimalField(default=Decimal('0'))
    upgrade_cost = DecimalField(default=Decimal('0'))
    wallet_amount = DecimalField(default=Decimal('0'))

class MatrixTree(Document):
    """User's matrix tree structure"""
    user_id = ObjectIdField(required=True, unique=True)
    current_slot = IntField(default=1)  # Current active slot (1-15)
    current_level = IntField(default=1)  # Current level (1-15)
    total_members = IntField(default=0)  # Total members in tree
    level_1_members = IntField(default=0)  # Members in level 1
    level_2_members = IntField(default=0)  # Members in level 2
    level_3_members = IntField(default=0)  # Members in level 3
    is_complete = BooleanField(default=False)  # True when 39 members complete
    nodes = ListField(EmbeddedDocumentField(MatrixNode))  # All nodes in tree
    slots = ListField(EmbeddedDocumentField(MatrixSlotInfo))  # User's slot info
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'matrix_trees',
        'indexes': [
            'user_id',
            'current_slot',
            'is_complete',
            'created_at'
        ]
    }

class MatrixActivation(Document):
    """Matrix slot activation records"""
    user_id = ObjectIdField(required=True)
    slot_no = IntField(required=True)
    slot_name = StringField(required=True)
    activation_type = StringField(choices=['initial', 'upgrade'], default='initial')
    upgrade_source = StringField(choices=['auto', 'manual'], default='manual')
    amount_paid = DecimalField(required=True)
    currency = StringField(default="USDT")
    tx_hash = StringField(required=True)
    is_auto_upgrade = BooleanField(default=False)
    status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    activated_at = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField()
    
    meta = {
        'collection': 'matrix_activations',
        'indexes': [
            'user_id',
            'slot_no',
            'activation_type',
            'status',
            'activated_at'
        ]
    }

class MatrixUpgradeLog(Document):
    """Log of matrix slot upgrades"""
    user_id = ObjectIdField(required=True)
    from_slot_no = IntField(required=True)
    to_slot_no = IntField(required=True)
    from_slot_name = StringField(required=True)
    to_slot_name = StringField(required=True)
    upgrade_cost = DecimalField(required=True)
    currency = StringField(default="USDT")
    tx_hash = StringField(required=True)
    upgrade_type = StringField(choices=['manual', 'auto'], default='manual')
    trigger_type = StringField(choices=['middle_three', 'manual'], default='manual')
    earnings_used = DecimalField(default=Decimal('0'))
    profit_gained = DecimalField(default=Decimal('0'))
    contributors = ListField(DictField(), default=list)  # List of middle-three contributors
    status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    created_at = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField()
    
    meta = {
        'collection': 'matrix_upgrade_logs',
        'indexes': [
            'user_id',
            'status',
            'created_at'
        ]
    }

class MatrixEarningHistory(Document):
    """Matrix earning history for a user"""
    user_id = ObjectIdField(required=True)
    earning_type = StringField(choices=['slot_activation', 'commission', 'level_income', 'mentorship', 'dream_matrix'], required=True)
    slot_no = IntField()
    slot_name = StringField()
    amount = DecimalField(required=True)
    currency = StringField(default="USDT")
    source_user_id = ObjectIdField()  # User who triggered the earning
    source_type = StringField()  # Type of source (join, upgrade, etc.)
    level = IntField()  # Matrix level for level income
    description = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'matrix_earning_history',
        'indexes': [
            'user_id',
            'earning_type',
            'created_at'
        ]
    }

class MatrixCommission(Document):
    """Matrix commission records"""
    from_user_id = ObjectIdField(required=True)  # User who activated/upgraded
    to_user_id = ObjectIdField(required=True)    # User who receives commission
    program = StringField(default="matrix")
    slot_no = IntField(required=True)
    slot_name = StringField(required=True)
    commission_type = StringField(choices=['joining', 'upgrade', 'level_income', 'mentorship'], required=True)
    commission_level = IntField()  # Level in upline chain
    amount = DecimalField(required=True)
    currency = StringField(default="USDT")
    percentage = FloatField()  # Commission percentage
    status = StringField(choices=['pending', 'paid', 'missed'], default='pending')
    tx_hash = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    paid_at = DateTimeField()
    
    meta = {
        'collection': 'matrix_commissions',
        'indexes': [
            'from_user_id',
            'to_user_id',
            'commission_type',
            'status',
            'created_at'
        ]
    }

class MatrixRecycleInstance(Document):
    """Matrix recycle instance tracking"""
    user_id = ObjectIdField(required=True)
    slot_number = IntField(required=True)  # 1-15
    recycle_no = IntField(required=True)  # 1-based counter per user+slot
    is_complete = BooleanField(default=False)  # True when 39 members complete
    total_members = IntField(default=0)  # Total members in this recycle
    level_1_members = IntField(default=0)
    level_2_members = IntField(default=0)
    level_3_members = IntField(default=0)
    created_at = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField()
    
    meta = {
        'collection': 'matrix_recycle_instances',
        'indexes': [
            'user_id',
            'slot_number',
            'recycle_no',
            'is_complete',
            'created_at'
        ]
    }

class MatrixRecycleNode(Document):
    """Immutable snapshot of matrix recycle nodes"""
    instance_id = ObjectIdField(required=True)  # Reference to MatrixRecycleInstance
    user_id = ObjectIdField(required=True)  # User who owns this recycle
    slot_number = IntField(required=True)
    recycle_no = IntField(required=True)
    level = IntField(required=True)  # 1, 2, or 3
    position = IntField(required=True)  # 0-based position within level
    occupant_user_id = ObjectIdField(required=True)  # User occupying this position
    placed_at = DateTimeField(required=True)
    
    meta = {
        'collection': 'matrix_recycle_nodes',
        'indexes': [
            'instance_id',
            'user_id',
            'slot_number',
            'recycle_no',
            'level',
            'position'
        ]
    }