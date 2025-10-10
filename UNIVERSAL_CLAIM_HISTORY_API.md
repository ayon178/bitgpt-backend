# Universal Claim History API

## Overview
একটি single API যা সব bonus programs এর সব claims একসাথে দেখায়।

---

## Endpoint

```
GET /wallet/claim-history
```

---

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | ✅ Yes | User ID |
| `currency` | string | ❌ No | Filter by currency (USDT or BNB) |
| `type` | string | ❌ No | Filter by claim type |
| `page` | integer | ❌ No | Page number (default: 1) |
| `limit` | integer | ❌ No | Items per page (default: 50, max: 100) |

### Supported Claim Types (for `type` parameter)
- `royal_captain` - Royal Captain Bonus
- `president_reward` - President Reward
- `leadership_stipend` - Leadership Stipend
- `triple_entry` - Triple Entry Reward
- `top_leader_gift` - Top Leader Gift

---

## Response Structure

```json
{
  "status": "Ok",
  "message": "Claim history fetched successfully",
  "data": {
    "claims": [
      {
        "s_no": 1,
        "id": "68e7c6198509d3d4b1e7c9eb",
        "type": "Royal Captain Bonus",
        "amount": 200.0,
        "currency": "USDT",
        "tier": 1,
        "status": "paid",
        "paid_at": "09 Oct 2025 (14:26)",
        "created_at": "09 Oct 2025 (14:26)",
        "tx_hash": "RC-68e7c6198509d3d4b1e7c9eb"
      },
      {
        "s_no": 2,
        "id": "68e7a48aaa4b12d3d66f7c40",
        "type": "Leadership Stipend",
        "amount": 0.25031111,
        "currency": "BNB",
        "tier": "LEADER",
        "slot": 10,
        "status": "paid",
        "paid_at": "09 Oct 2025 (12:03)",
        "created_at": "09 Oct 2025 (12:03)",
        "tx_hash": "LS-68e7a48aaa4b12d3d66f7c40"
      },
      {
        "s_no": 3,
        "id": "68e5273f0c54e46368e4df9d",
        "type": "Top Leader Gift",
        "amount": 1800.0,
        "currency": "USDT",
        "level": 1,
        "level_name": "Level 1",
        "status": "paid",
        "paid_at": "07 Oct 2025 (14:44)",
        "created_at": "07 Oct 2025 (14:44)",
        "tx_hash": "TLG-68e5273f0c54e46368e4df9d"
      },
      {
        "s_no": 4,
        "id": "68e90d7c8dc5c8fe04c8c41c",
        "type": "Triple Entry Reward",
        "amount": 13.69863014,
        "currency": "USDT",
        "status": "paid",
        "paid_at": "10 Oct 2025 (13:43)",
        "created_at": "10 Oct 2025 (13:43)",
        "tx_hash": "TER-USDT-..."
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 50,
      "total": 4,
      "total_pages": 1
    },
    "filters": {
      "currency": "All",
      "type": "All"
    },
    "summary": {
      "total_claims": 4,
      "total_amount_usdt": 2000.0,
      "total_amount_bnb": 1.16
    }
  },
  "status_code": 200,
  "success": true
}
```

---

## Response Fields

### Claim Object
| Field | Type | Description |
|-------|------|-------------|
| `s_no` | integer | Serial number |
| `id` | string | Payment/claim ID |
| `type` | string | Claim type (Royal Captain Bonus, etc.) |
| `amount` | float | Amount claimed |
| `currency` | string | USDT or BNB |
| `status` | string | Payment status (paid) |
| `paid_at` | string | Payment date/time |
| `created_at` | string | Created date/time |
| `tx_hash` | string | Transaction hash |

### Additional Fields (varies by type)
- **Royal Captain / President Reward**: `tier` (1-6)
- **Leadership Stipend**: `tier` (LEADER/CHAMPION/etc.), `slot` (10-16)
- **Top Leader Gift**: `level` (1-5), `level_name` (Level 1/2/etc.)
- **Triple Entry**: No additional fields

### Pagination
- `page`: Current page
- `limit`: Items per page
- `total`: Total claims
- `total_pages`: Total pages

### Filters
- `currency`: Applied currency filter (or "All")
- `type`: Applied type filter (or "All")

### Summary
- `total_claims`: Total number of claims
- `total_amount_usdt`: Total USDT claimed
- `total_amount_bnb`: Total BNB claimed

---

## Usage Examples

### 1. Get All Claims
```
GET /wallet/claim-history?user_id=68e39a5a7e00955f335ae44d
```

### 2. Filter by Currency (USDT only)
```
GET /wallet/claim-history?user_id=68e39a5a7e00955f335ae44d&currency=USDT
```

### 3. Filter by Currency (BNB only)
```
GET /wallet/claim-history?user_id=68e39a5a7e00955f335ae44d&currency=BNB
```

### 4. Filter by Type (Royal Captain only)
```
GET /wallet/claim-history?user_id=68e39a5a7e00955f335ae44d&type=royal_captain
```

### 5. Filter by Type AND Currency
```
GET /wallet/claim-history?user_id=68e39a5a7e00955f335ae44d&type=triple_entry&currency=USDT
```

### 6. With Pagination
```
GET /wallet/claim-history?user_id=68e39a5a7e00955f335ae44d&page=2&limit=20
```

---

## Supported Bonus Programs

| Program | Currency | Payment Collection |
|---------|----------|-------------------|
| **Royal Captain Bonus** | USDT (60%) + BNB (40%) | `royal_captain_bonus_payment` |
| **President Reward** | USDT (60%) + BNB (40%) | `president_reward_payment` |
| **Leadership Stipend** | BNB (100%) | `leadership_stipend_payment` |
| **Triple Entry Reward** | USDT or BNB | `triple_entry_payments` |
| **Top Leader Gift** | USDT + BNB | `top_leaders_gift_payment` |

---

## Frontend Integration

### Example: Display All Claims
```javascript
const userId = "68e39a5a7e00955f335ae44d";

// Fetch all claims
const response = await fetch(`/wallet/claim-history?user_id=${userId}`);
const data = await response.json();

// Display claims
data.data.claims.forEach(claim => {
  console.log(`${claim.type}: ${claim.amount} ${claim.currency}`);
});

// Show summary
console.log(`Total USDT: $${data.data.summary.total_amount_usdt}`);
console.log(`Total BNB: ${data.data.summary.total_amount_bnb} BNB`);
```

### Example: Filter by Currency
```javascript
// Show only USDT claims
const usdtResponse = await fetch(
  `/wallet/claim-history?user_id=${userId}&currency=USDT`
);
const usdtData = await usdtResponse.json();

// Show only BNB claims
const bnbResponse = await fetch(
  `/wallet/claim-history?user_id=${userId}&currency=BNB`
);
const bnbData = await bnbResponse.json();
```

### Example: Filter by Type
```javascript
// Show only Royal Captain claims
const rcResponse = await fetch(
  `/wallet/claim-history?user_id=${userId}&type=royal_captain`
);
const rcData = await rcResponse.json();
```

### Example: Dropdown Filters
```javascript
function fetchClaimHistory(userId, currency = null, type = null) {
  let url = `/wallet/claim-history?user_id=${userId}`;
  
  if (currency) url += `&currency=${currency}`;
  if (type) url += `&type=${type}`;
  
  return fetch(url).then(res => res.json());
}

// Usage
const allClaims = await fetchClaimHistory(userId);
const usdtClaims = await fetchClaimHistory(userId, 'USDT');
const royalCaptain = await fetchClaimHistory(userId, null, 'royal_captain');
const royalCaptainUSDT = await fetchClaimHistory(userId, 'USDT', 'royal_captain');
```

---

## Implementation Details

### Data Sources
API aggregates data from 5 different payment collections:
1. `RoyalCaptainBonusPayment` - Royal Captain claims
2. `PresidentRewardPayment` - President Reward claims
3. `LeadershipStipendPayment` - Leadership Stipend claims
4. `TripleEntryPayment` - Triple Entry Reward claims
5. `TopLeadersGiftPayment` - Top Leader Gift claims

### Sorting
Claims are sorted by `created_at` in descending order (most recent first).

### Pagination
- Default: 50 items per page
- Maximum: 100 items per page
- Minimum: 1 item per page

### Error Handling
If any payment collection fails to load, the API continues with other collections and logs the error. This ensures partial data is still returned.

---

## Benefits

✅ **Single API** - One endpoint for all bonus claims  
✅ **Flexible Filtering** - Filter by currency, type, or both  
✅ **Pagination** - Handle large claim histories  
✅ **Summary Stats** - Total amounts by currency  
✅ **Consistent Format** - Uniform response structure  
✅ **Error Resilient** - Continues even if some sources fail  

---

## Technical Notes

### Currency Handling
- Royal Captain, President Reward, and Top Leader Gift pay in **both USDT and BNB**
- Each payment creates **2 separate claim entries** (one for USDT, one for BNB)
- Leadership Stipend pays only in **BNB**
- Triple Entry Reward pays in **either USDT or BNB** (user choice)

### Date Formatting
All dates are formatted as: `DD MMM YYYY (HH:MM)`  
Example: `09 Oct 2025 (14:26)`

### Status
Currently only `paid` status claims are returned. Future versions may include `pending`, `processing`, and `failed` statuses.

---

## Reference
- Implementation: `backend/modules/wallet/service.py` → `get_universal_claim_history()`
- Route: `backend/modules/wallet/router.py` → `GET /wallet/claim-history`
- Models: Various payment models across different modules

