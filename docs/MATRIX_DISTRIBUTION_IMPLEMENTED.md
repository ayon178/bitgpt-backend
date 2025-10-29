## Matrix Distribution - Implemented Rules (Authoritative)

This document summarizes the Matrix program distribution logic implemented in code.

### Core Percentages (per join/upgrade amount)
- Spark Bonus: 8% (global fund)
- Royal Captain Bonus: 4% (global fund)
- President Reward: 3% (global fund)
- Newcomer Growth Support (NGS): 20%
  - 50% to joining user as claimable newcomer support
  - 50% reserved to direct upline’s newcomer fund; distributed every 30 days equally to their current direct referrals
- Mentorship Bonus: 10% (to super upline = direct referrer’s referrer)
- Partner Incentive: 10% (to direct referrer)
- Shareholders: 5% (credited to shareholders fund/account)
- Level Distribution: 40% (Matrix breakdown below)

### Matrix Level Distribution (of the 40% pool)
- Level 1: 30%
- Level 2: 10%
- Level 3: 10%

Recipients are resolved by tree placement context (after sweepover/recycle) and recorded as level incomes.

### Special Routing Rules
- Super-upline Middle Routing (join/upgrade):
  - If the placement is Level 2 and the position is middle (position % 3 == 1) relative to the tree owner (super upline), and the owner’s next slot is not yet active, route 100% of the amount to that owner’s reserve for auto-upgrade.
  - If the next slot is already active, normal distribution applies.

- Recycle Middle Override (39th completion → new tree):
  - For placements during recycle, if the new placement is Level 2 middle under the tree owner and their next slot is not active, route 100% to reserve; else normal distribution.

### Newcomer Growth Support (NGS) Mechanics
- 20% total of the amount:
  - 50% credited as claimable income to the joining user (income_type: newcomer_support)
  - 50% credited as reserved fund to the direct upline (income_type: newcomer_support_upline_fund) for scheduled 30-day equal distribution among their current directs

### Shareholders Handling
- 5% routed to shareholders fund/account and recorded in income events for audit. Distribution to registered shareholders uses existing global shareholders fund mechanisms.

### Implementation Touchpoints
- Special reserve routing: `modules/fund_distribution/service.py` and `modules/matrix/sweepover_service.py`
- Level distribution (40% split): `modules/matrix/service.py` (`_calculate_level_distribution`)
- NGS 50/50 split: `modules/newcomer_support/service.py` (`process_matrix_contribution`)
- Mentorship 10%: `modules/fund_distribution/service.py` → `modules/mentorship/service.py`
- Partner incentive 10%: `modules/fund_distribution/service.py`
- Shareholders 5%: `modules/fund_distribution/service.py` → global shareholders handler

### Notes
- All fund flows are recorded via income/ledger events and eligible wallets/reserves.
- Reserve auto-activation triggers when the reserve balance reaches the next slot cost.


