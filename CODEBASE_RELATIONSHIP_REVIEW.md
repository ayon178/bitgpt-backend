# Cross‑Module Relationship Review (per PROJECT_DOCUMENTATION.md)

Date: 2024-12-19
Scope: Models, routers, and services added in recent phases; focus on inter‑module relations and doc alignment.

## High‑Priority Issues (blocking/testing risks)

1) Binary Spillover service expects child pointers that do not exist
- Where: `modules/spillover/service.py::_find_nearest_vacancy`
- Code expects: `TreePlacement.left_child_id`, `TreePlacement.right_child_id`
- Actual model: `modules/tree/model.py::TreePlacement` does not define child pointer fields.
- Impact: Spillover BFS cannot traverse; will always fail to find vacancy.
- Fix:
  - Add fields to `TreePlacement`: `left_child_id`, `right_child_id` (ObjectIdField, indexed).
  - Ensure they are maintained on placements and updates.

2) Matrix Recycle model duplication across modules
- Where: `modules/matrix/model.py::MatrixRecycle`, `modules/tree/model.py::MatrixRecycle`, and new `modules/recycle/model.py` abstractions.
- Impact: Overlapping collections/semantics can cause confusion and data inconsistency.
- Fix:
  - Keep one authoritative recycle record (recommend `modules/matrix/model.py::MatrixRecycle`).
  - Use `modules/recycle` as orchestration (queue/settings/logs) and reference the matrix recycle id; remove duplicate `MatrixRecycle` from `tree.model`.

3) Helper methods return mock data (logic stubs)
- Where: `_check_current_status` / `_check_current_phase_status` etc. in multiple routers/services (Top Leader Gift, Phase System, etc.).
- Impact: Eligibility/upgrade/reward logic will behave incorrectly in tests.
- Fix: Implement real queries to rank, team, and program activations per documentation.

4) Missing auth guards on new routers
- Many new routers do not protect endpoints with authentication.
- Impact: Public access to sensitive operations.
- Fix: Add `Depends(authentication_service.verify_authentication)` where required.

## Medium‑Priority Issues

5) ObjectId relationships are unvalidated
- Many models store `user_id`, `parent_id`, `upline_id` as raw `ObjectIdField` without referential checks.
- Impact: Orphan records possible.
- Fix: Add service‑level validation on create/update; optionally custom `ReferenceField` where appropriate.

6) Index coverage and naming
- Several high‑volume collections lack compound indexes that match read patterns (e.g., queue status + created_at).
- Fix: Add indexes like `('status', 'created_at')` for queues; ensure `unique` where business‑wise required.

7) Currency consistency
- Matrix uses USDT, Binary uses BNB, Global uses USD. Most places align, but verify all new models honor those (e.g., recycle defaults to USDT; phase_system uses USD).
- Fix: Confirm during implementation of business methods; standardize constants.

8) Router prefixes/tags consistency
- New routers rely on internal prefixes; ensure they don’t conflict and are documented.
- Fix: Confirm API docs show expected paths per PROJECT_DOCUMENTATION.md.

## Low‑Priority / Refactoring

9) Settings consolidation
- Multiple settings documents per module; consider a central configuration service with caching.

10) Logs and statistics schema alignment
- Good coverage, but field names vary; harmonize key names for analytics.

## Specific Module Notes

- Spillover (Binary):
  - BFS relies on binary child pointers (see Issue #1). After adding pointers, ensure `TreePlacement.children_count` stays consistent.

- Phase System (Global):
  - Align level names/values with doc tables if used in UI; logic flow matches (4 → 8, alternation).

- Top Leader Gift / President Reward / Royal Captain:
  - Eligibility and counts require integration with rank and team services; currently stubs.

- Missed Profit → Leadership Stipend:
  - Flow modeled; distribution recipients resolution is stubbed and must consult stipend eligibility.

- Recycle (Matrix):
  - Use `modules/recycle` for orchestration and keep only one `MatrixRecycle` data model.

## Actionable Fix List

A) TreePlacement child pointers (Required now)
- Add to `modules/tree/model.py::TreePlacement`:
  - `left_child_id = ObjectIdField()`
  - `right_child_id = ObjectIdField()`
  - Add indexes for quick lookup.

B) Remove duplicate MatrixRecycle definition in `modules/tree/model.py`
- Keep `MatrixRecycle` in `modules/matrix/model.py` (or pick one) and refactor usages.

C) Replace mock status helpers with real implementations
- Implement team size, rank fetch, and program activations queries per documentation.


D) Add compound indexes to queues
- RecycleQueue/SpilloverQueue: `('status','created_at')`.

E) Validate ObjectId relationships in services
- Ensure user/parent existence before writes.

---

