from ctxai.core.agent import LoopData
from ctxai.tools.skills_tool import DATA_NAME_LOADED_SKILLS
from ctxai.utils import skills
from ctxai.utils.extension import Extension


class IncludeLoadedSkills(Extension):
    async def execute(self, loop_data: LoopData | None = None, **kwargs):
        loop_data = loop_data or LoopData()
        if not self.agent:
            return

        extras = loop_data.extras_persistent

        # Get loaded skills names
        skill_names = self.agent.data.get(DATA_NAME_LOADED_SKILLS)
        if not skill_names:
            return

        # load skill text here
        content = ""
        for skill_name in skill_names:
            skill_data = skills.load_skill_for_agent(skill_name=skill_name, agent=self.agent)
            content += "\n\n" + skill_data
        content = content.strip()
        if not content:
            return

        # Inject into extras
        extras["loaded_skills"] = self.agent.read_prompt(
            "agent.system.skills.loaded.md",
            skills=content,
        )
