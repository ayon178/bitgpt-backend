from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, FloatField, ListField, EmbeddedDocumentField, EmbeddedDocument, DictField
from datetime import datetime

class PresidentRewardTier(EmbeddedDocument):
    """Embedded document for President Reward tiers"""
    tier_number = IntField(required=True)  # 1-15
    direct_partners_required = IntField(required=True)
    global_team_required = IntField(required=True)
    reward_amount = FloatField(required=True)
    currency = StringField(choices=['USD'], default='USD')
    tier_description = StringField(required=True)
    is_achieved = BooleanField(default=False)
    achieved_at = DateTimeField()
    requirements_met = DictField(default={})

class PresidentReward(Document):
    """President Reward Program - Main document"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Program status
    is_eligible = BooleanField(default=False)
    is_active = BooleanField(default=False)
    joined_at = DateTimeField()
    qualified_at = DateTimeField()
    
    # Qualification tracking
    direct_partners_matrix = IntField(default=0)
    direct_partners_global = IntField(default=0)
    direct_partners_both = IntField(default=0)
    total_direct_partners = IntField(default=0)
    
    # Global team tracking
    global_team_size = IntField(default=0)
    global_team_members = ListField(ObjectIdField(), default=[])
    
    # Tier tracking
    tiers = ListField(EmbeddedDocumentField(PresidentRewardTier), default=[])
    current_tier = IntField(default=0)
    highest_tier_achieved = IntField(default=0)
    
    # Rewards tracking
    total_rewards_earned = FloatField(default=0.0)
    total_rewards_paid = FloatField(default=0.0)
    pending_rewards = FloatField(default=0.0)
    
    # Achievement tracking
    achievements = ListField(DictField(), default=[])
    milestone_reached = ListField(StringField(), default=[])
    
    # Status
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'president_reward',
        'indexes': [
            'user_id',
            'is_eligible',
            'is_active',
            'current_tier',
            'total_direct_partners'
        ]
    }

class PresidentRewardEligibility(Document):
    """Track President Reward eligibility requirements"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Direct partners requirements
    direct_partners_matrix_count = IntField(default=0)
    direct_partners_global_count = IntField(default=0)
    direct_partners_both_count = IntField(default=0)
    min_direct_partners_required = IntField(default=30)
    
    # Global team requirements
    global_team_count = IntField(default=0)
    min_global_team_for_qualification = IntField(default=0)
    
    # Eligibility status
    is_eligible_for_president_reward = BooleanField(default=False)
    eligibility_reasons = ListField(StringField(), default=[])
    
    # Qualification milestones
    qualified_for_tier_1 = BooleanField(default=False)  # 10 direct partners, 80 global team
    qualified_for_tier_6 = BooleanField(default=False)  # 15 direct partners, 400 global team
    qualified_for_tier_10 = BooleanField(default=False)  # 20 direct partners, 1000 global team
    qualified_for_tier_15 = BooleanField(default=False)  # 30 direct partners, 40000 global team
    
    # Qualification date
    qualified_at = DateTimeField()
    
    # Status
    last_checked = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'president_reward_eligibility',
        'indexes': [
            'user_id',
            'is_eligible_for_president_reward',
            'qualified_for_tier_15'
        ]
    }

class PresidentRewardPayment(Document):
    """Track President Reward payments"""
    user_id = ObjectIdField(required=True)
    president_reward_id = ObjectIdField(required=True)
    
    # Reward details
    tier_number = IntField(required=True)  # 1-15
    reward_amount = FloatField(required=True)
    currency = StringField(choices=['USD'], default='USD')
    
    # Requirements met at payment
    direct_partners_at_payment = IntField(required=True)
    global_team_at_payment = IntField(required=True)
    
    # Payment details
    payment_status = StringField(choices=['pending', 'processing', 'paid', 'failed'], default='pending')
    payment_method = StringField(choices=['wallet', 'blockchain', 'bonus_pool'], default='bonus_pool')
    payment_reference = StringField()  # Transaction hash or reference
    
    # Payment processing
    processed_at = DateTimeField()
    paid_at = DateTimeField()
    failed_reason = StringField()
    
    # Status
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'president_reward_payment',
        'indexes': [
            'user_id',
            'president_reward_id',
            'tier_number',
            'payment_status',
            'created_at'
        ]
    }

class PresidentRewardFund(Document):
    """President Reward Fund management"""
    fund_name = StringField(default='President Reward Fund', unique=True)
    
    # Fund details
    total_fund_amount = FloatField(default=0.0)
    available_amount = FloatField(default=0.0)
    distributed_amount = FloatField(default=0.0)
    currency = StringField(choices=['USD'], default='USD')
    
    # Fund sources
    fund_sources = DictField(default={
        'matrix_contributions': 0.0,
        'global_contributions': 0.0,
        'other_contributions': 0.0
    })
    
    # Fund management
    auto_replenish = BooleanField(default=True)
    replenish_threshold = FloatField(default=5000.0)  # Replenish when below $5000
    max_distribution_per_day = FloatField(default=50000.0)  # Max $50k per day
    
    # Statistics
    total_participants = IntField(default=0)
    total_rewards_paid = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'president_reward_fund',
        'indexes': ['fund_name', 'is_active']
    }

class PresidentRewardSettings(Document):
    """President Reward system settings"""
    setting_name = StringField(default='President Reward Settings', unique=True)
    
    # General settings
    president_reward_enabled = BooleanField(default=True)
    auto_eligibility_check = BooleanField(default=True)
    auto_reward_distribution = BooleanField(default=True)
    
    # Qualification requirements
    min_direct_partners_for_qualification = IntField(default=30)
    require_both_matrix_and_global = BooleanField(default=True)
    
    # Tier requirements
    tier_1_direct_partners = IntField(default=10)
    tier_1_global_team = IntField(default=80)
    tier_6_direct_partners = IntField(default=15)
    tier_6_global_team = IntField(default=400)
    tier_10_direct_partners = IntField(default=20)
    tier_10_global_team = IntField(default=1000)
    tier_15_direct_partners = IntField(default=30)
    tier_15_global_team = IntField(default=40000)
    
    # Reward amounts
    tier_1_reward_amount = FloatField(default=500.0)
    tier_2_5_reward_amount = FloatField(default=700.0)
    tier_6_9_reward_amount = FloatField(default=800.0)
    tier_10_14_reward_amount = FloatField(default=1500.0)
    tier_15_reward_amount = FloatField(default=2000.0)
    
    # Payment settings
    payment_currency = StringField(choices=['USD'], default='USD')
    payment_method = StringField(choices=['bonus_pool'], default='bonus_pool')
    payment_delay_hours = IntField(default=48)  # 48 hours delay
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'president_reward_settings',
        'indexes': ['setting_name', 'is_active']
    }

class PresidentRewardLog(Document):
    """President Reward activity log"""
    user_id = ObjectIdField(required=True)
    action_type = StringField(choices=[
        'eligibility_check', 'qualification_met', 'tier_achieved', 'reward_earned', 'reward_paid',
        'direct_partner_added', 'global_team_growth', 'milestone_reached'
    ], required=True)
    
    # Action details
    action_description = StringField(required=True)
    action_data = DictField(default={})
    
    # Related entities
    related_user_id = ObjectIdField()  # For partner additions
    related_reward_id = ObjectIdField()  # For reward payments
    tier_number = IntField()
    
    # Status
    is_processed = BooleanField(default=False)
    processed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'president_reward_log',
        'indexes': [
            'user_id',
            'action_type',
            'created_at',
            'is_processed'
        ]
    }

class PresidentRewardStatistics(Document):
    """President Reward program statistics"""
    period = StringField(choices=['daily', 'weekly', 'monthly', 'all_time'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField()
    
    # Statistics
    total_eligible_users = IntField(default=0)
    total_active_users = IntField(default=0)
    total_rewards_paid = IntField(default=0)
    total_amount_distributed = FloatField(default=0.0)
    
    # Tier statistics
    tier_1_achievements = IntField(default=0)
    tier_6_achievements = IntField(default=0)
    tier_10_achievements = IntField(default=0)
    tier_15_achievements = IntField(default=0)
    
    # Growth statistics
    new_eligible_users = IntField(default=0)
    new_reward_earners = IntField(default=0)
    total_direct_partners = IntField(default=0)
    total_global_team = IntField(default=0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'president_reward_statistics',
        'indexes': [
            'period',
            'period_start',
            'is_active'
        ]
    }

class PresidentRewardMilestone(Document):
    """Track President Reward milestones"""
    user_id = ObjectIdField(required=True)
    milestone_type = StringField(choices=[
        'first_qualification', 'tier_1_achieved', 'tier_6_achieved', 'tier_10_achieved', 'tier_15_achieved',
        'direct_partners_milestone', 'global_team_milestone', 'reward_milestone'
    ], required=True)
    
    # Milestone details
    milestone_name = StringField(required=True)
    milestone_description = StringField()
    achieved_at = DateTimeField(default=datetime.utcnow)
    
    # Milestone requirements
    requirements_met = DictField(default={})
    tier_number = IntField()
    
    # Rewards
    reward_type = StringField(choices=['bonus', 'privilege', 'access', 'gift'])
    reward_value = FloatField(default=0.0)
    reward_description = StringField()
    
    # Status
    is_claimed = BooleanField(default=False)
    claimed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'president_reward_milestone',
        'indexes': [
            'user_id',
            'milestone_type',
            'achieved_at',
            'is_claimed'
        ]
    }
