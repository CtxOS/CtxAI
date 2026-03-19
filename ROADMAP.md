# Ctx AI Roadmap

> Last updated: 2026-03-19

---

## ✅ Completed (Recent)

### 🔐 Security Hardening
- Centralised `safe_eval.py` — sanitised metadata filter evaluation (dunder-key rejection, primitive-only values, fail-closed)
- Context capacity limits — `MAX_CONTEXTS=64` with LRU eviction of non-running contexts
- Concurrency limits — `MAX_CONCURRENT_TASKS=16` semaphore on agent execution
- Plugin API auth enforcement — all plugin handlers require auth+CSRF+API-key regardless of class overrides
- Login rate limiting — 10 attempts / 5 min window on `/login`
- Startup warning when auth is not configured
- Trace correlation — `trace_id` on `AgentContext` and `LogItem` output

### 🏗️ Architecture Layers
- **Reasoning Engine** (`helpers/reasoning_engine.py`) — prompt assembly, LLM calls, tool resolution & execution; stateless service layer
- **Agent Orchestrator** (`helpers/agent_orchestrator.py`) — monologue loop, process chain, message-loop lifecycle
- **Event Bus** (`helpers/event_bus.py`) — typed publish/subscribe for 15+ framework lifecycle events
- `Agent` class reduced 27% (993→727 lines) — all `@extension.extensible` methods preserved as thin delegates

### 🤖 Agent System
- **Task Router** (`helpers/task_router.py`) — priority `TaskQueue` (heap-based), `TaskRouter` with skill-based agent dispatch, `AgentSkillProfile` with load tracking
- **Orchestrator Agent** (`helpers/orchestrator_agent.py`) — worker pool, per-task timeouts (`asyncio.wait_for`), retry with exponential backoff, result tracking
- **Retry/Fallback** — `execute_tool_with_retry()` wrapping base `execute_tool()` with configurable max_retries, delay, fallback tool
- **Agent Memory** — `AgentMemory` class with observations (transient, TTL), facts (persistent via `MemoryManager`), rolling tool results window
- **Per-Context Timeouts** — `AgentContext.timeout` field enforced in `run_task()`

### 🧠 Memory & Context
- **MemoryManager** (`helpers/memory_manager.py`) — unified `remember/retrieve/forget` API with importance scoring, TTL, and memory type (short/long)
- **Pluggable Backends** — `InMemoryBackend` (default), `QdrantBackend` stub with graceful fallback
- **Importance-Aware Compression** — `Message.importance` field; compression skips high-importance messages; bulk eviction by importance ascending
- **Budget Eviction** — `forget(policy="budget")` and `forget(policy="age")` for controlled memory limits

### 🏷️ CI/CD
- `.github/labeler.yml` — path-based PR labels (agent, reasoning, memory, tools, plugins, api, webui, config, docker, ci, tests, docs, prompts)
- `.github/workflows/labeler.yml` — auto-label PRs on open/sync
- `.github/workflows/pre-commit.yml` — runs pre-commit hooks in CI

### 🔧 Misc
- Script permissions — all `.sh` files in `scripts/` set to executable

---

## 🔄 In Progress

### Memory Backends
- [ ] Full Qdrant integration (embedding computation, vector search, multi-tenant collections)
- [ ] Chroma backend implementation
- [ ] Redis backend for high-concurrency short-term memory

### Observability
- [ ] Structured metrics export (Prometheus/OpenTelemetry)
- [ ] Dashboard for agent context pool, task queue depth, memory stats

---

## 📋 Planned

### High Priority
- [ ] **Streaming tool responses** — tool execute returns async iterator for progressive output
- [ ] **Agent skill profiles in agent.yaml** — declare skills per agent, auto-register with `TaskRouter`
- [ ] **Context-aware agent selection** — map incoming tasks to "skill agents" (tool/agent roles)
- [ ] **Graceful degradation** — fallback to simpler model when primary model fails/overloads

### Medium Priority
- [ ] **Multi-tenant isolation** — per-user context pools and memory namespaces
- [ ] **Conversation branching** — snapshot and restore context state for explore/backtrack
- [ ] **Knowledge graph integration** — structured knowledge beyond vector similarity
- [ ] **Plugin sandboxing** — restrict plugin filesystem and network access

### Low Priority
- [ ] **Agent personality system** — persistent persona traits learned from interactions
- [ ] **Collaborative memory** — shared memory pool across agent instances
- [ ] **Webhook triggers** — external events drive agent tasks (email, git push, cron)
- [ ] **Mobile-friendly API** — lightweight endpoints for mobile clients

---

## Architecture (Current)

```
┌─────────────────────────────────────────────────────────────┐
│                    API / WebUI / WebSocket                   │
├─────────────────────────────────────────────────────────────┤
│                     Agent Orchestrator                       │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │ Process Chain │  │  Monologue Loop│  │  Intervention   │  │
│  └──────────────┘  └────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Reasoning Engine                          │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │ Prompt Build │  │  LLM Invocation │  │ Tool Execution  │  │
│  └──────────────┘  └────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │  History/    │  │  MemoryManager │  │   Vector DB     │  │
│  │  Compression │  │  (short/long)  │  │   (FAISS)       │  │
│  └──────────────┘  └────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│         EventBus  ·  Extensions  ·  Plugins                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Contributing

See [AGENTS.md](./AGENTS.md) for development patterns, [docs/](./docs/) for architecture deep dives.
