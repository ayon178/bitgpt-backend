# Pools Summary Fix Verification Guide

## সমস্যা কি ছিল?

যখন নতুন user create করা হত এবং automatically Binary program এ join হত:
- ✅ IncomeEvent তৈরি হচ্ছিল
- ✅ BonusFund update হচ্ছিল
- ❌ **WalletLedger এ credit entry হচ্ছিল না**

ফলে `/wallet/pools-summary` API তে কোনো পরিবর্তন দেখা যেত না।

## কি পরিবর্তন করেছি?

`backend/modules/fund_distribution/service.py` এর `_create_income_event` method এ:

1. **Partner Incentive** এর জন্য WalletLedger এ credit করার logic যুক্ত করেছি
2. **Level Distribution** (Dual Tree Earning) এর জন্যও WalletLedger এ credit করার logic যুক্ত করেছি
3. Proper `reason` field তৈরি করেছি যা pools-summary এ map হয়:
   - `binary_partner_incentive` → maps to `binary_partner_incentive` pool
   - `binary_dual_tree_level_1` → maps to `duel_tree` pool

## কিভাবে Verify করবেন?

### Step 1: Current Pools Summary Check করুন

```bash
# RC1760429616945918 এর user_id দিয়ে pools summary check করুন
GET http://localhost:8000/wallet/pools-summary?user_id=<USER_ID>
```

Response এ দেখবেন:
```json
{
  "success": true,
  "data": {
    "pools": {
      "binary_partner_incentive": {
        "USDT": 0,
        "BNB": X.XXXX  // এই মান note করুন
      },
      "duel_tree": {
        "USDT": 0,
        "BNB": Y.YYYY  // এই মান note করুন
      },
      ...
    }
  }
}
```

### Step 2: নতুন User Create করুন

```bash
POST http://localhost:8000/user/create-temp
{
  "refered_by_code": "RC1760429616945918",
  "wallet_address": "0x...",
  "name": "Test User"
}
```

নতুন user automatically:
1. Binary program এ join হবে
2. Slot 1 & 2 activate হবে (0.0022 BNB + 0.0044 BNB = 0.0066 BNB)
3. Parent user কে distribute করবে:
   - **Partner Incentive**: 10% of 0.0066 BNB = 0.00066 BNB
   - **Level Distribution**: 60% of 0.0066 BNB = 0.00396 BNB (level 1 পাবে 30%)

### Step 3: Updated Pools Summary Check করুন

আবার pools summary call করুন:

```bash
GET http://localhost:8000/wallet/pools-summary?user_id=<USER_ID>
```

এখন দেখবেন:
```json
{
  "success": true,
  "data": {
    "pools": {
      "binary_partner_incentive": {
        "USDT": 0,
        "BNB": X.XXXX + 0.00066  // বেড়েছে!
      },
      "duel_tree": {
        "USDT": 0,
        "BNB": Y.YYYY + amount  // বেড়েছে!
      },
      ...
    }
  }
}
```

## Expected Calculations

নতুন user এর জন্য (Slot 1 + 2 = 0.0066 BNB):

### Binary Fund Distribution (100%):
1. **Spark Bonus (8%)**: 0.000528 BNB → BonusFund
2. **Royal Captain (4%)**: 0.000264 BNB → BonusFund
3. **President Reward (3%)**: 0.000198 BNB → BonusFund
4. **Leadership Stipend (5%)**: 0.00033 BNB → BonusFund
5. **Jackpot (5%)**: 0.00033 BNB → BonusFund
6. **Partner Incentive (10%)**: 0.00066 BNB → **Parent User Wallet** ✅
7. **Shareholders (5%)**: 0.00033 BNB → BonusFund
8. **Level Distribution (60%)**: 0.00396 BNB → **Tree Uplines Wallets** ✅
   - Level 1 (30% of 60%): 0.001188 BNB → **Parent User Wallet** ✅
   - Level 2-16: Distributed to uplines based on percentages

### Total Parent User Should Receive:
- **Binary Partner Incentive**: 0.00066 BNB
- **Duel Tree (Level 1)**: 0.001188 BNB (if parent is level 1 upline)
- **Total**: ~0.001848 BNB (minimum, more if also in higher levels)

## WalletLedger Entries

Check database তে WalletLedger collection এ নতুন entries:

```javascript
// Binary Partner Incentive
{
  user_id: <PARENT_USER_OBJECTID>,
  type: "credit",
  amount: 0.00066,
  currency: "BNB",
  reason: "binary_partner_incentive",
  tx_hash: "AUTO-...",
  created_at: ...
}

// Dual Tree Level 1
{
  user_id: <PARENT_USER_OBJECTID>,
  type: "credit",
  amount: 0.001188,
  currency: "BNB",
  reason: "binary_dual_tree_level_1",
  tx_hash: "AUTO-...",
  created_at: ...
}
```

## Troubleshooting

যদি pools-summary তে এখনো পরিবর্তন না আসে:

1. **Backend server restart করুন**: পরিবর্তিত code load হওয়ার জন্য
2. **WalletLedger check করুন**: Database তে entry হয়েছে কিনা
3. **Console logs check করুন**: Backend এ error আছে কিনা
4. **User join confirmation**: User কি সত্যিই binary এ join হয়েছে

## Summary

এখন থেকে যখনই নতুন user create হবে:
- ✅ IncomeEvent তৈরি হবে (history tracking)
- ✅ BonusFund update হবে (pool balance)
- ✅ **WalletLedger এ credit হবে (user wallet)**
- ✅ **Pools Summary তে দেখা যাবে**

---

**Note**: এই fix শুধুমাত্র **নতুন users** এর জন্য কাজ করবে। পুরনো users যারা already create হয়ে গেছে, তাদের জন্য আলাদা migration script লাগবে যদি pools summary update করতে চান।

