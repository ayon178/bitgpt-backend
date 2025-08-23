from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, DecimalField
from datetime import datetime

class TreePlacement(Document):
    """Binary/Matrix tree structure and positioning"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    parent_id = ObjectIdField(required=True)
    position = StringField(choices=['left', 'right', 'center'])
    level = IntField(required=True)
    slot_no = IntField(required=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'tree_placement',
        'indexes': [('user_id', 'program'), ('parent_id', 'program'), ('program', 'level')]
    }

class AutoUpgradeLog(Document):
    """Track automatic slot upgrades"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    from_slot = IntField(required=True)
    to_slot = IntField(required=True)
    upgrade_source = StringField(choices=['level_income', 'reserve', 'mixed'], required=True)
    triggered_by = StringField(choices=['first_two_people', 'middle_three', 'phase_completion'], required=True)
    amount_used = DecimalField(required=True, precision=8)
    tx_hash = StringField(required=True)
    status = StringField(choices=['pending', 'completed', 'failed'], default='pending')
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'auto_upgrade_log',
        'indexes': [('user_id', 'program'), 'tx_hash']
    }
