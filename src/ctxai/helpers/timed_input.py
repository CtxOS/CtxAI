import sys

from inputimeout import inputimeout
from inputimeout import TimeoutOccurred


def timeout_input(prompt, timeout=10):
    try:
        if sys.platform != "win32":
            pass
        user_input = inputimeout(prompt=prompt, timeout=timeout)
        return user_input
    except TimeoutOccurred:
        return ""
