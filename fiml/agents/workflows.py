"""
Agent Workflows - High-level orchestrated workflows for complex analysis

This module provides pre-built, production-ready agent workflows that combine
multiple specialized agents, data providers, and LLM capabilities to deliver
comprehensive financial analysis.

Workflows:
- DeepEquityAnalysis: Multi-dimensional equity analysis
- CryptoSentimentAnalysis: Cryptocurrency sentiment and market analysis
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, cast

from pydantic import BaseModel, Field

from fiml.agents.orchestrator import AgentOrchestrator
from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.llm.azure_client import AzureOpenAIClient
from fiml.providers.registry import provider_registry

logger = get_logger(__name__)


class WorkflowStatus(str, Enum):
    """Workflow execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some steps succeeded, some failed


class WorkflowResult(BaseModel):
    """Base workflow result"""

    workflow_name: str
    status: WorkflowStatus
    asset: Asset
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[float] = None
    steps_completed: int = 0
    steps_total: int = 0
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class DeepEquityAnalysisResult(WorkflowResult):
    """Deep equity analysis workflow result"""

    # Quick snapshot data
    snapshot: Optional[Dict[str, Any]] = None

    # Fundamental analysis
    fundamentals: Optional[Dict[str, Any]] = None

    # Technical analysis
    technicals: Optional[Dict[str, Any]] = None

    # Sentiment analysis
    sentiment: Optional[Dict[str, Any]] = None

    # Risk analysis
    risk: Optional[Dict[str, Any]] = None

    # LLM-generated narrative
    narrative: Optional[str] = None

    # Overall recommendation
    recommendation: Optional[Dict[str, Any]] = None

    # Data quality and confidence
    data_quality_score: float = 0.0
    confidence_score: float = 0.0


class CryptoSentimentAnalysisResult(WorkflowResult):
    """Crypto sentiment analysis workflow result"""

    # Price snapshot
    price_data: Optional[Dict[str, Any]] = None

    # Sentiment from news and social media
    sentiment: Optional[Dict[str, Any]] = None

    # Technical indicators
    technicals: Optional[Dict[str, Any]] = None

    # Correlation with BTC/ETH
    correlations: Optional[Dict[str, Any]] = None

    # LLM-generated market narrative
    narrative: Optional[str] = None

    # Trading signals
    signals: Optional[Dict[str, Any]] = None

    # Confidence metrics
    confidence_score: float = 0.0


class DeepEquityAnalysisWorkflow:
    """
    Deep Equity Analysis Workflow

    Performs comprehensive multi-dimensional analysis of an equity:
    1. Quick snapshot (price, basic metrics)
    2. Fundamental analysis (financials, ratios, valuation)
    3. Technical analysis (indicators, patterns, trends)
    4. Sentiment analysis (news, social media, analyst opinions)
    5. Risk assessment (volatility, correlations, exposures)
    6. LLM narrative generation (synthesis and insights)
    7. Recommendation generation (actionable insights)

    Example:
        workflow = DeepEquityAnalysisWorkflow()
        result = await workflow.execute("AAPL")
        print(result.narrative)
        print(result.recommendation)
    """

    def __init__(
        self,
        orchestrator: Optional[AgentOrchestrator] = None,
        llm_client: Optional[AzureOpenAIClient] = None,
    ):
        """
        Initialize deep equity analysis workflow

        Args:
            orchestrator: Agent orchestrator (creates new if not provided)
            llm_client: Azure OpenAI client (creates new if not provided)
        """
        self.orchestrator = orchestrator or AgentOrchestrator()
        self.llm_client = llm_client or AzureOpenAIClient()
        self.logger = get_logger(__name__)

    async def execute(
        self,
        symbol: str,
        market: Market = Market.US,
        include_narrative: bool = True,
        include_recommendation: bool = True,
    ) -> DeepEquityAnalysisResult:
        """
        Execute deep equity analysis workflow

        Args:
            symbol: Stock symbol (e.g., "AAPL", "MSFT")
            market: Market identifier
            include_narrative: Whether to generate LLM narrative
            include_recommendation: Whether to generate recommendation

        Returns:
            Comprehensive analysis result
        """
        start_time = datetime.now(timezone.utc)
        asset = Asset(symbol=symbol, asset_type=AssetType.EQUITY, market=market)

        result = DeepEquityAnalysisResult(
            workflow_name="deep_equity_analysis",
            status=WorkflowStatus.RUNNING,
            asset=asset,
            started_at=start_time,
            steps_total=7,
        )

        try:
            # Initialize orchestrator if needed
            if not self.orchestrator.initialized:
                await self.orchestrator.initialize()

            # Step 1: Quick Snapshot (price data)
            self.logger.info("Step 1/7: Fetching quick snapshot", symbol=symbol)
            result.snapshot = await self._fetch_snapshot(asset)
            result.steps_completed = 1

            # Step 2: Fundamental Analysis
            self.logger.info("Step 2/7: Analyzing fundamentals", symbol=symbol)
            result.fundamentals = await self._analyze_fundamentals(asset)
            result.steps_completed = 2

            # Step 3: Technical Analysis
            self.logger.info("Step 3/7: Analyzing technicals", symbol=symbol)
            result.technicals = await self._analyze_technicals(asset)
            result.steps_completed = 3

            # Step 4: Sentiment Analysis
            self.logger.info("Step 4/7: Analyzing sentiment", symbol=symbol)
            result.sentiment = await self._analyze_sentiment(asset)
            result.steps_completed = 4

            # Step 5: Risk Assessment
            self.logger.info("Step 5/7: Assessing risk", symbol=symbol)
            result.risk = await self._assess_risk(asset)
            result.steps_completed = 5

            # Step 6: LLM Narrative Generation
            if include_narrative:
                self.logger.info("Step 6/7: Generating narrative", symbol=symbol)
                result.narrative = await self._generate_narrative(
                    asset,
                    result.snapshot,
                    result.fundamentals,
                    result.technicals,
                    result.sentiment,
                    result.risk,
                )
                result.steps_completed = 6
            else:
                result.steps_completed = 6

            # Step 7: Generate Recommendation
            if include_recommendation:
                self.logger.info("Step 7/7: Generating recommendation", symbol=symbol)
                result.recommendation = await self._generate_recommendation(
                    result.fundamentals, result.technicals, result.sentiment, result.risk
                )
                result.steps_completed = 7
            else:
                result.steps_completed = 7

            # Calculate quality and confidence scores
            result.data_quality_score = self._calculate_data_quality(result)
            result.confidence_score = self._calculate_confidence(result)

            # Mark as completed
            result.status = WorkflowStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc)
            result.execution_time_ms = (result.completed_at - start_time).total_seconds() * 1000

            self.logger.info(
                "Deep equity analysis completed",
                symbol=symbol,
                execution_time_ms=result.execution_time_ms,
                confidence=result.confidence_score,
            )

            return result

        except Exception as e:
            self.logger.error("Workflow execution failed", symbol=symbol, error=str(e))
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.now(timezone.utc)
            result.execution_time_ms = (result.completed_at - start_time).total_seconds() * 1000
            return result

    async def _fetch_snapshot(self, asset: Asset) -> Dict[str, Any]:
        """Fetch quick price snapshot"""
        try:
            providers = await provider_registry.get_providers_for_asset(asset, DataType.PRICE)

            for provider in providers:
                try:
                    response = await provider.fetch_price(asset)
                    if response.is_valid and response.data:
                        return {
                            "price": response.data.get("price", 0),
                            "change": response.data.get("change", 0),
                            "change_percent": response.data.get("change_percent", 0),
                            "volume": response.data.get("volume", 0),
                            "market_cap": response.data.get("market_cap", 0),
                            "provider": provider.name,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                except Exception as e:
                    self.logger.warning(
                        "Provider failed for snapshot", provider=provider.name, error=str(e)
                    )
                    continue

            # Fallback to mock data
            return {
                "price": 0,
                "change": 0,
                "change_percent": 0,
                "volume": 0,
                "market_cap": 0,
                "provider": "mock",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.logger.error("Snapshot fetch failed", error=str(e))
            raise

    async def _analyze_fundamentals(self, asset: Asset) -> Dict[str, Any]:
        """Analyze fundamental data using orchestrator"""
        try:
            # Use orchestrator to run fundamentals worker
            analysis = await self.orchestrator.analyze_asset(asset, agents=["fundamentals"])
            return cast(Dict[str, Any], analysis.get("fundamentals", {}))
        except Exception as e:
            self.logger.warning("Fundamentals analysis failed", error=str(e))
            return {"error": str(e), "available": False}

    async def _analyze_technicals(self, asset: Asset) -> Dict[str, Any]:
        """Analyze technical indicators using orchestrator"""
        try:
            analysis = await self.orchestrator.analyze_asset(asset, agents=["technical"])
            return cast(Dict[str, Any], analysis.get("technical", {}))
        except Exception as e:
            self.logger.warning("Technical analysis failed", error=str(e))
            return {"error": str(e), "available": False}

    async def _analyze_sentiment(self, asset: Asset) -> Dict[str, Any]:
        """Analyze sentiment using orchestrator"""
        try:
            analysis = await self.orchestrator.analyze_asset(asset, agents=["sentiment", "news"])
            return {
                "sentiment": analysis.get("sentiment", {}),
                "news": analysis.get("news", {}),
            }
        except Exception as e:
            self.logger.warning("Sentiment analysis failed", error=str(e))
            return {"error": str(e), "available": False}

    async def _assess_risk(self, asset: Asset) -> Dict[str, Any]:
        """Assess risk using orchestrator"""
        try:
            analysis = await self.orchestrator.analyze_asset(asset, agents=["risk", "correlation"])
            return {
                "risk": analysis.get("risk", {}),
                "correlation": analysis.get("correlation", {}),
            }
        except Exception as e:
            self.logger.warning("Risk assessment failed", error=str(e))
            return {"error": str(e), "available": False}

    async def _generate_narrative(
        self,
        asset: Asset,
        snapshot: Optional[Dict],
        fundamentals: Optional[Dict],
        technicals: Optional[Dict],
        sentiment: Optional[Dict],
        risk: Optional[Dict],
    ) -> str:
        """Generate LLM-powered narrative synthesis"""
        try:
            # Build comprehensive context for LLM
            context = self._build_narrative_context(
                asset, snapshot, fundamentals, technicals, sentiment, risk
            )

            # Create prompt for narrative generation
            prompt = f"""You are a senior financial analyst. Provide a comprehensive analysis of {asset.symbol}.

PRICE DATA:
{context.get('snapshot_text', 'Not available')}

FUNDAMENTALS:
{context.get('fundamentals_text', 'Not available')}

TECHNICALS:
{context.get('technicals_text', 'Not available')}

SENTIMENT:
{context.get('sentiment_text', 'Not available')}

RISK:
{context.get('risk_text', 'Not available')}

Please provide:
1. Executive Summary (2-3 sentences)
2. Key Strengths and Opportunities
3. Key Risks and Concerns
4. Investment Thesis
5. Market Outlook

Be specific, data-driven, and actionable."""

            # Generate narrative using LLM
            # Build context with all required information
            # Spread context first, then override with explicit values
            narrative_context = {
                **context,
                "asset": asset.symbol,
                "asset_type": asset.asset_type.value,
                "prompt": prompt,
            }
            narrative = await self.llm_client.generate_narrative(
                context=narrative_context,
            )

            return narrative

        except Exception as e:
            self.logger.error("Narrative generation failed", error=str(e))
            return f"Narrative generation unavailable: {str(e)}"

    def _build_narrative_context(
        self,
        asset: Asset,
        snapshot: Optional[Dict],
        fundamentals: Optional[Dict],
        technicals: Optional[Dict],
        sentiment: Optional[Dict],
        risk: Optional[Dict],
    ) -> Dict[str, str]:
        """Build textual context for narrative generation"""
        context = {}

        # Snapshot context
        if snapshot and snapshot.get("price"):
            context[
                "snapshot_text"
            ] = f"""
Price: ${snapshot['price']:.2f}
Change: {snapshot.get('change_percent', 0):+.2f}%
Volume: {snapshot.get('volume', 0):,.0f}
Market Cap: ${snapshot.get('market_cap', 0):,.0f}
"""

        # Fundamentals context
        if fundamentals and not fundamentals.get("error"):
            metrics = fundamentals.get("metrics", {})
            context[
                "fundamentals_text"
            ] = f"""
P/E Ratio: {metrics.get('pe_ratio', 'N/A')}
EPS: ${metrics.get('eps', 'N/A')}
ROE: {metrics.get('roe', 'N/A')}
Debt/Equity: {metrics.get('debt_to_equity', 'N/A')}
Valuation: {fundamentals.get('valuation', {}).get('assessment', 'N/A')}
"""

        # Technicals context
        if technicals and not technicals.get("error"):
            indicators = technicals.get("indicators", {})
            context[
                "technicals_text"
            ] = f"""
RSI: {indicators.get('rsi', 'N/A')}
MACD: {indicators.get('macd', 'N/A')}
Trend: {technicals.get('trend', {}).get('direction', 'N/A')}
Support: ${technicals.get('levels', {}).get('support', 'N/A')}
Resistance: ${technicals.get('levels', {}).get('resistance', 'N/A')}
"""

        # Sentiment context
        if sentiment and not sentiment.get("error"):
            sent_data = sentiment.get("sentiment", {})
            context[
                "sentiment_text"
            ] = f"""
Overall Sentiment: {sent_data.get('score', 'N/A')}
News Sentiment: {sent_data.get('news_sentiment', 'N/A')}
Social Sentiment: {sent_data.get('social_sentiment', 'N/A')}
"""

        # Risk context
        if risk and not risk.get("error"):
            risk_data = risk.get("risk", {})
            context[
                "risk_text"
            ] = f"""
Risk Level: {risk_data.get('level', 'N/A')}
Volatility: {risk_data.get('volatility', 'N/A')}
Beta: {risk_data.get('beta', 'N/A')}
Max Drawdown: {risk_data.get('max_drawdown', 'N/A')}
"""

        return context

    async def _generate_recommendation(
        self,
        fundamentals: Optional[Dict],
        technicals: Optional[Dict],
        sentiment: Optional[Dict],
        risk: Optional[Dict],
    ) -> Dict[str, Any]:
        """Generate actionable recommendation based on analysis"""
        try:
            # Simple rule-based recommendation logic
            # (In production, this could use ML or more sophisticated logic)

            scores = {
                "fundamental_score": 0,
                "technical_score": 0,
                "sentiment_score": 0,
                "risk_score": 0,
            }

            # Fundamental score
            if fundamentals and not fundamentals.get("error"):
                valuation = fundamentals.get("valuation", {})
                if valuation.get("assessment") == "undervalued":
                    scores["fundamental_score"] = 75
                elif valuation.get("assessment") == "fairly_valued":
                    scores["fundamental_score"] = 50
                else:
                    scores["fundamental_score"] = 25

            # Technical score
            if technicals and not technicals.get("error"):
                trend = technicals.get("trend", {})
                if trend.get("direction") == "bullish":
                    scores["technical_score"] = 75
                elif trend.get("direction") == "neutral":
                    scores["technical_score"] = 50
                else:
                    scores["technical_score"] = 25

            # Sentiment score
            if sentiment and not sentiment.get("error"):
                sent_data = sentiment.get("sentiment", {})
                score = sent_data.get("score", 50)
                scores["sentiment_score"] = score

            # Risk score (inverse - lower risk = higher score)
            if risk and not risk.get("error"):
                risk_data = risk.get("risk", {})
                level = risk_data.get("level", "medium")
                if level == "low":
                    scores["risk_score"] = 75
                elif level == "medium":
                    scores["risk_score"] = 50
                else:
                    scores["risk_score"] = 25

            # Calculate overall score
            overall_score = sum(scores.values()) / len(scores)

            # Generate recommendation
            if overall_score >= 65:
                action = "BUY"
                confidence = "HIGH"
            elif overall_score >= 45:
                action = "HOLD"
                confidence = "MEDIUM"
            else:
                action = "SELL"
                confidence = "LOW"

            return {
                "action": action,
                "confidence": confidence,
                "overall_score": round(overall_score, 2),
                "component_scores": scores,
                "reasoning": "Based on comprehensive analysis across fundamental, technical, sentiment, and risk dimensions.",
            }

        except Exception as e:
            self.logger.error("Recommendation generation failed", error=str(e))
            return {
                "action": "HOLD",
                "confidence": "LOW",
                "overall_score": 50,
                "error": str(e),
            }

    def _calculate_data_quality(self, result: DeepEquityAnalysisResult) -> float:
        """Calculate data quality score based on available data"""
        available_sections = 0
        total_sections = 5  # snapshot, fundamentals, technicals, sentiment, risk

        if result.snapshot and result.snapshot.get("price"):
            available_sections += 1
        if result.fundamentals and not result.fundamentals.get("error"):
            available_sections += 1
        if result.technicals and not result.technicals.get("error"):
            available_sections += 1
        if result.sentiment and not result.sentiment.get("error"):
            available_sections += 1
        if result.risk and not result.risk.get("error"):
            available_sections += 1

        return (available_sections / total_sections) * 100

    def _calculate_confidence(self, result: DeepEquityAnalysisResult) -> float:
        """Calculate overall confidence score"""
        # Confidence based on data quality and recommendation confidence
        data_quality = self._calculate_data_quality(result)

        recommendation_confidence = 50  # Default
        if result.recommendation:
            conf = result.recommendation.get("confidence", "MEDIUM")
            if conf == "HIGH":
                recommendation_confidence = 80
            elif conf == "MEDIUM":
                recommendation_confidence = 60
            else:
                recommendation_confidence = 40

        return (data_quality * 0.6 + recommendation_confidence * 0.4) / 100


class CryptoSentimentAnalysisWorkflow:
    """
    Crypto Sentiment Analysis Workflow

    Specialized workflow for cryptocurrency sentiment and market analysis:
    1. Price data snapshot
    2. Technical indicators (RSI, MACD, volume analysis)
    3. Sentiment analysis (news, social media, on-chain metrics)
    4. Correlation analysis with major cryptos (BTC, ETH)
    5. LLM-powered market narrative
    6. Trading signal generation

    Example:
        workflow = CryptoSentimentAnalysisWorkflow()
        result = await workflow.execute("ETH", exchange="binance")
        print(result.narrative)
        print(result.signals)
    """

    def __init__(
        self,
        orchestrator: Optional[AgentOrchestrator] = None,
        llm_client: Optional[AzureOpenAIClient] = None,
    ):
        """Initialize crypto sentiment analysis workflow"""
        self.orchestrator = orchestrator or AgentOrchestrator()
        self.llm_client = llm_client or AzureOpenAIClient()
        self.logger = get_logger(__name__)

    async def execute(
        self,
        symbol: str,
        exchange: str = "binance",
        pair: str = "USDT",
        include_narrative: bool = True,
    ) -> CryptoSentimentAnalysisResult:
        """
        Execute crypto sentiment analysis workflow

        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH", "SOL")
            exchange: Exchange name (default: "binance")
            pair: Trading pair (default: "USDT")
            include_narrative: Whether to generate LLM narrative

        Returns:
            Comprehensive crypto sentiment analysis result
        """
        start_time = datetime.now(timezone.utc)
        asset = Asset(
            symbol=symbol,
            asset_type=AssetType.CRYPTO,
            exchange=exchange,
            pair=pair,
        )

        result = CryptoSentimentAnalysisResult(
            workflow_name="crypto_sentiment_analysis",
            status=WorkflowStatus.RUNNING,
            asset=asset,
            started_at=start_time,
            steps_total=6,
        )

        try:
            # Initialize orchestrator if needed
            if not self.orchestrator.initialized:
                await self.orchestrator.initialize()

            # Step 1: Fetch price data
            self.logger.info("Step 1/6: Fetching price data", symbol=symbol)
            result.price_data = await self._fetch_price_data(asset)
            result.steps_completed = 1

            # Step 2: Analyze sentiment
            self.logger.info("Step 2/6: Analyzing sentiment", symbol=symbol)
            result.sentiment = await self._analyze_sentiment(asset)
            result.steps_completed = 2

            # Step 3: Technical analysis
            self.logger.info("Step 3/6: Analyzing technicals", symbol=symbol)
            result.technicals = await self._analyze_technicals(asset)
            result.steps_completed = 3

            # Step 4: Correlation analysis
            self.logger.info("Step 4/6: Analyzing correlations", symbol=symbol)
            result.correlations = await self._analyze_correlations(asset)
            result.steps_completed = 4

            # Step 5: Generate narrative
            if include_narrative:
                self.logger.info("Step 5/6: Generating narrative", symbol=symbol)
                result.narrative = await self._generate_narrative(
                    asset,
                    result.price_data,
                    result.sentiment,
                    result.technicals,
                    result.correlations,
                )
                result.steps_completed = 5
            else:
                result.steps_completed = 5

            # Step 6: Generate trading signals
            self.logger.info("Step 6/6: Generating signals", symbol=symbol)
            result.signals = await self._generate_signals(
                result.sentiment, result.technicals, result.correlations
            )
            result.steps_completed = 6

            # Calculate confidence
            result.confidence_score = self._calculate_confidence(result)

            # Mark as completed
            result.status = WorkflowStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc)
            result.execution_time_ms = (result.completed_at - start_time).total_seconds() * 1000

            self.logger.info(
                "Crypto sentiment analysis completed",
                symbol=symbol,
                execution_time_ms=result.execution_time_ms,
            )

            return result

        except Exception as e:
            self.logger.error("Workflow execution failed", symbol=symbol, error=str(e))
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.now(timezone.utc)
            result.execution_time_ms = (result.completed_at - start_time).total_seconds() * 1000
            return result

    async def _fetch_price_data(self, asset: Asset) -> Dict[str, Any]:
        """Fetch crypto price data"""
        try:
            providers = await provider_registry.get_providers_for_asset(asset, DataType.PRICE)

            for provider in providers:
                try:
                    response = await provider.fetch_price(asset)
                    if response.is_valid and response.data:
                        return response.data
                except Exception as e:
                    self.logger.warning("Provider failed", provider=provider.name, error=str(e))
                    continue

            return {"error": "No price data available"}
        except Exception as e:
            self.logger.error("Price fetch failed", error=str(e))
            return {"error": str(e)}

    async def _analyze_sentiment(self, asset: Asset) -> Dict[str, Any]:
        """Analyze crypto sentiment"""
        try:
            analysis = await self.orchestrator.analyze_asset(asset, agents=["sentiment", "news"])
            return {
                "sentiment": analysis.get("sentiment", {}),
                "news": analysis.get("news", {}),
            }
        except Exception as e:
            self.logger.warning("Sentiment analysis failed", error=str(e))
            return {"error": str(e)}

    async def _analyze_technicals(self, asset: Asset) -> Dict[str, Any]:
        """Analyze technical indicators"""
        try:
            analysis = await self.orchestrator.analyze_asset(asset, agents=["technical"])
            return cast(Dict[str, Any], analysis.get("technical", {}))
        except Exception as e:
            self.logger.warning("Technical analysis failed", error=str(e))
            return {"error": str(e)}

    async def _analyze_correlations(self, asset: Asset) -> Dict[str, Any]:
        """Analyze correlations with BTC and ETH"""
        try:
            analysis = await self.orchestrator.analyze_asset(asset, agents=["correlation"])
            return cast(Dict[str, Any], analysis.get("correlation", {}))
        except Exception as e:
            self.logger.warning("Correlation analysis failed", error=str(e))
            return {"error": str(e)}

    async def _generate_narrative(
        self,
        asset: Asset,
        price_data: Optional[Dict],
        sentiment: Optional[Dict],
        technicals: Optional[Dict],
        correlations: Optional[Dict],
    ) -> str:
        """Generate market narrative"""
        try:
            prompt = f"""You are a cryptocurrency market analyst. Provide insights on {asset.symbol}/{asset.pair}.

PRICE: ${(price_data or {}).get('price', 'N/A')} | Change: {(price_data or {}).get('change_percent', 0):+.2f}%

SENTIMENT: {(sentiment or {}).get('sentiment', {}).get('score', 'N/A')}

TECHNICALS: RSI={(technicals or {}).get('indicators', {}).get('rsi', 'N/A')}

CORRELATIONS: {correlations}

Provide:
1. Market Summary
2. Key Drivers
3. Trading Outlook
4. Risk Factors"""

            # Build context with all required information
            narrative_context = {
                "asset": asset.symbol,
                "pair": asset.pair,
                "prompt": prompt,
                "price": price_data,
                "sentiment": sentiment,
            }
            narrative = await self.llm_client.generate_narrative(
                context=narrative_context,
            )
            return narrative
        except Exception as e:
            self.logger.error("Narrative generation failed", error=str(e))
            return f"Narrative unavailable: {str(e)}"

    async def _generate_signals(
        self,
        sentiment: Optional[Dict],
        technicals: Optional[Dict],
        correlations: Optional[Dict],
    ) -> Dict[str, Any]:
        """Generate trading signals"""
        signals: Dict[str, Any] = {
            "signal": "NEUTRAL",
            "strength": 0,
            "indicators": [],
        }

        strength = 0

        # Sentiment signals
        if sentiment and not sentiment.get("error"):
            score = sentiment.get("sentiment", {}).get("score", 50)
            if score > 65:
                signals["indicators"].append("Bullish sentiment")
                strength += 25
            elif score < 35:
                signals["indicators"].append("Bearish sentiment")
                strength -= 25

        # Technical signals
        if technicals and not technicals.get("error"):
            rsi = technicals.get("indicators", {}).get("rsi", 50)
            if rsi > 70:
                signals["indicators"].append("Overbought (RSI)")
                strength -= 20
            elif rsi < 30:
                signals["indicators"].append("Oversold (RSI)")
                strength += 20

        # Determine signal
        if strength > 30:
            signals["signal"] = "BUY"
        elif strength < -30:
            signals["signal"] = "SELL"

        signals["strength"] = abs(strength)

        return signals

    def _calculate_confidence(self, result: CryptoSentimentAnalysisResult) -> float:
        """Calculate confidence score"""
        available = 0
        total = 4

        if result.price_data and not result.price_data.get("error"):
            available += 1
        if result.sentiment and not result.sentiment.get("error"):
            available += 1
        if result.technicals and not result.technicals.get("error"):
            available += 1
        if result.correlations and not result.correlations.get("error"):
            available += 1

        return available / total


# Convenience functions for easy access
async def deep_equity_analysis(
    symbol: str,
    market: Market = Market.US,
    include_narrative: bool = True,
    include_recommendation: bool = True,
) -> DeepEquityAnalysisResult:
    """
    Convenience function for deep equity analysis

    Args:
        symbol: Stock symbol
        market: Market identifier
        include_narrative: Generate LLM narrative
        include_recommendation: Generate recommendation

    Returns:
        Analysis result
    """
    workflow = DeepEquityAnalysisWorkflow()
    return await workflow.execute(
        symbol=symbol,
        market=market,
        include_narrative=include_narrative,
        include_recommendation=include_recommendation,
    )


async def crypto_sentiment_analysis(
    symbol: str,
    exchange: str = "binance",
    pair: str = "USDT",
    include_narrative: bool = True,
) -> CryptoSentimentAnalysisResult:
    """
    Convenience function for crypto sentiment analysis

    Args:
        symbol: Crypto symbol
        exchange: Exchange name
        pair: Trading pair
        include_narrative: Generate LLM narrative

    Returns:
        Analysis result
    """
    workflow = CryptoSentimentAnalysisWorkflow()
    return await workflow.execute(
        symbol=symbol,
        exchange=exchange,
        pair=pair,
        include_narrative=include_narrative,
    )
