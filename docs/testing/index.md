# Testing Documentation

Comprehensive testing documentation for the FIML project.

## Overview

- [Test Documentation Index](TEST_DOCUMENTATION_INDEX.md) - Complete testing overview
- [Testing Quickstart](TESTING_QUICKSTART.md) - Get started with testing

## Test Reports

- [Test Report](TEST_REPORT.md) - Latest test results
- [Test Status Report](TEST_STATUS_REPORT.md) - Current testing status

## Infrastructure

- [Test Infrastructure Improvement](TEST_INFRASTRUCTURE_IMPROVEMENT.md) - Testing framework enhancements
- [Quickstart Test Fixes](QUICKSTART_TEST_FIXES.md) - Fixes for quickstart tests

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=fiml --cov-report=html

# Run specific test suite
pytest tests/test_arbitrator.py
```

## Test Coverage

The project maintains high test coverage across all components:

- Core functionality: 90%+ coverage
- Integration tests: Full workflow coverage
- Performance benchmarks: Automated regression detection

For detailed test metrics, see the [Test Report](TEST_REPORT.md).
