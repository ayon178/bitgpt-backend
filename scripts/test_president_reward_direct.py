"""
Direct test for President Reward claim (without API server)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mongoengine import connect
from modules.user.model import User
from modules.president_reward.model import PresidentReward, PresidentRewardFund
from modules.president_reward.service import PresidentRewardService
from modules.slot.model import SlotActivation
from bson import ObjectId
from datetime import datetime

# Connect to database
MONGO_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"
connect(host=MONGO_URI)

def test_president_reward_direct(user_id: str):
    """Direct test of President Reward claim"""
    print(f"\n{'='*60}")
    print(f"Testing President Reward Claim (Direct) for: {user_id}")
    print(f"{'='*60}\n")
    
    # 1. Ensure fund
    fund = PresidentRewardFund.objects(is_active=True).first()
    if not fund:
        fund = PresidentRewardFund(
            fund_name="President Reward Fund",
            total_fund_amount=100000.0,
            available_amount=100000.0,
            currency="USDT",
            is_active=True
        )
        fund.save()
        print(f"✅ Created President Reward Fund with $100,000")
    else:
        print(f"✅ President Reward Fund balance: ${fund.available_amount}")
    
    # 2. Ensure user has programs
    for program in ['binary', 'matrix', 'global']:
        slot = SlotActivation.objects(user_id=ObjectId(user_id), program=program, slot_no=1).first()
        if not slot:
            slot = SlotActivation(
                user_id=ObjectId(user_id),
                program=program,
                slot_no=1,
                status='completed',
                activated_at=datetime.utcnow()
            )
            slot.save()
            print(f"✅ Activated {program} program")
    
    # 3. Join President Reward
    svc = PresidentRewardService()
    pr = PresidentReward.objects(user_id=ObjectId(user_id)).first()
    if not pr:
        result = svc.join_president_reward_program(user_id)
        print(f"Join result: {result}")
        pr = PresidentReward.objects(user_id=ObjectId(user_id)).first()
    
    # 4. Update eligibility manually
    pr.direct_partners_both = 10
    pr.total_direct_partners = 10
    pr.global_team_size = 400
    pr.is_eligible = True
    pr.save()
    print(f"✅ Updated PR: 10 direct + 400 team")
    
    # Also update eligibility record
    from modules.president_reward.model import PresidentRewardEligibility
    elig = PresidentRewardEligibility.objects(user_id=ObjectId(user_id)).first()
    if not elig:
        elig = PresidentRewardEligibility(user_id=ObjectId(user_id))
    elig.direct_partners_both_count = 10
    elig.global_team_count = 400
    elig.is_eligible_for_president_reward = True
    elig.save()
    print(f"✅ Updated eligibility record")
    
    # 5. Attempt claim
    print(f"\n{'='*60}")
    print(f"Attempting claim...")
    print(f"{'='*60}")
    result = svc.claim_president_reward(user_id=user_id, currency='USDT')
    print(f"Claim result: {result}")
    
    if result.get('success'):
        print(f"\n✅ President Reward claimed successfully!")
        print(f"   Tier: {result.get('tier')}")
        print(f"   Amount: ${result.get('amount')} {result.get('currency')}")
        print(f"   Payment ID: {result.get('payment_id')}")
    else:
        print(f"\n❌ Claim failed: {result.get('error')}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_president_reward_direct.py <user_id>")
        sys.exit(1)
    
    user_id = sys.argv[1]
    test_president_reward_direct(user_id)

