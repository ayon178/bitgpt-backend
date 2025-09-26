# Matrix System Postman Testing Guide

## Overview
This guide provides all the necessary API endpoints and JSON payloads to test the Matrix system using Postman. All endpoints assume the backend is running on `http://127.0.0.1:8000`.

---

## 1. MATRIX JOIN ENDPOINT

### Endpoint: Join Matrix Program
**POST** `http://127.0.0.1:8000/matrix/join`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer your_jwt_token_here
```

**Request Body:**
```json
{
  "user_id": "68bee4ffc1eac053757f5d1e",
  "referrer_id": "68bee3aec1eac053757f5cf1",
  "tx_hash": "0x1234567890abcdef1234567890abcdef12345678",
  "amount": 11.0
}
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "68bee4ffc1eac053757f5d1e",
    "referrer_id": "68bee3aec1eac053757f5cf1",
    "matrix_tree_id": "507f1f77bcf86cd799439011",
    "activation_id": "507f1f77bcf86cd799439012",
    "slot_activated": "STARTER",
    "amount": 11.0,
    "currency": "USDT",
    "placement_result": {
      "success": true,
      "level": 1,
      "position": 0,
      "total_members": 1,
      "placed_under_user_id": "68bee3aec1eac053757f5cf1"
    },
    "message": "Successfully joined Matrix program with STARTER slot"
  }
}
```

### Alternative Path-based Join
**POST** `http://127.0.0.1:8000/matrix/join/68bee4ffc1eac053757f5d1e/68bee3aec1eac053757f5cf1`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer your_jwt_token_here
```

**Request Body:**
```json
{
  "tx_hash": "0x1234567890abcdef1234567890abcdef12345678",
  "amount": 11.0
}
```

---

## 2. MATRIX STATUS ENDPOINTS

### Get Matrix Status
**GET** `http://127.0.0.1:8000/matrix/status/68bee4ffc1eac053757f5d1e`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "68bee4ffc1eac053757f5d1e",
    "current_slot": 1,
    "current_level": 1,
    "total_members": 1,
    "level_1_members": 0,
    "level_2_members": 0,
    "level_3_members": 0,
    "is_complete": false,
    "total_earnings": 0.0,
    "slots": [
      {
        "slot_no": 1,
        "slot_name": "STARTER",
        "slot_value": 11.0,
        "level": 1,
        "members_count": 0,
        "is_active": true,
        "activated_at": "2024-01-01T00:00:00Z",
        "total_income": 0.0,
        "upgrade_cost": 33.0,
        "wallet_amount": 0.0
      }
    ]
  }
}
```

---

## 3. MATRIX RECYCLE ENDPOINTS

### Get Recycle Tree
**GET** `http://127.0.0.1:8000/matrix/recycle-tree?user_id=68bee4ffc1eac053757f5d1e&slot=1&recycle_no=current`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "68bee4ffc1eac053757f5d1e",
    "slot_number": 1,
    "recycle_no": "current",
    "is_snapshot": false,
    "is_complete": false,
    "total_recycles": 0,
    "nodes": [
      {
        "level": 1,
        "position": 0,
        "user_id": "68bee560c1eac053757f5d32",
        "placed_at": "2024-01-01T00:00:00Z"
      },
      {
        "level": 1,
        "position": 1,
        "user_id": "68bee751c1eac053757f5d46",
        "placed_at": "2024-01-01T00:05:00Z"
      }
    ]
  }
}
```

### Get Recycles List
**GET** `http://127.0.0.1:8000/matrix/recycles?user_id=68bee4ffc1eac053757f5d1e&slot=1`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

**Expected Response:**
```json
{
  "success": true,
  "data": [
    {
      "recycle_no": 1,
      "is_complete": true,
      "created_at": "2024-01-01T00:00:00Z",
      "completed_at": "2024-01-01T12:00:00Z"
    },
    {
      "recycle_no": 2,
      "is_complete": false,
      "created_at": "2024-01-01T12:01:00Z",
      "completed_at": null
    }
  ]
}
```

---

## 4. MATRIX UPGRADE ENDPOINTS

### Upgrade Matrix Slot
**POST** `http://127.0.0.1:8000/matrix/upgrade-slot`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer your_jwt_token_here
```

**Request Body:**
```json
{
  "user_id": "68bee4ffc1eac053757f5d1e",
  "from_slot": 1,
  "to_slot": 2,
  "amount": 33.0,
  "upgrade_type": "manual"
}
```

### Alternative Path-based Upgrade
**POST** `http://127.0.0.1:8000/matrix/upgrade-slot/68bee4ffc1eac053757f5d1e`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer your_jwt_token_here
```

**Request Body:**
```json
{
  "from_slot": 1,
  "to_slot": 2,
  "amount": 33.0,
  "upgrade_type": "manual"
}
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "68bee4ffc1eac053757f5d1e",
    "from_slot": 1,
    "to_slot": 2,
    "amount": 33.0,
    "upgrade_type": "manual",
    "activated_at": "2024-01-01T00:00:00Z",
    "message": "Successfully upgraded to slot 2 (BRONZE)"
  }
}
```

---

## 5. AUTO UPGRADE ENDPOINTS

### Get Middle Three Earnings
**GET** `http://127.0.0.1:8000/matrix/middle-three-earnings/68bee4ffc1eac053757f5d1e?slot_no=1`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "68bee4ffc1eac053757f5d1e",
    "middle_three_earnings": 150.0,
    "sufficient_for_upgrade": true,
    "next_slot_cost": 100.0
  }
}
```

### Trigger Automatic Upgrade
**POST** `http://127.0.0.1:8000/matrix/trigger-auto-upgrade/68bee4ffc1eac053757f5d1e?slot_no=1`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "upgraded": true,
    "from_slot": 1,
    "to_slot": 2,
    "amount_used": 100.0,
    "remaining_balance": 50.0
  }
}
```

---

## 6. DREAM MATRIX ENDPOINTS

### Get Dream Matrix Status
**GET** `http://127.0.0.1:8000/matrix/dream-matrix-status/68bee4ffc1eac053757f5d1e`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "68bee4ffc1eac053757f5d1e",
    "eligible": true,
    "direct_partners": 3,
    "total_earnings": 800.0,
    "slot_5_earnings": {
      "level_1": 240.0,
      "level_2": 720.0,
      "level_3": 3240.0,
      "level_4": 16200.0,
      "level_5": 77760.0,
      "total": 98160.0
    }
  }
}
```

### Distribute Dream Matrix Earnings
**POST** `http://127.0.0.1:8000/matrix/dream-matrix-distribute/68bee4ffc1eac053757f5d1e?slot_no=5`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "distributed": true,
    "total_amount": 800.0,
    "user_id": "68bee4ffc1eac053757f5d1e",
    "slot_no": 5
  }
}
```

---

## 7. RANK SYSTEM ENDPOINTS

### Get Rank Status
**GET** `http://127.0.0.1:8000/matrix/rank-status/68bee4ffc1eac053757f5d1e`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "68bee4ffc1eac053757f5d1e",
    "current_rank": "Bitron",
    "rank_number": 1,
    "binary_slots_activated": 2,
    "matrix_slots_activated": 1,
    "next_rank": "Cryzen",
    "requirements_for_next": {
      "binary_slots_needed": 1,
      "matrix_slots_needed": 1
    }
  }
}
```

### Update Rank
**POST** `http://127.0.0.1:8000/matrix/update-rank/68bee4ffc1eac053757f5d1e`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "68bee4ffc1eac053757f5d1e",
    "old_rank": "Bitron",
    "new_rank": "Cryzen",
    "rank_updated": true
  }
}
```

---

## 8. MENTORSHIP BONUS ENDPOINTS

### Get Mentorship Status
**GET** `http://127.0.0.1:8000/matrix/mentorship-status/68bee4ffc1eac053757f5d1e`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "user_id": "68bee4ffc1eac053757f5d1e",
    "super_upline": "68bee3aec1eac053757f5cf1",
    "direct_of_direct_partners": 3,
    "total_commission": 100.0,
    "recent_activities": [
      {
        "partner_id": "68bee560c1eac053757f5d32",
        "action": "slot_upgrade",
        "slot": 2,
        "commission": 33.0,
        "date": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

### Distribute Mentorship Bonus
**POST** `http://127.0.0.1:8000/matrix/mentorship-bonus-distribute/68bee3aec1eac053757f5cf1`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer your_jwt_token_here
```

**Request Body:**
```json
{
  "direct_referral_id": "68bee4ffc1eac053757f5d1e",
  "amount": 100.0,
  "activity_type": "joining"
}
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "distributed": true,
    "commission_amount": 100.0,
    "super_upline_id": "68bee3aec1eac053757f5cf1",
    "activity_type": "joining"
  }
}
```

---

## 9. SPECIAL PROGRAMS INTEGRATION

### Global Program Status
**GET** `http://127.0.0.1:8000/matrix/global-program-status/68bee4ffc1eac053757f5d1e`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

### Jackpot Program Status
**GET** `http://127.0.0.1:8000/matrix/jackpot-program-status/68bee4ffc1eac053757f5d1e`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

### Leadership Stipend Status
**GET** `http://127.0.0.1:8000/matrix/leadership-stipend-status/68bee4ffc1eac053757f5d1e`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

### NGS (Newcomer Growth Support) Status
**GET** `http://127.0.0.1:8000/matrix/ngs-status/68bee4ffc1eac053757f5d1e`

**Headers:**
```
Authorization: Bearer your_jwt_token_here
```

---

## 10. TESTING SEQUENCE RECOMMENDATIONS

### Step 1: Matrix Join Flow
1. **Join Matrix** - Use the main join endpoint with ROOT user as referrer
2. **Check Status** - Verify the user is properly placed in the matrix
3. **View Tree** - Check the recycle tree to see placement

### Step 2: Multi-User Testing
1. **Join User 2** - Join with User 1 as referrer
2. **Join User 3** - Join with User 1 as referrer
3. **Join User 4** - Join with User 2 as referrer (test spillover)

### Step 3: Upgrade Testing
1. **Check Middle Three Earnings** - See if auto-upgrade is possible
2. **Manual Upgrade** - Test manual slot upgrade
3. **Auto Upgrade** - Test automatic upgrade using earnings

### Step 4: Special Programs
1. **Dream Matrix** - Check eligibility and earnings
2. **Mentorship Bonus** - Test direct-of-direct commissions
3. **Rank System** - Verify rank progression

### Step 5: Advanced Features
1. **Recycle Testing** - Fill a tree to 39 members and test recycle
2. **Sweepover Testing** - Test when upline doesn't have required slot
3. **Commission Distribution** - Verify 20/20/60 distribution

---

## 11. USER IDs FOR TESTING

Based on your MongoDB data:

- **ROOT (Mother)**: `68bee3aec1eac053757f5cf1`
- **User 3**: `68bee4ffc1eac053757f5d1e` (refered_by: 68bee455c1eac053757f5cf4)
- **User 4**: `68bee560c1eac053757f5d32` (refered_by: 68bee3aec1eac053757f5cf1)
- **User 5**: `68bee751c1eac053757f5d46` (refered_by: 68bee455c1eac053757f5cf4)

---

## 12. AUTHENTICATION NOTE

For testing purposes, if you don't have JWT tokens, you may need to either:
1. Implement a test login endpoint to get tokens
2. Temporarily disable authentication for testing
3. Use mock tokens if the system accepts them

Replace `your_jwt_token_here` with actual JWT tokens from your authentication system.

---

## 13. EXPECTED MATRIX BEHAVIOR

According to PROJECT_DOCUMENTATION.md:

- **Matrix Structure**: 3×3×3 (3 levels: 3, 9, 27 members)
- **Join Cost**: $11 USDT for STARTER slot
- **Upgrade Costs**: BRONZE ($33), SILVER ($99), GOLD ($297), etc.
- **Recycle**: Happens at 39 members (3+9+27)
- **Distribution**: 20% Level-1, 20% Level-2, 60% Level-3
- **Auto Upgrade**: Middle 3 members' earnings fund next slot
- **Partner Incentive**: 10% to direct upline
- **Mentorship Bonus**: 10% to super upline (direct-of-direct)

Test these behaviors systematically using the endpoints above to ensure the Matrix system works as documented.
