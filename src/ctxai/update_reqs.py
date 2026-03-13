import pkg_resources
import re

import subprocess
import os

def update_requirements():
    print("Updating uv.lock...")
    subprocess.run(["uv", "lock", "--upgrade"], check=True)
    
    # Optional: Still sync requirements.txt for external tools that might need it
    print("Exporting to requirements.txt for compatibility...")
    subprocess.run(["uv", "export", "--format", "requirements-txt", "--output-file", "requirements.txt", "--no-hashes"], check=True)
    
if __name__ == '__main__':
    update_requirements()
