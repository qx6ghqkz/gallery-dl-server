# -*- coding: utf-8 -*-

import uvicorn

from . import options, utils


def main(
    args: options.CustomNamespace | None = None,
    module_name: str | None = None,
):
    """Main entry point for gallery-dl-server."""
    if args is None:
        args = options.parse_args(module_name)

    kwargs = {
        "host": args.host,
        "port": args.port,
        "log_level": args.server_log_level,
        "access_log": args.access_log,
        "workers": 1 if utils.WINDOWS else 2,
    }

    app = "gallery_dl_server.server:app"

    try:
        uvicorn.run(app, **kwargs)
    except KeyboardInterrupt:
        pass
