"""
Base Worker Class for All Agents
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from fiml.core.logging import get_logger
from fiml.core.models import Asset

logger = get_logger(__name__)


class BaseWorker(ABC):
    """
    Base class for all specialized workers

    Workers are Ray actors that can execute in parallel
    """

    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.logger = get_logger(f"{self.__class__.__name__}:{worker_id}")
        self.logger.info("Worker initialized")

    @abstractmethod
    async def process(self, asset: Asset, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process analysis for an asset

        Args:
            asset: Asset to analyze
            params: Optional parameters

        Returns:
            Analysis results
        """
        pass

    async def health_check(self) -> Dict[str, Any]:
        """Worker health check"""
        return {
            "worker_id": self.worker_id,
            "status": "healthy",
            "class": self.__class__.__name__,
        }
