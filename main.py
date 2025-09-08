import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize the FastAPI app
app = FastAPI(title="BitGPT MLM Platform", version="1.0.0")

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

@app.get("/")
async def root():
    return {"message": "Welcome to BitGPT MLM Platform API 🔥"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "BitGPT MLM Platform is running!"}

