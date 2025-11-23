"""
Load Testing Framework for FIML

Uses locust for load testing with realistic traffic patterns.

Traffic Distribution:
- Simple price queries: 80%
- Deep analysis: 15%
- FK-DSL queries: 5%

Concurrent Users: 10, 50, 100, 500, 1000

Metrics:
- Response time (p50, p95, p99)
- Throughput (requests/second)
- Error rate
- Cache hit rate
- Provider API calls

Usage:
    # Run with 100 users, spawning 10 per second
    locust -f tests/performance/load_test.py --host=http://localhost:8000 --users 100 --spawn-rate 10

    # Run headless with report
    locust -f tests/performance/load_test.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 5m --headless \
           --html tests/performance/reports/load_test_report.html
"""

import random
from typing import List

from locust import HttpUser, TaskSet, between, task


class PriceQueryTasks(TaskSet):
    """Simple price query tasks (80% of traffic)"""

    # Popular symbols to query
    SYMBOLS = [
        "AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AMD",
        "BTC", "ETH", "SOL", "AVAX", "LINK", "UNI",
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD"
    ]

    @task(50)
    def get_price_simple(self):
        """Simple price query - most common operation"""
        symbol = random.choice(self.SYMBOLS)
        with self.client.get(
            "/mcp/tools/get_price",
            json={"symbol": symbol},
            catch_response=True,
            name="[Price] Simple Query"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Validate response structure
                if "price" in data or "content" in data:
                    response.success()
                else:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(20)
    def get_price_with_provider(self):
        """Price query with specific provider"""
        symbol = random.choice(self.SYMBOLS)
        provider = random.choice(["yahoo", "fmp", "ccxt"])

        with self.client.get(
            "/mcp/tools/get_price",
            json={"symbol": symbol, "provider": provider},
            catch_response=True,
            name="[Price] With Provider"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(15)
    def get_multiple_prices(self):
        """Batch price query"""
        symbols = random.sample(self.SYMBOLS, k=5)

        for symbol in symbols:
            with self.client.get(
                "/mcp/tools/get_price",
                json={"symbol": symbol},
                catch_response=True,
                name="[Price] Batch Query"
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Status code: {response.status_code}")
                    break

    @task(10)
    def get_market_data(self):
        """Get market data with history"""
        symbol = random.choice(self.SYMBOLS[:8])  # Equities only

        with self.client.get(
            "/mcp/tools/get_market_data",
            json={
                "symbol": symbol,
                "include_history": True,
                "days": 30
            },
            catch_response=True,
            name="[Market] Data with History"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(5)
    def health_check(self):
        """Health check endpoint"""
        with self.client.get(
            "/health",
            catch_response=True,
            name="[System] Health Check"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure("System unhealthy")
            else:
                response.failure(f"Status code: {response.status_code}")


class DeepAnalysisTasks(TaskSet):
    """Deep analysis tasks (15% of traffic)"""

    SYMBOLS = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "BTC", "ETH"]

    @task(40)
    def get_narrative(self):
        """Generate AI narrative"""
        symbol = random.choice(self.SYMBOLS)
        style = random.choice(["concise", "detailed", "technical", "fundamental"])

        with self.client.get(
            "/mcp/tools/generate_narrative",
            json={
                "symbol": symbol,
                "style": style,
                "include_context": True
            },
            catch_response=True,
            name="[Narrative] Generate"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(30)
    def analyze_sentiment(self):
        """Sentiment analysis"""
        symbol = random.choice(self.SYMBOLS)

        with self.client.get(
            "/mcp/tools/analyze_sentiment",
            json={"symbol": symbol},
            catch_response=True,
            name="[Analysis] Sentiment"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(20)
    def get_fundamentals(self):
        """Get fundamental data"""
        symbol = random.choice(self.SYMBOLS[:5])  # Equities only

        with self.client.get(
            "/mcp/tools/get_fundamentals",
            json={"symbol": symbol},
            catch_response=True,
            name="[Analysis] Fundamentals"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(10)
    def multi_asset_analysis(self):
        """Multi-asset portfolio analysis"""
        symbols = random.sample(self.SYMBOLS, k=3)

        with self.client.get(
            "/mcp/tools/analyze_portfolio",
            json={
                "symbols": symbols,
                "weights": [0.4, 0.35, 0.25]
            },
            catch_response=True,
            name="[Analysis] Portfolio"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class DSLQueryTasks(TaskSet):
    """FK-DSL query tasks (5% of traffic)"""

    DSL_QUERIES = [
        "GET PRICE OF AAPL",
        "GET PRICE OF BTC IN USD",
        "COMPARE AAPL WITH MSFT",
        "ANALYZE PORTFOLIO [AAPL:0.4, TSLA:0.3, MSFT:0.3]",
        "GET TECHNICAL INDICATORS FOR NVDA",
        "CALCULATE RSI FOR ETH PERIOD 14",
        "GET MOVING AVERAGE FOR GOOGL PERIOD 50",
    ]

    @task(60)
    def execute_dsl_query(self):
        """Execute FK-DSL query"""
        query = random.choice(self.DSL_QUERIES)

        with self.client.post(
            "/mcp/tools/execute_dsl",
            json={"query": query},
            catch_response=True,
            name="[DSL] Execute Query"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(20)
    def execute_complex_dsl(self):
        """Execute complex FK-DSL query"""
        queries = [
            "GET PRICE OF AAPL, MSFT, GOOGL",
            "ANALYZE CORRELATION BETWEEN AAPL AND TSLA PERIOD 30",
            "GET VOLATILITY FOR BTC PERIOD 14",
        ]
        query = random.choice(queries)

        with self.client.post(
            "/mcp/tools/execute_dsl",
            json={"query": query, "include_metadata": True},
            catch_response=True,
            name="[DSL] Complex Query"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(20)
    def validate_dsl(self):
        """Validate FK-DSL syntax"""
        query = random.choice(self.DSL_QUERIES)

        with self.client.post(
            "/mcp/tools/validate_dsl",
            json={"query": query},
            catch_response=True,
            name="[DSL] Validate"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class MetricsTask(TaskSet):
    """Collect performance metrics"""

    @task
    def get_metrics(self):
        """Get Prometheus metrics"""
        with self.client.get(
            "/metrics",
            catch_response=True,
            name="[Metrics] Prometheus"
        ) as response:
            if response.status_code == 200:
                # Parse metrics and track cache hit rate
                metrics_text = response.text

                # Extract cache hit rate if available
                for line in metrics_text.split('\n'):
                    if 'cache_hit_rate' in line and not line.startswith('#'):
                        try:
                            rate = float(line.split()[-1])
                            # Store in user environment for reporting
                            if hasattr(self.user, 'cache_hit_rates'):
                                self.user.cache_hit_rates.append(rate)
                        except:
                            pass

                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class FIMLUser(HttpUser):
    """
    FIML Load Testing User

    Simulates realistic user behavior with weighted task distribution:
    - 80% price queries
    - 15% deep analysis
    - 5% FK-DSL queries
    """

    # Wait time between tasks (1-5 seconds to simulate human behavior)
    wait_time = between(1, 5)

    # Track metrics
    cache_hit_rates: List[float] = []

    tasks = {
        PriceQueryTasks: 80,  # 80% of traffic
        DeepAnalysisTasks: 15,  # 15% of traffic
        DSLQueryTasks: 5,       # 5% of traffic
    }

    def on_start(self):
        """Called when a user starts"""
        # Could add authentication here if needed
        self.cache_hit_rates = []

    def on_stop(self):
        """Called when a user stops"""
        # Could log final metrics here
        if self.cache_hit_rates:
            avg_cache_hit_rate = sum(self.cache_hit_rates) / len(self.cache_hit_rates)
            print(f"User avg cache hit rate: {avg_cache_hit_rate:.2%}")


class HighLoadUser(FIMLUser):
    """User profile for high load testing (500-1000 users)"""
    wait_time = between(0.5, 2)  # Faster requests


class SpikeLoadUser(FIMLUser):
    """User profile for spike testing (sudden load increase)"""
    wait_time = between(0.1, 1)  # Very fast requests


# Additional user classes for different test scenarios
class CachedQueryUser(HttpUser):
    """User that only queries cached data (to test cache performance)"""
    wait_time = between(0.5, 2)

    CACHED_SYMBOLS = ["AAPL", "TSLA", "MSFT"]  # Pre-warmed symbols

    @task
    def query_cached_price(self):
        """Query pre-cached price"""
        symbol = random.choice(self.CACHED_SYMBOLS)
        with self.client.get(
            "/mcp/tools/get_price",
            json={"symbol": symbol},
            catch_response=True,
            name="[Cache] Cached Price"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


class UncachedQueryUser(HttpUser):
    """User that queries uncached data (cache miss scenarios)"""
    wait_time = between(1, 3)

    # Use random symbols to force cache misses
    @task
    def query_random_price(self):
        """Query random uncached price"""
        # Generate random symbol to force cache miss
        symbol = f"TEST{random.randint(1000, 9999)}"
        with self.client.get(
            "/mcp/tools/get_price",
            json={"symbol": symbol},
            catch_response=True,
            name="[Cache] Uncached Price"
        ) as response:
            # Accept 404 as success (symbol doesn't exist)
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")
