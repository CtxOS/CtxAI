from ctxai.shared.files import VariablesPlugin
from ctxai.shared import settings
from ctxai.shared import projects
from ctxai.shared import runtime
from ctxai.shared import files
from typing import Any

class WorkdirPath(VariablesPlugin):
    def get_variables(
        self, file: str, backup_dirs: list[str] | None = None, **kwargs
    ) -> dict[str, Any]:

        # agent = kwargs.get("_agent")
        # if agent and getattr(agent, "context", None):
        #     project_name = projects.get_context_project_name(agent.context)
        #     if project_name:
        #         folder = projects.get_project_folder(project_name)
        #         if runtime.is_development():
        #             folder = files.normalize_ctxai_path(folder)
        #         return {"workdir_path": folder}

        set = settings.get_settings()
        return {"workdir_path": set["workdir_path"]}
        
