# Earning Statistics API Documentation

## Overview
This API provides comprehensive earning statistics for users across all programs (Binary, Matrix, Global). It calculates total earnings from the `wallet_ledger` collection and shows the highest activated slot for each program.

## Endpoint

### GET `/wallet/earning-statistics/{user_id}`

Get earning statistics for a specific user.

#### Parameters
- **user_id** (path parameter): The user's MongoDB ObjectId as a string

#### Authentication
- Requires valid authentication token
- Users can only view their own statistics (unless admin)

#### Response Format

```json
{
    "success": true,
    "message": "Earning statistics fetched successfully",
    "data": {
        "binary": {
            "total_earnings": {
                "USDT": 0.0,
                "BNB": 0.05544
            },
            "highest_activated_slot": 2,
            "highest_activated_slot_name": "CONTRIBUTOR",
            "activated_at": "2025-09-30T17:35:06.249000"
        },
        "matrix": {
            "total_earnings": {
                "USDT": 15.4,
                "BNB": 0.0
            },
            "highest_activated_slot": 3,
            "highest_activated_slot_name": "SILVER",
            "activated_at": "2025-09-30T17:42:55.705000"
        },
        "global": {
            "total_earnings": {
                "USDT": 358.6,
                "BNB": 0.0
            },
            "highest_activated_slot": 8,
            "highest_activated_slot_name": "APEX",
            "activated_at": "2025-09-30T18:16:06.334000"
        }
    }
}
```

## How It Works

### Earnings Calculation
The API calculates earnings from the `wallet_ledger` collection based on the `reason` field:

1. **Binary Earnings**: All entries where `reason` starts with `binary_`
   - Examples: `binary_joining_commission`, `binary_upgrade_level_1`, `binary_dual_tree_L1_S1`, `binary_dual_tree_L1_S2`

2. **Matrix Earnings**: All entries where `reason` starts with `matrix_`
   - Examples: `matrix_joining_commission`, `matrix_partner_incentive`, `matrix_level_income`

3. **Global Earnings**: All entries where `reason` starts with `global_`
   - Examples: `global_joining_commission`, `global_partner_incentive`, `global_phase_income`

### Slot Information
The highest activated slot is fetched from the `slot_activation` collection where:
- `user_id` matches the requested user
- `program` matches the specific program (binary/matrix/global)
- `status` is 'completed'
- Ordered by `slot_no` in descending order (highest first)

## Example Usage

### cURL
```bash
curl -X GET "http://localhost:8000/wallet/earning-statistics/68dc13a98b174277bc40cc12" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

### Python (requests)
```python
import requests

user_id = "68dc13a98b174277bc40cc12"
headers = {
    "Authorization": "Bearer YOUR_AUTH_TOKEN"
}

response = requests.get(
    f"http://localhost:8000/wallet/earning-statistics/{user_id}",
    headers=headers
)

data = response.json()
print(f"Binary Earnings: {data['data']['binary']['total_earnings']}")
print(f"Matrix Highest Slot: {data['data']['matrix']['highest_activated_slot']}")
```

### JavaScript (fetch)
```javascript
const userId = "68dc13a98b174277bc40cc12";

fetch(`http://localhost:8000/wallet/earning-statistics/${userId}`, {
  headers: {
    'Authorization': 'Bearer YOUR_AUTH_TOKEN'
  }
})
.then(response => response.json())
.then(data => {
  console.log('Binary Earnings:', data.data.binary.total_earnings);
  console.log('Global Highest Slot:', data.data.global.highest_activated_slot);
});
```

## Error Responses

### 403 Forbidden
User trying to access another user's statistics (unless admin):
```json
{
    "success": false,
    "error": "Unauthorized to view this user's earning statistics"
}
```

### 400 Bad Request
Error during data fetching:
```json
{
    "success": false,
    "error": "Failed to fetch earning statistics"
}
```

### 401 Unauthorized
Invalid or missing authentication token:
```json
{
    "detail": "Unauthorized"
}
```

## Database Collections Used

1. **wallet_ledger**: For calculating earnings
   - Fields: `user_id`, `amount`, `currency`, `type`, `reason`

2. **slot_activation**: For getting highest activated slots
   - Fields: `user_id`, `program`, `slot_no`, `slot_name`, `status`, `activated_at`

## Notes

- All earnings are separated by currency (USDT and BNB)
- Only 'credit' type transactions are counted as earnings
- If no slots are activated for a program, `highest_activated_slot` will be 0
- The `activated_at` timestamp uses the activation date or creation date from slot_activation
- Response amounts are in float format for easy frontend consumption

