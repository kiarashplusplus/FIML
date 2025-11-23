# Agent Workflows Quick Reference

## Quick Start

### Deep Equity Analysis

```python
from fiml.agents import deep_equity_analysis

result = await deep_equity_analysis("AAPL")
print(f"Recommendation: {result.recommendation['action']}")
print(f"Narrative: {result.narrative}")
```

### Crypto Sentiment Analysis

```python
from fiml.agents import crypto_sentiment_analysis

result = await crypto_sentiment_analysis("ETH", exchange="binance")
print(f"Signal: {result.signals['signal']}")
print(f"Price: ${result.price_data['price']:,.2f}")
```

---

## Common Patterns

### Batch Analysis

```python
import asyncio

symbols = ["AAPL", "MSFT", "GOOGL"]
results = await asyncio.gather(
    *[deep_equity_analysis(s) for s in symbols]
)
```

### Without LLM Narrative (Faster)

```python
result = await deep_equity_analysis(
    symbol="AAPL",
    include_narrative=False  # Saves 500-1000ms
)
```

### Error Handling

```python
result = await deep_equity_analysis("AAPL")

if result.status == WorkflowStatus.FAILED:
    print(f"Error: {result.error}")
elif result.status == WorkflowStatus.PARTIAL:
    print(f"Partial: {result.steps_completed}/{result.steps_total}")
```

---

## Result Structure Cheatsheet

### Deep Equity Analysis

```python
result.snapshot            # Price data
result.fundamentals        # P/E, EPS, ROE, valuation
result.technicals          # RSI, MACD, trends
result.sentiment           # News, social sentiment
result.risk                # Volatility, beta, correlations
result.narrative           # AI-generated insights
result.recommendation      # BUY/HOLD/SELL with scores
result.confidence_score    # Overall confidence (0-1)
```

### Crypto Sentiment Analysis

```python
result.price_data          # Real-time price
result.sentiment           # Sentiment score & trend
result.technicals          # RSI, MACD indicators
result.correlations        # BTC/ETH correlations
result.signals             # BUY/SELL/NEUTRAL signals
result.narrative           # Market narrative
result.confidence_score    # Overall confidence
```

---

## Workflow Execution Times

| Workflow | Typical Time | With Narrative | Without Narrative |
|----------|--------------|----------------|-------------------|
| Deep Equity Analysis | 1-3s | 2-3s | 1-1.5s |
| Crypto Sentiment | 0.8-2s | 1.5-2s | 0.8-1s |

---

## Environment Setup

```bash
# Required for LLM narratives
export AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4"

# Optional - for distributed processing
export RAY_ADDRESS="local"
```

---

## Key Features

### ✅ Built-in Capabilities

- ✓ Multi-provider data aggregation
- ✓ Parallel agent execution (Ray)
- ✓ LLM-powered narratives (Azure OpenAI)
- ✓ Automatic error recovery
- ✓ Data quality scoring
- ✓ Confidence metrics
- ✓ Partial result handling

### 🎯 Recommendation System

```python
recommendation = {
    "action": "BUY",           # BUY | HOLD | SELL
    "confidence": "HIGH",       # HIGH | MEDIUM | LOW
    "overall_score": 72.5,      # 0-100 scale
    "component_scores": {
        "fundamental_score": 75,
        "technical_score": 70,
        "sentiment_score": 65,
        "risk_score": 80
    }
}
```

---

## Advanced Usage

### Custom Workflow Instance

```python
from fiml.agents.workflows import DeepEquityAnalysisWorkflow
from fiml.llm import AzureOpenAIClient

workflow = DeepEquityAnalysisWorkflow(
    llm_client=AzureOpenAIClient(timeout=60)
)

result = await workflow.execute("MSFT")
```

### Extending Workflows

```python
from fiml.agents.workflows import DeepEquityAnalysisWorkflow

class MyCustomWorkflow(DeepEquityAnalysisWorkflow):
    async def _generate_recommendation(self, *args):
        # Custom recommendation logic
        return {"action": "BUY", "custom_score": 95}

workflow = MyCustomWorkflow()
```

---

## Testing

```bash
# Run workflow tests
pytest tests/test_agent_workflows.py -v

# Run specific test
pytest tests/test_agent_workflows.py::TestDeepEquityAnalysisWorkflow::test_workflow_execute_success -v
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Ray initialization failed | `export RAY_ADDRESS=local` |
| No providers available | Check API keys in `.env` |
| LLM API timeout | Increase timeout or set `include_narrative=False` |
| Low confidence scores | Check `result.data_quality_score` and `result.warnings` |

---

## Examples

See `examples/agent_workflows_demo.py` for:
- Basic workflow execution
- Batch processing
- Error handling
- Multi-asset comparison

Run demo:
```bash
python examples/agent_workflows_demo.py
```

---

## API Quick Reference

### Functions

```python
# Deep equity analysis
await deep_equity_analysis(
    symbol: str,
    market: Market = Market.US,
    include_narrative: bool = True,
    include_recommendation: bool = True
) -> DeepEquityAnalysisResult

# Crypto sentiment analysis
await crypto_sentiment_analysis(
    symbol: str,
    exchange: str = "binance",
    pair: str = "USDT",
    include_narrative: bool = True
) -> CryptoSentimentAnalysisResult
```

### Classes

```python
DeepEquityAnalysisWorkflow()
CryptoSentimentAnalysisWorkflow()
```

### Enums

```python
WorkflowStatus.PENDING
WorkflowStatus.RUNNING
WorkflowStatus.COMPLETED
WorkflowStatus.FAILED
WorkflowStatus.PARTIAL
```

---

For detailed documentation, see [Agent Workflows Guide](./agent-workflows.md)
