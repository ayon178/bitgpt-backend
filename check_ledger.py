import sys
sys.path.insert(0, ".")

from modules.wallet.model import WalletLedger
from bson import ObjectId

USER_ID = "69018a522791b8ae0143c6d6"

ledger_entries = WalletLedger.objects(user_id=ObjectId(USER_ID), type="credit").order_by("-created_at")

print(f"\n=== WalletLedger Entries for USER_A ===")
print(f"Total credits: {ledger_entries.count()}\n")

grouped = {}
for entry in ledger_entries:
    reason = entry.reason
    amount = float(entry.amount)
    currency = entry.currency
    
    if reason not in grouped:
        grouped[reason] = {"USDT": 0.0, "BNB": 0.0}
    
    grouped[reason][currency] += amount

print("Grouped by reason:")
print("-" * 80)
for reason, amounts in sorted(grouped.items()):
    total_usdt = amounts.get('USDT', 0)
    total_bnb = amounts.get('BNB', 0)
    if total_usdt > 0 or total_bnb > 0:
        print(f"{reason:50s} USDT: {total_usdt:10.2f}  BNB: {total_bnb:10.2f}")

print("\n" + "=" * 80)
print("Analysis:")
print("=" * 80)

# Check for level distributions
matrix_dual_tree = [k for k in grouped.keys() if 'matrix_dual_tree' in k.lower()]
if matrix_dual_tree:
    print(f"\n✅ Found matrix_dual_tree entries: {matrix_dual_tree}")
    for reason in matrix_dual_tree:
        print(f"   {reason}: USDT {grouped[reason]['USDT']:.2f}")
else:
    print("\n❌ NO matrix_dual_tree entries found")

# Matrix partner incentive
matrix_pi = grouped.get('matrix_partner_incentive', {})
print(f"\nmatrix_partner_incentive: USDT {matrix_pi.get('USDT', 0):.2f}")

# Newcomer
ngs = [k for k in grouped.keys() if 'newcomer' in k.lower() or 'ngs' in k.lower()]
if ngs:
    print(f"\nNewcomer entries: {ngs}")
    for reason in ngs:
        print(f"   {reason}: USDT {grouped[reason]['USDT']:.2f}")

# Mentorship
mentorship = [k for k in grouped.keys() if 'mentorship' in k.lower()]
if mentorship:
    print(f"\nMentorship entries: {mentorship}")
    for reason in mentorship:
        print(f"   {reason}: USDT {grouped[reason]['USDT']:.2f}")

