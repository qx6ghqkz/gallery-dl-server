# -*- coding: utf-8 -*-

"""
gallery-dl-server: Web UI for downloading media with gallery-dl and yt-dlp.

This package serves as a middleware for gallery-dl and yt-dlp, providing a simple
web and REST interface for downloading media from various websites.
"""

import sys

if sys.version_info < (3, 10):
    raise ImportError(
        "You are using an unsupported version of Python. "
        "Please upgrade to Python 3.10 or above to use gallery-dl-server."
    )

from . import app, options, utils, version

__version__ = version.__version__
__all__ = ["run"]


def run(
    host: str = "0.0.0.0",
    port: int = 0,
    log_dir: str = "~",
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
        TypeError: If an invalid parameter is passed to the function, it will raise a `TypeError`.

    Examples:
        To run the server on `localhost` with a specific port:

        ```python
        import gallery_dl_server as server

        if __name__ == "__main__":
            server.run(host="127.0.0.1", port=9080, log_level="info", access_log=False)
        ```

        To run the server on all interfaces with a random port and enable access logging:

        ```python
        import gallery_dl_server as server

        if __name__ == "__main__":
            server.run(host="0.0.0.0", port=0, log_level="debug", access_log=True)
        ```

        The `if __name__ == "__main__"` guard is necessary on Windows to prevent the server from
        starting itself recursively when attempting to initiate a download.

        This is because the server runs each download in a child process using the
        `multiprocessing` module, which uses `spawn` as the default start method on Windows.

        The `spawn` method creates a new Python interpreter which imports the main module,
        causing any unguarded code to be executed again in the child process.

        See the following:
        - https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
        - https://docs.python.org/3/library/multiprocessing.html#the-spawn-and-forkserver-start-methods
    """
    kwargs = {
        "host": host,
        "port": port,
        "log_dir": utils.normalise_path(log_dir),
        "log_level": log_level.lower(),
        "access_log": access_log,
    }

    try:
        args = options.custom_args = options.CustomNamespace(**kwargs)
        app.main(args)
    except TypeError:
        raise
