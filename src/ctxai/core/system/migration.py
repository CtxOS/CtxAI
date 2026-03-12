import os
import json
from ctxai.shared import files
from ctxai.shared import subagents
from ctxai.shared import yaml as yaml_helper
from ctxai.shared.print_style import PrintStyle


def startup_migration() -> None:
    migrate_user_data()
    convert_agents_json_yaml()

def migrate_user_data() -> None:
    """
    Migrate user data from /tmp and other locations to /usr.
    """
    
    PrintStyle().print("Checking for data migration...")
    
    # --- Migrate Directories -------------------------------------------------------
    # Move directories from tmp/ or other source locations to usr/
    
    _move_dir("tmp/chats", os.path.join(files.USER_DIR, "chats"))
    _move_dir("tmp/scheduler", os.path.join(files.USER_DIR, "scheduler"), overwrite=True)
    _move_dir("tmp/uploads", os.path.join(files.USER_DIR, "uploads"))
    _move_dir("tmp/upload", os.path.join(files.USER_DIR, "upload"))
    _move_dir("tmp/downloads", os.path.join(files.USER_DIR, "downloads"))
    _move_dir("tmp/email", os.path.join(files.USER_DIR, "email"))
    _move_dir("knowledge/custom", os.path.join(files.USER_DIR, "knowledge"), overwrite=True)

    # --- Migrate Files -------------------------------------------------------------
    # Move specific configuration files to usr/
    
    _move_file("tmp/settings.json", os.path.join(files.USER_DIR, "settings.json"))
    _move_file("tmp/secrets.env", os.path.join(files.USER_DIR, "secrets.env"))
    _move_file(".env", os.path.join(files.USER_DIR, ".env"), overwrite=True)

    # --- Special Migration Cases ---------------------------------------------------
    
    # Migrate Memory
    _migrate_memory()

    # Flatten default directories (knowledge/default -> knowledge/, etc.)
    # We use _merge_dir_contents because we want to move the *contents* of default/ 
    # into the parent directory, not move the default directory itself.
    _merge_dir_contents("knowledge/default", files.KNOWLEDGE_DIR)

    # --- Cleanup -------------------------------------------------------------------
    
    # Remove obsolete directories after migration
    _cleanup_obsolete()

    PrintStyle().print("Migration check complete.")


def convert_agents_json_yaml() -> None:
    for root in subagents.get_agents_roots():
        rel_root = files.deabsolute_path(root)
        for subdir in files.get_subdirectories(rel_root):
            agent_yaml = os.path.join(rel_root, subdir, "agent.yaml")
            if files.exists(agent_yaml):
                continue

            agent_json = os.path.join(rel_root, subdir, "agent.json")
            if not files.exists(agent_json):
                continue

            try:
                agent_obj = json.loads(files.read_file(agent_json))
                files.write_file(agent_yaml, yaml_helper.dumps(agent_obj))
            except Exception as e:
                PrintStyle.error(f"Failed to convert {agent_json} to YAML", e)
                continue

# --- Helper Functions ----------------------------------------------------------

def _move_dir(src: str, dst: str, overwrite: bool = False) -> None:
    """
    Move a directory from src to dst if src exists and dst does not.
    """
    if files.exists(src) and (not files.exists(dst) or overwrite):
        PrintStyle().print(f"Migrating {src} to {dst}...")
        if overwrite and files.exists(dst):
            files.delete_dir(dst)
        files.move_dir(src, dst)

def _move_file(src: str, dst: str, overwrite: bool = False) -> None:
    """
    Move a file from src to dst if src exists and dst does not.
    """
    if files.exists(src) and (not files.exists(dst) or overwrite):
        PrintStyle().print(f"Migrating {src} to {dst}...")
        files.move_file(src, dst)

def _migrate_memory(base_path: str = "memory") -> None:
    """
    Migrate memory subdirectories.
    """
    subdirs = files.get_subdirectories(base_path)
    for subdir in subdirs:
        if subdir == "embeddings":
            # Special case: Embeddings
            _move_dir("memory/embeddings", os.path.join(files.TMP_DIR, "memory/embeddings"))
        else:
            # Move other memory items to usr/memory
            dst = os.path.join(files.USER_DIR, f"memory/{subdir}")
            _move_dir(f"memory/{subdir}", dst)

def _merge_dir_contents(src_parent: str, dst_parent: str) -> None:
    """
    Moves all items from src_parent to dst_parent.
    Useful for flattening structures like 'knowledge/default/*' -> 'knowledge/*'.
    """
    if not files.exists(src_parent):
        return

    entries = files.list_files(src_parent)
    for entry in entries:
        src = f"{src_parent}/{entry}"
        dst = f"{dst_parent}/{entry}"
        abs_src = files.get_abs_path(src)
        if os.path.isdir(abs_src):
            _move_dir(src, dst)
        elif os.path.isfile(abs_src):
            _move_file(src, dst)

def _cleanup_obsolete() -> None:
    """
    Remove directories that are no longer needed.
    """
    to_remove = [
        "knowledge/default",
        "memory"
    ]
    for path in to_remove:
        if files.exists(path):
            PrintStyle().print(f"Removing {path}...")
            files.delete_dir(path)
