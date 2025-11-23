# FK-DSL Query Language

The Financial Knowledge Domain Specific Language (FK-DSL) provides a powerful query language for complex financial analysis.

## Syntax

### EVALUATE

Analyze a single asset:

```fkdsl
EVALUATE TSLA: PRICE, VOLATILITY(30d), TECHNICAL(RSI, MACD)
```

### COMPARE

Compare multiple assets:

```fkdsl
COMPARE BTC vs ETH vs SOL ON: VOLUME(7d), LIQUIDITY
```

### SCAN

Screen for assets matching criteria:

```fkdsl
SCAN NASDAQ WHERE VOLUME > AVG_VOLUME(30d) * 2
```

## Functions

- `PRICE` - Current price
- `VOLATILITY(period)` - Volatility calculation
- `CORRELATE(assets...)` - Correlation analysis
- `TECHNICAL(indicators...)` - Technical indicators
- `VOLUME(period)` - Volume metrics

See the complete [FK-DSL Reference](https://github.com/kiarashplusplus/FIML/blob/main/docs/fk-dsl-reference.md).
