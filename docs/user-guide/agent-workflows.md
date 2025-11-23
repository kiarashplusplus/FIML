# Agent Workflows Guide

## Overview

FIML provides high-level **Agent Workflows** that orchestrate multiple specialized agents, data providers, and LLM capabilities to deliver comprehensive financial analysis. These workflows are production-ready, robust, and designed for real-world use cases.

## Available Workflows

### 1. Deep Equity Analysis

**Purpose**: Multi-dimensional analysis of equity securities combining fundamental, technical, sentiment, and risk analysis with AI-generated narratives.

**Key Features**:
- Quick price snapshot from multiple providers
- Fundamental analysis (P/E, EPS, ROE, ROA, debt ratios, valuation)
- Technical analysis (RSI, MACD, trends, support/resistance)
- Sentiment analysis (news, social media, analyst opinions)
- Risk assessment (volatility, beta, correlations, drawdowns)
- LLM-generated narrative synthesis
- Actionable buy/hold/sell recommendations
- Data quality and confidence scoring

**Use Cases**:
- Pre-investment research
- Portfolio monitoring
- Earnings analysis
- Risk assessment
- Automated reporting

### 2. Crypto Sentiment Analysis

**Purpose**: Specialized cryptocurrency analysis focusing on sentiment, technical indicators, and market dynamics.

**Key Features**:
- Real-time price data from crypto exchanges
- Technical indicators (RSI, MACD, volume analysis)
- Sentiment from news and social media
- Correlation with major cryptos (BTC, ETH)
- LLM-powered market narrative
- Trading signal generation (Buy/Sell/Neutral)
- Confidence scoring

**Use Cases**:
- Trading signal generation
- Market sentiment tracking
- Crypto portfolio management
- Risk monitoring
- Automated alerts

---

## Quick Start

### Deep Equity Analysis

```python
from fiml.agents import deep_equity_analysis
from fiml.core.models import Market

# Analyze a stock
result = await deep_equity_analysis(
    symbol="AAPL",
    market=Market.US,
    include_narrative=True,
    include_recommendation=True
)

# Access results
print(f"Price: ${result.snapshot['price']:.2f}")
print(f"P/E Ratio: {result.fundamentals['metrics']['pe_ratio']}")
print(f"Recommendation: {result.recommendation['action']}")
print(f"Narrative:\n{result.narrative}")
```

### Crypto Sentiment Analysis

```python
from fiml.agents import crypto_sentiment_analysis

# Analyze a cryptocurrency
result = await crypto_sentiment_analysis(
    symbol="ETH",
    exchange="binance",
    pair="USDT",
    include_narrative=True
)

# Access results
print(f"Price: ${result.price_data['price']:,.2f}")
print(f"Signal: {result.signals['signal']}")
print(f"Sentiment Score: {result.sentiment['sentiment']['score']}")
print(f"Narrative:\n{result.narrative}")
```

---

## Workflow Architecture

### Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Execution                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Initialize Orchestrator                                 │
│     └─> Spawn Ray workers for parallel processing          │
│                                                             │
│  2. Fetch Data (Parallel)                                   │
│     ├─> Provider Registry → Multiple Data Sources          │
│     ├─> FundamentalsWorker → Financial metrics             │
│     ├─> TechnicalWorker → Indicators & patterns            │
│     ├─> SentimentWorker → News & social sentiment          │
│     └─> RiskWorker → Volatility & correlations             │
│                                                             │
│  3. Aggregate Results                                       │
│     └─> Combine data from all workers                      │
│                                                             │
│  4. LLM Narrative Generation (Optional)                     │
│     └─> Azure OpenAI → Synthesize insights                 │
│                                                             │
│  5. Generate Recommendations                                │
│     └─> Rule-based + ML scoring                            │
│                                                             │
│  6. Quality & Confidence Scoring                            │
│     └─> Calculate data quality and confidence metrics      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Integration

1. **Agent Orchestrator**: Manages parallel execution of specialized workers
2. **Provider Registry**: Routes requests to appropriate data providers
3. **Specialized Workers**: Execute domain-specific analysis
4. **LLM Client**: Generates natural language narratives and insights
5. **Result Aggregation**: Combines and validates all analysis components

---

## Detailed Usage

### Using Workflow Classes

For more control, instantiate workflow classes directly:

```python
from fiml.agents.workflows import DeepEquityAnalysisWorkflow
from fiml.agents import AgentOrchestrator
from fiml.llm import AzureOpenAIClient

# Create custom orchestrator and LLM client
orchestrator = AgentOrchestrator()
llm_client = AzureOpenAIClient(
    timeout=60,
    max_retries=5
)

# Initialize workflow with custom components
workflow = DeepEquityAnalysisWorkflow(
    orchestrator=orchestrator,
    llm_client=llm_client
)

# Execute
result = await workflow.execute(
    symbol="MSFT",
    market=Market.US,
    include_narrative=True,
    include_recommendation=True
)

# Clean up
await orchestrator.shutdown()
```

### Error Handling

Workflows are designed to be resilient:

```python
result = await deep_equity_analysis(symbol="INVALID")

# Check status
if result.status == WorkflowStatus.FAILED:
    print(f"Workflow failed: {result.error}")
elif result.status == WorkflowStatus.PARTIAL:
    print(f"Partial success: {result.steps_completed}/{result.steps_total}")
    
# Check warnings
for warning in result.warnings:
    print(f"Warning: {warning}")

# Even with failures, partial data may be available
if result.snapshot:
    print(f"Price data available: ${result.snapshot['price']}")
```

### Batch Processing

Analyze multiple assets in parallel:

```python
import asyncio

symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

# Run analyses concurrently
results = await asyncio.gather(
    *[deep_equity_analysis(symbol) for symbol in symbols]
)

# Process results
for symbol, result in zip(symbols, results):
    if result.status == WorkflowStatus.COMPLETED:
        rec = result.recommendation
        print(f"{symbol}: {rec['action']} (Score: {rec['overall_score']:.1f})")
```

---

## Result Structure

### DeepEquityAnalysisResult

```python
result = await deep_equity_analysis("AAPL")

# Metadata
result.workflow_name       # "deep_equity_analysis"
result.status             # WorkflowStatus.COMPLETED
result.execution_time_ms  # 1250.5
result.steps_completed    # 7
result.steps_total        # 7

# Price snapshot
result.snapshot = {
    "price": 150.25,
    "change": 2.50,
    "change_percent": 1.69,
    "volume": 50000000,
    "market_cap": 2500000000000,
    "provider": "yahoo_finance",
    "timestamp": "2024-01-15T10:30:00Z"
}

# Fundamentals
result.fundamentals = {
    "metrics": {
        "pe_ratio": 25.5,
        "pb_ratio": 10.2,
        "eps": 6.12,
        "roe": 0.45,
        "roa": 0.15,
        "debt_to_equity": 1.2
    },
    "valuation": {
        "assessment": "fairly_valued",  # undervalued | fairly_valued | overvalued
        "confidence": 0.75
    }
}

# Technical analysis
result.technicals = {
    "indicators": {
        "rsi": 55.2,
        "macd": 0.5,
        "signal": 0.3
    },
    "trend": {
        "direction": "bullish",  # bullish | bearish | neutral
        "strength": "medium"     # strong | medium | weak
    },
    "levels": {
        "support": 145.00,
        "resistance": 155.00
    }
}

# Sentiment analysis
result.sentiment = {
    "sentiment": {
        "score": 65,  # 0-100 scale
        "news_sentiment": "positive",
        "social_sentiment": "neutral"
    },
    "news": {
        "count": 15,
        "headlines": [...]
    }
}

# Risk assessment
result.risk = {
    "risk": {
        "level": "medium",  # low | medium | high
        "volatility": 0.25,
        "beta": 1.1,
        "max_drawdown": -0.15
    },
    "correlation": {
        "spy_correlation": 0.85
    }
}

# AI narrative
result.narrative = """
Executive Summary:
Apple (AAPL) demonstrates strong fundamentals with a P/E ratio of 25.5...
"""

# Recommendation
result.recommendation = {
    "action": "BUY",  # BUY | HOLD | SELL
    "confidence": "HIGH",  # HIGH | MEDIUM | LOW
    "overall_score": 72.5,  # 0-100 scale
    "component_scores": {
        "fundamental_score": 75,
        "technical_score": 70,
        "sentiment_score": 65,
        "risk_score": 80
    },
    "reasoning": "Based on comprehensive analysis..."
}

# Quality metrics
result.data_quality_score  # 95.0 (percentage)
result.confidence_score    # 0.85 (0-1 scale)
```

### CryptoSentimentAnalysisResult

```python
result = await crypto_sentiment_analysis("ETH", exchange="binance")

# Price data
result.price_data = {
    "price": 3500.50,
    "change": 50.25,
    "change_percent": 1.45,
    "volume": 500000,
    "high_24h": 3600.00,
    "low_24h": 3400.00
}

# Sentiment
result.sentiment = {
    "sentiment": {
        "score": 70,
        "trend": "bullish"
    },
    "news": {
        "count": 25,
        "sentiment": "positive"
    }
}

# Technical indicators
result.technicals = {
    "indicators": {
        "rsi": 60.5,
        "macd": 0.3
    },
    "volume": {
        "trend": "increasing"
    }
}

# Correlations
result.correlations = {
    "btc_correlation": 0.85,
    "eth_correlation": 1.0
}

# Trading signals
result.signals = {
    "signal": "BUY",  # BUY | SELL | NEUTRAL
    "strength": 65,    # 0-100 scale
    "indicators": [
        "Bullish sentiment",
        "Oversold (RSI)"
    ]
}

# Confidence
result.confidence_score  # 0.90
```

---

## Configuration

### Environment Variables

Configure Azure OpenAI for narrative generation:

```bash
# .env file
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### Ray Configuration

For distributed processing:

```bash
RAY_ADDRESS=auto  # Use existing Ray cluster
# or
RAY_ADDRESS=local  # Start local Ray instance
```

---

## Performance Considerations

### Execution Times

Typical execution times (with all components enabled):

- **Deep Equity Analysis**: 1-3 seconds
- **Crypto Sentiment Analysis**: 0.8-2 seconds

Times vary based on:
- Number of data providers
- LLM API response time
- Network latency
- Ray cluster availability

### Optimization Tips

1. **Disable Narrative for Faster Results**:
   ```python
   result = await deep_equity_analysis(
       symbol="AAPL",
       include_narrative=False  # Saves 500-1000ms
   )
   ```

2. **Batch Processing**:
   ```python
   # More efficient than sequential processing
   results = await asyncio.gather(
       *[deep_equity_analysis(s) for s in symbols]
   )
   ```

3. **Reuse Workflow Instances**:
   ```python
   workflow = DeepEquityAnalysisWorkflow()
   
   # Reuse for multiple analyses
   result1 = await workflow.execute("AAPL")
   result2 = await workflow.execute("MSFT")
   ```

4. **Configure Provider Priority**:
   ```python
   # Use faster providers first (in provider registry)
   ```

---

## Advanced Features

### Custom Recommendation Logic

Extend the workflow with custom recommendation logic:

```python
from fiml.agents.workflows import DeepEquityAnalysisWorkflow

class CustomEquityWorkflow(DeepEquityAnalysisWorkflow):
    async def _generate_recommendation(self, fundamentals, technicals, sentiment, risk):
        # Custom recommendation logic
        score = self._calculate_custom_score(fundamentals, technicals)
        
        return {
            "action": "BUY" if score > 70 else "HOLD",
            "confidence": "HIGH",
            "overall_score": score,
            "custom_metric": self._custom_calculation()
        }

workflow = CustomEquityWorkflow()
result = await workflow.execute("AAPL")
```

### Integration with FK-DSL

Workflows can be combined with FK-DSL queries:

```python
from fiml.dsl import FKDSLParser, FKDSLExecutor

# Use FK-DSL for complex queries
parser = FKDSLParser()
executor = FKDSLExecutor()

# Execute FK-DSL query
query = "GET price, fundamentals FOR AAPL WHERE pe_ratio < 20"
dsl_result = await executor.execute(parser.parse(query))

# Then run deep analysis
workflow_result = await deep_equity_analysis("AAPL")

# Combine results
combined = {
    "dsl_data": dsl_result,
    "deep_analysis": workflow_result
}
```

### Streaming Results

For real-time updates, use callbacks:

```python
async def progress_callback(step: int, total: int, description: str):
    print(f"[{step}/{total}] {description}")

# Note: This feature requires workflow modification
# to support callbacks (future enhancement)
```

---

## Error Handling Guide

### Common Errors

1. **Provider Failures**:
   ```python
   if result.snapshot.get("provider") == "mock":
       print("Warning: Using fallback mock data")
   ```

2. **LLM API Errors**:
   ```python
   if "unavailable" in result.narrative:
       print("Warning: Narrative generation failed")
   ```

3. **Orchestrator Issues**:
   ```python
   if result.status == WorkflowStatus.FAILED:
       if "Ray" in result.error:
           print("Ray initialization failed - check Ray cluster")
   ```

### Best Practices

1. **Always Check Status**:
   ```python
   result = await deep_equity_analysis("AAPL")
   
   if result.status != WorkflowStatus.COMPLETED:
       logger.error(f"Workflow incomplete: {result.error}")
       # Handle gracefully
   ```

2. **Validate Data Quality**:
   ```python
   if result.data_quality_score < 60:
       logger.warning("Low data quality - results may be unreliable")
   ```

3. **Use Timeouts**:
   ```python
   try:
       result = await asyncio.wait_for(
           deep_equity_analysis("AAPL"),
           timeout=10.0  # 10 second timeout
       )
   except asyncio.TimeoutError:
       logger.error("Workflow timed out")
   ```

---

## Testing

### Unit Tests

Run workflow tests:

```bash
pytest tests/test_agent_workflows.py -v
```

### Integration Tests

Run with real providers (requires API keys):

```bash
pytest tests/test_agent_workflows.py -v -m integration
```

### Example Test

```python
import pytest
from fiml.agents import deep_equity_analysis
from fiml.core.models import Market

@pytest.mark.asyncio
async def test_deep_analysis():
    result = await deep_equity_analysis(
        symbol="AAPL",
        market=Market.US,
        include_narrative=False
    )
    
    assert result.status == WorkflowStatus.COMPLETED
    assert result.snapshot is not None
    assert result.recommendation is not None
```

---

## API Reference

### Functions

#### `deep_equity_analysis`

```python
async def deep_equity_analysis(
    symbol: str,
    market: Market = Market.US,
    include_narrative: bool = True,
    include_recommendation: bool = True,
) -> DeepEquityAnalysisResult
```

**Parameters**:
- `symbol` (str): Stock symbol (e.g., "AAPL", "MSFT")
- `market` (Market): Market identifier (default: Market.US)
- `include_narrative` (bool): Generate LLM narrative (default: True)
- `include_recommendation` (bool): Generate recommendation (default: True)

**Returns**: `DeepEquityAnalysisResult`

---

#### `crypto_sentiment_analysis`

```python
async def crypto_sentiment_analysis(
    symbol: str,
    exchange: str = "binance",
    pair: str = "USDT",
    include_narrative: bool = True,
) -> CryptoSentimentAnalysisResult
```

**Parameters**:
- `symbol` (str): Crypto symbol (e.g., "BTC", "ETH")
- `exchange` (str): Exchange name (default: "binance")
- `pair` (str): Trading pair (default: "USDT")
- `include_narrative` (bool): Generate LLM narrative (default: True)

**Returns**: `CryptoSentimentAnalysisResult`

---

### Classes

#### `DeepEquityAnalysisWorkflow`

High-level workflow for comprehensive equity analysis.

**Methods**:
- `async execute(symbol, market, include_narrative, include_recommendation) -> DeepEquityAnalysisResult`

---

#### `CryptoSentimentAnalysisWorkflow`

Specialized workflow for cryptocurrency sentiment analysis.

**Methods**:
- `async execute(symbol, exchange, pair, include_narrative) -> CryptoSentimentAnalysisResult`

---

## Examples

See [`examples/agent_workflows_demo.py`](../examples/agent_workflows_demo.py) for comprehensive usage examples including:

- Basic workflow execution
- Batch processing multiple assets
- Error handling and resilience
- Custom workflow extensions
- Integration patterns

Run the demo:

```bash
python examples/agent_workflows_demo.py
```

---

## Troubleshooting

### Issue: "Ray initialization failed"

**Solution**: Ensure Ray is installed and configured:
```bash
pip install ray
export RAY_ADDRESS=local
```

### Issue: "No providers available"

**Solution**: Check provider configuration and API keys:
```bash
# Check .env file
cat .env | grep PROVIDER
```

### Issue: "LLM API timeout"

**Solution**: Increase timeout or disable narrative:
```python
from fiml.llm import AzureOpenAIClient

llm_client = AzureOpenAIClient(timeout=60)
workflow = DeepEquityAnalysisWorkflow(llm_client=llm_client)
```

### Issue: "Low confidence scores"

**Cause**: Missing or incomplete data from providers

**Solution**: Check data quality score and warnings:
```python
print(f"Data quality: {result.data_quality_score}%")
print(f"Warnings: {result.warnings}")
```

---

## Contributing

To add new workflows:

1. Extend base workflow structure in `fiml/agents/workflows.py`
2. Implement workflow execution logic
3. Add comprehensive tests in `tests/test_agent_workflows.py`
4. Update documentation
5. Add example usage in `examples/`

---

## License

See [LICENSE](../LICENSE) for details.
