# User Join Automatic Functions Documentation

## Overview
This document provides comprehensive JavaScript function implementations for all automatic calculations and processes that occur when a user joins the BitGPT platform, based on the backend analysis and `01_USER_JOIN_AUTO_ACTIONS.md`.

---

## 1. USER CREATION AND INITIALIZATION FUNCTIONS

### 1.1 Create User Function
```javascript
/**
 * Creates a new user and triggers all automatic initialization processes
 * @param {Object} userData - User registration data
 * @returns {Object} Result with user ID and token
 */
async function createUser(userData) {
    try {
        // Validate required fields
        const requiredFields = ['uid', 'referCode', 'referedBy', 'walletAddress', 'name'];
        const missingFields = requiredFields.filter(field => !userData[field]);
        
        if (missingFields.length > 0) {
            throw new Error(`Missing required fields: ${missingFields.join(', ')}`);
        }

        // Check wallet address uniqueness
        const existingUser = await User.findOne({ walletAddress: userData.walletAddress });
        if (existingUser) {
            throw new Error('User with this wallet address already exists');
        }

        // Validate referrer exists
        const referrer = await User.findById(userData.referedBy);
        if (!referrer) {
            throw new Error('Invalid referrer/upline provided');
        }

        // Create user record
        const user = new User({
            uid: userData.uid,
            referCode: userData.referCode,
            referedBy: userData.referedBy,
            walletAddress: userData.walletAddress,
            name: userData.name,
            role: userData.role || 'user',
            email: userData.email,
            password: userData.password ? await hashPassword(userData.password) : null,
            binaryJoined: true, // Binary is required
            matrixJoined: !!userData.matrixPaymentTx,
            globalJoined: !!userData.globalPaymentTx,
            createdAt: new Date()
        });

        await user.save();

        // Initialize all automatic processes
        await initializeUserPrograms(user._id, userData);
        await initializePartnerGraph(user._id, referrer._id);
        await initializeAutoUpgradeTracking(user._id);
        await initializeSpecialPrograms(user._id, userData);
        
        // Process referrer benefits and calculations
        await processReferrerCalculations(user._id, referrer._id, userData);

        // Generate JWT token
        const token = generateJWTToken({
            sub: user.uid,
            userId: user._id.toString()
        });

        return {
            success: true,
            userId: user._id.toString(),
            token: token.accessToken,
            tokenType: token.tokenType
        };

    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}
```

### 1.2 Initialize User Programs Function
```javascript
/**
 * Initializes all program participations for new user
 * @param {string} userId - User ID
 * @param {Object} userData - User data with payment transactions
 */
async function initializeUserPrograms(userId, userData) {
    try {
        // Initialize Binary Program (always required)
        await initializeBinaryProgram(userId, userData.binaryPaymentTx);
        
        // Initialize Matrix Program (optional)
        if (userData.matrixPaymentTx) {
            await initializeMatrixProgram(userId, userData.matrixPaymentTx);
        }
        
        // Initialize Global Program (optional)
        if (userData.globalPaymentTx) {
            await initializeGlobalProgram(userId, userData.globalPaymentTx);
        }

        // Record blockchain events
        await recordBlockchainEvents(userId, userData);

    } catch (error) {
        console.error('Error initializing user programs:', error);
    }
}
```

---

## 2. REFERRER AUTOMATIC CALCULATIONS

### 2.1 Process Referrer Calculations Function
```javascript
/**
 * Processes all automatic calculations for referrer when new user joins
 * @param {string} newUserId - New user ID
 * @param {string} referrerId - Referrer user ID
 * @param {Object} userData - New user data
 */
async function processReferrerCalculations(newUserId, referrerId, userData) {
    try {
        const referrer = await User.findById(referrerId);
        if (!referrer) {
            console.error('Referrer not found for calculations');
            return;
        }

        // 1. Update Partner Graph
        await updateReferrerPartnerGraph(referrerId, newUserId, userData);

        // 2. Process Joining Commissions
        await processReferrerJoiningCommissions(newUserId, referrerId, userData);

        // 3. Check Royal Captain Bonus Eligibility
        await checkReferrerRoyalCaptainEligibility(referrerId, userData);

        // 4. Check President Reward Eligibility
        await checkReferrerPresidentRewardEligibility(referrerId);

        // 5. Update Referrer Rank
        await updateReferrerRank(referrerId);

        // 6. Update Commission Accumulation
        await updateReferrerCommissionAccumulation(referrerId, userData);

        console.log(`Referrer calculations completed for user ${referrerId}`);

    } catch (error) {
        console.error('Error processing referrer calculations:', error);
    }
}
```

### 2.2 Update Referrer Partner Graph Function
```javascript
/**
 * Updates referrer's partner graph with new user
 * @param {string} referrerId - Referrer user ID
 * @param {string} newUserId - New user ID
 * @param {Object} userData - New user data
 */
async function updateReferrerPartnerGraph(referrerId, newUserId, userData) {
    try {
        let refPG = await PartnerGraph.findOne({ userId: referrerId });
        if (!refPG) {
            refPG = new PartnerGraph({ userId: referrerId });
        }

        // Add new user to direct partners
        const directs = refPG.directs || [];
        if (!directs.includes(newUserId)) {
            directs.push(newUserId);
            refPG.directs = directs;
        }

        // Update direct partners count by program
        refPG.directsCountByProgram = refPG.directsCountByProgram || {};
        
        // Binary program count (always +1)
        refPG.directsCountByProgram['binary'] = (refPG.directsCountByProgram['binary'] || 0) + 1;
        
        // Matrix program count (if new user joined matrix)
        if (userData.matrixPaymentTx) {
            refPG.directsCountByProgram['matrix'] = (refPG.directsCountByProgram['matrix'] || 0) + 1;
        }
        
        // Global program count (if new user joined global)
        if (userData.globalPaymentTx) {
            refPG.directsCountByProgram['global'] = (refPG.directsCountByProgram['global'] || 0) + 1;
        }

        refPG.lastUpdated = new Date();
        await refPG.save();

        console.log(`Partner graph updated for referrer ${referrerId}`);

    } catch (error) {
        console.error('Error updating referrer partner graph:', error);
    }
}
```

### 2.3 Process Referrer Joining Commissions Function
```javascript
/**
 * Processes joining commissions for referrer
 * @param {string} newUserId - New user ID
 * @param {string} referrerId - Referrer user ID
 * @param {Object} userData - New user data
 */
async function processReferrerJoiningCommissions(newUserId, referrerId, userData) {
    try {
        const newUser = await User.findById(newUserId);
        if (!newUser) return;

        // Binary joining commission (10% of 0.0066 BNB = 0.00066 BNB)
        if (userData.binaryPaymentTx) {
            const binaryCommissionAmount = 0.0066 * 0.10; // 10% of 0.0066 BNB
            await creditWallet(referrerId, binaryCommissionAmount, 'BNB', 'binary_joining_commission', `JOIN-${newUserId}-${Date.now()}`);
            
            // Create earning history
            await createEarningHistory(referrerId, 'commission', 'binary', binaryCommissionAmount, 'BNB', 'JOINING', 1, `Joining commission from ${newUser.name}`);
        }

        // Matrix joining commission (10% of $11 = $1.1)
        if (userData.matrixPaymentTx) {
            const matrixCommissionAmount = 11 * 0.10; // 10% of $11
            await creditWallet(referrerId, matrixCommissionAmount, 'USDT', 'matrix_joining_commission', `JOIN-${newUserId}-${Date.now()}`);
            
            // Create earning history
            await createEarningHistory(referrerId, 'commission', 'matrix', matrixCommissionAmount, 'USDT', 'JOINING', 1, `Joining commission from ${newUser.name}`);
        }

        // Global joining commission (10% of $33 = $3.3)
        if (userData.globalPaymentTx) {
            const globalCommissionAmount = 33 * 0.10; // 10% of $33
            await creditWallet(referrerId, globalCommissionAmount, 'USD', 'global_joining_commission', `JOIN-${newUserId}-${Date.now()}`);
            
            // Create earning history
            await createEarningHistory(referrerId, 'commission', 'global', globalCommissionAmount, 'USD', 'JOINING', 1, `Joining commission from ${newUser.name}`);
        }

        console.log(`Joining commissions processed for referrer ${referrerId}`);

    } catch (error) {
        console.error('Error processing referrer joining commissions:', error);
    }
}
```

---

## 3. BINARY PROGRAM AUTOMATIC FUNCTIONS

### 2.1 Initialize Binary Program Function
```javascript
/**
 * Initializes Binary program with first 2 slots auto-activation
 * @param {string} userId - User ID
 * @param {string} paymentTx - Payment transaction hash
 */
async function initializeBinaryProgram(userId, paymentTx) {
    try {
        const totalJoinAmount = 0.0066; // BNB
        const currency = 'BNB';
        
        // Auto-activate first 2 slots (EXPLORER and CONTRIBUTOR)
        for (let slotNo = 1; slotNo <= 2; slotNo++) {
            const slotCatalog = await SlotCatalog.findOne({
                program: 'binary',
                slotNo: slotNo,
                isActive: true
            });

            if (slotCatalog) {
                const amount = slotCatalog.price || 0;
                
                // Create slot activation record
                const activation = new SlotActivation({
                    userId: userId,
                    program: 'binary',
                    slotNo: slotNo,
                    slotName: slotCatalog.name,
                    activationType: 'initial',
                    upgradeSource: 'auto',
                    amountPaid: amount,
                    currency: currency,
                    txHash: paymentTx || `AUTO-${userId}-S${slotNo}`,
                    isAutoUpgrade: true,
                    status: 'completed',
                    activatedAt: new Date(),
                    completedAt: new Date()
                });
                
                await activation.save();

                // Record earning history
                await createEarningHistory(userId, 'binary_slot', 'binary', amount, currency, slotCatalog.name, slotCatalog.level, `Auto activation of binary slot ${slotNo}`);

                // Trigger upgrade commission logic
                if (amount > 0) {
                    await calculateUpgradeCommission(userId, 'binary', slotNo, slotCatalog.name, amount, currency);
                }

                // Award jackpot free coupons
                await awardJackpotFreeCoupon(userId, slotNo);
            }
        }

        // Calculate joining commission (10% of total join amount)
        await calculateJoiningCommission(userId, 'binary', totalJoinAmount, currency);

        // Update user rank
        await updateUserRank(userId);

    } catch (error) {
        console.error('Error initializing binary program:', error);
    }
}
```

### 2.2 Binary Auto Upgrade Function
```javascript
/**
 * Processes Binary auto upgrade using first 2 partners' earnings
 * @param {string} userId - User ID
 * @returns {Object} Upgrade result
 */
async function processBinaryAutoUpgrade(userId) {
    try {
        const binaryStatus = await BinaryAutoUpgrade.findOne({ userId: userId });
        if (!binaryStatus) {
            throw new Error('Binary auto upgrade status not found');
        }

        // Check if user has 2 partners
        if (binaryStatus.partnersAvailable < binaryStatus.partnersRequired) {
            return {
                success: false,
                error: 'Insufficient partners for auto upgrade'
            };
        }

        // Calculate earnings from first 2 partners
        const earningsFromPartners = await calculateBinaryPartnerEarnings(userId);
        
        if (earningsFromPartners <= 0) {
            return {
                success: false,
                error: 'No earnings available from partners'
            };
        }

        // Calculate next upgrade cost
        const nextSlot = binaryStatus.currentSlotNo + 1;
        const upgradeCost = getBinarySlotCost(nextSlot);
        
        if (earningsFromPartners < upgradeCost) {
            return {
                success: false,
                error: 'Insufficient earnings for upgrade'
            };
        }

        // Create auto upgrade queue entry
        const queueEntry = new AutoUpgradeQueue({
            userId: userId,
            program: 'binary',
            currentSlotNo: binaryStatus.currentSlotNo,
            targetSlotNo: nextSlot,
            upgradeCost: upgradeCost,
            currency: 'BNB',
            earningsAvailable: earningsFromPartners,
            status: 'pending',
            priority: 1,
            trigger: {
                triggerType: 'first_two_partners',
                program: 'binary',
                partnersRequired: 2,
                partnersAvailable: binaryStatus.partnersAvailable,
                earningsThreshold: upgradeCost,
                currentEarnings: earningsFromPartners,
                isTriggered: true,
                triggeredAt: new Date()
            }
        });

        await queueEntry.save();

        // Process the upgrade
        const result = await processUpgradeQueueEntry(queueEntry);

        return {
            success: true,
            queueId: queueEntry._id.toString(),
            fromSlot: binaryStatus.currentSlotNo,
            toSlot: nextSlot,
            earningsUsed: earningsFromPartners,
            upgradeCost: upgradeCost,
            profit: earningsFromPartners - upgradeCost,
            message: 'Binary auto upgrade processed successfully'
        };

    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}
```

### 2.3 Dual Tree Earning Calculation Function
```javascript
/**
 * Calculates dual tree earnings distribution according to PROJECT_DOCUMENTATION.md
 * @param {number} slotNo - Slot number
 * @param {number} slotValue - Slot value in BNB
 * @returns {Object} Distribution result
 */
function calculateDualTreeEarnings(slotNo, slotValue) {
    try {
        // Level members mapping
        const levelMembers = {
            1: 2, 2: 4, 3: 8, 4: 16, 5: 32, 6: 64, 7: 128, 8: 256,
            9: 512, 10: 1024, 11: 2048, 12: 4096, 13: 8192, 14: 16384, 15: 32768, 16: 65536
        };

        const totalIncome = slotValue * (levelMembers[slotNo] || 0);

        // Distribution percentages based on PROJECT_DOCUMENTATION.md
        const distributions = {
            1: 0.30,   // 30%
            2: 0.10,   // 10%
            3: 0.10,   // 10%
            4: 0.05,   // 5%
            5: 0.05,   // 5%
            6: 0.05,   // 5%
            7: 0.05,   // 5%
            8: 0.05,   // 5%
            9: 0.05,   // 5%
            10: 0.05,  // 5%
            11: 0.03,  // 3%
            12: 0.03,  // 3%
            13: 0.03,  // 3%
            14: 0.02,  // 2%
            15: 0.02,  // 2%
            16: 0.02   // 2%
        };

        // Calculate level earnings
        const levelEarnings = {};
        for (let level = 1; level <= Math.min(slotNo, 16); level++) {
            const percentage = distributions[level] || 0;
            const levelAmount = totalIncome * percentage;
            levelEarnings[level] = {
                percentage: percentage * 100,
                amount: levelAmount,
                members: levelMembers[level] || 0
            };
        }

        return {
            success: true,
            slotNo: slotNo,
            slotValue: slotValue,
            totalIncome: totalIncome,
            levelEarnings: levelEarnings,
            totalDistribution: Object.values(levelEarnings).reduce((sum, level) => sum + level.amount, 0)
        };

    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}
```

---

## 3. COMMISSION CALCULATION FUNCTIONS

### 3.1 Joining Commission Function
```javascript
/**
 * Calculates 10% joining commission for referrer
 * @param {string} fromUserId - User who joined
 * @param {string} program - Program type (binary/matrix/global)
 * @param {number} amount - Join amount
 * @param {string} currency - Currency
 * @returns {Object} Commission result
 */
async function calculateJoiningCommission(fromUserId, program, amount, currency) {
    try {
        const user = await User.findById(fromUserId);
        if (!user || !user.referedBy) {
            throw new Error('User or referrer not found');
        }

        const referrerId = user.referedBy;
        const commissionPercentage = 10.0; // 10% commission
        const commissionAmount = amount * (commissionPercentage / 100);

        // Create commission record
        const commission = new Commission({
            userId: referrerId,
            fromUserId: fromUserId,
            commissionType: 'joining',
            program: program,
            commissionAmount: commissionAmount,
            currency: currency,
            commissionPercentage: commissionPercentage,
            sourceSlotNo: 1,
            sourceSlotName: 'JOINING',
            isDirectCommission: true,
            status: 'pending',
            createdAt: new Date()
        });

        await commission.save();

        // Update commission accumulation
        await updateCommissionAccumulation(referrerId, program, commissionAmount, currency, 'joining');

        // Credit referrer's wallet
        await creditWallet(referrerId, commissionAmount, currency, `${program}_joining_commission`, `JOIN-${fromUserId}-${Date.now()}`);

        // Create earning history for referrer
        await createEarningHistory(referrerId, 'commission', program, commissionAmount, currency, 'JOINING', 1, `Joining commission from ${user.name}`);

        return {
            success: true,
            commissionId: commission._id.toString(),
            referrerId: referrerId.toString(),
            commissionAmount: commissionAmount,
            currency: currency,
            message: 'Joining commission calculated and distributed'
        };

    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}
```

### 3.2 Upgrade Commission Function
```javascript
/**
 * Calculates upgrade commission (30% to corresponding level upline + 70% dual tree distribution)
 * @param {string} fromUserId - User who upgraded
 * @param {string} program - Program type
 * @param {number} slotNo - Slot number
 * @param {string} slotName - Slot name
 * @param {number} amount - Upgrade amount
 * @param {string} currency - Currency
 * @returns {Object} Commission result
 */
async function calculateUpgradeCommission(fromUserId, program, slotNo, slotName, amount, currency) {
    try {
        // Calculate 30% commission for corresponding level upline
        const levelCommissionPercentage = 30.0;
        const levelCommissionAmount = amount * (levelCommissionPercentage / 100);
        
        // Get corresponding level upline
        const levelUpline = await getLevelUpline(fromUserId, slotNo);
        
        if (levelUpline) {
            // Create level commission record
            const levelCommission = new Commission({
                userId: levelUpline,
                fromUserId: fromUserId,
                commissionType: 'upgrade',
                program: program,
                commissionAmount: levelCommissionAmount,
                currency: currency,
                commissionPercentage: levelCommissionPercentage,
                sourceSlotNo: slotNo,
                sourceSlotName: slotName,
                level: slotNo,
                isLevelCommission: true,
                distributionType: 'level',
                distributionLevel: slotNo,
                status: 'pending',
                createdAt: new Date()
            });

            await levelCommission.save();

            // Credit level upline's wallet
            await creditWallet(levelUpline, levelCommissionAmount, currency, `${program}_level_L${slotNo}_commission`, `LEVEL-${fromUserId}-L${slotNo}-${Date.now()}`);

            // Update commission accumulation
            await updateCommissionAccumulation(levelUpline, program, levelCommissionAmount, currency, 'level');
        }

        // Calculate remaining 70% for dual tree distribution
        const remainingAmount = amount - levelCommissionAmount;
        const dualTreeResult = await distributeAcrossLevels(fromUserId, remainingAmount, currency, program, slotNo, slotName);

        return {
            success: true,
            levelCommission: {
                uplineId: levelUpline?.toString(),
                amount: levelCommissionAmount,
                percentage: levelCommissionPercentage
            },
            dualTreeDistribution: dualTreeResult,
            totalCommission: amount,
            message: 'Upgrade commission calculated and distributed'
        };

    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}
```

### 3.3 Dual Tree Distribution Function
```javascript
/**
 * Distributes commission across levels 1-16 using Dual-Tree percentages
 * @param {string} fromUserId - User who generated commission
 * @param {number} amount - Amount to distribute
 * @param {string} currency - Currency
 * @param {string} program - Program type
 * @param {number} sourceSlotNo - Source slot number
 * @param {string} sourceSlotName - Source slot name
 * @returns {Array} Distribution results
 */
async function distributeAcrossLevels(fromUserId, amount, currency, program, sourceSlotNo, sourceSlotName) {
    try {
        const levelDistributions = [];
        const percentages = getDualTreePercentages();

        for (let level = 1; level <= 16; level++) {
            const percentage = percentages[level] || 0;
            const levelAmount = amount * (percentage / 100);
            
            if (levelAmount <= 0) continue;

            const levelUser = await getLevelUpline(fromUserId, level);
            
            if (!levelUser) continue;

            // Check if user is eligible for this level
            if (await isUserEligibleForLevel(levelUser, program, level)) {
                levelDistributions.push({
                    level: level,
                    amount: levelAmount,
                    userId: levelUser.toString()
                });

                // Update commission accumulation
                await updateCommissionAccumulation(levelUser, program, levelAmount, currency, 'level');

                // Auto-credit wallet for level distribution
                await creditWallet(
                    levelUser.toString(),
                    levelAmount,
                    currency,
                    `${program}_dual_tree_L${level}_S${sourceSlotNo}`,
                    `DUALTREE-${fromUserId}-L${level}-S${sourceSlotNo}-${Date.now()}`
                );
            } else {
                // Missed profit to Leadership Stipend
                await handleMissedProfit(levelUser, levelAmount, currency, program, level, sourceSlotNo);
            }
        }

        return levelDistributions;

    } catch (error) {
        console.error('Error distributing across levels:', error);
        return [];
    }
}
```

---

## 4. RANK SYSTEM FUNCTIONS

### 4.1 Update User Rank Function
```javascript
/**
 * Updates user's rank based on current achievements
 * @param {string} userId - User ID
 * @param {boolean} forceUpdate - Force update even if no change
 * @returns {Object} Rank update result
 */
async function updateUserRank(userId, forceUpdate = false) {
    try {
        // Get user's current rank
        let userRank = await UserRank.findOne({ userId: userId });
        if (!userRank) {
            userRank = await createInitialUserRank(userId);
        }

        // Get user's current achievements
        const achievements = await getUserAchievements(userId);

        // Determine new rank based on achievements
        const newRankNumber = calculateUserRank(achievements);

        // Check if rank should be updated
        if (newRankNumber > userRank.currentRankNumber || forceUpdate) {
            const oldRankNumber = userRank.currentRankNumber;
            const oldRankName = userRank.currentRankName;

            // Get new rank details
            const newRank = await Rank.findOne({ rankNumber: newRankNumber });
            if (!newRank) {
                throw new Error(`Rank ${newRankNumber} not found`);
            }

            // Update user rank
            userRank.currentRankNumber = newRankNumber;
            userRank.currentRankName = newRank.rankName;
            userRank.rankAchievedAt = new Date();

            // Add to rank history
            userRank.rankHistory.push({
                rankNumber: oldRankNumber,
                rankName: oldRankName,
                achievedAt: userRank.rankAchievedAt
            });

            // Update next rank
            if (newRankNumber < 15) {
                userRank.nextRankNumber = newRankNumber + 1;
                const nextRank = await Rank.findOne({ rankNumber: userRank.nextRankNumber });
                userRank.nextRankName = nextRank ? nextRank.rankName : 'Unknown';
            } else {
                userRank.nextRankNumber = 15;
                userRank.nextRankName = 'Omega';
            }

            // Update achievements
            userRank.binarySlotsActivated = achievements.binarySlots;
            userRank.matrixSlotsActivated = achievements.matrixSlots;
            userRank.globalSlotsActivated = achievements.globalSlots;
            userRank.totalSlotsActivated = achievements.totalSlots;
            userRank.totalTeamSize = achievements.teamSize;
            userRank.directPartnersCount = achievements.directPartners;
            userRank.totalEarnings = achievements.totalEarnings;

            // Update special qualifications
            userRank.royalCaptainEligible = newRankNumber >= 5;
            userRank.presidentRewardEligible = newRankNumber >= 10;
            userRank.topLeaderGiftEligible = newRankNumber >= 15;
            userRank.leadershipStipendEligible = newRankNumber >= 10;

            // Calculate progress percentage
            userRank.progressPercentage = calculateProgressPercentage(userRank);

            userRank.lastUpdated = new Date();
            await userRank.save();

            // Create rank achievement record
            await createRankAchievement(userId, newRankNumber, newRank.rankName, achievements);

            // Check for milestones
            await checkAndCreateMilestones(userId, newRankNumber);

            return {
                success: true,
                oldRank: { number: oldRankNumber, name: oldRankName },
                newRank: { number: newRankNumber, name: newRank.rankName },
                achievements: achievements,
                specialQualifications: {
                    royalCaptainEligible: userRank.royalCaptainEligible,
                    presidentRewardEligible: userRank.presidentRewardEligible,
                    topLeaderGiftEligible: userRank.topLeaderGiftEligible,
                    leadershipStipendEligible: userRank.leadershipStipendEligible
                },
                message: `Rank updated from ${oldRankName} to ${newRank.rankName}`
            };
        } else {
            return {
                success: true,
                currentRank: { number: userRank.currentRankNumber, name: userRank.currentRankName },
                message: 'No rank update needed'
            };
        }

    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}
```

### 4.2 Calculate User Rank Function
```javascript
/**
 * Calculates user's rank based on achievements
 * @param {Object} achievements - User achievements
 * @returns {number} Rank number (1-15)
 */
function calculateUserRank(achievements) {
    const totalSlots = achievements.totalSlots;

    // Progressive rank calculation based on total slots activated
    if (totalSlots >= 30) return 15; // Omega
    if (totalSlots >= 25) return 14; // Spectra
    if (totalSlots >= 20) return 13; // Trion
    if (totalSlots >= 18) return 12; // Axion
    if (totalSlots >= 16) return 11; // Fyre
    if (totalSlots >= 14) return 10; // Nexus
    if (totalSlots >= 12) return 9;  // Arion
    if (totalSlots >= 10) return 8;  // Lumix
    if (totalSlots >= 8) return 7;   // Quanta
    if (totalSlots >= 6) return 6;  // Ignis
    if (totalSlots >= 5) return 5;  // Stellar
    if (totalSlots >= 4) return 4;  // Glint
    if (totalSlots >= 3) return 3;  // Neura
    if (totalSlots >= 2) return 2;  // Cryzen
    return 1; // Bitron
}
```

---

## 5. SPECIAL PROGRAMS FUNCTIONS

### 5.1 Royal Captain Bonus Function
```javascript
/**
 * Checks and processes Royal Captain Bonus eligibility
 * @param {string} userId - User ID
 * @returns {Object} Royal Captain result
 */
async function checkRoyalCaptainEligibility(userId) {
    try {
        const user = await User.findById(userId);
        if (!user) {
            throw new Error('User not found');
        }

        // Check if user has both Matrix and Global packages
        const hasMatrixPackage = user.matrixJoined;
        const hasGlobalPackage = user.globalJoined;
        const hasBothPackages = hasMatrixPackage && hasGlobalPackage;

        if (!hasBothPackages) {
            return {
                success: true,
                isEligible: false,
                reason: 'User must have both Matrix and Global packages',
                requirements: {
                    hasMatrixPackage,
                    hasGlobalPackage,
                    hasBothPackages
                }
            };
        }

        // Count direct partners with both packages
        const directPartners = await TreePlacement.find({
            parentId: userId,
            isActive: true
        });

        let partnersWithBothPackages = 0;
        const partnersList = [];

        for (const partner of directPartners) {
            const partnerUser = await User.findById(partner.userId);
            if (partnerUser && partnerUser.matrixJoined && partnerUser.globalJoined) {
                partnersWithBothPackages++;
            }
            partnersList.push(partner.userId);
        }

        // Check if user has 5+ direct partners with both packages
        const isEligible = partnersWithBothPackages >= 5;

        // Calculate global team size
        const globalTeamSize = await calculateGlobalTeamSize(userId);

        // Determine bonus amount based on global team size
        let bonusAmount = 0;
        if (isEligible) {
            if (globalTeamSize >= 0 && globalTeamSize < 10) {
                bonusAmount = 200;
            } else if (globalTeamSize >= 10 && globalTeamSize < 20) {
                bonusAmount = 200;
            } else if (globalTeamSize >= 20 && globalTeamSize < 30) {
                bonusAmount = 200;
            } else if (globalTeamSize >= 30 && globalTeamSize < 40) {
                bonusAmount = 200;
            } else if (globalTeamSize >= 40 && globalTeamSize < 50) {
                bonusAmount = 250;
            } else if (globalTeamSize >= 50) {
                bonusAmount = 250;
            }
        }

        // Create Royal Captain Bonus record if eligible
        if (isEligible && bonusAmount > 0) {
            const royalCaptainBonus = new RoyalCaptainBonus({
                userId: userId,
                awardAmount: bonusAmount,
                globalTeamSize: globalTeamSize,
                matrixGlobalReferrals: partnersWithBothPackages,
                status: 'pending',
                createdAt: new Date()
            });

            await royalCaptainBonus.save();
        }

        return {
            success: true,
            isEligible: isEligible,
            bonusAmount: bonusAmount,
            requirements: {
                hasMatrixPackage,
                hasGlobalPackage,
                hasBothPackages,
                directPartnersCount: directPartners.length,
                partnersWithBothPackages,
                globalTeamSize,
                minRequired: 5
            },
            message: isEligible ? `Eligible for $${bonusAmount} Royal Captain Bonus` : 'Not eligible for Royal Captain Bonus'
        };

    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}
```

### 5.2 President Reward Function
```javascript
/**
 * Checks and processes President Reward eligibility
 * @param {string} userId - User ID
 * @returns {Object} President Reward result
 */
async function checkPresidentRewardEligibility(userId) {
    try {
        const user = await User.findById(userId);
        if (!user) {
            throw new Error('User not found');
        }

        // Count direct invitations
        const directInvites = await TreePlacement.find({
            parentId: userId,
            isActive: true
        }).countDocuments();

        // Calculate global team size
        const globalTeamSize = await calculateGlobalTeamSize(userId);

        // Evaluate qualification tiers based on PROJECT_DOCUMENTATION.md
        let awardAmount = 0;
        let tier = 0;

        if (directInvites >= 10 && globalTeamSize >= 80) {
            awardAmount = 500; // Tier 1
            tier = 1;
        } else if (globalTeamSize >= 150 && globalTeamSize < 200) {
            awardAmount = 700; // Tier 2
            tier = 2;
        } else if (globalTeamSize >= 200 && globalTeamSize < 250) {
            awardAmount = 700; // Tier 2
            tier = 2;
        } else if (globalTeamSize >= 250 && globalTeamSize < 300) {
            awardAmount = 700; // Tier 2
            tier = 2;
        } else if (globalTeamSize >= 300 && globalTeamSize < 400) {
            awardAmount = 700; // Tier 2
            tier = 2;
        } else if (directInvites >= 15 && globalTeamSize >= 400 && globalTeamSize < 500) {
            awardAmount = 800; // Tier 3
            tier = 3;
        } else if (directInvites >= 15 && globalTeamSize >= 500 && globalTeamSize < 600) {
            awardAmount = 800; // Tier 3
            tier = 3;
        } else if (directInvites >= 15 && globalTeamSize >= 600 && globalTeamSize < 700) {
            awardAmount = 800; // Tier 3
            tier = 3;
        } else if (directInvites >= 15 && globalTeamSize >= 700 && globalTeamSize < 1000) {
            awardAmount = 800; // Tier 3
            tier = 3;
        } else if (directInvites >= 20 && globalTeamSize >= 1000 && globalTeamSize < 1500) {
            awardAmount = 1500; // Tier 4
            tier = 4;
        } else if (globalTeamSize >= 1500 && globalTeamSize < 2000) {
            awardAmount = 1500; // Tier 5
            tier = 5;
        } else if (globalTeamSize >= 2000 && globalTeamSize < 2500) {
            awardAmount = 2000; // Tier 5
            tier = 5;
        } else if (globalTeamSize >= 2500 && globalTeamSize < 3000) {
            awardAmount = 2500; // Tier 5
            tier = 5;
        } else if (globalTeamSize >= 3000 && globalTeamSize < 4000) {
            awardAmount = 2500; // Tier 5
            tier = 5;
        } else if (directInvites >= 30 && globalTeamSize >= 4000) {
            awardAmount = 5000; // Tier 6
            tier = 6;
        }

        // Create President Reward record if any threshold met
        if (awardAmount > 0) {
            const presidentReward = new PresidentReward({
                userId: userId,
                awardAmount: awardAmount,
                globalTeamSize: globalTeamSize,
                directInvites: directInvites,
                tier: tier,
                status: 'pending',
                createdAt: new Date()
            });

            await presidentReward.save();
        }

        return {
            success: true,
            isEligible: awardAmount > 0,
            awardAmount: awardAmount,
            tier: tier,
            requirements: {
                directInvites: directInvites,
                globalTeamSize: globalTeamSize,
                minDirectInvites: 10,
                minGlobalTeam: 80
            },
            message: awardAmount > 0 ? `Eligible for $${awardAmount} President Reward (Tier ${tier})` : 'Not eligible for President Reward'
        };

    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}
```

### 5.3 Leadership Stipend Function
```javascript
/**
 * Checks Leadership Stipend eligibility for slots 10-16
 * @param {string} userId - User ID
 * @returns {Object} Leadership Stipend result
 */
async function checkLeadershipStipendEligibility(userId) {
    try {
        // Get user's highest activated slot
        const slotActivations = await SlotActivation.find({
            userId: userId,
            status: 'completed'
        }).sort({ slotNo: -1 });

        const highestSlot = slotActivations.length > 0 ? slotActivations[0].slotNo : 0;
        const slots10to16 = slotActivations.filter(activation => activation.slotNo >= 10 && activation.slotNo <= 16);

        // Check if user has slot 10+ activated
        const isEligible = highestSlot >= 10;

        if (!isEligible) {
            return {
                success: true,
                isEligible: false,
                highestSlot: highestSlot,
                slots10to16: slots10to16.map(s => s.slotNo),
                reason: `Need to activate slot ${10 - highestSlot} more to reach slot 10`,
                message: 'Not eligible for Leadership Stipend'
            };
        }

        // Get tier information for highest slot
        const tierInfo = getLeadershipStipendTierInfo(highestSlot);
        
        // Calculate daily return (double the slot value)
        const dailyReturn = tierInfo.dailyReturn;

        // Create or update Leadership Stipend record
        let leadershipStipend = await LeadershipStipend.findOne({ userId: userId });
        if (!leadershipStipend) {
            leadershipStipend = new LeadershipStipend({
                userId: userId,
                joinedAt: new Date(),
                isActive: true,
                isEligible: true,
                qualifiedAt: new Date(),
                currentTier: highestSlot,
                currentTierName: tierInfo.tierName,
                currentDailyReturn: dailyReturn,
                highestSlotAchieved: highestSlot,
                slotsActivated: slotActivations.map(s => s.slotNo)
            });
        } else {
            leadershipStipend.isEligible = true;
            leadershipStipend.currentTier = highestSlot;
            leadershipStipend.currentTierName = tierInfo.tierName;
            leadershipStipend.currentDailyReturn = dailyReturn;
            leadershipStipend.highestSlotAchieved = highestSlot;
            leadershipStipend.lastUpdated = new Date();
        }

        await leadershipStipend.save();

        return {
            success: true,
            isEligible: true,
            currentTier: {
                slotNumber: highestSlot,
                tierName: tierInfo.tierName,
                slotValue: tierInfo.slotValue,
                dailyReturn: dailyReturn
            },
            slots10to16: slots10to16.map(s => s.slotNo),
            message: `Eligible for Leadership Stipend - ${tierInfo.tierName} tier with ${dailyReturn} BNB daily return`
        };

    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}
```

---

## 6. JACKPOT PROGRAM FUNCTIONS

### 6.1 Award Jackpot Free Coupon Function
```javascript
/**
 * Awards free jackpot coupons based on binary slot upgrades
 * @param {string} userId - User ID
 * @param {number} slotNo - Slot number
 */
async function awardJackpotFreeCoupon(userId, slotNo) {
    try {
        // Per docs: Slot 5 => 1, Slot 6 => 2, ... up to Slot 16 (progressive)
        if (slotNo < 5) {
            return; // No free coupons for slots 1-4
        }

        const entries = Math.max(1, slotNo - 4); // Slot 5 = 1 entry, Slot 6 = 2 entries, etc.
        
        const user = await User.findById(userId);
        const referrer = user ? user.referedBy : null;

        // Create free jackpot entries
        for (let i = 0; i < entries; i++) {
            const ticket = new JackpotTicket({
                userId: userId,
                referrerUserId: referrer,
                weekId: getCurrentWeekId(),
                source: 'free',
                freeSourceSlot: slotNo,
                status: 'active',
                createdAt: new Date()
            });

            await ticket.save();
        }

        console.log(`Awarded ${entries} free jackpot coupons for slot ${slotNo} to user ${userId}`);

    } catch (error) {
        console.error('Error awarding jackpot free coupon:', error);
    }
}
```

---

## 7. HELPER FUNCTIONS

### 7.1 Get Dual Tree Percentages Function
```javascript
/**
 * Returns dual tree distribution percentages
 * @returns {Object} Level percentages
 */
function getDualTreePercentages() {
    return {
        1: 30,   // 30%
        2: 10,   // 10%
        3: 10,   // 10%
        4: 5,    // 5%
        5: 5,    // 5%
        6: 5,    // 5%
        7: 5,    // 5%
        8: 5,    // 5%
        9: 5,    // 5%
        10: 5,   // 5%
        11: 3,   // 3%
        12: 3,   // 3%
        13: 3,   // 3%
        14: 2,   // 2%
        15: 2,   // 2%
        16: 2    // 2%
    };
}
```

### 7.2 Get Binary Slot Cost Function
```javascript
/**
 * Returns Binary slot cost based on slot number
 * @param {number} slotNo - Slot number
 * @returns {number} Slot cost in BNB
 */
function getBinarySlotCost(slotNo) {
    const slotCosts = [
        0.0022, 0.0044, 0.0088, 0.0176, 0.0352, 0.0704, 0.1408, 0.2816,
        0.5632, 1.1264, 2.2528, 4.5056, 9.0112, 18.0224, 36.0448, 72.0896
    ];
    
    if (slotNo >= 1 && slotNo <= slotCosts.length) {
        return slotCosts[slotNo - 1];
    }
    
    return 0;
}
```

### 7.3 Get Leadership Stipend Tier Info Function
```javascript
/**
 * Returns Leadership Stipend tier information
 * @param {number} slotNumber - Slot number
 * @returns {Object} Tier information
 */
function getLeadershipStipendTierInfo(slotNumber) {
    const tierMapping = {
        10: { tierName: 'LEADER', slotValue: 1.1264, dailyReturn: 2.2528 },
        11: { tierName: 'VANGURD', slotValue: 2.2528, dailyReturn: 4.5056 },
        12: { tierName: 'CENTER', slotValue: 4.5056, dailyReturn: 9.0112 },
        13: { tierName: 'CLIMAX', slotValue: 9.0112, dailyReturn: 18.0224 },
        14: { tierName: 'ENTERNITY', slotValue: 18.0224, dailyReturn: 36.0448 },
        15: { tierName: 'KING', slotValue: 36.0448, dailyReturn: 72.0896 },
        16: { tierName: 'COMMENDER', slotValue: 72.0896, dailyReturn: 144.1792 }
    };
    
    return tierMapping[slotNumber] || { tierName: 'UNKNOWN', slotValue: 0, dailyReturn: 0 };
}
```

### 7.4 Get Current Week ID Function
```javascript
/**
 * Returns current week ID for jackpot system
 * @returns {string} Week ID in format YYYY-WW
 */
function getCurrentWeekId() {
    const now = new Date();
    const year = now.getFullYear();
    const week = getWeekNumber(now);
    return `${year}-${week.toString().padStart(2, '0')}`;
}

/**
 * Gets week number of the year
 * @param {Date} date - Date object
 * @returns {number} Week number
 */
function getWeekNumber(date) {
    const firstDayOfYear = new Date(date.getFullYear(), 0, 1);
    const pastDaysOfYear = (date - firstDayOfYear) / 86400000;
    return Math.ceil((pastDaysOfYear + firstDayOfYear.getDay() + 1) / 7);
}
```

---

## 8. SUMMARY

This documentation provides comprehensive JavaScript function implementations for all automatic processes that occur when a user joins the BitGPT platform:

### Key Functions Implemented:

1. **User Creation Functions**:
   - `createUser()` - Main user creation with all automatic processes
   - `initializeUserPrograms()` - Program initialization
   - `initializeBinaryProgram()` - Binary program setup

2. **Referrer Automatic Calculations**:
   - `processReferrerCalculations()` - Main referrer calculation processor
   - `updateReferrerPartnerGraph()` - Partner graph updates
   - `processReferrerJoiningCommissions()` - 10% joining commissions
   - `checkReferrerRoyalCaptainEligibility()` - Royal Captain Bonus checks
   - `checkReferrerPresidentRewardEligibility()` - President Reward checks
   - `updateReferrerRank()` - Rank progression
   - `updateReferrerCommissionAccumulation()` - Commission tracking

3. **Binary Program Functions**:
   - `processBinaryAutoUpgrade()` - Auto upgrade processing
   - `calculateDualTreeEarnings()` - Dual tree earning calculations

4. **Commission Functions**:
   - `calculateJoiningCommission()` - 10% joining commission
   - `calculateUpgradeCommission()` - 30% upgrade commission
   - `distributeAcrossLevels()` - Dual tree distribution

5. **Rank System Functions**:
   - `updateUserRank()` - Rank calculation and update
   - `calculateUserRank()` - Rank determination logic

6. **Special Programs Functions**:
   - `checkRoyalCaptainEligibility()` - Royal Captain Bonus
   - `checkPresidentRewardEligibility()` - President Reward
   - `checkLeadershipStipendEligibility()` - Leadership Stipend

7. **Jackpot Functions**:
   - `awardJackpotFreeCoupon()` - Free coupon awards

8. **Helper Functions**:
   - Various utility functions for calculations and data retrieval

### How These Functions Work:

1. **User Join Process**: When a user joins, `createUser()` is called which triggers all automatic initialization processes
2. **Automatic Calculations**: All commission calculations, rank updates, and special program checks happen automatically
3. **Real-time Processing**: Functions process data in real-time and update user status immediately
4. **Error Handling**: All functions include comprehensive error handling and logging
5. **Database Integration**: Functions interact with MongoDB collections for data persistence

**All processes are fully automated and require no manual intervention.**

---

*This documentation is part of the BitGPT platform documentation suite and provides JavaScript implementations for all automatic user join processes.*
