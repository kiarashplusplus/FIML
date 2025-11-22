"""
Performance benchmarks for FK-DSL Parser and Executor
"""

import pytest
from fiml.dsl.parser import FKDSLParser
from fiml.dsl.executor import FKDSLExecutor


class TestDSLBenchmarks:
    """Benchmarks for DSL parsing and execution"""

    def test_parse_simple_query(self, benchmark):
        """Benchmark parsing a simple EVALUATE query"""
        parser = FKDSLParser()
        query = "EVALUATE AAPL: PRICE"
        
        def parse_query():
            return parser.parse(query)
        
        result = benchmark(parse_query)
        assert result is not None

    def test_parse_complex_query(self, benchmark):
        """Benchmark parsing a complex multi-metric query"""
        parser = FKDSLParser()
        query = "EVALUATE TSLA: PRICE, VOLATILITY(30d), CORRELATE(BTC, SPY), TECHNICAL(RSI, MACD)"
        
        def parse_query():
            return parser.parse(query)
        
        result = benchmark(parse_query)
        assert result is not None

    def test_parse_compare_query(self, benchmark):
        """Benchmark parsing a COMPARE query"""
        parser = FKDSLParser()
        query = "COMPARE BTC vs ETH vs SOL ON: VOLUME(7d), LIQUIDITY, MOMENTUM(14d)"
        
        def parse_query():
            return parser.parse(query)
        
        result = benchmark(parse_query)
        assert result is not None

    def test_parse_scan_query(self, benchmark):
        """Benchmark parsing a SCAN query with filters"""
        parser = FKDSLParser()
        query = "SCAN NASDAQ WHERE VOLUME > AVG_VOLUME(30d) * 2 AND PRICE_CHANGE(1d) > 5%"
        
        def parse_query():
            return parser.parse(query)
        
        result = benchmark(parse_query)
        assert result is not None

    def test_parse_macro_query(self, benchmark):
        """Benchmark parsing a MACRO analysis query"""
        parser = FKDSLParser()
        query = "MACRO: US10Y, CPI, VIX, DXY"
        
        def parse_query():
            return parser.parse(query)
        
        result = benchmark(parse_query)
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_simple_query(self, benchmark):
        """Benchmark executing a simple query"""
        parser = FKDSLParser()
        executor = FKDSLExecutor()
        
        query = "EVALUATE AAPL: PRICE"
        ast = parser.parse(query)
        
        async def execute_query():
            return await executor.execute(ast)
        
        result = await benchmark.pedantic(execute_query, rounds=5)
        assert result is not None

    def test_parser_initialization(self, benchmark):
        """Benchmark parser initialization overhead"""
        
        def init_parser():
            return FKDSLParser()
        
        result = benchmark(init_parser)
        assert result is not None

    def test_parse_multiple_queries(self, benchmark):
        """Benchmark parsing multiple queries in sequence"""
        parser = FKDSLParser()
        queries = [
            "EVALUATE AAPL: PRICE",
            "EVALUATE TSLA: VOLATILITY(30d)",
            "COMPARE BTC vs ETH ON: VOLUME(7d)",
            "MACRO: VIX, DXY",
            "SCAN NASDAQ WHERE VOLUME > 1000000",
        ]
        
        def parse_multiple():
            results = []
            for query in queries:
                results.append(parser.parse(query))
            return results
        
        results = benchmark(parse_multiple)
        assert len(results) == 5
