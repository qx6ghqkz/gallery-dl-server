import os
import sys


def resource_path(relative_path):
    """Get absolute path to resource for frozen PyInstaller executable."""
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", ""), relative_path)
    else:
        return relative_path
