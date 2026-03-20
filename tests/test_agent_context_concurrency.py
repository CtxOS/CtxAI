import asyncio

import pytest
from ctxai.agent import AgentContext, AgentConfig
from ctxai.models import ModelConfig, ModelType


def make_config():
    return AgentConfig(
        chat_model=ModelConfig(type=ModelType.CHAT, provider="huggingface", name="some-model"),
        utility_model=ModelConfig(type=ModelType.CHAT, provider="huggingface", name="some-model"),
        embeddings_model=ModelConfig(type=ModelType.EMBEDDING, provider="sentence-transformers", name="all-MiniLM-L6-v2"),
        browser_model=ModelConfig(type=ModelType.BROWSER, provider="huggingface", name="some-model"),
        mcp_servers="",
    )


def test_agent_context_eviction_limits():
    # Keep the global context cache clean for this test.
    AgentContext._contexts.clear()

    AgentContext.set_max_contexts(1)
    config = make_config()
    first = AgentContext(config=config, name="first")
    second = AgentContext(config=config, name="second")

    assert len(AgentContext.all()) == 1
    assert AgentContext.all()[0].id == second.id

    AgentContext._contexts.clear()


def test_agent_context_task_timeout():
    AgentContext.set_max_concurrent_tasks(2)
    config = make_config()
    ctx = AgentContext(config=config, name="timeout-context")

    async def slow():
        await asyncio.sleep(0.15)
        return "done"

    task = ctx.run_task(slow)
    try:
        with pytest.raises(asyncio.TimeoutError):
            asyncio.run(task.result(timeout=0.01))
    finally:
        ctx.kill_process()


def test_agent_context_product_metrics_are_included_in_output():
    config = make_config()
    ctx = AgentContext(config=config, name="metrics-context")

    async def short_task():
        await asyncio.sleep(0.01)
        return "ok"

    task = ctx.run_task(short_task)
    asyncio.run(task.result())
    output = ctx.output()
    assert "product_metrics" in output
    assert output["product_metrics"]["tasks_started"] >= 1
    assert output["product_metrics"]["tasks_completed"] >= 1
