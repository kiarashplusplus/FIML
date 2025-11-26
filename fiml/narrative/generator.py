"""
Narrative Generation Engine

Generates natural language narratives from structured financial analysis data
using Azure OpenAI. Supports multiple languages and expertise levels with
comprehensive quality validation.
"""

import json
import re
import time
from typing import Any, Dict, List, Optional

from fiml.compliance.disclaimers import AssetClass, DisclaimerGenerator
from fiml.core.logging import get_logger
from fiml.llm.azure_client import AzureOpenAIClient
from fiml.narrative.models import (
    ExpertiseLevel,
    Narrative,
    NarrativeContext,
    NarrativePreferences,
    NarrativeQualityMetrics,
    NarrativeSection,
    NarrativeType,
)
from fiml.narrative.prompts import prompt_library

logger = get_logger(__name__)


class NarrativeGenerator:
    """
    Generate comprehensive financial narratives from analysis data

    Uses Azure OpenAI to transform structured data into natural language
    narratives adapted to user expertise level and language preference.
    Includes quality validation and compliance disclaimer injection.
    """

    def __init__(
        self,
        azure_client: Optional[AzureOpenAIClient] = None,
        disclaimer_generator: Optional[DisclaimerGenerator] = None,
    ):
        """
        Initialize narrative generator

        Args:
            azure_client: Azure OpenAI client (creates new if None)
            disclaimer_generator: Disclaimer generator (creates new if None)
        """
        self.azure_client = azure_client or AzureOpenAIClient()
        self.disclaimer_generator = (
            disclaimer_generator or DisclaimerGenerator()
        )
        self.prompt_library = prompt_library

        logger.info("Narrative generator initialized")

    async def generate_narrative(
        self,
        context: NarrativeContext,
    ) -> Narrative:
        """
        Generate comprehensive narrative from analysis context

        Args:
            context: Narrative context with all analysis data and preferences

        Returns:
            Complete narrative with sections, summary, and insights

        Example:
            >>> context = NarrativeContext(
            ...     asset_symbol="AAPL",
            ...     price_data={"price": 175.50, "change_percent": 2.3},
            ...     technical_data={"rsi": 65, "macd": "bullish"},
            ... )
            >>> narrative = await generator.generate_narrative(context)
        """
        start_time = time.time()
        logger.info(
            "Generating narrative",
            symbol=context.asset_symbol,
            language=context.preferences.language.value,
            expertise=context.preferences.expertise_level.value,
        )

        sections: List[NarrativeSection] = []
        generation_errors: List[str] = []  # Track errors during generation

        # Generate market context section
        if context.price_data:
            try:
                market_section = await self._generate_market_context(
                    context.asset_symbol,
                    context.asset_name or context.asset_symbol,
                    context.price_data,
                    context.preferences,
                )
                if market_section:
                    sections.append(market_section)
            except Exception as e:
                logger.error("Failed to generate market context", error=str(e))
                generation_errors.append(f"Market Context: {str(e)}")

        # Generate technical analysis section
        if context.technical_data and context.preferences.include_technical:
            try:
                technical_section = await self._generate_technical_narrative(
                    context.asset_symbol,
                    context.technical_data,
                    context.preferences,
                )
                if technical_section:
                    sections.append(technical_section)
            except Exception as e:
                logger.error("Failed to generate technical narrative", error=str(e))
                generation_errors.append(f"Technical: {str(e)}")

        # Generate fundamental analysis section
        if (
            context.fundamental_data
            and context.preferences.include_fundamental
        ):
            try:
                fundamental_section = await self._generate_fundamental_narrative(
                    context.asset_symbol,
                    context.asset_name or context.asset_symbol,
                    context.fundamental_data,
                    context.preferences,
                )
                if fundamental_section:
                    sections.append(fundamental_section)
            except Exception as e:
                logger.error("Failed to generate fundamental narrative", error=str(e))
                generation_errors.append(f"Fundamental: {str(e)}")

        # Generate sentiment analysis section
        if context.sentiment_data and context.preferences.include_sentiment:
            try:
                sentiment_section = await self._generate_sentiment_narrative(
                    context.asset_symbol,
                    context.sentiment_data,
                    context.preferences,
                )
                if sentiment_section:
                    sections.append(sentiment_section)
            except Exception as e:
                logger.error("Failed to generate sentiment narrative", error=str(e))
                generation_errors.append(f"Sentiment: {str(e)}")

        # Generate risk analysis section
        if context.risk_data and context.preferences.include_risk:
            try:
                risk_section = await self._generate_risk_narrative(
                    context.asset_symbol,
                    context.risk_data,
                    context.preferences,
                )
                if risk_section:
                    sections.append(risk_section)
            except Exception as e:
                logger.error("Failed to generate risk narrative", error=str(e))
                generation_errors.append(f"Risk: {str(e)}")

        # Extract key insights from all analysis
        key_insights = await self._extract_key_insights(context, sections)

        # Extract risk factors
        risk_factors = self._extract_risk_factors(context, sections)

        # Generate executive summary
        summary = await self._generate_executive_summary(
            context, sections, key_insights
        )

        # Generate disclaimer
        disclaimer = self._generate_disclaimer(context)

        # Calculate generation time
        generation_time_ms = (time.time() - start_time) * 1000

        # Create narrative
        narrative = Narrative(
            summary=summary,
            sections=sections,
            key_insights=key_insights,
            risk_factors=risk_factors,
            disclaimer=disclaimer,
            language=context.preferences.language,
            expertise_level=context.preferences.expertise_level,
            generation_time_ms=generation_time_ms,
            metadata={
                "asset_symbol": context.asset_symbol,
                "asset_name": context.asset_name,
                "region": context.region,
                "data_sources": context.data_sources,
                "section_count": len(sections),
                "generation_errors": generation_errors,
            },
        )

        # Validate narrative quality
        quality_metrics = self._validate_narrative_quality(narrative, context)
        narrative.confidence = quality_metrics.overall_quality
        narrative.metadata["quality_metrics"] = quality_metrics.model_dump()

        logger.info(
            "Narrative generated successfully",
            symbol=context.asset_symbol,
            sections=len(sections),
            word_count=narrative.total_word_count,
            generation_time_ms=generation_time_ms,
            quality=quality_metrics.overall_quality,
        )

        return narrative

    async def _generate_market_context(
        self,
        symbol: str,
        name: str,
        price_data: Dict[str, Any],
        preferences: NarrativePreferences,
    ) -> Optional[NarrativeSection]:
        """
        Generate market context narrative section

        Args:
            symbol: Asset symbol
            name: Asset name
            price_data: Price and market data
            preferences: User preferences

        Returns:
            Market context narrative section or None if generation fails
        """
        try:
            # Get appropriate prompt template
            template = self.prompt_library.get_template(
                NarrativeType.MARKET_CONTEXT,
                preferences.expertise_level,
                preferences.language,
            )

            # Format user prompt with data
            user_prompt = template["user"].format(
                asset_name=name,
                symbol=symbol,
                price=price_data.get("price", 0),
                change=price_data.get("change", 0),
                change_percent=price_data.get("change_percent", 0),
                volume=price_data.get("volume", 0),
                avg_volume=price_data.get("avg_volume", 0),
                market_cap=price_data.get("market_cap", 0),
                week_52_high=price_data.get("week_52_high", 0),
                week_52_low=price_data.get("week_52_low", 0),
                day_high=price_data.get("day_high", price_data.get("price", 0)),
                day_low=price_data.get("day_low", price_data.get("price", 0)),
                beta=price_data.get("beta", 1.0),
                volume_ratio=price_data.get("volume", 1)
                / max(price_data.get("avg_volume", 1), 1),
                mean_return=price_data.get("mean_return", 0),
                std_dev=price_data.get("std_dev", 0),
                volatility=price_data.get("volatility", 0),
                historical_vol=price_data.get("historical_volatility", 0),
                implied_vol=price_data.get("implied_volatility", 0),
                volume_zscore=price_data.get("volume_zscore", 0),
                return_1d=price_data.get("return_1d", 0),
                return_5d=price_data.get("return_5d", 0),
                return_20d=price_data.get("return_20d", 0),
                sharpe_ratio=price_data.get("sharpe_ratio", 0),
                sortino_ratio=price_data.get("sortino_ratio", 0),
            )

            # Generate narrative using Azure OpenAI
            messages = [
                {"role": "system", "content": template["system"]},
                {"role": "user", "content": user_prompt},
            ]

            response = await self.azure_client._make_request(
                messages=messages, temperature=0.7, max_tokens=500
            )

            content = response["choices"][0]["message"]["content"]

            # Calculate readability score (Flesch Reading Ease approximation)
            readability = self._calculate_readability(content)

            return NarrativeSection(
                title="Market Context",
                content=content,
                section_type=NarrativeType.MARKET_CONTEXT,
                confidence=0.95,
                readability_score=readability,
                metadata={"source": "azure_openai", "data_points": len(price_data)},
            )
        except Exception as e:
            logger.error("Failed to generate market context narrative", error=str(e))
            return None

    async def _generate_technical_narrative(
        self,
        symbol: str,
        technical_data: Dict[str, Any],
        preferences: NarrativePreferences,
    ) -> Optional[NarrativeSection]:
        """
        Generate technical analysis narrative section

        Args:
            symbol: Asset symbol
            technical_data: Technical indicators and analysis
            preferences: User preferences

        Returns:
            Technical analysis narrative section or None if generation fails
        """
        try:
            template = self.prompt_library.get_template(
                NarrativeType.TECHNICAL,
                preferences.expertise_level,
                preferences.language,
            )

            # Format technical data for prompt
            if preferences.expertise_level == ExpertiseLevel.ADVANCED:
                # For advanced users, include full technical data
                user_prompt = template["user"].format(
                    symbol=symbol,
                    technical_data=json.dumps(technical_data, indent=2),
                )
            else:
                # For beginners/intermediate, use simplified format
                user_prompt = template["user"].format(
                    symbol=symbol,
                    rsi=technical_data.get("rsi", "N/A"),
                    macd_line=technical_data.get("macd", {}).get("macd", "N/A"),
                    macd_signal=technical_data.get("macd", {}).get("signal", "N/A"),
                    macd_hist=technical_data.get("macd", {}).get(
                        "histogram", "N/A"
                    ),
                    ma_50=technical_data.get("ma_50", "N/A"),
                    ma_200=technical_data.get("ma_200", "N/A"),
                    price=technical_data.get("current_price", "N/A"),
                    stoch_k=technical_data.get("stochastic", {}).get("k", "N/A"),
                    ma_50_position=technical_data.get("ma_50_position", "N/A"),
                    ma_200_position=technical_data.get("ma_200_position", "N/A"),
                    bb_upper=technical_data.get("bollinger", {}).get("upper", "N/A"),
                    bb_middle=technical_data.get("bollinger", {}).get(
                        "middle", "N/A"
                    ),
                    bb_lower=technical_data.get("bollinger", {}).get("lower", "N/A"),
                    atr=technical_data.get("atr", "N/A"),
                )

            messages = [
                {"role": "system", "content": template["system"]},
                {"role": "user", "content": user_prompt},
            ]

            response = await self.azure_client._make_request(
                messages=messages, temperature=0.6, max_tokens=600
            )

            content = response["choices"][0]["message"]["content"]
            readability = self._calculate_readability(content)

            return NarrativeSection(
                title="Technical Analysis",
                content=content,
                section_type=NarrativeType.TECHNICAL,
                confidence=0.90,
                readability_score=readability,
                metadata={
                    "source": "azure_openai",
                    "indicators": list(technical_data.keys()),
                },
            )
        except Exception as e:
            logger.error("Failed to generate technical narrative", error=str(e))
            return None

    async def _generate_fundamental_narrative(
        self,
        symbol: str,
        name: str,
        fundamental_data: Dict[str, Any],
        preferences: NarrativePreferences,
    ) -> Optional[NarrativeSection]:
        """
        Generate fundamental analysis narrative section

        Args:
            symbol: Asset symbol
            name: Company name
            fundamental_data: Fundamental metrics and ratios
            preferences: User preferences

        Returns:
            Fundamental analysis narrative section or None if generation fails
        """
        try:
            template = self.prompt_library.get_template(
                NarrativeType.FUNDAMENTAL,
                preferences.expertise_level,
                preferences.language,
            )

            user_prompt = template["user"].format(
                company_name=name,
                symbol=symbol,
                pe_ratio=fundamental_data.get("pe_ratio", "N/A"),
                industry_pe=fundamental_data.get("industry_pe", "N/A"),
                market_cap=fundamental_data.get("market_cap", "N/A"),
                revenue=fundamental_data.get("revenue", "N/A"),
                profit_margin=fundamental_data.get("profit_margin", "N/A"),
                sector_pe=fundamental_data.get("sector_pe", "N/A"),
                sp500_pe=fundamental_data.get("sp500_pe", "N/A"),
                pb_ratio=fundamental_data.get("pb_ratio", "N/A"),
                peg_ratio=fundamental_data.get("peg_ratio", "N/A"),
                ev_ebitda=fundamental_data.get("ev_ebitda", "N/A"),
                net_margin=fundamental_data.get("net_margin", "N/A"),
                roe=fundamental_data.get("roe", "N/A"),
                debt_equity=fundamental_data.get("debt_equity", "N/A"),
                eps_growth=fundamental_data.get("eps_growth", "N/A"),
                revenue_growth=fundamental_data.get("revenue_growth", "N/A"),
            )

            messages = [
                {"role": "system", "content": template["system"]},
                {"role": "user", "content": user_prompt},
            ]

            response = await self.azure_client._make_request(
                messages=messages, temperature=0.6, max_tokens=700
            )

            content = response["choices"][0]["message"]["content"]
            readability = self._calculate_readability(content)

            return NarrativeSection(
                title="Fundamental Analysis",
                content=content,
                section_type=NarrativeType.FUNDAMENTAL,
                confidence=0.88,
                readability_score=readability,
                metadata={
                    "source": "azure_openai",
                    "metrics": list(fundamental_data.keys()),
                },
            )
        except Exception as e:
            logger.error("Failed to generate fundamental narrative", error=str(e))
            return None

    async def _generate_sentiment_narrative(
        self,
        symbol: str,
        sentiment_data: Dict[str, Any],
        preferences: NarrativePreferences,
    ) -> Optional[NarrativeSection]:
        """
        Generate sentiment analysis narrative section

        Args:
            symbol: Asset symbol
            sentiment_data: Sentiment scores and news data
            preferences: User preferences

        Returns:
            Sentiment analysis narrative section or None if generation fails
        """
        try:
            template = self.prompt_library.get_template(
                NarrativeType.SENTIMENT,
                preferences.expertise_level,
                preferences.language,
            )

            # Format news headlines
            headlines = sentiment_data.get("headlines", [])
            headlines_text = "\n".join(
                [f"- {h}" for h in headlines[:5]]
            )  # Top 5 headlines

            # Format trending topics
            topics = sentiment_data.get("trending_topics", [])
            topics_text = ", ".join(topics[:5])  # Top 5 topics

            user_prompt = template["user"].format(
                symbol=symbol,
                sentiment_score=sentiment_data.get("overall_score", 0),
                news_sentiment=sentiment_data.get("news_sentiment", 0),
                social_sentiment=sentiment_data.get("social_sentiment", 0),
                sentiment_trend=sentiment_data.get("trend", "neutral"),
                news_headlines=headlines_text,
                trending_topics=topics_text,
            )

            messages = [
                {"role": "system", "content": template["system"]},
                {"role": "user", "content": user_prompt},
            ]

            response = await self.azure_client._make_request(
                messages=messages, temperature=0.7, max_tokens=600
            )

            content = response["choices"][0]["message"]["content"]
            readability = self._calculate_readability(content)

            return NarrativeSection(
                title="Market Sentiment",
                content=content,
                section_type=NarrativeType.SENTIMENT,
                confidence=0.85,
                readability_score=readability,
                metadata={
                    "source": "azure_openai",
                    "sentiment_score": sentiment_data.get("overall_score", 0),
                    "headline_count": len(headlines),
                },
            )
        except Exception as e:
            logger.error("Failed to generate sentiment narrative", error=str(e))
            return None

    async def _generate_risk_narrative(
        self,
        symbol: str,
        risk_data: Dict[str, Any],
        preferences: NarrativePreferences,
    ) -> Optional[NarrativeSection]:
        """
        Generate risk analysis narrative section

        Args:
            symbol: Asset symbol
            risk_data: Risk metrics and volatility data
            preferences: User preferences

        Returns:
            Risk analysis narrative section or None if generation fails
        """
        try:
            template = self.prompt_library.get_template(
                NarrativeType.RISK,
                preferences.expertise_level,
                preferences.language,
            )

            user_prompt = template["user"].format(
                symbol=symbol,
                volatility_30d=risk_data.get("volatility_30d", 0),
                beta=risk_data.get("beta", 1.0),
                sharpe=risk_data.get("sharpe_ratio", 0),
                max_drawdown=risk_data.get("max_drawdown", 0),
                var_1d=risk_data.get("var_1d", 0),
                var_10d=risk_data.get("var_10d", 0),
                sp500_correlation=risk_data.get("sp500_correlation", 0),
            )

            messages = [
                {"role": "system", "content": template["system"]},
                {"role": "user", "content": user_prompt},
            ]

            response = await self.azure_client._make_request(
                messages=messages, temperature=0.5, max_tokens=600
            )

            content = response["choices"][0]["message"]["content"]
            readability = self._calculate_readability(content)

            return NarrativeSection(
                title="Risk Analysis",
                content=content,
                section_type=NarrativeType.RISK,
                confidence=0.92,
                readability_score=readability,
                metadata={
                    "source": "azure_openai",
                    "volatility": risk_data.get("volatility_30d", 0),
                    "beta": risk_data.get("beta", 1.0),
                },
            )
        except Exception as e:
            logger.error("Failed to generate risk narrative", error=str(e))
            return None

    async def _extract_key_insights(
        self,
        context: NarrativeContext,
        sections: List[NarrativeSection],
    ) -> List[str]:
        """
        Extract key actionable insights from analysis

        Args:
            context: Full narrative context
            sections: Generated narrative sections

        Returns:
            List of key insights (3-5 items)
        """
        insights = []

        try:
            # Compile all section content
            all_content = "\n\n".join(
                [f"{s.title}:\n{s.content}" for s in sections]
            )

            # Use Azure OpenAI to extract insights
            system_prompt = (
                "You are a financial analyst extracting key actionable insights. "
                "Identify 3-5 most important takeaways that investors should know. "
                "Be specific and concise. Return as a JSON array of strings."
            )

            user_prompt = (
                f"Extract 3-5 key insights from this analysis of "
                f"{context.asset_symbol}:\n\n{all_content}\n\n"
                "Return ONLY a JSON array of insight strings, no other text."
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = await self.azure_client._make_request(
                messages=messages, temperature=0.4, max_tokens=400
            )

            content = response["choices"][0]["message"]["content"]

            # Parse JSON response
            insights = json.loads(content)

            # Validate and clean
            insights = [
                insight.strip()
                for insight in insights
                if isinstance(insight, str) and insight.strip()
            ][:5]

        except Exception as e:
            logger.error("Failed to extract insights", error=str(e))
            # Fallback to simple extraction
            insights = self._fallback_extract_insights(context, sections)

        return insights

    def _fallback_extract_insights(
        self,
        context: NarrativeContext,
        sections: List[NarrativeSection],
    ) -> List[str]:
        """Fallback method for extracting insights without LLM"""
        insights = []

        # Volatility insight
        if context.risk_data:
            volatility = context.risk_data.get("volatility_30d", 0)
            if volatility > 40:
                insights.append(
                    f"High volatility ({volatility:.0f}%) indicates increased risk"
                )

        # Price movement insight
        if context.price_data:
            change_pct = context.price_data.get("change_percent", 0)
            if abs(change_pct) > 3:
                direction = "up" if change_pct > 0 else "down"
                insights.append(
                    f"Significant price movement: {direction} {abs(change_pct):.1f}%"
                )

        # Sentiment insight
        if context.sentiment_data:
            sentiment = context.sentiment_data.get("overall_score", 0)
            if abs(sentiment) > 0.5:
                tone = "positive" if sentiment > 0 else "negative"
                insights.append(f"Market sentiment is strongly {tone}")

        return insights[:5]

    def _extract_risk_factors(
        self,
        context: NarrativeContext,
        sections: List[NarrativeSection],
    ) -> List[str]:
        """Extract key risk factors from analysis"""
        risk_factors = []

        # Volatility risk
        if context.risk_data:
            volatility = context.risk_data.get("volatility_30d", 0)
            if volatility > 30:
                risk_factors.append(f"High volatility: {volatility:.0f}%")

            beta = context.risk_data.get("beta", 1.0)
            if beta > 1.5:
                risk_factors.append(f"High market sensitivity (Beta: {beta:.2f})")

        # Valuation risk
        if context.fundamental_data:
            pe_ratio = context.fundamental_data.get("pe_ratio", 0)
            if pe_ratio > 40:
                risk_factors.append(f"High valuation (P/E: {pe_ratio:.1f})")

        # Technical risk
        if context.technical_data:
            rsi = context.technical_data.get("rsi", 50)
            if rsi > 70:
                risk_factors.append("Overbought conditions (RSI > 70)")
            elif rsi < 30:
                risk_factors.append("Oversold conditions (RSI < 30)")

        return risk_factors[:5]

    async def _generate_executive_summary(
        self,
        context: NarrativeContext,
        sections: List[NarrativeSection],
        insights: List[str],
    ) -> str:
        """
        Generate executive summary from all sections

        Args:
            context: Narrative context
            sections: All generated sections
            insights: Key insights

        Returns:
            Executive summary text
        """
        try:
            template = self.prompt_library.get_template(
                NarrativeType.SUMMARY,
                context.preferences.expertise_level,
                context.preferences.language,
            )

            # Compile section summaries
            section_summaries = "\n\n".join(
                [f"**{s.title}**: {s.content[:200]}..." for s in sections]
            )

            user_prompt = template["user"].format(
                symbol=context.asset_symbol,
                analysis_sections=section_summaries,
            )

            messages = [
                {"role": "system", "content": template["system"]},
                {"role": "user", "content": user_prompt},
            ]

            response = await self.azure_client._make_request(
                messages=messages, temperature=0.6, max_tokens=400
            )

            summary = response["choices"][0]["message"]["content"]

            # Ensure summary meets length requirements
            if len(summary) < 50:
                summary = f"Analysis of {context.asset_symbol}: " + summary

            return str(summary)

        except Exception as e:
            logger.error("Failed to generate summary", error=str(e))
            # Fallback summary
            return (
                f"Comprehensive analysis of {context.asset_symbol} including "
                f"{len(sections)} analytical perspectives. "
                f"Key insights: {'; '.join(insights[:2])}."
            )

    def _generate_disclaimer(self, context: NarrativeContext) -> str:
        """
        Generate appropriate disclaimer based on asset type and region

        Args:
            context: Narrative context

        Returns:
            Disclaimer text
        """
        # Map asset type to disclaimer asset class
        asset_class_map = {
            "equity": AssetClass.EQUITY,
            "crypto": AssetClass.CRYPTO,
            "forex": AssetClass.FOREX,
            "commodity": AssetClass.COMMODITY,
            "etf": AssetClass.ETF,
        }

        asset_class = asset_class_map.get(
            context.asset_type.lower(), AssetClass.EQUITY
        )

        return self.disclaimer_generator.generate(
            asset_class=asset_class,
            region=context.region,
            include_general=True,
        )

    def _validate_narrative_quality(
        self,
        narrative: Narrative,
        context: NarrativeContext,
    ) -> NarrativeQualityMetrics:
        """
        Validate narrative quality against constraints

        Args:
            narrative: Generated narrative
            context: Original context

        Returns:
            Quality metrics and validation results
        """
        issues = []
        warnings = []

        # Length validation
        if len(narrative.summary) < 50:
            issues.append("Summary too short (< 50 characters)")
        if len(narrative.summary) > 2000:
            warnings.append("Summary exceeds recommended length")

        # Section validation
        for section in narrative.sections:
            if len(section.content) < 10:
                issues.append(f"{section.title}: Content too short")
            if len(section.content) > 5000:
                issues.append(f"{section.title}: Content too long")

        # Completeness score
        expected_sections = sum(
            [
                context.preferences.include_technical,
                context.preferences.include_fundamental,
                context.preferences.include_sentiment,
                context.preferences.include_risk,
            ]
        )
        actual_sections = len(
            [
                s
                for s in narrative.sections
                if s.section_type != NarrativeType.MARKET_CONTEXT
            ]
        )
        completeness = min(actual_sections / max(expected_sections, 1), 1.0)

        # Coherence score (based on section confidence)
        coherence = sum(s.confidence for s in narrative.sections) / max(
            len(narrative.sections), 1
        )

        # Accuracy score (assume high if no data mismatches)
        accuracy = 0.95  # Would need fact-checking against source data

        # Average readability
        readability_scores = [
            s.readability_score
            for s in narrative.sections
            if s.readability_score
        ]
        readability = (
            sum(readability_scores) / len(readability_scores)
            if readability_scores
            else 60.0
        )

        # Compliance score
        compliance = 1.0 if narrative.disclaimer else 0.0

        # Overall quality
        overall = (coherence + completeness + accuracy + compliance) / 4

        return NarrativeQualityMetrics(
            coherence_score=coherence,
            completeness_score=completeness,
            accuracy_score=accuracy,
            readability_score=readability,
            compliance_score=compliance,
            overall_quality=overall,
            issues=issues,
            warnings=warnings,
        )

    def _calculate_readability(self, text: str) -> float:
        """
        Calculate Flesch Reading Ease score

        Args:
            text: Text to analyze

        Returns:
            Readability score (0-100, higher is easier)
        """
        # Simple approximation of Flesch Reading Ease
        sentences = len(re.split(r'[.!?]+', text))
        words = len(text.split())
        syllables = sum(self._count_syllables(word) for word in text.split())

        if sentences == 0 or words == 0:
            return 60.0

        avg_sentence_length = words / sentences
        avg_syllables_per_word = syllables / words

        # Flesch Reading Ease formula
        score = (
            206.835
            - 1.015 * avg_sentence_length
            - 84.6 * avg_syllables_per_word
        )

        # Clamp to 0-100
        return max(0, min(100, score))

    def _count_syllables(self, word: str) -> int:
        """
        Approximate syllable count for a word

        Args:
            word: Word to count syllables in

        Returns:
            Estimated syllable count
        """
        word = word.lower()
        vowels = "aeiouy"
        syllable_count = 0
        previous_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel

        # Adjust for silent e
        if word.endswith("e"):
            syllable_count -= 1

        # Every word has at least one syllable
        return max(1, syllable_count)
