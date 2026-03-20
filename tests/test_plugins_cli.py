import uuid

from ctxai.helpers.plugins_cli import create_plugin, validate_plugin


def test_create_and_validate_plugin(tmp_path):
    # Use a unique name to avoid collisions with existing plugins
    plugin_name = f"test-plugin-{uuid.uuid4().hex[:6]}"
    try:
        plugin_dir = create_plugin(plugin_name, "A test plugin.", "tester")
        assert plugin_dir.exists()
        assert (plugin_dir / "plugin.yaml").exists()

        # Validate should pass and not raise
        validate_plugin(plugin_name)
    finally:
        # Clean up created plugin directory
        import shutil

        shutil.rmtree(plugin_dir, ignore_errors=True)
