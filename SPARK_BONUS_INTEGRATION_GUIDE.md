# Spark Bonus Dynamic Fund Collection - Integration Guide

## Overview
Spark Bonus fund is now **fully dynamic** and collects from Binary and Matrix slot activations per PROJECT_DOCUMENTATION.md.

---

## Fund Collection Logic

### Binary Slot Activation
When a user activates a Binary slot:
```python
from modules.spark.service import SparkService
from decimal import Decimal

# Example: User activates Binary Slot 3 worth 0.0088 BNB
slot_value = Decimal('0.0088')  # BNB value
slot_value_usd = slot_value * Decimal('600')  # Convert to USD (example rate)

spark_service = SparkService()
result = spark_service.contribute_to_spark_fund(
    amount=slot_value_usd,
    program='binary',
    slot_number=3,
    user_id=user_id
)

# Result:
# - 8% of slot value goes to Spark Bonus fund
# - BonusFund collection updated
# - total_collected and current_balance increased
```

### Matrix Slot Activation
When a user activates a Matrix slot:
```python
# Example: User activates Matrix Slot 1 worth $11
slot_value = Decimal('11')

result = spark_service.contribute_to_spark_fund(
    amount=slot_value,
    program='matrix',
    slot_number=1,
    user_id=user_id
)

# Result:
# - 8% of $11 = $0.88 goes to Spark Bonus fund
# - BonusFund collection updated
```

---

## Integration Points

### 1. Binary Service Integration
Add to `backend/modules/binary/service.py` (or wherever Binary activation happens):

```python
def activate_binary_slot(self, user_id: str, slot_number: int, amount: Decimal):
    # ... existing activation logic ...
    
    # Contribute 8% to Spark Bonus
    from modules.spark.service import SparkService
    spark_service = SparkService()
    
    spark_result = spark_service.contribute_to_spark_fund(
        amount=amount,
        program='binary',
        slot_number=slot_number,
        user_id=user_id
    )
    
    if spark_result.get('success'):
        print(f"✅ Contributed {spark_result['spark_contribution_8_percent']} to Spark Bonus")
    
    # ... rest of activation logic ...
```

### 2. Matrix Service Integration
Add to `backend/modules/matrix/service.py`:

```python
def join_matrix(self, user_id: str, referrer_id: str, tx_hash: str, amount: Decimal):
    # ... existing join logic ...
    
    # Contribute 8% to Spark Bonus
    from modules.spark.service import SparkService
    spark_service = SparkService()
    
    spark_result = spark_service.contribute_to_spark_fund(
        amount=amount,
        program='matrix',
        slot_number=1,  # or current slot
        user_id=user_id
    )
    
    if spark_result.get('success'):
        print(f"✅ Contributed {spark_result['spark_contribution_8_percent']} to Spark Bonus")
    
    # ... rest of join logic ...
```

---

## Fund Distribution

### Spark Bonus Fund Allocation (100%)
```
Total Spark Fund (collected from activations)
├─ 80% → Matrix Slot Users (slots 1-14)
│   ├─ Slot 1: 15%
│   ├─ Slot 2-5: 10% each
│   ├─ Slot 6: 7%
│   ├─ Slot 7-9: 6% each
│   └─ Slot 10-14: 4% each
│
└─ 20% → Triple Entry Reward
    + 5% from Global Program
    = 25% total TER fund
```

### Example Calculation
```
Binary Activations (total): $10,000
├─ 8% → Spark Bonus: $800

Matrix Activations (total): $5,000
├─ 8% → Spark Bonus: $400

Total Spark Fund = $1,200

Distribution:
├─ 80% ($960) → Matrix Slot Users
└─ 20% ($240) → Triple Entry Reward
    + Global 5% ($50)
    = $290 total TER
```

---

## API Methods

### 1. Contribute to Spark Fund
```python
SparkService.contribute_to_spark_fund(
    amount: Decimal,      # Slot activation amount
    program: str,         # 'binary' or 'matrix'
    slot_number: int,     # Optional
    user_id: str          # Optional
) -> Dict[str, Any]
```

**Returns:**
```json
{
  "success": true,
  "program": "matrix",
  "slot_number": 1,
  "activation_amount": 11.0,
  "spark_contribution_8_percent": 0.88,
  "new_balance": 1200.88,
  "message": "Contributed $0.88 (8%) to matrix Spark Bonus fund"
}
```

### 2. Get Spark Fund Info (Dynamic)
```python
SparkService.get_spark_bonus_fund_info() -> Dict[str, Any]
```

**Returns:**
```json
{
  "success": true,
  "currency": "USDT",
  "total_fund_amount": 1200.0,
  "available_amount": 1200.0,
  "sources": {
    "binary_8_percent": 800.0,
    "matrix_8_percent": 400.0
  },
  "is_dynamic": true,
  "updated_at": "2025-10-10T14:00:00"
}
```

### 3. Get Triple Entry Fund (Uses Spark 20%)
```python
SparkService.get_triple_entry_claimable_amount(user_id) -> Dict[str, Any]
```

**Calculation:**
```
Spark Fund: $1,200
├─ 20% for TER: $240

Global Income: $1,000
├─ 5% for TER: $50

Total TER Fund = $290
Per User (73 eligible) = $3.97
```

---

## Database Schema

### BonusFund Collection
```python
{
  "fund_type": "spark_bonus",
  "program": "binary" | "matrix",
  "total_collected": Decimal,     # Total 8% collected
  "total_distributed": Decimal,   # Total distributed to users
  "current_balance": Decimal,     # Available balance
  "status": "active",
  "last_distribution": DateTime,
  "created_at": DateTime,
  "updated_at": DateTime
}
```

---

## Implementation Checklist

- [x] ✅ Dynamic fund calculation in `get_spark_bonus_fund_info()`
- [x] ✅ Fund contribution method `contribute_to_spark_fund()`
- [x] ✅ Triple Entry uses 20% of dynamic Spark fund
- [x] ✅ Fund deduction on claim
- [ ] ⏳ Binary activation integration (call `contribute_to_spark_fund`)
- [ ] ⏳ Matrix activation integration (call `contribute_to_spark_fund`)
- [ ] ⏳ Slot upgrade integration

---

## Testing

### Test Fund Contribution
```python
from modules.spark.service import SparkService
from decimal import Decimal

service = SparkService()

# Test Binary contribution
result = service.contribute_to_spark_fund(
    amount=Decimal('100'),
    program='binary'
)
print(result)  # Should show $8 contributed

# Test Matrix contribution
result = service.contribute_to_spark_fund(
    amount=Decimal('11'),
    program='matrix'
)
print(result)  # Should show $0.88 contributed

# Check fund
fund_info = service.get_spark_bonus_fund_info()
print(fund_info['total_fund_amount'])  # Should show $8.88
```

---

## Key Points

1. **Dynamic Collection**: Fund grows with each activation
2. **8% Contribution**: Both Binary and Matrix contribute 8%
3. **20% for TER**: Triple Entry gets 20% of accumulated Spark fund
4. **80% for Slots**: Matrix slot users share 80%
5. **Fallback**: Uses env variable if no fund collected yet
6. **Deduction**: Fund decreases when distributed/claimed

---

## Reference
- PROJECT_DOCUMENTATION.md Section 22 (Spark Bonus)
- PROJECT_DOCUMENTATION.md Section 32 (Fund Distribution)

