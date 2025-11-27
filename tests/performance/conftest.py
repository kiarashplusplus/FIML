"""
Pytest configuration for performance tests
"""

import contextlib
import os

import pytest


@pytest.fixture(scope="session")
def base_url():
    """Base URL for API tests"""
    return os.getenv("FIML_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def performance_threshold():
    """Performance threshold for regression detection (10%)"""
    return float(os.getenv("PERF_THRESHOLD", "0.10"))


@pytest.fixture(scope="function")
async def clean_cache():
    """Clean cache before and after test"""
    from fiml.cache.manager import cache_manager

    await cache_manager.initialize()

    # Clean before test
    with contextlib.suppress(Exception):
        await cache_manager.l1.clear()

    yield

    # Clean after test
    with contextlib.suppress(Exception):
        await cache_manager.l1.clear()

    await cache_manager.shutdown()


@pytest.fixture(scope="function")
def perf_metrics():
    """Access to performance metrics"""
    from fiml.monitoring.performance import performance_monitor

    return performance_monitor


# Configure pytest markers
def pytest_configure(config):
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    config.addinivalue_line("markers", "slow: mark test as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "load: mark test as a load test")
