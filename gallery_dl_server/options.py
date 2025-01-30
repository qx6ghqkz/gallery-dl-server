# -*- coding: utf-8 -*-

import os

from argparse import ArgumentParser, Namespace

from . import utils


def parse_args(module_name: str):
    """Parse command-line arguments and return namespace with the correct types."""
    prog_name = utils.get_package_name() if module_name == "__main__" else None

    parser = ArgumentParser(
        prog=prog_name, description="Run gallery-dl-server with custom options."
    )

    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("HOST", "0.0.0.0"),
        help="Host address (default: 0.0.0.0)",
    )

    default_port = os.environ.get("PORT", "0")
    try:
        default_port = int(default_port)
    except ValueError:
        default_port = 0

    parser.add_argument(
        "--port",
        type=int,
        default=default_port,
        help="Port number (default: selects any available port) [1024-65535]",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default=os.environ.get("LOG_LEVEL", "info"),
        help="Uvicorn log level (default: info) [critical|error|warning|info|debug|trace]",
    )

    parser.add_argument(
        "--access-log",
        type=str,
        default=os.environ.get("ACCESS_LOG", "false"),
        help="Enable Uvicorn access log (default: false) [true|false]",
    )

    args = parser.parse_args()

    return validate_args(parser, args)


def validate_args(parser: ArgumentParser, args: Namespace):
    """Validate arguments and return the correct types."""
    host: str = args.host
    port: int = args.port
    log_level: str = args.log_level
    access_log: str = args.access_log

    if port != 0 and (port < 1024 or port > 65535):
        parser.error("Port number must be between 1024 and 65535.")

    if log_level.lower() not in ["critical", "error", "warning", "info", "debug", "trace"]:
        parser.error("Invalid value for --log-level. Use -h to view options.")

    if access_log.lower() not in ["true", "false"]:
        parser.error("Invalid value for --access-log. Choose 'true' or 'false'.")

    access_log_bool: bool = access_log.lower() == "true"

    custom_args = CustomNamespace(
        host=host,
        port=port,
        log_level=log_level,
        access_log=access_log_bool,
    )

    return custom_args


class CustomNamespace(Namespace):
    """Custom namespace for type enforcement."""

    def __init__(self, host: str, port: int, log_level: str, access_log: bool):
        super().__init__()
        self.host = host
        self.port = port
        self.log_level = log_level
        self.access_log = access_log

        self._validate_types()

    def _validate_types(self):
        """Perform validation of types."""
        if not isinstance(self.host, str):
            raise TypeError(f"Expected 'host' to be of type str, got {type(self.host).__name__}")

        if not isinstance(self.port, int):
            raise TypeError(f"Expected 'port' to be of type int, got {type(self.port).__name__}")

        if not isinstance(self.log_level, str):
            raise TypeError(
                f"Expected 'log_level' to be of type str, got {type(self.log_level).__name__}"
            )

        if not isinstance(self.access_log, bool):
            raise TypeError(
                f"Expected 'access_log' to be of type bool, got {type(self.access_log).__name__}"
            )
