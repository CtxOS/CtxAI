"""
core/system/plugin_lifecycle.py
================================
Plugin lifecycle management for Ctx AI.

The ``PluginLifecycleRunner`` is responsible for discovering enabled plugins
and executing their optional ``initialize.py`` entry-point at framework
startup, giving each plugin a chance to install dependencies, pre-load models,
or register callbacks before any agent starts running.

Usage (called automatically from ``initialize.py``)::

    from ctxai.core.system.plugin_lifecycle import PluginLifecycleRunner

    async def my_startup():
        runner = PluginLifecycleRunner()
        await runner.run_all_initializers()

Plugin initialize.py contract
------------------------------
An ``initialize.py`` at the root of a plugin directory may define:

    async def setup(config: dict | None, plugin_name: str) -> None: ...
    # or sync:
    def setup(config: dict | None, plugin_name: str) -> None: ...

If neither is defined the module is still imported (side-effects allowed).
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable

from ctxai.core.system import plugins as _plugins

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


INIT_SCRIPT_NAME = "initialize.py"


class PluginLifecycleRunner:
    """Discovers enabled plugins and runs their ``initialize.py`` setup hook.

    Args:
        agent: Optional agent instance.  When provided, enabled-plugin lookup
               respects per-agent / per-project toggle overrides.
    """

    def __init__(self, agent=None) -> None:
        self._agent = agent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_all_initializers(self) -> None:
        """Run the ``setup`` hook of every enabled plugin that ships one.

        Errors in individual plugins are caught and logged so that a single
        broken plugin cannot prevent the rest of the framework from starting.
        """
        enabled = _plugins.get_enabled_plugins(self._agent)
        for plugin_name in enabled:
            await self._run_plugin_initializer(plugin_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_plugin_initializer(self, plugin_name: str) -> None:
        plugin_dir = _plugins.find_plugin_dir(plugin_name)
        if not plugin_dir:
            return

        script_path = Path(plugin_dir) / INIT_SCRIPT_NAME
        if not script_path.exists():
            return  # optional — not an error

        logger.info("[plugin_lifecycle] Initializing plugin: %s", plugin_name)

        try:
            module = self._load_module(plugin_name, str(script_path))
        except Exception as exc:
            logger.error(
                "[plugin_lifecycle] Failed to import %s/initialize.py: %s",
                plugin_name,
                exc,
            )
            return

        config = _plugins.get_plugin_config(plugin_name, agent=self._agent)
        await self._call_setup(module, plugin_name, config)

    @staticmethod
    def _load_module(plugin_name: str, path: str):
        """Dynamically import an ``initialize.py`` without polluting sys.modules."""
        module_name = f"_a0_plugin_{plugin_name}_init"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot create module spec for {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module

    @staticmethod
    async def _call_setup(module, plugin_name: str, config: dict | None) -> None:
        """Call the ``setup`` callable in the module if it exists."""
        setup_fn = getattr(module, "setup", None)
        if setup_fn is None:
            # Side-effect-only initializer — already executed via exec_module.
            return

        try:
            result = setup_fn(config=config, plugin_name=plugin_name)
            if isinstance(result, Awaitable):
                await result
            logger.info(
                "[plugin_lifecycle] Plugin '%s' initialized successfully.", plugin_name
            )
        except Exception as exc:
            logger.error(
                "[plugin_lifecycle] setup() in '%s' raised an exception: %s",
                plugin_name,
                exc,
            )
