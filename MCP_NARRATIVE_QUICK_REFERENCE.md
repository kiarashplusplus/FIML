# MCP Narrative Integration - Quick Reference

## Quick Start

### 1. Search Stock with Narrative
```python
from fiml.mcp.tools import search_by_symbol
from fiml.core.models import Market, AnalysisDepth

response = await search_by_symbol(
    symbol="AAPL",
    market=Market.US,
    depth=AnalysisDepth.STANDARD,
    language="en",
    expertise_level="intermediate",
    include_narrative=True
)

# Access narrative
if response.narrative:
    print(response.narrative.summary)
    print(response.narrative.key_insights)
    print(response.narrative.risk_factors)
```

### 2. Search Crypto with Narrative
```python
from fiml.mcp.tools import search_by_coin

response = await search_by_coin(
    symbol="BTC",
    exchange="Binance",
    pair="USD",
    depth=AnalysisDepth.DEEP,
    language="en",
    expertise_level="beginner",
    include_narrative=True
)

# Crypto-specific insights
print(response.narrative.key_insights)  # Includes blockchain metrics
print(response.narrative.risk_factors)  # Crypto-specific warnings
```

### 3. Generate Standalone Narrative
```python
from fiml.mcp.tools import get_narrative

result = await get_narrative(
    symbol="AAPL",
    asset_type="equity",
    language="en",
    expertise_level="advanced",
    analysis_data={
        "price_data": {"price": 175.0, "change_percent": 1.5},
        "technical_data": {"rsi": 65, "trend": "bullish"}
    },
    focus_areas=["market", "technical", "risk"]
)

# Full narrative access
narrative = result["narrative"]
print(narrative["summary"])
print(narrative["full_text"])      # Plain text
print(narrative["markdown"])       # Markdown format
```

## Parameters

### Depth Levels
- `QUICK`: No narrative (data only)
- `STANDARD`: Market + Technical + Fundamental narratives
- `DEEP`: All sections including Sentiment + Risk

### Languages
`en`, `es`, `fr`, `ja`, `zh`, `de`, `it`, `pt`, `fa`

### Expertise Levels
- `beginner`: Simple language, basic concepts
- `intermediate`: Balanced technical detail
- `advanced`: Professional terminology
- `quant`: Mathematical formulations

## Response Structure

### SearchBySymbolResponse / SearchByCoinResponse
```python
response = SearchBySymbolResponse(
    symbol="AAPL",
    name="Apple Inc.",
    cached=CachedData(...),
    narrative=NarrativeSummary(
        summary="Executive summary text...",
        key_insights=["Insight 1", "Insight 2"],
        risk_factors=["Risk 1", "Risk 2"],
        language="en"
    )
)
```

### get_narrative Response
```python
result = {
    "symbol": "AAPL",
    "asset_type": "equity",
    "narrative": {
        "summary": "...",
        "key_insights": [...],
        "risk_factors": [...],
        "sections": [
            {
                "title": "Market Context",
                "content": "...",
                "type": "market_context",
                "confidence": 0.85
            }
        ],
        "full_text": "Plain text version...",
        "markdown": "# Markdown version...",
        "word_count": 1250,
        "generation_time_ms": 850.5
    },
    "cached": false
}
```

## Cache Behavior

### TTL by Asset Type and Volatility

**Crypto (24/7)**:
- High volatility (>10%): 3 minutes
- Medium (5-10%): 5 minutes  
- Low: 10 minutes

**Equity**:
- After hours: 30 minutes
- Market hours + high volatility (>3%): 5 minutes
- Market hours + moderate (1-3%): 10 minutes
- Market hours + low: 15 minutes

### Cache Keys
Format: `narrative:{SYMBOL}:{language}:{expertise_level}`

Examples:
- `narrative:AAPL:en:intermediate`
- `narrative:BTC/USD:es:beginner`

## Utility Functions

### Format Narrative
```python
from fiml.mcp.tools import format_narrative_text, format_narrative_markdown

# Plain text
text = format_narrative_text(narrative)

# Markdown
markdown = format_narrative_markdown(narrative)
```

### Truncate for Display
```python
from fiml.mcp.tools import truncate_narrative

short = truncate_narrative(text, max_length=500)
```

### Manual Cache Access
```python
from fiml.mcp.tools import get_cached_narrative, cache_narrative

# Retrieve
cached = await get_cached_narrative("AAPL", "en", "intermediate")

# Store
success = await cache_narrative(
    "AAPL", "en", "intermediate",
    narrative_data, ttl=900
)
```

## Common Patterns

### 1. Multi-Language Analysis
```python
languages = ["en", "es", "fr"]
results = []

for lang in languages:
    response = await search_by_symbol(
        symbol="AAPL",
        market=Market.US,
        depth=AnalysisDepth.STANDARD,
        language=lang,
        expertise_level="intermediate"
    )
    results.append(response.narrative)
```

### 2. Progressive Depth
```python
# Quick first (no narrative, fast)
quick = await search_by_symbol(
    symbol="AAPL", depth=AnalysisDepth.QUICK,
    market=Market.US, language="en"
)

# Then deep if needed
if user_wants_details:
    deep = await search_by_symbol(
        symbol="AAPL", depth=AnalysisDepth.DEEP,
        market=Market.US, language="en",
        expertise_level="advanced"
    )
```

### 3. Crypto Risk Focus
```python
result = await get_narrative(
    symbol="BTC/USD",
    asset_type="crypto",
    language="en",
    expertise_level="beginner",
    focus_areas=["market", "risk"]  # Focus on risks
)
```

### 4. Error Handling
```python
try:
    response = await search_by_symbol(
        symbol="AAPL",
        market=Market.US,
        depth=AnalysisDepth.STANDARD,
        language="en",
        include_narrative=True
    )
    
    if response.narrative:
        # Use narrative
        display(response.narrative.summary)
    else:
        # Fallback to data only
        display(f"Price: ${response.cached.price}")
        
except Exception as e:
    logger.error(f"Analysis failed: {e}")
```

## Testing

### Run Integration Tests
```bash
pytest tests/test_mcp_narrative_integration.py -v
```

### Run Example Demos
```bash
python examples/mcp_narrative_demo.py
```

### Specific Test
```bash
pytest tests/test_mcp_narrative_integration.py::TestMCPNarrativeIntegration::test_search_by_symbol_with_narrative_standard -v
```

## Performance Tips

1. **Use QUICK depth** when narrative not needed (much faster)
2. **Cache is automatic** - same params = cache hit
3. **Different languages** cache separately
4. **Volatility affects TTL** - high volatility = shorter cache
5. **Focus areas** reduce generation time in standalone tool

## Troubleshooting

### No Narrative Generated
- Check `include_narrative=True`
- Verify depth is not QUICK
- Check logs for generation errors (falls back gracefully)

### Narrative in Wrong Language
- Verify language code is valid (en, es, fr, etc.)
- Check cache - different language = different cache key

### Cache Not Working
- Ensure cache_manager.l1 is initialized
- Check Redis connection
- Verify cache keys match exactly

### Slow Generation
- First call always slower (generates + caches)
- Second call fast (cache hit ~10ms)
- Deep analysis takes longer (more sections)

## API Reference

### search_by_symbol()
```python
async def search_by_symbol(
    symbol: str,
    market: Market,
    depth: AnalysisDepth,
    language: str,
    expertise_level: str = "intermediate",
    include_narrative: bool = True,
) -> SearchBySymbolResponse
```

### search_by_coin()
```python
async def search_by_coin(
    symbol: str,
    exchange: str,
    pair: str,
    depth: AnalysisDepth,
    language: str,
    expertise_level: str = "intermediate",
    include_narrative: bool = True,
) -> SearchByCoinResponse
```

### get_narrative()
```python
async def get_narrative(
    symbol: str,
    asset_type: str = "equity",
    language: str = "en",
    expertise_level: str = "intermediate",
    analysis_data: Optional[Dict[str, Any]] = None,
    focus_areas: Optional[list] = None,
) -> Dict[str, Any]
```

## Examples Directory

- `examples/mcp_narrative_demo.py`: Live demonstrations
  - AAPL standard/deep analysis
  - BTC crypto narratives
  - Multilingual examples
  - Caching efficiency demo
  - Format comparison

Run: `python examples/mcp_narrative_demo.py`
