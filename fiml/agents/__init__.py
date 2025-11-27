"""
Multi-Agent Orchestration System
"""

from fiml.agents.orchestrator import AgentOrchestrator
from fiml.agents.workers import (
                                 CorrelationWorker,
                                 FundamentalsWorker,
                                 MacroWorker,
                                 NewsWorker,
                                 OptionsWorker,
                                 RiskWorker,
                                 SentimentWorker,
                                 TechnicalWorker,
)
from fiml.agents.workflows import (
                                 CryptoSentimentAnalysisResult,
                                 CryptoSentimentAnalysisWorkflow,
                                 DeepEquityAnalysisResult,
                                 DeepEquityAnalysisWorkflow,
                                 WorkflowResult,
                                 WorkflowStatus,
                                 crypto_sentiment_analysis,
                                 deep_equity_analysis,
)

__all__ = [
    "AgentOrchestrator",
    "FundamentalsWorker",
    "TechnicalWorker",
    "MacroWorker",
    "SentimentWorker",
    "CorrelationWorker",
    "RiskWorker",
    "NewsWorker",
    "OptionsWorker",
    # Workflows
    "DeepEquityAnalysisWorkflow",
    "DeepEquityAnalysisResult",
    "CryptoSentimentAnalysisWorkflow",
    "CryptoSentimentAnalysisResult",
    "WorkflowResult",
    "WorkflowStatus",
    "deep_equity_analysis",
    "crypto_sentiment_analysis",
]
