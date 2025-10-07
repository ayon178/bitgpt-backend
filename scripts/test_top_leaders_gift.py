"""
Test Top Leaders Gift claim
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mongoengine import connect
from modules.top_leader_gift.payment_model import TopLeadersGiftFund, TopLeadersGiftUser
from modules.top_leader_gift.claim_service import TopLeadersGiftClaimService
from modules.rank.model import UserRank
from bson import ObjectId
from datetime import datetime

# Connect to database
MONGO_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"
connect(host=MONGO_URI)

def test_top_leaders_claim(user_id: str):
    """Test Top Leaders Gift claim"""
    print(f"\n{'='*60}")
    print(f"Testing Top Leaders Gift for: {user_id}")
    print(f"{'='*60}\n")
    
    # 1. Ensure fund exists
    fund = TopLeadersGiftFund.objects(is_active=True).first()
    if not fund:
        fund = TopLeadersGiftFund(
            total_fund_usdt=10000.0,
            available_usdt=10000.0,
            total_fund_bnb=50.0,
            available_bnb=50.0
        )
        fund.save()
        print(f"✅ Created Top Leaders Gift Fund")
    else:
        print(f"✅ Fund exists: ${fund.available_usdt} USDT, {fund.available_bnb} BNB")
    
    # 2. Set user rank to 6 (for Level 1 eligibility)
    user_rank = UserRank.objects(user_id=ObjectId(user_id)).first()
    if not user_rank:
        user_rank = UserRank(user_id=ObjectId(user_id))
    user_rank.current_rank_number = 6
    user_rank.current_rank_name = "Ignis"
    user_rank.save()
    print(f"✅ Set user rank to 6")
    
    # 3. Set direct partners and team (manual for testing)
    from modules.user.model import PartnerGraph
    graph = PartnerGraph.objects(user_id=ObjectId(user_id)).first()
    if not graph:
        graph = PartnerGraph(user_id=ObjectId(user_id))
    graph.total_team = 300
    graph.save()
    print(f"✅ Set team size to 300")
    
    # 4. Test claim
    service = TopLeadersGiftClaimService()
    
    # Check eligibility first
    print(f"\n{'='*60}")
    print(f"Checking eligibility...")
    print(f"{'='*60}")
    elig = service.check_eligibility(user_id)
    print(f"Eligibility: {elig}")
    
    # Manually set eligibility for testing
    tl_user = TopLeadersGiftUser.objects(user_id=ObjectId(user_id)).first()
    if tl_user:
        tl_user.current_self_rank = 6
        tl_user.current_direct_partners_count = 5
        tl_user.current_total_team_size = 300
        tl_user.is_eligible = True
        tl_user.highest_level_achieved = 1
        
        # Mark level 1 as achieved
        for level in tl_user.levels:
            if level.level_number == 1:
                level.is_achieved = True
                level.achieved_at = datetime.utcnow()
        
        tl_user.save()
        print(f"✅ Updated user eligibility manually")
    
    # Claim Level 1
    print(f"\n{'='*60}")
    print(f"Claiming Level 1...")
    print(f"{'='*60}")
    result = service.claim_reward(user_id=user_id, level_number=1, currency='BOTH')
    print(f"Claim result: {result}")
    
    if result.get('success'):
        print(f"\n✅ Top Leaders Gift claimed!")
        print(f"   Level: {result.get('level')}")
        print(f"   USDT: ${result.get('claimed_usdt')}")
        print(f"   BNB: {result.get('claimed_bnb')}")
    else:
        print(f"\n❌ Claim failed: {result.get('error')}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_top_leaders_gift.py <user_id>")
        sys.exit(1)
    
    user_id = sys.argv[1]
    test_top_leaders_claim(user_id)

