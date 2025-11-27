"""
Test FK-DSL Integration with Telegram Bot
Basic smoke tests to verify functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fiml.bot.adapters.telegram_adapter import DSL_TEMPLATES, TelegramBotAdapter
from fiml.bot.core.key_manager import UserProviderKeyManager
from fiml.bot.core.provider_configurator import FIMLProviderConfigurator
from fiml.bot.education.gamification import GamificationEngine


@pytest.fixture
def mock_telegram_update():
    """Create mock Telegram update object"""
    update = MagicMock()
    update.effective_user.id = "test_user_123"
    update.effective_user.first_name = "Test"
    update.message.reply_text = AsyncMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram context object"""
    context = MagicMock()
    context.user_data = {}
    return context


@pytest.fixture
def bot_adapter():
    """Create TelegramBotAdapter instance for testing"""
    with patch('fiml.bot.adapters.telegram_adapter.Application'):
        key_manager = MagicMock(spec=UserProviderKeyManager)
        provider_configurator = MagicMock(spec=FIMLProviderConfigurator)
        gamification = MagicMock(spec=GamificationEngine)
        gamification.award_xp = AsyncMock()
        
        adapter = TelegramBotAdapter(
            token="test_token",
            key_manager=key_manager,
            provider_configurator=provider_configurator,
            gamification=gamification
        )
        return adapter


@pytest.mark.asyncio
async def test_cmd_fkdsl_displays_templates(bot_adapter, mock_telegram_update, mock_context):
    """Test that /fkdsl command displays query templates"""
    await bot_adapter.cmd_fkdsl(mock_telegram_update, mock_context)
    
    # Verify message was sent
    assert mock_telegram_update.message.reply_text.called
    call_args = mock_telegram_update.message.reply_text.call_args
    
    # Check that message contains FK-DSL info
    message_text = call_args[0][0]
    assert "FK-DSL" in message_text
    assert "EVALUATE" in message_text
    assert "COMPARE" in message_text
    assert "CORRELATE" in message_text
    assert "SCAN" in message_text


@pytest.mark.asyncio
async def test_dsl_templates_defined():
    """Test that DSL templates are properly defined"""
    assert len(DSL_TEMPLATES) > 0
    
    # Check required templates
    assert "analyze_stock" in DSL_TEMPLATES
    assert "compare_tech" in DSL_TEMPLATES
    assert "correlate_crypto" in DSL_TEMPLATES
    assert "scan_stocks" in DSL_TEMPLATES
    assert "custom" in DSL_TEMPLATES
    
    # Verify template structure
    for template_id, template_data in DSL_TEMPLATES.items():
        assert "display" in template_data
        assert "query" in template_data or template_id == "custom"
        assert "description" in template_data
        assert "example" in template_data


@pytest.mark.asyncio
async def test_execute_dsl_query_success(bot_adapter, mock_telegram_update, mock_context):
    """Test successful DSL query execution"""
    
    mock_result = {
        "query": "EVALUATE AAPL: PRICE",
        "status": "completed",
        "result": {
            "AAPL": {
                "price": 150.25,
                "volume": 50000000
            }
        }
    }
    
    with patch('fiml.bot.adapters.telegram_adapter.execute_fk_dsl', new_callable=AsyncMock) as mock_dsl:
        mock_dsl.return_value = mock_result
        
        await bot_adapter.execute_user_dsl_query(
            update=mock_telegram_update,
            context=mock_context,
            user_id="test_user_123",
            query="EVALUATE AAPL: PRICE",
            from_callback=False
        )
        
        # Verify execute_fk_dsl was called
        assert mock_dsl.called
        assert mock_dsl.call_args[1]['query'] == "EVALUATE AAPL: PRICE"
        
        # Verify response was sent
        assert mock_telegram_update.message.reply_text.called
        
        # Verify XP was awarded
        assert bot_adapter.gamification.award_xp.called


@pytest.mark.asyncio
async def test_execute_dsl_query_failure(bot_adapter, mock_telegram_update, mock_context):
    """Test DSL query execution with error handling"""
    
    with patch('fiml.bot.adapters.telegram_adapter.execute_fk_dsl', new_callable=AsyncMock) as mock_dsl:
        mock_dsl.side_effect = Exception("Invalid DSL syntax")
        
        await bot_adapter.execute_user_dsl_query(
            update=mock_telegram_update,
            context=mock_context,
            user_id="test_user_123",
            query="INVALID QUERY",
            from_callback=False
        )
        
        # Verify error message was sent
        assert mock_telegram_update.message.reply_text.called
        call_args = mock_telegram_update.message.reply_text.call_args
        error_message = call_args[0][0]
        
        assert "Query Execution Failed" in error_message
        assert "Invalid DSL syntax" in error_message


@pytest.mark.asyncio
async def test_format_dsl_result_completed(bot_adapter):
    """Test formatting of completed DSL results"""
    
    result = {
        "query": "EVALUATE AAPL: PRICE",
        "status": "completed",
        "result": {
            "AAPL": {
                "price": 150.25,
                "volume": 50000000
            }
        }
    }
    
    formatted = await bot_adapter.format_dsl_result(result, "EVALUATE AAPL: PRICE")
    
    assert "Query Completed" in formatted
    assert "AAPL" in formatted
    assert "150.25" in formatted
    assert "Educational purposes only" in formatted


@pytest.mark.asyncio
async def test_format_dsl_result_failed(bot_adapter):
    """Test formatting of failed DSL results"""
    
    result = {
        "query": "INVALID QUERY",
        "status": "failed",
        "error": "Syntax error at position 5"
    }
    
    formatted = await bot_adapter.format_dsl_result(result, "INVALID QUERY")
    
    assert "Query Failed" in formatted
    assert "Syntax error" in formatted
    assert "Educational purposes only" in formatted


@pytest.mark.asyncio
async def test_format_dsl_result_running(bot_adapter):
    """Test formatting of running DSL results (async mode)"""
    
    result = {
        "query": "EVALUATE AAPL: PRICE",
        "status": "running",
        "task_id": "task_12345",
        "total_steps": 5
    }
    
    formatted = await bot_adapter.format_dsl_result(result, "EVALUATE AAPL: PRICE")
    
    assert "Query Running" in formatted
    assert "task_12345" in formatted
    assert "5 steps" in formatted


@pytest.mark.asyncio
async def test_format_dsl_result_respects_telegram_limits(bot_adapter):
    """Test that formatted results respect Telegram's 4096 character limit"""
    
    # Create very large result
    large_result = {
        "query": "SCAN US_TECH",
        "status": "completed",
        "result": {f"STOCK_{i}": {"price": 100.0 + i} for i in range(500)}
    }
    
    formatted = await bot_adapter.format_dsl_result(large_result, "SCAN US_TECH")
    
    # Verify it's under the limit
    assert len(formatted) <= 4096
    
    # Should contain truncation notice if truncated
    if len(large_result) > 4000:
        assert "truncated" in formatted.lower()


@pytest.mark.asyncio
async def test_handle_dsl_template_custom(bot_adapter, mock_telegram_update, mock_context):
    """Test handling of custom template selection"""
    
    mock_telegram_update.callback_query.data = "dsl_template:custom"
    
    await bot_adapter.handle_dsl_template(mock_telegram_update, mock_context)
    
    # Verify message was edited with custom query instructions
    assert mock_telegram_update.callback_query.edit_message_text.called
    call_args = mock_telegram_update.callback_query.edit_message_text.call_args
    message = call_args[0][0]
    
    assert "Custom FK-DSL Query" in message
    assert "EVALUATE" in message
    assert "COMPARE" in message
    
    # Verify context flag set
    assert mock_context.user_data.get("awaiting_dsl_query") is True


@pytest.mark.asyncio
async def test_handle_dsl_template_predefined(bot_adapter, mock_telegram_update, mock_context):
    """Test handling of predefined template selection"""
    
    mock_telegram_update.callback_query.data = "dsl_template:analyze_stock"
    
    mock_result = {
        "query": "EVALUATE AAPL: PRICE, VOLUME, VOLATILITY(30d)",
        "status": "completed",
        "result": {"AAPL": {"price": 150.25}}
    }
    
    with patch('fiml.bot.adapters.telegram_adapter.execute_fk_dsl', new_callable=AsyncMock) as mock_dsl:
        mock_dsl.return_value = mock_result
        
        await bot_adapter.handle_dsl_template(mock_telegram_update, mock_context)
        
        # Verify template message was shown
        assert mock_telegram_update.callback_query.edit_message_text.called
        
        # Verify query was executed
        assert mock_dsl.called
