import logging
from typing import Dict, List, Optional, Set, Any
from pydantic import BaseModel

class Capability(BaseModel):
    name: str
    description: str
    plugin_name: str
    tools: List[str] = [] # List of tool names provided by this capability

class CapabilityRegistry:
    """
    Registry for agent capabilities provided by plugins.
    Allows agents to discover tools by capability rather than by name.
    """
    _capabilities: Dict[str, List[Capability]] = {} # capability_name -> list of providers

    @classmethod
    def register_capability(cls, name: str, description: str, plugin_name: str, tools: List[str]):
        """Register a new capability from a plugin."""
        if name not in cls._capabilities:
            cls._capabilities[name] = []
        
        # Check if already registered by this plugin
        for cap in cls._capabilities[name]:
            if cap.plugin_name == plugin_name:
                cap.description = description
                cap.tools = tools
                return

        cls._capabilities[name].append(Capability(
            name=name,
            description=description,
            plugin_name=plugin_name,
            tools=tools
        ))
        logging.info(f"Registered capability '{name}' from plugin '{plugin_name}'")

    @classmethod
    def unregister_capabilities_for_plugin(cls, plugin_name: str):
        """Unregister all capabilities for a specific plugin."""
        for name in list(cls._capabilities.keys()):
            cls._capabilities[name] = [c for c in cls._capabilities[name] if c.plugin_name != plugin_name]
            if not cls._capabilities[name]:
                del cls._capabilities[name]

    @classmethod
    def get_capabilities(cls) -> Dict[str, List[Capability]]:
        """Get all registered capabilities."""
        return cls._capabilities

    @classmethod
    def get_providers_for_capability(cls, name: str) -> List[Capability]:
        """Get all plugins providing a specific capability."""
        return cls._capabilities.get(name, [])

    @classmethod
    def discover_tools(cls, capability_name: str) -> List[str]:
        """Discover all tools providing a certain capability."""
        tools = []
        for cap in cls.get_providers_for_capability(capability_name):
            tools.extend(cap.tools)
        return list(set(tools))
