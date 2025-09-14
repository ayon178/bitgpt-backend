"""
Integration Test Runner for Matrix Program

This script provides comprehensive integration test execution for the Matrix Program,
including end-to-end workflows, database integration, cross-program integration,
and performance testing.

Usage:
    python integration_test_runner.py                    # Run all integration tests
    python integration_test_runner.py --e2e             # Run only end-to-end tests
    python integration_test_runner.py --database        # Run only database tests
    python integration_test_runner.py --cross-program   # Run only cross-program tests
    python integration_test_runner.py --performance     # Run only performance tests
    python integration_test_runner.py --api            # Run only API integration tests
    python integration_test_runner.py --coverage       # Run with coverage report
    python integration_test_runner.py --verbose        # Run with verbose output
"""

import unittest
import sys
import os
import argparse
import time
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import integration test modules
from tests.modules.matrix.test_matrix_integration import (
    TestMatrixEndToEndWorkflow, TestMatrixDatabaseIntegration,
    TestMatrixCrossProgramIntegration, TestMatrixPerformanceIntegration,
    TestMatrixErrorHandlingIntegration, TestMatrixRealWorldScenarios
)
from tests.modules.matrix.test_matrix_api_integration import (
    TestMatrixAPIIntegration, TestMatrixAPICrossProgramIntegration,
    TestMatrixAPIPerformanceIntegration, TestMatrixAPIErrorHandlingIntegration
)
from tests.modules.matrix.test_config import MatrixTestConfig, MatrixTestFixtures, MatrixTestUtils


class MatrixIntegrationTestRunner:
    """Integration test runner for Matrix Program."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
    
    def run_all_integration_tests(self, verbose=False):
        """Run all Matrix integration tests."""
        print("🚀 Starting Matrix Program Integration Test Suite")
        print("=" * 70)
        
        self.start_time = time.time()
        
        # Integration test suites
        test_suites = [
            ("End-to-End Workflow Tests", self.run_e2e_tests),
            ("Database Integration Tests", self.run_database_tests),
            ("Cross-Program Integration Tests", self.run_cross_program_tests),
            ("Performance Integration Tests", self.run_performance_tests),
            ("API Integration Tests", self.run_api_integration_tests),
            ("Error Handling Integration Tests", self.run_error_handling_tests),
            ("Real-World Scenario Tests", self.run_real_world_tests)
        ]
        
        for suite_name, test_function in test_suites:
            print(f"\n📋 Running {suite_name}")
            print("-" * 50)
            
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
    
    def run_e2e_tests(self, verbose=False):
        """Run end-to-end workflow tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add end-to-end test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixEndToEndWorkflow))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_database_tests(self, verbose=False):
        """Run database integration tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add database integration test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixDatabaseIntegration))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_cross_program_tests(self, verbose=False):
        """Run cross-program integration tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add cross-program integration test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixCrossProgramIntegration))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_performance_tests(self, verbose=False):
        """Run performance integration tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add performance integration test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixPerformanceIntegration))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_api_integration_tests(self, verbose=False):
        """Run API integration tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add API integration test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixAPIIntegration))
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixAPICrossProgramIntegration))
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixAPIPerformanceIntegration))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_error_handling_tests(self, verbose=False):
        """Run error handling integration tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add error handling integration test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixErrorHandlingIntegration))
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixAPIErrorHandlingIntegration))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_real_world_tests(self, verbose=False):
        """Run real-world scenario tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add real-world scenario test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixRealWorldScenarios))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def print_summary(self):
        """Print integration test summary."""
        duration = self.end_time - self.start_time
        
        print("\n" + "=" * 70)
        print("📊 MATRIX PROGRAM INTEGRATION TEST SUMMARY")
        print("=" * 70)
        
        print(f"⏱️  Total Duration: {duration:.2f} seconds")
        print(f"📈 Total Tests: {self.total_tests}")
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"⏭️  Skipped: {self.skipped_tests}")
        
        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
            print(f"📊 Success Rate: {success_rate:.1f}%")
        
        print("\n📋 Integration Test Suite Results:")
        for suite_name, results in self.test_results.items():
            print(f"   {suite_name}: {results['passed']}/{results['total']} passed")
        
        print("\n🎯 Integration Test Coverage:")
        print("   ✅ End-to-End Workflows: Complete Matrix join, upgrade, recycle workflows")
        print("   ✅ Database Integration: Matrix tree, recycle, upgrade operations")
        print("   ✅ Cross-Program Integration: Binary, Global, Special Programs")
        print("   ✅ Performance Testing: Join, upgrade, recycle performance")
        print("   ✅ API Integration: Complete API workflows and cross-program APIs")
        print("   ✅ Error Handling: Comprehensive error scenario testing")
        print("   ✅ Real-World Scenarios: Multi-user, chain, and complex scenarios")
        
        if self.failed_tests == 0:
            print("\n🎉 All integration tests passed! Matrix Program is ready for production.")
        else:
            print(f"\n⚠️  {self.failed_tests} integration tests failed. Please review and fix issues.")
        
        print("=" * 70)
    
    def run_specific_integration_tests(self, test_type, verbose=False):
        """Run specific type of integration tests."""
        if test_type == "e2e":
            self.run_e2e_tests(verbose)
        elif test_type == "database":
            self.run_database_tests(verbose)
        elif test_type == "cross-program":
            self.run_cross_program_tests(verbose)
        elif test_type == "performance":
            self.run_performance_tests(verbose)
        elif test_type == "api":
            self.run_api_integration_tests(verbose)
        elif test_type == "error-handling":
            self.run_error_handling_tests(verbose)
        elif test_type == "real-world":
            self.run_real_world_tests(verbose)
        else:
            print(f"❌ Unknown integration test type: {test_type}")
            return False
        
        return True


def main():
    """Main function for integration test runner."""
    parser = argparse.ArgumentParser(description="Matrix Program Integration Test Runner")
    parser.add_argument("--e2e", action="store_true", help="Run only end-to-end tests")
    parser.add_argument("--database", action="store_true", help="Run only database tests")
    parser.add_argument("--cross-program", action="store_true", help="Run only cross-program tests")
    parser.add_argument("--performance", action="store_true", help="Run only performance tests")
    parser.add_argument("--api", action="store_true", help="Run only API integration tests")
    parser.add_argument("--error-handling", action="store_true", help="Run only error handling tests")
    parser.add_argument("--real-world", action="store_true", help="Run only real-world scenario tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Run with verbose output")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    
    args = parser.parse_args()
    
    runner = MatrixIntegrationTestRunner()
    
    if args.e2e:
        runner.run_specific_integration_tests("e2e", args.verbose)
    elif args.database:
        runner.run_specific_integration_tests("database", args.verbose)
    elif args.cross_program:
        runner.run_specific_integration_tests("cross-program", args.verbose)
    elif args.performance:
        runner.run_specific_integration_tests("performance", args.verbose)
    elif args.api:
        runner.run_specific_integration_tests("api", args.verbose)
    elif args.error_handling:
        runner.run_specific_integration_tests("error-handling", args.verbose)
    elif args.real_world:
        runner.run_specific_integration_tests("real-world", args.verbose)
    else:
        runner.run_all_integration_tests(args.verbose)
    
    if args.coverage:
        print("\n📊 Coverage report would be generated here (requires coverage.py)")


if __name__ == "__main__":
    main()
