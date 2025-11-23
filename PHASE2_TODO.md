# FIML Phase 2 Todo List - Tasks Not Done Yet

**Document Created**: November 23, 2025  
**Last Updated**: November 23, 2025  
**Status**: Phase 2 Planning - Aligned with BLUEPRINT.md  
**Context**: Following completion of Phase 1, this document outlines Phase 2 tasks NOT YET DONE according to BLUEPRINT.md (Section 17, lines 4932-4953)

---

## 📋 Executive Summary

**Phase 2 Scope (per BLUEPRINT.md Section 17.2):**
Phase 2 focuses on **Enhancement & Scale (Q1-Q2 2026)** with these core goals:
- Expand platform distribution
- Add session management
- Launch mobile and bot interfaces
- Enhance caching and performance
- Integrate additional data providers

**Tasks NOT in Phase 2 (moved to Phase 3+):**
- ❌ Real-time watchdog system (8 watchdogs) → Phase 3 (Q3-Q4 2026)
- ❌ Unified event stream (Kafka) → Phase 3
- ❌ Narrative generation engine → Phase 3 (Q3-Q4 2026)
- ❌ Multi-language support (5 languages) → Phase 3
- ❌ Web app (Next.js) → Phase 3
- ❌ WhatsApp bot → Phase 3
- ❌ Self-updating schema system → 2027
- ❌ TV app → 2027

**Phase 2 Deliverables (per BLUEPRINT.md):**
1. ✅ Session management and state persistence (not done)
2. ✅ Expo mobile app (iOS/Android) (not done)
3. ✅ Telegram bot service (not done)
4. ✅ Additional data providers (Polygon.io, NewsAPI) (not done)
5. ✅ ChatGPT GPT marketplace launch (not done)
6. ✅ Enhanced caching and performance optimization (partially done)
7. ✅ Advanced multi-agent workflows (real data, not mock) (not done)

**Available Resources**:
- Existing agent framework (fiml/agents/) with 7 worker types
- 5 operational data providers (Yahoo Finance, Alpha Vantage, FMP, CCXT, custom)
- Complete L1/L2 caching infrastructure (Redis + PostgreSQL/TimescaleDB)
- MCP protocol foundation with 4 working tools
- Docker Compose production deployment

---

## 🔧 Configuration Prerequisites

### Environment Variables for Phase 2

Add these to `.env`:

```bash
# Additional Data Provider APIs (new in Phase 2)
POLYGON_IO_API_KEY=your_polygon_io_key
NEWSAPI_KEY=your_newsapi_key

# Telegram Bot (new in Phase 2)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram/webhook  # optional

# ChatGPT GPT Marketplace (new in Phase 2)
GPT_ACTIONS_API_KEY=your_gpt_actions_api_key
GPT_ACTIONS_BASE_URL=https://your-domain.com/api/v1/gpt

# Expo Mobile App (new in Phase 2)
EXPO_PROJECT_ID=your_expo_project_id
EXPO_PUSH_TOKEN=your_expo_push_token

# Session Management (new in Phase 2)
SESSION_TTL_SECONDS=3600  # default session time-to-live
SESSION_CLEANUP_INTERVAL=3600  # cleanup job interval
MAX_SESSIONS_PER_USER=10

# Performance Optimization
CACHE_WARMING_ENABLED=true
CACHE_EVICTION_STRATEGY=hybrid  # lru, lfu, hybrid
BATCH_UPDATE_INTERVAL=300  # seconds
```

---

## 📝 Phase 2 Tasks - NOT DONE YET (Per BLUEPRINT.md)

Each task below includes:
1. **Objective**: What to accomplish
2. **Context**: Current state and dependencies
3. **Prompt**: AI agent-ready instructions
4. **Files**: Where to make changes
5. **Success Criteria**: How to verify completion

---

### Task 1: Additional Data Provider Integration

**Priority**: HIGH  
**Estimated Time**: 6-8 hours  
**Dependencies**: Existing provider framework
**BLUEPRINT Reference**: Section 17.2, line 4943 - "Additional data providers (Polygon.io, NewsAPI)"

#### Objective
Integrate Polygon.io and NewsAPI as additional data providers to enhance data quality and coverage beyond current providers (Yahoo Finance, Alpha Vantage, FMP, CCXT).

#### Context
- Current state: 5 providers operational (Yahoo Finance, Alpha Vantage, FMP, CCXT, custom)
- Provider framework exists at fiml/providers/
- Data arbitration engine can handle multiple providers
- Need high-quality news data and enhanced market data

#### Prompt for AI Agent

```
Integrate two new data providers following existing provider patterns:

1. Create Polygon.io provider (fiml/providers/polygon_io.py):
   - PolygonIOProvider class extending BaseProvider
   - Implement methods:
     * async def get_quote(symbol: str) -> Quote
     * async def get_ohlcv(symbol: str, timeframe: str, limit: int) -> OHLCV
     * async def get_news(symbol: str, limit: int = 10) -> List[NewsArticle]
     * async def get_fundamentals(symbol: str) -> Fundamentals
   - Use Polygon.io REST API v2/v3
   - Handle rate limiting (5 requests/min on free tier, configurable)
   - Implement proper error handling
   - Add retry logic with exponential backoff
   - Cache responses appropriately

2. Create NewsAPI provider (fiml/providers/newsapi.py):
   - NewsAPIProvider class extending BaseProvider
   - Implement methods:
     * async def get_news(query: str, from_date: str, to_date: str) -> List[NewsArticle]
     * async def get_top_headlines(category: str, country: str) -> List[NewsArticle]
     * async def search_everything(q: str, language: str) -> List[NewsArticle]
   - Use NewsAPI v2 endpoints
   - Handle rate limiting (100 requests/day on free tier, 1000 on paid)
   - Parse and normalize news articles to common format
   - Extract sentiment indicators
   - Handle API errors gracefully

3. Register both providers in provider registry:
   - Modify fiml/providers/registry.py
   - Add to AVAILABLE_PROVIDERS
   - Configure priority/scoring for arbitration
   - Set appropriate TTL for each data type

4. Update data arbitration scoring:
   - Modify fiml/arbitration/engine.py
   - Add Polygon.io with high score for market data
   - Add NewsAPI with high score for news/sentiment
   - Configure fallback hierarchy

5. Add configuration:
   - Update fiml/core/config.py
   - Add settings for Polygon.io API key
   - Add settings for NewsAPI key
   - Add provider-specific rate limits
   - Add enable/disable flags

6. Create comprehensive tests:
   - tests/providers/test_polygon_io.py (200-250 lines)
   - tests/providers/test_newsapi.py (150-200 lines)
   - Mock API responses
   - Test error handling
   - Test rate limiting
   - Integration tests with arbitration engine

Reference:
- BLUEPRINT.md Section 17.2 (line 4943)
- fiml/providers/base.py for provider interface
- fiml/providers/yahoo_finance.py for implementation example
- fiml/providers/registry.py for registration pattern

Success criteria:
- Both providers fetch real data successfully
- Providers register with arbitration engine
- Rate limiting prevents API quota exhaustion
- Errors handled without crashing
- Tests achieve 90%+ coverage
- Integration test demonstrates multi-provider arbitration
```

#### Files to Create/Modify
- **Create**: `fiml/providers/polygon_io.py` (300-400 lines)
- **Create**: `fiml/providers/newsapi.py` (250-300 lines)
- **Create**: `tests/providers/test_polygon_io.py` (200-250 lines)
- **Create**: `tests/providers/test_newsapi.py` (150-200 lines)
- **Modify**: `fiml/providers/registry.py` (add new providers, ~50 lines)
- **Modify**: `fiml/core/config.py` (add settings, ~30 lines)
- **Modify**: `fiml/arbitration/engine.py` (update scoring, ~40 lines)
- **Modify**: `.env.example` (add API key placeholders)
- **Create**: `docs/providers/polygon_io.md` (documentation, 100+ lines)
- **Create**: `docs/providers/newsapi.md` (documentation, 100+ lines)

#### Success Criteria
- [ ] Polygon.io provider fetches quotes, OHLCV, news, fundamentals
- [ ] NewsAPI provider fetches news articles
- [ ] Both providers respect rate limits
- [ ] Providers register successfully
- [ ] Arbitration engine uses new providers
- [ ] Error handling tested
- [ ] Tests achieve 90%+ coverage
- [ ] Documentation complete

---

### Task 2: Enhanced Agent Workers with Real Data

**Priority**: CRITICAL  
**Estimated Time**: 8-10 hours  
**Dependencies**: Task 1 (more data providers help), existing agent framework
**BLUEPRINT Reference**: Section 17.2, line 4946 - "Advanced multi-agent workflows"

#### Objective
Replace mock implementations in agent workers with real data processing using actual provider data. Make workers production-ready with comprehensive analysis capabilities.

#### Context
- Current state: Workers return hardcoded mock data (fiml/agents/workers.py)
- BLUEPRINT.md Sections 5.2-5.5 specify worker capabilities
- Phase 1 completed: provider integration, caching, basic worker structure
- Phase 2 goal: Workers process real data and produce actionable insights
- 7 worker types: Fundamentals, Technical, Macro, Sentiment, Correlation, Risk, News

#### Prompt for AI Agent

```
Enhance fiml/agents/workers.py by replacing all mock implementations with real data processing:

For FundamentalsWorker:
1. Fetch real fundamental data via provider_registry
2. Try multiple providers in fallback order (FMP → Alpha Vantage → Yahoo Finance → Polygon.io)
3. Calculate financial ratios:
   - P/E ratio (price / earnings per share)
   - P/B ratio (price / book value per share)
   - Debt-to-Equity (total debt / shareholder equity)
   - Current Ratio (current assets / current liabilities)
   - ROE (net income / shareholder equity)
   - ROA (net income / total assets)
   - Profit margins (gross, operating, net)
4. Compare to sector/industry averages if available
5. Assess valuation (overvalued/fairly valued/undervalued) based on ratios
6. Return structured data with confidence scores (0-10)
7. Handle missing data gracefully (mark fields as N/A, reduce confidence)

For TechnicalWorker:
1. Fetch OHLCV data from cache/providers (100+ bars for indicators)
2. Calculate technical indicators:
   - RSI (14-period) using ta-lib or pandas-ta
   - MACD (12, 26, 9)
   - Bollinger Bands (20-period, 2 std dev)
   - Moving Averages: SMA (20, 50, 200), EMA (12, 26)
   - ATR (14-period) for volatility
   - OBV (On-Balance Volume) for volume analysis
3. Identify support/resistance levels from price action
4. Detect chart patterns (double top/bottom, head & shoulders, if feasible)
5. Generate signals:
   - RSI overbought (>70) / oversold (<30)
   - MACD crossovers
   - Price vs moving averages
6. Return indicators + interpretations + signals + confidence

For MacroWorker:
1. Fetch macro indicators from providers/custom sources:
   - US 10-Year Treasury yield
   - CPI (inflation data)
   - VIX (volatility index)
   - DXY (dollar index)
   - Unemployment rate
   - GDP growth
   - Fed Funds rate
2. Calculate correlation with target asset (30d, 90d rolling)
3. Identify macro regime (risk-on vs risk-off, inflationary vs deflationary)
4. Assess current macro environment impact on target asset
5. Return macro indicators + correlations + impact assessment

For SentimentWorker:
1. Fetch news articles from NewsAPI, Alpha Vantage News, FMP News, Polygon.io News
2. Analyze sentiment using:
   - Keyword-based scoring (bullish/bearish keywords)
   - If available, use FinBERT or similar NLP model for sentiment
   - Count positive vs negative headlines
3. Weight by source credibility (major outlets weighted higher)
4. Aggregate sentiment scores across sources
5. Identify sentiment trends (improving/declining/stable)
6. Return sentiment score (-1 to +1), supporting articles, trend direction

For CorrelationWorker:
1. Fetch price data for target asset + comparison assets (SPY, QQQ, relevant sector ETFs, BTC for crypto)
2. Calculate Pearson correlation coefficients (30d, 90d windows)
3. Compute rolling correlations to detect changes
4. Identify correlation breakdowns (correlation change >0.3)
5. Calculate beta vs market (SPY for stocks, BTC for crypto)
6. Return correlation matrix + rolling data + insights

For RiskWorker:
1. Fetch historical price data (1 year minimum)
2. Calculate risk metrics:
   - Volatility: historical (annualized standard deviation)
   - VaR (Value at Risk) at 95% and 99% confidence
   - Sharpe Ratio (if risk-free rate available)
   - Max Drawdown (largest peak-to-trough decline)
   - Downside Deviation (volatility of negative returns)
   - Beta (systematic risk vs market)
3. Classify risk level: Low (<15% vol), Medium (15-30%), High (30-50%), Extreme (>50%)
4. Generate risk warnings for high-risk assets
5. Return risk metrics + classification + warnings

For NewsWorker:
1. Fetch recent news from all available news providers (last 7 days)
2. Deduplicate articles (same event from multiple sources)
3. Extract key events and their timestamps
4. Assess impact level (high/medium/low) based on:
   - Article prominence (headline vs mention)
   - Source credibility
   - Keyword analysis (earnings, merger, lawsuit, etc.)
5. Detect market-moving news (unusual volume spike correlated with news timestamp)
6. Build event timeline
7. Return top 10 articles + event timeline + impact scores

Each worker should:
- Use provider_registry from fiml.providers.registry to fetch data
- Leverage L1/L2 cache for historical data (reduce API calls)
- Implement comprehensive error handling:
  * Provider failures (try alternates)
  * Missing data (partial results with warnings)
  * Invalid data (validation and filtering)
- Return consistent data structure:
  * scores: Dict[str, float] (0-10 scale)
  * data: Dict[str, Any] (structured results)
  * confidence: float (0.0-1.0)
  * warnings: List[str] (any issues encountered)
  * timestamp: datetime
  * sources: List[str] (providers used)
- Log all operations using fiml.core.logging.get_logger
- Be resilient to partial failures (return what's available)
- Include timing metrics for performance monitoring

Add integration tests (tests/agents/test_enhanced_workers.py):
- Mock provider responses with realistic data
- Test each worker independently
- Test error scenarios (provider down, bad data, missing data)
- Test scoring logic accuracy
- Verify consistency of output structure
- Integration test: run all workers on real symbol (AAPL, BTC)

Reference:
- BLUEPRINT.md Section 5 (lines 1313-1622) for worker specifications
- fiml/providers/registry.py for data access
- fiml/cache/ for caching patterns
- Existing worker structure in fiml/agents/workers.py
- fiml/agents/orchestrator.py for worker coordination

Success criteria:
- All 7 workers fetch real data (not mocks)
- Financial calculations are mathematically correct
- Workers handle missing/bad data without crashing
- All workers return consistent structure
- Tests achieve 85%+ coverage
- Integration test runs full analysis on AAPL and BTC
- Performance: each worker completes in <2 seconds for cached data
- Documentation explains each worker's algorithm
```

#### Files to Modify/Create
- **Refactor**: Split `fiml/agents/workers.py` into modular structure:
  - `fiml/agents/workers/__init__.py`
  - `fiml/agents/workers/fundamentals.py` (200-250 lines)
  - `fiml/agents/workers/technical.py` (200-250 lines)
  - `fiml/agents/workers/macro.py` (150-180 lines)
  - `fiml/agents/workers/sentiment.py` (180-220 lines)
  - `fiml/agents/workers/correlation.py` (120-150 lines)
  - `fiml/agents/workers/risk.py` (180-220 lines)
  - `fiml/agents/workers/news.py` (150-180 lines)
- **Create**: `fiml/agents/calculators.py` (shared calculation utilities, 250-300 lines)
- **Create**: `tests/agents/test_fundamentals_worker.py` (per-worker tests)
- **Create**: `tests/agents/test_technical_worker.py`
- **Create**: `tests/agents/test_macro_worker.py`
- **Create**: `tests/agents/test_sentiment_worker.py`
- **Create**: `tests/agents/test_correlation_worker.py`
- **Create**: `tests/agents/test_risk_worker.py`
- **Create**: `tests/agents/test_news_worker.py`
- **Create**: `tests/agents/test_enhanced_workers.py` (integration tests, 300-400 lines)
- **Modify**: `tests/test_agents.py` (update existing tests)
- **Create**: `docs/agents/worker_algorithms.md` (document calculation methods)

#### Success Criteria
- [ ] All 7 workers use real provider data
- [ ] Financial calculations verified accurate
- [ ] Indicators (RSI, MACD, etc.) calculated correctly
- [ ] Workers handle missing/bad data gracefully
- [ ] All workers return consistent output structure
- [ ] Tests cover success and failure scenarios
- [ ] Integration test demonstrates multi-agent analysis
- [ ] Performance meets targets (<2s per worker with cache)
- [ ] Documentation explains algorithms

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
---

### Task 11: Expo Mobile App (iOS/Android)

**Priority**: HIGH  
**Estimated Time**: 12-15 hours  
**Dependencies**: Task 6 (MCP tools), Task 2 (optional - enhanced workers)
**BLUEPRINT Reference**: Section 17.2, line 4941 - "Expo mobile app (iOS/Android)"

#### Objective
Create a cross-platform mobile app using Expo/React Native that provides mobile access to FIML's market intelligence capabilities.

#### Context
- BLUEPRINT.md Section 17.2 specifies Expo mobile app as Phase 2 deliverable
- Need native iOS and Android apps from single codebase
- Should provide search, analysis, and real-time updates
- Integration with WebSocket for live data
- Push notifications for watchdog events (if implemented)

#### Prompt for AI Agent

```
Create Expo mobile application for FIML:

1. Initialize Expo project structure (expo/):
   - Use Expo SDK 50+
   - TypeScript configuration
   - Navigation setup (React Navigation)
   - State management (Redux Toolkit or Zustand)
   - API client for FIML backend
   - Environment configuration (.env support)

2. Implement core screens:
   a) Home/Dashboard:
      - Popular symbols grid
      - Recent searches
      - Market overview (indices)
      - Quick search bar
      - Navigation to other screens
   
   b) Search Screen:
      - Symbol search input
      - Asset type selector (stock/crypto)
      - Recent searches list
      - Autocomplete suggestions
      - Navigation to detail screen
   
   c) Asset Detail Screen:
      - Price chart (react-native-chart-kit or Victory)
      - Key metrics display
      - Fundamentals tab (if stock)
      - Technical indicators tab
      - News tab
      - Narrative summary (collapsible)
      - Share functionality
   
   d) Watchlist Screen:
      - User watchlist management
      - Add/remove symbols
      - Real-time price updates
      - Swipe actions (delete, reorder)
      - Pull-to-refresh
   
   e) Settings Screen:
      - Language preference
      - Analysis depth preference
      - Expertise level selector
      - Notification settings
      - Theme (light/dark mode)
      - About/version info

3. Implement API integration (services/api.ts):
   - MCP tool calls via HTTP
   - search-by-symbol integration
   - search-by-coin integration
   - get-task-status for async queries
   - Error handling and retries
   - Loading states
   - Request cancellation

4. Implement WebSocket integration (services/websocket.ts):
   - Connect to FIML WebSocket endpoint
   - Subscribe to price updates
   - Subscribe to watchdog events (if available)
   - Reconnection logic
   - Connection status indicator
   - Update UI on real-time data

5. Implement state management:
   - Global state for user preferences
   - Cache for searched symbols
   - Watchlist state (synced to backend optionally)
   - Loading/error states
   - Offline support (cache recent data)

6. Add push notifications (if watchdog implemented):
   - Expo push notification setup
   - Register device token
   - Handle notification received
   - Handle notification tapped
   - Customize notification content
   - Deep linking to asset detail

7. Implement caching strategy:
   - AsyncStorage for user preferences
   - In-memory cache for recent queries
   - Offline fallback data
   - Cache invalidation strategy

8. Add UI/UX polish:
   - Loading skeletons
   - Error boundaries
   - Pull-to-refresh on lists
   - Smooth animations (Reanimated)
   - Dark mode support
   - Responsive layouts (tablet support)
   - Accessibility labels

9. Create build configuration:
   - EAS Build setup (Expo Application Services)
   - iOS bundle identifier
   - Android package name
   - App icons and splash screens
   - App store metadata (name, description)
   - Privacy policy and terms (links)

10. Add analytics:
    - Track screen views
    - Track search queries
    - Track errors
    - Export to Amplitude/Mixpanel (optional)
    - Privacy-respecting analytics

Reference:
- BLUEPRINT.md Section 17.2 (line 4941)
- BLUEPRINT.md Section 11.3 (lines 3723-3808) for Expo integration patterns
- Expo documentation (docs.expo.dev)
- React Navigation docs
- fiml/mcp/tools.py for API endpoints to call

Success criteria:
- App builds for iOS and Android
- Search and view asset details works
- Real-time price updates functional
- Watchlist management works
- Settings persist across sessions
- Push notifications delivered (if watchdog available)
- App runs smoothly on mid-range devices
- No crashes during normal usage
- App published to TestFlight/Google Play (internal testing)
```

#### Files to Create
- **Create**: `expo/` (entire Expo project directory)
  - `expo/app.json` (Expo configuration)
  - `expo/package.json` (dependencies)
  - `expo/tsconfig.json` (TypeScript config)
  - `expo/App.tsx` (root component, 100-150 lines)
  - `expo/src/screens/HomeScreen.tsx` (200-250 lines)
  - `expo/src/screens/SearchScreen.tsx` (150-200 lines)
  - `expo/src/screens/AssetDetailScreen.tsx` (300-400 lines)
  - `expo/src/screens/WatchlistScreen.tsx` (200-250 lines)
  - `expo/src/screens/SettingsScreen.tsx` (150-200 lines)
  - `expo/src/services/api.ts` (API client, 250-300 lines)
  - `expo/src/services/websocket.ts` (WebSocket client, 150-200 lines)
  - `expo/src/state/store.ts` (state management, 200-250 lines)
  - `expo/src/components/` (reusable components)
    - `PriceChart.tsx` (chart component, 150-200 lines)
    - `MetricCard.tsx` (metric display, 50-100 lines)
    - `SymbolSearch.tsx` (search input, 100-150 lines)
  - `expo/src/navigation/AppNavigator.tsx` (navigation setup, 100-150 lines)
  - `expo/src/hooks/` (custom hooks)
    - `useMarketData.ts` (data fetching hook, 100-150 lines)
    - `useWebSocket.ts` (WebSocket hook, 100-150 lines)
  - `expo/src/utils/` (utilities)
    - `formatting.ts` (number/date formatting, 100 lines)
    - `cache.ts` (caching utilities, 100-150 lines)
  - `expo/assets/` (images, icons, splash)
  - `expo/eas.json` (EAS Build configuration)
  - `expo/README.md` (setup and build instructions)

#### Success Criteria
- [ ] App initializes and runs on iOS simulator
- [ ] App initializes and runs on Android emulator
- [ ] Search functionality works
- [ ] Asset detail screen displays data
- [ ] Real-time updates work via WebSocket
- [ ] Watchlist can be managed
- [ ] Settings persist
- [ ] Push notifications work (if watchdog available)
- [ ] App builds successfully with EAS Build
- [ ] No crashes during testing
- [ ] Performance acceptable on devices
- [ ] Documentation for building and deploying

---

## 🎯 Phase 2 Success Criteria

Phase 2 is complete when ALL of these are achieved:

1. **Additional Data Providers** ✅
   - [ ] Polygon.io integrated and operational
   - [ ] NewsAPI integrated and operational
   - [ ] Both providers registered with arbitration engine
   - [ ] Data quality improved with new sources

2. **Enhanced Agent Workers** ✅
   - [ ] All 7 workers use real data (no mocks)
   - [ ] Workers produce accurate analysis
   - [ ] Error handling robust
   - [ ] Performance targets met (<2s per worker with cache)

3. **Platform Distribution** ✅
   - [ ] ChatGPT GPT deployed to marketplace
   - [ ] Telegram bot operational and responsive
   - [ ] Expo mobile app published to TestFlight/Google Play Beta
   - [ ] All platforms integrated with backend

4. **Session Management** ✅
   - [ ] Sessions create and persist
   - [ ] Multi-step analysis context tracked
   - [ ] Session cleanup working

5. **Performance** ✅
   - [ ] Cache hit rate >90%
   - [ ] P95 latency <200ms for cached queries
   - [ ] Task completion rate >95%
   - [ ] System handles 1000 concurrent users

6. **Quality** ✅
   - [ ] 90%+ test coverage on new code
   - [ ] All performance targets met
   - [ ] Security review passed
   - [ ] Documentation complete for all new features

---

## 📊 Estimated Timeline

**Total Estimated Time**: 50-65 hours of development work

**Recommended Sequence**:

Week 1 (Core Infrastructure):
- Task 1: Additional Data Providers (Day 1-2)
- Task 2: Enhanced Agent Workers (Day 2-5)
- Task 5: Cache Optimization (Day 5-7)

Week 2 (Session & Platform):
- Task 9: Session Management (Day 1-3)
- Task 7: ChatGPT Integration (Day 3-5)
- Task 8: Telegram Bot (Day 5-7)

Week 3 (Mobile & Testing):
- Task 11: Expo Mobile App (Day 1-5)
- Task 10: Performance Testing (Day 5-7)

Week 4 (Final Integration):
- Final integration testing (Day 1-3)
- Bug fixes and polish (Day 3-5)
- Documentation and deployment (Day 6-7)

---

## 🔄 Task Dependencies Graph

```
Task 1 (Data Providers) ───┬─→ Task 2 (Enhanced Agents) ─┬─→ Task 10 (Performance)
                            │                             │
Task 5 (Cache Opt) ─────────┴─────────────────────────────┤
                                                          │
Task 9 (Sessions) ────────────────────────────────────────┤
                                                          │
Task 7 (ChatGPT) ─────────────────────────────────────────┤
Task 8 (Telegram) ────────────────────────────────────────┤
Task 11 (Expo App) ───────────────────────────────────────┘
```

---

## 📝 Notes for Implementation

### Following Phase 2 Scope (per BLUEPRINT.md)
This document contains ONLY tasks specified for Phase 2 in BLUEPRINT.md Section 17.2 (lines 4932-4953):
1. ✅ Session management and state persistence (Task 9)
2. ✅ Expo mobile app (iOS/Android) (Task 11)
3. ✅ Telegram bot service (Task 8)
4. ✅ Additional data providers (Polygon.io, NewsAPI) (Task 1)
5. ✅ ChatGPT GPT marketplace launch (Task 7)
6. ✅ Enhanced caching and performance optimization (Task 5)
7. ✅ Advanced multi-agent workflows (Task 2 - real data processing)

### Tasks MOVED to Phase 3 (Q3-Q4 2026)
These are explicitly Phase 3 per BLUEPRINT.md Section 17.3 (lines 4956-4979):
- ❌ Real-time watchdog system (8 watchdogs)
- ❌ Unified event stream (Kafka)
- ❌ Narrative generation engine (Azure OpenAI integration)
- ❌ Multi-language support (5 languages)
- ❌ Web app (Next.js)
- ❌ WhatsApp bot
- ❌ Self-updating schema system (2027)
- ❌ TV app (2027)

### Implementation Notes
1. **Context is Critical**: Read referenced BLUEPRINT.md sections before starting each task
2. **Follow Existing Patterns**: Maintain consistency with Phase 1 code in fiml/
3. **Test Thoroughly**: Aim for 90%+ coverage on new code
4. **Document as You Go**: Add docstrings, comments, and update .md files
5. **Handle Errors Gracefully**: Financial data is critical - never crash
6. **Security First**: No hardcoded credentials, validate inputs, sanitize outputs
7. **Performance Matters**: Profile and optimize, meet targets
8. **Compliance Always**: Every user-facing feature needs disclaimers

### Security Considerations
- Store API keys in environment variables only
- Validate all user inputs (especially in bot commands and API endpoints)
- Rate limit all endpoints (prevent abuse)
- Log security events (failed auth, unusual patterns)
- Never expose internal errors to users
- Sanitize any generated content before displaying
- Review API usage for PII leakage

---

## 📚 Additional Resources

**Data Provider Documentation**:
- Polygon.io API: https://polygon.io/docs
- NewsAPI: https://newsapi.org/docs

**Mobile Development**:
- Expo Documentation: https://docs.expo.dev
- React Navigation: https://reactnavigation.org
- React Native Chart Kit: https://github.com/indiespirit/react-native-chart-kit

**Bot Development**:
- Telegram Bot API: https://core.telegram.org/bots/api
- python-telegram-bot: https://python-telegram-bot.readthedocs.io

**ChatGPT Integration**:
- ChatGPT Actions: https://platform.openai.com/docs/actions
- GPT Builder: https://help.openai.com/en/articles/8554397-gpt-builder

**FIML Codebase**:
- MCP Protocol: fiml/mcp/
- Providers: fiml/providers/
- Agents: fiml/agents/
- Testing: tests/

---

## ✅ Phase 2 Completion Checklist

Track your progress:

**Infrastructure & Data**:
- [ ] Task 1: Additional Data Providers (Polygon.io, NewsAPI)
- [ ] Task 2: Enhanced Agent Workers (real data)
- [ ] Task 5: Advanced Cache Optimization

**Platform Distribution**:
- [ ] Task 7: ChatGPT GPT Marketplace Integration
- [ ] Task 8: Telegram Bot Service
- [ ] Task 11: Expo Mobile App (iOS/Android)

**Core Features**:
- [ ] Task 9: Session Management & State Persistence

**Quality Assurance**:
- [ ] Task 10: Performance Testing & Optimization
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Security review completed

**Phase 2 Complete**: [ ]

When all tasks are checked, Phase 2 deliverables are complete and FIML is ready for Phase 3 (Q3-Q4 2026).

---

**Document Status**: Phase 2 Tasks - Not Done Yet (per BLUEPRINT.md)  
**Last Updated**: November 23, 2025  
**Maintainer**: FIML Development Team  
**Version**: 2.0 - Aligned with BLUEPRINT.md Phase 2 Scope
