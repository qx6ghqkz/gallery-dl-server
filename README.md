# gallery-dl-server

Web UI for [`gallery-dl`](https://github.com/mikf/gallery-dl) with support for downloading videos via [`yt-dlp`](https://github.com/yt-dlp/yt-dlp).

## Running

### Docker CLI

This example uses the docker run command to create the container to run the app.

```shell
docker run -d \
  --name gallery-dl-server \
  --user 1000:1000 \
  -p 9080:9080 \
  --mount type=bind,source="/path/to/config/gallery-dl.conf",target=/etc/gallery-dl.conf,readonly \
  --mount type=bind,source="/path/to/config/yt-dlp.conf",target=/etc/yt-dlp.conf,readonly \
  --mount type=bind,source="/path/to/downloads/gallery-dl",target=/gallery-dl \
  --mount type=bind,source="/path/to/downloads/yt-dlp",target=/yt-dlp \
  --mount type=bind,source="/path/to/data/archive.txt",target=/data/archive.txt \
  --mount type=bind,source="/path/to/data/cookies.txt",target=/data/cookies.txt \
  --restart unless-stopped \
  qx6ghqkz/gallery-dl-server:latest
```

### Docker Compose

This is an example service definition that could be put in `docker-compose.yml`. This service uses a VPN client container for its networking.

[Gluetun](https://github.com/qdm12/gluetun) is recommended for VPN use.

```yml
services:
  gallery-dl-server:
    image: qx6ghqkz/gallery-dl-server:latest
    network_mode: container:vpn
    user: 1000:1000
    volumes:
      - type: bind
        source: "/path/to/config/gallery-dl.conf"
        target: /etc/gallery-dl.conf
      - type: bind
        source: "/path/to/config/yt-dlp.conf"
        target: /etc/yt-dlp.conf
      - type: bind
        source: "/path/to/downloads/gallery-dl"
        target: /gallery-dl
      - type: bind
        source: "/path/to/downloads/yt-dlp"
        target: /yt-dlp
      - type: bind
        source: "/path/to/data/archive.txt"
        target: /data/archive.txt
      - type: bind
        source: "/path/to/data/cookies.txt"
        target: /data/cookies.txt
    restart: unless-stopped
```

### Python

If you have python ^3.6.0 installed in your PATH you can simply run like this.

```shell
python3 -m uvicorn gallery-dl-server:app --port 9080
```

### Configuration

Configuration of gallery-dl is as documented in the [official documentation](https://github.com/mikf/gallery-dl/tree/master?tab=readme-ov-file#configuration).

The configuration file must be mounted inside the Docker container in one of the locations where gallery-dl will check for the config file (gallery-dl.conf or config.json depending on the location).

The config location used in the examples is `/etc/gallery-dl.conf`. A default config file for use with gallery-dl-server is provided in this repo ([link](https://github.com/qx6ghqkz/gallery-dl-server/blob/main/gallery-dl.conf)).

The same goes for yt-dlp ([documentation](https://github.com/yt-dlp/yt-dlp/tree/master?tab=readme-ov-file#configuration)). The configuration file in the examples is mounted at `/etc/yt-dlp.conf`. An example config file for yt-dlp is provided [here](https://github.com/qx6ghqkz/gallery-dl-server/blob/main/yt-dlp.conf).

Any additional directories specified in the configuration files must also be mounted inside the Docker container, for example if you specify a cookies file location then that file must be mounted in that same location inside the Docker container.

## Usage

### Start a download remotely

Downloads can be triggered by supplying the `{{url}}` of the requested video through the Web UI or through the REST interface via curl, etc.

#### HTML

Just navigate to `http://{{host}}:9080/gallery-dl` and enter the requested `{{url}}`.

#### Curl

```shell
curl -X POST --data-urlencode "url={{url}}" http://{{host}}:9080/gallery-dl/q
```

#### Fetch

```javascript
fetch(`http://${host}:9080/gallery-dl/q`, {
  method: "POST",
  body: new URLSearchParams({
    url: url
  }),
});
```

#### Bookmarklet

Add the following bookmarklet to your bookmark bar so you can conviently send the current page url to your youtube-dl-server instance.

```javascript
javascript:!function(){fetch("http://${host}:9080/gallery-dl/q",{body:new URLSearchParams({url:window.location.href}),method:"POST"})}();
```

## Implementation

The server uses [`starlette`](https://github.com/encode/starlette) for the web framework and [`gallery-dl`](https://github.com/mikf/gallery-dl) to handle the downloading. The integration with gallery-dl uses python as described [here](https://github.com/mikf/gallery-dl/issues/642).

This docker image is based on [`python:alpine`](https://registry.hub.docker.com/_/python/) and consequently [`alpine:3.8`](https://hub.docker.com/_/alpine/).
