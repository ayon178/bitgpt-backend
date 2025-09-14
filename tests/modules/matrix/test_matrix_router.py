"""
Unit Tests for Matrix Router (API Endpoints)

This module contains comprehensive unit tests for the Matrix Program API endpoints,
including all phases: Core Matrix, Recycle System, Auto Upgrade, Dream Matrix,
Mentorship Bonus, Manual Upgrades, and Special Programs Integration.

Test Coverage:
- Matrix join API endpoints
- Tree placement API endpoints
- Recycle system API endpoints
- Auto upgrade API endpoints
- Dream Matrix API endpoints
- Mentorship Bonus API endpoints
- Manual upgrade API endpoints
- Special programs integration API endpoints
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.matrix.router import router
from modules.matrix.service import MatrixService


class TestMatrixRouter(unittest.TestCase):
    """Test cases for Matrix router API endpoints."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        
        self.test_user_id = "507f1f77bcf86cd799439011"
        self.test_referrer_id = "507f1f77bcf86cd799439012"
        
        # Mock authentication
        self.mock_auth = {
            "user_id": self.test_user_id,
            "username": "testuser",
            "email": "test@example.com"
        }
    
    def tearDown(self):
        """Clean up after each test method."""
        pass
    
    # ==================== CORE MATRIX API TESTS ====================
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_join_matrix_endpoint_success(self, mock_service_class, mock_auth):
        """Test successful Matrix join API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.join_matrix.return_value = {
            "success": True,
            "user_id": self.test_user_id,
            "referrer_id": self.test_referrer_id,
            "slot_activated": 1
        }
        
        # Make request
        response = self.client.post(
            f"/matrix/join/{self.test_user_id}/{self.test_referrer_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["user_id"], self.test_user_id)
        self.assertEqual(data["data"]["referrer_id"], self.test_referrer_id)
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    def test_join_matrix_endpoint_unauthorized(self, mock_auth):
        """Test Matrix join API endpoint with unauthorized access."""
        # Mock authentication failure
        mock_auth.side_effect = HTTPException(status_code=401, detail="Unauthorized")
        
        # Make request
        response = self.client.post(
            f"/matrix/join/{self.test_user_id}/{self.test_referrer_id}",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 401)
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_get_matrix_status_endpoint(self, mock_service_class, mock_auth):
        """Test Matrix status API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_matrix_status.return_value = {
            "success": True,
            "status": {
                "user_id": self.test_user_id,
                "current_slot": 1,
                "slot_name": "STARTER",
                "total_members": 0,
                "is_complete": False
            }
        }
        
        # Make request
        response = self.client.get(
            f"/matrix/status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["user_id"], self.test_user_id)
        self.assertEqual(data["data"]["current_slot"], 1)
    
    # ==================== RECYCLE SYSTEM API TESTS ====================
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_get_recycle_tree_endpoint(self, mock_service_class, mock_auth):
        """Test recycle tree API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_recycle_tree.return_value = {
            "success": True,
            "tree": {
                "user_id": self.test_user_id,
                "slot_number": 1,
                "recycle_no": 1,
                "is_complete": True,
                "nodes": []
            }
        }
        
        # Make request
        response = self.client.get(
            f"/matrix/recycle-tree?user_id={self.test_user_id}&slot=1&recycle_no=1",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["user_id"], self.test_user_id)
        self.assertEqual(data["data"]["slot_number"], 1)
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_get_recycles_endpoint(self, mock_service_class, mock_auth):
        """Test recycles list API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_recycles.return_value = {
            "success": True,
            "recycles": [
                {
                    "recycle_no": 1,
                    "is_complete": True,
                    "created_at": "2024-01-01T00:00:00Z",
                    "completed_at": "2024-01-01T00:00:00Z"
                }
            ]
        }
        
        # Make request
        response = self.client.get(
            f"/matrix/recycles?user_id={self.test_user_id}&slot=1",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["recycle_no"], 1)
    
    # ==================== AUTO UPGRADE SYSTEM API TESTS ====================
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_get_middle_three_earnings_endpoint(self, mock_service_class, mock_auth):
        """Test middle three earnings API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_middle_three_earnings.return_value = {
            "success": True,
            "earnings": {
                "user_id": self.test_user_id,
                "middle_three_earnings": 150.0,
                "sufficient_for_upgrade": True,
                "next_slot_cost": 100.0
            }
        }
        
        # Make request
        response = self.client.get(
            f"/matrix/middle-three-earnings/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["middle_three_earnings"], 150.0)
        self.assertTrue(data["data"]["sufficient_for_upgrade"])
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_trigger_auto_upgrade_endpoint(self, mock_service_class, mock_auth):
        """Test trigger auto upgrade API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.trigger_automatic_upgrade.return_value = {
            "success": True,
            "upgraded": True,
            "from_slot": 1,
            "to_slot": 2
        }
        
        # Make request
        response = self.client.post(
            f"/matrix/trigger-auto-upgrade/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["data"]["upgraded"])
        self.assertEqual(data["data"]["from_slot"], 1)
        self.assertEqual(data["data"]["to_slot"], 2)
    
    # ==================== DREAM MATRIX SYSTEM API TESTS ====================
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_get_dream_matrix_status_endpoint(self, mock_service_class, mock_auth):
        """Test Dream Matrix status API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_dream_matrix_status.return_value = {
            "success": True,
            "status": {
                "user_id": self.test_user_id,
                "eligible": True,
                "direct_partners": 3,
                "total_earnings": 800.0
            }
        }
        
        # Make request
        response = self.client.get(
            f"/matrix/dream-matrix-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["data"]["eligible"])
        self.assertEqual(data["data"]["direct_partners"], 3)
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_dream_matrix_distribute_endpoint(self, mock_service_class, mock_auth):
        """Test Dream Matrix distribute API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.distribute_dream_matrix_earnings.return_value = {
            "success": True,
            "distributed": True,
            "total_amount": 800.0
        }
        
        # Make request
        response = self.client.post(
            f"/matrix/dream-matrix-distribute/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["data"]["distributed"])
        self.assertEqual(data["data"]["total_amount"], 800.0)
    
    # ==================== MENTORSHIP BONUS SYSTEM API TESTS ====================
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_get_mentorship_status_endpoint(self, mock_service_class, mock_auth):
        """Test Mentorship Bonus status API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_mentorship_status.return_value = {
            "success": True,
            "status": {
                "user_id": self.test_user_id,
                "super_upline": self.test_referrer_id,
                "direct_of_direct_partners": 3,
                "total_commission": 100.0
            }
        }
        
        # Make request
        response = self.client.get(
            f"/matrix/mentorship-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["user_id"], self.test_user_id)
        self.assertEqual(data["data"]["super_upline"], self.test_referrer_id)
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_mentorship_bonus_distribute_endpoint(self, mock_service_class, mock_auth):
        """Test Mentorship Bonus distribute API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.distribute_mentorship_bonus.return_value = {
            "success": True,
            "distributed": True,
            "commission_amount": 100.0
        }
        
        # Make request
        response = self.client.post(
            f"/matrix/mentorship-bonus-distribute/{self.test_referrer_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["data"]["distributed"])
        self.assertEqual(data["data"]["commission_amount"], 100.0)
    
    # ==================== MANUAL UPGRADE SYSTEM API TESTS ====================
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_upgrade_slot_endpoint(self, mock_service_class, mock_auth):
        """Test Matrix slot upgrade API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.upgrade_matrix_slot.return_value = {
            "success": True,
            "user_id": self.test_user_id,
            "from_slot_no": 1,
            "to_slot_no": 2,
            "upgrade_cost": 100.0
        }
        
        # Make request
        response = self.client.post(
            f"/matrix/upgrade-slot/{self.test_user_id}",
            json={
                "from_slot_no": 1,
                "to_slot_no": 2,
                "upgrade_cost": 100.0
            },
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["from_slot_no"], 1)
        self.assertEqual(data["data"]["to_slot_no"], 2)
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_get_upgrade_options_endpoint(self, mock_service_class, mock_auth):
        """Test Matrix upgrade options API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_matrix_upgrade_options.return_value = {
            "success": True,
            "options": [
                {
                    "slot_number": 2,
                    "slot_name": "BRONZE",
                    "slot_value": 33,
                    "upgrade_cost": 99
                }
            ]
        }
        
        # Make request
        response = self.client.get(
            f"/matrix/upgrade-options/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["slot_number"], 2)
    
    # ==================== SPECIAL PROGRAMS INTEGRATION API TESTS ====================
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_get_rank_status_endpoint(self, mock_service_class, mock_auth):
        """Test Rank System status API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_user_rank_status.return_value = {
            "success": True,
            "status": {
                "user_id": self.test_user_id,
                "current_rank": "Bitron",
                "rank_number": 1,
                "total_slots": 1
            }
        }
        
        # Make request
        response = self.client.get(
            f"/matrix/rank-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["current_rank"], "Bitron")
        self.assertEqual(data["data"]["rank_number"], 1)
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_get_global_program_status_endpoint(self, mock_service_class, mock_auth):
        """Test Global Program status API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_global_program_status.return_value = {
            "success": True,
            "status": {
                "user_id": self.test_user_id,
                "integrated": True,
                "contribution": 5.0,
                "distribution": {
                    "level": 2.0,
                    "profit": 1.5,
                    "royal_captain": 0.75,
                    "president_reward": 0.75
                }
            }
        }
        
        # Make request
        response = self.client.get(
            f"/matrix/global-program-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["data"]["integrated"])
        self.assertEqual(data["data"]["contribution"], 5.0)
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_get_leadership_stipend_status_endpoint(self, mock_service_class, mock_auth):
        """Test Leadership Stipend status API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_leadership_stipend_status.return_value = {
            "success": True,
            "status": {
                "user_id": self.test_user_id,
                "eligible": True,
                "matrix_slot": 10,
                "daily_return": 2.2528,
                "distribution": {
                    "level_10": 0.033792,
                    "level_11": 0.022528,
                    "level_12": 0.011264
                }
            }
        }
        
        # Make request
        response = self.client.get(
            f"/matrix/leadership-stipend-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["data"]["eligible"])
        self.assertEqual(data["data"]["matrix_slot"], 10)
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_get_jackpot_program_status_endpoint(self, mock_service_class, mock_auth):
        """Test Jackpot Program status API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_jackpot_program_status.return_value = {
            "success": True,
            "status": {
                "user_id": self.test_user_id,
                "matrix_slot": 5,
                "contribution": 17.82,
                "coupons_awarded": 1,
                "fund_distribution": {
                    "open_pool": 8.91,
                    "top_direct_promoters": 5.346,
                    "top_buyers": 1.782,
                    "binary_contribution": 0.891
                }
            }
        }
        
        # Make request
        response = self.client.get(
            f"/matrix/jackpot-program-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["matrix_slot"], 5)
        self.assertEqual(data["data"]["coupons_awarded"], 1)
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_get_ngs_status_endpoint(self, mock_service_class, mock_auth):
        """Test NGS status API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_ngs_status.return_value = {
            "success": True,
            "status": {
                "user_id": self.test_user_id,
                "matrix_slot": 1,
                "benefits": {
                    "instant_bonus": 0.55,
                    "extra_earning": 0.33,
                    "upline_rank_bonus": 0.22,
                    "total_benefits": 1.10
                }
            }
        }
        
        # Make request
        response = self.client.get(
            f"/matrix/ngs-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["matrix_slot"], 1)
        self.assertEqual(data["data"]["benefits"]["total_benefits"], 1.10)
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_get_mentorship_bonus_status_endpoint(self, mock_service_class, mock_auth):
        """Test Mentorship Bonus status API endpoint."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_mentorship_bonus_status.return_value = {
            "success": True,
            "status": {
                "user_id": self.test_user_id,
                "matrix_slot": 1,
                "benefits": {
                    "direct_of_direct_commission": 1.10,
                    "total_benefits": 1.10
                }
            }
        }
        
        # Make request
        response = self.client.get(
            f"/matrix/mentorship-bonus-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["matrix_slot"], 1)
        self.assertEqual(data["data"]["benefits"]["total_benefits"], 1.10)
    
    # ==================== ERROR HANDLING TESTS ====================
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_api_error_handling(self, mock_service_class, mock_auth):
        """Test API error handling."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service error
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.join_matrix.return_value = {
            "success": False,
            "error": "Test error message"
        }
        
        # Make request
        response = self.client.post(
            f"/matrix/join/{self.test_user_id}/{self.test_referrer_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Test error message", data["error"])
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    def test_api_unauthorized_access(self, mock_auth):
        """Test API unauthorized access."""
        # Mock authentication failure
        mock_auth.side_effect = HTTPException(status_code=403, detail="Unauthorized")
        
        # Make request
        response = self.client.get(
            f"/matrix/status/{self.test_user_id}",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 403)


class TestMatrixAPIIntegration(unittest.TestCase):
    """Integration tests for Matrix API endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        
        self.test_user_id = "507f1f77bcf86cd799439011"
        self.test_referrer_id = "507f1f77bcf86cd799439012"
        
        # Mock authentication
        self.mock_auth = {
            "user_id": self.test_user_id,
            "username": "testuser",
            "email": "test@example.com"
        }
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_full_matrix_workflow_api(self, mock_service_class, mock_auth):
        """Test complete Matrix workflow through API endpoints."""
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Mock successful responses
        mock_service.join_matrix.return_value = {
            "success": True,
            "user_id": self.test_user_id,
            "referrer_id": self.test_referrer_id,
            "slot_activated": 1
        }
        
        mock_service.get_matrix_status.return_value = {
            "success": True,
            "status": {
                "user_id": self.test_user_id,
                "current_slot": 1,
                "slot_name": "STARTER",
                "total_members": 1,
                "is_complete": False
            }
        }
        
        mock_service.upgrade_matrix_slot.return_value = {
            "success": True,
            "user_id": self.test_user_id,
            "from_slot_no": 1,
            "to_slot_no": 2,
            "upgrade_cost": 100.0
        }
        
        # Test Matrix join
        join_response = self.client.post(
            f"/matrix/join/{self.test_user_id}/{self.test_referrer_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        self.assertEqual(join_response.status_code, 200)
        
        # Test Matrix status
        status_response = self.client.get(
            f"/matrix/status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        self.assertEqual(status_response.status_code, 200)
        
        # Test Matrix upgrade
        upgrade_response = self.client.post(
            f"/matrix/upgrade-slot/{self.test_user_id}",
            json={
                "from_slot_no": 1,
                "to_slot_no": 2,
                "upgrade_cost": 100.0
            },
            headers={"Authorization": "Bearer test_token"}
        )
        self.assertEqual(upgrade_response.status_code, 200)
        
        # Verify all service methods were called
        mock_service.join_matrix.assert_called_once()
        mock_service.get_matrix_status.assert_called_once()
        mock_service.upgrade_matrix_slot.assert_called_once()


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
