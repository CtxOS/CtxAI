import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from ctxai.core.engine.llm_gateway import LLMGateway
import ctxai.models as models

@pytest.mark.asyncio
async def test_call_utility_model():
    mock_agent = MagicMock()
    mock_agent.rate_limiter_callback = None
    
    mock_config = MagicMock(spec=models.ModelConfig)
    mock_config.provider = "openai"
    mock_config.name = "gpt-4o"
    mock_config.build_kwargs.return_value = {}
    
    mock_model = AsyncMock()
    mock_model.unified_call.return_value = ("result", "reasoning")
    
    with patch("a0.core.engine.llm_gateway.models.get_chat_model", return_value=mock_model):
        response = await LLMGateway.call_utility_model(
            agent=mock_agent,
            config_model=mock_config,
            system="system",
            message="message"
        )
        
        assert response == "result"
        mock_model.unified_call.assert_called_once()

@pytest.mark.asyncio
async def test_call_chat_model():
    mock_agent = MagicMock()
    
    mock_config = MagicMock(spec=models.ModelConfig)
    mock_config.provider = "anthropic"
    mock_config.name = "claude-3-5-sonnet"
    mock_config.build_kwargs.return_value = {}
    
    mock_model = AsyncMock()
    mock_model.unified_call.return_value = ("chat result", "chat reasoning")
    
    with patch("a0.core.engine.llm_gateway.models.get_chat_model", return_value=mock_model):
        response, reasoning = await LLMGateway.call_chat_model(
            agent=mock_agent,
            config_model=mock_config,
            messages=[]
        )
        
        assert response == "chat result"
        assert reasoning == "chat reasoning"
        mock_model.unified_call.assert_called_once()
