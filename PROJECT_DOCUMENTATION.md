# BitGPT Project Documentation

## Overview
This document contains comprehensive details about the BitGPT project's earning programs and business logic, extracted from the project documentation images.

---

## 1. EARNING PROGRAMMES OVERVIEW

### Introduction
As a community building up platforms we strongly suggest everyone to bring at least 5 partners with global package to maximise your fund and team growth.

### Available Earning Programs
The platform offers 14 different earning programs organized in three rows:

#### First Row (5 programs):
- **Dual Tree Earning**
- **Binary Partner Incentive**
- **Leadership Stipend**
- **Dream Matrix**
- **Matrix Partner Incentive**

#### Second Row (5 programs):
- **New Commer Growth Support**
- **MENTORSHIP BONUS**
- **Spark Bonus**
- **PHASE-1 AND PHASE-2**
- **Global Partner Incentive**

#### Third Row (4 programs):
- **Royal captain Bonus**
- **President Reward**
- **TOP LEADER GIFT**
- **Jackpot Programme**

---

## 2. BINARY PROGRAM OVERVIEW

### Joining Requirement
- **0.0066 BNB** will be needed to join this programme.

### Membership Tiers and Costs (BNB)

| Slot | Name        | BNB Cost     |
| :--- | :---------- | :----------- |
| 1    | Explorer    | 0.0022 BNB   |
| 2    | Contributor | 0.0044 BNB   |
| 3    | Subscriber  | 0.0088 BNB   |
| 4    | Dreamer     | 0.0176 BNB   |
| 5    | Planner     | 0.0352 BNB   |
| 6    | Challenger  | 0.0704 BNB   |
| 7    | Adventurer  | 0.1408 BNB   |
| 8    | Game-Shifter| 0.2816 BNB   |
| 9    | Organizer   | 0.5632 BNB   |
| 10   | Leader      | 1.1264 BNB   |
| 11   | Vanguard    | 2.2528 BNB   |
| 12   | Center      | 4.5056 BNB   |
| 13   | Climax      | 9.0112 BNB   |
| 14   | Eternity    | 18.0224 BNB  |
| 15   | King        | 36.0448 BNB  |
| 16   | Commander   | 72.0896 BNB  |
| 17   | CEO         | 144.1792 BNB |

### Binary Earning Chart
**FROM BINARY, A PERSON CAN EARN ACCORDING TO THE CHART BELOW:**

| SL.NO | SLOT NAME    | SLOT VALUE | LEVEL | MEMBER | TOTAL INCOME | UPGRADE COST | WALLET      |
| :---- | :----------- | :--------- | :---- | :----- | :----------- | :----------- | :---------- |
| 1     | EXPLORER     | 0.0022     | -     | -      | -            | -            | -           |
| 2     | CONTRIBUTOR  | 0.0044     | 1     | 2      | -            | -            | -           |
| 3     | SUBSCRIBER   | 0.0088     | 2     | 4      | 0.02288      | 0.0176       | 0.00528     |
| 4     | DREAMER      | 0.0176     | 3     | 8      | 0.06688      | 0.0352       | 0.03168     |
| 5     | PLANNER      | 0.0352     | 4     | 16     | 0.21824      | 0.0704       | 0.14784     |
| 6     | CHALLENGER   | 0.0704     | 5     | 32     | 0.7744       | 0.1408       | 0.6336      |
| 7     | ADVENTURER   | 0.1408     | 6     | 64     | 2.90048      | 0.2816       | 2.61888     |
| 8     | GAME-SHIFTER | 0.2816     | 7     | 128    | 11.20768     | 0.5632       | 10.64448    |
| 9     | ORGANIGER    | 0.5632     | 8     | 256    | 44.04224     | 1.1264       | 42.91584    |
| 10    | LEADER       | 1.1264     | 9     | 512    | 174.592      | 2.2528       | 172.3392    |
| 11    | VANGURD      | 2.2528     | 10    | 1024   | 695.21408    | 4.5056       | 690.70848   |
| 12    | CENTER       | 4.5056     | 11    | 2048   | 2774.54848   | 9.0112       | 2765.53728  |
| 13    | CLIMAX       | 9.0112     | 12    | 4096   | 11085.5782   | 18.0224      | 11067.5558  |
| 14    | ENTERNITY    | 18.0224    | 13    | 8192   | 44317.0816   | 36.0448      | 44281.0368  |
| 15    | KING         | 36.0448    | 14    | 16384  | 177217.864   | 72.0896      | 177145.774  |
| 16    | COMMENDER    | 72.0896    | 15    | 32768  | 708669.603   | +139.656     | 708669.603  |

### Binary Program Patterns
- **SLOT VALUE**: Each slot value doubles from the previous one
- **LEVEL**: Starts from 1 for CONTRIBUTOR, increments by 1
- **MEMBER**: Follows 2^Level pattern (2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768)
- **UPGRADE COST**: Generally equals the SLOT VALUE of the next tier
- **WALLET**: Calculated as TOTAL INCOME minus UPGRADE COST

### Tree Upline Reserve System
**CRITICAL FEATURE**: Tree upline reserve fund system for automatic slot activation.

#### Slot Activation & Tree Structure:
- **Each slot has separate tree**: When a user joins Binary, they activate Slot 1 and Slot 2 automatically
- **Separate tree for each slot**: User placed in Slot 1 tree joins Slot 1 tree, user placed in Slot 2 tree joins Slot 2 tree, etc.
- **User joins multiple trees**: Same user can be in different positions in Slot 1 tree, Slot 2 tree, Slot 3 tree, etc.

#### Slot 1 Activation Logic:
- **Full fee to direct upline**: When a user joins Slot 1, the entire joining fee goes to their direct upline (referrer)
- **Example**: User C refers User H to join Slot 1, then User C gets the full Slot 1 fee

#### Slot 2-17 Activation Logic:
When a user activates Slot 2 or above, the system checks:

**Condition 1: First or Second Level User**
- If the activating user is the tree upline's (for that slot number) 1st level or 2nd level user
- **THEN**: Entire activation fee goes to tree upline's reserve fund for next slot activation
- **Purpose**: Auto-upgrade the tree upline when reserve reaches next slot cost

**Condition 2: Tree Upline Not Activated**
- If the tree upline hasn't activated the target slot yet
- **THEN**: Fund goes to mother account

**Condition 3: Normal Distribution**
- If the target slot is already activated by tree upline
- **THEN**: Fund follows normal distribution percentages (Spark Bonus, Royal Captain, etc.)

#### Automatic Slot Activation:
- When reserve fund reaches the cost of next slot, automatic activation occurs
- Example: User C refers User H, User H activates Slot 3, entire fee goes to User A's (tree upline) reserve, and automatic Slot 4 activation happens when sufficient funds

#### Example Scenario:
- User C refers User H
- User H activates Slot 3
- Entire Slot 3 fee goes to User A's (tree upline) reserve for next slot activation
- System automatically activates User A's next slot when reserve reaches required amount

#### Normal Distribution (When NOT in First/Second Level):

If a user is NOT in tree upline's 1st or 2nd level, the slot activation fee is distributed as:

| Component | Percentage (%) |
| :-------- | :------------- |
| Spark Bonus | 8% |
| Royal Captain Bonus | 4% |
| President Reward | 3% |
| Leadership Stipend | 5% |
| Jackpot Entry | 5% |
| Partner Incentive | 10% (direct referrer) |
| Share Holders | 5% |
| Level Distribution | 60% (distributed across levels 1-16) |

**Additional Notes:**
- **Newcomer Growth Fund**: Created when user joins Binary
- **Global Funds**: Spark Bonus, Royal Captain Bonus, President Reward, Leadership Stipend, Jackpot Entry are global funds distributed based on eligibility
- **Share Holders**: 5% goes to separate wallet
- **Partner Incentive**: Goes directly to referrer who brought the user

#### Level Distribution (60%):

The 60% level distribution is treated as 100% baseline and distributed across levels:

| Level | Percentage of 60% | Description |
| :---- | :---------------- | :---------- |
| Level 1 | 30% | Tree upline at level 1 |
| Level 2 | 10% | Tree upline at level 2 |
| Level 3 | 10% | Tree upline at level 3 |
| Level 4-10 | 5% each | Tree upline at levels 4-10 |
| Level 11-13 | 3% each | Tree upline at levels 11-13 |
| Level 14-16 | 2% each | Tree upline at levels 14-16 |

**Important Rule**: If a level's user hasn't activated the corresponding slot, that level's reward goes to Mother ID.

---

## 3. MATRIX PROGRAM OVERVIEW

### Joining Requirement
- **$11 WILL BE NEEDED TO JOIN THIS PROGRAMME**

### Membership Tiers and Costs (USDT)

| Slot | Price (USDT) |
| :--- | :----------- |
| 1    | 11           |
| 2    | 33           |
| 3    | 99           |
| 4    | 297          |
| 5    | 891          |
| 6    | 2673         |
| 7    | 8019         |
| 8    | 24057        |
| 9    | 72171        |
| 10   | 216513       |
| 11   | 649539       |
| 12   | 1948617      |
| 13   | 5845851      |
| 14   | 6537553      |
| 15   | 52612659     |

### Matrix Earning Chart
**FROM MATRIX, A PERSON CAN EARN ACCORDING TO THE CHART BELOW:**

| SL.NO | SLOT NAME | SLOT VALUE | LEVEL | MEMBER | TOTAL INCOME | UPGRADE COST | WALLET   |
| :---- | :-------- | :--------- | :---- | :----- | :----------- | :----------- | :------- |
| 1     | STARTER   | $11        | 1     | 3      | -            | -            | -        |
| 2     | BRONZE    | $33        | 2     | 9      | $158.4       | $99          | $59.4    |
| 3     | SILVER    | $99        | 3     | 27     | $1039.5      | $297         | $742.5   |
| 4     | GOLD      | $297       | 4     | 81     | $7929.9      | $891         | $7038.9  |
| 5     | PLATINUM  | $891       | 5     | 243    | $67092.3     | $2673        | $64419.3 |

### Matrix Program Patterns
- **SLOT VALUE**: Each tier costs 3x the previous tier
- **LEVEL**: Increments by 1 for each tier
- **MEMBER**: Follows 3^Level pattern (3, 9, 27, 81, 243)
- **UPGRADE COST**: Generally equals the SLOT VALUE of the next tier
- **WALLET**: Calculated as TOTAL INCOME minus UPGRADE COST

---

## 4. GLOBAL PROGRAM OVERVIEW

### Joining Requirement
- **$33 WILL BE NEEDED TO JOIN THIS PROGRAMME**

### Program Structure
The Global Program is organized into two phases:

#### PHASE-1 Slot Prices:
| Slot | Price (USDT) |
| :--- | :----------- |
| 1    | 33           |
| 2    | 94.60        |
| 3    | 271.70       |
| 4    | 782.10       |
| 5    | 2251.70      |
| 6    | 6486.70      |
| 7    | 18682.40     |
| 8    | 53809.80     |

#### PHASE-2 Slot Prices:
| Slot | Price (USDT) |
| :--- | :----------- |
| 1    | 39.6         |
| 2    | 113.3        |
| 3    | 325.6        |
| 4    | 938.3        |
| 5    | 2702.7       |
| 6    | 7783.6       |
| 7    | 22419.1      |
| 8    | 64566.7      |

### Global Earning Chart
**FROM GLOBAL, A PERSON CAN EARN ACCORDING TO THE CHART BELOW:**

| SL.NO | LEVEL NAME | SLOT NAME  | SLOT VALUE | LEVEL | MEMBER | TOTAL INCOME | UPGRADE COST | WALLET   |
| :---- | :--------- | :--------- | :--------- | :---- | :----- | :----------- | :----------- | :------- |
| 1     | PHASE-1    | FOUNDATION | 30         | 1     | 4      | 72           | 36           | 36       |
| 2     | PHASE-2    | APEX       | 36         | 2     | 8      | 172          | 86           | 86       |
| 3     | PHASE-1    | SUMMIT     | 86         | 3     | 4      | 206          | 103          | 103      |
| 4     | PHASE-2    | RADIANCE   | 103        | 4     | 8      | 494          | 247          | 247      |
| 5     | PHASE-1    | HORIZON    | 247        | 5     | 4      | 592          | 296          | 296      |
| 6     | PHASE-2    | PARAMOUNT  | 296        | 6     | 8      | 1420         | 710          | 710      |
| 7     | PHASE-1    | CATALYST   | 710        | 7     | 4      | 1704         | 852          | 852      |
| 8     | PHASE-2    | ODYSSEY    | 852        | 8     | 8      | 4089         | 2044         | 2044     |
| 9     | PHASE-1    | PINNACLE   | 2044       | 9     | 4      | 4905         | 2452         | 2452     |
| 10    | PHASE-2    | PRIME      | 2452       | 10    | 8      | 11769        | 5884         | 5884     |
| 11    | PHASE-1    | MOMENTUM   | 5884       | 11    | 4      | 14121        | 7060         | 7060     |
| 12    | PHASE-2    | CREST      | 7060       | 12    | 8      | 33888        | 16944        | 16944    |
| 13    | PHASE-1    | VERTEX     | 16944      | 13    | 4      | 40665        | 20332        | 20332    |
| 14    | PHASE-2    | LEGACY     | 20332      | 14    | 8      | 97593        | 48796        | 48796    |
| 15    | PHASE-1    | ASCEND     | 48796      | 15    | 4      | 117110       | 58555        | 58555    |
| 16    | PHASE-2    | EVEREST    | 58555      | 16    | 8      | 281064       | 140532       | 140532   |

### Global Program Summary
- **TOTAL INCOME**: 609864
- **UPGRADE COST**: -304929
- **WALLET**: -304929

### Global Program Patterns
- **Alternating Phases**: Levels alternate between PHASE-1 and PHASE-2
- **MEMBER Pattern**: PHASE-1 levels have 4 members, PHASE-2 levels have 8 members
- **SLOT VALUE**: Increases progressively through levels
- **UPGRADE COST**: Generally equals the SLOT VALUE of the next level
- **WALLET**: Calculated as TOTAL INCOME minus UPGRADE COST

### Global Distribution
- **Level (30%)**: 30% reserved to upgrade corresponding Phase/slot
- **Partner Incentive (10%)**: 10% to direct upline
- **Profit (30%)**: Net profit portion
- **Royal Captain Bonus (10%)**
- **President Reward (10%)**
- **Triple Entry Reward (5%)**
- **Shareholders (5%)**

---

## 5. PLATFORM REQUIREMENTS AND DEPLOYMENT

### Smart Contract Deployment Requirements
- **Mother ID Setup**: The first ID must be set up during smart contract deployment
- **Mother ID Access**: Mother ID has access to all programs and serves as fallback for fund distribution
- **Unique Referral ID System**: Each user gets a unique referral ID after joining Binary program
- **Referral ID Reuse**: Same referral ID used across all programs (Binary, Matrix, Global)

### Mandatory Join Sequence
**CRITICAL REQUIREMENT**: Users MUST follow this exact sequence:
1. **Binary Program** (Required first) - Cannot join other programs without Binary
2. **Matrix Program** (Required second) - Cannot join Global without Matrix  
3. **Global Program** (Required third) - Final program in sequence

**Enforcement Rules**:
- No user can join Matrix without first joining Binary
- No user can join Global without first joining Matrix
- Referral ID from Binary is used for Matrix and Global programs

---

## 6. DEVELOPMENT REQUIREMENTS

### Key Business Logic Points

1. **User Creation Success**:
   - When a user is successfully created, they should be added to the binary tree with 1 position
   - This triggers the binary tree placement logic

2. **User Join Process**:
   - When a user joins Binary, **BOTH Slot 1 AND Slot 2 activate automatically**
   - Each slot has separate tree structure
   - User gets unique referral ID for use across all programs

3. **Tree Placement Logic**:
   - Direct referral placement (when referrer has available positions)
   - Indirect referral placement (spillover when referrer's positions are full)

4. **Program Integration**:
   - Binary Program (BNB-based)
   - Matrix Program (USDT-based)
   - Global Program (USD-based)

### Implementation Priority

1. **Phase 1**: Binary Tree Placement System ✅ (Already implemented and tested)
2. **Phase 2**: User Creation Integration with Binary Tree
3. **Phase 3**: Slot Activation Logic (First 2 slots on user join)
4. **Phase 4**: Matrix Program Implementation
5. **Phase 5**: Global Program Implementation
6. **Phase 6**: Earning Calculation and Distribution
7. **Phase 7**: Multi-program Integration

---

## 6. NEXT STEPS

### Immediate Actions Needed

1. **Integrate User Creation with Binary Tree**:
   - Modify user creation process to automatically create binary tree placement
   - Ensure proper referrer assignment

2. **Implement Slot Activation Logic**:
   - When user joins, activate first 2 binary slots (EXPLORER and CONTRIBUTOR)
   - Update user status and available positions

3. **Create Program Models**:
   - Binary Program Model
   - Matrix Program Model
   - Global Program Model

4. **Implement Earning Calculations**:
   - Binary earning calculations based on the chart
   - Matrix earning calculations
   - Global earning calculations

### Technical Implementation

1. **Database Models**:
   - Extend existing TreePlacement model
   - Create Program models for each earning program
   - Create Earning models for tracking income

2. **API Endpoints**:
   - User creation with tree placement
   - Slot activation endpoints
   - Earning calculation endpoints
   - Program status endpoints

3. **Business Logic**:
   - Tree placement algorithms
   - Earning calculation algorithms
   - Program progression logic

---

## 7. BITGPT RANK SYSTEM

### Rank Overview
BitGPT has 15 special ranks, made from the combination of Binary and Matrix slots. Every time you activate a slot, you reach a new rank — showing your growth and leadership.

### 15 Special Ranks

#### Row 1 (Ranks 1-5):
1. **Bitron**
2. **Cryzen**
3. **Neura**
4. **Glint**
5. **Stellar**

#### Row 2 (Ranks 6-10):
6. **Ignis**
7. **Quanta**
8. **Lumix**
9. **Arion**
10. **Nexus**

#### Row 3 (Ranks 11-15):
11. **Fyre**
12. **Axion**
13. **Trion**
14. **Spectra**
15. **Omega**

### Rank System Logic
- Each rank is achieved by activating slots in Binary and Matrix programs
- Ranks represent leadership and growth within the platform
- Higher ranks indicate more active participation and team building

---

## 8. BINARY PARTNER INCENTIVE

### Core Incentive System
**IF A PERSON JOINS THE BINARY WITH 0.0066 BNB, THEIR UPLINE WILL RECEIVE A 10% COMMISSION FROM THE JOINING AND FROM EACH SLOT UPGRADE.**

### Binary Tree Structure
The system uses a binary tree structure where:
- Each user can have 2 direct referrals (left and right positions)
- Upline receives commissions from all downline activities
- Spillover occurs when direct positions are filled

### Commission Flow
- **Joining Commission**: 10% of joining fee (0.0066 BNB)
- **Upgrade Commission**: 10% of each slot upgrade
- **Upline Benefits**: Receives commissions from all levels below

---

## 9. DUAL TREE EARNING

### Level Income System
**Here is the list of Level Incomes that a person will receive when they upgrade a slot in the Binary.**

### Bonus Structure (From Level 2-16)
**Every Slot Upgrade (Bonus)**

| Level    | Percentage (%) |
| :------- | :------------- |
| Level 1  | 30%            |
| Level 2-3| 10%            |
| Level 4-10| 5%            |
| Level 11-13| 3%           |
| Level 14-16| 2%           |
| **Total** | **=100%**     |

### Dual Tree Logic
- Level 1 receives the highest bonus (30%)
- Bonuses decrease as levels increase
- Total bonus distribution equals 100%
- Encourages early participation and team building

---

## 10. AUTO UPGRADE SYSTEM

### Core Auto Upgrade Rule
**IN BITGPT, ALL UPGRADES WILL BE AUTOMATIC.**
**THE EARNINGS FROM THE FIRST TWO PEOPLE AT EACH LEVEL WILL BE USED FOR THE NEXT SLOT UPGRADE.**

### Auto Upgrade Mechanism
- **Requirement**: User needs 2 partners to activate their ID
- **Process**: Earnings from first 2 partners are used for next slot upgrade
- **Result**: User automatically goes to next level (2) with profit

### Auto Upgrade Flow
1. User ("ME") gets 2 direct referrals
2. First 2 partners generate earnings
3. Earnings are automatically used for next slot upgrade
4. User advances to next level with profit

### Activation Condition
**YOU MUST NEED 2 PARTNERS TO ACTIVATE YOUR ID AND YOU WILL GO NEXT LEVEL (2) WITH PROFIT!**

---

## 11. UPGRADE COMMISSION SYSTEM

### Commission Distribution Rule
**Whenever a partner upgrades to a specific slot, the upline at that exact level (corresponding to the slot number) will receive 30% upgrade commission. The remaining is distributed across Levels 1-16 as per Dual Tree rules.**

### Level-1 Special Rule
- For Slot 1 activations, the full Level-1 amount goes to the immediate upline.

### First-Two Reserve (Auto-Upgrade) Rule
- For Slots 2-16, the first two contributors at each level are reserved for the corresponding upline's upgrade at that slot number; remaining contributors are distributed by level rules.

### Example
**If a partner upgrades to Slot 5, the 5th upline will receive 30% upgrade commission from that slot's value.**

### Commission Flow Structure
- **Direct Commission**: 30% goes to upline at corresponding level
- **Distribution**: Remaining 70% distributed across levels 1-16
- **Level Matching**: Slot number must match upline level for 30% commission

### Upgrade Commission Logic
- When downline upgrades Slot 1 → Immediate upline gets 30% commission
- When downline upgrades Slot 2 → Immediate upline gets 30% commission
- When user upgrades Slot 3 → 3rd upline gets 30% commission
- When user upgrades Slot 4 → 4th upline gets 30% commission

---

## 12. BINARY MISSED PROFIT & LEVEL REWARDS

### Missed Rewards Scenarios
**MISSED REWARDS USUALLY OCCUR FOR TWO REASONS:**

1. **Account Inactivity**: The account is inactive and does not have two personal partners
2. **Level Advancement**: A member advances to a higher level than their sponsor

### Missed Profit Handling
**SUCH REWARDS ARE ACCUMULATED IN THE LEADERSHIP STIPEND AND DISTRIBUTED AMONG MEMBERS WHO ACHIEVE THE TARGETS.**

### Missed Commission Example
- **Scenario**: If you are on Level-4 and your team upgrades Slot-5 from Level-5
- **Result**: You will not get a commission because your level is lower than the upgrade slot
- **Handling**: Those missed profits go to the Leadership Stipend as reward

### Leadership Stipend System
- Missed profits are not lost
- Accumulated in Leadership Stipend pool
- Distributed to members who achieve targets
- Rewards active and successful members

---

## 13. UPDATED DEVELOPMENT REQUIREMENTS

### Critical Business Logic Points

1. **User Creation Success**:
   - When a user is successfully created, they should be added to the binary tree with 1 position
   - This triggers the binary tree placement logic

2. **User Join Process**:
   - When a user joins, the first 2 slots of the binary program should become active
   - User needs 2 partners to activate their ID
   - Earnings from first 2 partners are used for auto-upgrade

3. **Auto Upgrade System**:
   - All upgrades are automatic
   - First 2 partners' earnings fund next slot upgrade
   - User advances to next level with profit

4. **Commission Structure**:
   - 10% commission on joining and slot upgrades
   - 30% upgrade commission to corresponding level upline
   - Remaining 70% distributed across levels 1-16

5. **Rank System**:
   - 15 special ranks (Bitron to Omega)
   - Achieved by activating Binary and Matrix slots
   - Represents leadership and growth

6. **Missed Profit Handling**:
   - Missed profits go to Leadership Stipend
   - Distributed to members who achieve targets
   - Prevents loss of commissions due to inactivity or level mismatches

### Implementation Priority (Updated)

1. **Phase 1**: Binary Tree Placement System ✅ (Already implemented and tested)
2. **Phase 2**: User Creation Integration with Binary Tree
3. **Phase 3**: Auto Upgrade System Implementation
4. **Phase 4**: Commission Calculation and Distribution
5. **Phase 5**: Rank System Implementation
6. **Phase 6**: Missed Profit and Leadership Stipend System
7. **Phase 7**: Matrix Program Implementation
8. **Phase 8**: Global Program Implementation
9. **Phase 9**: Multi-program Integration

---

## 14. TECHNICAL IMPLEMENTATION REQUIREMENTS

### Database Models Needed

1. **User Model** (Already exists)
   - Add rank field
   - Add activation status
   - Add partner count tracking

2. **BinaryTree Model** (Already exists)
   - Extend with slot activation tracking
   - Add upgrade history
   - Add commission tracking

3. **Commission Model** (New)
   - Track commission types (joining, upgrade, missed)
   - Store commission amounts and recipients
   - Track commission status (pending, paid, missed)

4. **Rank Model** (New)
   - Define 15 ranks with requirements
   - Track user rank progression
   - Store rank benefits and privileges

5. **LeadershipStipend Model** (New)
   - Track missed profits
   - Manage stipend distribution
   - Track target achievements

### API Endpoints Required

1. **User Management**:
   - `POST /users/create` - Create user with binary tree placement
   - `POST /users/activate` - Activate user with 2 partners
   - `GET /users/rank` - Get user rank information

2. **Binary Tree Operations**:
   - `POST /binary/place` - Place user in binary tree
   - `POST /binary/upgrade` - Process slot upgrade
   - `GET /binary/structure` - Get tree structure

3. **Commission Management**:
   - `POST /commissions/calculate` - Calculate commissions
   - `POST /commissions/distribute` - Distribute commissions
   - `GET /commissions/history` - Get commission history

4. **Auto Upgrade System**:
   - `POST /auto-upgrade/process` - Process auto upgrade
   - `GET /auto-upgrade/status` - Get upgrade status

5. **Rank System**:
   - `POST /ranks/update` - Update user rank
   - `GET /ranks/list` - Get all ranks
   - `GET /ranks/requirements` - Get rank requirements

### Business Logic Implementation

1. **Auto Upgrade Logic**:
   ```python
   def process_auto_upgrade(user_id):
       # Check if user has 2 active partners
       # Calculate earnings from first 2 partners
       # Determine next slot upgrade cost
       # Process automatic upgrade
       # Update user level and rank
   ```

2. **Commission Calculation**:
   ```python
   def calculate_commissions(upgrade_user_id, slot_number):
       # Calculate 30% commission for corresponding level upline
       # Calculate remaining 70% distribution across levels 1-16
       # Handle missed profits
       # Update commission records
   ```

3. **Rank Progression**:
   ```python
   def update_user_rank(user_id):
       # Check activated slots in Binary and Matrix
       # Determine current rank based on slot activations
       # Update user rank
       # Trigger rank-based benefits
   ```

---

## 15. ROYAL CAPTAIN BONUS

### Overview
The Royal Captain Bonus is a special reward program for members who refer others with both Matrix and Global packages.

### Bonus Structure
**IF A PERSON JOINS WITH BOTH THE MATRIX AND GLOBAL PACKAGES AND REFERS 5 PEOPLE WHO ALSO JOIN WITH BOTH MATRIX AND GLOBAL, THEY WILL RECEIVE $200 FROM THE ROYAL CAPTAIN FUND.**

**IF THE SAME PERSON REFERS ANOTHER 5 PEOPLE WITH BOTH MATRIX AND GLOBAL PACKAGES, THEY WILL RECEIVE ANOTHER $200.**

**IN THIS WAY, THE SAME PERSON CAN CONTINUE EARNING BONUSES FOR REFERRING MEMBERS WITH BOTH MATRIX AND GLOBAL PACKAGES ACCORDING TO THE CHART BELOW:**

### Royal Captain Bonus Chart

| Direct partner (Joined in binary, matrix and global) | Global Team (Total team) | Rewards (USDT) |
| :--------------------------------------------------- | :----------------------- | :------------- |
| 5                                                   | 0                        | $200           |
| 5                                                   | 10                       | $200           |
| 5                                                   | 50                       | $200           |
| 5                                                   | 100                      | $200           |
| 5                                                   | 200                      | $250           |
| 5                                                   | 300                      | $250           |

### Royal Captain Logic
- Requires both Matrix and Global package participation
- Must maintain 5 directly invited partners
- Bonus increases with global team growth
- Continuous earning potential

---

## 16. PRESIDENT REWARD

### Overview
The President Reward is a special bonus program for members who achieve specific milestones in direct invitations and global team size.

### Qualification Criteria
Qualify initially with 10 direct partners and a global team of 400. Rewards then scale by reaching the following thresholds:

### President Reward Tiers

| Direct partner (Joined in binary, matrix and global) | Global Team (Total team) | Rewards (USDT) |
| :--------------------------------------------------- | :----------------------- | :------------- |
| 10                                                  | 400                      | $500           |
| 10                                                  | 600                      | $700           |
| 10                                                  | 800                      | $700           |
| 10                                                  | 1000                     | $700           |
| 10                                                  | 1200                     | $700           |
| 15                                                  | 1500                     | $800           |
| 15                                                  | 1800                     | $800           |
| 15                                                  | 2100                     | $800           |
| 15                                                  | 2400                     | $800           |
| 20                                                  | 2700                     | $1500          |
| 20                                                  | 3000                     | $1500          |
| 20                                                  | 3500                     | $2000          |
| 20                                                  | 4000                     | $2500          |
| 20                                                  | 5000                     | $2500          |
| 25                                                  | 6000                     | $5000          |

### President Reward Logic
- Requires 30 direct invitations in both Global and Matrix
- Progressive bonus structure based on team size
- Higher rewards for larger global teams
- Tier-based achievement system

---

## 17. LEADERSHIP STIPEND

### Overview
The Leadership Stipend provides daily returns for members who upgrade to higher-level slots (10-16).

### Stipend Rules
**If a person upgrades to any slot between 10 and 16, they will receive double the value of that slot as a daily return. However, if someone upgrades to another slot before receiving the full double amount from the previous slot, they will start receiving double the value of the new slot as a daily return.**

### Leadership Stipend Tiers

| Tier Name  | Slot Value (BNB) |
| :--------- | :--------------- |
| LEADER     | 1.1264 BNB       |
| VANGURD    | 2.2528 BNB       |
| CENTER     | 4.5056 BNB       |
| CLIMAX     | 9.0112 BNB       |
| ENTERNITY  | 18.0224 BNB      |
| KING       | 36.0448 BNB      |
| COMMENDER  | 72.0896 BNB      |

### Stipend Logic
- Double slot value as daily return
- Applies to slots 10-16 only
- New slot upgrade resets the return calculation
- Progressive daily income system

#### Leadership Stipend Distribution
- Slot 10: 30%
- Slot 11: 20%
- Slot 12: 10%
- Slot 13: 10%
- Slot 14: 10%
- Slot 15: 10%
- Slot 16: 5%
- Slot 17: 5%

---

## 18. MATRIX PARTNER INCENTIVE

### Overview
The Matrix Partner Incentive provides commission structure for Matrix program participation.

### Incentive Structure
**IF A PERSON JOINS THE MATRIX WITH $11, THEIR UPLINE WILL RECEIVE A 10% COMMISSION FROM THE JOINING AND FROM EACH SLOT UPGRADE.**

### Matrix System Features
- **MATRIX HAS RECYCLE SYSTEM** - Special recycling mechanism
- **3x Matrix Structure** - Each level has 3 members under each parent
- **10% Commission** - On joining and slot upgrades
- **Upline Benefits** - Receives commissions from all downline activities

### Matrix Tree Structure
- **Level 1**: 3 members directly under you
- **Level 2**: 9 members (3 under each Level 1 member)
- **Level 3**: 27 members (3 under each Level 2 member)
- **Recycle System**: Special mechanism for matrix completion

### Matrix Recycle System (Detailed)
**CRITICAL FEATURE**: 39-member completion with automatic recycle mechanism.

#### Recycle System Rules:
- **39-Member Completion**: Each slot (1-15) completes with 39 members across 3 levels (3 + 9 + 27)
- **Automatic Recycle**: When all 39 positions fill, that slot RECYCLES to direct upline's corresponding slot
- **No Re-payment**: Recycled user doesn't pay joining fee again
- **Fund Distribution**: Triggering join/upgrade fee distributed in upline's tree
- **Level Income**: Distributed to First/Second/Third upline according to user's relative level in new tree

#### Recycle Process:
1. **Tree Completion**: Matrix slot reaches 39 members (3 + 9 + 27 structure)
2. **New Tree Creation**: New empty tree created for same slot
3. **Recycle Placement**: User moves to direct upline's same slot empty tree
4. **Fund Distribution**: Recycle user's fee distributed in new tree location
5. **Level Relationships**: Income distribution adjusts based on new tree placement

#### Recycle Placement Logic:
- **Level 1 Placement**: If recycled into upline's Level-1, upline becomes Level-2, their upline becomes Level-3
- **Level 2/3 Placement**: If placed into Level-2/3, relationships adjust accordingly for income distribution
- **BFS Placement**: Uses Breadth-First Search algorithm for optimal placement
- **Income Distribution**: Always resolves relative to new tree placement

#### Recycle Data Model:
- **Multiple Recycles**: User can have multiple recycle instances per slot
- **Immutable Snapshots**: Each recycle creates separate, immutable snapshot of 3-level tree
- **Historical Trees**: Previous trees can be fetched reliably even after multiple recycles
- **Completion Tracking**: System tracks recycle completion and triggers new tree creation

### Matrix Recycle Data Model
- A user can have multiple recycle instances per slot. Each recycle creates a separate, immutable snapshot of a 3-level tree (max 39 members).
- Storage is snapshot-based so historical trees can be fetched reliably, even after multiple recycles.

Entities:
- MatrixRecycleInstance
  - id (UUID/PK)
  - user_id (FK → users)
  - slot_number (1-15)
  - recycle_no (1-based counter per user_id + slot_number)
  - is_complete (boolean; true when all 39 positions are filled)
  - created_at, completed_at (timestamps)
  - UNIQUE(user_id, slot_number, recycle_no)
- MatrixRecycleNode
  - id (UUID/PK)
  - instance_id (FK → MatrixRecycleInstance)
  - occupant_user_id (FK → users)
  - level_index (1, 2, or 3)
  - position_index (0-based within level; 0..2 for L1, 0..8 for L2, 0..26 for L3)
  - placed_at (timestamp)
  - UNIQUE(instance_id, level_index, position_index)

Notes:
- If a user's slot has never recycled, the "current" tree is considered the in-progress tree; serve it partially with however many nodes exist.
- On each recycle completion, increment recycle_no and start a fresh in-progress tree for that slot.

### Placement and Indexing Rules (Authoritative)
- Level sizes: L1 = 3, L2 = 9, L3 = 27. Completion at 39 occupants.
- L1 index mapping: 0 = left, 1 = upline-reserve (middle), 2 = right.
- L2 indexing is breadth-first, left-to-right under L1 parents:
  - Positions 0..2 under L1[0]; 3..5 under L1[1]; 6..8 under L1[2].
  - Formula: L2 index = parentL1Index * 3 + childOffset (childOffset ∈ {0,1,2}).
- L3 indexing is breadth-first, left-to-right under L2 parents:
  - Positions 0..2 under L2[0], 3..5 under L2[1], …, 24..26 under L2[8].
  - Formula: L3 index = parentL2Index * 3 + childOffset.
- Placement algorithm (BFS): always place at the shallowest level with a vacancy, scanning left→right. L1 fills strictly in order: left → middle (upline-reserve) → right.
- Recycle re-entry placement: apply the same BFS algorithm in the direct upline's current in-progress tree for that slot. If that tree is full at the target level per rules, follow spillover to the next eligible upline path and continue BFS.
- Duplicate occupants: the same `occupant_user_id` may appear multiple times across trees due to recycle re-entries. Treat nodes as placements, not a global uniqueness constraint.

---

## 19. DREAM MATRIX

### Overview
The Dream Matrix is a mandatory program with specific earning requirements and profit calculations.

### Joining Requirements
**A PERSON MUST JOIN THE MATRIX BY PURCHASING THE FIRST SLOT, AND TO START EARNING, THEY MUST HAVE 3 DIRECT PARTNERS AS A MANDATORY REQUIREMENT.**

### Calculation Context
**For illustration purposes, the matrix program calculation has been based solely on the 5th slot, with a total value of $800. This approach helps simplify the explanation of the process.**

### Dream Matrix Profit Calculation

| Level | Member | Percentage(%) | 800$ | Total-Profit |
| :---- | :----- | :------------ | :--- | :----------- |
| 1     | 3      | 10%           | $80  | $240         |
| 2     | 9      | 10%           | $80  | $720         |
| 3     | 27     | 15%           | $120 | $3240        |
| 4     | 81     | 25%           | $200 | $16200       |
| 5     | 243    | 40%           | $320 | $77760       |
| **Total** | **363** | **100%** | **$800** | **$98160** |

### Dream Matrix Logic
- Mandatory 3 direct partners requirement
- Progressive commission percentages
- 3x matrix structure (3, 9, 27, 81, 243)
- Total profit calculation based on slot value

---

## 20. MATRIX AUTO UPGRADE SYSTEM

### Overview
The Matrix Auto Upgrade System automatically uses earnings from specific members to fund next slot upgrades.

### Auto Upgrade Rule
**FROM LEVEL 1 TO LEVEL 15, THE 100% EARNINGS FROM THE MIDDLE 3 MEMBERS WILL BE USED FOR THE NEXT SLOT UPGRADE.**

### Matrix Tree Structure
- **YOU** are at the top of your personal matrix
- **Level 1**: 3 members directly under you
  - Left member
  - **Upline Reserve** (middle)
  - Right member
- **Level 2**: 9 members (3 under each Level 1 member)
  - **Middle 3 members** (one under each Level 1 member) contribute 100% earnings for auto-upgrade
- **Level 3**: 27 members (3 under each Level 2 member)

### Auto Upgrade Logic
- **100% earnings from middle 3 members** at each level fund next slot upgrade
- **Automatic reinvestment** for next slot upgrade
- **Applies from Level 1 to Level 15**: This rule applies across all matrix levels
- **Upline Reserve position** for special handling

### Middle Position Logic
1. **Level 1 Structure**: 3 members directly under main user (left, middle/upline-reserve, right)
2. **Level 2 Structure**: 9 members (3 under each Level 1 member)
3. **Middle 3 Identification**: One member from each Level 1 branch (positions 4, 5, 6 in Level 2)
4. **Fund Collection**: 100% of middle 3 users' slot fees go to main user's next slot upgrade
5. **Manual Activation Option**: Users can manually add funds to activate slots
6. **Reserve Combination**: 2 reserves + 1 manual fund, or 1 reserve + 2 manual funds

### Super Upline Detection
- **System Check**: When user joins matrix, system checks upline's upline level and position
- **Middle Position**: If user is in middle position of their level, fee goes to super upline's slot activation fund
- **Manual Override**: Users can manually add funds to activate slots even without sufficient reserves

### Manual Upgrade Options
- You may upgrade manually using wallet funds.
- Reserve combination is allowed: with 2 reserves + 1 wallet share, or 1 reserve + 2 wallet shares to complete an upgrade.
- If the next slot is already upgraded, no further funds from that tree go into reserve.

### Sweepover Rules (Updated, Authoritative)
**CRITICAL FEATURE**: Sweepover mechanism with 60-level search for eligible upline.

#### Sweepover Definition:
- **Sweepover occurs** when a junior upgrades a slot before their upline/senior has upgraded the same slot
- **Junior jumps** into the super-upline's current in-progress tree for that slot (placed by BFS per matrix rules)
- **60-level search**: System searches up to 60 levels for eligible upline with target slot active
- **Slot activation requirement**: Upline must have target slot active to receive placement

#### Sweepover Logic:
1. **Eligibility Check**: When user activates slot, system checks if direct upline has that slot active
2. **Escalation Search**: If direct upline doesn't have slot, system searches up to 60 levels for eligible upline
3. **Placement**: User is placed in eligible upline's tree for that slot
4. **Income Distribution**: Placement and income references resolve relative to new tree placement
5. **Missed Income**: Skipped upline doesn't receive level-income for that slot (missed for that slot only)
6. **Future Restoration**: Normal distribution restored if senior upgrades first at later slots

#### Example Scenario:
- User A has Slot 5 active, User B has Slot 4, User C has Slot 3
- User D activates Slot 3 → placed in User C's tree (normal)
- User G activates Slot 4 → sweeps over User C (who doesn't have Slot 4) and goes to User B's tree
- User I activates Slot 4 → goes to User C's tree (since User C now has Slot 5 active)

### Eligibility Escalation and Fallback
- When resolving sweepover placement, check eligibility upward to the 60th-level upline for an upgraded holder of the target slot.
- If no eligible upline exists within 60 levels, place into the Mother ID's tree for that slot.

### Level Distribution (Matrix) — 3 Levels: 20% / 20% / 60%
Matrix level-income distributes across the immediate three upline levels relative to the placed position:
- Level-1 (closest ancestor): 20%
- Level-2: 20%
- Level-3: 60%

Example with an $800 basis for illustration:

| Level | Team | %   | Per-member | Total      |
| :---- | :--- | :-- | :--------- | :--------- |
| 1     | 3    | 20% | $160       | $160×3 = $480 |
| 2     | 9    | 20% | $160       | $160×9 = $1440 |
| 3     | 27   | 60% | $320       | $320×27 = $8640 |
|       |      |      |            | **$10560** |

Summary: 1) 20%, 2) 20%, 3) 60%.

### Recycle Behavior with Sweepover
- Each slot (1–15) completes at 39 occupants (3/9/27) and then recycles. On recycle, a user re-enters the direct upline's corresponding slot using BFS placement.
- If the user originally occupied a position via sweepover, they will re-enter the same super-upline's tree on recycle, unless their immediate upline has upgraded that slot in the meantime. If the immediate upline later upgrades the same slot, subsequent upgrade/recycle for that slot will place under that upline per normal rules.
- Chain recycle: If a downline's final placement completes the upline's tree and triggers the upline's recycle, both recycles occur. The triggering join/upgrade amount is accounted for in the upline's tree at the tick-marked circle, and level-income distributes to the first/second/third uplines relative to that placement. This cascade may repeat multiple times.

### Direct vs Tree Upline (Authoritative)
- Direct Upline: The referral relationship. This never changes across slots or recycles.
- Tree Upline: The ancestor that receives level-income for a specific placement in a specific slot tree. This can change per slot and per recycle due to sweepover and BFS placement.

#### Initial Placement Resolution (Clarified)
- When a user joins Matrix for a given slot, resolve placement as follows:
  1) If the user's direct referrer (B) is active in Matrix for the target slot (or any eligible slot per rules), place the new user (C) under B's current in-progress tree using BFS. In this case, direct_upline = B and initial tree_upline = B. On later recycle(s), only tree_upline may change; direct_upline remains B.
  2) If the direct referrer (B) is not active in Matrix for that slot (or has not joined Matrix), escalate up to B's referrer (A) and check eligibility. If A is eligible, place C under A's tree using BFS. In this case, direct_upline = B (unchanged referral), but initial tree_upline = A. PI and Mentorship remain referral-based and continue to reference B (and B's referrer) regardless of tree placement.
  3) Continue escalation up the referral chain as needed (up to 60 levels). If no eligible upline is found within the escalation depth, place under the configured Mother ID's tree. In all cases, direct_upline never changes once set.

Notes:
- This behavior ensures sweepover/escalation never mutates the referral chain. Recycles can cause tree_upline to change (per sweepover and BFS), but direct_upline is immutable.

### Recycle Re-entry Algorithm (BFS with Ancestor Resolution)
When a user completes a slot (39 occupants) and recycles:
1) If the immediate upline has the same slot active, place the recycling user into the immediate upline's current in-progress tree using BFS:
   - Try Level-1 first (any of the 3 direct positions). If none are free, proceed breadth-first to Level-2 then Level-3.
2) If the immediate upline does NOT have that slot active, escalate upward to the next upline who has that slot active and space available, using the same BFS rule. Continue escalation up to 60 levels; if none is eligible, place into the Mother ID's tree for that slot.
3) The resulting three ancestors above the placed position define Level-1/2/3 for income distribution (20/20/60).

Implication: A user may temporarily appear under a super-upline's tree (sweepover or recycle), while the direct upline relationship remains unchanged. Later, if the skipped upline activates the relevant slot (or a higher slot before the downline's next upgrade), subsequent placements can return under that upline's tree.

### Worked Example (Slots 3 and 4)
Assume the hierarchy: You (A) → Me (B) → My Downline (D).
- A has Slot-3 active. D has Slot-3 active. B does NOT yet have Slot-3.
- D completes Slot-3 and recycles. Since B lacks Slot-3, D is placed into A Slot-3 tree by BFS. This may place D at A Level-1 if a direct position is free, otherwise at Level-2/3 per BFS. During this time, Tree Upline for D@Slot-3 is A. Direct Upline remains B.
- Later, B upgrades Slot-3. Before D upgrades to Slot-4, D's next placement (e.g., D's Slot-4 join/upgrade) will resolve under B's tree if B has Slot-4 first (or activates the relevant slot before D's corresponding upgrade). Thus Tree Upline for D@Slot-4 becomes B, while Direct Upline was always B.

### Bonuses Unaffected by Sweepover
- Partner Incentive (10%), Newcomer Growth Support, and Mentorship Bonus are not impacted by sweepover; they distribute per their normal rules regardless of the tree used for level-income.

### Notes
- "Second-level middle three fund the next slot" remains the authoritative auto-upgrade rule for Matrix and is unchanged here.
- For concrete scenarios (e.g., junior upgrades $60 and sweeps over a non-upgraded upline into a super-upline's tree), recycle re-entry will remain in that same tree so long as the skipped upline stays non-upgraded at that slot. If the upline later upgrades (e.g., $60 and $240), then when the junior reaches the higher slot (e.g., $240) the placement and distribution will occur under the upgraded upline per normal.

### Partner Incentive & Mentorship Bonus (Matrix) — Distribution Rules
- Partner Incentive (PI) — 10%: Paid to the direct sponsor/upline of the user who joins or upgrades a Matrix slot. This is always based on the referral chain (not tree placement). Unaffected by sweepover or recycle.
- Mentorship Bonus — 10%: Paid to the "super upline" (the sponsor of the sponsor) for transactions made by the direct-of-direct partner (i.e., your direct's direct). Also based on the referral chain and unaffected by sweepover or recycle.
- Scope: Both apply on Matrix join ($11) and on every Matrix slot upgrade (slots 1–15) per slot value.
- Independence: PI and Mentorship are independent of the 20/20/60 level-income and of reserve mechanics. They are computed in parallel with level-income.
- Missing super upline: If a super upline does not exist for a user (no sponsor-of-sponsor), the Mentorship portion for that user does not apply.

Example:
- If X joins/upgrade a Matrix slot and S is X's direct sponsor, Y is S's sponsor:
  - PI 10% of the slot amount → S (direct sponsor of X).
  - Mentorship 10% of the slot amount → Y (sponsor of S), because X is a direct-of-direct relative to Y.
  - These payouts are independent of whether X's level-income flows under S's tree or under any super-upline's tree due to sweepover.


### Matrix Recycle Tree API
- Fetch a user's matrix tree by recycle number and slot. Frontend provides user_id and recycle_no; backend returns the tree snapshot for that recycle. If multiple recycles happened, there will be multiple trees per user.
- If no recycle exists yet for that slot, return the current in-progress tree (partial), with however many members exist.

Endpoints:
- GET `/matrix/recycle-tree?user_id={uid}&slot={1-15}&recycle_no={n|current}`
  - recycle_no: integer ≥ 1, or the string `current` to force the in-progress tree
  - Behavior:
    - If recycle_no = current → return current in-progress tree
    - If recycle_no ≤ max recycle for that user+slot → return the matching snapshot
    - If recycle_no > max recycle (or none exist) → return current in-progress tree
  - Response shape:
    ```json
    {
      "user_id": "...",
      "slot_number": 1,
      "recycle_no": 2,
      "is_snapshot": true,
      "is_complete": true,
      "total_recycles": 3,
      "nodes": [
        { "level": 1, "position": 0, "user_id": "..." },
        { "level": 1, "position": 1, "user_id": "..." },
        { "level": 1, "position": 2, "user_id": "..." },
        { "level": 2, "position": 0, "user_id": "..." }
        // ... up to 39 for complete snapshots; partial for in-progress
      ]
    }
    ```
  - Metadata helps frontend navigate between snapshots and current state.

- GET `/matrix/recycles?user_id={uid}&slot={1-15}`
  - Returns a list of recycle instances for that user+slot with `recycle_no`, `is_complete`, `created_at`, `completed_at`.

---

## 21. UPDATED IMPLEMENTATION PRIORITY

### Phase-by-Phase Development Plan

1. **Phase 1**: Binary Tree Placement System ✅ (Already implemented and tested)
2. **Phase 2**: User Creation Integration with Binary Tree
3. **Phase 3**: Binary Auto Upgrade System Implementation
4. **Phase 4**: Commission Calculation and Distribution
5. **Phase 5**: Rank System Implementation
6. **Phase 6**: Matrix Program Implementation
7. **Phase 7**: Matrix Auto Upgrade System
8. **Phase 8**: Dream Matrix Implementation
9. **Phase 9**: Global Program Implementation
10. **Phase 10**: Royal Captain Bonus System
11. **Phase 11**: President Reward System
12. **Phase 12**: Leadership Stipend System
13. **Phase 13**: Missed Profit and Leadership Stipend System
14. **Phase 14**: Multi-program Integration
15. **Phase 15**: Advanced Features and Optimization

### Critical Business Logic Points (Updated)

1. **User Creation Success**:
   - When a user is successfully created, they should be added to the binary tree with 1 position
   - This triggers the binary tree placement logic

2. **User Join Process**:
   - When a user joins, the first 2 slots of the binary program should become active
   - User needs 2 partners to activate their ID
   - Earnings from first 2 partners are used for auto-upgrade

3. **Binary Auto Upgrade System**:
   - All upgrades are automatic
   - First 2 partners' earnings fund next slot upgrade
   - User advances to next level with profit

4. **Matrix Auto Upgrade System**:
   - 100% earnings from middle 3 members fund next slot upgrade
   - Applies from Level 1 to Level 15
   - Upline Reserve position for special handling

5. **Commission Structure**:
   - 10% commission on joining and slot upgrades
   - 30% upgrade commission to corresponding level upline
   - Remaining 70% distributed across levels 1-16

6. **Rank System**:
   - 15 special ranks (Bitron to Omega)akhon
   - Achieved by activating Binary and Matrix slots
   - Represents leadership and growth

7. **Special Bonus Programs**:
   - Royal Captain Bonus for Matrix + Global referrals
   - President Reward for 30 direct invitations
   - Leadership Stipend for slots 10-16

8. **Missed Profit Handling**:
   - Missed profits go to Leadership Stipend
   - Distributed to members who achieve targets
   - Prevents loss of commissions due to inactivity or level mismatches

---

## 22. SPARK BONUS

### Overview
The Spark Bonus is a special fund distribution system that provides rewards across different levels of the Matrix program.

### Spark Bonus Fund Structure
20% of the Spark Bonus fund (funded by 8% from Binary and 8% from Matrix), plus an additional 5% from Global, is allocated to the Triple Entry Reward. The remaining 80% (treated as 100% baseline) is distributed across Matrix Levels 1-14 according to the chart below.

### Spark Bonus Distribution Chart

| Slot | Percentage (%) |
| :--- | :------------- |
| 1    | 15%            |
| 2    | 10%            |
| 3    | 10%            |
| 4    | 10%            |
| 5    | 10%            |
| 6    | 7%             |
| 7    | 6%             |
| 8    | 6%             |
| 9    | 6%             |
| 10   | 4%             |
| 11   | 4%             |
| 12   | 4%             |
| 13   | 4%             |
| 14   | 4%             |
| **Total** | **= 100%**     |

### Spark Bonus Logic
- **Fund Sources**: 8% from Binary + 8% from Matrix + 5% from Global = 21% total
- **Triple Entry Reward**: 20% of Spark Bonus + 5% from Global = 25% total
- **Remaining Distribution**: 80% of Spark Bonus treated as 100% baseline
- **Matrix Slot Distribution**: 14 slots with progressive percentages
- **Distribution Frequency**: Every 30 days for 60 days (2 distributions per slot completion)

### Triple Entry Reward Details
- **Eligibility**: Users who join all three programs (Binary + Matrix + Global) in first step
- **Return Amounts**:
  - Binary: 0.006 BNB (2 slots: 0.002 + 0.004)
  - Matrix: $11 (first slot)
- **Distribution**: Equal distribution among all Triple Entry users
- **Frequency**: Every 30 days

### Spark Bonus Distribution Example
**Example Scenario**: 1000 users in Matrix Slot 1 today
- **Fund Allocation**: 15% of total Spark fund for Slot 1
- **Distribution**: Equal among all 1000 users
- **Calculation**: If total Spark fund = $1000, then Slot 1 gets $150 (15%)
- **Per User**: $150 ÷ 1000 = $0.15 per user

**Slot-wise Distribution**:
- Slot 1 (100 users): 15% of fund
- Slot 2 (80 users): 10% of fund  
- Slot 3 (60 users): 10% of fund
- Slot 4 (40 users): 10% of fund
- Slot 5 (20 users): 10% of fund
- And so on for all 14 slots

### Matrix Slot Completion Bonus
- **Trigger**: When a Matrix slot is completed
- **Bonus Frequency**: Every 30 days for 60 days (2 distributions)
- **Distribution**: Based on slot completion order and fund allocation percentages

---

## 23. NEW COMMER GROWTH SUPPORT

### Overview
This program is designed to boost non-working income for new members joining the Matrix system.

### Key Benefits

1. **Instant Bonus**:
   - Upon joining Matrix, members receive an Instant Bonus from Newcomer Growth Support (NGS)
   - This bonus can be cashed out instantly

2. **Extra Earning Opportunities (Monthly)**:
   - At the end of the month (30 days), members gain extra earning opportunities
   - These opportunities are based on the activity of their Upline

3. **Upline Rank Bonus (10%)**:
   - When a member achieves the same rank as their Upline, they receive an additional 10% Bonus
   - This bonus is paid directly from the Upline
   - This benefit applies from the very first joining to every subsequent Slot Upgrade

### Newcomer Growth Support Fund Distribution
**CRITICAL FEATURE**: 50/50 split distribution system.

#### Fund Distribution Logic:
1. **50% Instant Claim**: User can immediately claim 50% of their newcomer growth support
2. **50% Upline Fund**: Remaining 50% goes to user's direct upline's newcomer growth fund
3. **30-Day Distribution**: Upline's fund distributed among all direct referrals every 30 days
4. **Equal Distribution**: All direct referrals of upline can claim equal share

#### Distribution Process:
- **Upon Matrix Join**: User receives newcomer growth support fund
- **Instant Withdrawal**: User can immediately withdraw 50% to their wallet
- **Upline Fund Creation**: 50% goes to upline's newcomer growth support fund
- **Monthly Distribution**: Every 30 days, upline's fund distributed among all their direct referrals
- **Claimable by All**: All direct referrals can claim their equal share from upline's fund

### Summary of Earning Journey
- **Instant Reward**: 50% immediate claim upon joining
- **Extra Income**: Monthly opportunities based on upline activity
- **Long-Term Support**: Continuous earning through upline's direct referral network

All these benefits are combined into one program to ensure an immediate and sustained earning journey.

---

## 24. MENTORSHIP BONUS

### Overview
The Mentorship Bonus is a Direct-of-Direct income program within the Matrix program, designed to maximize funds from partners invited by your direct referrals.

### Bonus Structure
For every person you directly invite, and from the people they directly invite, the Super Upline will receive a 10% commission from their joining fees and all their slot upgrades. This is considered Direct-of-Direct income.

### Example of Mentorship Bonus
1. **A** is in the Matrix program
2. **A** directly invites **B**
3. **B** directly invites **C, D, and E**

**Result:**
When **C, D, and E** join the Matrix and upgrade their slots, 10% from all those upgrades will go to **A** as the Super Upline.

### Visual Representation
```
MENTOR (A)
   ↓ (10% commission from Upline's direct referrals)
UPLINE (B)
   ↓ (10% commission from Direct of Direct Partners)
DIRECT OF DIRECT PARTNERS (C, D, E)
```

---

## 25. GLOBAL PARTNER INCENTIVE

### Overview
The Global Partner Incentive provides commission structure for Global program participation.

### Incentive Structure
**IF A PERSON JOINS THE GLOBAL WITH $33, THEIR UPLINE WILL RECEIVE A 10% COMMISSION FROM THE JOINING AND FROM EACH SLOT UPGRADE.**

### Global Tree Structure
- **Global Tree**: Shows progression from 4 people to 8 people
- **Slot-2**: Represents the second slot in the global system
- **10% Commission**: On joining and slot upgrades
- **Upline Benefits**: Receives commissions from all downline activities

### Global System Features
- $33 joining fee
- 10% commission structure (Partner Incentive)
- Tree-based progression system
- Multiple slot levels
- **Global Incentive**: 10% income from each direct partner's slot activities
- **24-hour Royal Captain Bonus**: $200 for 5 direct partners, progressive amounts
- **24-hour President Reward**: $500 for 10 direct partners + 80 global team, progressive amounts

---

## 26. PHASE-1 AND PHASE-2 SYSTEM

### Overview
The Phase-1 and Phase-2 system is a global pool progression mechanism that automatically upgrades users through different phases and slots.

### System Rules

1. **Joining**: **WHEN A PERSON JOINS THE GLOBAL POOL WITH $33, THEY ARE PLACED IN SLOT 1 OF PHASE 1.**

2. **Phase 1 to Phase 2 Upgrade**: **ONCE 4 PEOPLE ARE PLACED GLOBALLY UNDER THEM, THEIR SLOT IS AUTOMATICALLY UP-GRADED, AND THEY MOVE TO PHASE 2, OCCUPYING SLOT 1 THERE.**

3. **Phase 2 to Phase 1 Re-entry**: **WHEN THEIR SLOT 1 IN PHASE 2 IS COMPLETED WITH 8 PEOPLE GLOBALLY UNDER THEM, THEY RE-ENTER PHASE 1 AND ARE PLACED IN SLOT 2.**

4. **Continuation**: **THIS PROCESS CONTINUES, FOLLOWING THE DIAGRAM BELOW, UNTIL REACHING SLOT 16.**

### Phase Progression Flow
```
YOU
↓
PHASE-1, SLOT-1 (4 people) → UPGRADE
↓
PHASE-2, SLOT-1 (8 people) → UPGRADE
↓
PHASE-1, SLOT-2 (4 people) → UPGRADE
↓
PHASE-2, SLOT-2 (8 people) → UPGRADE
↓
...continues until SLOT 16
```

### Phase System Logic
- **PHASE-1**: Requires 4 people globally under user (4 slots per person)
- **PHASE-2**: Requires 8 people globally under user (8 slots per person)
- **Distribution from each slot**: 40% total (10% Partner Incentive + 30% for Phase upgrade)
- **Global Matrix Distribution**: 30% total (15% Royal Captain Bonus + 15% President Reward)
- **Profit**: 30%
- **Triple Entry Reward**: 5%
- **Shareholders**: 5%
- Automatic progression between phases
- Re-entry system for continuous advancement
- Continues up to Slot 16

### Global Program Tree Structure
**CRITICAL FEATURE**: Serial placement logic with first user priority.

#### Serial Placement Rules:
1. **First User Priority**: Very first user's tree opens first and has priority
2. **Serial Placement**: All subsequent users placed serially in first user's Phase 1 Slot 1 tree
3. **Phase Progression**: 4 users → Phase 2, 8 users → back to Phase 1 Slot 2
4. **Continuous Flow**: Process continues with all users following first user's progression

#### Placement Logic:
- **Very First User**: Platform's first user (could be Mother ID) gets tree priority
- **Serial Tree Building**: All next users placed serially in first user's Phase 1 Slot 1
- **Phase 1 Completion**: When 4 users fill first user's Phase 1 Slot 1, first user upgrades to Phase 2 Slot 1
- **Phase 2 Completion**: When 8 users fill first user's Phase 2 Slot 1, first user upgrades to Phase 1 Slot 2
- **Continuous Cycle**: Process repeats for all subsequent slots

#### Tree Distribution Logic:
- **30% Tree Upline Reserve**: For next slot upgrade (tree upline is the user receiving placement)
- **30% Tree Upline Wallet**: Direct payment to tree upline
- **10% Partner Incentive**: To direct referrer (who referred the joining user)
- **10% Royal Captain Bonus**: Global fund distribution
- **10% President Reward**: Global fund distribution
- **5% Share Holders**: Separate wallet
- **5% Triple Entry Reward**: Global fund distribution

---

## 27. TOP LEADER GIFT

### Overview
The Top Leader Gift program rewards individuals who achieve specific targets with valuable prizes.

### Qualification Criteria
**When a person achieves a specific target, he will be considered as a Top Leader and will receive the following rewards:**

### Top Leader Gift Rewards

| SL NO | Self Rank | Direct Partners Rank | Total Team | Reward |
| :---- | :-------- | :------------------ | :--------- | :----- |
| 01    | 06        | 5 DIRECT PARTNERS WITH 5 RANK | 300 | LAPTOP ($3000) |
| 02    | 08        | 7 DIRECT PARTNERS WITH 6 RANK | 500 | PRIVATE CAR ($30000) |
| 03    | 11        | 8 DIRECT PARTNERS WITH 10 RANK | 1000 | GLOBAL TOUR PACKAGE ($3000000) |
| 04    | 13        | 9 DIRECT PARTNERS WITH 13 RANK | 2000 | BUSINESS INVESTMENT FUND ($50000000) |
| 05    | 15        | 10 DIRECT PARTNERS WITH 14 RANK | 3000 | SUPER LUXURY APARTMENT ($150000000) |

### Top Leader Gift Logic
- Progressive reward system based on rank achievement
- Requires specific number of direct partners with certain ranks
- Total team size requirements
- Valuable physical and financial rewards
- Highest reward: $150,000,000 Super Luxury Apartment

---

## 28. JACKPOT PROGRAM OVERVIEW

### Overview
The Jackpot Program is a raffle draw system that provides opportunities to win millions of dollars.

### Program Description
**JACKPOT IS A RAFFLE DRAW SYSTEM. ANYONE CAN JOIN WITH JUST $2 AND GET THE CHANCE TO WIN MILLIONS OF DOLLARS.**

### Jackpot Fund Structure
**CRITICAL FEATURE**: 4-part distribution system with weekly draws.

#### Entry Requirements:
- **ENTRY FEES**: 0.0025 BNB per entry
- **Multiple Entries**: Users can enter multiple times with each entry requiring fee
- **DISTRIBUTION FREQUENCY**: Every Sunday (7 days accumulation period)
- **BINARY CONTRIBUTION**: 5% deduction from each Binary slot activation added to Jackpot fund

#### 4-Part Distribution System:

**1. OPEN POOL (50%)**:
- **10 Random Winners**: 10 randomly selected winners share 50% equally
- **Random Selection**: System randomly selects 10 winners from all entries
- **Equal Distribution**: 50% of total jackpot fund divided equally among 10 winners

**2. TOP DIRECT PROMOTERS POOL (30%)**:
- **20 Top Promoters**: 20 users with most direct referral entries share 30% equally
- **Direct Refer Counting**: System counts total entries from all direct referrals
- **Example**: UserA has 10 direct referrals, each with 5 entries = 50 direct refer entries
- **Rollover Mechanism**: If less than 20 promoters, unused portion rolls to next week's fund

**3. TOP BUYERS POOL (10%)**:
- **20 Top Buyers**: 20 users with most individual entries share 10% equally
- **Individual Entry Counting**: Based on total individual entries per user
- **Example**: UserA has 10 entries, UserB has 9 entries, UserC has 15 entries
- **Rollover Mechanism**: If less than 20 buyers, unused portion rolls to next week's fund

**4. NEW JOINERS POOL (10%)**:
- **10 Random New Joiners**: Last 7 days' Binary program joiners randomly selected
- **Eligibility**: Only users who joined Binary in last 7 days
- **Random Distribution**: 10% equally distributed among 10 randomly selected new joiners

### Free Coupons System
**NOTE- FREE COUPONS FOR BINARY SLOT UPGRADES**

| Slot | FREE Entry Coupons |
| :--- | :----------------- |
| 5    | 1 FREE Entry       |
| 6    | 2 FREE Entries     |
| 7    | 3 FREE Entries     |
| 8    | 4 FREE Entries     |
| 9    | 5 FREE Entries     |
| 10   | 6 FREE Entries     |
| 11   | 7 FREE Entries     |
| 12   | 8 FREE Entries     |
| 13   | 9 FREE Entries     |
| 14   | 10 FREE Entries    |
| 15   | 11 FREE Entries    |
| 16   | 12 FREE Entries    |
| 17   | 13 FREE Entries    |

### Jackpot Program Logic
- Low entry fee ($2) for high reward potential
- Multiple pool distribution system
- Free coupons for binary slot upgrades
- Progressive coupon system up to Slot 16
- Raffle-based winning mechanism

---

## 29. COMPREHENSIVE IMPLEMENTATION ROADMAP

### Complete Phase-by-Phase Development Plan

1. **Phase 1**: Binary Tree Placement System ✅ (Already implemented and tested)
2. **Phase 2**: User Creation Integration with Binary Tree
3. **Phase 3**: Binary Auto Upgrade System Implementation
4. **Phase 4**: Commission Calculation and Distribution
5. **Phase 5**: Rank System Implementation
6. **Phase 6**: Matrix Program Implementation
7. **Phase 7**: Matrix Auto Upgrade System
8. **Phase 8**: Dream Matrix Implementation
9. **Phase 9**: Global Program Implementation
10. **Phase 10**: Phase-1 and Phase-2 System
11. **Phase 11**: Royal Captain Bonus System
12. **Phase 12**: President Reward System
13. **Phase 13**: Leadership Stipend System
14. **Phase 14**: Spark Bonus System
15. **Phase 15**: New Commer Growth Support
16. **Phase 16**: Mentorship Bonus System
17. **Phase 17**: Global Partner Incentive
18. **Phase 18**: Top Leader Gift System
19. **Phase 19**: Jackpot Program Implementation
20. **Phase 20**: Missed Profit and Leadership Stipend System
21. **Phase 21**: Multi-program Integration
22. **Phase 22**: Advanced Features and Optimization

### Critical Business Logic Points (Final Update)

1. **User Creation Success**:
   - When a user is successfully created, they should be added to the binary tree with 1 position
   - This triggers the binary tree placement logic

2. **User Join Process**:
   - When a user joins, the first 2 slots of the binary program should become active
   - User needs 2 partners to activate their ID
   - Earnings from first 2 partners are used for auto-upgrade

3. **Binary Auto Upgrade System**:
   - All upgrades are automatic
   - First 2 partners' earnings fund next slot upgrade
   - User advances to next level with profit

4. **Matrix Auto Upgrade System**:
   - 100% earnings from middle 3 members fund next slot upgrade
   - Applies from Level 1 to Level 15
   - Upline Reserve position for special handling

5. **Global Phase System**:
   - Phase 1: 4 people globally under user
   - Phase 2: 8 people globally under user
   - Automatic progression between phases
   - Re-entry system for continuous advancement

6. **Commission Structure**:
   - 10% commission on joining and slot upgrades
   - 30% upgrade commission to corresponding level upline
   - Remaining 70% distributed across levels 1-16

7. **Rank System**:
   - 15 special ranks (Bitron to Omega)
   - Achieved by activating Binary and Matrix slots
   - Represents leadership and growth

8. **Special Bonus Programs**:
   - Royal Captain Bonus for Matrix + Global referrals
   - President Reward for 30 direct invitations
   - Leadership Stipend for slots 10-16
   - Spark Bonus distribution system
   - New Commer Growth Support
   - Mentorship Bonus (Direct-of-Direct income)
   - Top Leader Gift rewards

9. **Jackpot System**:
   - $2 entry fee raffle system
   - Multiple pool distribution
   - Free coupons for binary slot upgrades

10. **Missed Profit Handling**:
    - Missed profits go to Leadership Stipend
    - Distributed to members who achieve targets
    - Prevents loss of commissions due to inactivity or level mismatches

---

## 30. OUR ROAD MAP

### Overview
The "OUR ROAD MAP" diagram illustrates the various interconnected features and programs that form the core of the project's ecosystem, centered around a digital platform (represented by a laptop icon).

### Key Components and Programs

The roadmap is structured around a central platform, with different functionalities branching out:

#### Core Platform (Central Laptop Icon)
- Represents the central digital hub or application that integrates all other features.

#### Left Side Features:
- **NFT & GAMING PROGRAM**: A program focused on Non-Fungible Tokens and gaming.
- **E-COMMERCE PLATFORM**: An online platform for buying and selling goods or services.
- **EXCHANGER**: A system for exchanging assets, likely cryptocurrencies.
- **NFT & GAMING PLATFORM**: A dedicated platform for NFT and gaming activities.

#### Top Side Features:
- **SINGLE LEG PROGRAM**: A specific type of referral or earning program.
- **AI TRADING**: Automated trading functionalities powered by Artificial Intelligence.

#### Right Side Features:
- **GLOBAL AUTOPOOL BONUS 2**: A global bonus pool system, likely the second iteration or a specific type of autopool.
- **SOCIAL MEDIA & OTHERS APPS**: Integration with social media and other applications.
- **STAKING & MINING**: Features related to cryptocurrency staking and mining.
- **DAILY GAME EARNING**: Opportunities for users to earn through daily gaming activities.

#### Bottom Side Features:
- **WEB3.0 PROJECTS**: Initiatives or developments related to the decentralized web (Web3).
- **STAKING & MINING**: (Duplicate entry, indicating its importance or presence in multiple contexts) Features related to cryptocurrency staking and mining.

### Interconnectivity
All listed components are shown as directly connected to the central laptop icon, indicating that they are integrated parts of the main platform.

### Extended Implementation Roadmap

Based on the complete roadmap, the implementation phases should be expanded to include:

23. **Phase 23**: NFT & Gaming Program Implementation
24. **Phase 24**: E-Commerce Platform Development
25. **Phase 25**: Exchanger System Implementation
26. **Phase 26**: Single Leg Program Development
27. **Phase 27**: AI Trading System
28. **Phase 28**: Global Autopool Bonus 2
29. **Phase 29**: Social Media Integration
30. **Phase 30**: Staking & Mining Features
31. **Phase 31**: Daily Game Earning System
32. **Phase 32**: Web3.0 Projects Integration
33. **Phase 33**: Complete Platform Integration
34. **Phase 34**: Advanced Features and Optimization

---

## 31. COMPLETE PROJECT SUMMARY

### BitGPT Platform Overview
BitGPT is a comprehensive multi-program earning platform that combines:

#### Core Earning Programs:
1. **Binary Program** (BNB-based) - 16 tiers with auto-upgrade system
2. **Matrix Program** (USDT-based) - 3x matrix structure with recycle system
3. **Global Program** (USD-based) - Phase-1 and Phase-2 progression system
4. **Dream Matrix** - Mandatory program with progressive commissions

#### Special Bonus Systems:
5. **Royal Captain Bonus** - Matrix + Global referrals
6. **President Reward** - 30 direct invitations achievement
7. **Leadership Stipend** - Daily returns for slots 10-16
8. **Spark Bonus** - Fund distribution across Matrix levels
9. **New Commer Growth Support** - Instant bonuses for new members
10. **Mentorship Bonus** - Direct-of-Direct income program
11. **Top Leader Gift** - Progressive reward system
12. **Jackpot Program** - $2 raffle system with free coupons

#### Advanced Features:
13. **Rank System** - 15 special ranks (Bitron to Omega)
14. **Commission Structure** - 10% joining, 30% upgrade commissions
15. **Auto Upgrade Systems** - Both Binary and Matrix
16. **Missed Profit Handling** - Leadership Stipend distribution

#### Extended Platform Features:
17. **NFT & Gaming Program**
18. **E-Commerce Platform**
19. **Exchanger System**
20. **Single Leg Program**
21. **AI Trading**
22. **Social Media Integration**
23. **Staking & Mining**
24. **Daily Game Earning**
25. **Web3.0 Projects**

### Technical Implementation Status
- ✅ **Binary Tree Placement System** - Implemented and tested
- ✅ **User Creation Integration** - Implemented
- ✅ **Auto Upgrade Systems (Binary)** - Implemented
- ✅ **Commission Calculation (Binary)** - Implemented
- ⏳ **Matrix Program** - Pending implementation
- ⏳ **Global Program** - Pending implementation
- ⏳ **All Bonus Systems (non-binary)** - Pending implementation

### Next Development Priority
1. **Matrix Program Implementation** - Second major earning program
2. **Global Program Implementation** - Third major earning program
3. **Spark/Leadership/President/Royal Captain/Jackpot integrations** (as applicable)

---

## 32. COMPLETE FUND DISTRIBUTION PERCENTAGES

### Binary Program Fund Distribution
Based on the final requirements, here are the complete fund distribution percentages:

| Program/Component | Percentage (%) |
| :---------------- | :------------- |
| **Spark Bonus** | 8% |
| **Royal Captain Bonus** | 4% |
| **President Reward** | 3% |
| **Leadership Stipend** | 5% |
| **Jackpot Entry** | 5% |
| **Partner Incentive** | 10% |
| **Share Holders** | 5% |
| **Level Distribution** | 60% |

### Binary Level Distribution Breakdown
**60% Level Distribution** (treated as 100% for calculation):

| Level | Percentage (%) |
| :---- | :------------- |
| Level 1 | 30% |
| Level 2 | 10% |
| Level 3 | 10% |
| Level 4 | 5% |
| Level 5 | 5% |
| Level 6 | 5% |
| Level 7 | 5% |
| Level 8 | 5% |
| Level 9 | 5% |
| Level 10 | 5% |
| Level 11 | 3% |
| Level 12 | 3% |
| Level 13 | 3% |
| Level 14 | 2% |
| Level 15 | 2% |
| Level 16 | 2% |

### Matrix Program Fund Distribution
**Matrix Program** has different distribution percentages:

| Program/Component | Percentage (%) |
| :---------------- | :------------- |
| **Spark Bonus** | 8% |
| **Royal Captain Bonus** | 4% |
| **President Reward** | 3% |
| **Newcomer Growth Support** | 20% |
| **Mentorship Bonus** | 10% |
| **Partner Incentive** | 10% |
| **Share Holders** | 5% |
| **Level Distribution** | 40% |

### Global Program Fund Distribution
**Global Program** has specific distribution structure:

| Program/Component | Percentage (%) |
| :---------------- | :------------- |
| **Tree Upline Reserve** | 30% |
| **Tree Upline Wallet** | 30% |
| **Partner Incentive** | 10% |
| **Royal Captain Bonus** | 10% |
| **President Reward** | 10% |
| **Share Holders** | 5% |
| **Triple Entry Reward** | 5% |

### Fund Distribution Logic
- **Partner Incentive (10%)**: Goes directly to the referrer
- **Level Distribution**: Distributed across levels based on dual tree rules (Binary: 60%, Matrix: 40%)
- **Global Fund Programs**: Spark Bonus, Royal Captain Bonus, President Reward distributed among eligible users
- **Share Holders (5%)**: Goes into a separate wallet
- **Jackpot Fund**: Created from 5% of binary slot activations plus entry fees
- **Tree Upline Reserve**: 30% goes to tree upline's reserve for next slot upgrade

---

*This comprehensive documentation now covers the complete BitGPT platform roadmap and all earning programs with accurate information from the project images. The implementation will follow the extended phase-by-phase development plan outlined above.*
