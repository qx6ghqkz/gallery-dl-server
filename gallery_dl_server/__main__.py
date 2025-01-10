import os
import multiprocessing

import uvicorn

import gallery_dl_server


if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run(
        gallery_dl_server.app,
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 0)),
        log_level=os.environ.get("LOG_LEVEL", "info"),
        access_log=os.environ.get("ACCESS_LOG", "False") == "True",
    )
