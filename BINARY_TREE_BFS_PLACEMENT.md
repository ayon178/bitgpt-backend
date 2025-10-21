# Binary Tree BFS Placement Implementation

## Overview
This document explains the Binary Tree placement logic with BFS (Breadth-First Search) spillover mechanism for handling unlimited referrals.

## Problem Statement
In a binary tree structure, each user can have maximum 2 direct downlines (left and right positions). When a user refers more than 2 people, the additional referrals need to be placed in the next available position in the tree using spillover logic.

## Key Concepts

### parent_id vs upline_id
- **parent_id**: Direct referrer (who actually invited the user) - NEVER CHANGES
- **upline_id**: Tree placement parent (where the user is actually placed) - CAN BE DIFFERENT due to spillover

### Example Scenario
```
User A refers 5 people: B, C, D, E, F

Tree Structure:
       A (level 0)
      / \
     B   C  (level 1 - direct under A)
    / \   \
   D   E   F  (level 2 - spillover placements)

Placements:
- B: parent_id=A, upline_id=A, position=left, is_spillover=false
- C: parent_id=A, upline_id=A, position=right, is_spillover=false
- D: parent_id=A, upline_id=B, position=left, is_spillover=true
- E: parent_id=A, upline_id=B, position=right, is_spillover=true
- F: parent_id=A, upline_id=C, position=left, is_spillover=true
```

## BFS Placement Algorithm

### Step 1: Check Direct Positions
When a user refers someone:
1. Check if referrer has left position available
2. If yes, place there (parent_id = upline_id = referrer)
3. If left is filled, check right position
4. If yes, place there (parent_id = upline_id = referrer)

### Step 2: BFS Spillover (if both direct positions filled)
If both direct positions are filled, use BFS to find next available position:

```python
queue = [(referrer, referrer_level)]
visited = set()

while queue:
    current_user, current_level = queue.popleft()
    
    # Check left position of current user
    if left_position_available:
        place_user(
            parent_id=referrer,           # Original referrer
            upline_id=current_user,       # Actual placement parent
            position='left',
            is_spillover=True
        )
        return
    
    # Check right position of current user
    if right_position_available:
        place_user(
            parent_id=referrer,           # Original referrer
            upline_id=current_user,       # Actual placement parent
            position='right',
            is_spillover=True
        )
        return
    
    # Both filled, add children to queue for next level
    queue.append(left_child)
    queue.append(right_child)
```

## Implementation Details

### Method: `place_user_in_tree()`
Location: `backend/modules/tree/service.py`

This method is called during user creation and handles placement:
1. Checks if user already has placement
2. Gets referrer's placement
3. Checks referrer's left position
4. Checks referrer's right position
5. If both filled, uses BFS to find next available position
6. Creates TreePlacement with appropriate parent_id and upline_id

### Method: `_find_next_available_position_bfs()`
Location: `backend/modules/tree/service.py`

Helper method that implements BFS algorithm:
- Returns: `{'upline_id': ObjectId, 'position': 'left'|'right', 'level': int}`
- Uses deque for efficient BFS traversal
- Checks positions level by level
- Returns first available position found

### Method: `_handle_indirect_referral_placement()`
Location: `backend/modules/tree/service.py`

Handles spillover placement for API calls:
- Calls `_find_next_available_position_bfs()`
- Creates placement with spillover flags
- Updates BinaryAutoUpgrade for direct referrer
- Maintains partner counts for commissions

## Database Fields

### TreePlacement Model
```python
class TreePlacement(Document):
    user_id = ObjectIdField(required=True)
    program = StringField(choices=['binary', 'matrix', 'global'])
    
    # Critical fields for spillover
    parent_id = ObjectIdField()      # Direct referrer
    upline_id = ObjectIdField()      # Tree placement parent
    
    position = StringField()         # 'left' or 'right'
    level = IntField()
    slot_no = IntField()
    
    # Spillover tracking
    is_spillover = BooleanField(default=False)
    spillover_from = ObjectIdField()  # Original referrer for spillover
    
    # Binary child pointers (for faster BFS)
    left_child_id = ObjectIdField()
    right_child_id = ObjectIdField()
```

## Query Patterns

### Tree Structure Queries (use upline_id)
```python
# Get direct children in tree
children = TreePlacement.objects(
    program='binary',
    upline_id=parent_user_id,
    slot_no=slot_no
)

# Get left child
left_child = TreePlacement.objects(
    program='binary',
    upline_id=parent_user_id,
    position='left',
    slot_no=slot_no
).first()
```

### Direct Referral Queries (use parent_id)
```python
# Get direct referrals (for commissions)
direct_referrals = TreePlacement.objects(
    program='binary',
    parent_id=referrer_id,
    slot_no=slot_no
)

# Count direct partners
direct_count = TreePlacement.objects(
    program='binary',
    parent_id=user_id
).count()
```

## Commission Impact

### Partner Incentive
- Uses **parent_id** (direct referrer gets commission)
- Even if user is placed via spillover, direct referrer gets credit

### Level Income
- Uses **upline_id** (tree structure determines level income)
- Follows actual tree hierarchy for level-based commissions

### Binary Auto-Upgrade
- Direct referrer's partner count increases
- Both direct and spillover referrals count toward auto-upgrade
- Uses **parent_id** for partner tracking

## API Response Structure

### GET /binary/duel-tree-earnings/{uid}
```json
{
  "tree": {
    "userId": "user17608872172129581",
    "totalMembers": 4,
    "levels": 2,
    "nodes": [
      {
        "id": 0,
        "type": "self",
        "userId": "user17608872172129581",
        "level": 0,
        "position": "root",
        "directDownline": [
          {
            "id": 1,
            "type": "downLine",
            "userId": "user17608874657221927",
            "level": 1,
            "position": "left",
            "directDownline": [...]
          },
          {
            "id": 2,
            "type": "downLine",
            "userId": "user17608875609939231",
            "level": 1,
            "position": "right"
          }
        ]
      }
    ]
  },
  "slots": [...],
  "totalSlots": 17
}
```

### Tree Building Method: `_build_nested_binary_tree_limited()`
Location: `backend/modules/binary/service.py`

This method builds the nested tree structure using **upline_id**:
- Queries: `TreePlacement.objects(upline_id=parent_oid, position='left')`
- Shows actual tree structure (not direct referrals)
- Handles spillover placements correctly

## Testing Scenarios

### Scenario 1: Direct Placement (2 referrals)
```
User A refers B and C
Expected:
- B: parent_id=A, upline_id=A, position=left, level=1
- C: parent_id=A, upline_id=A, position=right, level=1
```

### Scenario 2: Spillover Placement (3+ referrals)
```
User A refers B, C, D, E
Expected:
- B: parent_id=A, upline_id=A, position=left, level=1
- C: parent_id=A, upline_id=A, position=right, level=1
- D: parent_id=A, upline_id=B, position=left, level=2, is_spillover=true
- E: parent_id=A, upline_id=B, position=right, level=2, is_spillover=true
```

### Scenario 3: Multi-Level Spillover
```
User A refers B, C, D, E, F, G
Expected Tree:
       A
      / \
     B   C
    / \ / \
   D  E F  G

All D, E, F, G have:
- parent_id = A (direct referrer)
- upline_id = B or C (tree placement parent)
- is_spillover = true
```

## Benefits

1. **Unlimited Referrals**: Users can refer unlimited people
2. **Fair Distribution**: BFS ensures balanced tree growth
3. **Clear Tracking**: parent_id and upline_id separate concerns
4. **Accurate Commissions**: Direct referrer always gets credit
5. **Spillover Benefits**: Downline benefits from upline's referrals

## Migration Considerations

For existing tree_placement records without proper upline_id:
```python
# If no spillover occurred, upline_id = parent_id
for placement in TreePlacement.objects(upline_id=None):
    if not placement.is_spillover:
        placement.upline_id = placement.parent_id
        placement.save()
```

## Related Files
- `backend/modules/tree/service.py` - TreeService with BFS placement
- `backend/modules/tree/model.py` - TreePlacement model
- `backend/modules/binary/service.py` - BinaryService with tree building
- `backend/modules/binary/router.py` - Binary API endpoints
- `backend/PARENT_ID_VS_UPLINE_ID.md` - parent_id vs upline_id explanation
- `backend/TREE_PLACEMENT_UPDATE_SUMMARY.md` - Tree placement update summary

