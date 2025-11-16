"""
Cron-style script to process Newcomer Growth Support upline 50% after 30 days.

Logic:
  - Find all NewcomerSupportBonus documents with:
      bonus_type == 'upline_reserve'
      payment_status == 'pending'
      available_from <= now
  - For each:
      * credit the upline's main wallet with bonus_amount (reason='newcomer_support')
      * mark payment_status='paid', paid_at=now, processed_at=now
      * update NewcomerSupportFund statistics (optional / best-effort)

Run this script periodically (e.g. daily) via cron / scheduler:
  cd backend && python process_newcomer_upline_reserve_payouts.py
"""

from datetime import datetime
from decimal import Decimal

from core.db import connect_to_db
from modules.newcomer_support.model import NewcomerSupportBonus, NewcomerSupportFund
from modules.wallet.service import WalletService


def process_upline_reserve_payouts(batch_size: int = 500):
    """Process matured upline_reserve bonuses and credit wallets."""
    connect_to_db()

    now = datetime.utcnow()
    ws = WalletService()
    processed_count = 0
    total_amount = Decimal("0")

    # Find all eligible bonuses in batches
    q = NewcomerSupportBonus.objects(
        bonus_type="upline_reserve",
        payment_status="pending",
        available_from__lte=now,
    ).order_by("available_from")

    for bonus in q.limit(batch_size):
        try:
            user_id = str(bonus.user_id)
            amount = Decimal(str(bonus.bonus_amount or 0))
            if amount <= 0:
                # Skip zero/negative entries but mark processed to avoid re-scanning
                bonus.payment_status = "failed"
                bonus.processed_at = now
                bonus.failed_reason = "Non-positive bonus_amount"
                bonus.save()
                continue

            # Credit upline's wallet
            tx_hash = bonus.payment_reference or f"NGS-UPLINE-{user_id}-{int(now.timestamp())}"
            res = ws.credit_main_wallet(
                user_id=user_id,
                amount=amount,
                currency=bonus.currency or "USDT",
                reason="newcomer_support",
                tx_hash=tx_hash,
            )

            if not res.get("success"):
                bonus.payment_status = "failed"
                bonus.processed_at = now
                bonus.failed_reason = res.get("error", "wallet credit failed")
                bonus.save()
                continue

            # Mark as paid
            bonus.payment_status = "paid"
            bonus.payment_method = "wallet"
            bonus.payment_reference = tx_hash
            bonus.processed_at = now
            bonus.paid_at = now
            bonus.save()

            processed_count += 1
            total_amount += amount

        except Exception as e:
            bonus.payment_status = "failed"
            bonus.processed_at = now
            bonus.failed_reason = str(e)
            bonus.save()

    # Best-effort fund statistics update
    if processed_count and total_amount > 0:
        try:
            fund = NewcomerSupportFund.objects(fund_name="Newcomer Support Fund").first()
            if not fund:
                fund = NewcomerSupportFund()
            fund.available_amount = float((Decimal(str(fund.available_amount or 0)) - total_amount).max(Decimal("0")))
            fund.distributed_amount = float(Decimal(str(fund.distributed_amount or 0)) + total_amount)
            fund.total_amount_distributed = fund.distributed_amount  # backward-compat alias
            fund.total_bonuses_paid = int(fund.total_bonuses_paid or 0) + processed_count
            fund.last_updated = now
            fund.save()
        except Exception:
            # Do not fail script if statistics update fails
            pass

    print(
        f"✅ Newcomer upline_reserve payouts processed: count={processed_count}, "
        f"total={float(total_amount)}"
    )


if __name__ == "__main__":
    process_upline_reserve_payouts()


