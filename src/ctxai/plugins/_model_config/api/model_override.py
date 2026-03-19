from ctxai.helpers.api import ApiHandler, Request, Response
from ctxai.helpers import settings
from ctxai.helpers.print_style import PrintStyle


class ModelOverride(ApiHandler):
    """Override the chat model for a specific agent context (per-chat switching)."""

    async def process(self, input: dict, request: Request) -> dict | Response:
        s = settings.get_settings()

        if not s.get("allow_chat_override", True):
            return Response("Chat model override is disabled by configuration.", 403)

        ctxid = input.get("ctxid", "")
        if not ctxid:
            return Response("Missing 'ctxid'.", 400)

        provider = input.get("provider", "")
        name = input.get("name", "")

        if not provider or not name:
            return Response("Missing 'provider' or 'name'.", 400)

        context = self.use_context(ctxid, create_if_not_exists=False)

        # Store override on the context
        override = {"provider": provider, "name": name}
        api_base = input.get("api_base", "")
        if api_base:
            override["api_base"] = api_base  # type: ignore

        context.data["_model_override"] = override

        PrintStyle(font_color="green", padding=True).print(f"Model override for context {ctxid}: {provider}/{name}")

        return {
            "ok": True,
            "ctxid": ctxid,
            "override": override,
        }
