# BitGPT User API Documentation (বাংলা)

## সারসংক্ষেপ
BitGPT MLM প্ল্যাটফর্মের জন্য সম্পূর্ণ API ডকুমেন্টেশন। এই ডকুমেন্টেশনে সব ধরনের API endpoint, field details এবং user join করার সময় automatic data creation সম্পর্কে বিস্তারিত তথ্য রয়েছে।

## Base URL
```
http://localhost:8000
```

## Authentication (প্রমাণীকরণ)
সব API endpoint এ Bearer token প্রয়োজন:
```
Authorization: Bearer <your_access_token>
```

---

## 1. Authentication APIs (প্রমাণীকরণ API)

### 1.1 User Login (ব্যবহারকারী লগইন)
**POST** `/auth/login`

**Request Body:**
```json
{
  "wallet_address": "0xABCDEF0123456789",
  "email": "user@example.com",
  "password": "password123"
}
```

**Field Details:**
- `wallet_address` (string, optional): Blockchain wallet address
- `email` (string, optional): Email address (admin/shareholder এর জন্য)
- `password` (string, optional): Password (admin/shareholder এর জন্য)

**Response:**
```json
{
  "status": "Ok",
  "status_code": 200,
  "message": "Login successful",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer"
  }
}
```

### 1.2 Verify Authentication (প্রমাণীকরণ যাচাই)
**GET** `/auth/verify_authentication`

**Response:**
```json
{
  "uid": "user123",
  "user_id": "507f1f77bcf86cd799439011",
  "role": "user",
  "name": "John Doe"
}
```

---

## 2. User Management APIs (ব্যবহারকারী ব্যবস্থাপনা API)

### 2.1 Create User (ব্যবহারকারী তৈরি)
**POST** `/user/create`

**Request Body:**
```json
{
  "uid": "user123",
  "refer_code": "RC12345",
  "upline_id": "66f1aab2c1f3a2a9c0b4e123",
  "wallet_address": "0xABCDEF0123456789",
  "name": "John Doe",
  "role": "user",
  "email": "john@example.com",
  "password": "secret123",
  "binary_payment_tx": "0x1234567890abcdef",
  "matrix_payment_tx": "0xabcdef1234567890",
  "global_payment_tx": "0x9876543210fedcba",
  "network": "BSC"
}
```

**Field Details:**
- `uid` (string, required): Unique user identifier
- `refer_code` (string, required): Unique referral code
- `upline_id` (string, required): Referrer/upline এর MongoDB ObjectId
- `wallet_address` (string, required): Unique blockchain wallet address
- `name` (string, required): User এর full name
- `role` (string, optional): user | admin | shareholder (default: user)
- `email` (string, optional): Email address
- `password` (string, optional): Password (admin/shareholder এর জন্য)
- `binary_payment_tx` (string, optional): Binary join এর blockchain transaction hash
- `matrix_payment_tx` (string, optional): Matrix join এর blockchain transaction hash
- `global_payment_tx` (string, optional): Global join এর blockchain transaction hash
- `network` (string, optional): Blockchain network (BSC, ETH, TESTNET)

**Response:**
```json
{
  "status": "Ok",
  "status_code": 201,
  "message": "User created successfully",
  "data": {
    "_id": "507f1f77bcf86cd799439011",
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer"
  }
}
```

### 2.2 Create Root User (রুট ব্যবহারকারী তৈরি)
**POST** `/user/create-root`

**Request Body:**
```json
{
  "uid": "ROOT",
  "refer_code": "ROOT001",
  "wallet_address": "0xROOT123456789",
  "name": "Root User",
  "role": "admin",
  "email": "root@bitgpt.com",
  "password": "rootpassword"
}
```

---

## 3. Tree Management APIs (ট্রি ব্যবস্থাপনা API)

### 3.1 Get Binary Tree Data (বাইনারি ট্রি ডেটা)
**GET** `/tree/{user_id}/binary`

**Response:**
```json
{
  "success": true,
  "message": "Tree data retrieved successfully",
  "data": [
    {
      "id": 1,
      "price": 0.0022,
      "userId": "507f1f77bcf86cd799439011",
      "recycle": 0,
      "isCompleted": false,
      "isProcess": false,
      "isAutoUpgrade": true,
      "isManualUpgrade": false,
      "processPercent": 42,
      "users": [
        {
          "id": 1,
          "type": "self",
          "userId": "507f1f77bcf86cd799439011"
        },
        {
          "id": 2,
          "type": "downLine",
          "userId": "507f1f77bcf86cd799439012"
        }
      ]
    }
  ]
}
```

### 3.2 Get Matrix Tree Data (ম্যাট্রিক্স ট্রি ডেটা)
**GET** `/tree/{user_id}/matrix`

### 3.3 Get Global Tree Data (গ্লোবাল ট্রি ডেটা)
**GET** `/tree/{user_id}/global`

### 3.4 Get All Tree Data (সব ট্রি ডেটা)
**GET** `/tree/{user_id}/all`

### 3.5 Get Matrix Recycle Tree (ম্যাট্রিক্স রিসাইকেল ট্রি)
**GET** `/matrix/recycle-tree?user_id={uid}&slot={1-15}&recycle_no={n|current}`

**Parameters:**
- `user_id` (string, required): User ID
- `slot` (integer, required): Slot number (1-15)
- `recycle_no` (integer|string, required): Recycle number or "current"

**Response:**
```json
{
  "user_id": "507f1f77bcf86cd799439011",
  "slot_number": 1,
  "recycle_no": 2,
  "is_snapshot": true,
  "is_complete": true,
  "total_recycles": 3,
  "nodes": [
    { "level": 1, "position": 0, "user_id": "507f1f77bcf86cd799439012" },
    { "level": 1, "position": 1, "user_id": "507f1f77bcf86cd799439013" },
    { "level": 1, "position": 2, "user_id": "507f1f77bcf86cd799439014" },
    { "level": 2, "position": 0, "user_id": "507f1f77bcf86cd799439015" }
  ]
}
```

### 3.6 Get Matrix Recycle History (ম্যাট্রিক্স রিসাইকেল ইতিহাস)
**GET** `/matrix/recycles?user_id={uid}&slot={1-15}`

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "recycle_no": 1,
      "is_complete": true,
      "created_at": "2024-01-10T08:00:00Z",
      "completed_at": "2024-01-15T12:00:00Z"
    },
    {
      "recycle_no": 2,
      "is_complete": true,
      "created_at": "2024-01-15T12:00:00Z",
      "completed_at": "2024-01-20T16:00:00Z"
    }
  ]
}
```

---

## 4. User Data Structure (ব্যবহারকারী ডেটা স্ট্রাকচার)

### User Model Fields:
```json
{
  "uid": "string",                    // Unique identifier
  "refer_code": "string",             // Referral code
  "refered_by": "ObjectId",           // Referrer ID
  "wallet_address": "string",         // Blockchain wallet
  "name": "string",                   // Full name
  "role": "string",                    // user | admin | shareholder
  "email": "string",                   // Email address
  "password": "string",                // Hashed password
  "status": "string",                  // active | inactive | blocked
  
  // Rank System (15 ranks)
  "current_rank": "string",            // Bitron to Omega
  
  // Activation Status
  "is_activated": "boolean",          // Activation status
  "activation_date": "datetime",       // When activated
  "partners_required": "number",       // Partners needed (default: 2)
  "partners_count": "number",          // Current partner count
  
  // Program Participation
  "binary_joined": "boolean",          // Binary program status
  "matrix_joined": "boolean",          // Matrix program status
  "global_joined": "boolean",          // Global program status
  
  // Binary Program Info
  "binary_slots": "array",            // Binary slot information
  "binary_total_earnings": "number",   // Total binary earnings
  "binary_total_spent": "number",     // Total binary spent
  
  // Matrix Program Info
  "matrix_slots": "array",             // Matrix slot information
  "matrix_total_earnings": "number",  // Total matrix earnings
  "matrix_total_spent": "number",     // Total matrix spent
  
  // Global Program Info
  "global_slots": "array",             // Global slot information
  "global_total_earnings": "number",   // Total global earnings
  "global_total_spent": "number",     // Total global spent
  
  // Commission Tracking
  "total_commissions_earned": "number", // Total commissions earned
  "total_commissions_paid": "number",   // Total commissions paid
  "missed_profits": "number",           // Missed profits amount
  
  // Special Programs
  "royal_captain_qualifications": "number",    // Royal Captain qualifications
  "president_reward_qualifications": "number", // President Reward qualifications
  "leadership_stipend_eligible": "boolean",     // Leadership stipend eligibility
  
  // Auto Upgrade Status
  "binary_auto_upgrade_enabled": "boolean",    // Binary auto upgrade
  "matrix_auto_upgrade_enabled": "boolean",    // Matrix auto upgrade
  "global_auto_upgrade_enabled": "boolean",    // Global auto upgrade
  
  // Timestamps
  "created_at": "datetime",            // Creation time
  "updated_at": "datetime"             // Last update time
}
```

---

## 5. User Join এর সময় Automatic Data Creation (স্বয়ংক্রিয় ডেটা তৈরি)

### 5.1 User Creation Process:
যখন একজন নতুন user join করে, তখন automatically এই সব কাজ হয়:

#### A. Core User Creation:
- User record তৈরি হয়
- Referrer linkage সেট হয়
- Activation status initialize হয় (inactive until 2 partners)
- Partner count = 0 সেট হয়
- Rank initialize হয় (default: Bitron)

#### B. Binary Program (সবসময়):
1. **Automatic Slot Activation:**
   - Slot-1: EXPLORER (0.0022 BNB) - automatically activate
   - Slot-2: CONTRIBUTOR (0.0044 BNB) - automatically activate

2. **Tree Placement:**
   - User কে Binary Tree তে place করা হয়
   - Referrer এর under এ direct placement attempt
   - যদি referrer এর position full হয়, তাহলে spillover logic use করে

3. **Commission Distribution:**
   - Joining commission: 10% of total (0.0066 BNB) referrer কে দেওয়া হয়
   - Upgrade commission: 30% matching level upline কে দেওয়া হয়

4. **Auto-Upgrade System:**
   - BinaryAutoUpgrade tracking initialize হয়
   - First 2 partners এর earnings track করা হয়
   - যখন 2 direct partners আসবে, তখন auto upgrade হবে

#### C. Matrix Program (যদি Matrix join করা হয়):
1. **Matrix Tree Placement:**
   - User কে Matrix tree তে place করা হয়
   - 3×3 structure maintain করা হয়

2. **Slot Activation:**
   - Matrix Slot-1 (STARTER) automatically activate হয়
   - Price: $11 USDT

3. **Commission:**
   - Joining commission: 10% of $11 referrer কে দেওয়া হয়
   - Mentorship bonus: Super upline কে 10% দেওয়া হয়

4. **Auto-Upgrade System:**
   - MatrixAutoUpgrade tracking initialize হয়
   - Middle 3 members এর earnings track করা হয়

#### D. Global Program (যদি Global join করা হয়):
1. **Global Tree Placement:**
   - User কে Phase-1, Slot-1 এ place করা হয়
   - Price: $33 USD

2. **Commission:**
   - Joining commission: 10% of $33 referrer কে দেওয়া হয়

3. **Phase Progression:**
   - GlobalPhaseProgression tracking initialize হয়
   - Phase-1: 4 members required
   - Phase-2: 8 members required

### 5.2 Additional Automatic Actions:

#### A. Partner Graph Update:
- Referrer এর PartnerGraph এ নতুন user add হয়
- Directs count update হয়
- Program-wise count update হয়

#### B. Commission Ledger:
- Joining commission entries তৈরি হয়
- Upgrade commission entries তৈরি হয়
- Commission status track করা হয়

#### C. Earning History:
- Slot activation এর earning history record হয়
- Commission earning history record হয়

#### D. Blockchain Events:
- Payment transaction hash store হয়
- Slot activation events record হয়

#### E. Special Programs:
- NewcomerSupport record তৈরি হয়
- Royal Captain qualifications count হয়
- President Reward qualifications count হয়

#### F. Rank System:
- User rank initialize হয়
- Rank update triggers সেট হয়

#### G. Auto-Upgrade Tracking:
- BinaryAutoUpgrade record তৈরি হয়
- MatrixAutoUpgrade record তৈরি হয় (যদি matrix join করে)
- GlobalPhaseProgression record তৈরি হয় (যদি global join করে)

---

## 6. Slot Information (স্লট তথ্য)

### 6.1 Binary Slots (বাইনারি স্লট):
```
Slot 1:  EXPLORER     - 0.0022 BNB
Slot 2:  CONTRIBUTOR  - 0.0044 BNB
Slot 3:  SUBSCRIBER   - 0.0088 BNB
Slot 4:  DREAMER      - 0.0176 BNB
Slot 5:  PLANNER      - 0.0352 BNB
Slot 6:  CHALLENGER   - 0.0704 BNB
Slot 7:  ADVENTURER   - 0.1408 BNB
Slot 8:  GAME-SHIFTER - 0.2816 BNB
Slot 9:  ORGANIGER    - 0.5632 BNB
Slot 10: LEADER       - 1.1264 BNB
Slot 11: VANGURD      - 2.2528 BNB
Slot 12: CENTER       - 4.5056 BNB
Slot 13: CLIMAX       - 9.0112 BNB
Slot 14: ENTERNTY     - 18.0224 BNB
Slot 15: KING         - 36.0448 BNB
Slot 16: COMMENDER    - 72.0896 BNB
```

### 6.2 Matrix Slots (ম্যাট্রিক্স স্লট):
```
Slot 1:  STARTER   - $11 USDT
Slot 2:  BRONZE    - $33 USDT
Slot 3:  SILVER    - $99 USDT
Slot 4:  GOLD      - $297 USDT
Slot 5:  PLATINUM  - $891 USDT
Slot 6:  DIAMOND   - $2,673 USDT
Slot 7:  RUBY      - $8,019 USDT
Slot 8:  EMERALD   - $24,057 USDT
Slot 9:  SAPPHIRE  - $72,171 USDT
Slot 10: TOPAZ     - $216,513 USDT
Slot 11: PEARL     - $649,539 USDT
Slot 12: AMETHYST  - $1,948,617 USDT
Slot 13: OBSIDIAN  - $5,845,851 USDT
Slot 14: TITANIUM  - $17,537,553 USDT
Slot 15: STAR      - $52,612,659 USDT
```

### 6.3 Global Slots (গ্লোবাল স্লট):
```
Phase-1 Slots:
Slot 1:  FOUNDATION - $30 USD
Slot 3:  SUMMIT     - $86 USD
Slot 5:  HORIZON    - $247 USD
Slot 7:  CATALYST   - $711 USD
Slot 9:  PINNACLE   - $2,047 USD
Slot 11: MOMENTUM   - $5,897 USD
Slot 13: VERTEX     - $16,984 USD
Slot 15: ASCEND     - $48,796 USD

Phase-2 Slots:
Slot 2:  APEX       - $36 USD
Slot 4:  RADIANCE   - $103 USD
Slot 6:  PARADIGM   - $296 USD
Slot 8:  ODYSSEY    - $853 USD
Slot 10: PRIME      - $2,457 USD
Slot 12: CREST      - $7,076 USD
Slot 14: LEGACY     - $20,381 USD
Slot 16: EVEREST    - $58,555 USD
```

---

## 7. Rank System (র্যাঙ্ক সিস্টেম)

### 7.1 15 Special Ranks:
```
1. Bitron    - Base rank
2. Cryzen    - First upgrade
3. Neura     - Second upgrade
4. Glint     - Third upgrade
5. Stellar   - Fourth upgrade
6. Ignis     - Fifth upgrade
7. Quanta    - Sixth upgrade
8. Lumix     - Seventh upgrade
9. Arion     - Eighth upgrade
10. Nexus    - Ninth upgrade
11. Fyre     - Tenth upgrade
12. Axion    - Eleventh upgrade
13. Trion    - Twelfth upgrade
14. Spectra  - Thirteenth upgrade
15. Omega    - Highest rank
```

---

## 8. Commission Distribution (কমিশন বিতরণ)

### 8.1 Binary Distribution (100%):
```
🌟 স্পার্ক বোনাস: 8%
🌟 রয়েল ক্যাপ্টেন: 4%
🌟 প্রেসিডেন্ট রিওয়ার্ড: 3%
🌟 শেয়ারহোল্ডার: 5%
নিউকামার গ্রোথ সাপোর্ট: 20%
🌟 মেন্টরশিপ বোনাস: 10%
পার্টনার ইনসেনটিভ: 10%
লেভেল পেআউট: 40%
```

### 8.2 Matrix Distribution (100%):
```
🌟 স্পার্ক বোনাস: 8%
🌟 রয়েল ক্যাপ্টেন: 4%
🌟 প্রেসিডেন্ট রিওয়ার্ড: 3%
🌟 শেয়ারহোল্ডার: 5%
নিউকামার গ্রোথ সাপোর্ট: 20%
🌟 মেন্টরশিপ বোনাস: 10%
পার্টনার ইনসেনটিভ: 10%
লেভেল পেআউট: 40%
```

### 8.3 Global Distribution (100%):
```
পার্টনার ইনসেনটিভ: 10%
লেভেল পেআউট: 30%
প্রফিট: 30%
🌟 রয়েল ক্যাপ্টেন: 15%
🌟 প্রেসিডেন্ট রিওয়ার্ড: 15%
🌟 ট্রিপল এন্ট্রি রিওয়ার্ড: 5%
🌟 শেয়ারহোল্ডার: 5%
```

---

## 9. Error Handling (ত্রুটি ব্যবস্থাপনা)

### 9.1 Common Error Responses:
```json
{
  "status": "Error",
  "status_code": 400,
  "message": "Error description",
  "data": null
}
```

### 9.2 Error Codes:
- `400`: Bad Request - Invalid input data
- `401`: Unauthorized - Invalid or missing token
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource not found
- `500`: Internal Server Error - Server error

---

## 10. Important Notes (গুরুত্বপূর্ণ নোট)

### 10.1 User Join Requirements:
- Valid referrer/upline ID প্রয়োজন
- Unique wallet address প্রয়োজন
- Unique referral code প্রয়োজন
- Binary program এ join করা বাধ্যতামূলক

### 10.2 Payment Requirements:
- Binary: 0.0066 BNB (EXPLORER + CONTRIBUTOR)
- Matrix: $11 USDT (optional)
- Global: $33 USD (optional)

### 10.3 Automatic Features:
- First 2 binary slots automatically activate হয়
- Tree placement automatically হয়
- Commission distribution automatically হয়
- Auto-upgrade system automatically initialize হয়

### 10.4 Security:
- All API calls require Bearer token
- Wallet address must be unique
- Referral code must be unique
- Password is hashed before storage

---

## 11. API Testing (API টেস্টিং)

### 11.1 Test User Creation:
```bash
curl -X POST "http://localhost:8000/user/create" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "testuser123",
    "refer_code": "TEST123",
    "upline_id": "66f1aab2c1f3a2a9c0b4e123",
    "wallet_address": "0x1234567890abcdef",
    "name": "Test User",
    "role": "user"
  }'
```

### 11.2 Test Login:
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_address": "0x1234567890abcdef"
  }'
```

---

