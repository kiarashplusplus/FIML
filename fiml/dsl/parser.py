"""
FK-DSL Parser using Lark Grammar

Implements the Financial Knowledge DSL (FK-DSL) parser as specified in Blueprint.md.
Supports comprehensive financial queries including:
- EVALUATE: Single asset analysis with multiple metrics
- COMPARE: Cross-asset comparison on selected metrics
- MACRO: Macroeconomic indicator regression/correlation analysis
- CORRELATE: Correlation analysis between assets
- SCAN: Market screening with conditions
- FIND, ANALYZE, TRACK, GET: Legacy query types for backward compatibility
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from lark import Lark, Token, Transformer, v_args

from fiml.core.exceptions import FKDSLParseError
from fiml.core.logging import get_logger

logger = get_logger(__name__)


# Data classes for structured query representation
@dataclass
class TimeframeSpec:
    """Represents a timeframe specification like 30d, 7h, 4w"""

    value: int
    unit: str  # d=day, h=hour, w=week, m=month, y=year

    def to_days(self) -> float:
        """Convert to approximate days"""
        unit_map = {"d": 1, "h": 1 / 24, "w": 7, "m": 30, "y": 365}
        return self.value * unit_map.get(self.unit, 1)

    def __str__(self) -> str:
        return f"{self.value}{self.unit}"


@dataclass
class MetricSpec:
    """Represents a metric specification"""

    name: str
    category: str  # price, technical, fundamental, sentiment, crypto
    params: List[Any] = field(default_factory=list)
    timeframe: Optional[TimeframeSpec] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"name": self.name, "category": self.category}
        if self.params:
            result["params"] = self.params
        if self.timeframe:
            result["timeframe"] = str(self.timeframe)
        return result


@dataclass
class AssetSpec:
    """Represents an asset specification"""

    symbol: str
    asset_type: str = "symbol"  # symbol, sector, market
    market: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"symbol": self.symbol, "type": self.asset_type}
        if self.market:
            result["market"] = self.market
        return result


@dataclass
class ConditionSpec:
    """Represents a condition in a scan query"""

    metric: Union[str, MetricSpec]
    operator: str
    value: Any
    second_value: Optional[Any] = None  # For BETWEEN conditions

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "metric": self.metric.to_dict()
            if isinstance(self.metric, MetricSpec)
            else self.metric,
            "operator": self.operator,
            "value": self.value,
        }
        if self.second_value is not None:
            result["second_value"] = self.second_value
        return result


# FK-DSL Grammar based on BLUEPRINT.md Section 4
# Supports: EVALUATE, COMPARE, MACRO, CORRELATE, SCAN
# Plus legacy: FIND, ANALYZE, TRACK, GET
FK_DSL_GRAMMAR = r"""
    ?start: statement (";" statement)*

    // Query types - order matters for ambiguous parsing
    // Put compare_stmt BEFORE compare_query since compare_stmt has the distinct "vs" keyword
    statement: evaluate_stmt
             | compare_stmt
             | compare_query
             | macro_stmt
             | correlate_stmt
             | scan_stmt
             | find_query
             | analyze_query
             | track_query
             | get_query

    // EVALUATE TSLA: PRICE, VOLATILITY(30d), CORRELATE(BTC, SPY), TECHNICAL(RSI, MACD)
    evaluate_stmt: "EVALUATE" asset ":" metric_list

    // COMPARE BTC vs ETH vs SOL ON: VOLUME(7d), LIQUIDITY, MOMENTUM (new blueprint style)
    compare_stmt: "COMPARE" asset (VS asset)+ "ON:" metric_list

    // MACRO: US10Y, CPI, VIX, DXY → REGRESSION ON SPY
    macro_stmt: "MACRO:" indicator_list ("→" | "->") analysis_type "ON" asset

    // CORRELATE TSLA WITH BTC, SPY WINDOW 90d
    correlate_stmt: "CORRELATE" asset "WITH" asset_list ("WINDOW" timeframe)?

    // SCAN NASDAQ WHERE VOLUME > AVG_VOLUME(30d) * 2 AND PRICE_CHANGE(1d) > 5%
    scan_stmt: "SCAN" market "WHERE" condition_list

    // Legacy query types for backward compatibility
    find_query: "FIND" asset_spec "WITH" condition_list
    analyze_query: "ANALYZE" asset_spec "FOR" legacy_analysis_type
    compare_query: "COMPARE" asset_spec_list "BY" metric_list
    track_query: "TRACK" asset_spec "WHEN" condition_list
    get_query: "GET" data_request

    // Assets - use CNAME consistently for all asset references
    asset: CNAME
    asset_list: asset ("," asset)*

    asset_spec: asset_filter ("IN" market)?
    asset_spec_list: asset_spec ("," asset_spec)*
    asset_filter: symbol
                | sector
                | "TOP" INT "BY" metric
                | "BOTTOM" INT "BY" metric
                | "ALL"

    symbol: CNAME
    sector: "SECTOR" CNAME
    market: CNAME

    // Metrics (for EVALUATE and COMPARE)
    metric_list: metric ("," metric)*

    metric: simple_metric
          | metric_with_params
          | compound_metric

    simple_metric: "PRICE" -> price_metric
                 | "VOLUME" -> volume_metric
                 | "MARKETCAP" -> marketcap_metric
                 | "PE" -> pe_metric
                 | "BETA" -> beta_metric
                 | "RSI" -> rsi_metric
                 | "MACD" -> macd_metric
                 | "MOMENTUM" -> momentum_metric
                 | "LIQUIDITY" -> liquidity_metric
                 | "SENTIMENT" -> sentiment_metric
                 | "CHANGE" -> change_metric
                 | "EPS" -> eps_metric
                 | "ROE" -> roe_metric
                 | "DEBT" -> debt_metric
                 | "REVENUE" -> revenue_metric
                 | "GROWTH" -> growth_metric
                 | "STOCH" -> stoch_metric
                 | "ATR" -> atr_metric
                 | "BUZZ" -> buzz_metric
                 | "NEWS_SCORE" -> news_score_metric

    metric_with_params: METRIC_NAME "(" params ")"

    compound_metric: "TECHNICAL" "(" indicator_params ")" -> technical_compound
                   | "CORRELATE" "(" asset_list ")" -> correlate_compound
                   | "VOLATILITY" "(" timeframe ")" -> volatility_compound
                   | "VOLUME" "(" timeframe ")" -> volume_with_timeframe
                   | "MOMENTUM" "(" timeframe ")" -> momentum_with_timeframe
                   | "PRICE_CHANGE" "(" timeframe ")" -> price_change_compound
                   | "AVG_VOLUME" "(" timeframe ")" -> avg_volume_compound
                   | "SMA" INT -> sma_metric
                   | "EMA" INT -> ema_metric

    indicator_params: indicator_name ("," indicator_name)*
    indicator_name: CNAME

    params: param ("," param)*
    param: NUMBER | timeframe | ESCAPED_STRING | asset

    timeframe: NUMBER TIMEUNIT
    TIMEUNIT: "d" | "h" | "w" | "m" | "y"

    // Macro indicators
    indicator_list: indicator ("," indicator)*
    indicator: MACRO_INDICATOR
    MACRO_INDICATOR: "US10Y" | "CPI" | "VIX" | "DXY" | "UNEMPLOYMENT" | "GDP" | "FED_RATE"

    // Analysis types for MACRO
    analysis_type: ANALYSIS_KEYWORD
    ANALYSIS_KEYWORD: "REGRESSION" | "CORRELATION" | "CAUSALITY" | "IMPACT"

    // Legacy analysis types
    legacy_analysis_type: LEGACY_ANALYSIS_KEYWORD
    LEGACY_ANALYSIS_KEYWORD: "TECHNICALS"
                           | "FUNDAMENTALS"
                           | "SENTIMENT"
                           | "CORRELATIONS"
                        | "RISK"

    // Conditions for SCAN and legacy queries
    condition_list: condition ("AND" condition)*

    condition: metric COMPARATOR value
             | metric COMPARATOR metric "*" NUMBER
             | metric "BETWEEN" value "AND" value
             | metric "ABOVE" metric
             | metric "BELOW" metric
             | "TREND" "IS" trend_type
             | "SIGNAL" "IS" signal_type

    COMPARATOR: ">=" | "<=" | "!=" | ">" | "<" | "="

    value: NUMBER "%"? | ESCAPED_STRING | metric

    trend_type: "BULLISH" | "BEARISH" | "NEUTRAL"
    signal_type: "BUY" | "SELL" | "HOLD"

    // Data request for GET queries
    data_request: "PRICE" "FOR" symbol
                | "OHLCV" "FOR" symbol legacy_timeframe?
                | "NEWS" "FOR" symbol
                | "FUNDAMENTALS" "FOR" symbol

    legacy_timeframe: "1m" | "5m" | "15m" | "1h" | "4h" | "1d" | "1w"

    // Tokens
    METRIC_NAME: /[A-Z_]+/
    VS: "vs"i  // Case-insensitive vs keyword

    %import common.CNAME
    %import common.INT
    %import common.NUMBER
    %import common.ESCAPED_STRING
    %import common.WS
    %ignore WS
"""


@v_args(inline=True)
class FKDSLTransformer(Transformer):
    """
    Transform parsed FK-DSL tree into structured execution plan.

    Handles both new Blueprint-spec queries (EVALUATE, COMPARE, MACRO, CORRELATE, SCAN)
    and legacy queries (FIND, ANALYZE, TRACK, GET) for backward compatibility.
    """

    # ================== Statement Handlers ==================

    def start(self, *statements: Any) -> Dict[str, Any]:
        """Handle multiple statements separated by semicolons"""
        if len(statements) == 1:
            return statements[0]
        return {"type": "MULTI", "statements": list(statements)}

    def statement(self, stmt: Any) -> Any:
        """Pass through statement to its specific handler"""
        return stmt

    # ================== New Blueprint Query Types ==================

    def evaluate_stmt(self, asset: Any, metrics: Any) -> Dict[str, Any]:
        """
        Handle EVALUATE query: EVALUATE TSLA: PRICE, VOLATILITY(30d)

        Returns structured evaluation request with asset and metrics.
        """
        return {
            "type": "EVALUATE",
            "asset": self._to_asset_dict(asset),
            "metrics": metrics if isinstance(metrics, list) else [metrics],
        }

    def compare_stmt(self, *args: Any) -> Dict[str, Any]:
        """
        Handle COMPARE query: COMPARE BTC vs ETH vs SOL ON: VOLUME(7d), LIQUIDITY

        Returns structured comparison with assets and metrics.
        """
        # Last argument is the metric list, all preceding are assets
        # Filter out VS tokens (keyword separators)
        metrics = args[-1]
        assets = []
        for a in args[:-1]:
            # Skip VS tokens
            if hasattr(a, 'type') and str(a).lower() == 'vs':
                continue
            assets.append(self._to_asset_dict(a))
        return {
            "type": "COMPARE",
            "assets": assets,
            "metrics": metrics if isinstance(metrics, list) else [metrics],
        }

    def macro_stmt(
        self, indicators: Any, analysis_type: Any, target_asset: Any
    ) -> Dict[str, Any]:
        """
        Handle MACRO query: MACRO: US10Y, CPI, VIX → REGRESSION ON SPY

        Returns structured macro analysis request.
        """
        return {
            "type": "MACRO",
            "indicators": indicators if isinstance(indicators, list) else [indicators],
            "analysis": str(analysis_type).lower(),
            "target": self._to_asset_dict(target_asset),
        }

    def correlate_stmt(self, *args: Any) -> Dict[str, Any]:
        """
        Handle CORRELATE query: CORRELATE TSLA WITH BTC, SPY WINDOW 90d

        Returns structured correlation analysis request.
        """
        primary_asset = args[0]
        correlation_assets = args[1]
        window = args[2] if len(args) > 2 else None

        return {
            "type": "CORRELATE",
            "asset": self._to_asset_dict(primary_asset),
            "with_assets": (
                [self._to_asset_dict(a) for a in correlation_assets]
                if isinstance(correlation_assets, list)
                else [self._to_asset_dict(correlation_assets)]
            ),
            "window": window,
        }

    def scan_stmt(self, market: Any, conditions: Any) -> Dict[str, Any]:
        """
        Handle SCAN query: SCAN NASDAQ WHERE VOLUME > AVG_VOLUME(30d) * 2

        Returns structured market scan request.
        """
        return {
            "type": "SCAN",
            "market": str(market),
            "conditions": conditions if isinstance(conditions, list) else [conditions],
        }

    # ================== Legacy Query Types ==================

    def find_query(self, asset_spec: Any, condition_list: Any) -> Dict[str, Any]:
        """Handle legacy FIND query"""
        return {"type": "FIND", "args": [asset_spec, condition_list]}

    def analyze_query(self, asset_spec: Any, analysis_type: Any) -> Dict[str, Any]:
        """Handle legacy ANALYZE query"""
        return {"type": "ANALYZE", "args": [asset_spec, analysis_type]}

    def compare_query(self, asset_list: Any, metric_list: Any) -> Dict[str, Any]:
        """Handle legacy COMPARE query with BY syntax"""
        return {"type": "COMPARE", "args": [asset_list, metric_list]}

    def track_query(self, asset_spec: Any, condition_list: Any) -> Dict[str, Any]:
        """Handle legacy TRACK query"""
        return {"type": "TRACK", "args": [asset_spec, condition_list]}

    def get_query(self, data_request: Any) -> Dict[str, Any]:
        """Handle legacy GET query"""
        return {"type": "GET", "args": [data_request]}

    # ================== Asset Handlers ==================

    def asset(self, symbol: Token) -> str:
        """Handle simple asset symbol"""
        return str(symbol)

    def asset_list(self, *assets: Any) -> List[Any]:
        """Handle list of assets"""
        return list(assets)

    def asset_spec_list(self, *asset_specs: Any) -> List[Any]:
        """Handle list of asset specifications"""
        return list(asset_specs)

    def asset_spec(self, asset_filter: Any, market: Any = None) -> Dict[str, Any]:
        """Handle asset specification with optional market"""
        return {"filter": asset_filter, "market": str(market) if market else None}

    def asset_filter(self, *args: Any) -> Any:
        """Handle asset filter - could be symbol, sector, top/bottom, or all"""
        if args:
            return args[0]
        return None

    def symbol(self, name: Token) -> Dict[str, Any]:
        """Handle symbol reference"""
        return {"type": "symbol", "value": str(name)}

    def sector(self, name: Token) -> Dict[str, Any]:
        """Handle sector reference"""
        return {"type": "sector", "value": str(name)}

    def market(self, name: Token) -> str:
        """Handle market reference"""
        return str(name)

    # ================== Metric Handlers ==================

    def metric_list(self, *metrics: Any) -> List[Dict[str, Any]]:
        """Handle list of metrics"""
        return list(metrics)

    def metric(self, m: Any) -> Any:
        """Pass through metric"""
        return m

    def simple_metric(self, m: Any) -> Any:
        """Pass through simple metric"""
        return m

    # Simple metrics - price category
    def price_metric(self) -> Dict[str, str]:
        return {"category": "price", "name": "price"}

    def volume_metric(self) -> Dict[str, str]:
        return {"category": "price", "name": "volume"}

    def marketcap_metric(self) -> Dict[str, str]:
        return {"category": "price", "name": "marketcap"}

    def change_metric(self) -> Dict[str, str]:
        return {"category": "price", "name": "change"}

    # Fundamental metrics
    def pe_metric(self) -> Dict[str, str]:
        return {"category": "fundamental", "name": "pe"}

    def eps_metric(self) -> Dict[str, str]:
        return {"category": "fundamental", "name": "eps"}

    def roe_metric(self) -> Dict[str, str]:
        return {"category": "fundamental", "name": "roe"}

    def debt_metric(self) -> Dict[str, str]:
        return {"category": "fundamental", "name": "debt"}

    def revenue_metric(self) -> Dict[str, str]:
        return {"category": "fundamental", "name": "revenue"}

    def growth_metric(self) -> Dict[str, str]:
        return {"category": "fundamental", "name": "growth"}

    def beta_metric(self) -> Dict[str, str]:
        return {"category": "fundamental", "name": "beta"}

    # Technical metrics
    def rsi_metric(self) -> Dict[str, str]:
        return {"category": "technical", "name": "rsi"}

    def macd_metric(self) -> Dict[str, str]:
        return {"category": "technical", "name": "macd"}

    def momentum_metric(self) -> Dict[str, str]:
        return {"category": "technical", "name": "momentum"}

    def stoch_metric(self) -> Dict[str, str]:
        return {"category": "technical", "name": "stoch"}

    def atr_metric(self) -> Dict[str, str]:
        return {"category": "technical", "name": "atr"}

    def sma_metric(self, period: Token) -> Dict[str, Any]:
        return {"category": "technical", "name": "sma", "period": int(period)}

    def ema_metric(self, period: Token) -> Dict[str, Any]:
        return {"category": "technical", "name": "ema", "period": int(period)}

    # Sentiment metrics
    def sentiment_metric(self) -> Dict[str, str]:
        return {"category": "sentiment", "name": "sentiment"}

    def buzz_metric(self) -> Dict[str, str]:
        return {"category": "sentiment", "name": "buzz"}

    def news_score_metric(self) -> Dict[str, str]:
        return {"category": "sentiment", "name": "news_score"}

    # Special metrics
    def liquidity_metric(self) -> Dict[str, str]:
        return {"category": "market", "name": "liquidity"}

    # ================== Compound Metric Handlers ==================

    def metric_with_params(self, name: Token, params: Any) -> Dict[str, Any]:
        """Handle metrics with parameters like VOLATILITY(30d)"""
        return {
            "category": "compound",
            "name": str(name).lower(),
            "params": params if isinstance(params, list) else [params],
        }

    def technical_compound(self, indicators: Any) -> Dict[str, Any]:
        """Handle TECHNICAL(RSI, MACD, BOLLINGER)"""
        return {
            "category": "technical",
            "name": "technical",
            "indicators": indicators if isinstance(indicators, list) else [indicators],
        }

    def correlate_compound(self, assets: Any) -> Dict[str, Any]:
        """Handle CORRELATE(BTC, SPY)"""
        return {
            "category": "analysis",
            "name": "correlate",
            "assets": [self._to_asset_dict(a) for a in assets]
            if isinstance(assets, list)
            else [self._to_asset_dict(assets)],
        }

    def volatility_compound(self, timeframe: Any) -> Dict[str, Any]:
        """Handle VOLATILITY(30d)"""
        return {
            "category": "technical",
            "name": "volatility",
            "timeframe": timeframe,
        }

    def volume_with_timeframe(self, timeframe: Any) -> Dict[str, Any]:
        """Handle VOLUME(7d)"""
        return {
            "category": "price",
            "name": "volume",
            "timeframe": timeframe,
        }

    def momentum_with_timeframe(self, timeframe: Any) -> Dict[str, Any]:
        """Handle MOMENTUM(14d)"""
        return {
            "category": "technical",
            "name": "momentum",
            "timeframe": timeframe,
        }

    def price_change_compound(self, timeframe: Any) -> Dict[str, Any]:
        """Handle PRICE_CHANGE(1d)"""
        return {
            "category": "price",
            "name": "price_change",
            "timeframe": timeframe,
        }

    def avg_volume_compound(self, timeframe: Any) -> Dict[str, Any]:
        """Handle AVG_VOLUME(30d)"""
        return {
            "category": "price",
            "name": "avg_volume",
            "timeframe": timeframe,
        }

    # ================== Parameters and Timeframes ==================

    def params(self, *args: Any) -> List[Any]:
        """Handle parameter list"""
        return list(args)

    def param(self, p: Any) -> Any:
        """Handle individual parameter"""
        return p

    def indicator_params(self, *indicators: Any) -> List[str]:
        """Handle indicator parameters in TECHNICAL()"""
        return [str(i) for i in indicators]

    def indicator_name(self, name: Token) -> str:
        """Handle indicator name"""
        return str(name)

    def timeframe(self, value: Token, unit: Token) -> Dict[str, Any]:
        """Handle timeframe like 30d, 7h, 4w"""
        return {"value": int(value), "unit": str(unit)}

    # ================== Indicators ==================

    def indicator_list(self, *indicators: Any) -> List[str]:
        """Handle list of macro indicators"""
        return [str(i) for i in indicators]

    def indicator(self, *args: Any) -> str:
        """Handle macro indicator"""
        if args:
            return str(args[0])
        return ""

    # ================== Analysis Types ==================

    def analysis_type(self, *args: Any) -> str:
        """Handle analysis type for MACRO queries"""
        if args:
            return str(args[0]).lower()
        return "regression"

    def legacy_analysis_type(self, *args: Any) -> str:
        """Handle legacy analysis type"""
        if args:
            return str(args[0]).lower()
        return "technicals"

    # ================== Conditions ==================

    def condition_list(self, *conditions: Any) -> List[Dict[str, Any]]:
        """Handle list of conditions"""
        return list(conditions)

    def condition(self, *args: Any) -> Dict[str, Any]:
        """Handle various condition types"""
        if len(args) >= 3:
            # Check for metric COMPARATOR metric * NUMBER pattern
            if len(args) == 4 and args[2] == "*":
                return {
                    "type": "comparison_multiplier",
                    "metric": args[0],
                    "operator": str(args[1]) if hasattr(args[1], "__str__") else args[1],
                    "compare_metric": args[2],
                    "multiplier": float(args[3]),
                }
            # Standard comparison: metric COMPARATOR value
            elif len(args) == 3:
                return {
                    "type": "comparison",
                    "metric": args[0],
                    "operator": str(args[1]) if hasattr(args[1], "__str__") else args[1],
                    "value": args[2],
                }
            # BETWEEN: metric BETWEEN value AND value
            elif len(args) == 4:
                return {
                    "type": "between",
                    "metric": args[0],
                    "min": args[1],
                    "max": args[3],
                }
        elif len(args) == 2:
            # TREND IS / SIGNAL IS
            return {"type": "state", "name": str(args[0]), "value": str(args[1])}

        return {"type": "custom", "args": list(args)}

    def trend_type(self, t: Token) -> str:
        """Handle trend type"""
        return str(t).lower()

    def signal_type(self, s: Token) -> str:
        """Handle signal type"""
        return str(s).lower()

    # ================== Values ==================

    def value(self, *args: Any) -> Any:
        """Handle value (number, percentage, string, or metric)"""
        if len(args) == 2 and str(args[1]) == "%":
            return {"type": "percentage", "value": float(args[0])}
        elif len(args) == 1:
            v = args[0]
            if isinstance(v, dict):
                return v
            try:
                return float(v)
            except (ValueError, TypeError):
                return str(v).strip('"')
        return args[0] if args else None

    # ================== Data Requests ==================

    def data_request(self, *args: Any) -> Dict[str, Any]:
        """Handle GET data request"""
        return {"type": "data_request", "args": list(args)}

    def legacy_timeframe(self, *args: Any) -> str:
        """Handle legacy timeframe formats"""
        if args:
            return str(args[0])
        return "1d"

    # ================== Helper Methods ==================

    def _to_asset_dict(self, asset: Any) -> Dict[str, Any]:
        """Convert asset to dictionary format"""
        if isinstance(asset, dict):
            return asset
        elif isinstance(asset, str):
            return {"symbol": asset, "type": "symbol"}
        else:
            return {"symbol": str(asset), "type": "symbol"}


class FKDSLParser:
    """
    FK-DSL Parser

    Parses Financial Knowledge DSL queries into structured execution plans.

    Supports Blueprint-specified queries:
        EVALUATE TSLA: PRICE, VOLATILITY(30d), CORRELATE(BTC, SPY)
        COMPARE BTC vs ETH vs SOL ON: VOLUME(7d), LIQUIDITY
        MACRO: US10Y, CPI, VIX → REGRESSION ON SPY
        CORRELATE TSLA WITH BTC, SPY WINDOW 90d
        SCAN NASDAQ WHERE VOLUME > 1000000 AND PE < 20

    Also supports legacy queries:
        FIND AAPL WITH PRICE > 150 AND RSI < 30
        ANALYZE AAPL FOR TECHNICALS
        COMPARE AAPL, MSFT, GOOGL BY PE, EPS
        GET PRICE FOR BTCUSD
    """

    def __init__(self) -> None:
        self.parser = Lark(FK_DSL_GRAMMAR, start="start", parser="lalr")
        self.transformer = FKDSLTransformer()

    def parse(self, query: str) -> Dict[str, Any]:
        """
        Parse DSL query string into execution plan

        Args:
            query: FK-DSL query string

        Returns:
            Parsed execution plan dict

        Raises:
            FKDSLParseError: If query is invalid
        """
        try:
            # Remove extra whitespace
            query = " ".join(query.split())

            # Parse to tree
            tree = self.parser.parse(query)

            # Transform to dict
            plan = self.transformer.transform(tree)

            logger.info("DSL query parsed", query=query[:100])
            return dict(plan) if isinstance(plan, dict) else plan

        except Exception as e:
            logger.error(f"DSL parse error: {e}", query=query)
            raise FKDSLParseError(f"Failed to parse DSL query: {e}")

    def validate(self, query: str) -> bool:
        """Validate DSL query syntax"""
        try:
            self.parse(query)
            return True
        except FKDSLParseError:
            return False


# Global parser instance
fk_dsl_parser = FKDSLParser()
