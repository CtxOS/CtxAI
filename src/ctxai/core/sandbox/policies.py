from typing import Dict, List, Optional, Any
from pydantic import BaseModel

class SandboxPolicy(BaseModel):
    name: str
    max_memory_mb: Optional[int] = 512
    max_cpu_percent: Optional[float] = 50.0
    allow_internet: bool = True
    read_only_fs: bool = False
    max_execution_time_s: int = 60

DEFAULT_POLICY = SandboxPolicy(
    name="default",
    max_memory_mb=512,
    max_cpu_percent=50.0,
    allow_internet=True,
    read_only_fs=False,
    max_execution_time_s=60
)

STRICT_POLICY = SandboxPolicy(
    name="strict",
    max_memory_mb=256,
    max_cpu_percent=10.0,
    allow_internet=False,
    read_only_fs=True,
    max_execution_time_s=30
)

class PolicyRegistry:
    """Registry for sandbox execution policies."""
    _policies: Dict[str, SandboxPolicy] = {
        "default": DEFAULT_POLICY,
        "strict": STRICT_POLICY
    }

    @classmethod
    def get_policy(cls, name: str) -> SandboxPolicy:
        return cls._policies.get(name, DEFAULT_POLICY)

    @classmethod
    def register_policy(cls, policy: SandboxPolicy):
        cls._policies[policy.name] = policy
