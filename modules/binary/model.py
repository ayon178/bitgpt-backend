from mongoengine import Document, ObjectIdField, StringField, IntField, FloatField, BooleanField, DateTimeField, ListField, EmbeddedDocument, EmbeddedDocumentField
from datetime import datetime

class BinarySlotInfo(EmbeddedDocument):
    """Binary slot information for a user"""
    slot_no = IntField(required=True)
    slot_name = StringField(required=True)
    slot_value = FloatField(required=True)
    is_active = BooleanField(default=False)
    activated_at = DateTimeField()
    wallet_amount = FloatField(default=0.0)

class BinaryUpgradeLog(Document):
    """Log of binary slot upgrades"""
    user_id = ObjectIdField(required=True)
    from_slot_no = IntField(required=True)
    to_slot_no = IntField(required=True)
    from_slot_name = StringField(required=True)
    to_slot_name = StringField(required=True)
    upgrade_cost = FloatField(required=True)
    currency = StringField(default="BNB")
    tx_hash = StringField(required=True)
    upgrade_type = StringField(choices=['manual', 'auto'], default='manual')
    status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    created_at = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField()
    
    meta = {
        'collection': 'binary_upgrade_logs',
        'indexes': [
            'user_id',
            'status',
            'created_at'
        ]
    }

class BinaryEarningHistory(Document):
    """Binary earning history for a user"""
    user_id = ObjectIdField(required=True)
    earning_type = StringField(choices=['slot_upgrade', 'commission', 'dual_tree', 'leadership_stipend'], required=True)
    slot_no = IntField()
    slot_name = StringField()
    amount = FloatField(required=True)
    currency = StringField(default="BNB")
    source_user_id = ObjectIdField()  # User who triggered the earning
    source_type = StringField()  # Type of source (join, upgrade, etc.)
    description = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'binary_earning_history',
        'indexes': [
            'user_id',
            'earning_type',
            'created_at'
        ]
    }

class BinaryCommission(Document):
    """Binary commission records"""
    from_user_id = ObjectIdField(required=True)  # User who upgraded
    to_user_id = ObjectIdField(required=True)    # User who receives commission
    program = StringField(default="binary")
    slot_no = IntField(required=True)
    slot_name = StringField(required=True)
    commission_type = StringField(choices=['upgrade', 'dual_tree'], required=True)
    commission_level = IntField()  # Level in upline chain
    amount = FloatField(required=True)
    currency = StringField(default="BNB")
    percentage = FloatField()  # Commission percentage
    status = StringField(choices=['pending', 'paid', 'missed'], default='pending')
    tx_hash = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    paid_at = DateTimeField()
    
    meta = {
        'collection': 'binary_commissions',
        'indexes': [
            'from_user_id',
            'to_user_id',
            'commission_type',
            'status',
            'created_at'
        ]
    }

class BinaryDualTreeDistribution(Document):
    """Dual tree distribution records"""
    user_id = ObjectIdField(required=True)  # User who upgraded
    slot_no = IntField(required=True)
    slot_name = StringField(required=True)
    total_amount = FloatField(required=True)
    currency = StringField(default="BNB")
    distributions = ListField()  # List of level distributions
    status = StringField(choices=['pending', 'distributed'], default='pending')
    created_at = DateTimeField(default=datetime.utcnow)
    distributed_at = DateTimeField()
    
    meta = {
        'collection': 'binary_dual_tree_distributions',
        'indexes': [
            'user_id',
            'slot_no',
            'status',
            'created_at'
        ]
    }
