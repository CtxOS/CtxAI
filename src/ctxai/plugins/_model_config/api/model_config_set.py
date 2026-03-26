from ctxai.helpers import settings
from ctxai.helpers.api import ApiHandler, Request, Response
from ctxai.helpers.print_style import PrintStyle


class ModelConfigSet(ApiHandler):
    """Update model configuration for chat, utility, or embedding models."""

    async def process(self, input: dict, request: Request) -> dict | Response:
        section = input.get("section", "")  # chat_model, utility_model, embedding_model
        if section not in ("chat_model", "utility_model", "embedding_model"):
            return Response("Invalid section. Must be chat_model, utility_model, or embedding_model.", 400)

        s = settings.get_settings()

        # Allowed fields per section
        allowed_fields = {
            "chat_model": {"provider", "name", "api_base", "ctx_length", "ctx_history", "vision", "kwargs"},
            "utility_model": {"provider", "name", "api_base", "ctx_length", "ctx_input", "kwargs"},
            "embedding_model": {"provider", "name", "api_base", "kwargs"},
        }

        updates = input.get("config", {})
        if not isinstance(updates, dict):
            return Response("'config' must be a dictionary.", 400)

        prefix = section  # e.g. "chat_model"
        for key, value in updates.items():
            if key not in allowed_fields[section]:
                continue
            setting_key = f"{prefix}_{key}" if key not in ("kwargs",) else f"{prefix}_{key}"
            s[setting_key] = value

        # Save
        settings.save_settings(s)

        PrintStyle(font_color="green", padding=True).print(f"Model config updated: {section}")
        return {"ok": True, "section": section, "updated": list(updates.keys())}
