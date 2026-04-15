# run_tests.py
#!/usr/bin/env python3
"""
Comprehensive Test Suite Runner for Smart Energy AI

This script runs all test phases:
- Unit Tests: Battery models, control system, optimization
- Integration Tests: API endpoints, system integration
- E2E Tests: Dashboard workflows (if Playwright available)
- Performance Tests: Load testing, response times

Usage:
    python run_tests.py               # Run all tests
    python run_tests.py --unit        # Run only unit tests
    python run_tests.py --integration # Run only integration tests
    python run_tests.py --e2e          # Run only E2E tests
    python run_tests.py --performance  # Run only performance tests
    python run_tests.py --coverage     # Run with coverage report
"""

import sys
import os
import subprocess
import argparse
import time
from pathlib import Path

def run_command(command, description="", timeout=300):
    """Run a command and return success status"""
    print(f"🔄 {description}")
    print(f"Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout.strip():
                print("Output:", result.stdout.strip()[-500:])  # Last 500 chars
        else:
            print(f"❌ {description} - FAILED")
            if result.stderr:
                print("Error:", result.stderr.strip()[-500:])
                
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def install_dependencies():
    """Install test dependencies"""
    print("📦 Installing Test Dependencies")
    print("=" * 50)
    
    # Core testing dependencies
    deps = [
        "pytest",
        "pytest-asyncio", 
        "pytest-cov",
        "httpx",
        "pandas",
        "numpy"
    ]
    
    success = True
    for dep in deps:
        if not run_command([sys.executable, "-m", "pip", "install", dep], 
                          f"Installing {dep}"):
            success = False
            
    # Optional dependencies
    optional_deps = ["playwright"]
    for dep in optional_deps:
        run_command([sys.executable, "-m", "pip", "install", dep],
                   f"Installing {dep} (optional)")
        
    # Install Playwright browsers if available
    try:
        run_command([sys.executable, "-m", "playwright", "install", "chromium"],
                   "Installing Playwright browsers (optional)")
    except:
        print("⚠️  Playwright browsers not installed (E2E tests will be skipped)")
    
    return success

def run_unit_tests():
    """Run unit tests"""
    print("📋 Running Unit Tests")
    print("=" * 30)
    
    return run_command([
        sys.executable, "-m", "pytest", 
        "tests/unit/", 
        "-v", 
        "--tb=short",
        "-m", "not slow"
    ], "Unit Tests")

def run_integration_tests():
    """Run integration tests"""
    print("🔗 Running Integration Tests") 
    print("=" * 35)
    
    return run_command([
        sys.executable, "-m", "pytest",
        "tests/integration/",
        "-v",
        "--tb=short",
        "--timeout=60"
    ], "Integration Tests")

def run_e2e_tests():
    """Run end-to-end tests"""
    print("🎭 Running E2E Tests")
    print("=" * 25)
    
    return run_command([
        sys.executable, "-m", "pytest",
        "tests/e2e/", 
        "-v",
        "--tb=short",
        "--timeout=120"
    ], "E2E Tests", timeout=600)

def run_performance_tests():
    """Run performance tests"""
    print("⚡ Running Performance Tests")
    print("=" * 35)
    
    return run_command([
        sys.executable, "-m", "pytest",
        "tests/performance/",
        "-v", 
        "--tb=short",
        "--timeout=30"
    ], "Performance Tests")

def run_with_coverage():
    """Run all tests with coverage"""
    print("📊 Running Tests with Coverage")
    print("=" * 40)
    
    # Run tests with coverage
    success = run_command([
        sys.executable, "-m", "pytest",
        "tests/",
        "--cov=energy_ml",
        "--cov-report=html",
        "--cov-report=term",
        "--cov-report=xml",
        "-v"
    ], "Coverage Tests", timeout=600)
    
    if success:
        print("\n📈 Coverage Report Generated:")
        print("  - HTML: htmlcov/index.html")
        print("  - XML: coverage.xml")
        
    return success

def check_test_environment():
    """Check if test environment is properly set up"""
    print("🔍 Checking Test Environment")
    print("=" * 35)
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or python_version.minor < 8:
        print("❌ Python 3.8+ required")
        return False
    else:
        print(f"✅ Python {python_version.major}.{python_version.minor}")
    
    # Check project structure
    required_dirs = ['tests', 'energy_ml']
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ {dir_name}/ directory found")
        else:
            print(f"❌ {dir_name}/ directory missing")
            return False
    
    # Check test files exist
    test_files = [
        'tests/unit/test_battery_physics.py',
        'tests/unit/test_control_system.py', 
        'tests/integration/test_api_integration.py',
        'tests/e2e/test_dashboard_e2e.py'
    ]
    
    missing_files = []
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"✅ {test_file}")
        else:
            print(f"⚠️  {test_file} missing")
            missing_files.append(test_file)
    
    if missing_files:
        print(f"⚠️  Some test files missing, but continuing...")
    
    return True


def _run_selected_suites(args) -> dict[str, bool]:
    if args.unit:
        return {'unit': run_unit_tests()}
    if args.integration:
        return {'integration': run_integration_tests()}
    if args.e2e:
        return {'e2e': run_e2e_tests()}
    if args.performance:
        return {'performance': run_performance_tests()}
    if args.coverage:
        return {'coverage': run_with_coverage()}

    print("🚀 Running Full Test Suite")
    print("=" * 30)
    return {
        'unit': run_unit_tests(),
        'integration': run_integration_tests(),
        'e2e': run_e2e_tests(),
        'performance': run_performance_tests(),
    }


def _print_summary(results: dict[str, bool], duration: float) -> int:
    print("\n" + "=" * 50)
    print("📊 TEST SUITE SUMMARY")
    print("=" * 50)

    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)

    for test_type, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_type.upper():<15} {status}")

    print(f"\nTotal: {passed_tests}/{total_tests} test suites passed")
    print(f"Duration: {duration:.1f} seconds")

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        return 0

    print(f"\n⚠️  {total_tests - passed_tests} test suite(s) failed")
    return 1

def main():
    parser = argparse.ArgumentParser(description="Run Smart Energy AI Test Suite")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--e2e", action="store_true", help="Run E2E tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only") 
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--install-deps", action="store_true", help="Install dependencies first")
    parser.add_argument("--skip-env-check", action="store_true", help="Skip environment check")
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    print("🧪 Smart Energy AI - Comprehensive Test Suite")
    print("=" * 50)
    
    # Install dependencies if requested
    if args.install_deps:
        if not install_dependencies():
            print("❌ Failed to install dependencies")
            return 1
    
    # Check environment
    if not args.skip_env_check:
        if not check_test_environment():
            print("❌ Environment check failed")
            return 1

    results = _run_selected_suites(args)

    end_time = time.time()
    duration = end_time - start_time

    return _print_summary(results, duration)

if __name__ == "__main__":
    sys.exit(main())