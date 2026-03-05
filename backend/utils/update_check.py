import hashlib

from backend.infrastructure.system import git
from backend.utils import runtime


async def check_version():
    import httpx

    current_version = git.get_version()
    if not git.is_official_ctxai_repo():
        current_version = "fork"

    anonymized_id = hashlib.sha256(runtime.get_persistent_id().encode()).hexdigest()[:20]

    url = "https://api.ctxai.ai/a0-update-check"
    payload = {"current_version": current_version, "anonymized_id": anonymized_id}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        version = response.json()
    return version
