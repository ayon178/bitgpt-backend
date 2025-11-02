#!/usr/bin/env python3
"""
Comprehensive Database Seed Script for BitGPT MLM Platform
This script seeds all essential data after database wipe:
- SlotCatalog (Binary, Matrix, Global)
- Ranks
- SystemConfig
Based on main.py startup_initializer logic
"""

import os
import sys
from decimal import Decimal
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.slot.model import SlotCatalog
from modules.blockchain.model import SystemConfig
from modules.rank.service import RankService
from modules.rank.model import RankSettings
from modules.income.bonus_fund import BonusFund
from modules.phase_system.model import PhaseSystemSettings
from modules.newcomer_support.model import NewcomerSupportSettings
from modules.dream_matrix.model import DreamMatrixSettings
from modules.royal_captain.model import RoyalCaptainSettings
from modules.president_reward.model import PresidentRewardSettings
from modules.top_leader_gift.model import TopLeaderGiftSettings


def seed_slot_catalog():
    """Seed SlotCatalog entries for Binary, Matrix, and Global programs"""
    print("\n🌱 Seeding SlotCatalog...")
    
    def _ensure_slot(program: str, slot_no: int, name: str, price: Decimal, level: int, phase: str | None = None):
        slot = SlotCatalog.objects(program=program, slot_no=slot_no).first()
        if not slot:
            slot = SlotCatalog(program=program, slot_no=slot_no)
        slot.name = name
        slot.price = price
        slot.currency = 'BNB' if program == 'binary' else ('USDT' if program == 'matrix' else 'USD')
        slot.level = level
        if program == 'global' and phase:
            slot.phase = phase
        slot.is_active = True
        slot.updated_at = datetime.utcnow()
        slot.save()
        print(f"  ✅ {program.upper()} Slot {slot_no}: {name} - {price} {slot.currency}")

    # Binary slots 1..17 (names and prices per PROJECT_DOCUMENTATION.md)
    binary_slots = [
        (1,  'Explorer',     '0.0022', 0),
        (2,  'Contributor',  '0.0044', 1),
        (3,  'Subscriber',   '0.0088', 2),
        (4,  'Dreamer',      '0.0176', 3),
        (5,  'Planner',      '0.0352', 4),
        (6,  'Challenger',   '0.0704', 5),
        (7,  'Adventurer',   '0.1408', 6),
        (8,  'Game-Shifter', '0.2816', 7),
        (9,  'Organizer',    '0.5632', 8),
        (10, 'Leader',       '1.1264', 9),
        (11, 'Vanguard',     '2.2528', 10),
        (12, 'Center',       '4.5056', 11),
        (13, 'Climax',       '9.0112', 12),
        (14, 'Eternity',     '18.0224', 13),
        (15, 'King',         '36.0448', 14),
        (16, 'Commander',    '72.0896', 15),
        (17, 'CEO',          '144.1792', 16),
    ]
    for slot_no, name, price, level in binary_slots:
        _ensure_slot('binary', slot_no, name, Decimal(price), level)

    # Matrix slots 1..15 (names and prices per docs)
    matrix_slots = [
        (1,  'STARTER',   '11',        1),
        (2,  'BRONZE',    '33',        2),
        (3,  'SILVER',    '99',        3),
        (4,  'GOLD',      '297',       4),
        (5,  'PLATINUM',  '891',       5),
        (6,  'DIAMOND',   '2673',      6),
        (7,  'RUBY',      '8019',      7),
        (8,  'EMERALD',   '24057',     8),
        (9,  'SAPPHIRE',  '72171',     9),
        (10, 'TOPAZ',     '216513',    10),
        (11, 'PEARL',     '649539',    11),
        (12, 'AMETHYST',  '1948617',   12),
        (13, 'OBSIDIAN',  '5845851',   13),
        (14, 'TITANIUM',  '17537553',  14),
        (15, 'STAR',      '52612659',  15),
    ]
    for slot_no, name, price, level in matrix_slots:
        _ensure_slot('matrix', slot_no, name, Decimal(price), level)

    # Global slots 1..16 with alternating phases and names per docs
    global_slots = [
        (1,  'FOUNDATION', '33',    1, 'PHASE-1'),
        (2,  'APEX',       '36',    2, 'PHASE-2'),
        (3,  'SUMMIT',     '86',    3, 'PHASE-1'),
        (4,  'RADIANCE',   '103',   4, 'PHASE-2'),
        (5,  'HORIZON',    '247',   5, 'PHASE-1'),
        (6,  'PARADIGM',   '296',   6, 'PHASE-2'),
        (7,  'CATALYST',   '711',   7, 'PHASE-1'),
        (8,  'ODYSSEY',    '853',   8, 'PHASE-2'),
        (9,  'PINNACLE',   '2047',  9, 'PHASE-1'),
        (10, 'PRIME',      '2457', 10, 'PHASE-2'),
        (11, 'MOMENTUM',   '5897', 11, 'PHASE-1'),
        (12, 'CREST',      '7076', 12, 'PHASE-2'),
        (13, 'VERTEX',     '16984',13, 'PHASE-1'),
        (14, 'LEGACY',     '20381',14, 'PHASE-2'),
        (15, 'ASCEND',     '48796',15, 'PHASE-1'),
        (16, 'EVEREST',    '58555',16, 'PHASE-2'),
    ]
    for slot_no, name, price, level, phase in global_slots:
        _ensure_slot('global', slot_no, name, Decimal(price), level, phase)
    
    print("✅ SlotCatalog seeding completed!")


def seed_ranks():
    """Initialize ranks using RankService"""
    print("\n🌱 Seeding Ranks...")
    try:
        rank_service = RankService()
        result = rank_service.initialize_ranks()
        if result.get('success'):
            print(f"✅ Ranks initialized successfully: {result.get('message', '')}")
        else:
            print(f"⚠️  Ranks initialization warning: {result.get('message', '')}")
    except Exception as e:
        print(f"❌ Error seeding ranks: {e}")


def seed_system_config():
    """Seed essential SystemConfig entries"""
    print("\n🌱 Seeding SystemConfig...")
    
    def _ensure_config(config_key: str, config_value: str, description: str):
        cfg = SystemConfig.objects(config_key=config_key).first()
        if not cfg:
            cfg = SystemConfig(config_key=config_key)
        cfg.config_value = config_value
        cfg.description = description
        cfg.is_active = True
        cfg.updated_at = datetime.utcnow()
        cfg.save()
        print(f"  ✅ {config_key} = {config_value}")

    # Essential configs (based on main.py)
    configs = [
        ("MOTHER_ACCOUNT_ID", "000000000000000000000000", "Mother Account ObjectId for fund routing"),
        ("SPARK_USDT_PER_BNB", "300", "Spark Bonus USDT to BNB conversion rate"),
    ]
    
    for config_key, config_value, description in configs:
        _ensure_config(config_key, config_value, description)
    
    print("✅ SystemConfig seeding completed!")


def seed_settings_singletons():
    """Seed essential Settings singleton documents"""
    print("\n🌱 Seeding Settings Singletons...")
    
    # RankSettings
    if not RankSettings.objects(is_active=True).first():
        RankSettings().save()
        print("  ✅ RankSettings created")
    else:
        print("  ✅ RankSettings already exists")
    
    # PhaseSystemSettings
    if not PhaseSystemSettings.objects().first():
        PhaseSystemSettings().save()
        print("  ✅ PhaseSystemSettings created")
    else:
        print("  ✅ PhaseSystemSettings already exists")
    
    # NewcomerSupportSettings
    if not NewcomerSupportSettings.objects().first():
        NewcomerSupportSettings().save()
        print("  ✅ NewcomerSupportSettings created")
    else:
        print("  ✅ NewcomerSupportSettings already exists")
    
    # DreamMatrixSettings
    if not DreamMatrixSettings.objects().first():
        DreamMatrixSettings().save()
        print("  ✅ DreamMatrixSettings created")
    else:
        print("  ✅ DreamMatrixSettings already exists")
    
    # RoyalCaptainSettings
    if not RoyalCaptainSettings.objects().first():
        RoyalCaptainSettings().save()
        print("  ✅ RoyalCaptainSettings created")
    else:
        print("  ✅ RoyalCaptainSettings already exists")
    
    # PresidentRewardSettings
    if not PresidentRewardSettings.objects().first():
        PresidentRewardSettings().save()
        print("  ✅ PresidentRewardSettings created")
    else:
        print("  ✅ PresidentRewardSettings already exists")
    
    # TopLeaderGiftSettings
    if not TopLeaderGiftSettings.objects().first():
        TopLeaderGiftSettings().save()
        print("  ✅ TopLeaderGiftSettings created")
    else:
        print("  ✅ TopLeaderGiftSettings already exists")
    
    print("✅ Settings Singletons seeding completed!")


def seed_bonus_funds():
    """Seed BonusFund trackers for all fund types and programs"""
    print("\n🌱 Seeding BonusFund entries...")
    
    def _ensure_bonus_fund(fund_type: str, program: str):
        bf = BonusFund.objects(fund_type=fund_type, program=program).first()
        if not bf:
            bf = BonusFund(fund_type=fund_type, program=program)
            bf.status = 'active'
            bf.created_at = datetime.utcnow()
            bf.updated_at = datetime.utcnow()
            bf.save()
            print(f"  ✅ BonusFund created: {fund_type} ({program})")
        else:
            print(f"  ✅ BonusFund exists: {fund_type} ({program})")
    
    fund_types = [
        'spark_bonus', 'royal_captain', 'president_reward',
        'leadership_stipend', 'jackpot_entry', 'partner_incentive',
        'shareholders', 'newcomer_support', 'mentorship_bonus'
    ]
    programs = ['binary', 'matrix', 'global']
    
    for ft in fund_types:
        for pg in programs:
            _ensure_bonus_fund(ft, pg)
    
    print("✅ BonusFund seeding completed!")


def main():
    """Main seeding function"""
    print("=" * 60)
    print("🚀 BitGPT MLM Platform - Database Seed Script")
    print("=" * 60)
    
    try:
        # Connect to database
        print("\n🔌 Connecting to database...")
        connect_to_db()
        print("✅ Database connected successfully!")
        
        # Seed all essential data
        seed_slot_catalog()
        seed_ranks()
        seed_system_config()
        seed_settings_singletons()
        seed_bonus_funds()
        
        print("\n" + "=" * 60)
        print("🎉 All essential data seeding completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

