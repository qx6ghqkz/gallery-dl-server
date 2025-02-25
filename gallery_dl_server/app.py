# -*- coding: utf-8 -*-

import os
import multiprocessing

import uvicorn

from . import options


def main(args: options.CustomNamespace | None = None, module_name: str | None = None):
    """Main entry point for gallery-dl-server."""
    if args is None:
        args = options.parse_args(module_name)

    multiprocessing.freeze_support()

    from . import server

    kwargs = {
        "app": server.app,
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "access_log": args.access_log,
        "proxy_headers": os.environ.get("PROXY_HEADERS", "true").lower() == "true",
        "forwarded_allow_ips": os.environ.get("FORWARDED_ALLOW_IPS", "*"),
    }

    uvicorn_config = uvicorn.Config(**kwargs)
    uvicorn_server = uvicorn.Server(uvicorn_config)

    try:
        uvicorn_server.run()
    except KeyboardInterrupt:
        pass
