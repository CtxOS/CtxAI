# Extension Hook Execution Order

> Extensions provide lifecycle hooks that run at defined points during agent execution.

## Directory Structure

```
extensions/python/
  _10_early_setup.py       # Runs first
  _50_default_handler.py   # Runs middle (default)
  _90_cleanup.py           # Runs last
```

Extensions can also live in `usr/extensions/` for user-defined hooks.

## Execution Order

Files are **sorted alphabetically** by filename. Use numeric prefixes to control order:

| Prefix | Phase | Typical Use |
|--------|-------|-------------|
| `_00_` – `_19_` | Early | Pre-processing, validation, auth checks |
| `_20_` – `_49_` | Pre-main | Input transformation, logging setup |
| `_50_` | Default | Standard handlers (no prefix = `_50_` equivalent) |
| `_51_` – `_79_` | Post-main | Output transformation, metrics |
| `_80_` – `_99_` | Late | Cleanup, notifications, audit logging |

## Hook Types

### `@extensible` Decorator

Wraps a function to create two implicit extension points:

```
{module}_{qualname}_start  →  runs before the function
{module}_{qualname}_end    →  runs after the function
```

### Extension Point Data

Each extension receives a mutable `data` dict:

```python
data = {
    "args": tuple,          # Positional args (mutable)
    "kwargs": dict,         # Keyword args (mutable)
    "result": Any | UNSET,  # Set to short-circuit the function
    "exception": Exception | UNSET,  # Set to force-raise
}
```

### Lifecycle

| Action | Extension Hook | When |
|--------|---------------|------|
| Agent init | `agent_init` | AgentContext created |
| Monologue start | `monologue_start` | Before agent reasoning loop |
| Monologue end | `monologue_end` | After agent reasoning loop |
| Tool execute | `tool_execute_start/end` | Around tool execution |
| Context delete | `context_deleted` | AgentContext removed |

## Writing an Extension

```python
# extensions/python/_10_my_hook.py
from ctxai.helpers.extension import extensible

class MyExtension:
    @staticmethod
    def on_monologue_start(data):
        """Called before each monologue iteration."""
        data["kwargs"]["context"]["preprocessed"] = True

    @staticmethod
    def on_monologue_end(data):
        """Called after each monologue iteration."""
        result = data.get("result")
        # Can modify or wrap the result
```

## Best Practices

1. **Use prefixes** — Don't rely on default ordering for critical paths
2. **Be idempotent** — Extensions may run multiple times in error recovery
3. **Handle missing data** — Other extensions may modify the data dict
4. **Avoid blocking** — Use async patterns for I/O operations
5. **Log sparingly** — Extensions run on every request; excessive logging impacts performance
