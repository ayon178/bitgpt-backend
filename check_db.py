from pymongo import MongoClient
from core.config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client['bitgpt']

print("Collections in bitgpt:")
print(db.list_collection_names())

print("\nDatabases:")
print(client.list_database_names())
