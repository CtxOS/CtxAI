# Ctx AI Roadmap

> Last updated: 2026-03-19

---

## ✅ Completed

### 🔐 Security
| Item | Detail |
|------|--------|
| Safe eval | `safe_eval.py` — primitive-only values, dunder-key rejection, fail-closed |
| Context limits | `MAX_CONTEXTS=64`, LRU eviction of non-running contexts |
| Concurrency limits | `MAX_CONCURRENT_TASKS=16` semaphore on agent execution |
| Plugin auth | All plugin API handlers enforce auth+CSRF+API-key unconditionally |
| Login rate limit | 10 attempts / 5 min window on `/login` |
| Trace correlation | `trace_id` on `AgentContext` and `LogItem` output |

### 🏗️ Architecture (Layered Separation)
| Layer | Module | Responsibility |
|-------|--------|----------------|
| Agent Orchestrator | `helpers/agent_orchestrator.py` | Monologue loop, process chain, lifecycle hooks |
| Reasoning Engine | `helpers/reasoning_engine.py` | Prompt assembly, LLM calls, tool resolution & execution |
| Event Bus | `helpers/event_bus.py` | Typed pub/sub for 15+ lifecycle events |
| Task Router | `helpers/task_router.py` | Priority queue, skill-based dispatch, load tracking |
| Orchestrator Agent | `helpers/orchestrator_agent.py` | Worker pool, per-task timeouts, retry with backoff |

`Agent` class reduced 27% (993→727 lines). All `@extension.extensible` methods preserved as thin delegates.

### 🤖 Agent System
- `AgentMemory` — observations (transient, TTL), facts (persistent), rolling tool results window
- `execute_tool_with_retry()` — configurable retries, exponential backoff, fallback tool support
- `AgentContext.timeout` — per-context execution timeout enforced via `asyncio.wait_for`

### 🧠 Memory & Context
| Component | Detail |
|-----------|--------|
| MemoryManager | `remember/retrieve/forget` API, importance scoring, TTL, short/long memory types |
| Backends | `InMemoryBackend` (default), `QdrantBackend` stub with fallback |
| Compression | `Message.importance` field — high-importance messages skipped during eviction |
| Budget eviction | `forget(policy="budget\|age\|importance\|expired")` |

### 🏷️ CI/CD & Tooling
- `.github/labeler.yml` — path-based PR labels (17 area/type labels)
- `.github/workflows/labeler.yml` — auto-label PRs on open/sync
- `.github/workflows/pre-commit.yml` — pre-commit hooks in CI
- `scripts/` — all `.sh` files set executable (755)

---

## 🔄 In Progress

### Memory Backends
- [ ] Qdrant — embedding computation, vector search, multi-tenant collections
- [ ] Chroma backend
- [ ] Redis backend for high-concurrency short-term memory

### Observability
- [ ] Structured metrics export (Prometheus/OpenTelemetry)
- [ ] Dashboard — agent context pool, task queue depth, memory stats

### Testing
- [ ] Unit tests for `History.compress()` and `Topic.summarize()`
- [ ] Integration tests for agent + tool loops with known inputs
- [ ] Load tests for concurrent contexts

---

## 📋 Planned

### Phase 2 — Stability
- [ ] Streaming tool responses — async iterator for progressive output
- [ ] Agent skill profiles in `agent.yaml` — auto-register with `TaskRouter`
- [ ] Context-aware agent selection — map tasks to skill agents
- [ ] Graceful degradation — fallback to simpler model on overload
- [ ] Typed `ToolRequest` dataclass and centralized parser
- [ ] Standardized error handling — exceptions → user-friendly error with retry policy

### Phase 3 — Scaling
- [ ] Distributed context store (Redis/DB + workers)
- [ ] Persistent vector DB (Qdrant/Chroma optional plugin)
- [ ] Multi-tenant isolation — per-user context pools and memory namespaces
- [ ] Cluster orchestration for multi-host, with leader election
- [ ] Backpressure and queue limits for new contexts

### Phase 4 — Advanced AI
- [ ] Self-improving learning loop — post-task evaluation + autoprompt refinement
- [ ] Multi-agent collaboration graph — capability-based routing
- [ ] Conversation branching — snapshot/restore context state
- [ ] Knowledge graph integration — structured knowledge beyond vector similarity
- [ ] Plugin sandboxing — restrict filesystem and network access
- [ ] Dynamic tool-function schema generation and safe-call enforcement
- [ ] Agent personality — persistent persona traits learned from interactions
- [ ] Webhook triggers — external events drive agent tasks (email, git push, cron)

---

## Refactoring Priorities

### Code quality
- Break large functions (`Agent.monologue`, `History.compress`, `Agent.process_tools`)
- Move history compression policy to configurable strategy classes
- Remove dead/commented code in `handle_exception`

### Dependencies
- Split core runtime vs optional features (browser, speech, document, MCP)
- Regularly run `pip-audit` and `safety` scans
- CI step for dependency drift

---

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│                  API / WebUI / WebSocket                  │
├───────────────────────────────────────────────────────────┤
│                   Agent Orchestrator                      │
│  ┌───────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Process Chain  │  │ Monologue    │  │ Intervention  │  │
│  └───────────────┘  └──────────────┘  └───────────────┘  │
├───────────────────────────────────────────────────────────┤
│                   Reasoning Engine                        │
│  ┌───────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Prompt Build   │  │ LLM Call     │  │ Tool Execute  │  │
│  └───────────────┘  └──────────────┘  └───────────────┘  │
├───────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ History/       │  │ MemoryMgr    │  │ Vector DB     │  │
│  │ Compression    │  │ short/long   │  │ FAISS         │  │
│  └───────────────┘  └──────────────┘  └───────────────┘  │
├───────────────────────────────────────────────────────────┤
│       EventBus  ·  Extensions  ·  Plugins                │
└───────────────────────────────────────────────────────────┘
```

---

See [AGENTS.md](./AGENTS.md) for development patterns.
