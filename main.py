import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Import routers
from auth.router import auth_router
from modules.user.router import user_router
from modules.image.router import image_router
from modules.tree.router import router as tree_router

# DB connection
from core.db import connect_to_db

# Import all models to ensure they are registered
from modules.user import User, PartnerGraph
from modules.slot import SlotCatalog, SlotActivation
from modules.tree import TreePlacement, AutoUpgradeLog
from modules.income import IncomeEvent, SpilloverEvent, LeadershipStipend
from modules.income.bonus_fund import BonusFund, FundDistribution
from modules.wallet import UserWallet, ReserveLedger, WalletLedger
from modules.jackpot import JackpotTicket, JackpotFund
from modules.spark import SparkCycle, TripleEntryReward
import importlib as _importlib
_global_module = _importlib.import_module('modules.global')
GlobalPhaseState = getattr(_global_module, 'GlobalPhaseState')
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

@app.get("/")
async def root():
    return {"message": "Welcome to BitGPT MLM Platform API 🔥"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "BitGPT MLM Platform is running!"}

