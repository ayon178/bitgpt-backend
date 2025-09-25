"""
API Integration Tests for Matrix Program

This module contains comprehensive API integration tests for the Matrix Program,
including end-to-end API workflows, authentication, error handling, and
cross-program API integration.

Test Coverage:
- End-to-end API workflows
- Authentication and authorization
- API error handling
- Cross-program API integration
- Performance testing
- Real-world API scenarios
"""

import pytest
import unittest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.modules.matrix.router import router
from modules.matrix.service import MatrixService
from tests.modules.matrix.test_config import MatrixTestConfig, MatrixTestFixtures, MatrixTestUtils


class TestMatrixAPIIntegration(unittest.TestCase):
    """API integration tests for Matrix Program."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        
        self.test_user_id = MatrixTestConfig.TEST_USER_ID
        self.test_referrer_id = MatrixTestConfig.TEST_REFERRER_ID
        
        # Mock authentication
        self.mock_auth = {
            "user_id": self.test_user_id,
            "username": "testuser",
            "email": "test@example.com"
        }
    
    def tearDown(self):
        """Clean up test data."""
        pass
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_complete_matrix_join_api_workflow(self, mock_service_class, mock_auth):
        """Test complete Matrix join API workflow."""
        print("\n🔄 Testing Complete Matrix Join API Workflow")
        
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
        
        # Make Matrix join request
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
        
        print("✅ Complete Matrix join API workflow test passed")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_complete_matrix_upgrade_api_workflow(self, mock_service_class, mock_auth):
        """Test complete Matrix upgrade API workflow."""
        print("\n🔄 Testing Complete Matrix Upgrade API Workflow")
        
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
        
        # Make Matrix upgrade request
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
        
        print("✅ Complete Matrix upgrade API workflow test passed")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_complete_matrix_recycle_api_workflow(self, mock_service_class, mock_auth):
        """Test complete Matrix recycle API workflow."""
        print("\n🔄 Testing Complete Matrix Recycle API Workflow")
        
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
        
        # Make recycle tree request
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
        
        print("✅ Complete Matrix recycle API workflow test passed")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_complete_matrix_auto_upgrade_api_workflow(self, mock_service_class, mock_auth):
        """Test complete Matrix auto upgrade API workflow."""
        print("\n🔄 Testing Complete Matrix Auto Upgrade API Workflow")
        
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
        
        mock_service.trigger_automatic_upgrade.return_value = {
            "success": True,
            "upgraded": True,
            "from_slot": 1,
            "to_slot": 2
        }
        
        # Make middle three earnings request
        response1 = self.client.get(
            f"/matrix/middle-three-earnings/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Make trigger auto upgrade request
        response2 = self.client.post(
            f"/matrix/trigger-auto-upgrade/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        data1 = response1.json()
        data2 = response2.json()
        
        self.assertTrue(data1["success"])
        self.assertTrue(data2["success"])
        self.assertTrue(data2["data"]["upgraded"])
        
        print("✅ Complete Matrix auto upgrade API workflow test passed")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_complete_matrix_dream_matrix_api_workflow(self, mock_service_class, mock_auth):
        """Test complete Dream Matrix API workflow."""
        print("\n🔄 Testing Complete Dream Matrix API Workflow")
        
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
        
        mock_service.distribute_dream_matrix_earnings.return_value = {
            "success": True,
            "distributed": True,
            "total_amount": 800.0
        }
        
        # Make Dream Matrix status request
        response1 = self.client.get(
            f"/matrix/dream-matrix-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Make Dream Matrix distribute request
        response2 = self.client.post(
            f"/matrix/dream-matrix-distribute/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        data1 = response1.json()
        data2 = response2.json()
        
        self.assertTrue(data1["success"])
        self.assertTrue(data2["success"])
        self.assertTrue(data1["data"]["eligible"])
        self.assertTrue(data2["data"]["distributed"])
        
        print("✅ Complete Dream Matrix API workflow test passed")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_complete_matrix_mentorship_bonus_api_workflow(self, mock_service_class, mock_auth):
        """Test complete Mentorship Bonus API workflow."""
        print("\n🔄 Testing Complete Mentorship Bonus API Workflow")
        
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
        
        mock_service.distribute_mentorship_bonus.return_value = {
            "success": True,
            "distributed": True,
            "commission_amount": 100.0
        }
        
        # Make Mentorship Bonus status request
        response1 = self.client.get(
            f"/matrix/mentorship-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Make Mentorship Bonus distribute request
        response2 = self.client.post(
            f"/matrix/mentorship-bonus-distribute/{self.test_referrer_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        data1 = response1.json()
        data2 = response2.json()
        
        self.assertTrue(data1["success"])
        self.assertTrue(data2["success"])
        self.assertEqual(data1["data"]["user_id"], self.test_user_id)
        self.assertTrue(data2["data"]["distributed"])
        
        print("✅ Complete Mentorship Bonus API workflow test passed")


class TestMatrixAPICrossProgramIntegration(unittest.TestCase):
    """Cross-program API integration tests for Matrix Program."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        
        self.test_user_id = MatrixTestConfig.TEST_USER_ID
        
        # Mock authentication
        self.mock_auth = {
            "user_id": self.test_user_id,
            "username": "testuser",
            "email": "test@example.com"
        }
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_matrix_rank_system_api_integration(self, mock_service_class, mock_auth):
        """Test Matrix-Rank System API integration."""
        print("\n🔄 Testing Matrix-Rank System API Integration")
        
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_user_rank_status.return_value = {
            "success": True,
            "status": {
                "user_id": self.test_user_id,
                "current_rank": "Stellar",
                "rank_number": 5,
                "total_slots": 5
            }
        }
        
        mock_service.update_user_rank_from_programs.return_value = {
            "success": True,
            "rank_updated": True,
            "rank": "Stellar"
        }
        
        # Make rank status request
        response1 = self.client.get(
            f"/matrix/rank-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Make rank update request
        response2 = self.client.post(
            f"/matrix/update-rank/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        data1 = response1.json()
        data2 = response2.json()
        
        self.assertTrue(data1["success"])
        self.assertTrue(data2["success"])
        self.assertEqual(data1["data"]["current_rank"], "Stellar")
        self.assertTrue(data2["data"]["rank_updated"])
        
        print("✅ Matrix-Rank System API integration test passed")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_matrix_global_program_api_integration(self, mock_service_class, mock_auth):
        """Test Matrix-Global Program API integration."""
        print("\n🔄 Testing Matrix-Global Program API Integration")
        
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
        
        mock_service.integrate_with_global_program.return_value = {
            "success": True,
            "integrated": True,
            "contribution": 5.0
        }
        
        # Make Global Program status request
        response1 = self.client.get(
            f"/matrix/global-program-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Make Global Program integration request
        response2 = self.client.post(
            f"/matrix/integrate-global-program/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        data1 = response1.json()
        data2 = response2.json()
        
        self.assertTrue(data1["success"])
        self.assertTrue(data2["success"])
        self.assertTrue(data1["data"]["integrated"])
        self.assertTrue(data2["data"]["integrated"])
        
        print("✅ Matrix-Global Program API integration test passed")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_matrix_leadership_stipend_api_integration(self, mock_service_class, mock_auth):
        """Test Matrix-Leadership Stipend API integration."""
        print("\n🔄 Testing Matrix-Leadership Stipend API Integration")
        
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
        
        mock_service.integrate_with_leadership_stipend.return_value = {
            "success": True,
            "integrated": True,
            "daily_return": 2.2528
        }
        
        # Make Leadership Stipend status request
        response1 = self.client.get(
            f"/matrix/leadership-stipend-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Make Leadership Stipend integration request
        response2 = self.client.post(
            f"/matrix/integrate-leadership-stipend/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        data1 = response1.json()
        data2 = response2.json()
        
        self.assertTrue(data1["success"])
        self.assertTrue(data2["success"])
        self.assertTrue(data1["data"]["eligible"])
        self.assertTrue(data2["data"]["integrated"])
        
        print("✅ Matrix-Leadership Stipend API integration test passed")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_matrix_jackpot_program_api_integration(self, mock_service_class, mock_auth):
        """Test Matrix-Jackpot Program API integration."""
        print("\n🔄 Testing Matrix-Jackpot Program API Integration")
        
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
        
        mock_service.integrate_with_jackpot_program.return_value = {
            "success": True,
            "integrated": True,
            "contribution": 17.82
        }
        
        # Make Jackpot Program status request
        response1 = self.client.get(
            f"/matrix/jackpot-program-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Make Jackpot Program integration request
        response2 = self.client.post(
            f"/matrix/integrate-jackpot-program/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        data1 = response1.json()
        data2 = response2.json()
        
        self.assertTrue(data1["success"])
        self.assertTrue(data2["success"])
        self.assertEqual(data1["data"]["matrix_slot"], 5)
        self.assertTrue(data2["data"]["integrated"])
        
        print("✅ Matrix-Jackpot Program API integration test passed")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_matrix_ngs_api_integration(self, mock_service_class, mock_auth):
        """Test Matrix-NGS API integration."""
        print("\n🔄 Testing Matrix-NGS API Integration")
        
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
        
        mock_service.integrate_with_newcomer_growth_support.return_value = {
            "success": True,
            "integrated": True,
            "total_benefits": 1.10
        }
        
        # Make NGS status request
        response1 = self.client.get(
            f"/matrix/ngs-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Make NGS integration request
        response2 = self.client.post(
            f"/matrix/integrate-ngs/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        data1 = response1.json()
        data2 = response2.json()
        
        self.assertTrue(data1["success"])
        self.assertTrue(data2["success"])
        self.assertEqual(data1["data"]["matrix_slot"], 1)
        self.assertTrue(data2["data"]["integrated"])
        
        print("✅ Matrix-NGS API integration test passed")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_matrix_mentorship_bonus_api_integration(self, mock_service_class, mock_auth):
        """Test Matrix-Mentorship Bonus API integration."""
        print("\n🔄 Testing Matrix-Mentorship Bonus API Integration")
        
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
        
        mock_service.integrate_with_mentorship_bonus.return_value = {
            "success": True,
            "integrated": True,
            "total_benefits": 1.10
        }
        
        # Make Mentorship Bonus status request
        response1 = self.client.get(
            f"/matrix/mentorship-bonus-status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Make Mentorship Bonus integration request
        response2 = self.client.post(
            f"/matrix/integrate-mentorship-bonus/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        data1 = response1.json()
        data2 = response2.json()
        
        self.assertTrue(data1["success"])
        self.assertTrue(data2["success"])
        self.assertEqual(data1["data"]["matrix_slot"], 1)
        self.assertTrue(data2["data"]["integrated"])
        
        print("✅ Matrix-Mentorship Bonus API integration test passed")


class TestMatrixAPIPerformanceIntegration(unittest.TestCase):
    """API performance integration tests for Matrix Program."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        
        self.test_user_id = MatrixTestConfig.TEST_USER_ID
        self.test_referrer_id = MatrixTestConfig.TEST_REFERRER_ID
        
        # Mock authentication
        self.mock_auth = {
            "user_id": self.test_user_id,
            "username": "testuser",
            "email": "test@example.com"
        }
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_matrix_join_api_performance(self, mock_service_class, mock_auth):
        """Test Matrix join API performance."""
        print("\n🔄 Testing Matrix Join API Performance")
        
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
        
        start_time = time.time()
        
        # Make Matrix join request
        response = self.client.post(
            f"/matrix/join/{self.test_user_id}/{self.test_referrer_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 1.0)  # Should complete within 1 second
        
        data = response.json()
        self.assertTrue(data["success"])
        
        print(f"✅ Matrix join API performance test passed - Duration: {duration:.3f}s")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_matrix_status_api_performance(self, mock_service_class, mock_auth):
        """Test Matrix status API performance."""
        print("\n🔄 Testing Matrix Status API Performance")
        
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
        
        start_time = time.time()
        
        # Make Matrix status request
        response = self.client.get(
            f"/matrix/status/{self.test_user_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 0.5)  # Should complete within 0.5 seconds
        
        data = response.json()
        self.assertTrue(data["success"])
        
        print(f"✅ Matrix status API performance test passed - Duration: {duration:.3f}s")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_matrix_special_programs_api_performance(self, mock_service_class, mock_auth):
        """Test Matrix special programs API performance."""
        print("\n🔄 Testing Matrix Special Programs API Performance")
        
        # Mock authentication
        mock_auth.return_value = self.mock_auth
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Mock all special programs responses
        mock_service.get_user_rank_status.return_value = {"success": True, "status": {}}
        mock_service.get_global_program_status.return_value = {"success": True, "status": {}}
        mock_service.get_leadership_stipend_status.return_value = {"success": True, "status": {}}
        mock_service.get_jackpot_program_status.return_value = {"success": True, "status": {}}
        mock_service.get_ngs_status.return_value = {"success": True, "status": {}}
        mock_service.get_mentorship_bonus_status.return_value = {"success": True, "status": {}}
        
        start_time = time.time()
        
        # Make all special programs requests
        responses = []
        endpoints = [
            f"/matrix/rank-status/{self.test_user_id}",
            f"/matrix/global-program-status/{self.test_user_id}",
            f"/matrix/leadership-stipend-status/{self.test_user_id}",
            f"/matrix/jackpot-program-status/{self.test_user_id}",
            f"/matrix/ngs-status/{self.test_user_id}",
            f"/matrix/mentorship-bonus-status/{self.test_user_id}"
        ]
        
        for endpoint in endpoints:
            response = self.client.get(
                endpoint,
                headers={"Authorization": "Bearer test_token"}
            )
            responses.append(response)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assertions
        for response in responses:
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
        
        self.assertLess(duration, 2.0)  # Should complete within 2 seconds
        
        print(f"✅ Matrix special programs API performance test passed - Duration: {duration:.3f}s")


class TestMatrixAPIErrorHandlingIntegration(unittest.TestCase):
    """API error handling integration tests for Matrix Program."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        
        self.test_user_id = MatrixTestConfig.TEST_USER_ID
        self.test_referrer_id = MatrixTestConfig.TEST_REFERRER_ID
    
    def test_matrix_api_unauthorized_access(self):
        """Test Matrix API unauthorized access."""
        print("\n🔄 Testing Matrix API Unauthorized Access")
        
        # Mock authentication failure
        with patch('modules.matrix.router.authentication_service.verify_authentication') as mock_auth:
            mock_auth.side_effect = HTTPException(status_code=401, detail="Unauthorized")
            
            # Make request without valid token
            response = self.client.post(
                f"/matrix/join/{self.test_user_id}/{self.test_referrer_id}",
                headers={"Authorization": "Bearer invalid_token"}
            )
            
            # Assertions
            self.assertEqual(response.status_code, 401)
            
            print("✅ Matrix API unauthorized access test passed")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    @patch('modules.matrix.router.MatrixService')
    def test_matrix_api_service_error_handling(self, mock_service_class, mock_auth):
        """Test Matrix API service error handling."""
        print("\n🔄 Testing Matrix API Service Error Handling")
        
        # Mock authentication
        mock_auth.return_value = {"user_id": self.test_user_id}
        
        # Mock service error
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.join_matrix.return_value = {
            "success": False,
            "error": "Database connection error"
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
        self.assertIn("Database connection error", data["error"])
        
        print("✅ Matrix API service error handling test passed")
    
    @patch('modules.matrix.router.authentication_service.verify_authentication')
    def test_matrix_api_validation_error_handling(self, mock_auth):
        """Test Matrix API validation error handling."""
        print("\n🔄 Testing Matrix API Validation Error Handling")
        
        # Mock authentication
        mock_auth.return_value = {"user_id": self.test_user_id}
        
        # Make request with invalid data
        response = self.client.post(
            f"/matrix/upgrade-slot/{self.test_user_id}",
            json={
                "from_slot_no": "invalid",
                "to_slot_no": 2,
                "upgrade_cost": -100.0
            },
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Assertions
        self.assertEqual(response.status_code, 422)  # Validation error
        
        print("✅ Matrix API validation error handling test passed")


if __name__ == '__main__':
    # Run the API integration tests
    unittest.main(verbosity=2)
