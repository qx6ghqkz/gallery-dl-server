# -*- coding: utf-8 -*-

import uvicorn

from . import options


def main(
    args: options.CustomNamespace | None = None,
    module_name: str | None = None,
):
    """Main entry point for gallery-dl-server."""
    if args is None:
        args = options.parse_args(module_name)

    from . import server

    kwargs = {
        "app": server.app,
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "access_log": args.access_log,
    }

    uvicorn_config = uvicorn.Config(**kwargs)
    uvicorn_server = uvicorn.Server(uvicorn_config)

    try:
        uvicorn_server.run()
    except KeyboardInterrupt:
        pass
