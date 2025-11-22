"""
Agent Orchestrator - Coordinates multi-agent analysis
"""

import asyncio
from typing import Any, Dict, List, Optional

import ray

from fiml.agents.workers import (
    CorrelationWorker,
    FundamentalsWorker,
    MacroWorker,
    NewsWorker,
    RiskWorker,
    SentimentWorker,
    TechnicalWorker,
)
from fiml.core.config import settings
from fiml.core.logging import get_logger
from fiml.core.models import Asset

logger = get_logger(__name__)


class AgentOrchestrator:
    """
    Orchestrates multiple specialized agents for comprehensive analysis
    
    Architecture:
    - Parallel execution of independent agents
    - Result aggregation and synthesis
    - Load balancing across workers
    - Fault tolerance with fallbacks
    """

    def __init__(self):
        self.initialized = False
        self.workers: Dict[str, List] = {}

    async def initialize(self) -> None:
        """Initialize Ray and spawn workers"""
        if self.initialized:
            logger.warning("Orchestrator already initialized")
            return

        try:
            # Initialize Ray with timeout to prevent blocking
            if not ray.is_initialized():
                # Run Ray initialization in a thread pool with timeout
                loop = asyncio.get_event_loop()
                init_task = loop.run_in_executor(
                    None,
                    lambda: ray.init(
                        address=settings.ray_address,
                        ignore_reinit_error=True,
                        _node_ip_address="0.0.0.0",
                    )
                )
                
                # Wait up to 10 seconds for Ray to connect
                await asyncio.wait_for(init_task, timeout=10.0)

            # Spawn worker pool
            self.workers = {
                "fundamentals": [FundamentalsWorker.remote(f"fund_{i}") for i in range(2)],
                "technical": [TechnicalWorker.remote(f"tech_{i}") for i in range(2)],
                "macro": [MacroWorker.remote(f"macro_{i}") for i in range(1)],
                "sentiment": [SentimentWorker.remote(f"sent_{i}") for i in range(2)],
                "correlation": [CorrelationWorker.remote(f"corr_{i}") for i in range(1)],
                "risk": [RiskWorker.remote(f"risk_{i}") for i in range(1)],
                "news": [NewsWorker.remote(f"news_{i}") for i in range(2)],
            }

            self.initialized = True
            logger.info(
                "Agent orchestrator initialized",
                total_workers=sum(len(w) for w in self.workers.values()),
            )

        except asyncio.TimeoutError:
            logger.warning("Ray initialization timed out - orchestrator will run in degraded mode")
            self.initialized = False
        except Exception as e:
            logger.warning(f"Failed to initialize orchestrator (non-critical): {e}")
            self.initialized = False

    async def shutdown(self) -> None:
        """Shutdown Ray and workers"""
        if ray.is_initialized():
            ray.shutdown()
        self.initialized = False
        logger.info("Agent orchestrator shutdown")

    async def analyze_asset(
        self,
        asset: Asset,
        agents: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run comprehensive analysis on an asset
        
        Args:
            asset: Asset to analyze
            agents: Specific agents to run (None = all)
            
        Returns:
            Aggregated analysis results
        """
        if not self.initialized:
            raise RuntimeError("Orchestrator not initialized")

        # Default to all agents
        if agents is None:
            agents = list(self.workers.keys())

        logger.info(f"Starting multi-agent analysis", asset=asset.symbol, agents=agents)

        # Schedule tasks
        tasks = []
        for agent_type in agents:
            if agent_type in self.workers:
                # Use first available worker (could implement load balancing)
                worker = self.workers[agent_type][0]
                task = worker.process.remote(asset)
                tasks.append((agent_type, task))

        # Execute in parallel
        results = {}
        for agent_type, task in tasks:
            try:
                result = await task
                results[agent_type] = result
            except Exception as e:
                logger.error(f"Agent failed: {e}", agent=agent_type, asset=asset.symbol)
                results[agent_type] = {"error": str(e)}

        # Aggregate scores
        aggregate = self._aggregate_results(results)

        logger.info(
            f"Multi-agent analysis complete",
            asset=asset.symbol,
            agents_completed=len(results),
            overall_score=aggregate.get("overall_score"),
        )

        return {
            "asset": asset.symbol,
            "analyses": results,
            "aggregate": aggregate,
        }

    async def analyze_multiple(
        self,
        assets: List[Asset],
        agents: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Analyze multiple assets in parallel"""
        tasks = [self.analyze_asset(asset, agents) for asset in assets]
        return await asyncio.gather(*tasks)

    def _aggregate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate results from multiple agents
        
        Returns overall score and recommendations
        """
        scores = []
        for agent_type, result in results.items():
            if isinstance(result, dict) and "score" in result:
                scores.append(result["score"])

        overall_score = sum(scores) / len(scores) if scores else 0

        # Determine recommendation based on score
        if overall_score >= 7.5:
            recommendation = "strong_buy"
        elif overall_score >= 6.5:
            recommendation = "buy"
        elif overall_score >= 5.5:
            recommendation = "hold"
        elif overall_score >= 4.5:
            recommendation = "sell"
        else:
            recommendation = "strong_sell"

        return {
            "overall_score": round(overall_score, 2),
            "recommendation": recommendation,
            "agent_count": len(results),
            "scores": scores,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all workers"""
        if not self.initialized:
            return {"status": "not_initialized"}

        health = {}
        for agent_type, workers in self.workers.items():
            worker_health = []
            for worker in workers:
                try:
                    result = await worker.health_check.remote()
                    worker_health.append(result)
                except Exception as e:
                    worker_health.append({"error": str(e)})

            health[agent_type] = worker_health

        return {
            "status": "healthy" if self.initialized else "degraded",
            "workers": health,
        }


# Global orchestrator instance
agent_orchestrator = AgentOrchestrator()
