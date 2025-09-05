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
    refered_by = ObjectIdField(required=True)
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
    
    # Program Participation Status
    binary_joined = BooleanField(default=False)
    matrix_joined = BooleanField(default=False)
    global_joined = BooleanField(default=False)
    
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

class Commission(Document):
    """Track commission transactions"""
    user_id = ObjectIdField(required=True)
    commission_type = StringField(choices=[
        'joining', 'upgrade', 'binary_partner', 'matrix_partner', 
        'global_partner', 'royal_captain', 'president_reward',
        'leadership_stipend', 'spark_bonus', 'mentorship', 'missed_profit'
    ], required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    amount = FloatField(required=True)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    from_user_id = ObjectIdField()  # Who generated this commission
    slot_level = IntField()  # Which slot level generated this
    status = StringField(choices=['pending', 'paid', 'missed'], default='pending')
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'commissions',
        'indexes': [
            'user_id',
            'commission_type',
            'program',
            'status',
            'created_at'
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

class AutoUpgradeLog(Document):
    """Track auto upgrade activities"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    from_slot = StringField(required=True)
    to_slot = StringField(required=True)
    upgrade_cost = FloatField(required=True)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    earnings_used = FloatField(required=True)
    partners_contributed = ListField(ObjectIdField())
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'auto_upgrade_log',
        'indexes': [
            'user_id',
            'program',
            'created_at'
        ]
    }
