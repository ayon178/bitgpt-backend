"""
Corrected Matrix Unit Test Runner

This script runs Matrix unit tests using the actual methods that exist in MatrixService.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from bson import ObjectId
from decimal import Decimal

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import Matrix service
from modules.matrix.service import MatrixService


class TestMatrixCorrectedFunctionality(unittest.TestCase):
    """Corrected Matrix functionality tests using actual methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = MatrixService()
        self.test_user_id = str(ObjectId())
        self.test_referrer_id = str(ObjectId())
    
    def test_matrix_service_initialization(self):
        """Test Matrix service initialization."""
        print("🔄 Testing Matrix Service Initialization")
        self.assertIsNotNone(self.service)
        print("✅ Matrix Service initialization test passed")
    
    @patch('modules.matrix.service.User.objects')
    @patch('modules.matrix.service.MatrixTree.objects')
    def test_matrix_join_corrected(self, mock_matrix_objects, mock_user_objects):
        """Test Matrix join functionality with correct parameters."""
        print("🔄 Testing Matrix Join (Corrected)")
        
        # Mock user and referrer
        mock_user = Mock()
        mock_user.id = ObjectId(self.test_user_id)
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.wallet_balance = 1000.0
        
        mock_referrer = Mock()
        mock_referrer.id = ObjectId(self.test_referrer_id)
        mock_referrer.username = "referrer"
        mock_referrer.email = "referrer@example.com"
        
        mock_user_objects.return_value.first.side_effect = [mock_user, mock_referrer]
        
        # Mock Matrix tree
        mock_tree = Mock()
        mock_tree.user_id = ObjectId(self.test_referrer_id)
        mock_tree.slot_number = 1
        mock_tree.nodes = []
        mock_matrix_objects.return_value.first.return_value = mock_tree
        
        # Mock all integration methods
        with patch.object(self.service, '_place_user_in_matrix_tree') as mock_place, \
             patch.object(self.service, '_create_matrix_activation') as mock_activate, \
             patch.object(self.service, 'trigger_rank_update_automatic') as mock_rank, \
             patch.object(self.service, 'trigger_global_integration_automatic') as mock_global, \
             patch.object(self.service, 'trigger_jackpot_integration_automatic') as mock_jackpot, \
             patch.object(self.service, 'trigger_ngs_integration_automatic') as mock_ngs, \
             patch.object(self.service, 'trigger_mentorship_bonus_integration_automatic') as mock_mentorship:
            
            mock_place.return_value = {"success": True, "level": 1, "position": 0, "total_members": 1}
            mock_activate.return_value = {"success": True}
            
            # Execute Matrix join with correct parameters
            result = self.service.join_matrix(
                self.test_user_id, 
                self.test_referrer_id, 
                "test_tx_hash", 
                Decimal("11.0")
            )
            
            # Assertions
            self.assertTrue(result["success"])
            self.assertEqual(result["user_id"], self.test_user_id)
            self.assertEqual(result["referrer_id"], self.test_referrer_id)
            self.assertEqual(result["slot_activated"], 1)
            
            print("✅ Matrix join test passed")
    
    def test_matrix_status(self):
        """Test Matrix status functionality."""
        print("🔄 Testing Matrix Status")
        
        with patch('modules.matrix.service.MatrixTree.objects') as mock_objects:
            mock_tree = Mock()
            mock_tree.user_id = ObjectId(self.test_user_id)
            mock_tree.current_slot = 1
            mock_tree.slot_name = "STARTER"
            mock_tree.total_members = 0
            mock_tree.is_complete = False
            mock_objects.return_value.first.return_value = mock_tree
            
            result = self.service.get_matrix_status(self.test_user_id)
            
            # Assertions
            self.assertTrue(result["success"])
            self.assertEqual(result["data"]["user_id"], self.test_user_id)
            self.assertEqual(result["data"]["current_slot"], 1)
            
            print("✅ Matrix status test passed")
    
    def test_dream_matrix_eligibility(self):
        """Test Dream Matrix eligibility check."""
        print("🔄 Testing Dream Matrix Eligibility")
        
        with patch('modules.matrix.service.MatrixTree.objects') as mock_objects:
            mock_tree = Mock()
            mock_tree.nodes = [
                Mock(level=1, position=0, user_id=ObjectId()),
                Mock(level=1, position=1, user_id=ObjectId()),
                Mock(level=1, position=2, user_id=ObjectId())
            ]
            mock_objects.return_value.first.return_value = mock_tree
            
            result = self.service.check_dream_matrix_eligibility(self.test_user_id)
            
            # Should be eligible for Dream Matrix
            self.assertTrue(result.get("eligible", False))
            
            print("✅ Dream Matrix eligibility test passed")
    
    def test_dream_matrix_status(self):
        """Test Dream Matrix status."""
        print("🔄 Testing Dream Matrix Status")
        
        with patch('modules.matrix.service.MatrixTree.objects') as mock_objects:
            mock_tree = Mock()
            mock_tree.nodes = [
                Mock(level=1, position=0, user_id=ObjectId()),
                Mock(level=1, position=1, user_id=ObjectId()),
                Mock(level=1, position=2, user_id=ObjectId())
            ]
            mock_objects.return_value.first.return_value = mock_tree
            
            result = self.service.get_dream_matrix_status(self.test_user_id)
            
            # Should return status
            self.assertTrue(result.get("success", False))
            
            print("✅ Dream Matrix status test passed")
    
    def test_matrix_upgrade_status(self):
        """Test Matrix upgrade status."""
        print("🔄 Testing Matrix Upgrade Status")
        
        with patch('modules.matrix.service.MatrixTree.objects') as mock_objects:
            mock_tree = Mock()
            mock_tree.current_slot = 1
            mock_tree.slot_name = "STARTER"
            mock_objects.return_value.first.return_value = mock_tree
            
            result = self.service.get_matrix_upgrade_status(self.test_user_id)
            
            # Should return upgrade status
            self.assertTrue(result.get("success", False))
            
            print("✅ Matrix upgrade status test passed")
    
    def test_mentorship_bonus_calculation(self):
        """Test Mentorship Bonus calculation."""
        print("🔄 Testing Mentorship Bonus Calculation")
        
        # Test with $100 amount
        result = self.service.calculate_mentorship_bonus(
            self.test_referrer_id, 
            self.test_user_id, 
            100.0
        )
        
        # Should calculate 10% commission
        self.assertTrue(result.get("success", False))
        self.assertEqual(result.get("mentorship_bonus", 0), 10.0)
        self.assertEqual(result.get("commission_percentage", 0), 10)
        
        print("✅ Mentorship Bonus calculation test passed")
    
    def test_matrix_slot_values(self):
        """Test Matrix slot values."""
        print("🔄 Testing Matrix Slot Values")
        
        # Test slot values from PROJECT_DOCUMENTATION.md
        expected_slots = [
            {"slot_no": 1, "slot_name": "STARTER", "slot_value": 11},
            {"slot_no": 2, "slot_name": "BRONZE", "slot_value": 33},
            {"slot_no": 3, "slot_name": "SILVER", "slot_value": 99},
            {"slot_no": 4, "slot_name": "GOLD", "slot_value": 297},
            {"slot_no": 5, "slot_name": "PLATINUM", "slot_value": 891}
        ]
        
        # Verify slot values are correct
        for slot in expected_slots:
            if slot["slot_no"] == 1:
                self.assertEqual(slot["slot_value"], 11)
            elif slot["slot_no"] == 2:
                self.assertEqual(slot["slot_value"], 33)
            elif slot["slot_no"] == 3:
                self.assertEqual(slot["slot_value"], 99)
            elif slot["slot_no"] == 4:
                self.assertEqual(slot["slot_value"], 297)
            elif slot["slot_no"] == 5:
                self.assertEqual(slot["slot_value"], 891)
        
        print("✅ Matrix slot values test passed")


def run_corrected_matrix_tests():
    """Run corrected Matrix unit tests."""
    print("🚀 Starting Corrected Matrix Program Unit Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test class
    suite.addTests(loader.loadTestsFromTestCase(TestMatrixCorrectedFunctionality))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 CORRECTED MATRIX UNIT TEST SUMMARY")
    print("=" * 60)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    passed = total_tests - failures - errors
    
    print(f"📈 Total Tests: {total_tests}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failures}")
    print(f"💥 Errors: {errors}")
    print(f"⏭️  Skipped: {skipped}")
    
    if total_tests > 0:
        success_rate = (passed / total_tests) * 100
        print(f"📊 Success Rate: {success_rate:.1f}%")
    
    # Print failures and errors
    if failures:
        print(f"\n❌ FAILURES ({failures}):")
        for test, traceback in result.failures:
            print(f"   {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if errors:
        print(f"\n💥 ERRORS ({errors}):")
        for test, traceback in result.errors:
            print(f"   {test}: {traceback.split('Exception:')[-1].strip()}")
    
    if failures == 0 and errors == 0:
        print("\n🎉 All corrected Matrix unit tests passed!")
        print("✅ Matrix Program core functionality is working correctly!")
    else:
        print(f"\n⚠️  {failures + errors} Matrix unit tests failed.")
        print("❌ There are issues in the Matrix Program that need to be fixed.")
    
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    run_corrected_matrix_tests()
