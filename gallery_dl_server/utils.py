# -*- coding: utf-8 -*-

import os
import sys

WINDOWS = os.name == "nt"
DOCKER = os.path.isfile("/.dockerenv")
KUBERNETES = os.environ.get("KUBERNETES_SERVICE_HOST") is not None
EXECUTABLE = bool(getattr(sys, "frozen", False))
_MEIPASS_PATH = getattr(sys, "_MEIPASS", None)

CONTAINER = DOCKER or KUBERNETES
_MEIPASS = _MEIPASS_PATH is not None
PYINSTALLER = EXECUTABLE and _MEIPASS


def resource_path(relative_path: str):
    """Return absolute path to resource for frozen PyInstaller executable."""
    if PYINSTALLER:
        assert _MEIPASS_PATH
        return os.path.join(_MEIPASS_PATH, relative_path)
    else:
        return relative_path


def dirname_parent(path: str):
    """Return grandparent directory of the given path."""
    return os.path.dirname(os.path.dirname(path))


def join_paths(base_path: str, /, *paths: str):
    """Join each path with the base path and return a list."""
    return [os.path.join(base_path, path) for path in paths]


def get_package_name():
    """Return the name of the package."""
    fallback = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
    return __package__ if __package__ else fallback
