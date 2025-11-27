"""
Tests for Agent System
"""

import pytest

from fiml.agents.base import BaseWorker


class TestWorkerAgents:
    """Test worker agents"""

    @pytest.mark.asyncio
    async def test_worker_health_check(self):
        """Test worker health check"""

        # Create a simple worker implementation for testing
        class TestWorker(BaseWorker):
            async def process(self, asset, params=None):
                return {"asset": asset.symbol, "result": "test"}

        worker = TestWorker(worker_id="test-1")

        health = await worker.health_check()
        assert "worker_id" in health
        assert health["status"] == "healthy"
        assert health["worker_id"] == "test-1"
