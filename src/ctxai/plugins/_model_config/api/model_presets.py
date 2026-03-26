import os

from ctxai.helpers import files
from ctxai.helpers import yaml as yaml_helper
from ctxai.helpers.api import ApiHandler, Request, Response


class ModelPresets(ApiHandler):
    """Get available model presets (predefined chat/utility model combinations)."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        # Load presets from plugin default_presets.yaml
        plugin_dir = os.path.dirname(os.path.dirname(__file__))
        presets_path = os.path.join(plugin_dir, "default_presets.yaml")

        presets: list[dict] = []
        if files.exists(presets_path):
            content = files.read_file(presets_path)
            parsed = yaml_helper.loads(content)
            if isinstance(parsed, list):
                presets = parsed

        # Load user overrides from usr/presets if they exist
        user_presets_path = files.get_abs_path("usr/presets.yaml")
        if files.exists(user_presets_path):
            content = files.read_file(user_presets_path)
            parsed = yaml_helper.loads(content)
            if isinstance(parsed, list):
                # User presets override defaults by name
                user_names = {p.get("name") for p in parsed}
                presets = [p for p in presets if p.get("name") not in user_names] + parsed

        return {"ok": True, "presets": presets}
