"""
Top Leaders Gift Payment Models - Cash reward system from Spark Bonus 2%
"""
from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, FloatField, DecimalField, ListField, EmbeddedDocumentField, EmbeddedDocument, DictField
from datetime import datetime
from decimal import Decimal

class TopLeadersGiftLevel(EmbeddedDocument):
    """Embedded document for Top Leaders Gift levels (1-5)"""
    level_number = IntField(required=True)  # 1-5
    level_name = StringField(required=True)  # Level 1, Level 2, etc.
    
    # Eligibility criteria
    self_rank_required = IntField(required=True)  # 6, 8, 11, 13, 15
    direct_partners_required = IntField(required=True)  # 5, 7, 8, 9, 10
    partners_rank_required = IntField(required=True)  # 5, 6, 10, 13, 14
    total_team_required = IntField(required=True)  # 300, 500, 1000, 2000, 3000
    
    # Fund allocation from Top Leaders pool
    fund_percentage = FloatField(required=True)  # 37.5%, 25%, 15%, 12.5%, 10%
    
    # Reward limits
    max_reward_usd = FloatField(required=True)  # 3000, 30000, 3000000, 50000000, 150000000
    max_reward_usdt = FloatField(required=True)  # 60% of max_reward_usd
    max_reward_bnb = FloatField(required=True)  # 40% of max_reward_usd (converted)
    
    # Tracking
    is_achieved = BooleanField(default=False)
    achieved_at = DateTimeField()
    total_claimed_usdt = FloatField(default=0.0)
    total_claimed_bnb = FloatField(default=0.0)
    is_maxed_out = BooleanField(default=False)  # Hit the reward limit

class TopLeadersGiftUser(Document):
    """Track Top Leaders Gift for each user"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Program status
    is_eligible = BooleanField(default=False)
    is_active = BooleanField(default=True)
    joined_at = DateTimeField(default=datetime.utcnow)
    qualified_at = DateTimeField()
    
    # Current status
    current_self_rank = IntField(default=0)
    current_direct_partners_count = IntField(default=0)
    current_total_team_size = IntField(default=0)
    direct_partners_with_ranks = DictField(default={})
    
    # Levels tracking
    levels = ListField(EmbeddedDocumentField(TopLeadersGiftLevel), default=[])
    current_level = IntField(default=0)
    highest_level_achieved = IntField(default=0)
    
    # Total rewards claimed
    total_claimed_usdt = FloatField(default=0.0)
    total_claimed_bnb = FloatField(default=0.0)
    total_claims_count = IntField(default=0)
    
    # Last claim
    last_claim_date = DateTimeField()
    
    # Timestamps
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'top_leaders_gift_users',
        'indexes': [
            'user_id',
            'is_eligible',
            'current_level',
            'highest_level_achieved'
        ]
    }

class TopLeadersGiftPayment(Document):
    """Track individual Top Leaders Gift claims/payments"""
    user_id = ObjectIdField(required=True)
    
    # Level details
    level_number = IntField(required=True)  # 1-5
    level_name = StringField(required=True)
    
    # Claim amounts
    claimed_amount_usdt = FloatField(default=0.0)
    claimed_amount_bnb = FloatField(default=0.0)
    currency = StringField(choices=['USDT', 'BNB', 'BOTH'], default='BOTH')
    
    # Eligibility at claim time
    self_rank_at_claim = IntField(required=True)
    direct_partners_at_claim = IntField(required=True)
    total_team_at_claim = IntField(required=True)
    
    # Payment status
    payment_status = StringField(choices=['pending', 'processing', 'paid', 'failed'], default='pending')
    processed_at = DateTimeField()
    paid_at = DateTimeField()
    failed_reason = StringField()
    
    # Transaction references
    usdt_tx_hash = StringField()
    bnb_tx_hash = StringField()
    payment_reference = StringField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'top_leaders_gift_payments',
        'indexes': [
            'user_id',
            'level_number',
            'payment_status',
            'created_at'
        ]
    }

class TopLeadersGiftFund(Document):
    """Top Leaders Gift Fund - 2% from Spark Bonus"""
    fund_name = StringField(default='Top Leaders Gift Fund', unique=True)
    
    # Fund details - USDT (2% from Spark USDT)
    total_fund_usdt = FloatField(default=0.0)
    available_usdt = FloatField(default=0.0)
    distributed_usdt = FloatField(default=0.0)
    
    # Fund details - BNB (2% from Spark BNB)
    total_fund_bnb = FloatField(default=0.0)
    available_bnb = FloatField(default=0.0)
    distributed_bnb = FloatField(default=0.0)
    
    # Level allocations (from available fund)
    level_1_percentage = FloatField(default=37.5)  # 37.5%
    level_2_percentage = FloatField(default=25.0)  # 25%
    level_3_percentage = FloatField(default=15.0)  # 15%
    level_4_percentage = FloatField(default=12.5)  # 12.5%
    level_5_percentage = FloatField(default=10.0)  # 10%
    
    # Statistics
    total_claims = IntField(default=0)
    total_users_claimed = IntField(default=0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'top_leaders_gift_fund',
        'indexes': ['fund_name', 'is_active']
    }

class TopLeadersGiftDistribution(Document):
    """Track 30-day distribution cycles"""
    cycle_no = IntField(required=True, unique=True)  # YYYYMMDD format
    cycle_start = DateTimeField(required=True)
    cycle_end = DateTimeField(required=True)
    
    # Collected from Spark in this cycle
    spark_contribution_usdt = FloatField(default=0.0)  # 2% of Spark USDT
    spark_contribution_bnb = FloatField(default=0.0)   # 2% of Spark BNB
    
    # Level-wise distribution
    level_1_allocated_usdt = FloatField(default=0.0)
    level_1_allocated_bnb = FloatField(default=0.0)
    level_2_allocated_usdt = FloatField(default=0.0)
    level_2_allocated_bnb = FloatField(default=0.0)
    level_3_allocated_usdt = FloatField(default=0.0)
    level_3_allocated_bnb = FloatField(default=0.0)
    level_4_allocated_usdt = FloatField(default=0.0)
    level_4_allocated_bnb = FloatField(default=0.0)
    level_5_allocated_usdt = FloatField(default=0.0)
    level_5_allocated_bnb = FloatField(default=0.0)
    
    # Distribution status
    status = StringField(choices=['active', 'distributing', 'completed'], default='active')
    distributed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'top_leaders_gift_distributions',
        'indexes': ['cycle_no', 'status', 'cycle_start']
    }

