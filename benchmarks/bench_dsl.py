"""
Performance benchmarks for FK-DSL Parser
"""

from fiml.dsl.parser import FKDSLParser


class TestDSLBenchmarks:
    """Benchmarks for DSL parsing and execution"""

    def test_parse_simple_query(self, benchmark):
        """Benchmark parsing a simple GET query"""
        parser = FKDSLParser()
        query = "GET PRICE FOR AAPL"

        def parse_query():
            return parser.parse(query)

        result = benchmark(parse_query)
        assert result is not None

    def test_parse_analyze_query(self, benchmark):
        """Benchmark parsing an ANALYZE query"""
        parser = FKDSLParser()
        query = "ANALYZE AAPL FOR TECHNICALS"

        def parse_query():
            return parser.parse(query)

        result = benchmark(parse_query)
        assert result is not None

    def test_parse_compare_query(self, benchmark):
        """Benchmark parsing a COMPARE query"""
        parser = FKDSLParser()
        query = "COMPARE AAPL, TSLA BY PRICE, VOLUME"

        def parse_query():
            return parser.parse(query)

        result = benchmark(parse_query)
        assert result is not None

    def test_parse_find_query(self, benchmark):
        """Benchmark parsing a FIND query with conditions"""
        parser = FKDSLParser()
        query = "FIND AAPL WITH PRICE > 100"

        def parse_query():
            return parser.parse(query)

        result = benchmark(parse_query)
        assert result is not None

    def test_parse_track_query(self, benchmark):
        """Benchmark parsing a TRACK query"""
        parser = FKDSLParser()
        query = "TRACK AAPL WHEN PRICE > 150"

        def parse_query():
            return parser.parse(query)

        result = benchmark(parse_query)
        assert result is not None

    def test_parser_initialization(self, benchmark):
        """Benchmark parser initialization overhead"""

        def init_parser():
            return FKDSLParser()

        result = benchmark(init_parser)
        assert result is not None

    def test_parse_multiple_queries(self, benchmark):
        """Benchmark parsing multiple queries including parser initialization"""
        queries = [
            "GET PRICE FOR AAPL",
            "ANALYZE TSLA FOR FUNDAMENTALS",
            "COMPARE AAPL, TSLA BY PRICE, VOLUME",
            "FIND AAPL WITH PRICE > 100",
            "TRACK AAPL WHEN VOLUME > 1000000",
        ]

        def parse_multiple():
            # Parser creation included to measure total overhead
            parser = FKDSLParser()
            results = []
            for query in queries:
                results.append(parser.parse(query))
            return results

        results = benchmark(parse_multiple)
        assert len(results) == 5

    def test_parse_with_reused_parser(self, benchmark):
        """Benchmark query parsing with parser reuse (excludes initialization)"""
        parser = FKDSLParser()
        query = "GET PRICE FOR AAPL"

        def parse_query():
            return parser.parse(query)

        result = benchmark(parse_query)
        assert result is not None
