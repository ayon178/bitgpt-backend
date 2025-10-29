Title: Binary Reserve Routing and Auto-Upgrade Specification

Overview
- Scope: Defines how Binary slot funds (slots 2–17) are routed to tree uplines’ reserve for auto-upgrade, or distributed to global pools when special routing conditions are not met.
- Slot 1: Already implemented. 100% to direct upline wallet; no pools distribution; no partner split.
- Slot 2–17: Special reserve routing first; otherwise fall back to binary distributions:
  - Spark 8%, Royal Captain 4%, President 3%, Leadership Stipend 5%, Jackpot 5%, Partner Incentive 10%, Shareholders 5%, Level Distribution 60% (Dual-tree: L1 30, L2 10, L3 10, L4–10 5, L11–13 3, L14–16 2).

Key Definitions
- Tree Upline for Slot N: The ancestor in the Binary slot-N tree considered as uplines by depth; in practice we derive “Nth upline” as: parent at each hop from the user’s placement node (slot tree specific).
- First/Second position requirement: For a slot-N payment to be routed to an upline’s reserve, the downline user must appear on that upline’s slot-N tree as either their 1st or 2nd level user at the time of the transaction. If this positional rule is not satisfied, we do not use reserve routing.
- Reserve Ledger: `ReserveLedger(user_id, program='binary', slot_no=target_slot, amount, direction='credit', source='tree_upline_reserve', tx_hash)`.
- Mother Account: When a qualified tree upline exists but hasn’t activated the target slot yet and special rule does not hold (not first/second), we route per binary distributions (no mother catch here). If a tree upline is absent (edge), deposit to mother.

Routing Rules (Join and Upgrades)
1) Slot 1 (Explorer): 100% to direct upline main wallet. DONE.

2) Slot 2 (Contributor) on join:
   - Identify 2nd upline (Alice in the example where Ada/Kimmy -> Carol -> Alice).
   - If the joining user is counted as first or second user under Alice in the slot-2 tree, route 100% of Slot-2 value to Alice’s reserve for next-slot (slot 3) auto-upgrade.
   - Else, distribute whole Slot-2 value via Binary distributions (Spark, Royal, President, Leadership, Jackpot, Partner 10%, Shareholders 5%, Level 60%).

3) Slot N upgrade (N >= 3):
   - Identify Nth upline.
   - If the upgrading user is counted as the first or second user under that Nth upline in slot-N tree, route 100% of the slot-N value to that Nth upline’s reserve for their next slot (N+1) auto-upgrade.
   - Else, distribute entire slot-N value via Binary distributions (Spark… Level 60%).

Auto-Upgrade Trigger
- After any reserve credit for target slot T, evaluate accumulated reserve for that user and slot T.
- If reserve >= cost(T):
  - Activate target slot T for that upline automatically (AutoUpgradeService).
  - Record upgrade log and reserve debits accordingly (future enhancement: explicit debit entries).
  - Chain upgrades: If upgraded to T, re-evaluate reserve for T+1 only when subsequent events add more reserve.

Example Walkthroughs
- Ada join under Carol (Alice is 2nd upline):
  - Slot 1: 100% to Carol’s wallet (0.0022 BNB).
  - Slot 2: If Ada is first/second in Alice’s slot-2 tree → 100% to Alice’s reserve for slot 3; else distribute via pools list above.

- Kimmy join under Carol (same chain):
  - Slot 1: 100% to Carol’s wallet.
  - Slot 2: Same rule as Ada relative to Alice’s slot-2 tree.

- Shaun upgrade slot 2 under Dave (Alice as 3rd upline):
  - Alice is the 3rd upline for Shaun; however, for slot 2, rule checks the 2nd upline. Since Shaun isn’t first/second under the relevant upline for slot 2 (per example), slot-2 value does NOT go to Alice’s reserve; it is distributed via pools.
  - For Shaun’s future slot 3 upgrade, check the 3rd upline and first/second requirement again; if satisfied, route to that upline’s reserve for slot 4, otherwise distribute via pools.

Edge Cases & Fallbacks
- If positional data cannot be resolved (missing placements):
  - Treat as special condition not met → distribute via Binary pools.
- If calculated upline is missing (corrupted/edge):
  - Credit mother account as safety.
- Eligibility gates on level distribution remain enforced (users without required level or 2 partners miss level distribution; missed routed to stipend as already implemented).

Wallet Reasons & Tx Hash Conventions
- Slot-1: `binary_slot1_full` (already used), tx: `auto_slot_1_<user_id>_<ts>`
- Reserve credit: `binary_reserve_route_slot_<N>_to_slot_<N+1>` (ReserveLedger only; no wallet credit until upgrade).
- Pools distributions: per existing income ledger mapping.
- Partner incentive for slot 2+: remains 10% in pools branch; none when 100% reserve routing applies.

Data Model Hooks
- TreePlacement: Must be queried per program+slot to compute ancestor per depth and to determine first/second qualification.
- ReserveLedger: Use `slot_no=target_slot_no` where target_slot_no = current_slot_no + 1 for the upline.
- SlotActivation: Auto-activate target slot on reserve sufficiency.

Implementation Plan (Step-by-step)
1. Add a helper to compute Nth upline for a given user and slot tree.
2. Add a helper to test “first-or-second child” condition under the computed upline for the given slot.
3. Update AutoUpgradeService `_process_slot_2plus_activation` to:
   - Compute Nth upline and positional test.
   - If satisfied: write ReserveLedger credit for upline with target slot N+1; evaluate auto-upgrade.
   - Else: call FundDistributionService.distribute_binary_funds for full amount (which will do pools + level distribution per Binary percentages).
4. Ensure FundDistributionService skips slot 1 (already added) and handles Binary pools correctly for N>=2.
5. Add tests:
   - A) Ada/Kimmy: Alice reserve gets Slot-2 when first/second; else pools.
   - B) Shaun: demonstrate no reserve to Alice for Slot-2 when not first/second; then for Slot-3 check relevant upline.
   - C) Auto-upgrade triggers when reserve >= next slot cost; verify slot activation and logs.

Notes
- This spec aligns with user narrative: funds route to tree uplines’ reserve only when the joining/upgrading user is within the first/second position for the specific slot tree of the designated Nth upline; otherwise the entire amount is distributed to global pools according to Binary percentages and dual-tree level breakdown.


