from mongoengine import connect
from modules.slot.model import SlotCatalog
from core.config import MONGO_URI

print(f"Connecting to DB...")
connect('bitgpt', host=MONGO_URI)
print("✅ DB connected")

print("Querying SlotCatalog for Matrix Slot 2...")
try:
    catalog = SlotCatalog.objects(
        program='matrix',
        slot_no=2,
        is_active=True
    ).first()
    
    if catalog:
        print(f"✅ Found Catalog: {catalog.name}, Price: {catalog.price}")
    else:
        print("❌ Catalog NOT found")
        
except Exception as e:
    print(f"❌ Error querying catalog: {e}")

print("Done")
