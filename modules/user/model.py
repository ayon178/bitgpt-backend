from mongoengine import Document, StringField, ObjectIdField, DateTimeField, BooleanField, DecimalField, IntField, ListField, DictField, EnumField
from datetime import datetime
from typing import Optional
from decimal import Decimal

class User(Document):
    """Core user model for BitGPT platform"""
    uid = StringField(required=True, unique=True)
    refer_code = StringField(required=True, unique=True)
    upline_id = ObjectIdField(required=True)
    wallet_address = StringField(required=True, unique=True)
    name = StringField(required=True)
    email = StringField(required=True)
    phone = StringField()
    status = StringField(choices=['active', 'inactive', 'blocked'], default='active')
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'users',
        'indexes': [
            'uid',
            'refer_code', 
            'wallet_address',
            'upline_id'
        ]
    }

class UserWallet(Document):
    """User wallet balances for different purposes"""
    user_id = ObjectIdField(required=True)
    wallet_type = StringField(choices=['main', 'reserve', 'matrix', 'global'], required=True)
    balance = DecimalField(default=Decimal('0.00'), precision=8)
    currency = StringField(default='USDT')
    last_updated = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'user_wallets',
        'indexes': [
            ('user_id', 'wallet_type')
        ]
    }

class SlotCatalog(Document):
    """Predefined slot information for all programs"""
    slot_no = IntField(required=True)
    name = StringField(required=True)
    price = DecimalField(required=True, precision=8)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    level = IntField(required=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'slot_catalog',
        'indexes': [
            ('program', 'slot_no'),
            'slot_no'
        ]
    }

class TreePlacement(Document):
    """Binary/Matrix tree structure and positioning"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    parent_id = ObjectIdField(required=True)
    position = StringField(choices=['left', 'right', 'center'])
    level = IntField(required=True)
    slot_no = IntField(required=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'tree_placement',
        'indexes': [
            ('user_id', 'program'),
            ('parent_id', 'program'),
            ('program', 'level')
        ]
    }

class SlotActivation(Document):
    """Track slot activations and upgrades"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    slot_no = IntField(required=True)
    activation_type = StringField(choices=['initial', 'upgrade', 'auto'], required=True)
    upgrade_source = StringField(choices=['wallet', 'reserve', 'mixed', 'auto'], required=True)
    amount_paid = DecimalField(required=True, precision=8)
    tx_hash = StringField(required=True, unique=True)
    status = StringField(choices=['pending', 'completed', 'failed'], default='pending')
    activated_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'slot_activation',
        'indexes': [
            ('user_id', 'program'),
            'tx_hash',
            ('program', 'slot_no')
        ]
    }

class IncomeEvent(Document):
    """All income distributions and bonuses"""
    user_id = ObjectIdField(required=True)
    source_user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    slot_no = IntField(required=True)
    income_type = StringField(choices=[
        'level_payout', 'partner_incentive', 'spark_bonus', 'royal_captain',
        'president_reward', 'leadership_stipend', 'jackpot', 'mentorship',
        'newcomer_support', 'triple_entry'
    ], required=True)
    amount = DecimalField(required=True, precision=8)
    percentage = DecimalField(required=True, precision=4)
    tx_hash = StringField(required=True)
    status = StringField(choices=['pending', 'completed', 'failed'], default='pending')
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'income_event',
        'indexes': [
            ('user_id', 'created_at'),
            'tx_hash',
            ('program', 'slot_no')
        ]
    }

class SpilloverEvent(Document):
    """Track spillover occurrences"""
    from_user_id = ObjectIdField(required=True)
    to_user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    slot_no = IntField(required=True)
    amount = DecimalField(required=True, precision=8)
    spillover_type = StringField(choices=['upline_30_percent', 'leadership_stipend'], required=True)
    tx_hash = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'spillover_event',
        'indexes': [
            ('from_user_id', 'program'),
            ('to_user_id', 'program'),
            'tx_hash'
        ]
    }

class ReserveLedger(Document):
    """Track reserve fund movements"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    slot_no = IntField(required=True)
    amount = DecimalField(required=True, precision=8)
    direction = StringField(choices=['credit', 'debit'], required=True)
    source = StringField(choices=['income', 'manual', 'transfer'], required=True)
    balance_after = DecimalField(required=True, precision=8)
    tx_hash = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'reserve_ledger',
        'indexes': [
            ('user_id', 'program'),
            'tx_hash',
            ('program', 'slot_no')
        ]
    }

class WalletLedger(Document):
    """Track main wallet transactions"""
    user_id = ObjectIdField(required=True)
    amount = DecimalField(required=True, precision=8)
    currency = StringField(default='USDT')
    type = StringField(choices=['credit', 'debit'], required=True)
    reason = StringField(required=True)
    balance_after = DecimalField(required=True, precision=8)
    tx_hash = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'wallet_ledger',
        'indexes': [
            ('user_id', 'created_at'),
            'tx_hash'
        ]
    }

class JackpotTicket(Document):
    """Track jackpot entries and free coupons"""
    user_id = ObjectIdField(required=True)
    week_id = StringField(required=True)  # YYYY-WW format
    count = IntField(required=True)
    source = StringField(choices=['free', 'paid'], required=True)
    free_source_slot = IntField()  # if free from slot activation
    status = StringField(choices=['active', 'used', 'expired'], default='active')
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'jackpot_ticket',
        'indexes': [
            ('user_id', 'week_id'),
            'week_id',
            'status'
        ]
    }

class JackpotFund(Document):
    """Weekly jackpot pools and winners"""
    week_id = StringField(required=True, unique=True)  # YYYY-WW format
    total_pool = DecimalField(required=True, precision=8)
    open_winners_pool = DecimalField(required=True, precision=8)  # 50%
    seller_pool = DecimalField(required=True, precision=8)  # 30%
    buyer_pool = DecimalField(required=True, precision=8)  # 10%
    newcomer_pool = DecimalField(required=True, precision=8)  # 10%
    winners = DictField(default={
        'open': [],
        'top_sellers': [],
        'top_buyers': [],
        'newcomers': []
    })
    status = StringField(choices=['active', 'settled', 'distributed'], default='active')
    settled_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'jackpot_fund',
        'indexes': [
            'week_id',
            'status'
        ]
    }

class SparkCycle(Document):
    """Track spark bonus cycles and distributions"""
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
        'indexes': [
            ('cycle_no', 'slot_no'),
            'status'
        ]
    }

class GlobalPhaseState(Document):
    """Track global matrix phase progression"""
    user_id = ObjectIdField(required=True)
    phase = IntField(choices=[1, 2], required=True)
    slot_index = IntField(required=True)
    children = ListField(ObjectIdField(), default=[])
    ready_for_next = BooleanField(default=False)
    phase_1_completed = BooleanField(default=False)
    phase_2_completed = BooleanField(default=False)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'global_phase_state',
        'indexes': [
            ('user_id', 'phase'),
            'phase',
            'ready_for_next'
        ]
    }

class Qualification(Document):
    """Track user qualifications for bonuses"""
    user_id = ObjectIdField(required=True, unique=True)
    flags = DictField(default={
        'royal_captain_ok': False,
        'president_ok': False,
        'ter_ok': False,
        'leadership_ok': False
    })
    counters = DictField(default={
        'direct_partners': 0,
        'global_team': 0,
        'total_sales': 0,
        'total_purchases': 0
    })
    royal_captain_level = IntField(choices=[5, 10, 20, 30, 40, 50])
    president_level = IntField(choices=[30, 80, 150, 200, 250, 300, 400, 500, 600, 700, 1000, 1500, 2000, 2500, 3000, 4000])
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'qualification',
        'indexes': [
            'user_id'
        ]
    }

class PartnerGraph(Document):
    """Track direct partner relationships"""
    user_id = ObjectIdField(required=True, unique=True)
    directs = ListField(ObjectIdField(), default=[])
    directs_count_by_program = DictField(default={
        'binary': 0,
        'matrix': 0,
        'global': 0
    })
    total_team = IntField(default=0)
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'partner_graph',
        'indexes': [
            'user_id'
        ]
    }

class AutoUpgradeLog(Document):
    """Track automatic slot upgrades"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    from_slot = IntField(required=True)
    to_slot = IntField(required=True)
    upgrade_source = StringField(choices=['level_income', 'reserve', 'mixed'], required=True)
    triggered_by = StringField(choices=['first_two_people', 'middle_three', 'phase_completion'], required=True)
    amount_used = DecimalField(required=True, precision=8)
    tx_hash = StringField(required=True)
    status = StringField(choices=['pending', 'completed', 'failed'], default='pending')
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'auto_upgrade_log',
        'indexes': [
            ('user_id', 'program'),
            'tx_hash'
        ]
    }

class LeadershipStipend(Document):
    """Track leadership stipend distributions"""
    user_id = ObjectIdField(required=True)
    slot_no = IntField(required=True)
    target_amount = DecimalField(required=True, precision=8)
    current_amount = DecimalField(required=True, precision=8)
    is_active = BooleanField(default=True)
    started_at = DateTimeField(required=True)
    completed_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'leadership_stipend',
        'indexes': [
            ('user_id', 'slot_no'),
            'is_active'
        ]
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
        'indexes': [
            'cycle_no',
            'status'
        ]
    }

class BlockchainEvent(Document):
    """Store blockchain events for idempotency"""
    tx_hash = StringField(required=True, unique=True)
    event_type = StringField(choices=[
        'slot_activated', 'income_distributed', 'upgrade_triggered',
        'spillover_occurred', 'jackpot_settled', 'spark_distributed'
    ], required=True)
    event_data = DictField(required=True)
    status = StringField(choices=['pending', 'processed', 'failed'], default='pending')
    processed_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'blockchain_event',
        'indexes': [
            'tx_hash',
            ('status', 'created_at')
        ]
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
        'indexes': [
            'config_key',
            'is_active'
        ]
    }
