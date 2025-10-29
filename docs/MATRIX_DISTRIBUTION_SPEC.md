## Matrix Distribution & Reserve Routing - Authoritative Spec

This spec consolidates the exact rules we will implement for Matrix joins, upgrades, and recycle events.

### 1) Percentages (Matrix)
- Spark Bonus: 8% (global fund)
- Royal Captain Bonus: 4% (global fund)
- President Reward: 3% (global fund)
- Newcomer Growth Support: 20%
  - 50% instantly claimable by the joining user
  - 50% goes to direct upline's newcomer fund; every 30 days, equally distribute across their current direct referrals (claimable by those users)
- Mentorship Bonus: 10% (to super upline = direct referrer's referrer)
- Partner Incentive: 10% (to direct referrer)
- Share Holders: 5% (credited to dedicated shareholders wallet/account)
- Level Distribution: 40% (see breakdown below)

### 2) Level Distribution (40% total)
Treat 40% as 100% baseline for the table below:
- Level 1: 30%
- Level 2: 10%
- Level 3: 10%
- Levels 4–10: 5% each
- Levels 11–13: 3% each
- Levels 14–16: 2% each
Rules:
- Eligibility resolved on the tree upline chain relative to the placement position (after sweepover/recycle).
- If a level’s user hasn’t activated the corresponding slot, the reward goes to Mother account (fallback).

### 3) Middle-Three Reserve Rule (Auto-Upgrade)
- For each matrix tree, the three middle positions at Level 2 (one under each Level 1 child) contribute 100% of their slot fee to the tree owner’s next-slot reserve.
- Manual activation allowed: combination of reserves + manual top-ups.
- If the next slot is already activated, middle-three fees follow Normal Distribution.

### 4) Super-Upline Middle Routing
- On any join/upgrade/recycle placement, detect if the placement is “middle” for the super upline:
  - Super upline = upline’s upline for the placed node (per current tree placement)
  - If the placed node is middle (center) under its parent and that parent is directly under the super upline (i.e., super upline sees it as a Level-2 middle), then route 100% of the slot fee to the super upline’s next-slot reserve, UNLESS that next slot is already active; if already active, use Normal Distribution.

### 5) Recycle Override (39th user)
- When a tree reaches 39 members, a new empty tree for that slot is created.
- The recycled user is placed into the upline’s same-slot current tree using BFS/sweepover rules.
- If the recycled placement is in a middle position that would fund the tree owner’s next slot and that next slot is not activated, route 100% of the fee to that owner’s next-slot reserve; otherwise, apply Normal Distribution.

### 6) Normal Distribution
Applied whenever special routing does not apply and for cases where the next slot is already activated.
Percentages: Spark 8, Royal 4, President 3, Newcomer 20 (with 50/50 split), Mentorship 10 (super upline), Partner 10 (referrer), Shareholders 5, Level 40.

### 7) Sweepover Rules
- If direct upline lacks the slot, search up to 60 levels for an eligible upline with the slot active; place via BFS into that tree.
- Level incomes resolve relative to the final tree placement, not original referrer.

### 8) Operational Notes
- All fund movements must be recorded in wallet/ledger models with auditable metadata (source user, slot, tree upline, placement level/position, tx_hash).
- Reserve balances trigger auto-activation when reaching the next slot’s cost.
- Scheduled job distributes newcomer-fund 50% portion every 30 days equally among the direct upline’s current direct referrals.


