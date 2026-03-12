import asyncio
import os
from ctxai.core.sandbox.manager import SandboxManager

async def test_rpc_flow():
    print("--- Starting RPC Sandbox Verification ---")
    
    # Configure SandboxManager to use RPC
    os.environ["A0_SANDBOX_PROVIDER"] = "rpc"
    os.environ["A0_SANDBOX_ENDPOINT"] = "http://localhost:50002"
    
    env_id = "test_rpc_env"
    
    try:
        print(f"Requesting environment: {env_id} (Provider: {os.environ['A0_SANDBOX_PROVIDER']})")
        env = await SandboxManager.get_environment(env_id)
        
        print("Executing 'whoami'...")
        await env.send_command("whoami")
        stdout, stderr = await env.read_output()
        print(f"Stdout: {stdout.strip()}")
        if stderr:
             print(f"Stderr: {stderr.strip()}")
             
        assert len(stdout.strip()) > 0
        
        print("Executing Python command...")
        # Check if it has the execute_python method (RPC provider has it)
        if hasattr(env, "execute_python"):
            py_stdout, py_stderr, py_exit = await env.execute_python("print('Hello from RPC Sandbox')")
            print(f"Python Stdout: {py_stdout.strip()}")
            assert py_stdout.strip() == "Hello from RPC Sandbox"
        
        print("--- Verification Successful! ---")
        
    except Exception as e:
        print(f"--- Verification Failed: {e} ---")
        raise e
    finally:
        await SandboxManager.remove_environment(env_id)

if __name__ == "__main__":
    asyncio.run(test_rpc_flow())
