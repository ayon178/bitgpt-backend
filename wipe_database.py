#!/usr/bin/env python3
"""
Wipe all data from all collections in the MongoDB database.
WARNING: This will delete ALL data from all collections!
"""
import sys
from mongoengine import connect, disconnect_all
from datetime import datetime

# Database connection string
MONGO_URI = "mongodb+srv://ayonjd178:ayonjd178@cluster0.wqxk9a6.mongodb.net/bitgpt"

def wipe_all_collections():
    """Wipe all data from all collections in the database"""
    try:
        # Connect to MongoDB
        print("🔌 Connecting to MongoDB...")
        connect('bitgpt', host=MONGO_URI)
        print("✅ Connected to MongoDB")
        
        # Get database instance
        from mongoengine import get_db
        db = get_db()
        
        # Get list of all collections
        collections = db.list_collection_names()
        print(f"\n📋 Found {len(collections)} collections")
        
        # Wipe each collection
        print("\n🗑️  Starting data wipe...")
        wiped_count = 0
        total_documents = 0
        
        for collection_name in collections:
            try:
                collection = db[collection_name]
                doc_count = collection.count_documents({})
                
                if doc_count > 0:
                    print(f"  📦 Wiping {collection_name}: {doc_count} documents...", end=" ")
                    result = collection.delete_many({})
                    print(f"✅ Deleted {result.deleted_count} documents")
                    wiped_count += result.deleted_count
                    total_documents += result.deleted_count
                else:
                    print(f"  📦 {collection_name}: Already empty")
                    
            except Exception as e:
                print(f"  ❌ Error wiping {collection_name}: {str(e)}")
        
        print(f"\n✅ Data wipe completed!")
        print(f"   Collections wiped: {len(collections)}")
        print(f"   Total documents deleted: {wiped_count}")
        
    except Exception as e:
        print(f"\n❌ Error during database wipe: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Disconnect from database
        disconnect_all()
        print("\n🔌 Disconnected from MongoDB")

if __name__ == "__main__":
    print("=" * 60)
    print("MongoDB Database Wipe Tool")
    print("=" * 60)
    print(f"Database: {MONGO_URI}")
    print(f"Time: {datetime.utcnow().isoformat()}")
    print("=" * 60)
    print()
    
    wipe_all_collections()
    
    print("\n" + "=" * 60)
    print("Process completed")
    print("=" * 60)
