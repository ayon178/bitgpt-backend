import unittest
from unittest.mock import patch, Mock
from fastapi import FastAPI
from fastapi.testclient import TestClient
import sys
import os

# Ensure backend package is importable when running tests from repo root
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.modules.matrix.router import router as matrix_router
from backend.modules.matrix.router import authentication_service


class TestMatrixE2EFlow(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(matrix_router)
        self.client = TestClient(self.app)

        self.user_id = "507f1f77bcf86cd799439011"
        self.referrer_id = "507f1f77bcf86cd799439012"

        # Mock auth for all requests
        self.auth_patcher = patch('backend.modules.matrix.router.authentication_service.verify_authentication')
        self.mock_auth = self.auth_patcher.start()
        self.mock_auth.return_value = {"user_id": self.user_id, "role": "admin", "email": "test@example.com"}

        # Patch MatrixService for end-to-end flow assertions without DB
        self.service_patcher = patch('backend.modules.matrix.router.MatrixService')
        self.mock_service_class = self.service_patcher.start()
        self.mock_service = Mock()
        self.mock_service_class.return_value = self.mock_service

        # Join returns success
        self.mock_service.join_matrix.return_value = {
            "success": True,
            "user_id": self.user_id,
            "referrer_id": self.referrer_id,
            "slot_activated": 1
        }

        # Middle-three earnings sufficient
        self.mock_service.get_middle_three_earnings.return_value = {
            "success": True,
            "earnings": {
                "user_id": self.user_id,
                "middle_three_earnings": 150.0,
                "sufficient_for_upgrade": True,
                "next_slot_cost": 100.0
            }
        }

        # Trigger auto upgrade succeeds
        self.mock_service.trigger_automatic_upgrade.return_value = {
            "success": True,
            "upgraded": True,
            "from_slot": 1,
            "to_slot": 2
        }

    def tearDown(self):
        self.auth_patcher.stop()
        self.service_patcher.stop()

    def test_join_to_middle_three_to_auto_upgrade_flow(self):
        # Step 1: Join Matrix
        resp_join = self.client.post(
            "/matrix/join",
            json={"user_id": self.user_id, "referrer_id": self.referrer_id, "tx_hash": "tx", "amount": 11.0},
            headers={"Authorization": "Bearer test"}
        )
        self.assertEqual(resp_join.status_code, 200)
        self.assertTrue(resp_join.json()["success"])

        # Step 2: Check middle-three earnings
        resp_m3 = self.client.get(
            f"/matrix/middle-three-earnings/{self.user_id}",
            headers={"Authorization": "Bearer test"}
        )
        self.assertEqual(resp_m3.status_code, 200)
        self.assertTrue(resp_m3.json()["success"])
        data = resp_m3.json()["data"]
        self.assertTrue(data.get("sufficient_for_upgrade", False))

        # Step 3: Trigger auto-upgrade
        resp_auto = self.client.post(
            "/matrix/trigger-auto-upgrade",
            params={"user_id": self.user_id, "slot_no": 1},
            headers={"Authorization": "Bearer test"}
        )
        self.assertEqual(resp_auto.status_code, 200)
        self.assertTrue(resp_auto.json()["success"])
        up = resp_auto.json()["data"]
        self.assertTrue(up.get("upgraded", False))
        self.assertEqual(up.get("from_slot"), 1)
        self.assertEqual(up.get("to_slot"), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)


