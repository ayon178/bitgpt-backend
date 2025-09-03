# BitGPT Models Documentation
## সকল Model এর Key-এর উদ্দেশ্য এবং ব্যবহার (Examples সহ)

এই ডকুমেন্টে BitGPT প্রজেক্টের সকল module এর model গুলোর প্রতিটি key এর ব্যবহার, উদ্দেশ্য এবং practical examples বর্ণনা করা হয়েছে।

---

## 🔗 **Blockchain Module**

### **BlockchainEvent Model**
**উদ্দেশ্য**: ব্লকচেইন ইভেন্টগুলো track করা এবং duplicate processing এড়ানো

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `tx_hash` | StringField | ব্লকচেইন transaction এর unique hash - duplicate ইভেন্ট এড়াতে | `"0x1a2b3c4d5e6f..."` - এই hash দিয়ে same transaction দুইবার process হওয়া থেকে বাঁচায় |
| `event_type` | StringField | কি ধরনের ইভেন্ট (slot_activated, income_distributed ইত্যাদি) | `"slot_activated"` - জানায় যে একটি slot activate হয়েছে |
| `event_data` | DictField | ইভেন্ট সম্পর্কিত additional data store করতে | `{"user_id": "123", "slot_no": 5, "amount": 100}` - ইভেন্টের details |
| `status` | StringField | ইভেন্ট processing status track করতে | `"processed"` - ইভেন্ট successfully process হয়েছে |
| `processed_at` | DateTimeField | কখন ইভেন্ট process হয়েছে সেটা track করতে | `"2024-01-15 10:30:00"` - processing time |
| `created_at` | DateTimeField | ইভেন্ট কখন create হয়েছে সেটা জানতে | `"2024-01-15 10:25:00"` - ইভেন্ট detect হওয়ার time |

### **SystemConfig Model**
**উদ্দেশ্য**: সিস্টেমের global configuration manage করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `config_key` | StringField | Configuration এর unique identifier | `"spark_bonus_percentage"` - spark bonus এর percentage config |
| `config_value` | StringField | Configuration এর actual value | `"8"` - 8% spark bonus |
| `description` | StringField | Configuration এর বর্ণনা | `"Matrix program spark bonus percentage"` |
| `is_active` | BooleanField | Configuration টি active কিনা | `true` - এই config currently active |
| `updated_by` | ObjectIdField | কোন admin user এটা update করেছে | `ObjectId("507f1f77bcf86cd799439011")` - admin user ID |
| `updated_at` | DateTimeField | কখন last update হয়েছে | `"2024-01-15 14:20:00"` |
| `created_at` | DateTimeField | কখন create হয়েছে | `"2024-01-01 00:00:00"` |

---

## 🌍 **Global Module**

### **GlobalPhaseState Model**
**উদ্দেশ্য**: Global Matrix এর phase progression track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `user_id` | ObjectIdField | কোন user এর phase state এটা | `ObjectId("507f1f77bcf86cd799439011")` - specific user |
| `phase` | IntField | বর্তমানে কোন phase এ আছে (1 বা 2) | `1` - Phase 1 এ আছে |
| `slot_index` | IntField | Phase এর মধ্যে কোন slot position এ আছে | `3` - Phase 1 এর 3rd slot এ আছে |
| `children` | ListField | এই position এর নিচে কোন users আছে | `[ObjectId("123"), ObjectId("456")]` - 2 জন children |
| `ready_for_next` | BooleanField | পরবর্তী phase এর জন্য ready কিনা | `false` - এখনো Phase 2 এর জন্য ready না |
| `phase_1_completed` | BooleanField | Phase 1 complete হয়েছে কিনা | `true` - Phase 1 শেষ হয়েছে |
| `phase_2_completed` | BooleanField | Phase 2 complete হয়েছে কিনা | `false` - Phase 2 এখনো চলমান |
| `last_updated` | DateTimeField | শেষ কখন update হয়েছে | `"2024-01-15 12:45:00"` |
| `created_at` | DateTimeField | কখন create হয়েছে | `"2024-01-10 09:30:00"` |

---

## 🖼️ **Image Module**

### **ImageUploadRequest Model**
**উদ্দেশ্য**: Image upload এর জন্য request data validation

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `user_id` | Optional[str] | কোন user image upload করছে (optional) | `"USER123"` - user এর unique ID |
| `folder` | Optional[str] | কোন folder এ image save করতে হবে | `"profile_pics"` - profile picture folder |

---

## 💰 **Income Module**

### **IncomeEvent Model**
**উদ্দেশ্য**: সকল ধরনের income এবং bonus distribution track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `user_id` | ObjectIdField | কোন user income পাচ্ছে | `ObjectId("507f1f77bcf86cd799439011")` - income receiver |
| `source_user_id` | ObjectIdField | কোন user থেকে income আসছে | `ObjectId("507f1f77bcf86cd799439012")` - income source |
| `program` | StringField | কোন program থেকে income (binary/matrix/global) | `"matrix"` - Matrix program থেকে income |
| `slot_no` | IntField | কোন slot থেকে income | `5` - Slot 5 থেকে income |
| `income_type` | StringField | income এর ধরন (level_payout, royal_captain ইত্যাদি) | `"level_payout"` - Level income |
| `amount` | DecimalField | income এর amount | `25.50` - $25.50 income |
| `percentage` | DecimalField | income distribution এর percentage | `40.00` - 40% distribution |
| `tx_hash` | StringField | blockchain transaction hash | `"0x1a2b3c4d..."` - blockchain hash |
| `status` | StringField | payment status | `"completed"` - payment successful |
| `created_at` | DateTimeField | কখন income generate হয়েছে | `"2024-01-15 11:30:00"` |

### **SpilloverEvent Model**
**উদ্দেশ্য**: Spillover income track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `from_user_id` | ObjectIdField | কোন user spillover trigger করেছে | `ObjectId("507f1f77bcf86cd799439011")` - spillover trigger |
| `to_user_id` | ObjectIdField | কে spillover income পাচ্ছে | `ObjectId("507f1f77bcf86cd799439012")` - spillover receiver |
| `program` | StringField | কোন program এর spillover | `"binary"` - Binary program spillover |
| `slot_no` | IntField | কোন slot এর spillover | `12` - Slot 12 spillover |
| `amount` | DecimalField | spillover amount | `180.00` - $180 spillover |
| `spillover_type` | StringField | spillover এর ধরন | `"upline_30_percent"` - 30% upline spillover |
| `tx_hash` | StringField | transaction hash | `"0x9f8e7d6c..."` |
| `created_at` | DateTimeField | কখন spillover হয়েছে | `"2024-01-15 15:45:00"` |

### **LeadershipStipend Model**
**উদ্দেশ্য**: Leadership stipend (slot 10-16) track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `user_id` | ObjectIdField | কোন user leadership stipend পাচ্ছে | `ObjectId("507f1f77bcf86cd799439011")` - stipend receiver |
| `slot_no` | IntField | কোন slot এর stipend (10-16) | `12` - Slot 12 leadership stipend |
| `target_amount` | DecimalField | target amount (double slot value) | `1200.00` - $1200 target (double of slot 12) |
| `current_amount` | DecimalField | এখন পর্যন্ত কত collect হয়েছে | `850.00` - $850 collected so far |
| `is_active` | BooleanField | stipend active আছে কিনা | `true` - still collecting |
| `started_at` | DateTimeField | কখন শুরু হয়েছে | `"2024-01-10 08:00:00"` |
| `completed_at` | DateTimeField | কখন complete হয়েছে | `null` - not completed yet |
| `created_at` | DateTimeField | কখন create হয়েছে | `"2024-01-10 08:00:00"` |

### **BonusFund Model**
**উদ্দেশ্য**: বিভিন্ন ধরনের bonus fund আলাদাভাবে track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `fund_type` | StringField | কি ধরনের bonus fund | `"spark_bonus"` - Spark bonus fund |
| `program` | StringField | কোন program এর fund | `"matrix"` - Matrix program fund |
| `total_collected` | DecimalField | মোট কত collect হয়েছে | `15000.00` - $15k collected |
| `total_distributed` | DecimalField | মোট কত distribute হয়েছে | `12000.00` - $12k distributed |
| `current_balance` | DecimalField | বর্তমান balance | `3000.00` - $3k remaining |
| `status` | StringField | Fund status | `"active"` - fund is active |
| `last_distribution` | DateTimeField | শেষ কখন distribute হয়েছে | `"2024-01-14 20:00:00"` |
| `created_at` | DateTimeField | কখন fund create হয়েছে | `"2024-01-01 00:00:00"` |
| `updated_at` | DateTimeField | শেষ কখন update হয়েছে | `"2024-01-15 10:30:00"` |

### **FundDistribution Model**
**উদ্দেশ্য**: Fund distribution এর details track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `fund_type` | StringField | কোন fund distribute হচ্ছে | `"royal_captain"` - Royal captain fund |
| `program` | StringField | কোন program এর distribution | `"binary"` - Binary program |
| `distribution_amount` | DecimalField | কত amount distribute হয়েছে | `5000.00` - $5k distributed |
| `distribution_type` | StringField | কি ধরনের distribution | `"weekly"` - Weekly distribution |
| `beneficiaries_count` | IntField | কতজন পেয়েছে | `25` - 25 জন পেয়েছে |
| `distribution_date` | DateTimeField | কখন distribute হয়েছে | `"2024-01-15 12:00:00"` |
| `status` | StringField | Distribution status | `"completed"` - Successfully completed |
| `tx_hash` | StringField | Transaction hash | `"0x5a4b3c2d..."` - blockchain record |
| `created_at` | DateTimeField | কখন record create হয়েছে | `"2024-01-15 12:00:00"` |

---

## 🎰 **Jackpot Module**

### **JackpotTicket Model**
**উদ্দেশ্য**: User এর jackpot tickets track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `user_id` | ObjectIdField | কোন user এর ticket | `ObjectId("507f1f77bcf86cd799439011")` - ticket owner |
| `week_id` | StringField | কোন সপ্তাহের jackpot (YYYY-WW format) | `"2024-03"` - March 2024, Week 3 |
| `count` | IntField | কতগুলো ticket | `5` - 5টি jackpot ticket |
| `source` | StringField | ticket free পেয়েছে নাকি paid | `"free"` - Slot activation থেকে free ticket |
| `free_source_slot` | IntField | কোন slot থেকে free ticket পেয়েছে | `8` - Slot 8 activate করে free ticket পেয়েছে |
| `status` | StringField | ticket এর status | `"active"` - This week এর lottery তে participate করবে |
| `created_at` | DateTimeField | কখন ticket create হয়েছে | `"2024-01-15 09:00:00"` |

### **JackpotFund Model**
**উদ্দেশ্য**: সাপ্তাহিক jackpot pool এবং winners track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `week_id` | StringField | সপ্তাহের unique identifier | `"2024-03"` - March 2024, Week 3 |
| `total_pool` | DecimalField | মোট jackpot pool amount | `50000.00` - $50k total pool |
| `open_winners_pool` | DecimalField | Open winners এর জন্য pool (50%) | `25000.00` - $25k for open lottery |
| `seller_pool` | DecimalField | Top sellers এর জন্য pool (30%) | `15000.00` - $15k for top sellers |
| `buyer_pool` | DecimalField | Top buyers এর জন্য pool (10%) | `5000.00` - $5k for top buyers |
| `newcomer_pool` | DecimalField | Newcomers এর জন্য pool (10%) | `5000.00` - $5k for newcomers |
| `winners` | DictField | Different category তে winners এর list | `{"open": ["user1", "user2"], "top_sellers": [...]}` |
| `status` | StringField | Jackpot এর status | `"settled"` - Winners declared |
| `settled_at` | DateTimeField | কখন settle হয়েছে | `"2024-01-21 20:00:00"` - Week end এ settle |
| `created_at` | DateTimeField | কখন create হয়েছে | `"2024-01-15 00:00:00"` - Week start |

---

## 🏆 **Qualification Module**

### **Qualification Model**
**উদ্দেশ্য**: User এর bonus qualify করার জন্য conditions track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `user_id` | ObjectIdField | কোন user এর qualification | `ObjectId("507f1f77bcf86cd799439011")` - user এর qualification |
| `flags` | DictField | Different bonus এর জন্য qualification flags | `{"royal_captain_ok": true, "president_ok": false}` - Royal captain qualified |
| `counters` | DictField | Direct partners, team size ইত্যাদি count | `{"direct_partners": 15, "global_team": 150}` - 15 direct, 150 team |
| `royal_captain_level` | IntField | Royal Captain এর level (5,10,20...) | `10` - Level 10 Royal Captain |
| `president_level` | IntField | President এর level (30,80,150...) | `80` - Level 80 President |
| `last_updated` | DateTimeField | শেষ কখন update হয়েছে | `"2024-01-15 16:30:00"` |
| `created_at` | DateTimeField | কখন create হয়েছে | `"2024-01-01 10:00:00"` |

---

## 🎰 **Slot Module**

### **SlotCatalog Model**
**উদ্দেশ্য**: সকল program এর predefined slot information store করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `slot_no` | IntField | Slot number (1-16) | `5` - Slot number 5 |
| `name` | StringField | Slot এর name (Explorer, Contributor ইত্যাদি) | `"Contributor"` - Slot 5 এর name |
| `price` | DecimalField | Slot এর price | `100.00` - $100 to activate |
| `program` | StringField | কোন program এর slot | `"matrix"` - Matrix program slot |
| `level` | IntField | Slot এর level | `5` - Level 5 slot |
| `is_active` | BooleanField | Slot active আছে কিনা | `true` - Currently available |
| `created_at` | DateTimeField | কখন create হয়েছে | `"2024-01-01 00:00:00"` |

### **SlotActivation Model**
**উদ্দেশ্য**: User এর slot activation এবং upgrade track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `user_id` | ObjectIdField | কোন user slot activate করেছে | `ObjectId("507f1f77bcf86cd799439011")` - activator user |
| `program` | StringField | কোন program এর slot | `"binary"` - Binary program slot |
| `slot_no` | IntField | কোন slot activate হয়েছে | `8` - Slot 8 activated |
| `activation_type` | StringField | কি ধরনের activation (initial/upgrade/auto) | `"upgrade"` - Manual upgrade |
| `upgrade_source` | StringField | কোথা থেকে payment করেছে | `"wallet"` - Main wallet থেকে payment |
| `amount_paid` | DecimalField | কত amount pay করেছে | `300.00` - $300 paid |
| `tx_hash` | StringField | Blockchain transaction hash | `"0x7f6e5d4c..."` - blockchain record |
| `status` | StringField | Activation status | `"completed"` - Successfully activated |
| `activated_at` | DateTimeField | কখন activate হয়েছে | `"2024-01-15 14:30:00"` |
| `created_at` | DateTimeField | কখন record create হয়েছে | `"2024-01-15 14:30:00"` |

---

## ⚡ **Spark Module**

### **SparkCycle Model**
**উদ্দেশ্য**: Matrix program এর spark bonus distribution track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `cycle_no` | IntField | Spark cycle number | `15` - 15th spark cycle |
| `slot_no` | IntField | কোন slot এর spark bonus | `5` - Slot 5 spark bonus |
| `pool_amount` | DecimalField | Cycle এর মোট pool amount | `8000.00` - $8k pool for this cycle |
| `participants` | ListField | কারা participate করেছে | `[ObjectId("123"), ObjectId("456")]` - 2 participants |
| `distribution_percentage` | DecimalField | Distribution percentage | `15.00` - 15% distribution |
| `payout_per_participant` | DecimalField | প্রতি participant কত পাবে | `600.00` - $600 per participant |
| `status` | StringField | Cycle status | `"completed"` - Payout completed |
| `payout_at` | DateTimeField | কখন payout হবে | `"2024-01-20 20:00:00"` - 20 days later |
| `created_at` | DateTimeField | কখন cycle create হয়েছে | `"2024-01-01 08:00:00"` |

### **TripleEntryReward Model**
**উদ্দেশ্য**: TER (Triple Entry Reward) fund distribution track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `cycle_no` | IntField | TER cycle number | `3` - 3rd TER cycle |
| `pool_amount` | DecimalField | TER pool এর মোট amount | `25000.00` - $25k TER pool |
| `eligible_users` | ListField | কারা TER পাওয়ার eligible | `[ObjectId("123"), ObjectId("456")]` - Users who joined all 3 programs |
| `distribution_amount` | DecimalField | প্রতি user কত পাবে | `500.00` - $500 per eligible user |
| `status` | StringField | Distribution status | `"distributed"` - TER distributed |
| `distributed_at` | DateTimeField | কখন distribute হয়েছে | `"2024-01-31 18:00:00"` - Month end |
| `created_at` | DateTimeField | কখন create হয়েছে | `"2024-01-01 00:00:00"` |

---

## 🌳 **Tree Module**

### **TreePlacement Model**
**উদ্দেশ্য**: Binary/Matrix tree structure এবং positioning track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `user_id` | ObjectIdField | কোন user এর tree placement | `ObjectId("507f1f77bcf86cd799439011")` - tree member |
| `program` | StringField | কোন program এর tree | `"binary"` - Binary tree placement |
| `parent_id` | ObjectIdField | Tree তে parent কে | `ObjectId("507f1f77bcf86cd799439012")` - upline/sponsor |
| `position` | StringField | Parent এর কোন position এ (left/right/center) | `"left"` - Parent এর left side এ আছে |
| `level` | IntField | Tree এর কোন level এ | `3` - Level 3 position |
| `slot_no` | IntField | কোন slot এর tree | `7` - Slot 7 tree |
| `is_active` | BooleanField | Placement active আছে কিনা | `true` - Currently active position |
| `created_at` | DateTimeField | কখন placement হয়েছে | `"2024-01-15 13:45:00"` |
| `updated_at` | DateTimeField | শেষ কখন update হয়েছে | `"2024-01-15 13:45:00"` |

### **AutoUpgradeLog Model**
**উদ্দেশ্য**: Automatic slot upgrade track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `user_id` | ObjectIdField | কোন user এর auto upgrade | `ObjectId("507f1f77bcf86cd799439011")` - upgraded user |
| `program` | StringField | কোন program এর upgrade | `"matrix"` - Matrix auto upgrade |
| `from_slot` | IntField | কোন slot থেকে upgrade | `5` - From slot 5 |
| `to_slot` | IntField | কোন slot এ upgrade | `6` - To slot 6 |
| `upgrade_source` | StringField | কোথা থেকে fund এসেছে | `"level_income"` - Level income থেকে auto upgrade |
| `triggered_by` | StringField | কি কারণে trigger হয়েছে | `"first_two_people"` - First 2 people joined |
| `amount_used` | DecimalField | কত amount use হয়েছে | `150.00` - $150 used for upgrade |
| `tx_hash` | StringField | Transaction hash | `"0x3c2b1a9d..."` |
| `status` | StringField | Upgrade status | `"completed"` - Auto upgrade successful |
| `created_at` | DateTimeField | কখন upgrade হয়েছে | `"2024-01-15 16:00:00"` |

---

## 👤 **User Module**

### **User Model**
**উদ্দেশ্য**: Core user information store করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `uid` | StringField | User এর unique identifier | `"USER123456"` - System generated unique ID |
| `refer_code` | StringField | User এর unique referral code | `"REF789"` - Referral code for inviting others |
| `refered_by` | ObjectIdField | কোন user এর referral এ join করেছে | `ObjectId("507f1f77bcf86cd799439012")` - Sponsor/upline |
| `wallet_address` | StringField | User এর blockchain wallet address | `"0x742d35Cc6634C0532925a3b8D404e35b0C93D77E"` - USDT wallet |
| `name` | StringField | User এর নাম | `"John Doe"` - User's full name |
| `role` | StringField | User এর role (user/admin/shareholder) | `"user"` - Regular platform user |
| `status` | StringField | Account status (active/inactive/blocked) | `"active"` - Account is active |
| `created_at` | DateTimeField | কখন account create হয়েছে | `"2024-01-10 08:30:00"` |
| `updated_at` | DateTimeField | শেষ কখন update হয়েছে | `"2024-01-15 12:00:00"` |

### **PartnerGraph Model**
**উদ্দেশ্য**: Direct partner relationships track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `user_id` | ObjectIdField | কোন user এর partner graph | `ObjectId("507f1f77bcf86cd799439011")` - graph owner |
| `directs` | ListField | Direct partners এর list | `[ObjectId("123"), ObjectId("456")]` - 2 direct partners |
| `directs_count_by_program` | DictField | Program wise direct count | `{"binary": 5, "matrix": 3, "global": 2}` - Program-wise breakdown |
| `total_team` | IntField | মোট team size | `25` - Total 25 people in downline |
| `last_updated` | DateTimeField | শেষ কখন update হয়েছে | `"2024-01-15 17:00:00"` |
| `created_at` | DateTimeField | কখন create হয়েছে | `"2024-01-10 08:30:00"` |

---

## 💼 **Wallet Module**

### **UserWallet Model**
**উদ্দেশ্য**: User এর different type এর wallet balance track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `user_id` | ObjectIdField | কোন user এর wallet | `ObjectId("507f1f77bcf86cd799439011")` - wallet owner |
| `wallet_type` | StringField | Wallet এর type (main/reserve/matrix/global) | `"main"` - Main trading wallet |
| `balance` | DecimalField | Wallet এর current balance | `1500.50` - $1500.50 current balance |
| `currency` | StringField | Currency type (default: USDT) | `"USDT"` - Tether USD |
| `last_updated` | DateTimeField | শেষ কখন balance update হয়েছে | `"2024-01-15 18:30:00"` |

### **ReserveLedger Model**
**উদ্দেশ্য**: Reserve fund এর movement track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `user_id` | ObjectIdField | কোন user এর reserve fund | `ObjectId("507f1f77bcf86cd799439011")` - reserve owner |
| `program` | StringField | কোন program এর reserve | `"binary"` - Binary program reserve |
| `slot_no` | IntField | কোন slot এর reserve | `10` - Slot 10 reserve fund |
| `amount` | DecimalField | Transaction amount | `75.00` - $75 credited to reserve |
| `direction` | StringField | Credit নাকি debit | `"credit"` - Money added to reserve |
| `source` | StringField | কোথা থেকে এসেছে | `"income"` - Level income থেকে |
| `balance_after` | DecimalField | Transaction এর পর balance | `425.00` - $425 total reserve balance |
| `tx_hash` | StringField | Transaction hash | `"0x9e8d7c6b..."` |
| `created_at` | DateTimeField | কখন transaction হয়েছে | `"2024-01-15 19:00:00"` |

### **WalletLedger Model**
**উদ্দেশ্য**: Main wallet এর transactions track করা

| **Key** | **Type** | **উদ্দেশ্য** | **Example** |
|---------|----------|-------------|-------------|
| `user_id` | ObjectIdField | কোন user এর wallet transaction | `ObjectId("507f1f77bcf86cd799439011")` - transaction owner |
| `amount` | DecimalField | Transaction amount | `250.00` - $250 transaction |
| `currency` | StringField | Currency type | `"USDT"` - Tether USD |
| `type` | StringField | Credit নাকি debit | `"credit"` - Money received |
| `reason` | StringField | Transaction এর কারণ | `"Level income payout"` - Level bonus received |
| `balance_after` | DecimalField | Transaction এর পর balance | `1750.50` - $1750.50 new balance |
| `tx_hash` | StringField | Transaction hash | `"0x4f3e2d1c..."` |
| `created_at` | DateTimeField | কখন transaction হয়েছে | `"2024-01-15 19:15:00"` |

---

## 🔗 **Key Relationships Overview**

### **Core Relationships**
- **Users** ↔ **TreePlacement**: User এর tree position
- **Users** ↔ **SlotActivation**: User এর slot upgrades
- **Users** ↔ **IncomeEvent**: User এর সকল income
- **Users** ↔ **UserWallet**: User এর wallet balances
- **Users** ↔ **Qualification**: User এর bonus qualifications

### **Income Flow**
1. **SlotActivation** → **IncomeEvent** (slot activation থেকে income generate)
2. **IncomeEvent** → **WalletLedger** (income wallet এ add)
3. **IncomeEvent** → **ReserveLedger** (reserve fund এ add)

### **Tree Management**
1. **User.upline_id** → **TreePlacement.parent_id**
2. **TreePlacement** → **AutoUpgradeLog** (auto upgrade trigger)

### **Bonus Distribution**
1. **SparkCycle** → **IncomeEvent** (spark bonus distribution)
2. **JackpotFund** → **IncomeEvent** (jackpot prize distribution)
3. **TripleEntryReward** → **IncomeEvent** (TER distribution)

---

## 📝 **Summary**

এই documentation এ BitGPT platform এর সকল model এর প্রতিটি key এর উদ্দেশ্য এবং ব্যবহার বিস্তারিতভাবে বর্ণনা করা হয়েছে। প্রতিটি model একটি নির্দিষ্ট business logic serve করে এবং একসাথে মিলে একটি complete MLM platform তৈরি করে।

**মূল বৈশিষ্ট্য:**
- ✅ Complete audit trail of all transactions
- ✅ Separate fund management for different bonuses
- ✅ Tree structure management for MLM
- ✅ User qualification tracking
- ✅ Automated income distribution
- ✅ Blockchain integration support
