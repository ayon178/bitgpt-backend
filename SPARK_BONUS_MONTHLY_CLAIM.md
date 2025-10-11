# Spark Bonus - Monthly Claim Limit

## Overview
Spark Bonus claim limit updated to **monthly basis** instead of daily.

---

## Claim Rules

### ✅ **Monthly Limit**
- **1 claim per MONTH per SLOT per CURRENCY**
- প্রতি মাসে 1 বার করে claim করতে পারবে

### 📊 **Per Slot Calculation**

#### For 1 Slot:
```
Month 1:
  - 1 × USDT claim
  - 1 × BNB claim
  ─────────────────
  Total: 2 claims

Month 2:
  - 1 × USDT claim
  - 1 × BNB claim
  ─────────────────
  Total: 2 claims

Over 2 Months: 4 claims total
```

#### For Multiple Slots:
```
If user has 3 Matrix slots (1, 2, 3):

Month 1:
  - Slot 1: USDT + BNB = 2 claims
  - Slot 2: USDT + BNB = 2 claims
  - Slot 3: USDT + BNB = 2 claims
  ─────────────────────────────────
  Total: 6 claims

Month 2:
  - Slot 1: USDT + BNB = 2 claims
  - Slot 2: USDT + BNB = 2 claims
  - Slot 3: USDT + BNB = 2 claims
  ─────────────────────────────────
  Total: 6 claims

Over 2 Months: 12 claims total
```

---

## API Behavior

### Endpoint
```
POST /spark/claim
```

### Query Parameters
- `slot_no` (required): Matrix slot number
- `currency` (required): USDT or BNB
- `claimer_user_id` (required): User ID

### Success Response
```json
{
  "success": true,
  "slot_no": 1,
  "currency": "USDT",
  "amount": 12.5,
  "eligible_users": 10,
  "message": "Spark bonus claimed successfully"
}
```

### Error Response (Already Claimed This Month)
```json
{
  "success": false,
  "error": "Already claimed for slot 1 (USDT) this month",
  "last_claim_date": "05 Oct 2025",
  "next_claim_date": "01 Nov 2025",
  "message": "You can claim again from 01 Nov 2025"
}
```

---

## Implementation Details

### Monthly Check Logic
```python
# Get start of current month
now = datetime.utcnow()
month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

# Check if already claimed this month for this slot+currency
existing_claim = SparkBonusDistribution.objects(
    user_id=ObjectId(claimer_user_id), 
    slot_number=slot_no, 
    currency=currency, 
    created_at__gte=month_start
).first()

if existing_claim:
    # Calculate next claim date (next month)
    import calendar
    last_day = calendar.monthrange(now.year, now.month)[1]
    next_claim_date = now.replace(day=last_day, hour=23, minute=59, second=59) + timedelta(seconds=1)
    
    return {
        "success": False,
        "error": f"Already claimed for slot {slot_no} ({currency}) this month",
        "last_claim_date": existing_claim.created_at.strftime("%d %b %Y"),
        "next_claim_date": next_claim_date.strftime("%d %b %Y"),
        "message": f"You can claim again from {next_claim_date.strftime('%d %b %Y')}"
    }
```

### Database Query
```python
# Find existing claim in current month
SparkBonusDistribution.objects(
    user_id=ObjectId(user_id),
    slot_number=slot_no,
    currency=currency,
    created_at__gte=month_start
).first()
```

---

## Key Changes

### ❌ Old (Daily Limit)
```python
# Daily check
day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
existing_claim = SparkBonusDistribution.objects(
    user_id=ObjectId(claimer_user_id), 
    slot_number=slot_no, 
    currency=currency, 
    created_at__gte=day_start
).first()

if existing_claim:
    return {"success": False, "error": "Already claimed for this slot today"}
```

### ✅ New (Monthly Limit)
```python
# Monthly check
now = datetime.utcnow()
month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
existing_claim = SparkBonusDistribution.objects(
    user_id=ObjectId(claimer_user_id), 
    slot_number=slot_no, 
    currency=currency, 
    created_at__gte=month_start
).first()

if existing_claim:
    # Calculate next month
    last_day = calendar.monthrange(now.year, now.month)[1]
    next_claim_date = now.replace(day=last_day, hour=23, minute=59, second=59) + timedelta(seconds=1)
    
    return {
        "success": False,
        "error": f"Already claimed for slot {slot_no} ({currency}) this month",
        "last_claim_date": existing_claim.created_at.strftime("%d %b %Y"),
        "next_claim_date": next_claim_date.strftime("%d %b %Y"),
        "message": f"You can claim again from {next_claim_date.strftime('%d %b %Y')}"
    }
```

---

## Example Scenarios

### Scenario 1: First Claim of the Month
```
Date: October 5, 2025
Action: User claims Slot 1 USDT

Result: ✅ Success
Next allowed: October 5, 2025 for BNB (different currency)
Next USDT claim: November 1, 2025
```

### Scenario 2: Try to Claim Same Currency Again
```
Date: October 5, 2025
Action: User claims Slot 1 USDT (first time)
Result: ✅ Success

Date: October 10, 2025
Action: User tries to claim Slot 1 USDT again
Result: ❌ Error
Message: "Already claimed for slot 1 (USDT) this month"
Last Claim: "05 Oct 2025"
Next Claim: "01 Nov 2025"
```

### Scenario 3: Different Currency Same Month
```
Date: October 5, 2025
Action: User claims Slot 1 USDT
Result: ✅ Success

Date: October 10, 2025
Action: User claims Slot 1 BNB
Result: ✅ Success (different currency)

Date: October 15, 2025
Action: User tries to claim Slot 1 USDT again
Result: ❌ Error (already claimed USDT this month)
```

### Scenario 4: Different Slot Same Month
```
Date: October 5, 2025
Action: User claims Slot 1 USDT
Result: ✅ Success

Date: October 10, 2025
Action: User claims Slot 2 USDT
Result: ✅ Success (different slot)

Date: October 15, 2025
Action: User claims Slot 3 USDT
Result: ✅ Success (different slot)
```

### Scenario 5: Next Month
```
Date: October 5, 2025
Action: User claims Slot 1 USDT
Result: ✅ Success

Date: November 1, 2025
Action: User claims Slot 1 USDT again
Result: ✅ Success (new month started)
```

---

## Frontend Integration

### Check Claimable Status
```javascript
async function claimSparkBonus(slotNo, currency, userId) {
  try {
    const response = await fetch(
      `/spark/claim?slot_no=${slotNo}&currency=${currency}&claimer_user_id=${userId}`,
      { method: 'POST' }
    );
    
    const result = await response.json();
    
    if (!result.success) {
      // Show error with next claim date
      alert(`${result.error}\n\n${result.message}`);
      
      // Display in UI
      document.getElementById('next-claim').innerText = 
        `Next claim available: ${result.next_claim_date}`;
    } else {
      alert(`Successfully claimed ${result.amount} ${result.currency}!`);
      refreshClaimHistory();
    }
  } catch (error) {
    console.error('Claim error:', error);
  }
}
```

### Display Next Claim Date
```javascript
function displayClaimStatus(lastClaimDate, nextClaimDate) {
  const statusDiv = document.getElementById('claim-status');
  
  if (lastClaimDate) {
    statusDiv.innerHTML = `
      <div class="alert alert-info">
        <p>Last claimed: ${lastClaimDate}</p>
        <p>Next claim available: ${nextClaimDate}</p>
      </div>
    `;
    
    // Disable claim button
    document.getElementById('claim-btn').disabled = true;
  } else {
    // Enable claim button
    document.getElementById('claim-btn').disabled = false;
  }
}
```

---

## Database Schema

### SparkBonusDistribution Collection
```python
{
  "_id": ObjectId,
  "user_id": ObjectId,           # User who claimed
  "slot_number": int,             # Matrix slot (1-14)
  "distribution_amount": Decimal, # Amount claimed
  "currency": str,                # USDT or BNB
  "fund_source": "spark_bonus",
  "status": "completed",
  "created_at": datetime,         # Used for monthly check
  "distributed_at": datetime,
  ...
}
```

### Index for Performance
```python
# Composite index for fast monthly lookup
db.spark_bonus_distributions.createIndex({
  "user_id": 1,
  "slot_number": 1,
  "currency": 1,
  "created_at": -1
})
```

---

## Benefits

✅ **Fair Distribution** - Each user gets equal opportunity per month  
✅ **Multiple Assets** - Can claim both USDT and BNB  
✅ **Scalable** - Works for multiple slots  
✅ **Clear Messaging** - Shows exact next claim date  
✅ **Database Efficient** - Single query with date filter  

---

## Reference

- Implementation: `backend/modules/spark/service.py` → `claim_spark_bonus()`
- Model: `backend/modules/spark/model.py` → `SparkBonusDistribution`
- Documentation: `PROJECT_DOCUMENTATION.md` Section 22

---

## Summary

| Aspect | Value |
|--------|-------|
| **Claim Frequency** | 1 time per MONTH |
| **Per Slot** | 2 claims/month (USDT + BNB) |
| **Per 2 Months** | 4 claims (2 USDT + 2 BNB) |
| **Multiple Slots** | Independent claims for each slot |
| **Reset Time** | 1st day of next month (00:00:00) |

**Implementation Status: ✅ Complete**

