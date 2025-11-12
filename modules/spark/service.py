from typing import Dict, Any, List, Optional
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from .model import TripleEntryReward, SparkCycle, SparkBonusDistribution, TripleEntryPayment
from ..user.model import User
import os

SPARK_SLOT_INFO: List[tuple[int, str, Decimal]] = [
    (1, "Starter", Decimal('15')),
    (2, "Bronze", Decimal('10')),
    (3, "Silver", Decimal('10')),
    (4, "Gold", Decimal('10')),
    (5, "Platinum", Decimal('10')),
    (6, "Diamond", Decimal('7')),
    (7, "Ruby", Decimal('6')),
    (8, "Emerald", Decimal('6')),
    (9, "Sapphire", Decimal('6')),
    (10, "Topaz", Decimal('4')),
    (11, "Pearl", Decimal('4')),
    (12, "Amethyst", Decimal('4')),
    (13, "Obsidian", Decimal('4')),
    (14, "Titanium", Decimal('2')),
    (15, "Star", Decimal('2')),
]

SPARK_SLOT_NAMES = {slot: name for slot, name, _ in SPARK_SLOT_INFO}
SPARK_SLOT_PERCENTAGES = {slot: pct for slot, _, pct in SPARK_SLOT_INFO}
SPARK_SLOT_NUMBERS = [slot for slot, _, _ in SPARK_SLOT_INFO]


class SparkService:
    """Business logic for Spark/Triple Entry Reward"""

    @staticmethod
    def _slot_name(slot_no: int) -> str:
        return SPARK_SLOT_NAMES.get(slot_no, f"Slot {slot_no}")

    @staticmethod
    def compute_triple_entry_eligibles(target_date: datetime) -> Dict[str, Any]:
        """Find users who joined all three programs (binary, matrix, global) on the same calendar day.
        Assumption: We infer join by checking the first active slot activation timestamps embedded in user.
        Fallback: use User.created_at for baseline if slot timestamps are missing.
        """
        try:
            # Normalize to date boundaries UTC
            day_start = datetime(target_date.year, target_date.month, target_date.day)
            day_end = day_start + timedelta(days=1)

            # Query users who have joined flags set for all three programs
            users = User.objects(
                binary_joined=True,
                matrix_joined=True,
                global_joined=True,
                created_at__gte=day_start,
                created_at__lt=day_end
            ).only('id')

            eligible_ids: List[ObjectId] = [u.id for u in users]

            # Create/update a TER record for that cycle (use yyyymmdd as cycle_no)
            cycle_no = int(target_date.strftime('%Y%m%d'))
            ter = TripleEntryReward.objects(cycle_no=cycle_no).first()
            if not ter:
                ter = TripleEntryReward(
                    cycle_no=cycle_no,
                    pool_amount=0,
                    eligible_users=[],
                    distribution_amount=0,
                    status='active'
                )
            ter.eligible_users = eligible_ids
            ter.save()

            return {
                "success": True,
                "cycle_no": cycle_no,
                "eligible_user_count": len(eligible_ids),
                "eligible_users": [str(_id) for _id in eligible_ids]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _record_triple_entry_share(self, program: str, amount: Decimal) -> None:
        """Persist triple entry contribution into dedicated BonusFund buckets."""
        if amount <= 0:
            return
        from modules.income.bonus_fund import BonusFund

        triple_entry_fund = BonusFund.objects(
            fund_type='triple_entry',
            program=program,
            status='active'
        ).first()

        if not triple_entry_fund:
            triple_entry_fund = BonusFund(
                fund_type='triple_entry',
                program=program,
                total_collected=Decimal('0'),
                total_distributed=Decimal('0'),
                current_balance=Decimal('0'),
                status='active'
            )

        triple_entry_fund.total_collected += amount
        triple_entry_fund.current_balance += amount
        triple_entry_fund.updated_at = datetime.utcnow()
        triple_entry_fund.save()

    def contribute_to_spark_fund(self, amount: Decimal, program: str, slot_number: int = None, user_id: str = None, currency: str | None = None) -> Dict[str, Any]:
        """
        Contribute 8% of activation amount to Spark Bonus fund
        Called when Binary or Matrix slot is activated
        
        Per PROJECT_DOCUMENTATION.md Section 22:
        - Binary activations contribute 8% to Spark Bonus
        - Matrix activations contribute 8% to Spark Bonus
        """
        try:
            from modules.income.bonus_fund import BonusFund
            
            # Validate program
            if program not in ['binary', 'matrix']:
                return {"success": False, "error": "Invalid program. Must be 'binary' or 'matrix'"}
            
            # Calculate 8% contribution and split into (18% TER, 2% TLG, 80% spark distribution)
            spark_contribution = (amount * Decimal('0.08')).quantize(Decimal('0.00000001'))
            triple_entry_share = (spark_contribution * Decimal('0.18')).quantize(Decimal('0.00000001'))
            top_leader_share = (spark_contribution * Decimal('0.02')).quantize(Decimal('0.00000001'))
            spark_distribution_share = spark_contribution - triple_entry_share - top_leader_share
            
            # Get or create BonusFund for this program
            spark_fund = BonusFund.objects(
                fund_type='spark_bonus',
                program=program,
                status='active'
            ).first()
            
            if not spark_fund:
                # Create new fund if doesn't exist
                spark_fund = BonusFund(
                    fund_type='spark_bonus',
                    program=program,
                    total_collected=Decimal('0'),
                    total_distributed=Decimal('0'),
                    current_balance=Decimal('0'),
                    status='active'
                )
            
            # Update fund balances
            spark_fund.total_collected += spark_contribution
            spark_fund.current_balance += spark_distribution_share
            spark_fund.total_distributed = (spark_fund.total_distributed or Decimal('0')) + triple_entry_share + top_leader_share
            spark_fund.updated_at = datetime.utcnow()
            spark_fund.save()

            # Record triple entry contribution (per program => currency)
            self._record_triple_entry_share(program, triple_entry_share)

            # Allocate 2% to Top Leaders Gift fund
            try:
                from modules.top_leader_gift.payment_model import TopLeadersGiftFund
                tl_fund = TopLeadersGiftFund.objects(is_active=True).first()
                if not tl_fund:
                    tl_fund = TopLeadersGiftFund()

                # Determine currency bucket
                currency_value = (currency or ('BNB' if program == 'binary' else 'USDT')).upper()
                share_float = float(top_leader_share)
                if currency_value == 'BNB':
                    tl_fund.total_fund_bnb += share_float
                    tl_fund.available_bnb += share_float
                else:
                    tl_fund.total_fund_usdt += share_float
                    tl_fund.available_usdt += share_float

                tl_fund.last_updated = datetime.utcnow()
                tl_fund.save()
            except Exception as e:
                print(f"[SPARK] Failed to allocate Top Leaders Gift share: {e}")
            
            return {
                "success": True,
                "program": program,
                "slot_number": slot_number,
                "activation_amount": float(amount),
                "spark_contribution_8_percent": float(spark_contribution),
                "spark_distribution_share": float(spark_distribution_share),
                "triple_entry_share": float(triple_entry_share),
                "top_leaders_gift_share": float(top_leader_share),
                "spark_bonus_net": float(spark_distribution_share),
                "new_balance": float(spark_fund.current_balance),
                "message": f"Contributed ${float(spark_contribution)} (8%) to {program} Spark Bonus fund"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def contribute_to_fund(self, amount: float, source: str = "matrix", metadata: Dict[str, Any] | None = None, program: str | None = None, **kwargs) -> Dict[str, Any]:
        """Record contribution to Spark fund and distribute to Triple Entry (18%) and Top Leaders Gift (2%).
        Matrix distribution gets remaining 80%.
        """
        try:
            contributed = Decimal(str(amount or 0))
            program_value = (program or source or "").lower()
            currency = kwargs.get("currency")

            spark_details: Dict[str, Any] | None = None
            triple_entry_contribution = 0.0
            spark_distribution_amount = 0.0

            if program_value in ("binary", "matrix"):
                spark_details = self.contribute_to_spark_fund(
                    amount=contributed,
                    program=program_value,
                    slot_number=kwargs.get("source_slot_no"),
                    user_id=kwargs.get("source_user_id"),
                    currency=currency,
                )
            elif program_value == "global":
                # Entire contribution feeds Triple Entry (5% from Global program)
                self._record_triple_entry_share(program_value, contributed)
                spark_details = {
                    "success": True,
                    "program": program_value,
                    "triple_entry_share": float(contributed),
                    "spark_distribution_share": 0.0,
                    "top_leaders_gift_share": 0.0,
                    "message": f"Contributed ${float(contributed)} to Triple Entry fund from global program",
                }
            elif contributed > 0:
                try:
                    from modules.income.bonus_fund import BonusFund

                    spark_fund = BonusFund.objects(
                        fund_type="spark_bonus",
                        program=program_value if program_value in ("binary", "matrix") else "matrix",
                        status="active",
                    ).first()
                    if not spark_fund:
                        spark_fund = BonusFund(
                            fund_type="spark_bonus",
                            program=program_value if program_value in ("binary", "matrix") else "matrix",
                            total_collected=Decimal("0"),
                            total_distributed=Decimal("0"),
                            current_balance=Decimal("0"),
                            status="active",
                        )

                    spark_fund.total_collected += contributed
                    spark_fund.current_balance += contributed
                    spark_fund.updated_at = datetime.utcnow()
                    spark_fund.save()

                    spark_details = {
                        "success": True,
                        "program": spark_fund.program,
                        "spark_distribution_share": float(contributed),
                        "top_leaders_gift_share": 0.0,
                        "triple_entry_share": 0.0,
                        "message": f"Contributed ${float(contributed)} to Spark Bonus fund",
                    }
                except Exception as e:
                    print(f"[SPARK] Failed to update BonusFund for generic contribution: {e}")

            top_leaders_contribution = 0.0
            if spark_details:
                top_leaders_contribution = float(spark_details.get("top_leaders_gift_share", 0.0) or 0.0)
                triple_entry_contribution = float(spark_details.get("triple_entry_share", 0.0) or 0.0)
                spark_distribution_amount = float(spark_details.get("spark_distribution_share", spark_details.get("spark_bonus_net", 0.0) or 0.0))

            return {
                "success": True,
                "contributed": float(contributed),
                "top_leaders_gift_contribution": top_leaders_contribution,
                "triple_entry_contribution": triple_entry_contribution,
                "remaining_for_distribution": spark_distribution_amount,
                "source": source,
                "program": program or source,
                "metadata": metadata or {},
                "extra": {k: v for k, v in (kwargs or {}).items()},
                "spark_details": spark_details,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------ Fund Info & Slot Breakdown ------------------
    def get_spark_bonus_fund_info(self) -> Dict[str, Any]:
        """
        Return Spark Bonus fund totals - DYNAMIC calculation
        Fund Sources (PROJECT_DOCUMENTATION.md):
        - 8% from Binary slot activations
        - 8% from Matrix slot activations
        
        Calculates actual accumulated fund from database transactions
        """
        try:
            from modules.income.bonus_fund import BonusFund
            
            # Get Spark Bonus funds from database (collected from activations)
            spark_binary = BonusFund.objects(
                fund_type='spark_bonus',
                program='binary',
                status='active'
            ).first()
            
            spark_matrix = BonusFund.objects(
                fund_type='spark_bonus',
                program='matrix',
                status='active'
            ).first()
            
            # Calculate total available fund
            binary_balance = float(spark_binary.current_balance) if spark_binary else 0.0
            matrix_balance = float(spark_matrix.current_balance) if spark_matrix else 0.0
            total_fund = binary_balance + matrix_balance
            
            return {
                "success": True,
                "currency": "USDT",
                "total_fund_amount": total_fund,
                "available_amount": total_fund,
                "sources": {
                    "binary_8_percent": binary_balance,
                    "matrix_8_percent": matrix_balance
                },
                "is_dynamic": True,
                "updated_at": datetime.utcnow(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_slot_breakdown(self, currency: str = "USDT", user_id: str | None = None, slot_number: int | None = None) -> Dict[str, Any]:
        """Compute slot-wise Spark fund breakdown for UI display.
        - Uses the Spark distribution pool (80% of contributions) as baseline
        - Distributes across slots 1-15 by documented percentages
        - Returns both per-slot allocation and summary totals
        - Always returns BOTH currencies (USDT and BNB) in a "funds" object
        """
        info = self.get_spark_bonus_fund_info()
        if not info.get("success"):
            return {"success": False, "error": info.get("error", "Fund info not available")}

        total_usdt = Decimal(str(info.get("available_amount", 0)))
        baseline_usdt = total_usdt

        slots_usdt: List[Dict[str, Any]] = []
        total_allocated = Decimal('0')
        slot_range = range(1, 16) if slot_number is None else [int(slot_number)]

        # Determine user's eligible matrix slots (1-15) based on completed activations
        eligible_slots: List[int] = []
        if user_id:
            try:
                from modules.slot.model import SlotActivation  # lazy import
                from modules.matrix.model import MatrixActivation as _MA
                slots_a = [
                    int(sa.slot_no) for sa in SlotActivation.objects(
                        user_id=ObjectId(user_id),
                        program='matrix',
                        status='completed',
                        slot_no__gte=1,
                        slot_no__lte=15
                    ).only('slot_no')
                ]
                slots_b = [
                    int(ma.slot_no) for ma in _MA.objects(
                        user_id=ObjectId(user_id)
                    ).only('slot_no')
                ]
                eligible_slots = sorted(list(set(slots_a + slots_b)))
            except Exception:
                eligible_slots = []
        for slot_no in slot_range:
            pct = self._slot_percentage(slot_no)
            alloc = (baseline_usdt * pct / Decimal('100')) if pct > 0 else Decimal('0')
            total_allocated += alloc
            slots_usdt.append({
                "slot_number": slot_no,
                "percentage": float(pct),
                "allocated_amount": float(alloc),  # USDT value
                "slot_name": self._slot_name(slot_no),
                "user_eligible": (slot_no in eligible_slots) if user_id else None,
            })

        # Eligibility: Triple Entry for this user (joined all three)
        is_user_eligible = False
        if user_id:
            try:
                u = User.objects(id=ObjectId(user_id)).first()
                is_user_eligible = bool(u and u.binary_joined and u.matrix_joined and u.global_joined)
            except Exception:
                is_user_eligible = False

        # Build BOTH currencies views
        try:
            rate = Decimal(os.getenv('SPARK_USDT_PER_BNB', '300'))
            if rate <= 0:
                rate = Decimal('300')
        except Exception:
            rate = Decimal('300')

        def usdt_to_bnb(val: Decimal | float) -> float:
            d = Decimal(str(val))
            return float((d / rate).quantize(Decimal('0.00000001')))

        # Build a unified slots array with both currencies per slot, showing per-user claimable amounts
        slots_combined: List[Dict[str, Any]] = []
        
        # Get today's start for claim check
        from datetime import datetime as _DT
        day_start = _DT.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for s in slots_usdt:
            slot_no = s["slot_number"]
            total_usdt_alloc = s["allocated_amount"]
            total_bnb_alloc = usdt_to_bnb(total_usdt_alloc)
            
            # Calculate per-user claimable amount
            claimable_usdt = 0.0
            claimable_bnb = 0.0
            
            # Only calculate if user is provided and eligible for this slot
            if user_id and s.get("user_eligible"):
                # Check if user already claimed today for this slot (either currency)
                already_claimed = False
                try:
                    from modules.spark.model import SparkBonusDistribution as _SBD
                    dup = _SBD.objects(
                        user_id=ObjectId(user_id),
                        slot_number=slot_no,
                        created_at__gte=day_start
                    ).first()
                    if dup:
                        already_claimed = True
                except Exception:
                    pass
                
                if not already_claimed:
                    # Get eligible users count for this slot
                    eligible_users = self.get_slot_eligible_user_ids(slot_no)
                    eligible_count = len(eligible_users)
                    
                    if eligible_count > 0:
                        # Calculate per-user share
                        claimable_usdt = float(Decimal(str(total_usdt_alloc)) / Decimal(str(eligible_count)))
                        claimable_bnb = float(Decimal(str(total_bnb_alloc)) / Decimal(str(eligible_count)))
            
            slots_combined.append({
                "slot_number": slot_no,
                "slot_name": self._slot_name(slot_no),
                "percentage": s["percentage"],
                "slot_reserve_usdt": float(total_usdt_alloc),
                "slot_reserve_bnb": float(total_bnb_alloc),
                "allocated_amount_usdt": claimable_usdt,  # per-user claimable amount
                "allocated_amount_bnb": claimable_bnb,    # per-user claimable amount
                "user_eligible": s.get("user_eligible"),
            })

        funds = {
            "USDT": {
                "total_fund_amount": float(total_usdt),
                "baseline_amount": float(baseline_usdt),
                "total_allocated": float(total_allocated),
                "unallocated": float(max(Decimal('0'), baseline_usdt - total_allocated)),
            },
            "BNB": {
                "total_fund_amount": usdt_to_bnb(total_usdt),
                "baseline_amount": usdt_to_bnb(baseline_usdt),
                "total_allocated": usdt_to_bnb(total_allocated),
                "unallocated": usdt_to_bnb(max(Decimal('0'), baseline_usdt - total_allocated)),
            }
        }

        # Get total global Spark Bonus fund amounts from BonusFund (separate USDT and BNB)
        total_global_usdt = 0.0
        total_global_bnb = 0.0
        try:
            from modules.income.bonus_fund import BonusFund
            # Get USDT fund (from matrix program)
            usdt_fund = BonusFund.objects(fund_type='spark_bonus', program='matrix').first()
            if usdt_fund:
                total_global_usdt = float(usdt_fund.current_balance or 0.0)
            
            # Get BNB fund (from binary program)
            bnb_fund = BonusFund.objects(fund_type='spark_bonus', program='binary').first()
            if bnb_fund:
                total_global_bnb = float(bnb_fund.current_balance or 0.0)
        except Exception as e:
            print(f"Error fetching spark bonus global funds: {e}")
        
        # Add global totals to each slot (since we don't track per-slot, use global totals)
        slots_with_global = []
        for slot in slots_combined:
            slot_with_global = slot.copy()
            slot_with_global["total_global_usdt"] = total_global_usdt  # Global total for reference
            slot_with_global["total_global_bnb"] = total_global_bnb    # Global total for reference
            slots_with_global.append(slot_with_global)
        
        return {
            "success": True,
            "funds": funds,
            "slots": slots_with_global,  # Now includes global totals per slot
            "user": {
                "user_id": user_id,
                "is_triple_entry_eligible": is_user_eligible,
                "eligible_slots": eligible_slots
            } if user_id else None,
            # Backward-compat single-currency view (defaults to requested or USDT)
            "currency": (currency or "USDT").upper(),
            "total_fund_amount": funds.get((currency or "USDT").upper(), {}).get("total_fund_amount"),
            "baseline_amount": funds.get((currency or "USDT").upper(), {}).get("baseline_amount"),
            "total_allocated": funds.get((currency or "USDT").upper(), {}).get("total_allocated"),
            "unallocated": funds.get((currency or "USDT").upper(), {}).get("unallocated"),
            # Global totals (outside slots = global total)
            "total_global_usdt": total_global_usdt,  # Total Spark Bonus fund in USDT
            "total_global_bnb": total_global_bnb,    # Total Spark Bonus fund in BNB
        }

    # ------------------ Claim Processing ------------------
    def get_slot_eligible_user_ids(self, slot_no: int) -> List[str]:
        """Return user ids eligible for Spark Bonus for a given Matrix slot.
        Eligibility = any of:
          - SlotActivation(program='matrix', slot_no, status='completed')
          - MatrixActivation(slot_no)
        """
        try:
            from modules.slot.model import SlotActivation
            from modules.matrix.model import MatrixActivation as _MA
            from bson import ObjectId
            ids1 = [str(a.user_id) for a in SlotActivation.objects(program='matrix', slot_no=slot_no, status='completed').only('user_id')]
            ids2 = [str(a.user_id) for a in _MA.objects(slot_no=slot_no).only('user_id')]
            return sorted(list(set(ids1 + ids2)))
        except Exception:
            return []

    def claim_spark_bonus(self, slot_no: int, currency: str = 'USDT', claimer_user_id: str | None = None) -> Dict[str, Any]:
        """Distribute the allocated fund for a slot equally among eligible users and credit wallets.
        - currency: 'USDT' or 'BNB'
        - uses current slot breakdown to get allocated amount per slot
        """
        try:
            currency = (currency or 'USDT').upper()
            if currency not in ('USDT', 'BNB'):
                return {"success": False, "error": "Invalid currency"}

            # Get allocated amount for this slot (exact, not per-day fraction)
            br = self.get_slot_breakdown('USDT')  # baseline in USDT
            slots = br.get('slots', [])
            alloc_usdt = 0.0
            for s in slots:
                if int(s.get('slot_number')) == int(slot_no):
                    alloc_usdt = float(s.get('allocated_amount_usdt') or 0.0)
                    break
            if alloc_usdt <= 0:
                return {"success": False, "error": "No allocated fund for this slot"}

            # Get eligible users
            user_ids = self.get_slot_eligible_user_ids(slot_no)
            if not user_ids:
                return {"success": False, "error": "No eligible users for this slot"}

            # If claimer is provided, enforce they are eligible
            if claimer_user_id and claimer_user_id not in user_ids:
                return {"success": False, "error": "Claimer is not eligible for this slot"}

            # Rolling 30-day claim limit: maximum 2 claims per slot per currency
            # সর্বোচ্চ ৩০ দিনের মধ্যে ২ বার করে claim (per currency per slot)
            try:
                from datetime import datetime as _DT, timedelta as _TD
                from modules.spark.model import SparkBonusDistribution as _SBD
                if claimer_user_id:
                    now = _DT.utcnow()
                    window_start = now - _TD(days=30)

                    recent_claims = list(_SBD.objects(
                        user_id=ObjectId(claimer_user_id), 
                        slot_number=slot_no, 
                        currency=currency, 
                        created_at__gte=window_start
                    ).order_by('-created_at'))

                    if len(recent_claims) >= 2:
                        oldest_claim = recent_claims[-1]
                        next_claim_date = oldest_claim.created_at + _TD(days=30)
                        return {
                            "success": False, 
                            "error": f"Already claimed twice for slot {slot_no} ({currency}) in the last 30 days",
                            "last_claim_date": recent_claims[0].created_at.strftime("%d %b %Y"),
                            "next_claim_date": next_claim_date.strftime("%d %b %Y"),
                            "message": f"You can claim again from {next_claim_date.strftime('%d %b %Y')}"
                        }
            except Exception as e:
                print(f"Error checking rolling claim limit: {e}")
                pass

            from decimal import Decimal as _D
            # Full slot allocation divided by the number of eligible users
            per_user_usdt = (_D(str(alloc_usdt)) / _D(str(len(user_ids)))).quantize(_D('0.00000001'))

            # Convert if needed
            import os
            rate = _D(os.getenv('SPARK_USDT_PER_BNB', '300') or '300')
            if rate <= 0:
                rate = _D('300')
            if currency == 'BNB':
                per_user_amount = (per_user_usdt / rate).quantize(_D('0.00000001'))
            else:
                per_user_amount = per_user_usdt

            # Credit wallets and record distribution history
            from modules.wallet.service import WalletService
            from modules.spark.model import SparkBonusDistribution, SparkSlotClaimLedger
            ws = WalletService()
            credited = []
            for uid in user_ids:
                r = ws.credit_main_wallet(uid, per_user_amount, currency, 'spark_bonus_distribution', f'SPARK-{slot_no}-{currency}')
                # Save history
                try:
                    SparkBonusDistribution(
                        user_id=ObjectId(uid),
                        slot_number=int(slot_no),
                        distribution_amount=per_user_amount,
                        currency=currency,
                        fund_source='spark_bonus',
                        distribution_percentage=self._slot_percentage(slot_no),
                        total_fund_amount=_D(str(alloc_usdt)),
                        matrix_slot_name=self._slot_name(slot_no),
                        matrix_slot_level=int(slot_no),
                        status='completed',
                        distributed_at=_DT.utcnow(),
                        wallet_credit_tx_hash=f'SPARK-{slot_no}-{currency}',
                        wallet_credit_status='completed',
                    ).save()
                except Exception:
                    pass
                credited.append({"user_id": uid, "amount": float(per_user_amount), "currency": currency, "result": r})

            # Write one ledger row reducing the visible allocated amount for this slot
            try:
                SparkSlotClaimLedger(slot_number=int(slot_no), currency=currency, amount=per_user_amount * len(user_ids)).save()
            except Exception:
                pass

            return {
                "success": True,
                "slot_no": slot_no,
                "currency": currency,
                "eligible_users": len(user_ids),
                "per_user_amount": float(per_user_amount),
                "total_distributed": float(per_user_amount) * len(user_ids),
                "details": credited,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _slot_percentage(slot_no: int) -> Decimal:
        """Return Spark Bonus distribution percentage for Matrix slot."""
        return SPARK_SLOT_PERCENTAGES.get(slot_no, Decimal('0'))

    def distribute_spark_for_slot(self, cycle_no: int, slot_no: int, total_spark_pool: Decimal, participant_user_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Distribute Spark Bonus for a given cycle and matrix slot.
        - total_spark_pool: Decimal amount representing 80% Spark pool baseline (treated as 100%).
        - participant_user_ids: optional list of user ids; if None, no-op distribution.
        """
        try:
            pct = self._slot_percentage(slot_no)
            if pct <= 0:
                return {"success": False, "error": "Invalid slot number for Spark distribution"}
            if not participant_user_ids:
                return {"success": True, "cycle_no": cycle_no, "slot_no": slot_no, "participants": 0, "payout_per_participant": str(Decimal('0'))}

            slot_pool = (total_spark_pool * pct) / Decimal('100')
            count = len(participant_user_ids)
            if count == 0:
                return {"success": True, "cycle_no": cycle_no, "slot_no": slot_no, "participants": 0, "payout_per_participant": str(Decimal('0'))}
            payout_each = (slot_pool / Decimal(count)).quantize(Decimal('0.00000001'))

            # Create SparkCycle record
            cycle = SparkCycle(
                cycle_no=cycle_no,
                slot_no=slot_no,
                pool_amount=slot_pool,
                participants=[ObjectId(uid) for uid in participant_user_ids],
                distribution_percentage=pct,
                payout_per_participant=payout_each,
                status='completed',
                payout_at=datetime.utcnow()
            )
            cycle.save()

            # Create distributions
            total_fund_amount = total_spark_pool
            for uid in participant_user_ids:
                SparkBonusDistribution(
                    user_id=ObjectId(uid),
                    slot_number=slot_no,
                    distribution_amount=payout_each,
                    currency='USDT',
                    fund_source='spark_bonus',
                    distribution_percentage=pct,
                    total_fund_amount=total_fund_amount,
                    matrix_slot_name=self._slot_name(slot_no),
                    matrix_slot_level=slot_no,
                    status='completed',
                    distributed_at=datetime.utcnow()
                ).save()

            return {
                "success": True,
                "cycle_no": cycle_no,
                "slot_no": slot_no,
                "slot_name": self._slot_name(slot_no),
                "participants": count,
                "slot_percentage": str(pct),
                "payout_per_participant": str(payout_each)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------ Triple Entry Reward Methods ------------------
    def _deduct_from_triple_entry_fund(self, amount: Decimal, currency: str) -> Dict[str, Any]:
        """
        Deduct claimed amount from stored Triple Entry BonusFund balances.
        Currency-aware: BNB deductions come from program 'binary'; USDT deductions
        are split proportionally across 'matrix' and 'global'.
        """
        try:
            from modules.income.bonus_fund import BonusFund

            if amount <= 0:
                return {"success": True, "message": "No deduction necessary"}

            currency = currency.upper()
            updates: List[str] = []

            if currency == 'BNB':
                fund = BonusFund.objects(
                    fund_type='triple_entry',
                    program='binary',
                    status='active'
                ).first()
                available = Decimal(str(fund.current_balance or 0)) if fund else Decimal('0')
                if available <= 0:
                    return {"success": False, "error": "Triple Entry BNB fund unavailable"}

                deduction = min(amount, available)
                fund.current_balance = available - deduction
                fund.total_distributed = (fund.total_distributed or Decimal('0')) + deduction
                fund.last_distribution = datetime.utcnow()
                fund.updated_at = datetime.utcnow()
                fund.save()
                updates.append(f"binary:{float(deduction)} BNB")

                return {
                    "success": True,
                    "total_deducted": float(deduction),
                    "sources_updated": updates,
                    "message": f"Deducted {float(deduction)} BNB from Triple Entry fund"
                }

            # USDT deductions span matrix/global funds
            funds = BonusFund.objects(
                fund_type='triple_entry',
                program__in=['matrix', 'global'],
                status='active'
            )
            balances: Dict[str, Decimal] = {
                f.program: Decimal(str(f.current_balance or 0)) for f in funds
            }
            total_usdt = sum(balances.values())
            if total_usdt <= 0:
                return {"success": False, "error": "Triple Entry USDT fund unavailable"}

            remaining = amount
            for fund in funds:
                balance = Decimal(str(fund.current_balance or 0))
                if balance <= 0 or remaining <= 0:
                    continue
                proportion = (balance / total_usdt) if total_usdt > 0 else Decimal('0')
                deduction = (amount * proportion).quantize(Decimal('0.00000001'))
                if deduction > remaining:
                    deduction = remaining
                if deduction > balance:
                    deduction = balance
                fund.current_balance = balance - deduction
                fund.total_distributed = (fund.total_distributed or Decimal('0')) + deduction
                fund.last_distribution = datetime.utcnow()
                fund.updated_at = datetime.utcnow()
                fund.save()
                remaining -= deduction
                updates.append(f"{fund.program}:{float(deduction)} USDT")

            if remaining > Decimal('0'):
                updates.append(f"unallocated:{float(remaining)} USDT")

            return {
                "success": True,
                "total_deducted": float(amount - remaining),
                "sources_updated": updates,
                "message": f"Deducted {float(amount - remaining)} USDT from Triple Entry fund"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calculate_triple_entry_fund(self) -> Dict[str, Any]:
        """
        Calculate total Triple Entry Reward fund from persisted BonusFund balances.
        Aggregates separate buckets:
        - binary (BNB) -> 18% of Spark BNB contributions
        - matrix (USDT) -> 18% of Spark USDT contributions
        - global (USDT) -> 5% of Global program contributions
        """
        try:
            from modules.income.bonus_fund import BonusFund

            triple_funds = BonusFund.objects(
                fund_type='triple_entry',
                status='active'
            )

            totals_by_program: Dict[str, Decimal] = {}
            for fund in triple_funds:
                amt = Decimal(str(fund.current_balance or 0))
                totals_by_program[fund.program] = totals_by_program.get(fund.program, Decimal('0')) + amt

            total_bnb = totals_by_program.get('binary', Decimal('0'))
            total_usdt = Decimal('0')
            for program in ('matrix', 'global'):
                total_usdt += totals_by_program.get(program, Decimal('0'))

            rate = Decimal(os.getenv('SPARK_USDT_PER_BNB', '300') or '300')
            if rate <= 0:
                rate = Decimal('300')

            total_usdt_equivalent = total_usdt + (total_bnb * rate)

            return {
                "success": True,
                "total_fund_usdt": float(total_usdt_equivalent),
                "totals": {
                    "BNB": float(total_bnb),
                    "USDT": float(total_usdt),
                    "by_program": {prog: float(val) for prog, val in totals_by_program.items()}
                },
                "conversion_rate": float(rate)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_triple_entry_claimable_amount(self, user_id: str) -> Dict[str, Any]:
        """
        Calculate claimable Triple Entry Reward amounts for both USDT and BNB
        
        Eligibility: User must have joined all three programs (Binary, Matrix, Global)
        Distribution: Total TER fund divided equally among all eligible users
        Fund Sources: 18% from Spark Bonus + 5% from Global program
        """
        try:
            # 1. Check eligibility
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            is_eligible = bool(user.binary_joined and user.matrix_joined and user.global_joined)
            if not is_eligible:
                return {
                    "success": True,
                    "is_eligible": False,
                    "claimable_amounts": {"USDT": 0, "BNB": 0},
                    "message": "User must join all three programs (Binary, Matrix, Global) to be eligible for Triple Entry Reward"
                }
            
            # 2. Get all eligible users (who joined all 3 programs)
            eligible_users = User.objects(
                binary_joined=True,
                matrix_joined=True,
                global_joined=True
            ).only('id')
            
            eligible_count = eligible_users.count()
            if eligible_count == 0:
                return {
                    "success": True,
                    "is_eligible": True,
                    "claimable_amounts": {"USDT": 0, "BNB": 0},
                    "message": "No eligible users found"
                }
            
            # 3. Calculate total TER fund from database
            fund_info = self._calculate_triple_entry_fund()
            
            if not fund_info.get("success"):
                return {
                    "success": False,
                    "error": "Failed to calculate Triple Entry fund",
                    "details": fund_info.get("error")
                }
            
            ter_fund_usdt = Decimal(str(fund_info.get('total_fund_usdt', 0)))
            
            # Check if fund is available
            if ter_fund_usdt <= 0:
                return {
                    "success": True,
                    "is_eligible": True,
                    "claimable_amounts": {"USDT": 0, "BNB": 0},
                    "eligible_users_count": eligible_count,
                    "total_fund_usdt": 0,
                    "fund_totals": fund_info.get("totals", {}),
                    "already_claimed": {"USDT": False, "BNB": False},
                    "message": "No Triple Entry Reward fund available yet. Fund will be collected from Binary/Matrix activations (8% each) and Global program (5%)."
                }
            
            # 4. Calculate per-user share
            per_user_usdt = (ter_fund_usdt / Decimal(str(eligible_count))).quantize(Decimal('0.00000001'))
            
            # 5. Convert to BNB
            rate = Decimal(str(fund_info.get('conversion_rate', os.getenv('SPARK_USDT_PER_BNB', '300'))))
            if rate <= 0:
                rate = Decimal('300')
            per_user_bnb = (per_user_usdt / rate).quantize(Decimal('0.00000001'))
            
            # 6. Check if user already claimed today
            day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            already_claimed_usdt = TripleEntryPayment.objects(
                user_id=ObjectId(user_id),
                currency='USDT',
                created_at__gte=day_start
            ).first()
            
            already_claimed_bnb = TripleEntryPayment.objects(
                user_id=ObjectId(user_id),
                currency='BNB',
                created_at__gte=day_start
            ).first()
            
            return {
                "success": True,
                "is_eligible": True,
                "claimable_amounts": {
                    "USDT": float(per_user_usdt) if not already_claimed_usdt else 0,
                    "BNB": float(per_user_bnb) if not already_claimed_bnb else 0
                },
                "eligible_users_count": eligible_count,
                "total_fund_usdt": float(ter_fund_usdt),
                "fund_totals": fund_info.get("totals", {}),
                "already_claimed": {
                    "USDT": bool(already_claimed_usdt),
                    "BNB": bool(already_claimed_bnb)
                },
                "message": "Eligible for Triple Entry Reward"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_triple_entry_claim_history(self, user_id: str, currency: str = None) -> Dict[str, Any]:
        """
        Get Triple Entry Reward claim history for a user
        Returns both USDT and BNB history by default, or filtered by currency
        """
        try:
            # Build query
            query = {"user_id": ObjectId(user_id)}
            if currency:
                currency = currency.upper()
                if currency not in ['USDT', 'BNB']:
                    return {"success": False, "error": "Invalid currency. Must be USDT or BNB"}
                query["currency"] = currency
            
            # Get payments
            payments = TripleEntryPayment.objects(**query).order_by('-created_at')
            
            # Group by currency
            usdt_claims = []
            bnb_claims = []
            
            for payment in payments:
                claim_data = {
                    "id": str(payment.id),
                    "amount": float(payment.amount),
                    "status": payment.status,
                    "paid_at": payment.paid_at.strftime("%d %b %Y (%H:%M)") if payment.paid_at else None,
                    "created_at": payment.created_at.strftime("%d %b %Y (%H:%M)"),
                    "tx_hash": payment.tx_hash,
                    "eligible_users_count": payment.eligible_users_count,
                    "total_fund_amount": float(payment.total_fund_amount) if payment.total_fund_amount else None
                }
                
                if payment.currency == 'USDT':
                    usdt_claims.append(claim_data)
                elif payment.currency == 'BNB':
                    bnb_claims.append(claim_data)
            
            return {
                "success": True,
                "USDT": {
                    "claims": usdt_claims,
                    "total_claims": len(usdt_claims)
                },
                "BNB": {
                    "claims": bnb_claims,
                    "total_claims": len(bnb_claims)
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def claim_triple_entry_reward(self, user_id: str, currency: str = 'USDT') -> Dict[str, Any]:
        """
        Process Triple Entry Reward claim for a user
        """
        try:
            currency = currency.upper()
            if currency not in ['USDT', 'BNB']:
                return {"success": False, "error": "Invalid currency. Must be USDT or BNB"}
            
            # Get claimable amount
            claimable_info = self.get_triple_entry_claimable_amount(user_id)
            if not claimable_info.get("success"):
                return claimable_info
            
            if not claimable_info.get("is_eligible"):
                return {"success": False, "error": "User is not eligible for Triple Entry Reward"}
            
            claimable_amount = claimable_info["claimable_amounts"][currency]
            if claimable_amount <= 0:
                return {"success": False, "error": f"No claimable amount for {currency} or already claimed today"}
            
            # Deduct from fund sources
            fund_deduction_result = self._deduct_from_triple_entry_fund(Decimal(str(claimable_amount)), currency)
            
            # Create payment record
            payment = TripleEntryPayment(
                user_id=ObjectId(user_id),
                amount=Decimal(str(claimable_amount)),
                currency=currency,
                status='paid',
                paid_at=datetime.utcnow(),
                tx_hash=f"TER-{currency}-{user_id}-{int(datetime.utcnow().timestamp())}",
                eligible_users_count=claimable_info.get("eligible_users_count"),
                total_fund_amount=Decimal(str(claimable_info.get("total_fund_usdt", 0)))
            )
            payment.save()
            
            # Credit wallet
            from modules.wallet.service import WalletService
            wallet_service = WalletService()
            wallet_result = wallet_service.credit_main_wallet(
                user_id=user_id,
                amount=Decimal(str(claimable_amount)),
                currency=currency,
                reason='triple_entry_reward',
                tx_hash=payment.tx_hash
            )
            
            return {
                "success": True,
                "payment_id": str(payment.id),
                "amount": claimable_amount,
                "currency": currency,
                "tx_hash": payment.tx_hash,
                "wallet_credited": wallet_result.get("success", False),
                "fund_deducted": fund_deduction_result.get("success", False),
                "fund_sources_updated": fund_deduction_result.get("sources_updated", []),
                "message": f"Triple Entry Reward of {claimable_amount} {currency} claimed successfully"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


