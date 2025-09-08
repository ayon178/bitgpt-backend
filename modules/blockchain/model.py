from mongoengine import Document, StringField, ObjectIdField, DictField, DateTimeField, BooleanField
from datetime import datetime

class BlockchainEvent(Document):
    """Store blockchain events for idempotency"""
    tx_hash = StringField(required=True, unique=True)
    event_type = StringField(choices=[
        'join_payment', 'slot_activated', 'income_distributed', 'upgrade_triggered',
        'spillover_occurred', 'jackpot_settled', 'spark_distributed'
    ], required=True)
    event_data = DictField(required=True)
    status = StringField(choices=['pending', 'processed', 'failed'], default='pending')
    processed_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'blockchain_event',
        'indexes': ['tx_hash', ('status', 'created_at')]
    }

class SystemConfig(Document):
    """Store system-wide configuration"""
    config_key = StringField(required=True, unique=True)
    config_value = StringField(required=True)
    description = StringField()
    is_active = BooleanField(default=True)
    updated_by = ObjectIdField()
    updated_at = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'system_config',
        'indexes': ['config_key', 'is_active']
    }
