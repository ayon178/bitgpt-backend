# Binary Tree Placement - Quick Reference

## 🎯 Core Concept
```
Maximum 2 direct children per user (left & right)
3+ referrals = Spillover using BFS algorithm
```

## 📌 Key Fields

| Field | Meaning | Usage |
|-------|---------|-------|
| `parent_id` | Direct referrer (who invited) | Partner Incentive, Direct referrals count |
| `upline_id` | Tree placement parent | Tree structure, Level income |
| `is_spillover` | Spillover placement flag | Track spillover vs direct placement |
| `position` | left / right | Tree position under upline |
| `level` | Tree level (0, 1, 2, ...) | Level-based commissions |

## 🌳 Placement Logic

### Direct Placement (1st & 2nd Referral)
```python
if not left_child:
    place_at_left(parent_id=referrer, upline_id=referrer)
elif not right_child:
    place_at_right(parent_id=referrer, upline_id=referrer)
```

### Spillover Placement (3+ Referrals)
```python
# Use BFS to find next position
next_pos = find_next_position_bfs(referrer)
place_user(
    parent_id=referrer,           # Original referrer
    upline_id=next_pos.upline_id, # Tree parent (can be different)
    is_spillover=True
)
```

## 🔍 Database Queries

### Tree Structure (use upline_id)
```python
# Get tree children
TreePlacement.objects(upline_id=user_id, program='binary')

# Get left child
TreePlacement.objects(upline_id=user_id, position='left', program='binary')

# Get right child
TreePlacement.objects(upline_id=user_id, position='right', program='binary')
```

### Direct Referrals (use parent_id)
```python
# Get direct referrals
TreePlacement.objects(parent_id=user_id, program='binary')

# Count direct partners
TreePlacement.objects(parent_id=user_id, program='binary').count()

# Get spillover referrals
TreePlacement.objects(parent_id=user_id, is_spillover=True)
```

## 📊 Example Scenarios

### Scenario 1: 2 Referrals
```
User A → B, C

Tree:    A
        / \
       B   C

B: parent_id=A, upline_id=A, spillover=false
C: parent_id=A, upline_id=A, spillover=false
```

### Scenario 2: 4 Referrals
```
User A → B, C, D, E

Tree:    A
        / \
       B   C
      / \
     D   E

B: parent_id=A, upline_id=A, spillover=false
C: parent_id=A, upline_id=A, spillover=false
D: parent_id=A, upline_id=B, spillover=TRUE
E: parent_id=A, upline_id=B, spillover=TRUE
```

### Scenario 3: 7 Referrals
```
User A → B, C, D, E, F, G, H

Tree:      A
         /   \
        B     C
       / \   / \
      D   E F   G
     /
    H

All have parent_id=A (direct referrer)
H: upline_id=D, level=3, spillover=TRUE
```

## 💰 Commission Distribution

### Partner Incentive
- Uses: `parent_id`
- Logic: Direct referrer gets commission
- Example: A refers 5 people → A gets 5 partner incentives

### Level Income
- Uses: `upline_id`
- Logic: Tree structure hierarchy
- Example: B gets level income from his tree children (D, E)

### Binary Auto-Upgrade
- Uses: `parent_id`
- Logic: Count direct referrals
- Example: A's partner_count includes all direct referrals

## 🧪 Testing Checklist

- [ ] User refers 2 people → Both placed at level 1
- [ ] User refers 3rd person → Placed at level 2 (spillover)
- [ ] User refers 4th person → Placed at level 2 (spillover)
- [ ] User refers 5+ people → BFS placement continues
- [ ] parent_id always = direct referrer
- [ ] upline_id = tree placement parent
- [ ] API response shows nested tree correctly
- [ ] Commissions calculated correctly

## 🛠️ Key Methods

### TreeService (backend/modules/tree/service.py)
```python
place_user_in_tree(user_id, referrer_id, program, slot_no)
  → Main placement method
  
_find_next_available_position_bfs(referrer_id, program, slot_no)
  → BFS algorithm to find next position
  
_handle_indirect_referral_placement(user_id, referrer_id, program, slot_no)
  → Handle spillover placements
```

### BinaryService (backend/modules/binary/service.py)
```python
get_duel_tree_earnings(user_id)
  → Get tree structure + slots for API
  
_build_nested_binary_tree_limited(user_oid, max_levels)
  → Build nested tree structure with directDownline
```

## 📝 Common Patterns

### Check if position available
```python
left_child = TreePlacement.objects(
    upline_id=user_id,
    position='left',
    program='binary',
    slot_no=1
).first()

if not left_child:
    # Left position available
```

### Count total team size
```python
def count_team_recursive(user_id):
    children = TreePlacement.objects(upline_id=user_id, program='binary')
    total = children.count()
    for child in children:
        total += count_team_recursive(child.user_id)
    return total
```

### Get spillover placements
```python
spillovers = TreePlacement.objects(
    parent_id=user_id,
    is_spillover=True,
    program='binary'
)
print(f"Spillover count: {spillovers.count()}")
```

## 🚨 Important Notes

1. **Always use upline_id for tree queries**
2. **Always use parent_id for commission queries**
3. **BFS ensures balanced tree growth**
4. **Spillover is automatic, not optional**
5. **Level calculated from upline's level + 1**

## 🔗 Related Documentation

- `BINARY_TREE_BFS_PLACEMENT.md` - Detailed algorithm explanation
- `BINARY_TREE_SPILLOVER_IMPLEMENTATION.md` - Complete implementation guide
- `BINARY_TREE_PLACEMENT_VISUAL_GUIDE.md` - Visual examples (Bangla + English)
- `PARENT_ID_VS_UPLINE_ID.md` - parent_id vs upline_id distinction
- `test_binary_tree_placement.py` - Test script

## 🎯 Quick Debug Commands

```python
# Check user's tree
from modules.tree.model import TreePlacement
placements = TreePlacement.objects(upline_id=user_id, program='binary')
for p in placements:
    print(f"Child: {p.user_id}, Position: {p.position}, Level: {p.level}")

# Check user's direct referrals
referrals = TreePlacement.objects(parent_id=user_id, program='binary')
print(f"Direct referrals: {referrals.count()}")

# Find next available position
from modules.tree.service import TreeService
import asyncio
next_pos = asyncio.run(TreeService._find_next_available_position_bfs(user_id, 'binary', 1))
print(f"Next position: {next_pos}")
```

---

**সংক্ষেপে: 2 জনের বেশি refer করলে BFS spillover হবে! ✅**

