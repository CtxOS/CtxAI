from typing import List, Set, Optional
import os
from ctxai.shared.print_style import PrintStyle

class ToolScope:
    BASH_EXEC = "bash_exec"
    PYTHON_EXEC = "python_exec"
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    NETWORK_ACCESS = "network_access"
    BROWSER_CONTROL = "browser_control"
    SECRET_ACCESS = "secret_access"

class SecurityRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SecurityRegistry, cls).__new__(cls)
            cls._instance.granted_scopes = set()
            cls._instance._load_from_settings()
        return cls._instance

    def _load_from_settings(self):
        # In a real scenario, we'd load these from settings.json or env
        # For now, let's assume all are granted if not in a strict mode
        self.granted_scopes = {
            ToolScope.BASH_EXEC,
            ToolScope.PYTHON_EXEC,
            ToolScope.FILESYSTEM_READ,
            ToolScope.FILESYSTEM_WRITE,
            ToolScope.NETWORK_ACCESS,
            ToolScope.BROWSER_CONTROL,
            ToolScope.SECRET_ACCESS
        }

    def is_scope_granted(self, scope: str) -> bool:
        return scope in self.granted_scopes

    def validate_tool_access(self, tool_name: str, required_scopes: List[str]) -> bool:
        for scope in required_scopes:
            if not self.is_scope_granted(scope):
                PrintStyle(background_color="red", font_color="white", padding=True).print(
                    f"SECURITY ALERT: Tool '{tool_name}' requires scope '{scope}' which is not granted."
                )
                return False
        return True

security_registry = SecurityRegistry()
