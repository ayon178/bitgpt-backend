# Earning Statistics API - Postman Testing Guide

## 🎯 Quick Start

### Endpoint
```
GET http://localhost:8000/wallet/earning-statistics/{user_id}
```

## 📋 Postman Setup Steps

### 1. Create New Request
- Method: **GET**
- URL: `http://localhost:8000/wallet/earning-statistics/68dc13a98b174277bc40cc12`
  - Replace `68dc13a98b174277bc40cc12` with your actual user_id

### 2. Set Headers
Add the following header:
```
Key: Authorization
Value: Bearer YOUR_AUTH_TOKEN
```

### 3. Send Request

Expected response:
```json
{
    "success": true,
    "message": "Earning statistics fetched successfully",
    "data": {
        "binary": {
            "total_earnings": {
                "USDT": 0.0,
                "BNB": 0.142032
            },
            "highest_activated_slot": 2,
            "highest_activated_slot_name": "CONTRIBUTOR",
            "activated_at": "2025-09-30T17:35:06.249000"
        },
        "matrix": {
            "total_earnings": {
                "USDT": 101.2,
                "BNB": 0.0
            },
            "highest_activated_slot": 0,
            "highest_activated_slot_name": "N/A",
            "activated_at": null
        },
        "global": {
            "total_earnings": {
                "USDT": 264.0,
                "BNB": 0.0
            },
            "highest_activated_slot": 1,
            "highest_activated_slot_name": "FOUNDATION",
            "activated_at": "2025-09-30T18:16:06.334000"
        }
    }
}
```

## 🔧 Complete Postman Collection JSON

Copy and import this into Postman:

```json
{
    "info": {
        "name": "Earning Statistics API",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [
        {
            "name": "Get Earning Statistics",
            "request": {
                "method": "GET",
                "header": [
                    {
                        "key": "Authorization",
                        "value": "Bearer {{auth_token}}",
                        "type": "text"
                    }
                ],
                "url": {
                    "raw": "{{base_url}}/wallet/earning-statistics/{{user_id}}",
                    "host": ["{{base_url}}"],
                    "path": ["wallet", "earning-statistics", "{{user_id}}"]
                }
            },
            "response": []
        }
    ],
    "variable": [
        {
            "key": "base_url",
            "value": "http://localhost:8000"
        },
        {
            "key": "user_id",
            "value": "68dc13a98b174277bc40cc12"
        },
        {
            "key": "auth_token",
            "value": "YOUR_TOKEN_HERE"
        }
    ]
}
```

## 🧪 Test Scenarios

### ✅ Success Case (200 OK)
**Request:**
```
GET /wallet/earning-statistics/68dc13a98b174277bc40cc12
Authorization: Bearer valid_token
```

**Response:**
```json
{
    "success": true,
    "message": "Earning statistics fetched successfully",
    "data": { ... }
}
```

### ❌ Unauthorized (403 Forbidden)
**Scenario:** User trying to access another user's data

**Request:**
```
GET /wallet/earning-statistics/OTHER_USER_ID
Authorization: Bearer user_token
```

**Response:**
```json
{
    "success": false,
    "error": "Unauthorized to view this user's earning statistics"
}
```

### ❌ No Authentication (401 Unauthorized)
**Request:**
```
GET /wallet/earning-statistics/68dc13a98b174277bc40cc12
(No Authorization header)
```

**Response:**
```json
{
    "detail": "Unauthorized"
}
```

### ❌ Invalid User ID (400 Bad Request)
**Request:**
```
GET /wallet/earning-statistics/invalid_id
Authorization: Bearer valid_token
```

**Response:**
```json
{
    "success": false,
    "error": "Failed to fetch earning statistics"
}
```

## 📊 Response Fields Explanation

### Binary Program Fields
- `total_earnings.USDT`: Total USDT earned from binary program
- `total_earnings.BNB`: Total BNB earned from binary program
- `highest_activated_slot`: Highest slot number activated (0 if none)
- `highest_activated_slot_name`: Name of the highest slot (e.g., EXPLORER, CONTRIBUTOR)
- `activated_at`: ISO timestamp of when slot was activated

### Matrix Program Fields
- Same structure as Binary
- Tracks matrix-specific earnings and slots

### Global Program Fields
- Same structure as Binary
- Tracks global program earnings and slots

## 🔍 How to Get Auth Token

1. **Login First:**
```
POST http://localhost:8000/auth/login
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "your_password"
}
```

2. **Copy Token from Response:**
```json
{
    "success": true,
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ...
    }
}
```

3. **Use in Authorization Header:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 💡 Tips

1. **Save as Environment Variable:**
   - Create a Postman environment
   - Save `base_url`, `user_id`, and `auth_token` as variables
   - Use `{{variable_name}}` in requests

2. **Use Pre-request Script for Auto-login:**
```javascript
// Pre-request Script
pm.sendRequest({
    url: pm.environment.get("base_url") + "/auth/login",
    method: 'POST',
    header: {'Content-Type': 'application/json'},
    body: {
        mode: 'raw',
        raw: JSON.stringify({
            email: pm.environment.get("email"),
            password: pm.environment.get("password")
        })
    }
}, function (err, res) {
    if (!err) {
        const token = res.json().data.access_token;
        pm.environment.set("auth_token", token);
    }
});
```

3. **Tests Script:**
```javascript
// Tests
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has success field", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('success');
    pm.expect(jsonData.success).to.be.true;
});

pm.test("Response has data field", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('data');
});

pm.test("Data has all programs", function () {
    const data = pm.response.json().data;
    pm.expect(data).to.have.property('binary');
    pm.expect(data).to.have.property('matrix');
    pm.expect(data).to.have.property('global');
});
```

## 🚀 Ready to Test!

Your earning statistics API is ready for testing in Postman. Just:
1. Import the collection
2. Set your auth token
3. Replace user_id
4. Send the request!

