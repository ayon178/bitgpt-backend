# User Join: End-to-End Automatic Actions (from PROJECT_DOCUMENTATION.md)

This note consolidates everything that must happen automatically when a user joins via a referrer, derived A–Z from `PROJECT_DOCUMENTATION.md`.

## 0) Preconditions
- Join occurs via a valid referrer (upline) identifier.
- Payment captured per joined program:
  - Binary: 0.0066 BNB (EXPLORER 0.0022 + CONTRIBUTOR 0.0044)
  - Matrix (optional): $11
  - Global (optional): $33

## 1) Core User Creation
- Create `User` with:
  - Referrer linkage (direct upline)
  - Activation status initialized (inactive until partner requirement met where applicable)
  - Partner count = 0
  - Rank initialized (per Rank System; default base rank)

## 2) Binary Program (Always, on Binary join)
1. Activate first two slots for the new user automatically:
   - Slot-1: EXPLORER (0.0022 BNB)
   - Slot-2: CONTRIBUTOR (0.0044 BNB)
2. Place the new user in the Binary Tree with one position:
   - Attempt direct placement under referrer (left/right if available)
   - If referrer positions are full, place by spillover using existing placement logic
3. Trigger Binary Partner Incentive commissions:
   - 10% of joining (0.0066 BNB) to the referrer (upline)
4. Initialize Auto-Upgrade pipeline (Binary Auto Upgrade System):
   - Track “first 2 partners” earnings for this new user
   - When this new user later gets 2 direct partners, their earnings are auto-allocated to upgrade the next slot
   - Keep upgrade history and current slot level
5. Initialize Dual Tree earning distribution context for future upgrades:
   - Level bonus rules (1: 30%, 2–3: 10%, 4–10: 5%, 11–13: 3%, 14–16: 2%) apply on each slot upgrade event
6. Initialize 30% Upgrade Commission routing for future upgrades:
   - On any slot upgrade by a downline, the matching-level upline gets 30% of that slot value; remaining 70% is distributed across levels 1–16
7. Missed Profit handling hooks:
   - If upline is inactive (no 2 partners) or at a lower level than required, missed amounts are diverted to Leadership Stipend pool
8. Spark Bonus fund contribution hooks:
   - Allocate configured Binary portion (part of the 8% Binary+Matrix fund) into Spark Bonus fund for later distribution
9. Jackpot linkage (no immediate payout on join):
   - Track free coupon entitlement counters that unlock on future slot upgrades (Slot-5: 1 coupon, Slot-6: 2 coupons, ... up to Slot-16)

## 3) Matrix Program (Only if Matrix join is included)
1. Create Matrix identity for the user in the 3× structure
2. Place user in Matrix tree under referrer’s Matrix structure (with recycle support)
3. Process Matrix Partner Incentive:
   - 10% of joining ($11) to the upline
   - 10% of each Matrix slot upgrade to the upline
4. Matrix Auto Upgrade System:
   - From Level 1 to 15, 100% earnings from the middle 3 members are reserved and auto-applied to the next slot upgrade
   - Track “Upline Reserve” position and middle-3 contributions
5. Mentorship Bonus:
   - Super upline (direct of direct) receives 10% from joining and all slot upgrades of direct-of-direct partners
6. Spark Bonus fund contribution hooks:
   - Allocate configured Matrix portion (contributes to the combined 8%) into Spark Bonus fund
7. Dream Matrix (if/when applicable):
   - Enforce mandatory 3 direct partners to start earning
   - Initialize distribution percentages per Dream Matrix levels for future earnings

## 4) Global Program (Only if Global join is included)
1. Place user in Phase-1, Slot-1 (Global pool)
2. Process Global Partner Incentive:
   - 10% of joining ($33) to the upline
3. Initialize Phase-1/Phase-2 Autopool progression:
   - Phase-1 slots complete with 4 global placements under the user → upgrade to Phase-2 same slot
   - Phase-2 slots complete with 8 global placements under the user → re-enter Phase-1 at next slot
   - Continue progression until Slot-16

## 5) Leadership Stipend (Hooks for future state)
- If/when the user upgrades to Binary slots 10–16:
  - Start daily return equal to 2× the current slot value
  - If user upgrades again before full 2× is paid, reset to the new slot’s 2×

## 6) Rank System
- Initialize rank for the new user
- Setup automatic rank recalculation triggers:
  - On Binary/Matrix slot activations and upgrades
  - On partner count changes and team progress

## 7) Commission Ledger & Distribution
- Create commission ledger entries (pending/paid/missed) for:
  - Joining commissions (Binary/Matrix/Global as applicable)
  - Upgrade commissions (30% matching-level for Binary; 10% Matrix/Global)
  - Dual Tree/Level distributions (Binary 1–16 levels)
  - Mentorship bonus (Matrix)
  - Missed profits redirected to Leadership Stipend
- Ensure wallet balances and program-specific pools are updated atomically

## 8) Newcomer Growth Support (NGS)
- Create NGS record for the user
- Credit Instant Bonus (cashable)
- Initialize monthly “extra earning opportunities” trackers (based on upline activity)
- Enable 10% Upline Rank Bonus when the user reaches the same rank as upline (applies from first joining to every slot upgrade)

## 9) Top Leader / Royal Captain / President Tracking (Counters only at join)
- Increment/track counters that contribute to:
  - Royal Captain Bonus (Matrix+Global referrals in sets of 5)
  - President Reward (30 direct invites thresholds with global team tiers)
  - Top Leader Gift (self rank, direct partners’ ranks, total team size)
- No immediate payout at join unless thresholds are met; hook evaluations run after each qualifying event

## 10) Data to Persist/Update (Summary)
- User: referrer, activation, partner counts, rank, Royal Captain/President counters, joined flags (binary/matrix/global)
- Binary: slot activations (1–2), tree placement node, upgrade history, level income context, BinaryAutoUpgrade status, blockchain events, earning history
- Matrix (if joined): placement node, slot activations, auto-upgrade (middle-3) tracker, mentorship links/status, NGS record, recycle state (when enabled), blockchain events, earning history
- Global (if joined): phase/slot index, GlobalPhaseProgression status, queue positions, team members, progression state, blockchain events, earning history
- Commissions: joining, upgrade (30% level + 70% dual-tree), distributions/receipts, mentorship, missed→stipend routing, accumulations, history
- Funds/Pools: Spark (eligibility cycles), Leadership Stipend (missed profits fund and user tiers/payments), Jackpot coupon counters
- Rank: user rank status/history, leaderboard stats
- NGS: eligibility, instant bonus records, monthly opportunities, upline-rank bonus state
- Programs’ ledgers and history audit trails

## 11) Triggers/Events to Fire (Transactional Order)
Recommended high-level sequence (atomic where possible):
1. Validate payment(s) and referrer → create `User`
2. Binary: activate Slot-1 & Slot-2 → place in Binary tree
3. Binary: record joining commission (10%), seed level/dual-tree contexts
4. Matrix (if joined): create/placement → joining commission (10%) → auto-upgrade reserves init
5. Global (if joined): place in Phase-1 Slot-1 → joining commission (10%)
6. Initialize NGS for user and credit Instant Bonus
7. Update Rank evaluation hooks
8. Persist all ledgers (commissions, pools, stipend missed-profit routing)
9. Emit events for async calculations (auto-upgrade checks, global progression, spark distribution, jackpot coupons, leadership stipend)

—

This file is the authoritative checklist for implementing the “user join” automations. Use it to wire API flows, services, models, and background jobs in alignment with `PROJECT_DOCUMENTATION.md`.


