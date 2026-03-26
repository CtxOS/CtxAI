from ctxai.agent import LoopData
from ctxai.helpers import plugins
from ctxai.helpers.extension import Extension


class TextEditorPrompt(Extension):
    async def execute(
        self,
        system_prompt: list[str] = None,
        loop_data: LoopData | None = None,
        **kwargs,
    ):
        if system_prompt is None:
            system_prompt = []
        if not self.agent:
            return

        config = plugins.get_plugin_config("_text_editor", agent=self.agent) or {}
        default_line_count = config.get("default_line_count", 100)
        prompt = self.agent.read_prompt(
            "agent.system.tool.text_editor.md",
            default_line_count=default_line_count,
        )
        system_prompt.append(prompt)
