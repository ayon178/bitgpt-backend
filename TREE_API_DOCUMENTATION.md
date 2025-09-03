# Tree Management API Documentation

## Overview
The Tree Management API provides endpoints to retrieve binary tree, matrix tree, and global matrix data in a format compatible with the BitGPT frontend. The API transforms data from the `tree_placement` collection into the structured format expected by the frontend components.

## Base URL
```
/tree
```

## Authentication
All endpoints require authentication using Bearer token. Include the token in the Authorization header:
```
Authorization: Bearer <your_access_token>
```

## Endpoints

### 1. Create Tree Placement
**POST** `/tree/placement`

Creates a new tree placement with binary tree logic.

**Request Body:**
```json
{
  "user_id": "507f1f77bcf86cd799439011",
  "referrer_id": "507f1f77bcf86cd799439012",
  "program": "binary",
  "slot_no": 1
}
```

**Parameters:**
- `user_id` (string, required): The user ID to place in the tree
- `referrer_id` (string, required): The referrer/sponsor user ID
- `program` (string, optional): Program type - 'binary', 'matrix', 'global' (default: 'binary')
- `slot_no` (integer, optional): Slot number (default: 1)

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

### 2. Get Binary Tree Data
**GET** `/tree/{user_id}/binary`

Retrieves binary tree data for a specific user.

**Parameters:**
- `user_id` (string, required): The user ID to get tree data for

**Response:**
```json
{
  "success": true,
  "message": "Tree data retrieved successfully",
  "data": [
    {
      "id": 1,
      "price": 510,
      "userId": "507f1f77bcf86cd799439011",
      "recycle": 0,
      "isCompleted": false,
      "isProcess": false,
      "isAutoUpgrade": false,
      "isManualUpgrade": false,
      "processPercent": 42,
      "users": [
        {
          "id": 1,
          "type": "self",
          "userId": "507f1f77bcf86cd799439011"
        },
        {
          "id": 2,
          "type": "downLine",
          "userId": "507f1f77bcf86cd799439012"
        },
        {
          "id": 3,
          "type": "upLine",
          "userId": "507f1f77bcf86cd799439013"
        }
      ]
    }
  ]
}
```

### 3. Get Matrix Tree Data
**GET** `/tree/{user_id}/matrix`

Retrieves matrix tree data for a specific user.

**Parameters:**
- `user_id` (string, required): The user ID to get tree data for

**Response:** Same structure as binary tree but with matrix-specific data.

### 4. Get Global Matrix Tree Data
**GET** `/tree/{user_id}/global`

Retrieves global matrix tree data for a specific user.

**Parameters:**
- `user_id` (string, required): The user ID to get tree data for

**Response:** Same structure as binary tree but with global matrix-specific data.

### 5. Get All Tree Data
**GET** `/tree/{user_id}/all`

Retrieves all tree types (binary, matrix, global) for a specific user.

**Parameters:**
- `user_id` (string, required): The user ID to get tree data for

**Response:**
```json
{
  "success": true,
  "message": "All tree data retrieved successfully",
  "data": {
    "binary": [...],
    "matrix": [...],
    "global": [...]
  }
}
```

### 6. Get Tree Data by Program
**GET** `/tree/{user_id}/{program}`

Retrieves tree data for a specific user and program type.

**Parameters:**
- `user_id` (string, required): The user ID to get tree data for
- `program` (string, required): Program type - must be one of: `binary`, `matrix`, `global`

**Response:** Same structure as individual program endpoints.

## Placement Logic

### Binary Tree Placement Algorithm

The tree placement follows a sophisticated algorithm with two main scenarios:

#### Scenario 1: Direct Referral Placement
1. **Check Referrer Capacity**: Verify if the referrer has less than 2 positions filled
2. **Position Assignment**:
   - If no left child exists → Place on left position
   - If left exists but no right child → Place on right position
   - If both positions filled → Cannot place directly under referrer

#### Scenario 2: Indirect Referral Placement (Spillover)
1. **Find Lowest Level**: Identify the lowest level in the tree
2. **Check Available Positions**:
   - First check left position at lowest level
   - Then check right position at lowest level
   - If no space, move to next level
3. **Parent Assignment**: Find appropriate parent for the position
4. **Placement Creation**: Create placement with calculated level and position

### Placement Rules

1. **Level Calculation**: Child level = Parent level + 1
2. **Position Priority**: Left position takes priority over right
3. **Spillover Logic**: When direct placement fails, find lowest available position
4. **Duplicate Prevention**: User cannot have multiple placements in same program/slot

## Data Structure

### Tree Object
Each tree object represents a slot/tree in the system:

```json
{
  "id": 1,                    // Slot number/tree ID
  "price": 510,               // Tree price/value
  "userId": "507f1f77bcf86cd799439011", // Owner user ID
  "recycle": 0,               // Number of times recycled
  "isCompleted": false,        // Whether tree is completed
  "isProcess": false,          // Whether currently processing
  "isAutoUpgrade": false,      // Auto upgrade status
  "isManualUpgrade": false,    // Manual upgrade status
  "processPercent": 42,        // Completion percentage (0-100)
  "users": [...]               // Array of user nodes
}
```

### User Node Object
Each user node represents a position in the tree:

```json
{
  "id": 1,                     // Position ID in tree
  "type": "self",              // User type: "self", "downLine", "upLine", "overTaker"
  "userId": "507f1f77bcf86cd799439011" // Actual user ID
}
```

### TreePlacement Object
Each placement represents a user position in the tree:

```json
{
  "id": "507f1f77bcf86cd799439013",
  "user_id": "507f1f77bcf86cd799439011", // User ID
  "program": "binary",                    // Program type
  "parent_id": "507f1f77bcf86cd799439012", // Parent user ID
  "position": "left",                    // Position: left, right, center
  "level": 2,                            // Tree level
  "slot_no": 1,                          // Slot number
  "is_active": true,                     // Active status
  "created_at": "2024-01-15T13:45:00Z",  // Creation timestamp
  "updated_at": "2024-01-15T13:45:00Z"   // Update timestamp
}
```

## User Types

- **"self"**: The user who owns the position
- **"downLine"**: Direct referral/child in the tree
- **"upLine"**: Sponsor/parent in the tree  
- **"overTaker"**: User who takes over an empty position

## Tree Types

### Binary Tree
- **Structure**: Each node has exactly 2 children
- **Positions**: 7 total positions (3 levels: 1 + 2 + 4)
- **Layout**: Hierarchical binary structure

### Matrix Tree
- **Structure**: 3x3 matrix with hierarchical levels
- **Positions**: 13 total positions
- **Layout**: Matrix structure with multiple levels

### Global Matrix
- **Structure**: Same as matrix but with different phases
- **Positions**: 9 total positions
- **Layout**: 3x3 matrix structure

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid program type. Must be one of: ['binary', 'matrix', 'global']"
}
```

### 401 Unauthorized
```json
{
  "detail": "JWT Error"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error creating tree placement: <error_message>"
}
```

## Usage Examples

### Frontend Integration

```javascript
// Create tree placement
const response = await fetch('/tree/placement', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    user_id: '507f1f77bcf86cd799439011',
    referrer_id: '507f1f77bcf86cd799439012',
    program: 'binary',
    slot_no: 1
  })
});
const data = await response.json();

// Get binary tree data
const treeResponse = await fetch('/tree/507f1f77bcf86cd799439011/binary', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const treeData = await treeResponse.json();

// Use with DualTreeGraph component
<DualTreeGraph 
  usersData={treeData.data[0].users}
  isDetails={true}
  onUserClick={(userId) => handleUserClick(userId)}
/>
```

### cURL Examples

```bash
# Create tree placement
curl -X POST "http://localhost:8000/tree/placement" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token_here" \
  -d '{
    "user_id": "507f1f77bcf86cd799439011",
    "referrer_id": "507f1f77bcf86cd799439012",
    "program": "binary",
    "slot_no": 1
  }'

# Get binary tree data
curl -X GET "http://localhost:8000/tree/507f1f77bcf86cd799439011/binary" \
  -H "Authorization: Bearer your_token_here"

# Get all tree data
curl -X GET "http://localhost:8000/tree/507f1f77bcf86cd799439011/all" \
  -H "Authorization: Bearer your_token_here"
```

## Database Schema

The API reads from and writes to the `tree_placement` collection with the following structure:

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

## Business Logic

The service includes several business logic calculations:

1. **Tree Completion**: Checks if all positions in a tree are filled
2. **Process Percentage**: Calculates completion percentage based on filled positions
3. **Position Calculation**: Maps database positions to frontend position IDs
4. **User Type Determination**: Determines user type based on position and relationship
5. **Price Calculation**: Calculates tree price based on program and slot
6. **Recycle Tracking**: Tracks number of times a tree has been recycled
7. **Placement Logic**: Handles direct and indirect referral placement
8. **Level Management**: Automatically calculates and assigns tree levels
9. **Parent Assignment**: Finds appropriate parents for spillover placements

## Testing

Use the provided test script to verify functionality:

```bash
cd backend
python test_tree_placement.py
```

This will create sample data, test both placement scenarios, and clean up afterward.

## Placement Flow Diagram

```
User Joins → Check Referrer Capacity → Direct Placement Possible?
    ↓
Yes → Place under referrer (left/right)
    ↓
No → Find lowest level → Check available positions → Assign parent → Create placement
```

This comprehensive API provides complete tree management functionality for the BitGPT platform, including sophisticated placement logic that handles both direct referrals and spillover scenarios.
