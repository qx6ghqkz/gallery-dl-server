from gallery_dl import job, exception

from . import config, output


log = output.initialise_logging(__name__)


def run(url, options, log_queue, return_status):
    """Set gallery-dl configuration, set up logging and run download job."""
    config.clear()

    config_files = [
        "/config/gallery-dl.conf",
        "/config/config.json",
    ]

    config.load(config_files)

    output.setup_logging()

    output.capture_logs(log_queue)

    output.redirect_standard_streams()

    log.info(f"Requested download with the following options: {options}")

    entries = config_update(options)

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
        log.error(f"Exception: {e}")

    return_status.put(status)


def config_update(options):
    """Update loaded configuration with request options."""
    entries_added = []
    entries_removed = []

    requested_format = options.get("video-options", "none-selected")

    if requested_format == "download-video":
        try:
            cmdline_args = (
                config._config.get("extractor", {})
                .get("ytdl", {})
                .get("cmdline-args", [])
            )
        except AttributeError:
            pass
        else:
            entries_removed.extend(
                config.remove(cmdline_args, item="--extract-audio")
                + config.remove(cmdline_args, item="-x")
            )

        try:
            raw_options = (
                config._config.get("extractor", {})
                .get("ytdl", {})
                .get("raw-options", {})
            )
        except AttributeError:
            pass
        else:
            entries_removed.extend(
                config.remove(raw_options, key="writethumbnail", value=False)
            )

        try:
            postprocessors = (
                config._config.get("extractor", {})
                .get("ytdl", {})
                .get("raw-options", {})
                .get("postprocessors", [])
            )
        except AttributeError:
            pass
        else:
            entries_removed.extend(
                config.remove(postprocessors, key="key", value="FFmpegExtractAudio")
            )

    if requested_format == "extract-audio":
        entries_added.extend(
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
            )[1]
            + config.add(
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
            )[1]
        )

        try:
            cmdline_args = (
                config._config.get("extractor", {})
                .get("ytdl", {})
                .get("cmdline-args", [])
            )
        except AttributeError:
            pass
        else:
            entries_removed.extend(
                config.remove(cmdline_args, item="--merge-output-format", value="any")
            )

    return (entries_added, entries_removed)
