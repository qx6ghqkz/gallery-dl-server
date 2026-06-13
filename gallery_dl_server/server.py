# -*- coding: utf-8 -*-

import asyncio
import mimetypes
import multiprocessing
import os
import queue
import shutil
import signal
import time

from contextlib import asynccontextmanager
from multiprocessing.queues import Queue
from pathlib import Path
from types import FrameType
from typing import Any
from urllib.parse import quote

import aiofiles
import watchfiles

from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.datastructures import UploadFile
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse, JSONResponse, StreamingResponse, FileResponse
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

from . import config as server_config
from . import download, output, utils, version

custom_args = output.args

log_file = output.LOG_FILE
last_line = ""
last_position = 0

log = output.initialise_logging(__name__)

MEDIA_EXTENSIONS = {
    ".aac": "audio",
    ".aif": "audio",
    ".aiff": "audio",
    ".flac": "audio",
    ".m4a": "audio",
    ".mp3": "audio",
    ".oga": "audio",
    ".ogg": "audio",
    ".opus": "audio",
    ".wav": "audio",
    ".weba": "audio",
    ".avif": "image",
    ".bmp": "image",
    ".gif": "image",
    ".jpeg": "image",
    ".jpg": "image",
    ".png": "image",
    ".svg": "image",
    ".webp": "image",
    ".avi": "video",
    ".m4v": "video",
    ".mkv": "video",
    ".mov": "video",
    ".mp4": "video",
    ".mpeg": "video",
    ".mpg": "video",
    ".ogv": "video",
    ".webm": "video",
}
MEDIA_LIMIT = 500
MEDIA_ROOT_CACHE_SECONDS = 10.0
media_root_cache: Path | None = None
media_root_cache_time = 0.0


async def redirect(request: Request):
    """Redirect to homepage on request."""
    return RedirectResponse(url="/gallery-dl")


async def homepage(request: Request):
    """Return homepage template response."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {
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
        request,
        "logs.html",
        {
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


def get_media_root():
    """Return the configured download directory for media browsing."""
    global media_root_cache, media_root_cache_time

    now = time.monotonic()
    if media_root_cache and now - media_root_cache_time < MEDIA_ROOT_CACHE_SECONDS:
        return media_root_cache

    try:
        server_config.clear()
        server_config.load()
        media_root = server_config.get(["extractor", "base-directory"])
    except Exception as e:
        log.debug(f"Exception while loading media root: {type(e).__name__}: {e}")
        media_root = None

    if not media_root:
        media_root = "/gallery-dl" if utils.CONTAINER else os.path.join(os.getcwd(), "gallery-dl")

    media_root_cache = Path(utils.normalise_path(str(media_root))).resolve()
    media_root_cache_time = now

    return media_root_cache


def get_media_kind(path: Path):
    """Return the broad media type for a file path."""
    return MEDIA_EXTENSIONS.get(path.suffix.lower())


def is_path_within(path: Path, root: Path):
    """Return whether a resolved path is inside a resolved root directory."""
    try:
        os.path.commonpath([str(path), str(root)])
    except ValueError:
        return False

    return os.path.commonpath([str(path), str(root)]) == str(root)


def build_media_item(path: Path, media_root: Path):
    """Build a JSON-serialisable media item for the browser UI."""
    stat = path.stat()
    relative_path = path.relative_to(media_root).as_posix()
    media_type = get_media_kind(path)

    return {
        "name": path.name,
        "path": relative_path,
        "directory": path.parent.relative_to(media_root).as_posix(),
        "type": media_type,
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "url": "/gallery-dl/media/" + quote(relative_path),
    }


def get_media_items(media_root: Path):
    """Return recent media files from the configured download directory."""
    items = []
    total = 0

    if not media_root.is_dir():
        return items, total

    for root, dirnames, filenames in os.walk(media_root):
        dirnames[:] = [dirname for dirname in dirnames if not dirname.startswith(".")]

        for filename in filenames:
            path = Path(root, filename)

            if filename.startswith(".") or not get_media_kind(path):
                continue

            try:
                resolved_path = path.resolve()
                if not is_path_within(resolved_path, media_root):
                    continue

                total += 1
                items.append(build_media_item(resolved_path, media_root))
            except OSError as e:
                log.debug(f"Exception while reading media file: {type(e).__name__}: {e}")

    items.sort(key=lambda item: item["modified"], reverse=True)

    return items[:MEDIA_LIMIT], total


async def media_index(request: Request):
    """Return downloaded media files for the web UI."""
    media_root = get_media_root()
    items, total = await asyncio.to_thread(get_media_items, media_root)

    return JSONResponse(
        {
            "root": str(media_root),
            "exists": media_root.is_dir(),
            "total": total,
            "limit": MEDIA_LIMIT,
            "items": items,
        }
    )


async def media_file(request: Request):
    """Serve a downloaded media file from the configured media directory."""
    media_root = get_media_root()
    requested_path = (media_root / request.path_params["path"]).resolve()

    if (
        not is_path_within(requested_path, media_root)
        or not requested_path.is_file()
        or not get_media_kind(requested_path)
    ):
        return JSONResponse(
            {
                "success": False,
                "error": "Media file not found.",
            },
            status_code=HTTP_404_NOT_FOUND,
        )

    media_type, _encoding = mimetypes.guess_type(requested_path.name)
    return FileResponse(requested_path, media_type=media_type)


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
    Route("/gallery-dl/media", endpoint=media_index, methods=["GET"]),
    Route("/gallery-dl/media/{path:path}", endpoint=media_file, methods=["GET", "HEAD"]),
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
    "media-src 'self'; "
    "object-src 'none'; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com;"
)

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST"]),
    Middleware(CSPMiddleware, csp_policy=csp_policy),
]

app = Starlette(debug=True, routes=routes, middleware=middleware, lifespan=lifespan)
