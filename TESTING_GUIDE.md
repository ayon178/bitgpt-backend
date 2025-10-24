# 🧪 Global Program Testing Guide

## Overview
This guide helps you test the Global Program implementation step by step.

## Prerequisites
1. **Backend server running** on `http://localhost:8000`
2. **Database connected** and accessible
3. **Python environment** with required dependencies

## Test Scripts Available

### 1. **API Testing Script** (`test_global_program.py`)
- Tests Global Program through API endpoints
- Creates test users via API
- Joins Global Program via API
- Checks earnings and tree structure via API

### 2. **Manual Testing Script** (`manual_test_global.py`)
- Direct database operations
- More detailed debugging information
- Step-by-step placement verification
- Phase transition testing

### 3. **Cleanup Script** (`cleanup_test_data.py`)
- Cleans up all test data
- Removes test users and Global program data
- Resets database state

## Testing Steps

### Step 1: Start Backend Server
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Run Manual Testing (Recommended)
```bash
cd backend
python manual_test_global.py
```

### Step 3: Run API Testing (Optional)
```bash
cd backend
python test_global_program.py
```

### Step 4: Clean Up Test Data
```bash
cd backend
python cleanup_test_data.py
```

## Expected Test Results

### **Placement Logic Test:**
1. **User A** joins → Slot 1, Phase 1, Level 1, Position 1
2. **User B** joins → Slot 1, Phase 1, Level 2, Position 1 (under A)
3. **User C** joins → Slot 1, Phase 1, Level 2, Position 2 (under A)
4. **User D** joins → Slot 1, Phase 1, Level 2, Position 3 (under A)
5. **User E** joins → Slot 1, Phase 1, Level 2, Position 4 (under A)
6. **Phase 1 Full** → User A moves to Phase 2
7. **User F** joins → Slot 1, Phase 1, Level 2, Position 1 (under B)

### **Phase Transition Test:**
- **Phase 1**: Maximum 4 users
- **Phase 2**: Maximum 8 users
- **Auto Transition**: When Phase 1 is full, first user moves to Phase 2
- **Upline Change**: When users move to Phase 2, their upline changes to original Phase 1 upline

### **Slot Upgrade Test:**
- **Phase 2 Full**: When Phase 2 has 8 users, first user upgrades to next slot
- **Slot Progression**: Slot 1 → Slot 2 → Slot 3 → ... → Slot 8
- **History Tracking**: All slot and phase records maintained

## Test Scenarios

### **Scenario 1: Basic Placement**
- Test 5 users joining Global Program
- Verify correct placement under most recent eligible parent
- Check phase distribution

### **Scenario 2: Phase Transition**
- Test 10 users joining Global Program
- Verify Phase 1 → Phase 2 transitions
- Check upline reassignment

### **Scenario 3: Slot Upgrade**
- Test 20+ users joining Global Program
- Verify slot upgrades
- Check history tracking

### **Scenario 4: Fund Distribution**
- Verify fund distribution percentages
- Check all collections receiving funds
- Verify wallet ledger entries

## Debugging Tips

### **Check Database Collections:**
```python
# Check placements
placements = TreePlacement.objects(program='global', is_active=True).order_by('created_at')

# Check phase distribution
phase1_count = TreePlacement.objects(program='global', phase='PHASE-1', is_active=True).count()
phase2_count = TreePlacement.objects(program='global', phase='PHASE-2', is_active=True).count()

# Check slot distribution
for slot_no in range(1, 9):
    count = TreePlacement.objects(program='global', slot_no=slot_no, is_active=True).count()
    print(f"Slot {slot_no}: {count} users")
```

### **Check API Endpoints:**
```bash
# Get Global earnings
curl http://localhost:8000/global/earnings/slots/TEST_A

# Get Global tree
curl http://localhost:8000/global/tree/TEST_A/PHASE-1
```

## Common Issues & Solutions

### **Issue 1: Join Sequence Validation**
- **Problem**: "Join sequence violation" error
- **Solution**: Already disabled in router for testing

### **Issue 2: Phase Transition Not Working**
- **Problem**: Users not moving to Phase 2
- **Solution**: Check `_handle_phase_progression` method

### **Issue 3: Slot Upgrade Not Working**
- **Problem**: Users not upgrading slots
- **Solution**: Check `_upgrade_user_to_next_slot` method

### **Issue 4: Fund Distribution Issues**
- **Problem**: Funds not distributed correctly
- **Solution**: Check `FundDistributionService` and percentage calculations

## Test Data Cleanup

After testing, always run the cleanup script to remove test data:

```bash
python cleanup_test_data.py
```

This ensures a clean state for future tests.

## Success Criteria

✅ **Placement Logic**: Users placed under most recent eligible parent  
✅ **Phase Transitions**: Automatic Phase 1 → Phase 2 transitions  
✅ **Slot Upgrades**: Automatic slot upgrades when Phase 2 is full  
✅ **Upline Changes**: Correct upline reassignment during transitions  
✅ **History Tracking**: All slot and phase records maintained  
✅ **Fund Distribution**: Correct percentage distribution to all collections  
✅ **API Endpoints**: All endpoints working correctly  

## Next Steps

After successful testing:
1. **Re-enable join sequence validation** in router
2. **Deploy to staging environment**
3. **Run integration tests**
4. **Prepare for production deployment**
