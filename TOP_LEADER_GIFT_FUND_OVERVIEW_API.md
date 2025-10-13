# Top Leader Gift Fund Overview API

## Overview
এই API user-specific level-wise fund overview প্রদান করে যা Top Leaders Gift program এর জন্য।

## Endpoint

```
GET /top-leader-gift/fund/overview
```

## Authentication
**Required:** Bearer Token

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | Yes | User's MongoDB ObjectId |

## Response Structure

### Success Response (200)

```json
{
  "status": "Ok",
  "data": {
    "success": true,
    "user_id": "68dc13a98b174277bc40cc12",
    "is_eligible": true,
    "highest_level_achieved": 2,
    "total_fund": {
      "usdt": 10000.0,
      "bnb": 7.6
    },
    "levels": [
      {
        "level": 1,
        "level_name": "Level 1",
        "is_eligible": true,
        "is_maxed_out": false,
        "requirements": {
          "self_rank": 6,
          "direct_partners": 5,
          "partners_rank": 5,
          "total_team": 300
        },
        "current_status": {
          "self_rank": 8,
          "direct_partners": 6,
          "total_team": 350
        },
        "fund_allocation": {
          "percentage": 37.5,
          "allocated_usdt": 3750.0,
          "allocated_bnb": 2.85
        },
        "eligible_users_count": 5,
        "claimable_amount": {
          "usdt": 750.0,
          "bnb": 0.57
        },
        "claimed": {
          "usdt": 200.0,
          "bnb": 0.15
        },
        "remaining": {
          "usdt": 1600.0,
          "bnb": 0.76
        },
        "max_reward": {
          "usdt": 1800.0,
          "bnb": 0.91
        },
        "already_claimed_percent": 11.54
      }
    ]
  },
  "message": "Fund overview retrieved successfully"
}
```

## Response Fields Explanation

### Root Level
- **user_id**: User এর MongoDB ObjectId
- **is_eligible**: User কোনো level এর জন্য eligible কিনা
- **highest_level_achieved**: User সর্বোচ্চ কোন level achieve করেছে (0-5)
- **total_fund**: Total available fund (USDT + BNB)

### Level Details (প্রতি level এর জন্য)

#### Basic Info
- **level**: Level number (1-5)
- **level_name**: Level এর নাম
- **is_eligible**: User এই level এর জন্য eligible কিনা
- **is_maxed_out**: Maximum reward limit এ পৌঁছেছে কিনা

#### Requirements
Level এ qualify করার জন্য প্রয়োজনীয়:
- **self_rank**: নিজের rank requirement
- **direct_partners**: কতজন direct partners থাকতে হবে
- **partners_rank**: Partners দের কী rank থাকতে হবে
- **total_team**: Total team size কত হতে হবে

#### Current Status
User এর বর্তমান status:
- **self_rank**: User এর current rank
- **direct_partners**: User এর direct partners count
- **total_team**: User এর total team size

#### Fund Allocation
এই level এর জন্য allocated fund:
- **percentage**: Total fund থেকে এই level এ কত % allocated (37.5%, 25%, 15%, 12.5%, 10%)
- **allocated_usdt**: USDT তে allocated amount
- **allocated_bnb**: BNB তে allocated amount

#### Eligible Users Count
এই level এর জন্য মোট কতজন user eligible

#### Claimable Amount
User এই level থেকে কত claim করতে পারবে:
- **usdt**: USDT amount
- **bnb**: BNB amount

**Calculation:**
```
claimable = min(
  allocated_fund / eligible_users_count,
  max_reward - claimed_amount
)
```

#### Claimed
User ইতিমধ্যে এই level থেকে কত claim করেছে:
- **usdt**: Claimed USDT
- **bnb**: Claimed BNB

#### Remaining
Max reward থেকে আর কত claim করতে পারবে:
- **usdt**: Remaining USDT
- **bnb**: Remaining BNB

#### Max Reward
এই level এর maximum reward limit:
- **usdt**: Maximum USDT (60% of total)
- **bnb**: Maximum BNB (40% of total)

#### Already Claimed Percent
Max reward এর কত % ইতিমধ্যে claim করা হয়েছে

**Calculation:**
```
already_claimed_percent = (
  (claimed_usdt / max_reward_usdt * 100) + 
  (claimed_bnb / max_reward_bnb * 100)
) / 2
```

## Level Details

| Level | Self Rank | Direct Partners | Partners Rank | Total Team | Max Reward | Fund % |
|-------|-----------|-----------------|---------------|------------|------------|--------|
| 1 | 6 | 5 | 5 | 300 | $3,000 | 37.5% |
| 2 | 8 | 7 | 6 | 500 | $30,000 | 25% |
| 3 | 11 | 8 | 10 | 1,000 | $3,000,000 | 15% |
| 4 | 13 | 9 | 13 | 2,000 | $50,000,000 | 12.5% |
| 5 | 15 | 10 | 14 | 3,000 | $150,000,000 | 10% |

## Fund Distribution

**Source:** Spark Bonus থেকে 2% Top Leaders Gift Fund এ যায়

**Currency Split:**
- USDT: 60%
- BNB: 40%

**Level Allocation:**
Total available fund এই ভাবে distribute হয়:
1. Level 1: 37.5%
2. Level 2: 25%
3. Level 3: 15%
4. Level 4: 12.5%
5. Level 5: 10%

**Per User Calculation:**
প্রতি level এর allocated fund সেই level এর সব eligible user এর মধ্যে সমানভাবে ভাগ হয়।

## Error Responses

### 400 Bad Request
```json
{
  "status": "Error",
  "message": "Failed to get fund overview"
}
```

### 401 Unauthorized
```json
{
  "status": "Error",
  "message": "User ID not found in token"
}
```

### 404 Not Found
```json
{
  "status": "Error",
  "message": "Top Leaders Gift fund not found"
}
```

## Example Usage

### Using cURL

```bash
curl -X GET "http://localhost:8000/top-leader-gift/fund/overview?user_id=68dc13a98b174277bc40cc12" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Using JavaScript (Fetch)

```javascript
const userId = '68dc13a98b174277bc40cc12';
const token = 'YOUR_TOKEN_HERE';

fetch(`http://localhost:8000/top-leader-gift/fund/overview?user_id=${userId}`, {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));
```

### Using Python (requests)

```python
import requests

user_id = '68dc13a98b174277bc40cc12'
token = 'YOUR_TOKEN_HERE'

headers = {
    'Authorization': f'Bearer {token}'
}

response = requests.get(
    f'http://localhost:8000/top-leader-gift/fund/overview',
    params={'user_id': user_id},
    headers=headers
)

data = response.json()
print(data)
```

## Business Logic

1. **Auto-join**: যদি user Top Leaders Gift program এ না থাকে, automatically join করানো হয়
2. **Eligibility Check**: User এর current rank, direct partners, এবং team size check করা হয়
3. **Level Assessment**: প্রতি level এর জন্য eligibility determine করা হয়
4. **Fund Calculation**: 
   - Total available fund থেকে level wise allocation
   - Eligible users count করা
   - Per user amount calculate করা
   - Max reward limit এর সাথে compare করা
5. **Response Building**: সব data organize করে response তৈরি করা

## Notes

- ✅ User automatically Top Leaders Gift program এ join হয়ে যায় যদি না থাকে
- ✅ Real-time eligibility check করা হয়
- ✅ Fund fair distribution নিশ্চিত করা হয় সব eligible users এর মধ্যে
- ✅ Max reward limits enforce করা হয়
- ✅ Already claimed percentage দেখানো হয়
- ✅ USDT এবং BNB উভয় currency support করে

## Related APIs

- `POST /top-leader-gift/claim` - Claim reward from a specific level
- `GET /top-leader-gift/status/{user_id}` - Get user's Top Leader Gift status
- `GET /top-leader-gift/fund` - Get overall fund status (admin)

