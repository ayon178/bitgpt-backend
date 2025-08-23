from mongoengine import Document, StringField, ObjectIdField, IntField, DictField, DateTimeField
from datetime import datetime

class Qualification(Document):
    """Track user qualifications for bonuses - Royal Captain & President"""
    user_id = ObjectIdField(required=True, unique=True)
    flags = DictField(default={
        'royal_captain_ok': False, 'president_ok': False, 
        'ter_ok': False, 'leadership_ok': False
    })
    counters = DictField(default={
        'direct_partners': 0, 'global_team': 0, 
        'total_sales': 0, 'total_purchases': 0
    })
    royal_captain_level = IntField(choices=[5, 10, 20, 30, 40, 50])
    president_level = IntField(choices=[30, 80, 150, 200, 250, 300, 400, 500, 600, 700, 1000, 1500, 2000, 2500, 3000, 4000])
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'qualification',
        'indexes': ['user_id']
    }
