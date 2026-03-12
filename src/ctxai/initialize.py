from ctxai.agent import AgentConfig
from ctxai import models
from ctxai.shared import runtime, settings, defer, extension
from ctxai.shared.print_style import PrintStyle


@extension.extensible
def initialize_agent(override_settings: dict | None = None):
    current_settings = settings.get_settings()
    if override_settings:
        current_settings = settings.merge_settings(current_settings, override_settings)

    def _normalize_model_kwargs(kwargs: dict) -> dict:
        # convert string values that represent valid Python numbers to numeric types
        result = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                # try to convert string to number if it's a valid Python number
                try:
                    # try int first, then float
                    result[key] = int(value)
                except ValueError:
                    try:
                        result[key] = float(value)
                    except ValueError:
                        result[key] = value
            else:
                result[key] = value
        return result

    # chat model from user settings
    chat_llm = models.ModelConfig(
        type=models.ModelType.CHAT,
        provider=current_settings["chat_model_provider"],
        name=current_settings["chat_model_name"],
        api_base=current_settings["chat_model_api_base"],
        ctx_length=current_settings["chat_model_ctx_length"],
        vision=current_settings["chat_model_vision"],
        limit_requests=current_settings["chat_model_rl_requests"],
        limit_input=current_settings["chat_model_rl_input"],
        limit_output=current_settings["chat_model_rl_output"],
        kwargs=_normalize_model_kwargs(current_settings["chat_model_kwargs"]),
    )

    # utility model from user settings
    utility_llm = models.ModelConfig(
        type=models.ModelType.CHAT,
        provider=current_settings["util_model_provider"],
        name=current_settings["util_model_name"],
        api_base=current_settings["util_model_api_base"],
        ctx_length=current_settings["util_model_ctx_length"],
        limit_requests=current_settings["util_model_rl_requests"],
        limit_input=current_settings["util_model_rl_input"],
        limit_output=current_settings["util_model_rl_output"],
        kwargs=_normalize_model_kwargs(current_settings["util_model_kwargs"]),
    )
    # embedding model from user settings
    embedding_llm = models.ModelConfig(
        type=models.ModelType.EMBEDDING,
        provider=current_settings["embed_model_provider"],
        name=current_settings["embed_model_name"],
        api_base=current_settings["embed_model_api_base"],
        limit_requests=current_settings["embed_model_rl_requests"],
        kwargs=_normalize_model_kwargs(current_settings["embed_model_kwargs"]),
    )
    # browser model from user settings
    browser_llm = models.ModelConfig(
        type=models.ModelType.CHAT,
        provider=current_settings["browser_model_provider"],
        name=current_settings["browser_model_name"],
        api_base=current_settings["browser_model_api_base"],
        vision=current_settings["browser_model_vision"],
        kwargs=_normalize_model_kwargs(current_settings["browser_model_kwargs"]),
    )
    # agent configuration
    config = AgentConfig(
        chat_model=chat_llm,
        utility_model=utility_llm,
        embeddings_model=embedding_llm,
        browser_model=browser_llm,
        profile=current_settings["agent_profile"],
        knowledge_subdirs=[current_settings["agent_knowledge_subdir"], "default"],
        mcp_servers=current_settings["mcp_servers"],
        browser_http_headers=current_settings["browser_http_headers"],
    )

    # update config with runtime args
    _args_override(config)

    # initialize MCP in deferred task to prevent blocking the main thread
    # async def initialize_mcp_async(mcp_servers_config: str):
    #     return initialize_mcp(mcp_servers_config)
    # defer.DeferredTask(thread_name="mcp-initializer").start_task(initialize_mcp_async, config.mcp_servers)
    # initialize_mcp(config.mcp_servers)

    # import ctxai.shared.mcp_handler as mcp_helper
    # import ctxai.agent as agent_helper
    # import ctxai.shared.print_style as print_style_helper
    # if not mcp_helper.MCPConfig.get_instance().is_initialized():
    #     try:
    #         mcp_helper.MCPConfig.update(config.mcp_servers)
    #     except Exception as e:
    #         first_context = agent_helper.AgentContext.first()
    #         if first_context:
    #             (
    #                 first_context.log
    #                 .log(type="warning", content=f"Failed to update MCP settings: {e}")
    #             )
    #         (
    #             print_style_helper.PrintStyle(background_color="black", font_color="red", padding=True)
    #             .print(f"Failed to update MCP settings: {e}")
    #         )

    # initialize persistence
    from ctxai.core.engine.memory import MemoryManager
    from ctxai.core.engine.persistence import InMemoryProvider, RedisProvider
    
    p_type = current_settings.get("persistence_provider", "in-memory")
    if p_type == "redis":
        try:
            provider = RedisProvider(
                host=current_settings.get("persistence_redis_host", "localhost"),
                port=current_settings.get("persistence_redis_port", 6379)
            )
            MemoryManager.set_provider(provider)
        except Exception as e:
            PrintStyle(background_color="red", font_color="black").print(f"Failed to initialize Redis provider: {e}. Falling back to in-memory.")
            MemoryManager.set_provider(InMemoryProvider())
    else:
        MemoryManager.set_provider(InMemoryProvider())

    # initialize job queue
    from ctxai.core.engine.job_queue import LocalJobQueue, RedisJobQueue
    from ctxai.core.engine.runtime_state import set_job_queue
    
    j_type = current_settings.get("job_queue_provider", "local")
    if j_type == "redis":
        try:
            queue = RedisJobQueue(
                host=current_settings.get("job_queue_redis_host", "localhost"),
                port=current_settings.get("job_queue_redis_port", 6379)
            )
            set_job_queue(queue)
        except Exception as e:
            PrintStyle(background_color="red", font_color="black").print(f"Failed to initialize Redis job queue: {e}. Falling back to local.")
            set_job_queue(LocalJobQueue())
    else:
        set_job_queue(LocalJobQueue())

    # return config object
    return config

def get_job_queue():
    from ctxai.core.engine.runtime_state import get_job_queue as _get_queue
    return _get_queue()

@extension.extensible
def initialize_chats():
    from ctxai.shared import persist_chat
    async def initialize_chats_async():
        persist_chat.load_tmp_chats()
    return defer.DeferredTask().start_task(initialize_chats_async)

@extension.extensible
def initialize_mcp():
    set = settings.get_settings()
    async def initialize_mcp_async():
        from ctxai.shared.mcp_handler import initialize_mcp as _initialize_mcp
        return _initialize_mcp(set["mcp_servers"])
    return defer.DeferredTask().start_task(initialize_mcp_async)

@extension.extensible
def initialize_job_loop():
    from ctxai.shared.job_loop import run_loop
    return defer.DeferredTask("JobLoop").start_task(run_loop)

@extension.extensible
def initialize_preload():
    import ctxai.preload as preload
    return defer.DeferredTask().start_task(preload.preload)

@extension.extensible
def initialize_plugins():
    """Discover enabled plugins and execute their initialize.py setup hooks."""
    async def _run_plugin_inits():
        from ctxai.core.system.plugin_lifecycle import PluginLifecycleRunner
        runner = PluginLifecycleRunner()
        await runner.run_all_initializers()

    return defer.DeferredTask("PluginLifecycle").start_task(_run_plugin_inits)


@extension.extensible
def initialize_migration():
    from ctxai.shared import migration, dotenv
    # run migration
    migration.startup_migration()
    # reload .env as it might have been moved
    dotenv.load_dotenv()
    # reload settings to ensure new paths are picked up
    settings.reload_settings()

def _args_override(config):
    # update config with runtime args
    for key, value in runtime.args.items():
        if hasattr(config, key):
            # conversion based on type of config[key]
            if isinstance(getattr(config, key), bool):
                value = value.lower().strip() == "true"
            elif isinstance(getattr(config, key), int):
                value = int(value)
            elif isinstance(getattr(config, key), float):
                value = float(value)
            elif isinstance(getattr(config, key), str):
                value = str(value)
            else:
                raise Exception(
                    f"Unsupported argument type of '{key}': {type(getattr(config, key))}"
                )

            setattr(config, key, value)



