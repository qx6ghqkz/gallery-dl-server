Web UI for [`gallery-dl`](https://github.com/mikf/gallery-dl) with support for downloading videos via [`yt-dlp`](https://github.com/yt-dlp/yt-dlp). This is a fork which includes uploading cookies files. Original : https://github.com/qx6ghqkz/gallery-dl-server

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
  --name gallery-dl-server-neo \
  -p "9080:9080" \
  -e "UID=1000" \
  -e "GID=1000" \
  -v "/path/to/config:/config" \
  -v "/path/to/downloads:/gallery-dl" \
  --restart on-failure \
  ashraaf97/gallery-dl-server-neo:latest
```

#### Docker Compose

This is an example of a `docker-compose.yaml` service definition which can be used to start a running container with the `docker compose up -d` command.

```yaml
services:
  gallery-dl:
    image: ashraaf97/gallery-dl-server-neo::latest
    container_name: gallery-dl-server-neo
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

#### Important Notes

- Make sure to mount the directory containing the configuration file rather than the file itself. This ensures changes to the configuration file are propagated to the running Docker container and it will not need to be restarted for changes to take effect. More information on this issue [here](https://github.com/moby/moby/issues/15793#issuecomment-135411504).

- The output download directory depends on the `base-directory` in your gallery-dl configuration file. Make sure it is the absolute path `/gallery-dl/` instead of the relative path `./gallery-dl/` or else the download directory will need to be mounted to `/usr/src/app/gallery-dl` instead (not recommended).

- The environment variables `UID` and `GID` can be used to change the user ID and group ID of the user running the server process. This is important because downloaded files will be owned by that user. Make sure the IDs match those of the user on the host system. The default `UID:GID` is `1000:1000` when left unspecified.

### Python

If Python 3.10 or later (3.12 is recommended) is installed and on the PATH, the server can simply be run from the command line.

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
