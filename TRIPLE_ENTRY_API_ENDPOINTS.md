# Triple Entry Reward - API Endpoints

## Overview
Triple Entry Reward has **3 main APIs** split for better frontend integration:
1. Claimable Fund API - Check how much user can claim
2. Claim History API - View past claims (with optional currency filter)
3. Claim API - Process claim

---

## API 1: Get Claimable Fund

### Endpoint
```
GET /spark/triple-entry/claimable-fund?user_id={user_id}
```

### Purpose
Check if user is eligible and how much they can claim (without claim history)

### Response
```json
{
  "status": "Ok",
  "message": "Triple Entry claimable fund fetched successfully",
  "data": {
    "USDT": {
      "claimable_amount": 0.40
    },
    "BNB": {
      "claimable_amount": 0.00133
    },
    "eligibility": {
      "is_eligible": true,
      "eligible_users_count": 83,
      "total_fund_usdt": 33.96,
      "fund_sources": {
        "spark_bonus_contribution": 10.69,
        "global_program_contribution": 23.27
      },
      "already_claimed": {
        "USDT": false,
        "BNB": false
      },
      "message": "Eligible for Triple Entry Reward"
    }
  },
  "status_code": 200,
  "success": true
}
```

### Response Fields
- `USDT.claimable_amount`: Amount user can claim in USDT (0 if already claimed today)
- `BNB.claimable_amount`: Amount user can claim in BNB (0 if already claimed today)
- `eligibility.is_eligible`: User eligible or not
- `eligibility.already_claimed`: Shows if claimed today for each currency
- `eligibility.fund_sources`: Breakdown of fund sources (Spark 20% + Global 5%)

### Use Case
```javascript
// Check if user can claim before showing claim button
const response = await fetch(`/spark/triple-entry/claimable-fund?user_id=${userId}`);
const data = await response.json();

if (data.data.USDT.claimable_amount > 0) {
  showClaimButton('USDT', data.data.USDT.claimable_amount);
}
```

---

## API 2: Get Claim History

### Endpoint (All Currencies)
```
GET /spark/triple-entry/history?user_id={user_id}
```

### Endpoint (Filtered)
```
GET /spark/triple-entry/history?user_id={user_id}&currency=USDT
GET /spark/triple-entry/history?user_id={user_id}&currency=BNB
```

### Purpose
View past claim history, optionally filtered by currency

### Response (All Currencies)
```json
{
  "status": "Ok",
  "message": "Triple Entry claim history fetched successfully",
  "data": {
    "USDT": {
      "claims": [
        {
          "id": "68e90d7c8dc5c8fe04c8c41c",
          "amount": 13.69863014,
          "status": "paid",
          "paid_at": "10 Oct 2025 (13:43)",
          "created_at": "10 Oct 2025 (13:43)",
          "tx_hash": "TER-USDT-...",
          "eligible_users_count": 73,
          "total_fund_amount": 1000.0
        }
      ],
      "total_claims": 1
    },
    "BNB": {
      "claims": [
        {
          "id": "68e90fb9d0401741b8db4f94",
          "amount": 0.0456621,
          "status": "paid",
          "paid_at": "10 Oct 2025 (13:52)",
          "created_at": "10 Oct 2025 (13:52)",
          "tx_hash": "TER-BNB-...",
          "eligible_users_count": 73,
          "total_fund_amount": 1000.0
        }
      ],
      "total_claims": 1
    }
  },
  "status_code": 200,
  "success": true
}
```

### Response (Filtered by USDT)
```json
{
  "status": "Ok",
  "message": "Triple Entry claim history fetched successfully",
  "data": {
    "currency": "USDT",
    "claims": [
      {
        "id": "68e90d7c8dc5c8fe04c8c41c",
        "amount": 13.69863014,
        "status": "paid",
        "paid_at": "10 Oct 2025 (13:43)",
        "created_at": "10 Oct 2025 (13:43)",
        "tx_hash": "TER-USDT-...",
        "eligible_users_count": 73,
        "total_fund_amount": 1000.0
      }
    ],
    "total_claims": 1
  },
  "status_code": 200,
  "success": true
}
```

### Use Case
```javascript
// Show all history
const allHistory = await fetch(`/spark/triple-entry/history?user_id=${userId}`);

// Show only USDT history
const usdtHistory = await fetch(`/spark/triple-entry/history?user_id=${userId}&currency=USDT`);

// Show only BNB history
const bnbHistory = await fetch(`/spark/triple-entry/history?user_id=${userId}&currency=BNB`);
```

---

## API 3: Claim Reward

### Endpoint
```
POST /spark/triple-entry/claim?user_id={user_id}&currency={USDT|BNB}
```

### Purpose
Process Triple Entry Reward claim for specific currency

### Query Parameters
- `user_id` (required): User ID
- `currency` (required): Currency to claim (USDT or BNB)

### Response (Success)
```json
{
  "status": "Ok",
  "message": "Triple Entry Reward of 0.40 USDT claimed successfully",
  "data": {
    "success": true,
    "payment_id": "68e90d7c8dc5c8fe04c8c41c",
    "amount": 0.40,
    "currency": "USDT",
    "tx_hash": "TER-USDT-...",
    "wallet_credited": true,
    "fund_deducted": true
  },
  "status_code": 200,
  "success": true
}
```

### Response (Error - Already Claimed)
```json
{
  "status": "Error",
  "message": "No claimable amount for USDT or already claimed today",
  "status_code": 400,
  "success": false
}
```

### Use Case
```javascript
// Claim USDT
const claimResult = await fetch(
  `/spark/triple-entry/claim?user_id=${userId}&currency=USDT`,
  { method: 'POST' }
);
```

---

## API Comparison

| API | Endpoint | Purpose | Returns Claimable | Returns History |
|-----|----------|---------|-------------------|-----------------|
| **Claimable Fund** | `/claimable-fund` | Check amounts | ✅ USDT & BNB | ❌ No |
| **History (All)** | `/history` | View all history | ❌ No | ✅ USDT & BNB |
| **History (Filtered)** | `/history?currency=USDT` | View specific currency | ❌ No | ✅ USDT only |
| **Claim** | `/claim` (POST) | Process claim | ❌ No | ❌ No |

---

## Frontend Integration Examples

### Example 1: Check Claimable Before Showing Button
```javascript
// Step 1: Get claimable amounts
const claimableResponse = await fetch(
  `/spark/triple-entry/claimable-fund?user_id=${userId}`
);
const claimableData = await claimableResponse.json();

// Step 2: Show claim buttons if amounts > 0
if (claimableData.data.USDT.claimable_amount > 0) {
  showClaimButton('USDT', claimableData.data.USDT.claimable_amount);
}

if (claimableData.data.BNB.claimable_amount > 0) {
  showClaimButton('BNB', claimableData.data.BNB.claimable_amount);
}

// Step 3: Show eligibility info
console.log('Eligible:', claimableData.data.eligibility.is_eligible);
console.log('Total Fund:', claimableData.data.eligibility.total_fund_usdt);
```

### Example 2: Show Complete History
```javascript
// Get all history (both currencies)
const historyResponse = await fetch(
  `/spark/triple-entry/history?user_id=${userId}`
);
const historyData = await historyResponse.json();

// Display USDT history
displayHistory('USDT', historyData.data.USDT.claims);

// Display BNB history
displayHistory('BNB', historyData.data.BNB.claims);
```

### Example 3: Currency-Specific History
```javascript
// Get only USDT history
const usdtHistoryResponse = await fetch(
  `/spark/triple-entry/history?user_id=${userId}&currency=USDT`
);
const usdtHistory = await usdtHistoryResponse.json();

// Display
displayHistory(usdtHistory.data.currency, usdtHistory.data.claims);
```

### Example 4: Complete Flow
```javascript
async function tripleEntryPage(userId) {
  // 1. Get claimable amounts
  const claimable = await getClaimableFund(userId);
  displayClaimableAmounts(claimable.data);
  
  // 2. Get history (filtered by selected currency)
  const selectedCurrency = 'USDT'; // or from dropdown
  const history = await getHistory(userId, selectedCurrency);
  displayHistory(history.data);
  
  // 3. On claim button click
  async function onClaim(currency) {
    const result = await claimReward(userId, currency);
    if (result.success) {
      // Refresh both claimable and history
      refreshPage();
    }
  }
}
```

---

## Business Logic

### Claimable Amount Calculation
```
1. Get all eligible users (Binary + Matrix + Global joined)
2. Calculate total TER fund:
   - Spark Bonus fund × 20%
   - Global income × 5%
3. Per user share = Total fund / Eligible users count
4. Check if already claimed today (per currency)
5. Return claimable amount (0 if claimed or not eligible)
```

### Claim Process
```
1. Verify eligibility
2. Check if already claimed today for requested currency
3. Calculate claimable amount
4. Create payment record
5. Credit wallet
6. Deduct from fund sources
7. Return success with transaction details
```

---

## Key Features

✅ **Separate APIs** - Claimable vs History  
✅ **Currency Filter** - Optional filter on history API  
✅ **Dynamic Calculation** - Backend calculates from actual funds  
✅ **24h Limit** - Once per day per currency  
✅ **Fund Deduction** - Auto-deducts from sources  
✅ **Transparent** - Shows fund sources breakdown  

---

## Reference
- Implementation: `backend/modules/spark/service.py`
- Routes: `backend/modules/spark/router.py`
- Documentation: PROJECT_DOCUMENTATION.md Section 22

