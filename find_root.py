from core.db import connect_to_db
from modules.user.model import User

def find_root():
    connect_to_db()
    # Find a user with no referrer or a specific root code
    root = User.objects(refered_by=None).first()
    if root:
        print(f"Found root: {root.id}, {root.refer_code}")
    else:
        # Try finding by known root code pattern or just the first user
        root = User.objects().first()
        if root:
            print(f"Found user (using as root): {root.id}, {root.refer_code}")
        else:
            print("No users found")

if __name__ == "__main__":
    find_root()
