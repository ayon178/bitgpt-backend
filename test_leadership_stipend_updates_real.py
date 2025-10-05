from bson import ObjectId
from datetime import datetime
from core.db import connect_to_db
from modules.user.model import User
from modules.slot.model import SlotActivation
from modules.leadership_stipend.service import LeadershipStipendService
from modules.leadership_stipend.model import LeadershipStipend, LeadershipStipendEligibility, LeadershipStipendPayment


def create_user_with_slot10() -> str:
    uid = f"ls_{datetime.utcnow().timestamp()}".replace('.', '')
    u = User(
        uid=uid,
        refer_code=f"RC_{uid}",
        wallet_address=f"0x{uid}",
        name=f"LS Test",
        status='active',
        binary_joined=True,
        matrix_joined=True,
        global_joined=True,
        binary_joined_at=datetime.utcnow(),
        matrix_joined_at=datetime.utcnow(),
        global_joined_at=datetime.utcnow(),
    )
    u.save()

    # Insert slot activation for slot 10 (binary program)
    act = SlotActivation(
        user_id=ObjectId(u.id),
        program='binary',
        slot_no=10,
        slot_name='Leader',
        amount_paid=1.1264,  # value doesn't affect stipend logic directly here
        activation_type='upgrade',
        upgrade_source='wallet',
        currency='BNB',
        tx_hash=f"tx_{uid}",
        status='completed'
    )
    act.save()
    return str(u.id)


def run_test():
    connect_to_db()
    print("✅ Database connected successfully!")
    print("🚀 Leadership Stipend Updates - Real User Fast Test\n" + "="*70)

    service = LeadershipStipendService()

    user_id = create_user_with_slot10()
    print(f"✅ Created user: {user_id} with Binary slot 10 active")

    join_res = service.join_leadership_stipend_program(user_id)
    assert join_res.get("success"), join_res
    print("✅ Joined Leadership Stipend program")

    elig = service.check_eligibility(user_id)
    assert elig.get("success"), elig
    assert elig.get("is_eligible") is True
    current = elig.get("current_tier", {})
    assert current.get("slot_number") == 10
    assert current.get("daily_return") == 2.2528
    print("✅ Eligibility and current tier set (slot 10, daily 2.2528 BNB)")

    # Daily calculation should create a pending payment up to cap (2.2528) once
    calc = service.process_daily_calculation()
    assert calc.get("success"), calc
    print("✅ Daily calculation executed")

    # Ensure fund exists and has balance
    try:
        from modules.leadership_stipend.model import LeadershipStipendFund
        fund = LeadershipStipendFund.objects().first()
        if not fund:
            fund = LeadershipStipendFund(available_amount=10000.0, total_fund_amount=10000.0)
        else:
            fund.available_amount = max(fund.available_amount or 0.0, 10000.0)
            fund.total_fund_amount = max(fund.total_fund_amount or 0.0, fund.available_amount)
        fund.save()
    except Exception:
        pass

    # Fetch created payment and distribute it
    payment = LeadershipStipendPayment.objects(user_id=ObjectId(user_id), slot_number=10, payment_status='pending').first()
    assert payment is not None
    dist = service.distribute_stipend_payment(str(payment.id))
    assert dist.get("success"), dist
    print("✅ Payment distributed successfully")

    print("\n🎯 Leadership Stipend Updates - Fast Test Complete!\n" + "="*70)

    # Cleanup
    print("🧹 Cleaning up test user...")
    User.objects(id=ObjectId(user_id)).delete()
    print("✅ Cleanup completed")


if __name__ == "__main__":
    run_test()


