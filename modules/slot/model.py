from mongoengine import Document, StringField, IntField, DecimalField, BooleanField, DateTimeField, ObjectIdField
from datetime import datetime
from decimal import Decimal

class SlotCatalog(Document):
    """Predefined slot information for all programs"""
    slot_no = IntField(required=True)
    name = StringField(required=True)
    price = DecimalField(required=True, precision=8)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    level = IntField(required=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'slot_catalog',
        'indexes': [('program', 'slot_no'), 'slot_no']
    }

class SlotActivation(Document):
    """Track slot activations and upgrades"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    slot_no = IntField(required=True)
    activation_type = StringField(choices=['initial', 'upgrade', 'auto'], required=True)
    upgrade_source = StringField(choices=['wallet', 'reserve', 'mixed', 'auto'], required=True)
    amount_paid = DecimalField(required=True, precision=8)
    tx_hash = StringField(required=True, unique=True)
    status = StringField(choices=['pending', 'completed', 'failed'], default='pending')
    activated_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'slot_activation',
        'indexes': [('user_id', 'program'), 'tx_hash', ('program', 'slot_no')]
    }
