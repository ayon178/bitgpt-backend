# Top Leader Gift Claim History API

## Overview
এই API user এর Top Leaders Gift claim history দেখায় level-wise এবং currency-wise breakdown সহ।

## Endpoint

```
GET /top-leader-gift/claim/history
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
    "user_id": "68e39a5a7e00955f335ae44d",
    "overall_summary": {
      "total_claims": 1,
      "successful_claims": 1,
      "pending_claims": 0,
      "failed_claims": 0,
      "total_claimed_usdt": 1800.0,
      "total_claimed_bnb": 0.91,
      "total_claims_count": 1,
      "last_claim_date": "2025-10-07T14:44:20.611000",
      "highest_level_claimed": 1
    },
    "level_summary": {
      "level_1": {
        "level": 1,
        "total_claims": 1,
        "successful_claims": 1,
        "pending_claims": 0,
        "failed_claims": 0,
        "total_claimed_usdt": 1800.0,
        "total_claimed_bnb": 0.91,
        "total_claimed_usd_value": 2997.56,
        "claims": [
          {
            "payment_id": "68e5273f0c54e46368e4df9d",
            "claimed_at": "2025-10-07T14:44:13.680000",
            "claimed_usdt": 1800.0,
            "claimed_bnb": 0.91,
            "currency": "BOTH",
            "status": "paid",
            "paid_at": "2025-10-07T14:44:20.303000",
            "usdt_tx_hash": null,
            "bnb_tx_hash": null,
            "payment_reference": "TLG-68e5273f0c54e46368e4df9d"
          }
        ]
      },
      "level_2": {
        "level": 2,
        "total_claims": 0,
        "successful_claims": 0,
        "pending_claims": 0,
        "failed_claims": 0,
        "total_claimed_usdt": 0,
        "total_claimed_bnb": 0,
        "total_claimed_usd_value": 0,
        "claims": []
      }
      // ... levels 3-5 similar structure
    },
    "currency_summary": {
      "usdt": {
        "total_claimed": 1800.0,
        "claim_count": 1,
        "claims_by_level": {
          "level_1": 1800.0,
          "level_2": 0,
          "level_3": 0,
          "level_4": 0,
          "level_5": 0
        }
      },
      "bnb": {
        "total_claimed": 0.91,
        "claim_count": 1,
        "claims_by_level": {
          "level_1": 0.91,
          "level_2": 0,
          "level_3": 0,
          "level_4": 0,
          "level_5": 0
        }
      }
    },
    "all_claims": [
      {
        "payment_id": "68e5273f0c54e46368e4df9d",
        "level": 1,
        "level_name": "Level 1",
        "claimed_at": "2025-10-07T14:44:13.680000",
        "claimed_usdt": 1800.0,
        "claimed_bnb": 0.91,
        "currency": "BOTH",
        "status": "paid",
        "paid_at": "2025-10-07T14:44:20.303000",
        "payment_reference": "TLG-68e5273f0c54e46368e4df9d",
        "self_rank_at_claim": 6,
        "direct_partners_at_claim": 5,
        "total_team_at_claim": 300
      }
    ]
  },
  "message": "Claim history retrieved successfully"
}
```

## Response Fields Explanation

### Overall Summary
Complete overview of all claims:

| Field | Type | Description |
|-------|------|-------------|
| total_claims | integer | Total number of claim attempts |
| successful_claims | integer | Number of successfully paid claims |
| pending_claims | integer | Number of pending claims |
| failed_claims | integer | Number of failed claims |
| total_claimed_usdt | float | Total USDT claimed across all levels |
| total_claimed_bnb | float | Total BNB claimed across all levels |
| total_claims_count | integer | Total claims count from user record |
| last_claim_date | datetime | Date of last claim |
| highest_level_claimed | integer | Highest level user has claimed (0-5) |

### Level Summary
Breakdown by each level (level_1 to level_5):

| Field | Type | Description |
|-------|------|-------------|
| level | integer | Level number (1-5) |
| total_claims | integer | Total claims for this level |
| successful_claims | integer | Successful claims for this level |
| pending_claims | integer | Pending claims for this level |
| failed_claims | integer | Failed claims for this level |
| total_claimed_usdt | float | Total USDT claimed from this level |
| total_claimed_bnb | float | Total BNB claimed from this level |
| total_claimed_usd_value | float | Approximate USD value (USDT + BNB*1316) |
| claims | array | Individual claim records for this level |

#### Individual Claim Record (inside claims array)

| Field | Type | Description |
|-------|------|-------------|
| payment_id | string | Unique payment identifier |
| claimed_at | datetime | When claim was made |
| claimed_usdt | float | USDT amount claimed |
| claimed_bnb | float | BNB amount claimed |
| currency | string | Currency type (USDT/BNB/BOTH) |
| status | string | Payment status (paid/pending/failed) |
| paid_at | datetime | When payment was completed |
| usdt_tx_hash | string | USDT transaction hash |
| bnb_tx_hash | string | BNB transaction hash |
| payment_reference | string | Payment reference number |

### Currency Summary
Currency-wise breakdown:

**USDT:**
| Field | Type | Description |
|-------|------|-------------|
| total_claimed | float | Total USDT claimed |
| claim_count | integer | Number of claims with USDT |
| claims_by_level | object | USDT claims broken down by level |

**BNB:**
| Field | Type | Description |
|-------|------|-------------|
| total_claimed | float | Total BNB claimed |
| claim_count | integer | Number of claims with BNB |
| claims_by_level | object | BNB claims broken down by level |

### All Claims
Array of all claim records (recent first):

| Field | Type | Description |
|-------|------|-------------|
| payment_id | string | Unique payment ID |
| level | integer | Level number (1-5) |
| level_name | string | Level name |
| claimed_at | datetime | Claim timestamp |
| claimed_usdt | float | USDT amount |
| claimed_bnb | float | BNB amount |
| currency | string | Currency type |
| status | string | Payment status |
| paid_at | datetime | Payment completion time |
| payment_reference | string | Reference number |
| self_rank_at_claim | integer | User's rank when claimed |
| direct_partners_at_claim | integer | Direct partners count when claimed |
| total_team_at_claim | integer | Team size when claimed |

## Usage Examples

### Example 1: Using cURL

```bash
curl -X GET "http://localhost:8000/top-leader-gift/claim/history?user_id=68e39a5a7e00955f335ae44d" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Example 2: JavaScript (Fetch)

```javascript
const userId = '68e39a5a7e00955f335ae44d';
const token = 'YOUR_TOKEN_HERE';

fetch(`http://localhost:8000/top-leader-gift/claim/history?user_id=${userId}`, {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
  .then(response => response.json())
  .then(data => {
    console.log('Overall Summary:', data.data.overall_summary);
    console.log('Level Summary:', data.data.level_summary);
    console.log('Currency Summary:', data.data.currency_summary);
    console.log('All Claims:', data.data.all_claims);
  })
  .catch(error => console.error('Error:', error));
```

### Example 3: Python (requests)

```python
import requests

user_id = '68e39a5a7e00955f335ae44d'
token = 'YOUR_TOKEN_HERE'

headers = {
    'Authorization': f'Bearer {token}'
}

response = requests.get(
    f'http://localhost:8000/top-leader-gift/claim/history',
    params={'user_id': user_id},
    headers=headers
)

data = response.json()
print(f"Total Claims: {data['data']['overall_summary']['total_claims']}")
print(f"Total USDT: {data['data']['overall_summary']['total_claimed_usdt']}")
print(f"Total BNB: {data['data']['overall_summary']['total_claimed_bnb']}")
```

## Frontend Integration

### Display Overall Summary
```javascript
const summary = data.data.overall_summary;

console.log(`Total Claims: ${summary.total_claims}`);
console.log(`Successful: ${summary.successful_claims}`);
console.log(`Total USDT: $${summary.total_claimed_usdt.toLocaleString()}`);
console.log(`Total BNB: ${summary.total_claimed_bnb} BNB`);
```

### Display Level-wise Claims
```javascript
const levelSummary = data.data.level_summary;

for (let i = 1; i <= 5; i++) {
  const levelData = levelSummary[`level_${i}`];
  
  if (levelData.total_claims > 0) {
    console.log(`Level ${i}:`);
    console.log(`  USDT: $${levelData.total_claimed_usdt}`);
    console.log(`  BNB: ${levelData.total_claimed_bnb}`);
    console.log(`  Claims: ${levelData.successful_claims}`);
  }
}
```

### Display Currency-wise Summary
```javascript
const currencySummary = data.data.currency_summary;

// USDT breakdown
console.log('USDT Claims:');
console.log(`Total: $${currencySummary.usdt.total_claimed}`);
for (let i = 1; i <= 5; i++) {
  const amount = currencySummary.usdt.claims_by_level[`level_${i}`];
  if (amount > 0) {
    console.log(`  Level ${i}: $${amount}`);
  }
}

// BNB breakdown
console.log('BNB Claims:');
console.log(`Total: ${currencySummary.bnb.total_claimed} BNB`);
for (let i = 1; i <= 5; i++) {
  const amount = currencySummary.bnb.claims_by_level[`level_${i}`];
  if (amount > 0) {
    console.log(`  Level ${i}: ${amount} BNB`);
  }
}
```

### Display All Claims List
```javascript
const allClaims = data.data.all_claims;

allClaims.forEach(claim => {
  console.log(`Level ${claim.level} - ${claim.currency}`);
  console.log(`  USDT: $${claim.claimed_usdt}`);
  console.log(`  BNB: ${claim.claimed_bnb}`);
  console.log(`  Status: ${claim.status}`);
  console.log(`  Date: ${new Date(claim.claimed_at).toLocaleDateString()}`);
  console.log(`  Ref: ${claim.payment_reference}`);
});
```

## Use Cases

### Use Case 1: Show User's Total Earnings
Display total USDT and BNB claimed from Top Leaders Gift across all levels.

### Use Case 2: Level-wise History
Show how much user has claimed from each level separately.

### Use Case 3: Currency Filter
Filter claims by currency type (USDT only, BNB only, or both).

### Use Case 4: Claim Timeline
Display chronological history of all claims with dates and amounts.

### Use Case 5: Payment Verification
Track individual payments with payment IDs and transaction hashes.

### Use Case 6: User Progress Tracking
Show user's rank and team size at the time of each claim.

## Payment Status Values

| Status | Description |
|--------|-------------|
| `pending` | Claim initiated but not yet processed |
| `processing` | Payment being processed |
| `paid` | Payment completed successfully |
| `failed` | Payment failed |

## Error Responses

### 400 Bad Request
```json
{
  "status": "Error",
  "message": "Failed to get claim history"
}
```

### 401 Unauthorized
```json
{
  "status": "Error",
  "message": "User ID not found in token"
}
```

## Test Results

### ✅ Verified with Real Data

**Test User:** LSUSER2_1759746644  
**User ID:** 68e39a5a7e00955f335ae44d

**Results:**
- Total Claims: 1
- Successful Claims: 1
- Total USDT: $1,800.00
- Total BNB: 0.91
- Highest Level Claimed: 1
- Level 1 Status: 100% claimed (maxed out)

## API Response Sections

### 1. Overall Summary
Quick overview of all claims across all levels.

**Best for:** Dashboard summary, total earnings display

### 2. Level Summary
Detailed breakdown for each level (1-5).

**Best for:** Level-wise progress tracking, per-level earnings display

### 3. Currency Summary
Breakdown by currency type (USDT/BNB) with level details.

**Best for:** Currency-specific analysis, wallet reconciliation

### 4. All Claims
Complete list of individual claim records.

**Best for:** Transaction history, detailed audit trail, payment verification

## Integration Examples

### Dashboard Summary Card
```javascript
// Show total earnings
const summary = response.data.overall_summary;

<div className="summary-card">
  <h3>Total Top Leader Gift Earnings</h3>
  <p>USDT: ${summary.total_claimed_usdt.toLocaleString()}</p>
  <p>BNB: {summary.total_claimed_bnb}</p>
  <p>Total Claims: {summary.successful_claims}</p>
</div>
```

### Level Progress Chart
```javascript
// Show level-wise earnings
const levelSummary = response.data.level_summary;

levels = [1, 2, 3, 4, 5].map(level => ({
  level,
  usdt: levelSummary[`level_${level}`].total_claimed_usdt,
  bnb: levelSummary[`level_${level}`].total_claimed_bnb,
  claims: levelSummary[`level_${level}`].successful_claims
}));
```

### Currency Breakdown Table
```javascript
// Show currency-wise breakdown
const currencyData = response.data.currency_summary;

<table>
  <thead>
    <tr>
      <th>Level</th>
      <th>USDT</th>
      <th>BNB</th>
    </tr>
  </thead>
  <tbody>
    {[1,2,3,4,5].map(level => (
      <tr key={level}>
        <td>Level {level}</td>
        <td>${currencyData.usdt.claims_by_level[`level_${level}`]}</td>
        <td>{currencyData.bnb.claims_by_level[`level_${level}`]} BNB</td>
      </tr>
    ))}
  </tbody>
</table>
```

### Transaction History
```javascript
// Show all claims with details
const claims = response.data.all_claims;

<div className="claim-history">
  {claims.map(claim => (
    <div key={claim.payment_id} className="claim-item">
      <h4>Level {claim.level} - {claim.currency}</h4>
      <p>USDT: ${claim.claimed_usdt.toLocaleString()}</p>
      <p>BNB: {claim.claimed_bnb}</p>
      <p>Status: {claim.status}</p>
      <p>Date: {new Date(claim.claimed_at).toLocaleDateString()}</p>
      <p>Ref: {claim.payment_reference}</p>
      <div className="user-status">
        <small>Rank: {claim.self_rank_at_claim}</small>
        <small>Partners: {claim.direct_partners_at_claim}</small>
        <small>Team: {claim.total_team_at_claim}</small>
      </div>
    </div>
  ))}
</div>
```

## Key Features

✅ **Comprehensive History**: All claims across all levels  
✅ **Level-wise Breakdown**: Separate summary for each level  
✅ **Currency-wise Breakdown**: USDT and BNB totals with level details  
✅ **Individual Records**: Complete claim details with timestamps  
✅ **Status Tracking**: paid/pending/failed status for each claim  
✅ **User Context**: Rank, partners, and team size at claim time  
✅ **Payment References**: Transaction IDs and hashes for verification  
✅ **Chronological Order**: Recent claims first  

## Related APIs

1. **Fund Overview** - Check claimable amounts
   ```
   GET /top-leader-gift/fund/overview?user_id={user_id}
   ```

2. **Claim Reward** - Make a claim
   ```
   POST /top-leader-gift/claim
   ```

3. **Claim History** - View claim history (this API)
   ```
   GET /top-leader-gift/claim/history?user_id={user_id}
   ```

## Notes

- Claims are ordered by creation date (recent first)
- All timestamps in UTC
- Currency values are exact as stored in database
- USD value calculated using 1 BNB = $1316 (approximate)
- Auto-joins user to program if not already joined
- Includes both successful and unsuccessful claims for audit trail

