import asyncio
import hashlib
import json
import re
import time
from typing import Any

from ctxai.agent import Agent, AgentContext


def clean_text(raw: str) -> str:
    if raw is None:
        return ""
    text = str(raw).strip()
    text = re.sub(r"\s+", " ", text)
    # Remove non-printable characters.
    text = "".join(ch for ch in text if 32 <= ord(ch) <= 126 or ch == "\n")
    # Redact common secrets.
    text = re.sub(r"(api_key|token|password)=\S+", "[REDACTED]", text, flags=re.IGNORECASE)
    return text


def detect_intent(text: str) -> str:
    lc = (text or "").lower()
    if "exploit" in lc or "malware" in lc or "payload" in lc:
        return "security_attack"
    if "scan" in lc or "recon" in lc or "enumerate" in lc:
        return "recon"
    if "fix" in lc or "debug" in lc or "solve" in lc:
        return "remediation"
    if "summarize" in lc or "explain" in lc:
        return "summarize"
    if "status" in lc or "health" in lc or "metrics" in lc:
        return "observability"
    if "gpt" in lc or "assistant" in lc or "chat" in lc:
        return "conversation"
    return "unknown"


def extract_entities(text: str) -> dict[str, Any]:
    if not text:
        return {}
    entities: dict[str, Any] = {}
    # Simple extraction for common patterns
    m = re.search(r"\b(domain|host|ip|url)=([\w\.-]+)\b", text, flags=re.IGNORECASE)
    if m:
        entities[m.group(1).lower()] = m.group(2)
    return entities


def risk_score_for_context(cleaned: str, intent: str, entities: dict[str, Any]) -> int:
    score = 1
    text = (cleaned or "").lower()
    if "exploit" in text or "payload" in text or "rce" in text:
        score += 90
    if "scan" in text or "recon" in text:
        score += 5
    if intent == "security_attack":
        score += 10
    if entities:
        score += 2
    return min(100, score)


def fingerprint_context(cleaned: str, intent: str, entities: dict[str, Any]) -> str:
    input_data = cleaned + "|" + intent + "|" + json.dumps(entities, sort_keys=True)
    return hashlib.sha256(input_data.encode("utf-8")).hexdigest()


def _context_to_payload(ctx: AgentContext) -> dict[str, Any]:
    return {
        "raw": ctx.data.get("raw", "") if ctx.data else "",
        "source": f"agent_context:{ctx.id}",
        "timestamp": time.time(),
        "metadata": {
            "context_id": ctx.id,
            "name": ctx.name,
            "type": ctx.type.value if ctx.type else "unknown",
        },
        "agent": ctx.agent0,
    }


async def _process_payload(payload: dict[str, Any], default_agent: Agent | None = None) -> dict[str, Any]:
    raw = payload.get("raw", "")
    source = payload.get("source", "")
    cleaned = clean_text(raw)
    intent = payload.get("intent") or detect_intent(cleaned)
    entities = payload.get("entities") or extract_entities(cleaned)

    agent = payload.get("agent") or default_agent
    memory_refs: list[dict[str, Any]] = []
    if agent and hasattr(agent, "memory"):
        try:
            # Use recall_by_query if available
            recall = getattr(agent.memory, "recall_by_query", None)
            if callable(recall) and cleaned:
                memory_refs = recall(cleaned, top_k=3)
            elif hasattr(agent.memory, "get_observations"):
                memory_refs = agent.memory.get_observations()
        except Exception:
            memory_refs = []

    embeddings = []
    if cleaned and agent and hasattr(agent, "get_embedding_model"):
        try:
            emb_model = agent.get_embedding_model()
            if hasattr(emb_model, "embed_query"):
                embeddings = emb_model.embed_query(cleaned)
        except Exception:
            embeddings = []

    risk = risk_score_for_context(cleaned, intent, entities)
    fingerprint = fingerprint_context(cleaned, intent, entities)

    return {
        "raw": raw,
        "source": source,
        "timestamp": payload.get("timestamp", time.time()),
        "cleaned": cleaned,
        "intent": intent,
        "entities": entities,
        "embeddings": embeddings,
        "risk_score": risk,
        "memory_refs": memory_refs,
        "fingerprint": fingerprint,
        "metrics": payload.get("metrics", {}),
    }


async def load_metrics(
    payloads: list[dict[str, Any]],
    options: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Load and enrich context payloads asynchronously.

    payloads: list of dicts with keys:
      - raw (required)
      - source (optional)
      - timestamp (optional)
      - metadata (optional)
      - agent (optional): Agent instance used to resolve embeddings/memory

    options:
      - batch_size: int (default 50)
      - parallel: bool (default True)
      - default_agent: Agent (optional)
      - include_metrics: bool (default True)
    """
    opts = options or {}
    batch_size = int(opts.get("batch_size", 50))
    parallel = bool(opts.get("parallel", True))
    default_agent = opts.get("default_agent")
    include_metrics = bool(opts.get("include_metrics", True))

    results: list[dict[str, Any]] = []
    start_all = time.time()
    for i in range(0, len(payloads), batch_size):
        batch = payloads[i : i + batch_size]
        start = time.time()

        tasks = [_process_payload(payload, default_agent) for payload in batch]
        if parallel:
            processed_batch = await asyncio.gather(*tasks)
        else:
            processed_batch = []
            for t in tasks:
                processed_batch.append(await t)

        end = time.time()
        latency_ms = int((end - start) * 1000)
        batch_metrics = {
            "batch_size": len(batch),
            "latency_ms": latency_ms,
            "throughput_per_sec": len(batch) / max(0.001, (end - start)),
        }

        for idx, ctx in enumerate(processed_batch):
            if include_metrics:
                payload_metrics = ctx.get("metrics", {})
                ctx["metrics"] = {**payload_metrics, **batch_metrics}
            results.append(ctx)

    end_all = time.time()
    if options is not None and options.get("collect_aggregate_metrics"):
        results.append({
            "aggregate": True,
            "total_payloads": len(payloads),
            "wallclock_ms": int((end_all - start_all) * 1000),
        })
    return results


async def load_metrics_from_contexts(
    contexts: list[AgentContext],
    options: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    payloads = [_context_to_payload(c) for c in contexts]
    return await load_metrics(payloads, options=options)
