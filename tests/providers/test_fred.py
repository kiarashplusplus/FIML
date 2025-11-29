import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from fiml.core.models import Asset, AssetType, DataType
from fiml.providers.fred import FredProvider
from fiml.core.exceptions import ProviderError

@pytest.fixture
def fred_provider():
    return FredProvider(api_key="test_key")

@pytest.mark.asyncio
async def test_fred_initialization(fred_provider):
    await fred_provider.initialize()
    assert fred_provider._is_initialized
    assert fred_provider._session is not None
    await fred_provider.shutdown()
    assert not fred_provider._is_initialized

@pytest.mark.asyncio
async def test_fetch_macro_success(fred_provider):
    await fred_provider.initialize()
    
    asset = Asset(symbol="GDP", asset_type=AssetType.INDEX)
    
    mock_response = {
        "observations": [
            {
                "date": "2023-01-01",
                "value": "26185.21"
            }
        ]
    }
    
    with patch.object(fred_provider, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        
        response = await fred_provider.fetch_macro(asset)
        
        assert response.is_valid
        assert response.data_type == DataType.MACRO
        assert response.data["value"] == 26185.21
        assert response.metadata["source"] == "fred"
        
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        # params is the second positional argument
        assert args[1]["series_id"] == "GDP"

@pytest.mark.asyncio
async def test_fetch_macro_mapped_symbol(fred_provider):
    await fred_provider.initialize()
    
    # UNEMPLOYMENT maps to UNRATE
    asset = Asset(symbol="UNEMPLOYMENT", asset_type=AssetType.INDEX)
    
    mock_response = {
        "observations": [{"date": "2023-10-01", "value": "3.9"}]
    }
    
    with patch.object(fred_provider, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        await fred_provider.fetch_macro(asset)
        
        args, kwargs = mock_request.call_args
        assert args[1]["series_id"] == "UNRATE"

@pytest.mark.asyncio
async def test_fetch_macro_failure(fred_provider):
    await fred_provider.initialize()
    asset = Asset(symbol="INVALID", asset_type=AssetType.INDEX)
    
    with patch.object(fred_provider, '_make_request', side_effect=ProviderError("API Error")):
        with pytest.raises(ProviderError):
            await fred_provider.fetch_macro(asset)
