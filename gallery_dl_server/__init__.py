import os
import multiprocessing
import queue
import shutil
import time

from contextlib import asynccontextmanager

import aiofiles

from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.responses import RedirectResponse, JSONResponse, StreamingResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.status import HTTP_303_SEE_OTHER
from starlette.templating import Jinja2Templates

from gallery_dl import version as gdl_version
from yt_dlp import version as ydl_version

from . import output, download
from .utils import resource_path


log_file = output.LOG_FILE

log = output.initialise_logging(__name__)
blank = output.get_blank_logger()

blank_sent = False


async def redirect(request):
    return RedirectResponse(url="/gallery-dl")


async def dl_queue_list(request):
    templates = Jinja2Templates(directory=resource_path("templates"))

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "gallerydl_version": gdl_version.__version__,
            "ytdlp_version": ydl_version.__version__,
        },
    )


async def q_put(request):
    global blank_sent

    if not blank_sent:
        blank.info("")
        blank_sent = True

    form = await request.form()
    url = form.get("url").strip()
    ui = form.get("ui")
    options = {"video-options": form.get("video-opts")}

    if not url:
        log.error("No URL provided.")

        if not ui:
            return JSONResponse(
                {"success": False, "error": "/q called without a 'url' in form data"}
            )

        return RedirectResponse(url="/gallery-dl", status_code=HTTP_303_SEE_OTHER)

    task = BackgroundTask(download_task, url, options)

    log.info("Added URL to the download queue: %s", url)

    if not ui:
        return JSONResponse(
            {"success": True, "url": url, "options": options}, background=task
        )

    return RedirectResponse(
        url="/gallery-dl?added=" + url, status_code=HTTP_303_SEE_OTHER, background=task
    )


async def log_route(request):
    async def file_iterator(file_path):
        async with aiofiles.open(file_path, mode="r", encoding="utf-8") as file:
            while True:
                chunk = await file.read(64 * 1024)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(file_iterator(log_file), media_type="text/plain")


@asynccontextmanager
async def lifespan(app):
    yield
    if os.path.isfile("/.dockerenv") and os.path.isdir("/config"):
        if os.path.isfile(log_file) and os.path.getsize(log_file) > 0:
            dst_dir = "/config/logs"

            os.makedirs(dst_dir, exist_ok=True)

            dst = os.path.join(
                dst_dir, "app_" + time.strftime("%Y-%m-%d_%H-%M-%S") + ".log"
            )
            shutil.copy2(log_file, dst)


def download_task(url, options):
    """Initiate download as a subprocess and log output."""
    log_queue = multiprocessing.Queue()

    process = multiprocessing.Process(
        target=download.run, args=(url, options, log_queue)
    )
    process.start()

    while True:
        if log_queue.empty() and not process.is_alive():
            break

        try:
            record_dict = log_queue.get(timeout=1)
            record = output.dict_to_record(record_dict)

            if record.levelno >= log.getEffectiveLevel():
                log.handle(record)

            if "Video should already be available" in record.getMessage():
                log.warning("Terminating process as video is not available")
                process.terminate()
        except queue.Empty:
            continue

    process.join()

    exit_code = process.exitcode

    if exit_code == 0:
        log.info("Download job completed with exit code: 0")
    else:
        log.error("Download job failed with exit code: %s", exit_code)


routes = [
    Route("/", endpoint=redirect, methods=["GET"]),
    Route("/gallery-dl", endpoint=dl_queue_list, methods=["GET"]),
    Route("/gallery-dl/q", endpoint=q_put, methods=["POST"]),
    Route("/gallery-dl/logs", endpoint=log_route, methods=["GET"]),
    Mount("/icons", app=StaticFiles(directory=resource_path("icons")), name="icons"),
]

app = Starlette(debug=True, routes=routes, lifespan=lifespan)
