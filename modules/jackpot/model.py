from mongoengine import Document, StringField, ObjectIdField, DecimalField, DateTimeField, IntField, ListField, EmbeddedDocumentField, BooleanField, EmbeddedDocument
from datetime import datetime, timedelta
from decimal import Decimal
from bson import ObjectId

class JackpotEntry(EmbeddedDocument):
    """Individual jackpot entry"""
    entry_id = StringField(required=True)
    entry_type = StringField(choices=['paid', 'free'], required=True)
    entry_fee = DecimalField(required=True, precision=8)
    tx_hash = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)

class JackpotWinner(EmbeddedDocument):
    """Jackpot winner information"""
    user_id = ObjectIdField(required=True)
    pool_type = StringField(choices=['open_pool', 'top_promoters', 'top_buyers', 'new_joiners'], required=True)
    rank = IntField(required=True)  # 1-10 for open/new_joiners, 1-20 for promoters/buyers
    amount_won = DecimalField(required=True, precision=8)
    entries_count = IntField(required=True)
    direct_referrals_count = IntField(required=False)  # For promoters pool
    is_new_joiner = BooleanField(default=False)  # For new joiners pool

class JackpotDistribution(Document):
    """Jackpot distribution record"""
    distribution_id = StringField(required=True, unique=True)
    week_start_date = DateTimeField(required=True)
    week_end_date = DateTimeField(required=True)
    total_fund = DecimalField(required=True, precision=8)
    total_entries = IntField(required=True)
    
    # Pool distributions
    open_pool_amount = DecimalField(required=True, precision=8)
    top_promoters_pool_amount = DecimalField(required=True, precision=8)
    top_buyers_pool_amount = DecimalField(required=True, precision=8)
    new_joiners_pool_amount = DecimalField(required=True, precision=8)
    
    # Winners
    winners = ListField(EmbeddedDocumentField(JackpotWinner))
    
    # Rollover amounts
    promoters_rollover = DecimalField(default=Decimal('0.0'), precision=8)
    buyers_rollover = DecimalField(default=Decimal('0.0'), precision=8)
    
    status = StringField(choices=['pending', 'completed', 'failed'], default='pending')
    distribution_date = DateTimeField(required=False)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'jackpot_distributions',
        'indexes': [('week_start_date', 'week_end_date'), 'distribution_id']
    }

class JackpotUserEntry(Document):
    """User's jackpot entries for a specific week"""
    user_id = ObjectIdField(required=True)
    week_start_date = DateTimeField(required=True)
    week_end_date = DateTimeField(required=True)
    
    # Entry counts
    paid_entries_count = IntField(default=0)
    free_entries_count = IntField(default=0)
    total_entries_count = IntField(default=0)
    
    # Direct referrals entries (for promoters pool)
    direct_referrals_entries_count = IntField(default=0)
    
    # Entry details
    entries = ListField(EmbeddedDocumentField(JackpotEntry))
    
    # Free coupons earned from binary slots
    free_coupons_earned = IntField(default=0)
    free_coupons_used = IntField(default=0)
    
    # Binary slot contributions
    binary_contributions = DecimalField(default=Decimal('0.0'), precision=8)
    
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'jackpot_user_entries',
        'indexes': [('user_id', 'week_start_date'), ('week_start_date', 'week_end_date')]
    }

class JackpotFreeCoupon(Document):
    """Free jackpot coupons earned from binary slot upgrades"""
    user_id = ObjectIdField(required=True)
    slot_number = IntField(required=True)
    coupons_earned = IntField(required=True)
    coupons_used = IntField(default=0)
    week_start_date = DateTimeField(required=True)
    week_end_date = DateTimeField(required=True)
    earned_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'jackpot_free_coupons',
        'indexes': [('user_id', 'week_start_date'), ('slot_number', 'week_start_date')]
    }

class JackpotFund(Document):
    """Jackpot fund tracking"""
    fund_id = StringField(required=True, unique=True)
    week_start_date = DateTimeField(required=True)
    week_end_date = DateTimeField(required=True)
    
    # Fund sources
    entry_fees_total = DecimalField(default=Decimal('0.0'), precision=8)
    binary_contributions_total = DecimalField(default=Decimal('0.0'), precision=8)
    rollover_from_previous = DecimalField(default=Decimal('0.0'), precision=8)
    
    # Total fund
    total_fund = DecimalField(required=True, precision=8)
    
    # Pool allocations
    open_pool_allocation = DecimalField(required=True, precision=8)  # 50%
    top_promoters_pool_allocation = DecimalField(required=True, precision=8)  # 30%
    top_buyers_pool_allocation = DecimalField(required=True, precision=8)  # 10%
    new_joiners_pool_allocation = DecimalField(required=True, precision=8)  # 10%
    
    status = StringField(choices=['accumulating', 'ready_for_distribution', 'distributed'], default='accumulating')
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'jackpot_funds',
        'indexes': [('week_start_date', 'week_end_date'), 'fund_id']
    }