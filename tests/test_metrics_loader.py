import asyncio

from ctxai.agent import AgentConfig, AgentContext
from ctxai.helpers.metrics_loader import load_metrics, load_metrics_from_contexts
from ctxai.models import ModelConfig, ModelType


def make_config():
    return AgentConfig(
        chat_model=ModelConfig(type=ModelType.CHAT, provider="huggingface", name="some-model"),
        utility_model=ModelConfig(type=ModelType.CHAT, provider="huggingface", name="some-model"),
        embeddings_model=ModelConfig(
            type=ModelType.EMBEDDING,
            provider="sentence-transformers",
            name="all-MiniLM-L6-v2",
        ),
        browser_model=ModelConfig(type=ModelType.CHAT, provider="huggingface", name="some-model"),
        mcp_servers="",
    )


def test_load_metrics_basic():
    payloads = [
        {"raw": "scan example.com and enumerate ports", "source": "test", "metadata": {"team": "red"}},
        {"raw": "please summarize today's logs", "source": "test"},
    ]
    results = asyncio.run(load_metrics(payloads, options={"batch_size": 1, "parallel": False}))
    assert len(results) == 2
    assert results[0]["intent"] in ("recon", "unknown")
    assert "cleaned" in results[0]
    assert "fingerprint" in results[0]
    assert results[0]["metrics"]["batch_size"] == 1


def test_load_metrics_from_contexts():
    config = make_config()
    ctx = AgentContext(config=config, name="test-context")
    ctx.set_data("raw", "exploit test target")
    results = asyncio.run(load_metrics_from_contexts([ctx], options={"batch_size": 1, "parallel": False}))
    assert len(results) == 1
    assert results[0]["intent"] == "security_attack"
    assert results[0]["risk_score"] > 1
