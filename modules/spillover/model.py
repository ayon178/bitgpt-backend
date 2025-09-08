from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, ListField, DictField
from datetime import datetime


class SpilloverQueue(Document):
    """Queue entries for binary spillover placement when direct positions are full"""
    user_id = ObjectIdField(required=True)
    original_parent_id = ObjectIdField(required=True)
    intended_parent_id = ObjectIdField(required=True)  # where user tried to place
    spillover_reason = StringField(choices=['parent_full', 'upline_reroute', 'admin_adjustment'], required=True)
    preferred_side = StringField(choices=['left', 'right'], default='left')

    status = StringField(choices=['queued', 'processing', 'completed', 'failed'], default='queued')
    attempts = IntField(default=0)
    last_attempt_at = DateTimeField()
    processed_at = DateTimeField()
    failure_reason = StringField()

    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'spillover_queue',
        'indexes': ['user_id', 'original_parent_id', 'status']
    }


class SpilloverPlacement(Document):
    """Finalized spillover placements"""
    user_id = ObjectIdField(required=True)
    original_parent_id = ObjectIdField(required=True)
    spillover_parent_id = ObjectIdField(required=True)
    position = StringField(choices=['left', 'right'], required=True)
    spillover_level = IntField(required=True)  # distance from original parent

    queue_id = ObjectIdField()
    trigger = StringField(choices=['auto', 'manual'], default='auto')
    processed_by = ObjectIdField()

    processed_at = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'spillover_placement',
        'indexes': ['user_id', 'spillover_parent_id', 'spillover_level', 'processed_at']
    }


class SpilloverSettings(Document):
    """Global settings for spillover behavior"""
    setting_name = StringField(default='Spillover Settings', unique=True)
    enabled = BooleanField(default=True)
    bfs_search_limit = IntField(default=1000)  # nodes to scan while searching vacancy
    prefer_balance = BooleanField(default=True)  # try to balance left/right
    max_queue_attempts = IntField(default=5)
    queue_batch_size = IntField(default=200)

    # If true, place as far-left-most available; else follow preferred_side
    far_left_strategy = BooleanField(default=True)

    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'spillover_settings',
        'indexes': ['enabled']
    }


class SpilloverLog(Document):
    """Operational log for spillover events"""
    user_id = ObjectIdField(required=True)
    action_type = StringField(choices=['queued', 'placement_attempt', 'placed', 'failed', 'settings_update'], required=True)
    description = StringField(required=True)
    data = DictField(default={})
    related_queue_id = ObjectIdField()
    related_placement_id = ObjectIdField()
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'spillover_log',
        'indexes': ['user_id', 'action_type', 'created_at']
    }


class SpilloverStatistics(Document):
    """Aggregated statistics for spillover"""
    period = StringField(choices=['daily', 'weekly', 'monthly', 'all_time'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField()

    total_queued = IntField(default=0)
    total_processed = IntField(default=0)
    total_failed = IntField(default=0)
    total_attempts = IntField(default=0)

    by_level = DictField(default={})  # level->count
    by_position = DictField(default={'left': 0, 'right': 0})

    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'spillover_statistics',
        'indexes': ['period', 'period_start']
    }


