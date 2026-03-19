"""Safe evaluation of metadata filter conditions.

Centralizes all simple_eval usage to enforce consistent security controls:
- Only primitive values (str, int, float, bool, None) are allowed in the names dict.
- Dunder keys are stripped to prevent builtin shadowing.
- No functions or callables are exposed.
"""

from __future__ import annotations

from typing import Any, Callable

from simpleeval import SimpleEval

# Allowed types for values exposed to the evaluator.
_SAFE_TYPES = (str, int, float, bool, type(None))


def _sanitize_names(names: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of *names* containing only safe primitives."""
    safe: dict[str, Any] = {}
    for key, value in names.items():
        # Reject dunder keys (e.g. __class__, __builtins__) and empty keys
        if not key or key.startswith("__") or key.endswith("__"):
            continue
        # Reject keys with non-identifier characters
        if not key.isidentifier():
            continue
        # Only allow primitive types
        if isinstance(value, _SAFE_TYPES):
            safe[key] = value
    return safe


# Module-level evaluator instance – SimpleEval is reusable and caches its AST
# compiler.  Each call to safe_eval_condition still receives a fresh names dict.
_evaluator = SimpleEval()


def safe_eval_condition(condition: str, names: dict[str, Any]) -> bool:
    """Evaluate *condition* against *names* safely.

    Returns ``False`` on any evaluation error rather than propagating
    exceptions to the caller.
    """
    try:
        safe_names = _sanitize_names(names)
        _evaluator.names = safe_names
        result = _evaluator.eval(condition)
        return bool(result)
    except Exception:
        return False


def make_comparator(condition: str) -> Callable[[dict[str, Any]], bool]:
    """Return a comparator function that safely evaluates *condition*.

    The returned callable accepts a metadata dict and returns True/False.
    """

    def comparator(data: dict[str, Any]) -> bool:
        return safe_eval_condition(condition, data)

    return comparator
