import asyncio
import sys
import contextlib
from typing import Any

# Monkeypatch for Python 3.12+ compatibility with current engineio/socketio versions
# Some async libraries call asyncio.wait_for, asyncio.timeout or aiohttp Timer outside of a task context, 
# which raises RuntimeError in newer Python versions (especially on Python 3.14+).
def apply_asyncio_patch():
    if sys.version_info >= (3, 12):
        _orig_current_task = asyncio.current_task
        
        def _patched_current_task(loop=None):
            task = _orig_current_task(loop)
            if task is None:
                # If no task is found for the current context, try to find ANY running task in the loop
                # This tricks code that strictly requires being inside a task (like Python 3.14 timeouts)
                try:
                    current_loop = loop or asyncio.get_running_loop()
                    tasks = asyncio.all_tasks(current_loop)
                    if tasks:
                        return list(tasks)[0]
                except RuntimeError:
                    pass
            return task
        
        asyncio.current_task = _patched_current_task

        async def _patched_wait_for(fut: Any, timeout: float | None = None) -> Any:
            if timeout is None:
                return await fut
            
            # Using asyncio.wait instead of asyncio.wait_for to avoid "Timeout should be used inside a task" error
            if isinstance(fut, asyncio.Task):
                task = fut
            else:
                task = asyncio.create_task(fut)
                
            done, pending = await asyncio.wait([task], timeout=timeout)
            if pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
                raise asyncio.TimeoutError()
            
            return list(done)[0].result()

        asyncio.wait_for = _patched_wait_for
        
        # Patch asyncio.timeout if it exists (Python 3.11+)
        if hasattr(asyncio, "timeout"):
            _orig_timeout = asyncio.timeout
            
            class _PatchedTimeout:
                def __init__(self, delay):
                    self.delay = delay
                    self.timeout_obj = None
                
                async def __aenter__(self):
                    try:
                        self.timeout_obj = _orig_timeout(self.delay)
                        return await self.timeout_obj.__aenter__()
                    except RuntimeError as e:
                        if "Timeout should be used inside a task" in str(e):
                            return self
                        raise
                
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    if self.timeout_obj and hasattr(self.timeout_obj, "__aexit__"):
                        return await self.timeout_obj.__aexit__(exc_type, exc_val, exc_tb)
                    return False

            asyncio.timeout = _PatchedTimeout

        # Patch aiohttp if installed
        try:
            import aiohttp.helpers
            aiohttp.helpers.current_task = _patched_current_task
        except (ImportError, AttributeError):
            pass

        try:
            import engineio.async_server
            engineio.async_server.asyncio.wait_for = _patched_wait_for
        except ImportError:
            pass
