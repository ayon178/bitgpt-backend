#!/usr/bin/env python3
"""
Delete All Global Program Data for Fresh Test
"""

import sys
import os
import importlib.util
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.tree.model import TreePlacement
from modules.user.model import User
from bson import ObjectId
from datetime import datetime

# Import GlobalPhaseProgression from auto_upgrade model
from modules.auto_upgrade.model import GlobalPhaseProgression

# Setup database connection
from mongoengine import connect
connect('bitgpt_db', host='mongodb://localhost:27017/bitgpt_db')

def delete_global_data():
    """Delete all Global Program related data"""
    print("🧹 Deleting All Global Program Data")
    print("=" * 50)
    
    try:
        # Delete TreePlacement records for Global program
        global_placements = TreePlacement.objects(program='global')
        placement_count = global_placements.count()
        global_placements.delete()
        print(f"✅ Deleted {placement_count} Global TreePlacement records")
        
        # Delete GlobalPhaseProgression records
        global_progressions = GlobalPhaseProgression.objects()
        progression_count = global_progressions.count()
        global_progressions.delete()
        print(f"✅ Deleted {progression_count} GlobalPhaseProgression records")
        
        # Delete test users (users with test emails)
        test_users = User.objects(email__contains='test')
        test_user_count = test_users.count()
        test_users.delete()
        print(f"✅ Deleted {test_user_count} test users")
        
        # Delete users with test UIDs
        test_uid_users = User.objects(uid__contains='TEST')
        test_uid_count = test_uid_users.count()
        test_uid_users.delete()
        print(f"✅ Deleted {test_uid_count} users with TEST UIDs")
        
        # Delete users with test refer codes
        test_refer_users = User.objects(refer_code__contains='RC176')
        test_refer_count = test_refer_users.count()
        test_refer_users.delete()
        print(f"✅ Deleted {test_refer_count} users with test refer codes")
        
        print(f"\n🎉 Global Program Data Cleanup Completed!")
        print("=" * 50)
        
        # Verify cleanup
        remaining_global_placements = TreePlacement.objects(program='global').count()
        remaining_progressions = GlobalPhaseProgression.objects().count()
        remaining_test_users = User.objects(email__contains='test').count()
        
        print(f"\n📊 Verification:")
        print(f"Remaining Global TreePlacements: {remaining_global_placements}")
        print(f"Remaining GlobalPhaseProgressions: {remaining_progressions}")
        print(f"Remaining test users: {remaining_test_users}")
        
        if remaining_global_placements == 0 and remaining_progressions == 0 and remaining_test_users == 0:
            print("✅ Database is clean and ready for fresh test!")
        else:
            print("⚠️ Some data still remains")
            
    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")

if __name__ == "__main__":
    delete_global_data()
