import sys
import os

def resource_path(relative_path: str) -> str:
    """
    Returns the absolute path to a resource, whether running in dev mode or from a PyInstaller .exe.
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller extracts files to this temp folder at runtime
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)
