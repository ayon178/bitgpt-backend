from mongoengine import Document, StringField, ObjectIdField, DateTimeField, BooleanField, IntField, ListField, DictField
from datetime import datetime

class User(Document):
    """Core user model for BitGPT platform"""
    uid = StringField(required=True, unique=True)
    refer_code = StringField(required=True, unique=True)
    upline_id = ObjectIdField(required=True)
    wallet_address = StringField(required=True, unique=True)
    name = StringField(required=True)
    role = StringField(choices=['user', 'admin', 'shareholder'], default='user')
    status = StringField(choices=['active', 'inactive', 'blocked'], default='active')
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'users',
        'indexes': [
            'uid',
            'refer_code', 
            'wallet_address',
            'upline_id',
            'role'
        ]
    }

class PartnerGraph(Document):
    """Track direct partner relationships"""
    user_id = ObjectIdField(required=True, unique=True)
    directs = ListField(ObjectIdField(), default=[])
    directs_count_by_program = DictField(default={
        'binary': 0,
        'matrix': 0,
        'global': 0
    })
    total_team = IntField(default=0)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'partner_graph',
        'indexes': [
            'user_id'
        ]
    }
