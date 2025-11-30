from pymongo import MongoClient
from core.config import MONGO_URI
from bson import ObjectId

client = MongoClient(MONGO_URI)
db = client['bitgpt']

print("Listing ROOT user details:")
root = db.users.find_one({'refer_code': 'ROOT001'})
if root:
    print(root)
else:
    print("ROOT user not found by refer_code")

root_by_id = db.users.find_one({'_id': ObjectId('68bee3aec1eac053757f5cf1')})
if root_by_id:
    print("Found by ID:", root_by_id)
else:
    print("ROOT user not found by ID")
