import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.db import connect_to_db
from modules.matrix.service import MatrixService


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/upgrade_matrix_to_slot5.py <USER_ID>")
        return
    user_id = sys.argv[1]
    connect_to_db()
    svc = MatrixService()
    res = svc.upgrade_matrix_slot(user_id, 1, 5, 'manual')
    print(res)


if __name__ == '__main__':
    main()
