from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, ListField
from datetime import datetime

class GlobalPhaseState(Document):
    """Track global matrix phase progression"""
    user_id = ObjectIdField(required=True)
    phase = IntField(choices=[1, 2], required=True)
    slot_index = IntField(required=True)
    children = ListField(ObjectIdField(), default=[])
    ready_for_next = BooleanField(default=False)
    phase_1_completed = BooleanField(default=False)
    phase_2_completed = BooleanField(default=False)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'global_phase_state',
        'indexes': [('user_id', 'phase'), 'phase', 'ready_for_next']
    }
