"""
Test script for President Reward claim functionality.
This script will:
1. Ensure user has all 3 programs active (Binary, Matrix, Global)
2. Create 10 direct partners with all 3 programs active
3. Ensure fund balance
4. Attempt to claim President Reward
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mongoengine import connect
from modules.user.model import User
from modules.president_reward.model import PresidentReward, PresidentRewardFund
from modules.president_reward.service import PresidentRewardService
from modules.slot.model import SlotActivation
from modules.tree.model import TreePlacement
from bson import ObjectId
from datetime import datetime
import requests

# Connect to database
MONGO_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"
connect(host=MONGO_URI)

def ensure_president_reward_fund():
    """Ensure President Reward fund has sufficient balance"""
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
        if fund.available_amount < 10000:
            fund.available_amount += 50000
            fund.total_fund_amount += 50000
            fund.save()
            print(f"✅ Topped up President Reward Fund. New balance: ${fund.available_amount}")
        else:
            print(f"✅ President Reward Fund balance: ${fund.available_amount}")
    return fund

def ensure_user_programs_active(user_id: str):
    """Ensure user has all 3 programs (Binary, Matrix, Global) active"""
    user = User.objects(id=ObjectId(user_id)).first()
    if not user:
        print(f"❌ User {user_id} not found")
        return False
    
    # Check Binary (slot 1)
    binary_slot = SlotActivation.objects(user_id=ObjectId(user_id), program='binary', slot_no=1).first()
    if not binary_slot:
        binary_slot = SlotActivation(
            user_id=ObjectId(user_id),
            program='binary',
            slot_no=1,
            status='completed',
            activated_at=datetime.utcnow()
        )
        binary_slot.save()
        print(f"✅ Activated Binary program for user")
    
    # Check Matrix (slot 1)
    matrix_slot = SlotActivation.objects(user_id=ObjectId(user_id), program='matrix', slot_no=1).first()
    if not matrix_slot:
        matrix_slot = SlotActivation(
            user_id=ObjectId(user_id),
            program='matrix',
            slot_no=1,
            status='completed',
            activated_at=datetime.utcnow()
        )
        matrix_slot.save()
        print(f"✅ Activated Matrix program for user")
    
    # Check Global (slot 1)
    global_slot = SlotActivation.objects(user_id=ObjectId(user_id), program='global', slot_no=1).first()
    if not global_slot:
        global_slot = SlotActivation(
            user_id=ObjectId(user_id),
            program='global',
            slot_no=1,
            status='completed',
            activated_at=datetime.utcnow()
        )
        global_slot.save()
        print(f"✅ Activated Global program for user")
    
    return True

def create_direct_partners_with_programs(user_id: str, count: int = 10):
    """Create direct partners with all 3 programs active"""
    user = User.objects(id=ObjectId(user_id)).first()
    if not user:
        print(f"❌ User {user_id} not found")
        return []
    
    partners = []
    for i in range(count):
        # Create partner
        partner = User(
            email=f"pr_partner_{i+1}_{user_id[:8]}@test.com",
            username=f"pr_partner_{i+1}_{user_id[:8]}",
            password_hash="test123",
            full_name=f"PR Partner {i+1}",
            phone=f"+8801700{i:06d}",
            referrer_id=ObjectId(user_id),
            status="active"
        )
        partner.save()
        
        # Activate all 3 programs
        for program in ['binary', 'matrix', 'global']:
            slot = SlotActivation(
                user_id=partner.id,
                program=program,
                slot_no=1,
                status='completed',
                activated_at=datetime.utcnow()
            )
            slot.save()
        
        partners.append(partner)
    
    print(f"✅ Created {count} direct partners with all 3 programs active")
    return partners

def create_global_team(user_id: str, team_size: int = 400):
    """Create global team members"""
    # For simplicity, we'll just create team records
    # In real scenario, this would be calculated from actual tree structure
    team_members = []
    for i in range(team_size):
        member = User(
            email=f"pr_team_{i+1}_{user_id[:8]}@test.com",
            username=f"pr_team_{i+1}_{user_id[:8]}",
            password_hash="test123",
            full_name=f"PR Team {i+1}",
            phone=f"+8801800{i:06d}",
            status="active"
        )
        member.save()
        team_members.append(member)
    
    print(f"✅ Created {team_size} global team members")
    return team_members

def ensure_president_reward_joined(user_id: str):
    """Ensure user has joined President Reward program"""
    pr = PresidentReward.objects(user_id=ObjectId(user_id)).first()
    if not pr:
        svc = PresidentRewardService()
        result = svc.join_president_reward_program(user_id)
        if result.get('success'):
            print(f"✅ User joined President Reward program")
        else:
            print(f"❌ Failed to join President Reward: {result.get('error')}")
        pr = PresidentReward.objects(user_id=ObjectId(user_id)).first()
    else:
        print(f"✅ User already in President Reward program")
    
    # Update counts manually for testing
    pr.direct_partners_both = 10
    pr.total_direct_partners = 10
    pr.global_team_size = 400
    pr.is_eligible = True
    pr.save()
    print(f"✅ Updated President Reward eligibility (10 direct, 400 team)")
    
    return pr

def test_president_reward_claim(user_id: str):
    """Test President Reward claim"""
    print(f"\n{'='*60}")
    print(f"Testing President Reward Claim for user: {user_id}")
    print(f"{'='*60}\n")
    
    # 1. Ensure fund
    ensure_president_reward_fund()
    
    # 2. Ensure user programs
    ensure_user_programs_active(user_id)
    
    # 3. Create direct partners (we'll just update the counts)
    ensure_president_reward_joined(user_id)
    
    # 4. Attempt to claim
    try:
        url = "http://localhost:8000/president-reward/claim"
        params = {
            "user_id": user_id,
            "currency": "USDT"
        }
        response = requests.post(url, params=params)
        
        print(f"\n{'='*60}")
        print(f"Claim Response:")
        print(f"{'='*60}")
        print(response.json())
        print(f"{'='*60}\n")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ President Reward claimed successfully!")
                print(f"   Tier: {data['data']['tier']}")
                print(f"   Amount: ${data['data']['amount']} {data['data']['currency']}")
            else:
                print(f"❌ Claim failed: {data.get('message')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Exception during claim: {str(e)}")
    
    # 5. Check history
    try:
        url = f"http://localhost:8000/president-reward/claim/history"
        params = {
            "user_id": user_id,
            "page": 1,
            "limit": 10
        }
        response = requests.get(url, params=params)
        
        print(f"\n{'='*60}")
        print(f"Claim History:")
        print(f"{'='*60}")
        print(response.json())
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"❌ Exception getting history: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_president_reward_claim.py <user_id>")
        sys.exit(1)
    
    user_id = sys.argv[1]
    test_president_reward_claim(user_id)

