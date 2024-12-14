FROM python:3.12-alpine

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
  && mkdir -p /.cache/pip /.local \
  && chown -R $UID:$GID . /.cache/pip /.local \
  && chmod +x ./start.sh

CMD ["./start.sh"]
