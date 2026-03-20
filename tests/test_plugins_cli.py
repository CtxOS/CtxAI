import os

from ctxai.helpers.plugins_cli import create_plugin
from ctxai.helpers.plugins_cli import validate_plugin


def test_create_and_validate_plugin(tmp_path):
    # Override user plugins directory to temp for test isolation
    user_dir = tmp_path / "usr"
    user_plugins_dir = user_dir / "plugins"
    user_plugins_dir.mkdir(parents=True, exist_ok=True)

    # Monkeypatch files.USER_DIR path by environment variable if used
    # In this code base, files.get_abs_path uses standard root, so set cwd
    old_cwd = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        plugin_name = "test-plugin"
        plugin_dir = create_plugin(plugin_name, "A test plugin.", "tester")
        assert plugin_dir.exists()
        assert (plugin_dir / "plugin.yaml").exists()

        # Validate should pass and not raise
        validate_plugin(plugin_name)
    finally:
        os.chdir(old_cwd)
