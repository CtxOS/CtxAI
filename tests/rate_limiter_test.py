"""
Manual / exploratory script for rate-limiter smoke testing.

This was originally a top-level script that invoked the live OpenRouter API.
It has been wrapped in a pytest-skipped test so that the test suite can
collect it without making real network calls.  To run the smoke test manually:

    uv run python tests/rate_limiter_test.py
"""

import asyncio

import pytest


@pytest.mark.skip(reason="Exploratory smoke test that requires live OpenRouter API key – run manually")
@pytest.mark.asyncio
async def test_rate_limiter_smoke():
    import ctxai.models as models

    provider = "openrouter"
    name = "deepseek/deepseek-r1"

    model = models.get_chat_model(
        provider=provider,
        name=name,
        model_config=models.ModelConfig(
            type=models.ModelType.CHAT,
            provider=provider,
            name=name,
            limit_requests=5,
            limit_input=15000,
            limit_output=1000,
        ),
    )

    response, reasoning = await model.unified_call(user_message="Tell me a joke")
    print("Response: ", response)
    print("Reasoning: ", reasoning)


if __name__ == "__main__":
    asyncio.run(test_rate_limiter_smoke())
