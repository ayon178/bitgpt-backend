from mongoengine import Document, StringField, ObjectIdField, IntField, BooleanField, DateTimeField, FloatField, ListField, EmbeddedDocumentField, EmbeddedDocument, DictField
from datetime import datetime

class RankRequirement(EmbeddedDocument):
    """Embedded document for rank requirements"""
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    min_slots_activated = IntField(required=True)
    min_slot_level = IntField(required=True)  # Minimum slot level required
    min_team_size = IntField(default=0)  # Minimum team size
    min_direct_partners = IntField(default=0)  # Minimum direct partners
    min_earnings = FloatField(default=0.0)  # Minimum earnings requirement
    special_conditions = ListField(StringField())  # Special conditions like "both programs"

class RankBenefit(EmbeddedDocument):
    """Embedded document for rank benefits and privileges"""
    benefit_type = StringField(choices=[
        'commission_bonus', 'daily_income', 'special_bonus', 'priority_support',
        'exclusive_access', 'mentorship_privilege', 'leadership_bonus', 'royal_captain_eligible',
        'president_reward_eligible', 'top_leader_gift_eligible'
    ], required=True)
    benefit_value = FloatField(default=0.0)
    benefit_description = StringField(required=True)
    is_active = BooleanField(default=True)

class Rank(Document):
    """Define the 15 special ranks with their requirements and benefits"""
    rank_number = IntField(required=True, unique=True)  # 1-15
    rank_name = StringField(required=True, unique=True)  # Bitron, Cryzen, etc.
    rank_row = IntField(required=True)  # 1, 2, or 3
    
    # Requirements
    requirements = ListField(EmbeddedDocumentField(RankRequirement), default=[])
    
    # Benefits and privileges
    benefits = ListField(EmbeddedDocumentField(RankBenefit), default=[])
    
    # Rank progression
    is_achievable = BooleanField(default=True)
    is_final_rank = BooleanField(default=False)  # True for Omega (rank 15)
    
    # Display information
    rank_description = StringField()
    rank_icon = StringField()  # Icon or image path
    rank_color = StringField()  # Color code for UI
    
    # Status
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'ranks',
        'indexes': [
            'rank_number',
            'rank_name',
            'rank_row',
            'is_active'
        ]
    }

class UserRank(Document):
    """Track user's rank progression and current status"""
    user_id = ObjectIdField(required=True, unique=True)
    
    # Current rank
    current_rank_number = IntField(default=1)
    current_rank_name = StringField(default="Bitron")
    rank_achieved_at = DateTimeField(default=datetime.utcnow)
    
    # Rank progression history
    rank_history = ListField(DictField(), default=[])  # List of {rank_number, rank_name, achieved_at}
    
    # Requirements tracking
    binary_slots_activated = IntField(default=0)
    matrix_slots_activated = IntField(default=0)
    global_slots_activated = IntField(default=0)
    total_slots_activated = IntField(default=0)
    
    # Team statistics
    total_team_size = IntField(default=0)
    direct_partners_count = IntField(default=0)
    total_earnings = FloatField(default=0.0)
    
    # Special qualifications
    royal_captain_eligible = BooleanField(default=False)
    president_reward_eligible = BooleanField(default=False)
    top_leader_gift_eligible = BooleanField(default=False)
    leadership_stipend_eligible = BooleanField(default=False)
    
    # Next rank progress
    next_rank_number = IntField(default=2)
    next_rank_name = StringField(default="Cryzen")
    progress_percentage = FloatField(default=0.0)  # Progress towards next rank
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'user_ranks',
        'indexes': [
            'user_id',
            'current_rank_number',
            'current_rank_name',
            'is_active'
        ]
    }

class RankAchievement(Document):
    """Track individual rank achievements"""
    user_id = ObjectIdField(required=True)
    rank_number = IntField(required=True)
    rank_name = StringField(required=True)
    
    # Achievement details
    achieved_at = DateTimeField(default=datetime.utcnow)
    achievement_type = StringField(choices=['automatic', 'manual', 'special'], default='automatic')
    
    # Requirements met at time of achievement
    binary_slots_at_achievement = IntField(default=0)
    matrix_slots_at_achievement = IntField(default=0)
    global_slots_at_achievement = IntField(default=0)
    team_size_at_achievement = IntField(default=0)
    earnings_at_achievement = FloatField(default=0.0)
    
    # Benefits activated
    benefits_activated = ListField(StringField(), default=[])
    
    # Status
    is_active = BooleanField(default=True)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'rank_achievements',
        'indexes': [
            'user_id',
            'rank_number',
            'achieved_at',
            'is_active'
        ]
    }

class RankBonus(Document):
    """Track rank-based bonuses and rewards"""
    user_id = ObjectIdField(required=True)
    rank_number = IntField(required=True)
    rank_name = StringField(required=True)
    
    # Bonus details
    bonus_type = StringField(choices=[
        'commission_bonus', 'daily_income', 'special_bonus', 'leadership_bonus',
        'royal_captain_bonus', 'president_reward', 'top_leader_gift'
    ], required=True)
    bonus_amount = FloatField(required=True)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    
    # Bonus calculation
    base_amount = FloatField(required=True)
    bonus_percentage = FloatField(default=0.0)
    multiplier = FloatField(default=1.0)
    
    # Payment details
    payment_status = StringField(choices=['pending', 'paid', 'failed'], default='pending')
    payment_method = StringField(choices=['wallet', 'blockchain', 'bonus_pool'])
    tx_hash = StringField()
    paid_at = DateTimeField()
    
    # Status
    is_active = BooleanField(default=True)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'rank_bonuses',
        'indexes': [
            'user_id',
            'rank_number',
            'bonus_type',
            'payment_status',
            'created_at'
        ]
    }

class RankLeaderboard(Document):
    """Global rank leaderboard"""
    period = StringField(choices=['daily', 'weekly', 'monthly', 'all_time'], required=True)
    period_start = DateTimeField(required=True)
    period_end = DateTimeField()
    
    # Leaderboard data
    leaderboard_data = ListField(DictField(), default=[])  # List of {user_id, rank_number, rank_name, score}
    
    # Statistics
    total_participants = IntField(default=0)
    top_rank_achieved = IntField(default=1)
    average_rank = FloatField(default=1.0)
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'rank_leaderboard',
        'indexes': [
            'period',
            'period_start',
            'is_active'
        ]
    }

class RankSettings(Document):
    """Global rank system settings"""
    setting_name = StringField(default='Rank System Settings', unique=True)
    
    # General settings
    rank_system_enabled = BooleanField(default=True)
    auto_rank_progression = BooleanField(default=True)
    manual_rank_verification = BooleanField(default=False)
    
    # Progression settings
    min_slots_for_rank_2 = IntField(default=2)  # Minimum slots for Cryzen
    min_slots_for_rank_3 = IntField(default=4)  # Minimum slots for Neura
    rank_progression_multiplier = FloatField(default=1.0)
    
    # Bonus settings
    rank_bonus_enabled = BooleanField(default=True)
    daily_rank_income_enabled = BooleanField(default=True)
    commission_bonus_percentage = FloatField(default=5.0)  # 5% bonus per rank
    
    # Special program eligibility
    royal_captain_min_rank = IntField(default=5)  # Minimum rank for Royal Captain
    president_reward_min_rank = IntField(default=10)  # Minimum rank for President Reward
    top_leader_gift_min_rank = IntField(default=15)  # Minimum rank for Top Leader Gift
    
    # Status
    is_active = BooleanField(default=True)
    last_updated = DateTimeField(default=datetime.utcnow)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'rank_settings',
        'indexes': ['setting_name', 'is_active']
    }

class RankMilestone(Document):
    """Track rank milestones and special achievements"""
    user_id = ObjectIdField(required=True)
    milestone_type = StringField(choices=[
        'first_rank', 'rank_5_achieved', 'rank_10_achieved', 'rank_15_achieved',
        'both_programs_active', 'team_milestone', 'earnings_milestone'
    ], required=True)
    
    # Milestone details
    milestone_name = StringField(required=True)
    milestone_description = StringField()
    achieved_at = DateTimeField(default=datetime.utcnow)
    
    # Milestone requirements
    requirements_met = DictField(default={})
    
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
        'collection': 'rank_milestones',
        'indexes': [
            'user_id',
            'milestone_type',
            'achieved_at',
            'is_claimed'
        ]
    }
