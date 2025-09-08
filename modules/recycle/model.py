from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, FloatField, ListField, EmbeddedDocumentField, EmbeddedDocument, DictField, DecimalField
from datetime import datetime


class RecycleRule(EmbeddedDocument):
    """Embedded rules for recycle thresholds and placement"""
    slot_no = IntField(required=True)  # 1-15 (matrix slots)
    required_members = IntField(required=True)  # e.g., when 3^level is filled
    recycle_position = StringField(choices=['left', 'center', 'right'], default='center')
    auto_recycle_enabled = BooleanField(default=True)
    carry_over_earnings = BooleanField(default=True)


class RecycleQueue(Document):
    """Queue of users pending recycle placement"""
    user_id = ObjectIdField(required=True)
    parent_id = ObjectIdField(required=True)
    matrix_level = IntField(required=True)
    slot_no = IntField(required=True)
    recycle_reason = StringField(choices=['matrix_completion', 'auto_recycle', 'manual_recycle'], required=True)
    preferred_position = StringField(choices=['left', 'center', 'right'], default='center')

    # Earnings involved in recycle
    recycle_amount = DecimalField(precision=8, default=0)
    currency = StringField(choices=['USDT'], default='USDT')

    # Processing
    status = StringField(choices=['queued', 'processing', 'completed', 'failed'], default='queued')
    attempts = IntField(default=0)
    last_attempt_at = DateTimeField()
    processed_at = DateTimeField()
    failure_reason = StringField()

    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'recycle_queue',
        'indexes': ['user_id', 'parent_id', 'status', 'slot_no', 'matrix_level']
    }


class RecyclePlacement(Document):
    """Record of completed recycle placements"""
    user_id = ObjectIdField(required=True)
    old_parent_id = ObjectIdField(required=True)
    new_parent_id = ObjectIdField(required=True)
    matrix_level = IntField(required=True)
    slot_no = IntField(required=True)
    position = StringField(choices=['left', 'center', 'right'], required=True)

    recycle_amount = DecimalField(precision=8, default=0)
    currency = StringField(choices=['USDT'], default='USDT')

    # Link to queue or trigger
    queue_id = ObjectIdField()
    trigger = StringField(choices=['auto', 'manual'], default='auto')

    processed_by = ObjectIdField()  # admin or system id
    processed_at = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'recycle_placement',
        'indexes': ['user_id', 'new_parent_id', 'slot_no', 'matrix_level', 'processed_at']
    }


class RecycleSettings(Document):
    """Recycle system global settings"""
    setting_name = StringField(default='Recycle Settings', unique=True)

    enabled = BooleanField(default=True)
    auto_recycle_enabled = BooleanField(default=True)
    max_queue_attempts = IntField(default=5)
    queue_batch_size = IntField(default=100)

    # Rules by slot
    rules = ListField(EmbeddedDocumentField(RecycleRule), default=[])

    # Distribution options
    carry_over_earnings = BooleanField(default=True)
    lock_center_position_for_upline_reserve = BooleanField(default=True)

    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'recycle_settings',
        'indexes': ['enabled']
    }


class RecycleLog(Document):
    """Operational log for recycle events"""
    user_id = ObjectIdField(required=True)
    action_type = StringField(choices=['queued', 'placement_attempt', 'placed', 'failed', 'settings_update'], required=True)
    description = StringField(required=True)
    data = DictField(default={})
    related_queue_id = ObjectIdField()
    related_placement_id = ObjectIdField()
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'recycle_log',
        'indexes': ['user_id', 'action_type', 'created_at']
    }


class RecycleStatistics(Document):
    """Aggregated statistics for recycle system"""
    period = StringField(choices=['daily', 'weekly', 'monthly', 'all_time'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField()

    total_queued = IntField(default=0)
    total_processed = IntField(default=0)
    total_failed = IntField(default=0)
    total_attempts = IntField(default=0)

    total_recycle_amount = DecimalField(precision=8, default=0)
    total_distributed_amount = DecimalField(precision=8, default=0)

    by_slot = DictField(default={})
    by_level = DictField(default={})

    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'recycle_statistics',
        'indexes': ['period', 'period_start']
    }


