import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from fiml.core.models import Asset, AssetType, DataType
from fiml.providers.quandl import QuandlProvider
from fiml.core.exceptions import ProviderError

@pytest.fixture
def quandl_provider():
    return QuandlProvider(api_key="test_key")

@pytest.mark.asyncio
async def test_fetch_macro_success(quandl_provider):
    await quandl_provider.initialize()
    
    asset = Asset(symbol="GDP", asset_type=AssetType.INDEX)
    
    mock_response = {
        "dataset": {
            "data": [
                ["2023-01-01", 26185.21]
            ]
        }
    }
    
    with patch.object(quandl_provider, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        response = await quandl_provider.fetch_macro(asset)
        
        assert response.is_valid
        assert response.data_type == DataType.MACRO
        assert response.data["value"] == 26185.21
        assert response.metadata["source"] == "quandl"
        assert response.metadata["dataset"] == "FRED/GDP"
        
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        # params is second arg
        assert args[0] == "/datasets/FRED/GDP.json"

@pytest.mark.asyncio
async def test_fetch_macro_failure(quandl_provider):
    await quandl_provider.initialize()
    asset = Asset(symbol="INVALID", asset_type=AssetType.INDEX)
    
    with patch.object(quandl_provider, '_make_request', side_effect=ProviderError("API Error")):
        with pytest.raises(ProviderError):
            await quandl_provider.fetch_macro(asset)
