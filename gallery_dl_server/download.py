# -*- coding: utf-8 -*-

from itertools import chain
from multiprocessing.queues import Queue
from typing import Any

from gallery_dl import job, exception

from . import options


def _init(custom_args: options.CustomNamespace | None):
    """Import required modules and set up basic logging.

    Ensures that parsed command-line arguments are set in the
    memory space of the current process if supplied.
    """
    global config, output, log

    if options.custom_args is None and custom_args is not None:
        options.custom_args = custom_args

    from . import config, output

    output.configure_default_loggers(is_main_process=False)

    log = output.initialise_logging(__name__)


def run(
    url: str,
    request_options: dict[str, str],
    log_queue: Queue[dict[str, Any]],
    return_status: Queue[int],
    custom_args: options.CustomNamespace | None,
):
    """Set gallery-dl configuration, set up logging and run download job."""
    _init(custom_args)

    config_files = [
        "/config/gallery-dl.conf",
        "/config/config.json",
    ]

    config.clear()
    config.load(config_files)

    output.setup_logging()
    output.capture_logs(log_queue)
    output.redirect_standard_streams()

    log.info(f"Requested download with the following options: {request_options}")

    entries = config_update(request_options)

    if any(entries[0]):
        log.info(f"Added entries to the config dict: {entries[0]}")

    if any(entries[1]):
        log.info(f"Removed entries from the config dict: {entries[1]}")

    status = 0
    try:
        status = job.DownloadJob(url).run()
    except exception.GalleryDLException as e:
        status = e.code
        log.error(f"Exception: {e.__module__}.{type(e).__name__}: {e}")
    except Exception as e:
        status = -1
        log.error(f"Exception: {type(e).__name__}: {e}")
    except KeyboardInterrupt:
        pass

    output.close_handlers()

    return_status.put(status)


def config_update(request_options: dict[str, str]):
    """Update loaded configuration with request options."""
    entries_added: list[dict[str, Any] | None] = []
    entries_removed: list[Any] = []

    requested_format = request_options.get("video-options", "none-selected")

    if requested_format == "none-selected":
        return entries_added, entries_removed

    cmdline_args = config.get(["extractor", "ytdl", "cmdline-args"])
    raw_options = config.get(["extractor", "ytdl", "raw-options"])
    postprocessors = config.get(["postprocessors"], conf=raw_options)

    if requested_format == "download-video":
        entries_removed.extend(
            chain(
                config.remove(cmdline_args, item="--extract-audio"),
                config.remove(cmdline_args, item="-x"),
                config.remove(raw_options, key="writethumbnail", value=False),
                config.remove(postprocessors, key="key", value="FFmpegExtractAudio"),
            )
        )

    if requested_format == "extract-audio":
        entries_added.extend(
            chain(
                config.add(
                    {
                        "extractor": {
                            "ytdl": {
                                "cmdline-args": [
                                    "--extract-audio",
                                ]
                            }
                        }
                    }
                )[1],
                config.add(
                    {
                        "extractor": {
                            "ytdl": {
                                "raw-options": {
                                    "writethumbnail": False,
                                    "postprocessors": [
                                        {
                                            "key": "FFmpegExtractAudio",
                                            "preferredcodec": "best",
                                            "preferredquality": 320,
                                        }
                                    ],
                                }
                            }
                        }
                    }
                )[1],
            )
        )

        entries_removed.extend(
            config.remove(cmdline_args, item="--merge-output-format", value="any")
        )

    return entries_added, entries_removed
