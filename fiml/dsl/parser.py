"""
FK-DSL Parser using Lark Grammar
"""

from typing import Any, Dict, List

from lark import Lark, Transformer, Tree, v_args

from fiml.core.exceptions import FKDSLParseError
from fiml.core.logging import get_logger

logger = get_logger(__name__)

# FK-DSL Grammar based on BLUEPRINT.md
FK_DSL_GRAMMAR = r"""
    ?start: query

    query: "FIND" asset_spec "WITH" condition_list
         | "ANALYZE" asset_spec "FOR" analysis_type
         | "COMPARE" asset_list "BY" metric_list
         | "TRACK" asset_spec "WHEN" condition_list
         | "GET" data_request

    asset_spec: asset_filter ("IN" market)?
    
    asset_filter: symbol
                | sector
                | "TOP" INT "BY" metric
                | "BOTTOM" INT "BY" metric
                | "ALL"

    symbol: CNAME
    sector: "SECTOR" CNAME
    market: CNAME

    condition_list: condition ("AND" condition)*
    
    condition: metric COMPARATOR value
             | metric "BETWEEN" value "AND" value
             | metric "ABOVE" metric
             | metric "BELOW" metric
             | "TREND" "IS" trend_type
             | "SIGNAL" "IS" signal_type

    metric: price_metric
          | fundamental_metric
          | technical_metric
          | sentiment_metric

    price_metric: "PRICE"
                | "VOLUME"
                | "MARKETCAP"
                | "CHANGE"

    fundamental_metric: "PE" | "EPS" | "ROE" | "DEBT" | "REVENUE" | "GROWTH"
    
    technical_metric: "RSI" | "MACD" | "SMA" INT | "EMA" INT | "STOCH" | "ATR"
    
    sentiment_metric: "SENTIMENT" | "BUZZ" | "NEWS_SCORE"

    analysis_type: "TECHNICALS"
                 | "FUNDAMENTALS"
                 | "SENTIMENT"
                 | "CORRELATIONS"
                 | "RISK"

    asset_list: asset_spec ("," asset_spec)*
    metric_list: metric ("," metric)*

    trend_type: "BULLISH" | "BEARISH" | "NEUTRAL"
    signal_type: "BUY" | "SELL" | "HOLD"

    data_request: "PRICE" "FOR" symbol
                | "OHLCV" "FOR" symbol timeframe?
                | "NEWS" "FOR" symbol
                | "FUNDAMENTALS" "FOR" symbol

    timeframe: "1m" | "5m" | "15m" | "1h" | "4h" | "1d" | "1w"

    COMPARATOR: ">" | "<" | ">=" | "<=" | "=" | "!="
    
    value: NUMBER | ESCAPED_STRING

    %import common.CNAME
    %import common.INT
    %import common.NUMBER
    %import common.ESCAPED_STRING
    %import common.WS
    %ignore WS
"""


@v_args(inline=True)
class FKDSLTransformer(Transformer):
    """Transform parsed tree into execution plan"""

    def query(self, *args):
        query_type = args[0]
        return {"type": query_type, "args": args[1:]}

    def asset_spec(self, asset_filter, market=None):
        return {"filter": asset_filter, "market": market}

    def symbol(self, name):
        return {"type": "symbol", "value": str(name)}

    def sector(self, name):
        return {"type": "sector", "value": str(name)}

    def condition(self, *args):
        if len(args) == 3:  # metric COMPARATOR value
            return {
                "type": "comparison",
                "metric": args[0],
                "operator": str(args[1]),
                "value": args[2],
            }
        elif len(args) == 4 and str(args[1]) == "BETWEEN":
            return {
                "type": "between",
                "metric": args[0],
                "min": args[2],
                "max": args[3],
            }
        else:
            return {"type": "custom", "args": args}

    def metric(self, m):
        return m

    def price_metric(self, name):
        return {"category": "price", "name": str(name).lower()}

    def fundamental_metric(self, name):
        return {"category": "fundamental", "name": str(name).lower()}

    def technical_metric(self, *args):
        if len(args) == 2:  # SMA 20, EMA 50
            return {"category": "technical", "name": str(args[0]).lower(), "period": int(args[1])}
        return {"category": "technical", "name": str(args[0]).lower()}

    def sentiment_metric(self, name):
        return {"category": "sentiment", "name": str(name).lower()}

    def value(self, v):
        try:
            return float(v)
        except:
            return str(v).strip('"')

    def condition_list(self, *conditions):
        return list(conditions)

    def analysis_type(self, atype):
        return str(atype).lower()

    def asset_list(self, *assets):
        return list(assets)

    def metric_list(self, *metrics):
        return list(metrics)


class FKDSLParser:
    """
    FK-DSL Parser
    
    Parses Financial Knowledge DSL queries into execution plans
    
    Examples:
        FIND AAPL WITH PRICE > 150 AND RSI < 30
        ANALYZE AAPL FOR TECHNICALS
        COMPARE AAPL, MSFT, GOOGL BY PE, EPS
        GET PRICE FOR BTCUSD
    """

    def __init__(self):
        self.parser = Lark(FK_DSL_GRAMMAR, start="query", parser="lalr")
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
            return plan

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
