# Parent ID vs Upline ID - Tree Placement Documentation

## Critical Distinction

The `TreePlacement` model now has TWO different IDs to track relationships:

### 1. `parent_id` (Direct Referrer)
- **Definition**: The user who directly referred/invited you
- **Never Changes**: This relationship is permanent
- **Use Cases**:
  - Direct referral counting
  - Partner Incentive calculations (10% commission)
  - Mentorship Bonus calculations
  - Direct team statistics

### 2. `upline_id` (Tree Placement Parent)
- **Definition**: The user under whose tree position you are actually placed
- **Can Change**: May differ from `parent_id` due to spillover
- **Use Cases**:
  - Tree structure traversal
  - Level income distribution
  - Actual tree hierarchy display
  - Team counting (all descendants in tree)

## Example Scenario

### Scenario 1: Normal Placement (No Spillover)
```
user123 refers userA
└─ userA joins binary
   parent_id: user123
   upline_id: user123
   (Same because no spillover)
```

### Scenario 2: With Spillover
```
Initial Structure:
user123 (root)
├─ userA (left) - FULL (has 2 children)
└─ userB (right) - Available

Now user123 refers userC:
- userC's parent_id = user123 (direct referrer)
- userC's upline_id = userB (placed under userB due to spillover)
```

### Scenario 3: Complex Tree
```
user123 (Level 0)
├─ userA (Level 1, left) - parent_id: user123, upline_id: user123
│  ├─ userC (Level 2, left) - parent_id: userA, upline_id: userA
│  └─ userD (Level 2, right) - parent_id: userA, upline_id: userA
└─ userB (Level 1, right) - parent_id: user123, upline_id: user123
   ├─ userE (Level 2, left) - parent_id: userB, upline_id: userB
   └─ userF (Level 2, right) - parent_id: userB, upline_id: userB

Now user123 refers userG:
- userG's parent_id = user123 (who referred)
- userG's upline_id = userC (placed under userC at Level 3 due to spillover)
```

## Database Queries

### For Direct Referrals (Use `parent_id`)
```python
# Count direct referrals
direct_count = TreePlacement.objects(
    program='binary',
    parent_id=user_id
).count()

# Get direct team for today
today_direct = TreePlacement.objects(
    program='binary',
    parent_id=user_id,
    created_at__gte=today_start
).count()
```

### For Tree Structure (Use `upline_id`)
```python
# Get tree children
tree_children = TreePlacement.objects(
    program='binary',
    upline_id=user_id
)

# Recursive tree traversal
def get_all_tree_descendants(upline_id):
    children = TreePlacement.objects(
        program='binary',
        upline_id=upline_id
    )
    for child in children:
        # Process child
        get_all_tree_descendants(child.user_id)
```

## Commission Calculations

### Partner Incentive (10%) - Uses `parent_id`
```python
# Partner Incentive goes to DIRECT REFERRER
direct_referrer = tree_placement.parent_id
# Pay 10% to direct_referrer
```

### Level Income (60%) - Uses `upline_id`
```python
# Level Income distributed based on TREE STRUCTURE
current_upline = tree_placement.upline_id
level = 1
while current_upline and level <= 16:
    # Calculate and distribute level income
    current_upline = get_tree_upline(current_upline)
    level += 1
```

## API Response Examples

### `/binary/duel-tree-earnings/{uid}` - Uses `upline_id`
Returns nested tree structure showing actual tree placement:
```json
{
  "tree": {
    "userId": "user123",
    "nodes": [
      {
        "userId": "user123",
        "directDownline": [
          {
            "userId": "userA",
            "directDownline": []
          }
        ]
      }
    ]
  }
}
```

### `/binary/dashboard/{uid}` - Uses both
- Direct team stats: `parent_id`
- Total team stats: `upline_id`

## Implementation Notes

### When Creating Tree Placement
```python
tree_placement = TreePlacement(
    user_id=new_user_id,
    program='binary',
    parent_id=referrer_id,  # Who referred them
    upline_id=placement_parent_id,  # Where they're placed
    position=position,
    level=level
)
```

### Binary Tree Placement Logic
1. Check if `parent_id` (direct referrer) has space
2. If yes: `upline_id = parent_id`
3. If no (spillover): Find available position
4. `upline_id` = whoever has the available position
5. `parent_id` = always the direct referrer (unchanged)

### Spillover Detection
```python
if placement_position_found != direct_referrer:
    is_spillover = True
    spillover_from = direct_referrer
    upline_id = placement_position_found
    parent_id = direct_referrer  # Never changes
```

## Modified Files

### 1. `backend/modules/tree/model.py`
- Added `upline_id` field
- Added index for `upline_id`
- Added documentation comments

### 2. `backend/modules/binary/service.py`
Updated all tree queries:
- Tree traversal → use `upline_id`
- Direct referral counting → use `parent_id`
- Level income → use `upline_id`
- Partner incentive → use `parent_id`

## Benefits

1. **Accurate Commission Distribution**: 
   - Partner Incentive goes to actual referrer
   - Level Income follows tree structure

2. **Clear Tree Visualization**:
   - Shows actual placement hierarchy
   - Easy to understand spillover

3. **Flexible Placement**:
   - Supports spillover mechanism
   - Maintains referral relationships

4. **Audit Trail**:
   - Can track both relationships
   - Clear history of placements

## Migration Considerations

For existing data:
```python
# For existing tree_placements without upline_id
# If no spillover occurred, upline_id = parent_id
for placement in TreePlacement.objects(upline_id=None):
    if not placement.is_spillover:
        placement.upline_id = placement.parent_id
    else:
        # Need to recalculate actual placement
        placement.upline_id = calculate_actual_upline(placement)
    placement.save()
```

## Summary

- **`parent_id`**: WHO referred you (direct relationship, never changes)
- **`upline_id`**: WHERE you are placed in tree (tree structure, can differ due to spillover)

Both are essential for proper Binary/Matrix/Global program functioning.

