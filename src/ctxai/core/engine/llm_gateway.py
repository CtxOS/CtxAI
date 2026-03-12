from typing import Awaitable, Callable, Any
from langchain_core.messages import BaseMessage
from ctxai import models
from ctxai.core.common.metrics import metrics
from ctxai.core.common.tracing import span_context
from ctxai.shared import extension

# Define metrics
LLM_CALLS_TOTAL = metrics.counter("llm_calls_total", "Total number of LLM calls", ["type", "model"])
LLM_ERRORS_TOTAL = metrics.counter("llm_errors_total", "Total number of LLM call errors", ["type", "model"])

class LLMGateway:
    """
    Core Domain: LLM Gateway
    Extracts LiteLLM interface interactions, abstracting away Ctx AI specifics
    so that prompt calls can be made universally.
    """
    
    @staticmethod
    async def call_utility_model(
        agent: Any,
        config_model: models.ModelConfig,
        system: str,
        message: str,
        callback: Callable[[str], Awaitable[None]] | None = None,
        background: bool = False,
    ):
        model = models.get_chat_model(
            config_model.provider,
            config_model.name,
            model_config=config_model,
            **config_model.build_kwargs(),
        )

        # call extensions
        call_data = {
            "model": model,
            "system": system,
            "message": message,
            "callback": callback,
            "background": background,
        }
        await extension.call_extensions_async(
            "util_model_call_before", agent, call_data=call_data
        )

        # propagate stream to callback if set
        async def stream_callback(chunk: str, total: str):
            if call_data["callback"]:
                await call_data["callback"](chunk)

        LLM_CALLS_TOTAL.inc(labels={"type": "utility", "model": config_model.name})
        
        with span_context("llm_utility_call", {"model": config_model.name}):
            try:
                response, _reasoning = await call_data["model"].unified_call(
                    system_message=call_data["system"],
                    user_message=call_data["message"],
                    response_callback=stream_callback if call_data["callback"] else None,
                    rate_limiter_callback=(
                        agent.rate_limiter_callback if not call_data["background"] else None
                    ),
                )
            except Exception as e:
                LLM_ERRORS_TOTAL.inc(labels={"type": "utility", "model": config_model.name})
                raise e

        await extension.call_extensions_async(
            "util_model_call_after", agent, call_data=call_data, response=response
        )

        return response

    @staticmethod
    async def call_chat_model(
        agent: Any,
        config_model: models.ModelConfig,
        messages: list[BaseMessage],
        response_callback: Callable[[str, str], Awaitable[None]] | None = None,
        reasoning_callback: Callable[[str, str], Awaitable[None]] | None = None,
        background: bool = False,
        explicit_caching: bool = True,
    ):
        # model class
        model = models.get_chat_model(
            config_model.provider,
            config_model.name,
            model_config=config_model,
            **config_model.build_kwargs(),
        )

        LLM_CALLS_TOTAL.inc(labels={"type": "chat", "model": config_model.name})
        
        with span_context("llm_chat_call", {"model": config_model.name}):
            try:
                # call model
                response, reasoning = await model.unified_call(
                    messages=messages,
                    reasoning_callback=reasoning_callback,
                    response_callback=response_callback,
                    rate_limiter_callback=(
                        agent.rate_limiter_callback if not background else None
                    ),
                    explicit_caching=explicit_caching,
                )
            except Exception as e:
                LLM_ERRORS_TOTAL.inc(labels={"type": "chat", "model": config_model.name})
                raise e

        return response, reasoning
