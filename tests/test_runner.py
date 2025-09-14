"""
Test Runner for Matrix Program

This script provides comprehensive test execution for the Matrix Program implementation,
including unit tests, integration tests, and performance tests.

Usage:
    python test_runner.py                    # Run all tests
    python test_runner.py --unit             # Run only unit tests
    python test_runner.py --integration      # Run only integration tests
    python test_runner.py --performance     # Run only performance tests
    python test_runner.py --coverage        # Run with coverage report
    python test_runner.py --verbose         # Run with verbose output
"""

import unittest
import sys
import os
import argparse
import time
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import test modules
from tests.modules.matrix.test_matrix_service import TestMatrixService, TestMatrixModels, TestMatrixIntegration
from tests.modules.matrix.test_matrix_router import TestMatrixRouter, TestMatrixAPIIntegration
from tests.modules.matrix.test_config import MatrixTestConfig, MatrixTestFixtures, MatrixTestUtils


class MatrixTestRunner:
    """Test runner for Matrix Program."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
    
    def run_all_tests(self, verbose=False):
        """Run all Matrix tests."""
        print("🚀 Starting Matrix Program Test Suite")
        print("=" * 60)
        
        self.start_time = time.time()
        
        # Test suites
        test_suites = [
            ("Unit Tests", self.run_unit_tests),
            ("Integration Tests", self.run_integration_tests),
            ("API Tests", self.run_api_tests),
            ("Configuration Tests", self.run_config_tests)
        ]
        
        for suite_name, test_function in test_suites:
            print(f"\n📋 Running {suite_name}")
            print("-" * 40)
            
            try:
                suite_results = test_function(verbose)
                self.test_results[suite_name] = suite_results
                self.total_tests += suite_results["total"]
                self.passed_tests += suite_results["passed"]
                self.failed_tests += suite_results["failed"]
                self.skipped_tests += suite_results["skipped"]
                
                print(f"✅ {suite_name} completed: {suite_results['passed']}/{suite_results['total']} passed")
                
            except Exception as e:
                print(f"❌ {suite_name} failed: {str(e)}")
                self.failed_tests += 1
        
        self.end_time = time.time()
        self.print_summary()
    
    def run_unit_tests(self, verbose=False):
        """Run unit tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add unit test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixService))
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixModels))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_integration_tests(self, verbose=False):
        """Run integration tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add integration test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixIntegration))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_api_tests(self, verbose=False):
        """Run API tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add API test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixRouter))
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixAPIIntegration))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_config_tests(self, verbose=False):
        """Run configuration tests."""
        print("🔧 Testing Matrix Test Configuration...")
        
        # Test configuration loading
        try:
            config = MatrixTestConfig()
            fixtures = MatrixTestFixtures()
            utils = MatrixTestUtils()
            
            # Test configuration values
            assert config.TEST_USER_ID is not None
            assert len(config.SLOT_VALUES) == 15
            assert len(config.SLOT_NAMES) == 15
            assert len(config.RANK_MAPPING) == 15
            assert len(config.DISTRIBUTION_PERCENTAGES) == 5
            
            # Test fixture creation
            mock_user = fixtures.create_mock_user()
            mock_tree = fixtures.create_mock_matrix_tree()
            mock_node = fixtures.create_mock_matrix_node()
            mock_activation = fixtures.create_mock_matrix_activation()
            
            assert mock_user is not None
            assert mock_tree is not None
            assert mock_node is not None
            assert mock_activation is not None
            
            # Test utility functions
            earnings = utils.calculate_expected_earnings(1, 10)
            upgrade_cost = utils.calculate_expected_upgrade_cost(1, 2)
            rank = utils.get_expected_rank(5)
            
            assert earnings > 0
            assert upgrade_cost > 0
            assert rank is not None
            
            print("✅ Configuration tests passed")
            
            return {
                "total": 1,
                "passed": 1,
                "failed": 0,
                "skipped": 0
            }
            
        except Exception as e:
            print(f"❌ Configuration tests failed: {str(e)}")
            return {
                "total": 1,
                "passed": 0,
                "failed": 1,
                "skipped": 0
            }
    
    def print_summary(self):
        """Print test summary."""
        duration = self.end_time - self.start_time
        
        print("\n" + "=" * 60)
        print("📊 MATRIX PROGRAM TEST SUMMARY")
        print("=" * 60)
        
        print(f"⏱️  Total Duration: {duration:.2f} seconds")
        print(f"📈 Total Tests: {self.total_tests}")
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"⏭️  Skipped: {self.skipped_tests}")
        
        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
            print(f"📊 Success Rate: {success_rate:.1f}%")
        
        print("\n📋 Test Suite Results:")
        for suite_name, results in self.test_results.items():
            print(f"   {suite_name}: {results['passed']}/{results['total']} passed")
        
        if self.failed_tests == 0:
            print("\n🎉 All tests passed! Matrix Program is ready for deployment.")
        else:
            print(f"\n⚠️  {self.failed_tests} tests failed. Please review and fix issues.")
        
        print("=" * 60)
    
    def run_specific_tests(self, test_type, verbose=False):
        """Run specific type of tests."""
        if test_type == "unit":
            self.run_unit_tests(verbose)
        elif test_type == "integration":
            self.run_integration_tests(verbose)
        elif test_type == "api":
            self.run_api_tests(verbose)
        elif test_type == "config":
            self.run_config_tests(verbose)
        else:
            print(f"❌ Unknown test type: {test_type}")
            return False
        
        return True


def main():
    """Main function for test runner."""
    parser = argparse.ArgumentParser(description="Matrix Program Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--api", action="store_true", help="Run only API tests")
    parser.add_argument("--config", action="store_true", help="Run only configuration tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Run with verbose output")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    
    args = parser.parse_args()
    
    runner = MatrixTestRunner()
    
    if args.unit:
        runner.run_specific_tests("unit", args.verbose)
    elif args.integration:
        runner.run_specific_tests("integration", args.verbose)
    elif args.api:
        runner.run_specific_tests("api", args.verbose)
    elif args.config:
        runner.run_specific_tests("config", args.verbose)
    else:
        runner.run_all_tests(args.verbose)
    
    if args.coverage:
        print("\n📊 Coverage report would be generated here (requires coverage.py)")


if __name__ == "__main__":
    main()
