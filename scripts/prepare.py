import random
import string

from backend.utils import dotenv, runtime, settings
from backend.utils.print_style import PrintStyle

PrintStyle.standard("Preparing environment...")

try:

    runtime.initialize()

    # generate random root password if not set (for SSH)
    if runtime.is_dockerized():
        root_pass = dotenv.get_dotenv_value(dotenv.KEY_ROOT_PASSWORD)
        if not root_pass:
            root_pass = "".join(random.choices(string.ascii_letters + string.digits, k=32))
            PrintStyle.standard("Changing root password...")
        settings.set_root_password(root_pass)

except Exception as e:
    PrintStyle.error(f"Error in preload: {e}")
