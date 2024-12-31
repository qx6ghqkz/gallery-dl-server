import os

import uvicorn

from . import app


if __name__ == "__main__":
    port = int(
        os.environ.get("CONTAINER_PORT", 9080),
    )
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info", access_log=False)
