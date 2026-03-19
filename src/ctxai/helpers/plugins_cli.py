#!/usr/bin/env python3
"""
Plugins CLI - Create, validate, and inspect plugin scaffolds.
Usage:
    python -m helpers.plugins_cli list
    python -m helpers.plugins_cli create <name>
    python -m helpers.plugins_cli validate <name>
    python -m helpers.plugins_cli show <name>
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List

# Add parent directory to path for imports (same pattern as skills_cli)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ctxai.helpers import files, print_style
from ctxai.helpers import yaml as yaml_helper
from ctxai.helpers.plugins import (
    META_FILE_NAME,
    get_enhanced_plugins_list,
    get_plugin_meta,
    find_plugin_dir,
)
from ctxai.plugins._plugin_installer.helpers.install import validate_plugin_dir


def _get_user_plugins_dir() -> Path:
    return Path(files.get_abs_path(files.USER_DIR, files.PLUGINS_DIR))


def _validate_plugin_name(name: str) -> List[str]:
    issues = []
    if not name:
        issues.append("Plugin name cannot be empty")
        return issues
    if not re.match(r"^[a-z0-9-]+$", name):
        issues.append("Plugin name must use lowercase letters, numbers, and hyphens")
    if name.startswith("-") or name.endswith("-"):
        issues.append("Plugin name must not start or end with a hyphen")
    if "--" in name:
        issues.append("Plugin name must not contain consecutive hyphens")
    if len(name) > 64:
        issues.append("Plugin name must be 64 characters or fewer")
    return issues


def _write_template_files(plugin_dir: Path, name: str, description: str, author: str):
    plugin_yaml = {
        "name": name,
        "title": name.replace("-", " ").title(),
        "description": description or "Describe your plugin's behavior.",
        "version": "0.1.0",
        "settings_sections": [],
        "per_project_config": False,
        "per_agent_config": False,
        "always_enabled": False,
        "framework_version": ">=0.1.0",
        "plugin_dependencies": [],
    }
    config_text = "version: 1.0\n"

    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / META_FILE_NAME).write_text(yaml_helper.dumps(plugin_yaml), encoding="utf-8")
    (plugin_dir / "README.md").write_text(f"# {plugin_yaml['title']}\n\n{plugin_yaml['description']}\n", encoding="utf-8")
    (plugin_dir / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    (plugin_dir / "default_config.yaml").write_text(config_text, encoding="utf-8")
    (plugin_dir / "hooks.py").write_text(
        """def install():\n    print('Running plugin install hook...')\n""",
        encoding="utf-8",
    )
    (plugin_dir / "initialize.py").write_text(
        """def main():\n    print('Initialization script for plugin')\n    return 0\n\nif __name__ == '__main__':\n    import sys\n    sys.exit(main())\n""",
        encoding="utf-8",
    )
    webui_dir = plugin_dir / "webui"
    webui_dir.mkdir(parents=True, exist_ok=True)
    (webui_dir / "config.html").write_text(
        """<div>\n  <h1>Plugin Settings</h1>\n  <p>Configure your plugin here.</p>\n</div>\n""",
        encoding="utf-8",
    )


def create_plugin(name: str, description: str = "", author: str = "") -> Path:
    issues = _validate_plugin_name(name)
    if issues:
        raise ValueError("Invalid plugin name: " + "; ".join(issues))

    user_plugins_dir = _get_user_plugins_dir()
    plugin_dir = user_plugins_dir / name
    if plugin_dir.exists():
        raise ValueError(f"Plugin '{name}' already exists at {plugin_dir}")

    _write_template_files(plugin_dir, name, description or "A new Ctx AI plugin.", author or "Your Name")
    return plugin_dir


def list_plugins():
    plugins = get_enhanced_plugins_list(custom=True, builtin=True)
    if not plugins:
        print("No plugins installed.")
        return

    print(f"{'Name':<30} {'Version':<10} {'Enabled':<10} {'Compatible':<10} Description")
    print("-" * 90)
    for item in plugins:
        print(
            f"{item.name:<30} {item.version:<10} {item.toggle_state:<10} {str(item.is_compatible):<10} {item.description[:40]}"
        )


def show_plugin(name: str):
    plugin_dir = find_plugin_dir(name)
    if not plugin_dir:
        raise ValueError(f"Plugin '{name}' not found")
    meta = get_plugin_meta(name)
    if not meta:
        raise ValueError(f"No plugin metadata for '{name}'")
    print(f"Plugin: {name}")
    print(f"Path: {plugin_dir}")
    print(f"Title: {meta.title}")
    print(f"Description: {meta.description}")
    print(f"Version: {meta.version}")
    print(f"Framework version requirement: {meta.framework_version}")
    print(f"Plugin dependencies: {', '.join(meta.plugin_dependencies or [])}")


def validate_plugin(name: str):
    plugin_dir = find_plugin_dir(name)
    if not plugin_dir:
        raise ValueError(f"Plugin '{name}' not found")
    try:
        meta = validate_plugin_dir(str(plugin_dir), plugin_name=name)
    except Exception as e:
        raise ValueError(f"Plugin validation failed: {e}") from e
    print(f"✅ Plugin '{name}' is valid (version {meta.version})")


def main():
    parser = argparse.ArgumentParser(description="Ctx AI Plugin CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_list = subparsers.add_parser("list", help="List installed plugins")

    parser_create = subparsers.add_parser("create", help="Create a plugin template")
    parser_create.add_argument("name", help="Plugin directory name (lowercase, hyphen-separated)")
    parser_create.add_argument("-d", "--description", default="", help="Plugin description")
    parser_create.add_argument("-a", "--author", default="", help="Author name")

    parser_show = subparsers.add_parser("show", help="Show plugin metadata")
    parser_show.add_argument("name", help="Plugin name")

    parser_validate = subparsers.add_parser("validate", help="Validate plugin directory")
    parser_validate.add_argument("name", help="Plugin name")

    args = parser.parse_args()

    try:
        if args.command == "list":
            list_plugins()
        elif args.command == "create":
            plugin_dir = create_plugin(args.name, args.description, args.author)
            print_style.PrintStyle.success(f"Created plugin template at: {plugin_dir}")
        elif args.command == "show":
            show_plugin(args.name)
        elif args.command == "validate":
            validate_plugin(args.name)
        else:
            parser.print_help()
    except Exception as exc:
        print_style.PrintStyle.error(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
