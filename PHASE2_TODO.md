# FIML Phase 2 Todo List - AI Agent Execution Guide

**Document Created**: November 23, 2025  
**Last Updated**: November 23, 2025  
**Status**: Phase 2 Planning - Ready for Implementation  
**Context**: Following completion of Phase 1 (95%), this document outlines Phase 2 tasks with Azure OpenAI integration

---

## 📋 Executive Summary

Phase 2 focuses on **intelligence enhancement** through Azure OpenAI integration, advanced agent implementations, and multi-platform distribution. This document provides AI agent-executable tasks with detailed prompts and context.

**Key Changes from Phase 1**:
- Integration of Azure OpenAI for narrative generation
- Enhanced agent workers with real data processing
- Multi-platform deployment (ChatGPT, Claude, Telegram)
- Advanced caching and performance optimization
- Real-time event intelligence system

**Available Resources**:
- Azure OpenAI endpoints (to be configured in .env)
- Existing agent framework (fiml/agents/) with 7 worker types
- 5 operational data providers
- Complete caching infrastructure
- MCP protocol foundation

---

## 🔧 Configuration Prerequisites

### Azure OpenAI Setup

Before starting Phase 2 implementation, configure these environment variables in `.env`:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4  # or gpt-35-turbo

# Model Configuration
AZURE_OPENAI_MODEL=gpt-4
AZURE_OPENAI_TEMPERATURE=0.7
AZURE_OPENAI_MAX_TOKENS=2000

# Narrative Generation Settings
ENABLE_NARRATIVE_GENERATION=true
NARRATIVE_LANGUAGE_DEFAULT=en
NARRATIVE_STYLE=professional  # professional, casual, technical

# Agent Intelligence Settings
ENABLE_AI_AGENTS=true
AGENT_LLM_PROVIDER=azure_openai  # azure_openai, openai, anthropic
AGENT_MAX_RETRIES=3
AGENT_TIMEOUT_SECONDS=30
```

### Alternative LLM Providers (if Azure unavailable)

```bash
# OpenAI Direct
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4-turbo-preview

# Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_key
ANTHROPIC_MODEL=claude-3-opus-20240229
```

---

## 📝 Phase 2 Tasks - AI Agent Executable

Each task below includes:
1. **Objective**: What to accomplish
2. **Context**: Current state and dependencies
3. **Prompt**: AI agent-ready instructions
4. **Files**: Where to make changes
5. **Success Criteria**: How to verify completion

---

### Task 1: Azure OpenAI Client Integration

**Priority**: CRITICAL  
**Estimated Time**: 2-3 hours  
**Dependencies**: Azure OpenAI credentials

#### Objective
Create a robust Azure OpenAI client wrapper for narrative generation and agent intelligence, with fallback to standard OpenAI if Azure is unavailable.

#### Context
- Current state: No LLM integration exists in codebase
- BLUEPRINT.md specifies narrative generation engine (Section 14)
- Agent workers exist but use mock data (fiml/agents/workers.py)
- Need abstraction layer to support multiple LLM providers

#### Prompt for AI Agent

```
Create a new module at fiml/llm/azure_client.py that:

1. Implements an AzureOpenAIClient class with these methods:
   - async def generate_narrative(context: Dict[str, Any], language: str = "en") -> str
   - async def analyze_sentiment(text: str) -> Dict[str, float]
   - async def summarize_analysis(data: Dict[str, Any], max_length: int = 500) -> str
   - async def health_check() -> Dict[str, bool]

2. Uses settings from fiml/core/config.py for configuration:
   - azure_openai_endpoint
   - azure_openai_api_key
   - azure_openai_deployment_name
   - azure_openai_api_version

3. Implements proper error handling:
   - Retry logic with exponential backoff (max 3 retries)
   - Rate limit handling
   - Timeout handling (30 seconds default)
   - Graceful degradation if Azure unavailable

4. Add comprehensive logging using fiml.core.logging.get_logger

5. Include type hints and docstrings following existing codebase patterns

6. Create corresponding tests in tests/test_azure_openai.py that:
   - Mock Azure API responses
   - Test error handling
   - Test retry logic
   - Test rate limiting

Reference implementations:
- fiml/providers/base.py for provider pattern
- fiml/providers/yahoo_finance.py for async HTTP patterns
- fiml/core/config.py for settings management

Success criteria:
- Client initializes with Azure credentials
- All methods return expected types
- Error handling tested and working
- Tests pass with 100% coverage of azure_client.py
```

#### Files to Create/Modify
- **Create**: `fiml/llm/__init__.py`
- **Create**: `fiml/llm/azure_client.py` (250-300 lines)
- **Create**: `fiml/llm/base.py` (abstract LLM interface)
- **Create**: `tests/test_azure_openai.py` (150-200 lines)
- **Modify**: `fiml/core/config.py` (add Azure OpenAI settings)

#### Success Criteria
- [ ] Azure OpenAI client initializes successfully
- [ ] Can generate narrative from market data context
- [ ] Handles rate limits and errors gracefully
- [ ] Falls back to mock data if Azure unavailable
- [ ] 100% test coverage for new code
- [ ] Integration test demonstrates narrative generation

---

### Task 2: Narrative Generation Engine Implementation

**Priority**: HIGH  
**Estimated Time**: 4-5 hours  
**Dependencies**: Task 1 (Azure OpenAI Client)

#### Objective
Build the narrative generation system specified in BLUEPRINT.md Section 14 that converts financial data into human-readable summaries using Azure OpenAI.

#### Context
- BLUEPRINT.md outlines comprehensive narrative generation (lines 4366-4603)
- Requires: market context, technical analysis, fundamentals, sentiment, risk narratives
- Current workers return mock data - need real narrative synthesis
- Should support multiple languages and expertise levels

#### Prompt for AI Agent

```
Create a narrative generation engine at fiml/narrative/generator.py that:

1. Implements NarrativeGenerator class with methods:
   - async def generate_narrative(analysis: ComprehensiveAnalysis, language: str = "en") -> Narrative
   - async def _generate_market_context(asset: Asset, cached_data: CachedData) -> NarrativeSection
   - async def _generate_technical_narrative(technical: TechnicalAnalysis) -> NarrativeSection
   - async def _generate_fundamental_narrative(fundamentals: FundamentalsData) -> NarrativeSection
   - async def _generate_sentiment_narrative(sentiment: SentimentAnalysis) -> NarrativeSection
   - async def _extract_key_insights(analysis: ComprehensiveAnalysis) -> List[str]

2. Use Azure OpenAI client from Task 1 for:
   - Generating natural language summaries from structured data
   - Identifying key insights from multi-source analysis
   - Adapting tone based on user expertise level
   - Supporting multiple languages (EN, ES, FR, JP, ZH initially)

3. Implement prompt templates for each narrative type:
   - Market context: price movement, volume analysis, 52-week positioning
   - Technical: indicator interpretation (RSI, MACD, Bollinger)
   - Fundamental: ratio analysis and valuation
   - Sentiment: news and social media synthesis
   - Risk: volatility and risk metrics explanation

4. Add narrative quality validation:
   - Length constraints (500-2000 characters per section)
   - Readability scoring
   - Fact-checking against source data
   - Disclaimer injection for compliance

5. Support adaptive depth based on user expertise:
   - Beginner: Simple language, basic concepts
   - Intermediate: Technical terms with explanations
   - Advanced: Professional terminology
   - Quant: Mathematical formulations

Create data models at fiml/narrative/models.py for:
- Narrative (with sections, summary, insights)
- NarrativeSection (title, content, confidence)
- NarrativeContext (analysis data, preferences, constraints)

Reference:
- BLUEPRINT.md Section 14 (lines 4366-4603)
- fiml/core/models.py for model patterns
- fiml/llm/azure_client.py for LLM integration

Success criteria:
- Generates coherent narratives from analysis data
- Supports 5+ languages
- Adapts to user expertise level
- Includes proper financial disclaimers
- Tests validate narrative quality and correctness
```

#### Files to Create/Modify
- **Create**: `fiml/narrative/__init__.py`
- **Create**: `fiml/narrative/generator.py` (400-500 lines)
- **Create**: `fiml/narrative/models.py` (100-150 lines)
- **Create**: `fiml/narrative/templates.py` (prompt templates, 200-250 lines)
- **Create**: `tests/test_narrative_generator.py` (200-250 lines)
- **Modify**: `fiml/core/models.py` (add Narrative types)

#### Success Criteria
- [ ] Generates narratives for stock analysis
- [ ] Generates narratives for crypto analysis
- [ ] Supports 5 languages (EN, ES, FR, JP, ZH)
- [ ] Adapts tone for 4 expertise levels
- [ ] Includes compliance disclaimers
- [ ] Passes quality validation checks
- [ ] Integration test with real data

---

### Task 3: Enhanced Agent Worker Implementations

**Priority**: HIGH  
**Estimated Time**: 6-8 hours  
**Dependencies**: Task 1 (Azure OpenAI), Provider data access

#### Objective
Replace mock implementations in fiml/agents/workers.py with real data processing and AI-enhanced analysis using Azure OpenAI for insights.

#### Context
- Current workers return hardcoded mock data (fiml/agents/workers.py)
- BLUEPRINT.md Sections 5.2-5.5 specify worker capabilities
- Need integration with: providers (Task complete), cache (exists), Azure OpenAI (Task 1)
- 7 worker types: Fundamentals, Technical, Macro, Sentiment, Correlation, Risk, News

#### Prompt for AI Agent

```
Enhance fiml/agents/workers.py by replacing mock implementations with real data processing:

For FundamentalsWorker:
1. Fetch real fundamental data via provider registry
2. Calculate financial ratios (P/E, P/B, ROE, ROA, debt-to-equity)
3. Use Azure OpenAI to interpret financial health
4. Compare metrics to sector averages
5. Generate valuation assessment (overvalued/fairly valued/undervalued)
6. Return structured data with confidence scores

For TechnicalWorker:
1. Fetch OHLCV data from providers
2. Calculate indicators using ta-lib or pandas-ta:
   - RSI (14-period)
   - MACD (12, 26, 9)
   - Bollinger Bands (20, 2)
   - Moving averages (SMA 20/50/200, EMA 12/26)
3. Identify support/resistance levels
4. Use Azure OpenAI to interpret chart patterns
5. Generate trading signals with confidence
6. Return indicator values + interpretations

For MacroWorker:
1. Fetch macro indicators (interest rates, inflation, GDP, unemployment)
2. Analyze correlation with target asset
3. Use Azure OpenAI to assess macro environment impact
4. Generate macro context narrative
5. Return impact assessment with confidence

For SentimentWorker:
1. Fetch news articles from providers
2. Use Azure OpenAI sentiment analysis on headlines and content
3. Aggregate sentiment scores across sources
4. Weight by source credibility
5. Identify sentiment trends (improving/declining)
6. Return sentiment score (-1 to 1) with supporting evidence

For CorrelationWorker:
1. Fetch price data for asset + comparison assets (SPY, QQQ, sector ETFs)
2. Calculate Pearson correlation coefficients
3. Compute rolling correlations (30d, 90d)
4. Identify correlation breakdowns
5. Calculate beta vs market
6. Return correlation matrix with insights

For RiskWorker:
1. Fetch historical price data
2. Calculate risk metrics:
   - Volatility (historical, implied)
   - Value at Risk (VaR 95%, 99%)
   - Sharpe ratio
   - Max drawdown
   - Downside deviation
3. Use Azure OpenAI to assess risk profile
4. Generate risk warnings for high-risk assets
5. Return risk metrics + risk level classification

For NewsWorker:
1. Fetch recent news from providers
2. Use Azure OpenAI to:
   - Extract key events
   - Assess impact (high/medium/low)
   - Identify sentiment per article
   - Detect market-moving news
3. Build event timeline
4. Return top articles with impact scores

Each worker should:
- Use provider_registry from fiml.providers.registry
- Leverage cache for historical data
- Integrate Azure OpenAI for interpretations
- Include comprehensive error handling
- Return consistent data structure with scores (0-10)
- Log all operations with structlog
- Handle missing data gracefully

Add integration tests that:
- Mock provider responses
- Mock Azure OpenAI responses
- Test each worker independently
- Test error scenarios
- Verify scoring logic

Reference:
- BLUEPRINT.md Section 5 (lines 1313-1622)
- fiml/providers/base.py for provider patterns
- fiml/llm/azure_client.py for LLM integration
- Existing worker structure in fiml/agents/workers.py

Success criteria:
- All 7 workers fetch real data from providers
- Azure OpenAI enhances analysis quality
- Workers return consistent, scored results
- Error handling covers provider failures
- Tests achieve 90%+ coverage
- Integration test runs full multi-agent analysis
```

#### Files to Modify/Create
- **Refactor**: `fiml/agents/workers.py` → split into separate modules:
  - `fiml/agents/workers/__init__.py`
  - `fiml/agents/workers/fundamentals.py` (150-200 lines)
  - `fiml/agents/workers/technical.py` (150-200 lines)
  - `fiml/agents/workers/macro.py` (100-150 lines)
  - `fiml/agents/workers/sentiment.py` (150-200 lines)
  - `fiml/agents/workers/correlation.py` (100-150 lines)
  - `fiml/agents/workers/risk.py` (150-200 lines)
  - `fiml/agents/workers/news.py` (100-150 lines)
- **Create**: `fiml/agents/calculators.py` (financial calculations, 300-400 lines)
- **Create**: `tests/workers/test_fundamentals.py` (separate test per worker)
- **Create**: `tests/workers/test_technical.py` 
- **Create**: `tests/workers/test_enhanced_workers.py` (integration tests)
- **Modify**: `tests/test_agents.py` (expand coverage)

**Note**: Splitting workers into separate files improves maintainability and follows single responsibility principle.

#### Success Criteria
- [ ] All workers fetch real data from providers
- [ ] Financial calculations are accurate
- [ ] Azure OpenAI integration enhances insights
- [ ] Workers handle missing/bad data
- [ ] All workers return consistent structure
- [ ] Tests cover success and failure paths
- [ ] Integration test demonstrates multi-agent analysis

---

### Task 4: Real-time Event Intelligence System

**Priority**: MEDIUM  
**Estimated Time**: 5-6 hours  
**Dependencies**: Enhanced workers (Task 3)

#### Objective
Implement the watchdog system specified in BLUEPRINT.md Section 10 to detect and alert on market anomalies in real-time.

#### Context
- BLUEPRINT.md Section 10 outlines 8 watchdog types (lines 3332-3553)
- Need continuous monitoring for: earnings anomalies, unusual volume, whale movements, funding spikes, liquidity drops, correlation breaks, exchange outages
- Should emit events via event stream (Kafka/Redis)
- Integrate with WebSocket for client notifications

#### Prompt for AI Agent

```
Create real-time event intelligence system at fiml/watchdog/:

1. Implement base watchdog class (fiml/watchdog/base.py):
   - Abstract BaseWatchdog with async monitoring loop
   - Event emission via event stream
   - Configurable check intervals
   - Health monitoring
   - Graceful shutdown

2. Implement 8 specialized watchdogs (fiml/watchdog/detectors.py):
   
   a) EarningsAnomalyWatchdog:
      - Monitor actual earnings vs estimates
      - Detect significant beats/misses (>10% deviation)
      - Emit events with severity based on surprise magnitude
   
   b) UnusualVolumeWatchdog:
      - Track volume vs 30-day average
      - Alert on >3x volume spikes
      - Correlate with price movement
   
   c) WhaleMovementWatchdog (crypto):
      - Monitor large transfers (>$1M)
      - Track exchange inflows/outflows
      - Detect unusual accumulation patterns
   
   d) FundingRateWatchdog (crypto futures):
      - Monitor perpetual funding rates
      - Alert on extreme rates (>0.1% or <-0.1%)
      - Detect funding rate spikes
   
   e) LiquidityDropWatchdog (crypto):
      - Track order book depth
      - Alert on >50% liquidity reduction
      - Monitor bid-ask spread widening
   
   f) CorrelationBreakdownWatchdog:
      - Track rolling correlations
      - Detect correlation changes >0.5
      - Alert on relationship breakdowns
   
   g) ExchangeOutageWatchdog:
      - Monitor exchange health endpoints
      - Track API response times
      - Alert on degraded service
   
   h) PriceAnomalyWatchdog:
      - Detect rapid price movements (>5% in 1 min)
      - Identify flash crashes
      - Compare across exchanges for arbitrage

3. Create event stream manager (fiml/watchdog/events.py):
   - EventStream class for pub/sub
   - Integration with Kafka/Redis Streams
   - Event persistence
   - Subscription management
   - WebSocket broadcasting

4. Build watchdog orchestrator (fiml/watchdog/orchestrator.py):
   - WatchdogManager to coordinate all watchdogs
   - Startup/shutdown lifecycle
   - Health monitoring
   - Event aggregation
   - Priority-based event handling

5. Add models (fiml/watchdog/models.py):
   - WatchdogEvent (type, severity, asset, data, timestamp)
   - EventType enum
   - Severity enum (low, medium, high, critical)
   - EventFilter for subscriptions

Each watchdog should:
- Run independently in background
- Fetch data from providers/cache
- Use Azure OpenAI to assess event significance
- Emit structured events
- Handle errors without crashing
- Be individually enable/disable via config

Create comprehensive tests:
- Mock provider data
- Simulate anomaly conditions
- Test event emission
- Verify alert accuracy
- Test orchestrator lifecycle

Reference:
- BLUEPRINT.md Section 10 (lines 3332-3553)
- fiml/providers/registry.py for data access
- fiml/cache/ for historical data
- Existing WebSocket in fiml/ (if exists)

Success criteria:
- All 8 watchdogs implemented and tested
- Events emit to event stream
- WebSocket broadcasts to clients
- False positive rate <5%
- Detects known anomaly patterns
- Handles high-frequency monitoring
- Graceful degradation on failures
```

#### Files to Create/Modify
- **Create**: `fiml/watchdog/__init__.py`
- **Create**: `fiml/watchdog/base.py` (150-200 lines)
- **Create**: `fiml/watchdog/detectors/__init__.py`
- **Create**: `fiml/watchdog/detectors/earnings.py` (100-120 lines)
- **Create**: `fiml/watchdog/detectors/volume.py` (100-120 lines)
- **Create**: `fiml/watchdog/detectors/whale.py` (120-150 lines)
- **Create**: `fiml/watchdog/detectors/funding.py` (100-120 lines)
- **Create**: `fiml/watchdog/detectors/liquidity.py` (120-150 lines)
- **Create**: `fiml/watchdog/detectors/correlation.py` (150-180 lines)
- **Create**: `fiml/watchdog/detectors/exchange.py` (100-120 lines)
- **Create**: `fiml/watchdog/detectors/price.py` (100-120 lines)
- **Create**: `fiml/watchdog/events.py` (200-250 lines)
- **Create**: `fiml/watchdog/orchestrator.py` (250-300 lines)
- **Create**: `fiml/watchdog/models.py` (100-150 lines)
- **Create**: `tests/watchdog/test_earnings_detector.py` (separate test per detector)
- **Create**: `tests/watchdog/test_volume_detector.py`
- **Create**: `tests/watchdog/test_watchdog_integration.py` (integration tests)
- **Modify**: `fiml/server.py` (integrate watchdog startup)

**Note**: Splitting detectors into separate files improves maintainability and allows independent testing/deployment.

#### Success Criteria
- [ ] All 8 watchdogs detect their target anomalies
- [ ] Events stream to Kafka/Redis
- [ ] WebSocket broadcasts to subscribers
- [ ] False positive rate validated
- [ ] Performance benchmarked (handle 100+ assets)
- [ ] Tests cover all watchdog types
- [ ] Documentation for adding new watchdogs

---

### Task 5: Advanced Cache Optimization

**Priority**: MEDIUM  
**Estimated Time**: 4-5 hours  
**Dependencies**: Baseline cache exists (Phase 1)

#### Objective
Enhance cache layer with predictive pre-warming, intelligent eviction, and performance optimization as outlined in BLUEPRINT.md Section 7.

#### Context
- Basic L1 (Redis) and L2 (PostgreSQL) cache exists
- BLUEPRINT.md specifies predictive pre-warming and batch updates (lines 2176-2308)
- Current implementation lacks optimization strategies
- Need to reduce API calls and improve response times

#### Prompt for AI Agent

```
Enhance caching system in fiml/cache/ with advanced optimizations:

1. Implement cache warming (fiml/cache/warming.py):
   - PredictiveCacheWarmer class
   - Analyze query patterns from logs
   - Identify frequently requested symbols
   - Pre-fetch during off-peak hours
   - Prioritize based on:
     * Request frequency (last 7 days)
     * Time of day patterns
     * Market events (earnings dates)
     * Trending symbols
   - Configurable warming schedules
   - Monitor warming effectiveness

2. Enhance eviction policies (modify fiml/cache/l1_cache.py):
   - Implement LFU (Least Frequently Used) alongside LRU
   - Track access frequency per key
   - Configurable eviction strategy (LRU/LFU/hybrid)
   - Protect critical keys from eviction
   - Log eviction decisions for analysis

3. Add batch update scheduler (fiml/cache/scheduler.py):
   - BatchUpdateScheduler class
   - Group similar requests
   - Schedule updates during low-load periods
   - Batch provider API calls
   - Update multiple cache entries atomically
   - Configurable batch size and interval

4. Implement cache analytics (fiml/cache/analytics.py):
   - Track hit/miss rates per data type
   - Monitor cache latency (p50, p95, p99)
   - Identify cache pollution
   - Generate optimization recommendations
   - Export metrics to Prometheus

5. Add intelligent TTL management (modify fiml/cache/manager.py):
   - Dynamic TTL based on data volatility
   - Shorter TTL for crypto (1-5 min)
   - Longer TTL for fundamentals (24 hours)
   - Adaptive TTL based on market hours
   - Weekend/holiday extended TTL

6. Optimize query patterns:
   - Add multi-key fetch operations
   - Pipeline Redis operations
   - Connection pooling optimization
   - Reduce serialization overhead
   - Implement read-through cache pattern

Create comprehensive benchmarks:
- Test with 1000 concurrent requests
- Measure cache hit rates under load
- Compare optimized vs baseline performance
- Test warming effectiveness
- Validate eviction accuracy

Reference:
- BLUEPRINT.md Section 7 (lines 2176-2308)
- fiml/cache/l1_cache.py (existing L1)
- fiml/cache/l2_cache.py (existing L2)
- fiml/cache/manager.py (existing coordinator)

Success criteria:
- Cache hit rate improves to >90%
- Average latency reduces by 30%
- Warming correctly predicts requests
- Eviction policy maintains hot data
- Batch updates reduce API calls by 40%
- Benchmarks show measurable improvement
- Prometheus metrics exported
```

#### Files to Create/Modify
- **Create**: `fiml/cache/warming.py` (250-300 lines)
- **Create**: `fiml/cache/scheduler.py` (200-250 lines)
- **Create**: `fiml/cache/analytics.py` (200-250 lines)
- **Modify**: `fiml/cache/l1_cache.py` (add LFU, ~100 lines)
- **Modify**: `fiml/cache/manager.py` (dynamic TTL, ~80 lines)
- **Create**: `tests/test_cache_optimization.py` (300-400 lines)
- **Create**: `benchmarks/cache_performance.py` (benchmark script, 150-200 lines)

#### Success Criteria
- [ ] Cache hit rate >90% for popular symbols
- [ ] P95 latency <100ms for L1 cache
- [ ] Warming predicts 70%+ of requests
- [ ] Eviction maintains frequently accessed data
- [ ] Batch updates demonstrated working
- [ ] Benchmarks show improvement
- [ ] Analytics dashboard functional

---

### Task 6: MCP Tool Integration with Narrative Generation

**Priority**: HIGH  
**Estimated Time**: 3-4 hours  
**Dependencies**: Task 2 (Narrative Generation)

#### Objective
Integrate narrative generation into existing MCP tools (search-by-symbol, search-by-coin) to provide AI-enhanced market analysis.

#### Context
- MCP tools currently return structured data only (fiml/mcp/tools.py)
- Task 2 creates narrative generation capability
- Need to enhance responses with human-readable narratives
- Should be optional based on depth parameter

#### Prompt for AI Agent

```
Enhance MCP tools in fiml/mcp/tools.py to include narrative generation:

1. Modify search_by_symbol tool:
   - Add narrative field to response when depth != "quick"
   - Call narrative_generator.generate_narrative() with analysis data
   - Include narratives for:
     * Market context (always)
     * Technical analysis (if depth >= "standard")
     * Fundamentals (if depth >= "standard")
     * Sentiment (if depth == "deep")
     * Risk factors (if depth == "deep")
   - Add language parameter support (en, es, fr, jp, zh)
   - Include expertise_level parameter (beginner, intermediate, advanced, quant)
   - Handle narrative generation errors gracefully (fallback to data-only)

2. Modify search_by_coin tool:
   - Add crypto-specific narratives
   - Include blockchain metrics interpretation
   - Add DeFi context if applicable
   - Explain funding rates and open interest
   - Compare across exchanges with narrative
   - Crypto risk warnings via narrative

3. Create new tool: get_narrative (fiml/mcp/tools.py):
   - Standalone narrative generation for existing analysis
   - Input: analysis_id or task_id
   - Output: comprehensive narrative
   - Support re-generation with different params
   - Allow custom narrative focus areas

4. Add narrative caching with dynamic TTL:
   - Cache generated narratives in L1 cache
   - Dynamic TTL based on market conditions:
     * Pre-market/After-hours: 30 minutes (less volatility)
     * Market hours, low volatility: 15 minutes
     * Market hours, high volatility: 5 minutes
     * Crypto (24/7): 10 minutes baseline, adjust for volatility
   - Invalidate on new analysis data or significant price movement (>3%)
   - Key: f"narrative:{symbol}:{language}:{expertise}"
   - Monitor cache efficiency and adjust TTLs based on hit rates

5. Update tool schemas:
   - Add language parameter to existing tools
   - Add expertise_level parameter
   - Add include_narrative boolean flag
   - Update response schemas to include narrative fields

6. Create narrative formatting utilities:
   - Format for plain text output
   - Format for markdown
   - Format for HTML (if web interface)
   - Truncate for display limits
   - Add proper citations to data sources

Reference:
- fiml/mcp/tools.py (existing tool implementations)
- fiml/narrative/generator.py (from Task 2)
- BLUEPRINT.md Section 3 (MCP tools, lines 456-875)

Success criteria:
- MCP tools return narratives when requested
- Narratives adapt to language and expertise
- Handles errors without breaking tool
- Narratives cached appropriately
- Tool schemas updated in MCP router
- Integration tests demonstrate narrative flow
- Example narratives generated for AAPL, BTC
```

#### Files to Modify/Create
- **Modify**: `fiml/mcp/tools.py` (add narrative integration, ~200 lines)
- **Modify**: `fiml/mcp/router.py` (update tool schemas)
- **Create**: `fiml/mcp/formatting.py` (narrative formatting, 100-150 lines)
- **Modify**: `tests/test_mcp_tools.py` (test narrative integration)
- **Create**: `examples/narrative_examples.py` (demo script, 100 lines)

#### Success Criteria
- [ ] search-by-symbol returns narratives
- [ ] search-by-coin returns crypto narratives
- [ ] Supports 5 languages
- [ ] Adapts to expertise levels
- [ ] Narratives cached effectively
- [ ] Errors handled gracefully
- [ ] Examples demonstrate capability

---

### Task 7: Platform Integration - ChatGPT GPT Marketplace

**Priority**: HIGH  
**Estimated Time**: 4-5 hours  
**Dependencies**: Task 6 (MCP + Narratives)

#### Objective
Create ChatGPT GPT marketplace integration as specified in BLUEPRINT.md Section 12.1 to distribute FIML as a custom GPT.

#### Context
- BLUEPRINT.md Section 12.1 outlines GPT configuration (lines 3967-4109)
- Need GPT Actions API configuration
- Requires public-facing API endpoint
- Should include adaptive expertise detection

#### Prompt for AI Agent

```
Create ChatGPT GPT marketplace integration:

1. Create GPT configuration file (config/chatgpt_gpt.json):
   - Name: "Financial Intelligence Assistant"
   - Description: comprehensive market analysis tool
   - Instructions: detailed prompt for GPT behavior
   - Actions: map to FIML MCP tools
   - Conversation starters: engaging example queries
   - Capabilities: enable actions only (no browsing/code)
   - Include compliance instructions

2. Implement GPT Actions adapter (fiml/integrations/chatgpt.py):
   - ChatGPTAdapter class
   - Convert GPT action calls to MCP tool calls
   - Map parameters between formats
   - Handle authentication via API key
   - Rate limiting per user
   - Error handling with user-friendly messages
   - Log all interactions for analytics

3. Create public API endpoints (fiml/api/gpt_actions.py):
   - POST /api/v1/gpt/search-symbol
   - POST /api/v1/gpt/search-coin
   - POST /api/v1/gpt/get-narrative
   - POST /api/v1/gpt/execute-query (FK-DSL)
   - GET /api/v1/gpt/health
   - Authentication via X-API-Key header
   - CORS configuration for GPT access

4. Add user profiling (fiml/integrations/profiler.py):
   - UserProfiler class (from BLUEPRINT lines 4066-4108)
   - Detect expertise level from conversation
   - Track: beginner/intermediate/advanced/quant
   - Analyze vocabulary and questions
   - Adapt response complexity automatically
   - Store user preferences (optional)

5. Implement compliance guard (fiml/integrations/compliance_guard.py):
   - Pre-process GPT queries for investment advice
   - Block recommendation requests
   - Inject disclaimers into responses
   - Detect and redirect advice-seeking queries
   - Log compliance events

6. Create deployment guide (docs/chatgpt_deployment.md):
   - Step-by-step GPT creation
   - Actions configuration
   - API endpoint setup
   - Testing procedures
   - Publishing checklist
   - Monitoring setup

7. Add analytics tracking:
   - Track GPT usage metrics
   - Popular queries
   - User retention
   - Error rates
   - Export to Prometheus

Reference:
- BLUEPRINT.md Section 12.1 (lines 3967-4109)
- ChatGPT Actions API documentation
- OpenAI GPT Builder guidelines
- fiml/compliance/router.py for compliance

Success criteria:
- GPT configuration complete and valid
- API endpoints operational
- User profiler detects expertise accurately
- Compliance guard blocks advice requests
- GPT responds with narratives and data
- Analytics tracks usage
- Documentation complete for deployment
```

#### Files to Create/Modify
- **Create**: `config/chatgpt_gpt.json` (GPT configuration, 100-150 lines)
- **Create**: `fiml/integrations/__init__.py`
- **Create**: `fiml/integrations/chatgpt.py` (adapter, 200-250 lines)
- **Create**: `fiml/integrations/profiler.py` (user profiling, 150-200 lines)
- **Create**: `fiml/integrations/compliance_guard.py` (100-150 lines)
- **Create**: `fiml/api/__init__.py`
- **Create**: `fiml/api/gpt_actions.py` (API endpoints, 250-300 lines)
- **Create**: `docs/chatgpt_deployment.md` (deployment guide, 300+ lines)
- **Create**: `tests/test_chatgpt_integration.py` (200-250 lines)
- **Modify**: `fiml/server.py` (add GPT API routes)

#### Success Criteria
- [ ] GPT configuration validates
- [ ] API endpoints respond correctly
- [ ] User profiler works on sample conversations
- [ ] Compliance guard blocks investment advice
- [ ] GPT returns rich narratives
- [ ] Analytics track usage
- [ ] Deployment guide tested
- [ ] End-to-end test with GPT platform

---

### Task 8: Platform Integration - Telegram Bot

**Priority**: MEDIUM  
**Estimated Time**: 5-6 hours  
**Dependencies**: Task 6 (MCP + Narratives)

#### Objective
Build Telegram bot integration as specified in BLUEPRINT.md Section 11.4 for mobile access to FIML.

#### Context
- BLUEPRINT.md Section 11.4 outlines bot design (lines 3812-3961)
- Should support: search, subscribe, notifications
- Real-time watchdog event forwarding
- MCP backend integration

#### Prompt for AI Agent

```
Create Telegram bot integration:

1. Implement bot service (fiml/bots/telegram_bot.py):
   - TelegramBotService class
   - Initialize with python-telegram-bot library
   - Connect to Telegram Bot API
   - Handle bot lifecycle (start/stop)
   - Webhook or long polling mode
   - Rate limiting per user

2. Implement bot commands:
   /start - Welcome message + instructions
   /search <symbol> - Search stock/crypto
   /subscribe <symbol> - Subscribe to watchdog alerts
   /unsubscribe <symbol> - Unsubscribe
   /list - List subscriptions
   /help - Command help
   /settings - Configure language, depth, expertise
   /status - System status

3. Integrate with MCP tools:
   - /search calls search-by-symbol or search-by-coin
   - Format response for Telegram (Markdown)
   - Include price, change, key metrics
   - Add inline keyboard for actions (subscribe, analyze, chart)
   - Handle errors with user-friendly messages

4. Implement subscription system:
   - Store user subscriptions in Redis
   - Key: f"telegram:user:{user_id}:subscriptions"
   - Value: Set of symbols
   - Per-user subscription limits (10 free, 50 premium)

5. Add watchdog event forwarding:
   - Subscribe to event stream from watchdog
   - Match events to user subscriptions
   - Format events for Telegram
   - Include event severity emoji (🔴🟡🟢)
   - Respect user notification preferences

6. Create response formatters (fiml/bots/formatters.py):
   - format_market_data() - price + metrics
   - format_narrative() - truncate for mobile
   - format_watchdog_event() - alert message
   - format_error() - user-friendly errors
   - Add Telegram markdown styling

7. Implement user preferences:
   - Store in Redis per user
   - Language preference
   - Depth preference (quick/standard/deep)
   - Expertise level
   - Notification settings (all/critical only)
   - Timezone for timing

8. Add analytics:
   - Track command usage
   - Monitor active users
   - Popular symbols
   - Error rates
   - Export to Prometheus

9. Create deployment config:
   - Docker container for bot
   - Environment variables for bot token
   - Health checks
   - Graceful shutdown
   - Auto-restart on failure

Reference:
- BLUEPRINT.md Section 11.4 (lines 3812-3961)
- python-telegram-bot documentation
- fiml/mcp/tools.py for backend integration
- fiml/watchdog/ for event stream

Success criteria:
- Bot responds to all commands
- Searches return formatted results
- Subscriptions work and persist
- Watchdog alerts delivered in real-time
- Preferences saved and applied
- Bot handles high message volume
- Deployment tested in Docker
- Documentation for bot setup
```

#### Files to Create/Modify
- **Create**: `fiml/bots/__init__.py`
- **Create**: `fiml/bots/telegram_bot.py` (main bot, 400-500 lines)
- **Create**: `fiml/bots/formatters.py` (message formatting, 200-250 lines)
- **Create**: `fiml/bots/subscriptions.py` (subscription manager, 150-200 lines)
- **Create**: `fiml/bots/preferences.py` (user preferences, 100-150 lines)
- **Create**: `config/telegram_bot.yaml` (configuration)
- **Create**: `tests/test_telegram_bot.py` (300-400 lines)
- **Create**: `docs/telegram_bot_setup.md` (setup guide, 200+ lines)
- **Modify**: `docker-compose.yml` (add telegram bot service)
- **Modify**: `.env.example` (add TELEGRAM_BOT_TOKEN)

#### Success Criteria
- [ ] Bot responds to all commands
- [ ] Search command returns formatted data
- [ ] Subscriptions persist across restarts
- [ ] Watchdog events forward to subscribers
- [ ] Preferences save and load correctly
- [ ] Bot handles errors gracefully
- [ ] Deployment in Docker works
- [ ] Documentation tested
- [ ] End-to-end user flow tested

---

### Task 9: Session Management & State Persistence

**Priority**: MEDIUM  
**Estimated Time**: 4-5 hours  
**Dependencies**: None (independent)

#### Objective
Implement session management as outlined in BLUEPRINT.md Section 6 for stateful multi-step analysis.

#### Context
- BLUEPRINT.md Section 6 specifies session architecture (lines 1623-1693)
- Need persistent sessions for multi-query analysis
- Should track analysis history and context
- Support session resumption

#### Prompt for AI Agent

```
Implement session management system:

1. Create session models (fiml/sessions/models.py):
   - Session (id, user_id, type, assets, created_at, expires_at)
   - SessionState (context, history, preferences)
   - SessionType enum (equity, crypto, portfolio, comparative, macro)
   - AnalysisHistory (queries, results, timestamps)

2. Implement session store (fiml/sessions/store.py):
   - SessionStore class
   - Backend: Redis for active sessions
   - Backend: PostgreSQL for archived sessions
   - Methods:
     * create_session(assets, type, ttl) -> Session
     * get_session(session_id) -> Session
     * update_session(session_id, state)
     * delete_session(session_id)
     * list_user_sessions(user_id) -> List[Session]
     * extend_session(session_id, ttl)
   - Auto-expiration with configurable TTL
   - Session cleanup background task

3. Add session context tracking:
   - Track all queries in session
   - Store intermediate results
   - Build analysis context over time
   - Enable "remember previous query" capability
   - Context-aware suggestions

4. Implement MCP tool: create-analysis-session:
   - Create new session
   - Return session_id
   - Configure assets, type, TTL
   - Initialize session state

5. Enhance existing tools with session support:
   - Add optional session_id parameter
   - Load session context if provided
   - Update session history
   - Accumulate analysis data
   - Return session_id in response

6. Add session analytics:
   - Track session duration
   - Queries per session
   - Most analyzed assets
   - Session abandonment rate
   - Export metrics

7. Create session cleanup job:
   - Celery task to expire old sessions
   - Archive to PostgreSQL before deletion
   - Configurable retention policy
   - Run hourly

Reference:
- BLUEPRINT.md Section 6 (lines 1623-1693)
- fiml/cache/l1_cache.py for Redis patterns
- fiml/cache/l2_cache.py for PostgreSQL
- fiml/mcp/tools.py for tool integration

Success criteria:
- Sessions create and persist
- Context accumulates across queries
- Sessions expire correctly
- Cleanup job runs reliably
- Session state survives restarts
- Analytics track usage
- Tests cover lifecycle
- Integration test demonstrates multi-query session
```

#### Files to Create/Modify
- **Create**: `fiml/sessions/__init__.py`
- **Create**: `fiml/sessions/models.py` (100-150 lines)
- **Create**: `fiml/sessions/store.py` (250-300 lines)
- **Create**: `fiml/sessions/cleanup.py` (Celery task, 100 lines)
- **Create**: `tests/test_sessions.py` (200-250 lines)
- **Modify**: `fiml/mcp/tools.py` (add create-analysis-session tool, session support)
- **Modify**: `scripts/init-db.sql` (add sessions table if needed)

#### Success Criteria
- [ ] Sessions create successfully
- [ ] Context persists across queries
- [ ] Sessions expire on TTL
- [ ] Cleanup job tested
- [ ] Session resumption works
- [ ] Analytics functional
- [ ] Integration test shows multi-step analysis
- [ ] Documentation complete

---

### Task 10: Performance Testing & Optimization

**Priority**: HIGH  
**Estimated Time**: 5-6 hours  
**Dependencies**: Tasks 1-9 complete (end-to-end system)

#### Objective
Conduct comprehensive performance testing and optimization to meet BLUEPRINT.md targets (Section 18).

#### Context
- BLUEPRINT.md Section 18 specifies KPIs (lines 5008-5053)
- Targets: <200ms response, >80% cache hit, >95% completion rate
- No current performance benchmarks exist
- Need load testing infrastructure

#### Prompt for AI Agent

```
Create performance testing and optimization suite:

1. Build load testing framework (tests/performance/load_test.py):
   - Use locust or pytest-benchmark
   - Simulate concurrent users (10, 50, 100, 500, 1000)
   - Test scenarios:
     * Simple price queries (80% of traffic)
     * Deep analysis (15% of traffic)
     * FK-DSL queries (5% of traffic)
   - Measure:
     * Response time (p50, p95, p99)
     * Throughput (requests/second)
     * Error rate
     * Cache hit rate
     * Provider API calls

2. Create stress tests:
   - Peak load testing (2x normal traffic)
   - Spike testing (sudden 10x load)
   - Endurance testing (sustained load for 1 hour)
   - Provider failure scenarios
   - Database connection pool exhaustion
   - Redis max connections

3. Build benchmarking suite (benchmarks/):
   - Benchmark each component individually:
     * Provider fetches
     * Cache operations (L1, L2)
     * Narrative generation
     * Agent processing
     * FK-DSL execution
   - Compare against Phase 1 baseline
   - Track performance over time
   - Generate performance reports

4. Implement performance monitoring:
   - Add detailed timing to all operations
   - Track slow queries (>1 second)
   - Monitor provider latencies
   - Cache performance metrics
   - Export to Prometheus
   - Create Grafana dashboards

5. Identify and fix bottlenecks:
   - Profile with cProfile or py-spy
   - Identify slow database queries
   - Optimize N+1 query patterns
   - Reduce provider API calls
   - Minimize serialization overhead
   - Optimize cache key generation

6. Database optimization:
   - Add missing indexes
   - Optimize query patterns
   - Review TimescaleDB hypertable performance
   - Tune PostgreSQL configuration
   - Connection pool sizing
   - Query plan analysis

7. Add performance targets as tests:
   - Assert p95 < 200ms for cached queries
   - Assert cache hit rate > 80%
   - Assert task completion rate > 95%
   - Assert uptime > 99.5%
   - Fail CI if targets not met

8. Create performance regression detection:
   - Benchmark on each PR
   - Compare against main branch
   - Alert on >10% regression
   - Track trends over time

9. Generate performance report:
   - Summary dashboard
   - Comparison to BLUEPRINT targets
   - Bottleneck analysis
   - Optimization recommendations
   - Before/after metrics

Reference:
- BLUEPRINT.md Section 18 (lines 5008-5053)
- All implemented components
- Existing monitoring in fiml/server.py

Success criteria:
- Load tests run successfully
- Performance measured under various loads
- Bottlenecks identified and documented
- Optimizations implemented
- Performance meets or exceeds targets:
  * P95 latency < 200ms
  * Cache hit rate > 80%
  * Task completion > 95%
- Performance report generated
- Regression detection working
- Documentation for running tests
```

#### Files to Create
- **Create**: `tests/performance/__init__.py`
- **Create**: `tests/performance/load_test.py` (300-400 lines)
- **Create**: `tests/performance/stress_test.py` (200-250 lines)
- **Create**: `benchmarks/component_benchmarks.py` (250-300 lines)
- **Create**: `benchmarks/regression_detection.py` (150-200 lines)
- **Create**: `scripts/performance_report.py` (200-250 lines)
- **Create**: `docs/performance_testing.md` (documentation)
- **Modify**: `.github/workflows/ci.yml` (add performance tests)
- **Create**: `config/grafana/performance_dashboard.json` (Grafana config)

#### Success Criteria
- [ ] Load tests handle 1000 concurrent users
- [ ] P95 latency measured for all endpoints
- [ ] Cache hit rate tracked and optimized
- [ ] Bottlenecks identified and fixed
- [ ] Performance meets BLUEPRINT targets
- [ ] Regression detection prevents slowdowns
- [ ] Performance report comprehensive
- [ ] Documentation complete

---

## 🎯 Phase 2 Success Criteria

Phase 2 is complete when:

1. **Intelligence Layer** ✅
   - [ ] Azure OpenAI integration operational
   - [ ] Narrative generation produces quality output in 5 languages
   - [ ] All 7 agent workers use real data and AI insights
   - [ ] Watchdog system detects market anomalies

2. **Performance** ✅
   - [ ] Cache hit rate >90%
   - [ ] P95 latency <200ms
   - [ ] Task completion rate >95%
   - [ ] Handle 1000 concurrent users

3. **Platform Distribution** ✅
   - [ ] ChatGPT GPT deployed to marketplace
   - [ ] Telegram bot operational
   - [ ] Session management working

4. **Quality** ✅
   - [ ] 95%+ test coverage
   - [ ] All performance targets met
   - [ ] Security audit passed
   - [ ] Documentation complete

---

## 📊 Estimated Timeline

**Total Estimated Time**: 40-50 hours of development

**Recommended Sequence**:

Week 1:
- Task 1: Azure OpenAI Client (Day 1-2)
- Task 2: Narrative Generation (Day 2-4)
- Task 3: Enhanced Agents (Day 4-7)

Week 2:
- Task 5: Cache Optimization (Day 1-3)
- Task 6: MCP Tool Integration (Day 3-4)
- Task 9: Session Management (Day 5-7)

Week 3:
- Task 7: ChatGPT Integration (Day 1-3)
- Task 8: Telegram Bot (Day 3-5)
- Task 4: Watchdog System (Day 5-7)

Week 4:
- Task 10: Performance Testing (Day 1-3)
- Final integration testing (Day 4-5)
- Documentation and cleanup (Day 6-7)

---

## 🔄 Task Dependencies

```
Task 1 (Azure OpenAI) ─────┬─→ Task 2 (Narrative) ─→ Task 6 (MCP Integration)
                           │                               │
                           └─→ Task 3 (Agents) ──┬─────────┼─→ Task 7 (ChatGPT)
                                                 │         │
                                                 │         └─→ Task 8 (Telegram)
                                                 │
                           Task 5 (Cache) ───────┴─→ Task 4 (Watchdog)
                           Task 9 (Sessions) ──────────────┘

All Tasks ───────────────────────────────────────→ Task 10 (Performance)
```

---

## 📝 Notes for AI Agents

When executing these tasks:

1. **Context is Critical**: Each prompt includes references to BLUEPRINT.md sections and existing code. Read referenced files before starting.

2. **Follow Patterns**: Maintain consistency with existing code patterns in fiml/. Look at similar implementations as templates.

3. **Test Thoroughly**: Each task requires comprehensive tests. Aim for 90%+ coverage of new code.

4. **Document as You Go**: Add docstrings, comments, and update relevant .md files.

5. **Handle Errors Gracefully**: Financial data is critical - never crash, always degrade gracefully.

6. **Security First**: No hardcoded credentials, validate all inputs, sanitize outputs.

7. **Performance Matters**: Profile before optimizing, but keep performance in mind from the start.

8. **Compliance Always**: Every user-facing feature needs compliance checks and disclaimers.

---

## 🔐 Security Considerations

**For All Tasks**:
- Store API keys in environment variables only
- Validate all user inputs
- Rate limit all endpoints
- Log security events
- Never expose internal errors to users
- Sanitize LLM outputs to prevent injection
- Review OpenAI API usage for PII leakage

**Specific to Azure OpenAI**:
- Rotate keys regularly
- Monitor token usage for abuse
- Implement per-user rate limits
- Log all LLM interactions for audit
- Review generated content for compliance

---

## 📚 Additional Resources

**Azure OpenAI Documentation**:
- https://learn.microsoft.com/en-us/azure/cognitive-services/openai/

**Telegram Bot API**:
- https://core.telegram.org/bots/api

**ChatGPT Actions**:
- https://platform.openai.com/docs/actions

**MCP Protocol**:
- Current MCP implementation in fiml/mcp/

**Testing**:
- pytest patterns in tests/
- Existing test fixtures in tests/conftest.py

---

## ✅ Completion Checklist

Use this to track Phase 2 progress:

- [ ] Task 1: Azure OpenAI Client Integration
- [ ] Task 2: Narrative Generation Engine
- [ ] Task 3: Enhanced Agent Workers
- [ ] Task 4: Real-time Event Intelligence
- [ ] Task 5: Advanced Cache Optimization
- [ ] Task 6: MCP Tool Integration
- [ ] Task 7: ChatGPT GPT Integration
- [ ] Task 8: Telegram Bot Integration
- [ ] Task 9: Session Management
- [ ] Task 10: Performance Testing

**Phase 2 Complete**: [ ]

---

## 🔮 Phase 3+ Future Enhancements

Beyond Phase 2, the following advanced features are planned for FIML's evolution into a comprehensive financial OS:

### Backtesting Framework (Phase 3 - 2026+)
**Priority**: HIGH for quant users  
**Description**: Comprehensive backtesting engine for strategy validation

**Planned Features**:
- Historical data replay with tick-level accuracy
- Multi-asset strategy testing (stocks, crypto, options)
- Performance metrics: Sharpe ratio, max drawdown, win rate, etc.
- Monte Carlo simulation for robustness testing
- Walk-forward optimization
- Slippage and commission modeling
- Risk-adjusted return analysis
- Strategy comparison and benchmarking
- Integration with FK-DSL for strategy definition
- Export backtest results to standard formats (QuantConnect, Backtrader compatible)

**Technical Approach**:
- Leverage existing cache layer for historical data
- Use Ray for distributed backtesting across multiple strategies
- Store backtest results in TimescaleDB for time-series analysis
- Provide MCP tool: `backtest-strategy` with parameters:
  * Strategy definition (FK-DSL or Python code)
  * Time period (start/end dates)
  * Initial capital
  * Assets to trade
  * Risk parameters
  * Execution model (market/limit orders, slippage)

**Success Criteria**:
- Backtest 10+ years of daily data in <1 minute
- Support intraday strategies (1-minute bars)
- Accurate modeling of trading costs
- Statistical validation of strategy performance
- Overfitting detection and warnings
- Comprehensive performance reporting

**Dependencies**:
- Enhanced historical data in L2 cache
- Advanced agent workers (for strategy execution logic)
- Performance optimization (to handle large datasets)

**Related Features**:
- Portfolio optimization engine (use backtest results)
- Paper trading mode (forward testing)
- Strategy marketplace (share/discover strategies)

---

**Document Status**: Ready for AI Agent Execution  
**Last Updated**: November 23, 2025  
**Maintainer**: FIML Development Team  
**Version**: 1.0
