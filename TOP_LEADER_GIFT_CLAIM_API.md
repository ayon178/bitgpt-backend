# Top Leader Gift Claim API Documentation

## Overview
এই API user কে Top Leaders Gift fund থেকে rewards claim করতে দেয় currency-wise (USDT, BNB, অথবা BOTH)।

## Endpoint

```
POST /top-leader-gift/claim
```

## Authentication
**Required:** Bearer Token

## Request

### Headers
```
Authorization: Bearer <your_token>
Content-Type: application/json
```

### Request Body

```json
{
  "user_id": "string",      // Required: User's MongoDB ObjectId
  "level": 1,               // Required: Level number (1-5)
  "currency": "BOTH"        // Optional: 'USDT', 'BNB', or 'BOTH' (default: 'BOTH')
}
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | Yes | User's MongoDB ObjectId |
| level | integer | Yes | Level number (1-5) |
| currency | string | No | Currency to claim: 'USDT', 'BNB', or 'BOTH' (default: 'BOTH') |

## Response

### Success Response (200)

```json
{
  "status": "Ok",
  "data": {
    "user_id": "68e39a5a7e00955f335ae44d",
    "level": 1,
    "currency": "BOTH",
    "claimed_usdt": 750.0,
    "claimed_bnb": 0.57,
    "payment_id": "67ab12cd34ef56gh78ij90kl",
    "message": "Top Leaders Gift Level 1 claimed successfully"
  },
  "message": "Top Leaders Gift Level 1 claimed successfully"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| user_id | string | User's MongoDB ObjectId |
| level | integer | Level number claimed (1-5) |
| currency | string | Currency claimed (USDT/BNB/BOTH) |
| claimed_usdt | float | Amount claimed in USDT |
| claimed_bnb | float | Amount claimed in BNB |
| payment_id | string | Payment transaction ID |
| message | string | Success message |

### Error Responses

#### 400 Bad Request - Missing Parameters
```json
{
  "status": "Error",
  "message": "user_id is required"
}
```

#### 400 Bad Request - Invalid Level
```json
{
  "status": "Error",
  "message": "level must be between 1 and 5"
}
```

#### 400 Bad Request - Invalid Currency
```json
{
  "status": "Error",
  "message": "currency must be USDT, BNB, or BOTH"
}
```

#### 400 Bad Request - Not Eligible
```json
{
  "status": "Error",
  "message": "You are not eligible to claim Top Leaders Gift"
}
```

#### 400 Bad Request - Level Not Eligible
```json
{
  "status": "Error",
  "message": "You are not eligible to claim Level 2"
}
```

#### 400 Bad Request - Max Limit Reached
```json
{
  "status": "Error",
  "message": "Level 1 reward limit reached"
}
```

#### 400 Bad Request - Insufficient Fund
```json
{
  "status": "Error",
  "message": "Insufficient fund balance"
}
```

#### 401 Unauthorized
```json
{
  "status": "Error",
  "message": "User ID not found in token"
}
```

#### 403 Forbidden
```json
{
  "status": "Error",
  "message": "You can only claim rewards for yourself"
}
```

## Business Logic

### Claim Process Flow

1. **Authentication Check**
   - Validates Bearer token
   - Extracts user_id from token

2. **Authorization Check**
   - Ensures user can only claim for themselves
   - Prevents claiming for other users

3. **Parameter Validation**
   - Checks user_id is provided
   - Validates level number (1-5)
   - Validates currency (USDT/BNB/BOTH)

4. **Eligibility Check**
   - Verifies user is in Top Leaders Gift program (auto-joins if not)
   - Checks if user meets level requirements:
     - Self rank requirement
     - Direct partners count
     - Partners' rank requirement
     - Total team size

5. **Fund Calculation**
   - Gets level's allocated fund (based on percentage)
   - Counts eligible users for that level
   - Calculates per-user claimable amount:
     ```
     per_user_amount = allocated_fund / eligible_users_count
     ```

6. **Limit Check**
   - Compares with max reward limit
   - Considers already claimed amount:
     ```
     claimable = min(per_user_amount, max_reward - already_claimed)
     ```

7. **Currency Selection**
   - **USDT only**: Claims USDT portion only
   - **BNB only**: Claims BNB portion only
   - **BOTH**: Claims both USDT and BNB

8. **Payment Processing**
   - Creates payment record
   - Deducts from fund
   - Credits user wallet
   - Updates claimed amounts
   - Checks if maxed out

9. **Response**
   - Returns claimed amounts
   - Provides payment ID for tracking

## Currency Split

Rewards are split between USDT and BNB:
- **USDT**: 60% of reward value
- **BNB**: 40% of reward value

### Examples:

**Level 1 Max Reward: $3,000**
- Max USDT: $1,800 (60%)
- Max BNB: 0.91 BNB (~$1,200 @ $1316/BNB = 40%)

**Level 2 Max Reward: $30,000**
- Max USDT: $18,000 (60%)
- Max BNB: 9.12 BNB (~$12,000 @ $1316/BNB = 40%)

## Level Requirements

| Level | Self Rank | Direct Partners | Partners Rank | Total Team | Max Reward |
|-------|-----------|-----------------|---------------|------------|------------|
| 1 | 6 | 5 | 5 | 300 | $3,000 |
| 2 | 8 | 7 | 6 | 500 | $30,000 |
| 3 | 11 | 8 | 10 | 1,000 | $3,000,000 |
| 4 | 13 | 9 | 13 | 2,000 | $50,000,000 |
| 5 | 15 | 10 | 14 | 3,000 | $150,000,000 |

## Usage Examples

### Example 1: Claim USDT Only

```bash
curl -X POST "http://localhost:8000/top-leader-gift/claim" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "68e39a5a7e00955f335ae44d",
    "level": 1,
    "currency": "USDT"
  }'
```

**Response:**
```json
{
  "status": "Ok",
  "data": {
    "user_id": "68e39a5a7e00955f335ae44d",
    "level": 1,
    "currency": "USDT",
    "claimed_usdt": 750.0,
    "claimed_bnb": 0.0,
    "payment_id": "67ab12cd34ef56gh78ij90kl",
    "message": "Top Leaders Gift Level 1 claimed successfully"
  }
}
```

### Example 2: Claim BNB Only

```bash
curl -X POST "http://localhost:8000/top-leader-gift/claim" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "68e39a5a7e00955f335ae44d",
    "level": 1,
    "currency": "BNB"
  }'
```

**Response:**
```json
{
  "status": "Ok",
  "data": {
    "user_id": "68e39a5a7e00955f335ae44d",
    "level": 1,
    "currency": "BNB",
    "claimed_usdt": 0.0,
    "claimed_bnb": 0.45,
    "payment_id": "67ab12cd34ef56gh78ij90kl",
    "message": "Top Leaders Gift Level 1 claimed successfully"
  }
}
```

### Example 3: Claim Both Currencies

```bash
curl -X POST "http://localhost:8000/top-leader-gift/claim" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "68e39a5a7e00955f335ae44d",
    "level": 2,
    "currency": "BOTH"
  }'
```

**Response:**
```json
{
  "status": "Ok",
  "data": {
    "user_id": "68e39a5a7e00955f335ae44d",
    "level": 2,
    "currency": "BOTH",
    "claimed_usdt": 2500.0,
    "claimed_bnb": 1.52,
    "payment_id": "67ab12cd34ef56gh78ij90kl",
    "message": "Top Leaders Gift Level 2 claimed successfully"
  }
}
```

### Example 4: JavaScript (Fetch)

```javascript
const claimReward = async () => {
  const token = 'YOUR_TOKEN_HERE';
  const userId = '68e39a5a7e00955f335ae44d';
  
  const response = await fetch('http://localhost:8000/top-leader-gift/claim', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      user_id: userId,
      level: 1,
      currency: 'BOTH'
    })
  });
  
  const data = await response.json();
  console.log(data);
};

claimReward();
```

### Example 5: Python (requests)

```python
import requests

url = 'http://localhost:8000/top-leader-gift/claim'
token = 'YOUR_TOKEN_HERE'
user_id = '68e39a5a7e00955f335ae44d'

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

payload = {
    'user_id': user_id,
    'level': 1,
    'currency': 'BOTH'
}

response = requests.post(url, json=payload, headers=headers)
data = response.json()
print(data)
```

## Important Notes

1. ✅ **Auto-Join**: User automatically joins Top Leaders Gift program if not already enrolled
2. ✅ **Eligibility Check**: Real-time validation against rank, partners, and team requirements
3. ✅ **Fair Distribution**: Fund equally distributed among all eligible users for each level
4. ✅ **Max Reward Limits**: Claims cannot exceed maximum reward limits per level
5. ✅ **Currency Flexibility**: Users can choose to claim USDT, BNB, or both
6. ✅ **Wallet Integration**: Claimed amounts automatically credited to user's wallet
7. ✅ **Tracking**: All claims tracked with payment IDs for audit trail
8. ✅ **Authorization**: Users can only claim for themselves (security)

## Claim Workflow Diagram

```
User Request
    ↓
Authentication (Bearer Token)
    ↓
Authorization (Self-claim only)
    ↓
Parameter Validation (user_id, level, currency)
    ↓
Eligibility Check (rank, partners, team)
    ↓
Fund Calculation (allocated_fund / eligible_users)
    ↓
Limit Check (min(calculated, max_reward - claimed))
    ↓
Currency Selection (USDT / BNB / BOTH)
    ↓
Payment Processing
    ├── Create Payment Record
    ├── Deduct from Fund
    ├── Credit User Wallet
    └── Update Claimed Amounts
    ↓
Response (claimed amounts + payment_id)
```

## Integration with Other APIs

### 1. Get Fund Overview First
```
GET /top-leader-gift/fund/overview?user_id={user_id}
```
Check claimable amounts before claiming.

### 2. Then Claim
```
POST /top-leader-gift/claim
```
Claim the reward.

### 3. Verify in Wallet
Check user's wallet balance to confirm credit.

## Testing

To test the claim API:

1. **Setup Fund**: Ensure Top Leaders Gift Fund has sufficient balance
2. **Check Eligibility**: Get fund overview to see claimable amounts
3. **Make Claim Request**: POST to /top-leader-gift/claim
4. **Verify Response**: Check claimed amounts and payment ID
5. **Check Updated Balance**: Get fund overview again to see updated claimed amounts

## Common Scenarios

### Scenario 1: First Time Claim
User meets Level 1 requirements → Claims $750 USDT → Success

### Scenario 2: Partial Claim
User claims USDT only → Later claims BNB → Both claims successful (up to max limit)

### Scenario 3: Max Limit Reached
User already claimed max reward → New claim attempt → Error: "Level X reward limit reached"

### Scenario 4: Not Eligible
User doesn't meet rank/team requirements → Claim attempt → Error: "Not eligible to claim Level X"

### Scenario 5: Insufficient Fund
Fund balance too low → Claim attempt → Error: "Insufficient fund balance"

