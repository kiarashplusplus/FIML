"""
Tests for Market API router.

These tests verify the market API endpoints work correctly
and integrate with the FIML data adapter.
"""

import pytest
from fastapi.testclient import TestClient

from fiml.server import app


class TestMarketAPI:
    """Tests for Market API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_search_assets(self, client):
        """Test asset search endpoint"""
        response = client.get("/api/market/search?q=AAPL")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        # Should find Apple
        symbols = [asset["symbol"] for asset in data]
        assert "AAPL" in symbols

    def test_search_assets_by_name(self, client):
        """Test searching by company name"""
        response = client.get("/api/market/search?q=Apple")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) > 0
        assert any("AAPL" in asset["symbol"] for asset in data)

    def test_search_assets_filter_by_type(self, client):
        """Test filtering search by asset type"""
        response = client.get("/api/market/search?q=BT&asset_type=crypto")
        
        assert response.status_code == 200
        data = response.json()
        
        # All results should be crypto
        for asset in data:
            assert asset["type"] == "crypto"

    def test_search_assets_limit_results(self, client):
        """Test that search results are limited"""
        response = client.get("/api/market/search?q=a")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be limited to 10
        assert len(data) <= 10

    def test_get_prices_missing_symbols(self, client):
        """Test prices endpoint with no symbols"""
        response = client.get("/api/market/prices?symbols=")
        
        assert response.status_code == 400

    def test_get_prices_too_many_symbols(self, client):
        """Test prices endpoint with too many symbols"""
        # Create 51 symbols
        symbols = ",".join([f"SYM{i}" for i in range(51)])
        response = client.get(f"/api/market/prices?symbols={symbols}")
        
        assert response.status_code == 400
        assert "50" in response.json()["detail"]
