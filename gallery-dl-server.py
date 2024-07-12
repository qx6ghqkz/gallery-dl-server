import sys
import subprocess

from starlette.status import HTTP_303_SEE_OTHER
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route, Mount
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from gallery_dl import config, job, version as gdl_version
from yt_dlp import version as ydl_version

templates = Jinja2Templates(directory="templates")


async def dl_queue_list(request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "gallerydl_version": gdl_version.__version__,
            "ytdlp_version": ydl_version.__version__,
        },
    )


async def redirect(request):
    return RedirectResponse(url="/gallery-dl")


async def q_put(request):
    form = await request.form()
    url = form.get("url").strip()
    ui = form.get("ui")
    options = {"format": form.get("format")}

    if not url:
        return JSONResponse(
            {"success": False, "error": "/q called without a 'url' in form data"}
        )

    task = BackgroundTask(download, url, options)

    print("Added url " + url + " to the download queue")

    if not ui:
        return JSONResponse(
            {"success": True, "url": url, "options": options}, background=task
        )
    return RedirectResponse(
        url="/gallery-dl?added=" + url, status_code=HTTP_303_SEE_OTHER, background=task
    )


async def update_route(scope, receive, send):
    task = BackgroundTask(update)

    return JSONResponse({"output": "Initiated package update"}, background=task)


def update():
    try:
        output = subprocess.check_output(
            [sys.executable, "-m", "pip", "install", "--upgrade", "gallery_dl"]
        )

        print(output.decode("utf-8"))
    except subprocess.CalledProcessError as e:
        print(e.output)
    try:
        output = subprocess.check_output(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
        )

        print(output.decode("utf-8"))
    except subprocess.CalledProcessError as e:
        print(e.output)


def config_update_options(request_options):
    requested_format = request_options.get("format", "video")

    if requested_format == "audio":
        config.set(
            ("extractor", "ytdl"),
            "raw-options",
            {
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "best",
                        "preferredquality": 320,
                    }
                ]
            },
        )


def download(url, request_options):
    config.clear()
    config.load()
    config_update_options(request_options)
    job.DownloadJob(url).run()


routes = [
    Route("/", endpoint=redirect),
    Route("/gallery-dl", endpoint=dl_queue_list),
    Route("/gallery-dl/q", endpoint=q_put, methods=["POST"]),
    Route("/gallery-dl/update", endpoint=update_route, methods=["PUT"]),
    Mount("/icons", StaticFiles(directory="icons"), name="icons"),
]

app = Starlette(debug=True, routes=routes)

print("\nUpdating gallery-dl and yt-dlp to the latest version . . . \n")
update()
