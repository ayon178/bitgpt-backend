from mongoengine import Document, StringField, ObjectIdField, IntField, DecimalField, DateTimeField, DictField
from datetime import datetime
from decimal import Decimal

class JackpotTicket(Document):
    """Track jackpot entries and free coupons
    Client requirement:
    - Include referrer (who invited the joining user) on jackpot entry
    - Remove count aggregation; one document per entry
    """
    user_id = ObjectIdField(required=True)            # Entrant
    referrer_user_id = ObjectIdField(required=True)   # Referrer who invited the entrant
    week_id = StringField(required=True)              # YYYY-WW format
    source = StringField(choices=['free', 'paid'], required=True)
    free_source_slot = IntField()                     # if free from slot activation
    status = StringField(choices=['active', 'used', 'expired'], default='active')
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'jackpot_ticket',
        'indexes': [
            ('user_id', 'week_id'),
            ('referrer_user_id', 'week_id'),
            'week_id',
            'status'
        ]
    }

class JackpotFund(Document):
    """Weekly lottery pools - Jackpot Entry 5%"""
    week_id = StringField(required=True, unique=True)  # YYYY-WW format
    total_pool = DecimalField(required=True, precision=8)
    open_winners_pool = DecimalField(required=True, precision=8)  # 50%
    seller_pool = DecimalField(required=True, precision=8)  # 30%
    buyer_pool = DecimalField(required=True, precision=8)  # 10%
    newcomer_pool = DecimalField(required=True, precision=8)  # 10%
    winners = DictField(default={
        'open': [], 'top_sellers': [], 'top_buyers': [], 'newcomers': []
    })
    status = StringField(choices=['active', 'settled', 'distributed'], default='active')
    settled_at = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'jackpot_fund',
        'indexes': ['week_id', 'status']
    }
