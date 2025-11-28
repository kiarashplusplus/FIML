"""
API Key Management Router
Provides REST endpoints for managing user API keys from mobile/web clients.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from fiml.bot.core.key_manager import UserProviderKeyManager
from fiml.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Singleton instance
_key_service: Optional[UserProviderKeyManager] = None


def get_key_service() -> UserProviderKeyManager:
    """Get or create the singleton key service instance"""
    global _key_service
    if _key_service is None:
        logger.info("Initializing UserProviderKeyManager for REST API")
        _key_service = UserProviderKeyManager()
    return _key_service



class Provider(BaseModel):
    """Provider model"""
    name: str
    displayName: str
    isConnected: bool
    description: Optional[str] = None


class AddKeyRequest(BaseModel):
    """Request model for adding API key"""
    provider: str
    api_key: str
    api_secret: Optional[str] = None


class ValidateKeyRequest(BaseModel):
    """Request model for validating API key format"""
    api_key: str


class KeyResponse(BaseModel):
    """Response model for key operations"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


@router.get("/api/user/{user_id}/keys")
async def get_provider_status(
    user_id: str,
    authorization: Optional[str] = Header(None)
) -> Dict[str, List[Provider]]:
    """
    Get the status of all providers for a user.
    Returns which providers have keys configured.
    """
    service = get_key_service()

    try:
        # Get all configured providers
        user_keys = await service.list_keys(user_id)

        # Define available providers
        all_providers = [
            {
                "name": "binance",
                "displayName": "Binance",
                "description": "Crypto trading data and market information",
            },
            {
                "name": "coinbase",
                "displayName": "Coinbase",
                "description": "Cryptocurrency exchange integration",
            },
            {
                "name": "alphavantage",
                "displayName": "Alpha Vantage",
                "description": "Stock market data and financial indicators",
            },
            {
                "name": "yfinance",
                "displayName": "Yahoo Finance",
                "description": "Free stock and market data (no key required)",
            },
        ]

        # Mark which providers are connected
        providers = []
        for provider_info in all_providers:
            is_connected = provider_info["name"] in user_keys
            providers.append(Provider(
                name=provider_info["name"],
                displayName=provider_info["displayName"],
                isConnected=is_connected,
                description=provider_info.get("description"),
            ))

        return {"providers": [p.model_dump() for p in providers]}

    except Exception as e:
        logger.error("Error fetching provider status", user_id=user_id, error=str(e))
        # Return default providers on error
        return {
            "providers": [
                {"name": "binance", "displayName": "Binance", "isConnected": False, "description": "Crypto trading data and market information"},
                {"name": "coinbase", "displayName": "Coinbase", "isConnected": False, "description": "Cryptocurrency exchange integration"},
                {"name": "alphavantage", "displayName": "Alpha Vantage", "isConnected": False, "description": "Stock market data"},
                {"name": "yfinance", "displayName": "Yahoo Finance", "isConnected": False, "description": "Free stock data"},
            ]
        }


@router.post("/api/user/{user_id}/keys/{provider}/validate-format")
async def validate_key_format(
    user_id: str,
    provider: str,
    request: ValidateKeyRequest,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Validate API key format without storing it.
    Provides real-time format validation feedback.

    Returns:
        200: Format validation result with details
        400: Unknown provider
    """
    service = get_key_service()

    try:
        # Check if provider is supported
        provider_info = service.get_provider_info(provider)
        if not provider_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown provider: {provider}"
            )

        # Validate format using backend patterns
        is_valid = service.validate_key_format(provider, request.api_key)

        # Get format description
        format_info = service._service.KEY_PATTERNS.get(provider)

        response_data = {
            "valid": is_valid,
            "provider": provider,
            "key_length": len(request.api_key)
        }

        if is_valid:
            response_data["message"] = f"Valid {provider} key format"
        else:
            response_data["message"] = f"Invalid format for {provider}"
            if format_info:
                response_data["expected_pattern"] = format_info

        logger.debug(
            "Format validation",
            provider=provider,
            valid=is_valid,
            key_length=len(request.api_key)
        )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error validating key format", provider=provider, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate format: {str(e)}"
        )


@router.post("/api/user/{user_id}/keys", status_code=status.HTTP_201_CREATED)
async def add_key(
    user_id: str,
    request: AddKeyRequest,
    authorization: Optional[str] = Header(None)
) -> KeyResponse:
    """
    Add a new API key for a provider.

    Returns:
        201: Key added successfully
        400: Invalid provider or key format
        500: Internal server error
    """
    service = get_key_service()

    try:
        # Validate provider exists
        provider_info = service.get_provider_info(request.provider)
        if not provider_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown provider: {request.provider}"
            )

        # Add the key
        await service.add_key(
            user_id=user_id,
            provider=request.provider,
            api_key=request.api_key,
            api_secret=request.api_secret,
        )

        logger.info("API key added successfully", user_id=user_id, provider=request.provider)

        return KeyResponse(
            success=True,
            message=f"{request.provider.capitalize()} API key added successfully"
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error("Error adding API key", user_id=user_id, provider=request.provider, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add API key: {str(e)}"
        )


@router.post("/api/user/{user_id}/keys/{provider}/test")
async def test_key(
    user_id: str,
    provider: str,
    authorization: Optional[str] = Header(None)
) -> KeyResponse:
    """
    Test if an API key is valid by making a test request to the provider's API.

    Returns:
        200: Key tested successfully
        404: No API key found for provider
        400: Key validation failed
        500: Internal server error
    """
    service = get_key_service()

    try:
        # Get the decrypted API key
        api_key = await service.get_key(user_id, provider)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No API key found for {provider}"
            )

        # Test the key with actual provider API
        test_result = await service.test_provider_key(provider, api_key)

        if test_result["valid"]:
            logger.info(
                "API key test passed",
                user_id=user_id,
                provider=provider,
                tier=test_result.get("tier")
            )

            return KeyResponse(
                success=True,
                message=f"{provider.capitalize()}: {test_result['message']}"
            )
        else:
            logger.warning(
                "API key test failed",
                user_id=user_id,
                provider=provider,
                reason=test_result.get("message")
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Key validation failed: {test_result['message']}"
            )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(
            "Error testing API key",
            user_id=user_id,
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test API key: {str(e)}"
        )


@router.delete("/api/user/{user_id}/keys/{provider}")
async def remove_key(
    user_id: str,
    provider: str,
    authorization: Optional[str] = Header(None)
) -> KeyResponse:
    """
    Remove an API key for a provider.

    Returns:
        200: Key removed successfully
        404: No API key found for provider
        500: Internal server error
    """
    service = get_key_service()

    try:
        # Check if key exists first
        existing_key = await service.get_key(user_id, provider)
        if not existing_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No API key found for {provider}"
            )

        # Remove the key
        await service.remove_key(user_id, provider)

        logger.info("API key removed successfully", user_id=user_id, provider=provider)

        return KeyResponse(
            success=True,
            message=f"{provider.capitalize()} API key removed successfully"
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error("Error removing API key", user_id=user_id, provider=provider, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove API key: {str(e)}"
        )
