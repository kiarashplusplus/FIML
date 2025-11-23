"""
Performance benchmarks for Core FIML Components
"""

from fiml.core.models import Asset, AssetType, Market


class TestCoreModelBenchmarks:
    """Benchmarks for core model operations"""

    def test_asset_creation(self, benchmark):
        """Benchmark Asset model creation"""

        def create_asset():
            return Asset(
                symbol="AAPL",
                name="Apple Inc.",
                asset_type=AssetType.EQUITY,
                market=Market.US,
                exchange="NASDAQ",
                currency="USD",
            )

        result = benchmark(create_asset)
        assert result.symbol == "AAPL"

    def test_asset_validation(self, benchmark, benchmark_asset):
        """Benchmark Asset model validation"""

        def validate_asset():
            # Pydantic validation happens on creation, so we create a new instance
            return Asset(
                symbol=benchmark_asset.symbol,
                name=benchmark_asset.name,
                asset_type=benchmark_asset.asset_type,
                market=benchmark_asset.market,
                exchange=benchmark_asset.exchange,
                currency=benchmark_asset.currency,
            )

        result = benchmark(validate_asset)
        assert result is not None

    def test_asset_dict_conversion(self, benchmark, benchmark_asset):
        """Benchmark Asset to dict conversion"""

        def to_dict():
            return benchmark_asset.model_dump()

        result = benchmark(to_dict)
        assert isinstance(result, dict)

    def test_asset_json_serialization(self, benchmark, benchmark_asset):
        """Benchmark Asset JSON serialization"""

        def to_json():
            return benchmark_asset.model_dump_json()

        result = benchmark(to_json)
        assert isinstance(result, str)

    def test_batch_asset_creation(self, benchmark):
        """Benchmark batch creation of assets"""

        symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AMD", "INTC", "NFLX"]

        def create_batch():
            assets = []
            for symbol in symbols:
                asset = Asset(
                    symbol=symbol,
                    name=f"{symbol} Inc.",
                    asset_type=AssetType.EQUITY,
                    market=Market.US,
                    exchange="NASDAQ",
                    currency="USD",
                )
                assets.append(asset)
            return assets

        results = benchmark(create_batch)
        assert len(results) == 10

    def test_crypto_asset_creation(self, benchmark):
        """Benchmark crypto asset creation"""

        def create_crypto():
            return Asset(
                symbol="BTC",
                name="Bitcoin",
                asset_type=AssetType.CRYPTO,
                market=Market.CRYPTO,
                exchange="binance",
                currency="USDT",
            )

        result = benchmark(create_crypto)
        assert result.asset_type == AssetType.CRYPTO
