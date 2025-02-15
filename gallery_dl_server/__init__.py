# -*- coding: utf-8 -*-

"""
gallery-dl-server: Web UI for downloading media with gallery-dl and yt-dlp.

This package serves as a middleware for gallery-dl and yt-dlp, providing a simple
web and REST interface for downloading media from various websites.
"""

import os
import sys

from . import version

if sys.version_info < (3, 10):
    raise ImportError(
        "You are using an unsupported version of Python. "
        "Please upgrade to Python 3.10 or above to use gallery-dl-server."
    )

__version__ = version.__version__
__all__ = ["run"]


def run(
    host: str = "0.0.0.0",
    port: int = 0,
    log_dir: str = os.path.expanduser("~"),
    log_level: str = "info",
    access_log: bool = False,
) -> None:
    """
    Run gallery-dl-server with custom options.

    Args:
        host (str): The host address for the server
            (`0.0.0.0` listens on all available interfaces, allowing access from any IP address).

        port (int): The port number for the server
            (`0` selects a random port).

        log_dir (str): The directory for the log file
            (defaults to the user's home directory on the operating system).

        log_level (str): The log level
            (accepted values: `critical`, `error`, `warning`, `info`, `debug`, `trace`).

        access_log (bool): Enable or disable the access log only, without changing the log level
            (i.e. show `GET` requests, WebSocket connections, etc.).

    Raises:
        SystemExit: If an error occurs during execution, an error message will be written to
            standard error, and the program will exit with a status code of 1.

    Examples:
        To run the server on `localhost` with a specific port:

        ```python
        run(host="127.0.0.1", port=9080, log_level="info", access_log=False)
        ```

        To run the server on all interfaces with a random port and enable access logging:

        ```python
        run(host="0.0.0.0", port=0, log_level="debug", access_log=True)
        ```
    """
    from . import __main__ as main, options

    kwargs = {
        "host": host,
        "port": port,
        "log_dir": log_dir,
        "log_level": log_level,
        "access_log": access_log,
    }

    try:
        args = options.custom_args = options.CustomNamespace(**kwargs)
        main.main(args)
    except TypeError as e:
        sys.stderr.write(f"{type(e).__name__}: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"An unexpected error occurred: {type(e).__name__}: {e}\n")
        sys.exit(1)
