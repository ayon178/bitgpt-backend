from mongoengine import Document, StringField, ObjectIdField, DateTimeField, BooleanField, IntField, ListField, DictField, FloatField, EmbeddedDocumentField, EmbeddedDocument
from datetime import datetime

class BinarySlotInfo(EmbeddedDocument):
    """Binary slot information"""
    slot_name = StringField(required=True)  # EXPLORER, CONTRIBUTOR, etc.
    slot_value = FloatField(required=True)  # BNB value
    level = IntField(required=True)
    is_active = BooleanField(default=False)
    activated_at = DateTimeField()
    upgrade_cost = FloatField(default=0.0)
    total_income = FloatField(default=0.0)
    wallet_amount = FloatField(default=0.0)

class MatrixSlotInfo(EmbeddedDocument):
    """Matrix slot information"""
    slot_name = StringField(required=True)  # STARTER, BRONZE, etc.
    slot_value = FloatField(required=True)  # USDT value
    level = IntField(required=True)
    is_active = BooleanField(default=False)
    activated_at = DateTimeField()
    upgrade_cost = FloatField(default=0.0)
    total_income = FloatField(default=0.0)
    wallet_amount = FloatField(default=0.0)

class GlobalSlotInfo(EmbeddedDocument):
    """Global slot information"""
    slot_name = StringField(required=True)  # FOUNDATION, APEX, etc.
    slot_value = FloatField(required=True)  # USD value
    level = IntField(required=True)
    phase = StringField(choices=['PHASE-1', 'PHASE-2'], required=True)
    is_active = BooleanField(default=False)
    activated_at = DateTimeField()
    upgrade_cost = FloatField(default=0.0)
    total_income = FloatField(default=0.0)
    wallet_amount = FloatField(default=0.0)

class User(Document):
    """Core user model for BitGPT platform"""
    uid = StringField(required=True, unique=True)
    refer_code = StringField(required=True, unique=True)
    refered_by = ObjectIdField(required=False)
    wallet_address = StringField(required=True, unique=True)
    name = StringField(required=True)
    role = StringField(choices=['user', 'admin', 'shareholder'], default='user')
    email = StringField(required=False)
    password = StringField(required=False)
    status = StringField(choices=['active', 'inactive', 'blocked'], default='active')
    
    # Rank System (15 special ranks from Bitron to Omega)
    current_rank = StringField(choices=[
        'Bitron', 'Cryzen', 'Neura', 'Glint', 'Stellar',
        'Ignis', 'Quanta', 'Lumix', 'Arion', 'Nexus',
        'Fyre', 'Axion', 'Trion', 'Spectra', 'Omega'
    ], default='Bitron')
    
    # Activation Status
    is_activated = BooleanField(default=False)
    activation_date = DateTimeField()
    partners_required = IntField(default=2)  # 2 partners needed for activation
    partners_count = IntField(default=0)
    
    # Program Participation Status (Mandatory Join Sequence: Binary → Matrix → Global)
    binary_joined = BooleanField(default=False)
    matrix_joined = BooleanField(default=False)
    global_joined = BooleanField(default=False)
    
    # Program Join Timestamps (for sequence tracking)
    binary_joined_at = DateTimeField()
    matrix_joined_at = DateTimeField()
    global_joined_at = DateTimeField()
    
    # Binary Program Information
    binary_slots = ListField(EmbeddedDocumentField(BinarySlotInfo), default=[])
    binary_total_earnings = FloatField(default=0.0)
    binary_total_spent = FloatField(default=0.0)
    
    # Matrix Program Information
    matrix_slots = ListField(EmbeddedDocumentField(MatrixSlotInfo), default=[])
    matrix_total_earnings = FloatField(default=0.0)
    matrix_total_spent = FloatField(default=0.0)
    
    # Global Program Information
    global_slots = ListField(EmbeddedDocumentField(GlobalSlotInfo), default=[])
    global_total_earnings = FloatField(default=0.0)
    global_total_spent = FloatField(default=0.0)
    
    # Commission and Earning Tracking
    total_commissions_earned = FloatField(default=0.0)
    total_commissions_paid = FloatField(default=0.0)
    missed_profits = FloatField(default=0.0)
    
    # Special Program Participation
    royal_captain_qualifications = IntField(default=0)  # Number of Matrix+Global referrals
    president_reward_qualifications = IntField(default=0)  # Direct invitations count
    leadership_stipend_eligible = BooleanField(default=False)
    
    # Auto Upgrade Status
    binary_auto_upgrade_enabled = BooleanField(default=True)
    matrix_auto_upgrade_enabled = BooleanField(default=True)
    global_auto_upgrade_enabled = BooleanField(default=True)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'users',
        'indexes': [
            'uid',
            'refer_code', 
            'wallet_address',
            'refered_by',
            'role',
            'current_rank',
            'is_activated',
            'binary_joined',
            'matrix_joined',
            'global_joined'
        ]
    }

class Shareholder(Document):
    """Shareholder information for users with shareholder role"""
    user_id = ObjectIdField(required=True, unique=True)
    share_percentage = FloatField(required=True)  # Percentage of total shares
    total_shares = FloatField(required=True)  # Total number of shares owned
    status = StringField(choices=['active', 'inactive', 'suspended'], default='active')
    
    # Shareholder details
    joined_at = DateTimeField(default=datetime.utcnow)
    last_distribution_at = DateTimeField()
    total_distributions_received = FloatField(default=0.0)
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'shareholders',
        'indexes': [
            'user_id',
            'status',
            'share_percentage'
        ]
    }

class ShareholdersFund(Document):
    """Track shareholders fund pool"""
    total_contributed = FloatField(default=0.0)
    total_distributed = FloatField(default=0.0)
    available_amount = FloatField(default=0.0)
    
    # Fund details
    last_updated = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'shareholders_fund',
        'indexes': [
            'last_updated'
        ]
    }

class ShareholdersDistribution(Document):
    """Track individual shareholder distributions"""
    shareholder_id = ObjectIdField(required=True)
    user_id = ObjectIdField(required=True)
    transaction_amount = FloatField(required=True)
    shareholders_contribution = FloatField(required=True)
    share_percentage = FloatField(required=True)
    distribution_amount = FloatField(required=True)
    currency = StringField(choices=['USD', 'USDT', 'BNB'], default='USD')
    transaction_type = StringField(choices=['global_transaction', 'binary_transaction', 'matrix_transaction'], default='global_transaction')
    
    # Status
    status = StringField(choices=['pending', 'completed', 'failed'], default='pending')
    completed_at = DateTimeField()
    failed_at = DateTimeField()
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'shareholders_distributions',
        'indexes': [
            'shareholder_id',
            'user_id',
            'status',
            'created_at'
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

class EarningHistory(Document):
    """Track all earning activities"""
    user_id = ObjectIdField(required=True)
    earning_type = StringField(choices=[
        'binary_slot', 'matrix_slot', 'global_slot', 'commission',
        'royal_captain', 'president_reward', 'leadership_stipend',
        'spark_bonus', 'mentorship', 'auto_upgrade'
    ], required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    amount = FloatField(required=True)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    slot_name = StringField()
    slot_level = IntField()
    description = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'earning_history',
        'indexes': [
            'user_id',
            'earning_type',
            'program',
            'created_at'
        ]
    }

## Note: AutoUpgradeLog is centralized in modules/auto_upgrade/model.py
