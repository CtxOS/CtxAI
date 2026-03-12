import asyncio
import time
from ctxai.initialize import initialize_agent, get_job_queue
from ctxai.core.engine.memory import MemoryManager
from ctxai.shared.print_style import PrintStyle

async def worker_loop():
    PrintStyle(background_color="blue", font_color="white", padding=True).print("Ctx AI Worker Starting...")
    
    # Initialize framework
    initialize_agent()
    queue = get_job_queue()
    
    if not queue:
        PrintStyle(background_color="red", font_color="black").print("Job queue not initialized. Exiting.")
        return

    PrintStyle(italic=True).print("Waiting for jobs...")
    
    while True:
        job = queue.pop()
        if job:
            job_id = job.get("id")
            func_ref = job.get("func")
            args = job.get("args", [])
            kwargs = job.get("kwargs", {})
            
            PrintStyle(font_color="green").print(f"Processing Job: {job_id} ({func_ref})")
            
            try:
                # Set tenant context for this job
                from ctxai.shared import context as context_helper
                tenant = job.get("tenant", {})
                context_helper.set_context_data("user_id", tenant.get("user_id"))
                context_helper.set_context_data("workspace_id", tenant.get("workspace_id", "default"))
                
                # Resolve function from func_ref
                if func_ref == "AgentContext.communicate":
                    ctx_id = args[0]
                    msg = args[1]
                    
                    # MemoryManager.get is now tenant-aware!
                    context = MemoryManager.get(ctx_id)
                    if context:
                        # Re-run communication
                        await context._process_chain(context.agent0, msg)
                        # Save state back
                        MemoryManager.register(context)
                    else:
                        PrintStyle(font_color="red").print(f"Context {ctx_id} not found for job {job_id}")
                
                # Clear for next job
                context_helper.clear_context_data()
                
            except Exception as e:
                PrintStyle(background_color="red", font_color="black").print(f"Error processing job {job_id}: {e}")
        
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(worker_loop())
