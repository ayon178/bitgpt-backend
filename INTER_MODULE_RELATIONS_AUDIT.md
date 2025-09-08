# Inter-Module Relations Audit (Backend)

Date: 2025-09-08

Scope: Reviewed core models and services to verify cross-module relations against `PROJECT_DOCUMENTATION.md` and `data_structure.md`.

## Findings

- User upline field naming mismatch
  - Documentation: `upline_id` (`data_structure.md`)
  - Implementation: `User.refered_by` (`modules/user/model.py`)
  - Impact: Inconsistent field naming across docs vs code may cause confusion in APIs/services expecting `upline_id`.
  - Suggested fix: Standardize on `upline_id` in the code (alias or rename), or document mapping clearly at API boundaries.

- Broken/invalid import in `modules/tree/__init__.py`
  - Current: `from .model import TreePlacement, AutoUpgradeLog`
  - Reality: `AutoUpgradeLog` is centralized under `modules/auto_upgrade/model.py` (per notes in `modules/tree/model.py`).
  - Impact: ImportError at startup for tree module.
  - Suggested fix: Remove `AutoUpgradeLog` from `modules/tree/__init__.py` import, or re-export from `modules/auto_upgrade` explicitly if needed.

- Incomplete/broken import in `backend/main.py` for global module
  - Lines around router/model imports show:
    - `_global_module =` (incomplete assignment)
    - `GlobalPhaseState = getattr(_global_module, 'GlobalPhaseState')`
  - `modules/global/model.py` is effectively empty (no models defined).
  - Impact: Runtime error on application startup due to invalid code and missing models.
  - Suggested fix: Implement required Global models (e.g., `GlobalPhaseState`) in `modules/global/model.py` and correct the import code in `main.py`; or remove until implemented.

- Global program model gap
  - Documentation references Global Phase System and levels; services like `PhaseSystemService` use their own `modules/phase_system/model.py`, which is fine.
  - However, `modules/global/model.py` is empty while `main.py` expects models.
  - Impact: Inconsistent module boundary; potential duplication/confusion between `global` and `phase_system` domains.
  - Suggested fix: Either (a) consolidate global-phase data under `modules/phase_system` and stop importing `modules/global` in `main.py`, or (b) implement `modules/global/model.py` and make `phase_system` depend on it.

- Tree service partial implementations
  - `modules/tree/service.py` references helpers like `_calculate_level` and spillover handling; router file shows an incomplete endpoint implementation stub.
  - Impact: Interactions from User creation → Tree placement may be blocked.
  - Suggested fix: Complete `TreeService` helper methods and `router.py` endpoint bodies to align with `TREE_API_DOCUMENTATION.md`.

- Wallet currency defaults vs program currencies
  - `UserWallet.currency` defaults to `USDT` while Binary uses `BNB` and Global uses `USD`.
  - Impact: Not a bug, but ensure services set appropriate currency per `wallet_type`/program when crediting/debiting.
  - Suggested fix: Validate currency at service layer when creating/updating wallet/ledger entries.

- Consistency of program enums and positions
  - `TreePlacement.program` uses `['binary', 'matrix', 'global']` matching docs.
  - Position handling comments cover Matrix center and Global phase-specific positions; OK.
  - No action needed.

## Recommended Edits (summary)

1) Align upline field naming
   - Option A: Rename `User.refered_by` → `upline_id` and add migration.
   - Option B: Keep field, but update API docs and DTOs to map `upline_id -> refered_by` consistently.

2) Fix tree module import
   - Edit `modules/tree/__init__.py` to only export `TreePlacement` (or re-export `AutoUpgradeLog` from `modules/auto_upgrade` if required explicitly).

3) Fix `main.py` global imports
   - Remove the broken `_global_module` lines and any `GlobalPhaseState` import until models exist; or implement the models in `modules/global/model.py`.

4) Complete Tree service/router stubs
   - Implement missing private helpers (e.g., `_calculate_level`, `_handle_indirect_referral_placement`) and finish router endpoint bodies to enable placement flows.

5) Enforce currency correctness in wallet/ledger services
   - Validate and set currency based on the program at the time of ledger creation.

## Cross-Module Reference Matrix (key ones)

- user → tree: `TreePlacement.user_id`, `parent_id` reference `User`
- slot → user/tree: `SlotActivation.user_id` references `User`; program/slot consistent with tree placements
- commission → user/slot: `Commission.user_id`/`from_user_id` (User), `source_transaction_id` (activation/upgrade)
- wallet → user: `UserWallet.user_id` and ledgers reference `User`

No circular hard dependencies detected at model level (MongoEngine ObjectId references only).

---

If you want, I can apply the targeted edits above (safe changes: tree __init__ import fix, remove broken lines in main.py; larger changes: rename `refered_by`).


