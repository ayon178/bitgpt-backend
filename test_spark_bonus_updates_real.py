from datetime import datetime
from decimal import Decimal
from bson import ObjectId
from core.db import connect_to_db
from modules.user.model import User
from modules.spark.service import SparkService


def create_matrix_users(n: int) -> list[str]:
    ids = []
    for i in range(n):
        uid = f"sb_{datetime.utcnow().timestamp()}_{i}".replace('.', '')
        u = User(
            uid=uid,
            refer_code=f"RC_{uid}",
            wallet_address=f"0x{uid}",
            name=f"Spark User {i+1}",
            status='active',
            binary_joined=True,
            matrix_joined=True,
            global_joined=False,
            binary_joined_at=datetime.utcnow(),
            matrix_joined_at=datetime.utcnow(),
        )
        u.save()
        ids.append(str(u.id))
    return ids


def run_test():
    connect_to_db()
    print("✅ Database connected successfully!")
    print("🚀 Spark Bonus Updates - Real User Fast Test\n" + "="*70)

    service = SparkService()
    cycle_no = int(datetime.utcnow().strftime('%Y%m%d'))

    # Create 5 users for Matrix Slot 1 distribution example
    user_ids = create_matrix_users(5)
    total_spark_pool = Decimal('1000')  # treat as 80% pool baseline

    # Slot 1 should get 15% → 150; per user = 150/5 = 30
    res = service.distribute_spark_for_slot(cycle_no, slot_no=1, total_spark_pool=total_spark_pool, participant_user_ids=user_ids)
    assert res.get('success'), res
    assert res.get('payout_per_participant') == '30.00000000'
    print("✅ Slot 1 distribution: 15% → per-user 30.00000000 USDT")

    # Slot 6 should get 7%; with 7 users
    user_ids2 = create_matrix_users(7)
    res2 = service.distribute_spark_for_slot(cycle_no, slot_no=6, total_spark_pool=total_spark_pool, participant_user_ids=user_ids2)
    assert res2.get('success'), res2
    # 7% of 1000 = 70; per user = 10
    assert res2.get('payout_per_participant') == '10.00000000'
    print("✅ Slot 6 distribution: 7% → per-user 10.00000000 USDT")

    print("\n🎯 Spark Bonus Updates - Fast Test Complete!\n" + "="*70)

    # Cleanup
    print("🧹 Cleaning up test users...")
    for uid in user_ids + user_ids2:
        User.objects(id=ObjectId(uid)).delete()
    print("✅ Cleanup completed")


if __name__ == "__main__":
    run_test()


