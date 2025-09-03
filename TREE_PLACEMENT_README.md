# Tree Placement System Documentation

## Overview
এই সিস্টেমটি **বাইনারি ট্রি প্লেসমেন্ট লজিক** implement করে যা আপনার বর্ণিত দুটি scenario handle করে:

### Scenario 1: Direct Referral
- **Condition**: Referrer এর নিচে 2টি position এর কম filled আছে
- **Logic**: 
  - প্রথমে left position check করে
  - যদি left খালি থাকে → left এ place করে
  - যদি left filled থাকে কিন্তু right খালি থাকে → right এ place করে
  - যদি দুটোই filled থাকে → direct placement সম্ভব নয়

### Scenario 2: Indirect Referral (Spillover)
- **Condition**: Referrer এর নিচে সব position filled
- **Logic**:
  - Lowest level খুঁজে বের করে
  - প্রথমে left position check করে
  - তারপর right position check করে
  - যেখানে প্রথমে space পাবে সেখানে place করে

## API Endpoints

### 1. Create Tree Placement
```
POST /tree/placement
```

**Request Body:**
```json
{
  "user_id": "507f1f77bcf86cd799439011",
  "referrer_id": "507f1f77bcf86cd799439012", 
  "program": "binary",
  "slot_no": 1
}
```

**Response:**
```json
{
  "success": true,
  "message": "Tree placement created successfully (direct referral)",
  "data": {
    "id": "507f1f77bcf86cd799439013",
    "user_id": "507f1f77bcf86cd799439011",
    "program": "binary",
    "parent_id": "507f1f77bcf86cd799439012",
    "position": "left",
    "level": 2,
    "slot_no": 1,
    "is_active": true,
    "created_at": "2024-01-15T13:45:00Z",
    "updated_at": "2024-01-15T13:45:00Z"
  }
}
```

### 2. Get Tree Data
```
GET /tree/{user_id}/binary
GET /tree/{user_id}/matrix  
GET /tree/{user_id}/global
GET /tree/{user_id}/all
```

## Database Schema

### TreePlacement Collection
```javascript
{
  user_id: ObjectId,           // User ID
  program: String,              // 'binary', 'matrix', 'global'
  parent_id: ObjectId,         // Parent user ID
  position: String,            // 'left', 'right', 'center'
  level: Number,               // Tree level
  slot_no: Number,             // Slot/tree number
  is_active: Boolean,          // Active status
  created_at: Date,           // Creation timestamp
  updated_at: Date            // Update timestamp
}
```

## Usage Examples

### Frontend Integration
```javascript
// Create tree placement
const createPlacement = async (userId, referrerId) => {
  const response = await fetch('/tree/placement', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      user_id: userId,
      referrer_id: referrerId,
      program: 'binary',
      slot_no: 1
    })
  });
  
  const result = await response.json();
  return result;
};

// Get tree data
const getTreeData = async (userId) => {
  const response = await fetch(`/tree/${userId}/binary`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const result = await response.json();
  return result;
};
```

### cURL Examples
```bash
# Create placement
curl -X POST "http://localhost:8000/tree/placement" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "user_id": "507f1f77bcf86cd799439011",
    "referrer_id": "507f1f77bcf86cd799439012",
    "program": "binary",
    "slot_no": 1
  }'

# Get tree data
curl -X GET "http://localhost:8000/tree/507f1f77bcf86cd799439011/binary" \
  -H "Authorization: Bearer your_token"
```

## Testing

### Run Test Script
```bash
cd backend
python test_tree_placement.py
```

### Simple Test
```bash
cd backend
python simple_test.py
```

## Placement Logic Flow

```
User Joins → Check Referrer Capacity → Direct Placement Possible?
    ↓
Yes → Place under referrer (left/right)
    ↓
No → Find lowest level → Check available positions → Assign parent → Create placement
```

## Key Features

1. **Automatic Level Calculation**: Child level = Parent level + 1
2. **Position Priority**: Left position takes priority over right
3. **Spillover Logic**: When direct placement fails, find lowest available position
4. **Duplicate Prevention**: User cannot have multiple placements in same program/slot
5. **Parent Assignment**: Automatically finds appropriate parents for spillover placements

## Error Handling

- **Duplicate Placement**: User already has placement in this program/slot
- **No Available Position**: Tree is completely full
- **Invalid Program**: Program type not supported
- **Database Errors**: Connection or query errors

## Integration Points

1. **User Registration**: Call placement API when new user registers
2. **Referral System**: Use referrer_id from referral system
3. **Frontend Tree Display**: Use tree data API for visualization
4. **Income Calculation**: Use placement data for commission calculations

## Security Considerations

1. **Authentication**: All endpoints require valid JWT token
2. **Authorization**: Users can only view their own tree data
3. **Validation**: Input validation for all parameters
4. **Rate Limiting**: Consider implementing rate limiting for placement API

## Performance Considerations

1. **Indexing**: Database indexes on frequently queried fields
2. **Caching**: Consider caching tree data for frequently accessed users
3. **Batch Operations**: For bulk placements, consider batch processing
4. **Monitoring**: Monitor placement API performance and errors

এই সিস্টেমটি আপনার বর্ণিত binary tree placement logic সম্পূর্ণভাবে implement করে এবং production-ready।
