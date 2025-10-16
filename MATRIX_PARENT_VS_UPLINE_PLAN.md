# Matrix Program - Parent ID vs Upline ID Implementation Plan

## Overview
Matrix program MUST implement the same `parent_id` vs `upline_id` distinction as Binary, but with additional complexity due to:
- Sweepover mechanism (60-level search)
- Recycle system
- Multiple tree instances per slot

## Current Matrix Structure

### Current Models:
```python
MatrixTree:
  - user_id
  - nodes (List of MatrixNode)
  - current_slot
  
MatrixNode:
  - level (1, 2, 3)
  - position (0-2 for L1, 0-8 for L2, 0-26 for L3)
  - user_id
  - placed_at
```

### Issue:
Current Matrix structure doesn't use `TreePlacement` model, so it's **missing the parent_id vs upline_id distinction**.

## Required Updates

### Option 1: Use TreePlacement for Matrix (RECOMMENDED)

Store Matrix placements in `TreePlacement` table alongside Binary/Global:

```python
# When user joins Matrix
TreePlacement.create(
    user_id=new_user_id,
    program='matrix',
    slot_no=slot_no,
    parent_id=direct_referrer_id,    # Who referred them (never changes)
    upline_id=tree_placement_id,     # Where placed in tree (can change)
    position=position,                # left (0), center (1), right (2)
    level=level,                      # 1, 2, or 3
    is_recycle=False                  # True if this is a recycle placement
)
```

### Option 2: Add Fields to MatrixNode (Alternative)

```python
class MatrixNode(EmbeddedDocument):
    level = IntField(required=True)
    position = IntField(required=True)
    user_id = ObjectIdField(required=True)
    
    # NEW FIELDS:
    parent_id = ObjectIdField()      # Direct referrer
    upline_id = ObjectIdField()      # Tree placement parent
    
    placed_at = DateTimeField(default=datetime.utcnow)
    is_active = BooleanField(default=True)
```

## Matrix-Specific Scenarios

### 1. Sweepover Placement

**Scenario:**
- UserA (sponsor) has Slot 3 active
- UserA refers UserB
- UserB activates Slot 5
- UserC (UserA's upline) has Slot 5 active
- System searches 60 levels up

**Result:**
```python
TreePlacement(
    user_id=UserB,
    program='matrix',
    slot_no=5,
    parent_id=UserA,           # Direct referrer (unchanged)
    upline_id=UserC,           # Actual placement (sweepover target)
    is_spillover=True,         # Indicates sweepover occurred
    spillover_from=UserA       # Original intended parent
)
```

### 2. Recycle Placement

**Scenario:**
- UserA completes 39 members in Slot 3
- UserA recycles back to direct upline's tree
- Direct upline = UserX

**First Tree:**
```python
TreePlacement(
    user_id=UserA,
    program='matrix',
    slot_no=3,
    parent_id=UserX,           # Original referrer
    upline_id=UserX,           # Original placement
    recycle_instance=1         # First tree
)
```

**After Recycle:**
```python
TreePlacement(
    user_id=UserA,
    program='matrix',
    slot_no=3,
    parent_id=UserX,           # Same (never changes)
    upline_id=UserX,           # Re-entered UserX's tree
    recycle_instance=2,        # Second tree
    is_recycle=True            # This is a recycle placement
)
```

### 3. Escalation with Sweepover

**Scenario:**
- UserA refers UserB
- UserA doesn't have Slot 4
- System searches up 60 levels
- UserC (40 levels up) has Slot 4
- UserB placed in UserC's tree

**Result:**
```python
TreePlacement(
    user_id=UserB,
    program='matrix',
    slot_no=4,
    parent_id=UserA,           # Direct referrer (unchanged)
    upline_id=UserC,           # Placed 40 levels up
    escalation_levels=40,      # How many levels escalated
    is_spillover=True          # Sweepover occurred
)
```

## Commission Distribution

### Partner Incentive (10%) - Uses parent_id
```python
def calculate_partner_incentive(user_id, slot_no):
    placement = TreePlacement.objects(
        user_id=user_id,
        program='matrix',
        slot_no=slot_no
    ).first()
    
    # PI goes to DIRECT REFERRER
    referrer = placement.parent_id
    amount = slot_value * 0.10
    pay_commission(referrer, amount, 'partner_incentive')
```

### Level Income (20/20/60) - Uses upline_id
```python
def calculate_level_income(user_id, slot_no):
    placement = TreePlacement.objects(
        user_id=user_id,
        program='matrix',
        slot_no=slot_no
    ).first()
    
    # Level income follows TREE STRUCTURE
    level_1_upline = placement.upline_id
    level_2_upline = get_tree_upline(level_1_upline)
    level_3_upline = get_tree_upline(level_2_upline)
    
    # Distribute: 20%, 20%, 60%
    pay_commission(level_1_upline, slot_value * 0.20, 'level_income')
    pay_commission(level_2_upline, slot_value * 0.20, 'level_income')
    pay_commission(level_3_upline, slot_value * 0.60, 'level_income')
```

### Mentorship Bonus (10%) - Uses parent_id
```python
def calculate_mentorship_bonus(user_id):
    placement = TreePlacement.objects(
        user_id=user_id,
        program='matrix'
    ).first()
    
    # Mentorship = sponsor's sponsor
    sponsor = placement.parent_id
    sponsor_placement = TreePlacement.objects(
        user_id=sponsor,
        program='matrix'
    ).first()
    
    # Super upline = sponsor's parent_id
    super_upline = sponsor_placement.parent_id
    amount = slot_value * 0.10
    pay_commission(super_upline, amount, 'mentorship_bonus')
```

## Implementation Steps

### Phase 1: Add TreePlacement for Matrix ✅
1. Start storing Matrix placements in `TreePlacement`
2. Set both `parent_id` and `upline_id` on placement
3. Keep `MatrixTree` for backward compatibility

### Phase 2: Update Matrix Service
1. Modify `_place_user_in_matrix_tree()` to create `TreePlacement`
2. Set `parent_id` = direct referrer
3. Set `upline_id` = actual placement target (after sweepover)

### Phase 3: Update Commission Calculations
1. Partner Incentive → use `parent_id`
2. Level Income → use `upline_id`
3. Mentorship Bonus → use `parent_id` chain

### Phase 4: Update Recycle Logic
1. On recycle, create new `TreePlacement` entry
2. Keep `parent_id` same
3. Update `upline_id` to new placement
4. Set `is_recycle=True`

### Phase 5: Update Tree Queries
1. Direct referrals → query by `parent_id`
2. Tree structure → query by `upline_id`
3. Team counting → query by `upline_id`

## Benefits for Matrix

### 1. Accurate Commission Distribution
- **Partner Incentive**: Always goes to direct referrer
- **Level Income**: Always follows tree structure
- **Mentorship**: Based on referral chain, not tree

### 2. Clear Sweepover Tracking
- Can see who referred vs where placed
- Audit trail for 60-level escalation
- Easy to verify placement logic

### 3. Recycle Support
- Each recycle creates new placement
- `parent_id` stays constant
- `upline_id` tracks new tree position

### 4. Team Statistics
- Direct referrals: count by `parent_id`
- Tree team: count by `upline_id`
- Both metrics accurate

## Migration Strategy

### For New Placements:
```python
# In MatrixService._place_user_in_matrix_tree()
def _place_user_in_matrix_tree(self, user_id, referrer_id, slot_no):
    # Find actual placement using sweepover logic
    target_parent = self._resolve_target_parent_tree_for_slot(referrer_id, slot_no)
    placement_position = self._find_bfs_placement_position(target_parent)
    
    # Create TreePlacement entry
    TreePlacement.create(
        user_id=user_id,
        program='matrix',
        slot_no=slot_no,
        parent_id=referrer_id,              # Direct referrer
        upline_id=target_parent.user_id,    # Actual placement
        position=placement_position['position'],
        level=placement_position['level'],
        is_spillover=(referrer_id != target_parent.user_id)
    )
    
    # Also update MatrixTree (for backward compatibility)
    # ...existing logic...
```

### For Existing Data:
```python
# Migration script
for matrix_tree in MatrixTree.objects():
    for node in matrix_tree.nodes:
        # Create TreePlacement for existing nodes
        # Need to infer parent_id and upline_id from context
        TreePlacement.create(
            user_id=node.user_id,
            program='matrix',
            slot_no=matrix_tree.current_slot,
            parent_id=infer_parent_id(node),    # Complex logic needed
            upline_id=infer_upline_id(node),    # From tree structure
            position=node.position,
            level=node.level,
            created_at=node.placed_at
        )
```

## Documentation References

From **PROJECT_DOCUMENTATION.md**:

> ### Direct vs Tree Upline (Authoritative)
> - **Direct Upline**: The referral relationship. This never changes across slots or recycles.
> - **Tree Upline**: The ancestor that receives level-income for a specific placement in a specific slot tree. This can change per slot and per recycle due to sweepover and BFS placement.

> ### Bonuses Unaffected by Sweepover
> - Partner Incentive (10%), Newcomer Growth Support, and Mentorship Bonus are not impacted by sweepover; they distribute per their normal rules regardless of the tree used for level-income.

## Summary

Matrix program **requires** `parent_id` vs `upline_id` distinction for:

1. ✅ **Accurate commissions** (PI vs Level Income)
2. ✅ **Sweepover tracking** (60-level escalation)
3. ✅ **Recycle support** (tree re-entry)
4. ✅ **Team statistics** (direct vs tree team)
5. ✅ **Audit trail** (referral vs placement)

The `TreePlacement` model with both `parent_id` and `upline_id` provides the **foundation** for proper Matrix program implementation.

**Next Step**: Implement TreePlacement for Matrix following the same pattern as Binary.

