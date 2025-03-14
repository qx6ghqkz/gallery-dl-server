# -*- coding: utf-8 -*-

import uvicorn

from . import options


def main(
    app: str = "gallery_dl_server.server:app",
    args: options.CustomNamespace | None = None,
    is_main_module: bool = False,
):
    """Main entry point for gallery-dl-server."""
    if args is None:
        args = options.parse_args(is_main_module)

    kwargs = {
        "host": args.host,
        "port": args.port,
        "log_level": args.server_log_level,
        "access_log": args.access_log,
    }

    try:
        uvicorn.run(app, **kwargs)
    except KeyboardInterrupt:
        pass
