import os
import sys
from mongoengine import connect

try:
    # Ensure a default MongoDB connection for tests
    from core.config import MONGO_URI
    connect(host=MONGO_URI)
except Exception:
    # Fallback: attempt localhost default if config import fails
    try:
        connect(host="mongodb://localhost:27017/bitgpt")
    except Exception:
        pass

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..'))
BACKEND_ROOT = os.path.join(PROJECT_ROOT, 'backend')

# Ensure both backend root (for 'modules.*') and project root (for 'backend.*') are importable
for path in (BACKEND_ROOT, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)
