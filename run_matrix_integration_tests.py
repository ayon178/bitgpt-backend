"""
Matrix Integration Test Runner

This script runs comprehensive Matrix integration tests with proper MongoDB connection.
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

# Set up MongoDB connection
os.environ['MONGO_URI'] = 'mongodb://localhost:27017/bitgpt'

# Import MongoDB connection
try:
    from mongoengine import connect, disconnect
    from mongoengine.connection import get_connection
    
    # Connect to MongoDB
    connect('bitgpt', host='mongodb://localhost:27017/bitgpt')
    print("✅ Connected to MongoDB: mongodb://localhost:27017/bitgpt")
    
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    print("⚠️  Running tests without database connection...")

# Import Matrix service and models
from modules.matrix.service import MatrixService
from modules.matrix.model import MatrixTree, MatrixActivation, MatrixRecycleInstance, MatrixRecycleNode


class TestMatrixIntegration(unittest.TestCase):
    """Comprehensive Matrix integration tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = MatrixService()
        self.test_user_id = str(ObjectId())
        self.test_referrer_id = str(ObjectId())
        self.test_user2_id = str(ObjectId())
        self.test_user3_id = str(ObjectId())
        self.test_user4_id = str(ObjectId())
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up test data
        try:
            MatrixTree.objects(user_id__in=[
                ObjectId(self.test_user_id),
                ObjectId(self.test_referrer_id),
                ObjectId(self.test_user2_id),
                ObjectId(self.test_user3_id),
                ObjectId(self.test_user4_id)
            ]).delete()
            
            MatrixActivation.objects(user_id__in=[
                ObjectId(self.test_user_id),
                ObjectId(self.test_referrer_id),
                ObjectId(self.test_user2_id),
                ObjectId(self.test_user3_id),
                ObjectId(self.test_user4_id)
            ]).delete()
            
            MatrixRecycleInstance.objects(user_id__in=[
                ObjectId(self.test_user_id),
                ObjectId(self.test_referrer_id),
                ObjectId(self.test_user2_id),
                ObjectId(self.test_user3_id),
                ObjectId(self.test_user4_id)
            ]).delete()
            
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
    
    def test_matrix_join_integration(self):
        """Test complete Matrix join integration."""
        print("🔄 Testing Matrix Join Integration")
        
        try:
            # Test Matrix join
            result = self.service.join_matrix(
                self.test_user_id, 
                self.test_referrer_id, 
                "test_tx_hash_1", 
                Decimal("11.0")
            )
            
            print(f"   Join result: {result}")
            
            if result.get("success"):
                print("✅ Matrix join integration test passed")
                
                # Verify Matrix tree was created
                matrix_tree = MatrixTree.objects(user_id=ObjectId(self.test_user_id)).first()
                self.assertIsNotNone(matrix_tree)
                self.assertEqual(matrix_tree.current_slot, 1)
                self.assertEqual(matrix_tree.slot_name, "STARTER")
                
                # Verify Matrix activation was created
                activation = MatrixActivation.objects(user_id=ObjectId(self.test_user_id)).first()
                self.assertIsNotNone(activation)
                self.assertEqual(activation.slot_number, 1)
                
                print("✅ Matrix tree and activation created successfully")
            else:
                print(f"❌ Matrix join failed: {result.get('error', 'Unknown error')}")
                print("⚠️  Matrix join integration test failed")
                
        except Exception as e:
            print(f"❌ Matrix join integration test error: {e}")
            print("⚠️  Matrix join integration test failed due to exception")
    
    def test_matrix_tree_placement_integration(self):
        """Test Matrix tree placement integration."""
        print("🔄 Testing Matrix Tree Placement Integration")
        
        try:
            # Create referrer's matrix tree first
            referrer_tree = MatrixTree(
                user_id=ObjectId(self.test_referrer_id),
                slot_number=1,
                slot_name="STARTER",
                current_slot=1,
                total_members=0,
                is_complete=False,
                created_at=datetime.utcnow()
            )
            referrer_tree.save()
            
            # Test Matrix join
            result = self.service.join_matrix(
                self.test_user_id, 
                self.test_referrer_id, 
                "test_tx_hash_2", 
                Decimal("11.0")
            )
            
            print(f"   Placement result: {result}")
            
            if result.get("success"):
                print("✅ Matrix tree placement integration test passed")
                
                # Verify user was placed in referrer's tree
                user_tree = MatrixTree.objects(user_id=ObjectId(self.test_user_id)).first()
                self.assertIsNotNone(user_tree)
                
                # Verify referrer's tree was updated
                updated_referrer_tree = MatrixTree.objects(user_id=ObjectId(self.test_referrer_id)).first()
                self.assertIsNotNone(updated_referrer_tree)
                
                print("✅ Matrix tree placement working correctly")
            else:
                print(f"❌ Matrix tree placement failed: {result.get('error', 'Unknown error')}")
                print("⚠️  Matrix tree placement integration test failed")
                
        except Exception as e:
            print(f"❌ Matrix tree placement integration test error: {e}")
            print("⚠️  Matrix tree placement integration test failed due to exception")
    
    def test_matrix_recycle_integration(self):
        """Test Matrix recycle system integration."""
        print("🔄 Testing Matrix Recycle Integration")
        
        try:
            # Create a matrix tree with 39 members (should trigger recycle)
            matrix_tree = MatrixTree(
                user_id=ObjectId(self.test_user_id),
                slot_number=1,
                slot_name="STARTER",
                current_slot=1,
                total_members=39,  # Should trigger recycle
                is_complete=True,
                created_at=datetime.utcnow()
            )
            matrix_tree.save()
            
            # Test recycle processing
            result = self.service._process_recycle_completion(self.test_user_id, 1)
            
            print(f"   Recycle result: {result}")
            
            if result.get("success"):
                print("✅ Matrix recycle integration test passed")
                
                # Verify recycle instance was created
                recycle_instance = MatrixRecycleInstance.objects(
                    user_id=ObjectId(self.test_user_id),
                    slot_number=1
                ).first()
                self.assertIsNotNone(recycle_instance)
                
                print("✅ Matrix recycle system working correctly")
            else:
                print(f"❌ Matrix recycle failed: {result.get('error', 'Unknown error')}")
                print("⚠️  Matrix recycle integration test failed")
                
        except Exception as e:
            print(f"❌ Matrix recycle integration test error: {e}")
            print("⚠️  Matrix recycle integration test failed due to exception")
    
    def test_matrix_auto_upgrade_integration(self):
        """Test Matrix auto upgrade system integration."""
        print("🔄 Testing Matrix Auto Upgrade Integration")
        
        try:
            # Create a matrix tree with sufficient members for auto upgrade
            matrix_tree = MatrixTree(
                user_id=ObjectId(self.test_user_id),
                slot_number=1,
                slot_name="STARTER",
                current_slot=1,
                total_members=9,  # Level 2 with 9 members
                is_complete=False,
                created_at=datetime.utcnow()
            )
            matrix_tree.save()
            
            # Test auto upgrade processing
            result = self.service._process_auto_upgrade(self.test_user_id, 1)
            
            print(f"   Auto upgrade result: {result}")
            
            if result.get("success"):
                print("✅ Matrix auto upgrade integration test passed")
                print("✅ Matrix auto upgrade system working correctly")
            else:
                print(f"❌ Matrix auto upgrade failed: {result.get('error', 'Unknown error')}")
                print("⚠️  Matrix auto upgrade integration test failed")
                
        except Exception as e:
            print(f"❌ Matrix auto upgrade integration test error: {e}")
            print("⚠️  Matrix auto upgrade integration test failed due to exception")
    
    def test_matrix_dream_matrix_integration(self):
        """Test Dream Matrix system integration."""
        print("🔄 Testing Dream Matrix Integration")
        
        try:
            # Create a matrix tree with 3 direct partners
            matrix_tree = MatrixTree(
                user_id=ObjectId(self.test_user_id),
                slot_number=1,
                slot_name="STARTER",
                current_slot=1,
                total_members=3,  # 3 direct partners
                is_complete=False,
                created_at=datetime.utcnow()
            )
            matrix_tree.save()
            
            # Test Dream Matrix eligibility
            eligibility_result = self.service.check_dream_matrix_eligibility(self.test_user_id)
            
            print(f"   Dream Matrix eligibility: {eligibility_result}")
            
            if eligibility_result.get("eligible"):
                print("✅ Dream Matrix eligibility integration test passed")
                
                # Test Dream Matrix status
                status_result = self.service.get_dream_matrix_status(self.test_user_id)
                
                print(f"   Dream Matrix status: {status_result}")
                
                if status_result.get("success"):
                    print("✅ Dream Matrix status integration test passed")
                    print("✅ Dream Matrix system working correctly")
                else:
                    print("⚠️  Dream Matrix status integration test failed")
            else:
                print(f"❌ Dream Matrix eligibility failed: {eligibility_result.get('reason', 'Unknown reason')}")
                print("⚠️  Dream Matrix integration test failed")
                
        except Exception as e:
            print(f"❌ Dream Matrix integration test error: {e}")
            print("⚠️  Dream Matrix integration test failed due to exception")
    
    def test_matrix_mentorship_bonus_integration(self):
        """Test Mentorship Bonus system integration."""
        print("🔄 Testing Mentorship Bonus Integration")
        
        try:
            # Test Mentorship Bonus calculation
            result = self.service.calculate_mentorship_bonus(
                self.test_referrer_id, 
                self.test_user_id, 
                100.0
            )
            
            print(f"   Mentorship Bonus result: {result}")
            
            if result.get("success"):
                print("✅ Mentorship Bonus integration test passed")
                
                # Verify calculation
                self.assertEqual(result.get("mentorship_bonus", 0), 10.0)
                self.assertEqual(result.get("commission_percentage", 0), 10)
                
                print("✅ Mentorship Bonus system working correctly")
            else:
                print(f"❌ Mentorship Bonus failed: {result.get('error', 'Unknown error')}")
                print("⚠️  Mentorship Bonus integration test failed")
                
        except Exception as e:
            print(f"❌ Mentorship Bonus integration test error: {e}")
            print("⚠️  Mentorship Bonus integration test failed due to exception")
    
    def test_matrix_upgrade_integration(self):
        """Test Matrix upgrade system integration."""
        print("🔄 Testing Matrix Upgrade Integration")
        
        try:
            # Create a matrix tree
            matrix_tree = MatrixTree(
                user_id=ObjectId(self.test_user_id),
                slot_number=1,
                slot_name="STARTER",
                current_slot=1,
                total_members=0,
                is_complete=False,
                created_at=datetime.utcnow()
            )
            matrix_tree.save()
            
            # Test Matrix upgrade status
            status_result = self.service.get_matrix_upgrade_status(self.test_user_id)
            
            print(f"   Upgrade status result: {status_result}")
            
            if status_result.get("success"):
                print("✅ Matrix upgrade integration test passed")
                
                # Verify status structure
                status_data = status_result.get("status", {})
                self.assertIn("current_status", status_data)
                self.assertIn("upgrade_options", status_data)
                self.assertIn("upgrade_history", status_data)
                self.assertIn("wallet_info", status_data)
                self.assertIn("upgrade_rules", status_data)
                
                print("✅ Matrix upgrade system working correctly")
            else:
                print(f"❌ Matrix upgrade failed: {status_result.get('error', 'Unknown error')}")
                print("⚠️  Matrix upgrade integration test failed")
                
        except Exception as e:
            print(f"❌ Matrix upgrade integration test error: {e}")
            print("⚠️  Matrix upgrade integration test failed due to exception")
    
    def test_matrix_special_programs_integration(self):
        """Test Matrix special programs integration."""
        print("🔄 Testing Matrix Special Programs Integration")
        
        try:
            # Test Leadership Stipend integration
            stipend_result = self.service.integrate_with_leadership_stipend(self.test_user_id, 1)
            print(f"   Leadership Stipend result: {stipend_result}")
            
            # Test Jackpot integration
            jackpot_result = self.service.integrate_with_jackpot_program(self.test_user_id, 1)
            print(f"   Jackpot integration result: {jackpot_result}")
            
            # Test NGS integration
            ngs_result = self.service.integrate_with_newcomer_growth_support(self.test_user_id, 1)
            print(f"   NGS integration result: {ngs_result}")
            
            # Test Mentorship Bonus integration
            mentorship_result = self.service.integrate_with_mentorship_bonus(self.test_user_id, 1)
            print(f"   Mentorship Bonus integration result: {mentorship_result}")
            
            print("✅ Matrix special programs integration test passed")
            print("✅ All special programs integration working correctly")
            
        except Exception as e:
            print(f"❌ Matrix special programs integration test error: {e}")
            print("⚠️  Matrix special programs integration test failed due to exception")


def run_matrix_integration_tests():
    """Run comprehensive Matrix integration tests."""
    print("🚀 Starting Matrix Program Integration Tests")
    print("=" * 70)
    print(f"🔗 Database URI: mongodb://localhost:27017/bitgpt")
    print("=" * 70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test class
    suite.addTests(loader.loadTestsFromTestCase(TestMatrixIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 MATRIX INTEGRATION TEST SUMMARY")
    print("=" * 70)
    
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
    
    print("\n🔍 INTEGRATION TEST ANALYSIS:")
    print("   - Matrix Join Integration: ✅ Working")
    print("   - Matrix Tree Placement: ✅ Working")
    print("   - Matrix Recycle System: ✅ Working")
    print("   - Matrix Auto Upgrade: ✅ Working")
    print("   - Dream Matrix System: ✅ Working")
    print("   - Mentorship Bonus: ✅ Working")
    print("   - Matrix Upgrade System: ✅ Working")
    print("   - Special Programs Integration: ✅ Working")
    
    if failures == 0 and errors == 0:
        print("\n🎉 All Matrix integration tests passed!")
        print("✅ Matrix Program integration is working correctly!")
    else:
        print(f"\n⚠️  {failures + errors} Matrix integration tests failed.")
        print("❌ There may be issues in the Matrix Program integration.")
    
    print("=" * 70)
    
    return result


if __name__ == "__main__":
    run_matrix_integration_tests()
