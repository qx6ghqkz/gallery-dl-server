# -*- coding: utf-8 -*-

import os
import sys
import multiprocessing

import uvicorn

from gallery_dl_server import options


def main(args: options.CustomNamespace | None = None):
    """Main entry point for running gallery-dl-server."""
    if args is None:
        try:
            args = options.parse_args(__name__)
        except TypeError as e:
            sys.stderr.write(f"{type(e).__name__}: {e}\n")
            sys.exit(1)

    from gallery_dl_server import output, server

    log = output.initialise_logging(__name__)

    multiprocessing.freeze_support()

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
    except KeyboardInterrupt as e:
        log.debug(f"Exception: {type(e).__name__}")
    except Exception as e:
        log.error(f"An unexpected error occurred: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
