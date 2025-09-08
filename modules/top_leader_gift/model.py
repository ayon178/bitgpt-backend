from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, FloatField, ListField, EmbeddedDocumentField, EmbeddedDocument, DictField
from datetime import datetime

class TopLeaderGiftTier(EmbeddedDocument):
    """Embedded document for Top Leader Gift tiers"""
    tier_number = IntField(required=True)  # 1-5
    tier_name = StringField(required=True)  # Tier 1, Tier 2, etc.
    self_rank_required = IntField(required=True)  # 6, 8, 11, 13, 15
    direct_partners_required = IntField(required=True)  # 5, 7, 8, 9, 10
    partners_rank_required = IntField(required=True)  # 5, 6, 10, 13, 14
    total_team_required = IntField(required=True)  # 300, 500, 1000, 2000, 3000
    gift_name = StringField(required=True)  # LAPTOP, PRIVATE CAR, etc.
    gift_value_usd = FloatField(required=True)  # 3000, 30000, 3000000, etc.
    gift_description = StringField(required=True)
    is_achieved = BooleanField(default=False)
    achieved_at = DateTimeField()
    is_claimed = BooleanField(default=False)
    claimed_at = DateTimeField()
    is_active = BooleanField(default=True)
    activated_at = DateTimeField()

class TopLeaderGift(Document):
    """Top Leader Gift Program - Main document"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Program status
    is_eligible = BooleanField(default=False)
    is_active = BooleanField(default=False)
    joined_at = DateTimeField()
    qualified_at = DateTimeField()
    
    # Current status
    current_self_rank = IntField(default=0)
    current_direct_partners_count = IntField(default=0)
    current_total_team_size = IntField(default=0)
    
    # Direct partners tracking
    direct_partners = ListField(ObjectIdField(), default=[])
    direct_partners_with_ranks = DictField(default={})  # {partner_id: rank}
    
    # Top Leader Gift tiers
    tiers = ListField(EmbeddedDocumentField(TopLeaderGiftTier), default=[])
    current_tier = IntField(default=0)
    max_tier_achieved = IntField(default=0)
    
    # Gift tracking
    total_gifts_earned = IntField(default=0)
    total_gifts_claimed = IntField(default=0)
    total_gift_value_usd = FloatField(default=0.0)
    total_gift_value_claimed_usd = FloatField(default=0.0)
    pending_gift_value_usd = FloatField(default=0.0)
    
    # Status
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'top_leader_gift',
        'indexes': [
            'user_id',
            'is_eligible',
            'is_active',
            'current_self_rank',
            'max_tier_achieved'
        ]
    }

class TopLeaderGiftEligibility(Document):
    """Track Top Leader Gift eligibility requirements"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Rank requirements
    current_self_rank = IntField(default=0)
    min_self_rank_required = IntField(default=6)
    
    # Direct partners requirements
    direct_partners_count = IntField(default=0)
    min_direct_partners_required = IntField(default=5)
    direct_partners_with_ranks = DictField(default={})
    
    # Team size requirements
    total_team_size = IntField(default=0)
    min_total_team_required = IntField(default=300)
    
    # Eligibility status
    is_eligible_for_tier_1 = BooleanField(default=False)
    is_eligible_for_tier_2 = BooleanField(default=False)
    is_eligible_for_tier_3 = BooleanField(default=False)
    is_eligible_for_tier_4 = BooleanField(default=False)
    is_eligible_for_tier_5 = BooleanField(default=False)
    
    # Eligibility reasons
    eligibility_reasons = ListField(StringField(), default=[])
    
    # Qualification date
    qualified_at = DateTimeField()
    
    # Status
    last_checked = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'top_leader_gift_eligibility',
        'indexes': [
            'user_id',
            'is_eligible_for_tier_1',
            'is_eligible_for_tier_2',
            'is_eligible_for_tier_3',
            'is_eligible_for_tier_4',
            'is_eligible_for_tier_5'
        ]
    }

class TopLeaderGiftReward(Document):
    """Track Top Leader Gift rewards"""
    user_id = ObjectIdField(required=True)  # Top Leader
    top_leader_gift_id = ObjectIdField(required=True)
    
    # Reward details
    tier_number = IntField(required=True)  # 1-5
    tier_name = StringField(required=True)
    gift_name = StringField(required=True)
    gift_description = StringField(required=True)
    gift_value_usd = FloatField(required=True)
    currency = StringField(choices=['USD'], default='USD')
    
    # Requirements met
    self_rank_achieved = IntField(required=True)
    direct_partners_count = IntField(required=True)
    partners_rank_achieved = IntField(required=True)
    total_team_size = IntField(required=True)
    
    # Reward status
    reward_status = StringField(choices=['pending', 'processing', 'delivered', 'failed'], default='pending')
    delivery_method = StringField(choices=['physical', 'digital', 'cash_equivalent'], default='physical')
    delivery_reference = StringField()  # Tracking number or reference
    
    # Delivery processing
    processed_at = DateTimeField()
    delivered_at = DateTimeField()
    failed_reason = StringField()
    
    # Status
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'top_leader_gift_reward',
        'indexes': [
            'user_id',
            'top_leader_gift_id',
            'tier_number',
            'reward_status',
            'created_at'
        ]
    }

class TopLeaderGiftFund(Document):
    """Top Leader Gift Fund management"""
    fund_name = StringField(default='Top Leader Gift Fund', unique=True)
    
    # Fund details
    total_fund_amount = FloatField(default=0.0)
    available_amount = FloatField(default=0.0)
    distributed_amount = FloatField(default=0.0)
    currency = StringField(choices=['USD'], default='USD')
    
    # Fund sources
    fund_sources = DictField(default={
        'platform_contributions': 0.0,
        'gift_purchases': 0.0,
        'sponsor_contributions': 0.0,
        'other_contributions': 0.0
    })
    
    # Fund management
    auto_replenish = BooleanField(default=True)
    replenish_threshold = FloatField(default=1000000.0)  # Replenish when below $1M
    max_distribution_per_day = FloatField(default=10000000.0)  # Max $10M per day
    
    # Statistics
    total_participants = IntField(default=0)
    total_rewards_delivered = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'top_leader_gift_fund',
        'indexes': ['fund_name', 'is_active']
    }

class TopLeaderGiftSettings(Document):
    """Top Leader Gift system settings"""
    setting_name = StringField(default='Top Leader Gift Settings', unique=True)
    
    # General settings
    top_leader_gift_enabled = BooleanField(default=True)
    auto_eligibility_check = BooleanField(default=True)
    auto_reward_distribution = BooleanField(default=True)
    
    # Tier requirements
    tier_requirements = DictField(default={
        'tier_1': {
            'self_rank': 6,
            'direct_partners': 5,
            'partners_rank': 5,
            'total_team': 300,
            'gift_name': 'LAPTOP',
            'gift_value': 3000.0
        },
        'tier_2': {
            'self_rank': 8,
            'direct_partners': 7,
            'partners_rank': 6,
            'total_team': 500,
            'gift_name': 'PRIVATE CAR',
            'gift_value': 30000.0
        },
        'tier_3': {
            'self_rank': 11,
            'direct_partners': 8,
            'partners_rank': 10,
            'total_team': 1000,
            'gift_name': 'GLOBAL TOUR PACKAGE',
            'gift_value': 3000000.0
        },
        'tier_4': {
            'self_rank': 13,
            'direct_partners': 9,
            'partners_rank': 13,
            'total_team': 2000,
            'gift_name': 'BUSINESS INVESTMENT FUND',
            'gift_value': 50000000.0
        },
        'tier_5': {
            'self_rank': 15,
            'direct_partners': 10,
            'partners_rank': 14,
            'total_team': 3000,
            'gift_name': 'SUPER LUXURY APARTMENT',
            'gift_value': 150000000.0
        }
    })
    
    # Delivery settings
    delivery_method = StringField(choices=['physical', 'digital', 'cash_equivalent'], default='physical')
    delivery_delay_days = IntField(default=30)  # 30 days delivery delay
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'top_leader_gift_settings',
        'indexes': ['setting_name', 'is_active']
    }

class TopLeaderGiftLog(Document):
    """Top Leader Gift activity log"""
    user_id = ObjectIdField(required=True)
    action_type = StringField(choices=[
        'eligibility_check', 'tier_achieved', 'tier_claimed',
        'reward_delivered', 'rank_updated', 'team_growth'
    ], required=True)
    
    # Action details
    action_description = StringField(required=True)
    action_data = DictField(default={})
    
    # Related entities
    related_tier_number = IntField()
    related_reward_id = ObjectIdField()
    reward_value = FloatField()
    
    # Status
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'top_leader_gift_log',
        'indexes': [
            'user_id',
            'action_type',
            'created_at',
            'is_processed'
        ]
    }

class TopLeaderGiftStatistics(Document):
    """Top Leader Gift program statistics"""
    period = StringField(choices=['daily', 'weekly', 'monthly', 'all_time'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField()
    
    # Statistics
    total_eligible_users = IntField(default=0)
    total_active_users = IntField(default=0)
    total_rewards_delivered = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Tier breakdown
    tier_1_achieved = IntField(default=0)
    tier_1_delivered = IntField(default=0)
    tier_1_amount = FloatField(default=0.0)
    tier_2_achieved = IntField(default=0)
    tier_2_delivered = IntField(default=0)
    tier_2_amount = FloatField(default=0.0)
    tier_3_achieved = IntField(default=0)
    tier_3_delivered = IntField(default=0)
    tier_3_amount = FloatField(default=0.0)
    tier_4_achieved = IntField(default=0)
    tier_4_delivered = IntField(default=0)
    tier_4_amount = FloatField(default=0.0)
    tier_5_achieved = IntField(default=0)
    tier_5_delivered = IntField(default=0)
    tier_5_amount = FloatField(default=0.0)
    
    # Growth statistics
    new_eligible_users = IntField(default=0)
    new_tier_achievers = IntField(default=0)
    total_rank_updates = IntField(default=0)
    total_team_growth = IntField(default=0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'top_leader_gift_statistics',
        'indexes': [
            'period',
            'period_start',
            'is_active'
        ]
    }

class TopLeaderGiftTierProgress(Document):
    """Track Top Leader Gift tier progress"""
    user_id = ObjectIdField(required=True)
    top_leader_gift_id = ObjectIdField(required=True)
    
    # Tier details
    tier_number = IntField(required=True)  # 1-5
    tier_name = StringField(required=True)
    self_rank_required = IntField(required=True)
    direct_partners_required = IntField(required=True)
    partners_rank_required = IntField(required=True)
    total_team_required = IntField(required=True)
    gift_name = StringField(required=True)
    gift_value_usd = FloatField(required=True)
    
    # Progress tracking
    current_self_rank = IntField(default=0)
    current_direct_partners = IntField(default=0)
    current_partners_rank = IntField(default=0)
    current_total_team = IntField(default=0)
    
    # Progress percentages
    self_rank_progress = FloatField(default=0.0)
    direct_partners_progress = FloatField(default=0.0)
    partners_rank_progress = FloatField(default=0.0)
    total_team_progress = FloatField(default=0.0)
    overall_progress = FloatField(default=0.0)
    
    # Status
    is_active = BooleanField(default=True)
    is_achieved = BooleanField(default=False)
    is_claimed = BooleanField(default=False)
    achieved_at = DateTimeField()
    claimed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    last_updated = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'top_leader_gift_tier_progress',
        'indexes': [
            'user_id',
            'top_leader_gift_id',
            'tier_number',
            'is_active',
            'is_achieved'
        ]
    }
