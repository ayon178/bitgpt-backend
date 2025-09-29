#!/usr/bin/env python3
"""
Migration script to fix Global program currency from USD to USDT
"""
import os
import sys
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parents[0]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from mongoengine import connect
from modules.wallet.model import WalletLedger
from modules.slot.model import SlotCatalog, SlotActivation

def update_global_currency():
    """Update all Global program related records from USD to USDT"""
    
    # Connect to MongoDB
    uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/bitgpt')
    connect(host=uri, alias='default')
    
    print("🔧 Starting Global currency migration from USD to USDT...")
    
    # 1. Update wallet_ledger entries
    wallet_updates = WalletLedger.objects(reason__regex=r'^global_.*').update(
        set__currency='USDT'
    )
    print(f"✅ Updated {wallet_updates} wallet ledger entries")
    
    # 2. Update slot activations
    activation_updates = SlotActivation.objects(program='global').update(
        set__currency='USDT'
    )
    print(f"✅ Updated {activation_updates} slot activation entries")
    
    # 3. Update slot catalog
    catalog_updates = SlotCatalog.objects(program='global').update(
        set__currency='USDT'
    )
    print(f"✅ Updated {catalog_updates} slot catalog entries")
    
    print("🎯 Global currency migration completed!")

if __name__ == "__main__":
    update_global_currency()
