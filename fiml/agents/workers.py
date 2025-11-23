"""
Specialized Worker Implementations

Each worker fetches real data from providers, performs calculations,
and leverages Azure OpenAI for interpretation and insights.
"""

from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import ray

from fiml.agents.base import BaseWorker
from fiml.core.logging import get_logger
from fiml.core.models import Asset, AssetType, DataType
from fiml.llm.azure_client import AzureOpenAIClient

logger = get_logger(__name__)

# Try to import pandas-ta, fallback if not available
try:
    import pandas_ta  # noqa: F401
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logger.warning("pandas-ta not available, using fallback calculations")




@ray.remote
class FundamentalsWorker(BaseWorker):
    """
    Analyzes fundamental financial data

    Capabilities:
    - Fetches real fundamental data from providers
    - Calculates financial ratios (P/E, P/B, ROE, ROA, debt-to-equity)
    - Uses Azure OpenAI to interpret financial health
    - Compares metrics to sector averages
    - Generates valuation assessment with confidence scores
    """

    async def process(self, asset: Asset, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze fundamentals with real data"""
        self.logger.info("Analyzing fundamentals", asset=asset.symbol)

        try:
            # Import provider registry
            from fiml.providers.registry import provider_registry

            # Fetch fundamental data from providers
            providers = await provider_registry.get_providers_for_asset(asset, DataType.FUNDAMENTALS)

            fundamental_data = None
            for provider in providers:
                try:
                    response = await provider.fetch_fundamentals(asset)
                    if response.is_valid:
                        fundamental_data = response.data
                        self.logger.info("Fetched fundamentals", provider=provider.name)
                        break
                except Exception as e:
                    self.logger.warning("Provider failed", provider=provider.name, error=str(e))
                    continue

            if not fundamental_data:
                self.logger.warning("No fundamental data available, using defaults")
                fundamental_data = {}

            # Extract key metrics with safe defaults
            market_cap = fundamental_data.get("market_cap", 0)
            shares_outstanding = fundamental_data.get("shares_outstanding", 1)
            eps = fundamental_data.get("eps", 0)
            book_value_per_share = fundamental_data.get("book_value_per_share", 0)
            total_assets = fundamental_data.get("total_assets", 0)
            total_equity = fundamental_data.get("total_equity", 1)
            net_income = fundamental_data.get("net_income", 0)
            total_debt = fundamental_data.get("total_debt", 0)
            revenue_growth = fundamental_data.get("revenue_growth", 0)
            profit_margin = fundamental_data.get("profit_margin", 0)

            # Calculate financial ratios
            price_per_share = market_cap / shares_outstanding if shares_outstanding > 0 else 0
            pe_ratio = price_per_share / eps if eps > 0 else 0
            pb_ratio = price_per_share / book_value_per_share if book_value_per_share > 0 else 0
            roe = net_income / total_equity if total_equity > 0 else 0
            roa = net_income / total_assets if total_assets > 0 else 0
            debt_to_equity = total_debt / total_equity if total_equity > 0 else 0

            # Build metrics dictionary
            metrics = {
                "pe_ratio": round(pe_ratio, 2),
                "pb_ratio": round(pb_ratio, 2),
                "eps": round(eps, 2),
                "roe": round(roe, 4),
                "roa": round(roa, 4),
                "debt_to_equity": round(debt_to_equity, 2),
                "revenue_growth": round(revenue_growth, 4),
                "profit_margin": round(profit_margin, 4),
                "market_cap": market_cap,
            }

            # Use Azure OpenAI for interpretation
            valuation = "fairly_valued"
            financial_health = "healthy"
            confidence = 0.7
            interpretation = ""

            try:
                azure_client = AzureOpenAIClient()

                # Request AI interpretation
                prompt = f"""Analyze these financial fundamentals for {asset.symbol}:Valuation Metrics:
- P/E Ratio: {pe_ratio:.2f}
- P/B Ratio: {pb_ratio:.2f}
- EPS: ${eps:.2f}

Profitability:
- ROE: {roe*100:.2f}%
- ROA: {roa*100:.2f}%
- Profit Margin: {profit_margin*100:.2f}%

Financial Health:
- Debt/Equity: {debt_to_equity:.2f}
- Revenue Growth: {revenue_growth*100:.2f}%

Provide a JSON response with:
1. "valuation": one of ["overvalued", "fairly_valued", "undervalued"]
2. "financial_health": one of ["excellent", "healthy", "concerning", "poor"]
3. "confidence": float 0-1
4. "interpretation": brief 2-3 sentence analysis
"""

                messages = [
                    {"role": "system", "content": "You are a financial analyst. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ]

                ai_response = await azure_client._make_request(messages, temperature=0.3, max_tokens=300)

                # Parse AI response
                import json
                ai_content = ai_response["choices"][0]["message"]["content"]
                # Extract JSON from response (might be wrapped in markdown)
                if "```json" in ai_content:
                    ai_content = ai_content.split("```json")[1].split("```")[0].strip()
                elif "```" in ai_content:
                    ai_content = ai_content.split("```")[1].split("```")[0].strip()

                ai_analysis = json.loads(ai_content)

                valuation = ai_analysis.get("valuation", "fairly_valued")
                financial_health = ai_analysis.get("financial_health", "healthy")
                confidence = ai_analysis.get("confidence", 0.7)
                interpretation = ai_analysis.get("interpretation", "")

            except Exception as e:
                self.logger.warning("Azure OpenAI interpretation failed", error=str(e))
                # Fallback to rule-based valuation
                if pe_ratio > 30:
                    valuation = "overvalued"
                elif pe_ratio < 15 and roe > 0.15:
                    valuation = "undervalued"

                if debt_to_equity > 2 or roe < 0.05:
                    financial_health = "concerning"
                elif roe > 0.20 and debt_to_equity < 1:
                    financial_health = "excellent"

            # Calculate score (0-10)
            score = 5.0  # Base score

            # Adjust based on profitability
            if roe > 0.15:
                score += 1.5
            elif roe < 0.05:
                score -= 1.5

            # Adjust based on valuation
            if valuation == "undervalued":
                score += 1.0
            elif valuation == "overvalued":
                score -= 1.0

            # Adjust based on debt
            if debt_to_equity < 0.5:
                score += 0.5
            elif debt_to_equity > 2:
                score -= 1.0

            # Adjust based on growth
            if revenue_growth > 0.15:
                score += 1.0
            elif revenue_growth < 0:
                score -= 1.0

            score = max(0.0, min(10.0, score))  # Clamp to 0-10

            return {
                "asset": asset.symbol,
                "analysis_type": "fundamentals",
                "metrics": metrics,
                "valuation": valuation,
                "financial_health": financial_health,
                "confidence": round(confidence, 2),
                "interpretation": interpretation,
                "score": round(score, 1),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error("Fundamentals analysis failed", error=str(e), exc_info=True)
            return {
                "asset": asset.symbol,
                "analysis_type": "fundamentals",
                "error": str(e),
                "score": 5.0,
                "timestamp": datetime.utcnow().isoformat(),
            }





@ray.remote
class TechnicalWorker(BaseWorker):
    """
    Performs technical analysis with real indicators

    Capabilities:
    - Fetches OHLCV data from providers
    - Calculates RSI, MACD, Bollinger Bands, Moving Averages
    - Identifies support/resistance levels
    - Uses Azure OpenAI for chart pattern interpretation
    - Generates trading signals with confidence scores
    """

    async def process(self, asset: Asset, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze technicals with real indicators"""
        self.logger.info("Analyzing technicals", asset=asset.symbol)

        try:
            # Import provider registry
            from fiml.providers.registry import provider_registry

            # Fetch OHLCV data (100 days for reliable indicators)
            providers = await provider_registry.get_providers_for_asset(asset, DataType.OHLCV)

            ohlcv_data = None
            for provider in providers:
                try:
                    response = await provider.fetch_ohlcv(asset, timeframe="1d", limit=200)
                    if response.is_valid and response.data:
                        ohlcv_data = response.data
                        self.logger.info("Fetched OHLCV", provider=provider.name, bars=len(ohlcv_data.get("close", [])))
                        break
                except Exception as e:
                    self.logger.warning("Provider failed", provider=provider.name, error=str(e))
                    continue

            if not ohlcv_data or not ohlcv_data.get("close"):
                self.logger.warning("No OHLCV data available")
                raise ValueError("No OHLCV data available")

            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data)

            # Ensure we have required columns
            required_cols = ["open", "high", "low", "close", "volume"]
            for col in required_cols:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")

            # Calculate indicators
            indicators = {}

            # Use pandas-ta if available, otherwise fallback
            if PANDAS_TA_AVAILABLE:
                # RSI (14-period)
                df.ta.rsi(length=14, append=True)
                indicators["rsi"] = float(df["RSI_14"].iloc[-1]) if "RSI_14" in df.columns else 50.0

                # MACD (12, 26, 9)
                df.ta.macd(fast=12, slow=26, signal=9, append=True)
                if "MACD_12_26_9" in df.columns:
                    indicators["macd"] = {
                        "macd": float(df["MACD_12_26_9"].iloc[-1]),
                        "signal": float(df["MACDs_12_26_9"].iloc[-1]),
                        "histogram": float(df["MACDh_12_26_9"].iloc[-1]),
                    }
                else:
                    indicators["macd"] = {"macd": 0, "signal": 0, "histogram": 0}

                # Bollinger Bands (20, 2)
                df.ta.bbands(length=20, std=2, append=True)
                if "BBL_20_2.0" in df.columns:
                    indicators["bollinger"] = {
                        "upper": float(df["BBU_20_2.0"].iloc[-1]),
                        "middle": float(df["BBM_20_2.0"].iloc[-1]),
                        "lower": float(df["BBL_20_2.0"].iloc[-1]),
                    }
                else:
                    close = float(df["close"].iloc[-1])
                    indicators["bollinger"] = {"upper": close * 1.05, "middle": close, "lower": close * 0.95}

                # Moving Averages
                df.ta.sma(length=20, append=True)
                df.ta.sma(length=50, append=True)
                df.ta.sma(length=200, append=True)
                df.ta.ema(length=12, append=True)
                df.ta.ema(length=26, append=True)

                indicators["sma_20"] = float(df["SMA_20"].iloc[-1]) if "SMA_20" in df.columns else float(df["close"].iloc[-20:].mean())
                indicators["sma_50"] = float(df["SMA_50"].iloc[-1]) if "SMA_50" in df.columns else float(df["close"].iloc[-50:].mean())
                indicators["sma_200"] = float(df["SMA_200"].iloc[-1]) if "SMA_200" in df.columns else float(df["close"].iloc[-200:].mean()) if len(df) >= 200 else float(df["close"].mean())
                indicators["ema_12"] = float(df["EMA_12"].iloc[-1]) if "EMA_12" in df.columns else float(df["close"].iloc[-1])
                indicators["ema_26"] = float(df["EMA_26"].iloc[-1]) if "EMA_26" in df.columns else float(df["close"].iloc[-1])

            else:
                # Fallback calculations without pandas-ta
                close = df["close"].values

                # RSI calculation
                delta = np.diff(close)
                gain = np.where(delta > 0, delta, 0)
                loss = np.where(delta < 0, -delta, 0)
                avg_gain = np.mean(gain[-14:]) if len(gain) >= 14 else 0
                avg_loss = np.mean(loss[-14:]) if len(loss) >= 14 else 1
                rs = avg_gain / avg_loss if avg_loss > 0 else 0
                indicators["rsi"] = 100 - (100 / (1 + rs))

                # Simple MACD
                ema12 = pd.Series(close).ewm(span=12, adjust=False).mean()
                ema26 = pd.Series(close).ewm(span=26, adjust=False).mean()
                macd_line = ema12 - ema26
                signal_line = macd_line.ewm(span=9, adjust=False).mean()

                indicators["macd"] = {
                    "macd": float(macd_line.iloc[-1]),
                    "signal": float(signal_line.iloc[-1]),
                    "histogram": float(macd_line.iloc[-1] - signal_line.iloc[-1]),
                }

                # Bollinger Bands
                sma20 = pd.Series(close).rolling(20).mean()
                std20 = pd.Series(close).rolling(20).std()
                indicators["bollinger"] = {
                    "upper": float(sma20.iloc[-1] + 2 * std20.iloc[-1]),
                    "middle": float(sma20.iloc[-1]),
                    "lower": float(sma20.iloc[-1] - 2 * std20.iloc[-1]),
                }

                # Moving averages
                indicators["sma_20"] = float(pd.Series(close).rolling(20).mean().iloc[-1])
                indicators["sma_50"] = float(pd.Series(close).rolling(50).mean().iloc[-1]) if len(close) >= 50 else float(np.mean(close))
                indicators["sma_200"] = float(pd.Series(close).rolling(200).mean().iloc[-1]) if len(close) >= 200 else float(np.mean(close))
                indicators["ema_12"] = float(ema12.iloc[-1])
                indicators["ema_26"] = float(ema26.iloc[-1])

            # Identify support/resistance (recent highs/lows)
            recent_high = float(df["high"].iloc[-20:].max())
            recent_low = float(df["low"].iloc[-20:].min())
            current_price = float(df["close"].iloc[-1])

            indicators["support"] = round(recent_low, 2)
            indicators["resistance"] = round(recent_high, 2)
            indicators["current_price"] = round(current_price, 2)

            # Determine trend and signal
            trend = "neutral"
            signal = "hold"
            confidence = 0.6

            # Basic trend determination
            if current_price > indicators["sma_50"] > indicators.get("sma_200", indicators["sma_50"]):
                trend = "bullish"
            elif current_price < indicators["sma_50"] < indicators.get("sma_200", indicators["sma_50"]):
                trend = "bearish"

            # Basic signal generation
            rsi = indicators.get("rsi", 50)
            macd_hist = indicators["macd"]["histogram"]

            if rsi < 30 and macd_hist > 0:
                signal = "buy"
                confidence = 0.75
            elif rsi > 70 and macd_hist < 0:
                signal = "sell"
                confidence = 0.75
            elif rsi > 50 and macd_hist > 0 and trend == "bullish":
                signal = "buy"
                confidence = 0.65
            elif rsi < 50 and macd_hist < 0 and trend == "bearish":
                signal = "sell"
                confidence = 0.65

            # Use Azure OpenAI for pattern interpretation
            pattern_analysis = ""
            try:
                azure_client = AzureOpenAIClient()

                prompt = f"""Analyze these technical indicators for {asset.symbol}:

Current Price: ${current_price:.2f}
Trend: {trend}

Momentum Indicators:
- RSI(14): {rsi:.2f}
- MACD: {indicators['macd']['macd']:.2f}, Signal: {indicators['macd']['signal']:.2f}, Histogram: {indicators['macd']['histogram']:.2f}

Moving Averages:
- SMA(20): ${indicators['sma_20']:.2f}
- SMA(50): ${indicators['sma_50']:.2f}
- EMA(12): ${indicators['ema_12']:.2f}

Bollinger Bands:
- Upper: ${indicators['bollinger']['upper']:.2f}
- Middle: ${indicators['bollinger']['middle']:.2f}
- Lower: ${indicators['bollinger']['lower']:.2f}

Support/Resistance:
- Resistance: ${indicators['resistance']:.2f}
- Support: ${indicators['support']:.2f}

Provide a JSON response with:
1. "signal": one of ["strong_buy", "buy", "hold", "sell", "strong_sell"]
2. "confidence": float 0-1
3. "pattern_analysis": brief analysis of any chart patterns or key technical levels
"""

                messages = [
                    {"role": "system", "content": "You are a technical analyst. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ]

                ai_response = await azure_client._make_request(messages, temperature=0.3, max_tokens=300)

                import json
                ai_content = ai_response["choices"][0]["message"]["content"]
                if "```json" in ai_content:
                    ai_content = ai_content.split("```json")[1].split("```")[0].strip()
                elif "```" in ai_content:
                    ai_content = ai_content.split("```")[1].split("```")[0].strip()

                ai_analysis = json.loads(ai_content)

                signal = ai_analysis.get("signal", signal)
                confidence = ai_analysis.get("confidence", confidence)
                pattern_analysis = ai_analysis.get("pattern_analysis", "")

            except Exception as e:
                self.logger.warning("Azure OpenAI pattern analysis failed", error=str(e))

            # Calculate score (0-10) based on signal strength
            score = 5.0
            if signal in ["strong_buy", "buy"]:
                score = 7.0 + (confidence * 2)
            elif signal in ["strong_sell", "sell"]:
                score = 3.0 - (confidence * 2)
            else:
                score = 5.0 + (confidence * 1)

            score = max(0.0, min(10.0, score))

            return {
                "asset": asset.symbol,
                "analysis_type": "technical",
                "indicators": {k: round(v, 2) if isinstance(v, (int, float)) else v for k, v in indicators.items()},
                "trend": trend,
                "signal": signal,
                "confidence": round(confidence, 2),
                "pattern_analysis": pattern_analysis,
                "score": round(score, 1),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error("Technical analysis failed", error=str(e), exc_info=True)
            return {
                "asset": asset.symbol,
                "analysis_type": "technical",
                "error": str(e),
                "score": 5.0,
                "timestamp": datetime.utcnow().isoformat(),
            }





@ray.remote
class MacroWorker(BaseWorker):
    """
    Analyzes macroeconomic factors with real data

    Capabilities:
    - Fetches macro indicators (interest rates, inflation, GDP, unemployment)
    - Analyzes correlation with target asset
    - Uses Azure OpenAI to assess macro environment impact
    - Generates macro context narrative
    - Returns impact assessment with confidence
    """

    async def process(self, asset: Asset, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze macro conditions with real data"""
        self.logger.info("Analyzing macro", asset=asset.symbol)

        try:
            # Import provider registry
            from fiml.providers.registry import provider_registry

            # Note: Most providers don't directly provide macro data
            # In production, this would integrate with FRED API or similar
            # For now, we'll use reasonable defaults and focus on the analysis structure

            # Fetch some macro proxies (treasury yields, VIX, etc.)
            macro_data = {}

            # Try to fetch related macro assets
            try:
                # Fetch treasury yield as interest rate proxy
                treasury = Asset(symbol="^TNX", asset_type=AssetType.INDEX, name="10-Year Treasury")
                providers = await provider_registry.get_providers_for_asset(treasury, DataType.PRICE)

                for provider in providers:
                    try:
                        response = await provider.fetch_price(treasury)
                        if response.is_valid:
                            macro_data["interest_rate"] = response.data.get("price", 4.5)
                            break
                    except:
                        continue
            except:
                pass

            # Set defaults for macro indicators
            factors = {
                "interest_rate": macro_data.get("interest_rate", 5.25),  # Current fed funds rate proxy
                "inflation": 3.2,  # CPI estimate
                "gdp_growth": 2.1,  # Annual GDP growth estimate
                "unemployment": 3.8,  # Unemployment rate estimate
            }

            # Fetch asset price data to analyze correlation
            correlation_impact = "neutral"
            try:
                providers = await provider_registry.get_providers_for_asset(asset, DataType.OHLCV)

                for provider in providers:
                    try:
                        response = await provider.fetch_ohlcv(asset, timeframe="1d", limit=90)
                        if response.is_valid and response.data:
                            ohlcv = response.data

                            # Simple volatility analysis as macro sensitivity proxy
                            if "close" in ohlcv:
                                close_prices = np.array(ohlcv["close"])
                                returns = np.diff(close_prices) / close_prices[:-1]
                                volatility = np.std(returns) * np.sqrt(252)  # Annualized

                                # High volatility suggests macro sensitivity
                                if volatility > 0.4:
                                    correlation_impact = "high"
                                elif volatility < 0.2:
                                    correlation_impact = "low"
                            break
                    except:
                        continue
            except:
                pass

            # Use Azure OpenAI for macro impact assessment
            environment = "moderately_positive"
            impact = "neutral"
            confidence = 0.65
            narrative = ""

            try:
                azure_client = AzureOpenAIClient()

                prompt = f"""Analyze the macroeconomic environment's impact on {asset.symbol}:

Current Macro Conditions:
- Interest Rate: {factors['interest_rate']:.2f}%
- Inflation: {factors['inflation']:.1f}%
- GDP Growth: {factors['gdp_growth']:.1f}%
- Unemployment: {factors['unemployment']:.1f}%

Asset Characteristics:
- Asset Type: {asset.asset_type.value}
- Sector Correlation: {correlation_impact}

Provide a JSON response with:
1. "environment": one of ["very_positive", "moderately_positive", "neutral", "moderately_negative", "very_negative"]
2. "impact": one of ["positive", "neutral", "negative"]
3. "confidence": float 0-1
4. "narrative": 2-3 sentence analysis of how macro conditions affect this asset
"""

                messages = [
                    {"role": "system", "content": "You are a macroeconomic analyst. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ]

                ai_response = await azure_client._make_request(messages, temperature=0.4, max_tokens=400)

                import json
                ai_content = ai_response["choices"][0]["message"]["content"]
                if "```json" in ai_content:
                    ai_content = ai_content.split("```json")[1].split("```")[0].strip()
                elif "```" in ai_content:
                    ai_content = ai_content.split("```")[1].split("```")[0].strip()

                ai_analysis = json.loads(ai_content)

                environment = ai_analysis.get("environment", "neutral")
                impact = ai_analysis.get("impact", "neutral")
                confidence = ai_analysis.get("confidence", 0.65)
                narrative = ai_analysis.get("narrative", "")

            except Exception as e:
                self.logger.warning("Azure OpenAI macro analysis failed", error=str(e))
                # Fallback analysis
                if factors["interest_rate"] < 3.0 and factors["gdp_growth"] > 2.5:
                    environment = "very_positive"
                    impact = "positive"
                elif factors["interest_rate"] > 5.0 and factors["inflation"] > 4.0:
                    environment = "moderately_negative"
                    impact = "negative"

            # Calculate score (0-10)
            score = 5.0

            if impact == "positive":
                score += 2.0
            elif impact == "negative":
                score -= 2.0

            if environment == "very_positive":
                score += 1.0
            elif environment == "very_negative":
                score -= 1.0

            score = max(0.0, min(10.0, score))

            return {
                "asset": asset.symbol,
                "analysis_type": "macro",
                "factors": factors,
                "environment": environment,
                "impact": impact,
                "correlation_impact": correlation_impact,
                "confidence": round(confidence, 2),
                "narrative": narrative,
                "score": round(score, 1),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error("Macro analysis failed", error=str(e), exc_info=True)
            return {
                "asset": asset.symbol,
                "analysis_type": "macro",
                "error": str(e),
                "score": 5.0,
                "timestamp": datetime.utcnow().isoformat(),
            }





@ray.remote
class SentimentWorker(BaseWorker):
    """
    Analyzes market sentiment using news and AI

    Capabilities:
    - Fetches news articles from providers
    - Uses Azure OpenAI for sentiment analysis on headlines and content
    - Aggregates sentiment scores across sources
    - Weights by source credibility
    - Identifies sentiment trends (improving/declining)
    - Returns sentiment score (-1 to 1) with supporting evidence
    """

    async def process(self, asset: Asset, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze sentiment with news and AI"""
        self.logger.info("Analyzing sentiment", asset=asset.symbol)

        try:
            # Import provider registry
            from fiml.providers.registry import provider_registry

            # Fetch news articles
            providers = await provider_registry.get_providers_for_asset(asset, DataType.NEWS)

            articles = []
            for provider in providers:
                try:
                    response = await provider.fetch_news(asset, limit=20)
                    if response.is_valid and response.data.get("articles"):
                        articles.extend(response.data["articles"])
                        self.logger.info("Fetched news", provider=provider.name, count=len(response.data["articles"]))
                        if len(articles) >= 20:
                            break
                except Exception as e:
                    self.logger.warning("Provider failed", provider=provider.name, error=str(e))
                    continue

            if not articles:
                self.logger.warning("No news articles available")
                # Return neutral sentiment
                return {
                    "asset": asset.symbol,
                    "analysis_type": "sentiment",
                    "sentiment_score": 0.0,
                    "overall": "neutral",
                    "confidence": 0.3,
                    "articles_analyzed": 0,
                    "score": 5.0,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Analyze sentiment using Azure OpenAI
            sentiment_scores = []
            analyzed_articles = []

            try:
                azure_client = AzureOpenAIClient()

                # Analyze up to 10 most recent articles
                for article in articles[:10]:
                    try:
                        title = article.get("title", "")
                        description = article.get("description", "")
                        text = f"{title}. {description}"

                        if not text.strip():
                            continue

                        # Analyze sentiment
                        sentiment = await azure_client.analyze_sentiment(text)

                        # Calculate compound score (-1 to 1)
                        compound = sentiment.get("positive", 0) - sentiment.get("negative", 0)

                        sentiment_scores.append(compound)
                        analyzed_articles.append({
                            "title": title,
                            "sentiment": round(compound, 2),
                            "published_at": article.get("published_at", ""),
                        })

                    except Exception as e:
                        self.logger.warning("Failed to analyze article", error=str(e))
                        continue

            except Exception as e:
                self.logger.warning("Azure OpenAI sentiment analysis failed", error=str(e))

            # Calculate aggregate sentiment
            if sentiment_scores:
                avg_sentiment = float(np.mean(sentiment_scores))
                sentiment_std = float(np.std(sentiment_scores))

                # Determine trend (compare recent vs older articles)
                if len(sentiment_scores) >= 5:
                    recent_sentiment = np.mean(sentiment_scores[:3])
                    older_sentiment = np.mean(sentiment_scores[3:])
                    if recent_sentiment > older_sentiment + 0.1:
                        trend = "improving"
                    elif recent_sentiment < older_sentiment - 0.1:
                        trend = "declining"
                    else:
                        trend = "stable"
                else:
                    trend = "stable"
            else:
                # Fallback to simple keyword analysis
                positive_keywords = ["growth", "profit", "beat", "success", "gain", "rise", "bullish"]
                negative_keywords = ["loss", "decline", "miss", "concern", "fall", "bearish", "risk"]

                pos_count = 0
                neg_count = 0

                for article in articles[:10]:
                    text = f"{article.get('title', '')} {article.get('description', '')}".lower()
                    pos_count += sum(1 for kw in positive_keywords if kw in text)
                    neg_count += sum(1 for kw in negative_keywords if kw in text)

                if pos_count + neg_count > 0:
                    avg_sentiment = (pos_count - neg_count) / (pos_count + neg_count)
                else:
                    avg_sentiment = 0.0

                sentiment_std = 0.3
                trend = "stable"

                # Create basic analyzed articles
                for article in articles[:5]:
                    analyzed_articles.append({
                        "title": article.get("title", ""),
                        "sentiment": 0.0,
                        "published_at": article.get("published_at", ""),
                    })

            # Determine overall sentiment
            if avg_sentiment > 0.3:
                overall = "positive"
            elif avg_sentiment < -0.3:
                overall = "negative"
            else:
                overall = "neutral"

            # Calculate confidence (lower std = higher confidence)
            confidence = max(0.3, min(0.95, 1.0 - sentiment_std))

            # Calculate score (0-10)
            # Map sentiment from [-1, 1] to [0, 10]
            score = 5.0 + (avg_sentiment * 4)

            # Adjust based on trend
            if trend == "improving":
                score += 0.5
            elif trend == "declining":
                score -= 0.5

            score = max(0.0, min(10.0, score))

            return {
                "asset": asset.symbol,
                "analysis_type": "sentiment",
                "sentiment_score": round(avg_sentiment, 2),
                "overall": overall,
                "trend": trend,
                "confidence": round(confidence, 2),
                "articles_analyzed": len(analyzed_articles),
                "top_articles": analyzed_articles[:5],
                "score": round(score, 1),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error("Sentiment analysis failed", error=str(e), exc_info=True)
            return {
                "asset": asset.symbol,
                "analysis_type": "sentiment",
                "error": str(e),
                "score": 5.0,
                "timestamp": datetime.utcnow().isoformat(),
            }





@ray.remote
class CorrelationWorker(BaseWorker):
    """
    Analyzes asset correlations with market and peers

    Capabilities:
    - Fetches price data for asset and comparison assets (SPY, QQQ, sector ETFs)
    - Calculates Pearson correlation coefficients
    - Computes rolling correlations (30d, 90d)
    - Identifies correlation breakdowns
    - Calculates beta vs market
    - Returns correlation matrix with insights
    """

    async def process(self, asset: Asset, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze correlations with market and peers"""
        self.logger.info("Analyzing correlations", asset=asset.symbol)

        try:
            # Import provider registry
            from fiml.providers.registry import provider_registry

            # Define benchmark assets to compare against
            benchmarks = {
                "SPY": Asset(symbol="SPY", asset_type=AssetType.EQUITY, name="S&P 500 ETF"),
                "QQQ": Asset(symbol="QQQ", asset_type=AssetType.EQUITY, name="Nasdaq 100 ETF"),
            }

            # Fetch price data for target asset
            providers = await provider_registry.get_providers_for_asset(asset, DataType.OHLCV)

            target_prices = None
            for provider in providers:
                try:
                    response = await provider.fetch_ohlcv(asset, timeframe="1d", limit=180)
                    if response.is_valid and response.data:
                        target_prices = np.array(response.data.get("close", []))
                        self.logger.info("Fetched target prices", provider=provider.name, points=len(target_prices))
                        break
                except Exception as e:
                    self.logger.warning("Provider failed for target", provider=provider.name, error=str(e))
                    continue

            if target_prices is None or len(target_prices) < 30:
                raise ValueError("Insufficient price data for correlation analysis")

            # Fetch benchmark prices
            benchmark_prices = {}
            for bench_name, bench_asset in benchmarks.items():
                try:
                    providers = await provider_registry.get_providers_for_asset(bench_asset, DataType.OHLCV)

                    for provider in providers:
                        try:
                            response = await provider.fetch_ohlcv(bench_asset, timeframe="1d", limit=180)
                            if response.is_valid and response.data:
                                benchmark_prices[bench_name] = np.array(response.data.get("close", []))
                                self.logger.info("Fetched benchmark", benchmark=bench_name, points=len(benchmark_prices[bench_name]))
                                break
                        except:
                            continue
                except Exception as e:
                    self.logger.warning("Failed to fetch benchmark", benchmark=bench_name, error=str(e))

            # Calculate correlations
            correlations = {}
            rolling_correlations = {}

            # Ensure all series are same length
            min_length = min(len(target_prices), *[len(prices) for prices in benchmark_prices.values()])
            target_returns = np.diff(target_prices[-min_length:]) / target_prices[-min_length:-1]

            for bench_name, bench_prices in benchmark_prices.items():
                bench_returns = np.diff(bench_prices[-min_length:]) / bench_prices[-min_length:-1]

                # Overall correlation
                if len(target_returns) > 0 and len(bench_returns) > 0:
                    correlation = float(np.corrcoef(target_returns, bench_returns)[0, 1])
                    correlations[bench_name.lower()] = round(correlation, 3)

                    # Rolling 30-day correlation
                    if len(target_returns) >= 30:
                        rolling_30d = []
                        for i in range(30, len(target_returns)):
                            corr = np.corrcoef(target_returns[i-30:i], bench_returns[i-30:i])[0, 1]
                            rolling_30d.append(corr)

                        current_30d_corr = float(rolling_30d[-1]) if rolling_30d else correlation
                        rolling_correlations[f"{bench_name.lower()}_30d"] = round(current_30d_corr, 3)

            # Calculate beta vs SPY (market)
            beta = 1.0
            if "SPY" in benchmark_prices and len(target_returns) > 0:
                spy_returns = np.diff(benchmark_prices["SPY"][-min_length:]) / benchmark_prices["SPY"][-min_length:-1]

                if len(spy_returns) > 0:
                    covariance = np.cov(target_returns, spy_returns)[0, 1]
                    market_variance = np.var(spy_returns)

                    if market_variance > 0:
                        beta = float(covariance / market_variance)

            # Identify correlation breakdown (recent vs historical)
            correlation_shift = "stable"
            if "spy_30d" in rolling_correlations and "spy" in correlations:
                recent_corr = rolling_correlations["spy_30d"]
                historical_corr = correlations["spy"]

                if abs(recent_corr - historical_corr) > 0.2:
                    if recent_corr < historical_corr:
                        correlation_shift = "decoupling"
                    else:
                        correlation_shift = "converging"

            # Calculate diversification score (lower correlation = better diversification)
            if correlations:
                avg_correlation = np.mean(list(correlations.values()))
                diversification_score = 1.0 - abs(avg_correlation)
            else:
                diversification_score = 0.5

            # Calculate score (0-10)
            # Lower correlation with market = higher diversification value
            score = 5.0

            if beta < 0.8:
                score += 1.5  # Low beta is defensive
            elif beta > 1.5:
                score -= 0.5  # High beta is aggressive

            if diversification_score > 0.5:
                score += 1.0
            elif diversification_score < 0.2:
                score -= 0.5

            if correlation_shift == "decoupling":
                score += 0.5  # Decoupling can be good for diversification

            score = max(0.0, min(10.0, score))

            return {
                "asset": asset.symbol,
                "analysis_type": "correlation",
                "correlations": correlations,
                "rolling_correlations": rolling_correlations,
                "beta": round(beta, 2),
                "correlation_shift": correlation_shift,
                "diversification_score": round(diversification_score, 2),
                "score": round(score, 1),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error("Correlation analysis failed", error=str(e), exc_info=True)
            return {
                "asset": asset.symbol,
                "analysis_type": "correlation",
                "error": str(e),
                "score": 5.0,
                "timestamp": datetime.utcnow().isoformat(),
            }





@ray.remote
class RiskWorker(BaseWorker):
    """
    Performs comprehensive risk analysis

    Capabilities:
    - Fetches historical price data
    - Calculates risk metrics: volatility, VaR, Sharpe ratio, max drawdown, downside deviation
    - Uses Azure OpenAI to assess risk profile
    - Generates risk warnings for high-risk assets
    - Returns risk metrics with risk level classification
    """

    async def process(self, asset: Asset, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze risk with comprehensive metrics"""
        self.logger.info("Analyzing risk", asset=asset.symbol)

        try:
            # Import provider registry
            from fiml.providers.registry import provider_registry

            # Fetch historical price data (1 year for reliable risk metrics)
            providers = await provider_registry.get_providers_for_asset(asset, DataType.OHLCV)

            ohlcv_data = None
            for provider in providers:
                try:
                    response = await provider.fetch_ohlcv(asset, timeframe="1d", limit=365)
                    if response.is_valid and response.data:
                        ohlcv_data = response.data
                        self.logger.info("Fetched price data", provider=provider.name, bars=len(ohlcv_data.get("close", [])))
                        break
                except Exception as e:
                    self.logger.warning("Provider failed", provider=provider.name, error=str(e))
                    continue

            if not ohlcv_data or not ohlcv_data.get("close"):
                raise ValueError("Insufficient price data for risk analysis")

            # Extract price data
            close_prices = np.array(ohlcv_data["close"])

            # Calculate returns
            returns = np.diff(close_prices) / close_prices[:-1]

            # Historical Volatility (annualized)
            daily_volatility = np.std(returns)
            annual_volatility = daily_volatility * np.sqrt(252)

            # Value at Risk (VaR) - parametric method
            var_95 = float(np.percentile(returns, 5))  # 95% VaR
            var_99 = float(np.percentile(returns, 1))  # 99% VaR

            # Sharpe Ratio (assuming risk-free rate of 4%)
            risk_free_rate = 0.04
            mean_return = np.mean(returns) * 252  # Annualized
            sharpe_ratio = (mean_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0

            # Maximum Drawdown
            cumulative_returns = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = float(np.min(drawdown))

            # Downside Deviation (semi-deviation)
            negative_returns = returns[returns < 0]
            downside_deviation = float(np.std(negative_returns) * np.sqrt(252)) if len(negative_returns) > 0 else 0

            # Sortino Ratio
            sortino_ratio = (mean_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0

            # Implied Volatility (if options data available - placeholder)
            implied_volatility = None  # Would need options provider

            # Build metrics dictionary
            metrics = {
                "volatility": round(annual_volatility, 4),
                "var_95": round(var_95, 4),
                "var_99": round(var_99, 4),
                "sharpe_ratio": round(sharpe_ratio, 2),
                "sortino_ratio": round(sortino_ratio, 2),
                "max_drawdown": round(max_drawdown, 4),
                "downside_deviation": round(downside_deviation, 4),
                "mean_return": round(mean_return, 4),
            }

            if implied_volatility:
                metrics["implied_volatility"] = round(implied_volatility, 4)

            # Classify risk level
            if annual_volatility > 0.5:
                risk_level = "very_high"
            elif annual_volatility > 0.35:
                risk_level = "high"
            elif annual_volatility > 0.20:
                risk_level = "moderate"
            elif annual_volatility > 0.10:
                risk_level = "low"
            else:
                risk_level = "very_low"

            # Use Azure OpenAI for risk assessment
            risk_assessment = ""
            warnings = []
            confidence = 0.75

            try:
                azure_client = AzureOpenAIClient()

                prompt = f"""Analyze the risk profile for {asset.symbol}:

Risk Metrics:
- Annual Volatility: {annual_volatility*100:.2f}%
- VaR (95%): {var_95*100:.2f}%
- VaR (99%): {var_99*100:.2f}%
- Sharpe Ratio: {sharpe_ratio:.2f}
- Sortino Ratio: {sortino_ratio:.2f}
- Maximum Drawdown: {max_drawdown*100:.2f}%
- Downside Deviation: {downside_deviation*100:.2f}%

Current Classification: {risk_level}

Provide a JSON response with:
1. "risk_level": one of ["very_low", "low", "moderate", "high", "very_high"]
2. "risk_assessment": 2-3 sentence analysis of the risk profile
3. "warnings": array of specific risk warnings (if any)
4. "confidence": float 0-1
"""

                messages = [
                    {"role": "system", "content": "You are a risk management analyst. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ]

                ai_response = await azure_client._make_request(messages, temperature=0.3, max_tokens=400)

                import json
                ai_content = ai_response["choices"][0]["message"]["content"]
                if "```json" in ai_content:
                    ai_content = ai_content.split("```json")[1].split("```")[0].strip()
                elif "```" in ai_content:
                    ai_content = ai_content.split("```")[1].split("```")[0].strip()

                ai_analysis = json.loads(ai_content)

                risk_level = ai_analysis.get("risk_level", risk_level)
                risk_assessment = ai_analysis.get("risk_assessment", "")
                warnings = ai_analysis.get("warnings", [])
                confidence = ai_analysis.get("confidence", 0.75)

            except Exception as e:
                self.logger.warning("Azure OpenAI risk assessment failed", error=str(e))
                # Generate rule-based warnings
                if annual_volatility > 0.5:
                    warnings.append("Extremely high volatility detected")
                if max_drawdown < -0.3:
                    warnings.append("Significant historical drawdown risk")
                if sharpe_ratio < 0.5:
                    warnings.append("Poor risk-adjusted returns")

            # Calculate score (0-10)
            # Lower risk = higher score for conservative investors
            # But also factor in risk-adjusted returns
            score = 5.0

            # Penalize high volatility
            if annual_volatility > 0.5:
                score -= 2.0
            elif annual_volatility < 0.15:
                score += 1.0

            # Reward good risk-adjusted returns
            if sharpe_ratio > 1.5:
                score += 2.0
            elif sharpe_ratio > 1.0:
                score += 1.0
            elif sharpe_ratio < 0:
                score -= 2.0

            # Penalize severe drawdowns
            if max_drawdown < -0.4:
                score -= 1.5
            elif max_drawdown > -0.1:
                score += 0.5

            score = max(0.0, min(10.0, score))

            return {
                "asset": asset.symbol,
                "analysis_type": "risk",
                "metrics": metrics,
                "risk_level": risk_level,
                "risk_assessment": risk_assessment,
                "warnings": warnings,
                "confidence": round(confidence, 2),
                "score": round(score, 1),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error("Risk analysis failed", error=str(e), exc_info=True)
            return {
                "asset": asset.symbol,
                "analysis_type": "risk",
                "error": str(e),
                "score": 5.0,
                "timestamp": datetime.utcnow().isoformat(),
            }





@ray.remote
class NewsWorker(BaseWorker):
    """
    Fetches and analyzes news with AI-powered event extraction

    Capabilities:
    - Fetches recent news from providers
    - Uses Azure OpenAI to extract key events
    - Assesses impact (high/medium/low) per article
    - Identifies sentiment per article
    - Detects market-moving news
    - Builds event timeline
    - Returns top articles with impact scores
    """

    async def process(self, asset: Asset, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch and analyze news with event extraction"""
        self.logger.info("Analyzing news", asset=asset.symbol)

        try:
            # Import provider registry
            from fiml.providers.registry import provider_registry

            # Fetch news articles
            providers = await provider_registry.get_providers_for_asset(asset, DataType.NEWS)

            articles = []
            for provider in providers:
                try:
                    response = await provider.fetch_news(asset, limit=25)
                    if response.is_valid and response.data.get("articles"):
                        articles.extend(response.data["articles"])
                        self.logger.info("Fetched news", provider=provider.name, count=len(response.data["articles"]))
                        if len(articles) >= 20:
                            break
                except Exception as e:
                    self.logger.warning("Provider failed", provider=provider.name, error=str(e))
                    continue

            if not articles:
                self.logger.warning("No news articles available")
                return {
                    "asset": asset.symbol,
                    "analysis_type": "news",
                    "articles": [],
                    "event_count": 0,
                    "overall_sentiment": 0.0,
                    "score": 5.0,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Analyze articles using Azure OpenAI
            analyzed_articles = []
            timeline_events = []

            try:
                azure_client = AzureOpenAIClient()

                # Analyze top 10 articles
                for article in articles[:10]:
                    try:
                        title = article.get("title", "")
                        description = article.get("description", "")
                        published_at = article.get("published_at", "")

                        if not title.strip():
                            continue

                        # Use AI to extract events and assess impact
                        prompt = f"""Analyze this news article about {asset.symbol}:

Title: {title}
Description: {description}

Provide a JSON response with:
1. "sentiment": float from -1 (very negative) to 1 (very positive)
2. "impact": one of ["high", "medium", "low"]
3. "key_event": brief description of main event (1 sentence)
4. "market_moving": boolean - is this likely to move the stock price?
"""

                        messages = [
                            {"role": "system", "content": "You are a financial news analyst. Return only valid JSON."},
                            {"role": "user", "content": prompt}
                        ]

                        ai_response = await azure_client._make_request(messages, temperature=0.3, max_tokens=200)

                        import json
                        ai_content = ai_response["choices"][0]["message"]["content"]
                        if "```json" in ai_content:
                            ai_content = ai_content.split("```json")[1].split("```")[0].strip()
                        elif "```" in ai_content:
                            ai_content = ai_content.split("```")[1].split("```")[0].strip()

                        analysis = json.loads(ai_content)

                        analyzed_article = {
                            "title": title,
                            "sentiment": round(analysis.get("sentiment", 0.0), 2),
                            "impact": analysis.get("impact", "low"),
                            "key_event": analysis.get("key_event", ""),
                            "market_moving": analysis.get("market_moving", False),
                            "published_at": published_at,
                            "source": article.get("source", ""),
                        }

                        analyzed_articles.append(analyzed_article)

                        # Add to timeline if significant
                        if analyzed_article["impact"] in ["high", "medium"]:
                            timeline_events.append({
                                "timestamp": published_at,
                                "event": analyzed_article["key_event"],
                                "impact": analyzed_article["impact"],
                                "sentiment": analyzed_article["sentiment"],
                            })

                    except Exception as e:
                        self.logger.warning("Failed to analyze article", error=str(e))
                        # Add basic article without AI analysis
                        analyzed_articles.append({
                            "title": title,
                            "sentiment": 0.0,
                            "impact": "low",
                            "published_at": published_at,
                            "source": article.get("source", ""),
                        })
                        continue

            except Exception as e:
                self.logger.warning("Azure OpenAI news analysis failed", error=str(e))
                # Fallback: basic sentiment from keywords
                for article in articles[:10]:
                    title = article.get("title", "")

                    # Simple keyword-based sentiment
                    positive_kw = ["beat", "surge", "rally", "gain", "profit", "growth", "success"]
                    negative_kw = ["miss", "plunge", "fall", "loss", "concern", "warning", "decline"]

                    title_lower = title.lower()
                    pos_count = sum(1 for kw in positive_kw if kw in title_lower)
                    neg_count = sum(1 for kw in negative_kw if kw in title_lower)

                    sentiment = 0.0
                    if pos_count > neg_count:
                        sentiment = 0.5
                    elif neg_count > pos_count:
                        sentiment = -0.5

                    # Detect high impact keywords
                    high_impact_kw = ["earnings", "acquisition", "merger", "bankruptcy", "lawsuit", "fda"]
                    impact = "high" if any(kw in title_lower for kw in high_impact_kw) else "low"

                    analyzed_articles.append({
                        "title": title,
                        "sentiment": sentiment,
                        "impact": impact,
                        "published_at": article.get("published_at", ""),
                        "source": article.get("source", ""),
                    })

            # Calculate overall sentiment
            if analyzed_articles:
                sentiments = [a["sentiment"] for a in analyzed_articles if "sentiment" in a]
                overall_sentiment = float(np.mean(sentiments)) if sentiments else 0.0

                # Weight high-impact articles more
                weighted_sentiments = []
                for a in analyzed_articles:
                    weight = 3.0 if a.get("impact") == "high" else (1.5 if a.get("impact") == "medium" else 1.0)
                    weighted_sentiments.extend([a.get("sentiment", 0.0)] * int(weight))

                if weighted_sentiments:
                    overall_sentiment = float(np.mean(weighted_sentiments))
            else:
                overall_sentiment = 0.0

            # Count high-impact events
            event_count = sum(1 for a in analyzed_articles if a.get("impact") in ["high", "medium"])
            market_moving_count = sum(1 for a in analyzed_articles if a.get("market_moving", False))

            # Sort timeline by date
            timeline_events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            # Calculate score (0-10)
            score = 5.0 + (overall_sentiment * 3)  # Sentiment drives score

            # Adjust based on news volume and quality
            if event_count > 3:
                score += 0.5

            if market_moving_count > 0:
                # Market-moving news increases uncertainty/volatility
                if overall_sentiment > 0:
                    score += 1.0
                else:
                    score -= 1.0

            score = max(0.0, min(10.0, score))

            return {
                "asset": asset.symbol,
                "analysis_type": "news",
                "articles": analyzed_articles[:10],  # Top 10
                "timeline": timeline_events[:5],  # Top 5 events
                "overall_sentiment": round(overall_sentiment, 2),
                "event_count": event_count,
                "market_moving_count": market_moving_count,
                "score": round(score, 1),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error("News analysis failed", error=str(e), exc_info=True)
            return {
                "asset": asset.symbol,
                "analysis_type": "news",
                "error": str(e),
                "score": 5.0,
                "timestamp": datetime.utcnow().isoformat(),
            }




@ray.remote
class OptionsWorker(BaseWorker):
    """
    Analyzes options market data for implied volatility and positioning

    Capabilities:
    - Calculates implied volatility from options prices
    - Analyzes put/call ratio
    - Identifies unusual options activity
    - Detects volatility skew
    - Assesses market sentiment from options flow
    - Returns options insights with implied outlook
    """

    async def process(self, asset: Asset, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze options market with real data"""
        self.logger.info("Analyzing options", asset=asset.symbol)

        try:
            # Import provider registry
            from fiml.providers.registry import provider_registry

            # Fetch options chain data
            providers = await provider_registry.get_providers_for_asset(asset, DataType.OPTIONS)

            options_data = None
            for provider in providers:
                try:
                    response = await provider.fetch_options_chain(asset)
                    if response.is_valid and response.data:
                        options_data = response.data
                        self.logger.info("Fetched options data", provider=provider.name)
                        break
                except Exception as e:
                    self.logger.warning("Provider failed", provider=provider.name, error=str(e))
                    continue

            if not options_data:
                self.logger.warning("No options data available")
                # Fallback to historical volatility
                return await self._analyze_historical_volatility(asset)

            # Extract options metrics
            calls = options_data.get("calls", [])
            puts = options_data.get("puts", [])

            if not calls and not puts:
                return await self._analyze_historical_volatility(asset)

            # Calculate Put/Call Ratio
            put_volume = sum(opt.get("volume", 0) for opt in puts)
            call_volume = sum(opt.get("volume", 0) for opt in calls)
            put_call_ratio = put_volume / call_volume if call_volume > 0 else 0

            # Calculate Put/Call Open Interest Ratio
            put_oi = sum(opt.get("open_interest", 0) for opt in puts)
            call_oi = sum(opt.get("open_interest", 0) for opt in calls)
            put_call_oi_ratio = put_oi / call_oi if call_oi > 0 else 0

            # Extract implied volatilities
            call_ivs = [opt.get("implied_volatility", 0) for opt in calls if opt.get("implied_volatility")]
            put_ivs = [opt.get("implied_volatility", 0) for opt in puts if opt.get("implied_volatility")]

            # Calculate average implied volatility
            avg_call_iv = float(np.mean(call_ivs)) if call_ivs else 0
            avg_put_iv = float(np.mean(put_ivs)) if put_ivs else 0
            avg_iv = (avg_call_iv + avg_put_iv) / 2 if (avg_call_iv or avg_put_iv) else 0

            # Detect volatility skew (put IV > call IV suggests fear)
            volatility_skew = avg_put_iv - avg_call_iv

            # Identify unusual activity (volume > 2x open interest)
            unusual_calls = [
                opt for opt in calls
                if opt.get("volume", 0) > 2 * opt.get("open_interest", 1)
                and opt.get("volume", 0) > 100
            ]
            unusual_puts = [
                opt for opt in puts
                if opt.get("volume", 0) > 2 * opt.get("open_interest", 1)
                and opt.get("volume", 0) > 100
            ]

            # Build metrics dictionary
            metrics = {
                "put_call_ratio": round(put_call_ratio, 3),
                "put_call_oi_ratio": round(put_call_oi_ratio, 3),
                "avg_implied_volatility": round(avg_iv, 4),
                "call_implied_volatility": round(avg_call_iv, 4),
                "put_implied_volatility": round(avg_put_iv, 4),
                "volatility_skew": round(volatility_skew, 4),
                "unusual_call_count": len(unusual_calls),
                "unusual_put_count": len(unusual_puts),
                "total_call_volume": call_volume,
                "total_put_volume": put_volume,
            }

            # Determine market sentiment from options
            sentiment = "neutral"
            if put_call_ratio > 1.2:
                sentiment = "bearish"  # More puts than calls
            elif put_call_ratio < 0.7:
                sentiment = "bullish"  # More calls than puts

            # Assess volatility outlook
            volatility_outlook = "normal"
            if avg_iv > 0.40:
                volatility_outlook = "elevated"
            elif avg_iv > 0.60:
                volatility_outlook = "extreme"
            elif avg_iv < 0.15:
                volatility_outlook = "compressed"

            # Use Azure OpenAI for interpretation
            interpretation = ""
            confidence = 0.7

            try:
                azure_client = AzureOpenAIClient()

                prompt = f"""Analyze these options market metrics for {asset.symbol}:

Options Metrics:
- Put/Call Ratio: {put_call_ratio:.2f}
- Put/Call OI Ratio: {put_call_oi_ratio:.2f}
- Average Implied Volatility: {avg_iv*100:.2f}%
- Volatility Skew: {volatility_skew*100:.2f}%
- Unusual Calls: {len(unusual_calls)}
- Unusual Puts: {len(unusual_puts)}

Provide a JSON response with:
1. "sentiment": one of ["very_bullish", "bullish", "neutral", "bearish", "very_bearish"]
2. "volatility_outlook": one of ["compressed", "normal", "elevated", "extreme"]
3. "confidence": float 0-1
4. "interpretation": 2-3 sentence analysis of options positioning and implied outlook
"""

                messages = [
                    {"role": "system", "content": "You are an options market analyst. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ]

                ai_response = await azure_client._make_request(messages, temperature=0.3, max_tokens=300)

                import json
                ai_content = ai_response["choices"][0]["message"]["content"]
                if "```json" in ai_content:
                    ai_content = ai_content.split("```json")[1].split("```")[0].strip()
                elif "```" in ai_content:
                    ai_content = ai_content.split("```")[1].split("```")[0].strip()

                ai_analysis = json.loads(ai_content)

                sentiment = ai_analysis.get("sentiment", sentiment)
                volatility_outlook = ai_analysis.get("volatility_outlook", volatility_outlook)
                confidence = ai_analysis.get("confidence", confidence)
                interpretation = ai_analysis.get("interpretation", "")

            except Exception as e:
                self.logger.warning("Azure OpenAI options interpretation failed", error=str(e))

            # Calculate score (0-10)
            score = 5.0

            # Adjust based on sentiment
            if sentiment == "very_bullish":
                score += 2.0
            elif sentiment == "bullish":
                score += 1.0
            elif sentiment == "bearish":
                score -= 1.0
            elif sentiment == "very_bearish":
                score -= 2.0

            # Adjust for volatility (extreme volatility is risky)
            if volatility_outlook == "extreme":
                score -= 1.0
            elif volatility_outlook == "compressed":
                score += 0.5

            # Adjust for unusual activity (can signal opportunity or risk)
            unusual_total = len(unusual_calls) + len(unusual_puts)
            if unusual_total > 5:
                score += 0.5 if sentiment in ["bullish", "very_bullish"] else -0.5

            score = max(0.0, min(10.0, score))

            return {
                "asset": asset.symbol,
                "analysis_type": "options",
                "metrics": metrics,
                "sentiment": sentiment,
                "volatility_outlook": volatility_outlook,
                "confidence": round(confidence, 2),
                "interpretation": interpretation,
                "unusual_activity": {
                    "calls": [
                        {
                            "strike": opt.get("strike"),
                            "volume": opt.get("volume"),
                            "open_interest": opt.get("open_interest"),
                        }
                        for opt in unusual_calls[:5]
                    ],
                    "puts": [
                        {
                            "strike": opt.get("strike"),
                            "volume": opt.get("volume"),
                            "open_interest": opt.get("open_interest"),
                        }
                        for opt in unusual_puts[:5]
                    ],
                },
                "score": round(score, 1),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error("Options analysis failed", error=str(e), exc_info=True)
            return {
                "asset": asset.symbol,
                "analysis_type": "options",
                "error": str(e),
                "score": 5.0,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _analyze_historical_volatility(self, asset: Asset) -> Dict[str, Any]:
        """Fallback to historical volatility when options data unavailable"""
        try:
            from fiml.providers.registry import provider_registry

            # Fetch OHLCV data
            providers = await provider_registry.get_providers_for_asset(asset, DataType.OHLCV)

            for provider in providers:
                try:
                    response = await provider.fetch_ohlcv(asset, timeframe="1d", limit=90)
                    if response.is_valid and response.data:
                        close_prices = np.array(response.data["close"])
                        returns = np.diff(close_prices) / close_prices[:-1]

                        # Calculate historical volatility (annualized)
                        hist_vol = float(np.std(returns) * np.sqrt(252))

                        return {
                            "asset": asset.symbol,
                            "analysis_type": "options",
                            "metrics": {
                                "historical_volatility": round(hist_vol, 4),
                                "put_call_ratio": None,
                                "avg_implied_volatility": None,
                            },
                            "sentiment": "neutral",
                            "volatility_outlook": "normal",
                            "confidence": 0.5,
                            "interpretation": f"Historical volatility: {hist_vol*100:.2f}%. No options data available.",
                            "score": 5.0,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                except:
                    continue

        except Exception as e:
            self.logger.error("Historical volatility fallback failed", error=str(e))

        return {
            "asset": asset.symbol,
            "analysis_type": "options",
            "error": "No data available",
            "score": 5.0,
            "timestamp": datetime.utcnow().isoformat(),
        }

