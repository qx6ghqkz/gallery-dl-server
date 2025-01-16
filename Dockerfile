FROM python:3.12-alpine

LABEL org.opencontainers.image.source=https://github.com/qx6ghqkz/gallery-dl-server
LABEL org.opencontainers.image.description="Docker image for gallery-dl-server, a simple web and REST interface designed for downloading media using gallery-dl and yt-dlp. It serves as middleware, allowing users to supply URLs to the server through a user-friendly web UI and API. The server processes requests to fetch media from a wide range of sources and allows users to monitor progress through real-time logging."
LABEL org.opencontainers.image.licenses=MIT

RUN apk add --no-cache \
  bash \
  ffmpeg \
  shadow \
  su-exec \
  tzdata

WORKDIR /usr/src/app

COPY requirements.txt .

RUN apk add --no-cache --virtual build-deps gcc libc-dev make \
  && pip install --no-cache-dir -r requirements.txt \
  && apk del build-deps

COPY . .

ENV CONTAINER_PORT=9080

EXPOSE $CONTAINER_PORT

VOLUME ["/gallery-dl"]

ENV USER=appuser
ENV GROUP=appgroup
ENV UID=1000
ENV GID=1000

RUN groupadd --gid $GID $GROUP \
  && useradd --home-dir $(pwd) --no-create-home --shell /bin/sh --gid $GID --uid $UID $USER \
  && chown -R $UID:$GID . \
  && chmod +x ./start.sh

CMD ["./start.sh"]
