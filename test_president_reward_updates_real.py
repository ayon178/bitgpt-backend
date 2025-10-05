from bson import ObjectId
from datetime import datetime
from modules.user.model import User
from modules.president_reward.service import PresidentRewardService
from modules.president_reward.model import PresidentReward, PresidentRewardEligibility, PresidentRewardPayment
from core.db import connect_to_db


def generate_unique(uid_prefix: str) -> str:
    return f"{uid_prefix}_{datetime.utcnow().timestamp()}".replace('.', '')


def create_user(parent_id: str | None, name_suffix: str, join_matrix: bool, join_global: bool) -> str:
    uid = generate_unique("pru")
    u = User(
        uid=f"{uid}_{name_suffix}",
        refer_code=f"RC_{uid}_{name_suffix}",
        wallet_address=f"0x{uid}{name_suffix}",
        name=f"PR Test {name_suffix}",
        refered_by=ObjectId(parent_id) if parent_id else ObjectId("68dc17f08b174277bc40d19c"),
        status='active',
        binary_joined=True,
        matrix_joined=join_matrix,
        global_joined=join_global,
        binary_joined_at=datetime.utcnow(),
        matrix_joined_at=datetime.utcnow() if join_matrix else None,
        global_joined_at=datetime.utcnow() if join_global else None,
    )
    u.save()
    return str(u.id)


def run_test():
    connect_to_db()
    print("✅ Database connected successfully!")
    print("🚀 President Reward Updates - Real User Fast Test\n" + "="*70)

    service = PresidentRewardService()

    # Create main user
    main_user_id = create_user(None, "main", True, True)
    print(f"✅ Main user: {main_user_id}")

    # Join program
    join_res = service.join_president_reward_program(main_user_id)
    assert join_res.get("success"), join_res
    print("✅ Joined President Reward program")

    # Create 10 direct partners with both packages
    direct_ids = []
    for i in range(10):
        did = create_user(main_user_id, f"d{i+1}", True, True)
        direct_ids.append(did)
    print(f"✅ Created {len(direct_ids)} direct partners with both packages")

    # Force eligibility for speed: set global team to 400 and mark eligible
    pr = PresidentReward.objects(user_id=ObjectId(main_user_id)).first()
    assert pr is not None
    pr.direct_partners_both = 10
    pr.global_team_size = 400
    pr.is_eligible = True
    pr.save()

    elig = PresidentRewardEligibility.objects(user_id=ObjectId(main_user_id)).first()
    if not elig:
        elig = PresidentRewardEligibility(user_id=ObjectId(main_user_id))
    elig.direct_partners_both_count = 10
    elig.global_team_count = 400
    elig.is_eligible_for_president_reward = True
    elig.last_checked = datetime.utcnow()
    elig.save()

    # Skip recomputation to keep fast path (we already set eligibility)
    print("✅ Eligibility set fast: 10 directs + 400 team")

    # Process tiers and verify currency USDT and first tier achieved
    proc = service.process_reward_tiers(main_user_id)
    assert proc.get("success"), proc
    rewards = proc.get("rewards_earned", [])
    assert any(r.get("tier") == 1 for r in rewards), "Tier 1 not achieved"
    # Verify payment stored with USDT
    payment = PresidentRewardPayment.objects(user_id=ObjectId(main_user_id), tier_number=1).first()
    assert payment is not None
    assert payment.currency == 'USDT'
    print("✅ Tier 1 reward created with USDT currency")

    print("\n🎯 President Reward Updates - Fast Test Complete!\n" + "="*70)

    # Cleanup
    print("🧹 Cleaning up test users...")
    User.objects(id=ObjectId(main_user_id)).delete()
    for did in direct_ids:
        User.objects(id=ObjectId(did)).delete()
    print("✅ Cleanup completed")


if __name__ == "__main__":
    run_test()


