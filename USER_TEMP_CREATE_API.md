# Temporary User Registration API

## Overview
সহজ এবং দ্রুত user registration এর জন্য simplified API। এটি automatically wallet address, password, uid, এবং refer code generate করে।

## Endpoint

```
POST /user/temp-create
```

## Authentication
**Not Required** - Public endpoint for registration

## Request

### Request Body

```json
{
  "email": "john@example.com",
  "name": "John Doe",
  "refered_by": "RC12345"
}
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | User's email address (must be unique) |
| name | string | Yes | User's full name |
| refered_by | string | Yes | Referral code of the person who referred |

## Response

### Success Response (201 Created)

```json
{
  "status": "Ok",
  "message": "User created successfully with auto-generated credentials",
  "data": {
    "_id": "68ecf7e8689707dd9594ace0",
    "uid": "user17603604232884494",
    "refer_code": "RC1760360423575855",
    "name": "Temp Test User",
    "email": "temp_test_1760360422@example.com",
    "wallet_address": "0x087a74a9f04e2c7e12c5a02590e89ec7b04f87b6",
    "auto_password": "O2M77HLzN8-5_RC-G4Lh1Q",
    "refered_by": "68e38bb4ba0e8a58e0537a3b",
    "refered_by_code": "LS8991",
    "refered_by_name": "userLS1_1759742899",
    "binary_joined": true,
    "matrix_joined": false,
    "global_joined": false,
    "created_at": "2025-10-13T13:00:24.116000",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| _id | string | User's MongoDB ObjectId |
| uid | string | Auto-generated unique user identifier |
| refer_code | string | Auto-generated referral code for this user |
| name | string | User's full name |
| email | string | User's email address |
| wallet_address | string | 🔐 Auto-generated blockchain wallet address |
| auto_password | string | 🔐 Auto-generated password (user MUST save this!) |
| refered_by | string | Referrer's user ID |
| refered_by_code | string | Referral code used for registration |
| refered_by_name | string | Referrer's name |
| binary_joined | boolean | Binary program auto-joined (always true) |
| matrix_joined | boolean | Matrix program status |
| global_joined | boolean | Global program status |
| created_at | datetime | Account creation timestamp |
| token | string | 🔑 JWT access token for immediate login |
| token_type | string | Token type (always "bearer") |

### Error Responses

#### 400 Bad Request - Missing Fields
```json
{
  "status": "Error",
  "message": "Missing required fields: email"
}
```

#### 400 Bad Request - Email Already Exists
```json
{
  "status": "Error",
  "message": "User with this email already exists"
}
```

#### 400 Bad Request - Invalid Referral Code
```json
{
  "status": "Error",
  "message": "Referral code 'RC12345' not found"
}
```

## Auto-Generated Fields

### 🔐 Wallet Address
- Format: `0x` + 40 hexadecimal characters
- Example: `0x087a74a9f04e2c7e12c5a02590e89ec7b04f87b6`
- Uniqueness: Guaranteed unique in database

### 🔐 Password
- Format: URL-safe base64 encoded (16 bytes)
- Example: `O2M77HLzN8-5_RC-G4Lh1Q`
- Strength: Cryptographically secure random
- **⚠️ IMPORTANT**: User MUST save this password!

### 🆔 UID
- Format: `user` + timestamp (ms) + 4 random digits
- Example: `user17603604232884494`
- Uniqueness: Guaranteed unique

### 🎫 Refer Code
- Format: `RC` + timestamp (ms) + 3 random digits
- Example: `RC1760360423575855`
- Uniqueness: Guaranteed unique
- Usage: Other users can use this to refer

### 🔑 Access Token
- Format: JWT token
- Expiry: Based on system configuration
- Usage: Immediate login without additional authentication

## Business Logic

### Registration Flow

1. **Input Validation**
   - Checks required fields (email, name, refered_by)
   - Validates email doesn't already exist
   - Validates referral code exists

2. **Auto-Generation**
   - Creates unique wallet address
   - Generates strong random password
   - Creates unique uid
   - Creates unique refer_code

3. **User Creation**
   - Saves user to database
   - Hashes password for security
   - Sets role as "user"
   - Marks binary_joined as true

4. **Relationship Setup**
   - Creates PartnerGraph for new user
   - Updates referrer's PartnerGraph
   - Adds user to referrer's directs list
   - Increments referrer's binary count

5. **Token Generation**
   - Creates JWT access token
   - Token valid for immediate login

6. **Background Processing**
   - Triggers same background tasks as /user/create
   - Tree placement
   - Wallet initialization
   - Rank calculation

## Comparison with /user/create

| Feature | /user/create | /user/temp-create |
|---------|--------------|-------------------|
| Email | ✓ Required | ✓ Required |
| Name | ✓ Required | ✓ Required |
| Password | ✓ Required | ✅ Auto-generated |
| Wallet Address | ✓ Required | ✅ Auto-generated |
| Refered By | ✓ Required | ✓ Required |
| Binary Payment TX | Optional | ✅ Not needed |
| Returns Password | ✗ No | ✅ Yes (auto_password) |
| Returns Token | ✓ Yes | ✓ Yes |
| Background Tasks | ✓ Yes | ✓ Yes |

## Usage Examples

### Example 1: cURL

```bash
curl -X POST "http://localhost:8000/user/temp-create" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "name": "John Doe",
    "refered_by": "RC12345"
  }'
```

### Example 2: JavaScript (Fetch)

```javascript
const registerUser = async () => {
  const response = await fetch('http://localhost:8000/user/temp-create', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      email: 'john@example.com',
      name: 'John Doe',
      refered_by: 'RC12345'
    })
  });
  
  const data = await response.json();
  
  if (data.status === 'Ok') {
    console.log('User Created!');
    console.log('Email:', data.data.email);
    console.log('Password:', data.data.auto_password); // Save this!
    console.log('Wallet:', data.data.wallet_address);
    console.log('Token:', data.data.token); // Use for login
    
    // Store token for immediate login
    localStorage.setItem('access_token', data.data.token);
    
    // Show credentials to user (they must save the password!)
    alert(`Account created! Save these credentials:
      Email: ${data.data.email}
      Password: ${data.data.auto_password}
      Wallet: ${data.data.wallet_address}
    `);
  }
};

registerUser();
```

### Example 3: Python (requests)

```python
import requests

url = 'http://localhost:8000/user/temp-create'
payload = {
    'email': 'john@example.com',
    'name': 'John Doe',
    'refered_by': 'RC12345'
}

response = requests.post(url, json=payload)
data = response.json()

if data['status'] == 'Ok':
    user_data = data['data']
    print(f"User Created!")
    print(f"Email: {user_data['email']}")
    print(f"Password: {user_data['auto_password']}")  # Save this!
    print(f"Wallet: {user_data['wallet_address']}")
    print(f"Token: {user_data['token']}")
```

### Example 4: Frontend Form

```jsx
import React, { useState } from 'react';

function TempRegisterForm() {
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    refered_by: ''
  });
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const response = await fetch('/user/temp-create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });
    
    const data = await response.json();
    
    if (data.status === 'Ok') {
      setResult(data.data);
      
      // Store token
      localStorage.setItem('access_token', data.data.token);
      
      // Show success with credentials
      alert(`Registration successful! 
        
        SAVE THESE CREDENTIALS:
        Email: ${data.data.email}
        Password: ${data.data.auto_password}
        Wallet: ${data.data.wallet_address}
        
        You can login immediately!
      `);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input 
        type="email" 
        placeholder="Email"
        value={formData.email}
        onChange={(e) => setFormData({...formData, email: e.target.value})}
        required
      />
      <input 
        type="text" 
        placeholder="Full Name"
        value={formData.name}
        onChange={(e) => setFormData({...formData, name: e.target.value})}
        required
      />
      <input 
        type="text" 
        placeholder="Referral Code"
        value={formData.refered_by}
        onChange={(e) => setFormData({...formData, refered_by: e.target.value})}
        required
      />
      <button type="submit">Register</button>
      
      {result && (
        <div className="credentials-display">
          <h3>🎉 Account Created Successfully!</h3>
          <p><strong>Email:</strong> {result.email}</p>
          <p><strong>Password:</strong> {result.auto_password}</p>
          <p><strong>Wallet:</strong> {result.wallet_address}</p>
          <p><strong>UID:</strong> {result.uid}</p>
          <p><strong>Your Referral Code:</strong> {result.refer_code}</p>
          <p className="warning">⚠️ Please save your password! You cannot recover it.</p>
        </div>
      )}
    </form>
  );
}
```

## Important Notes

### ⚠️ Security Considerations

1. **Password Display**: 
   - Auto-generated password is returned in response
   - User MUST save this password immediately
   - Password cannot be recovered later
   - Consider showing a "copy to clipboard" button

2. **Token Usage**:
   - Token allows immediate login
   - Store securely (localStorage/sessionStorage)
   - Use for authenticated API calls

3. **Wallet Address**:
   - Auto-generated for convenience
   - User can update later if needed
   - Not a real blockchain wallet (just identifier)

### 📝 Best Practices

1. **Frontend Implementation**:
   ```javascript
   // Show credentials prominently
   // Provide copy-to-clipboard functionality
   // Warn user to save password
   // Auto-login user with token
   ```

2. **User Experience**:
   - Display all credentials clearly
   - Highlight the auto-generated password
   - Provide download/copy options
   - Confirm user has saved credentials

3. **Data Handling**:
   - Store token for immediate login
   - Clear sensitive data after display
   - Log user in automatically
   - Redirect to dashboard

## Use Cases

### Use Case 1: Quick Registration
Perfect for:
- Testing environments
- Demo accounts
- Rapid onboarding
- Simplified user experience

### Use Case 2: Admin User Creation
Admins can quickly create users without wallet setup:
- Provide email and name
- Share generated credentials with user
- User can login immediately

### Use Case 3: Bulk User Import
Programmatic user creation:
- Import from CSV/Excel
- Auto-generate all credentials
- Return tokens for each user

## Limitations

1. **No Blockchain Verification**: 
   - Wallet address is generated, not verified
   - No actual blockchain transaction required
   - Suitable for testing/demo purposes

2. **Password Recovery**:
   - Auto-generated password cannot be recovered
   - User must save it immediately
   - No "forgot password" for auto-generated passwords

3. **Email Uniqueness**:
   - Email must be unique
   - Cannot register twice with same email

## Testing

### Run Test Script
```bash
cd E:\bitgpt\backend
.\venv\Scripts\python.exe test_temp_create_user.py
```

### Test Results
✅ User created successfully  
✅ Wallet address: `0x087a74a9f04e2c7e12c5a02590e89ec7b04f87b6`  
✅ Password: `O2M77HLzN8-5_RC-G4Lh1Q`  
✅ UID: `user17603604232884494`  
✅ Refer Code: `RC1760360423575855`  
✅ Token generated: `eyJhbGci...`  
✅ Binary program joined  
✅ Database verification passed  

## Migration to Full Account

Users can later:
1. Update wallet address to real blockchain wallet
2. Change auto-generated password
3. Add blockchain payment proofs
4. Verify email address
5. Complete KYC if required

## Related APIs

- **Full Registration**: `POST /user/create` - Full user creation with all fields
- **Login**: `POST /auth/login` - Login with email/password
- **Update Profile**: `PUT /user/profile` - Update user information

## Summary

### ✅ What Gets Auto-Generated
1. Wallet Address (0x + 40 hex chars)
2. Password (strong random)
3. UID (user + timestamp + random)
4. Refer Code (RC + timestamp + random)
5. Access Token (JWT)

### ✅ What Frontend Provides
1. Email
2. Name
3. Refered By (referral code)

### ✅ What Gets Returned
1. All auto-generated credentials
2. Full user data
3. Access token for immediate login
4. Referrer information

**Perfect for rapid testing and simplified registration! 🚀**

