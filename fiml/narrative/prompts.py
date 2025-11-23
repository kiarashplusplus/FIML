"""
Narrative Generation Prompt Templates

Provides structured prompts for different narrative types, expertise levels,
and languages. Templates are optimized for Azure OpenAI to generate
high-quality financial narratives.
"""

from typing import Dict

from fiml.narrative.models import ExpertiseLevel, Language, NarrativeType


class PromptTemplateLibrary:
    """
    Library of prompt templates for narrative generation

    Organizes templates by narrative type, expertise level, and language
    to enable adaptive, multi-lingual narrative generation.
    """

    def __init__(self) -> None:
        self.templates = self._initialize_templates()

    def get_template(
        self,
        narrative_type: NarrativeType,
        expertise_level: ExpertiseLevel,
        language: Language = Language.ENGLISH,
    ) -> Dict[str, str]:
        """
        Get prompt template for specific parameters

        Args:
            narrative_type: Type of narrative section
            expertise_level: User expertise level
            language: Target language

        Returns:
            Dictionary with 'system' and 'user' prompt templates
        """
        key = f"{narrative_type.value}_{expertise_level.value}_{language.value}"

        # Fallback to English if language not available
        if key not in self.templates:
            key = f"{narrative_type.value}_{expertise_level.value}_en"

        # Fallback to intermediate if expertise level not available
        if key not in self.templates:
            key = f"{narrative_type.value}_intermediate_en"

        return self.templates.get(
            key,
            {
                "system": "You are a financial analyst creating clear narratives.",
                "user": "Analyze the following data:\n{data}",
            },
        )

    def _initialize_templates(self) -> Dict[str, Dict[str, str]]:
        """Initialize all prompt templates"""
        templates = {}

        # Market Context Templates
        templates.update(self._get_market_context_templates())

        # Technical Analysis Templates
        templates.update(self._get_technical_templates())

        # Fundamental Analysis Templates
        templates.update(self._get_fundamental_templates())

        # Sentiment Analysis Templates
        templates.update(self._get_sentiment_templates())

        # Risk Analysis Templates
        templates.update(self._get_risk_templates())

        # Summary Templates
        templates.update(self._get_summary_templates())

        return templates

    def _get_market_context_templates(self) -> Dict[str, Dict[str, str]]:
        """Market context prompt templates"""
        return {
            # BEGINNER - English
            "market_context_beginner_en": {
                "system": (
                    "You are a friendly financial educator explaining market information "
                    "to someone new to investing. Use simple language, avoid jargon, and "
                    "explain concepts clearly. Keep it conversational and encouraging."
                ),
                "user": (
                    "Create a simple market context summary for {asset_name} ({symbol}).\n\n"
                    "Current price: ${price}\n"
                    "Today's change: {change_percent}%\n"
                    "Trading volume: {volume}\n"
                    "52-week high: ${week_52_high}\n"
                    "52-week low: ${week_52_low}\n\n"
                    "Explain in 2-3 sentences what this means in simple terms. "
                    "Focus on the current price movement and where the stock is trading "
                    "in its yearly range."
                ),
            },
            # INTERMEDIATE - English
            "market_context_intermediate_en": {
                "system": (
                    "You are a financial analyst providing market context for investors "
                    "with some experience. Use proper financial terminology but explain "
                    "key concepts. Be informative and professional."
                ),
                "user": (
                    "Provide market context analysis for {asset_name} ({symbol}).\n\n"
                    "Price: ${price}\n"
                    "Change: {change_percent}% ({change})\n"
                    "Volume: {volume} (Avg: {avg_volume})\n"
                    "Market Cap: ${market_cap}\n"
                    "52-week range: ${week_52_low} - ${week_52_high}\n\n"
                    "Create a 3-4 sentence summary covering:\n"
                    "1. Current price movement and magnitude\n"
                    "2. Volume analysis (relative to average)\n"
                    "3. Position within 52-week range\n"
                    "4. Any notable patterns or levels"
                ),
            },
            # ADVANCED - English
            "market_context_advanced_en": {
                "system": (
                    "You are a professional market analyst providing detailed market "
                    "context for experienced traders and investors. Use professional "
                    "terminology, include technical levels, and provide actionable insights."
                ),
                "user": (
                    "Generate professional market context for {asset_name} ({symbol}).\n\n"
                    "Price: ${price} (Change: {change_percent}%, ${change})\n"
                    "Volume: {volume} ({volume_ratio}x avg)\n"
                    "Market Cap: ${market_cap}\n"
                    "Beta: {beta}\n"
                    "52-week: ${week_52_low} - ${week_52_high}\n"
                    "Intraday: ${day_low} - ${day_high}\n\n"
                    "Provide comprehensive market context including price action, "
                    "volume profile, volatility considerations, and key support/resistance levels."
                ),
            },
            # QUANT - English
            "market_context_quant_en": {
                "system": (
                    "You are a quantitative analyst providing mathematical and statistical "
                    "market context. Include statistical measures, volatility metrics, and "
                    "quantitative indicators. Use precise terminology and cite specific metrics."
                ),
                "user": (
                    "Quantitative market analysis for {asset_name} ({symbol}).\n\n"
                    "Price: ${price} (μ_return: {mean_return}, σ: {std_dev})\n"
                    "Volume: {volume} (z-score: {volume_zscore})\n"
                    "Volatility: {volatility} (HV: {historical_vol}, IV: {implied_vol})\n"
                    "Returns: 1D: {return_1d}%, 5D: {return_5d}%, 20D: {return_20d}%\n"
                    "Sharpe: {sharpe_ratio}, Sortino: {sortino_ratio}\n\n"
                    "Provide statistical market context with quantitative metrics, "
                    "distribution characteristics, and risk-adjusted performance measures."
                ),
            },
        }

    def _get_technical_templates(self) -> Dict[str, Dict[str, str]]:
        """Technical analysis prompt templates"""
        return {
            # BEGINNER - English
            "technical_beginner_en": {
                "system": (
                    "You are teaching someone about technical analysis using simple language. "
                    "Explain what indicators mean without complex jargon. "
                    "Help them understand if the stock looks strong or weak."
                ),
                "user": (
                    "Explain the technical signals for {symbol} in simple terms.\n\n"
                    "RSI: {rsi} (Range: 0-100, above 70=overbought, below 30=oversold)\n"
                    "MACD: {macd_line} vs Signal: {macd_signal}\n"
                    "Moving Averages: 50-day ${ma_50}, 200-day ${ma_200}\n"
                    "Current Price: ${price}\n\n"
                    "In 2-3 sentences, explain what these indicators suggest about "
                    "the stock's momentum and trend."
                ),
            },
            # INTERMEDIATE - English
            "technical_intermediate_en": {
                "system": (
                    "You are a technical analyst providing indicator interpretation "
                    "for investors familiar with basic technical analysis. Use standard "
                    "terminology and provide clear buy/sell/neutral signals with context."
                ),
                "user": (
                    "Provide technical analysis summary for {symbol}.\n\n"
                    "Momentum Indicators:\n"
                    "- RSI(14): {rsi}\n"
                    "- MACD: {macd_line} (Signal: {macd_signal}, Histogram: {macd_hist})\n"
                    "- Stochastic: {stoch_k}%\n\n"
                    "Trend Indicators:\n"
                    "- Price: ${price}\n"
                    "- MA50: ${ma_50} (Price {ma_50_position})\n"
                    "- MA200: ${ma_200} (Price {ma_200_position})\n\n"
                    "Volatility:\n"
                    "- Bollinger Bands: ${bb_upper} / ${bb_middle} / ${bb_lower}\n"
                    "- ATR: {atr}\n\n"
                    "Synthesize these indicators into a cohesive technical outlook "
                    "covering momentum, trend, and volatility."
                ),
            },
            # ADVANCED - English
            "technical_advanced_en": {
                "system": (
                    "You are an experienced technical analyst providing professional-grade "
                    "technical analysis. Include pattern recognition, multiple timeframe analysis, "
                    "and confluence of indicators. Provide specific entry/exit considerations."
                ),
                "user": (
                    "Professional technical analysis for {symbol}.\n\n"
                    "{technical_data}\n\n"
                    "Analyze indicator confluence, identify key support/resistance levels, "
                    "discuss chart patterns, and provide actionable technical insights "
                    "with specific price levels and conditions."
                ),
            },
        }

    def _get_fundamental_templates(self) -> Dict[str, Dict[str, str]]:
        """Fundamental analysis prompt templates"""
        return {
            # BEGINNER - English
            "fundamental_beginner_en": {
                "system": (
                    "You are explaining company fundamentals to someone learning about "
                    "stock investing. Use simple comparisons and everyday language. "
                    "Help them understand if a company is financially healthy."
                ),
                "user": (
                    "Explain the fundamentals of {company_name} in simple terms.\n\n"
                    "Price-to-Earnings (P/E): {pe_ratio} (Industry average: {industry_pe})\n"
                    "Market Value: ${market_cap}\n"
                    "Revenue (last year): ${revenue}\n"
                    "Profit Margin: {profit_margin}%\n\n"
                    "In simple terms, explain what these numbers tell us about "
                    "whether the company is doing well financially."
                ),
            },
            # INTERMEDIATE - English
            "fundamental_intermediate_en": {
                "system": (
                    "You are a fundamental analyst providing valuation and financial "
                    "analysis for informed investors. Use standard financial metrics "
                    "and provide comparative context with industry and market."
                ),
                "user": (
                    "Fundamental analysis for {company_name} ({symbol}).\n\n"
                    "Valuation Metrics:\n"
                    "- P/E Ratio: {pe_ratio} (Sector: {sector_pe}, S&P 500: {sp500_pe})\n"
                    "- P/B Ratio: {pb_ratio}\n"
                    "- PEG Ratio: {peg_ratio}\n"
                    "- EV/EBITDA: {ev_ebitda}\n\n"
                    "Financial Health:\n"
                    "- Market Cap: ${market_cap}\n"
                    "- Revenue (TTM): ${revenue}\n"
                    "- Net Margin: {net_margin}%\n"
                    "- ROE: {roe}%\n"
                    "- Debt/Equity: {debt_equity}\n\n"
                    "Growth:\n"
                    "- EPS Growth: {eps_growth}%\n"
                    "- Revenue Growth: {revenue_growth}%\n\n"
                    "Provide a balanced fundamental assessment covering valuation, "
                    "financial health, and growth prospects."
                ),
            },
        }

    def _get_sentiment_templates(self) -> Dict[str, Dict[str, str]]:
        """Sentiment analysis prompt templates"""
        return {
            # INTERMEDIATE - English
            "sentiment_intermediate_en": {
                "system": (
                    "You are analyzing market sentiment from news and social media. "
                    "Synthesize sentiment data into clear insights about market perception "
                    "and potential impact on the stock."
                ),
                "user": (
                    "Sentiment analysis for {symbol}.\n\n"
                    "Overall Sentiment Score: {sentiment_score} (-1 to +1)\n"
                    "News Sentiment: {news_sentiment}\n"
                    "Social Media Sentiment: {social_sentiment}\n"
                    "Sentiment Trend: {sentiment_trend}\n\n"
                    "Recent News Headlines:\n{news_headlines}\n\n"
                    "Trending Topics:\n{trending_topics}\n\n"
                    "Summarize the market sentiment, key themes in coverage, "
                    "and potential impact on investor perception."
                ),
            },
        }

    def _get_risk_templates(self) -> Dict[str, Dict[str, str]]:
        """Risk analysis prompt templates"""
        return {
            # INTERMEDIATE - English
            "risk_intermediate_en": {
                "system": (
                    "You are a risk analyst explaining volatility and risk metrics. "
                    "Help investors understand the risk profile of the investment "
                    "and what it means for portfolio management."
                ),
                "user": (
                    "Risk analysis for {symbol}.\n\n"
                    "Volatility Metrics:\n"
                    "- Historical Volatility (30d): {volatility_30d}%\n"
                    "- Beta: {beta}\n"
                    "- Sharpe Ratio: {sharpe}\n"
                    "- Max Drawdown: {max_drawdown}%\n\n"
                    "Value at Risk (95% confidence):\n"
                    "- 1-day VaR: {var_1d}%\n"
                    "- 10-day VaR: {var_10d}%\n\n"
                    "Correlation with S&P 500: {sp500_correlation}\n\n"
                    "Explain the risk profile, what drives volatility, "
                    "and considerations for risk management."
                ),
            },
        }

    def _get_summary_templates(self) -> Dict[str, Dict[str, str]]:
        """Summary prompt templates"""
        return {
            # INTERMEDIATE - English
            "summary_intermediate_en": {
                "system": (
                    "You are synthesizing comprehensive analysis into an executive summary. "
                    "Distill key findings from technical, fundamental, and sentiment analysis "
                    "into clear, actionable insights."
                ),
                "user": (
                    "Create an executive summary for {symbol} based on this analysis:\n\n"
                    "{analysis_sections}\n\n"
                    "Synthesize the key findings into a concise summary (150-200 words) "
                    "that captures the overall picture, main opportunities/risks, "
                    "and primary considerations for investors."
                ),
            },
        }

    def get_language_name(self, language: Language) -> str:
        """Get human-readable language name"""
        language_names = {
            Language.ENGLISH: "English",
            Language.SPANISH: "Spanish",
            Language.FRENCH: "French",
            Language.JAPANESE: "Japanese",
            Language.CHINESE: "Chinese",
            Language.GERMAN: "German",
            Language.ITALIAN: "Italian",
            Language.PORTUGUESE: "Portuguese",
        }
        return language_names.get(language, "English")


# Global instance
prompt_library = PromptTemplateLibrary()
