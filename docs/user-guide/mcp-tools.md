# MCP Tools

FIML provides several MCP (Model Context Protocol) tools for financial data access.

## Available Tools

### search-by-symbol

Query equity data by ticker symbol.

**Parameters:**
- `symbol` (string): Stock ticker (e.g., "AAPL")
- `market` (string): Market region (default: "US")
- `depth` (string): Data depth - "basic", "standard", or "deep"

**Example:**
```json
{
  "name": "search-by-symbol",
  "arguments": {
    "symbol": "TSLA",
    "market": "US",
    "depth": "standard"
  }
}
```

### search-by-coin

Query cryptocurrency data.

**Parameters:**
- `symbol` (string): Crypto symbol (e.g., "BTC")
- `exchange` (string): Exchange name (e.g., "binance")
- `pair` (string): Trading pair (e.g., "USDT")

### execute-fk-dsl

Execute Financial Knowledge DSL queries.

See [FK-DSL Guide](fk-dsl.md) for query language documentation.
