# MATRIX PROGRAM DEVELOPMENT TODO

## Overview
This document outlines the complete development plan for the Matrix Program based on PROJECT_DOCUMENTATION.md specifications. The Matrix program includes tree placement, recycle system, auto calculations, and all automatic triggers that should happen when a user joins.

---

## 1. MATRIX PROGRAM SPECIFICATIONS

### 1.1 Joining Requirements
- **Cost**: $11 USDT to join Matrix program
- **Structure**: 3x Matrix structure (3, 9, 27 members per level)
- **Slots**: 15 slots total (STARTER to STAR)
- **Recycle System**: Each slot completes with 39 members (3+9+27)

### 1.2 Matrix Slot Structure
| Slot No | Slot Name | Value (USDT) | Level | Members | Total Income | Upgrade Cost | Wallet |
|---------|-----------|--------------|-------|---------|--------------|--------------|--------|
| 1 | STARTER | $11 | 1 | 3 | - | - | - |
| 2 | BRONZE | $33 | 2 | 9 | $158.4 | $99 | $59.4 |
| 3 | SILVER | $99 | 3 | 27 | $1039.5 | $297 | $742.5 |
| 4 | GOLD | $297 | 4 | 81 | $7929.9 | $891 | $7038.9 |
| 5 | PLATINUM | $891 | 5 | 243 | $67092.3 | $2673 | $64419.3 |
| 6 | DIAMOND | $2673 | 6 | 729 | - | - | - |
| 7 | RUBY | $8019 | 7 | 2187 | - | - | - |
| 8 | EMERALD | $24057 | 8 | 6561 | - | - | - |
| 9 | SAPPHIRE | $72171 | 9 | 19683 | - | - | - |
| 10 | TOPAZ | $216513 | 10 | 59049 | - | - | - |
| 11 | PEARL | $649539 | 11 | 177147 | - | - | - |
| 12 | AMETHYST | $1948617 | 12 | 531441 | - | - | - |
| 13 | OBSIDIAN | $5845851 | 13 | 1594323 | - | - | - |
| 14 | TITANIUM | $17537553 | 14 | 4782969 | - | - | - |
| 15 | STAR | $52612659 | 15 | 14348907 | - | - | - |

---

## 2. MATRIX TREE PLACEMENT SYSTEM

### 2.1 Tree Structure Rules
- **Level 1**: 3 members directly under user
- **Level 2**: 9 members (3 under each Level 1 member)
- **Level 3**: 27 members (3 under each Level 2 member)
- **Completion**: 39 total members (3+9+27) triggers recycle

### 2.2 Placement Algorithm (BFS)
- **Level 1**: Fill left → middle (upline-reserve) → right
- **Level 2**: Breadth-first, left-to-right under L1 parents
  - Positions 0..2 under L1[0]; 3..5 under L1[1]; 6..8 under L1[2]
  - Formula: L2 index = parentL1Index * 3 + childOffset
- **Level 3**: Breadth-first, left-to-right under L2 parents
  - Positions 0..2 under L2[0], 3..5 under L2[1], …, 24..26 under L2[8]
  - Formula: L3 index = parentL2Index * 3 + childOffset

### 2.3 Placement Implementation Tasks
- [ ] **MatrixTree Model**: Store user's matrix tree structure
- [ ] **MatrixPlacement Service**: Handle BFS placement algorithm
- [ ] **MatrixNode Model**: Individual node tracking
- [ ] **Placement Validation**: Ensure proper slot progression
- [ ] **Spillover Handling**: Handle overflow to upline trees

---

## 3. MATRIX RECYCLE SYSTEM

### 3.1 Recycle Rules
- **Trigger**: When all 39 positions fill (3+9+27)
- **Re-entry**: User re-enters upline's corresponding slot at first available BFS position
- **No Payment**: No re-joining payment required
- **Income Distribution**: Level incomes distributed to First/Second/Third upline

### 3.2 Recycle Data Model
- [ ] **MatrixRecycleInstance**: Track recycle instances per user+slot
- [ ] **MatrixRecycleNode**: Immutable snapshot of 39-member tree
- [ ] **Recycle History**: Multiple recycle instances per user per slot
- [ ] **Recycle API**: Fetch tree by recycle number

### 3.3 Recycle Implementation Tasks
- [ ] **Recycle Detection**: Monitor when 39 members complete
- [ ] **Snapshot Creation**: Create immutable tree snapshot
- [ ] **Re-entry Placement**: Place recycled user in upline's tree
- [ ] **Income Redistribution**: Adjust income distribution relationships
- [ ] **Recycle API Endpoints**: GET /matrix/recycle-tree, GET /matrix/recycles

---

## 4. MATRIX AUTO CALCULATIONS & DISTRIBUTIONS

### 4.1 Distribution Structure (100%)
- **🌟 স্পার্ক বোনাস**: 8%
- **🌟 রয়েল ক্যাপ্টেন**: 4%
- **🌟 প্রেসিডেন্ট রিওয়ার্ড**: 3%
- **🌟 শেয়ারহোল্ডার**: 5%
- **নিউকামার গ্রোথ সাপোর্ট**: 20%
- **🌟 মেন্টরশিপ বোনাস**: 10%
- **পার্টনার ইনসেনটিভ**: 10%
- **লেভেল পেআউট**: 40%

### 4.2 Auto Calculations on Matrix Join
When a user joins Matrix program, automatically trigger:

#### A. Core Matrix Setup
- [ ] **MatrixTree Creation**: Create user's matrix tree structure
- [ ] **Slot-1 Activation**: Activate STARTER slot ($11 USDT)
- [ ] **Tree Placement**: Place user in referrer's matrix tree
- [ ] **MatrixAutoUpgrade Tracking**: Initialize middle-3 auto-upgrade system

#### B. Commission & Distribution
- [ ] **Joining Commission**: 10% to direct upline
- [ ] **Partner Incentive**: 10% to upline from joining
- [ ] **Level Distribution**: 40% distributed across matrix levels
- [ ] **Spark Bonus**: 8% contribution to Spark fund
- [ ] **Royal Captain**: 4% contribution to Royal Captain fund
- [ ] **President Reward**: 3% contribution to President Reward fund
- [ ] **Shareholders**: 5% contribution to Shareholders fund

#### C. Special Programs
- [ ] **Newcomer Growth Support**: 20% contribution + instant bonus
- [ ] **Mentorship Bonus**: 10% to super upline (direct-of-direct)
- [ ] **Rank Update**: Update user rank based on matrix activation
- [ ] **Dream Matrix**: Initialize mandatory 3-partner requirement

#### D. Record Keeping
- [ ] **Earning History**: Record matrix slot activation
- [ ] **Blockchain Event**: Log matrix join transaction
- [ ] **Commission Ledger**: Track all commission distributions
- [ ] **Matrix Status**: Update user's matrix participation status

---

## 5. MATRIX AUTO UPGRADE SYSTEM

### 5.1 Auto Upgrade Rules
- **Rule**: "FROM LEVEL 1 TO LEVEL 15, THE 100% EARNINGS FROM THE MIDDLE 3 MEMBERS WILL BE USED FOR THE NEXT SLOT UPGRADE"
- **Middle 3 Members**: One under each Level 1 member (positions 1, 4, 7 in Level 2)
- **Upline Reserve**: Middle position in Level 1 for special handling

### 5.2 Auto Upgrade Implementation Tasks
- [ ] **Middle-3 Detection**: Identify middle 3 members at each level
- [ ] **Earnings Calculation**: Calculate 100% earnings from middle 3
- [ ] **Upgrade Cost Calculation**: Determine next slot upgrade cost
- [ ] **Auto Upgrade Trigger**: Process automatic upgrade when conditions met
- [ ] **Manual Upgrade Option**: Allow manual upgrade with wallet funds
- [ ] **Reserve Combination**: Support 2 reserves + 1 wallet or 1 reserve + 2 wallet

---

## 6. MATRIX DREAM MATRIX SYSTEM

### 6.1 Dream Matrix Rules
- **Mandatory Requirement**: User must have 3 direct partners to start earning
- **Calculation Base**: Based on 5th slot ($800 total value)
- **Progressive Commissions**: Different percentages per level

### 6.2 Dream Matrix Distribution
| Level | Members | Percentage | $800 Base | Total Profit |
|-------|---------|------------|-----------|--------------|
| 1 | 3 | 10% | $80 | $240 |
| 2 | 9 | 10% | $80 | $720 |
| 3 | 27 | 15% | $120 | $3240 |
| 4 | 81 | 25% | $200 | $16200 |
| 5 | 243 | 40% | $320 | $77760 |
| **Total** | **363** | **100%** | **$800** | **$98160** |

### 6.3 Dream Matrix Implementation Tasks
- [ ] **3-Partner Requirement**: Enforce mandatory 3 direct partners
- [ ] **Earning Calculation**: Calculate progressive commission percentages
- [ ] **Distribution Logic**: Distribute earnings based on level structure
- [ ] **Eligibility Check**: Verify user meets earning requirements

---

## 7. MATRIX MENTORSHIP BONUS

### 7.1 Mentorship Rules
- **Direct-of-Direct Income**: Super upline receives 10% from direct-of-direct partners
- **Commission Source**: From joining fees and all slot upgrades
- **Example**: A invites B, B invites C/D/E → A gets 10% from C/D/E activities

### 7.2 Mentorship Implementation Tasks
- [ ] **Super Upline Tracking**: Track direct-of-direct relationships
- [ ] **Commission Calculation**: 10% from direct-of-direct activities
- [ ] **Income Distribution**: Distribute mentorship bonuses
- [ ] **Relationship Mapping**: Maintain upline-downline relationships

---

## 8. MATRIX API ENDPOINTS

### 8.1 Core Matrix APIs
- [ ] **POST /matrix/join**: Join Matrix program with $11 USDT
- [ ] **POST /matrix/upgrade**: Upgrade Matrix slot manually
- [ ] **GET /matrix/tree/{user_id}**: Get user's matrix tree structure
- [ ] **GET /matrix/status/{user_id}**: Get user's matrix status

### 8.2 Recycle APIs
- [ ] **GET /matrix/recycle-tree**: Get matrix tree by recycle number
- [ ] **GET /matrix/recycles**: Get recycle history for user+slot
- [ ] **POST /matrix/process-recycle**: Process recycle completion

### 8.3 Auto Upgrade APIs
- [ ] **GET /matrix/auto-upgrade-status**: Get auto upgrade eligibility
- [ ] **POST /matrix/trigger-auto-upgrade**: Trigger auto upgrade
- [ ] **GET /matrix/middle-three-earnings**: Get middle 3 earnings

### 8.4 Dream Matrix APIs
- [ ] **GET /matrix/dream-matrix-status**: Get Dream Matrix eligibility
- [ ] **GET /matrix/dream-matrix-earnings**: Calculate Dream Matrix earnings
- [ ] **POST /matrix/dream-matrix-distribute**: Distribute Dream Matrix earnings

---

## 9. MATRIX DATABASE MODELS

### 9.1 Core Models
- [ ] **MatrixTree**: User's matrix tree structure
- [ ] **MatrixNode**: Individual matrix node
- [ ] **MatrixActivation**: Slot activation records
- [ ] **MatrixUpgradeLog**: Upgrade history

### 9.2 Recycle Models
- [ ] **MatrixRecycleInstance**: Recycle instance tracking
- [ ] **MatrixRecycleNode**: Immutable recycle snapshots
- [ ] **MatrixRecycleHistory**: Recycle event history

### 9.3 Auto Upgrade Models
- [ ] **MatrixAutoUpgrade**: Auto upgrade status tracking
- [ ] **MatrixMiddleThreeEarnings**: Middle 3 earnings tracking
- [ ] **MatrixUpgradeQueue**: Auto upgrade queue

### 9.4 Dream Matrix Models
- [ ] **DreamMatrixStatus**: Dream Matrix eligibility
- [ ] **DreamMatrixEarnings**: Dream Matrix earning calculations
- [ ] **DreamMatrixDistribution**: Dream Matrix distribution records

---

## 10. MATRIX INTEGRATION WITH OTHER PROGRAMS

### 10.1 Binary Program Integration
- [ ] **Rank System**: Matrix slots contribute to user rank
- [ ] **Royal Captain**: Matrix+Global referrals for Royal Captain bonus
- [ ] **President Reward**: Matrix referrals count toward President Reward
- [ ] **Spark Bonus**: Matrix contributes to combined Spark fund

### 10.2 Global Program Integration
- [ ] **Triple Entry**: Matrix+Binary+Global for Triple Entry Reward
- [ ] **Royal Captain**: Combined Matrix+Global referrals
- [ ] **Global Distribution**: Matrix contributes to Global distribution

### 10.3 Special Programs Integration
- [ ] **Leadership Stipend**: Matrix earnings contribute to Leadership Stipend
- [ ] **Jackpot**: Matrix contributes to Jackpot fund
- [ ] **Newcomer Support**: Matrix joiners get NGS benefits
- [ ] **Mentorship**: Matrix super upline gets mentorship bonuses

---

## 11. MATRIX DEVELOPMENT PHASES

### Phase 1: Core Matrix System
- [ ] Matrix tree placement system
- [ ] Basic slot activation
- [ ] Joining commission (10%)
- [ ] Matrix tree visualization

### Phase 2: Recycle System
- [ ] Recycle detection (39 members)
- [ ] Recycle snapshot creation
- [ ] Re-entry placement
- [ ] Recycle API endpoints

### Phase 3: Auto Upgrade System
- [ ] Middle-3 detection
- [ ] Auto upgrade calculation
- [ ] Manual upgrade option
- [ ] Reserve combination logic

### Phase 4: Dream Matrix
- [ ] 3-partner requirement
- [ ] Progressive commission calculation
- [ ] Dream Matrix distribution
- [ ] Dream Matrix API

### Phase 5: Mentorship Bonus
- [ ] Super upline tracking
- [ ] Direct-of-direct commission
- [ ] Mentorship distribution
- [ ] Mentorship API

### Phase 6: Full Integration
- [ ] All distribution percentages
- [ ] Integration with other programs
- [ ] Complete API suite
- [ ] Testing and optimization

---

## 12. MATRIX TESTING REQUIREMENTS

### 12.1 Unit Tests
- [ ] Matrix tree placement algorithm
- [ ] Recycle detection logic
- [ ] Auto upgrade calculations
- [ ] Commission distributions
- [ ] Dream Matrix calculations

### 12.2 Integration Tests
- [ ] Matrix join flow
- [ ] Recycle completion flow
- [ ] Auto upgrade flow
- [ ] Cross-program integration
- [ ] API endpoint testing

### 12.3 Performance Tests
- [ ] Large tree traversal
- [ ] Recycle snapshot creation
- [ ] Concurrent upgrades
- [ ] Database query optimization

---

## 13. MATRIX MONITORING & ANALYTICS

### 13.1 Key Metrics
- [ ] Matrix join rate
- [ ] Slot upgrade rate
- [ ] Recycle completion rate
- [ ] Auto upgrade success rate
- [ ] Commission distribution accuracy

### 13.2 Monitoring Dashboard
- [ ] Matrix tree visualization
- [ ] Recycle status tracking
- [ ] Auto upgrade queue monitoring
- [ ] Commission distribution reports
- [ ] Performance metrics

---

## 14. MATRIX SECURITY CONSIDERATIONS

### 14.1 Data Security
- [ ] Encrypt sensitive matrix data
- [ ] Secure API endpoints
- [ ] Validate all inputs
- [ ] Prevent unauthorized access

### 14.2 Business Logic Security
- [ ] Prevent duplicate activations
- [ ] Validate slot progression
- [ ] Secure commission calculations
- [ ] Prevent manipulation of recycle system

---

## 15. MATRIX DEPLOYMENT CHECKLIST

### 15.1 Pre-Deployment
- [ ] All models created and tested
- [ ] All services implemented
- [ ] All APIs tested
- [ ] Database migrations ready
- [ ] Integration tests passed

### 15.2 Deployment
- [ ] Deploy Matrix module
- [ ] Update main router
- [ ] Run database migrations
- [ ] Initialize Matrix settings
- [ ] Enable Matrix endpoints

### 15.3 Post-Deployment
- [ ] Monitor Matrix performance
- [ ] Verify commission distributions
- [ ] Test recycle system
- [ ] Monitor auto upgrade system
- [ ] Collect user feedback

---

## 16. MATRIX FUTURE ENHANCEMENTS

### 16.1 Advanced Features
- [ ] Matrix analytics dashboard
- [ ] Advanced recycle strategies
- [ ] Matrix performance optimization
- [ ] Mobile Matrix interface
- [ ] Matrix reporting system

### 16.2 Scalability Improvements
- [ ] Matrix tree caching
- [ ] Database optimization
- [ ] API rate limiting
- [ ] Load balancing
- [ ] Microservices architecture

---

## CONCLUSION

This MATRIX_TODO.md provides a comprehensive roadmap for implementing the complete Matrix Program according to PROJECT_DOCUMENTATION.md specifications. The Matrix program is a complex system with tree placement, recycle functionality, auto calculations, and multiple integration points with other programs.

**Priority Order:**
1. Core Matrix System (Tree placement, basic activation)
2. Recycle System (39-member completion, re-entry)
3. Auto Upgrade System (Middle-3 earnings)
4. Dream Matrix (3-partner requirement)
5. Mentorship Bonus (Direct-of-direct income)
6. Full Integration (All distributions and programs)

**Success Criteria:**
- Users can join Matrix with $11 USDT
- Tree placement works correctly with BFS algorithm
- Recycle system handles 39-member completion
- Auto upgrade system processes middle-3 earnings
- All commission distributions work accurately
- Integration with other programs functions properly

This development plan ensures the Matrix Program will be fully functional and integrated with the entire BitGPT platform ecosystem.
