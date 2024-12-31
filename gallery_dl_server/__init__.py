import os
import sys
import subprocess
import re
import shutil
import time

from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.responses import RedirectResponse, JSONResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.status import HTTP_303_SEE_OTHER
from starlette.templating import Jinja2Templates

from gallery_dl import version as gdl_version
from yt_dlp import version as ydl_version

from . import output


log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "app.log")

os.makedirs(os.path.dirname(log_file), exist_ok=True)

log = output.initialise_logging(log_file)
blank = output.get_blank_logger()

blank_sent = False


async def redirect(request):
    return RedirectResponse(url="/gallery-dl")


async def dl_queue_list(request):
    templates = Jinja2Templates(directory="templates")

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

    task = BackgroundTask(download, url, options)

    log.info("Added URL to the download queue: %s", url)

    if not ui:
        return JSONResponse(
            {"success": True, "url": url, "options": options}, background=task
        )

    return RedirectResponse(
        url="/gallery-dl?added=" + url, status_code=HTTP_303_SEE_OTHER, background=task
    )


async def log_route(request):
    return FileResponse(log_file)


@asynccontextmanager
async def lifespan(app):
    yield
    if os.path.isdir("/config"):
        if os.path.isfile(log_file) and os.path.getsize(log_file) > 0:
            dst_dir = "/config/logs"

            os.makedirs(dst_dir, exist_ok=True)

            dst = os.path.join(
                dst_dir, "app_" + time.strftime("%Y-%m-%d_%H-%M-%S") + ".log"
            )
            shutil.copy2(log_file, dst)


def download(url, options):
    cmd = [sys.executable, "-m", "gallery_dl_server.download", url, str(options)]

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    while True:
        if process.stdout:
            output = process.stdout.readline()

            if output == "" and process.poll() is not None:
                break

            if output:
                formatted_output = remove_ansi_escape_sequences(output.rstrip())

                if formatted_output.startswith("# "):
                    log.warning(
                        "File already exists and/or its ID is in a download archive: %s",
                        formatted_output.removeprefix("# "),
                    )
                elif "[error]" in formatted_output.lower():
                    log.error(formatted_output)
                elif "[warning]" in formatted_output.lower():
                    log.warning(formatted_output)
                elif "[debug]" in formatted_output.lower():
                    log.debug(formatted_output)
                else:
                    log.info(formatted_output)

                if "Video should already be available" in formatted_output:
                    process.kill()
                    log.warning("Terminating process as video is not available.")

    exit_code = process.wait()

    if exit_code == 0:
        log.info("Download job completed with exit code: 0")
    else:
        log.error("Download job failed with exit code: %s", exit_code)

    return exit_code


def remove_ansi_escape_sequences(text):
    ansi_escape_pattern = re.compile(r"\x1B\[[0-?9;]*[mGKH]")
    return ansi_escape_pattern.sub("", text)


routes = [
    Route("/", endpoint=redirect, methods=["GET"]),
    Route("/gallery-dl", endpoint=dl_queue_list, methods=["GET"]),
    Route("/gallery-dl/q", endpoint=q_put, methods=["POST"]),
    Route("/gallery-dl/logs", endpoint=log_route, methods=["GET"]),
    Mount("/icons", app=StaticFiles(directory="icons"), name="icons"),
]

app = Starlette(debug=True, routes=routes, lifespan=lifespan)
