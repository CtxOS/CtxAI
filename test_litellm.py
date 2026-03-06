import asyncio
from backend.core.models import get_utility_model, ModelConfig, ModelType
from litellm import acompletion
import logging

async def main():
    try:
        config = ModelConfig(
            type=ModelType.CHAT,
            provider="openrouter",
            name="openai/gpt-3.5-turbo",
        )
        model = get_utility_model("openrouter", "openai/gpt-3.5-turbo", config)
        print("Model created")
        
        response, reasoning = await model.unified_call(
            system_message="Hello",
            user_message="Are you there?"
        )
        print("Success:", response)
    except Exception as e:
        print("Error:", e)
        print(type(e))

asyncio.run(main())
