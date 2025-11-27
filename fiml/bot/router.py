"""
Bot Router
Exposes UnifiedBotGateway via REST API for mobile/web clients.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from fiml.bot.core.gateway import UnifiedBotGateway
from fiml.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Singleton instance of the gateway
# In a production environment with multiple workers, this means session state
# is per-worker unless SessionManager uses Redis (which is planned).
_gateway: Optional[UnifiedBotGateway] = None


def get_gateway() -> UnifiedBotGateway:
    """Get or create the singleton gateway instance"""
    global _gateway
    if _gateway is None:
        logger.info("Initializing UnifiedBotGateway for REST API")
        _gateway = UnifiedBotGateway()
    return _gateway


class BotMessageRequest(BaseModel):
    """Request model for bot messages"""

    user_id: str
    platform: str = "mobile_app"
    text: str
    context: Optional[Dict[str, Any]] = None


class BotMessageResponse(BaseModel):
    """Response model for bot messages"""

    text: str
    media: List[str] = []
    actions: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


@router.post("/message", response_model=BotMessageResponse)
async def handle_bot_message(request: BotMessageRequest) -> BotMessageResponse:
    """
    Handle a message from a client (mobile/web) and return the bot's response.
    """
    gateway = get_gateway()

    try:
        response = await gateway.handle_message(
            platform=request.platform,
            user_id=request.user_id,
            text=request.text,
            context=request.context,
        )

        return BotMessageResponse(
            text=response.text,
            media=response.media or [],
            actions=response.actions or [],
            metadata=response.metadata or {},
        )

    except Exception as e:
        logger.error(f"Error handling bot message: {e}", user_id=request.user_id)
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")
