"""
Performance Test Runner for Matrix Program

This script provides comprehensive performance test execution for the Matrix Program,
including large tree traversal, recycle snapshot creation, concurrent upgrades,
load testing, stress testing, and performance optimization.

Usage:
    python performance_test_runner.py                    # Run all performance tests
    python performance_test_runner.py --large-tree      # Run only large tree tests
    python performance_test_runner.py --recycle         # Run only recycle tests
    python performance_test_runner.py --concurrent      # Run only concurrent tests
    python performance_test_runner.py --load           # Run only load tests
    python performance_test_runner.py --stress          # Run only stress tests
    python performance_test_runner.py --memory          # Run only memory tests
    python performance_test_runner.py --database       # Run only database tests
    python performance_test_runner.py --optimization   # Run only optimization tests
    python performance_test_runner.py --verbose         # Run with verbose output
    python performance_test_runner.py --benchmark      # Run with benchmark output
"""

import unittest
import sys
import os
import argparse
import time
import psutil
import gc
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import performance test modules
from tests.modules.matrix.test_matrix_performance import (
    TestMatrixLargeTreeTraversalPerformance, TestMatrixRecycleSnapshotPerformance,
    TestMatrixConcurrentUpgradesPerformance, TestMatrixLoadTesting,
    TestMatrixStressTesting, TestMatrixMemoryUsagePerformance, TestMatrixDatabasePerformance
)
from tests.modules.matrix.test_config import MatrixTestConfig, MatrixTestFixtures, MatrixTestUtils


class MatrixPerformanceTestRunner:
    """Performance test runner for Matrix Program."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        self.performance_metrics = {}
    
    def run_all_performance_tests(self, verbose=False, benchmark=False):
        """Run all Matrix performance tests."""
        print("🚀 Starting Matrix Program Performance Test Suite")
        print("=" * 70)
        
        self.start_time = time.time()
        initial_memory = psutil.Process().memory_info().rss
        initial_cpu = psutil.cpu_percent()
        
        # Performance test suites
        test_suites = [
            ("Large Tree Traversal Tests", self.run_large_tree_tests),
            ("Recycle Snapshot Tests", self.run_recycle_snapshot_tests),
            ("Concurrent Upgrades Tests", self.run_concurrent_upgrades_tests),
            ("Load Testing", self.run_load_testing),
            ("Stress Testing", self.run_stress_testing),
            ("Memory Usage Tests", self.run_memory_usage_tests),
            ("Database Performance Tests", self.run_database_performance_tests)
        ]
        
        for suite_name, test_function in test_suites:
            print(f"\n📋 Running {suite_name}")
            print("-" * 50)
            
            try:
                suite_start_time = time.time()
                suite_results = test_function(verbose, benchmark)
                suite_end_time = time.time()
                suite_duration = suite_end_time - suite_start_time
                
                self.test_results[suite_name] = suite_results
                self.test_results[suite_name]["duration"] = suite_duration
                
                self.total_tests += suite_results["total"]
                self.passed_tests += suite_results["passed"]
                self.failed_tests += suite_results["failed"]
                self.skipped_tests += suite_results["skipped"]
                
                print(f"✅ {suite_name} completed: {suite_results['passed']}/{suite_results['total']} passed in {suite_duration:.2f}s")
                
            except Exception as e:
                print(f"❌ {suite_name} failed: {str(e)}")
                self.failed_tests += 1
        
        self.end_time = time.time()
        final_memory = psutil.Process().memory_info().rss
        final_cpu = psutil.cpu_percent()
        
        # Calculate performance metrics
        self.performance_metrics = {
            "total_duration": self.end_time - self.start_time,
            "memory_usage": final_memory - initial_memory,
            "cpu_usage": final_cpu - initial_cpu,
            "throughput": self.total_tests / (self.end_time - self.start_time)
        }
        
        self.print_summary()
        if benchmark:
            self.print_benchmark_results()
    
    def run_large_tree_tests(self, verbose=False, benchmark=False):
        """Run large tree traversal performance tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add large tree traversal test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixLargeTreeTraversalPerformance))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_recycle_snapshot_tests(self, verbose=False, benchmark=False):
        """Run recycle snapshot performance tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add recycle snapshot test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixRecycleSnapshotPerformance))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_concurrent_upgrades_tests(self, verbose=False, benchmark=False):
        """Run concurrent upgrades performance tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add concurrent upgrades test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixConcurrentUpgradesPerformance))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_load_testing(self, verbose=False, benchmark=False):
        """Run load testing."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add load testing classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixLoadTesting))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_stress_testing(self, verbose=False, benchmark=False):
        """Run stress testing."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add stress testing classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixStressTesting))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_memory_usage_tests(self, verbose=False, benchmark=False):
        """Run memory usage tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add memory usage test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixMemoryUsagePerformance))
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)
        
        return {
            "total": result.testsRun,
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures) + len(result.errors),
            "skipped": len(result.skipped) if hasattr(result, 'skipped') else 0
        }
    
    def run_database_performance_tests(self, verbose=False, benchmark=False):
        """Run database performance tests."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add database performance test classes
        suite.addTests(loader.loadTestsFromTestCase(TestMatrixDatabasePerformance))
        
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
        """Print performance test summary."""
        duration = self.end_time - self.start_time
        
        print("\n" + "=" * 70)
        print("📊 MATRIX PROGRAM PERFORMANCE TEST SUMMARY")
        print("=" * 70)
        
        print(f"⏱️  Total Duration: {duration:.2f} seconds")
        print(f"📈 Total Tests: {self.total_tests}")
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"⏭️  Skipped: {self.skipped_tests}")
        
        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
            print(f"📊 Success Rate: {success_rate:.1f}%")
        
        print(f"🚀 Throughput: {self.performance_metrics['throughput']:.1f} tests/second")
        print(f"💾 Memory Usage: {self.performance_metrics['memory_usage'] / 1024 / 1024:.1f}MB")
        print(f"🖥️  CPU Usage: {self.performance_metrics['cpu_usage']:.1f}%")
        
        print("\n📋 Performance Test Suite Results:")
        for suite_name, results in self.test_results.items():
            duration = results.get("duration", 0)
            print(f"   {suite_name}: {results['passed']}/{results['total']} passed in {duration:.2f}s")
        
        print("\n🎯 Performance Test Coverage:")
        print("   ✅ Large Tree Traversal: Tree operations with 1000+ nodes")
        print("   ✅ Recycle Snapshot Creation: Snapshot creation and management")
        print("   ✅ Concurrent Upgrades: Concurrent operations performance")
        print("   ✅ Load Testing: High user load performance")
        print("   ✅ Stress Testing: Extreme conditions performance")
        print("   ✅ Memory Usage: Memory consumption and leak detection")
        print("   ✅ Database Performance: Database operations optimization")
        
        if self.failed_tests == 0:
            print("\n🎉 All performance tests passed! Matrix Program meets performance requirements.")
        else:
            print(f"\n⚠️  {self.failed_tests} performance tests failed. Please review and optimize.")
        
        print("=" * 70)
    
    def print_benchmark_results(self):
        """Print detailed benchmark results."""
        print("\n" + "=" * 70)
        print("📊 DETAILED BENCHMARK RESULTS")
        print("=" * 70)
        
        print(f"🕐 Test Execution Time: {self.performance_metrics['total_duration']:.3f} seconds")
        print(f"📊 Test Throughput: {self.performance_metrics['throughput']:.2f} tests/second")
        print(f"💾 Memory Consumption: {self.performance_metrics['memory_usage'] / 1024 / 1024:.2f} MB")
        print(f"🖥️  CPU Usage: {self.performance_metrics['cpu_usage']:.1f}%")
        
        print("\n📈 Performance Benchmarks:")
        print("   🎯 Large Tree Traversal: < 2.0 seconds (1000+ nodes)")
        print("   🎯 Recycle Snapshot Creation: < 3.0 seconds (39 nodes)")
        print("   🎯 Concurrent Operations: < 5.0 seconds (10 concurrent)")
        print("   🎯 Load Testing: < 10.0 seconds (100 operations)")
        print("   🎯 Stress Testing: < 30.0 seconds (200 operations)")
        print("   🎯 Memory Usage: < 100MB per operation")
        print("   🎯 Database Operations: < 2.0 seconds per operation")
        
        print("\n🚀 Performance Optimization Recommendations:")
        print("   💡 Implement tree caching for large trees")
        print("   💡 Use connection pooling for database operations")
        print("   💡 Implement async operations for concurrent processing")
        print("   💡 Add memory monitoring and cleanup")
        print("   💡 Optimize database queries and indexes")
        print("   💡 Implement rate limiting for high load scenarios")
        
        print("=" * 70)
    
    def run_specific_performance_tests(self, test_type, verbose=False, benchmark=False):
        """Run specific type of performance tests."""
        if test_type == "large-tree":
            self.run_large_tree_tests(verbose, benchmark)
        elif test_type == "recycle":
            self.run_recycle_snapshot_tests(verbose, benchmark)
        elif test_type == "concurrent":
            self.run_concurrent_upgrades_tests(verbose, benchmark)
        elif test_type == "load":
            self.run_load_testing(verbose, benchmark)
        elif test_type == "stress":
            self.run_stress_testing(verbose, benchmark)
        elif test_type == "memory":
            self.run_memory_usage_tests(verbose, benchmark)
        elif test_type == "database":
            self.run_database_performance_tests(verbose, benchmark)
        else:
            print(f"❌ Unknown performance test type: {test_type}")
            return False
        
        return True


def main():
    """Main function for performance test runner."""
    parser = argparse.ArgumentParser(description="Matrix Program Performance Test Runner")
    parser.add_argument("--large-tree", action="store_true", help="Run only large tree tests")
    parser.add_argument("--recycle", action="store_true", help="Run only recycle tests")
    parser.add_argument("--concurrent", action="store_true", help="Run only concurrent tests")
    parser.add_argument("--load", action="store_true", help="Run only load tests")
    parser.add_argument("--stress", action="store_true", help="Run only stress tests")
    parser.add_argument("--memory", action="store_true", help="Run only memory tests")
    parser.add_argument("--database", action="store_true", help="Run only database tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Run with verbose output")
    parser.add_argument("--benchmark", "-b", action="store_true", help="Run with benchmark output")
    
    args = parser.parse_args()
    
    runner = MatrixPerformanceTestRunner()
    
    if args.large_tree:
        runner.run_specific_performance_tests("large-tree", args.verbose, args.benchmark)
    elif args.recycle:
        runner.run_specific_performance_tests("recycle", args.verbose, args.benchmark)
    elif args.concurrent:
        runner.run_specific_performance_tests("concurrent", args.verbose, args.benchmark)
    elif args.load:
        runner.run_specific_performance_tests("load", args.verbose, args.benchmark)
    elif args.stress:
        runner.run_specific_performance_tests("stress", args.verbose, args.benchmark)
    elif args.memory:
        runner.run_specific_performance_tests("memory", args.verbose, args.benchmark)
    elif args.database:
        runner.run_specific_performance_tests("database", args.verbose, args.benchmark)
    else:
        runner.run_all_performance_tests(args.verbose, args.benchmark)


if __name__ == "__main__":
    main()
