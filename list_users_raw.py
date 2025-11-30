from pymongo import MongoClient
from bson import ObjectId

client = MongoClient('mongodb://localhost:27017/')
db = client['bitgpt']

print("Listing all users (raw data):")
for user in db.user.find():
    print(f"ID: {user.get('_id')}, Name: {user.get('name')}, Refer Code: {user.get('refer_code')}, Username: {user.get('username')}")
