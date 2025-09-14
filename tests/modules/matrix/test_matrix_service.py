"""
Unit Tests for Matrix Service

This module contains comprehensive unit tests for the Matrix Program implementation,
including all phases: Core Matrix, Recycle System, Auto Upgrade, Dream Matrix,
Mentorship Bonus, Manual Upgrades, and Special Programs Integration.

Test Coverage:
- Matrix join functionality
- Tree placement algorithms
- Recycle system
- Auto upgrade system
- Dream Matrix system
- Mentorship Bonus system
- Manual upgrade system
- Special programs integration (Rank, Global, Leadership Stipend, Jackpot, NGS, Mentorship)
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from bson import ObjectId
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from modules.matrix.service import MatrixService
from modules.matrix.model import (
    MatrixTree, MatrixNode, MatrixActivation, MatrixUpgradeLog,
    MatrixEarningHistory, MatrixCommission, MatrixRecycleInstance,
    MatrixRecycleNode, MatrixAutoUpgrade
)
from modules.user.model import User


class TestMatrixService(unittest.TestCase):
    """Test cases for MatrixService class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.service = MatrixService()
        self.test_user_id = str(ObjectId())
        self.test_referrer_id = str(ObjectId())
        
        # Mock user data
        self.mock_user = Mock()
        self.mock_user.id = ObjectId(self.test_user_id)
        self.mock_user.username = "testuser"
        self.mock_user.email = "test@example.com"
        
        # Mock referrer data
        self.mock_referrer = Mock()
        self.mock_referrer.id = ObjectId(self.test_referrer_id)
        self.mock_referrer.username = "referrer"
        self.mock_referrer.email = "referrer@example.com"
        
        # Mock Matrix tree data
        self.mock_matrix_tree = Mock()
        self.mock_matrix_tree.user_id = ObjectId(self.test_user_id)
        self.mock_matrix_tree.current_slot = 1
        self.mock_matrix_tree.total_members = 0
        self.mock_matrix_tree.is_complete = False
        self.mock_matrix_tree.nodes = []
    
    def tearDown(self):
        """Clean up after each test method."""
        pass
    
    # ==================== CORE MATRIX SYSTEM TESTS ====================
    
    @patch('modules.matrix.service.User.objects')
    @patch('modules.matrix.service.MatrixTree.objects')
    def test_join_matrix_success(self, mock_matrix_tree_objects, mock_user_objects):
        """Test successful Matrix join."""
        # Mock user and referrer
        mock_user_objects.return_value.first.side_effect = [self.mock_user, self.mock_referrer]
        
        # Mock Matrix tree for referrer
        mock_referrer_tree = Mock()
        mock_referrer_tree.user_id = ObjectId(self.test_referrer_id)
        mock_referrer_tree.current_slot = 1
        mock_referrer_tree.total_members = 0
        mock_referrer_tree.is_complete = False
        mock_referrer_tree.nodes = []
        
        mock_matrix_tree_objects.return_value.first.return_value = mock_referrer_tree
        
        # Mock tree placement
        with patch.object(self.service, '_place_user_in_matrix_tree') as mock_place:
            mock_place.return_value = {
                "success": True,
                "level": 1,
                "position": 0,
                "total_members": 1,
                "is_complete": False
            }
            
            # Mock activation creation
            with patch.object(self.service, '_create_matrix_activation') as mock_activate:
                mock_activate.return_value = {"success": True}
                
                # Execute join
                result = self.service.join_matrix(self.test_user_id, self.test_referrer_id)
                
                # Assertions
                self.assertTrue(result["success"])
                self.assertEqual(result["user_id"], self.test_user_id)
                self.assertEqual(result["referrer_id"], self.test_referrer_id)
                self.assertEqual(result["slot_activated"], 1)
    
    @patch('modules.matrix.service.User.objects')
    def test_join_matrix_user_not_found(self, mock_user_objects):
        """Test Matrix join with non-existent user."""
        mock_user_objects.return_value.first.return_value = None
        
        result = self.service.join_matrix(self.test_user_id, self.test_referrer_id)
        
        self.assertFalse(result["success"])
        self.assertIn("User not found", result["error"])
    
    @patch('modules.matrix.service.User.objects')
    def test_join_matrix_referrer_not_found(self, mock_user_objects):
        """Test Matrix join with non-existent referrer."""
        mock_user_objects.return_value.first.side_effect = [self.mock_user, None]
        
        result = self.service.join_matrix(self.test_user_id, self.test_referrer_id)
        
        self.assertFalse(result["success"])
        self.assertIn("Referrer not found", result["error"])
    
    # ==================== TREE PLACEMENT TESTS ====================
    
    def test_place_user_in_matrix_tree_bfs_algorithm(self):
        """Test BFS tree placement algorithm."""
        # Create a mock tree with some existing nodes
        mock_tree = Mock()
        mock_tree.nodes = [
            Mock(level=1, position=0, user_id=ObjectId()),
            Mock(level=1, position=1, user_id=ObjectId()),
            Mock(level=1, position=2, user_id=None),  # Empty position
        ]
        mock_tree.total_members = 2
        mock_tree.is_complete = False
        
        # Mock tree update
        with patch.object(self.service, '_update_matrix_tree_status') as mock_update:
            mock_update.return_value = {"success": True}
            
            result = self.service._place_user_in_matrix_tree(
                self.test_user_id, mock_tree, self.test_referrer_id
            )
            
            self.assertTrue(result["success"])
            self.assertEqual(result["level"], 1)
            self.assertEqual(result["position"], 2)  # Should fill the empty position
    
    def test_place_user_in_matrix_tree_recycle_trigger(self):
        """Test automatic recycle trigger when tree reaches 39 members."""
        # Create a mock tree with 38 members (one short of recycle)
        mock_tree = Mock()
        mock_tree.nodes = [Mock() for _ in range(38)]
        mock_tree.total_members = 38
        mock_tree.is_complete = False
        
        # Mock recycle processing
        with patch.object(self.service, '_check_and_process_automatic_recycle') as mock_recycle:
            mock_recycle.return_value = {"success": True, "recycled": True}
            
            # Mock tree update
            with patch.object(self.service, '_update_matrix_tree_status') as mock_update:
                mock_update.return_value = {"success": True}
                
                result = self.service._place_user_in_matrix_tree(
                    self.test_user_id, mock_tree, self.test_referrer_id
                )
                
                # Should trigger recycle
                mock_recycle.assert_called_once()
    
    # ==================== RECYCLE SYSTEM TESTS ====================
    
    @patch('modules.matrix.service.MatrixRecycleInstance')
    @patch('modules.matrix.service.MatrixRecycleNode')
    def test_check_and_process_automatic_recycle(self, mock_recycle_node, mock_recycle_instance):
        """Test automatic recycle processing."""
        # Mock tree with 39 members
        mock_tree = Mock()
        mock_tree.user_id = ObjectId(self.test_referrer_id)
        mock_tree.current_slot = 1
        mock_tree.nodes = [Mock() for _ in range(39)]
        mock_tree.total_members = 39
        mock_tree.is_complete = True
        
        # Mock recycle instance creation
        mock_instance = Mock()
        mock_recycle_instance.return_value = mock_instance
        
        # Mock recycle node creation
        mock_node = Mock()
        mock_recycle_node.return_value = mock_node
        
        result = self.service._check_and_process_automatic_recycle(
            self.test_referrer_id, mock_tree
        )
        
        self.assertTrue(result["success"])
        self.assertTrue(result["recycled"])
        self.assertEqual(result["recycle_no"], 1)
    
    def test_check_and_process_automatic_recycle_not_ready(self):
        """Test recycle processing when tree is not ready (less than 39 members)."""
        # Mock tree with 38 members
        mock_tree = Mock()
        mock_tree.total_members = 38
        mock_tree.is_complete = False
        
        result = self.service._check_and_process_automatic_recycle(
            self.test_referrer_id, mock_tree
        )
        
        self.assertTrue(result["success"])
        self.assertFalse(result["recycled"])
    
    # ==================== AUTO UPGRADE SYSTEM TESTS ====================
    
    def test_check_and_process_automatic_upgrade(self):
        """Test automatic upgrade processing."""
        # Mock tree with middle 3 members
        mock_tree = Mock()
        mock_tree.user_id = ObjectId(self.test_user_id)
        mock_tree.current_slot = 1
        mock_tree.nodes = [Mock() for _ in range(9)]  # Level 2 has 9 members
        
        # Mock middle 3 earnings calculation
        with patch.object(self.service, '_calculate_middle_three_earnings') as mock_earnings:
            mock_earnings.return_value = 100.0  # Sufficient for upgrade
            
            # Mock upgrade processing
            with patch.object(self.service, '_process_automatic_upgrade') as mock_upgrade:
                mock_upgrade.return_value = {"success": True, "upgraded": True}
                
                result = self.service._check_and_process_automatic_upgrade(
                    self.test_user_id, mock_tree
                )
                
                self.assertTrue(result["success"])
                self.assertTrue(result["upgraded"])
    
    def test_calculate_middle_three_earnings(self):
        """Test middle 3 earnings calculation."""
        # Mock tree with level 2 nodes
        mock_tree = Mock()
        mock_tree.nodes = [
            Mock(level=2, position=0, user_id=ObjectId()),  # Not middle
            Mock(level=2, position=1, user_id=ObjectId()),  # Middle 1
            Mock(level=2, position=2, user_id=ObjectId()),  # Not middle
            Mock(level=2, position=3, user_id=ObjectId()),  # Middle 2
            Mock(level=2, position=4, user_id=ObjectId()),  # Not middle
            Mock(level=2, position=5, user_id=ObjectId()),  # Middle 3
            Mock(level=2, position=6, user_id=ObjectId()),  # Not middle
            Mock(level=2, position=7, user_id=ObjectId()),  # Not middle
            Mock(level=2, position=8, user_id=ObjectId()),   # Not middle
        ]
        
        # Mock earnings calculation for middle 3
        with patch.object(self.service, '_calculate_node_earnings') as mock_node_earnings:
            mock_node_earnings.return_value = 50.0  # Each middle node earns 50
            
            earnings = self.service._calculate_middle_three_earnings(mock_tree)
            
            self.assertEqual(earnings, 150.0)  # 3 * 50
    
    # ==================== DREAM MATRIX SYSTEM TESTS ====================
    
    def test_check_and_process_dream_matrix_eligibility(self):
        """Test Dream Matrix eligibility check and processing."""
        # Mock user with 3 direct partners
        mock_tree = Mock()
        mock_tree.user_id = ObjectId(self.test_user_id)
        mock_tree.current_slot = 1
        mock_tree.nodes = [
            Mock(level=1, position=0, user_id=ObjectId()),  # Direct partner 1
            Mock(level=1, position=1, user_id=ObjectId()),  # Direct partner 2
            Mock(level=1, position=2, user_id=ObjectId()),  # Direct partner 3
        ]
        
        # Mock Dream Matrix processing
        with patch.object(self.service, '_process_dream_matrix_distribution') as mock_dream:
            mock_dream.return_value = {"success": True, "distributed": True}
            
            result = self.service._check_and_process_dream_matrix_eligibility(
                self.test_user_id, mock_tree
            )
            
            self.assertTrue(result["success"])
            self.assertTrue(result["eligible"])
    
    def test_dream_matrix_eligibility_not_met(self):
        """Test Dream Matrix eligibility when user doesn't have 3 direct partners."""
        # Mock user with only 2 direct partners
        mock_tree = Mock()
        mock_tree.user_id = ObjectId(self.test_user_id)
        mock_tree.current_slot = 1
        mock_tree.nodes = [
            Mock(level=1, position=0, user_id=ObjectId()),  # Direct partner 1
            Mock(level=1, position=1, user_id=ObjectId()),  # Direct partner 2
            Mock(level=1, position=2, user_id=None),       # Empty position
        ]
        
        result = self.service._check_and_process_dream_matrix_eligibility(
            self.test_user_id, mock_tree
        )
        
        self.assertTrue(result["success"])
        self.assertFalse(result["eligible"])
    
    # ==================== MENTORSHIP BONUS SYSTEM TESTS ====================
    
    def test_track_mentorship_relationships_automatic(self):
        """Test automatic mentorship relationship tracking."""
        # Mock referrer tree
        mock_referrer_tree = Mock()
        mock_referrer_tree.user_id = ObjectId(self.test_referrer_id)
        mock_referrer_tree.current_slot = 1
        
        # Mock mentorship processing
        with patch.object(self.service, '_process_mentorship_bonus') as mock_mentorship:
            mock_mentorship.return_value = {"success": True, "bonus_awarded": True}
            
            result = self.service._track_mentorship_relationships_automatic(
                self.test_referrer_id, self.test_user_id
            )
            
            self.assertTrue(result["success"])
            self.assertTrue(result["tracked"])
    
    # ==================== MANUAL UPGRADE SYSTEM TESTS ====================
    
    @patch('modules.matrix.service.MatrixTree.objects')
    @patch('modules.matrix.service.User.objects')
    def test_upgrade_matrix_slot_success(self, mock_user_objects, mock_matrix_tree_objects):
        """Test successful Matrix slot upgrade."""
        # Mock user with sufficient wallet balance
        mock_user = Mock()
        mock_user.id = ObjectId(self.test_user_id)
        mock_user.wallet_balance = 1000.0
        mock_user_objects.return_value.first.return_value = mock_user
        
        # Mock Matrix tree
        mock_tree = Mock()
        mock_tree.user_id = ObjectId(self.test_user_id)
        mock_tree.current_slot = 1
        mock_matrix_tree_objects.return_value.first.return_value = mock_tree
        
        # Mock upgrade processing
        with patch.object(self.service, '_process_matrix_upgrade') as mock_upgrade:
            mock_upgrade.return_value = {"success": True}
            
            result = self.service.upgrade_matrix_slot(
                self.test_user_id, 1, 2, 100.0
            )
            
            self.assertTrue(result["success"])
            self.assertEqual(result["from_slot_no"], 1)
            self.assertEqual(result["to_slot_no"], 2)
    
    @patch('modules.matrix.service.User.objects')
    def test_upgrade_matrix_slot_insufficient_funds(self, mock_user_objects):
        """Test Matrix slot upgrade with insufficient funds."""
        # Mock user with insufficient wallet balance
        mock_user = Mock()
        mock_user.id = ObjectId(self.test_user_id)
        mock_user.wallet_balance = 50.0  # Less than upgrade cost
        mock_user_objects.return_value.first.return_value = mock_user
        
        result = self.service.upgrade_matrix_slot(
            self.test_user_id, 1, 2, 100.0
        )
        
        self.assertFalse(result["success"])
        self.assertIn("Insufficient funds", result["error"])
    
    # ==================== SPECIAL PROGRAMS INTEGRATION TESTS ====================
    
    def test_integrate_with_rank_system(self):
        """Test Rank System integration."""
        # Mock rank update
        with patch.object(self.service, 'update_user_rank_from_programs') as mock_rank:
            mock_rank.return_value = {"success": True, "rank_updated": True}
            
            result = self.service.integrate_with_rank_system(self.test_user_id)
            
            self.assertTrue(result["success"])
            self.assertTrue(result["rank_updated"])
    
    def test_integrate_with_global_program(self):
        """Test Global Program integration."""
        # Mock Matrix tree
        mock_tree = Mock()
        mock_tree.current_slot = 1
        
        with patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects:
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Mock Global Program processing
            with patch.object(self.service, '_process_global_distribution') as mock_global:
                mock_global.return_value = {"success": True, "distributed": True}
                
                result = self.service.integrate_with_global_program(self.test_user_id)
                
                self.assertTrue(result["success"])
                self.assertTrue(result["integrated"])
    
    def test_integrate_with_leadership_stipend(self):
        """Test Leadership Stipend integration."""
        # Mock Matrix tree with eligible slot (slot 10)
        mock_tree = Mock()
        mock_tree.current_slot = 10
        
        with patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects:
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Mock Leadership Stipend processing
            with patch.object(self.service, '_process_leadership_stipend_distribution') as mock_stipend:
                mock_stipend.return_value = {"success": True, "distributed": True}
                
                result = self.service.integrate_with_leadership_stipend(self.test_user_id)
                
                self.assertTrue(result["success"])
                self.assertTrue(result["integrated"])
    
    def test_integrate_with_jackpot_program(self):
        """Test Jackpot Program integration."""
        # Mock Matrix tree
        mock_tree = Mock()
        mock_tree.current_slot = 5
        
        with patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects:
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Mock Jackpot Program processing
            with patch.object(self.service, '_process_jackpot_program_distribution') as mock_jackpot:
                mock_jackpot.return_value = {"success": True, "distributed": True}
                
                result = self.service.integrate_with_jackpot_program(self.test_user_id)
                
                self.assertTrue(result["success"])
                self.assertTrue(result["integrated"])
    
    def test_integrate_with_newcomer_growth_support(self):
        """Test NGS integration."""
        # Mock Matrix tree
        mock_tree = Mock()
        mock_tree.current_slot = 1
        
        with patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects:
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Mock NGS processing
            with patch.object(self.service, '_process_ngs_instant_bonus') as mock_ngs:
                mock_ngs.return_value = {"success": True, "processed": True}
                
                result = self.service.integrate_with_newcomer_growth_support(self.test_user_id)
                
                self.assertTrue(result["success"])
                self.assertTrue(result["integrated"])
    
    def test_integrate_with_mentorship_bonus(self):
        """Test Mentorship Bonus integration."""
        # Mock Matrix tree
        mock_tree = Mock()
        mock_tree.current_slot = 1
        
        with patch('modules.matrix.service.MatrixTree.objects') as mock_matrix_objects:
            mock_matrix_objects.return_value.first.return_value = mock_tree
            
            # Mock Mentorship Bonus processing
            with patch.object(self.service, '_process_mentorship_bonus_distribution') as mock_mentorship:
                mock_mentorship.return_value = {"success": True, "processed": True}
                
                result = self.service.integrate_with_mentorship_bonus(self.test_user_id)
                
                self.assertTrue(result["success"])
                self.assertTrue(result["integrated"])
    
    # ==================== UTILITY METHOD TESTS ====================
    
    def test_calculate_rank_from_slots(self):
        """Test rank calculation from total slots."""
        # Test various slot combinations
        test_cases = [
            (1, "Bitron"),      # Rank 1
            (5, "Stellar"),     # Rank 5
            (10, "Nexus"),      # Rank 10
            (15, "Omega"),      # Rank 15
            (20, "Omega"),     # Beyond max rank
        ]
        
        for total_slots, expected_rank in test_cases:
            rank = self.service._calculate_rank_from_slots(total_slots)
            self.assertEqual(rank, expected_rank)
    
    def test_check_leadership_stipend_eligibility(self):
        """Test Leadership Stipend eligibility check."""
        # Test eligible slots (10-16)
        for slot in range(10, 17):
            result = self.service._check_leadership_stipend_eligibility(slot)
            self.assertTrue(result["is_eligible"])
        
        # Test ineligible slots (1-9)
        for slot in range(1, 10):
            result = self.service._check_leadership_stipend_eligibility(slot)
            self.assertFalse(result["is_eligible"])
    
    def test_calculate_leadership_stipend_contribution(self):
        """Test Leadership Stipend contribution calculation."""
        # Test slot 10 (LEADER)
        contribution = self.service._calculate_leadership_stipend_contribution(10)
        expected = 1.1264 * 2  # Double slot value
        self.assertEqual(contribution, expected)
        
        # Test slot 15 (STAR)
        contribution = self.service._calculate_leadership_stipend_contribution(15)
        expected = 52612659 * 2  # Double slot value
        self.assertEqual(contribution, expected)


class TestMatrixModels(unittest.TestCase):
    """Test cases for Matrix models."""
    
    def test_matrix_tree_model(self):
        """Test MatrixTree model creation."""
        tree = MatrixTree(
            user_id=ObjectId(),
            current_slot=1,
            total_members=0,
            is_complete=False,
            nodes=[]
        )
        
        self.assertEqual(tree.current_slot, 1)
        self.assertEqual(tree.total_members, 0)
        self.assertFalse(tree.is_complete)
        self.assertEqual(len(tree.nodes), 0)
    
    def test_matrix_node_model(self):
        """Test MatrixNode model creation."""
        node = MatrixNode(
            level=1,
            position=0,
            user_id=ObjectId(),
            placed_at=datetime.utcnow()
        )
        
        self.assertEqual(node.level, 1)
        self.assertEqual(node.position, 0)
        self.assertIsNotNone(node.user_id)
        self.assertIsNotNone(node.placed_at)
    
    def test_matrix_activation_model(self):
        """Test MatrixActivation model creation."""
        activation = MatrixActivation(
            user_id=ObjectId(),
            slot_number=1,
            slot_name="STARTER",
            slot_value=11,
            activated_at=datetime.utcnow()
        )
        
        self.assertEqual(activation.slot_number, 1)
        self.assertEqual(activation.slot_name, "STARTER")
        self.assertEqual(activation.slot_value, 11)
        self.assertIsNotNone(activation.activated_at)
    
    def test_matrix_recycle_instance_model(self):
        """Test MatrixRecycleInstance model creation."""
        instance = MatrixRecycleInstance(
            user_id=ObjectId(),
            slot_number=1,
            recycle_no=1,
            is_complete=True,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        self.assertEqual(instance.slot_number, 1)
        self.assertEqual(instance.recycle_no, 1)
        self.assertTrue(instance.is_complete)
        self.assertIsNotNone(instance.created_at)
        self.assertIsNotNone(instance.completed_at)
    
    def test_matrix_recycle_node_model(self):
        """Test MatrixRecycleNode model creation."""
        node = MatrixRecycleNode(
            instance_id=ObjectId(),
            occupant_user_id=ObjectId(),
            level_index=1,
            position_index=0,
            placed_at=datetime.utcnow()
        )
        
        self.assertEqual(node.level_index, 1)
        self.assertEqual(node.position_index, 0)
        self.assertIsNotNone(node.occupant_user_id)
        self.assertIsNotNone(node.placed_at)


class TestMatrixIntegration(unittest.TestCase):
    """Integration tests for Matrix Program."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = MatrixService()
        self.test_user_id = str(ObjectId())
        self.test_referrer_id = str(ObjectId())
    
    @patch('modules.matrix.service.User.objects')
    @patch('modules.matrix.service.MatrixTree.objects')
    def test_full_matrix_join_flow(self, mock_matrix_tree_objects, mock_user_objects):
        """Test complete Matrix join flow with all integrations."""
        # Mock user and referrer
        mock_user = Mock()
        mock_user.id = ObjectId(self.test_user_id)
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        
        mock_referrer = Mock()
        mock_referrer.id = ObjectId(self.test_referrer_id)
        mock_referrer.username = "referrer"
        mock_referrer.email = "referrer@example.com"
        
        mock_user_objects.return_value.first.side_effect = [mock_user, mock_referrer]
        
        # Mock referrer's Matrix tree
        mock_referrer_tree = Mock()
        mock_referrer_tree.user_id = ObjectId(self.test_referrer_id)
        mock_referrer_tree.current_slot = 1
        mock_referrer_tree.total_members = 0
        mock_referrer_tree.is_complete = False
        mock_referrer_tree.nodes = []
        
        mock_matrix_tree_objects.return_value.first.return_value = mock_referrer_tree
        
        # Mock all integration methods
        with patch.object(self.service, '_place_user_in_matrix_tree') as mock_place, \
             patch.object(self.service, '_create_matrix_activation') as mock_activate, \
             patch.object(self.service, 'trigger_rank_update_automatic') as mock_rank, \
             patch.object(self.service, 'trigger_global_integration_automatic') as mock_global, \
             patch.object(self.service, 'trigger_jackpot_integration_automatic') as mock_jackpot, \
             patch.object(self.service, 'trigger_ngs_integration_automatic') as mock_ngs, \
             patch.object(self.service, 'trigger_mentorship_bonus_integration_automatic') as mock_mentorship:
            
            mock_place.return_value = {"success": True, "level": 1, "position": 0}
            mock_activate.return_value = {"success": True}
            
            # Execute join
            result = self.service.join_matrix(self.test_user_id, self.test_referrer_id)
            
            # Assertions
            self.assertTrue(result["success"])
            
            # Verify all integrations were triggered
            mock_rank.assert_called_once_with(self.test_user_id)
            mock_global.assert_called_once_with(self.test_user_id)
            mock_jackpot.assert_called_once_with(self.test_user_id)
            mock_ngs.assert_called_once_with(self.test_user_id)
            mock_mentorship.assert_called_once_with(self.test_user_id)
    
    @patch('modules.matrix.service.User.objects')
    @patch('modules.matrix.service.MatrixTree.objects')
    def test_full_matrix_upgrade_flow(self, mock_matrix_tree_objects, mock_user_objects):
        """Test complete Matrix upgrade flow with all integrations."""
        # Mock user with sufficient funds
        mock_user = Mock()
        mock_user.id = ObjectId(self.test_user_id)
        mock_user.wallet_balance = 1000.0
        mock_user_objects.return_value.first.return_value = mock_user
        
        # Mock Matrix tree
        mock_tree = Mock()
        mock_tree.user_id = ObjectId(self.test_user_id)
        mock_tree.current_slot = 1
        mock_matrix_tree_objects.return_value.first.return_value = mock_tree
        
        # Mock all integration methods
        with patch.object(self.service, '_process_matrix_upgrade') as mock_upgrade, \
             patch.object(self.service, 'trigger_rank_update_automatic') as mock_rank, \
             patch.object(self.service, 'trigger_global_integration_automatic') as mock_global, \
             patch.object(self.service, 'trigger_leadership_stipend_integration_automatic') as mock_stipend, \
             patch.object(self.service, 'trigger_jackpot_integration_automatic') as mock_jackpot, \
             patch.object(self.service, 'trigger_ngs_integration_automatic') as mock_ngs, \
             patch.object(self.service, 'trigger_mentorship_bonus_integration_automatic') as mock_mentorship:
            
            mock_upgrade.return_value = {"success": True}
            
            # Execute upgrade
            result = self.service.upgrade_matrix_slot(
                self.test_user_id, 1, 2, 100.0
            )
            
            # Assertions
            self.assertTrue(result["success"])
            
            # Verify all integrations were triggered
            mock_rank.assert_called_once_with(self.test_user_id)
            mock_global.assert_called_once_with(self.test_user_id)
            mock_jackpot.assert_called_once_with(self.test_user_id)
            mock_ngs.assert_called_once_with(self.test_user_id)
            mock_mentorship.assert_called_once_with(self.test_user_id)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
