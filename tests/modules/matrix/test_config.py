"""
Test Configuration for Matrix Program

This module contains test configuration, fixtures, and utilities
for comprehensive testing of the Matrix Program implementation.
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
from modules.matrix.model import *
from modules.user.model import User


class MatrixTestConfig:
    """Configuration class for Matrix tests."""
    
    # Test user IDs
    TEST_USER_ID = "507f1f77bcf86cd799439011"
    TEST_REFERRER_ID = "507f1f77bcf86cd799439012"
    TEST_UPLINE_ID = "507f1f77bcf86cd799439013"
    
    # Test slot values
    SLOT_VALUES = {
        1: 11,      # STARTER
        2: 33,      # BRONZE
        3: 99,      # SILVER
        4: 297,     # GOLD
        5: 891,     # PLATINUM
        6: 2673,    # DIAMOND
        7: 8019,    # RUBY
        8: 24057,   # EMERALD
        9: 72171,   # SAPPHIRE
        10: 216513, # TOPAZ
        11: 649539, # PEARL
        12: 1948617, # AMETHYST
        13: 5845851, # OBSIDIAN
        14: 17537553, # TITANIUM
        15: 52612659  # STAR
    }
    
    # Test slot names
    SLOT_NAMES = {
        1: "STARTER",
        2: "BRONZE",
        3: "SILVER",
        4: "GOLD",
        5: "PLATINUM",
        6: "DIAMOND",
        7: "RUBY",
        8: "EMERALD",
        9: "SAPPHIRE",
        10: "TOPAZ",
        11: "PEARL",
        12: "AMETHYST",
        13: "OBSIDIAN",
        14: "TITANIUM",
        15: "STAR"
    }
    
    # Test rank mapping
    RANK_MAPPING = {
        1: "Bitron",
        2: "Cryzen",
        3: "Neura",
        4: "Glint",
        5: "Stellar",
        6: "Ignis",
        7: "Quanta",
        8: "Lumix",
        9: "Arion",
        10: "Nexus",
        11: "Fyre",
        12: "Axion",
        13: "Trion",
        14: "Spectra",
        15: "Omega"
    }
    
    # Test distribution percentages
    DISTRIBUTION_PERCENTAGES = {
        "global": {
            "level": 40,
            "profit": 30,
            "royal_captain": 15,
            "president_reward": 15,
            "triple_entry": 5,
            "shareholders": 5
        },
        "leadership_stipend": {
            "level_10": 1.5,
            "level_11": 1.0,
            "level_12": 0.5,
            "level_13": 0.5,
            "level_14": 0.5,
            "level_15": 0.5,
            "level_16": 0.5
        },
        "jackpot": {
            "open_pool": 50,
            "top_direct_promoters": 30,
            "top_buyers": 10,
            "binary_contribution": 5
        },
        "ngs": {
            "instant_bonus": 5,
            "extra_earning": 3,
            "upline_rank_bonus": 2
        },
        "mentorship_bonus": {
            "direct_of_direct_commission": 10
        }
    }


class MatrixTestFixtures:
    """Test fixtures for Matrix Program."""
    
    @staticmethod
    def create_mock_user(user_id=None, username="testuser", email="test@example.com"):
        """Create a mock user object."""
        if user_id is None:
            user_id = MatrixTestConfig.TEST_USER_ID
        
        mock_user = Mock()
        mock_user.id = ObjectId(user_id)
        mock_user.username = username
        mock_user.email = email
        mock_user.wallet_balance = 1000.0
        mock_user.created_at = datetime.utcnow()
        
        return mock_user
    
    @staticmethod
    def create_mock_matrix_tree(user_id=None, current_slot=1, total_members=0):
        """Create a mock Matrix tree object."""
        if user_id is None:
            user_id = MatrixTestConfig.TEST_USER_ID
        
        mock_tree = Mock()
        mock_tree.user_id = ObjectId(user_id)
        mock_tree.current_slot = current_slot
        mock_tree.total_members = total_members
        mock_tree.is_complete = False
        mock_tree.nodes = []
        mock_tree.created_at = datetime.utcnow()
        
        return mock_tree
    
    @staticmethod
    def create_mock_matrix_node(level=1, position=0, user_id=None):
        """Create a mock Matrix node object."""
        if user_id is None:
            user_id = MatrixTestConfig.TEST_USER_ID
        
        mock_node = Mock()
        mock_node.level = level
        mock_node.position = position
        mock_node.user_id = ObjectId(user_id)
        mock_node.placed_at = datetime.utcnow()
        
        return mock_node
    
    @staticmethod
    def create_mock_matrix_activation(user_id=None, slot_number=1):
        """Create a mock Matrix activation object."""
        if user_id is None:
            user_id = MatrixTestConfig.TEST_USER_ID
        
        mock_activation = Mock()
        mock_activation.user_id = ObjectId(user_id)
        mock_activation.slot_number = slot_number
        mock_activation.slot_name = MatrixTestConfig.SLOT_NAMES.get(slot_number, "UNKNOWN")
        mock_activation.slot_value = MatrixTestConfig.SLOT_VALUES.get(slot_number, 0)
        mock_activation.activated_at = datetime.utcnow()
        
        return mock_activation
    
    @staticmethod
    def create_mock_recycle_instance(user_id=None, slot_number=1, recycle_no=1):
        """Create a mock Matrix recycle instance object."""
        if user_id is None:
            user_id = MatrixTestConfig.TEST_USER_ID
        
        mock_instance = Mock()
        mock_instance.user_id = ObjectId(user_id)
        mock_instance.slot_number = slot_number
        mock_instance.recycle_no = recycle_no
        mock_instance.is_complete = True
        mock_instance.created_at = datetime.utcnow()
        mock_instance.completed_at = datetime.utcnow()
        
        return mock_instance
    
    @staticmethod
    def create_mock_recycle_node(instance_id=None, occupant_user_id=None, level_index=1, position_index=0):
        """Create a mock Matrix recycle node object."""
        if instance_id is None:
            instance_id = MatrixTestConfig.TEST_USER_ID
        if occupant_user_id is None:
            occupant_user_id = MatrixTestConfig.TEST_USER_ID
        
        mock_node = Mock()
        mock_node.instance_id = ObjectId(instance_id)
        mock_node.occupant_user_id = ObjectId(occupant_user_id)
        mock_node.level_index = level_index
        mock_node.position_index = position_index
        mock_node.placed_at = datetime.utcnow()
        
        return mock_node


class MatrixTestUtils:
    """Utility functions for Matrix tests."""
    
    @staticmethod
    def assert_matrix_response_structure(response_data, expected_keys):
        """Assert that response data has expected structure."""
        for key in expected_keys:
            assert key in response_data, f"Missing key: {key}"
    
    @staticmethod
    def assert_matrix_tree_structure(tree_data, expected_structure):
        """Assert that Matrix tree data has expected structure."""
        assert "user_id" in tree_data
        assert "current_slot" in tree_data
        assert "total_members" in tree_data
        assert "is_complete" in tree_data
        assert "nodes" in tree_data
    
    @staticmethod
    def assert_matrix_node_structure(node_data, expected_structure):
        """Assert that Matrix node data has expected structure."""
        assert "level" in node_data
        assert "position" in node_data
        assert "user_id" in node_data
        assert "placed_at" in node_data
    
    @staticmethod
    def assert_matrix_activation_structure(activation_data, expected_structure):
        """Assert that Matrix activation data has expected structure."""
        assert "user_id" in activation_data
        assert "slot_number" in activation_data
        assert "slot_name" in activation_data
        assert "slot_value" in activation_data
        assert "activated_at" in activation_data
    
    @staticmethod
    def assert_recycle_instance_structure(instance_data, expected_structure):
        """Assert that Matrix recycle instance data has expected structure."""
        assert "user_id" in instance_data
        assert "slot_number" in instance_data
        assert "recycle_no" in instance_data
        assert "is_complete" in instance_data
        assert "created_at" in instance_data
    
    @staticmethod
    def assert_recycle_node_structure(node_data, expected_structure):
        """Assert that Matrix recycle node data has expected structure."""
        assert "instance_id" in node_data
        assert "occupant_user_id" in node_data
        assert "level_index" in node_data
        assert "position_index" in node_data
        assert "placed_at" in node_data
    
    @staticmethod
    def calculate_expected_earnings(slot_number, percentage):
        """Calculate expected earnings for a given slot and percentage."""
        slot_value = MatrixTestConfig.SLOT_VALUES.get(slot_number, 0)
        return slot_value * (percentage / 100)
    
    @staticmethod
    def calculate_expected_upgrade_cost(from_slot, to_slot):
        """Calculate expected upgrade cost from one slot to another."""
        from_value = MatrixTestConfig.SLOT_VALUES.get(from_slot, 0)
        to_value = MatrixTestConfig.SLOT_VALUES.get(to_slot, 0)
        return to_value - from_value
    
    @staticmethod
    def get_expected_rank(total_slots):
        """Get expected rank for total number of slots."""
        if total_slots <= 0:
            return None
        
        rank_number = min(total_slots, 15)
        return MatrixTestConfig.RANK_MAPPING.get(rank_number, "Unknown")
    
    @staticmethod
    def validate_distribution_percentages(distribution, expected_total=100):
        """Validate that distribution percentages sum to expected total."""
        total = sum(distribution.values())
        assert abs(total - expected_total) < 0.01, f"Distribution percentages sum to {total}, expected {expected_total}"


class MatrixTestData:
    """Test data for Matrix Program."""
    
    # Sample Matrix tree structures
    SAMPLE_TREE_STRUCTURES = {
        "empty_tree": {
            "user_id": MatrixTestConfig.TEST_USER_ID,
            "current_slot": 1,
            "total_members": 0,
            "is_complete": False,
            "nodes": []
        },
        "level_1_complete": {
            "user_id": MatrixTestConfig.TEST_USER_ID,
            "current_slot": 1,
            "total_members": 3,
            "is_complete": False,
            "nodes": [
                {"level": 1, "position": 0, "user_id": MatrixTestConfig.TEST_USER_ID},
                {"level": 1, "position": 1, "user_id": MatrixTestConfig.TEST_USER_ID},
                {"level": 1, "position": 2, "user_id": MatrixTestConfig.TEST_USER_ID}
            ]
        },
        "level_2_partial": {
            "user_id": MatrixTestConfig.TEST_USER_ID,
            "current_slot": 1,
            "total_members": 6,
            "is_complete": False,
            "nodes": [
                {"level": 1, "position": 0, "user_id": MatrixTestConfig.TEST_USER_ID},
                {"level": 1, "position": 1, "user_id": MatrixTestConfig.TEST_USER_ID},
                {"level": 1, "position": 2, "user_id": MatrixTestConfig.TEST_USER_ID},
                {"level": 2, "position": 0, "user_id": MatrixTestConfig.TEST_USER_ID},
                {"level": 2, "position": 1, "user_id": MatrixTestConfig.TEST_USER_ID},
                {"level": 2, "position": 2, "user_id": MatrixTestConfig.TEST_USER_ID}
            ]
        },
        "recycle_ready": {
            "user_id": MatrixTestConfig.TEST_USER_ID,
            "current_slot": 1,
            "total_members": 39,
            "is_complete": True,
            "nodes": [{"level": i//3 + 1, "position": i%3, "user_id": MatrixTestConfig.TEST_USER_ID} for i in range(39)]
        }
    }
    
    # Sample upgrade scenarios
    SAMPLE_UPGRADE_SCENARIOS = [
        {
            "from_slot": 1,
            "to_slot": 2,
            "upgrade_cost": 22,  # 33 - 11
            "slot_name": "BRONZE"
        },
        {
            "from_slot": 2,
            "to_slot": 3,
            "upgrade_cost": 66,  # 99 - 33
            "slot_name": "SILVER"
        },
        {
            "from_slot": 5,
            "to_slot": 6,
            "upgrade_cost": 1782,  # 2673 - 891
            "slot_name": "DIAMOND"
        }
    ]
    
    # Sample earning scenarios
    SAMPLE_EARNING_SCENARIOS = [
        {
            "slot_number": 1,
            "slot_value": 11,
            "expected_earnings": {
                "global_contribution": 0.55,  # 5% of 11
                "jackpot_contribution": 0.22,  # 2% of 11
                "ngs_benefits": 1.10,  # 10% of 11
                "mentorship_bonus": 1.10  # 10% of 11
            }
        },
        {
            "slot_number": 5,
            "slot_value": 891,
            "expected_earnings": {
                "global_contribution": 44.55,  # 5% of 891
                "jackpot_contribution": 17.82,  # 2% of 891
                "ngs_benefits": 89.10,  # 10% of 891
                "mentorship_bonus": 89.10  # 10% of 891
            }
        }
    ]


# Test decorators and markers
def matrix_test(test_func):
    """Decorator for Matrix-specific tests."""
    return pytest.mark.matrix(test_func)

def integration_test(test_func):
    """Decorator for integration tests."""
    return pytest.mark.integration(test_func)

def unit_test(test_func):
    """Decorator for unit tests."""
    return pytest.mark.unit(test_func)

def performance_test(test_func):
    """Decorator for performance tests."""
    return pytest.mark.performance(test_func)


# Test constants
class TestConstants:
    """Constants for Matrix tests."""
    
    # Test timeouts
    TIMEOUT_SHORT = 1
    TIMEOUT_MEDIUM = 5
    TIMEOUT_LONG = 10
    
    # Test retry counts
    RETRY_COUNT = 3
    
    # Test data sizes
    SMALL_DATASET = 10
    MEDIUM_DATASET = 100
    LARGE_DATASET = 1000
    
    # Test precision
    FLOAT_PRECISION = 0.01
    PERCENTAGE_PRECISION = 0.1


if __name__ == '__main__':
    # Run configuration tests
    print("Matrix Test Configuration loaded successfully")
    print(f"Test User ID: {MatrixTestConfig.TEST_USER_ID}")
    print(f"Test Referrer ID: {MatrixTestConfig.TEST_REFERRER_ID}")
    print(f"Slot Values: {len(MatrixTestConfig.SLOT_VALUES)} slots")
    print(f"Rank Mapping: {len(MatrixTestConfig.RANK_MAPPING)} ranks")
    print(f"Distribution Percentages: {len(MatrixTestConfig.DISTRIBUTION_PERCENTAGES)} programs")
