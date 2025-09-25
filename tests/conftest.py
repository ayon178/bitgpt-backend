import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..'))
BACKEND_ROOT = os.path.join(PROJECT_ROOT, 'backend')

# Ensure both backend root (for 'modules.*') and project root (for 'backend.*') are importable
for path in (BACKEND_ROOT, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)
