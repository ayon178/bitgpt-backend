#!/usr/bin/env python3
"""
Master Bonus Programs Test Script
Runs all comprehensive bonus program tests with live progress
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import subprocess
from datetime import datetime

# Configure unbuffered output for live progress
sys.stdout.reconfigure(line_buffering=True)

async def run_test(test_name, test_file):
    """Run a single test file and return results"""
    print(f"\n{'='*60}")
    print(f"🚀 RUNNING {test_name.upper()} TEST")
    print(f"{'='*60}")
    
    try:
        # Run the test file
        result = subprocess.run([
            sys.executable, "-u", test_file
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            print(f"✅ {test_name} test completed successfully!")
            return True, result.stdout
        else:
            print(f"❌ {test_name} test failed!")
            print(f"Error: {result.stderr}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {test_name} test timed out!")
        return False, "Test timed out"
    except Exception as e:
        print(f"💥 {test_name} test crashed!")
        return False, str(e)

async def main():
    print("🎯 MASTER BONUS PROGRAMS TEST SUITE")
    print("=" * 60)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nThis test suite will run comprehensive tests for all bonus programs:")
    print("  🎰 Jackpot Program (4-part distribution)")
    print("  👑 Royal Captain Bonus (24h claims)")
    print("  🏛️ President Reward (24h claims)")
    print("  💼 Leadership Stipend (24h claims)")
    print("  ✨ Spark Bonus & Triple Entry Reward (30-day claims)")
    
    # Test files and their descriptions
    tests = [
        ("Jackpot Program", "test_jackpot_comprehensive_real.py"),
        ("Royal Captain Bonus", "test_royal_captain_comprehensive_real.py"),
        ("President Reward", "test_president_reward_comprehensive_real.py"),
        ("Leadership Stipend", "test_leadership_stipend_comprehensive_real.py"),
        ("Spark Bonus & Triple Entry", "test_spark_triple_entry_comprehensive_real.py")
    ]
    
    # Results tracking
    results = []
    total_tests = len(tests)
    passed_tests = 0
    
    # Run each test
    for test_name, test_file in tests:
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        
        if not os.path.exists(test_path):
            print(f"⚠️  Test file not found: {test_file}")
            results.append((test_name, False, f"Test file not found: {test_file}"))
            continue
        
        success, output = await run_test(test_name, test_path)
        results.append((test_name, success, output))
        
        if success:
            passed_tests += 1
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Final Summary
    print(f"\n{'='*60}")
    print("📊 FINAL TEST RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📈 Tests Run: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {total_tests - passed_tests}")
    print(f"📊 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    print(f"\n📋 Detailed Results:")
    for i, (test_name, success, output) in enumerate(results, 1):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {i}. {test_name}: {status}")
    
    # Overall Status
    if passed_tests == total_tests:
        print(f"\n🎉 ALL TESTS PASSED! All bonus programs are working correctly.")
        print(f"🚀 The system is ready for production deployment.")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Please review the errors above.")
        print(f"🔧 Fix the issues before deploying to production.")
    
    print(f"\n🎯 Bonus Programs Test Suite Completed!")
    print(f"📊 Tested Programs:")
    print(f"  • Jackpot Program: 4-part distribution system")
    print(f"  • Royal Captain Bonus: Progressive tier system")
    print(f"  • President Reward: Team-based reward system")
    print(f"  • Leadership Stipend: Slot-based daily returns")
    print(f"  • Spark Bonus: Matrix slot distribution")
    print(f"  • Triple Entry Reward: 24h join window rewards")

if __name__ == "__main__":
    asyncio.run(main())
