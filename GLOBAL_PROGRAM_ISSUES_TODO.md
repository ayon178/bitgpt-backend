# Global Program Issues - TODO List

## Overview
This document tracks all identified issues in the Global program implementation that need to be fixed step by step.

---

## 🔴 Critical Issues Found

### 1. ROOT User Detection Issue
**Status**: ✅ Complete
**Description**: First user should be detected as ROOT user with `parent_id: null` in all collections
**Collections Affected**: 
- `global_tree_structure`
- `tree_placement`
- `global_team_member`

**Current Problem**:
- First user has `parent_user_id: 68bee4b9c1eac053757f5d08` (self-parenting)
- Should be `parent_user_id: null` (ROOT)

**Expected Fix**:
- Update `_place_in_phase1` method to detect ROOT users correctly
- First user should have `parent_id: null` in all collections

---

### 2. Level Calculation Issue
**Status**: ✅ Complete
**Description**: All users have `level: 3` but should be `level: 1` for ROOT, `level: 2` for children
**Collections Affected**:
- `global_tree_structure`
- `tree_placement`

**Current Problem**:
- All users have `level: 3`
- ROOT user should be `level: 1`
- Children should be `level: 2`

**Expected Fix**:
- ROOT users: `level: 1`
- Children: `level: parent_level + 1`

---

### 3. Position Calculation Issue
**Status**: ❌ Incomplete
**Description**: Multiple users have same position instead of sequential positions
**Collections Affected**:
- `global_phase_seats`
- `global_tree_structure`
- `tree_placement`

**Current Problem**:
- Multiple users have `position: "position_3"`
- Multiple users have `position: "position_4"`
- Should be sequential: `position_1`, `position_2`, `position_3`, `position_4` in phase-1
- Should be sequential: `position_1-8` in phase-2

**Expected Fix**:
- Sequential position assignment
- ROOT user: `position: "position_1"` in phase-1
- ROOT user: `position: "position_1-8"` in phase-2
- Children: `position: "position_2,3,4"` in phase-1
- Children: `position: "position_1-8"` in phase-2

---

### 4. Team Size Tracking Issue
**Status**: ❌ Incomplete
**Description**: Users are counting other users in their team size instead of just themselves
**Collections Affected**:
- `global_phase_progression`

**Current Problem**:
- First user: `phase_1_members_current: 3`, `global_team_size: 3`
- Second user: `phase_1_members_current: 2`, `global_team_size: 2`
- Should be `1` for each user (self only)

**Expected Fix**:
- Each user: `phase_1_members_current: 1`, `global_team_size: 1`
- `global_team_members: [own_user_id]` only

---

### 5. Phase Progression Issue
**Status**: ❌ Incomplete
**Description**: Phase-1 to Phase-2 automatic progression not working
**Collections Affected**:
- `global_phase_progression`

**Current Problem**:
- First user has 3 people under them but still in `PHASE-1`
- `is_phase_complete: false`, `next_phase_ready: false`
- Should automatically move to `PHASE-2` when 4 members reached

**Expected Fix**:
- When `phase_1_members_current >= 4`, automatically move to `PHASE-2`
- Set `current_phase: 'PHASE-2'`, `is_phase_complete: true`

---

### 6. BFS Placement Logic Issue
**Status**: ❌ Incomplete
**Description**: BFS algorithm not finding correct parent for placement
**Collections Affected**:
- All placement collections

**Current Problem**:
- Users are not being placed under correct parents
- ROOT user detection failing
- Position calculation incorrect

**Expected Fix**:
- Fix `_find_phase1_parent_bfs()` method
- Proper ROOT user detection
- Correct parent-child relationships

---

## 🟡 Secondary Issues

### 7. Parent-Child Relationship Issue
**Status**: ❌ Incomplete
**Description**: Incorrect parent-child relationships in tree structure
**Collections Affected**:
- `global_tree_structure`
- `tree_placement`

**Current Problem**:
- First user self-parenting
- Incorrect parent assignments

**Expected Fix**:
- ROOT user: `parent_id: null`
- Children: `parent_id: ROOT_user_id`

---

### 8. Phase Seat Management Issue
**Status**: ❌ Incomplete
**Description**: Phase seats not being managed correctly
**Collections Affected**:
- `global_phase_seats`

**Current Problem**:
- Multiple users in same position
- Seat occupancy not tracked correctly

**Expected Fix**:
- Sequential seat assignment
- Proper occupancy tracking

---

## 📋 Implementation Plan

### Phase 1: Core Fixes
1. ✅ Fix ROOT user detection
2. ✅ Fix level calculation
3. ✅ Fix position calculation
4. ✅ Fix team size tracking

### Phase 2: Phase Progression
5. ✅ Implement automatic phase progression
6. ✅ Fix BFS placement logic

### Phase 3: Data Integrity
7. ✅ Fix parent-child relationships
8. ✅ Fix phase seat management

---

## 🎯 Success Criteria

- [ ] ROOT user has `parent_id: null` in all collections
- [ ] ROOT user has `level: 1`, children have `level: 2`
- [ ] Sequential positions: `position_1`, `position_2`, `position_3`, `position_4`
- [ ] Each user counts only themselves in team size
- [ ] Automatic phase progression works (PHASE-1 → PHASE-2)
- [ ] BFS placement finds correct parents
- [ ] All parent-child relationships correct
- [ ] Phase seats managed correctly

---

## 📝 Notes

- All issues stem from incorrect BFS placement logic
- ROOT user detection is the core issue
- Phase progression logic needs to be implemented
- Team size tracking logic needs correction
- Position calculation needs sequential assignment

---

*Last Updated: 2025-09-27*
*Status: All issues identified, ready for step-by-step implementation*
