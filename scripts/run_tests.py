#!/usr/bin/env python3
"""
Test Runner for TheBox
======================

Comprehensive test runner with deterministic seeds and clear reporting.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mvp.env_loader import load_thebox_env


def run_tests(
    test_path: str = "tests/",
    verbose: bool = False,
    coverage: bool = False,
    deterministic: bool = True,
    parallel: bool = False,
    markers: str = "",
    exit_on_failure: bool = True
) -> int:
    """Run tests with specified options"""
    
    # Load environment
    load_thebox_env()
    
    # Set deterministic seeds if requested
    if deterministic:
        os.environ["PYTHONHASHSEED"] = "0"
        os.environ["RANDOM_SEED"] = "42"
    
    # Build pytest arguments
    args = [test_path]
    
    if verbose:
        args.append("-v")
    
    if coverage:
        args.extend(["--cov=mvp", "--cov=plugins", "--cov-report=html", "--cov-report=term"])
    
    if parallel:
        args.extend(["-n", "auto"])
    
    if markers:
        args.extend(["-m", markers])
    
    # Add deterministic options
    if deterministic:
        args.extend(["--tb=short", "--strict-markers"])
    
    # Add test discovery options
    args.extend([
        "--pythonpath=.",
        "--import-mode=importlib",
        "--disable-warnings"
    ])
    
    print(f"Running tests with args: {' '.join(args)}")
    print(f"Test path: {test_path}")
    print(f"Verbose: {verbose}")
    print(f"Coverage: {coverage}")
    print(f"Deterministic: {deterministic}")
    print(f"Parallel: {parallel}")
    print(f"Markers: {markers}")
    print("-" * 60)
    
    start_time = time.time()
    
    try:
        exit_code = pytest.main(args)
        
        duration = time.time() - start_time
        print(f"\nTest run completed in {duration:.2f} seconds")
        
        if exit_code == 0:
            print("✓ All tests passed!")
        else:
            print(f"✗ Tests failed with exit code {exit_code}")
            
        return exit_code
        
    except Exception as e:
        print(f"✗ Test runner failed: {e}")
        return 1


def run_specific_tests():
    """Run specific test suites"""
    
    test_suites = {
        "confidence": "tests/test_confidence_fusion.py",
        "range": "tests/test_range_estimation.py",
        "plugins": "tests/plugins/",
        "integration": "tests/integration/",
        "unit": "tests/unit/",
        "all": "tests/"
    }
    
    print("Available test suites:")
    for name, path in test_suites.items():
        print(f"  {name}: {path}")
    
    return test_suites


def main():
    parser = argparse.ArgumentParser(description="Test Runner for TheBox")
    parser.add_argument("--path", default="tests/", help="Test path to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", "-c", action="store_true", help="Run with coverage")
    parser.add_argument("--deterministic", "-d", action="store_true", default=True, help="Use deterministic seeds")
    parser.add_argument("--parallel", "-p", action="store_true", help="Run tests in parallel")
    parser.add_argument("--markers", "-m", default="", help="Test markers to run")
    parser.add_argument("--exit-on-failure", action="store_true", default=True, help="Exit on first failure")
    parser.add_argument("--list-suites", action="store_true", help="List available test suites")
    parser.add_argument("--suite", choices=["confidence", "range", "plugins", "integration", "unit", "all"], help="Run specific test suite")
    
    args = parser.parse_args()
    
    if args.list_suites:
        run_specific_tests()
        return 0
    
    if args.suite:
        suites = run_specific_tests()
        args.path = suites[args.suite]
    
    return run_tests(
        test_path=args.path,
        verbose=args.verbose,
        coverage=args.coverage,
        deterministic=args.deterministic,
        parallel=args.parallel,
        markers=args.markers,
        exit_on_failure=args.exit_on_failure
    )


if __name__ == "__main__":
    exit(main())
