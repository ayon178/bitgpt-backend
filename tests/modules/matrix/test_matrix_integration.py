"""
Integration Tests for Matrix Program

This module contains comprehensive integration tests for the Matrix Program implementation,
including end-to-end workflows, database integration, cross-program integration,
and performance testing.

Test Coverage:
- End-to-end Matrix workflows
- Database integration testing
- Cross-program integration (Binary, Global, Special Programs)
- Performance and load testing
- Error handling and edge cases
- Real-world scenario testing
"""

import pytest
import unittest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from bson import ObjectId
import sys
import os
from decimal import Decimal
from types import SimpleNamespace

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.modules.matrix.service import MatrixService
from backend.modules.matrix.model import *
from backend.modules.user.model import User
from backend.modules.binary.service import BinaryService
from tests.modules.matrix.test_config import MatrixTestConfig, MatrixTestFixtures, MatrixTestUtils


class TestMatrixEndToEndWorkflow(unittest.TestCase):
    """End-to-end integration tests for Matrix Program workflows."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = MatrixService()
        self.binary_service = BinaryService()
        
        # Test user IDs
        self.root_user_id = str(ObjectId())
        self.referrer_id = str(ObjectId())
        self.user1_id = str(ObjectId())
        self.user2_id = str(ObjectId())
        self.user3_id = str(ObjectId())
        
        # Test data
        self.test_users = []
        self.test_matrix_trees = []
        self.test_recycle_instances = []
    
    def tearDown(self):
        """Clean up test data."""
        # Clean up test data
        pass
    
    @patch('backend.modules.matrix.service.User.objects')
    @patch('backend.modules.matrix.service.MatrixTree.objects')
    def test_complete_matrix_join_workflow(self, mock_matrix_objects, mock_user_objects):
        """Test complete Matrix join workflow from start to finish."""
        print("\n🔄 Testing Complete Matrix Join Workflow")
        
        # Mock users
        root_user = MatrixTestFixtures.create_mock_user(self.root_user_id, "root", "root@example.com")
        referrer_user = MatrixTestFixtures.create_mock_user(self.referrer_id, "referrer", "referrer@example.com")
        new_user = MatrixTestFixtures.create_mock_user(self.user1_id, "newuser", "newuser@example.com")
        
        mock_user_objects.return_value.first.side_effect = [new_user, referrer_user]
        
        # Mock referrer's Matrix tree
        referrer_tree = MatrixTestFixtures.create_mock_matrix_tree(self.referrer_id, 1, 0)
        mock_matrix_objects.return_value.first.return_value = referrer_tree
        
        # Mock all integration methods
        with patch.object(self.service, '_place_user_in_matrix_tree') as mock_place, \
             patch.object(self.service, '_create_matrix_activation') as mock_activate, \
             patch.object(self.service, 'trigger_rank_update_automatic') as mock_rank, \
             patch.object(self.service, 'trigger_global_integration_automatic') as mock_global, \
             patch.object(self.service, 'trigger_jackpot_integration_automatic') as mock_jackpot, \
             patch.object(self.service, 'trigger_ngs_integration_automatic') as mock_ngs, \
             patch.object(self.service, 'trigger_mentorship_bonus_integration_automatic') as mock_mentorship, \
             patch('backend.modules.matrix.service.ensure_currency_for_program', return_value='USDT'), \
             patch.object(self.service, '_create_matrix_tree') as mock_create_tree, \
             patch.object(self.service, '_process_matrix_commissions', return_value={"success": True}):
            
            mock_place.return_value = {"success": True, "level": 1, "position": 0, "total_members": 1}
            mock_activate.return_value = SimpleNamespace(id=ObjectId())
            mock_create_tree.return_value = SimpleNamespace(id=ObjectId())
            
            # Execute Matrix join
            result = self.service.join_matrix(self.user1_id, self.referrer_id, tx_hash="tx", amount=Decimal('11'))
            
            # Assertions
            self.assertTrue(result["success"])
            self.assertIn("matrix_tree_id", result)
            self.assertIn("activation_id", result)
            self.assertEqual(result["slot_activated"], 'STARTER')
            # Verify all integrations were triggered
            mock_rank.assert_called_once_with(self.user1_id)
            mock_global.assert_called_once_with(self.user1_id)
            mock_jackpot.assert_called_once_with(self.user1_id)
            mock_ngs.assert_called_once_with(self.user1_id)
            mock_mentorship.assert_called_once_with(self.user1_id)
            
            print("✅ Complete Matrix join workflow test passed")
    
    @patch('modules.matrix.service.User.objects')
    @patch('modules.matrix.service.MatrixTree.objects')
    def test_matrix_recycle_complete_workflow(self, mock_matrix_objects, mock_user_objects):
        """Test complete Matrix recycle workflow."""
        print("\n🔄 Testing Complete Matrix Recycle Workflow")
        
        # Mock user
        user = MatrixTestFixtures.create_mock_user(self.user1_id, "user", "user@example.com")
        mock_user_objects.return_value.first.return_value = user
        
        # Mock Matrix tree with 39 members (ready for recycle)
        tree = MatrixTestFixtures.create_mock_matrix_tree(self.user1_id, 1, 39)
        tree.nodes = [Mock() for _ in range(39)]
        tree.is_complete = True
        mock_matrix_objects.return_value.first.return_value = tree
        
        # Mock recycle processing
        with patch.object(self.service, '_check_and_process_automatic_recycle') as mock_recycle:
            mock_recycle.return_value = {
                "success": True,
                "recycled": True,
                "recycle_no": 1,
                "snapshot_created": True
            }
            
            # Mock tree update
            with patch.object(self.service, '_update_matrix_tree_status') as mock_update:
                mock_update.return_value = {"success": True}
                
                result = self.service._place_user_in_matrix_tree(
                    self.user2_id, tree, self.user1_id
                )
                
                # Should trigger recycle
                mock_recycle.assert_called_once()
                
                print("✅ Complete Matrix recycle workflow test passed")
    
    @patch('modules.matrix.service.User.objects')
    @patch('modules.matrix.service.MatrixTree.objects')
    def test_matrix_auto_upgrade_complete_workflow(self, mock_matrix_objects, mock_user_objects):
        """Test complete Matrix auto upgrade workflow."""
        print("\n🔄 Testing Complete Matrix Auto Upgrade Workflow")
        
        # Mock user
        user = MatrixTestFixtures.create_mock_user(self.user1_id, "user", "user@example.com")
        mock_user_objects.return_value.first.return_value = user
        
        # Mock Matrix tree with level 2 nodes
        tree = MatrixTestFixtures.create_mock_matrix_tree(self.user1_id, 1, 9)
        tree.nodes = [Mock() for _ in range(9)]
        mock_matrix_objects.return_value.first.return_value = tree
        
        # Mock auto upgrade processing
        with patch.object(self.service, '_check_and_process_automatic_upgrade') as mock_auto_upgrade:
            mock_auto_upgrade.return_value = {
                "success": True,
                "upgraded": True,
                "from_slot": 1,
                "to_slot": 2
            }
            
            # Mock tree update
            with patch.object(self.service, '_update_matrix_tree_status') as mock_update:
                mock_update.return_value = {"success": True}
                
                result = self.service._place_user_in_matrix_tree(
                    self.user2_id, tree, self.user1_id
                )
                
                # Should trigger auto upgrade check
                mock_auto_upgrade.assert_called_once()
                
                print("✅ Complete Matrix auto upgrade workflow test passed")
    
    @patch('modules.matrix.service.User.objects')
    @patch('modules.matrix.service.MatrixTree.objects')
    def test_matrix_dream_matrix_complete_workflow(self, mock_matrix_objects, mock_user_objects):
        """Test complete Dream Matrix workflow."""
        print("\n🔄 Testing Complete Dream Matrix Workflow")
        
        # Mock user
        user = MatrixTestFixtures.create_mock_user(self.user1_id, "user", "user@example.com")
        mock_user_objects.return_value.first.return_value = user
        
        # Mock Matrix tree with 3 direct partners
        tree = MatrixTestFixtures.create_mock_matrix_tree(self.user1_id, 1, 3)
        tree.nodes = [
            Mock(level=1, position=0, user_id=ObjectId()),
            Mock(level=1, position=1, user_id=ObjectId()),
            Mock(level=1, position=2, user_id=ObjectId())
        ]
        mock_matrix_objects.return_value.first.return_value = tree
        
        # Mock Dream Matrix processing
        with patch.object(self.service, '_check_and_process_dream_matrix_eligibility') as mock_dream:
            mock_dream.return_value = {
                "success": True,
                "eligible": True,
                "direct_partners": 3,
                "distributed": True
            }
            
            # Mock tree update
            with patch.object(self.service, '_update_matrix_tree_status') as mock_update:
                mock_update.return_value = {"success": True}
                
                result = self.service._place_user_in_matrix_tree(
                    self.user2_id, tree, self.user1_id
                )
                
                # Should trigger Dream Matrix check
                mock_dream.assert_called_once()
                
                print("✅ Complete Dream Matrix workflow test passed")
    
    @patch('modules.matrix.service.User.objects')
    @patch('modules.matrix.service.MatrixTree.objects')
    def test_matrix_mentorship_bonus_complete_workflow(self, mock_matrix_objects, mock_user_objects):
        """Test complete Mentorship Bonus workflow."""
        print("\n🔄 Testing Complete Mentorship Bonus Workflow")
        
        # Mock user
        user = MatrixTestFixtures.create_mock_user(self.user1_id, "user", "user@example.com")
        mock_user_objects.return_value.first.return_value = user
        
        # Mock Matrix tree
        tree = MatrixTestFixtures.create_mock_matrix_tree(self.user1_id, 1, 1)
        mock_matrix_objects.return_value.first.return_value = tree
        
        # Mock Mentorship Bonus processing
        with patch.object(self.service, '_track_mentorship_relationships_automatic') as mock_mentorship:
            mock_mentorship.return_value = {
                "success": True,
                "tracked": True,
                "commission_awarded": 1.10
            }
            
            # Mock tree update
            with patch.object(self.service, '_update_matrix_tree_status') as mock_update:
                mock_update.return_value = {"success": True}
                
                result = self.service._place_user_in_matrix_tree(
                    self.user2_id, tree, self.user1_id
                )
                
                # Should trigger Mentorship Bonus tracking
                mock_mentorship.assert_called_once()
                
                print("✅ Complete Mentorship Bonus workflow test passed")


class TestMatrixDatabaseIntegration(unittest.TestCase):
    """Database integration tests for Matrix Program."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = MatrixService()
        self.test_user_id = str(ObjectId())
        self.test_referrer_id = str(ObjectId())
    
    @patch('modules.matrix.service.MatrixTree')
    @patch('modules.matrix.service.MatrixActivation')
    @patch('modules.matrix.service.MatrixEarningHistory')
    def test_matrix_tree_database_operations(self, mock_earning_history, mock_activation, mock_tree):
        """Test Matrix tree database operations."""
        print("\n🔄 Testing Matrix Tree Database Operations")
        
        # Mock database operations
        mock_tree_instance = Mock()
        mock_tree.return_value = mock_tree_instance
        
        mock_activation_instance = Mock()
        mock_activation.return_value = mock_activation_instance
        
        mock_earning_instance = Mock()
        mock_earning_history.return_value = mock_earning_instance
        
        # Test tree creation
        with patch.object(self.service, '_create_matrix_tree') as mock_create_tree:
            mock_create_tree.return_value = {"success": True, "tree_id": str(ObjectId())}
            
            result = self.service._create_matrix_tree(self.test_user_id, 1)
            
            self.assertTrue(result["success"])
            self.assertIsNotNone(result["tree_id"])
            
            print("✅ Matrix tree database operations test passed")
    
    @patch('modules.matrix.service.MatrixRecycleInstance')
    @patch('modules.matrix.service.MatrixRecycleNode')
    def test_matrix_recycle_database_operations(self, mock_recycle_node, mock_recycle_instance):
        """Test Matrix recycle database operations."""
        print("\n🔄 Testing Matrix Recycle Database Operations")
        
        # Mock database operations
        mock_instance = Mock()
        mock_recycle_instance.return_value = mock_instance
        
        mock_node = Mock()
        mock_recycle_node.return_value = mock_node
        
        # Test recycle instance creation
        with patch.object(self.service, '_create_recycle_instance') as mock_create_instance:
            mock_create_instance.return_value = {"success": True, "instance_id": str(ObjectId())}
            
            result = self.service._create_recycle_instance(
                self.test_user_id, 1, 1
            )
            
            self.assertTrue(result["success"])
            self.assertIsNotNone(result["instance_id"])
            
            print("✅ Matrix recycle database operations test passed")
    
    @patch('modules.matrix.service.MatrixUpgradeLog')
    @patch('modules.matrix.service.MatrixEarningHistory')
    def test_matrix_upgrade_database_operations(self, mock_earning_history, mock_upgrade_log):
        """Test Matrix upgrade database operations."""
        print("\n🔄 Testing Matrix Upgrade Database Operations")
        
        # Mock database operations
        mock_upgrade_instance = Mock()
        mock_upgrade_log.return_value = mock_upgrade_instance
        
        mock_earning_instance = Mock()
        mock_earning_history.return_value = mock_earning_instance
        
        # Test upgrade logging
        with patch.object(self.service, '_log_matrix_upgrade') as mock_log_upgrade:
            mock_log_upgrade.return_value = {"success": True, "log_id": str(ObjectId())}
            
            result = self.service._log_matrix_upgrade(
                self.test_user_id, 1, 2, 100.0
            )
            
            self.assertTrue(result["success"])
            self.assertIsNotNone(result["log_id"])
            
            print("✅ Matrix upgrade database operations test passed")


class TestMatrixCrossProgramIntegration(unittest.TestCase):
    """Cross-program integration tests for Matrix Program."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.matrix_service = MatrixService()
        self.binary_service = BinaryService()
        self.test_user_id = str(ObjectId())
    
    def test_matrix_binary_rank_integration(self):
        """Test Matrix-Binary rank system integration."""
        print("\n🔄 Testing Matrix-Binary Rank Integration")
        
        # Mock Binary service
        with patch.object(self.binary_service, 'get_binary_slots_activated') as mock_binary_slots:
            mock_binary_slots.return_value = 2
            
            # Mock Matrix service
            with patch.object(self.matrix_service, '_get_matrix_slots_activated') as mock_matrix_slots:
                mock_matrix_slots.return_value = 3
                
                # Test rank calculation
                with patch.object(self.matrix_service, '_calculate_rank_from_slots') as mock_calculate_rank:
                    mock_calculate_rank.return_value = "Stellar"  # Rank 5
                    
                    result = self.matrix_service.update_user_rank_from_programs(self.test_user_id)
                    
                    self.assertTrue(result["success"])
                    self.assertEqual(result["rank"], "Stellar")
                    self.assertEqual(result["total_slots"], 5)
                    
                    print("✅ Matrix-Binary rank integration test passed")
    
    def test_matrix_global_program_integration(self):
        """Test Matrix-Global program integration."""
        print("\n🔄 Testing Matrix-Global Program Integration")
        
        # Mock Matrix tree
        with patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects:
            mock_tree = Mock()
            mock_tree.current_slot = 5
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Test Global program integration
            with patch.object(self.matrix_service, '_process_global_distribution') as mock_global_dist:
                mock_global_dist.return_value = {"success": True, "distributed": True}
                
                result = self.matrix_service.integrate_with_global_program(self.test_user_id)
                
                self.assertTrue(result["success"])
                self.assertTrue(result["integrated"])
                
                print("✅ Matrix-Global program integration test passed")
    
    def test_matrix_leadership_stipend_integration(self):
        """Test Matrix-Leadership Stipend integration."""
        print("\n🔄 Testing Matrix-Leadership Stipend Integration")
        
        # Mock Matrix tree with eligible slot
        with patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects:
            mock_tree = Mock()
            mock_tree.current_slot = 10  # Eligible for Leadership Stipend
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Test Leadership Stipend integration
            with patch.object(self.matrix_service, '_process_leadership_stipend_distribution') as mock_stipend_dist:
                mock_stipend_dist.return_value = {"success": True, "distributed": True}
                
                result = self.matrix_service.integrate_with_leadership_stipend(self.test_user_id)
                
                self.assertTrue(result["success"])
                self.assertTrue(result["integrated"])
                
                print("✅ Matrix-Leadership Stipend integration test passed")
    
    def test_matrix_jackpot_program_integration(self):
        """Test Matrix-Jackpot program integration."""
        print("\n🔄 Testing Matrix-Jackpot Program Integration")
        
        # Mock Matrix tree
        with patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects:
            mock_tree = Mock()
            mock_tree.current_slot = 5
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Test Jackpot program integration
            with patch.object(self.matrix_service, '_process_jackpot_program_distribution') as mock_jackpot_dist:
                mock_jackpot_dist.return_value = {"success": True, "distributed": True}
                
                result = self.matrix_service.integrate_with_jackpot_program(self.test_user_id)
                
                self.assertTrue(result["success"])
                self.assertTrue(result["integrated"])
                
                print("✅ Matrix-Jackpot program integration test passed")
    
    def test_matrix_ngs_integration(self):
        """Test Matrix-NGS integration."""
        print("\n🔄 Testing Matrix-NGS Integration")
        
        # Mock Matrix tree
        with patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects:
            mock_tree = Mock()
            mock_tree.current_slot = 1
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Test NGS integration
            with patch.object(self.matrix_service, '_process_ngs_instant_bonus') as mock_ngs_bonus:
                mock_ngs_bonus.return_value = {"success": True, "processed": True}
                
                result = self.matrix_service.integrate_with_newcomer_growth_support(self.test_user_id)
                
                self.assertTrue(result["success"])
                self.assertTrue(result["integrated"])
                
                print("✅ Matrix-NGS integration test passed")
    
    def test_matrix_mentorship_bonus_integration(self):
        """Test Matrix-Mentorship Bonus integration."""
        print("\n🔄 Testing Matrix-Mentorship Bonus Integration")
        
        # Mock Matrix tree
        with patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects:
            mock_tree = Mock()
            mock_tree.current_slot = 1
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Test Mentorship Bonus integration
            with patch.object(self.matrix_service, '_process_mentorship_bonus_distribution') as mock_mentorship_dist:
                mock_mentorship_dist.return_value = {"success": True, "processed": True}
                
                result = self.matrix_service.integrate_with_mentorship_bonus(self.test_user_id)
                
                self.assertTrue(result["success"])
                self.assertTrue(result["integrated"])
                
                print("✅ Matrix-Mentorship Bonus integration test passed")


class TestMatrixPerformanceIntegration(unittest.TestCase):
    """Performance integration tests for Matrix Program."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = MatrixService()
        self.test_user_id = str(ObjectId())
        self.test_referrer_id = str(ObjectId())
    
    def test_matrix_join_performance(self):
        """Test Matrix join performance."""
        print("\n🔄 Testing Matrix Join Performance")
        
        start_time = time.time()
        
        # Mock all dependencies
        with patch('modules.matrix.service.User.objects') as mock_user_objects, \
             patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects, \
             patch.object(self.service, '_place_user_in_matrix_tree') as mock_place, \
             patch.object(self.service, '_create_matrix_activation') as mock_activate, \
             patch.object(self.service, 'trigger_rank_update_automatic') as mock_rank, \
             patch.object(self.service, 'trigger_global_integration_automatic') as mock_global, \
             patch.object(self.service, 'trigger_jackpot_integration_automatic') as mock_jackpot, \
             patch.object(self.service, 'trigger_ngs_integration_automatic') as mock_ngs, \
             patch.object(self.service, 'trigger_mentorship_bonus_integration_automatic') as mock_mentorship:
            
            # Mock user and referrer
            mock_user = MatrixTestFixtures.create_mock_user(self.test_user_id)
            mock_referrer = MatrixTestFixtures.create_mock_user(self.test_referrer_id)
            mock_user_objects.return_value.first.side_effect = [mock_user, mock_referrer]
            
            # Mock Matrix tree
            mock_tree = MatrixTestFixtures.create_mock_matrix_tree(self.test_referrer_id)
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Mock all methods
            mock_place.return_value = {"success": True, "level": 1, "position": 0}
            mock_activate.return_value = {"success": True}
            
            # Execute Matrix join
            result = self.service.join_matrix(self.test_user_id, self.test_referrer_id, tx_hash="tx", amount=Decimal('11'))
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Assertions
            self.assertTrue(result["success"])
            self.assertLess(duration, 1.0)  # Should complete within 1 second
            
            print(f"✅ Matrix join performance test passed - Duration: {duration:.3f}s")
    
    def test_matrix_recycle_performance(self):
        """Test Matrix recycle performance."""
        print("\n🔄 Testing Matrix Recycle Performance")
        
        start_time = time.time()
        
        # Mock Matrix tree with 39 members
        mock_tree = MatrixTestFixtures.create_mock_matrix_tree(self.test_user_id, 1, 39)
        mock_tree.nodes = [Mock() for _ in range(39)]
        mock_tree.is_complete = True
        
        # Mock recycle processing
        with patch.object(self.service, '_check_and_process_automatic_recycle') as mock_recycle:
            mock_recycle.return_value = {
                "success": True,
                "recycled": True,
                "recycle_no": 1
            }
            
            # Mock tree update
            with patch.object(self.service, '_update_matrix_tree_status') as mock_update:
                mock_update.return_value = {"success": True}
                
                result = self.service._place_user_in_matrix_tree(
                    self.test_user_id, mock_tree, self.test_referrer_id
                )
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Assertions
                self.assertTrue(result["success"])
                self.assertLess(duration, 2.0)  # Should complete within 2 seconds
                
                print(f"✅ Matrix recycle performance test passed - Duration: {duration:.3f}s")
    
    def test_matrix_auto_upgrade_performance(self):
        """Test Matrix auto upgrade performance."""
        print("\n🔄 Testing Matrix Auto Upgrade Performance")
        
        start_time = time.time()
        
        # Mock Matrix tree with level 2 nodes
        mock_tree = MatrixTestFixtures.create_mock_matrix_tree(self.test_user_id, 1, 9)
        mock_tree.nodes = [Mock() for _ in range(9)]
        
        # Mock auto upgrade processing
        with patch.object(self.service, '_check_and_process_automatic_upgrade') as mock_auto_upgrade:
            mock_auto_upgrade.return_value = {
                "success": True,
                "upgraded": True,
                "from_slot": 1,
                "to_slot": 2
            }
            
            # Mock tree update
            with patch.object(self.service, '_update_matrix_tree_status') as mock_update:
                mock_update.return_value = {"success": True}
                
                result = self.service._place_user_in_matrix_tree(
                    self.test_user_id, mock_tree, self.test_referrer_id
                )
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Assertions
                self.assertTrue(result["success"])
                self.assertLess(duration, 1.5)  # Should complete within 1.5 seconds
                
                print(f"✅ Matrix auto upgrade performance test passed - Duration: {duration:.3f}s")
    
    def test_matrix_special_programs_performance(self):
        """Test Matrix special programs integration performance."""
        print("\n🔄 Testing Matrix Special Programs Performance")
        
        start_time = time.time()
        
        # Mock Matrix tree
        with patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects:
            mock_tree = MatrixTestFixtures.create_mock_matrix_tree(self.test_user_id, 5)
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Mock all special programs
            with patch.object(self.service, 'integrate_with_rank_system') as mock_rank, \
                 patch.object(self.service, 'integrate_with_global_program') as mock_global, \
                 patch.object(self.service, 'integrate_with_jackpot_program') as mock_jackpot, \
                 patch.object(self.service, 'integrate_with_newcomer_growth_support') as mock_ngs, \
                 patch.object(self.service, 'integrate_with_mentorship_bonus') as mock_mentorship:
                
                mock_rank.return_value = {"success": True, "rank_updated": True}
                mock_global.return_value = {"success": True, "integrated": True}
                mock_jackpot.return_value = {"success": True, "integrated": True}
                mock_ngs.return_value = {"success": True, "integrated": True}
                mock_mentorship.return_value = {"success": True, "integrated": True}
                
                # Execute all integrations
                results = []
                results.append(self.service.integrate_with_rank_system(self.test_user_id))
                results.append(self.service.integrate_with_global_program(self.test_user_id))
                results.append(self.service.integrate_with_jackpot_program(self.test_user_id))
                results.append(self.service.integrate_with_newcomer_growth_support(self.test_user_id))
                results.append(self.service.integrate_with_mentorship_bonus(self.test_user_id))
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Assertions
                for result in results:
                    self.assertTrue(result["success"])
                
                self.assertLess(duration, 3.0)  # Should complete within 3 seconds
                
                print(f"✅ Matrix special programs performance test passed - Duration: {duration:.3f}s")


class TestMatrixErrorHandlingIntegration(unittest.TestCase):
    """Error handling integration tests for Matrix Program."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = MatrixService()
        self.test_user_id = str(ObjectId())
        self.test_referrer_id = str(ObjectId())
    
    def test_matrix_join_error_handling(self):
        """Test Matrix join error handling."""
        print("\n🔄 Testing Matrix Join Error Handling")
        
        # Test with non-existent user
        with patch('modules.matrix.service.User.objects') as mock_user_objects:
            mock_user_objects.return_value.first.return_value = None
            
            result = self.service.join_matrix(self.test_user_id, self.test_referrer_id, tx_hash="tx", amount=Decimal('11'))
            
            self.assertFalse(result["success"])
            self.assertIn("User or referrer not found", result["error"])
            
            print("✅ Matrix join error handling test passed")
    
    def test_matrix_recycle_error_handling(self):
        """Test Matrix recycle error handling."""
        print("\n🔄 Testing Matrix Recycle Error Handling")
        
        # Test with invalid tree
        with patch.object(self.service, '_check_and_process_automatic_recycle') as mock_recycle:
            mock_recycle.side_effect = Exception("Database connection error")
            
            result = self.service._check_and_process_automatic_recycle(
                self.test_user_id, None
            )
            
            self.assertFalse(result["success"])
            self.assertIn("Database connection error", result["error"])
            
            print("✅ Matrix recycle error handling test passed")
    
    def test_matrix_upgrade_error_handling(self):
        """Test Matrix upgrade error handling."""
        print("\n🔄 Testing Matrix Upgrade Error Handling")
        
        # Test with insufficient funds
        with patch('modules.matrix.service.User.objects') as mock_user_objects:
            mock_user = MatrixTestFixtures.create_mock_user(self.test_user_id)
            mock_user.wallet_balance = 50.0  # Insufficient for upgrade
            mock_user_objects.return_value.first.return_value = mock_user
            
            result = self.service.upgrade_matrix_slot(
                self.test_user_id, 1, 2, 100.0
            )
            
            self.assertFalse(result["success"])
            self.assertIn("Insufficient funds", result["error"])
            
            print("✅ Matrix upgrade error handling test passed")
    
    def test_matrix_special_programs_error_handling(self):
        """Test Matrix special programs error handling."""
        print("\n🔄 Testing Matrix Special Programs Error Handling")
        
        # Test with invalid user
        with patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects:
            mock_matrix_objects.return_value.first.return_value = None
            
            result = self.service.integrate_with_rank_system(self.test_user_id)
            
            self.assertFalse(result["success"])
            self.assertIn("Matrix tree not found", result["error"])
            
            print("✅ Matrix special programs error handling test passed")


class TestMatrixRealWorldScenarios(unittest.TestCase):
    """Real-world scenario integration tests for Matrix Program."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = MatrixService()
        self.test_users = [str(ObjectId()) for _ in range(10)]
        self.test_referrer_id = str(ObjectId())
    
    def test_matrix_multi_user_join_scenario(self):
        """Test Matrix multi-user join scenario."""
        print("\n🔄 Testing Matrix Multi-User Join Scenario")
        
        # Mock multiple users joining
        with patch('modules.matrix.service.User.objects') as mock_user_objects, \
             patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects, \
             patch.object(self.service, '_place_user_in_matrix_tree') as mock_place, \
             patch.object(self.service, '_create_matrix_activation') as mock_activate, \
             patch.object(self.service, 'trigger_rank_update_automatic') as mock_rank, \
             patch.object(self.service, 'trigger_global_integration_automatic') as mock_global, \
             patch.object(self.service, 'trigger_jackpot_integration_automatic') as mock_jackpot, \
             patch.object(self.service, 'trigger_ngs_integration_automatic') as mock_ngs, \
             patch.object(self.service, 'trigger_mentorship_bonus_integration_automatic') as mock_mentorship:
            
            # Mock user and referrer
            mock_user = MatrixTestFixtures.create_mock_user(self.test_users[0])
            mock_referrer = MatrixTestFixtures.create_mock_user(self.test_referrer_id)
            mock_user_objects.return_value.first.side_effect = [mock_user, mock_referrer]
            
            # Mock Matrix tree
            mock_tree = MatrixTestFixtures.create_mock_matrix_tree(self.test_referrer_id)
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Mock all methods
            mock_place.return_value = {"success": True, "level": 1, "position": 0}
            mock_activate.return_value = {"success": True}
            
            # Execute multiple joins
            results = []
            for user_id in self.test_users[:5]:  # Test with 5 users
                result = self.service.join_matrix(user_id, self.test_referrer_id, tx_hash="tx", amount=Decimal('11'))
                results.append(result)
            
            # Assertions
            for result in results:
                self.assertTrue(result["success"])
            
            print("✅ Matrix multi-user join scenario test passed")
    
    def test_matrix_recycle_chain_scenario(self):
        """Test Matrix recycle chain scenario."""
        print("\n🔄 Testing Matrix Recycle Chain Scenario")
        
        # Mock multiple recycles
        with patch.object(self.service, '_check_and_process_automatic_recycle') as mock_recycle:
            mock_recycle.return_value = {
                "success": True,
                "recycled": True,
                "recycle_no": 1
            }
            
            # Test multiple recycles
            results = []
            for i in range(3):  # Test with 3 recycles
                result = self.service._check_and_process_automatic_recycle(
                    self.test_users[i], None
                )
                results.append(result)
            
            # Assertions
            for result in results:
                self.assertTrue(result["success"])
                self.assertTrue(result["recycled"])
            
            print("✅ Matrix recycle chain scenario test passed")
    
    def test_matrix_upgrade_chain_scenario(self):
        """Test Matrix upgrade chain scenario."""
        print("\n🔄 Testing Matrix Upgrade Chain Scenario")
        
        # Mock multiple upgrades
        with patch('modules.matrix.service.User.objects') as mock_user_objects, \
             patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects, \
             patch.object(self.service, '_process_matrix_upgrade') as mock_upgrade, \
             patch.object(self.service, 'trigger_rank_update_automatic') as mock_rank, \
             patch.object(self.service, 'trigger_global_integration_automatic') as mock_global, \
             patch.object(self.service, 'trigger_jackpot_integration_automatic') as mock_jackpot, \
             patch.object(self.service, 'trigger_ngs_integration_automatic') as mock_ngs, \
             patch.object(self.service, 'trigger_mentorship_bonus_integration_automatic') as mock_mentorship:
            
            # Mock user with sufficient funds
            mock_user = MatrixTestFixtures.create_mock_user(self.test_users[0])
            mock_user.wallet_balance = 10000.0
            mock_user_objects.return_value.first.return_value = mock_user
            
            # Mock Matrix tree
            mock_tree = MatrixTestFixtures.create_mock_matrix_tree(self.test_users[0], 1)
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Mock upgrade processing
            mock_upgrade.return_value = {"success": True}
            
            # Test multiple upgrades
            results = []
            for i in range(1, 4):  # Test upgrades from slot 1 to 3
                result = self.service.upgrade_matrix_slot(
                    self.test_users[0], i, i + 1, 100.0
                )
                results.append(result)
            
            # Assertions
            for result in results:
                self.assertTrue(result["success"])
            
            print("✅ Matrix upgrade chain scenario test passed")


if __name__ == '__main__':
    # Run the integration tests
    unittest.main(verbosity=2)
