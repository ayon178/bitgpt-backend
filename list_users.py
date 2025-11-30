from mongoengine import connect
from modules.user.model import User

connect('bitgpt', host='mongodb://localhost:27017/')

print("Listing all users:")
for user in User.objects:
    print(f"ID: {user.id}, Name: {user.name}, Refer Code: {user.refer_code}")
