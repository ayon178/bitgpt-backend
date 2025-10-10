# Triple Entry Reward API Documentation

## Overview
The Triple Entry Reward API provides endpoints to check claimable amounts and claim history for users who have joined all three programs (Binary, Matrix, and Global).

## Eligibility
- User must have joined **all three programs**:
  - Binary Program ✓
  - Matrix Program ✓
  - Global Program ✓

## Fund Distribution
- **Total TER Fund**: Configurable via `TRIPLE_ENTRY_FUND_USDT` env variable (default: $1000)
- **Distribution**: Equal distribution among all eligible users
- **Claim Frequency**: Once per 24 hours per currency

---

## API Endpoints

### 1. Get Triple Entry Claim History & Claimable Amount

**Endpoint**: `GET /spark/triple-entry/claim/history`

**Query Parameters**:
- `user_id` (required): User ID

**Response**:
```json
{
  "status": "Ok",
  "message": "Triple Entry Reward data fetched successfully",
  "data": {
    "USDT": {
      "claimable_amount": 13.69863014,
      "claims": [
        {
          "id": "68e90d7c8dc5c8fe04c8c41c",
          "amount": 13.69863014,
          "status": "paid",
          "paid_at": "10 Oct 2025 (13:43)",
          "created_at": "10 Oct 2025 (13:43)",
          "tx_hash": "TER-USDT-68dc13a98b174277bc40cc12-1760082204",
          "eligible_users_count": 73,
          "total_fund_amount": 1000.0
        }
      ],
      "total_claims": 1
    },
    "BNB": {
      "claimable_amount": 0.0456621,
      "claims": [],
      "total_claims": 0
    },
    "eligibility": {
      "is_eligible": true,
      "eligible_users_count": 73,
      "total_fund_usdt": 1000.0,
      "already_claimed": {
        "USDT": true,
        "BNB": false
      },
      "message": "Eligible for Triple Entry Reward"
    }
  },
  "status_code": 200,
  "success": true
}
```

**Response Fields**:

#### USDT Object:
- `claimable_amount`: Amount user can claim in USDT (0 if already claimed today)
- `claims`: Array of past USDT claim records
- `total_claims`: Total number of USDT claims

#### BNB Object:
- `claimable_amount`: Amount user can claim in BNB (0 if already claimed today)
- `claims`: Array of past BNB claim records
- `total_claims`: Total number of BNB claims

#### Eligibility Object:
- `is_eligible`: Boolean indicating if user is eligible for TER
- `eligible_users_count`: Total number of eligible users (who joined all 3 programs)
- `total_fund_usdt`: Total TER fund in USDT
- `already_claimed`: Object showing if user already claimed today for each currency
- `message`: Eligibility status message

---

### 2. Claim Triple Entry Reward

**Endpoint**: `POST /spark/triple-entry/claim`

**Query Parameters**:
- `user_id` (required): User ID
- `currency` (required): Currency to claim (USDT or BNB)

**Response** (Success):
```json
{
  "status": "Ok",
  "message": "Triple Entry Reward of 13.69863014 USDT claimed successfully",
  "data": {
    "success": true,
    "payment_id": "68e90d7c8dc5c8fe04c8c41c",
    "amount": 13.69863014,
    "currency": "USDT",
    "tx_hash": "TER-USDT-68dc13a98b174277bc40cc12-1760082204",
    "wallet_credited": true
  },
  "status_code": 200,
  "success": true
}
```

**Response** (Error - Already Claimed):
```json
{
  "status": "Error",
  "message": "No claimable amount for USDT or already claimed today",
  "status_code": 400,
  "success": false
}
```

**Response** (Error - Not Eligible):
```json
{
  "status": "Error",
  "message": "User is not eligible for Triple Entry Reward",
  "status_code": 400,
  "success": false
}
```

---

## Business Logic

### Claimable Amount Calculation
1. Get all users who joined Binary, Matrix, and Global programs
2. Calculate: `Per User Share = Total TER Fund / Total Eligible Users`
3. Convert to BNB using rate: `BNB Amount = USDT Amount / Exchange Rate`
4. Check if user already claimed today for the specific currency
5. Return claimable amount (0 if already claimed)

### Claim Process
1. Verify user eligibility (all 3 programs joined)
2. Check if user already claimed today for the requested currency
3. Calculate per-user share
4. Create payment record in `triple_entry_payments` collection
5. Credit user's wallet
6. Return success response with transaction details

### 24-Hour Claim Cooldown
- Users can claim once per 24 hours **per currency**
- USDT and BNB claims are tracked separately
- Example: User can claim USDT today and BNB tomorrow (or both on different days)

---

## Frontend Integration

### Example Usage:

```javascript
// Get Triple Entry data for user
const response = await fetch(`/spark/triple-entry/claim/history?user_id=${userId}`);
const data = await response.json();

// Access USDT data
const usdtClaimable = data.data.USDT.claimable_amount;
const usdtClaims = data.data.USDT.claims;

// Access BNB data
const bnbClaimable = data.data.BNB.claimable_amount;
const bnbClaims = data.data.BNB.claims;

// Check eligibility
const isEligible = data.data.eligibility.is_eligible;
const alreadyClaimedUSDT = data.data.eligibility.already_claimed.USDT;
const alreadyClaimedBNB = data.data.eligibility.already_claimed.BNB;

// Claim USDT
const claimResponse = await fetch(`/spark/triple-entry/claim?user_id=${userId}&currency=USDT`, {
  method: 'POST'
});
```

---

## Database Schema

### Collection: `triple_entry_payments`

```python
{
  "user_id": ObjectId,
  "amount": Decimal,
  "currency": "USDT" | "BNB",
  "status": "pending" | "paid" | "failed",
  "paid_at": DateTime,
  "tx_hash": String,
  "eligible_users_count": Integer,
  "total_fund_amount": Decimal,
  "created_at": DateTime,
  "updated_at": DateTime
}
```

---

## Environment Variables

- `TRIPLE_ENTRY_FUND_USDT`: Total TER fund in USDT (default: 1000)
- `SPARK_USDT_PER_BNB`: Exchange rate for USDT to BNB conversion (default: 300)

---

## Testing

Test the API with:
```bash
# Get claim history
curl "http://localhost:8000/spark/triple-entry/claim/history?user_id=68dc13a98b174277bc40cc12"

# Claim USDT
curl -X POST "http://localhost:8000/spark/triple-entry/claim?user_id=68dc13a98b174277bc40cc12&currency=USDT"

# Claim BNB
curl -X POST "http://localhost:8000/spark/triple-entry/claim?user_id=68dc13a98b174277bc40cc12&currency=BNB"
```

---

## Implementation Details

### Files Modified/Created:
1. `backend/modules/spark/model.py` - Added `TripleEntryPayment` model
2. `backend/modules/spark/service.py` - Added TER service methods
3. `backend/modules/spark/router.py` - Added API endpoints

### Service Methods:
- `get_triple_entry_claimable_amount(user_id)`: Calculate claimable amounts
- `get_triple_entry_claim_history(user_id, currency)`: Get claim history
- `claim_triple_entry_reward(user_id, currency)`: Process claim

---

## Notes

- TER fund is **equally distributed** among all eligible users
- Users must join **all three programs** (Binary, Matrix, Global) to be eligible
- Each currency (USDT, BNB) has **separate** claim tracking
- Claim cooldown is **24 hours per currency**
- Wallet is automatically credited upon successful claim

