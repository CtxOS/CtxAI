import asyncio
import pytest
from ctxai.core.system.plugin_bus import PluginBus
from ctxai.core.tools.capabilities import CapabilityRegistry

@pytest.mark.asyncio
async def test_plugin_bus_communication():
    """Verify that multiple subscribers receive events."""
    received_data_1 = []
    received_data_2 = []

    async def callback1(data):
        received_data_1.append(data)

    async def callback2(data):
        received_data_2.append(data)

    await PluginBus.subscribe("test_event", callback1)
    await PluginBus.subscribe("test_event", callback2)

    test_payload = {"message": "hello world"}
    await PluginBus.emit("test_event", test_payload)

    assert len(received_data_1) == 1
    assert received_data_1[0] == test_payload
    assert len(received_data_2) == 1
    assert received_data_2[0] == test_payload

    # Unsubscribe and verify
    await PluginBus.unsubscribe("test_event", callback1)
    await PluginBus.emit("test_event", "again")
    
    assert len(received_data_1) == 1 # Still 1
    assert len(received_data_2) == 2 # Now 2
    assert received_data_2[1] == "again"

@pytest.mark.asyncio
async def test_capability_discovery():
    """Verify that agents can discover tools via capabilities."""
    CapabilityRegistry.register_capability(
        name="image_processing",
        description="Handles image resizing and filters",
        plugin_name="image_plugin",
        tools=["resize_image", "apply_filter"]
    )

    CapabilityRegistry.register_capability(
        name="image_processing",
        description="Legacy image tools",
        plugin_name="legacy_plugin",
        tools=["old_crop"]
    )

    # Discover tools for image_processing
    tools = CapabilityRegistry.discover_tools("image_processing")
    assert set(tools) == {"resize_image", "apply_filter", "old_crop"}

    # Register other capability
    CapabilityRegistry.register_capability(
        name="text_analysis",
        description="Sentiment analysis",
        plugin_name="nlp_plugin",
        tools=["get_sentiment"]
    )

    all_caps = CapabilityRegistry.get_capabilities()
    assert "image_processing" in all_caps
    assert "text_analysis" in all_caps

    # Unregister plugin
    CapabilityRegistry.unregister_capabilities_for_plugin("image_plugin")
    tools_after = CapabilityRegistry.discover_tools("image_processing")
    assert set(tools_after) == {"old_crop"}
