"""
core/system/plugin_sdk.py
=========================
Plugin SDK for Ctx AI.

This module is the single, canonical import for plugin developers who want to
build *backend* extensions.  It re-exports the most commonly needed pieces and
defines the ``PluginBase`` abstract base class that every structured plugin
should subclass.

Quick-start
-----------
Place your plugin under ``usr/plugins/<plugin_name>/`` and create an
``extensions/python/<extension_point>/my_hook.py`` file that contains a class
derived from ``PluginBase``.  The framework will discover and call it via the
extension point mechanism.

Example::

    # usr/plugins/my_plugin/extensions/python/agent_init_start/setup.py
    from ctxai.core.system.plugin_sdk import PluginBase

    class Setup(PluginBase):
        async def execute(self, **kwargs):
            self.log(f"my_plugin initialised for agent {self.agent_id}")
            config = self.get_config()
            # ... perform setup ...

Lifecycle extension points (most common)
----------------------------------------
agent_init_start / agent_init_end
    Fires at ``AgentContext.__init__`` (before / after construction).

initialize_agent_start / initialize_agent_end
    Fires when ``initialize_agent()`` runs in ``initialize.py``.

monologue_start / monologue_end
    Fires at the start / end of every agent monologue step.

context_deleted
    Fires when an ``AgentContext`` is cleaned up.

See ``docs/agents/AGENTS.plugins.md`` for the full guide.
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Awaitable

from ctxai.core.system.extension import Extension
from ctxai.shared import plugins as _plugins

if TYPE_CHECKING:
    from ctxai.agent import Agent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PluginBase
# ---------------------------------------------------------------------------

class PluginBase(Extension):
    """Abstract base class for all Ctx AI backend plugin extensions.

    Subclass this instead of ``Extension`` directly to gain:

    * Convenience properties (``agent_id``, ``plugin_name``, ``log``).
    * A ``get_config()`` helper that reads the plugin's ``config.json``.
    * A ``get_meta()`` helper that returns the plugin's ``plugin.yaml``.
    * Structured error handling that logs exceptions without crashing the
      agent loop whenever ``safe_execute`` is used.
    """

    def __init__(self, agent: "Agent | None", **kwargs: Any) -> None:
        super().__init__(agent=agent, **kwargs)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def agent_id(self) -> str | None:
        """Return the current agent context ID, or *None* if unavailable."""
        return getattr(getattr(self.agent, "context", None), "id", None)

    @property
    def plugin_name(self) -> str:
        """Return the snake_case plugin name derived from the module path.

        Convention: the plugin directory name is the third component of the
        Python module path once the ``usr.plugins.`` prefix is stripped.
        Falls back to the class module name.
        """
        mod = self.__class__.__module__  # e.g. "usr.plugins.my_plugin.extensions..."
        parts = mod.split(".")
        try:
            idx = parts.index("plugins")
            return parts[idx + 1]
        except (ValueError, IndexError):
            return mod

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_config(self) -> dict | None:
        """Return the effective plugin configuration dictionary.

        Resolution order (highest priority first):
        1. project-agent scoped ``config.json``
        2. project-global scoped ``config.json``
        3. user-agent scoped ``config.json``
        4. user-global ``config.json``
        5. ``default_config.yaml`` (fallback)
        """
        return _plugins.get_plugin_config(self.plugin_name, agent=self.agent)

    def get_default_config(self) -> dict | None:
        """Return only the ``default_config.yaml`` defaults, ignoring overrides."""
        return _plugins.get_default_plugin_config(self.plugin_name)

    def get_meta(self):
        """Return the ``PluginMetadata`` object from ``plugin.yaml``."""
        return _plugins.get_plugin_meta(self.plugin_name)

    def log(self, message: str, level: str = "info") -> None:
        """Emit a structured log line prefixed with the plugin name.

        Args:
            message: Human-readable log message.
            level:   One of ``"debug"``, ``"info"``, ``"warning"``, ``"error"``.
        """
        prefix = f"[{self.plugin_name}]"
        fn = getattr(logger, level, logger.info)
        fn(f"{prefix} {message}")

    async def safe_execute(self, **kwargs: Any) -> None:
        """Wrap ``execute`` with exception logging.

        Call ``await self.safe_execute(...)`` in custom dispatch code to
        guarantee that plugin errors never propagate into the agent loop.
        """
        try:
            result = self.execute(**kwargs)
            if isinstance(result, Awaitable):
                await result
        except Exception as exc:
            self.log(
                f"Unhandled exception in {self.__class__.__name__}: {exc}",
                level="error",
            )

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def execute(self, **kwargs: Any) -> None | Awaitable[None]:
        """Execute plugin logic at the declared extension point.

        Override this method in your plugin class.  May be async.

        Keyword arguments are extension-point-specific; see the framework
        documentation for what each point passes.
        """


# ---------------------------------------------------------------------------
# Convenience re-exports so plugin authors only need one import
# ---------------------------------------------------------------------------

from ctxai.core.system.plugins import (  # noqa: E402,F401
    get_plugin_config,
    get_default_plugin_config,
    get_plugin_meta,
    get_enabled_plugin_paths,
    get_plugin_paths,
    PluginMetadata,
    PluginListItem,
)
from ctxai.core.system.extension import (  # noqa: E402,F401
    extensible,
    call_extensions_async,
    call_extensions_sync,
    Extension,
)

__all__ = [
    # Core SDK class
    "PluginBase",
    # Extension infrastructure
    "Extension",
    "extensible",
    "call_extensions_async",
    "call_extensions_sync",
    # Plugin registry helpers
    "get_plugin_config",
    "get_default_plugin_config",
    "get_plugin_meta",
    "get_enabled_plugin_paths",
    "get_plugin_paths",
    "PluginMetadata",
    "PluginListItem",
]
