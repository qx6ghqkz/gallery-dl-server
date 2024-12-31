import sys
import ast

from gallery_dl import job

from . import config, output


def run(url, options):
    config.clear()

    config_files = [
        "/config/gallery-dl.conf",
        "/config/config.json",
    ]

    config.load(config_files)

    output.setup_logging()

    output.stdout_write(
        f"Requesting download with the following overriding options: {options}"
    )

    entries = config_update(options)

    if any(entries[0]):
        output.stdout_write(f"Added entries to the config dict: {entries[0]}")

    if any(entries[1]):
        output.stdout_write(f"Removed entries from the config dict: {entries[1]}")

    status = job.DownloadJob(url).run()

    return status


def config_update(options):
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


if __name__ == "__main__":
    run(sys.argv[1], ast.literal_eval(sys.argv[2]))
