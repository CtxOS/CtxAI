import sys

# Mock sentence_transformers to avoid import failure
import sys.modules


class MockModule:
    pass
sys.modules['sentence_transformers'] = MockModule()
sys.modules['sentence_transformers.SentenceTransformer'] = MockModule

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()
print("Env OPENROUTER_API_KEY:", os.environ.get("OPENROUTER_API_KEY", "None")[:5] + "...")
print("Env API_KEY_OPENROUTER:", os.environ.get("API_KEY_OPENROUTER", "None")[:5] + "...")

from backend.core.models import ModelConfig, ModelType, get_utility_model


async def main():
    try:
        config = ModelConfig(
            type=ModelType.CHAT,
            provider="openrouter",
            name="deepseek/deepseek-chat", # Use a common model to test
        )
        model = get_utility_model("openrouter", "deepseek/deepseek-chat", config)
        print("Model created. Kwargs:", model.kwargs)

        response, reasoning = await model.unified_call(
            system_message="Hello",
            user_message="Are you there?"
        )
        print("Success:", response)
    except Exception:
        import traceback
        traceback.print_exc()

asyncio.run(main())
