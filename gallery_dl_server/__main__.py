import os

import uvicorn

from . import app


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 9080)),
        log_level=os.environ.get("LOG_LEVEL", "info"),
        access_log=os.environ.get("ACCESS_LOG", "False") == "True",
    )
