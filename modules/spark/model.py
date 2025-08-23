from mongoengine import Document, StringField, IntField, DecimalField, DateTimeField, ListField, ObjectIdField
from datetime import datetime
from decimal import Decimal

class SparkCycle(Document):
    """Matrix slot-based distribution - Spark Bonus 8%"""
    cycle_no = IntField(required=True)
    slot_no = IntField(required=True)
    pool_amount = DecimalField(required=True, precision=8)
    participants = ListField(ObjectIdField(), default=[])
    distribution_percentage = DecimalField(required=True, precision=4)
    payout_per_participant = DecimalField(required=True, precision=8)
    status = StringField(choices=['active', 'completed'], default='active')
    payout_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'spark_cycle',
        'indexes': [('cycle_no', 'slot_no'), 'status']
    }

class TripleEntryReward(Document):
    """Track TER fund distributions"""
    cycle_no = IntField(required=True)
    pool_amount = DecimalField(required=True, precision=8)
    eligible_users = ListField(ObjectIdField(), default=[])
    distribution_amount = DecimalField(required=True, precision=8)
    status = StringField(choices=['active', 'distributed'], default='active')
    distributed_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'triple_entry_reward',
        'indexes': ['cycle_no', 'status']
    }
