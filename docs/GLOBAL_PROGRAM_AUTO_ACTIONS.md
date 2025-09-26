# Global Program Auto Actions Documentation

## Overview
This document outlines all automatic actions and business logic for the Global Program implementation based on PROJECT_DOCUMENTATION.md.

---

## 1. GLOBAL PROGRAM JOIN AUTO ACTIONS

### 1.1 User Join Process
**Trigger**: User joins Global program with $33
**Endpoint**: `POST /global/join`

#### Auto Actions Sequence:
1. **User Validation**
   - Validate user exists
   - Check if user already joined Global program
   - Verify amount matches Phase-1 Slot-1 price ($33)

2. **Slot Activation**
   - Create `SlotActivation` record for Global Slot-1
   - Set activation_type: 'initial'
   - Set currency: 'USD'
   - Set status: 'completed'

3. **Global Phase Progression Setup**
   - Create `GlobalPhaseProgression` record if not exists
   - Set current_phase: 'PHASE-1'
   - Set current_slot_no: 1
   - Set phase_position: 1
   - Set phase_1_members_required: 4
   - Set phase_1_members_current: 0
   - Set phase_2_members_required: 8
   - Set phase_2_members_current: 0
   - Set auto_progression_enabled: true

4. **Phase-1 BFS Placement**
   - Place user in Phase-1 tree using BFS algorithm
   - Find eligible upline with available Phase-1 positions
   - Escalate up to 60 levels if needed
   - Fallback to Mother ID if no eligible upline found

5. **Commission Calculations**
   - **Joining Commission (10%)**: Calculate and distribute to upline
   - **Partner Incentive (10%)**: Calculate and distribute to direct upline

6. **Global Distribution (100% breakdown)**
   - **Level (30%)**: Reserve for Phase-2 slot upgrade
   - **Partner Incentive (10%)**: Direct upline commission
   - **Profit (30%)**: Net profit portion
   - **Royal Captain Bonus (10%)**: Add to RC fund
   - **President Reward (10%)**: Add to PR fund
   - **Triple Entry Reward (5%)**: Add to TER fund
   - **Shareholders (5%)**: Add to shareholders fund

7. **Triple Entry Eligibility Check**
   - If user has Binary + Matrix + Global: Compute triple-entry eligibles
   - Trigger `SparkService.compute_triple_entry_eligibles()`

8. **Earning History Record**
   - Create `EarningHistory` record
   - Set earning_type: 'global_slot'
   - Set program: 'global'
   - Set amount: $33
   - Set currency: 'USD'
   - Set slot_name: 'FOUNDATION'
   - Set description: 'Joined Global program, activated Phase-1 Slot-1'

---

## 2. GLOBAL PROGRAM UPGRADE AUTO ACTIONS

### 2.1 Slot Upgrade Process
**Trigger**: User upgrades to next Global slot (2-16)
**Endpoint**: `POST /global/upgrade`

#### Auto Actions Sequence:
1. **Upgrade Validation**
   - Validate user exists and has Global program access
   - Check if target slot is valid (2-16)
   - Verify amount matches target slot price from catalog
   - Check if user already has this slot activated

2. **Slot Activation Record**
   - Create `SlotActivation` record for target slot
   - Set activation_type: 'upgrade'
   - Set upgrade_source: 'wallet' or 'auto'
   - Set currency: 'USD'
   - Set status: 'completed'

3. **Commission Calculations**
   - **Partner Incentive (10%)**: Calculate and distribute to direct upline
   - **Upgrade Commission**: Calculate based on slot value

4. **Global Distribution (100% breakdown)**
   - **Level (30%)**: Reserve for next Phase/slot upgrade
   - **Partner Incentive (10%)**: Direct upline commission
   - **Profit (30%)**: Net profit portion
   - **Royal Captain Bonus (10%)**: Add to RC fund
   - **President Reward (10%)**: Add to PR fund
   - **Triple Entry Reward (5%)**: Add to TER fund
   - **Shareholders (5%)**: Add to shareholders fund

5. **Earning History Record**
   - Create `EarningHistory` record for upgrade
   - Set earning_type: 'global_slot'
   - Set program: 'global'
   - Set amount: slot_value
   - Set currency: 'USD'
   - Set slot_name: target_slot_name
   - Set description: 'Upgraded Global slot'

---

## 3. GLOBAL PHASE PROGRESSION AUTO ACTIONS

### 3.1 Phase-1 to Phase-2 Progression
**Trigger**: User has 4 people in Phase-1 under them
**Auto Action**: `process_progression()`

#### Auto Actions Sequence:
1. **Phase Completion Check**
   - Check if phase_1_members_current >= phase_1_members_required (4)
   - Verify next_phase_ready is true

2. **Phase Status Update**
   - Set current_phase: 'PHASE-2'
   - Set current_slot_no: 1 (Phase-2 first slot)
   - Set is_phase_complete: true
   - Set phase_completed_at: current_timestamp
   - Set next_phase_ready: false

3. **Phase-2 Placement**
   - Place user in Phase-2 tree using BFS algorithm
   - Find eligible upline with available Phase-2 positions
   - Update parent's phase_2_members_current count

4. **Reserved Funds Usage**
   - Use reserved_upgrade_amount for Phase-2 slot activation
   - Deduct from reserved funds
   - Update reserved_upgrade_amount

### 3.2 Phase-2 to Phase-1 Re-entry
**Trigger**: User has 8 people in Phase-2 under them
**Auto Action**: `process_progression()`

#### Auto Actions Sequence:
1. **Phase Completion Check**
   - Check if phase_2_members_current >= phase_2_members_required (8)
   - Verify next_phase_ready is true

2. **Phase Status Update**
   - Set current_phase: 'PHASE-1'
   - Set current_slot_no: next_slot_number
   - Set is_phase_complete: true
   - Set phase_completed_at: current_timestamp
   - Set next_phase_ready: false

3. **Phase-1 Re-entry Placement**
   - Place user in Phase-1 tree using BFS algorithm
   - Find eligible upline with available Phase-1 positions
   - Update parent's phase_1_members_current count

4. **Reserved Funds Usage**
   - Use reserved_upgrade_amount for Phase-1 slot activation
   - Deduct from reserved funds
   - Update reserved_upgrade_amount

---

## 4. GLOBAL INCENTIVE AUTO ACTIONS

### 4.1 Partner Incentive Distribution
**Trigger**: Direct partner joins or upgrades Global slot
**Auto Action**: `calculate_partner_incentive()`

#### Auto Actions Sequence:
1. **Incentive Calculation**
   - Calculate 10% of slot value
   - Identify direct upline from referral chain
   - Verify upline has Global program access

2. **Commission Distribution**
   - Create `Commission` record
   - Set commission_type: 'joining' or 'upgrade'
   - Set program: 'global'
   - Set amount: 10% of slot value
   - Set currency: 'USD'
   - Set status: 'pending'

3. **Wallet Credit**
   - Credit upline's main wallet
   - Create `WalletLedger` entry
   - Set type: 'credit'
   - Set reason: 'global_partner_incentive'
   - Set balance_after: new_balance

---

## 5. ROYAL CAPTAIN BONUS AUTO ACTIONS

### 5.1 Royal Captain Bonus Calculation
**Trigger**: User has 5 direct partners with Global program
**Auto Action**: `calculate_royal_captain_bonus()`

#### Auto Actions Sequence:
1. **Eligibility Check**
   - Count direct partners with Global program
   - Check if count >= 5
   - Verify user has Matrix + Global programs

2. **Bonus Calculation**
   - Initial bonus: $200 for 5 direct partners
   - Progressive amounts based on global team size:
     - 10 global team: $200
     - 50 global team: $200
     - 100 global team: $200
     - 200 global team: $250
     - 300 global team: $250

3. **Fund Distribution**
   - Deduct from Royal Captain Bonus fund
   - Create `RoyalCaptainBonus` record
   - Set amount: calculated_bonus
   - Set currency: 'USD'
   - Set status: 'paid'

4. **Wallet Credit**
   - Credit user's main wallet
   - Create `WalletLedger` entry
   - Set type: 'credit'
   - Set reason: 'royal_captain_bonus'
   - Set balance_after: new_balance

---

## 6. PRESIDENT REWARD AUTO ACTIONS

### 6.1 President Reward Calculation
**Trigger**: User has 10 direct partners + 80 global team
**Auto Action**: `calculate_president_reward()`

#### Auto Actions Sequence:
1. **Eligibility Check**
   - Count direct partners with Global program
   - Count total global team size
   - Check if direct_partners >= 10 AND global_team >= 80

2. **Reward Calculation**
   - Initial reward: $500 for 10 direct + 80 global team
   - Progressive amounts based on team size:
     - 400 global team: $500
     - 600 global team: $700
     - 800 global team: $700
     - 1000 global team: $700
     - 1200 global team: $700
     - 1500 global team: $800
     - 1800 global team: $800
     - 2100 global team: $800
     - 2400 global team: $800
     - 2700 global team: $1500
     - 3000 global team: $1500
     - 3500 global team: $2000
     - 4000 global team: $2500
     - 5000 global team: $2500
     - 6000 global team: $5000

3. **Fund Distribution**
   - Deduct from President Reward fund
   - Create `PresidentReward` record
   - Set amount: calculated_reward
   - Set currency: 'USD'
   - Set status: 'paid'

4. **Wallet Credit**
   - Credit user's main wallet
   - Create `WalletLedger` entry
   - Set type: 'credit'
   - Set reason: 'president_reward'
   - Set balance_after: new_balance

---

## 7. TRIPLE ENTRY REWARD AUTO ACTIONS

### 7.1 Triple Entry Eligibility
**Trigger**: User has Binary + Matrix + Global programs
**Auto Action**: `compute_triple_entry_eligibles()`

#### Auto Actions Sequence:
1. **Eligibility Check**
   - Verify user has all three programs (Binary, Matrix, Global)
   - Check if user is not already in triple-entry list
   - Validate program activation dates

2. **Triple Entry Registration**
   - Add user to triple-entry eligibles list
   - Create `TripleEntryReward` record
   - Set user_id: user_id
   - Set programs: ['binary', 'matrix', 'global']
   - Set eligible_date: current_date
   - Set status: 'eligible'

3. **Reward Distribution**
   - Calculate 5% from Global program income
   - Distribute to triple-entry eligibles
   - Create `WalletLedger` entries for recipients

---

## 8. SHAREHOLDERS FUND AUTO ACTIONS

### 8.1 Shareholders Fund Distribution
**Trigger**: Any Global program transaction
**Auto Action**: `distribute_shareholders_fund()`

#### Auto Actions Sequence:
1. **Fund Calculation**
   - Calculate 5% of transaction amount
   - Add to shareholders fund pool

2. **Distribution Logic**
   - Distribute to registered shareholders
   - Calculate proportional shares
   - Create `ShareholdersDistribution` records

3. **Wallet Credit**
   - Credit shareholders' wallets
   - Create `WalletLedger` entries
   - Set type: 'credit'
   - Set reason: 'shareholders_distribution'

---

## 9. AUTO UPGRADE SYSTEM

### 9.1 Reserved Funds Auto Upgrade
**Trigger**: Sufficient reserved funds for next slot
**Auto Action**: `process_auto_upgrade()`

#### Auto Actions Sequence:
1. **Upgrade Check**
   - Check if reserved_upgrade_amount >= next_slot_price
   - Verify next_phase_ready is true
   - Determine next slot number

2. **Auto Upgrade Execution**
   - Create auto-upgrade transaction
   - Set tx_hash: 'GLOBAL-AUTO-UP-{user_id}-S{slot}-{timestamp}'
   - Process slot upgrade
   - Deduct from reserved funds

3. **Status Update**
   - Update current_slot_no
   - Update reserved_upgrade_amount
   - Set last_updated: current_timestamp

---

## 10. ERROR HANDLING AND FALLBACKS

### 10.1 Common Error Scenarios
1. **Insufficient Funds**: Return error, don't process transaction
2. **Invalid User**: Return 404 error
3. **Already Activated**: Return conflict error
4. **Catalog Missing**: Return server error
5. **Upline Not Found**: Fallback to Mother ID

### 10.2 Fallback Mechanisms
1. **Mother ID Placement**: When no eligible upline found
2. **Default Currency**: USD for Global program
3. **Minimum Amounts**: Enforce minimum transaction amounts
4. **Rate Limiting**: Prevent spam transactions

---

## 11. DATABASE MODELS REQUIRED

### 11.1 Core Models
- `GlobalPhaseProgression`: Track user's phase progression
- `GlobalTeamMember`: Track team members
- `GlobalDistribution`: Track fund distributions
- `RoyalCaptainBonus`: Track RC bonus payments
- `PresidentReward`: Track PR payments
- `TripleEntryReward`: Track TER eligibility
- `ShareholdersDistribution`: Track shareholders payments

### 11.2 Integration Models
- `SlotActivation`: Global slot activations
- `Commission`: Global commissions
- `WalletLedger`: Global wallet transactions
- `EarningHistory`: Global earning records

---

## 12. API ENDPOINTS REQUIRED

### 12.1 Core Endpoints
- `POST /global/join`: Join Global program
- `POST /global/upgrade`: Upgrade Global slot
- `GET /global/status/{user_id}`: Get user status
- `POST /global/progress/{user_id}`: Process progression
- `GET /global/team/{user_id}`: Get team members
- `POST /global/team/add`: Add team member

### 12.2 Distribution Endpoints
- `POST /global/distribute`: Process distribution
- `GET /global/preview-distribution/{amount}`: Preview distribution
- `GET /global/seats/{user_id}/{phase}`: Get phase seats
- `GET /global/tree/{user_id}/{phase}`: Get global tree

---

## 13. IMPLEMENTATION PRIORITY

### 13.1 Phase 1 (Core)
1. Global program join functionality
2. Basic phase progression
3. Partner incentive distribution
4. Slot activation system

### 13.2 Phase 2 (Advanced)
1. Royal Captain Bonus system
2. President Reward system
3. Triple Entry Reward system
4. Auto upgrade system

### 13.3 Phase 3 (Optimization)
1. Shareholders fund distribution
2. Advanced error handling
3. Performance optimization
4. Comprehensive testing

---

*This documentation serves as the authoritative guide for implementing Global Program auto actions in the BitGPT platform.*
