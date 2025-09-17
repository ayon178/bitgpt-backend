# Binary Program Functions Documentation

## Overview
This document provides comprehensive JavaScript function implementations for all Binary Program slot upgrade processes, automatic calculations, and integrations that occur in the BitGPT platform, based on the backend analysis and `02_BINARY_SLOT_UPGRADE_AUTO_ACTIONS.md`.

---

## 1. BINARY SLOT UPGRADE FUNCTIONS

### 1.1 Main Binary Slot Upgrade Function
```javascript
/**
 * Main function to upgrade Binary slot with all automatic processes
 * @param {string} userId - User ID upgrading the slot
 * @param {number} slotNo - Target slot number (3-16)
 * @param {string} txHash - Blockchain transaction hash
 * @param {number} amount - Upgrade amount in BNB
 * @returns {Object} Result with success status and details
 */
async function upgradeBinarySlot(userId, slotNo, txHash, amount) {
    try {
        // 1. Validate user and slot upgrade
        const validationResult = await validateBinarySlotUpgrade(userId, slotNo, amount);
        if (!validationResult.success) {
            return validationResult;
        }

        const { user, binaryStatus, catalog, currency } = validationResult.data;

        // 2. Create slot activation record
        const activation = await createSlotActivation(userId, slotNo, catalog, amount, txHash, currency);

        // 3. Update binary auto upgrade status
        await updateBinaryAutoUpgradeStatus(userId, slotNo);

        // 4. Process upgrade commission (30% to corresponding level + 70% dual tree distribution)
        const commissionResult = await calculateUpgradeCommission(
            userId, 'binary', slotNo, catalog.name, amount, currency
        );

        // 5. Update user rank
        const rankResult = await updateUserRank(userId);

        // 6. Award jackpot free coupons (slots 5-16)
        let jackpotResult = null;
        if (slotNo >= 5) {
            jackpotResult = await awardJackpotFreeCoupon(userId, slotNo);
        }

        // 7. Check leadership stipend eligibility (slots 10-16)
        let stipendResult = null;
        if (slotNo >= 10) {
            stipendResult = await checkLeadershipStipendEligibility(userId, true);
        }

        // 8. Contribute to Spark bonus fund (8% of binary earnings)
        const sparkResult = await contributeToSparkFund(
            'binary', amount, currency, userId, 'slot_upgrade', slotNo
        );

        // 9. Record earning history
        await recordEarningHistory(userId, 'binary_slot_upgrade', 'binary', amount, currency, catalog);

        // 10. Record blockchain event
        await recordBlockchainEvent(txHash, 'slot_upgraded', {
            program: 'binary',
            slot_no: slotNo,
            slot_name: catalog.name,
            amount: amount.toString(),
            currency: currency,
            user_id: userId,
            upgrade_type: 'manual'
        });

        // 11. Update user's binary slot info
        await updateUserBinarySlotInfo(user, slotNo, catalog.name, amount);

        return {
            success: true,
            activation_id: activation.id,
            new_slot: catalog.name,
            slot_no: slotNo,
            amount: amount,
            currency: currency,
            commission_result: commissionResult,
            rank_result: rankResult,
            jackpot_result: jackpotResult,
            stipend_result: stipendResult,
            spark_result: sparkResult,
            message: `Successfully upgraded to ${catalog.name} (Slot ${slotNo})`
        };

    } catch (error) {
        return { success: false, error: error.message };
    }
}
```

### 1.2 Binary Slot Upgrade Validation Function
```javascript
/**
 * Validates Binary slot upgrade requirements
 * @param {string} userId - User ID
 * @param {number} slotNo - Target slot number
 * @param {number} amount - Upgrade amount
 * @returns {Object} Validation result
 */
async function validateBinarySlotUpgrade(userId, slotNo, amount) {
    try {
        // Validate user exists
        const user = await User.findById(userId);
        if (!user) {
            return { success: false, error: "User not found" };
        }

        // Validate slot upgrade range
        if (slotNo < 3 || slotNo > 16) {
            return { success: false, error: "Invalid slot number. Must be between 3-16" };
        }

        // Get current binary status
        const binaryStatus = await BinaryAutoUpgrade.findOne({ user_id: userId });
        if (!binaryStatus) {
            return { success: false, error: "User not in Binary program" };
        }

        // Validate slot progression
        if (slotNo <= binaryStatus.current_slot_no) {
            return { 
                success: false, 
                error: `Cannot upgrade to slot ${slotNo}. Current slot is ${binaryStatus.current_slot_no}` 
            };
        }

        // Get slot catalog
        const catalog = await SlotCatalog.findOne({ 
            program: 'binary', 
            slot_no: slotNo, 
            is_active: true 
        });
        if (!catalog) {
            return { success: false, error: `Slot ${slotNo} catalog not found` };
        }

        // Validate amount
        const expectedAmount = catalog.price || 0;
        if (amount !== expectedAmount) {
            return { 
                success: false, 
                error: `Upgrade amount must be ${expectedAmount} BNB` 
            };
        }

        const currency = ensureCurrencyForProgram('binary', 'BNB');

        return {
            success: true,
            data: { user, binaryStatus, catalog, currency }
        };

    } catch (error) {
        return { success: false, error: error.message };
    }
}
```

### 1.3 Slot Activation Creation Function
```javascript
/**
 * Creates slot activation record for Binary program
 * @param {string} userId - User ID
 * @param {number} slotNo - Slot number
 * @param {Object} catalog - Slot catalog data
 * @param {number} amount - Amount paid
 * @param {string} txHash - Transaction hash
 * @param {string} currency - Currency
 * @returns {Object} Created activation record
 */
async function createSlotActivation(userId, slotNo, catalog, amount, txHash, currency) {
    const activation = new SlotActivation({
        user_id: userId,
        program: 'binary',
        slot_no: slotNo,
        slot_name: catalog.name,
        activation_type: 'upgrade',
        upgrade_source: 'manual',
        amount_paid: amount,
        currency: currency,
        tx_hash: txHash,
        is_auto_upgrade: false,
        status: 'completed',
        activated_at: new Date(),
        completed_at: new Date()
    });

    await activation.save();
    return activation;
}
```

---

## 2. COMMISSION CALCULATION FUNCTIONS

### 2.1 Upgrade Commission Calculation Function
```javascript
/**
 * Calculates upgrade commission with 30% to corresponding level and 70% distribution
 * @param {string} fromUserId - User who upgraded
 * @param {string} program - Program name ('binary')
 * @param {number} slotNo - Slot number
 * @param {string} slotName - Slot name
 * @param {number} amount - Upgrade amount
 * @param {string} currency - Currency
 * @returns {Object} Commission calculation result
 */
async function calculateUpgradeCommission(fromUserId, program, slotNo, slotName, amount, currency) {
    try {
        // Get user
        const fromUser = await User.findById(fromUserId);
        if (!fromUser) {
            return { success: false, error: "User not found" };
        }

        // Calculate total commission amount (100% of upgrade value)
        const totalCommission = amount * (100.0 / 100); // 100% participates in distribution

        // 30% to corresponding level upline
        const levelCommission = totalCommission * (30.0 / 100);

        // 70% for distribution across levels 1-16
        const distributionAmount = totalCommission * (70.0 / 100);

        // Get corresponding level upline
        const levelUpline = await getLevelUpline(fromUserId, slotNo);

        // Process level commission (30%)
        if (levelUpline) {
            await createCommissionRecord({
                user_id: levelUpline.id,
                from_user_id: fromUserId,
                commission_type: 'upgrade',
                program: program,
                commission_amount: levelCommission,
                currency: currency,
                commission_percentage: 30.0,
                source_slot_no: slotNo,
                source_slot_name: slotName,
                level: slotNo,
                is_level_commission: true,
                distribution_type: 'level',
                status: 'pending'
            });

            // Credit wallet
            await creditWallet(levelUpline.id, levelCommission, currency, 
                `${program}_upgrade_level_commission`, '');
        } else {
            // Missed profit goes to Leadership Stipend
            await handleMissedProfit(fromUserId, levelCommission, currency, 
                `${program}_upgrade_level_commission_missed`);
        }

        // Process dual tree distribution (70%)
        const distributionResult = await distributeAcrossLevels(
            fromUserId, program, slotNo, distributionAmount, currency
        );

        return {
            success: true,
            total_commission: totalCommission,
            level_commission: levelCommission,
            distribution_amount: distributionAmount,
            level_upline: levelUpline ? levelUpline.id : null,
            distribution_result: distributionResult
        };

    } catch (error) {
        return { success: false, error: error.message };
    }
}
```

### 2.2 Dual Tree Distribution Function
```javascript
/**
 * Distributes 70% commission across levels 1-16 according to Dual Tree Earning rules
 * @param {string} fromUserId - User who generated commission
 * @param {string} program - Program name
 * @param {number} slotNo - Slot number
 * @param {number} distributionAmount - Amount to distribute
 * @param {string} currency - Currency
 * @returns {Object} Distribution result
 */
async function distributeAcrossLevels(fromUserId, program, slotNo, distributionAmount, currency) {
    try {
        // Distribution percentages according to PROJECT_DOCUMENTATION.md
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

        const distributionResults = [];

        // Distribute across levels 1 to slotNo
        for (let level = 1; level <= Math.min(slotNo, 16); level++) {
            const percentage = distributions[level] || 0;
            const levelAmount = distributionAmount * percentage;

            if (levelAmount > 0) {
                // Get upline at this level
                const upline = await getUplineAtLevel(fromUserId, level);

                if (upline) {
                    // Create commission record
                    await createCommissionRecord({
                        user_id: upline.id,
                        from_user_id: fromUserId,
                        commission_type: 'upgrade',
                        program: program,
                        commission_amount: levelAmount,
                        currency: currency,
                        commission_percentage: percentage * 100,
                        source_slot_no: slotNo,
                        level: level,
                        is_level_commission: false,
                        distribution_type: 'level',
                        distribution_level: level,
                        status: 'pending'
                    });

                    // Credit wallet
                    await creditWallet(upline.id, levelAmount, currency, 
                        `${program}_upgrade_level_${level}_commission`, '');

                    distributionResults.push({
                        level: level,
                        upline_id: upline.id,
                        amount: levelAmount,
                        percentage: percentage * 100,
                        status: 'distributed'
                    });
                } else {
                    // Missed profit
                    await handleMissedProfit(fromUserId, levelAmount, currency, 
                        `${program}_upgrade_level_${level}_commission_missed`);

                    distributionResults.push({
                        level: level,
                        upline_id: null,
                        amount: levelAmount,
                        percentage: percentage * 100,
                        status: 'missed'
                    });
                }
            }
        }

        return {
            success: true,
            total_distributed: distributionAmount,
            distributions: distributionResults
        };

    } catch (error) {
        return { success: false, error: error.message };
    }
}
```

### 2.3 Commission Record Creation Function
```javascript
/**
 * Creates commission record in database
 * @param {Object} commissionData - Commission data
 * @returns {Object} Created commission record
 */
async function createCommissionRecord(commissionData) {
    const commission = new Commission({
        user_id: commissionData.user_id,
        from_user_id: commissionData.from_user_id,
        commission_type: commissionData.commission_type,
        program: commissionData.program,
        commission_amount: commissionData.commission_amount,
        currency: commissionData.currency,
        commission_percentage: commissionData.commission_percentage,
        source_slot_no: commissionData.source_slot_no,
        source_slot_name: commissionData.source_slot_name,
        level: commissionData.level,
        is_direct_commission: commissionData.is_direct_commission || false,
        is_level_commission: commissionData.is_level_commission || false,
        distribution_type: commissionData.distribution_type || 'direct',
        distribution_level: commissionData.distribution_level,
        status: commissionData.status || 'pending',
        created_at: new Date()
    });

    await commission.save();
    return commission;
}
```

---

## 3. AUTO UPGRADE SYSTEM FUNCTIONS

### 3.1 Binary Auto Upgrade Processing Function
```javascript
/**
 * Processes Binary auto upgrade using first 2 partners' earnings
 * @param {string} userId - User ID
 * @returns {Object} Auto upgrade result
 */
async function processBinaryAutoUpgrade(userId) {
    try {
        // Get user's binary auto upgrade status
        const binaryStatus = await BinaryAutoUpgrade.findOne({ user_id: userId });
        if (!binaryStatus) {
            return { success: false, error: "Binary auto upgrade status not found" };
        }

        // Check if user has 2 partners
        if (binaryStatus.partners_available < binaryStatus.partners_required) {
            return { success: false, error: "Insufficient partners for auto upgrade" };
        }

        // Calculate earnings from first 2 partners
        const earningsFromPartners = await calculateBinaryPartnerEarnings(userId);

        if (earningsFromPartners <= 0) {
            return { success: false, error: "No earnings available from partners" };
        }

        // Calculate next upgrade cost
        const nextSlot = binaryStatus.current_slot_no + 1;
        const upgradeCost = await getBinarySlotCost(nextSlot);

        if (earningsFromPartners < upgradeCost) {
            return { success: false, error: "Insufficient earnings for upgrade" };
        }

        // Create auto upgrade queue entry
        const queueEntry = new AutoUpgradeQueue({
            user_id: userId,
            program: 'binary',
            current_slot_no: binaryStatus.current_slot_no,
            target_slot_no: nextSlot,
            upgrade_cost: upgradeCost,
            currency: 'BNB',
            earnings_available: earningsFromPartners,
            status: 'pending',
            priority: 1,
            trigger: {
                trigger_type: 'partner_upgrade',
                trigger_source: 'binary_partners',
                trigger_count: binaryStatus.partners_available,
                triggered_at: new Date()
            },
            queued_at: new Date()
        });

        await queueEntry.save();

        // Update binary status
        binaryStatus.is_eligible = true;
        binaryStatus.can_upgrade = true;
        binaryStatus.next_upgrade_cost = upgradeCost;
        binaryStatus.last_check_at = new Date();
        await binaryStatus.save();

        return {
            success: true,
            queue_id: queueEntry.id,
            current_slot: binaryStatus.current_slot_no,
            target_slot: nextSlot,
            upgrade_cost: upgradeCost,
            earnings_available: earningsFromPartners,
            message: "Auto upgrade queued successfully"
        };

    } catch (error) {
        return { success: false, error: error.message };
    }
}
```

### 3.2 Binary Partner Earnings Calculation Function
```javascript
/**
 * Calculates earnings from first 2 partners for auto upgrade
 * @param {string} userId - User ID
 * @returns {number} Total earnings from partners
 */
async function calculateBinaryPartnerEarnings(userId) {
    try {
        // Get user's binary status
        const binaryStatus = await BinaryAutoUpgrade.findOne({ user_id: userId });
        if (!binaryStatus || !binaryStatus.partner_ids || binaryStatus.partner_ids.length < 2) {
            return 0;
        }

        // Get first 2 partners
        const firstTwoPartners = binaryStatus.partner_ids.slice(0, 2);
        
        let totalEarnings = 0;

        // Calculate earnings from each partner
        for (const partnerId of firstTwoPartners) {
            // Get partner's commission records
            const partnerCommissions = await Commission.find({
                from_user_id: partnerId,
                program: 'binary',
                commission_type: 'upgrade',
                status: 'paid'
            });

            // Sum up earnings from this partner
            const partnerEarnings = partnerCommissions.reduce((sum, commission) => {
                return sum + parseFloat(commission.commission_amount);
            }, 0);

            totalEarnings += partnerEarnings;
        }

        return totalEarnings;

    } catch (error) {
        console.error('Error calculating partner earnings:', error);
        return 0;
    }
}
```

### 3.3 Auto Upgrade Queue Processing Function
```javascript
/**
 * Processes auto upgrade queue entries
 * @param {string} queueId - Queue entry ID
 * @returns {Object} Processing result
 */
async function processAutoUpgradeQueue(queueId) {
    try {
        const queueEntry = await AutoUpgradeQueue.findById(queueId);
        if (!queueEntry) {
            return { success: false, error: "Queue entry not found" };
        }

        // Update status to processing
        queueEntry.status = 'processing';
        queueEntry.processed_at = new Date();
        await queueEntry.save();

        const userId = queueEntry.user_id.toString();
        const fromSlot = queueEntry.current_slot_no;
        const toSlot = queueEntry.target_slot_no;
        const upgradeCost = queueEntry.upgrade_cost;
        const currency = queueEntry.currency;

        // Generate transaction hash
        const txHash = `AUTOUP-${userId}-${queueEntry.program}-S${toSlot}-${Date.now()}`;

        let result;

        if (queueEntry.program === 'binary') {
            // Process binary auto upgrade
            result = await upgradeBinarySlot(userId, toSlot, txHash, upgradeCost);
        } else {
            return { success: false, error: "Unsupported program for auto processing" };
        }

        if (result.success) {
            // Update queue entry
            queueEntry.status = 'completed';
            queueEntry.completed_at = new Date();
            await queueEntry.save();

            // Create auto upgrade log
            await createAutoUpgradeLog(queueEntry, result);

            return {
                success: true,
                result: result,
                message: "Auto upgrade completed successfully"
            };
        } else {
            // Handle failure
            queueEntry.status = 'failed';
            queueEntry.error_message = result.error;
            queueEntry.retry_count += 1;
            await queueEntry.save();

            return { success: false, error: result.error };
        }

    } catch (error) {
        return { success: false, error: error.message };
    }
}
```

---

## 4. INTEGRATION FUNCTIONS

### 4.1 Jackpot Free Coupon Award Function
```javascript
/**
 * Awards free jackpot coupons based on binary slot upgrades
 * Slot 5 => 1 entry, Slot 6 => 2 entries, Slot 7-16 => (slot_no - 4) entries
 * @param {string} userId - User ID
 * @param {number} slotNo - Slot number
 * @returns {Object} Jackpot result
 */
async function awardJackpotFreeCoupon(userId, slotNo) {
    try {
        if (slotNo < 5) {
            return { success: false, error: "Slot must be 5 or higher for jackpot coupons" };
        }

        // Calculate number of entries: Slot 5 = 1, Slot 6 = 2, Slot 7-16 = (slot_no - 4)
        const entries = Math.max(1, slotNo - 4);

        // Get user and referrer
        const user = await User.findById(userId);
        const referrerId = user.refered_by ? user.refered_by.toString() : null;

        if (!referrerId) {
            return { success: false, error: "Referrer not found for jackpot entry" };
        }

        const createdTickets = [];

        // Create entries
        for (let i = 0; i < entries; i++) {
            const ticket = new JackpotTicket({
                user_id: userId,
                referrer_user_id: referrerId,
                week_id: getCurrentWeekId(),
                source: 'free',
                free_source_slot: slotNo,
                status: 'active',
                created_at: new Date()
            });

            await ticket.save();
            createdTickets.push(ticket.id);
        }

        return {
            success: true,
            slot_no: slotNo,
            entries_awarded: entries,
            ticket_ids: createdTickets,
            message: `Awarded ${entries} free jackpot coupon(s) for slot ${slotNo}`
        };

    } catch (error) {
        return { success: false, error: error.message };
    }
}
```

### 4.2 Leadership Stipend Eligibility Check Function
```javascript
/**
 * Checks Leadership Stipend eligibility for user
 * @param {string} userId - User ID
 * @param {boolean} forceCheck - Force eligibility check
 * @returns {Object} Eligibility result
 */
async function checkLeadershipStipendEligibility(userId, forceCheck = false) {
    try {
        // Get Leadership Stipend record
        let leadershipStipend = await LeadershipStipend.findOne({ user_id: userId });
        if (!leadershipStipend) {
            return { success: false, error: "User not in Leadership Stipend program" };
        }

        // Get eligibility record
        let eligibility = await LeadershipStipendEligibility.findOne({ user_id: userId });
        if (!eligibility) {
            eligibility = new LeadershipStipendEligibility({ user_id: userId });
        }

        // Check slot requirements
        const slotStatus = await checkSlotRequirements(userId);
        eligibility.highest_slot_activated = slotStatus.highest_slot;
        eligibility.slots_10_16_activated = slotStatus.slots_10_16;

        // Update Leadership Stipend record
        leadershipStipend.highest_slot_achieved = slotStatus.highest_slot;
        leadershipStipend.slots_activated = slotStatus.all_slots;

        // Determine eligibility (minimum slot 10 required)
        eligibility.is_eligible_for_stipend = eligibility.highest_slot_activated >= 10;

        // Update eligibility reasons
        eligibility.eligibility_reasons = getEligibilityReasons(eligibility);

        if (eligibility.is_eligible_for_stipend && forceCheck) {
            // Update current tier and daily return
            const highestSlot = eligibility.highest_slot_activated;
            leadershipStipend.current_tier = highestSlot;
            leadershipStipend.current_tier_name = getSlotName(highestSlot);
            leadershipStipend.current_daily_return = calculateDailyReturn(highestSlot);
            leadershipStipend.is_active = true;
            leadershipStipend.qualified_at = new Date();
        }

        eligibility.last_checked = new Date();
        await eligibility.save();
        await leadershipStipend.save();

        return {
            success: true,
            is_eligible: eligibility.is_eligible_for_stipend,
            highest_slot: eligibility.highest_slot_activated,
            current_tier: leadershipStipend.current_tier,
            current_daily_return: leadershipStipend.current_daily_return,
            eligibility_reasons: eligibility.eligibility_reasons,
            message: eligibility.is_eligible_for_stipend ? 
                "User is eligible for Leadership Stipend" : 
                "User is not eligible for Leadership Stipend"
        };

    } catch (error) {
        return { success: false, error: error.message };
    }
}
```

### 4.3 Spark Fund Contribution Function
```javascript
/**
 * Contributes to Spark bonus fund (8% of binary earnings)
 * @param {string} program - Program name
 * @param {number} amount - Contribution amount
 * @param {string} currency - Currency
 * @param {string} sourceUserId - Source user ID
 * @param {string} sourceType - Source type
 * @param {number} sourceSlotNo - Source slot number
 * @returns {Object} Spark contribution result
 */
async function contributeToSparkFund(program, amount, currency, sourceUserId, sourceType, sourceSlotNo) {
    try {
        // Calculate 8% contribution
        const contributionAmount = amount * 0.08;

        // Get current cycle
        const currentCycle = getCurrentCycle();

        // Create or update Spark cycle
        let sparkCycle = await SparkCycle.findOne({ 
            cycle_no: currentCycle, 
            slot_no: sourceSlotNo 
        });

        if (!sparkCycle) {
            sparkCycle = new SparkCycle({
                cycle_no: currentCycle,
                slot_no: sourceSlotNo,
                pool_amount: contributionAmount,
                participants: [sourceUserId],
                distribution_percentage: 0,
                payout_per_participant: 0,
                status: 'active',
                created_at: new Date()
            });
        } else {
            sparkCycle.pool_amount += contributionAmount;
            if (!sparkCycle.participants.includes(sourceUserId)) {
                sparkCycle.participants.push(sourceUserId);
            }
        }

        await sparkCycle.save();

        // Calculate distribution percentage (80% distributed across Matrix levels 1-14)
        const matrixDistributionPercentage = 0.80;
        const tripleEntryPercentage = 0.20;

        // Update distribution percentages
        sparkCycle.distribution_percentage = matrixDistributionPercentage;
        sparkCycle.payout_per_participant = (sparkCycle.pool_amount * matrixDistributionPercentage) / sparkCycle.participants.length;
        await sparkCycle.save();

        return {
            success: true,
            cycle_no: currentCycle,
            slot_no: sourceSlotNo,
            contribution_amount: contributionAmount,
            total_pool: sparkCycle.pool_amount,
            participants_count: sparkCycle.participants.length,
            distribution_percentage: matrixDistributionPercentage * 100,
            payout_per_participant: sparkCycle.payout_per_participant,
            message: `Contributed ${contributionAmount} ${currency} to Spark fund`
        };

    } catch (error) {
        return { success: false, error: error.message };
    }
}
```

---

## 5. UTILITY FUNCTIONS

### 5.1 Level Upline Retrieval Function
```javascript
/**
 * Gets upline at specific level for commission distribution
 * @param {string} userId - User ID
 * @param {number} level - Level number
 * @returns {Object|null} Upline user or null
 */
async function getUplineAtLevel(userId, level) {
    try {
        let currentUserId = userId;
        
        // Traverse up the tree for the specified level
        for (let i = 0; i < level; i++) {
            const user = await User.findById(currentUserId);
            if (!user || !user.refered_by) {
                return null; // No upline at this level
            }
            currentUserId = user.refered_by.toString();
        }

        // Return the upline at the specified level
        return await User.findById(currentUserId);

    } catch (error) {
        console.error('Error getting upline at level:', error);
        return null;
    }
}
```

### 5.2 Binary Slot Cost Calculation Function
```javascript
/**
 * Gets Binary slot cost from catalog
 * @param {number} slotNo - Slot number
 * @returns {number} Slot cost in BNB
 */
async function getBinarySlotCost(slotNo) {
    try {
        const catalog = await SlotCatalog.findOne({ 
            program: 'binary', 
            slot_no: slotNo, 
            is_active: true 
        });
        
        return catalog ? parseFloat(catalog.price) : 0;

    } catch (error) {
        console.error('Error getting binary slot cost:', error);
        return 0;
    }
}
```

### 5.3 User Binary Slot Info Update Function
```javascript
/**
 * Updates user's binary slot information
 * @param {Object} user - User object
 * @param {number} slotNo - Slot number
 * @param {string} slotName - Slot name
 * @param {number} amount - Slot value
 */
async function updateUserBinarySlotInfo(user, slotNo, slotName, amount) {
    try {
        // Update user's current binary slot
        user.current_binary_slot = slotNo;
        user.current_binary_slot_name = slotName;

        // Add to binary slots list if not exists
        if (!user.binary_slots) {
            user.binary_slots = [];
        }

        // Check if slot already exists
        let slotExists = false;
        for (let slotInfo of user.binary_slots) {
            if (slotInfo.slot_no === slotNo) {
                slotInfo.is_active = true;
                slotInfo.activated_at = new Date();
                slotExists = true;
                break;
            }
        }

        // Add new slot if not exists
        if (!slotExists) {
            const newSlot = {
                slot_no: slotNo,
                slot_name: slotName,
                slot_value: amount,
                is_active: true,
                activated_at: new Date()
            };
            user.binary_slots.push(newSlot);
        }

        user.updated_at = new Date();
        await user.save();

    } catch (error) {
        console.error('Error updating user binary slot info:', error);
    }
}
```

### 5.4 Helper Functions
```javascript
/**
 * Gets current week ID in YYYY-WW format
 * @returns {string} Week ID
 */
function getCurrentWeekId() {
    const now = new Date();
    const year = now.getFullYear();
    const week = getWeekNumber(now);
    return `${year}-${week.toString().padStart(2, '0')}`;
}

/**
 * Gets current cycle number
 * @returns {number} Cycle number
 */
function getCurrentCycle() {
    const now = new Date();
    return parseInt(now.toISOString().slice(0, 10).replace(/-/g, ''));
}

/**
 * Ensures currency is correct for program
 * @param {string} program - Program name
 * @param {string} currency - Currency
 * @returns {string} Corrected currency
 */
function ensureCurrencyForProgram(program, currency) {
    const currencyMap = {
        'binary': 'BNB',
        'matrix': 'USDT',
        'global': 'USD'
    };
    return currencyMap[program] || currency;
}

/**
 * Calculates daily return for Leadership Stipend
 * @param {number} slotNo - Slot number
 * @returns {number} Daily return amount
 */
function calculateDailyReturn(slotNo) {
    // Double slot value as daily return
    const slotValues = {
        10: 2.2528, 11: 4.5056, 12: 9.0112, 13: 18.0224,
        14: 36.0448, 15: 72.0896, 16: 144.1792
    };
    return (slotValues[slotNo] || 0) * 2;
}

/**
 * Gets slot name from slot number
 * @param {number} slotNo - Slot number
 * @returns {string} Slot name
 */
function getSlotName(slotNo) {
    const slotNames = {
        10: 'VANGURD', 11: 'NEXUS', 12: 'QUANTUM', 13: 'PHOENIX',
        14: 'TITAN', 15: 'COSMOS', 16: 'INFINITY'
    };
    return slotNames[slotNo] || `SLOT_${slotNo}`;
}
```

---

## 6. SUMMARY

### 6.1 Main Functions Overview

1. **Binary Slot Upgrade Functions**:
   - `upgradeBinarySlot()` - Main upgrade function with all automatic processes
   - `validateBinarySlotUpgrade()` - Validation and requirements check
   - `createSlotActivation()` - Slot activation record creation

2. **Commission Calculation Functions**:
   - `calculateUpgradeCommission()` - 30% level + 70% distribution calculation
   - `distributeAcrossLevels()` - Dual tree earning distribution
   - `createCommissionRecord()` - Commission record creation

3. **Auto Upgrade System Functions**:
   - `processBinaryAutoUpgrade()` - Auto upgrade processing
   - `calculateBinaryPartnerEarnings()` - Partner earnings calculation
   - `processAutoUpgradeQueue()` - Queue processing

4. **Integration Functions**:
   - `awardJackpotFreeCoupon()` - Jackpot coupon awards
   - `checkLeadershipStipendEligibility()` - Leadership stipend checks
   - `contributeToSparkFund()` - Spark fund contributions

5. **Utility Functions**:
   - `getUplineAtLevel()` - Upline retrieval
   - `getBinarySlotCost()` - Slot cost calculation
   - `updateUserBinarySlotInfo()` - User info updates

### 6.2 Automatic Processes Triggered

When a user upgrades a Binary slot, the following automatic processes occur:

1. **Slot Upgrade Validation** - All validations are performed
2. **Fund Deduction** - Upgrade cost is deducted from wallet
3. **Slot Activation** - New slot is activated
4. **Commission Distribution** - 30% to corresponding level upline
5. **Dual Tree Earning** - 70% distributed across levels 1-16
6. **Auto Upgrade System** - First 2 partners' earnings reserved
7. **Rank Update** - User's rank is updated
8. **Jackpot Integration** - Free coupons awarded (slots 5-16)
9. **Leadership Stipend** - Eligibility checked (slots 10-16)
10. **Spark Fund** - 8% contribution to Spark bonus fund
11. **Database Operations** - All database operations completed
12. **Blockchain Logging** - All transactions logged on blockchain

**All processes are fully automated and require no manual intervention.**

---

*This documentation is part of the BitGPT platform documentation suite.*