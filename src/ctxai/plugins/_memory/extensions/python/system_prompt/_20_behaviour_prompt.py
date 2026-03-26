from ctxai.agent import Agent, LoopData
from ctxai.helpers import files
from ctxai.helpers.extension import Extension
from ctxai.plugins._memory.helpers import memory

# Direct import - this extension lives inside the memory plugin


class BehaviourPrompt(Extension):
    async def execute(self, system_prompt: list[str] = None, loop_data: LoopData | None = None, **kwargs):
        if system_prompt is None:
            system_prompt = []
        if not self.agent:
            return

        prompt = read_rules(self.agent)
        system_prompt.insert(0, prompt)


def get_custom_rules_file(agent: Agent):
    return files.get_abs_path(memory.get_memory_subdir_abs(agent), "behaviour.md")


def read_rules(agent: Agent):
    rules_file = get_custom_rules_file(agent)
    if files.exists(rules_file):
        rules = files.read_file(rules_file)
        return agent.read_prompt("agent.system.behaviour.md", rules=rules)
    else:
        rules = agent.read_prompt("agent.system.behaviour_default.md")
        return agent.read_prompt("agent.system.behaviour.md", rules=rules)
