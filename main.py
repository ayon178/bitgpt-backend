import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from auth.router import auth_router
from modules.user.router import user_router
from modules.image.router import image_router
from modules.tree.router import router as tree_router
# Newly added module routers
from modules.matrix.router import router as matrix_router
from modules.commission.router import router as commission_router
from modules.auto_upgrade.router import router as auto_upgrade_router
from modules.rank.router import router as rank_router
from modules.royal_captain.router import router as royal_captain_router
from modules.president_reward.router import router as president_reward_router
from modules.leadership_stipend.router import router as leadership_stipend_router
from modules.mentorship.router import router as mentorship_router
from modules.dream_matrix.router import router as dream_matrix_router
from modules.newcomer_support.router import router as newcomer_support_router
from modules.top_leader_gift.router import router as top_leader_gift_router
from modules.missed_profit.router import router as missed_profit_router
from modules.phase_system.router import router as phase_system_router
from modules.recycle.router import router as recycle_router
from modules.spillover.router import router as spillover_router
from modules.jackpot.router import router as jackpot_router
from modules.spark.router import router as spark_router
from modules.binary.router import router as binary_router
from importlib import import_module
# Dynamic import because 'global' is a Python keyword
global_router = import_module('modules.global.router').router

# DB connection
from core.db import connect_to_db

# Import all models to ensure they are registered
from modules.user import User, PartnerGraph
from modules.slot import SlotCatalog, SlotActivation
from modules.tree import TreePlacement
from modules.income import IncomeEvent, SpilloverEvent
from modules.leadership_stipend.model import LeadershipStipend
from modules.income.bonus_fund import BonusFund, FundDistribution
from modules.wallet import UserWallet, ReserveLedger, WalletLedger
from modules.jackpot import JackpotTicket, JackpotFund
from modules.spark import SparkCycle, TripleEntryReward
# TODO: Re-enable GlobalPhaseState import when models are implemented in modules/global/model.py
from modules.qualification import Qualification
from modules.blockchain import BlockchainEvent, SystemConfig
from modules.rank.service import RankService
from modules.slot.model import SlotCatalog
from decimal import Decimal
from datetime import datetime
from modules.rank.model import RankSettings
from modules.phase_system.model import PhaseSystemSettings
from modules.newcomer_support.model import NewcomerSupportSettings
from modules.dream_matrix.model import DreamMatrixSettings
from modules.royal_captain.model import RoyalCaptainSettings
from modules.president_reward.model import PresidentRewardSettings
from modules.top_leader_gift.model import TopLeaderGiftSettings

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize the FastAPI app
app = FastAPI(title="BitGPT MLM Platform", version="1.0.0")

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Connect to MongoDB
connect_to_db()

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/user", tags=["User Management"])
app.include_router(image_router, prefix="/image", tags=["Image"])
app.include_router(tree_router, prefix="/tree", tags=["Tree Management"])
# Include newly added routers (per PROJECT_DOCUMENTATION.md)
app.include_router(matrix_router)
app.include_router(commission_router)
app.include_router(auto_upgrade_router)
app.include_router(rank_router)
app.include_router(royal_captain_router)
app.include_router(president_reward_router)
app.include_router(leadership_stipend_router)
app.include_router(mentorship_router)
app.include_router(dream_matrix_router)
app.include_router(newcomer_support_router)
app.include_router(top_leader_gift_router)
app.include_router(missed_profit_router)
app.include_router(phase_system_router)
app.include_router(recycle_router)
app.include_router(spillover_router)
app.include_router(jackpot_router)
app.include_router(spark_router)
app.include_router(binary_router)
app.include_router(matrix_router)
app.include_router(global_router)
from modules.wallet.router import router as wallet_router
app.include_router(wallet_router)

@app.on_event("startup")
async def startup_initializer():
    """Idempotent production initializer: ensure ranks and essential slots exist."""
    try:
        # Ensure DB is connected
        connect_to_db()

        # Initialize ranks (creates missing, updates existing)
        RankService().initialize_ranks()

        # Ensure SlotCatalog entries exist (complete per docs)
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

        # Ensure baseline SystemConfig distribution keys (per docs)
        def _ensure_config(config_key: str, config_value: str, description: str):
            cfg = SystemConfig.objects(config_key=config_key).first()
            if not cfg:
                cfg = SystemConfig(config_key=config_key)
            cfg.config_value = config_value
            cfg.description = description
            cfg.is_active = True
            cfg.updated_at = datetime.utcnow()
            cfg.save()

        # Binary distribution
        _ensure_config('binary_distribution_spark', '8', 'Binary Spark Bonus percentage')
        _ensure_config('binary_distribution_royal_captain', '4', 'Binary Royal Captain percentage')
        _ensure_config('binary_distribution_president', '3', 'Binary President Reward percentage')
        _ensure_config('binary_distribution_leadership', '5', 'Binary Leadership Stipend percentage')
        _ensure_config('binary_distribution_jackpot', '5', 'Binary Jackpot Entry percentage')
        _ensure_config('binary_distribution_partner', '10', 'Binary Partner Incentive percentage')
        _ensure_config('binary_distribution_level', '60', 'Binary Level Payout percentage')
        _ensure_config('binary_distribution_shareholders', '5', 'Binary Shareholders percentage')

        # Matrix distribution
        _ensure_config('matrix_distribution_spark', '8', 'Matrix Spark Bonus percentage')
        _ensure_config('matrix_distribution_royal_captain', '4', 'Matrix Royal Captain percentage')
        _ensure_config('matrix_distribution_president', '3', 'Matrix President Reward percentage')
        _ensure_config('matrix_distribution_leadership', '5', 'Matrix Leadership Stipend percentage')
        _ensure_config('matrix_distribution_jackpot', '5', 'Matrix Jackpot Entry percentage')
        _ensure_config('matrix_distribution_partner', '10', 'Matrix Partner Incentive percentage')
        _ensure_config('matrix_distribution_level', '60', 'Matrix Level Payout percentage')
        _ensure_config('matrix_distribution_shareholders', '5', 'Matrix Shareholders percentage')

        # Global distribution
        _ensure_config('global_distribution_partner', '10', 'Global Partner Incentive percentage')
        _ensure_config('global_distribution_level', '60', 'Global Level Payout percentage')
        _ensure_config('global_distribution_rc', '4', 'Global Royal Captain percentage')
        _ensure_config('global_distribution_president', '3', 'Global President Reward percentage')
        _ensure_config('global_distribution_triple_entry', '5', 'Global Triple Entry Reward percentage')
        _ensure_config('global_distribution_shareholders', '5', 'Global Shareholders percentage')

        # Ensure RankSettings singleton
        if not RankSettings.objects(is_active=True).first():
            RankSettings().save()

        # Ensure Phase System Settings singleton with defaults per docs
        if not PhaseSystemSettings.objects().first():
            PhaseSystemSettings().save()

        # Ensure Newcomer Support Settings singleton
        if not NewcomerSupportSettings.objects().first():
            NewcomerSupportSettings().save()

        # Ensure Dream Matrix Settings singleton
        if not DreamMatrixSettings.objects().first():
            DreamMatrixSettings().save()

        # Ensure Royal Captain Settings singleton
        if not RoyalCaptainSettings.objects().first():
            RoyalCaptainSettings().save()

        # Ensure President Reward Settings singleton
        if not PresidentRewardSettings.objects().first():
            PresidentRewardSettings().save()

        # Ensure Top Leader Gift Settings singleton
        if not TopLeaderGiftSettings.objects().first():
            TopLeaderGiftSettings().save()

        # Ensure BonusFund trackers exist for each fund/program
        def _ensure_bonus_fund(fund_type: str, program: str):
            bf = BonusFund.objects(fund_type=fund_type, program=program).first()
            if not bf:
                bf = BonusFund(fund_type=fund_type, program=program)
                bf.status = 'active'
                bf.created_at = datetime.utcnow()
                bf.updated_at = datetime.utcnow()
                bf.save()

        fund_types = [
            'spark_bonus', 'royal_captain', 'president_reward',
            'leadership_stipend', 'jackpot_entry', 'partner_incentive',
            'shareholders', 'newcomer_support', 'mentorship_bonus'
        ]
        programs = ['binary', 'matrix', 'global']
        for ft in fund_types:
            for pg in programs:
                _ensure_bonus_fund(ft, pg)
    except Exception:
        # Startup should not crash app if seeding fails; logs are preferred in real env
        pass

@app.get("/")
async def root():
    return {"message": "Welcome to BitGPT MLM Platform API 🔥"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "BitGPT MLM Platform is running!"}

