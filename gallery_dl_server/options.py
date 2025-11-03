# -*- coding: utf-8 -*-

import os

from argparse import ArgumentParser, Namespace

from . import utils

custom_args: "CustomNamespace | None" = None


def parse_args(is_main_module: bool = False):
    """Parse command-line arguments and return namespace with the correct types."""
    global custom_args
    if custom_args is not None:
        return custom_args

    prog_name = utils.get_package_name() if is_main_module else None

    parser = ArgumentParser(prog=prog_name, description="Run gallery-dl-server with custom options")

    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("HOST", "0.0.0.0"),
        help="host address (default: 0.0.0.0)",
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
        help="port number [0-65535] (default: any available port)",
    )

    parser.add_argument(
        "--log-dir",
        type=str,
        default=os.environ.get("LOG_DIR", ""),
        help="log file directory (default: user home directory)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default=os.environ.get("LOG_LEVEL", "info"),
        help="download log level [critical|error|warning|info|debug] (default: info)",
    )

    parser.add_argument(
        "--server-log-level",
        type=str,
        default=os.environ.get("SERVER_LOG_LEVEL", "info"),
        help="server log level [critical|error|warning|info|debug|trace] (default: info)",
    )

    parser.add_argument(
        "--access-log",
        type=str,
        default=os.environ.get("ACCESS_LOG", "false"),
        help="enable server access logging [true|false] (default: false)",
    )

    args = parser.parse_args()

    custom_args = validate_args(parser, args)

    return custom_args


def validate_args(parser: ArgumentParser, args: Namespace):
    """Validate arguments and return the correct types."""
    host: str = args.host
    port: int = args.port
    log_dir: str = args.log_dir
    log_level: str = args.log_level
    server_log_level: str = args.server_log_level
    access_log: str = args.access_log

    if port < 0 or port > 65535:
        parser.error("invalid value for --port, must be a valid integer between 0 and 65535")

    if log_dir != "" and not os.path.isdir(utils.normalise_path(log_dir)):
        parser.error("invalid value for --log-dir, must be a path to an existing directory")

    log_levels = ["critical", "error", "warning", "info", "debug"]

    if log_level.lower() not in log_levels:
        parser.error("invalid value for --log-level, use --help to view the valid options")

    log_levels.append("trace")

    if server_log_level.lower() not in log_levels:
        parser.error("invalid value for --server-log-level, use --help to view the valid options")

    if access_log.lower() not in ["true", "false"]:
        parser.error("invalid value for --access-log, must be 'true' or 'false'")

    return CustomNamespace(
        host=host,
        port=port,
        log_dir=utils.normalise_path(log_dir),
        log_level=log_level.lower(),
        server_log_level=server_log_level.lower(),
        access_log=access_log.lower() == "true",
    )


def get_default_args():
    """Bypass argument parsing and return the default arguments."""
    host = os.environ.get("HOST", "0.0.0.0")
    port = os.environ.get("PORT", "0")
    log_dir = os.environ.get("LOG_DIR", "")
    log_level = os.environ.get("LOG_LEVEL", "info")
    server_log_level = os.environ.get("SERVER_LOG_LEVEL", "info")
    access_log = os.environ.get("ACCESS_LOG", "false")

    return CustomNamespace(
        host=host,
        port=int(port),
        log_dir=utils.normalise_path(log_dir),
        log_level=log_level.lower(),
        server_log_level=server_log_level.lower(),
        access_log=access_log.lower() == "true",
    )


class CustomNamespace(Namespace):
    """Custom namespace for type enforcement."""

    def __init__(
        self,
        host: str,
        port: int,
        log_dir: str,
        log_level: str,
        server_log_level: str,
        access_log: bool,
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.log_dir = log_dir
        self.log_level = log_level
        self.server_log_level = server_log_level
        self.access_log = access_log

        self._validate_types()

    def _validate_types(self):
        """Perform type validation."""
        if not isinstance(self.host, str):
            raise TypeError(
                "Expected 'host' to be of type str, got {}".format(type(self.host).__name__)
            )

        if not isinstance(self.port, int):
            raise TypeError(
                "Expected 'port' to be of type int, got {}".format(type(self.port).__name__)
            )

        if not isinstance(self.log_dir, str):
            raise TypeError(
                "Expected 'log_dir' to be of type str, got {}".format(type(self.log_dir).__name__)
            )

        if not isinstance(self.log_level, str):
            raise TypeError(
                "Expected 'log_level' to be of type str, got {}".format(
                    type(self.log_level).__name__
                )
            )

        if not isinstance(self.server_log_level, str):
            raise TypeError(
                "Expected 'server_log_level' to be of type str, got {}".format(
                    type(self.server_log_level).__name__
                )
            )

        if not isinstance(self.access_log, bool):
            raise TypeError(
                "Expected 'access_log' to be of type bool, got {}".format(
                    type(self.access_log).__name__
                )
            )
