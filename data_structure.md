# BitGPT Backend Data Structure (FastAPI + MongoDB)

## Overview
This document defines the complete data structure for the BitGPT MLM platform backend, including Binary Tree, Dream Matrix, Global Matrix, and all bonus systems.

## Database Collections

### 1️⃣ Users Collection
**Purpose**: Core user information and wallet management

```json
{
  "_id": "ObjectId",
  "uid": "string (unique)",
  "refer_code": "string (unique)",
  "upline_id": "ObjectId (reference)",
  "wallet_address": "string (blockchain wallet)",
  "name": "string",
  "email": "string",
  "phone": "string",
  "status": "enum: active|inactive|blocked",
  "created_at": "DateTime",
  "updated_at": "DateTime"
}
```

### 2️⃣ UserWallets Collection
**Purpose**: Separate wallet balances for different purposes

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (reference Users)",
  "wallet_type": "enum: main|reserve|matrix|global",
  "balance": "Decimal",
  "currency": "string (default: USDT)",
  "last_updated": "DateTime"
}
```

### 3️⃣ SlotCatalog Collection
**Purpose**: Predefined slot information for all programs

```json
{
  "_id": "ObjectId",
  "slot_no": "integer (1-16)",
  "name": "string (Explorer, Contributor, etc.)",
  "price": "Decimal",
  "program": "enum: binary|matrix|global",
  "level": "integer",
  "is_active": "boolean",
  "created_at": "DateTime"
}
```

### 4️⃣ TreePlacement Collection
**Purpose**: Binary/Matrix tree structure and positioning

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (reference Users)",
  "program": "enum: binary|matrix|global",
  "parent_id": "ObjectId (reference Users)",
  "position": "enum: left|right|center",
  "level": "integer (tree level)",
  "slot_no": "integer (current slot)",
  "is_active": "boolean",
  "created_at": "DateTime",
  "updated_at": "DateTime"
}
```

### 5️⃣ SlotActivation Collection
**Purpose**: Track slot activations and upgrades

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (reference Users)",
  "program": "enum: binary|matrix|global",
  "slot_no": "integer",
  "activation_type": "enum: initial|upgrade|auto",
  "upgrade_source": "enum: wallet|reserve|mixed|auto",
  "amount_paid": "Decimal",
  "tx_hash": "string (blockchain transaction)",
  "status": "enum: pending|completed|failed",
  "activated_at": "DateTime",
  "created_at": "DateTime"
}
```

### 6️⃣ IncomeEvent Collection
**Purpose**: All income distributions and bonuses

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (receiver)",
  "source_user_id": "ObjectId (source of income)",
  "program": "enum: binary|matrix|global",
  "slot_no": "integer",
  "income_type": "enum: level_payout|partner_incentive|spark_bonus|royal_captain|president_reward|leadership_stipend|jackpot|mentorship|newcomer_support|triple_entry",
  "amount": "Decimal",
  "percentage": "Decimal (distribution percentage)",
  "tx_hash": "string",
  "status": "enum: pending|completed|failed",
  "created_at": "DateTime"
}
```

### 7️⃣ SpilloverEvent Collection
**Purpose**: Track spillover occurrences

```json
{
  "_id": "ObjectId",
  "from_user_id": "ObjectId (user who triggered spillover)",
  "to_user_id": "ObjectId (receiver or fund)",
  "program": "enum: binary|matrix|global",
  "slot_no": "integer",
  "amount": "Decimal",
  "spillover_type": "enum: upline_30_percent|leadership_stipend",
  "tx_hash": "string",
  "created_at": "DateTime"
}
```

### 8️⃣ ReserveLedger Collection
**Purpose**: Track reserve fund movements

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (reference Users)",
  "program": "enum: binary|matrix|global",
  "slot_no": "integer",
  "amount": "Decimal",
  "direction": "enum: credit|debit",
  "source": "enum: income|manual|transfer",
  "balance_after": "Decimal",
  "tx_hash": "string",
  "created_at": "DateTime"
}
```

### 9️⃣ WalletLedger Collection
**Purpose**: Track main wallet transactions

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (reference Users)",
  "amount": "Decimal",
  "currency": "string",
  "type": "enum: credit|debit",
  "reason": "string (description)",
  "balance_after": "Decimal",
  "tx_hash": "string",
  "created_at": "DateTime"
}
```

### 🔟 JackpotTicket Collection
**Purpose**: Track jackpot entries and free coupons

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (reference Users)",
  "week_id": "string (YYYY-WW format)",
  "count": "integer (number of tickets)",
  "source": "enum: free|paid",
  "free_source_slot": "integer (if free from slot activation)",
  "status": "enum: active|used|expired",
  "created_at": "DateTime"
}
```

### 1️⃣1️⃣ JackpotFund Collection
**Purpose**: Weekly jackpot pools and winners

```json
{
  "_id": "ObjectId",
  "week_id": "string (YYYY-WW format)",
  "total_pool": "Decimal",
  "open_winners_pool": "Decimal (50%)",
  "seller_pool": "Decimal (30%)",
  "buyer_pool": "Decimal (10%)",
  "newcomer_pool": "Decimal (10%)",
  "winners": {
    "open": ["ObjectId (10 users)"],
    "top_sellers": ["ObjectId (20 users)"],
    "top_buyers": ["ObjectId (20 users)"],
    "newcomers": ["ObjectId (10 users)"]
  },
  "status": "enum: active|settled|distributed",
  "settled_at": "DateTime",
  "created_at": "DateTime"
}
```

### 1️⃣2️⃣ SparkCycle Collection
**Purpose**: Track spark bonus cycles and distributions

```json
{
  "_id": "ObjectId",
  "cycle_no": "integer",
  "slot_no": "integer",
  "pool_amount": "Decimal",
  "participants": ["ObjectId (users in this slot)"],
  "distribution_percentage": "Decimal (15%, 10%, etc.)",
  "payout_per_participant": "Decimal",
  "status": "enum: active|completed",
  "payout_at": "DateTime",
  "created_at": "DateTime"
}
```

### 1️⃣3️⃣ GlobalPhaseState Collection
**Purpose**: Track global matrix phase progression

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (reference Users)",
  "phase": "enum: 1|2",
  "slot_index": "integer (current slot in phase)",
  "children": ["ObjectId (users under this position)"],
  "ready_for_next": "boolean",
  "phase_1_completed": "boolean",
  "phase_2_completed": "boolean",
  "last_updated": "DateTime",
  "created_at": "DateTime"
}
```

### 1️⃣4️⃣ Qualification Collection
**Purpose**: Track user qualifications for bonuses

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (reference Users)",
  "flags": {
    "royal_captain_ok": "boolean",
    "president_ok": "boolean",
    "ter_ok": "boolean",
    "leadership_ok": "boolean"
  },
  "counters": {
    "direct_partners": "integer",
    "global_team": "integer",
    "total_sales": "integer",
    "total_purchases": "integer"
  },
  "royal_captain_level": "integer (5, 10, 20, 30, 40, 50)",
  "president_level": "integer (30, 80, 150, 200, 250, 300, 400, 500, 600, 700, 1000, 1500, 2000, 2500, 3000, 4000)",
  "last_updated": "DateTime",
  "created_at": "DateTime"
}
```

### 1️⃣5️⃣ PartnerGraph Collection
**Purpose**: Track direct partner relationships

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (reference Users)",
  "directs": ["ObjectId (direct partners)"],
  "directs_count_by_program": {
    "binary": "integer",
    "matrix": "integer",
    "global": "integer"
  },
  "total_team": "integer",
  "last_updated": "DateTime",
  "created_at": "DateTime"
}
```

### 1️⃣6️⃣ AutoUpgradeLog Collection
**Purpose**: Track automatic slot upgrades

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (reference Users)",
  "program": "enum: binary|matrix|global",
  "from_slot": "integer",
  "to_slot": "integer",
  "upgrade_source": "enum: level_income|reserve|mixed",
  "triggered_by": "enum: first_two_people|middle_three|phase_completion",
  "amount_used": "Decimal",
  "tx_hash": "string",
  "status": "enum: pending|completed|failed",
  "created_at": "DateTime"
}
```

### 1️⃣7️⃣ LeadershipStipend Collection
**Purpose**: Track leadership stipend distributions

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId (reference Users)",
  "slot_no": "integer (10-16)",
  "target_amount": "Decimal (double slot value)",
  "current_amount": "Decimal",
  "is_active": "boolean",
  "started_at": "DateTime",
  "completed_at": "DateTime",
  "created_at": "DateTime"
}
```

### 1️⃣8️⃣ TripleEntryReward Collection
**Purpose**: Track TER fund distributions

```json
{
  "_id": "ObjectId",
  "cycle_no": "integer",
  "pool_amount": "Decimal",
  "eligible_users": ["ObjectId (users who joined all programs)"],
  "distribution_amount": "Decimal (per user)",
  "status": "enum: active|distributed",
  "distributed_at": "DateTime",
  "created_at": "DateTime"
}
```

### 1️⃣9️⃣ BlockchainEvent Collection
**Purpose**: Store blockchain events for idempotency

```json
{
  "_id": "ObjectId",
  "tx_hash": "string (unique)",
  "event_type": "enum: slot_activated|income_distributed|upgrade_triggered|spillover_occurred|jackpot_settled|spark_distributed",
  "event_data": "object (event-specific data)",
  "status": "enum: pending|processed|failed",
  "processed_at": "DateTime",
  "created_at": "DateTime"
}
```

### 2️⃣0️⃣ SystemConfig Collection
**Purpose**: Store system-wide configuration

```json
{
  "_id": "ObjectId",
  "config_key": "string",
  "config_value": "mixed",
  "description": "string",
  "is_active": "boolean",
  "updated_by": "ObjectId (admin user)",
  "updated_at": "DateTime",
  "created_at": "DateTime"
}
```

## Key Relationships

### Binary Tree Structure
- `Users.upline_id` → `Users._id`
- `TreePlacement.parent_id` → `Users._id`
- `TreePlacement.user_id` → `Users._id`

### Slot Management
- `SlotActivation.user_id` → `Users._id`
- `SlotActivation.slot_no` → `SlotCatalog.slot_no`

### Income Tracking
- `IncomeEvent.user_id` → `Users._id`
- `IncomeEvent.source_user_id` → `Users._id`
- `IncomeEvent.tx_hash` → `BlockchainEvent.tx_hash`

### Wallet Management
- `UserWallets.user_id` → `Users._id`
- `WalletLedger.user_id` → `Users._id`
- `ReserveLedger.user_id` → `Users._id`

## Indexes (Recommended)

```javascript
// Users Collection
db.users.createIndex({ "uid": 1 }, { unique: true })
db.users.createIndex({ "refer_code": 1 }, { unique: true })
db.users.createIndex({ "wallet_address": 1 }, { unique: true })

// TreePlacement Collection
db.treeplacement.createIndex({ "user_id": 1, "program": 1 })
db.treeplacement.createIndex({ "parent_id": 1, "program": 1 })

// SlotActivation Collection
db.slotactivation.createIndex({ "user_id": 1, "program": 1 })
db.slotactivation.createIndex({ "tx_hash": 1 }, { unique: true })

// IncomeEvent Collection
db.incomeevent.createIndex({ "user_id": 1, "created_at": -1 })
db.incomeevent.createIndex({ "tx_hash": 1 }, { unique: true })

// BlockchainEvent Collection
db.blockchainevent.createIndex({ "tx_hash": 1 }, { unique: true })
db.blockchainevent.createIndex({ "status": 1, "created_at": 1 })
```

## Data Validation Rules

### User Creation
- `uid` must be unique
- `refer_code` must be unique
- `wallet_address` must be unique
- `upline_id` must reference existing user

### Slot Activation
- User must have sufficient balance
- Slot must be available for upgrade
- Transaction hash must be unique

### Income Distribution
- All percentages must sum to 100%
- Amounts must be positive
- Transaction hash must be unique

### Tree Placement
- Binary: Only left/right positions allowed
- Matrix: 3-9-27 structure must be maintained
- Global: Phase progression must be sequential

## API Endpoints Structure

### Public APIs
- `GET /users/{uid}/summary` - User overview
- `GET /users/{uid}/tree` - Tree structure
- `GET /users/{uid}/incomes` - Income history
- `GET /jackpot/current` - Current jackpot status
- `GET /spark/cycles` - Spark bonus cycles
- `GET /leaderboards` - Various leaderboards

### Webhook APIs
- `POST /webhooks/blockchain` - Blockchain events
- `POST /webhooks/income` - Income distributions

### Admin APIs
- `POST /admin/rebuild-views` - Rebuild aggregations
- `GET /admin/health` - System health
- `POST /admin/config` - Update system config

This data structure supports all the complex MLM logic described in the BitGPT documentation while maintaining data integrity and performance.

## 🔥 **Binary Distribution (Total 100%)**
```
🌟 স্পার্ক বোনাস: 8% → SparkCycle collection
 রয়েল ক্যাপ্টেন: 4% → IncomeEvent collection
🌟 প্রেসিডেন্ট রিওয়ার্ড: 3% → IncomeEvent collection
🌟 শেয়ারহোল্ডার: 5% → IncomeEvent collection
 নিউকামার গ্রোথ সাপোর্ট: 20% → IncomeEvent collection
🌟 মেন্টরশিপ বোনাস: 10% → IncomeEvent collection
 পার্টনার ইনসেনটিভ: 10% → IncomeEvent collection
 লেভেল পেআউট: 40% → IncomeEvent collection (level_payout)
```

## 🌟 **Matrix Distribution (Total 100%)**
```
🌟 স্পার্ক বোনাস: 8% → SparkCycle collection
 রয়েল ক্যাপ্টেন: 4% → IncomeEvent collection  
🌟 প্রেসিডেন্ট রিওয়ার্ড: 3% → IncomeEvent collection
 লিডারশিপ stipend: 5% → LeadershipStipend collection
 জ্যাকপট এন্ট্রি: 5% → JackpotFund collection
 পার্টনার ইনসেনটিভ: 10% → IncomeEvent collection
 লেভেল পেআউট: 60% → IncomeEvent collection (level_payout)
🌟 শেয়ারহোল্ডার: 5% → IncomeEvent collection
```

## 💰 **ফান্ড ম্যানেজমেন্ট সিস্টেম**

আমি নতুন collection যোগ করব যাতে এই ফান্ডগুলো আলাদাভাবে track করা যায়:

```python:modules/user/model.py
class BonusFund(Document):
    """Track bonus funds for different types"""
    fund_type = StringField(choices=[
        'spark_bonus', 'royal_captain', 'president_reward', 
        'leadership_stipend', 'jackpot_entry', 'partner_incentive',
        'shareholders', 'newcomer_support', 'mentorship_bonus'
    ], required=True)
    program = StringField(choices=['binary', 'matrix', 'global'], required=True)
    total_collected = DecimalField(default=Decimal('0.00'), precision=8)
    total_distributed = DecimalField(default=Decimal('0.00'), precision=8)
    current_balance = DecimalField(default=Decimal('0.00'), precision=8)
    status = StringField(choices=['active', 'paused'], default='active')
    last_distribution = DateTimeField()
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'bonus_fund',
        'indexes': [
            ('fund_type', 'program'),
            'status'
        ]
    }

class FundDistribution(Document):
    """Track when and how funds are distributed"""
    fund_type = StringField(required=True)
    program = StringField(required=True)
    distribution_amount = DecimalField(required=True, precision=8)
    distribution_type = StringField(choices=['daily', 'weekly', 'monthly', 'on_demand'], required=True)
    beneficiaries_count = IntField(required=True)
    distribution_date = DateTimeField(required=True)
    status = StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    tx_hash = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'fund_distribution',
        'indexes': [
            ('fund_type', 'program'),
            'distribution_date',
            'status'
        ]
    }
```

## 🔄 **ফ্লো কীভাবে কাজ করবে:**

### **1. Income Collection Phase**
```python
# যখন slot activation হয়
def handle_slot_income(slot_amount, program):
    # Binary এর জন্য
    if program == 'binary':
        spark_fund = slot_amount * 0.08      # 8%
        royal_fund = slot_amount * 0.04      # 4%
        president_fund = slot_amount * 0.03  # 3%
        leadership_fund = slot_amount * 0.05 # 5%
        jackpot_fund = slot_amount * 0.05    # 5%
        partner_fund = slot_amount * 0.10    # 10%
        level_fund = slot_amount * 0.60      # 60%
        shareholder_fund = slot_amount * 0.05 # 5%
        
        # প্রতিটি ফান্ডে যোগ করুন
        add_to_bonus_fund('spark_bonus', program, spark_fund)
        add_to_bonus_fund('royal_captain', program, royal_fund)
        # ... বাকি সব
```

### **2. Fund Distribution Phase**
```python
# স্পার্ক বোনাস ডিস্ট্রিবিউশন (20 দিন পর)
def distribute_spark_bonus():
    spark_fund = get_bonus_fund('spark_bonus', 'matrix')
    
    # 20% TER ফান্ডে যায়
    ter_amount = spark_fund * 0.20
    add_to_ter_fund(ter_amount)
    
    # বাকি 80% 14টি slot এ ভাগ হয়
    remaining_amount = spark_fund * 0.80
    distribute_to_matrix_slots(remaining_amount)

# লিডারশিপ stipend ডিস্ট্রিবিউশন
def distribute_leadership_stipend():
    leadership_fund = get_bonus_fund('leadership_stipend', 'binary')
    
    # Slot 10-16 এর জন্য distribution
    distribute_leadership_rewards(leadership_fund)
```

## 📊 **Collection Structure Summary:**

| **Bonus Type** | **Collection** | **Purpose** |
|----------------|----------------|-------------|
| **Spark Bonus** | `SparkCycle` | Matrix slot-based distribution |
| **Royal Captain** | `IncomeEvent` | Direct user rewards |
| **President Reward** | `IncomeEvent` | Direct user rewards |
| **Leadership Stipend** | `LeadershipStipend` | Slot 10-16 rewards |
| **Jackpot Entry** | `JackpotFund` | Weekly lottery pools |
| **Partner Incentive** | `IncomeEvent` | Direct partner rewards |
| **Level Payout** | `IncomeEvent` | Tree level distribution |
| **Shareholders** | `IncomeEvent` | Shareholder rewards |
| **Newcomer Support** | `IncomeEvent` | Growth fund distribution |
| **Mentorship** | `IncomeEvent` | Mentor rewards |

## 🎯 **Key Benefits:**

1. **Separate Fund Tracking** - প্রতিটি বোনাস আলাদাভাবে track হয়
2. **Distribution Control** - কখন, কীভাবে distribute হবে তা control করা যায়
3. **Audit Trail** - সব transaction track করা যায়
4. **Flexible Distribution** - Daily, weekly, monthly বা on-demand distribution
5. **Real-time Balance** - প্রতিটি ফান্ডের current balance দেখা যায়

এই সিস্টেমে আপনার টাকা প্রথমে আলাদা ফান্ডে জমা হবে, তারপর নির্দিষ্ট সময়ে বা শর্তে distribute হবে। এতে করে fund management অনেক সহজ এবং transparent হবে।
