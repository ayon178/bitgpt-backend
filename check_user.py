import sys
sys.path.insert(0, ".")

from modules.user.model import User

user_id = "69018a522791b8ae0143c6d6"

user = User.objects(id=user_id).first()

if user:
    print(f"User ID: {user.id}")
    print(f"UID: {user.uid}")
    print(f"Name: {user.name}")
    print(f"Refer Code: {user.refer_code}")
else:
    print("User not found")

