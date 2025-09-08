from mongoengine import Document, StringField, IntField, DecimalField, BooleanField, DateTimeField, ObjectIdField, FloatField, DictField, ListField
from datetime import datetime
from decimal import Decimal
from utils import ensure_currency_for_program

class SlotCatalog(Document):
    """Predefined slot information for all programs"""
    slot_no = IntField(required=True)
    name = StringField(required=True)
    price = DecimalField(required=True, precision=8)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    level = IntField(required=True)
    
    # Binary Program specific fields
    member_count = IntField()  # Required members for this slot
    upgrade_cost = DecimalField(precision=8)  # Cost to upgrade to next slot
    total_income = DecimalField(precision=8)  # Total income from this slot
    wallet_amount = DecimalField(precision=8)  # Wallet amount after upgrade
    
    # Global Program specific fields
    phase = StringField(choices=['PHASE-1', 'PHASE-2'])  # For Global program
    
    # Auto upgrade settings
    auto_upgrade_enabled = BooleanField(default=True)
    auto_upgrade_requirement = IntField(default=2)  # Partners needed for auto upgrade
    
    # Status
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'slot_catalog',
        'indexes': [
            ('program', 'slot_no'), 
            'slot_no',
            'program',
            'currency',
            'phase'
        ]
    }

class SlotActivation(Document):
    """Track slot activations and upgrades"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    slot_no = IntField(required=True)
    slot_name = StringField(required=True)
    activation_type = StringField(choices=['initial', 'upgrade', 'auto', 'manual'], required=True)
    upgrade_source = StringField(choices=['wallet', 'reserve', 'mixed', 'auto', 'commission'], required=True)
    amount_paid = DecimalField(required=True, precision=8)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    
    # Transaction details
    tx_hash = StringField(required=True, unique=True)
    blockchain_network = StringField(choices=['BSC', 'ETH', 'TRC20'], default='BSC')
    
    # Commission details
    commission_paid = DecimalField(precision=8, default=0)
    commission_percentage = FloatField(default=10.0)  # 10% commission
    
    # Auto upgrade details
    is_auto_upgrade = BooleanField(default=False)
    partners_contributed = ListField(ObjectIdField())  # Partners who contributed to auto upgrade
    earnings_used = DecimalField(precision=8, default=0)  # Earnings used for auto upgrade
    
    # Status and timing
    status = StringField(choices=['pending', 'completed', 'failed', 'refunded'], default='pending')
    activated_at = DateTimeField()
    completed_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    # Additional metadata
    metadata = DictField(default={})  # For storing additional information
    
    meta = {
        'collection': 'slot_activation',
        'indexes': [
            ('user_id', 'program'), 
            'tx_hash', 
            ('program', 'slot_no'),
            'status',
            'activation_type',
            'created_at'
        ]
    }

    def clean(self):
        # Ensure currency matches program default if not provided or mismatched
        self.currency = ensure_currency_for_program(self.program, self.currency)

class SlotUpgradeQueue(Document):
    """Queue for managing slot upgrades"""
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    current_slot_no = IntField(required=True)
    target_slot_no = IntField(required=True)
    upgrade_cost = DecimalField(required=True, precision=8)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    
    # Auto upgrade details
    is_auto_upgrade = BooleanField(default=False)
    partners_required = IntField(default=2)
    partners_available = IntField(default=0)
    earnings_available = DecimalField(precision=8, default=0)
    
    # Status
    status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    priority = IntField(default=1)  # Higher number = higher priority
    
    # Timing
    queued_at = DateTimeField(default=datetime.utcnow)
    processed_at = DateTimeField()
    completed_at = DateTimeField()
    
    meta = {
        'collection': 'slot_upgrade_queue',
        'indexes': [
            'user_id',
            'program',
            'status',
            'priority',
            'queued_at'
        ]
    }

class SlotCommission(Document):
    """Track commission distribution for slot upgrades"""
    slot_activation_id = ObjectIdField(required=True)
    user_id = ObjectIdField(required=True)  # User who gets commission
    from_user_id = ObjectIdField(required=True)  # User who generated commission
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    slot_no = IntField(required=True)
    
    # Commission details
    commission_amount = DecimalField(required=True, precision=8)
    currency = StringField(choices=['BNB', 'USDT', 'USD'], required=True)
    commission_type = StringField(choices=['joining', 'upgrade', 'level'], required=True)
    commission_percentage = FloatField(required=True)
    
    # Level information
    level = IntField()  # Which level this commission is for
    is_direct_commission = BooleanField(default=False)  # Direct upline commission
    
    # Status
    status = StringField(choices=['pending', 'paid', 'missed'], default='pending')
    paid_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'slot_commission',
        'indexes': [
            'user_id',
            'from_user_id',
            'program',
            'slot_no',
            'status',
            'created_at'
        ]
    }
