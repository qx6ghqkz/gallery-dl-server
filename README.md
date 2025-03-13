# gallery-dl-server

[![GitHub Release](https://img.shields.io/github/v/release/qx6ghqkz/gallery-dl-server?logo=github&style=for-the-badge)](https://github.com/qx6ghqkz/gallery-dl-server/releases/latest "Latest Release")
[![PyPI - Version](https://img.shields.io/pypi/v/gallery-dl-server?logo=pypi&style=for-the-badge)](https://pypi.org/project/gallery-dl-server "PyPI")
[![Docker Image Version](https://img.shields.io/docker/v/qx6ghqkz/gallery-dl-server?logo=docker&label=Docker&sort=semver&style=for-the-badge)](https://hub.docker.com/r/qx6ghqkz/gallery-dl-server "Docker")
[![Docker Pulls](https://img.shields.io/docker/pulls/qx6ghqkz/gallery-dl-server.svg?logo=docker&style=for-the-badge)](https://hub.docker.com/r/qx6ghqkz/gallery-dl-server/tags "Docker Tags")
[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/qx6ghqkz/gallery-dl-server/docker-image.yaml?branch=main&style=for-the-badge)](https://github.com/qx6ghqkz/gallery-dl-server/actions "GitHub Actions")
[![Commits](https://img.shields.io/github/commit-activity/m/qx6ghqkz/gallery-dl-server?label=Commits&style=for-the-badge)](https://github.com/qx6ghqkz/gallery-dl-server/commits/main/ "Commit History")
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=for-the-badge)](https://raw.githubusercontent.com/qx6ghqkz/gallery-dl-server/master/LICENSE "License")

![screenshot](https://raw.githubusercontent.com/qx6ghqkz/gallery-dl-server/refs/heads/main/images/gallery-dl-server.png)

Web UI for [`gallery-dl`](https://github.com/mikf/gallery-dl) with support for downloading videos via [`yt-dlp`](https://github.com/yt-dlp/yt-dlp).

* [Running](https://github.com/qx6ghqkz/gallery-dl-server#running)
  * [Docker](https://github.com/qx6ghqkz/gallery-dl-server#docker)
  * [Python](https://github.com/qx6ghqkz/gallery-dl-server#python)
  * [Standalone Executable](https://github.com/qx6ghqkz/gallery-dl-server#standalone-executable)
* [Options](https://github.com/qx6ghqkz/gallery-dl-server#options)
* [Dependencies](https://github.com/qx6ghqkz/gallery-dl-server#dependencies)
* [Configuration](https://github.com/qx6ghqkz/gallery-dl-server#configuration)
* [Usage](https://github.com/qx6ghqkz/gallery-dl-server#usage)
* [Implementation](https://github.com/qx6ghqkz/gallery-dl-server#implementation)
* [Useful Links](https://github.com/qx6ghqkz/gallery-dl-server#useful-links)

## Running

### Docker

#### Docker Run

This example uses the `docker run` command to create the container to run the app.

```shell
docker run -d \
  --name gallery-dl \
  -p "9080:9080" \
  -e "UID=1000" \
  -e "GID=1000" \
  -v "/path/to/config:/config" \
  -v "/path/to/downloads:/gallery-dl" \
  --restart on-failure \
  qx6ghqkz/gallery-dl-server:latest
```

#### Docker Compose

This is an example of a `docker-compose.yaml` service definition which can be used to start a running container with the `docker compose up -d` command.

```yaml
services:
  gallery-dl:
    image: qx6ghqkz/gallery-dl-server:latest
    container_name: gallery-dl
    ports:
      - "9080:9080"
    environment:
      - "UID=1000"
      - "GID=1000"
    volumes:
      - "/path/to/config:/config"
      - "/path/to/downloads:/gallery-dl"
    restart: on-failure
```

This is another example which uses a VPN client container for its networking.

```yaml
services:
  gallery-dl:
    image: qx6ghqkz/gallery-dl-server:latest
    container_name: gallery-dl
    network_mode: container:vpn
    environment:
      - "UID=1000"
      - "GID=1000"
    volumes:
      - "/path/to/config:/config"
      - "/path/to/downloads:/gallery-dl"
    restart: on-failure
```

[Gluetun](https://github.com/qdm12/gluetun) is recommended for VPN usage. See [docs/docker-compose.yaml](https://github.com/qx6ghqkz/gallery-dl-server/blob/main/docs/docker-compose.yaml) for an example.

#### Port Mapping

By default, this service listens on port 9080. Any value can be used for the host port, but the `CONTAINER_PORT` environment variable must be set to change the internal container port. This can be done using the `-e` flag with `docker run` or in a Docker Compose file.

For example, to run multiple instances of gallery-dl-server using a single [Gluetun](https://github.com/qdm12/gluetun) instance for the networking (each instance must use a different internal port), a different container port can be set for one of the containers.

```yaml
services:
  instance-1:
    image: qx6ghqkz/gallery-dl-server:latest
    container_name: day
    depends_on:
      - gluetun
    network_mode: service:gluetun
    # More settings here...

  instance-2:
    image: qx6ghqkz/gallery-dl-server:latest
    container_name: night
    environment:
      - "CONTAINER_PORT=9090"
    depends_on:
      - gluetun
    network_mode: service:gluetun
    # More settings here...

  gluetun:
    image: qmcgaw/gluetun:latest
    container_name: vpn
    ports:
      # instance-1
      - "9080:9080"
      # instance-2
      - "9090:9090"
    # More settings here...
```

#### Important Notes

- Make sure to mount the directory containing the configuration file rather than the file itself. This ensures changes to the configuration file are propagated to the running Docker container and it will not need to be restarted for changes to take effect. More information on this issue [here](https://github.com/moby/moby/issues/15793#issuecomment-135411504).

- The output download directory depends on the `base-directory` in your gallery-dl configuration file. Make sure it is the absolute path `/gallery-dl/` instead of the relative path `./gallery-dl/` or else the download directory will need to be mounted to `/usr/src/app/gallery-dl` instead (not recommended).

- The environment variables `UID` and `GID` can be used to change the user ID and group ID of the user running the server process. This is important because downloaded files will be owned by that user. Make sure the IDs match those of the user on the host system. The default `UID:GID` is `1000:1000` when left unspecified.

### Python

If Python 3.10 or later (3.12 is recommended) is installed and on the PATH, the server can simply be run from the command line.

#### Run from Source

Clone this repository and install the dependencies located in `requirements.txt` in a virtual environment, then run the command below in the root folder while inside the virtual environment. On Windows, replace `python3` with `python`.

```shell
python3 -m gallery_dl_server --host "0.0.0.0" --port "9080"
```

The command-line arguments are optional. By default, the server will run on host `0.0.0.0` and an available port will be selected if one is not provided.

To view the full list of command-line arguments, perform `python3 -m gallery_dl_server --help`. These arguments can also be provided as environment variables.

#### Installation

Installation allows running directly from the command line via the command `gallery-dl-server`. Using a virtual environment is recommended to avoid dependency conflicts.

From [PyPI](https://pypi.org/project/gallery-dl-server):

```shell
pip install gallery-dl-server
```

With optional dependencies:

```shell
pip install gallery-dl-server[full]
```

From source code (perform command in the root of the repository):

```shell
pip install .
```

With optional dependencies:

```shell
pip install .[full]
```

Once installed, perform `gallery-dl-server --help` to view the list of command-line options.

When installed, the log file is created directly in the home directory of the user, unless the package is found in the current working directory, in which case it is created in a `logs` folder in the same directory.

#### Run Programmatically

```python
import gallery_dl_server as server

server.run(host="0.0.0.0", port=9080, log_level="info")
```
The `run()` method needs to be guarded with an `if __name__ == "__main__"` block on Windows due to how multiprocessing works.

#### Run with Uvicorn

```shell
python3 -m uvicorn gallery_dl_server.server:app --host "0.0.0.0" --port "9080" --log-level "info" --no-access-log
```

### Standalone Executable

On Windows, the program can be run using the prebuilt `.exe` file, which includes a Python interpreter and the required Python packages. Prebuilt executables for each release can be found in [Releases](https://github.com/qx6ghqkz/gallery-dl-server/releases).

The executable can be run from the command line with the same arguments as the Python package.

```cmd
gallery-dl-server.exe --host "0.0.0.0" --port "9080"
```

When run as an executable, the log file will be created in a `logs` folder in the same directory as the executable.

Configuration files can also be loaded from the same directory as the executable. The bundled releases contain a default configuration file in JSON, YAML and TOML formats.

## Options

The server can be configured with numerous command-line arguments and environment variables. Command-line arguments take precedence over their equivalent environment variables.

Use the arguments when running the server directly from the command line, and the environment variables for configuring the server inside running containers.

| Command-Line Argument | Environment Variable | Docker Only | Type   | Expected Values                                                    | Default Value | Description                        |
|-----------------------|----------------------|-------------|--------|--------------------------------------------------------------------|---------------|------------------------------------|
| `‑‑host`              | `HOST`               | &cross;     | `str`  | IP address or hostname                                             | `0.0.0.0`     | Specify the host address           |
| `‑‑port`              | `PORT`               | &cross;     | `int`  | `0–65535`                                                          | `0`           | Specify the port to run the app    |
|                       | `CONTAINER_PORT`     | &check;     | `int`  | `0–65535`                                                          | `9080`        | Set the internal container port    |
| &mdash;               | `UID`                | &check;     | `int`  | Any valid user ID                                                  | `1000`        | User ID to run the server process  |
| &mdash;               | `GID`                | &check;     | `int`  | Any valid group ID                                                 | `1000`        | Group ID to run the server process |
| &mdash;               | `UMASK`              | &check;     | `int`  | Any valid `umask` value                                            | `002`         | Set `umask` for file permissions   |
| `‑‑log‑dir`           | `LOG_DIR`            | &cross;     | `str`  | Any existing directory                                             | `~`           | Set the log file directory         |
| `‑‑log‑level`         | `LOG_LEVEL`          | &cross;     | `str`  | `critical`<br>`error`<br>`warning`<br>`info`<br>`debug`            | `info`        | Set the download log level         |
| `‑‑server‑log‑level`  | `SERVER_LOG_LEVEL`   | &cross;     | `str`  | `critical`<br>`error`<br>`warning`<br>`info`<br>`debug`<br>`trace` | `info`        | Set the server log level           |
| `‑‑access‑log`        | `ACCESS_LOG`         | &cross;     | `bool` | `true`<br>`false`                                                  | `false`       | Enable the server access log       |

Note: `CONTAINER_PORT` takes precedence over the `PORT` environment variable in Docker containers to set the port the server will run on internally. This value and `HOST` should not normally need to be changed from their default values for Docker running.

## Dependencies

All required and optional Python and non-Python dependencies are included in the Docker image, however if you are running gallery-dl-server using any of the other methods, some dependencies may need to be installed separately.

In order to run with Python, the dependencies in `requirements.txt` need to be installed in the running Python environment. These are included in the standalone executable and do not need to be installed.

Installation with `pip` only installs the required dependencies by default. Install `gallery-dl-server[full]` for the optional dependencies.

### Optional

- [`brotli`](https://github.com/google/brotli) or [`brotlicffi`](https://github.com/python-hyper/brotlicffi): Brotli content encoding support
- [`mutagen`](https://github.com/quodlibet/mutagen): embed metadata and thumbnails in certain formats
- [`pycryptodomex`](https://github.com/Legrandin/pycryptodome): decrypt AES-128 HLS streams and other forms of data
- [`pyyaml`](https://pyyaml.org): YAML configuration file support
- [`toml`](https://pypi.org/project/toml): TOML configuration file support (<= Python 3.10 only)

Non-Python dependencies must be installed separately. [`FFmpeg`](https://ffmpeg.org) is strongly recommended for video and audio conversion and should be accessible from the command line, i.e. on the PATH.

There is also [`MKVToolNix`](https://mkvtoolnix.download/index.html), which includes [`mkvmerge`](https://www.matroska.org/downloads/mkvtoolnix.html) for accurate [Ugoira](https://www.pixiv.help/hc/en-us/articles/235584628-What-are-Ugoira) frame timecodes.

Dependencies for [gallery-dl](https://github.com/mikf/gallery-dl#dependencies) and [yt-dlp](https://github.com/yt-dlp/yt-dlp#dependencies) are documented in their respective repositories.

## Configuration

Configuration of gallery-dl is as documented in the [official documentation](https://github.com/mikf/gallery-dl#configuration). A configuration file is required.

If run outside of Docker, the [default locations](https://github.com/mikf/gallery-dl#locations) will be used to search for a configuration file. If run as an executable, the current directory will also be searched for a valid configuration file.

Additionally, YAML and TOML configuration files are supported at any of the pre-defined locations.

When run with Docker, the configuration file must be inside the directory mounted to `/config` inside the container.

### Locations

- `/config/gallery-dl.{conf, toml, yaml, yml}`
- `/config/config.{json, toml, yaml, yml}`

A [default configuration file](https://github.com/qx6ghqkz/gallery-dl-server/blob/main/docs/gallery-dl.conf) for use with gallery-dl-server will automatically be placed in the directory mounted to `/config` if none are found.

For more information on configuration file options, see [gallery-dl/docs/configuration.rst](https://github.com/mikf/gallery-dl/blob/master/docs/configuration.rst).

Any additional locations specified in the configuration file must also exist in the Docker container. For example, if a cookies file is required, ensure it is also mounted inside the Docker container.

It is easiest to place any additional files inside the same directory as the configuration file.

## Usage

Downloads can be triggered by supplying the `{{url}}` of the requested video through the web UI or through the REST interface via curl, etc.

### Web UI

Navigate to `http://{{host}}:{{port}}/gallery-dl` and enter the requested `{{url}}`.

### Curl

```shell
curl -X POST --data-urlencode "url={{url}}" http://{{host}}:{{port}}/gallery-dl/q
```

### Fetch

```javascript
fetch(`http://${host}:${port}/gallery-dl/q`, {
  method: "POST",
  body: new URLSearchParams({
    url: url
  })
});
```

### Bookmarklet

The following bookmarklet can be used from the bookmarks bar to send the current page URL to a gallery-dl-server instance.

```javascript
javascript:(function(){var url="http://${host}:${port}/gallery-dl/q",newTab=window.open(url,"_blank"),f=newTab.document.createElement("form");f.action=url;f.method="POST";var i=newTab.document.createElement("input");i.name="url";i.type="hidden";i.value=window.location.href;f.appendChild(i);newTab.document.body.appendChild(f);f.submit();})();
```

## Implementation

This service operates using the ASGI web server [`uvicorn`](https://github.com/encode/uvicorn) and is built on the [`starlette`](https://github.com/encode/starlette) ASGI framework.

Downloads are handled by [`gallery-dl`](https://github.com/mikf/gallery-dl) in conjunction with [`yt-dlp`](https://github.com/yt-dlp/yt-dlp). The integration with gallery-dl uses Python as discussed in [this issue](https://github.com/mikf/gallery-dl/issues/642). For video downloads, gallery-dl imports and uses yt-dlp.

The Docker image is based on [`python:3.12-alpine`](https://registry.hub.docker.com/_/python), which in turn is based on [`alpine`](https://hub.docker.com/_/alpine).

## Useful Links

### gallery-dl

- Documentation: [gallery-dl/README.rst](https://github.com/mikf/gallery-dl/blob/master/README.rst)
- Config file outline: [gallery-dl/wiki/config-file-outline](https://github.com/mikf/gallery-dl/wiki/config-file-outline)
- Configuration options: [gallery-dl/docs/configuration.rst](https://github.com/mikf/gallery-dl/blob/master/docs/configuration.rst)
- List of supported sites: [gallery-dl/docs/supportedsites.md](https://github.com/mikf/gallery-dl/blob/master/docs/supportedsites.md)

### yt-dlp

- Documentation: [yt-dlp/README.md](https://github.com/yt-dlp/yt-dlp/blob/master/README.md)
- List of supported sites: [yt-dlp/supportedsites.md](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- List of extractors: [yt-dlp/yt_dlp/extractor/_extractors.py](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/_extractors.py)
