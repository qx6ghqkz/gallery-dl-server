# -*- coding: utf-8 -*-

import asyncio
import multiprocessing
import os
import queue
import shutil
import signal
import time

from contextlib import asynccontextmanager
from multiprocessing.queues import Queue
from types import FrameType
from typing import Any

import aiofiles
import watchfiles

from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.datastructures import UploadFile
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse, JSONResponse, StreamingResponse
from starlette.requests import Request
from starlette.routing import Route, WebSocketRoute, Mount
from starlette.staticfiles import StaticFiles
from starlette.status import (
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from starlette.templating import Jinja2Templates
from starlette.types import ASGIApp
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

import gallery_dl.version
import yt_dlp.version

from . import download, output, utils, version

custom_args = output.args

log_file = output.LOG_FILE
last_line = ""
last_position = 0

log = output.initialise_logging(__name__)


async def redirect(request: Request):
    """Redirect to homepage on request."""
    return RedirectResponse(url="/gallery-dl")


async def homepage(request: Request):
    """Return homepage template response."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_version": version.__version__,
            "gallery_dl_version": gallery_dl.version.__version__,
            "yt_dlp_version": yt_dlp.version.__version__,
        },
    )


async def submit_form(request: Request):
    """Process form submission data and start download in the background."""
    form_data = await request.form()

    keys = ("url", "video-opts")
    values = tuple(form_data.get(key) for key in keys)

    url, video_opts = (None if isinstance(value, UploadFile) else value for value in values)

    if not url:
        log.error("No URL provided.")

        return JSONResponse(
            {
                "success": False,
                "error": "/q called without a 'url' in form data",
            },
        )

    if not video_opts:
        video_opts = "none-selected"

    request_options = {"video-options": video_opts}

    task = BackgroundTask(download_task, url.strip(), request_options)

    log.info("Added URL to the download queue: %s", url)

    return JSONResponse(
        {
            "success": True,
            "url": url,
            "options": request_options,
        },
        background=task,
    )


def download_task(url: str, request_options: dict[str, str]):
    """Initiate download as a subprocess and log the output."""
    log_queue: Queue[dict[str, Any]] = multiprocessing.Queue()
    return_status: Queue[int] = multiprocessing.Queue()

    args = (url, request_options, log_queue, return_status, custom_args)

    process = multiprocessing.Process(target=download.run, args=args)
    process.start()

    while True:
        if log_queue.empty() and not process.is_alive():
            break
        try:
            record_dict = log_queue.get(timeout=1)
            record = output.dict_to_record(record_dict)

            if record.levelno >= output.LOG_LEVEL_MIN:
                log.handle(record)

            if "Video should already be available" in record.getMessage():
                log.warning("Terminating process as video is not available")
                process.kill()
        except queue.Empty:
            continue

    process.join()

    try:
        exit_code = return_status.get(block=False)
    except queue.Empty:
        exit_code = process.exitcode

    if exit_code == 0:
        log.info("Download process exited successfully")
    else:
        log.error("Download failed with exit code: %s", exit_code)


async def log_route(request: Request):
    """Return logs page template response."""

    async def read_log_file(file_path: str):
        log_contents = ""
        try:
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as file:
                async for line in file:
                    log_contents += line
        except FileNotFoundError:
            return "Log file not found."
        except Exception as e:
            log.debug(f"Exception: {type(e).__name__}: {e}")
            return f"An error occurred: {e}"

        return log_contents if log_contents else "No logs to display."

    logs = await read_log_file(log_file)

    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "app_version": version.__version__,
            "logs": logs,
        },
    )


async def clear_logs(request: Request):
    """Clear the log file on request."""
    try:
        with open(log_file, "w") as file:
            file.write("")

        return JSONResponse(
            {
                "success": True,
                "message": "Logs successfully cleared.",
            },
            status_code=HTTP_200_OK,
        )
    except FileNotFoundError:
        return JSONResponse(
            {
                "success": False,
                "error": "Log file not found.",
            },
            status_code=HTTP_404_NOT_FOUND,
        )
    except IOError:
        return JSONResponse(
            {
                "success": False,
                "error": "An error occurred while accessing the log file.",
            },
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        log.debug(f"Exception: {type(e).__name__}: {e}")

        return JSONResponse(
            {
                "success": False,
                "error": str(e),
            },
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def log_stream(request: Request):
    """Stream the full contents of the log file."""

    async def file_iterator(file_path: str):
        try:
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as file:
                while True:
                    chunk = await file.read(64 * 1024)
                    if not chunk:
                        break
                    if utils.WINDOWS:
                        yield chunk.replace("\n", "\r\n")
                    else:
                        yield chunk
        except FileNotFoundError:
            yield "Log file not found."
        except Exception as e:
            log.debug(f"Exception: {type(e).__name__}: {e}")
            yield f"An error occurred: {type(e).__name__}: {e}"

    return StreamingResponse(file_iterator(log_file), media_type="text/plain")


async def log_update(websocket: WebSocket):
    """Stream log file updates over WebSocket connection."""
    global last_line, last_position

    await websocket.accept()
    log.debug(f"Accepted WebSocket connection: {websocket}")

    async with connections_lock:
        active_connections.add(websocket)
        log.debug("WebSocket added to active connections")
    try:
        async with aiofiles.open(log_file, mode="r", encoding="utf-8") as file:
            await file.seek(0, os.SEEK_END)

            async for changes in watchfiles.awatch(
                log_file,
                stop_event=shutdown_event,
                rust_timeout=100,
                yield_on_timeout=True,
            ):
                new_content = ""
                do_update_state = False

                previous_line, position = await asyncio.to_thread(
                    output.read_previous_line, log_file, last_position
                )
                if "B/s" in previous_line and previous_line != last_line:
                    new_content = previous_line
                    do_update_state = True

                new_lines = await file.read()
                if new_lines.strip():
                    new_content += new_lines

                if new_content.strip():
                    await websocket.send_text(new_content)

                    if do_update_state:
                        last_line = previous_line
                        last_position = position
                    else:
                        last_line = ""
                        last_position = 0
    except asyncio.CancelledError as e:
        log.debug(f"Exception: {type(e).__name__}")
    except WebSocketDisconnect as e:
        log.debug(f"Exception: {type(e).__name__}")
    except Exception as e:
        log.debug(f"Exception: {type(e).__name__}: {e}")
    finally:
        async with connections_lock:
            if websocket in active_connections:
                active_connections.remove(websocket)
                log.debug("WebSocket removed from active connections")


@asynccontextmanager
async def lifespan(app: Starlette):
    """Run server startup and shutdown tasks."""
    output.configure_default_loggers()

    uvicorn_log = output.get_logger("uvicorn")
    uvicorn_log.info(f"Starting {type(app).__name__} application.")

    await shutdown_override()
    try:
        yield
    except asyncio.CancelledError:
        pass
    finally:
        if utils.CONTAINER and os.path.isdir("/config"):
            if os.path.isfile(log_file) and os.path.getsize(log_file) > 0:
                dst_dir = "/config/logs"

                os.makedirs(dst_dir, exist_ok=True)

                dst = os.path.join(dst_dir, "app_" + time.strftime("%Y-%m-%d_%H-%M-%S") + ".log")
                shutil.copy2(log_file, dst)


async def shutdown_override():
    """Override uvicorn signal handlers to ensure a graceful shutdown."""
    sigint_handler = signal.getsignal(signal.SIGINT)
    sigterm_handler = signal.getsignal(signal.SIGTERM)

    def shutdown(sig: int, frame: FrameType | None = None):
        """Call shutdown handler and then original handler as a callback."""
        global shutdown_in_progress
        if shutdown_in_progress:
            return

        shutdown_in_progress = True

        event_loop = asyncio.get_event_loop()
        future = asyncio.run_coroutine_threadsafe(shutdown_handler(), event_loop)
        future.add_done_callback(lambda f: call_original_handler(sig, frame))

    def call_original_handler(sig: int, frame: FrameType | None = None):
        """Call the original signal handler for server shutdown."""
        if sig == signal.SIGINT and callable(sigint_handler):
            sigint_handler(sig, frame)
        elif sig == signal.SIGTERM and callable(sigterm_handler):
            sigterm_handler(sig, frame)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)


async def shutdown_handler():
    """Initiate server shutdown."""
    if not shutdown_event.is_set():
        shutdown_event.set()
        log.debug("Set shutdown event")

    await close_connections()
    output.close_handlers()


async def close_connections():
    """Close WebSocket connections and clear the set of active connections."""
    async with connections_lock:
        log.debug(f"Active connections before closing: {len(active_connections)}")
        log.debug(f"Active tasks before closing: {len(asyncio.all_tasks())}")

        close_connections = []
        for websocket in active_connections:
            if websocket.client_state == WebSocketState.CONNECTED:
                close_connections.append(websocket.close())
                log.debug(f"Scheduled WebSocket for closure: {websocket}")

        if close_connections:
            await asyncio.gather(*close_connections)
            log.debug("Closed all WebSocket connections")

        if active_connections:
            active_connections.clear()
            log.debug("Cleared active connections")


class CSPMiddleware(BaseHTTPMiddleware):
    """Enforce Content Security Policy for all requests."""

    def __init__(self, app: ASGIApp, csp_policy: str):
        super().__init__(app)
        self.csp_policy = csp_policy

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = self.csp_policy
        return response


templates = Jinja2Templates(directory=utils.resource_path("templates"))

active_connections: set[WebSocket] = set()
connections_lock = asyncio.Lock()
shutdown_event = asyncio.Event()
shutdown_in_progress = False

routes = [
    Route("/", endpoint=redirect, methods=["GET"]),
    Route("/gallery-dl", endpoint=homepage, methods=["GET"]),
    Route("/gallery-dl/q", endpoint=submit_form, methods=["POST"]),
    Route("/gallery-dl/logs", endpoint=log_route, methods=["GET"]),
    Route("/gallery-dl/logs/clear", endpoint=clear_logs, methods=["POST"]),
    Route("/stream/logs", endpoint=log_stream, methods=["GET"]),
    WebSocketRoute("/ws/logs", endpoint=log_update),
    Mount("/static", app=StaticFiles(directory=utils.resource_path("static")), name="static"),
]

csp_policy = (
    "default-src 'self'; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "manifest-src 'self'; "
    "img-src 'self' data:; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com;"
)

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST"]),
    Middleware(CSPMiddleware, csp_policy=csp_policy),
]

app = Starlette(debug=True, routes=routes, middleware=middleware, lifespan=lifespan)
