#!/usr/bin/env python3
"""
Delete Global Program Data from Database
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mongoengine import connect
import importlib.util
spec = importlib.util.spec_from_file_location("global_model", "modules/global/model.py")
global_model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(global_model)
GlobalTeamMember = global_model.GlobalTeamMember
GlobalDistribution = global_model.GlobalDistribution
GlobalTreeStructure = global_model.GlobalTreeStructure
GlobalPhaseSeat = global_model.GlobalPhaseSeat
from modules.tree.model import TreePlacement
from modules.income.model import IncomeEvent
from modules.income.bonus_fund import BonusFund
from modules.wallet.model import UserWallet, ReserveLedger
from modules.wallet.service import WalletService

def delete_global_data():
    """Delete all Global Program related data"""
    print("🗑️ Deleting Global Program Data...")
    print("=" * 50)
    
    try:
        # Connect to database
        connect('bitgpt', host='mongodb://localhost:27017/')
        
        # Delete Global Program collections
        collections_to_clear = [
            ("GlobalTeamMember", GlobalTeamMember),
            ("GlobalDistribution", GlobalDistribution), 
            ("GlobalTreeStructure", GlobalTreeStructure),
            ("GlobalPhaseSeat", GlobalPhaseSeat),
            ("TreePlacement (Global)", TreePlacement.objects(program='global')),
            ("IncomeEvent (Global)", IncomeEvent.objects(program='global')),
            ("BonusFund (Global)", BonusFund.objects(program='global')),
        ]
        
        total_deleted = 0
        
        for collection_name, collection in collections_to_clear:
            if hasattr(collection, 'objects'):
                # For MongoEngine models
                if collection_name == "TreePlacement (Global)":
                    count = collection.count()
                    collection.delete()
                elif collection_name == "IncomeEvent (Global)":
                    count = collection.count()
                    collection.delete()
                elif collection_name == "BonusFund (Global)":
                    count = collection.count()
                    collection.delete()
                else:
                    count = collection.objects.count()
                    collection.objects.delete()
            else:
                # For querysets
                count = collection.count()
                collection.delete()
            
            print(f"✅ Deleted {count} records from {collection_name}")
            total_deleted += count
        
        # Reset user global_joined status
        from modules.user.model import User
        users = User.objects(global_joined=True)
        user_count = users.count()
        users.update(set__global_joined=False)
        print(f"✅ Reset global_joined status for {user_count} users")
        
        print(f"\n🎉 Total {total_deleted} records deleted from Global Program")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ Error deleting Global data: {str(e)}")
        return False

if __name__ == "__main__":
    delete_global_data()
