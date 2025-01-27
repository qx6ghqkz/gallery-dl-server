# -*- coding: utf-8 -*-

import multiprocessing

import uvicorn

from gallery_dl_server import output, options, app


log = output.initialise_logging(__name__)


def main():
    multiprocessing.freeze_support()

    args = options.parse_args()

    opts = {
        "app": app,
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "access_log": args.access_log,
    }

    config = uvicorn.Config(**opts)
    server = uvicorn.Server(config)

    try:
        server.run()
    except KeyboardInterrupt as e:
        log.debug(f"Exception: {type(e).__name__}")


if __name__ == "__main__":
    main()
