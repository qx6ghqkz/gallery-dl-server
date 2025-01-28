# -*- coding: utf-8 -*-

import os
import sys
import importlib

WINDOWS = os.name == "nt"
DOCKER = os.path.isfile("/.dockerenv")
KUBERNETES = os.environ.get("KUBERNETES_SERVICE_HOST") is not None
EXECUTABLE = bool(getattr(sys, "frozen", False))
MEIPASS_PATH: str | None = getattr(sys, "_MEIPASS", None)

CONTAINER = DOCKER or KUBERNETES
MEIPASS = MEIPASS_PATH is not None
PYINSTALLER = EXECUTABLE and MEIPASS


def resource_path(relative_path: str):
    """Return absolute path to resource for frozen PyInstaller executable."""
    if PYINSTALLER:
        assert MEIPASS_PATH
        return os.path.join(MEIPASS_PATH, get_package_name(), relative_path)
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def get_log_file_path(filename: str):
    """Get log file path depending on whether the package is installed."""
    try:
        importlib.import_module(get_package_name())

        if os.getcwd() == dirname_parent(os.path.abspath(__file__)):
            raise ImportError

        log_dir = os.path.expanduser("~")
        filename = "gallery-dl-server.log"
    except ImportError:
        log_dir = os.path.join(os.getcwd(), "logs")

    log_path = os.path.join(log_dir, filename)

    return log_path


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


def normalise_path(path: str):
    """Expands environment variables in the given path, normalises it,
    and returns the absolute path."""
    return os.path.abspath(os.path.normpath(os.path.expandvars(path)))


def is_imported(module_name: str):
    """Check if a module has been imported."""
    return module_name in sys.modules


def filter_integers(values: list[int | str | None]):
    """Return only the integer values in a list."""
    return [value for value in values if isinstance(value, int)]
