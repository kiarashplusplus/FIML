"""
Narrative Template Library

Provides fallback templates for narrative generation when Azure OpenAI
is unavailable. Supports multiple languages and variable substitution
using Jinja2.
"""

from typing import Any, Dict, Optional

from jinja2 import Template

from fiml.core.logging import get_logger
from fiml.narrative.models import Language

logger = get_logger(__name__)


class TemplateLibrary:
    """Library of narrative templates for fallback scenarios"""

    def __init__(self):
        """Initialize template library"""
        self.templates = self._load_templates()
        logger.info("Template library initialized")

    def _load_templates(self) -> Dict[str, Dict[str, Template]]:
        """Load all narrative templates"""
        return {
            "price_movement": self._price_movement_templates(),
            "volume_analysis": self._volume_analysis_templates(),
            "technical_summary": self._technical_summary_templates(),
            "fundamental_summary": self._fundamental_summary_templates(),
            "risk_assessment": self._risk_assessment_templates(),
        }

    def _price_movement_templates(self) -> Dict[str, Template]:
        """Price movement templates by language"""
        return {
            "en": Template(
                "{{ symbol }} is trading at ${{ price }}, {{ direction }} {{ change_pct }}% "
                "in the last 24 hours. The {{ magnitude }} price {{ movement }} comes on "
                "{{ volume_status }} volume of {{ volume }} shares. "
                "Current price is {{ position_52w }} within its 52-week range. "
                "This is not financial advice. FIML provides data analysis only."
            ),
            "es": Template(
                "{{ symbol }} está cotizando a ${{ price }}, {{ direction }} {{ change_pct }}% "
                "en las últimas 24 horas. El {{ magnitude }} {{ movement }} de precio ocurre con "
                "un volumen {{ volume_status }} de {{ volume }} acciones. "
                "El precio actual está {{ position_52w }} dentro de su rango de 52 semanas. "
                "Esto no es asesoramiento financiero. FIML solo proporciona análisis de datos."
            ),
            "fr": Template(
                "{{ symbol }} se négocie à ${{ price }}, {{ direction }} {{ change_pct }}% "
                "au cours des dernières 24 heures. Le {{ magnitude }} {{ movement }} de prix "
                "se produit sur un volume {{ volume_status }} de {{ volume }} actions. "
                "Le prix actuel est {{ position_52w }} dans sa fourchette de 52 semaines. "
                "Ce n'est pas un conseil financier. FIML fournit uniquement une analyse de données."
            ),
            "ja": Template(
                "{{ symbol }}は${{ price }}で取引されており、過去24時間で{{ direction }}{{ change_pct }}%です。"
                "{{ magnitude }}価格{{ movement }}は{{ volume_status }}の{{ volume }}株の出来高で発生しています。"
                "現在の価格は52週間の範囲内で{{ position_52w }}です。"
                "これは金融アドバイスではありません。FIMLはデータ分析のみを提供します。"
            ),
            "zh": Template(
                "{{ symbol }}目前交易价格为${{ price }}，在过去24小时内{{ direction }}{{ change_pct }}%。"
                "{{ magnitude }}的价格{{ movement }}伴随着{{ volume_status }}的{{ volume }}股成交量。"
                "当前价格在52周范围内{{ position_52w }}。"
                "这不是财务建议。FIML仅提供数据分析。"
            ),
        }

    def _volume_analysis_templates(self) -> Dict[str, Template]:
        """Volume analysis templates by language"""
        return {
            "en": Template(
                "Trading volume is {{ volume_status }} at {{ volume }}, representing {{ ratio }}x "
                "the 30-day average volume of {{ avg_volume }}. {{ volume_interpretation }} "
                "This {{ above_below }} average activity suggests {{ market_interest }}. "
                "This is not financial advice. FIML provides data analysis only."
            ),
            "es": Template(
                "El volumen de negociación está {{ volume_status }} en {{ volume }}, "
                "representando {{ ratio }}x el volumen promedio de 30 días de {{ avg_volume }}. "
                "{{ volume_interpretation }} Esta actividad {{ above_below }} del promedio sugiere {{ market_interest }}. "
                "Esto no es asesoramiento financiero."
            ),
            "fr": Template(
                "Le volume de négociation est {{ volume_status }} à {{ volume }}, "
                "représentant {{ ratio }}x le volume moyen sur 30 jours de {{ avg_volume }}. "
                "{{ volume_interpretation }} Cette activité {{ above_below }} la moyenne suggère {{ market_interest }}. "
                "Ce n'est pas un conseil financier."
            ),
            "ja": Template(
                "取引量は{{ volume }}で{{ volume_status }}、30日平均の{{ avg_volume }}の{{ ratio }}倍です。"
                "{{ volume_interpretation }}この平均{{ above_below }}の活動は{{ market_interest }}を示唆しています。"
                "これは金融アドバイスではありません。"
            ),
            "zh": Template(
                "交易量{{ volume_status }}为{{ volume }}，是30天平均量{{ avg_volume }}的{{ ratio }}倍。"
                "{{ volume_interpretation }}这个{{ above_below }}平均水平的活动表明{{ market_interest }}。"
                "这不是财务建议。"
            ),
        }

    def _technical_summary_templates(self) -> Dict[str, Template]:
        """Technical analysis summary templates"""
        return {
            "en": Template(
                "Technical indicators show: RSI at {{ rsi }} indicates {{ rsi_signal }}. "
                "MACD shows {{ macd_signal }} with histogram at {{ macd_histogram }}. "
                "Price is {{ ma_position }} moving averages (MA50: ${{ ma50 }}, MA200: ${{ ma200 }}). "
                "Bollinger Bands suggest {{ bb_signal }}. Overall technical outlook: {{ outlook }}. "
                "This is technical analysis, not investment advice."
            ),
            "es": Template(
                "Los indicadores técnicos muestran: RSI en {{ rsi }} indica {{ rsi_signal }}. "
                "MACD muestra {{ macd_signal }} con histograma en {{ macd_histogram }}. "
                "El precio está {{ ma_position }} las medias móviles. "
                "Las Bandas de Bollinger sugieren {{ bb_signal }}. Perspectiva técnica: {{ outlook }}. "
                "Esto es análisis técnico, no asesoramiento de inversión."
            ),
            "fr": Template(
                "Les indicateurs techniques montrent: RSI à {{ rsi }} indique {{ rsi_signal }}. "
                "MACD montre {{ macd_signal }} avec histogramme à {{ macd_histogram }}. "
                "Le prix est {{ ma_position }} moyennes mobiles. "
                "Les Bandes de Bollinger suggèrent {{ bb_signal }}. Perspectives techniques: {{ outlook }}. "
                "C'est une analyse technique, pas un conseil d'investissement."
            ),
            "ja": Template(
                "テクニカル指標：RSI {{ rsi }}は{{ rsi_signal }}を示しています。"
                "MACDは{{ macd_signal }}を示し、ヒストグラムは{{ macd_histogram }}です。"
                "価格は移動平均{{ ma_position }}です。"
                "ボリンジャーバンドは{{ bb_signal }}を示唆しています。全体的な見通し：{{ outlook }}。"
                "これは投資アドバイスではありません。"
            ),
            "zh": Template(
                "技术指标显示：RSI为{{ rsi }}表明{{ rsi_signal }}。"
                "MACD显示{{ macd_signal }}，柱状图为{{ macd_histogram }}。"
                "价格{{ ma_position }}移动平均线。"
                "布林带表明{{ bb_signal }}。总体技术前景：{{ outlook }}。"
                "这是技术分析，不是投资建议。"
            ),
        }

    def _fundamental_summary_templates(self) -> Dict[str, Template]:
        """Fundamental analysis summary templates"""
        return {
            "en": Template(
                "{{ symbol }} fundamentals: P/E ratio of {{ pe }} is {{ pe_assessment }} "
                "compared to industry average of {{ industry_pe }}. "
                "Market cap: ${{ market_cap }}. Revenue growth: {{ revenue_growth }}%. "
                "Profit margin: {{ profit_margin }}%. ROE: {{ roe }}%. "
                "Debt-to-equity: {{ debt_equity }}. "
                "Overall valuation: {{ valuation }}. "
                "This is fundamental analysis, not investment advice."
            ),
            "es": Template(
                "Fundamentos de {{ symbol }}: P/E de {{ pe }} está {{ pe_assessment }} "
                "comparado con el promedio de la industria de {{ industry_pe }}. "
                "Capitalización: ${{ market_cap }}. Crecimiento de ingresos: {{ revenue_growth }}%. "
                "Esto es análisis fundamental, no asesoramiento de inversión."
            ),
            "fr": Template(
                "Fondamentaux de {{ symbol }}: Ratio P/E de {{ pe }} est {{ pe_assessment }} "
                "par rapport à la moyenne du secteur de {{ industry_pe }}. "
                "Capitalisation: ${{ market_cap }}. Croissance des revenus: {{ revenue_growth }}%. "
                "C'est une analyse fondamentale, pas un conseil d'investissement."
            ),
            "ja": Template(
                "{{ symbol }}のファンダメンタルズ：P/E比{{ pe }}は業界平均{{ industry_pe }}と比較して{{ pe_assessment }}です。"
                "時価総額：${{ market_cap }}。収益成長率：{{ revenue_growth }}%。"
                "これは投資アドバイスではありません。"
            ),
            "zh": Template(
                "{{ symbol }}基本面：市盈率{{ pe }}相比行业平均{{ industry_pe }}{{ pe_assessment }}。"
                "市值：${{ market_cap }}。收入增长：{{ revenue_growth }}%。"
                "这不是投资建议。"
            ),
        }

    def _risk_assessment_templates(self) -> Dict[str, Template]:
        """Risk assessment templates"""
        return {
            "en": Template(
                "Risk Assessment: Historical volatility of {{ volatility }}% indicates {{ risk_level }} risk. "
                "Beta of {{ beta }} suggests {{ beta_assessment }} compared to market. "
                "Value at Risk (95%): {{ var }}%. Maximum drawdown: {{ max_dd }}%. "
                "{{ risk_warnings }} "
                "Past volatility does not guarantee future risk levels. This is not investment advice."
            ),
            "es": Template(
                "Evaluación de riesgo: Volatilidad histórica de {{ volatility }}% indica riesgo {{ risk_level }}. "
                "Beta de {{ beta }} sugiere {{ beta_assessment }} comparado con el mercado. "
                "{{ risk_warnings }} "
                "La volatilidad pasada no garantiza niveles futuros de riesgo."
            ),
            "fr": Template(
                "Évaluation des risques: Volatilité historique de {{ volatility }}% indique un risque {{ risk_level }}. "
                "Bêta de {{ beta }} suggère {{ beta_assessment }} par rapport au marché. "
                "{{ risk_warnings }} "
                "La volatilité passée ne garantit pas les niveaux de risque futurs."
            ),
            "ja": Template(
                "リスク評価：過去のボラティリティ{{ volatility }}%は{{ risk_level }}リスクを示しています。"
                "ベータ{{ beta }}は市場と比較して{{ beta_assessment }}を示唆しています。"
                "{{ risk_warnings }} "
                "過去のボラティリティは将来のリスクを保証しません。"
            ),
            "zh": Template(
                "风险评估：历史波动率{{ volatility }}%表明{{ risk_level }}风险。"
                "贝塔值{{ beta }}相比市场{{ beta_assessment }}。"
                "{{ risk_warnings }} "
                "过去的波动性不能保证未来的风险水平。"
            ),
        }

    def render_template(
        self,
        template_type: str,
        language: Language,
        context: Dict[str, Any],
    ) -> str:
        """
        Render a template with given context

        Args:
            template_type: Type of template (price_movement, volume_analysis, etc.)
            language: Target language
            context: Variables to substitute in template

        Returns:
            Rendered template text

        Example:
            >>> library = TemplateLibrary()
            >>> text = library.render_template(
            ...     "price_movement",
            ...     Language.ENGLISH,
            ...     {"symbol": "AAPL", "price": 175.50, "change_pct": 2.48}
            ... )
        """
        try:
            templates = self.templates.get(template_type, {})
            template = templates.get(language.value)

            if not template:
                # Fallback to English
                template = templates.get("en")
                if not template:
                    raise ValueError(f"No template found for {template_type}")

            # Enrich context with computed values
            enriched_context = self._enrich_context(template_type, context)

            rendered = template.render(**enriched_context)
            logger.debug(
                "Template rendered",
                template_type=template_type,
                language=language.value,
            )
            return rendered

        except Exception as e:
            logger.error(
                f"Failed to render template: {e}",
                template_type=template_type,
                language=language.value,
            )
            return self._emergency_fallback(context)

    def _enrich_context(
        self, template_type: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich context with computed values"""
        enriched = context.copy()

        if template_type == "price_movement":
            change_pct = context.get("change_pct", 0)
            enriched["direction"] = "up" if change_pct > 0 else "down"
            enriched["movement"] = "gain" if change_pct > 0 else "decline"

            if abs(change_pct) > 5:
                enriched["magnitude"] = "significant"
            elif abs(change_pct) > 2:
                enriched["magnitude"] = "moderate"
            else:
                enriched["magnitude"] = "modest"

            # Volume status
            volume = context.get("volume", 0)
            avg_volume = context.get("avg_volume", volume)
            ratio = volume / avg_volume if avg_volume > 0 else 1.0
            enriched["volume_status"] = (
                "high" if ratio > 1.5 else "normal" if ratio > 0.7 else "light"
            )

            # 52-week position
            price = context.get("price", 0)
            week_52_high = context.get("week_52_high", price)
            week_52_low = context.get("week_52_low", price)
            if week_52_high > week_52_low:
                pct_range = (price - week_52_low) / (week_52_high - week_52_low) * 100
                if pct_range > 80:
                    enriched["position_52w"] = "near the upper end"
                elif pct_range > 60:
                    enriched["position_52w"] = "in the upper half"
                elif pct_range > 40:
                    enriched["position_52w"] = "in the middle"
                elif pct_range > 20:
                    enriched["position_52w"] = "in the lower half"
                else:
                    enriched["position_52w"] = "near the lower end"
            else:
                enriched["position_52w"] = "within range"

        elif template_type == "volume_analysis":
            volume = context.get("volume", 0)
            avg_volume = context.get("avg_volume", volume)
            ratio = volume / avg_volume if avg_volume > 0 else 1.0
            enriched["ratio"] = f"{ratio:.1f}"

            if ratio > 2:
                enriched["volume_status"] = "exceptionally high"
                enriched["above_below"] = "above"
                enriched["volume_interpretation"] = "This spike in volume suggests significant market interest."
                enriched["market_interest"] = "heightened market activity"
            elif ratio > 1.5:
                enriched["volume_status"] = "elevated"
                enriched["above_below"] = "above"
                enriched["volume_interpretation"] = "Volume is notably higher than usual."
                enriched["market_interest"] = "increased market participation"
            elif ratio < 0.5:
                enriched["volume_status"] = "light"
                enriched["above_below"] = "below"
                enriched["volume_interpretation"] = "Trading activity is subdued."
                enriched["market_interest"] = "reduced market interest"
            else:
                enriched["volume_status"] = "normal"
                enriched["above_below"] = "near"
                enriched["volume_interpretation"] = "Volume is within normal range."
                enriched["market_interest"] = "typical market participation"

        elif template_type == "technical_summary":
            rsi = context.get("rsi", 50)
            if rsi > 70:
                enriched["rsi_signal"] = "overbought conditions"
            elif rsi < 30:
                enriched["rsi_signal"] = "oversold conditions"
            else:
                enriched["rsi_signal"] = "neutral momentum"

            macd_hist = context.get("macd_histogram", 0)
            if macd_hist > 0:
                enriched["macd_signal"] = "bullish momentum"
            else:
                enriched["macd_signal"] = "bearish momentum"

            price = context.get("current_price", 0)
            ma50 = context.get("ma50", 0)
            ma200 = context.get("ma200", 0)

            if price > ma50 and price > ma200:
                enriched["ma_position"] = "above both"
                enriched["outlook"] = "bullish"
            elif price < ma50 and price < ma200:
                enriched["ma_position"] = "below both"
                enriched["outlook"] = "bearish"
            else:
                enriched["ma_position"] = "between"
                enriched["outlook"] = "mixed"

            bb_upper = context.get("bb_upper", 0)
            bb_lower = context.get("bb_lower", 0)
            if price > bb_upper:
                enriched["bb_signal"] = "overbought conditions"
            elif price < bb_lower:
                enriched["bb_signal"] = "oversold conditions"
            else:
                enriched["bb_signal"] = "normal trading range"

        elif template_type == "fundamental_summary":
            pe = context.get("pe", 0)
            industry_pe = context.get("industry_pe", pe)

            if pe > industry_pe * 1.2:
                enriched["pe_assessment"] = "higher than average"
                enriched["valuation"] = "potentially overvalued relative to peers"
            elif pe < industry_pe * 0.8:
                enriched["pe_assessment"] = "lower than average"
                enriched["valuation"] = "potentially undervalued relative to peers"
            else:
                enriched["pe_assessment"] = "in line with"
                enriched["valuation"] = "fairly valued relative to industry"

        elif template_type == "risk_assessment":
            volatility = context.get("volatility", 0)
            if volatility > 0.4:
                enriched["risk_level"] = "high"
                enriched["risk_warnings"] = "This asset shows high volatility and may not be suitable for risk-averse investors."
            elif volatility > 0.25:
                enriched["risk_level"] = "moderate to high"
                enriched["risk_warnings"] = "Moderate price swings can be expected."
            elif volatility > 0.15:
                enriched["risk_level"] = "moderate"
                enriched["risk_warnings"] = "Typical market volatility observed."
            else:
                enriched["risk_level"] = "low to moderate"
                enriched["risk_warnings"] = "Relatively stable price action historically."

            beta = context.get("beta", 1.0)
            if beta > 1.2:
                enriched["beta_assessment"] = "higher volatility than the market"
            elif beta < 0.8:
                enriched["beta_assessment"] = "lower volatility than the market"
            else:
                enriched["beta_assessment"] = "similar volatility to the market"

        return enriched

    def _emergency_fallback(self, context: Dict[str, Any]) -> str:
        """Emergency fallback when all template rendering fails"""
        symbol = context.get("symbol", "Asset")
        return (
            f"Analysis for {symbol} is currently available. "
            f"This is not financial advice. FIML provides data analysis only."
        )


# Global template library instance
template_library = TemplateLibrary()
